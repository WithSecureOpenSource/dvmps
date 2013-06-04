"""
Copyright (c) 2012-2013 F-Secure
See LICENSE for details
"""

from PySide.QtCore import QObject, QFile
#from PySide.QtGui import *
from PySide.QtUiTools import QUiLoader

def loadDialog(file_name):
        loader = QUiLoader()
        the_file = QFile(file_name)
        the_file.open(QFile.ReadOnly)
        ret_val = loader.load(the_file)
        the_file.close()
        return ret_val

class ProgressDialog(QObject):
    def __init__(self):
        QObject.__init__(self)
        self._dialog = loadDialog(r'dialog2.ui')

    def reportProgress(self, text):
        self._dialog.label.setText(text)

    def show(self, cancellable=False):
        self._dialog.pb_cancel.setVisible(cancellable)
        self._dialog.setResult(2)
        self._dialog.show()

    def exec_(self):
        self._dialog.exec_()

    def getResult(self):
        #2 if nothing yet, 0 if cancelled
        return self._dialog.result()

    def close(self):
        self._dialog.accept()
