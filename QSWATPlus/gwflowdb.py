# -*- coding: utf-8 -*-
"""
Database table creation and population for the gwflow module.

Creates tables per gwflowDatabaseDesign.md and populates them from:
- The generated gwflowcells.shp grid
- Spatial intersections with HRUs, channels, LSUs, lakes
- DEM sampling for cell elevations
- Aquifer thickness/permeability rasters and shapefiles
"""

import os
import sys
import math
import numpy as np
import multiprocessing
from multiprocessing import Pool, cpu_count
from osgeo import gdal, ogr
from qgis.PyQt.QtCore import QCoreApplication, QEventLoop, QSettings
from qgis.core import (
    QgsVectorLayer, QgsRasterLayer, QgsFeatureRequest, QgsGeometry,
    QgsProject, QgsPointXY, QgsRectangle, QgsSpatialIndex
)

from .QSWATUtils import QSWATUtils
from .QSWATTopology import QSWATTopology
from .parameters import Parameters


_mpExecutableConfigured = False


def _configureMultiprocessing():
    """Make multiprocessing workers spawn the bundled Python, not QGIS.

    Under QGIS on Windows sys.executable is qgis-bin.exe, so the default
    'spawn' start method relaunches a whole new QGIS instance for every worker.
    Pointing multiprocessing at pythonw.exe in the Python prefix
    (sys.exec_prefix) makes it start plain Python processes instead.
    Does nothing on non-Windows platforms (which use 'fork') and runs once.
    """
    global _mpExecutableConfigured
    if _mpExecutableConfigured:
        return
    if sys.platform == 'win32':
        for exe in ('pythonw.exe', 'python.exe'):
            candidate = os.path.join(sys.exec_prefix, exe)
            if os.path.isfile(candidate):
                multiprocessing.set_executable(candidate)
                break
    _mpExecutableConfigured = True


def _find_connections_chunk(args):
    """Worker: find touching neighbors for a chunk of cells using WKB geometry."""
    from shapely import wkb, prepare
    chunk_fids, all_wkbs, all_cellids, all_bboxes = args
    results = []
    # Build a simple spatial lookup: cells indexed by grid position
    for fid in chunk_fids:
        geom = wkb.loads(all_wkbs[fid])
        prepare(geom)
        cellId = all_cellids[fid]
        bx = all_bboxes[fid]
        for other_fid, other_bbox in all_bboxes.items():
            if other_fid == fid:
                continue
            # Quick bbox rejection
            if (bx[2] < other_bbox[0] or bx[0] > other_bbox[2] or
                bx[3] < other_bbox[1] or bx[1] > other_bbox[3]):
                continue
            other_geom = wkb.loads(all_wkbs[other_fid])
            if geom.touches(other_geom):
                results.append((cellId, all_cellids[other_fid]))
    return results


def _intersect_cells_chunk(args):
    """Worker: compute intersection areas between grid cells and overlay features."""
    from shapely import wkb
    cell_data, overlay_wkbs, overlay_ids = args
    results = []
    for cellId, cell_wkb in cell_data:
        cell_geom = wkb.loads(cell_wkb)
        cell_bbox = cell_geom.bounds  # (minx, miny, maxx, maxy)
        for oid, o_wkb in zip(overlay_ids, overlay_wkbs):
            o_geom = wkb.loads(o_wkb)
            o_bbox = o_geom.bounds
            if (cell_bbox[2] < o_bbox[0] or cell_bbox[0] > o_bbox[2] or
                cell_bbox[3] < o_bbox[1] or cell_bbox[1] > o_bbox[3]):
                continue
            if cell_geom.intersects(o_geom):
                inter = cell_geom.intersection(o_geom)
                area = inter.area
                if area > 0:
                    results.append((cellId, oid, area))
    return results


# SQL table definitions

_TABLES = {
    # Schema must match the swatplus-editor codes_gw model (column names + order).
    'codes_gw': '''CREATE TABLE IF NOT EXISTS codes_gw (
        id INTEGER PRIMARY KEY DEFAULT 1,
        grid_type TEXT DEFAULT 'structured',
        cell_size REAL DEFAULT 200,
        num_rows INTEGER DEFAULT 0,
        num_cols INTEGER DEFAULT 0,
        num_cells INTEGER DEFAULT 0,
        boundary_condition INTEGER DEFAULT 2,
        recharge_type INTEGER DEFAULT 2,
        gw_soil_transfer INTEGER DEFAULT 1,
        saturation_excess INTEGER DEFAULT 1,
        external_pumping INTEGER DEFAULT 0,
        tile_drainage INTEGER DEFAULT 0,
        reservoir_exchange INTEGER DEFAULT 1,
        wetland_exchange INTEGER DEFAULT 1,
        floodplain_exchange INTEGER DEFAULT 1,
        canal_seepage INTEGER DEFAULT 0,
        solute_transport INTEGER DEFAULT 0,
        timestep_days REAL DEFAULT 1.0,
        daily_output INTEGER DEFAULT 1,
        monthly_output INTEGER DEFAULT 0,
        annual_output INTEGER DEFAULT 1,
        aa_output INTEGER DEFAULT 1,
        river_depth REAL DEFAULT 5.0,
        tile_depth REAL DEFAULT 1.22,
        tile_area REAL DEFAULT 50,
        tile_k REAL DEFAULT 5.0,
        resbed_thickness REAL DEFAULT 2.0,
        resbed_k REAL DEFAULT 9.99e-6,
        wet_thickness REAL DEFAULT 0.25,
        transport_steps INTEGER DEFAULT 1,
        disp_coef REAL DEFAULT 5.0,
        detail_row INTEGER DEFAULT 0,
        detail_col INTEGER DEFAULT 0,
        heat_transport INTEGER DEFAULT 0
    )''',

    # thermal_K: per-zone thermal conductivity (heat batch); 0 until heat is on.
    'zones_gw': '''CREATE TABLE IF NOT EXISTS zones_gw (
        zone_id INTEGER PRIMARY KEY,
        aquifer_k REAL,
        specific_yield REAL DEFAULT 0.2,
        streambed_k REAL DEFAULT 0.005,
        streambed_thickness REAL DEFAULT 0.5,
        thermal_K REAL DEFAULT 0
    )''',

    'cells_gw': '''CREATE TABLE IF NOT EXISTS cells_gw (
        cell_id INTEGER PRIMARY KEY,
        status INTEGER NOT NULL DEFAULT 1,
        row INTEGER,
        col INTEGER,
        x_centroid REAL NOT NULL,
        y_centroid REAL NOT NULL,
        area REAL NOT NULL,
        elevation REAL NOT NULL DEFAULT 0,
        aquifer_thickness REAL NOT NULL DEFAULT 50,
        zone INTEGER NOT NULL DEFAULT 1 REFERENCES zones_gw (zone_id),
        extinction_depth REAL DEFAULT 1.0,
        initial_head REAL,
        tile INTEGER DEFAULT 0,
        streambed_k REAL,
        streambed_thickness REAL,
        bc_type INTEGER,
        tile_depth REAL,
        tile_area REAL,
        tile_k REAL,
        init_temp REAL,
        gis_id INTEGER
    )''',

    'cellcon_gw': '''CREATE TABLE IF NOT EXISTS cellcon_gw (
        cell_id INTEGER NOT NULL REFERENCES cells_gw (cell_id),
        connected_cell_id INTEGER NOT NULL REFERENCES cells_gw (cell_id),
        PRIMARY KEY (cell_id, connected_cell_id)
    )''',

    'hrucell_gw': '''CREATE TABLE IF NOT EXISTS hrucell_gw (
        cell_id INTEGER NOT NULL REFERENCES cells_gw (cell_id),
        hru_id INTEGER NOT NULL,
        area_m2 REAL NOT NULL,
        PRIMARY KEY (cell_id, hru_id)
    )''',

    'lsucell_gw': '''CREATE TABLE IF NOT EXISTS lsucell_gw (
        cell_id INTEGER NOT NULL REFERENCES cells_gw (cell_id),
        lsu_id INTEGER NOT NULL,
        area_m2 REAL NOT NULL,
        PRIMARY KEY (cell_id, lsu_id)
    )''',

    # obs (0/1) and dep_zone fold in the former chancells_obs / chancells_depth
    # zone; the daily depth series stays in chan_depth_gw.
    'chancell_gw': '''CREATE TABLE IF NOT EXISTS chancell_gw (
        id INTEGER PRIMARY KEY,
        cell_id INTEGER NOT NULL REFERENCES cells_gw (cell_id),
        channel_id INTEGER NOT NULL,
        bed_elevation REAL NOT NULL,
        length_m REAL NOT NULL,
        zone_id INTEGER NOT NULL DEFAULT 1 REFERENCES zones_gw (zone_id),
        obs INTEGER NOT NULL DEFAULT 0,
        dep_zone INTEGER
    )''',

    'floodplain_gw': '''CREATE TABLE IF NOT EXISTS floodplain_gw (
        cell_id INTEGER NOT NULL REFERENCES cells_gw (cell_id),
        channel_id INTEGER NOT NULL,
        area_m2 REAL NOT NULL,
        conductivity REAL NOT NULL DEFAULT 0,
        PRIMARY KEY (cell_id, channel_id)
    )''',

    'rescell_gw': '''CREATE TABLE IF NOT EXISTS rescell_gw (
        cell_id INTEGER NOT NULL REFERENCES cells_gw (cell_id),
        reservoir_id INTEGER NOT NULL,
        stage REAL DEFAULT 0,
        PRIMARY KEY (cell_id, reservoir_id)
    )''',

    'pumpex_gw': '''CREATE TABLE IF NOT EXISTS pumpex_gw (
        id INTEGER PRIMARY KEY,
        cell_id INTEGER NOT NULL REFERENCES cells_gw (cell_id),
        start_year INTEGER NOT NULL,
        start_day INTEGER NOT NULL,
        end_year INTEGER NOT NULL,
        end_day INTEGER NOT NULL,
        rate_m3day REAL NOT NULL
    )''',

    # Observation cells (feeds outputs.gw).
    'obs_gw': '''CREATE TABLE IF NOT EXISTS obs_gw (
        cell_id INTEGER NOT NULL REFERENCES cells_gw (cell_id),
        name TEXT,
        PRIMARY KEY (cell_id)
    )''',

    # HRUs to emit daily pumping output for; written to hru_pump.gw if non-empty.
    'hru_pump_gw': '''CREATE TABLE IF NOT EXISTS hru_pump_gw (
        hru_id INTEGER PRIMARY KEY
    )''',

    # Time-varying boundary heads: one row per cell per CALENDAR year; the editor
    # pivots to the per-sim-year positional row for tvheads.gw.
    'tvheads_gw': '''CREATE TABLE IF NOT EXISTS tvheads_gw (
        cell_id INTEGER NOT NULL REFERENCES cells_gw (cell_id),
        year INTEGER NOT NULL,
        head REAL NOT NULL,
        PRIMARY KEY (cell_id, year)
    )''',

    # Head-output times (feeds outputs.gw).
    'out_times_gw': '''CREATE TABLE IF NOT EXISTS out_times_gw (
        year INTEGER NOT NULL,
        jday INTEGER NOT NULL,
        PRIMARY KEY (year, jday)
    )''',

    # Per-solute params (editor solute_gw model -> solute.gw).
    'solute_gw': '''CREATE TABLE IF NOT EXISTS solute_gw (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        sorption_coef REAL DEFAULT 1,
        rate_const REAL DEFAULT 0,
        canal_irr REAL DEFAULT 0,
        init_conc REAL DEFAULT 0
    )''',

    # Per-cell initial solute concentration (normalized); empty until the solute batch.
    'cell_sol_gw': '''CREATE TABLE IF NOT EXISTS cell_sol_gw (
        cell_id INTEGER NOT NULL REFERENCES cells_gw (cell_id),
        solute_id INTEGER NOT NULL REFERENCES solute_gw (id),
        init_conc REAL DEFAULT 0,
        PRIMARY KEY (cell_id, solute_id)
    )''',

    'wetland_gw': '''CREATE TABLE IF NOT EXISTS wetland_gw (
        wet_id INTEGER PRIMARY KEY,
        thickness REAL
    )''',

    # Optional flat-file tables (population/UI deferred).

    # Groundwater-surface-water groups (group_id + member cells).
    'sw_group_gw': '''CREATE TABLE IF NOT EXISTS sw_group_gw (
        group_id INTEGER NOT NULL,
        cell_id INTEGER NOT NULL REFERENCES cells_gw (cell_id),
        PRIMARY KEY (group_id, cell_id)
    )''',

    # Recharge pond params; unload conc in pond_solute_gw, cells in pond_cell_gw.
    'ponds_gw': '''CREATE TABLE IF NOT EXISTS ponds_gw (
        id INTEGER PRIMARY KEY,
        area REAL,
        chan INTEGER,
        canal INTEGER,
        unl INTEGER,
        bed_k REAL,
        wsta INTEGER,
        evap_co REAL,
        start_yr INTEGER,
        start_mo INTEGER,
        start_day INTEGER
    )''',

    # Per-solute unload concentration for ponds.
    'pond_solute_gw': '''CREATE TABLE IF NOT EXISTS pond_solute_gw (
        pond_id INTEGER NOT NULL REFERENCES ponds_gw (id),
        solute_idx INTEGER NOT NULL,
        unl_conc REAL DEFAULT 0,
        PRIMARY KEY (pond_id, solute_idx)
    )''',

    # Pond-to-cell connections.
    'pond_cell_gw': '''CREATE TABLE IF NOT EXISTS pond_cell_gw (
        pond_id INTEGER NOT NULL REFERENCES ponds_gw (id),
        cell_id INTEGER NOT NULL REFERENCES cells_gw (cell_id),
        conn_area REAL,
        PRIMARY KEY (pond_id, cell_id)
    )''',

    # Optional daily pond-diversion series (per pond per day); absent => 0.
    'pond_div_gw': '''CREATE TABLE IF NOT EXISTS pond_div_gw (
        pond_id INTEGER NOT NULL REFERENCES ponds_gw (id),
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        day INTEGER NOT NULL,
        div REAL NOT NULL DEFAULT 0,
        PRIMARY KEY (pond_id, year, month, day)
    )''',

    # Depth-ET curve (ordered points).
    'phreato_gw': '''CREATE TABLE IF NOT EXISTS phreato_gw (
        id INTEGER PRIMARY KEY,
        depth REAL NOT NULL,
        et_rate REAL NOT NULL
    )''',

    # Phreatophyte cell list.
    'phreato_cell_gw': '''CREATE TABLE IF NOT EXISTS phreato_cell_gw (
        cell_id INTEGER PRIMARY KEY REFERENCES cells_gw (cell_id),
        area REAL
    )''',

    # Daily channel-depth series, one depth per dep_zone per day.
    'chan_depth_gw': '''CREATE TABLE IF NOT EXISTS chan_depth_gw (
        year INTEGER NOT NULL,
        jday INTEGER NOT NULL,
        zone_idx INTEGER NOT NULL,
        depth REAL NOT NULL,
        PRIMARY KEY (year, jday, zone_idx)
    )''',
}

# Drop all tables before each regen (incl. legacy pre-rename names) so a regrid
# of an older DB can't leave stale rows.
_DROP_ORDER = [
    # current tables
    'pond_div_gw', 'pond_solute_gw', 'pond_cell_gw', 'ponds_gw',
    'phreato_cell_gw', 'phreato_gw', 'sw_group_gw', 'chan_depth_gw',
    'cell_sol_gw', 'solute_gw', 'out_times_gw',
    'gwflow_init_conc', 'gwflow_solutes', 'gwflow_out_days',
    'tvheads_gw', 'hru_pump_gw', 'obs_gw', 'gwflow_obs_locs',
    'pumpex_gw', 'rescell_gw', 'floodplain_gw', 'chancell_gw',
    'lsucell_gw', 'hrucell_gw', 'cellcon_gw',
    'cells_gw', 'zones_gw', 'codes_gw', 'wetland_gw',
    # legacy names (older DBs)
    'gwflow_chancell_obs', 'gwflow_chancell', 'gwflow_rivcell',
    'gwflow_grid', 'gwflow_cell', 'gwflow_cell_connection',
    'gwflow_hrucell', 'gwflow_lsucell', 'gwflow_fpcell', 'gwflow_rescell',
    'gwflow_pump', 'gwflow_hru_pump_obs', 'gwflow_tvhead',
    'gwflow_zone', 'gwflow_config', 'gwflow_base', 'gwflow_wetland',
]


class GwflowDB:
    """Creates and populates gwflow database tables."""

    def __init__(self, gv, dialog, progress=None):
        self._gv = gv
        self._dialog = dialog
        self._progress = progress or (lambda msg: None)
        self._progressBar = dialog.progressBar2 if dialog else None

    def run(self):
        """Create tables, populate cells and intersections."""
        _configureMultiprocessing()
        gridPath = os.path.join(self._gv.shapesDir, 'gwflowcells.shp')
        if not os.path.isfile(gridPath):
            QSWATUtils.error('gwflow grid not found. Click Generate Grid first.',
                             self._gv.isBatch, logFile=self._gv.logFile)
            return False

        gridLayer = QgsVectorLayer(gridPath, 'gwflowcells', 'ogr')
        if not gridLayer.isValid():
            QSWATUtils.error('Failed to load gwflow grid: {0}'.format(gridPath),
                             self._gv.isBatch, logFile=self._gv.logFile)
            return False

        steps = [
            'Creating tables',
            'Writing configuration',
            'Populating cells',
            'Building connections',
            'HRU intersections',
            'LSU intersections',
            'Channel intersections',
            'Reservoir intersections',
            'Floodplain intersections',
            'Mapping wells',
            'Writing solutes',
        ]
        if self._progressBar:
            self._progressBar.setVisible(True)
            self._progressBar.setMaximum(len(steps))
            self._progressBar.setValue(0)

        def step(i):
            if self._progressBar:
                self._progressBar.setValue(i)
                self._progressBar.setFormat(steps[i])
            QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)

        with self._gv.db.conn as conn:
            step(0); self._createTables(conn)
            step(1); self._populateConfig(conn); self._populateZones(conn)
            step(2); self._populateCells(conn, gridLayer)
            # num_cells = active cell count (ncell) = rows in cells_gw. num_rows/
            # num_cols are full-rectangle metadata; backfill from active cells only
            # if _populateConfig left them 0 (e.g. unstructured).
            numCells = conn.execute('SELECT COUNT(*) FROM cells_gw').fetchone()[0]
            maxRow = conn.execute('SELECT MAX(row) FROM cells_gw').fetchone()[0] or 0
            maxCol = conn.execute('SELECT MAX(col) FROM cells_gw').fetchone()[0] or 0
            conn.execute('UPDATE codes_gw SET num_cells=? WHERE id=1', (numCells,))
            conn.execute('UPDATE codes_gw SET num_rows=? WHERE id=1 AND (num_rows IS NULL OR num_rows=0)', (maxRow,))
            conn.execute('UPDATE codes_gw SET num_cols=? WHERE id=1 AND (num_cols IS NULL OR num_cols=0)', (maxCol,))
            step(3); self._populateCellConnections(conn, gridLayer)
            step(4); self._populateHRUCells(conn, gridLayer)
            step(5); self._populateLSUCells(conn, gridLayer)
            step(6); self._populateChannelCells(conn, gridLayer)
            step(7); self._populateReservoirCells(conn, gridLayer)
            step(8); self._populateFloodplainCells(conn, gridLayer)
            step(9); self._populateObservationWells(conn, gridLayer)
            step(10); self._populateSolutes(conn)

        if self._progressBar:
            self._progressBar.setValue(len(steps))
            self._progressBar.setFormat('Done')
        return True

    def _createTables(self, conn):
        self._progress('Creating gwflow tables')
        for table in _DROP_ORDER:
            conn.execute('DROP TABLE IF EXISTS {0}'.format(table))
        for name in ['codes_gw', 'zones_gw', 'cells_gw',
                      'cellcon_gw', 'hrucell_gw', 'lsucell_gw',
                      'chancell_gw', 'floodplain_gw', 'rescell_gw',
                      'pumpex_gw', 'obs_gw', 'hru_pump_gw',
                      'tvheads_gw', 'out_times_gw',
                      'solute_gw', 'cell_sol_gw', 'wetland_gw',
                      'sw_group_gw', 'ponds_gw', 'pond_solute_gw',
                      'pond_cell_gw', 'pond_div_gw', 'phreato_gw',
                      'phreato_cell_gw', 'chan_depth_gw']:
            conn.execute(_TABLES[name])
        conn.execute('CREATE INDEX IF NOT EXISTS idx_cells_gw_zone ON cells_gw (zone)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_hrucell_gw_hru ON hrucell_gw (hru_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_lsucell_gw_lsu ON lsucell_gw (lsu_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_floodplain_gw_channel ON floodplain_gw (channel_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_rescell_gw_res ON rescell_gw (reservoir_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_chancell_gw_cell ON chancell_gw (cell_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_chancell_gw_channel ON chancell_gw (channel_id)')

    def _populateConfig(self, conn):
        """Write single config row with defaults from dialog."""
        self._progress('Writing gwflow configuration')
        dialog = self._dialog
        gridType = 'structured' if dialog.gridTab.currentIndex == 0 else 'unstructured'
        cellSize = dialog.cellSize.value() if gridType == 'structured' else dialog.maxCellSize.value()
        useTile = 1 if dialog.useTileDrains.isChecked() else 0

        numRows = 0
        numCols = 0
        if gridType == 'structured':
            gridPath = os.path.join(self._gv.shapesDir, 'gwflowcells.shp')
            gridLayer = QgsVectorLayer(gridPath, 'tmp', 'ogr')
            if gridLayer.isValid():
                extent = gridLayer.extent()
                cs = dialog.cellSize.value()
                if cs > 0:
                    numRows = int(math.ceil((extent.yMaximum() - extent.yMinimum()) / cs))
                    numCols = int(math.ceil((extent.xMaximum() - extent.xMinimum()) / cs))

        conn.execute('''INSERT INTO codes_gw
                        (id, grid_type, cell_size, num_rows, num_cols, tile_drainage, recharge_type)
                        VALUES (1, ?, ?, ?, ?, ?, 1)''',
                     (gridType, cellSize, numRows, numCols, useTile))

    def _populateZones(self, conn):
        """Create zones from aquifer permeability shapefile."""
        self._progress('Processing aquifer zones')
        permFile = self._dialog.aquiferPermeability.text()
        if not permFile or not os.path.isfile(permFile):
            conn.execute('INSERT INTO zones_gw (zone_id, aquifer_k) VALUES (1, 1.0)')
            return

        permLayer = QgsVectorLayer(permFile, 'permeability', 'ogr')
        if not permLayer.isValid():
            conn.execute('INSERT INTO zones_gw (zone_id, aquifer_k) VALUES (1, 1.0)')
            return

        # Find K field
        kFieldIdx = -1
        for i, field in enumerate(permLayer.fields()):
            name = field.name().lower()
            if name in ('k', 'k_mday', 'k_m_day', 'hydc', 'conductivity', 'perm'):
                kFieldIdx = i
                break

        zoneId = 0
        for feat in permLayer.getFeatures():
            zoneId += 1
            kVal = feat[kFieldIdx] if kFieldIdx >= 0 else 1.0
            if kVal is None or kVal == 0:
                kVal = 1.0
            conn.execute('INSERT INTO zones_gw (zone_id, aquifer_k) VALUES (?, ?)',
                         (zoneId, float(kVal)))

        if zoneId == 0:
            conn.execute('INSERT INTO zones_gw (zone_id, aquifer_k) VALUES (1, 1.0)')

    def _populateCells(self, conn, gridLayer):
        """Populate cell table from grid shapefile, sampling DEM and thickness."""
        self._progress('Populating gwflow cells')

        demDs = None
        demBand = None
        demTransform = None
        if self._gv.demFile and os.path.isfile(self._gv.demFile):
            demDs = gdal.Open(self._gv.demFile, gdal.GA_ReadOnly)
            if demDs:
                demBand = demDs.GetRasterBand(1)
                demTransform = demDs.GetGeoTransform()

        thickDs = None
        thickBand = None
        thickTransform = None
        thickFile = self._dialog.aquiferThickness.text()
        if thickFile and os.path.isfile(thickFile):
            thickDs = gdal.Open(thickFile, gdal.GA_ReadOnly)
            if thickDs:
                thickBand = thickDs.GetRasterBand(1)
                thickTransform = thickDs.GetGeoTransform()

        permZones = self._loadPermZones()
        wsGeom = self._getWatershedBoundaryLine()

        # For structured grids, compute row/col from cell centroid position
        isStructured = self._dialog.gridTab.currentIndex == 0
        cellSize = self._dialog.cellSize.value() if isStructured else 0
        gridExtent = gridLayer.extent() if isStructured else None

        # gis_id = gwflowcells.shp cell id (== cell_id), for GIS join-back; stored
        # so editor/reader don't recompute it from row/col.
        sql = '''INSERT INTO cells_gw
                 (cell_id, status, row, col, x_centroid, y_centroid, area, elevation,
                  aquifer_thickness, zone, initial_head, gis_id)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''

        count = 0
        for feat in gridLayer.getFeatures():
            count += 1
            if count % 50 == 0:
                QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
            cellId = feat['cell_id']
            geom = feat.geometry()
            centroid = geom.centroid().asPoint()
            area = geom.area()

            # Compute row/col for structured grids
            row = None
            col = None
            if isStructured and gridExtent and cellSize > 0:
                col = int((centroid.x() - gridExtent.xMinimum()) / cellSize) + 1
                row = int((gridExtent.yMaximum() - centroid.y()) / cellSize) + 1

            # Cell elevation = mean of DEM pixels over the cell footprint, not a
            # single centroid pixel. gwflow cells span many DEM pixels, so a
            # point sample picks up local spikes and produces a rough elevation
            # field (and spiky water-table-depth = elev - head); the cell mean is
            # the representative value.
            elev = self._cellMeanRaster(demBand, demTransform, geom)
            if elev is None or elev < -9000:
                elev = 0.0

            # Aquifer thickness: same, mean over the cell footprint.
            thick = self._cellMeanRaster(thickBand, thickTransform, geom)
            if thick is None or thick <= 0:
                thick = 50.0

            # Assign zone
            zoneId = self._findZone(permZones, centroid)

            # Determine status: 2=boundary (touches watershed edge), 1=interior
            status = 1
            if wsGeom is not None:
                try:
                    if geom.distance(wsGeom) < math.sqrt(area) * 0.1:
                        status = 2
                except Exception:
                    pass

            initialHead = elev - 5.0

            conn.execute(sql, (cellId, status, row, col, centroid.x(), centroid.y(),
                               area, elev, thick, zoneId, initialHead, cellId))

        demDs = None
        thickDs = None

    def _populateCellConnections(self, conn, gridLayer):
        """Build cell adjacency using parallel workers."""
        self._progress('Building cell connections')
        all_wkbs = {}
        all_cellids = {}
        all_bboxes = {}
        for feat in gridLayer.getFeatures():
            fid = feat.id()
            geom = feat.geometry()
            all_wkbs[fid] = bytes(geom.asWkb())
            all_cellids[fid] = feat['cell_id']
            bb = geom.boundingBox()
            all_bboxes[fid] = (bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum())

        fids = list(all_wkbs.keys())
        nWorkers = min(int(QSettings().value('/QSWATPlus/NumProcesses', 8)), len(fids), cpu_count())
        nWorkers = max(1, nWorkers)

        chunks = [[] for _ in range(nWorkers)]
        for i, fid in enumerate(fids):
            chunks[i % nWorkers].append(fid)

        worker_args = [(chunk, all_wkbs, all_cellids, all_bboxes) for chunk in chunks if chunk]

        sql = 'INSERT OR IGNORE INTO cellcon_gw (cell_id, connected_cell_id) VALUES (?, ?)'
        if nWorkers > 1 and len(fids) > 50:
            with Pool(nWorkers) as pool:
                for result in pool.imap_unordered(_find_connections_chunk, worker_args):
                    for pair in result:
                        conn.execute(sql, pair)
                    QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
        else:
            for args in worker_args:
                for pair in _find_connections_chunk(args):
                    conn.execute(sql, pair)

    def _populateHRUCells(self, conn, gridLayer):
        """Intersect gwflow grid with HRU shapefile using parallel workers."""
        self._progress('Computing HRU-cell intersections')
        hruFile = self._gv.actHRUsFile
        if not hruFile or not os.path.isfile(hruFile):
            QSWATUtils.error('You cannot use gwflow if you have not generated a fullHRUs shapefile', self._gv.isBatch)
            return

        hruLayer = QgsVectorLayer(hruFile, 'hrus', 'ogr')
        if not hruLayer.isValid():
            return

        hruIdIdx = hruLayer.fields().indexOf('HRUS')
        if hruIdIdx < 0:
            hruIdIdx = hruLayer.fields().indexOf('HRU')
        if hruIdIdx < 0:
            for i, f in enumerate(hruLayer.fields()):
                if 'hru' in f.name().lower():
                    hruIdIdx = i
                    break

        # Serialize cell and HRU geometries for parallel processing
        cell_data = []
        for feat in gridLayer.getFeatures():
            cell_data.append((feat['cell_id'], bytes(feat.geometry().asWkb())))

        overlay_wkbs = []
        overlay_ids = []
        for feat in hruLayer.getFeatures():
            hruVal = feat[hruIdIdx] if hruIdIdx >= 0 else feat.id()
            if hruVal is None:
                continue
            try:
                hruId = int(str(hruVal).split(',')[0])
                if hruId > 0:
                    overlay_wkbs.append(bytes(feat.geometry().asWkb()))
                    overlay_ids.append(hruId)
            except (ValueError, TypeError):
                pass

        if not cell_data or not overlay_ids:
            return

        nWorkers = min(int(QSettings().value('/QSWATPlus/NumProcesses', 8)), len(cell_data), cpu_count())
        nWorkers = max(1, nWorkers)

        # Split cells into chunks
        chunks = [[] for _ in range(nWorkers)]
        for i, cd in enumerate(cell_data):
            chunks[i % nWorkers].append(cd)

        sql = 'INSERT OR IGNORE INTO hrucell_gw (cell_id, hru_id, area_m2) VALUES (?, ?, ?)'
        worker_args = [(chunk, overlay_wkbs, overlay_ids) for chunk in chunks if chunk]

        if nWorkers > 1 and len(cell_data) > 20:
            with Pool(nWorkers) as pool:
                for result in pool.imap_unordered(_intersect_cells_chunk, worker_args):
                    for cellId, hruId, area in result:
                        conn.execute(sql, (cellId, hruId, area))
                    QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
        else:
            for args in worker_args:
                for cellId, hruId, area in _intersect_cells_chunk(args):
                    conn.execute(sql, (cellId, hruId, area))

    def _populateLSUCells(self, conn, gridLayer):
        """Intersect gwflow grid with LSU shapefile using parallel workers."""
        self._progress('Computing LSU-cell intersections')
        lsuFile = self._gv.actLSUsFile
        if not lsuFile or not os.path.isfile(lsuFile):
            return

        lsuLayer = QgsVectorLayer(lsuFile, 'lsus', 'ogr')
        if not lsuLayer.isValid():
            return

        lsuIdIdx = lsuLayer.fields().indexOf('LSUID')
        if lsuIdIdx < 0:
            return

        cell_data = []
        for feat in gridLayer.getFeatures():
            cell_data.append((feat['cell_id'], bytes(feat.geometry().asWkb())))

        overlay_wkbs = []
        overlay_ids = []
        for feat in lsuLayer.getFeatures():
            lsuId = feat[lsuIdIdx]
            if lsuId is not None:
                overlay_wkbs.append(bytes(feat.geometry().asWkb()))
                overlay_ids.append(int(lsuId))

        if not cell_data or not overlay_ids:
            return

        nWorkers = min(int(QSettings().value('/QSWATPlus/NumProcesses', 8)), len(cell_data), cpu_count())
        nWorkers = max(1, nWorkers)

        chunks = [[] for _ in range(nWorkers)]
        for i, cd in enumerate(cell_data):
            chunks[i % nWorkers].append(cd)

        sql = 'INSERT OR IGNORE INTO lsucell_gw (cell_id, lsu_id, area_m2) VALUES (?, ?, ?)'
        worker_args = [(chunk, overlay_wkbs, overlay_ids) for chunk in chunks if chunk]

        if nWorkers > 1 and len(cell_data) > 20:
            with Pool(nWorkers) as pool:
                for result in pool.imap_unordered(_intersect_cells_chunk, worker_args):
                    for cellId, lsuId, area in result:
                        conn.execute(sql, (cellId, lsuId, area))
                    QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
        else:
            for args in worker_args:
                for cellId, lsuId, area in _intersect_cells_chunk(args):
                    conn.execute(sql, (cellId, lsuId, area))

    def _populateChannelCells(self, conn, gridLayer):
        """Intersect gwflow grid with channel lines."""
        self._progress('Computing channel-cell intersections')
        # Use rivs1.shp: it carries the SWAT+ Channel number (== gis_channels.id /
        # chandeg.con / chancell.gw). self._gv.channelFile is the raw TauDEM
        # channel shapefile, which has only LINKNO (a different numbering) and no
        # Channel field, so it must not be used for the channel-cell links.
        channelFile = QSWATUtils.join(self._gv.shapesDir, Parameters._RIVS1 + '.shp')
        if not os.path.isfile(channelFile):
            return

        chanLayer = QgsVectorLayer(channelFile, 'channels', 'ogr')
        if not chanLayer.isValid():
            return

        chanIdIdx = chanLayer.fields().indexOf(QSWATTopology._CHANNEL)
        if chanIdIdx < 0:
            QSWATUtils.error('No {0} field in {1}; cannot link gwflow cells to channels.'
                             .format(QSWATTopology._CHANNEL, channelFile),
                             self._gv.isBatch, logFile=self._gv.logFile)
            return
        
        chanDepthIdx = chanLayer.fields().indexOf(QSWATTopology._DEP2)
        validChannels = set()
        for row in conn.execute('SELECT id FROM gis_channels'):
            validChannels.add(row[0])

        demDs = None
        demBand = None
        demTransform = None
        riverDepth = 5.0 # default: changed later to DEP2 field
        if self._gv.demFile and os.path.isfile(self._gv.demFile):
            demDs = gdal.Open(self._gv.demFile, gdal.GA_ReadOnly)
            if demDs:
                demBand = demDs.GetRasterBand(1)
                demTransform = demDs.GetGeoTransform()

        sql = '''INSERT INTO chancell_gw (cell_id, channel_id, bed_elevation, length_m, zone_id)
                 VALUES (?, ?, ?, ?, 1)'''

        for cellFeat in gridLayer.getFeatures():
            cellId = cellFeat['cell_id']
            cellGeom = cellFeat.geometry()
            cellBbox = cellGeom.boundingBox()

            for chanFeat in chanLayer.getFeatures(QgsFeatureRequest().setFilterRect(cellBbox)):
                chanId = int(chanFeat[chanIdIdx])
                if chanId not in validChannels:
                    continue
                if chanDepthIdx >= 0:
                    riverDepth = float(chanFeat[chanDepthIdx])
                chanGeom = chanFeat.geometry()
                if cellGeom.intersects(chanGeom):
                    intersection = cellGeom.intersection(chanGeom)
                    length = intersection.length()
                    if length > 0:
                        centroid = intersection.centroid().asPoint()
                        elev = self._sampleRaster(demBand, demTransform, centroid.x(), centroid.y())
                        bedElev = (elev - riverDepth) if elev is not None and elev > -9000 else 0.0
                        conn.execute(sql, (cellId, chanId, bedElev, length))

        demDs = None

    def _populateReservoirCells(self, conn, gridLayer):
        """Find cells that overlap reservoir/lake polygons."""
        self._progress('Computing reservoir-cell intersections')
        lakeFile = self._gv.lakeFile
        if not lakeFile or not os.path.isfile(lakeFile):
            return

        lakeLayer = QgsVectorLayer(lakeFile, 'lakes', 'ogr')
        if not lakeLayer.isValid():
            return

        lakeIdIdx = -1
        for i, f in enumerate(lakeLayer.fields()):
            if 'id' in f.name().lower() or 'lakeid' in f.name().lower():
                lakeIdIdx = i
                break

        sql = 'INSERT OR IGNORE INTO rescell_gw (cell_id, reservoir_id, stage) VALUES (?, ?, 0)'

        for cellFeat in gridLayer.getFeatures():
            cellId = cellFeat['cell_id']
            cellGeom = cellFeat.geometry()
            cellBbox = cellGeom.boundingBox()

            for lakeFeat in lakeLayer.getFeatures(QgsFeatureRequest().setFilterRect(cellBbox)):
                lakeGeom = lakeFeat.geometry()
                if cellGeom.intersects(lakeGeom):
                    lakeId = lakeFeat[lakeIdIdx] if lakeIdIdx >= 0 else lakeFeat.id()
                    if lakeId is not None:
                        conn.execute(sql, (cellId, int(lakeId)))

    def _populateFloodplainCells(self, conn, gridLayer):
        """Find cells that overlap floodplain LSUs, only for valid channels."""
        self._progress('Computing floodplain-cell intersections')
        lsuFile = self._gv.actLSUsFile
        if not lsuFile or not os.path.isfile(lsuFile):
            return

        lsuLayer = QgsVectorLayer(lsuFile, 'lsus', 'ogr')
        if not lsuLayer.isValid():
            return

        lsuIdIdx = lsuLayer.fields().indexOf('LSUID')
        if lsuIdIdx < 0:
            return

        validChannels = set()
        for row in conn.execute('SELECT id FROM gis_channels'):
            validChannels.add(row[0])

        sql = 'INSERT OR IGNORE INTO floodplain_gw (cell_id, channel_id, area_m2, conductivity) VALUES (?, ?, ?, 0)'

        for cellFeat in gridLayer.getFeatures():
            cellId = cellFeat['cell_id']
            cellGeom = cellFeat.geometry()
            cellBbox = cellGeom.boundingBox()

            for lsuFeat in lsuLayer.getFeatures(QgsFeatureRequest().setFilterRect(cellBbox)):
                lsuId = lsuFeat[lsuIdIdx]
                if lsuId is None:
                    continue
                lsuId = int(lsuId)
                if lsuId % 10 != 1:
                    continue
                channelId = lsuId // 10
                if channelId not in validChannels:
                    continue
                lsuGeom = lsuFeat.geometry()
                if cellGeom.intersects(lsuGeom):
                    intersection = cellGeom.intersection(lsuGeom)
                    interArea = intersection.area()
                    if interArea > 0:
                        conn.execute(sql, (cellId, channelId, interArea))

    def _populateSolutes(self, conn):
        """Insert default solute species."""
        self._progress('Writing default solutes')
        # columns: name, sorption_coef, rate_const, canal_irr, init_conc
        solutes = [
            ('no3-n', 1.0, -0.0001, 3.0, 3.0),
            ('p', 2.0, 0, 0.05, 0.05),
            ('so4', 1.0, 0, 0, 100.0),
            ('ca', 1.0, 0, 0, 50.0),
            ('mg', 1.0, 0, 0, 30.0),
            ('na', 1.0, 0, 0, 40.0),
            ('k', 1.0, 0, 0, 1.0),
            ('cl', 1.0, 0, 0, 25.0),
            ('co3', 1.0, 0, 0, 1.0),
            ('hco3', 1.0, 0, 0, 80.0),
        ]
        sql = 'INSERT INTO solute_gw (name, sorption_coef, rate_const, canal_irr, init_conc) VALUES (?, ?, ?, ?, ?)'
        for s in solutes:
            conn.execute(sql, s)

    def _populateObservationWells(self, conn, gridLayer):
        """Map observation well points (RES=3 in outlets) to nearest grid cells."""
        self._progress('Mapping observation wells to cells')
        # Source wells as gwflowgrid._getWellCoords does (outlets file; inlet==0,
        # RES==well type, ptsource==0) so obs_gw holds the same wells the grid was
        # refined around.
        wellCoords = dict()
        outletFile = getattr(self._gv, 'outletFile', '')
        if outletFile and os.path.isfile(outletFile):
            layer = QgsVectorLayer(outletFile, 'tmp', 'ogr')
            if layer.isValid():
                resIdx = layer.fields().indexOf(QSWATTopology._RES)
                inletIdx = layer.fields().indexOf(QSWATTopology._INLET)
                ptsourceIdx = layer.fields().indexOf(QSWATTopology._PTSOURCE)
                ptIdIdx = layer.fields().indexOf(QSWATTopology._POINTID);
                if resIdx >= 0 and inletIdx >= 0 and ptsourceIdx >= 0:
                    for feat in layer.getFeatures():
                        if (feat[inletIdx] == 0
                                and feat[resIdx] == QSWATTopology._WELLTYPE
                                and feat[ptsourceIdx] == 0):
                            geom = feat.geometry()
                            if geom and not geom.isEmpty():
                                ptId = int(feat[ptIdIdx])
                                wellCoords[ptId] = geom.asPoint()
        if not wellCoords:
            return

        # Find nearest cell for each well
        sql = 'INSERT OR IGNORE INTO obs_gw (cell_id, name) VALUES (?, ?)'
        for i, wellPt in wellCoords.items():
            wellGeom = QgsGeometry.fromPointXY(wellPt)
            bestCellId = None
            bestDist = float('inf')
            for cellFeat in gridLayer.getFeatures():
                cellGeom = cellFeat.geometry()
                dist = wellGeom.distance(cellGeom)
                if dist < bestDist:
                    bestDist = dist
                    bestCellId = cellFeat['cell_id']
            if bestCellId is not None:
                conn.execute(sql, (bestCellId, 'well_{0}'.format(i)))

    # Helpers

    @staticmethod
    def _sampleRaster(band, transform, x, y):
        """Sample a single raster value at (x, y). Returns None on failure."""
        if band is None or transform is None:
            return None
        col = int((x - transform[0]) / transform[1])
        row = int((y - transform[3]) / transform[5])
        if 0 <= col < band.XSize and 0 <= row < band.YSize:
            try:
                val = band.ReadAsArray(col, row, 1, 1)
                if val is not None:
                    return float(val[0, 0])
            except Exception:
                pass
        return None

    @staticmethod
    def _cellMeanRaster(band, transform, geom):
        """Mean of valid raster pixels over a cell's footprint (its bounding-box
        window), ignoring nodata. For axis-aligned grid cells the window is the
        cell, so this is the per-cell mean. Returns None if no valid pixels."""
        if band is None or transform is None:
            return None
        px, py = transform[1], transform[5]
        if px == 0 or py == 0:
            return None
        bb = geom.boundingBox()
        c0 = int((bb.xMinimum() - transform[0]) / px)
        c1 = int((bb.xMaximum() - transform[0]) / px)
        r0 = int((bb.yMaximum() - transform[3]) / py)
        r1 = int((bb.yMinimum() - transform[3]) / py)
        col0, col1 = max(0, min(c0, c1)), min(band.XSize - 1, max(c0, c1))
        row0, row1 = max(0, min(r0, r1)), min(band.YSize - 1, max(r0, r1))
        if col1 < col0 or row1 < row0:
            return None
        try:
            arr = band.ReadAsArray(col0, row0, col1 - col0 + 1, row1 - row0 + 1)
        except Exception:
            return None
        if arr is None:
            return None
        a = np.asarray(arr, dtype=float)
        mask = np.isfinite(a) & (a > -9000)
        nodata = band.GetNoDataValue()
        if nodata is not None:
            mask &= (a != nodata)
        if not mask.any():
            return None
        return float(a[mask].mean())

    def _loadPermZones(self):
        """Load permeability shapefile geometries with zone IDs."""
        permFile = self._dialog.aquiferPermeability.text()
        if not permFile or not os.path.isfile(permFile):
            return []
        layer = QgsVectorLayer(permFile, 'perm', 'ogr')
        if not layer.isValid():
            return []
        zones = []
        zoneId = 0
        for feat in layer.getFeatures():
            zoneId += 1
            zones.append((zoneId, feat.geometry()))
        return zones

    @staticmethod
    def _findZone(permZones, point):
        """Find which permeability zone contains a point. Returns zone_id or 1."""
        if not permZones:
            return 1
        ptGeom = QgsGeometry.fromPointXY(point)
        for zoneId, geom in permZones:
            if geom.contains(ptGeom):
                return zoneId
        return 1

    def _getWatershedBoundaryLine(self):
        """Get the watershed outer boundary as a line geometry for distance checks."""
        for attr in ('wshedFile', 'subbasinsFile'):
            f = getattr(self._gv, attr, '')
            if f and os.path.isfile(f):
                layer = QgsVectorLayer(f, 'tmp', 'ogr')
                if layer.isValid():
                    combined = None
                    for feat in layer.getFeatures():
                        g = feat.geometry()
                        if g and not g.isEmpty():
                            combined = g if combined is None else combined.combine(g)
                    if combined is not None:
                        return QgsGeometry(combined.constGet().boundary())
        return None
