"""
/***************************************************************************
 QSWAT
                                 A QGIS plugin
 Create SWAT inputs
                             -------------------
        begin                : 2014-07-18
        copyright            : (C) 2014 by Chris George
        email                : cgeorge@mcmaster.ca
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

try:
    from qgis.PyQt import QtWidgets
except:
    from PyQt5 import QtWidgets
 
from .ui_comparescenarios import Ui_compareScenarios
 
class compareDialog(QtWidgets.QDialog, Ui_compareScenarios):
    """Set up dialog from designer."""
    def __init__(self, parent=None):
        """Constructor."""
        super(compareDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)