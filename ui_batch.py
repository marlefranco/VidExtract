from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6 import uic
import os

class Ui_BatchExtractWindow(object):
    def setupUi(self, BatchExtractWindow):
        # Load the UI from the .ui file
        ui_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "batchextract.ui")
        uic.loadUi(ui_file_path, BatchExtractWindow)

        # Make UI elements accessible through this instance
        self.select_file_button = BatchExtractWindow.findChild(QtWidgets.QPushButton, "select_file_button")
        self.file_path_label = BatchExtractWindow.findChild(QtWidgets.QLabel, "file_path_label")
        self.select_dir_button = BatchExtractWindow.findChild(QtWidgets.QPushButton, "select_dir_button")
        self.dir_path_label = BatchExtractWindow.findChild(QtWidgets.QLabel, "dir_path_label")
        self.progress_bar = BatchExtractWindow.findChild(QtWidgets.QProgressBar, "progress_bar")
        self.status_label = BatchExtractWindow.findChild(QtWidgets.QLabel, "status_label")
        self.status_text = BatchExtractWindow.findChild(QtWidgets.QTextEdit, "status_text")
        self.extract_button = BatchExtractWindow.findChild(QtWidgets.QPushButton, "extract_button")
        self.close_button = BatchExtractWindow.findChild(QtWidgets.QPushButton, "close_button")
