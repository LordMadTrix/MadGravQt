from madgrav.gui.scene.sceneconst import ORIENTATION_CENTERED, ORIENTATION_HORIZONTAL
from madgrav.gui.scene.widget import Widget


class ToolbarWidget(Widget):
    def __init__(self, scene, left, top, **kwargs):
        Widget.__init__(self, scene, left, top, left, top, **kwargs)
        self.properties = ORIENTATION_CENTERED | ORIENTATION_HORIZONTAL
