import logging
import os

import yaml
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from gui.constants import TEMPLATE_PRESET_FILE_PATHS
from gui.template_edit.view_tree import TemplateEditViewTree
from gui.utils import widget_read_settings, widget_save_settings

logger = logging.getLogger(__name__)


class TemplateEditDialog(QDialog):
    def __init__(self, parent, template_path, template_path_settings):
        super().__init__(parent=parent, flags=Qt.Window)
        self.setWindowTitle("Edit")
        self.setWindowModality(Qt.ApplicationModal)
        self.template_path_settings = template_path_settings
        self.is_new = template_path is None

        self.button_box = QDialogButtonBox()
        self.save_btn = self.button_box.addButton("Save", QDialogButtonBox.YesRole)
        self.save_as_btn = self.button_box.addButton("Save As...", QDialogButtonBox.YesRole)
        self.cancel_btn = self.button_box.addButton(QDialogButtonBox.Cancel)

        for button in self.button_box.buttons():
            button.setAutoDefault(False)
            button.setDefault(False)

        self.button_box.clicked.connect(self.save_and_exit)
        self.button_box.rejected.connect(self.exit)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.template_view = TemplateEditViewTree(template_path=template_path, parent=self)
        self.template_dict = None

        self.layout.addWidget(self.template_view)
        self.layout.addWidget(self.button_box)

        self.finished.connect(self.save_geometry)
        self.finished.connect(self.template_view.save_state)

    def show(self):
        self.read_settings()
        super().show()

    def save_and_exit(self, button):
        if button is self.cancel_btn:
            return

        template_dict = self.template_view.convert_to_dict()

        path = self.template_path_settings.template_path
        if self.is_new or\
                path in TEMPLATE_PRESET_FILE_PATHS or\
                button is self.save_as_btn:
            if self.template_path_settings.template_path not in TEMPLATE_PRESET_FILE_PATHS:
                directory = os.path.dirname(self.template_path_settings.template_path)
            else:
                directory = QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)

            path = QFileDialog.getSaveFileName(
                parent=self,
                caption="Save File",
                directory=directory,
                filter=" ".join([f"*.{extension}" for extension
                                 in self.template_path_settings['template_path'].file_extensions])
            )[0]

        if not path:
            return

        try:
            with open(path, "w+") as f:
                f.write(yaml.dump(template_dict))
        except Exception as e:
            error_dialog = QErrorMessage(self)
            error_dialog.setWindowTitle("Error")
            error_dialog.showMessage(f"Could not save your file. {e}")
            error_dialog.raise_()
            return

        try:
            self.template_path_settings.template_path = path
        except ValueError:
            os.remove(path)
            error_dialog = QErrorMessage(self)
            error_dialog.setWindowTitle("Error")
            error_dialog.showMessage(f"{path} has not the right file format.")
            error_dialog.raise_()
            return

        self.template_path_settings.save()

        self.accept()

    def exit(self):
        self.reject()

    def closeEvent(self, event):
        self.save_geometry()
        self.template_view.save_state()
        super().closeEvent(event)

    def save_geometry(self):
        widget_save_settings(self, save_state=False)

    def read_settings(self):
        widget_read_settings(self, save_state=False)
