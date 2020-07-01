import logging.config
import sys
from multiprocessing import freeze_support
import encodings.idna  # This import is important, else aiohttp won't be able to work probably

freeze_support()

import colorama
from PyQt5.QtWidgets import QApplication

import gui.main_window
from core.constants import IS_FROZEN
from settings.logger import LOGGER_CONFIG
from settings import global_settings

colorama.init()

logging.config.dictConfig(LOGGER_CONFIG)
logger = logging.getLogger(__name__)


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == "__main__":
    if not IS_FROZEN and global_settings.loglevel == "DEBUG":
        sys.excepthook = except_hook

    app = QApplication([])

    main_window = gui.main_window.MainWindow()

    sys.exit(app.exec_())
