# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2011 Lars Kruse <devel@sumpfralle.de>

This file is part of PyCAM.

PyCAM is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

PyCAM is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PyCAM.  If not, see <http://www.gnu.org/licenses/>.
"""


import pycam.Plugins


class ModelPlaneMirror(pycam.Plugins.PluginBase):

    UI_FILE = "model_plane_mirror.ui"
    DEPENDS = ["Models"]

    def setup(self):
        if self.gui:
            mirror_box = self.gui.get_object("ModelMirrorBox")
            mirror_box.unparent()
            self.core.register_ui("model_handling", "Mirror", mirror_box, 0)
            self.gui.get_object("PlaneMirrorButton").connect("clicked",
                    self._plane_mirror)
        return True

    def teardown(self):
        if self.gui:
            self.core.unregister_ui("model_handling",
                    self.gui.get_object("ModelMirrorBox"))

    def _plane_mirror(self, widget=None):
        model = self.core.get("model")
        if not model:
            return
        self.core.emit_event("model-change-before")
        self.core.get("update_progress")("Mirroring model")
        self.core.get("disable_progress_cancel_button")()
        for plane in ("XY", "XZ", "YZ"):
            if self.gui.get_object("MirrorPlane%s" % plane).get_active():
                break
        model.transform_by_template("%s_mirror" % plane.lower(),
                callback=self.core.get("update_progress"))
        self.core.emit_event("model-change-after")
