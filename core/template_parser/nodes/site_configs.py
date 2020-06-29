import importlib
import inspect
import traceback
import re
import os
import time
import logging
import asyncio
from functools import partial

from PyQt5.QtGui import *

from core.storage import cache
from core.exceptions import ParseTemplateError, ParseTemplateRuntimeError
from core.template_parser.nodes.base import TemplateNode, NodeConfigs
from core.template_parser import nodes
from core.template_parser.queue_wrapper import QueueWrapper
from core.template_parser.constants import POSSIBLE_CONSUMER_KWARGS
from core.template_parser.utils import get_module_function, check_if_null, dict_to_string, login_module
from core.utils import safe_path_join
from gui.constants import SITE_ICON_PATH
from settings.config_objs import ConfigString, ConfigBool, ConfigOptions, ConfigDict, ConfigList
from settings import global_settings

logger = logging.getLogger(__name__)


class FunctionKwargsConfigDict(ConfigDict):
    def __init__(self, *args, **kwargs):
        super().__init__(layout={}, *args, **kwargs)
        self.current_module = None
        self.current_function = None
        self.widget_layouts = {}
        self.layouts = {}

    def _set(self, value):
        raw_module_name = self.instance["raw_module_name"].get()
        raw_function = self.instance["raw_function"].get()
        self.change_layout(raw_module_name, raw_function)
        super()._set(value)

    def cancel(self):
        raw_module_name = self.instance["raw_module_name"].get()
        raw_function = self.instance["raw_function"].get()
        self.change_layout(raw_module_name, raw_function)

    def change_layout(self, current_module, current_function):
        key = str(current_module)+str(current_function)
        if key in self.layouts:
            if self.layouts[key] is self.layout:
                return
        else:
            layout = self.create_layout(current_module, current_function)
            self.layouts[key] = layout

        self.layout = self.layouts[key]

        if self.widget is not None:
            self.widget.config_widget.clear()
            self.widget.config_widget.init()

    @staticmethod
    def create_layout(raw_module_name, raw_function):
        result = {}

        if raw_module_name is None:
            return {}

        try:
            module_name, function_name = nodes.Site.get_module_func_name(raw_module_name,
                                                                         raw_function)
        except ParseTemplateError:
            return {}

        site_module = importlib.import_module(module_name)
        producer_function = getattr(site_module, function_name)

        try:
            for name, parameter in inspect.signature(producer_function).parameters.items():
                if name in ["session", "queue", "base_path", "site_settings"]:
                    continue
                default_value = parameter.default if parameter.default is not parameter.empty else None
                optional = parameter.default != parameter.empty
                if isinstance(default_value, bool):
                    config_obj = ConfigBool(default=default_value, optional=optional)
                else:
                    config_obj = ConfigString(default=default_value, optional=optional)
                result[name] = config_obj
        except TypeError:
            return {}

        return result

    def reset_widget(self):
        raw_module_name = self.instance["raw_module_name"].get()
        raw_function = self.instance["raw_function"].get()
        self.change_layout(raw_module_name, raw_function)
        super().reset_widget()

    def update_widget(self):
        raw_module_name = self.instance["raw_module_name"].get_from_widget()
        raw_function = self.instance["raw_function"].get_from_widget()
        self.change_layout(raw_module_name, raw_function)
        super().update_widget()


def raw_folder_name_active(instance: NodeConfigs):
    try:
        use_folder = instance.get_config_obj("use_folder").get_from_widget()
        folder_function = instance.get_config_obj("raw_folder_function").get_from_widget()
        return use_folder and folder_function is None
    except ValueError:
        return False


def raw_function_active(instance):
    try:
        return instance.get_config_obj("raw_module_name").get_from_widget() == "custom"
    except ValueError:
        return False


def folder_function_active(instance):
    try:
        raw_module_name = instance.get_config_obj("raw_module_name").get_from_widget()
        use_folder = instance.get_config_obj("use_folder").get_from_widget()
        raw_folder_name = instance.get_config_obj("raw_folder_name").get_from_widget()
        return raw_module_name == "custom" and use_folder and raw_folder_name is None
    except ValueError:
        return False


class SiteConfigs(NodeConfigs):
    TITLE_NAME = "Site"

    raw_module_name = ConfigOptions(optional=False, options=["moodle",
                                                             "nethz",
                                                             "custom",
                                                             "video_portal",
                                                             "ilias",
                                                             "polybox"])
    use_folder = ConfigBool(default=True)
    raw_folder_name = ConfigString(optional=True, active_func=raw_folder_name_active)
    raw_function = ConfigString(active_func=raw_function_active)
    raw_folder_function = ConfigString(active_func=folder_function_active)

    consumer_kwargs = ConfigDict(layout={name: ConfigList(optional=True, hint_text="Add 'video' for all video types")
                                         for name in POSSIBLE_CONSUMER_KWARGS})

    function_kwargs = FunctionKwargsConfigDict()

    def get_name(self):
        if self.raw_module_name is not None:
            return self.raw_module_name
        return "+ Add Site"

    def get_icon(self):
        image_files = os.listdir(SITE_ICON_PATH)
        file_name = None
        for image_file in image_files:
            if self.raw_module_name is not None and self.raw_module_name in image_file:
                file_name = image_file
                break
        if file_name is None:
            return super(SiteConfigs, self).get_icon()

        path = os.path.join(SITE_ICON_PATH, file_name)
        return QIcon(path)
