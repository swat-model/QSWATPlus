# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qt5/Qt6 enum compatibility shim.
                                 
 Create SWATPlus inputs
                              -------------------
        begin                : 2026-03-12
        copyright            : (C) 2026 by Celray James Chawanda
        email                : celray.chawanda@outlook.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   PyQt6 (QGIS 4.0+) requires fully-qualified enum names                 *
 *   (e.g. Qt.AlignmentFlag.AlignLeft) while PyQt5 (QGIS 3.x) uses short   *
 *   names (e.g. Qt.AlignLeft). This module exports values that work with  *
 *   both.                                                                 *
 *                                                                         *
 *   Usage:                                                                *
 *     from .qt_compat import WaitCursor, ArrowCursor, MsgBoxYes, ...      *
 *                                                                         *
 ***************************************************************************/
"""

from qgis.PyQt.QtCore import Qt, QIODevice, QMetaType, QEventLoop
from qgis.PyQt.QtGui import QTextCursor, QIcon
from qgis.PyQt.QtWidgets import (QMessageBox, QAbstractItemView, QSizePolicy,
                                  QComboBox, QDialogButtonBox, QFrame, QSlider,
                                  QDialog)


def _e(cls, short, qualified):
    """Try Qt5 short name, fall back to Qt6 fully-qualified path."""
    val = getattr(cls, short, None)
    if val is not None:
        return val
    obj = cls
    for part in qualified.split('.'):
        obj = getattr(obj, part)
    return obj


def fv(val, default=0):
    """Return *val* unchanged when it is a real value, or *default* when NULL.

    In QGIS 3.x feature[index] returns QPyNullVariant for NULL fields,
    which compares safely with ints/floats.  In QGIS 4.0 it returns
    Python ``None``, so ``None <= 0`` raises ``TypeError``.

    Wrap any feature-attribute read that is later used in arithmetic or
    comparisons::

        SWATBasin = fv(polygon[subbasinIndex])
        if SWATBasin <= 0: ...          # safe on both 3.x and 4.0
    """
    return default if val is None else val


def compile_pyx(pyx_name):
    """Compile a .pyx Cython extension for the running Python version.

    Call this when an ``ImportError`` indicates that a compiled ``.so``
    (or ``.pyd``) is missing or was built for a different Python.  The
    ``.pyx`` source must sit in the same directory as this file.

    Requires ``Cython``, ``setuptools``, ``numpy``, and a C compiler.
    """
    import os, sys, subprocess
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    pyx_file = pyx_name + '.pyx'
    if not os.path.exists(os.path.join(pkg_dir, pyx_file)):
        raise ImportError('{0} not found in {1}'.format(pyx_file, pkg_dir))
    subprocess.check_call([
        sys.executable, '-c',
        'import numpy; '
        'from setuptools import setup, Extension; '
        'from Cython.Build import cythonize; '
        'ext = Extension("{name}", ["{src}"], '
        'include_dirs=[numpy.get_include()]); '
        'setup(ext_modules=cythonize([ext]), '
        'script_args=["build_ext", "--inplace"])'
        .format(name=pyx_name, src=pyx_file)
    ], cwd=pkg_dir)


# Qt.CursorShape
WaitCursor = _e(Qt, 'WaitCursor', 'CursorShape.WaitCursor')
ArrowCursor = _e(Qt, 'ArrowCursor', 'CursorShape.ArrowCursor')

# Qt.AlignmentFlag
AlignCenter = _e(Qt, 'AlignCenter', 'AlignmentFlag.AlignCenter')
AlignHCenter = _e(Qt, 'AlignHCenter', 'AlignmentFlag.AlignHCenter')

# Qt.MatchFlag
MatchExactly = _e(Qt, 'MatchExactly', 'MatchFlag.MatchExactly')

# Qt.SortOrder
AscendingOrder = _e(Qt, 'AscendingOrder', 'SortOrder.AscendingOrder')

# Qt.WindowType
WindowContextHelpButtonHint = _e(Qt, 'WindowContextHelpButtonHint', 'WindowType.WindowContextHelpButtonHint')
WindowMinimizeButtonHint = _e(Qt, 'WindowMinimizeButtonHint', 'WindowType.WindowMinimizeButtonHint')
MSWindowsFixedSizeDialogHint = _e(Qt, 'MSWindowsFixedSizeDialogHint', 'WindowType.MSWindowsFixedSizeDialogHint')

# Qt.WindowModality
NonModal = _e(Qt, 'NonModal', 'WindowModality.NonModal')

# Qt.Key
Key_Left = _e(Qt, 'Key_Left', 'Key.Key_Left')
Key_Right = _e(Qt, 'Key_Right', 'Key.Key_Right')

# QMessageBox.StandardButton
MsgBoxYes = _e(QMessageBox, 'Yes', 'StandardButton.Yes')
MsgBoxNo = _e(QMessageBox, 'No', 'StandardButton.No')
MsgBoxCancel = _e(QMessageBox, 'Cancel', 'StandardButton.Cancel')
MsgBoxOk = _e(QMessageBox, 'Ok', 'StandardButton.Ok')
MsgBoxSave = _e(QMessageBox, 'Save', 'StandardButton.Save')

# QMessageBox.Icon
MsgBoxCritical = _e(QMessageBox, 'Critical', 'Icon.Critical')
MsgBoxQuestion = _e(QMessageBox, 'Question', 'Icon.Question')
MsgBoxInformation = _e(QMessageBox, 'Information', 'Icon.Information')
MsgBoxWarning = _e(QMessageBox, 'Warning', 'Icon.Warning')

# QTextCursor.MoveOperation
TextCursorEnd = _e(QTextCursor, 'End', 'MoveOperation.End')

# QIODevice.OpenModeFlag
IOReadOnly = _e(QIODevice, 'ReadOnly', 'OpenModeFlag.ReadOnly')
IOReadWrite = _e(QIODevice, 'ReadWrite', 'OpenModeFlag.ReadWrite')

# QAbstractItemView.SelectionBehavior
SelectRows = _e(QAbstractItemView, 'SelectRows', 'SelectionBehavior.SelectRows')

# QAbstractItemView.SelectionMode
SingleSelection = _e(QAbstractItemView, 'SingleSelection', 'SelectionMode.SingleSelection')

# QMetaType.Type
MetaTypeInt = _e(QMetaType, 'Int', 'Type.Int')
MetaTypeDouble = _e(QMetaType, 'Double', 'Type.Double')
MetaTypeQString = _e(QMetaType, 'QString', 'Type.QString')
MetaTypeLongLong = _e(QMetaType, 'LongLong', 'Type.LongLong')

# ---------------------------------------------------------------------------
# Patch Qt5-style short names onto classes used in auto-generated ui_*.py
# files so they work unchanged on both Qt5 and Qt6.
# ---------------------------------------------------------------------------
if not hasattr(QIcon, 'Normal'):
    QIcon.Normal = QIcon.Mode.Normal
    QIcon.Active = QIcon.Mode.Active
    QIcon.Disabled = QIcon.Mode.Disabled
    QIcon.Selected = QIcon.Mode.Selected
if not hasattr(QIcon, 'Off'):
    QIcon.Off = QIcon.State.Off
    QIcon.On = QIcon.State.On

if not hasattr(Qt, 'Horizontal'):
    Qt.Horizontal = Qt.Orientation.Horizontal
    Qt.Vertical = Qt.Orientation.Vertical

if not hasattr(Qt, 'AlignLeft'):
    Qt.AlignLeft = Qt.AlignmentFlag.AlignLeft
    Qt.AlignRight = Qt.AlignmentFlag.AlignRight
    Qt.AlignHCenter = Qt.AlignmentFlag.AlignHCenter
    Qt.AlignVCenter = Qt.AlignmentFlag.AlignVCenter
    Qt.AlignCenter = Qt.AlignmentFlag.AlignCenter
    Qt.AlignTop = Qt.AlignmentFlag.AlignTop
    Qt.AlignBottom = Qt.AlignmentFlag.AlignBottom
    Qt.AlignLeading = Qt.AlignmentFlag.AlignLeading
    Qt.AlignTrailing = Qt.AlignmentFlag.AlignTrailing

if not hasattr(Qt, 'WindowContextHelpButtonHint'):
    Qt.WindowContextHelpButtonHint = Qt.WindowType.WindowContextHelpButtonHint
    Qt.WindowMinimizeButtonHint = Qt.WindowType.WindowMinimizeButtonHint
    Qt.MSWindowsFixedSizeDialogHint = Qt.WindowType.MSWindowsFixedSizeDialogHint
if not hasattr(Qt, 'NonModal'):
    Qt.NonModal = Qt.WindowModality.NonModal
if not hasattr(Qt, 'ApplicationModal'):
    Qt.ApplicationModal = Qt.WindowModality.ApplicationModal
if not hasattr(Qt, 'Key_Left'):
    Qt.Key_Left = Qt.Key.Key_Left
    Qt.Key_Right = Qt.Key.Key_Right
if not hasattr(Qt, 'AutoText'):
    Qt.AutoText = Qt.TextFormat.AutoText
if not hasattr(Qt, 'LeftToRight'):
    Qt.LeftToRight = Qt.LayoutDirection.LeftToRight
if not hasattr(Qt, 'ScrollBarAlwaysOff'):
    Qt.ScrollBarAlwaysOff = Qt.ScrollBarPolicy.ScrollBarAlwaysOff
if not hasattr(Qt, 'WheelFocus'):
    Qt.WheelFocus = Qt.FocusPolicy.WheelFocus
if not hasattr(Qt, 'ImhNone'):
    Qt.ImhNone = Qt.InputMethodHint.ImhNone
    Qt.ImhDigitsOnly = Qt.InputMethodHint.ImhDigitsOnly
    Qt.ImhFormattedNumbersOnly = Qt.InputMethodHint.ImhFormattedNumbersOnly
    Qt.ImhPreferNumbers = Qt.InputMethodHint.ImhPreferNumbers

if not hasattr(QAbstractItemView, 'SingleSelection'):
    QAbstractItemView.SingleSelection = QAbstractItemView.SelectionMode.SingleSelection
if not hasattr(QAbstractItemView, 'NoEditTriggers'):
    QAbstractItemView.NoEditTriggers = QAbstractItemView.EditTrigger.NoEditTriggers

if not hasattr(QSizePolicy, 'Expanding'):
    QSizePolicy.Expanding = QSizePolicy.Policy.Expanding
    QSizePolicy.Fixed = QSizePolicy.Policy.Fixed
    QSizePolicy.Maximum = QSizePolicy.Policy.Maximum
    QSizePolicy.Minimum = QSizePolicy.Policy.Minimum
    QSizePolicy.MinimumExpanding = QSizePolicy.Policy.MinimumExpanding
    QSizePolicy.Preferred = QSizePolicy.Policy.Preferred

if not hasattr(QComboBox, 'InsertAlphabetically'):
    QComboBox.InsertAlphabetically = QComboBox.InsertPolicy.InsertAlphabetically

if not hasattr(QDialogButtonBox, 'Ok'):
    QDialogButtonBox.Ok = QDialogButtonBox.StandardButton.Ok
    QDialogButtonBox.Cancel = QDialogButtonBox.StandardButton.Cancel

if not hasattr(QFrame, 'StyledPanel'):
    QFrame.StyledPanel = QFrame.Shape.StyledPanel
    QFrame.Raised = QFrame.Shadow.Raised

if not hasattr(QSlider, 'TicksAbove'):
    QSlider.TicksAbove = QSlider.TickPosition.TicksAbove
    QSlider.TicksBelow = QSlider.TickPosition.TicksBelow

if not hasattr(QEventLoop, 'ExcludeUserInputEvents'):
    QEventLoop.ExcludeUserInputEvents = QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents

if not hasattr(QDialog, 'Rejected'):
    QDialog.Rejected = QDialog.DialogCode.Rejected
    QDialog.Accepted = QDialog.DialogCode.Accepted
