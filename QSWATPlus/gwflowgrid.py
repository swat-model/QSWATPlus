# -*- coding: utf-8 -*-
"""
Background grid generation for gwflow.

Generates structured or unstructured (balanced quadtree) grids clipped
to the watershed + lake boundary and saved as a shapefile.

Unstructured algorithm adapted from process.py: uses cKDTree for fast
distance queries, levels-based refinement (min = max / 2^levels), and
2:1 balancing so adjacent cells differ by at most one refinement level.
"""

import math
import os
import traceback
import numpy as np
from qgis.core import (
    QgsTask, QgsApplication, QgsVectorLayer, QgsFeature, QgsGeometry,
    QgsProject, QgsRectangle, QgsPointXY, QgsWkbTypes,
    QgsFields, QgsField, QgsVectorFileWriter, QgsCoordinateTransformContext,
    QgsMessageLog, Qgis
)
from qgis.PyQt.QtCore import QVariant, QTimer

from .QSWATTopology import QSWATTopology
from .QSWATUtils import QSWATUtils

_LAYER_NAME = 'GWFlow Cells'
_LAYER_ID = 'gwflowcells'
_SUBBASINS_NAME = 'Subbasins'
_LOG_TAG = 'gwflow grid'


def _log(msg, level=Qgis.MessageLevel.Info):
    QgsMessageLog.logMessage(str(msg), _LOG_TAG, level)


class GridGenerator:
    """Manages background grid generation and layer updates."""

    def __init__(self, gv, progressLabel):
        self._gv = gv
        self._task = None
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(600)
        self._timer.timeout.connect(self._startGeneration)
        self._params = {}
        self.progressLabel = progressLabel

    def requestGeneration(self, params):
        self._params = dict(params)
        self._timer.start()

    def _startGeneration(self):
        try:
            if self._task is not None and self._task.status() == QgsTask.Running:
                self._task.cancel()
        except RuntimeError:
            pass
        self._task = None

        wsGeom, extent = self._getWatershedGeometry()
        if extent is None or extent.isEmpty():
            _log('No watershed geometry found (checked wshedFile/subbasinsFile/basinFile and "Subbasins" map layer). Aborting.',
                 Qgis.MessageLevel.Warning)
            return

        crs = self._gv.crsProject
        outPath = os.path.normpath(os.path.join(self._gv.shapesDir, 'gwflowcells.shp'))
        _log('Starting grid generation: type={0} extent={1} out={2}'.format(
            self._params.get('gridType'), extent.toString(), outPath))
        QSWATUtils.progress('Starting grid generation', self.progressLabel)
        # Drop any map layer pointing at this shapefile so Windows releases the file lock
        # before the background task tries to overwrite it.
        self._releaseLayerLocks(outPath)

        # Collect refinement points for unstructured grids
        refineCoords = []
        if self._params.get('gridType') == 'unstructured':
            if self._params.get('refineStreams'):
                refineCoords.extend(self._getStreamCoords())
            if self._params.get('refineBoundary') and wsGeom is not None:
                refineCoords.extend(self._getBoundaryCoords(wsGeom))
            if self._params.get('refineWells'):
                refineCoords.extend(self._getWellCoords())

        demFile = ''
        if self._params.get('refineTopography') and self._params.get('gridType') == 'unstructured':
            demFile = getattr(self._gv, 'demFile', '')

        from qgis.PyQt.QtCore import QSettings
        numProcesses = int(QSettings().value('/QSWATPlus/NumProcesses', 8))

        task = _GridTask(extent, wsGeom, crs, self._params, refineCoords, demFile, outPath, numProcesses)
        task.taskCompleted.connect(lambda: self._onComplete(outPath))
        task.taskTerminated.connect(lambda: _log(
            'Grid task terminated (returned False or exception). See earlier log entries for the cause.',
            Qgis.MessageLevel.Critical))
        self._task = task
        QgsApplication.taskManager().addTask(task)

    def _getWatershedExtent(self):
        _, extent = self._getWatershedGeometry()
        return extent

    def _getWatershedGeometry(self):
        """Get the combined watershed + lakes geometry and extent."""
        combined = None
        extent = None
        for attr in ('wshedFile', 'subbasinsFile', 'basinFile'):
            f = getattr(self._gv, attr, '')
            if f and os.path.isfile(f):
                layer = QgsVectorLayer(f, 'tmp', 'ogr')
                if layer.isValid() and layer.featureCount() > 0:
                    for feat in layer.getFeatures():
                        g = feat.geometry()
                        if g and not g.isEmpty():
                            combined = g if combined is None else combined.combine(g)
                    extent = layer.extent()
                    break
        if combined is None:
            for layer in QgsProject.instance().mapLayersByName(_SUBBASINS_NAME):
                for feat in layer.getFeatures():
                    g = feat.geometry()
                    if g and not g.isEmpty():
                        combined = g if combined is None else combined.combine(g)
                extent = layer.extent()
                break
        if combined is None:
            return None, None
        lakeFile = getattr(self._gv, 'lakeFile', '')
        if lakeFile and os.path.isfile(lakeFile):
            lakeLayer = QgsVectorLayer(lakeFile, 'tmp', 'ogr')
            if lakeLayer.isValid():
                for feat in lakeLayer.getFeatures():
                    g = feat.geometry()
                    if g and not g.isEmpty():
                        combined = combined.combine(g)
        return combined, extent

    def _getStreamCoords(self):
        """Get stream vertex coordinates as numpy array for cKDTree."""
        channelFile = getattr(self._gv, 'channelFile', '')
        if not channelFile or not os.path.isfile(channelFile):
            return []
        layer = QgsVectorLayer(channelFile, 'tmp', 'ogr')
        if not layer.isValid():
            return []
        coords = []
        for feat in layer.getFeatures():
            geom = feat.geometry()
            if geom and not geom.isEmpty():
                for v in geom.vertices():
                    coords.append([v.x(), v.y()])
        return coords

    @staticmethod
    def _getBoundaryCoords(wsGeom):
        """Extract vertices from the outer boundary only, not internal subbasin edges."""
        coords = []
        # Get the convex hull boundary or dissolved exterior
        # coerce to a single polygon to get just the outer ring
        try:
            outer = wsGeom.combine(wsGeom)  # dissolve internal boundaries
            for part in outer.parts():
                # Only take the exterior ring (first ring of each polygon part)
                ring = part.exteriorRing()
                if ring is not None:
                    for i in range(ring.numPoints()):
                        pt = ring.pointN(i)
                        coords.append([pt.x(), pt.y()])
        except Exception:
            # Fallback: use all vertices
            for v in wsGeom.vertices():
                coords.append([v.x(), v.y()])
        return coords

    def _getWellCoords(self):
        """Get observation well locations from the outlets layer."""
        # Wells are deliberately excluded from the snap file, so read the source outlets file.
        outletFile = getattr(self._gv, 'outletFile', '')
        if not outletFile or not os.path.isfile(outletFile):
            return []
        layer = QgsVectorLayer(outletFile, 'tmp', 'ogr')
        if not layer.isValid():
            return []
        resIdx = layer.fields().indexOf(QSWATTopology._RES)
        inletIdx = layer.fields().indexOf(QSWATTopology._INLET)
        ptsourceIdx = layer.fields().indexOf(QSWATTopology._PTSOURCE)
        if resIdx < 0 or inletIdx < 0 or ptsourceIdx < 0:
            return []
        coords = []
        for feat in layer.getFeatures():
            if (feat[inletIdx] == 0
                    and feat[resIdx] == QSWATTopology._WELLTYPE
                    and feat[ptsourceIdx] == 0):
                geom = feat.geometry()
                if geom and not geom.isEmpty():
                    pt = geom.asPoint()
                    coords.append([pt.x(), pt.y()])
        return coords

    @staticmethod
    def _releaseLayerLocks(outPath):
        """Remove map layers whose source is outPath. On Windows the OGR provider
        holds an exclusive file lock that blocks rewriting until the layer is gone."""
        project = QgsProject.instance()
        targetNorm = os.path.normcase(os.path.normpath(outPath))
        toRemove = []
        for layer in project.mapLayers().values():
            try:
                src = layer.dataProvider().dataSourceUri()
            except Exception:
                continue
            # Strip the optional "|layername=..." suffix that OGR appends
            srcPath = src.split('|', 1)[0]
            if os.path.normcase(os.path.normpath(srcPath)) == targetNorm:
                toRemove.append(layer.id())
        for lid in toRemove:
            project.removeMapLayer(lid)
        if toRemove:
            _log('Released {0} layer(s) holding {1}'.format(len(toRemove), outPath))

    def _onComplete(self, shapePath):
        if not os.path.isfile(shapePath):
            return
        project = QgsProject.instance()
        for layer in project.mapLayersByName(_LAYER_NAME):
            project.removeMapLayer(layer.id())
        newLayer = QgsVectorLayer(shapePath, _LAYER_NAME, 'ogr')
        if newLayer.isValid():
            newLayer.setCustomProperty('layerId', _LAYER_ID)
            # Apply style
            qmlPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gwflowcells.qml')
            if os.path.isfile(qmlPath):
                newLayer.loadNamedStyle(qmlPath)
            project.addMapLayer(newLayer)
            GridGenerator.setGwflowMode(True)
            QSWATUtils.progress('Completed grid generation', self.progressLabel)

    @staticmethod
    def setGwflowMode(active):
        root = QgsProject.instance().layerTreeRoot()
        for treeLayer in root.findLayers():
            layer = treeLayer.layer()
            if layer is None:
                continue
            name = layer.name()
            if name.startswith(_SUBBASINS_NAME):
                treeLayer.setItemVisibilityChecked(not active)
            elif name == _LAYER_NAME:
                treeLayer.setItemVisibilityChecked(active)

    @staticmethod
    def removeGwflowLayer():
        project = QgsProject.instance()
        root = project.layerTreeRoot()
        for layer in project.mapLayersByName(_LAYER_NAME):
            project.removeMapLayer(layer.id())
        for treeLayer in root.findLayers():
            layer = treeLayer.layer()
            if layer and layer.name().startswith(_SUBBASINS_NAME):
                treeLayer.setItemVisibilityChecked(True)

    def cleanup(self):
        self._timer.stop()
        try:
            if self._task and self._task.status() == QgsTask.Running:
                self._task.cancel()
        except RuntimeError:
            pass


class _GridTask(QgsTask):
    """Background task that builds grid cells clipped to the watershed."""

    def __init__(self, extent, wsGeom, crs, params, refineCoords, demFile, outPath, numProcesses=8):
        super().__init__('Generating gwflow grid', QgsTask.CanCancel)
        self.extent = extent
        self.wsGeom = wsGeom
        self.crs = crs
        self.params = params
        self.refineCoords = refineCoords
        self.demFile = demFile
        self.outPath = outPath
        self.numProcesses = numProcesses
        self.resultFeatures = []

    def run(self):
        try:
            if self.params.get('gridType') == 'structured':
                ok = self._buildStructured()
            else:
                ok = self._buildUnstructured()
            _log('Build phase complete: ok={0} features={1}'.format(ok, len(self.resultFeatures)))
            if ok and self.resultFeatures:
                wrote = self._writeShapefile()
                _log('Write phase: success={0}'.format(wrote))
                return wrote
            if ok and not self.resultFeatures:
                _log('Build returned True but produced 0 features, nothing to write.',
                     Qgis.MessageLevel.Warning)
            return ok
        except Exception as exc:
            _log('Exception in grid task: {0}\n{1}'.format(exc, traceback.format_exc()),
                 Qgis.MessageLevel.Critical)
            return False

    def _buildStructured(self):
        cellSize = self.params.get('cellSize', 200)
        if cellSize <= 0:
            return False

        minX = self.extent.xMinimum()
        minY = self.extent.yMinimum()
        maxX = self.extent.xMaximum()
        maxY = self.extent.yMaximum()

        cols = math.ceil((maxX - minX) / cellSize)
        rows = math.ceil((maxY - minY) / cellSize)
        wsBbox = self.wsGeom.boundingBox() if self.wsGeom else None

        cellId = 1
        for row in range(rows):
            if self.isCanceled():
                return False
            for col in range(cols):
                x0 = minX + col * cellSize
                y0 = minY + row * cellSize
                x1 = x0 + cellSize
                y1 = y0 + cellSize
                cellRect = QgsRectangle(x0, y0, x1, y1)
                if self.wsGeom and not cellRect.intersects(wsBbox):
                    continue
                cellGeom = QgsGeometry.fromRect(cellRect)
                if self.wsGeom and not cellGeom.intersects(self.wsGeom):
                    continue
                feat = QgsFeature()
                feat.setGeometry(cellGeom)
                feat.setAttributes([cellId, cellSize * cellSize])
                cellId += 1
                self.resultFeatures.append(feat)
        return True

    def _buildUnstructured(self):
        """Balanced quadtree grid using cKDTree distance queries, DEM variance, and 2:1 balancing."""
        from scipy.spatial import cKDTree
        from osgeo import gdal

        maxSize = self.params.get('maxSize', 500)
        levels = self.params.get('levels', 4)
        rate = self.params.get('transitionRate', 1.0)

        if maxSize <= 0 or levels < 1:
            return False

        minSize = maxSize / (2 ** levels)

        minX = self.extent.xMinimum()
        minY = self.extent.yMinimum()
        maxX = self.extent.xMaximum()
        maxY = self.extent.yMaximum()

        # Build KDTree from refinement points (streams + boundary)
        refineTree = None
        if self.refineCoords:
            refineTree = cKDTree(np.array(self.refineCoords))

        # Open DEM for topographic refinement
        demDs = None
        demBand = None
        demTransform = None
        if self.demFile and os.path.isfile(self.demFile):
            demDs = gdal.Open(self.demFile, gdal.GA_ReadOnly)
            if demDs is not None:
                demBand = demDs.GetRasterBand(1)
                demTransform = demDs.GetGeoTransform()

        # Phase 1: quadtree refinement
        x0 = np.floor(minX / maxSize) * maxSize
        y0 = np.floor(minY / maxSize) * maxSize
        xs = np.arange(x0, maxX + maxSize, maxSize)
        ys = np.arange(y0, maxY + maxSize, maxSize)

        queue = [(x, y, maxSize) for y in ys[:-1] for x in xs[:-1]]
        cellDict = {}
        wsBbox = self.wsGeom.boundingBox() if self.wsGeom else None

        while queue:
            if self.isCanceled():
                demDs = None
                return False
            cx, cy, sz = queue.pop()
            cellRect = QgsRectangle(cx, cy, cx + sz, cy + sz)
            if self.wsGeom:
                if not cellRect.intersects(wsBbox):
                    continue
                cellGeom = QgsGeometry.fromRect(cellRect)
                if not cellGeom.intersects(self.wsGeom):
                    continue

            half = sz / 2
            shouldRefine = False

            # Distance-based refinement (streams, boundary, wells)
            if refineTree is not None and half >= minSize:
                cxMid = cx + half
                cyMid = cy + half
                dCentroid, _ = refineTree.query([cxMid, cyMid])
                d = max(0.0, dCentroid - sz * np.sqrt(2) / 2)
                t = 1.0 - np.exp(-rate * d / maxSize)
                target = minSize + (maxSize - minSize) * t
                if half >= target:
                    shouldRefine = True

            # DEM-based refinement: subdivide where terrain is variable
            if not shouldRefine and demBand is not None and half >= minSize:
                elevRange = self._demElevRange(
                    demBand, demTransform, cx, cy, sz)
                elevTol = self.params.get('elevTolerance', 10)
                if elevRange is not None and elevRange > elevTol:
                    shouldRefine = True

            if shouldRefine and half >= minSize:
                    queue.extend([
                        (cx,        cy,        half),
                        (cx + half, cy,        half),
                        (cx,        cy + half, half),
                        (cx + half, cy + half, half),
                    ])
                    continue
            cellDict[(cx, cy, sz)] = True

        demDs = None  # close DEM after Phase 1

        # Phase 2: 2:1 balancing
        eps = minSize * 0.1

        def findCellAt(px, py):
            sz = minSize
            while sz <= maxSize:
                cx = np.floor(px / sz) * sz
                cy = np.floor(py / sz) * sz
                if (cx, cy, sz) in cellDict:
                    return (cx, cy, sz)
                sz *= 2
            return None

        changed = True
        while changed:
            if self.isCanceled():
                return False
            changed = False
            toSplit = []
            for (cx, cy, sz) in list(cellDict.keys()):
                half = sz / 2
                if half < minSize:
                    continue
                mid = sz / 2
                probes = [
                    (cx + mid, cy - eps),
                    (cx + mid, cy + sz + eps),
                    (cx - eps, cy + mid),
                    (cx + sz + eps, cy + mid),
                ]
                for px, py in probes:
                    nb = findCellAt(px, py)
                    if nb is not None and sz > 2 * nb[2]:
                        toSplit.append((cx, cy, sz))
                        break

            for (cx, cy, sz) in toSplit:
                if (cx, cy, sz) not in cellDict:
                    continue
                half = sz / 2
                if half < minSize:
                    continue
                del cellDict[(cx, cy, sz)]
                for dx, dy in [(0, 0), (half, 0), (0, half), (half, half)]:
                    childRect = QgsRectangle(cx + dx, cy + dy, cx + dx + half, cy + dy + half)
                    if self.wsGeom and not QgsGeometry.fromRect(childRect).intersects(self.wsGeom):
                        continue
                    cellDict[(cx + dx, cy + dy, half)] = True
                changed = True

        # Build features: keep full cells if they touch the watershed
        cellId = 1
        for (cx, cy, sz) in cellDict:
            if self.isCanceled():
                return False
            cellGeom = QgsGeometry.fromRect(QgsRectangle(cx, cy, cx + sz, cy + sz))
            feat = QgsFeature()
            feat.setGeometry(cellGeom)
            feat.setAttributes([cellId, sz * sz])
            cellId += 1
            self.resultFeatures.append(feat)
        return True

    @staticmethod
    def _demElevRange(band, transform, cx, cy, sz):
        """Sample DEM at cell corners and center, return elevation range or None."""
        originX, pixelW, _, originY, _, pixelH = transform
        cols = band.XSize
        rows = band.YSize
        points = [
            (cx, cy), (cx + sz, cy), (cx, cy + sz), (cx + sz, cy + sz),
            (cx + sz / 2, cy + sz / 2),
        ]
        elevs = []
        for px, py in points:
            col = int((px - originX) / pixelW)
            row = int((py - originY) / pixelH)
            if 0 <= col < cols and 0 <= row < rows:
                try:
                    val = band.ReadAsArray(col, row, 1, 1)
                    if val is not None:
                        e = float(val[0, 0])
                        if e > -9999:
                            elevs.append(e)
                except Exception:
                    pass
        if len(elevs) >= 2:
            return max(elevs) - min(elevs)
        return None

    def _writeShapefile(self):
        # Remove any leftover shapefile sidecars so the driver can recreate cleanly.
        base, _ = os.path.splitext(self.outPath)
        for ext in ('.shp', '.shx', '.dbf', '.prj', '.cpg', '.qix', '.qmd'):
            try:
                os.remove(base + ext)
            except FileNotFoundError:
                pass
            except OSError as exc:
                _log('Could not remove {0}: {1}'.format(base + ext, exc),
                     Qgis.MessageLevel.Warning)

        fields = QgsFields()
        fields.append(QgsField('cell_id', QVariant.Int))
        fields.append(QgsField('cell_area', QVariant.Double))
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = 'ESRI Shapefile'
        options.fileEncoding = 'UTF-8'
        writer = QgsVectorFileWriter.create(
            self.outPath, fields, QgsWkbTypes.Polygon,
            self.crs, QgsCoordinateTransformContext(), options)
        if writer.hasError() != QgsVectorFileWriter.NoError:
            _log('Writer creation failed for {0}: {1}'.format(self.outPath, writer.errorMessage()),
                 Qgis.MessageLevel.Critical)
            return False
        for feat in self.resultFeatures:
            f = QgsFeature(fields)
            f.setGeometry(feat.geometry())
            f.setAttributes(feat.attributes())
            writer.addFeature(f)
        del writer
        return True

    def finished(self, result):
        pass
