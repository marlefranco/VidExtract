from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6 import uic
import os

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        # Load the UI from the .ui file
        ui_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mainwindow.ui")
        uic.loadUi(ui_file_path, MainWindow)

        # Make UI elements accessible through this instance
        self.selectFileButton = MainWindow.findChild(QtWidgets.QPushButton, "selectFileButton")
        self.filePathLabel = MainWindow.findChild(QtWidgets.QLabel, "filePathLabel")
        self.startTimeEdit = MainWindow.findChild(QtWidgets.QLineEdit, "startTimeEdit")
        self.endTimeEdit = MainWindow.findChild(QtWidgets.QLineEdit, "endTimeEdit")
        self.progressBar = MainWindow.findChild(QtWidgets.QProgressBar, "progressBar")
        self.statusLabel = MainWindow.findChild(QtWidgets.QLabel, "statusLabel")
        self.statusTextEdit = MainWindow.findChild(QtWidgets.QTextEdit, "statusTextEdit")
        self.extractButton = MainWindow.findChild(QtWidgets.QPushButton, "extractButton")
        self.actionOpen = MainWindow.findChild(QtGui.QAction, "actionOpen")
        self.actionExit = MainWindow.findChild(QtGui.QAction, "actionExit")
