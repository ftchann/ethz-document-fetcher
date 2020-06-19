from core.template_parser.utils import ignore_if_signal_is_none


class SignalHandler(object):
    def __init__(self, signals=None):
        self.signals = signals

    @ignore_if_signal_is_none
    def start(self, unique_key, msg=None):
        if msg is None:
            self.signals.site_started[str].emit(unique_key)
        else:
            self.signals.site_started[str, str].emit(unique_key, msg)

    @ignore_if_signal_is_none
    def finished_successful(self, unique_key, msg=None):
        if msg is None:
            self.signals.site_finished_successful[str].emit(unique_key)
        else:
            self.signals.site_finished_successful[str, str].emit(unique_key, msg)

    @ignore_if_signal_is_none
    def quit_with_warning(self, unique_key, msg=None):
        if msg is None:
            self.signals.site_quit_with_warning[str].emit(unique_key)
        else:
            self.signals.site_quit_with_warning[str, str].emit(unique_key, msg)

    @ignore_if_signal_is_none
    def quit_with_error(self, unique_key, msg=None):
        if msg is None:
            self.signals.site_quit_with_error[str].emit(unique_key)
        else:
            self.signals.site_quit_with_error[str, str].emit(unique_key, msg)

    @ignore_if_signal_is_none
    def update_folder_name(self, unique_key, new_folder_name):
        self.signals.update_folder_name[str, str].emit(unique_key, new_folder_name)

    @ignore_if_signal_is_none
    def update_base_path(self, unique_key, new_base_path):
        self.signals.update_base_path[str, str].emit(unique_key, new_base_path)

    @ignore_if_signal_is_none
    def added_new_file(self, unique_key, path):
        self.signals.added_new_file[str, str].emit(unique_key, path)

    @ignore_if_signal_is_none
    def replaced_file(self, unique_key, path, old_path=None):
        if old_path is None:
            self.signals.replaced_file[str, str].emit(unique_key, path)
        else:
            self.signals.replaced_file[str, str, str].emit(unique_key, path, old_path)
