# -*- coding: utf-8 -*-
"""
Embedded gwflow configuration panel for the HRUs dialog.

Replaces the standalone gwflow dialog with an inline panel that shows
file inputs and grid creation controls directly in the HRUs tab.
"""

import os
import math
from qgis.PyQt.QtCore import QSettings, pyqtSignal
from qgis.PyQt.QtWidgets import QGroupBox, QFileDialog
from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer

#from .ui_gwflow_hru import Ui_GwflowHru
from .QSWATUtils import QSWATUtils, fileWriter, FileTypes, ListFuns  # type: ignore

class GwflowHru(QGroupBox, Ui_GwflowHru):
    """gwflow configuration panel embedded in the HRUs dialog."""

    validityChanged = pyqtSignal(bool)

    def __init__(self, gv, parent):
        super().__init__(parent)
        self._gv = gv
        self.setupUi(self)
        self._gridGen = None
        self._watershedArea = 0
        self._updateMinSizeLabel()
        self._connect()
        self.progressLabel = parent.progressLabel2

    def _connect(self):
        self.aquiferThicknessButton.clicked.connect(self._browseThickness)
        self.aquiferPermeabilityButton.clicked.connect(self._browsePermeability)
        self.tileDrainsButton.clicked.connect(self._browseTileDrains)
        self.useTileDrains.toggled.connect(self._toggleTile)
        self.structuredRadio.toggled.connect(self._toggleGridType)
        self.refineTopography.toggled.connect(self._toggleElevTolerance)
        self.transitionSlider.valueChanged.connect(
            lambda v: self.transitionSpin.setValue(v / 10.0))
        self.transitionSpin.valueChanged.connect(
            lambda v: self.transitionSlider.setValue(int(v * 10)))
        self.cellSize.valueChanged.connect(self._onCellSizeChanged)
        self.maxCellSize.valueChanged.connect(self._updateMinSizeLabel)
        self.refineLevels.valueChanged.connect(self._updateMinSizeLabel)
        self.generateGridButton.clicked.connect(self._requestGrid)
        self.aquiferThickness.textChanged.connect(self._checkValidity)
        self.aquiferPermeability.textChanged.connect(self._checkValidity)

    def _lastInputPath(self):
        return str(QSettings().value('/QSWATPlus/LastInputPath', ''))

    def _saveInputPath(self, filePath):
        QSettings().setValue('/QSWATPlus/LastInputPath', os.path.dirname(filePath))

    def _browseThickness(self):
        gwflowDir = QSWATUtils.join(self._gv.projDir, 'gwflowFiles')
        if not os.path.isdir(gwflowDir):
            os.makedirs(gwflowDir)
        # for this filetype the file will not be loaded or opened, but will be copied if nesessary to gwflowDir
        proj = QgsProject.instance()
        root = proj.layerTreeRoot()
        thicknessFile, _ = QSWATUtils.openAndLoadFile(root, FileTypes._AQUIFERTHICKNESS, self.aquiferThickness, gwflowDir, self._gv, None, "")
        if not thicknessFile:
            return 
        self.aquiferThickness.setText(thicknessFile)
        # check projection
        projEpsg = self._gv.crsProject.authid()
        layer = QgsRasterLayer(thicknessFile)
        epsg = layer.crs().authid()
        if not QSWATUtils.areSameProjection(projEpsg, epsg):
            QSWATUtils.information('''Thickness raster {0} has projection {1} different from the project's {2}.
            Do you need to reproject it?'''.format(thicknessFile, epsg, projEpsg), self._gv.isBatch)

    def _browsePermeability(self):
        f, _ = QFileDialog.getOpenFileName(
            self, 'Select aquifer permeability shapefile', self._lastInputPath(),
            FileTypes.filter(FileTypes._PERMEABILITY))
        if not (f and os.path.isfile(f)):
            return
        self._saveInputPath(f)
        gwflowDir = QSWATUtils.join(self._gv.projDir, 'gwflowFiles')
        if not os.path.isdir(gwflowDir):
            os.makedirs(gwflowDir)
        # this is a no-op if f is gwflowDir/permeability.shp
        QSWATUtils.copyShapefile(f, "permeability", gwflowDir);
        permFile = QSWATUtils.join(gwflowDir, "permeability.shp");    
        self.aquiferPermeability.setText(permFile)
        # check projection
        projEpsg = self._gv.crsProject.authid()
        layer = QgsVectorLayer(permFile, '', 'ogr')
        epsg = layer.crs().authid()
        if not QSWATUtils.areSameProjection(projEpsg, epsg):
            QSWATUtils.information('''Permeability shapefile {0} has projection {1} different from the project's {2}.
            Do you need to reproject it?'''.format(permFile, epsg, projEpsg), self._gv.isBatch)


    def _browseTileDrains(self):
        f, _ = QFileDialog.getOpenFileName(
            self, 'Select tile drains shapefile', self._lastInputPath(),
            FileTypes.filter(FileTypes._TILEDRAINS))
        if not (f and os.path.isfile(f)):
            return
        self._saveInputPath(f)
        gwflowDir = QSWATUtils.join(self._gv.projDir, 'gwflowFiles')
        if not os.path.isdir(gwflowDir):
            os.makedirs(gwflowDir)
        # this is a no-op if f is gwflowDir/permeability.shp
        QSWATUtils.copyShapefile(f, "tileDrains", gwflowDir);
        tileDrainsFile = QSWATUtils.join(gwflowDir, "tileDrains.shp"); 
        self.tileDrains.setText(tileDrainsFile)
        # check projection
        projEpsg = self._gv.crsProject.authid()
        layer = QgsVectorLayer(tileDrainsFile, '', 'ogr')
        epsg = layer.crs().authid()
        if not QSWATUtils.areSameProjection(projEpsg, epsg):
            QSWATUtils.information('''TileDrains shapefile {0} has projection {1} different from the project's {2}.
            Do you need to reproject it?'''.format(tileDrainsFile, epsg, projEpsg), self._gv.isBatch)

    def _toggleTile(self, on):
        self.tileDrains.setEnabled(on)
        self.tileDrainsButton.setEnabled(on)

    def _toggleGridType(self, structured):
        self.structuredWidget.setVisible(structured)
        self.unstructuredWidget.setVisible(not structured)

    def _toggleElevTolerance(self, on):
        self.elevTolLabel.setVisible(on)
        self.elevTolerance.setVisible(on)

    def _updateMinSizeLabel(self):
        maxSz = self.maxCellSize.value()
        levels = self.refineLevels.value()
        minSz = maxSz / (2 ** levels)
        self.minSizeLabel.setText('Min cell size: {0:.1f} m  (max / 2^{1})'.format(minSz, levels))

    def initGridGenerator(self, gv):
        """Set up background grid generation and auto-size cells for ~200 cells."""
        from .gwflowgrid import GridGenerator
        self._gridGen = GridGenerator(gv, self.progressLabel)
        extent = self._gridGen._getWatershedExtent()
        if extent is not None and not extent.isEmpty():
            areaM2 = extent.width() * extent.height()
            self._watershedArea = areaM2
            targetCells = 200
            idealSize = int(math.sqrt(areaM2 / targetCells))
            magnitude = 10 ** int(math.log10(max(idealSize, 1)))
            idealSize = max(magnitude, round(idealSize / magnitude) * magnitude)
            self.cellSize.setValue(idealSize)
            self.maxCellSize.setValue(idealSize * 3)
            self.updateCellEstimate(areaM2)
            self._updateMinSizeLabel()

    def _requestGrid(self):
        """Collect current parameters and request background grid generation."""
        if self._gridGen is None:
            return
        params = {
            'gridType': 'structured' if self.structuredRadio.isChecked() else 'unstructured',
            'cellSize': self.cellSize.value(),
            'maxSize': self.maxCellSize.value(),
            'levels': self.refineLevels.value(),
            'transitionRate': self.transitionSpin.value(),
            'refineStreams': self.refineStreams.isChecked(),
            'refineTopography': self.refineTopography.isChecked(),
            'refineBoundary': self.refineBoundary.isChecked(),
            'refineWells': self.refineWells.isChecked(),
            'elevTolerance': self.elevTolerance.value(),
            'alignToGrid': self.alignGrids.isChecked(),
        }
        self._gridGen.requestGeneration(params)

    def _onCellSizeChanged(self):
        if self._watershedArea > 0:
            self.updateCellEstimate(self._watershedArea)

    def updateCellEstimate(self, areaM2):
        size = self.cellSize.value()
        if size > 0:
            cells = int(areaM2 / (size * size))
            self.cellEstimateLabel.setText(
                '\u2248 {0:,} cells (based on watershed area)'.format(cells))

    def saveToProject(self, proj, attTitle):
        proj.writeEntry(attTitle, 'gwflow/aquiferThickness', proj.writePath(self.aquiferThickness.text()))
        proj.writeEntry(attTitle, 'gwflow/aquiferPermeability', proj.writePath(self.aquiferPermeability.text()))
        proj.writeEntry(attTitle, 'gwflow/tileDrains', proj.writePath(self.tileDrains.text()))
        proj.writeEntry(attTitle, 'gwflow/gridType', 'structured' if self.structuredRadio.isChecked() else 'unstructured')
        proj.writeEntryDouble(attTitle, 'gwflow/cellSize', float(self.cellSize.value()))
        proj.writeEntryDouble(attTitle, 'gwflow/maxSize', float(self.maxCellSize.value()))
        proj.writeEntryDouble(attTitle, 'gwflow/levels', float(self.refineLevels.value()))
        proj.writeEntryDouble(attTitle, 'gwflow/transitionRate', self.transitionSpin.value())
        proj.writeEntryBool(attTitle, 'gwflow/refineStreams', self.refineStreams.isChecked())
        proj.writeEntryBool(attTitle, 'gwflow/refineTopography', self.refineTopography.isChecked())
        proj.writeEntryBool(attTitle, 'gwflow/refineBoundary', self.refineBoundary.isChecked())
        proj.writeEntryBool(attTitle, 'gwflow/refineWells', self.refineWells.isChecked())
        proj.writeEntryBool(attTitle, 'gwflow/useTileDrains', self.useTileDrains.isChecked())
        proj.writeEntryBool(attTitle, 'gwflow/alignGrids', self.alignGrids.isChecked())
        proj.writeEntryDouble(attTitle, 'gwflow/elevTolerance', float(self.elevTolerance.value()))

    def loadFromProject(self, proj, attTitle):
        val, found = proj.readEntry(attTitle, 'gwflow/aquiferThickness', '')
        if found and val:
            self.aquiferThickness.setText(proj.readPath(val))
        val, found = proj.readEntry(attTitle, 'gwflow/aquiferPermeability', '')
        if found and val:
            self.aquiferPermeability.setText(proj.readPath(val))
        val, found = proj.readEntry(attTitle, 'gwflow/tileDrains', '')
        if found and val:
            self.tileDrains.setText(proj.readPath(val))
            self.useTileDrains.setChecked(True)
        val, found = proj.readEntry(attTitle, 'gwflow/gridType', '')
        if found and val == 'unstructured':
            self.unstructuredRadio.setChecked(True)
        val, found = proj.readDoubleEntry(attTitle, 'gwflow/cellSize', 0)
        if found and val > 0:
            self.cellSize.setValue(int(val))
        val, found = proj.readDoubleEntry(attTitle, 'gwflow/maxSize', 0)
        if found and val > 0:
            self.maxCellSize.setValue(int(val))
        val, found = proj.readDoubleEntry(attTitle, 'gwflow/levels', 0)
        if found and val > 0:
            self.refineLevels.setValue(int(val))
        val, found = proj.readDoubleEntry(attTitle, 'gwflow/transitionRate', 0)
        if found and val > 0:
            self.transitionSpin.setValue(val)
        val, found = proj.readBoolEntry(attTitle, 'gwflow/refineStreams', True)
        if found:
            self.refineStreams.setChecked(val)
        val, found = proj.readBoolEntry(attTitle, 'gwflow/refineTopography', True)
        if found:
            self.refineTopography.setChecked(val)
        val, found = proj.readBoolEntry(attTitle, 'gwflow/refineBoundary', True)
        if found:
            self.refineBoundary.setChecked(val)
        val, found = proj.readBoolEntry(attTitle, 'gwflow/refineWells', False)
        if found:
            self.refineWells.setChecked(val)
        val, found = proj.readBoolEntry(attTitle, 'gwflow/alignGrids', True)
        if found:
            self.alignGrids.setChecked(val)
        val, found = proj.readDoubleEntry(attTitle, 'gwflow/elevTolerance', 0)
        if found and val > 0:
            self.elevTolerance.setValue(int(val))
        self._updateMinSizeLabel()

    def isValid(self):
        t = self.aquiferThickness.text()
        p = self.aquiferPermeability.text()
        return bool(t) and os.path.isfile(t) and bool(p) and os.path.isfile(p)

    def _checkValidity(self):
        self.validityChanged.emit(self.isValid())

    def cleanup(self):
        if self._gridGen:
            self._gridGen.cleanup()
