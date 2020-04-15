import base64

from .constants import *


class String(object):
    def __init__(self, name, value="", active_func=lambda: True, depends_on=None):
        if depends_on is None:
            depends_on = []
        self.depends_on = depends_on
        self._value = value
        self.name = name
        self.active_func = active_func

    def get_value(self, obj=None):
        return self._value

    def set_value(self, obj, value):
        self._value = value

    def load_value(self, value):
        self._value = value

    def test_value(self, value):
        return True, ""

    def is_active(self):
        return self.active_func() and all([x.get_value() for x in self.depends_on])

    def is_set(self):
        return self._value != ""

    def _get_current(self):
        return f" (current: {self.get_value()})" if self.get_value() else ""

    def get_user_prompt(self):
        return f"Please enter the {self.__class__.__name__.lower()} for {self.name}{self._get_current()}: "


class Path(String):
    def test_value(self, value):
        if value and not os.path.exists(value):
            return False, "please enter a valid path, which exists"
        if value and not os.path.isabs(value):
            return False, "please enter an absolute path"
        return True, ""

    def is_set(self):
        valid, msg = self.test_value(self._value)
        return valid


class Password(String):
    def get_value(self, obj=None):
        return base64.b64decode(self._value).decode("utf-8")

    def set_value(self, obj, value):
        self._value = base64.b64encode(value.encode("utf-8")).decode("utf-8")

    def _get_current(self):
        if self.get_value():
            censored = self.get_value()[0] + "*" * (len(self.get_value()) - 1)
            return f" (current: {censored})"
        return ""

    def get_user_prompt(self):
        return f"Please enter your password{self._get_current()} (password is not shown): "


class Bool(String):
    def get_value(self, obj=None):
        return "y" in self._value and self.is_active()

    def set_value(self, obj, value):
        self._value = "yes" if "y" in value else "no"

    def load_value(self, value):
        self.set_value(None, value.lower())

    def is_set(self):
        return True

    def get_user_prompt(self):
        string_value = "yes" if self.get_value() else "no"
        current = f" (current: {string_value}) (yes/no)"

        return f"Please enter the bool for {self.name}{current}: "


class Option(String):
    def __init__(self, name, options, **kwargs):
        value = kwargs.pop("value", "")
        if value and value not in options:
            raise ValueError("value not in options")
        super().__init__(name, value=value, **kwargs)
        self.options = options

    def test_value(self, value):
        if value in self.options:
            return True, ""
        return False, f"please enter a value from these options: {self.options}"

    def is_set(self):
        valid, msg = self.test_value(self._value)
        return valid

    def get_user_prompt(self):
        return f"Please enter the value for the {self.name} (valid: {self.options}){self._get_current()}: "
