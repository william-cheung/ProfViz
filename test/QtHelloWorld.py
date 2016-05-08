import sys
from PyQt4 import QtGui, QtCore, uic


app = QtGui.QApplication(sys.argv)
window = uic.loadUi("qt_hello_world.ui")


def onButtonOK():
    window.plainTextEdit.document().setPlainText('OK')


def onButtonCancel():
    window.plainTextEdit.document().setPlainText('Cancel')

window.connect(window.okButton, QtCore.SIGNAL('clicked()'), onButtonOK)
window.connect(window.cancelButton, QtCore.SIGNAL('clicked()'), onButtonCancel)


window.show()

sys.exit(app.exec_())
