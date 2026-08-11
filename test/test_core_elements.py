import math
import unittest

from madgrav.core.node.node import Node
from madgrav.core.units import UNITS_PER_MIL
from test import bootstrap


class TestElements(unittest.TestCase):
    def test_elements_type(self):
        """
        Tests some generic elements commands and validates output as correct type
        """
        kernel = bootstrap.bootstrap()

        @kernel.console_command("validate_type", input_type="elements")
        def validation_type(command, data=None, **kwargs):
            for node in data:
                self.assertTrue(isinstance(node, Node))

        try:
            for cmd, path, command in kernel.find("command/elements.*"):
                kernel.console(
                    "element* " + command.split("/")[-1] + " validate_type\n"
                )
        finally:
            kernel()

    def test_elements_specific(self):
        """
        Tests specific elements for correct non-failure.
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel.console("polyline grid 3 3\n")
            kernel.console("polyline 3cm 3cm  2cm 2cm 1cm 1cm grid 3 3\n")
            kernel.console("circle 2cm 2cm 1cm grid 3 3\n")
            kernel.console("rect 2cm 2cm 1cm 1cm grid 3 3\n")
            kernel.console("ellipse 2cm 2cm 1cm 1cm grid 3 3\n")
            kernel.console("line 2cm 2cm 1cm 1cm grid 3 3\n")
            kernel.console("element* circ_copy 4 10mm 5deg 0.5turn -d 25deg")
            kernel.console("element* radial 2 5mm 20deg 200deg")
        finally:
            kernel()

    def test_elements_frame(self):
        """
        Test frame command creates a rectangle of a rectangle
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel.console("rect 2cm 2cm 1cm 1cm\n")
            kernel.console("frame\n")
            f = list(kernel.elements.elem_branch.flat(types="elem rect"))
            self.assertAlmostEqual(f[0].x, f[1].x)
            self.assertAlmostEqual(f[0].y, f[1].y)
            self.assertAlmostEqual(f[0].width, f[1].width)
            self.assertAlmostEqual(f[0].height, f[1].height)
            self.assertAlmostEqual(f[0].rx, f[1].rx)
            self.assertAlmostEqual(f[0].ry, f[1].ry)
        finally:
            kernel()

    def test_elements_circle(self):
        """
        Intro test for elements

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel_root = kernel.get_context("/")
            kernel_root("circle 1in 1in 1in\n")
            for node in kernel_root.elements.elems():
                self.assertEqual(node.cx, 1000 * UNITS_PER_MIL)
                self.assertEqual(node.cy, 1000 * UNITS_PER_MIL)
                self.assertEqual(node.rx, 1000 * UNITS_PER_MIL)
                self.assertEqual(node.ry, 1000 * UNITS_PER_MIL)
                self.assertEqual(node.stroke, "blue")
        finally:
            kernel()

    def test_elements_rect(self):
        """
        Intro test for elements

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel_root = kernel.get_context("/")
            kernel_root("rect 1in 1in 1in 1in stroke red fill blue\n")
            for node in kernel_root.elements.elems():
                self.assertEqual(node.x, 1000 * UNITS_PER_MIL)
                self.assertEqual(node.y, 1000 * UNITS_PER_MIL)
                self.assertEqual(node.width, 1000 * UNITS_PER_MIL)
                self.assertEqual(node.height, 1000 * UNITS_PER_MIL)
                self.assertEqual(node.stroke, "red")
                self.assertEqual(node.fill, "blue")
        finally:
            kernel()

    def test_elements_clipboard(self):
        """
        Intro test for elements

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel_root = kernel.get_context("/")
            kernel_root("rect 1in 1in 1in 1in stroke red fill blue\n")
            kernel_root("clipboard copy\n")
            kernel_root("clipboard paste -xy 2in 2in\n")
            kernel_root("grid 2 4\n")
        finally:
            kernel()

    def test_elements_shapes(self):
        """
        Intro test for elements

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel_root = kernel.get_context("/")
            kernel_root("shape 5 2in 2in 1in\n")
            # kernel_root("polygon 1in 1in 2in 2in 0in 4cm\n")

        finally:
            kernel()

    def test_elements_bad_grid(self):
        """
        Intro test for elements

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel_root = kernel.get_context("/")
            kernel_root("shape 5 2in 2in 1in\n")
            kernel_root("grid 2 2 1in 1foo\n")
        finally:
            kernel()

    def test_move_to_laser_on_locked_element_does_not_corrupt_geometry(self):
        # Regression test for the same class of bug fixed for "position"
        # (see test_qt_main.py:
        # test_position_field_edit_on_locked_element_moves_it_without_corruption):
        # "move_to_laser" (madgrav/core/elements/shapes.py:
        # element_move_to_laser) computed its reference bounds with
        # Node.union_bounds(data), which defaults to ignore_locked=True.
        # Locking an element doesn't block repositioning by default
        # (elements.lock_allows_move defaults to True -- lock only blocks
        # GUI drag-move), but with every selected node locked, that
        # default silently excluded them all from their own reference
        # bounds, leaving it at union_bounds()'s empty-set sentinel
        # (inf, inf, -inf, -inf). ntx/nty then came out +-infinity and
        # got written straight into the node's transform matrix via
        # post_translate(), permanently wrecking its geometry. Fixed by
        # passing ignore_locked=False at that call site.
        kernel = bootstrap.bootstrap()
        try:
            kernel_root = kernel.get_context("/")
            elements = kernel_root.elements
            kernel_root("rect 10mm 10mm 5mm 5mm\n")
            node = list(elements.elems())[-1]
            elements.set_emphasis([node])
            node.lock = True
            self.assertTrue(node.lock)

            kernel_root("move_to_laser\n")

            bounds = node.bounds
            self.assertTrue(all(math.isfinite(b) for b in bounds), bounds)
        finally:
            kernel()
