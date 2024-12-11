# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QSWATPlus
                                 A QGIS plugin
 Create SWATPlus inputs
                              -------------------
        begin                : 2014-07-18
        copyright            : (C) 2023 by Chris George
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

Acknowledgements: based on SWAT+GW_INPUT_CREATION.py written by Ryan Bailey and Estafinos Addisu Yimer
 
"""

# Import the PyQt and QGIS libraries
from PyQt5 import QtCore, QtWidgets # @UnusedImport
from PyQt5.QtCore import Qt, QSettings # @UnresolvedImport
from PyQt5.QtWidgets import QFileDialog, QDialog # @UnresolvedImport

from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer, QgsProcessingContext,  QgsFeatureRequest 

from osgeo import gdal, ogr, osr
from shapely import geometry
import pandas as pd
import numpy as np
import math
from datetime import datetime
import os
import shutil
import re
import processing
import subprocess
from osgeo._gdalconst import GA_ReadOnly
import configparser
try:
    import geopandas as gpd # @UnresolvedImport
    # import matplotlib.pyplot as plt
    # from matplotlib_scalebar.scalebar import ScaleBar # @UnresolvedImport
    # import matplotlib.patches as mpatches
    # from functools import reduce
except:
    pass

# cwg don't use: prefer actual locations
# root_dir = os.path.dirname(os.path.abspath(__file__))


from .globals import GlobalVars
from .gwflowdialog import gwflowDialog
from .QSWATUtils import QSWATUtils, FileTypes
from .QSWATTopology import QSWATTopology
from .parameters import Parameters
from numpy.ma.core import _get_dtype_of
from osgeo.gdalconst import GA_Update
from . import rtree

class GWFlow():

    def __init__(self, gv: GlobalVars, progress):
        self._gv = gv
        self.progress = progress
        self.gwflowDir = os.path.join(gv.projDir, 'gwflow')
        os.makedirs(self.gwflowDir, exist_ok = True)
        self.inputFiles = os.path.join(self.gwflowDir, 'input_files')
        os.makedirs(self.inputFiles, exist_ok = True)
        self.supplementary = os.path.join(self.gwflowDir, 'supplementary')
        os.makedirs(self.supplementary, exist_ok = True)
        self.grids = os.path.join(self.gwflowDir, 'grids')
        os.makedirs(self.grids, exist_ok = True)
        self.TxtInOut_gwflow = os.path.join(self.gwflowDir, 'TxtInOut_gwflow')
        os.makedirs(self.TxtInOut_gwflow, exist_ok = True)
        self._dlg = gwflowDialog()
        self._dlg.setWindowFlags(self._dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._dlg.aquiferPermeabilityButton.clicked.connect(self.getPermeabilityFile)
        self._dlg.aquiferThicknessButton.clicked.connect(self.getThicknessFile)
        self._dlg.initializationButton.clicked.connect(self.getInitializationFile)
        self._dlg.useObservationLocations.stateChanged.connect(self.setObservation)
        self._dlg.useTileDrains.stateChanged.connect(self.setTileDrains)
        self._dlg.setOutputTimes.stateChanged.connect(self.setOutputTimes)
        self._dlg.useUnstructured.stateChanged.connect(self.setUnstructured)
        self._dlg.observationLocationsButton.clicked.connect(self.getObservationFile)
        self._dlg.tileDrainsButton.clicked.connect(self.getTileDrainsFile)
        self._dlg.outputTimesButton.clicked.connect(self.getOutputTimesFile)
        self._dlg.buttonBox.accepted.connect(self.checkFiles)
        self._dlg.buttonBox.rejected.connect(self._dlg.close)
        # alignGrids only visible if grid model, and defaults to checked
        self._dlg.alignGrids.setVisible(gv.useGridModel)
        self._dlg.alignGrids.setChecked(gv.useGridModel)
        # for now unstructured option is not available
        self.hideUnstructured()
        ## function defined later (in fishnet) to convert (x, y) pair to (row, column) in grid
        self.coordToCell = None
        # February 2024 no longer a special executable SWAT+gwflow.exe
        # # store SWAT+ executable, years_example.xlsx and default initialization file
        # SWATExecutable = os.path.join(self.gwflowDir, 'SWAT+gwflow.exe')
        # if not os.path.isfile(SWATExecutable):
        #     shutil.copy(os.path.join(self._gv.SWATPlusDir, 'gwflow/SWAT+gwflow.exe'), self.gwflowDir)
        # excelFile = os.path.join(self.gwflowDir, 'years_example.xlsx')
        # if not os.path.isfile(excelFile):
        #     shutil.copy(os.path.join(self._gv.SWATPlusDir, 'gwflow/years_example.xlsx'), self.gwflowDir)
        if not os.path.isfile(os.path.join(self.gwflowDir, 'gwflow.ini')):
            shutil.copy(os.path.join(Parameters._GWFLOWDIR, 'gwflow.ini'), self.gwflowDir)
        iniFile = os.path.join(gv.defaultDir, 'gwflow.ini')
        if not os.path.isfile(iniFile):
            shutil.copy(os.path.join(self.gwflowDir, 'gwflow.ini'), gv.defaultDir)
        self._dlg.initialization.setText(iniFile)
        ## optional observation locations file
        self.obs_file = ''
        ## optional tile drains file
        self.tiles_file = ''
        self.readProj()
        
    def getPermeabilityFile(self):
        settings = QSettings()
        if settings.contains('/QSWATPlus/LastInputPath'):
            path = str(settings.value('/QSWATPlus/LastInputPath'))
        else:
            path = ''
        filtr = FileTypes.filter(FileTypes._PERMEABILITY)
        permFile, _ = QFileDialog.getOpenFileName(None, 'Select permeability shapefile', path, filtr)
        if os.path.isfile(permFile):
            settings.setValue('/QSWATPlus/LastInputPath', os.path.dirname(str(permFile)))
            self._dlg.aquiferPermeability.setText(permFile)
            
    def getThicknessFile(self):
        settings = QSettings()
        if settings.contains('/QSWATPlus/LastInputPath'):
            path = str(settings.value('/QSWATPlus/LastInputPath'))
        else:
            path = ''
        filtr = FileTypes.filter(FileTypes._AQUIFERTHICKNESS)
        thicknessFile, _ = QFileDialog.getOpenFileName(None, 'Select aquifer thickness raster', path, filtr)
        if os.path.isfile(thicknessFile):
            settings.setValue('/QSWATPlus/LastInputPath', os.path.dirname(str(thicknessFile)))
            self._dlg.aquiferThickness.setText(thicknessFile)
            
    def getInitializationFile(self):
        settings = QSettings()
        if settings.contains('/QSWATPlus/LastInputPath'):
            path = str(settings.value('/QSWATPlus/LastInputPath'))
        else:
            path = ''
        filtr = FileTypes.filter(FileTypes._INITIALIZATION)
        initFile, _ = QFileDialog.getOpenFileName(None, 'Select gwflow initialization file', path, filtr)
        if os.path.isfile(initFile):
            settings.setValue('/QSWATPlus/LastInputPath', os.path.dirname(str(initFile)))
            self._dlg.initialization.setText(initFile)
            
    def getObservationFile(self):
        settings = QSettings()
        if settings.contains('/QSWATPlus/LastInputPath'):
            path = str(settings.value('/QSWATPlus/LastInputPath'))
        else:
            path = ''
        filtr = FileTypes.filter(FileTypes._OBSERVATIONLOCATIONS)
        obsFile, _ = QFileDialog.getOpenFileName(None, 'Select observation locations shapefile', path, filtr)
        if os.path.isfile(obsFile):
            settings.setValue('/QSWATPlus/LastInputPath', os.path.dirname(str(obsFile)))
            self._dlg.observationLocations.setText(obsFile)
            
    def getTileDrainsFile(self):
        settings = QSettings()
        if settings.contains('/QSWATPlus/LastInputPath'):
            path = str(settings.value('/QSWATPlus/LastInputPath'))
        else:
            path = ''
        filtr = FileTypes.filter(FileTypes._TILEDRAINS)
        tilesFile, _ = QFileDialog.getOpenFileName(None, 'Select tile drainss shapefile', path, filtr)
        if os.path.isfile(tilesFile):
            settings.setValue('/QSWATPlus/LastInputPath', os.path.dirname(str(tilesFile)))
            self._dlg.tileDrains.setText(tilesFile)
            
    def getOutputTimesFile(self):
        settings = QSettings()
        if settings.contains('/QSWATPlus/LastInputPath'):
            path = str(settings.value('/QSWATPlus/LastInputPath'))
        else:
            path = ''
        filtr = FileTypes.filter(FileTypes._OUTPUTTIMES)
        timesFile, _ = QFileDialog.getOpenFileName(None, 'Select output times file', path, filtr)
        if os.path.isfile(timesFile):
            settings.setValue('/QSWATPlus/LastInputPath', os.path.dirname(str(timesFile)))
            self._dlg.outputTimes.setText(timesFile)
            
    def checkFiles(self):
        if not os.path.isfile(self._dlg.aquiferThickness.text()):
            QSWATUtils.information('Please select an aquifer thickness raster', self._gv.isBatch)
            return 
        if not os.path.isfile(self._dlg.aquiferPermeability.text()):
            QSWATUtils.information('Please select a permeability shapefile', self._gv.isBatch)
            return 
        if not os.path.isfile(self._dlg.initialization.text()):
            QSWATUtils.information('Please select a gwflow initialization file', self._gv.isBatch)
            return 
        if self._dlg.useObservationLocations.isChecked() and not os.path.isfile(self._dlg.observationLocations.text()):
            QSWATUtils.information('Please select an observation locations shapefile', self._gv.isBatch)
            return
        if self._dlg.useTileDrains.isChecked() and not os.path.isfile(self._dlg.tileDrains.text()):
            QSWATUtils.information('Please select a tile drains shapefile', self._gv.isBatch)
            return
        if self._dlg.setOutputTimes.isChecked() and not os.path.isfile(self._dlg.outputTimes.text()):
            QSWATUtils.information('Please select an output times file', self._gv.isBatch)
            return
        self._dlg.close()
        
    def hideUnstructured(self):
        """Remove option to use unstructured grids"""
        self._dlg.useUnstructured.setVisible(False)
        self._dlg.refinementLabel.setVisible(False)
        self._dlg.refinementLevel.setVisible(False)
        
    def setUnstructured(self):
        self._dlg.refinementLabel.setEnabled(self._dlg.useUnstructured.isChecked())
        self._dlg.refinementLevel.setEnabled(self._dlg.useUnstructured.isChecked())
        
    def setObservation(self):
        self._dlg.observationLocations.setEnabled(self._dlg.useObservationLocations.isChecked())
        self._dlg.observationLocationsButton.setEnabled(self._dlg.useObservationLocations.isChecked())
        
    def setTileDrains(self):
        self._dlg.tileDrains.setEnabled(self._dlg.useTileDrains.isChecked())
        self._dlg.tileDrainsButton.setEnabled(self._dlg.useTileDrains.isChecked())
        
    def setOutputTimes(self):
        self._dlg.outputTimes.setEnabled(self._dlg.setOutputTimes.isChecked())
        self._dlg.outputTimesButton.setEnabled(self._dlg.setOutputTimes.isChecked())
              
    def run(self):
        res = self._dlg.exec_()
        if res ==  QDialog.Rejected:
            return False
        self.saveProj()
        if self._dlg.useUnstructured.isChecked():
            os.makedirs(os.path.join(self.gwflowDir, 'output_usgdata'), exist_ok = True)
            os.makedirs(os.path.join(self.gwflowDir, 'output_shapefiles'), exist_ok = True)
            shutil.copy(os.path.join(Parameters._GWFLOWDIR, 'runGridGen.bat'), self.gwflowDir)
            shutil.copy(os.path.join(Parameters._GWFLOWDIR, 'clean.bat'), self.gwflowDir)
            shutil.copy(os.path.join(Parameters._GWFLOWDIR, 'action01_buildqtg.template'), self.gwflowDir)
            shutil.copy(os.path.join(Parameters._GWFLOWDIR, 'action02_writeusgdata.dfn'), self.gwflowDir)
            shutil.copy(os.path.join(Parameters._GWFLOWDIR, 'action03_shapefile.dfn'), self.gwflowDir)
        thick_file_dir = os.path.dirname(self._dlg.aquiferThickness.text())
        if not QSWATUtils.samePath(thick_file_dir, self.gwflowDir):
            shutil.copy(self._dlg.aquiferThickness.text(), self.gwflowDir)
            self._dlg.aquiferThickness.setText(os.path.join(self.gwflowDir, os.path.basename(self._dlg.aquiferThickness.text())))
        self.thick_file_local = self._dlg.aquiferThickness.text()
        conductivity_dir = os.path.dirname(self._dlg.aquiferPermeability.text())
        if not QSWATUtils.samePath(conductivity_dir, self.gwflowDir):
            QSWATUtils.copyShapefile(self._dlg.aquiferPermeability.text(), 'permeability', self.gwflowDir)
            self._dlg.aquiferPermeability.setText(os.path.join(self.gwflowDir, 'permeability.shp'))
        self.conductivity_file = self._dlg.aquiferPermeability.text()
        if self._dlg.useObservationLocations.isChecked():
            obs_dir = os.path.dirname(self._dlg.observationLocations.text())
            if not QSWATUtils.samePath(obs_dir, self.gwflowDir):
                QSWATUtils.copyShapefile(self._dlg.observationLocations.text(), 'observationLocationss', self.gwflowDir)
                self._dlg.observationLocations.setText(os.path.join(self.gwflowDir, 'observationLocationss.shp'))
            self.obs_file = self._dlg.observationLocations.text()
        else:
            self.obs_file = ''
        if self._dlg.useTileDrains.isChecked():
            drains_dir = os.path.dirname(self._dlg.tileDrains.text())
            if not QSWATUtils.samePath(drains_dir, self.gwflowDir):
                QSWATUtils.copyShapefile(self._dlg.tileDrains.text(), 'tileDrains', self.gwflowDir)
                self._dlg.tileDrains.setText(os.path.join(self.gwflowDir, 'tileDrains.shp'))
            self.tiles_file = self._dlg.tileDrains.text()
        else:
            self.tiles_file = ''
        init_dir = os.path.dirname(self._dlg.initialization.text())
        if not QSWATUtils.samePath(init_dir, self.gwflowDir):
            shutil.copy(self._dlg.initialization.text(), self.gwflowDir)
            self._dlg.initialization.setText(os.path.join(self.gwflowDir, os.path.basename(self._dlg.initialization.text())))
        if self._dlg.setOutputTimes.isChecked():
            times_dir = os.path.dirname(self._dlg.outputTimes.text())
            if not QSWATUtils.samePath(times_dir, self.gwflowDir):
                shutil.copy(self._dlg.outputTimes.text(), self.gwflowDir)
                self._dlg.outputTimes.setText(os.path.join(self.gwflowDir, os.path.basename(self._dlg.outputTimes.text())))
            self.times_file = self._dlg.outputTimes.text()
        else:
            self.times_file = ''
        
        #%% Initial values for SWATgwflow module
        # Initial values
        config = configparser.ConfigParser()
        configFile = self._dlg.initialization.text()
        config.read(configFile)
        default = config['DEFAULT']
        self.cell_size = default.getint('cell_size', 200) #Grid cell size (units depending on projection)
        self.Boundary_conditions = default.getint('Boundary_conditions', 1) #Boundary conditions (1 = constant head; 2 = no flow)
        self.HRUorLSU_recharge = default.getint('HRUorLSU_recharge', 2) #Recharge connection type (HRU-cell = 1, LSU-cell = 2, both = 3)
        self.HRU_recharge = self.HRUorLSU_recharge == 1 or self.HRUorLSU_recharge == 3
        self.LSU_recharge = self.HRUorLSU_recharge >= 2
        self.GW_soiltransfer = default.getint('GW_soiltransfer', 1) #Groundwater --> soil transfer is simulated (0 = n; 1 = yes)
        self.Saturation_excess = default.getint('Saturation_excess', 1) #Saturation excess flow is simulated (0 = no; 1 = yes)
        self.ext_pumping = default.getint('ext_pumping', 0) #external groundwater pumping (0=off; 1=on)
        self.reservoir_exchange = default.getint('reservoir_exchange', 1) # Groundwater-reservoir exchange (0=off; 1=on)
        self.wetland_exchange = default.getint('wetland_exchange', 1) # Groundwater-wetland exchange (0=off; 1=on)
        self.floodplain_exchange = default.getint('floodplain_exchange', 1) # Groundwater-floodplain exchange (0=off; 1=on)
        self.canal_seepage = default.getint('canal_seepage', 0) # Canal seepage to groundwater (0=off; 1=on)
        self.solute_transport = default.getint('solute_transport', 1) # Groundwater solute transport (0=off; 1=on)
        self.transport_steps = default.getint('transport_steps', 1) #Number of transport time steps per flow time step
        self.disp_coef = default.getfloat('disp_coef', 5.00) #Dispersion coefficient (m2/day)
        self.recharge_delay = default.getfloat('recharge_delay', 0.0) #Recharge delay (days) between soil profile and water table
        self.EXDP = default.getfloat('EXDP', 1.00) #Groundwater ET extinction depth (m)
        self.WT_depth = default.getfloat('WT_depth', 5) #Water table depth (m) at start of simulation
        self.river_depth = default.getfloat('river_depth', 5.0) #Vertical distance (m) of streambed below the DEM value
        self.tile_depth = default.getfloat('tile_depth', 1.22) #Depth (m) of tiles below ground surface
        self.tile_area = default.getfloat('tile_area', 50) #Area (m2) of groundwater inflow (circumference*length) * flow length
        self.tile_k = default.getfloat('tile_k', 5.0) #Hydraulic conductivity (m/day) of the drain perimeter
        self.tile_groups = default.getint('tile_groups', 1) #Tile cell groups (flag: 0 = no; 1 = yes)
        self.resbed_thickness = default.getfloat('resbed_thickness', 2) # Reservoir bed thickness (m)
        self.resbed_k = default.getfloat('resbed_k', 9.99E-06) # Reservoir bed conductivity
        self.wet_thickness = default.getfloat('wet_thickness', 0.25) # Wetland bottom material thickness (m)
        self.daily_output = default.getint('daily_output', 1) # Daily write flag
        self.annual_output  = default.getint('annual_output ', 1) # Annual write flag
        self.aa_output  = default.getint('aa_output ', 1) # Average annual write flag
        self.row_det = default.getint('row_det', 0) #Cell row for detailed sources/sink output (zero means not used)
        self.col_det = default.getint('col_det', 0) #Cell column for detailed sources/sink output (zero means not used)
        self.timestep_balance = default.getfloat('timestep_balance', 1) #Time step (days) to solve groundwater balance equation
        self.init_sy = default.getfloat('init_sy', 0.2) #Initial specific yield 'Sy'
        self.init_n = default.getfloat('init_n', 0.25) #Initial porosity 'n'
        self.streambed_k = default.getfloat('streambed_k', 0.005) #Streambed hydraulic conductivity (m/day)
        self.streambed_thickness = default.getfloat('streambed_thickness', 0.5) #Streambed thickness (m)
        self.init_NO3 = default.getfloat('init_NO3', 3.0) #Initial NO3 concentration
        self.init_P = default.getfloat('init_P', 0.05) #Initial P concentration
        self.tile_groups_number = default.getint('tile_groups_number', 1) #Number of tile cell groups
        self.denit_constant = default.getfloat('denit_constant', -0.0001) #First-order rate constant for denitrification (1/day)
        self.nit_sorp = default.getfloat('nit_sorp', 1.00) #Sorption retardation coefficient for Nitrate
        self.pho_sorp = default.getfloat('pho_sorp', 2.00) #Sorption retardation coefficient for Phosphorus
        self.Tiledrain_flow_sim = 1 if self._dlg.useTileDrains.isChecked() else 0 #Tile drain flow is simulated (0 = no; 1 = yes)
        
        #%% EPSG code and file names
    
        # Define projection code. Must be written as string EPSG:CODE
        EPSG = self._gv.crsProject.authid()  # 'EPSG:31370'
        
        #SWAT+ original folder (TxtInOut by default)
        swat_folder = self._gv.txtInOutDir 
        
        # GIS Filenames (Basin shapefile, global rasters, etc)
        # Filename and directory of basin shapefile
        basin_file = 'subs.shp'
        # Raster file of aquifer thickness GLOBAL 
        # thick_raster_file = 'aquifer_thickness_cm.tif'
        # cwg local thickness was shapefile, now raster
        # Raster of aquifer thickness LOCAL, if not used, leave equal to 0 
        # thick_file_local = 0
        thickness_attribute_name = 'Avg_Thick' #Specify the attribute name for thickness in the shapefile
        # DEM raster filename
        # dem_raster = 'Demer_filled_DEM.tif'
        # Conductivity GeoDataBase filename
        # conductivity_file = 'GLHYMPS.shp'
        #River network shapefile filename
        river_filename = 'rivs.shp'
        # HRU shapefile filename
        hrus_filename = 'hrus1.shp'  # full HRUs shapefile
        lsus_filename = 'lsus.shp'
        #Excel simulation years file
        #years_file = os.path.join(self.gwflowDir, 'years_example.xlsx')
        # Observation locations shapefile filename - If not existent, leave as empty string
        obs_file = ''
        # Tile cell locations shapefile filename and attribute name if tile groups exist - If not existent, leave as empty string
        tiles_file = ''
        tile_group_att = 'group'
        
        #FILENAMES FROM SWAT+OUTPUT 
        #file.cio from original SWAT+folder
        filename_cio = swat_folder+'/file.cio'
        #rout_unit.con original SWAT+folder
        filename_routunit = swat_folder+'/rout_unit.con'
        #object.cnt from original SWAT+folder
        filename_objectcnt = swat_folder+'/object.cnt'
        
        
        
        #%% Look for files and copy SWAT files to new gwflow folder
        
        QSWATUtils.loginfo('...Looking for your files...')
        basin_file = os.path.join(self._gv.resultsDir, basin_file) # look_file(basin_file)
        # thick_raster_file = self.look_file(thick_raster_file)
        thick_file_local = self.thick_file_local # self.look_file(thick_file_local)
        dem_raster = self._gv.demFile # look_file(dem_raster)
        conductivity_file = self.conductivity_file # self.look_file(conductivity_file)
        river_filename = os.path.join(self._gv.resultsDir, river_filename) # look_file(river_filename)
        hrus_filename = os.path.join(self._gv.shapesDir, hrus_filename) # look_file(hrus_filename)
        if self.HRU_recharge and not os.path.isfile(hrus_filename):
            QSWATUtils.error('There is no full HRUs shapefile.  HRU recharge will not be used.  LSU recharge will be used.', self._gv.isBatch)
            self.HRU_recharge = False
            self.LSU_recharge = True
        lsus_filename = os.path.join(self._gv.resultsDir, lsus_filename) 
        #years_file = os.path.join(self.gwflowDir, years_file) # self.look_file(years_file)
        obs_file = self.obs_file # self.look_file(obs_file)
        tiles_file = self.tiles_file # self.look_file(tiles_file)
        
        #Copying contents on swat folder to a new folder for gwflow
        src = swat_folder
        trg = self.TxtInOut_gwflow # 'TxtInOut_gwflow'
         
        files = os.listdir(src)
         
        # iterating over all the files in
        # the source directory
        for fname in files:
             
            # copying the files to the
            # destination directory
            nxtFile = os.path.join(src, fname)
            if os.path.isfile(nxtFile):
                shutil.copy2(nxtFile, trg)
            
        if self._dlg.useUnstructured.isChecked():
            try:
                subprocess.run('clean.bat',
                                  cwd=self.gwflowDir, 
                                  shell=True, 
                                  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.PIPE,
                                  universal_newlines=True,    # text=True) only in python 3.7 
                                  check=True)
            except subprocess.CalledProcessError as ex:
                QSWATUtils.error('GridGen clean failed: ' + ex.output, self._gv.isBatch)
            self.createBuildDfn()
            self.createBoundary()
            rows, cols = self.createDatFiles(EPSG)
            try:
                subprocess.run('runGridGen.bat',
                                  cwd=self.gwflowDir, 
                                  shell=True, 
                                  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.PIPE,
                                  universal_newlines=True,    # text=True) only in python 3.7 
                                  check=True)
            except subprocess.CalledProcessError as ex:
                QSWATUtils.error('GridGen failed: ' + ex.stderr, self._gv.isBatch)
            # bat files creates two shapefiles in gwflow/output_shapefiles that need .prj files
            QSWATUtils.copyPrj(self._gv.demFile, os.path.join(self.gwflowDir, 'output_shapefiles/grid02qtg_pts.shp'))
            QSWATUtils.copyPrj(self._gv.demFile, os.path.join(self.gwflowDir, 'output_shapefiles/grid02qtg.shp'))
        
        #%%Executing GIS rotuines to generate necessary information
        #GRID CREATION AND OTHER GIS ROUTINES
        # Next function is to create grid1 as a GeoDataFrame, must be used like this:
        '''fishnet(basin_file, square size in corresponding units to the working projection, grid1 filename (.shp extension)'''
        basin_gdf, grid1_gdf, rows, cols = self.fishnet(basin_file, self.cell_size, os.path.join(self.grids, 'grid1.shp'), EPSG)
        
        # Next function is to create grid2 as a GeoDataFrame, must be used like this:
        '''activecells(Basin GeoDataFrame, Grid1 GeoDataFrame, grid2 filename) '''
        grid2_gdf = self.activecells(basin_gdf, grid1_gdf, os.path.join(self.grids, 'grid2.shp'))
        
        # Next functions are to get Grid 3, whether with global raster file or local shapefile
        # if type(thick_file_local) != type(None):
        #     grid3_gdf = self.aquif_thickness_local(thick_file_local, thickness_attribute_name, grid2_gdf, 'grids/grid3.shp')
        # else:  
        #     '''aquif_thickness(thickness raster file, Grid2 GeoDataFrame, grid3 filename, EPSG) '''
        #     grid3_gdf = self.aquif_thickness(thick_raster_file, grid2_gdf, 'grids/grid3.shp', EPSG)
        grid3_gdf = self.aquif_thickness(thick_file_local, grid2_gdf, os.path.join(self.grids, 'grid3.shp'), EPSG)
        
        # Next function is to get grid 4 as a GeoDataFrame, must be used like this:
        '''aquif_elevation(dem_raster filename, grid3 GeoDataFrame, grid4 filename) '''
        grid4_gdf = self.aquif_elevation(dem_raster, grid3_gdf, os.path.join(self.grids, 'grid4.shp'), EPSG, self.cell_size)
        
        # Next function is to get grid 5 as a GeoDataFrame and the zones with corresponding K values as a data frame
        # must be used like this:
        '''aquif_conductivity(conductivity database filename, grid4 GeoDataFrame, Basin Geodata Frame, grid5 filename, EPSG code) '''
        grid5_gdf, K_gdf_zones = self.aquif_conductivity(conductivity_file, grid4_gdf, basin_gdf, os.path.join(self.grids, 'grid5.shp'), EPSG)
        
        # Boundary Cell Information
        start = datetime.now()
        QSWATUtils.loginfo('..Detecting boundary cells...')
        self.progress('Detecting boundary cells')
        borders_gdf = gpd.read_file(os.path.join(self.supplementary, 'only_basin_boundary.shp'))
        borders_gdf['geometry'] = borders_gdf.boundary #Getting the geometry of only the boundaries of the catchment
        borders_gdf['boundary'] = 1 
        grid6_gdf = gpd.sjoin(grid5_gdf, borders_gdf, how = 'left') #Spatial join between grid5 and the boundaries shapefile to assign 1 as boundary attribute value to the cells that intersect it
        end = datetime.now()
        QSWATUtils.loginfo('That took '+str(end-start))
        
        # GRID 6 CLEAN UP
        #Necessary clean up to replace nan values to 0, and deleting index_right to avoid warnings of attribute name truncation
        grid6_gdf['boundary'] = grid6_gdf['boundary'].fillna(0)
        grid6_gdf['Avg_Thick'] = grid6_gdf['Avg_Thick'].fillna(0)
        grid6_gdf['Avg_elevat'] = grid6_gdf['Avg_elevat'].fillna(0)
        del grid6_gdf['index_right']
        
        
        # Tile Drain Cell Information and tile groups
        start = datetime.now()
        QSWATUtils.loginfo('..Detecting tile drain cells...')
        grid6_gdf['tile_cell'] = 0 #Assign value of 0 to tile_cell attribute
        if self.Tiledrain_flow_sim == 1:
            self.progress('Detecting tile drain cells')
            try:
                tiles_gdf = gpd.read_file(tiles_file)
                tiles_gdf['tile_cell'] = 1
                grid6_gdf = gpd.sjoin(grid6_gdf, tiles_gdf, how = 'left') #Spatial join to get the cells that intersect the tile drains
                grid6_gdf['tile_cell'] = grid6_gdf['tile_cell_right'] #Tile cell right will be equal to 1 when it intersects, this copies that value to tile_cell for it to be 1
                grid6_gdf['tile_cell'] = grid6_gdf['tile_cell'].fillna(0) #All the rest of tile_cell right now are nan, they will become 0        del grid6_gdf['tile_cell_right']
                del grid6_gdf['tile_cell_left'] #Delete this columns as they are not necessary and generate warnings of name truncation
                del grid6_gdf['index_right']
                del grid6_gdf['tile_cell_right']
            except:
                QSWATUtils.loginfo('No tile drain cells provided') #If the file is not provided it reminds the user 
        end = datetime.now()
        QSWATUtils.loginfo('That took '+str(end-start))         
        
        grid6_gdf.to_file(os.path.join(self.grids, 'grid6.shp')) #Save grid 6 as shapefile
        
        # River cell information
        start = datetime.now()
        QSWATUtils.loginfo('..Getting river cells...')
        self.progress('Getting river cells')
        rivers_gdf = gpd.read_file(river_filename)
        river_cell_gdf = gpd.overlay(rivers_gdf, grid6_gdf, keep_geom_type = True) #Intersection of cells with rivers (the resultant geometry is cells (polygons))
        
        #rivers_intersection = gpd.overlay(river_cell_gdf, rivers_gdf, keep_geom_type = True) #Intersection of rivers with cells (the resultant geometry is the rivers cut in segments (polylines))
        river_cell_gdf['riv_length'] = river_cell_gdf['geometry'].length #Calculate the geometry of each segment and assign it to each corresponding cell
        
        river_cell_gdf.to_file(os.path.join(self.grids, 'cell_channel_inter.shp')) #Save shapefile of cells that intersect with rivers
        end = datetime.now()
        QSWATUtils.loginfo('That took '+str(end-start))
        
        # LSU connection 
        start = datetime.now()
        QSWATUtils.loginfo('..Generating LSU intersection file...')
        self.progress('Generating LSU intersection file')
        lsus_gdf = gpd.read_file(lsus_filename) 
        lsus_gdf['Area'] = lsus_gdf['geometry'].area
        lsu_intersection = gpd.overlay(lsus_gdf, grid6_gdf, keep_geom_type = True) #Intersection of LSUS with cells (resultant geometry is polygons of LSUS)
        lsu_intersection['Poly_area'] = lsu_intersection['geometry'].area #Calculate the area of each resulting polygon
        lsu_intersection.to_file(os.path.join(self.grids, 'lsus_inter.shp')) #Save to shapefile
        end = datetime.now()
        QSWATUtils.loginfo('That took '+str(end-start))
        
        # lake connection
        if os.path.isfile(self._gv.lakeFile):
            start = datetime.now()
            QSWATUtils.loginfo('..Generating lake intersection file...')
            self.progress('Generating lake intersection file')
            lakes_gdf = gpd.read_file(self._gv.lakeFile) 
            lake_intersection = gpd.overlay(lakes_gdf, grid6_gdf, keep_geom_type = True) #Intersection of lakes with cells (resultant geometry is polygons of HRUS)
            lake_intersection.to_file(os.path.join(self.grids, 'lakes_inter.shp')) #Save to shapefile
            end = datetime.now()
            QSWATUtils.loginfo('That took '+str(end-start))
            
        # HRU connection
        if self.HRU_recharge:
            start = datetime.now()
            QSWATUtils.loginfo('..Generating HRU intersection file...')
            self.progress('Generating HRU intersection file')
            hrus_gdf = gpd.read_file(hrus_filename) 
            hrus_gdf['Area'] = hrus_gdf['geometry'].area
            hru_intersection = gpd.overlay(hrus_gdf, grid6_gdf, keep_geom_type = True) #Intersection of HRUS with cells (resultant geometry is polygons of HRUS)
            hru_intersection['Poly_area'] = hru_intersection['geometry'].area #Calculate the area of each resulting polygon
            hru_intersection.to_file(os.path.join(self.grids, 'hrus_inter.shp')) #Save to shapefile
            end = datetime.now()
            QSWATUtils.loginfo('That took '+str(end-start)) 
                    
        
        #%%Plotting Maps
        
        # plot_grid = grid6_gdf.copy()
        # plot_grid.replace(0, np.nan, inplace = True) #New auxiliary dataframe to change o to nan values so that they are not plotted
        
        # QSWATUtils.loginfo('...Generating Map Plots...')
        # f, ax = plt.subplots()
        # plot_grid.plot(ax = ax, facecolor = 'none', edgecolor = 'k', linewidth = 0.2, legend = True)
        # basin_gdf.plot(ax = ax, facecolor = 'none', edgecolor = 'r', linewidth = 0.5)
        # red_patch = mpatches.Patch(color = 'red', label = 'Basin boundaries deliniation')
        # ax.legend(handles = [red_patch], bbox_to_anchor = (0.5, -0.150), loc = "center")
        # GWFlow.scale_north(ax)
        # plt.title('Generated Grid for Catchment')
        #
        # f, ax = plt.subplots()
        # plot_grid.plot(ax = ax, column = 'Avg_active')
        # basin_gdf.plot(ax = ax, facecolor = 'none', edgecolor = 'k', linewidth = 0.5)
        # orangered_patch = mpatches.Patch(color = 'purple', label = 'Active cells')
        # ax.legend(handles = [orangered_patch], bbox_to_anchor = (0.5, -0.150), loc = "center")
        # GWFlow.scale_north(ax)
        # plt.title('Active cells')
        #
        # f, ax = plt.subplots()
        # plot_grid.plot(ax = ax, column = 'Avg_Thick', cmap = 'RdYlGn', legend = True, legend_kwds = {'label':"Thickness (m)", 'orientation':"vertical"})
        # basin_gdf.plot(ax = ax, facecolor = 'none', edgecolor = 'k', linewidth = 0.5)
        # GWFlow.scale_north(ax)
        # plt.title('Aquifer Thickness')
        #
        # f, ax = plt.subplots()
        # plot_grid.plot(ax = ax, column = 'zone', legend = True, legend_kwds = {'label':"Conductivity zones", 'orientation':"vertical"})
        # basin_gdf.plot(ax = ax, facecolor = 'none', edgecolor = 'k', linewidth = 0.5)
        # GWFlow.scale_north(ax)
        # plt.title('Aquifer Conductivity Zones')
        #
        # f, ax = plt.subplots()
        # plot_grid.plot(ax = ax, column = 'Avg_elevat', legend = True, legend_kwds = {'label':"Elevation (m)", 'orientation':"vertical"})
        # basin_gdf.plot(ax = ax, facecolor = 'none', edgecolor = 'k', linewidth = 0.5)
        # GWFlow.scale_north(ax)
        # plt.title('Ground Elevation')
        #
        # f, ax = plt.subplots()
        # plot_grid.plot(ax = ax, column = 'boundary', cmap = 'gray')
        # yellow2_patch = mpatches.Patch(color = 'k', label = 'Basin boundaries')
        # ax.legend(handles = [yellow2_patch], bbox_to_anchor = (0.5, -0.150), loc = "center")
        # x, y, arrow_length = 0.07, 0.95, 0.2
        # GWFlow.scale_north(ax)
        # plt.title('Catchment Boundaries')
        #
        # f, ax = plt.subplots()
        # river_cell_gdf.plot(ax = ax, color = 'skyblue')
        # basin_gdf.plot(ax = ax, facecolor = 'none', edgecolor = 'k', linewidth = 0.5)
        # blue_patch = mpatches.Patch(color = 'skyblue', label = 'River cells')
        # ax.legend(handles = [blue_patch], bbox_to_anchor = (0.5, -0.150), loc = "center")
        # GWFlow.scale_north(ax)
        # plt.title('River Cells')
        
        
        with self._gv.db.conn as conn:
            self.progress('Writing gwflow tables')
            self.createTables(conn)
            # basic settings
            sql = 'INSERT INTO gwflow_base VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
            conn.execute(sql, (self.cell_size, rows, cols, self.Boundary_conditions, self.HRUorLSU_recharge,
                               self.GW_soiltransfer, self.Saturation_excess, self.ext_pumping, self.Tiledrain_flow_sim,
                               self.reservoir_exchange, self.wetland_exchange, self.floodplain_exchange,
                               self.canal_seepage, self.solute_transport, self.transport_steps, self.disp_coef, self.recharge_delay, self.EXDP,
                               self.WT_depth, self.river_depth, self.tile_depth, self.tile_area,
                               self.tile_k, self.tile_groups, self.resbed_thickness, self.resbed_k,
                               self.wet_thickness, self.daily_output, self.annual_output, self.aa_output,
                               self.row_det, self.col_det, self.timestep_balance))
            
            # zones
            sql = 'INSERT INTO gwflow_zone VALUES(?,?,?,?,?)'
            for _,row in K_gdf_zones.iterrows():
                conn.execute(sql, (row['zone'], row['K[m/day]'], self.init_sy, self.streambed_k, self.streambed_thickness))
                           
            # grid cells (active cells only)  
            sql = 'INSERT INTO gwflow_grid VALUES(?,?,?,?,?,?,?,?)'
            for _,row in grid6_gdf.iterrows():
                status = row['Avg_active']+row['boundary']
                if status > 0:
                    conn.execute(sql, (row['Id'], status, row['zone'], row['Avg_elevat'], row['Avg_Thick'],
                                       self.EXDP, row['Avg_elevat'] - self.WT_depth, row['tile_cell']))
            
            # output times
            if self._dlg.setOutputTimes.isChecked():
                outputTimesFile = self._dlg.outputTimes.text()
                suffix = os.path.splitext(outputTimesFile)[1]
                if suffix == '.txt':
                    outputTimes_df = pd.read_csv(outputTimesFile, sep=" ")
                elif suffix == '.csv':
                    outputTimes_df = pd.read_csv(outputTimesFile, sep=",")
                else:
                    outputTimes_df = pd.read_excel(outputTimesFile, sheet_name = 'Years')
                np.savetxt(os.path.join(self.supplementary, 'sim_years.txt'), outputTimes_df.to_numpy(), fmt = '%d\t%d')
                sql = 'INSERT INTO gwflow_out_days VALUES(?,?)'
                for _,row in outputTimes_df.iterrows():
                    conn.execute(sql, (int(row[0]), int(row[1])))
            
            # observation locations
            if self.obs_file != '':
                sql = 'INSERT INTO gwflow_obs_locs VALUES(?)'
                obs_gdf = gpd.read_file(self.obs_file)
                obs_cells_gdf = gpd.overlay(obs_gdf, grid6_gdf, keep_geom_type = True)
                for _, row in obs_cells_gdf.iterrows():
                    conn.execute(sql, (row['Id'],))
            
            # chemical transport
            sql = 'INSERT INTO gwflow_solutes (solute_name, sorption, rate_const, canal_irr, init_data, init_conc) VALUES(?,?,?,?,?,?)'
            conn.execute(sql, ('no3-n', self.nit_sorp, self.denit_constant, 3, 'single', self.init_NO3))
            conn.execute(sql, ('p', self.pho_sorp, 0, 0.05, 'single', self.init_P))
            conn.execute(sql, ('so4', 1, 0, 0, 'single', 100))
            conn.execute(sql, ('ca', 1, 0, 0, 'single', 50))
            conn.execute(sql, ('mg', 1, 0, 0, 'single', 30))
            conn.execute(sql, ('na', 1, 0, 0, 'single', 40))
            conn.execute(sql, ('k', 1, 0, 0, 'single', 1))
            conn.execute(sql, ('cl', 1, 0, 0, 'single', 25))
            conn.execute(sql, ('co3', 1, 0, 0, 'single', 1))
            conn.execute(sql, ('hco3', 1, 0, 0, 'single', 80))
            
            # hrucells
            if self.HRU_recharge:
                self.makeHRUData(hru_intersection)
            
            # channels
            sql = 'INSERT INTO gwflow_rivcell VALUES(?,?,?)'
            for _, row in river_cell_gdf.iterrows():
                conn.execute(sql, (row['Id'], row['Channel'], row['riv_length']))
            
            # landscape units and floodplain
            sql1 = 'INSERT INTO gwflow_lsucell VALUES(?,?,?)'
            sql2 = 'INSERT INTO gwflow_fpcell VALUES(?,?,?,?)'
            for _, row in lsu_intersection.iterrows():
                lsuId = int(row['LSUID'])
                cellId = row['Id']
                area = row['Poly_area']
                if self.LSU_recharge:
                    conn.execute(sql1, (cellId, lsuId, area))
                if lsuId % 2 == 1: # floodplain lsu
                    channel = lsuId // 10
                    conn.execute(sql2, (cellId, channel, area, 0))
            
            # reservoirs
            sql = 'INSERT INTO gwflow_rescell VALUES(?,?,?)'
            # we consider reservoirs and ponds as reservoirs
            # these are cells having a connection with either lakes or reservoirs
            # 1. Cells having a connection with lakes.  These are (cells intersection lakes)
            # 2. Cells whose lsu has a water body
            if os.path.isfile(self._gv.lakeFile):
                for _,row in lake_intersection.iterrows():
                    lakeId = int(row['LakeId'])
                    lakeData = self._gv.topo.lakesData.get(lakeId, None)
                    if lakeData is None:
                        # no intersection with watershed
                        continue
                    if lakeData.waterRole == QSWATTopology._RESTYPE or lakeData.waterRole == QSWATTopology._PONDTYPE:
                        elev = lakeData.elevation
                        conn.execute(sql, (row['Id'], lakeId, elev))
            for row in conn.execute('SELECT gwflow_lsucell.cell_id, gis_water.id, gis_water.elev FROM gis_water INNER JOIN gwflow_lsucell USING (lsu)'):
                conn.execute(sql, (row[0], row[1], row[2]))
                    
            
        
        #%%Input file creation (gwflow.input / gwflow.rivcells / gwflow.hrucell / gwflow.cellhru)
        #------- Creating gwflow.input file---------------
        # QSWATUtils.loginfo('...Creating gwflow.input file...')
        # gwflow_input = open(os.path.join(self.inputFiles, 'gwflow.input'), "w") # create file
        # gwflow_input.write('INPUT FOR GWFLOW MODULE'+'\n')
        # gwflow_input.write('Basic information'+'\n')
        # gwflow_input.write(str(self.cell_size)+3*'\t'+'Grid cell size (m)'+'\n')
        # gwflow_input.write(str(rows)+' '+str(cols)+3*'\t'+'Number of rows and columns in the grid'+'\n')
        # #gwflow_input.write(str(self.WTI_flag)+3*'\t'+'Water table initiation flag (1 = water table depth is specified'+'\n')
        # gwflow_input.write(str(self.WT_depth)+3*'\t'+'Water table depth (m) at start of simulation'+'\n')
        # gwflow_input.write(str(self.Boundary_conditions)+3*'\t'+'Boundary conditions (1 = constant head; 2 = no flow)'+'\n')
        # gwflow_input.write(str(self.GW_soiltransfer)+3*'\t'+'Groundwater --> soil transfer is simulated (0 = n; 1 = yes)'+'\n')
        # gwflow_input.write(str(self.Saturation_excess)+3*'\t'+'Saturation excess flow is simulated (0 = no; 1 = yes)'+'\n')
        # gwflow_input.write(str(self.ext_pumping)+3*'\t'+'External groundwater pumping (0 = off, 1 = on)'+'\n')
        # gwflow_input.write(str(self.Tiledrain_flow_sim)+3*'\t'+'Tile drain flow is simulated (0 = no; 1 = yes)'+'\n')
        # gwflow_input.write(str(self.HRUorLSU_recharge)+3*'\t'+'Recharge connection type (HRU-cell = 1, LSU-cell = 2)'+'\n')
        # #gwflow_input.write(str(self.GW_nutrient_sim)+3*'\t'+'Groundwater nutrient transport is simulated (0 = no; 1 = yes)'+'\n')
        # gwflow_input.write(str(self.timestep_balance)+3*'\t'+'Time step (days) to solve groundwater balance equation'+'\n')
        # gwflow_input.write('1 1 0'+3*'\t'+'Flags for groundwater and nutrient mass balance files (daily; annual; average annual)'+'\n')
        #
        # self.input_zones(gwflow_input, '\n'+'Aquifer and Streambed Parameter Zones'+'\n'+'Aquifer Hydraulic Conductivity (m/day) Zones', K_gdf_zones, K_gdf_zones['K[m/day]'])
        # self.input_zones(gwflow_input, 'Aquifer Specific Yield Zones', K_gdf_zones, self.init_sy)
        # self.input_zones(gwflow_input, 'Aquifer Porosity Zones', K_gdf_zones, self.init_n)
        # self.input_zones(gwflow_input, 'Streambed Hydraulic Conductivity (m/day) Zones', K_gdf_zones, self.streambed_k)
        # self.input_zones(gwflow_input, 'Streambed Thickness (m) Zones', K_gdf_zones, self.streambed_thickness)
        #
        # # Grid Cell Information
        # gwflow_input.write('\n'+'Grid Cell Information'+'\n')
        # gwflow_input.write('Cell'+'\t'+'status'+'\t'+'top_m'+'\t'+'thick_m'+'\t'+'K_zone'+'\t'+'Sy_zone'+'\t'+'n_zone'+'\t'+'EXDP'+'\t'+'ET_fix'+'\t'+'Tile'+'\t'+'InitN'+'\t'+'InitP')
        # grid_info = pd.DataFrame()
        # grid_info['Cell'] = grid6_gdf['Id']
        # grid_info['status'] = grid6_gdf['Avg_active']+grid6_gdf['boundary']
        # grid_info['top_m'] = grid6_gdf['Avg_elevat']
        # grid_info['thick_m'] = grid6_gdf['Avg_Thick']
        # grid_info['K_zone'] = grid_info['Sy_zone'] = grid_info['n_zone'] = grid6_gdf['zone']
        # grid_info['EXDP'] = self.EXDP
        # grid_info['ET_fix'] = 0  # self.ET_fix
        # grid_info['Tile'] = grid6_gdf['tile_cell']
        # grid_info['InitN'] = self.init_NO3
        # grid_info['InitP'] = self.init_P
        # grid_info = grid_info.to_numpy()
        # fmt = '%d\t%d\t%1.2f\t%1.2f\t%d\t%d\t%d\t%1.2f\t%1.2f\t%d\t%1.2f\t%1.2f'
        # np.savetxt(os.path.join(self.supplementary, 'cellinfo.txt'), grid_info, fmt = fmt)
        # cell_txt = open(os.path.join(self.supplementary, 'cellinfo.txt'), 'r')
        # gwflow_input.write('\n'+cell_txt.read())
        
        # # Times for Groundwater Head Output
        # if self._dlg.setOutputTimes.isChecked():
        #     gwflow_input.write('\n'+'Times for Groundwater Head Output'+'\n')
        #     years_df = pd.read_excel(years_file, sheet_name = 'Years')
        #     gwflow_input.write(str(len(years_df)))
        #     np.savetxt(os.path.join(self.supplementary, 'sim_years.txt'), years_df.to_numpy(), fmt = '%d\t%d')
        #     years_txt = open(os.path.join(self.supplementary, 'sim_years.txt'))
        #     gwflow_input.write('\n'+years_txt.read())
        
        # Groundwater Observation Locations
        
        # if self.obs_file != '':
        #     try:
        #         obs_gdf = gpd.read_file(self.obs_file)
        #         obs_cells_gdf = gpd.overlay(obs_gdf, grid6_gdf, keep_geom_type = True)
        #         obs_cells = obs_cells_gdf['Id'].to_numpy()
        #         np.savetxt(os.path.join(self.supplementary, 'obs_cells.txt'), obs_cells, fmt = '%d')
        #         obs_txt = open(os.path.join(self.supplementary, 'obs_cells.txt'))
        #         gwflow_input.write('Groundwater Observation Locations'+'\n')
        #         gwflow_input.write(str(len(obs_cells)))
        #         gwflow_input.write('\n'+obs_txt.read())
        #         obs_txt.close()
        #     except:
        #         QSWATUtils.error('No observation cells defined', self._gv.isBatch)
        #         gwflow_input.write('Groundwater Observation Locations'+'\n')
        #         gwflow_input.write('0'+'\n')
        # else:
        #     QSWATUtils.loginfo('No observation cells defined')
        #     gwflow_input.write('Groundwater Observation Locations'+'\n')
        #     gwflow_input.write('0'+'\n')
            
        
        # # Cell for detailed sources/sink u = output
        # if self.row_det > 0 and self.col_det > 0:
        #     gwflow_input.write('Cell for detailed daily sources/sink output'+'\n')
        #     gwflow_input.write('Row\tColumn'+'\n')
        #     gwflow_input.write(str(self.row_det)+'\t'+str(self.col_det)+2*'\n')
        #
        # #River cell information
        # gwflow_input.write('River Cell Information'+'\n')
        # gwflow_input.write(str(self.river_depth)+3*'\t'+'Vertical distance (m) of streambed below the DEM value'+2*'\n')
        
        # # Tile cell information
        #
        # if tiles_file != '':
        #     tiles_df = grid6_gdf.loc[grid6_gdf['tile_cell'] == 1]
        #     gwflow_input.write('Tile Cell Information'+'\n')
        #     gwflow_input.write(str(self.tile_depth)+3*'\t'+'Depth (m) of tiles below ground surface'+'\n')
        #     gwflow_input.write(str(self.tile_area)+3*'\t'+'Area (m2) of groundwater inflow (circumference*length) * flow length'+'\n')
        #     gwflow_input.write(str(self.tile_k)+3*'\t'+'Hydraulic conductivity (m/day) of the drain perimeter'+'\n')
        #     gwflow_input.write(str(self.tile_groups)+3*'\t'+'Tile cell groups (flag: 0 = no; 1 = yes)'+'\n')
        #     gwflow_input.write(str(self.tile_groups_number)+3*'\t'+'Number of tile cells groups'+'\n')       
        #     if self.tile_groups == 1:
        #         for k in range(0, self.tile_groups_number):
        #             gwflow_input.write('Group '+str(k+1)+'\n')
        #             tile_by_group = tiles_df.loc[tiles_df['group'] == k+1]
        #             gwflow_input.write(str(len(tile_by_group))+3*'\t'+'Number of cells in the tile group'+'\n')
        #             gwflow_input.write(str(tile_by_group['Id'].iloc[0])+3*'\t'+'Cell ID')
        #             for i in range(1, len(tile_by_group)):
        #                 gwflow_input.write('\n'+str(tile_by_group['Id'].iloc[i]))
        #             gwflow_input.write('\n')
        # else:
        #     gwflow_input.write('Tile Cell Information'+'\n')
        #     gwflow_input.write(str(self.tile_depth)+3*'\t'+'Depth (m) of tiles below ground surface'+'\n')
        #     gwflow_input.write(str(self.tile_area)+3*'\t'+'Area (m2) of groundwater inflow (circumference*length) * flow length'+'\n')
        #     gwflow_input.write(str(self.tile_k)+3*'\t'+'Hydraulic conductivity (m/day) of the drain perimeter'+'\n')
        #     gwflow_input.write(str(0)+3*'\t'+'Tile cell groups (flag: 0 = no; 1 = yes)'+'\n')
        #     QSWATUtils.loginfo('No tile cells defined') 
        #
        # # Chemical Transport Information
        # gwflow_input.write('\n'+'Chemical Transport Information'+'\n')
        # gwflow_input.write(str(self.denit_constant)+3*'\t'+'First-order rate constant for denitrification (1/day)'+'\n')
        # gwflow_input.write(str(self.disp_coef)+3*'\t'+'Dispersion coefficient (m2/day)'+'\n')
        # gwflow_input.write(str(self.nit_sorp)+3*'\t'+'Sorption retardation coefficient for Nitrate'+'\n')
        # gwflow_input.write(str(self.pho_sorp)+3*'\t'+'Sorption retardation coefficient for Phosphorus'+'\n')
        # gwflow_input.write(str(self.transport_steps)+3*'\t'+'Number of transport time steps per flow time step')
        #
        # #years_txt.close()
        # cell_txt.close()
        # gwflow_input.close()
        
        # #------- Creating gwflow.rivcells file---------------
        # QSWATUtils.loginfo('...Creating gwflow.rivercells file...')
        # gwflow_river = open(os.path.join(self.inputFiles, 'gwflow.rivcells'), "w") # create file
        # gwflow_river.write('Cell-Channel Connection Information'+'\n')
        # gwflow_river.write('\n'+'ID\telev_m\tchannel\triv_length(m)\tzone')
        # river_cell_df = pd.DataFrame()
        # river_cell_df['ID'] = river_cell_gdf['Id']
        # river_cell_df['elev_m'] = river_cell_gdf['Avg_elevat']
        # river_cell_df['channel'] = river_cell_gdf['Channel']
        # river_cell_df['riv_length(m)'] = river_cell_gdf['riv_length']
        # river_cell_df['zone'] = river_cell_gdf['zone']
        # river_cell_df = river_cell_df.sort_values(by = ['ID', 'channel'])
        # river_cell = river_cell_df.to_numpy()
        # fmt = '%d\t%1.2f\t%d\t%1.2f\t%d'
        # np.savetxt(os.path.join(self.supplementary, 'rivercells.txt'), river_cell, fmt = fmt)
        # riv_txt = open(os.path.join(self.supplementary, 'rivercells.txt'), 'r')
        # gwflow_river.write('\n'+riv_txt.read())
        # gwflow_river.close()
        # riv_txt.close()
        # riv_unique = np.unique(river_cell_df['ID'].to_numpy())
        # riv_unique_nr = len(riv_unique)
        
        # if self.HRU_recharge:
        #     #------- Creating gwflow.hrucell file---------------
        #     QSWATUtils.loginfo('...Creating gwflow.hrucell file...')
        #     # cwg need to guard against possible split HRUs and NA for removed HRUs
        #     # can safely use split even for single values
        #     # change hru_intersection before copying to mod1_intersection_df so both are OK
        #     hru_intersection['HRUS'] = hru_intersection['HRUS'].map(lambda x: '0' if x == 'NA' else x.split(',')[0])
        #     mod1_intersection_df = hru_intersection.copy() #Deep copy of the gdf to be able to modify it
        #     mod1_intersection_df  = mod1_intersection_df.reindex(columns = ['HRUS', 'Area', 'Id', 'Poly_area'])#Rearrange the position of columns
        #     mod1_intersection_df = mod1_intersection_df.apply(pd.to_numeric)
        #     mod1_intersection_df = mod1_intersection_df.sort_values(by = ['HRUS', 'Id'])
        #     mod1_intersection_df_array = mod1_intersection_df.values
        #     np.savetxt(os.path.join(self.supplementary, 'hrucell_table.txt'), mod1_intersection_df_array, fmt = '%d', delimiter = '\t')
        #     cellhru = open(os.path.join(self.inputFiles, 'gwflow.hrucell'), 'w')
        #     cellhru.write('HRU-Cell Connection Information'+ 2*'\n'+'HRU'+'\t'+'area_m2'+'\t'+'Cell_Id'+'\t'+'Poly_area_m2')
        #     txt = open(os.path.join(self.supplementary, 'hrucell_table.txt'), 'r')
        #     cellhru.write('\n'+txt.read())
        #     cellhru.close()
        #     txt.close()
        #
        #     #------- Creating gwflow.cellhru file---------------
        #     hrucell1 = pd.DataFrame()                       #Generation of dataframe
        #     hrucell1['ID'] = hru_intersection["Id"]               #New data frame based on former hru data frame from previous code lines     
        #     hrucell1['hrus'] = hru_intersection["HRUS"]
        #     hrucell1['cellarea'] = self.cell_size*self.cell_size
        #     hrucell1['POLY_AREA'] = hru_intersection['Poly_area']
        #     hrucell1 = hrucell1.sort_values(by = ['ID', 'hrus'])
        #     hrucell2 = hrucell1.to_numpy(dtype = 'float')       #New numpy array based on the data frame generated specifying data type
        #     hrucell3 = hrucell1['ID'].to_numpy(dtype = 'float') #Generation of new array only with ID values to proceed to unique cells calculation
        #     uniquecell = np.unique(hrucell3, axis = 0)         #Discretization of unique cells from the ID of the array
        #     HRUCELL =  open(os.path.join(self.inputFiles, 'gwflow.cellhru'), 'w')            #Generation of base file
        #     HRUCELL.write("Cell-HRU Connection Information"+2*'\n'+ str( len (uniquecell))+ "\tNumber of cells that intersect HRUs"+'\n'\
        #                   "Cell_Id"+'\t'+"HRU_Id"+'\t'+"cell_area_(m2)"+'\t'+"poly_area_(m2)")      #generation of column titles and 
        #                                                                                             #unique cells number
        #     np.savetxt(os.path.join(self.supplementary, "tablacellhru.txt"), hrucell2, fmt = '%d\t%d\t%d\t%d')    #Conversion of data values from numpy array and format imposition
        #     text = open(os.path.join(self.supplementary, "tablacellhru.txt"), 'r')
        #     HRUCELL.write('\n'+text.read())                                     #Combination of column titles and array data values(from the .txt file) 
        #     HRUCELL.close()
        #     text.close()
        
        # #%%Modification of SWAT+ files (file.cio / object.cnt / rout_unit.con)
        # #------- Modifying file.cio file---------------
        # QSWATUtils.loginfo('...Modifying file.cio file...')
        # file_cio = open(filename_cio, 'r')
        # file_cio_lst = file_cio.readlines()
        # file_cio.close()
        #
        # file_cio_lst[4] = file_cio_lst[4].split(' ')
        # file_cio_lst[12] = file_cio_lst[12].split(' ')
        # count = 0
        #
        # for i in range(0, len(file_cio_lst[4])):
        #     if file_cio_lst[4][i] != '':
        #         count+= 1
        #         if count == 5:
        #             file_cio_lst[4][i] = 'gwflow.con'
        #         if count == 6:
        #             file_cio_lst[4][i] = 'null'
        # count = 0
        #
        # for i in range(0, len(file_cio_lst[12])):
        #     if file_cio_lst[12][i] != '':
        #         count+= 1
        #         if count == 3:
        #             file_cio_lst[12][i] = 'null'        
        #
        # file_cio_lst[4] = ' '.join(file_cio_lst[4])
        # file_cio_lst[12] = ' '.join(file_cio_lst[12])
        #
        # file_cio_out = open(os.path.join(self.inputFiles, 'file.cio'), 'w')
        # for line in file_cio_lst:
        #     file_cio_out.write(line)    
        #
        # file_cio_out.close()
        
        # #------ Modifying object.cnt -----
        # QSWATUtils.loginfo('...object.cnt file...')
        # object_cnt = open(filename_objectcnt, 'r')
        # object_cnt_lines = object_cnt.readlines()
        # object_cnt.close()
        #
        # object_cnt_lines[2] = object_cnt_lines[2].split(' ')
        # count = 0
        # for i in range(0, len(object_cnt_lines[2])):
        #     if object_cnt_lines[2][i] != '':
        #         count+= 1
        #
        #         if count == 8:
        #             object_cnt_lines[2][i] = str(riv_unique_nr)
        #         if count == 9:
        #             object_cnt_lines[2][i] = '0'
        #
        # obj_numr = 0     
        # count = 0       
        # for i in range(0, len(object_cnt_lines[2])):
        #     if object_cnt_lines[2][i] != '':
        #         count+= 1
        #         if count >= 5 and count != 22:
        #             obj_numr+= float(object_cnt_lines[2][i])  
        # count = 0
        # for i in range(0, len(object_cnt_lines[2])):
        #     if object_cnt_lines[2][i] != '':
        #         count+= 1
        #         if count == 4:
        #             object_cnt_lines[2][i] = str(int(obj_numr))
        #
        # object_cnt_lines[2] = ' '.join(object_cnt_lines[2])
        #
        # object_cnt_out = open(os.path.join(self.inputFiles, 'object.cnt'), 'w')
        # for line in object_cnt_lines:
        #     object_cnt_out.write(line)    
        #
        # #object_cnt.close()
        # object_cnt_out.close()
        
        # #----------Modifying rout_unit.con---------
        # QSWATUtils.loginfo('...rout_unit.con file...')
        # nru = open(filename_routunit, "r")              #Delete first line of text generated by the model to be able to work in a dataframe
        # lines = nru.readlines()
        # line0 = lines[0]
        # rout_unit_data = lines[1:]
        # nru.close()
        #
        # for i in range(0, len(rout_unit_data)):
        #     rout_unit_data[i] = rout_unit_data[i].split()
        #     if i>0:
        #         rout_unit_data[i][12] = '1'
        #         del rout_unit_data[i][-4:]
        #
        #
        # rout_unit_array = np.array(rout_unit_data)
        # np.savetxt(os.path.join(self.supplementary, 'rout_unit_data.txt'), rout_unit_array, fmt = '%-8s', delimiter = '\t')
        # rout_txt = open(os.path.join(self.supplementary, 'rout_unit_data.txt'), 'r')
        #
        # routunit = open(os.path.join(self.inputFiles, 'rout_unit.con'), 'w')            #Generation of base file
        #
        # routunit.write(line0)
        # routunit.write(rout_txt.read())
        # rout_txt.close()
        # routunit.close()                          
        
        # #%%Run the GWFLOW MODULE EXECUTABLE
        # #Copying contents on input folder to a new folder for gwflow
        # src = self.inputFiles # 'input_files'
        # trg = self.TxtInOut_gwflow  # 'TxtInOut_gwflow'
        #
        # files = os.listdir(src)
        #
        # # iterating over all the files in
        # # the source directory
        # for fname in files:
        #
        #     # copying the files to the
        #     # destination directory
        #     shutil.copy2(os.path.join(src, fname), trg)
        #
        #
        # #Copying swatgwflow exe to the gwflow folder
        # swat_exe = os.path.join(self.gwflowDir, 'SWAT+gwflow.exe')
        # # swat_exe = self.look_file(swat_exe)
        # # cwg makes no sense: look_file returns full path
        # # shutil.copy2(os.path.join(root_dir, swat_exe), trg)
        # shutil.copy2(swat_exe, trg)
        # #Change new working directory as the same as all the inputs are
        # # cwg simpler
        # # new_dir = os.path.dirname(os.path.abspath(os.path.join(self.TxtInOut_gwflow, 'SWAT+gwflow.exe')))
        # new_dir = self.TxtInOut_gwflow
        # os.chdir(new_dir)
        #
        # os.startfile('SWAT+gwflow.exe')


    #-----no longer used---------------------------------------------
    # #%% Functions
    # #Look for files function
    # def look_file(self, fileToSearch):
    #     #https://www.youtube.com/watch?v = EmiTz2P60yw&ab_channel = ShwetaLodha
    #     for relPath, dirs, files in os.walk(root_dir):
    #         if(fileToSearch in files):
    #             fullPath = os.path.join(root_dir, relPath, fileToSearch)
    #             return(fullPath)    
            
    # Geoprocessing functions for grids (To use in GIS routines) and other useful functions
    def fishnet(self, basinFileName, squaresize, OutputFileName, EPSG):
        start = datetime.now()
        QSWATUtils.loginfo('..Creating Fishnet...')
        self.progress('Creating fishnet grid')
        if self._dlg.alignGrids.isChecked():
            gridFile = QSWATUtils.join(self._gv.shapesDir, 'grid.shp')
            gridLayer = QgsVectorLayer(gridFile, 'Grid', 'ogr')
            extent = gridLayer.extent()
            minX = extent.xMinimum()
            maxX = extent.xMaximum()
            minY = extent.yMinimum()
            maxY = extent.yMaximum()
            squaresize = self._gv.gridSize * self._gv.topo.dx
            gdf = gpd.read_file(gridFile)
        else:
            ###Part of code obtained from https://spatial-dev.guru/2022/05/22/create-fishnet-grid-using-geopandas-and-shapely/
            gdf = gpd.read_file(basinFileName)
        
            # Get the extent of the shapefile
            total_bounds = gdf.total_bounds
            
            # Get minX, minY, maxX and maxY
            minX, minY, maxX, maxY = total_bounds
        
        # Number of rows and columns of the grid
        # this method fails sometimes: better method guaranteeing consistency with grid geometry below
        #rows = math.ceil((maxY-minY)/squaresize)
        #cols = math.ceil((maxX-minX)/squaresize)
        
        xToCol = lambda x: math.floor((x - minX) / squaresize)
        yToRow = lambda y: math.floor((y - minY) / squaresize)
        self.coordToCell = lambda x, y: (yToRow(y), xToCol(x))
        
        # Create a fishnet
        x, y = (minX, maxY)
        geom_array = []
        
        rows = 0
        size = 0
        while y >= minY:
            while x <= maxX:
                geom = geometry.Polygon([(x, y), (x, y-squaresize), (x+squaresize, y-squaresize), (x+squaresize, y), (x, y)])
                geom_array.append(geom)
                x+= squaresize
                size += 1
                
            x = minX
            y-= squaresize
            rows += 1
        cols = size // rows
            
        fishnet = gpd.GeoDataFrame(geom_array, columns = ['geometry']).set_crs(EPSG)
     
        
    
        fishnet['Id'] = 0
        fish_id = np.arange(1, size+1)
        
        fishnet['Id'] = fish_id
        end = datetime.now()
        QSWATUtils.loginfo('That took '+str(end-start))
        fishnet.to_file(OutputFileName)
        return(gdf, fishnet, rows, cols)
    
    def activecells(self, basin, grid1, OutputFileName):
        start = datetime.now()
        QSWATUtils.loginfo('...Identifying active cells...')
        self.progress('Identifying active cells')
        # Recognize active cells
        # Create new geodataframe called Grid 2 that is the same as Grid 1 for now
        grid2 = grid1.copy()
        # Create the atributte Avg_active in grid 2 and the basin (At the moment, at the grid everything is 0)
        grid2['Avg_active'] = 0
        basin['Avg_active'] = 1
        # Spatial join attributes from grid1 and the basin creating a new geodataframe from its combination (grid_join will repeat grid1 geometry, but get the basins attributes)
        # With this, all the cells that intersect the basin will now have a new attribute that is equal to 1, while for the rest the attribute value will be nan
        grid_join = gpd.sjoin(grid2, basin, how = "left", predicate = 'intersects')
        # Get the avg active values from the joined geodataframe and save into array
        active_array = grid_join['Avg_active_right'].to_numpy() #This will take an array of the avg_active attribute for the positions where cells intersect the basin as 1, and the rest as nan
        active_array = np.nan_to_num(active_array, nan = 0) #This will change al nan in the array, to 0
        # Create array from Id values
        id_array = grid_join['Id'].to_numpy()
        # Create new empty dataframe
        grid2_df = pd.DataFrame()
        # Assign avg_active array values to data frame, as well as Ids
        grid2_df['Avg_active'] = active_array.tolist()
        grid2_df['Id'] = id_array.tolist()
        # If there is repetition, for example a cell intersects the basin twice (its in the border between 2 sub-catchmetnts) the cell will be duplicated
        # The next line of code merges the duplicated cells and takes the average of the numerical attributes (in this case if avg_active is 1, it will stay as 1 after the average)
        grid2_df = grid2_df.groupby('Id').mean().reset_index()
        # We assign the avg_active corrected values from the dataframe, into the GeoDataFrame called Grid 2
        grid2['Avg_active'] = grid2_df['Avg_active']
        # We save grid 2 as a new Shapefile
        grid2.to_file(OutputFileName)
        end = datetime.now()
        QSWATUtils.loginfo('That took '+str(end-start))
        return(grid2)
    
    def aquif_thickness(self, raster, grid2, OutputFileName, EPSG):
        start = datetime.now()
        QSWATUtils.loginfo('...Assigning aquifer thickness to each cell...')
        self.progress('Assigning aquifer thickness')
        # Some functions usage was based on the tutorial: https://www.youtube.com/watch?v = p_BsFdV_LUk&list = PL4aUQR9L9RFp7kuu38hInDE-9ByueEMES&ab_channel = MakingSenseRemotely
        # To manipulate raster files, we will use the GDAL library and OSR to manipulate shapefiles
        
        # cwg now assumed to be clipped and reprojected
        # thick_ds = gdal.Open(raster) #Open world aquifer thickness file as a GDAL data source
        #
        # # Change grid boundary projection to be the same as raster source and save as different file
        # fish_boundary = grid2.to_crs('EPSG:4326')
        # fish_boundary.to_file(os.path.join(self.supplementary, 'fish_boundary_4326.shp')) 
        #
        # #Clip the raster and save clipped raster as a different file
        # thick_clip_ds = gdal.Warp(os.path.join(self.supplementary, 'thick_clipped.tif'), thick_ds, 
        #                         cutlineDSName = os.path.join(self.supplementary, 'fish_boundary_4326.shp'), 
        #                         cropToCutline = True) 
        #
        # # Reproject the clipped raster to the one of the basin, and save as a different file
        # thick_clip_ds = gdal.Warp(os.path.join(self.supplementary, 'Aq_thicknessRaster.tif'), thick_clip_ds, dstSRS = EPSG) 
        
        if not self._dlg.useUnstructured.isChecked():  # else already done in createDatFiles
            thick_ds = gdal.Open(raster, GA_Update)
            # Fill in missing values with an interpolation method from GDAL, it will find look information from a maximum of 5 pixels away from the missing data
            gdal.FillNodata(targetBand = thick_ds.GetRasterBand(1), maskBand = None, maxSearchDist = 5, smoothingIterations = 0)
            
            #Close all GDAL datasources (this is necessary because otherwise all modifications do not take place in the files 
            # after running the code, they just stay in python)
            # thick_clip_ds = None
            thick_ds = None
    
        # Raster to polygon the aquifer thickness
        # Based on the tutorial: https://www.youtube.com/watch?v = q3DLdMj5zLA&ab_channel = GeoGISLabs
        th_rast_ds = gdal.Open(raster) #Open clipped raster with gdal and get raster band
        th_rast_band = th_rast_ds.GetRasterBand(1) #Get rasterband means get the actual numerical information from the raster
    
        poly_projection = osr.SpatialReference() #Create a spatial reference (projection) for the new shapefile that will be created 
        poly_projection.ImportFromWkt(th_rast_ds.GetProjection()) #Assign the same projection as the raster
    
        output_poly = os.path.join(self.supplementary, 'thickness_raster2poly.shp') #Shapefile name
        driver = ogr.GetDriverByName('ESRI Shapefile') #The OGR driver works as constructor to create new GIS files like tif, shp, etc.
        out_thick_poly_ds = driver.CreateDataSource(output_poly) #Create OGR datasource
        out_thick_poly_layer = out_thick_poly_ds.CreateLayer('layer', srs = poly_projection) #Create a layer for the shapefile
        out_thick_poly_layer.CreateField(ogr.FieldDefn(str('Avg_Thick'), ogr.OFTInteger)) #Create a field in the shapefile for the thickness
        gdal.Polygonize(th_rast_band, None, out_thick_poly_layer, 0, [], callback = None) #Polygonize the raster into the created shapefile
        
        #Close all datasources GDAL/OGR
        out_thick_poly_layer = None
        out_thick_poly_ds = None
        th_rast_ds = None
        th_rast_band = None
        
        #Open new shapefile as GeoPandas DataFrame and convert the thickness to meters 
        thickness_gdf = gpd.read_file(output_poly)
        t_array = thickness_gdf['Avg_Thick'].to_numpy()
        t_array = t_array/100
        thickness_gdf['Avg_Thick'] = t_array.tolist()
        thickness_gdf = thickness_gdf.drop(thickness_gdf.index[-1]) #Deleting outter polygon generated when polygonizing raster
    
        #Save the final shapefile into a file
        thickness_gdf.to_file(os.path.join(self.supplementary, 'aqu_thick.shp'))
    
        #---------------------------------
        #Spatial join grid 2 with thickness shapefile
        grid3_gdf = grid2.copy()
        grid3 = gpd.sjoin(thickness_gdf, grid3_gdf, how = "right", predicate = 'intersects')
        id_array = grid3['Id'].to_numpy()
        aqthick_array = grid3['Avg_Thick'].to_numpy()
        thickness_df = pd.DataFrame()
        thickness_df['Id'] = id_array.tolist()
        thickness_df['Avg_Thick'] = aqthick_array.tolist()
        thickness_df = thickness_df.groupby('Id').mean().reset_index()
        thickness_df[thickness_df['Avg_Thick'] <= 0] = np.nan
        grid3_gdf['Avg_Thick'] = thickness_df['Avg_Thick']
        
        grid3_gdf.to_file(OutputFileName)
        end = datetime.now()
        QSWATUtils.loginfo('That took '+str(end-start))
        return(grid3_gdf)
    
    def aquif_thickness_local(self, localshp, thickness_attribute, grid2, OutputFileName):
        start = datetime.now()
        QSWATUtils.loginfo('...Assigning aquifer thickness to each cell...')
        self.progress('Assigning aquifer thickness')
     
        #Open new shapefile as GeoPandas DataFrame and convert the thickness to meters 
        thickness_gdf = gpd.read_file(localshp)
        #---------------------------------
        #Spatial join grid 2 with thickness shapefile
        grid3_gdf = grid2.copy()
        grid3 = gpd.sjoin(thickness_gdf, grid3_gdf, how = "right", predicate = 'intersects')
        id_array = grid3['Id'].to_numpy()
        aqthick_array = grid3[thickness_attribute].to_numpy()
        thickness_df = pd.DataFrame()
        thickness_df['Id'] = id_array.tolist()
        thickness_df['Avg_Thick'] = aqthick_array.tolist()
        thickness_df = thickness_df.groupby('Id').mean().reset_index()
        thickness_df[thickness_df['Avg_Thick'] <= 0] = np.nan
        grid3_gdf['Avg_Thick'] = thickness_df['Avg_Thick']
        
        grid3_gdf.to_file(OutputFileName)
        end = datetime.now()
        QSWATUtils.loginfo('That took '+str(end-start))
        return(grid3_gdf)
    
    def aquif_elevation(self, raster, grid3, OutputFileName, EPSG, pxl_res):
        start = datetime.now()
        QSWATUtils.loginfo('...Assigning ground elevation to each cell...')
        self.progress('Assigning ground elevation')
        # Some functions usage was based on the tutorial: https://www.youtube.com/watch?v = p_BsFdV_LUk&list = PL4aUQR9L9RFp7kuu38hInDE-9ByueEMES&ab_channel = MakingSenseRemotely
        # To manipulate raster files, we will use the GDAL library and OSR to manipulate shapefiles
        original_ds = gdal.Open(raster) #Open DEM raster file as GDAL data source
        elev_ds = gdal.Warp(os.path.join(self.supplementary, 'coarse_DEM.tif'), original_ds, dstSRS = EPSG, xRes = pxl_res, yRes = pxl_res, resampleAlg = 'average')
        # Raster to polygon the DEM
        # Based on the tutorial: https://www.youtube.com/watch?v = q3DLdMj5zLA&ab_channel = GeoGISLabs
        elev_band = elev_ds.GetRasterBand(1) #Get rasterband means get the actual numerical information from the raster
    
        poly_projection = osr.SpatialReference()#Create a spatial reference (projection) for the new shapefile that will be created 
        poly_projection.ImportFromWkt(elev_ds.GetProjection())#Assign the same projection as the raster
    
        output_poly = os.path.join(self.supplementary, 'elevation_poly.shp') #Shapefile name
        driver = ogr.GetDriverByName('ESRI Shapefile') #The OGR driver works as constructor to create new GIS files like tif, shp, etc.
           
        out_elev_poly_ds = driver.CreateDataSource(output_poly) #Create OGR datasource
        out_elev_poly_layer = out_elev_poly_ds.CreateLayer('layer', srs = poly_projection) #Create a layer for the shapefile
        out_elev_poly_layer.CreateField(ogr.FieldDefn(str('Avg_elevat'), ogr.OFTInteger)) #Create a field in the shapefile for the ground elevation
    
    
        gdal.Polygonize(elev_band, None, out_elev_poly_layer, 0, [], callback = None) #Polygonize the raster into the created shapefile
    
        #Close all datasources GDAL/OGR
        original_ds = None
        out_elev_poly_layer = None
        out_elev_poly_ds = None
        elev_ds = None
        elev_band = None
    
        #Spatial join grid 2 with thickness shapefile
    
        elevation = gpd.read_file(os.path.join(self.supplementary, 'elevation_poly.shp')) #Open polgonized elevations as geodatagrame
    
        elevation_gdf = elevation.dissolve(by = 'Avg_elevat') #Join polygons of polygonized raster that have the same elevation to make file smaller
        elevation_gdf = elevation_gdf.reset_index() #Reset index to send elevations as a column and not index
    
        grid4 = gpd.sjoin(elevation, grid3, how = "right", predicate = 'intersects') #Spatial join grid with elevation polygons
    
    
        #Create arrays with Id and elevation from the spatial join
        id_array = grid4['Id'].to_numpy()
        elevation_array = grid4['Avg_elevat'].to_numpy()
        #Create new dataframe and assign Id and elevation values from arrays
        elevation_df = pd.DataFrame()
        elevation_df['Id'] = id_array.tolist()
        elevation_df['Avg_elevat'] = elevation_array.tolist()
        #Groupby to average elevation values of cells that intersect different polygons
        elevation_df = elevation_df.groupby('Id').mean().reset_index()
        #Set negative values to 
        elevation_df[elevation_df['Avg_elevat'] <= 0] = np.nan
        #Make grid 4 equal to grid 3
        grid4 = grid3.copy()
        #Assign elevation values from the previously created dataframe to grid 3
        grid4['Avg_elevat'] = elevation_df['Avg_elevat']
        #Save to shapefile
        grid4.to_file(OutputFileName)
        end = datetime.now()
        QSWATUtils.loginfo('That took '+str(end-start))
        return(grid4)    
    
    def aquif_conductivity(self, K_FileName, grid4, basin_gdf, OutputFileName, EPSG):

        start = datetime.now()
        QSWATUtils.loginfo('...Assigning aquifer conductivity zone to each cell...')
        self.progress('Assigning aquifer conductivity zone')
        # Define and open fishnet boundary
        
        borders = basin_gdf['geometry'].unary_union #Create polygon of the external borders of the grid
        borders_gs = gpd.GeoSeries(borders) 
        borders_gdf = gpd.GeoDataFrame()
        borders_gdf['geometry'] = borders_gs #Assign geometry of borders to a geodataframe to work with it
        borders_gdf = borders_gdf.set_crs(EPSG) #Set projection (should be the same as the basin)
        borders_gdf.to_file(os.path.join(self.supplementary, 'only_basin_boundary.shp')) #Save to shapefile
         
        # Assignment of conductivity zones 
        #Open GLHYMPS database and get the layer with the information
        #It is necessary to open only the polygons that touch the grid, otherwise it takes too long
        #Therefore, we use bbox which creates a max for which python will only open the information of GLHYMPS that is intersecting the grid
        K_gdf = gpd.read_file(K_FileName, bbox = borders_gdf) 
        
        K_gdf_prj = K_gdf.to_crs(EPSG) #Reproject the conductivity polygons from GLHYMPS to the basins projection
        
        #Save the Log_K_Ferr values into an array and do all numerical operations to end up with K in [m/day]
        k_array = K_gdf_prj['logK_Ferr_'].to_numpy()
        k_array = k_array/100
        k_array = 10**(k_array)
        k_array = k_array*1000*9.81/0.001
        k_array = k_array*86400
       
        #Assing K in [m/dy] to the geodataframe 
        K_gdf_prj['K[m/day]'] = k_array
        
        # Clip polygons INTO the grid (Previously the polygons had portions outside of the grid)
        K_gdf = gpd.overlay(K_gdf_prj, borders_gdf)
        # Save the clipped shapefile of GLHYMS with conductivity zones well defined
        K_gdf.to_file(os.path.join(self.supplementary, 'GLHYMS_clipped.shp'))
        
        #Join geometries of polygons with same values of K (So that we can define zones of same K later)
        K_gdf_zones = K_gdf.copy()
        
        K_gdf_zones['zone'] = np.arange(1, len(K_gdf_zones)+1, 1)
    
    
    
        # Spatial join of the clipped GLHYMS with the grid to assign zone value to each grid
        grid_intersection = gpd.sjoin(grid4, K_gdf_zones, how = 'left', predicate = 'intersects')
        
        #From the spatial join, we need to convert zone and Id values to numpy (this is necessary to summarize attributes)
        zone_array = grid_intersection['zone'].to_numpy()
        id_array = grid_intersection['Id'].to_numpy()
        
        # Create new data frame with the important data that corresponds to grid 5
        grid5_df = pd.DataFrame()
        grid5_df['zone'] = zone_array
        grid5_df['Id'] = id_array
    
        #Group rows that have the same Id value (but different zone value) and summarize by choosing the minimum value of zone
        grid5_df = grid5_df.groupby('Id').mean().reset_index()
        
        #Equal grid 5 to grid 4 and assign new summarized zone values to grid 5
        grid5 = grid4.copy()
        grid5['zone'] = 0
        grid5['zone'] = grid5_df['zone']
        grid5['zone'] = grid5['zone'].fillna(0)
        grid5['zone'] = grid5['zone'].astype('int64')
        #Export grid 5 to shapefile and save in code to plot later
        grid5.to_file(OutputFileName)
        end = datetime.now()
      
        QSWATUtils.loginfo('That took '+str(end-start))
        return(grid5, K_gdf_zones)
    
    # # Aquifer and Streambed Parameter Zones
    # def input_zones(self, gwflow_input, title, original_gdf, value):
    #     gwflow_input.write(title+'\n')
    #     gwflow_input.write(str(len(original_gdf))+'\n')
    #     zonesdf = pd.DataFrame()
    #     zonesdf['zone'] = original_gdf['zone']
    #     zonesdf['Value'] = value
    #     zones = zonesdf.to_numpy()
    #     fmt = '%d\t%1.6f'
    #     np.savetxt(os.path.join(self.supplementary, 'zones.txt'), zones, fmt = fmt)
    #     zones_txt = open(os.path.join(self.supplementary, 'zones.txt'), 'r')
    #     gwflow_input.write(zones_txt.read())
    #     zones_txt.close()
    
    def createBuildDfn(self):
        """Create build dfn file for GridGen."""
        demLayer = QgsRasterLayer(self._gv.demFile, 'dem')
        extent = demLayer.extent()
        xMin = extent.xMinimum()
        yMin = extent.yMinimum()
        xMax = extent.xMaximum()
        yMax = extent.yMaximum()
        ncols = int(abs(xMax - xMin) / self.cell_size)
        nrows = int(abs(yMax - yMin) / self.cell_size)
        refinementLevel = self._dlg.refinementLevel.value()
        template = os.path.join(self.gwflowDir, 'action01_buildqtg.template')
        buildDfn = re.sub('.template$', '.dfn', template)
        with open(template) as tmpl, open(buildDfn, 'w') as build:
            for line in tmpl:
                if '%%' in line:
                    line = line.replace('%%xorigin%%', str(xMin))
                    line = line.replace('%%yorigin%%', str(yMin))
                    line = line.replace('%%nrow%%', str(nrows))
                    line = line.replace('%%ncol%%', str(ncols))
                    line = line.replace('%%cellsize%%', str(self.cell_size))
                    line = line.replace('%%channelslevel%%', str(refinementLevel))
                build.write(line)
                
    def createBoundary(self):
        """Create boundary shapefile by dissolving subbasins."""
        boundaryFile = os.path.join(self._gv.shapesDir, 'boundary.shp')
        root = QgsProject.instance().layerTreeRoot()
        QSWATUtils.removeLayerAndFiles(boundaryFile, root)
        # create context to make processing turn off detection of what it claims are invalid shapes
        # as shapefiles generated from rasters, like the subbasins shapefile, often have such shapes
        context = QgsProcessingContext()
        context.setInvalidGeometryCheck(QgsFeatureRequest.GeometryNoCheck)
        processing.run('native:dissolve', {'INPUT': self._gv.subbasinsFile, 'OUTPUT': boundaryFile}, context=context)
        if not os.path.exists(boundaryFile):
            QSWATUtils.error('Failed to create boundary shapefile {0}'.format(boundaryFile), self._gv.isBatch)
            
    def createDatFiles(self, EPSG):
        """Create .dat files for top (equals dem) and bottom (dem - aquifer thickness) of layer."""
        original_ds = gdal.Open(self._gv.demFile, GA_ReadOnly)
        elev_ds = gdal.Warp(os.path.join(self.supplementary, 'coarse_DEM.tif'), original_ds, dstSRS = EPSG, xRes = self.cell_size, yRes = self.cell_size, resampleAlg = 'average')
        thick_ds = gdal.Open(self.thick_file_local, GA_Update)
        # Fill in missing values with an interpolation method from GDAL, it will find look information from a maximum of 5 pixels away from the missing data
        gdal.FillNodata(targetBand = thick_ds.GetRasterBand(1), maskBand = None, maxSearchDist = 5, smoothingIterations = 0)
        #Close GDAL datasource to write file
        thick_ds = None 
        # need to convert elevation row, col to aquifer thickness row, col
        thick_ds = gdal.Open(self.thick_file_local, GA_ReadOnly)
        elevNumberRows = elev_ds.RasterYSize
        elevNumberCols = elev_ds.RasterXSize
        thickNumberRows = thick_ds.RasterYSize
        thickNumberCols = thick_ds.RasterXSize
        elevTransform = elev_ds.GetGeoTransform()
        thickTransform = thick_ds.GetGeoTransform()
        thickRowFun, thickColFun = \
            QSWATTopology.translateCoords(elevTransform, thickTransform, 
                                          elevNumberRows, elevNumberCols)  
        elevBand = elev_ds.GetRasterBand(1) 
        thickBand = thick_ds.GetRasterBand(1)   
        elevCurrentRow = -1
        elevData = np.empty([1, elevNumberCols], dtype=float)  
        thickCurrentRow = -1
        thickData = np.empty([1, thickNumberCols], dtype=float)
        with open(os.path.join(self.gwflowDir,'grid01mfg.top.dat'), 'w') as top, open(os.path.join(self.gwflowDir,'grid01mfg.bot1.dat'), 'w') as bottom:
            for row in range(elevNumberRows):
                if row != elevCurrentRow:
                    elevCurrentRow = row
                    elevData = elevBand.ReadAsArray(0, row, elevNumberCols, 1)
                y = QSWATTopology.rowToY(row, elevTransform)
                thickRow = thickRowFun(row, y)
                if thickRow != thickCurrentRow:
                    if 0 <= thickRow < thickNumberRows:
                        thickCurrentRow = thickRow
                        thickData = thickBand.ReadAsArray(0, thickRow, thickNumberCols, 1)
                    else:
                        QSWATUtils.error('DEM row {0} for latitude {1} gives thickness row {2} which exceeds maximum row {3}.  Using zero.'
                                         .format(row, int(y), thickRow, thickNumberRows), self._gv.isBatch)
                        thickData = np.zeros([1, thickNumberCols], dtype=float)
                for col in range(elevNumberCols):
                    # coerce to float else considered to be a numpy float
                    elev = float(elevData[0, col])
                    x = QSWATTopology.colToX(col, elevTransform)
                    thickCol = thickColFun(col, x)
                    if 0 <= thickCol < thickNumberCols:
                        thick = float(thickData[0, thickCol]) / 100 # converted to metres
                    else:
                        QSWATUtils.error('DEM column {0} for longitude {1} gives thickness column {2} which exceeds maximum column {3}.  Using zero.'.format(col, int(x), thickCol, thickNumberCols), self._gv.isBatch)
                        thick = 0
                    top.write('{0}\n'.format(elev))
                    bottom.write('{0}\n'.format(elev - thick))
        elev_ds =  None 
        thick_ds = None 
        return elevNumberRows, elevNumberCols                
        
    # @staticmethod
    # def scale_north(ax):
    #     ax.add_artist(ScaleBar(dx = 1, units = "km", dimension = "si-length", length_fraction = 0.25, 
    #      scale_formatter = lambda value, unit: f' {value * 1000} km ', location = 'lower left'))
    #     x, y, arrow_length = 0.07, 0.95, 0.2
    #     ax.annotate('N', color = 'black', xy = (x, y), xytext = (x, y-arrow_length), arrowprops = dict(facecolor = 'black', width = 1, headwidth = 5), 
    #                 ha = 'center', va = 'center', fontsize = 12, xycoords = ax.transAxes)
        
    def createTables(self, conn):
        # remove tables in case of redesign.  Last two must come last because of foreign key constraints
        for table in ['gwflow_base', 'gwflow_out_days', 'gwflow_obs_locs', 'gwflow_solutes', 'gwflow_init_conc', 'gwflow_hrucell', 
                       'gwflow_fpcell', 'gwflow_rivcell', 'gwflow_lsucell', 'gwflow_rescell', 'gwflow_grid', 'gwflow_zone']:
            sql = 'DROP TABLE IF EXISTS ' + table
            conn.execute(sql)
        conn.execute(_GWFLOW_BASE)
        conn.execute(_GWFLOW_ZONE)
        conn.execute(_GWFLOW_GRID)
        conn.execute(_GWFLOW_OUT_DAYS)
        conn.execute(_GWFLOW_OBS_LOCS)
        conn.execute(_GWFLOW_SOLUTES)
        conn.execute(_GWFLOW_INIT_CONC)
        conn.execute(_GWFLOW_HRUCELL)
        conn.execute(_GWFLOW_FPCELL)
        conn.execute(_GWFLOW_RIVCELL)
        conn.execute(_GWFLOW_LSUCELL)
        conn.execute(_GWFLOW_RESCELL)
        
    def makeHRUData(self, hru_intersection):
        '''Create table HRUData.'''
        
        def getLanduse(hru, conn):
            sql = 'SELECT landuse FROM gis_hrus WHERE id=?'
            row = conn.execute(sql, (hru,)).fetchone()
            return row[0]
        
        # map cell -> hru -> area
        result = dict()        
        # store split details
        splits = dict()
        sql = 'SELECT * FROM gis_splithrus'
        with self._gv.db.conn as conn:
            for row in conn.execute(sql):
                splitData = splits.setdefault(row[0], dict())
                splitData[row[1]] = float(row[2]) / 100 # convert % to fraction
            cellArea = self.cell_size * self.cell_size
            # map of lsu to triple (hru -> cell -> area, hru -> area, area)
            LSUData = dict()
            # mao of lsu -> polyArea, ie area that can be occupied by HRUs
            LSUPolyAreas = dict()
            # map lsu -> cell -> area
            #LSUMaxAreas = dict()
            # map lsu -> cell -> area occupied by removed HRUs
            LSUSpareAreas = dict()
            for _,row in hru_intersection.iterrows():
                channel = int(row['Channel'])
                lscape = row['Landscape']
                lsu = channel * 10 + (2 if lscape == 'Upslope' else 1 if lscape == 'Floodplain' else 0)
                cellId = row['Id']
                polyArea = float(row['Poly_area'])
                #cellMaxAreas = LSUMaxAreas.setdefault(lsu, dict())
                #cellMaxAreas[cellId] = cellMaxAreas.setdefault(cellId, 0) + polyArea
                LSUPolyAreas[lsu] = LSUPolyAreas.setdefault(lsu, 0) + polyArea
                cellSpareAreas = LSUSpareAreas.setdefault(lsu, dict())
                hrus = row['HRUS'].split(',')
                landuse = row['Landuse']
                if len(hrus) == 1 and hrus[0] == 'NA':
                    # removed HRU
                    cellSpareAreas[cellId] = cellSpareAreas.setdefault(cellId, 0) + polyArea
                    continue
                # lsuData is map hru -> cell -> area
                # hruAreas is map hru -> area
                lsuData, hruAreas, totHRUArea = LSUData.setdefault(lsu, (dict(), dict(), 0))
                for hru in hrus:
                    hruData = lsuData.setdefault(hru, dict())
                    hruArea = hruAreas.setdefault(hru, 0)
                    if landuse in splits:
                        splitLanduse = getLanduse(hru, conn)
                        frac = splits[landuse][splitLanduse]
                        area = polyArea * frac
                    else:
                        area = polyArea
                    hruData[cellId] = area
                    hruAreas[hru] = hruArea + area
                    totHRUArea += area
                    # initialise result map
                    cellResult = result.setdefault(cellId, dict())
                    cellResult[hru] = cellResult.setdefault(hru, 0) + area
                LSUData[lsu] = (lsuData, hruAreas, totHRUArea)
            for lsu, (lsuData, hruAreas, totHRUArea) in LSUData.items():
                if totHRUArea == 0:
                    QSWATUtils.loginfo('Zero total area for lsu {0}'.format(lsu))
                    QSWATUtils.loginfo('lsuData for lsu {0}: {1}'.format(lsu, str(lsuData)))
                    QSWATUtils.loginfo('hruAreas for lsu {0}: {1}'.format(lsu, str(hruAreas)))
                    return
                # have for each hru in the lsu a mapping cell -> area,  and an hru area, plus total of all hru area
                # first calculate a target increase in area for each hru
                # then distribute the spare space until targets are met.
                # target for an HRU is % of HRU * spare space
                cellSpareAreas = LSUSpareAreas[lsu]
                spareSpace = LSUPolyAreas[lsu] - totHRUArea
                targets = sorted([(hru, spareSpace * hruAreas[hru] / totHRUArea) for hru in hruAreas ], key=lambda x: x[1], reverse=True)
                for (hru, target) in targets:
                    todo = target
                    # order cells by area of this hru and then spare space
                    # multiplying hru area in the cell by cellArea makes it predominate over spare space, 
                    # so cells already containing some of this hru are chosen first
                    orderedCells = sorted([(cellId, lsuData[hru].get(cellId, 0), cellSpareAreas[cellId]) for cellId in cellSpareAreas],
                                          key=lambda x: x[2] if x[1] == 0 else x[1] * cellArea, reverse=True) 
                    for (cellId, hruArea, spareArea) in orderedCells:
                        if todo == 0:
                            break
                        toAssign = min(todo, spareArea)
                        cellResult = result.setdefault(cellId, dict())
                        cellResult[hru] = cellResult.setdefault(hru, 0) + toAssign
                        cellSpareAreas[cellId] -= toAssign
                        if cellSpareAreas[cellId] == 0:
                            del cellSpareAreas[cellId]
                        lsuData[hru][cellId] = lsuData[hru].setdefault(cellId, 0) + toAssign
                        todo -= toAssign
            sql = 'INSERT INTO gwflow_hrucell VALUES(?,?,?)'
            for cellId, cellResult in result.items():
                for hru, area in cellResult.items():
                    conn.execute(sql, (cellId, hru, round(area)))
        
    def readProj(self) -> None:
        """Read aquifer thickness, permeability, observation and tile drain settings from the project file."""
        proj = QgsProject.instance()
        attTitle = proj.title().replace(' ', '')
        aquiferThickness, found = proj.readEntry(attTitle, 'gwflow/aquiferThickness', '')
        if found and aquiferThickness != '':
            aquiferThickness = proj.readPath(aquiferThickness)
            self._dlg.aquiferThickness.setText(aquiferThickness)
        permeability, found = proj.readEntry(attTitle, 'gwflow/aquiferPermeability', '')
        if found and permeability != '':
            permeability = proj.readPath(permeability)
            self._dlg.aquiferPermeability.setText(permeability)
        observationLocations, found = proj.readEntry(attTitle, 'gwflow/observationLocations', '')
        if found and observationLocations != '':
            self.obs_file = proj.readPath(observationLocations)
            self._dlg.observationLocations.setText(self.obs_file)
        tileDrains, found = proj.readEntry(attTitle, 'gwflow/tileDrains', '')
        if found and tileDrains != '':
            self.tiles_file = proj.readPath(tileDrains)
            self._dlg.tileDrains.setText(self.tiles_file)
        initFile, found = proj.readEntry(attTitle, 'gwflow/initFile', '')
        if found and initFile != '':
            initFile = proj.readPath(initFile)
            self._dlg.initialization.setText(initFile)
        outputTimes, found = proj.readEntry(attTitle, 'gwflow/outputTimes', '')
        if found and outputTimes != '':
            outputTimes = proj.readPath(outputTimes)
            self._dlg.outputTimes.setText(outputTimes)
        
    def saveProj(self):
        """Write entries for aquifer thickness, permeability, observation and tile drain files to project file."""
        proj = QgsProject.instance()
        attTitle = proj.title().replace(' ', '')
        proj.writeEntry(attTitle, 'gwflow/aquiferThickness', proj.writePath(self._dlg.aquiferThickness.text()))
        proj.writeEntry(attTitle, 'gwflow/aquiferPermeability', proj.writePath(self._dlg.aquiferPermeability.text()))
        proj.writeEntry(attTitle, 'gwflow/observationLocations', proj.writePath(self.obs_file))
        proj.writeEntry(attTitle, 'gwflow/tileDrains', proj.writePath(self.tiles_file))
        proj.writeEntry(attTitle, 'gwflow/initFile', proj.writePath(self._dlg.initialization.text()))
        proj.writeEntry(attTitle, 'gwflow/outputTimes', proj.writePath(self._dlg.outputTimes.text()))
        
_GWFLOW_BASE = '''CREATE TABLE gwflow_base (
cell_size INTEGER,
row_count INTEGER,
col_count INTEGER,
boundary_conditions INTEGER,
recharge INTEGER,
soil_transfer INTEGER,
saturation_excess INTEGER,
external_pumping INTEGER,
tile_drainage INTEGER,
reservoir_exchange INTEGER,
wetland_exchange INTEGER,
floodplain_exchange INTEGER,
canal_seepage INTEGER,
solute_transport INTEGER,
transport_steps REAL,
disp_coef REAL,
recharge_delay INTEGER,
et_extinction_depth REAL,
water_table_depth REAL,
river_depth REAL,
tile_depth REAL,
tile_area REAL,
tile_k REAL,
tile_groups INTEGER,
resbed_thickness REAL,
resbed_k REAL,
wet_thickness REAL,
daily_output INTEGER,
annual_output INTEGER,
aa_output INTEGER,
daily_output_row INTEGER,
daily_output_col INTEGER,
timestep_balance REAL
);'''

_GWFLOW_GRID = '''CREATE TABLE gwflow_grid (
cell_id INTEGER PRIMARY KEY,
status INTEGER,
zone INTEGER REFERENCES gwflow_zone (zone_id),
elevation REAL,
aquifer_thickness REAL,
extinction_depth REAL,
initial_head REAL,
tile INTEGER
);'''

_GWFLOW_ZONE = '''CREATE TABLE gwflow_zone (
zone_id INTEGER PRIMARY KEY,
aquifer_k REAL,
specific_yield REAL,
streambed_k REAL,
streambed_thickness REAL
);'''

_GWFLOW_OUT_DAYS = '''CREATE TABLE gwflow_out_days (
year INTEGER,
jday INTEGER
);'''

# do not make this a foreign key since may accidentally reference inactive cell
_GWFLOW_OBS_LOCS = '''CREATE TABLE gwflow_obs_locs (
cell_id INTEGER
);'''

_GWFLOW_SOLUTES = '''CREATE TABLE gwflow_solutes (
solute_name TEXT,
sorption REAL,
rate_const REAL,
canal_irr REAL,
init_data TEXT,
init_conc REAL
);'''

_GWFLOW_INIT_CONC = '''CREATE TABLE gwflow_init_conc (
cell_id INTEGER REFERENCES gwflow_grid (cell_id),
init_no3 REAL DEFAULT 0,
init_p REAL DEFAULT 0,
init_so4 REAL DEFAULT 0,
init_ca REAL DEFAULT 0,
init_mg REAL DEFAULT 0,
init_na REAL DEFAULT 0,
init_k REAL DEFAULT 0,
init_cl REAL DEFAULT 0,
init_co3 REAL DEFAULT 0,
init_hco3 REAL DEFAULT 0
);'''

_GWFLOW_HRUCELL = '''CREATE TABLE gwflow_hrucell (
cell_id INTEGER REFERENCES gwflow_grid (cell_id),
hru INTEGER REFERENCES gis_hrus (id),
area_m2 REAL
);'''

_GWFLOW_FPCELL = '''CREATE TABLE gwflow_fpcell (
cell_id INTEGER REFERENCES gwflow_grid (cell_id),
channel INTEGER REFERENCES gis_channels (id),
area_m2 REAL,
conductivity REAL
);'''

_GWFLOW_RIVCELL = '''CREATE TABLE gwflow_rivcell (
cell_id INTEGER REFERENCES gwflow_grid (cell_id),
channel INTEGER REFERENCES gis_channels (id),
length_m REAL
);'''

_GWFLOW_LSUCELL = '''CREATE TABLE gwflow_lsucell (
cell_id INTEGER REFERENCES gwflow_grid (cell_id),
lsu INTEGER REFERENCES gis_lsus (id),
area_m2 REAL
);'''

_GWFLOW_RESCELL = '''CREATE TABLE gwflow_rescell (
cell_id INTEGER REFERENCES gwflow_grid (cell_id),
res INTEGER REFERENCES gis_water (id),
res_stage REAL
);'''
