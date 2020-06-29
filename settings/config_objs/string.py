import base64
import logging
import copy
from functools import lru_cache

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from settings.config_objs.constants import NotSet

logger = logging.getLogger(__name__)


class AbstractConfigWidget:
    def get_value(self):
        raise NotImplementedError()

    def set_value(self, value):
        raise NotImplementedError()

    def update_widget(self):
        pass


class LineEdit(QWidget, AbstractConfigWidget):
    def __init__(self, config_obj):
        super().__init__()
        self.config_obj = config_obj

        self.line_edit = QLineEdit()
        self.data_changed_signal = self.line_edit.textChanged
        if config_obj.get() is not None:
            self.set_value(config_obj.get())

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(1, 1, 1, 1)
        self.layout.addWidget(QLabel(f"{config_obj.get_gui_name()}: "))
        self.layout.addWidget(self.line_edit)
        self.setLayout(self.layout)

    def get_value(self):
        value = self.line_edit.text().strip()
        if value == "":
            return None
        return value

    def set_value(self, value):
        if value is not None:
            self.line_edit.setText(str(value))


class WidgetWrapper(QWidget):
    data_changed_signal = pyqtSignal()

    def __init__(self, config_widget, hint_text=None, parent=None):
        super().__init__(parent=parent)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)

        self.config_widget = config_widget
        self.config_widget.data_changed_signal.connect(self.data_changed_emit)
        self.layout.addWidget(self.config_widget)

        if hint_text is not None:
            hint = QLabel()
            hint.setText(hint_text)
            hint.setStyleSheet("QLabel { color : gray; }")
            self.layout.addWidget(hint)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("QLabel { color : red; }")
        if not self.set_error_msg():
            self.error_label.hide()
        self.layout.addWidget(self.error_label)

    def get_value(self):
        return self.config_widget.get_value()

    def set_value(self, value):
        self.config_widget.set_value(value)

    def set_error_msg(self):
        value = self.config_widget.get_value()
        if self.config_widget.config_obj.is_valid(value):
            return False
        msg = self.config_widget.config_obj.msg
        self.error_label.setText(msg)
        return True

    def update_widget(self):
        if self.set_error_msg():
            self.error_label.show()
        else:
            self.error_label.hide()
        self.config_widget.update_widget()

    def data_changed_emit(self, *args, **kwargs):
        self.data_changed_signal.emit()


class ConfigString(object):
    def __init__(self,
                 default=None,
                 active_func=lambda instance: True,
                 depends_on=None,
                 optional=False,
                 gui_name=None,
                 hint_text=None):
        if depends_on is None:
            depends_on = []
        self.depends_on = depends_on
        self.default = default
        self.gui_name = gui_name
        self.hint_text = hint_text
        self._value = None
        self.active_func = active_func
        self.name = None  # will be set on runtime
        self.instance = None  # will be set on runtime
        self.optional = optional
        self.msg = ""
        self._buffer = None
        self.widget = None
        self.observers = []
        if default is not None:
            self.set(default)

    def instance_created(self):
        pass

    def get_widget(self) -> WidgetWrapper:
        if self.widget is None:
            self.widget = WidgetWrapper(self.init_widget(), hint_text=self.hint_text)
        return self.widget

    def init_widget(self):
        return LineEdit(self)

    def get(self):
        return self._get()

    def _get(self):
        return self._value

    def get_from_widget(self):
        if self.widget is None:
            raise ValueError("Widget not active")
        return self.widget.get_value()

    def get_gui_name(self):
        if self.gui_name is not None:
            return self.gui_name
        return self.name

    def set(self, value):
        if not self.is_valid(value):
            raise ValueError(f"Can not set invalid value. msg: {self.msg}")
        self._set(value)

    def _set(self, value):
        self._value = value

    def set_to_widget(self, value):
        if self.widget is not None:
            self.widget.set_value(value)

    def set_from_widget(self):
        value = self.widget.get_value()
        self.set(value)

    def is_valid_from_widget(self):
        if self.widget is None:
            return None
        value = self.widget.get_value()
        return self.is_valid(value)

    def test(self, value):
        if value is None:
            return True
        try:
            self._test(value)
            return True
        except ValueError as e:
            self.msg = str(e)
            return False

    def _test(self, value):
        return True

    def load(self, value):
        if not value:
            return
        self._value = self._load(value)

    def _load(self, value):
        return value

    def save(self):
        if self._value is None:
            return None

        if self.test(self._value):
            return self._save()
        raise ValueError("Tried to save an invalid ConfigObject")

    def _save(self):
        return self._value

    def is_active(self, value=NotSet):
        if value is NotSet:
            value = self._value
        return self.active_func(self.instance) and all([x.is_set(value) for x in self.depends_on])

    def is_set(self, value=NotSet):
        if value is NotSet:
            value = self._value
        if isinstance(value, str) and value == "":
            value = None
        return value is not None or self.optional

    def is_valid(self, value=NotSet):
        if value is NotSet:
            value = self._value

        result = self._is_valid(value)
        return result

    def _is_valid(self, value):
        if not self.is_active(value):
            return True
        if not self.is_set(value):
            self.msg = "Can not be empty"
            return False
        if not self.test(value):
            return False
        return True

    def set_parser(self, parser):
        parser.add_argument(f"--{self.name}")

    def reset_widget(self):
        self.set_to_widget(self.get())

    def update_widget(self):
        if self.widget is None:
            return
        self.widget.update_widget()

    def update_visibility(self):
        if self.widget is None:
            return
        if self.is_active():
            self.widget.show()
        else:
            self.widget.hide()

    def cancel(self):
        pass

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if v is self.widget:
                setattr(result, k, v)
            else:
                setattr(result, k, copy.deepcopy(v, memo))
        return result
