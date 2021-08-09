# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'G:/Users/Public/QSWAT3/QSWAT3/QSWAT/ui_convert.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_qswatConvertChoice(object):
    def setupUi(self, qswatConvertChoice):
        qswatConvertChoice.setObjectName("qswatConvertChoice")
        qswatConvertChoice.setWindowModality(QtCore.Qt.ApplicationModal)
        qswatConvertChoice.resize(479, 222)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/plugins/QSWATPlus/SWATPlus32.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        qswatConvertChoice.setWindowIcon(icon)
        self.gridLayout = QtWidgets.QGridLayout(qswatConvertChoice)
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtWidgets.QLabel(qswatConvertChoice)
        self.label.setWordWrap(True)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 2)
        self.fullButton = QtWidgets.QRadioButton(qswatConvertChoice)
        self.fullButton.setChecked(True)
        self.fullButton.setObjectName("fullButton")
        self.gridLayout.addWidget(self.fullButton, 1, 0, 1, 1)
        self.noGISButton = QtWidgets.QRadioButton(qswatConvertChoice)
        self.noGISButton.setObjectName("noGISButton")
        self.gridLayout.addWidget(self.noGISButton, 1, 1, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(qswatConvertChoice)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 2, 0, 1, 2)

        self.retranslateUi(qswatConvertChoice)
        self.buttonBox.accepted.connect(qswatConvertChoice.accept)
        self.buttonBox.rejected.connect(qswatConvertChoice.reject)
        QtCore.QMetaObject.connectSlotsByName(qswatConvertChoice)

    def retranslateUi(self, qswatConvertChoice):
        _translate = QtCore.QCoreApplication.translate
        qswatConvertChoice.setWindowTitle(_translate("qswatConvertChoice", "Convert to QSWAT+ choice"))
        self.label.setText(_translate("qswatConvertChoice", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:8.25pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">There are two options available for converting a QSWAT project to QSWAT+.</p>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Choose <span style=\" font-weight:600;\">Full </span>if you want to create a QSWAT+ project from scratch using your DEM, landuse and soil maps, and other data, starting with watershed delineation. You will be able to set thresholds, define landscape units, a floodplain, and HRUs, as well as edit your inputs before running SWAT+.</p>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Choose <span style=\" font-weight:600;\">No GIS</span> if you want to run SWAT+ using your existing SWAT inputs. You will not be using GIS, will not be able to change your watershed, subbasins or HRUs, nor be able to create landscape units or a floodplain. You will be able to edit your inputs before running SWAT+.</p></body></html>"))
        self.fullButton.setText(_translate("qswatConvertChoice", "Full"))
        self.noGISButton.setText(_translate("qswatConvertChoice", "No GIS"))

import resources_rc
