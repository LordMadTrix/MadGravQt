"""
Precise Camera <-> Bed Alignment Wizard for MadGrav.

Mirrors LightBurn's "burn a target, photograph it, click the marks" camera
alignment workflow, but supports 4-9 points (not just 4) with a RANSAC
homography and a real residual-error score in mm, instead of a plain
4-corner stretch.

The wizard never fires the laser itself: it generates the target geometry
and a dedicated low-power engrave operation, and tells the user to run it
from the normal Job panel, same as any other job.
"""

import cv2
import wx

from madgrav.camera.camera import (
    _camera_service_for_index,
    frame_for_wx_bitmap,
)
from madgrav.camera.gui.cameracal import _bed_bbox
from madgrav.core.geomstr import Geomstr
from madgrav.core.node.op_engrave import EngraveOpNode
from madgrav.core.units import UNITS_PER_MM
from madgrav.gui.icons import icons8_image_in_frame
from madgrav.gui.mwindow import MWindow
from madgrav.gui.wxutils import StaticBoxSizer, wxButton, wxStaticText
from madgrav.svgelements import Color

_ = wx.GetTranslation

# Priority order in which target points are added as the requested count
# grows from 4 to 9 -- corners first (minimal, matches LightBurn), then
# center, then the four edge midpoints. Coordinates are fractions (fx, fy)
# of the inset bed rectangle, 0..1. This same order is used both when
# burning the numbered marks and when collecting clicks, so index i always
# refers to the same physical point in both places.
_POINT_FRACTIONS = [
    (0.0, 0.0),  # 1: top-left
    (1.0, 0.0),  # 2: top-right
    (1.0, 1.0),  # 3: bottom-right
    (0.0, 1.0),  # 4: bottom-left
    (0.5, 0.5),  # 5: center
    (0.5, 0.0),  # 6: top-mid
    (0.5, 1.0),  # 7: bottom-mid
    (0.0, 0.5),  # 8: left-mid
    (1.0, 0.5),  # 9: right-mid
]

MARK_RADIUS_MM = 6.0
MARK_INSET_MM = 20.0  # keep targets off the very edge of the bed
CLICK_CANVAS_MAX_DIM = 900  # max display size (px) for the click-photo


def generate_alignment_target_points(device, count):
    """
    Return `count` (4-9) known bed positions in real millimeters, in the
    fixed priority order used both for burning (numbered marks) and for
    the click-canvas step, so the two orders always match.

    @param device: active laser device (for bed bounds)
    @param count: how many target points to generate (clamped to 4-9)
    @return: list of (mm_x, mm_y) tuples
    """
    count = max(4, min(9, int(count)))
    x0, y0, x1, y1 = _bed_bbox(device)
    x_left, x_right = min(x0, x1), max(x0, x1)
    y_top, y_bottom = min(y0, y1), max(y0, y1)
    inset = MARK_INSET_MM * UNITS_PER_MM
    ix0, ix1 = x_left + inset, x_right - inset
    iy0, iy1 = y_top + inset, y_bottom - inset
    if ix1 <= ix0:
        ix0, ix1 = x_left, x_right
    if iy1 <= iy0:
        iy0, iy1 = y_top, y_bottom
    points_mm = []
    for fx, fy in _POINT_FRACTIONS[:count]:
        sx = ix0 + fx * (ix1 - ix0)
        sy = iy0 + fy * (iy1 - iy0)
        points_mm.append((sx / UNITS_PER_MM, sy / UNITS_PER_MM))
    return points_mm


def build_alignment_target(context, points_mm, power, speed):
    """
    Create numbered alignment marks (circle + crosshair) at the given known
    bed-mm positions, all bound to one dedicated engrave operation. Does
    NOT queue or fire anything -- the user reviews and starts the job from
    the normal Job panel.

    @param context: kernel root context
    @param points_mm: list of (mm_x, mm_y) target positions
    @param power: op power, 0-1000 scale
    @param speed: op speed, mm/s
    @return: the created EngraveOpNode
    """
    elements = context.elements
    op = EngraveOpNode()
    op.power = power
    op.speed = speed
    op.color = Color("red")
    op.label = _("Camera Alignment Target")
    elements.op_branch.add_node(op)

    r = MARK_RADIUS_MM * UNITS_PER_MM
    for i, (mx, my) in enumerate(points_mm):
        cx = mx * UNITS_PER_MM
        cy = my * UNITS_PER_MM
        geom = Geomstr()
        geom.append(Geomstr.circle(r, cx, cy))
        geom.append(Geomstr.circle(r * 0.3, cx, cy))
        ext = r * 1.4
        geom.line(complex(cx - ext, cy), complex(cx + ext, cy))
        geom.line(complex(cx, cy - ext), complex(cx, cy + ext))
        node = elements.elem_branch.add(
            geometry=geom,
            type="elem path",
            stroke=op.color,
            stroke_width=elements.default_strokewidth,
        )
        node.label = _("Align target {n}").format(n=i + 1)
        op.add_reference(node, 0)

        # Visual-only number next to each mark (not burned -- keeps the
        # physical job simple, this is just to help match photo clicks
        # to the right target while reviewing on screen).
        text_node = elements.elem_branch.add(
            type="elem text",
            text=str(i + 1),
            x=cx + ext + MARK_RADIUS_MM * UNITS_PER_MM * 0.3,
            y=cy,
            stroke=op.color,
        )
        text_node.label = _("Align label {n}").format(n=i + 1)

    elements.signal("refresh_scene")
    return op


class _ClickCanvas(wx.Panel):
    """Static photo with click-to-place numbered pins."""

    def __init__(self, parent, rgb_frame, on_points_changed=None):
        super().__init__(parent, style=wx.FULL_REPAINT_ON_RESIZE | wx.BORDER_SIMPLE)
        self.on_points_changed = on_points_changed
        orig_h, orig_w = rgb_frame.shape[:2]
        scale = min(1.0, CLICK_CANVAS_MAX_DIM / max(orig_w, orig_h))
        self.scale = scale
        disp_w = max(1, int(round(orig_w * scale)))
        disp_h = max(1, int(round(orig_h * scale)))
        if scale != 1.0:
            display_frame = cv2.resize(
                rgb_frame, (disp_w, disp_h), interpolation=cv2.INTER_AREA
            )
        else:
            display_frame = rgb_frame
        arr = frame_for_wx_bitmap(display_frame)
        img = wx.Image(disp_w, disp_h)
        img.SetData(arr.tobytes())
        self.bitmap = wx.Bitmap(img)
        self.SetMinSize((disp_w, disp_h))
        # Displayed (scaled) coordinates, for drawing pins.
        self.points_display = []
        # Original raw-frame pixel coordinates, matching the camera's
        # get_alignment_capture_frame() pixel space -- this is what gets
        # paired with the known bed-mm points for the homography.
        self.points_original = []
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_click)

    def _on_paint(self, event):
        dc = wx.PaintDC(self)
        dc.DrawBitmap(self.bitmap, 0, 0, True)
        gc = wx.GraphicsContext.Create(dc)
        if gc is None:
            return
        radius = 10
        for i, (x, y) in enumerate(self.points_display):
            gc.SetPen(wx.Pen(wx.RED, 3))
            gc.SetBrush(wx.Brush(wx.Colour(255, 0, 0, 130)))
            gc.DrawEllipse(x - radius, y - radius, radius * 2, radius * 2)
            gc.SetFont(
                wx.Font(
                    12,
                    wx.FONTFAMILY_SWISS,
                    wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_BOLD,
                ),
                wx.WHITE,
            )
            label = str(i + 1)
            tw, th = gc.GetTextExtent(label)
            gc.DrawText(label, x - tw / 2, y - radius - th - 2)

    def _on_click(self, event):
        x, y = event.GetX(), event.GetY()
        self.points_display.append((x, y))
        self.points_original.append((x / self.scale, y / self.scale))
        self.Refresh()
        if self.on_points_changed:
            self.on_points_changed()

    def undo_last(self):
        if self.points_display:
            self.points_display.pop()
            self.points_original.pop()
            self.Refresh()
            if self.on_points_changed:
                self.on_points_changed()


class _ClickTargetDialog(wx.Dialog):
    """Modal photo-click step: collects `count` ordered pixel coordinates."""

    def __init__(self, parent, rgb_frame, count):
        super().__init__(
            parent,
            title=_("Click each burnt alignment mark, in order"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.count = count
        self.result_points = None
        try:
            parent.context.themes.set_window_colors(self)
        except AttributeError:
            pass

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.label_progress = wxStaticText(self, wx.ID_ANY, "")
        sizer.Add(self.label_progress, 0, wx.ALL | wx.EXPAND, 6)

        self.canvas = _ClickCanvas(self, rgb_frame, self._refresh_progress)
        sizer.Add(self.canvas, 1, wx.ALL | wx.EXPAND, 6)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_undo = wxButton(self, wx.ID_ANY, _("Undo last click"))
        self.btn_done = wxButton(self, wx.ID_ANY, _("Done"))
        self.btn_cancel = wxButton(self, wx.ID_CANCEL, _("Cancel"))
        row.Add(self.btn_undo, 0, wx.RIGHT, 6)
        row.Add(self.btn_done, 0, wx.RIGHT, 6)
        row.Add(self.btn_cancel, 0, 0, 0)
        sizer.Add(row, 0, wx.ALL | wx.ALIGN_RIGHT, 6)

        self.SetSizerAndFit(sizer)
        self.btn_undo.Bind(wx.EVT_BUTTON, lambda e: self.canvas.undo_last())
        self.btn_done.Bind(wx.EVT_BUTTON, self._on_done)
        self._refresh_progress()

    def _refresh_progress(self):
        n = len(self.canvas.points_display)
        self.label_progress.SetLabel(
            _("Click target #{next} of {total} (placed so far: {n}/{total}).").format(
                next=min(n + 1, self.count), total=self.count, n=n
            )
        )
        self.btn_done.Enable(n == self.count)

    def _on_done(self, event=None):
        self.result_points = list(self.canvas.points_original)
        self.EndModal(wx.ID_OK)


class CameraAlignWizard(MWindow):
    """Guided burn-target -> photo -> click -> homography alignment flow."""

    def __init__(self, *args, **kwds):
        super().__init__(560, 640, *args, **kwds)
        self._target_points_mm = None

        cam_box = StaticBoxSizer(self, wx.ID_ANY, _("Camera"), wx.VERTICAL)
        row_cam = wx.BoxSizer(wx.HORIZONTAL)
        row_cam.Add(
            wxStaticText(self, wx.ID_ANY, _("Index")), 0, wx.ALIGN_CENTER_VERTICAL, 0
        )
        self.spin_camera = wx.SpinCtrl(self, wx.ID_ANY, min=0, max=8, initial=0)
        row_cam.Add(self.spin_camera, 0, wx.LEFT, 4)
        cam_box.Add(row_cam, 0, wx.EXPAND, 0)

        target_box = StaticBoxSizer(
            self, wx.ID_ANY, _("1. Generate target"), wx.VERTICAL
        )
        row_count = wx.BoxSizer(wx.HORIZONTAL)
        row_count.Add(
            wxStaticText(self, wx.ID_ANY, _("Number of points (4-9)")),
            0,
            wx.ALIGN_CENTER_VERTICAL,
            0,
        )
        self.spin_count = wx.SpinCtrl(self, wx.ID_ANY, min=4, max=9, initial=9)
        row_count.Add(self.spin_count, 0, wx.LEFT, 4)
        target_box.Add(row_count, 0, wx.EXPAND | wx.BOTTOM, 4)

        row_power = wx.BoxSizer(wx.HORIZONTAL)
        row_power.Add(
            wxStaticText(self, wx.ID_ANY, _("Power (%)")),
            0,
            wx.ALIGN_CENTER_VERTICAL,
            0,
        )
        self.spin_power = wx.SpinCtrl(self, wx.ID_ANY, min=1, max=100, initial=15)
        row_power.Add(self.spin_power, 0, wx.LEFT, 4)
        row_power.Add(
            wxStaticText(self, wx.ID_ANY, _("Speed (mm/s)")),
            0,
            wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            12,
        )
        self.spin_speed = wx.SpinCtrl(self, wx.ID_ANY, min=1, max=500, initial=20)
        row_power.Add(self.spin_speed, 0, wx.LEFT, 4)
        target_box.Add(row_power, 0, wx.EXPAND | wx.BOTTOM, 4)

        target_box.Add(
            wxStaticText(
                self,
                wx.ID_ANY,
                _(
                    "Conservative defaults, not a guarantee for your laser or\n"
                    "material -- verify on scrap before trusting them."
                ),
            ),
            0,
            wx.EXPAND | wx.BOTTOM,
            4,
        )
        self.btn_generate = wxButton(self, wx.ID_ANY, _("Generate target marks"))
        target_box.Add(self.btn_generate, 0, wx.EXPAND, 0)

        instr_box = StaticBoxSizer(self, wx.ID_ANY, _("2. Burn it yourself"), wx.VERTICAL)
        instr_box.Add(
            wxStaticText(
                self,
                wx.ID_ANY,
                _(
                    "1. Place scrap material flat on the bed; leave the\n"
                    "   camera and material undisturbed from now on.\n"
                    "2. Review the generated marks and the new engrave\n"
                    "   operation's power/speed above.\n"
                    "3. Go to the Job panel and start the job yourself,\n"
                    "   exactly as you would for any other job.\n"
                    "4. Do not move the camera or the material after\n"
                    "   burning, until you've finished this wizard."
                ),
            ),
            0,
            wx.EXPAND,
            0,
        )

        photo_box = StaticBoxSizer(
            self, wx.ID_ANY, _("3. Photograph and click"), wx.VERTICAL
        )
        self.btn_photo = wxButton(self, wx.ID_ANY, _("I've burned it — take photo"))
        self.btn_photo.Enable(False)
        photo_box.Add(self.btn_photo, 0, wx.EXPAND, 0)

        result_box = StaticBoxSizer(self, wx.ID_ANY, _("4. Result"), wx.VERTICAL)
        self.label_score = wxStaticText(
            self, wx.ID_ANY, _("No calibration computed yet.")
        )
        result_box.Add(self.label_score, 0, wx.EXPAND | wx.BOTTOM, 4)
        row_result = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_apply = wxButton(self, wx.ID_ANY, _("Apply"))
        self.btn_redo = wxButton(self, wx.ID_ANY, _("Start over"))
        self.btn_revert = wxButton(self, wx.ID_ANY, _("Revert to approximate mode"))
        self.btn_apply.Enable(False)
        for b in (self.btn_apply, self.btn_redo, self.btn_revert):
            row_result.Add(b, 1, wx.EXPAND | wx.RIGHT, 4)
        result_box.Add(row_result, 0, wx.EXPAND, 0)

        self.sizer.Add(cam_box, 0, wx.EXPAND | wx.ALL, 8)
        self.sizer.Add(target_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self.sizer.Add(instr_box, 0, wx.EXPAND | wx.ALL, 8)
        self.sizer.Add(photo_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self.sizer.Add(result_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.btn_generate.Bind(wx.EVT_BUTTON, self.on_generate)
        self.btn_photo.Bind(wx.EVT_BUTTON, self.on_photo)
        self.btn_apply.Bind(wx.EVT_BUTTON, self.on_apply)
        self.btn_redo.Bind(wx.EVT_BUTTON, self.on_redo)
        self.btn_revert.Bind(wx.EVT_BUTTON, self.on_revert)

        self.Layout()

    def _camera_index(self):
        return self.spin_camera.GetValue()

    def _camera_service(self):
        return _camera_service_for_index(self.context.kernel, self._camera_index())

    def on_generate(self, event=None):
        cam = self._camera_service()
        if cam is None:
            wx.MessageBox(
                _("Open the camera window for this index first."),
                _("No camera"),
                wx.OK | wx.ICON_WARNING,
                parent=self,
            )
            return
        device = self.context.device
        count = self.spin_count.GetValue()
        power = self.spin_power.GetValue() * 10.0  # percent -> 0-1000 scale
        speed = self.spin_speed.GetValue()
        points_mm = generate_alignment_target_points(device, count)
        build_alignment_target(self.context, points_mm, power, speed)
        self._target_points_mm = points_mm
        self.btn_photo.Enable(True)
        wx.MessageBox(
            _(
                "{n} target marks and a dedicated engrave operation were\n"
                "added. Review its power/speed, place scrap material, then\n"
                "start the job yourself from the Job panel."
            ).format(n=count),
            _("Target generated"),
            wx.OK | wx.ICON_INFORMATION,
            parent=self,
        )

    def on_photo(self, event=None):
        cam = self._camera_service()
        if cam is None or self._target_points_mm is None:
            return
        raw = cam.get_alignment_capture_frame()
        if raw is None:
            wx.MessageBox(
                _(
                    "No camera frame available yet -- make sure the camera\n"
                    "is connected and showing a live image first."
                ),
                _("No photo"),
                wx.OK | wx.ICON_WARNING,
                parent=self,
            )
            return
        rgb = cv2.cvtColor(raw, cv2.COLOR_BGR2RGB)
        dlg = _ClickTargetDialog(self, rgb, len(self._target_points_mm))
        try:
            if dlg.ShowModal() == wx.ID_OK and dlg.result_points:
                try:
                    rms = cam.compute_alignment_homography(
                        dlg.result_points, self._target_points_mm
                    )
                except ValueError as e:
                    wx.MessageBox(
                        str(e), _("Calibration failed"), wx.OK | wx.ICON_ERROR, parent=self
                    )
                    return
                self._update_score_label(rms)
                self.btn_apply.Enable(True)
                self.context.signal("refresh_scene")
        finally:
            dlg.Destroy()

    def _update_score_label(self, rms):
        if rms < 0.5:
            colour = wx.Colour(0, 150, 0)
            verdict = _("Excellent")
        elif rms < 2.0:
            colour = wx.Colour(210, 120, 0)
            verdict = _("Usable")
        else:
            colour = wx.Colour(200, 0, 0)
            verdict = _("Poor -- consider Start over")
        self.label_score.SetForegroundColour(colour)
        self.label_score.SetLabel(
            _("Alignment error: {rms:.2f} mm ({verdict}).").format(
                rms=rms, verdict=verdict
            )
        )

    def on_apply(self, event=None):
        wx.MessageBox(
            _(
                "Alignment applied -- the camera bed overlay now uses this\n"
                "precise calibration until you Start over or Revert."
            ),
            _("Applied"),
            wx.OK | wx.ICON_INFORMATION,
            parent=self,
        )
        self.context.signal("refresh_scene")

    def on_redo(self, event=None):
        cam = self._camera_service()
        if cam is not None:
            cam.reset_alignment_homography()
        self._target_points_mm = None
        self.btn_photo.Enable(False)
        self.btn_apply.Enable(False)
        self.label_score.SetForegroundColour(wx.BLACK)
        self.label_score.SetLabel(_("No calibration computed yet."))
        self.context.signal("refresh_scene")

    def on_revert(self, event=None):
        cam = self._camera_service()
        if cam is not None:
            cam.reset_alignment_homography()
        self.context.signal("refresh_scene")
        wx.MessageBox(
            _("Reverted to the approximate corner-drag alignment mode."),
            _("Reverted"),
            wx.OK | wx.ICON_INFORMATION,
            parent=self,
        )

    def window_open(self):
        self.Raise()

    @staticmethod
    def sub_register(kernel):
        kernel.register(
            "button/preparation/CameraAlignWizard",
            {
                "label": _("Precise Camera Align"),
                "icon": icons8_image_in_frame,
                "tip": _("Burn-and-click camera-to-bed alignment (LightBurn-style)"),
                "help": "camalignwizard",
                "action": lambda v: kernel.console("window toggle CameraAlignWizard\n"),
                "priority": 5,
            },
        )

    @staticmethod
    def submenu():
        return "Editing", "Camera", True

    @staticmethod
    def helptext():
        return _(
            "Precise camera-to-bed alignment: burn a target, photograph it, click the marks"
        )
