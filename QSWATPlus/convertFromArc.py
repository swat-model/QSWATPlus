# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QSWATPlus
                                 A QGIS plugin
 Create SWAT+ inputs
                             -------------------
        begin                : 2018-04-13
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
 
from PyQt5.QtCore import *  # @UnusedWildImport
from PyQt5.QtGui import *  # @UnusedWildImport
from PyQt5.QtWidgets import *  # @UnusedWildImport
from qgis.core import * # @UnusedWildImport
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry  # @UnresolvedImport
import sys
import os
import shutil
import glob
import csv
from osgeo import gdal
import numpy
import sqlite3
import subprocess
import datetime
import time
import traceback

from convertdialog import convertDialog
from QSWATUtils import QSWATUtils
from DBUtils import DBUtils
from QSWATTopology import QSWATTopology
#from parameters import Parameters
#from TauDEMUtils import TauDEMUtils
#from polygonizeInC2 import Polygonize  # @UnresolvedImport
from QSWATPlus import QSWATPlus

class ConvertFromArc(QObject):
    """Convert ArcSWAT projects to SWAT+"""
    _fullChoice = 0
    _existingChoice = 1
    _noGISChoice = 2
    
    def __init__(self, ConvertFromArcDir):
        """Initialise class variables."""
        QObject.__init__(self)
        ## ConvertFromArc directory
        self.ConvertFromArcDir = ConvertFromArcDir
        ## SWATPlus directory
        self.SWATPlusDir = r'{0}\..\..'.format(ConvertFromArcDir)
        ## plugin directory
        self.pluginDir = os.path.dirname(__file__)
        ## QGIS project
        self.proj = None
        ## ArcSWAT project directory
        self.arcProjDir = ''
        ## ArcSWAT project name
        self.arcProjName = ''
        ## QSWAT+ project directory
        self.qProjDir = ''
        ## QSWAT+ project name
        self.qProjName = ''
        ## DEM
        self.demFile = ''
        ## coordinate reference system
        self.crs = None
        ## outlets
        self.outletFile = ''
        ## extra outlets
        self.extraOutletFile = ''
        ## Subbasins shapefile 
        self.subbasinsFile = ''
        ## watershed shapefile
        self.wshedFile = ''
        ## channels shapefile
        self.channelsFile = ''
        ## landuse file
        self.landuseFile = ''
        ## soil file
        self.soilFile = ''
        ## number of landuse classes reported in MasterProgress
        self.numLuClasses = 0
        ## soil option reported in MasterProgress
        self.soilOption = ''
        ## soils used in model (no GIS option only)
        self.usedSoils = set()
        ## landuses used in model (no GIS option only)
        self.usedLanduses = set()
        ## wgn stations stored as station id -> (lat, long)
        self.wgnStations = dict()
        self._dlg = convertDialog()
        self._dlg.setWindowFlags(self._dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint & Qt.WindowMinimizeButtonHint)
        self._dlg.fullButton.clicked.connect(self.getChoice)
        self._dlg.existingButton.clicked.connect(self.getChoice)
        self._dlg.noGISButton.clicked.connect(self.getChoice)
        ## choice of conversion
        self.choice = ConvertFromArc._fullChoice
        
    def run(self):
        print("Converting from ArcSWAT")
        # QSettings does not seem to work 
#         settings = QSettings()
#         if settings.contains('/QSWATPlus/LastInputPath'):
#             path = settings.value('/QSWATPlus/LastInputPath').toString()
#         else:
#             path = ''
        path = ''
        self.arcProjDir = None
        title = 'Select ArcSWAT directory, i.e. directory containing directories RasterStore.idb, Scenarios and Watershed.'
        while self.arcProjDir is None:
            self.arcProjDir = QFileDialog.getExistingDirectory(None, title, path)
            if self.arcProjDir is None or self.arcProjDir == '':
                return
            try:
                # convert to string from QString
                self.arcProjDir = str(self.arcProjDir)
                self.arcProjName = os.path.split(self.arcProjDir)[1]
                arcProjFile = os.path.join(self.arcProjDir, self.arcProjName + '.mxd')
                if not os.path.exists(arcProjFile):
                    ConvertFromArc.error('Cannot find ArcSWAT project file {0}'.format(arcProjFile))
                    self.arcProjDir = None
                    continue
            except Exception:
                ConvertFromArc.exceptionError('Cannot find ArcSWAT project file in {0}'.format(self.arcProjDir))
                self.arcProjDir = None
                continue
        # set up QSWAT+ project directory
        qProjFile = None
        while qProjFile is None:
            title = 'Select a parent directory to hold the new QSWATPlus project'
            projParent = QFileDialog.getExistingDirectory(None, title, self.arcProjDir)
            if projParent is None or projParent == '':
                return
            arcAbs = os.path.abspath(self.arcProjDir)
            qAbs = os.path.abspath(projParent)
            if qAbs.startswith(arcAbs):
                ConvertFromArc.error('The QSWAT+ project cannot be within the ArcSWAT project')
                continue
            elif arcAbs.startswith(qAbs):
                ConvertFromArc.error('The ArcSWAT project cannot be within the QSWAT+ project')
                continue
            # convert to string from QString
            projParent = str(projParent)
            if ConvertFromArc.question('Use {0} as new project name?'.format(self.arcProjName)) == QMessageBox.Yes:
                self.qProjName = self.arcProjName
            else:
                self.qProjName, ok = QInputDialog.getText(None, 'QSWATPlus project name',
                                                          'Please enter the new project name, starting with a letter:',
                                                          flags=Qt.MSWindowsFixedSizeDialogHint)
                if not ok:
                    return
                if not str(self.qProjName[0]).isalpha():
                    self.error('Project name must start with a letter')
                    continue
            self.qProjDir = os.path.join(projParent, self.qProjName)
            if os.path.exists(self.qProjDir):
                response = ConvertFromArc.question('Project directory {0} already exists.  Do you wish to delete it?'.format(self.qProjDir))
                if response != QMessageBox.Yes:
                    continue
                try:
                    shutil.rmtree(self.qProjDir, ignore_errors=True)
                    time.sleep(2)  # givr deletion time to complete
                except Exception as e1:
                    ConvertFromArc.error('Problems encountered removing {0}: {1}.  Trying to continue regardless.'.format(self.qProjDir, str(e1)))
            qProjFile = os.path.join(self.qProjDir, self.qProjName + '.qgs')
            break
        try: 
            ConvertFromArc.makeDirs(self.qProjDir)
        except Exception:
            ConvertFromArc.exceptionError('Failed to create QSWAT+ project directory {0}'.format(self.qProjDir))
            return
        try:
            print('Creating directories ...')
            self.createSubDirectories()
        except Exception:
            ConvertFromArc.exceptionError('Problems creating subdirectories')
            return
#         settings.setValue('/QSWATPlus/LastInputPath', self.qProjDir)
        try:
            print('Copying databases ...')
            self.copyDbs()
        except Exception:
            ConvertFromArc.exceptionError('Problems creating databases or project file: {0}')
            return
        result = self._dlg.exec()
        if result == 0:
            return
        self.createDbTables()
        if self.choice == ConvertFromArc._noGISChoice:
            self.createGISTables()
        else:
            self.proj = QgsProject.instance()
            self.proj.read(qProjFile)
            self.proj.setTitle(self.qProjName)
            # avoids annoying gdal messages
            gdal.UseExceptions()
            print('Copying DEM ...')
            if not self.copyDEM():
                return
            isFull = self.choice == ConvertFromArc._fullChoice
            if not self.createOutletShapefiles(isFull):
                return
            if not isFull: 
                print('Creating existing watershed files ...')
                if not self.createExistingWatershed():
                    return
            self.setDelinParams(isFull)
            print('Copying landuse and soil files ...')
            self.copyLanduseAndSoil()
        print('Writing wgn tables ...')
        self.createWgnTables()
        self.createWeatherData()
        self.createRefTables()
        self.setupTime()
        if self.choice == ConvertFromArc._noGISChoice:
            self.createSoilTables()
            self.createLanduseTables()
            self.createProjectConfig()
        # write fromArc flag to project file
        self.proj.writeEntry(self.qProjName, 'fromArc', self.choice)
        self.proj.write()
        print('Project converted')
        ConvertFromArc.information('ArcSWAT project {0} converted to QSWAT+ project {1} in {2}'.
                                  format(self.arcProjName, self.qProjName, self.qProjDir))
        response = ConvertFromArc.question('Run QGIS on the QSWAT+ project?')
        if response == QMessageBox.Yes:
            osgeo4wroot = os.environ['OSGEO4W_ROOT']
            # print('OSGEO4W_ROOT: {0}'.format(osgeo4wroot))
            gisname = os.environ['GISNAME']
            # print('GISNAME: {0}'.format(gisname))
            command = '{0}/bin/{1}.bat --project "{2}"'.format(osgeo4wroot, gisname, qProjFile)
            subprocess.call(command, shell=True)
 
    def createSubDirectories(self):
        """Create subdirectories under QSWAT+ project's directory."""
        watershedDir = os.path.join(self.qProjDir, 'Watershed')
        ConvertFromArc.makeDirs(watershedDir)
        rastersDir = os.path.join(watershedDir, 'Rasters')
        ConvertFromArc.makeDirs(rastersDir)
        demDir = os.path.join(rastersDir, 'DEM')
        ConvertFromArc.makeDirs(demDir)
        soilDir = os.path.join(rastersDir, 'Soil')
        ConvertFromArc.makeDirs(soilDir)
        landuseDir = os.path.join(rastersDir, 'Landuse')
        ConvertFromArc.makeDirs(landuseDir)
        landscapeDir = os.path.join(rastersDir, 'Landscape')
        ConvertFromArc.makeDirs(landscapeDir)    
        floodDir = os.path.join(landscapeDir, 'Flood')
        ConvertFromArc.makeDirs(floodDir)
        scenariosDir = os.path.join(self.qProjDir, 'Scenarios')
        ConvertFromArc.makeDirs(scenariosDir)
        defaultDir = os.path.join(scenariosDir, 'Default')
        ConvertFromArc.makeDirs(defaultDir)
        txtInOutDir = os.path.join(defaultDir, 'TxtInOut')
        ConvertFromArc.makeDirs(txtInOutDir)
        resultsDir = os.path.join(defaultDir, 'Results')
        ConvertFromArc.makeDirs(resultsDir)
        plotsDir = os.path.join(resultsDir, 'Plots')
        ConvertFromArc.makeDirs(plotsDir)
        animationDir = os.path.join(resultsDir, 'Animation')
        ConvertFromArc.makeDirs(animationDir)
        pngDir = os.path.join(animationDir, 'Png')
        ConvertFromArc.makeDirs(pngDir)
        textDir = os.path.join(watershedDir, 'Text')
        ConvertFromArc.makeDirs(textDir)
        shapesDir = os.path.join(watershedDir, 'Shapes')
        ConvertFromArc.makeDirs(shapesDir)
        csvDir = os.path.join(self.qProjDir, 'csv')
        ConvertFromArc.makeDirs(csvDir)
        projCsvDir = os.path.join(csvDir, 'Project')
        ConvertFromArc.makeDirs(projCsvDir)
        refCsvDir = os.path.join(csvDir, 'Reference')
        ConvertFromArc.makeDirs(refCsvDir)
        
        
    def copyDbs(self):
        """Set up project and reference databases."""
        projDbTemplate = os.path.join(self.SWATPlusDir, r'Databases\QSWATPlusProj2018.sqlite')
        refDbTemplate = os.path.join(self.SWATPlusDir, r'Databases\swatplus_datasets.sqlite')
        projFileTemplate = os.path.join(self.ConvertFromArcDir, 'example.qgs')
        shutil.copy(projDbTemplate, os.path.join(self.qProjDir, self.qProjName + '.sqlite'))
        shutil.copy(refDbTemplate, self.qProjDir)
        shutil.copy(projFileTemplate, os.path.join(self.qProjDir, self.qProjName + '.qgs'))
    
    def copyDEM(self):
        """Copy ESRI DEM as GeoTiff into QSWAT project."""
        inDEM = os.path.join(self.arcProjDir, r'Watershed\Grid\sourcedem\hdr.adf')
        if not os.path.exists(inDEM):
            ConvertFromArc.error('Cannot find DEM {0}'.format(inDEM))
            return False
        outDEM = os.path.join(self.qProjDir, r'Watershed\Rasters\DEM\dem.tif')
        if not ConvertFromArc.copyESRIGrid(inDEM, outDEM):
            return False
        self.demFile = outDEM
        # need to provide a prj
        demLayer = QgsRasterLayer(self.demFile, 'DEM')
        QSWATUtils.writePrj(self.demFile, demLayer)
        self.crs = demLayer.crs()
        # set up transform to lat-long
        crsLatLong = QgsCoordinateReferenceSystem()
        if not crsLatLong.createFromId(4326, QgsCoordinateReferenceSystem.EpsgCrsId):
            QSWATUtils.error('Failed to create lat-long coordinate reference system')
            return False
        
        self.transformToDeg = QgsCoordinateTransform(crsLatLong, self.crs, QgsProject.instance())
        # self.transformToLatLong = QgsCoordinateTransform(self.crsProject, self.crsLatLong, QgsProject.instance())
        return True
        
    @staticmethod
    def copyESRIGrid(inFile, outFile):
        """Copy ESRI grid to GeoTiff."""
        # use GDAL CreateCopy to ensure result is a GeoTiff
        inDs = gdal.Open(inFile, gdal.GA_ReadOnly)
        driver = gdal.GetDriverByName('GTiff')
        outDs = driver.CreateCopy(outFile, inDs, 0)
        if outDs is None or not os.path.exists(outFile):
            ConvertFromArc.error('Failed to create dem in geoTiff format')
            return False
        return True
    
    def createOutletShapefiles(self, isFull):
        """Create inlets\outlets file and extra inlets\outlets file.  Return true if OK.
        
        The inlets/outlets shapefile is created even if not isFull, although it is not recorded in the project file,
        as it might be useful to users if they decide to delineate again.
        """
        if isFull:
            print('Creating inlets/outlets file ...')
        qOutlets = os.path.join(self.qProjDir, r'Watershed\Shapes\out.shp')
        rivsFile = ConvertFromArc.getMaxFileOrDir(os.path.join(self.arcProjDir, r'Watershed\Shapes'), 'riv', '.shp')
        prjFile = os.path.splitext(rivsFile)[0] + '.prj'
        rivsLayer = QgsVectorLayer(rivsFile, 'Rivers', 'ogr')
        rivsFelds = rivsLayer.fields()
        subIndex = rivsFelds.indexOf('Subbasin')
        toNodeIndex = rivsFelds.indexOf('TO_NODE')
        # collect outlet subbasins
        outletSubs = set()
        for river in rivsLayer.getFeatures():
            if river[toNodeIndex] == 0:
                outletSubs.add(river[subIndex])
        fields = ConvertFromArc.makeOutletFields()
        if not ConvertFromArc.makeOutletFile(qOutlets, fields, prjFile):
            return False
        # add main outlets and inlets to outlets file
        qOutletsLayer = QgsVectorLayer(qOutlets, 'Inlets\outlets', 'ogr')
        provider = qOutletsLayer.dataProvider()
        idIndex = provider.fieldNameIndex('ID')
        inletIndex = provider.fieldNameIndex('INLET')
        resIndex = provider.fieldNameIndex('RES')
        ptsrcIndex = provider.fieldNameIndex('PTSOURCE')
        # cannot use monitoring_points shapefile as it omits reservoirs
        # instead use MonitoringPoint.csv stored earlier in csv\Project directory
        idNum = 0
        reservoirs = []
        ptsrcs = []
        subIndex = 11
        typeIndex = 10
        xIndex = 4
        yIndex = 5
        with open(os.path.join(self.qProjDir, r'csv\Project\MonitoringPoint.csv'), 'r', newline='') as f:
            reader = csv.reader(f)
            next(reader) # skip headers
            for row in reader:
                typ = row[typeIndex]
                if typ in ['T', 'O'] or int(row[subIndex]) in outletSubs and typ == 'L':
                    qPt = QgsFeature(fields)
                    qPt.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(row[xIndex]), float(row[yIndex]))))
                    qPt.setAttribute(idIndex, idNum)
                    idNum += 1
                    qPt.setAttribute(inletIndex, 0)
                    qPt.setAttribute(resIndex, 0)
                    qPt.setAttribute(ptsrcIndex, 0)
                    provider.addFeatures([qPt])
                elif typ in ['W', 'I']:
                    qPt = QgsFeature(fields)
                    qPt.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(row[xIndex]), float(row[yIndex]))))
                    qPt.setAttribute(idIndex, idNum)
                    idNum += 1
                    qPt.setAttribute(inletIndex, 1)
                    qPt.setAttribute(resIndex, 0)
                    qPt.setAttribute(ptsrcIndex, 0)
                    provider.addFeatures([qPt])
                elif typ == 'R':
                    reservoirs.append(row)
                elif typ in ['P', 'D']:
                    ptsrcs.append(row)
        self.outletFile = qOutlets
        if not len(reservoirs) == 0 or not len(ptsrcs) == 0:
            # need an extra outlets layer
            # note the file name arcextra.shp is used by delineation.py and by FileTypes in QSWATUtils.py
            # and if changed here must be changed there
            print('Creating reservoirs and point sources file ...')
            qExtra = os.path.join(self.qProjDir, r'Watershed\Shapes\arcextra.shp')
            if not ConvertFromArc.makeOutletFile(qExtra, fields, prjFile, basinWanted=True):
                return False
            qExtraLayer = QgsVectorLayer(qExtra, 'Extra', 'ogr')
            provider = qExtraLayer.dataProvider()
            idIndex = provider.fieldNameIndex('ID')
            inletIndex = provider.fieldNameIndex('INLET')
            resIndex = provider.fieldNameIndex('RES')
            ptsrcIndex = provider.fieldNameIndex('PTSOURCE')
            outSubIndex = provider.fieldNameIndex('Subbasin')
            idNum = 0
            for res in reservoirs:
                qPt = QgsFeature(fields)
                qPt.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(res[xIndex]), float(res[yIndex]))))
                qPt.setAttribute(idIndex, idNum)
                idNum += 1
                qPt.setAttribute(inletIndex, 0)
                qPt.setAttribute(resIndex, 1)
                qPt.setAttribute(ptsrcIndex, 0)
                qPt.setAttribute(outSubIndex, int(res[subIndex]))
                provider.addFeatures([qPt])
            for ptsrc in ptsrcs:
                qPt = QgsFeature(fields)
                qPt.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(ptsrc[xIndex]), float(ptsrc[yIndex]))))
                qPt.setAttribute(idIndex, idNum)
                idNum += 1
                qPt.setAttribute(inletIndex, 1)
                qPt.setAttribute(resIndex, 0)
                qPt.setAttribute(ptsrcIndex, 1)
                qPt.setAttribute(outSubIndex, int(ptsrc[subIndex]))
                provider.addFeatures([qPt])
            self.extraOutletFile = qExtra
        return True
    
    # attempt to use flow accumulation and direction from ArcSWAT to get delineation consistent with ArcSWAT
    # problems:
    # - inlets make it hard to count subbasins (upstream ones missing from ArcSWAT;s subs1.shp)
    # - stream reaches affected similarly by inlets
    # - should snap inlets and outlets - TauDEM move can change subbasin boundaries
    # - still have to match subbasin numbers to ArcSWAT numbering
#===============================================================================
#     def createExistingWatershed(self):
#         """Try to create ArcSWAT watershed using arc's flow direction and accumulation."""
#         # make GeoTiff from flow direction with TauDEM d8 values
#         arcD8File = os.path.join(self.arcProjDir, r'Watershed\Grid\flowdir\hdr.adf')
#         if not os.path.exists(arcD8File):
#             ConvertFromArc.error('Cannot find arc flow direction {0}'.format(arcD8File))
#             return False
#         arcD8Layer = QgsRasterLayer(arcD8File, 'F')
#         threshold = int(arcD8Layer.width() * arcD8Layer.height() * 0.01)
#         entry = QgsRasterCalculatorEntry()
#         entry.bandNumber = 1
#         entry.raster = arcD8Layer
#         entry.ref = 'F@1' 
#         d8File = os.path.join(self.qProjDir, r'Watershed\Rasters\DEM\d8.tif')
#         formula = '("F@1" = 1) + ("F@1" = 128) * 2 + ("F@1" = 64) * 3 + ("F@1" = 32) * 4 + ("F@1" = 16) * 5 + ("F@1" = 8) * 6 + ("F@1" = 4) * 7 + ("F@1" = 2) * 8'
#         calc = QgsRasterCalculator(formula, d8File, 'GTiff', arcD8Layer.extent(), arcD8Layer.width(), arcD8Layer.height(), [entry])
#         result = calc.processCalculation(p=None)
#         if result == 0:
#             assert os.path.exists(d8File), 'QGIS calculator formula {0} failed to write output {1}'.format(formula, d8File)
#             QSWATUtils.copyPrj(self.demFile, d8File)
#         else:
#             ConvertFromArc.error('QGIS calculator formula {0} failed: returned {1}'.format(formula, result), True)
#             return False 
#         arcAd8 = os.path.join(self.arcProjDir, r'Watershed\Grid\flowacc\hdr.adf')
#         if not os.path.exists(arcAd8):
#             ConvertFromArc.error('Cannot find arc flow accumulation {0}'.format(arcAd8))
#             return False
#         ad8File = os.path.join(self.qProjDir, r'Watershed\Rasters\DEM\ad8.tif')
# #         arcAd8Layer = QgsRasterLayer(arcAd8, 'F')
# #         entry.raster = arcAd8Layer
# #         formula = '"F@1"'
# #         calc = QgsRasterCalculator(formula, ad8File, 'GTiff', arcAd8Layer.extent(), arcAd8Layer.width(), arcAd8Layer.height(), [entry])
# #         result = calc.processCalculation(p=None)
# #         if result == 0:
# #             assert os.path.exists(ad8File), 'QGIS calculator formula {0} failed to write output {1}'.format(formula, ad8File)
# #             QSWATUtils.copyPrj(self.demFile, ad8File)
# #         else:
# #             ConvertFromArc.error('QGIS calculator formula {0} failed: returned {1}'.format(formula, result), True)
# #             return False 
#         # use GDAL CreateCopy to ensure result is a GeoTiff
#         inDs = gdal.Open(arcAd8)
#         driver = gdal.GetDriverByName('GTiff')
#         outDs = driver.CreateCopy(ad8File, inDs, 0)
#         if outDs is None or not os.path.exists(ad8File):
#             ConvertFromArc.error('Failed to create flow accumulation in geoTiff format')
#             return False 
#         QSWATUtils.copyPrj(self.demFile, ad8File)
#         # create Dinf slopes
#         (base, suffix) = os.path.splitext(self.demFile)
#         shapesBase = os.path.join(self.qProjDir, r'Watershed\Shapes')
#         numProcesses = 0
#         felFile = base + 'fel' + suffix
#         slpFile = base + 'slp' + suffix
#         angFile = base + 'ang' + suffix
#         ok = TauDEMUtils.runPitFill(self.demFile, felFile, numProcesses, None) 
#         if not ok:
#             ConvertFromArc.error('Failed to create pit filled DEM {0}'.format(felFile))
#             return False
#         ok = TauDEMUtils.runDinfFlowDir(felFile, slpFile, angFile, numProcesses, None)  
#         if not ok:
#             ConvertFromArc.error('Failed to create DInf slopes {0}'.format(slpFile))
#             return  False
#         ok = TauDEMUtils.runAreaD8(d8File, ad8File, self.outletFile, None, numProcesses, None)   
#         if not ok:
#             ConvertFromArc.error('Failed to run area d8 on outlets')
#             return False
#         gordFile = base + 'gord' + suffix
#         plenFile = base + 'plen' + suffix
#         tlenFile = base + 'tlen' + suffix
#         ok = TauDEMUtils.runGridNet(d8File, plenFile, tlenFile, gordFile, self.outletFile, numProcesses, None)  
#         if not ok:
#             ConvertFromArc.error('Failed to create upslope lengths'.format(plenFile))
#             return False
#         # need to mask dem for use with arc d8 and ad8 files
#         demClip = base + 'masked' + suffix
#         d8Layer = QgsRasterLayer(d8File, 'F')
#         entry1 = QgsRasterCalculatorEntry()
#         entry1.bandNumber = 1
#         entry1.raster = d8Layer
#         entry1.ref = 'F@1' 
#         demLayer = QgsRasterLayer(self.demFile, 'D')
#         entry2 = QgsRasterCalculatorEntry()
#         entry2.bandNumber = 1
#         entry2.raster = demLayer
#         entry2.ref = 'D@1' 
#         formula = '("F@1" > 0) * "D@1"'
#         calc = QgsRasterCalculator(formula, demClip, 'GTiff', d8Layer.extent(), d8Layer.width(), d8Layer.height(), [entry1, entry2])
#         result = calc.processCalculation(p=None)
#         if result == 0:
#             assert os.path.exists(demClip), 'QGIS calculator formula {0} failed to write output {1}'.format(formula, demClip)
#             QSWATUtils.copyPrj(self.demFile, demClip)
#         else:
#             ConvertFromArc.error('QGIS calculator formula {0} failed: returned {1}'.format(formula, result))
#             return False 
#         QSWATUtils.copyPrj(self.demFile, demClip)
#         assert os.path.exists(demClip), 'Failed to create clipped raster  {2} by clipping {0} with {1}'.format(self.demFile, d8File, demClip)
#         srcStreamFile = base + 'srcStream' + suffix
#         arcSubsFile = self.getMaxFileOrDir(os.path.join(self.arcProjDir, r'Watershed\Shapes'), 'subs', '.shp')
#         arcSubsLayer = QgsVectorLayer(arcSubsFile, 'Subbasins', 'ogr')
#         numSubs = arcSubsLayer.featureCount()
#         prevLowThreshold = 0
#         prevHighThreshold = threshold * 10
#         while True:
#             ok = TauDEMUtils.runThreshold(ad8File, srcStreamFile, str(threshold), numProcesses, None) 
#             if not ok:
#                 ConvertFromArc.error('Failed to create stream raster {0}'.format(srcStreamFile))
#                 return False
#             outletMovedFile = os.path.splitext(self.outletFile)[0] + '_moved.shp'
#             ok = TauDEMUtils.runMoveOutlets(d8File, srcStreamFile, self.outletFile, outletMovedFile, numProcesses, None)
#             if not ok:
#                 ConvertFromArc.error('Moving outlets to streams failed')
#                 return False
#             ordStreamFile = base + 'ordStream' + suffix
#             streamFile = os.path.join(shapesBase,'stream.shp')
#             treeStreamFile = base + 'treeStream.dat'
#             coordStreamFile = base + 'coordStream.dat'
#             wStreamFile = base + 'wStream' + suffix
#             ok = TauDEMUtils.runStreamNet(demClip, d8File, ad8File, srcStreamFile, outletMovedFile, ordStreamFile, treeStreamFile, coordStreamFile,
#                                               streamFile, wStreamFile, False, numProcesses, None)
#             if not ok:
#                 ConvertFromArc.error('Failed to create stream shapefile {0}'.format(streamFile))
#                 return False
#             QSWATUtils.copyPrj(self.demFile, streamFile)
#             subbasinsLayer = None
#             subbasinsFile = os.path.join(shapesBase, 'subbasins.shp')
#             QSWATUtils.tryRemoveFiles(subbasinsFile)
#             subbasinsLayer = self.createWatershedShapefile(wStreamFile, subbasinsFile)
#             if subbasinsLayer is None:
#                 return False
#             numCreatedSubs = subbasinsLayer.featureCount()
#             print('Threshold {0} produced {1} subbasins: seeking for {2}'.format(threshold, numCreatedSubs, numSubs))
#             if numCreatedSubs < numSubs:
#                 # reduce threshold
#                 prevHighThreshold = threshold
#                 nextThreshold = (prevLowThreshold + threshold) // 2
#             elif numCreatedSubs > numSubs:
#                 # increase threshold
#                 prevLowThreshold = threshold
#                 nextThreshold = (prevHighThreshold + threshold) // 2
#             else:
#                 break
#             if nextThreshold == threshold:
#                 # avoid an endless loop
#                 break
#             threshold = nextThreshold
#         return False
#     
#     def createWatershedShapefile(self, wFile, subbasinsFile):
#         """Create watershed shapefile subbasinsFile from watershed grid wFile."""
#         # create shapes from wFile
#         wDs = gdal.Open(wFile, gdal.GA_ReadOnly)
#         if wDs is None:
#             ConvertFromArc.error('Cannot open watershed grid {0}'.format(wFile), self._gv.isBatch)
#             return None
#         wBand = wDs.GetRasterBand(1)
#         noData = wBand.GetNoDataValue()
#         transform = wDs.GetGeoTransform()
#         numCols = wDs.RasterXSize
#         numRows = wDs.RasterYSize
#         isConnected4 = True
#         shapes = Polygonize(isConnected4, numCols, noData, 
#                             QgsPointXY(transform[0], transform[3]), transform[1], abs(transform[5]))
#         for row in range(numRows):
#             wBuffer = wBand.ReadAsArray(0, row, numCols, 1).astype(int)
#             shapes.addRow(wBuffer.reshape([numCols]), row)
#         shapes.finish()
#         # create shapefile
#         fields = QgsFields()
#         fields.append(QgsField('Basin', QVariant.Int))
#         writer = QgsVectorFileWriter(subbasinsFile, 'CP1250', fields, 
#                                      QGis.WKBMultiPolygon, None, 'ESRI Shapefile')
#         if writer.hasError() != QgsVectorFileWriter.NoError:
#             ConvertFromArc.error('Cannot create subbasin shapefile {0}: {1}'. \
#                              format(subbasinsFile, writer.errorMessage()))
#             return None
#         # need to release writer before making layer
#         writer = None
#         # wFile may not have a .prj (being a .tif) so use DEM's
#         QSWATUtils.copyPrj(self.demFile, subbasinsFile)
#         subbasinsLayer = QgsVectorLayer(subbasinsFile, 'Subbasins', 'ogr')
#         provider = subbasinsLayer.dataProvider()
#         basinIndex = fields.indexFromName('Basin')
#         for basin in shapes.shapes:
#             geometry = shapes.getGeometry(basin)
#             feature = QgsFeature(fields)
#             # basin is a numpy.int32 so we need to convert it to a Python int
#             feature.setAttribute(basinIndex, int(basin))
#             feature.setGeometry(geometry)
#             if not provider.addFeatures([feature]):
#                 ConvertFromArc.error('Unable to add feature to watershed shapefile {0}'. \
#                                  format(subbasinsFile))
#                 return None
#         return subbasinsLayer
#===============================================================================
    
    def createExistingWatershed(self):
        """Make subbasin, watershed and channel shapefiles based on subs1.shp and riv1.shp."""
        # create subbasins shapefile
        arcShapesDir = os.path.join(self.arcProjDir, r'Watershed\Shapes')
        arcSubsFile = ConvertFromArc.getMaxFileOrDir(arcShapesDir, 'subs', '.shp')
        qShapesDir = os.path.join(self.qProjDir, r'Watershed\Shapes')
        QSWATUtils.copyShapefile(arcSubsFile, 'subbasins', qShapesDir)
        qSubsFile = os.path.join(qShapesDir, 'subbasins.shp')
        qSubsLayer = QgsVectorLayer(qSubsFile, 'Subbasins', 'ogr')
        provider = qSubsLayer.dataProvider()
        #provider.addAttributes([QgsField(QSWATTopology._POLYGONID, QVariant.Int)])
        subIndex = provider.fieldNameIndex('Subbasin')
        #polyIndex = provider.fieldNameIndex(QSWATTopology._POLYGONID)
        if not provider.renameAttributes({subIndex : QSWATTopology._POLYGONID}):
            ConvertFromArc.error('Could not edit subbasins shapefile {0}'.format(qSubsFile))
            return False
#         mmap = dict()
#         for f in provider.getFeatures():
#             mmap[f.id()] = {polyIndex : f[subIndex]}
#         if not provider.changeAttributeValues(mmap):
#             ConvertFromArc.error('Could not edit subbasins shapefile {0}'.format(qSubsFile))
#             return False
        self.subbasinsFile = qSubsFile
        # copy subbasins shapefile as watershed shapefile
        QSWATUtils.copyShapefile(qSubsFile, 'wshed', qShapesDir)
        self.wshedFile = os.path.join(qShapesDir, 'wshed.shp')
        # create channels shapefile
        arcRivFile = ConvertFromArc.getMaxFileOrDir(arcShapesDir, 'riv', '.shp')
        QSWATUtils.copyShapefile(arcRivFile, 'channels', qShapesDir)
        # add WSNO, LINKNO, DSLINKNO and Length as copies of Subbasin, FROM_NODE, TO_NODE and Shape_Leng
        # plus Drop as MaxEl - MinEl, or 0 if this is negative
        # plus BasinNo as copy of WSNO
        # (TO_NODE of 0 becomes -1)
        qChanFile = os.path.join(qShapesDir, 'channels.shp')
        qChanLayer = QgsVectorLayer(qChanFile, 'Channels', 'ogr')
        provider = qChanLayer.dataProvider()
        f1 = QgsField(QSWATTopology._LINKNO, QVariant.Int)
        f2 = QgsField(QSWATTopology._DSLINKNO, QVariant.Int)
        f3 = QgsField(QSWATTopology._WSNO, QVariant.Int)
        f4 = QgsField(QSWATTopology._LENGTH, QVariant.Double)
        f5 = QgsField(QSWATTopology._DROP, QVariant.Double)
        f6 = QgsField(QSWATTopology._BASINNO, QVariant.Int)
        provider.addAttributes([f1, f2, f3, f4, f5, f6])
        subIndex = provider.fieldNameIndex('Subbasin')
        fromIndex = provider.fieldNameIndex('FROM_NODE')
        toIndex = provider.fieldNameIndex('TO_NODE')
        arcLenIndex = provider.fieldNameIndex('Shape_Leng')
        minElIndex = provider.fieldNameIndex('MinEl')
        maxElIndex = provider.fieldNameIndex('MaxEl')
        linkIndex = provider.fieldNameIndex(QSWATTopology._LINKNO)
        dsIndex = provider.fieldNameIndex(QSWATTopology._DSLINKNO)
        wsnoIndex = provider.fieldNameIndex(QSWATTopology._WSNO)
        lenIndex = provider.fieldNameIndex(QSWATTopology._LENGTH)
        dropIndex = provider.fieldNameIndex(QSWATTopology._DROP)
        basinIndex = provider.fieldNameIndex(QSWATTopology._BASINNO)
        mmap = dict()
        for f in provider.getFeatures():
            subbasin = f[subIndex]
            toNode = f[toIndex]
            drop = max(0, f[maxElIndex] - f[minElIndex]) # avoid negative drop
            mmap[f.id()] = {wsnoIndex : subbasin,
                            linkIndex : f[fromIndex], 
                            dsIndex : -1 if toNode == 0 else toNode,
                            lenIndex : f[arcLenIndex],
                            dropIndex : drop,
                            basinIndex : subbasin}
        if not provider.changeAttributeValues(mmap):
            ConvertFromArc.error('Could not edit channels shapefile {0}'.format(qChanFile))
            return False
        self.channelsFile = qChanFile
        return True
    
    @staticmethod
    def makeOutletFields():
        """Create fields for outlets file."""
        fields = QgsFields()
        fields.append(QgsField('ID', QVariant.Int))
        fields.append(QgsField('INLET', QVariant.Int))
        fields.append(QgsField('RES', QVariant.Int))
        fields.append(QgsField('PTSOURCE', QVariant.Int))
        return fields
        
    @staticmethod
    def makeOutletFile(filePath, fields, prjFile, basinWanted=False):
        """Create filePath with fields needed for outlets file, 
        copying prjFile.  Return true if OK.
        """
        if os.path.exists(filePath):
            QSWATUtils.removeFiles(filePath)
        if basinWanted:
            fields.append(QgsField('Subbasin', QVariant.Int))
        writer = QgsVectorFileWriter(filePath, 'CP1250', fields, QgsWkbTypes.Point, QgsCoordinateReferenceSystem(), 'ESRI Shapefile')
        if writer.hasError() != QgsVectorFileWriter.NoError:
            ConvertFromArc.error('Cannot create outlets shapefile {0}: {1}'.format(filePath, writer.errorMessage()))
            return False
        writer.flushBuffer()
        shutil.copy(prjFile, os.path.splitext(filePath)[0] + '.prj')
        return True
    
    def setDelinParams(self, isFull):
        """Write delineation parameters to project file."""
        self.proj.writeEntry(self.qProjName, 'delin/existingWshed', not isFull)
        if not isFull:
            self.proj.writeEntry(self.qProjName, 'delin/subbasins', self.proj.writePath(self.subbasinsFile))
            self.proj.writeEntry(self.qProjName, 'delin/channels', self.proj.writePath(self.channelsFile))
            self.proj.writeEntry(self.qProjName, 'delin/wshed', self.proj.writePath(self.wshedFile))
            # provide threshold defaults in case landscapes are requested
            demLayer = QgsRasterLayer(self.demFile, 'DEM')
            threshold = int(demLayer.width() * demLayer.height() * 0.01)
            self.proj.writeEntry(self.qProjName, 'delin/thresholdCh', threshold)
            self.proj.writeEntry(self.qProjName, 'delin/thresholdSt', threshold)
            # check if there is a d8 flow direction file, and copy if so
            arcD8File = os.path.join(self.arcProjDir, r'Watershed\Grid\flowdir\hdr.adf')
            if os.path.isfile(arcD8File):
                # copy to QSWAT+ project 
                base = os.path.splitext(self.demFile)[0]
                ESRIPFile = base + 'arcpesri.tif'
                if ConvertFromArc.copyESRIGrid(arcD8File, ESRIPFile):
                    # now need to convert from ESRI D8 directions to TauDEM
                    ESRIPLayer = QgsRasterLayer(arcD8File, 'F')
                    entry = QgsRasterCalculatorEntry()
                    entry.bandNumber = 1
                    entry.raster = ESRIPLayer
                    entry.ref = 'F@1' 
                    arcPFile = base + 'arcp.tif'
                    formula = '("F@1" = 1) + ("F@1" = 128) * 2 + ("F@1" = 64) * 3 + ("F@1" = 32) * 4 + ("F@1" = 16) * 5 + ("F@1" = 8) * 6 + ("F@1" = 4) * 7 + ("F@1" = 2) * 8'
                    calc = QgsRasterCalculator(formula, arcPFile, 'GTiff', ESRIPLayer.extent(), ESRIPLayer.width(), ESRIPLayer.height(), [entry])
                    result = calc.processCalculation()
                    if result == 0:
                        assert os.path.exists(arcPFile), 'QGIS calculator formula {0} failed to write output {1}'.format(formula, arcPFile)
                        QSWATUtils.copyPrj(self.demFile, arcPFile)
                        self.proj.writeEntry(self.qProjName, 'delin/arcPFile', self.proj.writePath(arcPFile))
                    else:
                        QSWATUtils.error('QGIS calculator formula {0} failed: returned {1}'.format(formula, result), True)
        self.proj.writeEntry(self.qProjName, 'delin/DEM', self.proj.writePath(self.demFile))
        self.proj.writeEntry(self.qProjName, 'delin/useOutlets', isFull)
        if isFull:
            self.proj.writeEntry(self.qProjName, 'delin/outlets', self.proj.writePath(self.outletFile))
        self.proj.writeEntry(self.qProjName, 'delin/extraOutlets', self.proj.writePath(self.extraOutletFile))
        self.proj.write()
    
    def copyLanduseAndSoil(self):
        """Copy landuse and soil rasters, add to project file, read MasterProgress, make lookup csv files."""
        landuseFile = ConvertFromArc.getMaxFileOrDir(os.path.join(self.arcProjDir, r'Watershed\Grid'), 'landuse', '')
        ConvertFromArc.copyFiles(landuseFile, os.path.join(self.qProjDir, r'Watershed\Rasters\Landuse'))
        self.landuseFile = os.path.join(self.qProjDir, r'Watershed\Rasters\Landuse\{0}\hdr.adf'.format(os.path.split(landuseFile)[1]))
        soilFile = ConvertFromArc.getMaxFileOrDir(os.path.join(self.arcProjDir, r'Watershed\Grid'), 'landsoils', '')
        ConvertFromArc.copyFiles(soilFile, os.path.join(self.qProjDir, r'Watershed\Rasters\Soil'))
        self.soilFile = os.path.join(self.qProjDir, r'Watershed\Rasters\Soil\{0}\hdr.adf'.format(os.path.split(soilFile)[1]))
        self.setLanduseAndSoilParams()
        self.generateLookup('landuse')
        if self.soilOption != 'ssurgo':
            self.generateLookup('soil')
            if self.soilOption != 'name':
                self.proj.writeEntry(self.qProjName, 'soil/useSTATSGO', True)
        else:
            self.proj.writeEntry(self.qProjName, 'soil/useSSURGO', True)
        self.proj.write()
        
    def setLanduseAndSoilParams(self):
        """Write landuse and parameters to project file, plus slope limits."""
        self.proj.writeEntry(self.qProjName, 'landuse/file', self.proj.writePath(self.landuseFile))
        self.proj.writeEntry(self.qProjName, 'soil/file', self.proj.writePath(self.soilFile))
        report = os.path.join(self.arcProjDir, r'Watershed\text\LandUseSoilsReport.txt')
        slopeBands = ConvertFromArc.slopeBandsFromReport(report)
        self.proj.writeEntry(self.qProjName, 'hru/slopeBands', slopeBands)
        self.proj.write()
        
    
    def generateLookup(self, landuseOrSoil):
        """Generate lookup table for landuse or soil if required."""
        msgBox = QMessageBox()
        msgBox.setWindowTitle('Generate {0} lookup csv file'.format(landuseOrSoil))
        text = """
        Do you want to generate a {0} lookup csv file in the project directory?
        """.format(landuseOrSoil)
        infoText = """
        If you already have a suitable csv file click No.
        Otherwise click Yes and the tool will attempt to create a csv file 
        called {0}_lookup.csv in the project directory.
        This involves reading the {0} raster and may take a few minutes.
        """.format(landuseOrSoil)
        msgBox.setText(QSWATUtils.trans(text))
        msgBox.setInformativeText(QSWATUtils.trans(infoText))
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        result = msgBox.exec_()
        if result == QMessageBox.Yes:
            print('Creating {0} lookup table ...'.format(landuseOrSoil))
            self.generateCsv(landuseOrSoil)
            
    def generateCsv(self, landuseOrSoil):
        """Generate landuse or soil lookup csv file by comparing percentages from report and raster."""
        percents = self.percentsFromReport(landuseOrSoil)
        if len(percents) == 0:
            return
        if landuseOrSoil == 'landuse':
            raster = self.landuseFile
        else:
            raster = self.soilFile 
        rasterPercents = self.percentsFromRaster(raster)
        if len(rasterPercents) == 0:
            return
        self.makeLookupCsv(percents, rasterPercents, landuseOrSoil)
    
    def percentsFromReport(self, landuseOrSoil):
        """Generate and return map of value to percent for soil or landuse from landuse and soil report."""
        report = os.path.join(self.arcProjDir, r'Watershed\text\LandUseSoilsReport.txt')
        if not os.path.exists(report):
            ConvertFromArc.error('Cannot find {0}'.format(report))
            return dict()
        if landuseOrSoil == 'landuse':
            return ConvertFromArc.landusePercentsFromReport(report)
        else:
            return ConvertFromArc.soilPercentsFromReport(report)
        
    @staticmethod
    def landusePercentsFromReport(report):
        """Return percents of landuses."""
        with open(report, 'r') as reader:
            found = False
            while not found:
                line = reader.readline()
                found = line.startswith('LANDUSE:')
            if not found:
                ConvertFromArc.error('Cannot find "LANDUSE:" in {0}'.format(report)) 
                return dict()
            result = dict()
            while True:
                line = reader.readline()
                start = line.find('-->') + 3
                fields = line[start:].split()
                if len(fields) != 4:
                    break
                landuse = fields[0]
                percent = float(fields[3])
                result[landuse] = percent
            return result
                
    @staticmethod
    def soilPercentsFromReport(report):
        """Return percents of soils."""
        with open(report, 'r') as reader:
            found = False
            while not found:
                line = reader.readline()
                found = line.startswith('SOILS:')
            if not found:
                ConvertFromArc.error('Cannot find "SOILS:" in {0}'.format(report)) 
                return dict()
            result = dict()
            while True:
                line = reader.readline()
                fields = line.split()
                if len(fields) != 4:
                    break
                soil = fields[0]
                percent = float(fields[3])
                result[soil] = percent
            return result
        
    @staticmethod
    def slopeBandsFromReport(report):
        """Extract slope band limits from landuse and soils report."""
        with open(report, 'r') as reader:
            found = False
            while not found:
                line = reader.readline()
                found = line.startswith('SLOPE:')
            if not found:
                ConvertFromArc.error('Cannot find "SLOPE:" in {0}'.format(report)) 
                return '[0, 9999]'
            result = '['
            first = True
            while True:
                line = reader.readline()
                fields = line.split()
                if len(fields) != 4:
                    result += ', 9999]'
                    break
                if first:
                    first = False
                else:
                    result += ', '
                result += fields[0].split('-')[0]
            return result      
    
    def percentsFromRaster(self, raster):
        """Return map of raster values to percents of raster cells with that value."""
        counts = dict()
        total = 0
        ds = gdal.Open(raster, gdal.GA_ReadOnly)
        numRows = ds.RasterYSize
        numCols = ds.RasterXSize
        band = ds.GetRasterBand(1)
        noData = band.GetNoDataValue()
        buff = numpy.empty([1, numCols], dtype=int)
        for row in range(numRows):
            buff = band.ReadAsArray(0, row, numCols, 1)
            for col in range(numCols):
                val = buff[0, col]
                if val == noData:
                    continue
                total += 1
                if val in counts:
                    counts[val] += 1
                else:
                    counts[val] = 1
        # convert counts to percent
        result = dict()
        for val, count in counts.items():
            result[val] = (float(count) / total) * 100
        return result
    
    def makeLookupCsv(self, percents, rasterPercents, landuseOrSoil):
        """
        Make csv file mapping value to category from percents mapping category to percent 
        and raster percents mapping value to percents by matching percents.
        """
        # make ordered lists of pairs (percent, value) and (percent category
        values = ConvertFromArc.mapToOrderedPairs(rasterPercents)
        cats = ConvertFromArc.mapToOrderedPairs(percents)
        # reduce landuse raster values to number from MasterProgress
        if landuseOrSoil == 'landuse' and self.numLuClasses > 0:
            values = values[:self.numLuClasses]
        numValues = len(values)
        numCats = len(cats)
        if numValues != numCats:
            report = os.path.join(self.arcProjDir, r'Watershed\text\LandUseSoilsReport.txt')
            # percentString = ConvertFromArc.percentMapToString(rasterPercents)
            reportFile = os.path.join(self.qProjDir, '{0}_map_percentages.txt'.format(landuseOrSoil))
            with open(reportFile, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([b'Value', b'Percent'])
                for percent, val in values:
                    writer.writerow([b'{0!s}, {1:.2F}'.format(val, percent)])
            ConvertFromArc.error("""
            There are {0!s} {2}s reported in {3} but {1!s} values found in the {2} raster: cannot generate {2} lookup csv file.
            Percentages from raster reported in {4}"""
                                     .format(numCats, numValues, landuseOrSoil, report, reportFile))
            return
        # merge
        csvFile = os.path.join(self.qProjDir, '{0}_lookup.csv'.format(landuseOrSoil))
        with open(csvFile, 'w', newline='') as f:
            writer = csv.writer(f)
            if landuseOrSoil == 'landuse':
                writer.writerow([b'LANDUSE_ID', b'SWAT_CODE'])
            else:
                writer.writerow([b'SOIL_ID', b'SNAM'])
            closeWarn = False
            underOneCount = 0
            for i in range(numValues):
                percent1, val = values[i]
                percent2, cat = cats[i]
                writer.writerow([str(val), str(cat)])
                if percent1 < 1 or percent2 < 1:
                    underOneCount += 1
                if abs(percent1 - percent2) > 1:
                    ConvertFromArc.information('Warning: percents {0:.1F}% and {1:.1F}% for {2} not very close'
                                               .format(percent1, percent2, cat))
                if not closeWarn and i > 0 and abs(percent2 - cats[i-1][0]) < 1:
                    closeWarn = True # avoid many wornings
                    ConvertFromArc.information('Warning: percents {0:.1F}% and {1:.1F}% for {2} and {3} are close'
                                              .format(percent2, cats[i-1][0], cat, cats[i-1][1]))
            if underOneCount > 1:
                ConvertFromArc.information('Warning: {0} percentages for {1} were less than 1'.format(underOneCount, landuseOrSoil))
     
    @staticmethod               
    def percentMapToString(mmap):
        """Convert map of int -> float to string, using 2 decimal places."""
        result = '{'
        numItems = len(mmap)
        count = 0
        for val, percent in mmap.items():
            result += '{0!s}: {1:.2F}'.format(val, percent)
            count += 1
            if count == numItems:
                result += '}'
            else:
                result += ', '    
        return result
                    
    def createDbTables(self):
        """Create gis_landexempt, gis_splithrus and gis_elevationbands tables,
        creates MonitoringPoint.csv,
        and reads MasterProgress table to set number of landuse classes and soil option.
        Also reads Reach, hrus and Watershed if no GIS option selected.
        
        This is a 64-bit program for which there is no Access driver.
        Instead use the AccessToCSV program to write csv files which are then read."""
        projCsvDir = os.path.join(self.qProjDir, r'csv\Project')
        arcProjDb = os.path.join(self.arcProjDir, self.arcProjName + '.mdb')
        # extract csv files 
        toolPath = os.path.join(self.ConvertFromArcDir, 'AccessToCSV.exe')
        args = [toolPath, arcProjDb, 'LuExempt', 'SplitHrus', 'ElevationBand', 'MasterProgress', 'MonitoringPoint']
        if self.choice == ConvertFromArc._noGISChoice:
            args.extend(['Reach', 'hrus', 'Watershed'])
        subprocess.run(args, cwd=projCsvDir)
        qProjDb = os.path.join(self.qProjDir, self.qProjName + '.sqlite')
        with sqlite3.connect(qProjDb) as qConn:
            qCursor = qConn.cursor()
            csvFile = os.path.join(projCsvDir, 'LuExempt.csv')
            if os.path.exists(csvFile):
                first = True
                with open(csvFile, 'r', newline='') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if first:
                            first = False
                            qTable = 'gis_landexempt'
                            qCursor.execute('DROP TABLE IF EXISTS {0}'.format(qTable))
                            qCursor.execute(DBUtils._LANDEXEMPTCREATESQL)
                        else:
                            qCursor.execute(DBUtils._LANDEXEMPTINSERTSQL, tuple(row[1:]))
            csvFile = os.path.join(projCsvDir, 'SplitHrus.csv')
            if os.path.exists(csvFile):
                first = True
                with open(csvFile, 'r', newline='') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if first:
                            first = False
                            qTable = 'gis_splithrus'
                            qCursor.execute('DROP TABLE IF EXISTS {0}'.format(qTable))
                            qCursor.execute(DBUtils._SPLITHRUSCREATESQL)
                        else:
                            qCursor.execute(DBUtils._SPLITHRUSINSERTSQL, tuple(row[1:]))
            csvFile = os.path.join(projCsvDir, 'ElevationBand.csv')
            if os.path.exists(csvFile):
                first = True
                with open(csvFile, 'r', newline='') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if first:
                            first = False
                            qTable = 'gis_elevationbands'
                            qCursor.execute('DROP TABLE IF EXISTS {0}'.format(qTable))
                            qCursor.execute('CREATE TABLE ' + qTable + DBUtils._ELEVATIONBANDSTABLE)
                            insertSql = 'INSERT INTO {0} VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'.format(qTable)
                        else:
                            qCursor.execute(insertSql, tuple(row[1:]))
            qConn.commit()
        csvFile = os.path.join(projCsvDir, 'MasterProgress.csv')
        if os.path.exists(csvFile):
            with open(csvFile, 'r', newline='') as f:
                # skip header line
                f.readline()
                data = f.readline().split(',')
                self.soilOption = data[6]
                self.numLuClasses = int(data[7])
            
    def createRefTables(self):
        """Create tables from crop, fert, pest, till, septwq, and urban tables, plus usersoil if needed, in project database."""
        print('Writing reference tables ...')
        qProjDb = os.path.join(self.qProjDir, self.qProjName + '.sqlite')
        arcRefDb = os.path.join(self.arcProjDir, 'SWAT2012.mdb')
        # extract csv files 
        toolPath = os.path.join(self.ConvertFromArcDir, 'AccessToCSV.exe')
        args = [toolPath, arcRefDb, 'crop', 'fert', 'pest', 'septwq', 'till', 'urban']
        if self.soilOption == 'name':
            args.append('usersoil')
        refCsvDir = os.path.join(self.qProjDir, r'csv\Reference')
        subprocess.run(args, cwd=refCsvDir)
        with sqlite3.connect(qProjDb) as qConn:
            cursor = qConn.cursor()
            self.createPlantTable(cursor, refCsvDir)
            self.createFertTable(cursor, refCsvDir)
            self.createPestTable(cursor, refCsvDir)
            self.createSeptTable(cursor, refCsvDir)
            self.createTillTable(cursor, refCsvDir)
            self.createUrbanTable(cursor, refCsvDir)
            if self.soilOption == 'name':
                self.creatUsersoilTable(cursor, refCsvDir)
            qConn.commit()
            
    def createPlantTable(self, cursor, refCsvDir):
        """Create arc_plant in project database."""
        cropFile = os.path.join(refCsvDir, 'crop.csv')
        if not os.path.isfile(cropFile):
            return
        table = 'arc_plant'
        cursor.execute('DROP TABLE IF EXISTS {0}'.format(table))
        cursor.execute('CREATE TABLE ' + table + DBUtils._PLANTTABLE)
        sql = 'INSERT INTO {0} VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'.format(table)
        num = 0
        with open(cropFile, 'r', newline='') as f:
            reader = csv.reader(f)
            next(reader)  # skip headers
            for row in reader:
                num += 1
                self.writePlantRow(num, row, cursor, sql)
            
    def createFertTable(self, cursor, refCsvDir):
        """Create arc_fert in project database."""
        fertFile = os.path.join(refCsvDir, 'fert.csv')
        if not os.path.isfile(fertFile):
            return
        table = 'arc_fert'
        cursor.execute('DROP TABLE IF EXISTS {0}'.format(table))
        cursor.execute('CREATE TABLE ' + table + ConvertFromArc._FERTILIZERTABLE)
        sql = 'INSERT INTO {0} VALUES(?,?,?,?,?,?,?,?,?)'.format(table)
        num = 0
        with open(fertFile, 'r', newline='') as f:
            reader = csv.reader(f)
            next(reader)  # skip headers
            for row in reader:
                num += 1
                self.writeFertRow(num, row, cursor, sql)
            
    def createPestTable(self, cursor, refCsvDir):
        """Create arc_pest in project database."""
        pestFile = os.path.join(refCsvDir, 'pest.csv')
        if not os.path.isfile(pestFile):
            return
        table = 'arc_pest'
        cursor.execute('DROP TABLE IF EXISTS {0}'.format(table))
        cursor.execute('CREATE TABLE ' + table + ConvertFromArc._PESTICIDETABLE)
        sql = 'INSERT INTO {0} VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'.format(table)
        num = 0
        with open(pestFile, 'r', newline='') as f:
            reader = csv.reader(f)
            next(reader)  # skip headers
            for row in reader:
                num += 1
                self.writePestRow(num, row, cursor, sql)
            
    def createSeptTable(self, cursor, refCsvDir):
        """Create arc_septwq in project database."""
        septwqFile = os.path.join(refCsvDir, 'septwq.csv')
        if not os.path.isfile(septwqFile):
            return
        table = 'arc_septwq'
        cursor.execute('DROP TABLE IF EXISTS {0}'.format(table))
        cursor.execute('CREATE TABLE ' + table + ConvertFromArc._SEPTICTABLE)
        sql = 'INSERT INTO {0} VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)'.format(table)
        num = 0
        with open(septwqFile, 'r', newline='') as f:
            reader = csv.reader(f)
            next(reader)  # skip headers
            for row in reader:
                num += 1
                self.writeSeptRow(num, row, cursor, sql)
            
    def createTillTable(self, cursor, refCsvDir):
        """Create arc_till in project database."""
        tillFile = os.path.join(refCsvDir, 'till.csv')
        if not os.path.isfile(tillFile):
            return
        table = 'arc_till'
        cursor.execute('DROP TABLE IF EXISTS {0}'.format(table))
        cursor.execute('CREATE TABLE ' + table + ConvertFromArc._TILLAGETABLE)
        sql = 'INSERT INTO {0} VALUES(?,?,?,?,?,?,?,?)'.format(table)
        num = 0
        with open(tillFile, 'r', newline='') as f:
            reader = csv.reader(f)
            next(reader)  # skip headers
            for row in reader:
                num += 1
                self.writeTillRow(num, row, cursor, sql)
            
    def createUrbanTable(self, cursor, refCsvDir):
        """Create arc_urban in project database."""
        urbanFile = os.path.join(refCsvDir, 'urban.csv')
        if not os.path.isfile(urbanFile):
            return
        table = 'arc_urban'
        cursor.execute('DROP TABLE IF EXISTS {0}'.format(table))
        cursor.execute('CREATE TABLE ' + table + DBUtils._URBANTABLE)
        sql = 'INSERT INTO {0} VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)'.format(table)
        num = 0
        with open(urbanFile, 'r', newline='') as f:
            reader = csv.reader(f)
            next(reader)  # skip headers
            for row in reader:
                num += 1
                self.writeUrbanRow(num, row, cursor, sql)
            
    def createUsersoilTable(self, cursor, refCsvDir):
        """Create arc_usersoil in project database."""
        usersoilFile = os.path.join(refCsvDir, 'usersoil.csv')
        if not os.path.isfile(usersoilFile):
            return
        table = 'arc_usersoil'
        cursor.execute('DROP TABLE IF EXISTS {0}'.format(table))
        cursor.execute('CREATE TABLE ' + table + DBUtils._USERSOILTABLE)
        sql = 'INSERT INTO usersoil VALUES(' + ','.join(['?']*152) + ')'
        with open(usersoilFile, 'r', newline='') as f:
            reader = csv.reader(f)
            next(reader)  # skip headers
            for row in reader:
                cursor.execute(sql, tuple(row))
         
    def writePlantRow(self, num, row, cursor, sql):
        """Write values from row of crop table using cursor and sql, using num for the first element.
        
        SWAT crop - QSWAT plant_lt relation (column numbers are zero-based)
        SWAT crop                              QSWAT plants_plt
        2 CPNM                                 1 name
        3 IDC                                  2 plnt_typ
        -                                      3 gro_tri (default 'temp_gro')
        -                                      4 nfix_co (default 0)
        -                                      5 days_mat
        5 BIO_E                                6  bm_e
        ...                                    ...
        12 DLAI                                13 hu_lai:decl
        -                                      14 dlai_rate   (default 1)
        13 CHTMX                               15 can_ht_max
        ...                                    ...
        33 RSDCO_PL                            35 plnt_decomp
        40 ALAI_MIN                            36 lai_min
        ...                                    ...
        44 EXT_COEF                            40 ext_co
        -                                      41 leaf_tov_mn  (defuult 12)
        -                                      42 leaf_tov_mx  (defuult 3)
        45 BM_DIEOFF                           43 bm_dieoff
        -                                      44 rt_st_beg  (defuult 0)
        -                                      45 rt_st_end  (defuult 0)
        -                                      46 plnt_pop1  (defuult 0)
        -                                      47 frac_lai1  (defuult 0)
        -                                      48 plnt_pop2  (defuult 0)
        -                                      49 frac_lai2  (defuult 0)
        -                                      50 frac_sw_gro  (defuult 0.5)
        -                                      51 wnd_live  (defuult 0)
        -                                      52 wnd_dead  (defuult 0)
        -                                      53 wnd_flat  (defuult 0)
        4 CROPNAME                             54 description  
        """
        idc = int(row[3])
        daysMat = 120 if idc == 4 or idc == 5 else 365
        data = (num, row[2].lower(), row[3], 'temp_gro', 0, daysMat) + tuple(row[5:13]) + (1,) + \
                tuple(row[13:34]) + tuple(row[40:45]) + (12, 3, row[45], 0, 0, 0, 0, 0, 0, 0.5, 0, 0, 0, row[4])
        cursor.execute(sql, data)
            
    def writeFertRow(self, num, row, cursor, sql):
        """Write values from row of fert table using cursor and sql, using num for the first element."""
        # columns 1-10 of new table same as columns 2:11 of fert
        data = (num, row[2].lower()) + tuple(row[3:8]) + ('', row[11])
        cursor.execute(sql, data)
            
    def writePestRow(self, num, row, cursor, sql):
        """Write values from row of pest table using cursor and sql, using num for the first element."""
        data = (num, row[2].lower()) + tuple(row[3:7]) + (row[8], 0, 0, 0, 0, 0, 0, 0, 0, row[10])
        cursor.execute(sql, data)
            
    def writeSeptRow(self, num, row, cursor, sql):
        """Write values from row of septwq table using cursor and sql, using num for the first element."""
        data = (num, row[1].lower()) + tuple(row[4:7]) + tuple(row[8:12]) + tuple(row[13:16]) + (row[2],)
        cursor.execute(sql, data)
            
    def writeTillRow(self, num, row, cursor, sql):
        """Write values from row of till table using cursor and sql, using num for the first element."""
        data = (num, row[2].lower()) + tuple(row[3:5]) + (row[7], 0, 0, row[5])
        cursor.execute(sql, data)
            
    def writeUrbanRow(self, num, row, cursor, sql):
        """Write values from row of urban table using cursor and sql, using num for the first element."""
        # columns 2-10 of new table same as columns 4-12 of urban
        data = (num, row[2].lower()) + tuple(row[4:13]) + (row[18], row[3])
        cursor.execute(sql, data)
        
    def createSoilTables(self):
        """Write soils_sol and soils_sol_layer tables."""
        print('Writing soil tables ...')
        splitSTATSGO = False
        if self.soilOption == 'name':
            table = 'arc_usersoil'
            layerTable = ''
            soilDb = os.path.join(self.qProjDir, self.qProjName + '.sqlite')
            selectSql = 'SELECT * FROM arc_usersoil WHERE SNAM=?'
        else:
            soilDb = os.path.join(self.SWATPlusDir, r'Databases\swatplus_soils.sqlite')
            if self.soilOption == 'ssurgo':
                table = 'ssurgo'
                layerTable = 'ssurgo_layer'
                selectSql = 'SELECT * FROM ssurgo WHERE muid=?'
            else:
                table = 'statsgo'
                layerTable = 'statsgo_layer'
                if self.soilOption == 'stmuid':
                    selectSql = 'SELECT * FROM statsgo WHERE muid=?'
                elif self.soilOption == 'stmuid+seqnum':
                    selectSql = 'SELECT * FROM statsgo WHERE muid=? AND seqn=?'
                    splitSTATSGO = True
                elif self.soilOption == 'stmuid+name':
                    selectSql = 'SELECT * FROM statsgo WHERE muid=? AND name=?'
                    splitSTATSGO = True
                elif self.soilOption == 's5id':
                    selectSql = 'SELECT * FROM statsgo WHERE s5id=?'
                else:
                    ConvertFromArc.error('Unknown soil option {0}: cannot wrtite soil tables'.format(self.soilOption))
                    return
            sqlLayer = 'SELECT * FROM {0} WHERE soil_id=? ORDER BY layer_num'.format(layerTable)
        projDb = os.path.join(self.qProjDir, self.qProjName + '.sqlite')
        with sqlite3.connect(projDb) as writeConn:
            writeCursor = writeConn.cursor()
            sql = 'DROP TABLE IF EXISTS {0}'.format(DBUtils._SOILS_SOL_NAME)
            writeCursor.execute(sql)
            sql = 'CREATE TABLE {0} {1}'.format(DBUtils._SOILS_SOL_NAME, DBUtils._SOILS_SOL_TABLE)
            writeCursor.execute(sql)
            sql = 'DROP TABLE IF EXISTS {0}'.format(DBUtils._SOILS_SOL_LAYER_NAME)
            writeCursor.execute(sql)
            sql = 'CREATE TABLE {0} {1}'.format(DBUtils._SOILS_SOL_LAYER_NAME, DBUtils._SOILS_SOL_LAYER_TABLE)
            writeCursor.execute(sql)
            insert = 'INSERT INTO {0} VALUES(?,?,?,?,?,?,?,?)'.format(DBUtils._SOILS_SOL_NAME)
            insertLayer = 'INSERT INTO {0} VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'.format(DBUtils._SOILS_SOL_LAYER_NAME)
            with sqlite3.connect(soilDb) as readConn:
                readCursor = readConn.cursor()
                sid = 0 # last soil id used
                lid = 0 # last layer id used
                for soil in self.usedSoils:
                    if splitSTATSGO:
                        args = (soil[:5], soil[6:])  # note the plus sign must be skipped
                    else:
                        args = (soil,)
                    row = readCursor.execute(selectSql, args).fetchone()
                    if row is None:
                        ConvertFromArc.error('Soil name {0} (and perhaps others) not defined in {1} table in database {2}.  {3} table not written.'.
                                         format(soil, table, soilDb, DBUtils._SOILS_SOL_NAME))
                        return
                    sid += 1
                    if layerTable == '':
                        lid = self.writeUsedSoilRow(sid, lid, soil, row, writeCursor, insert, insertLayer)
                    else:
                        lid = self.writeUsedSoilRowSeparate(sid, lid, soil, row, writeCursor, insert, insertLayer, readCursor, sqlLayer, layerTable)
            writeConn.commit()
    
    @staticmethod                    
    def writeUsedSoilRow(sid, lid, name, row, cursor, insert, insertLayer):
        """Write data from one row of usersoil table to soils_sol and soils_sol_layer tables."""
        cursor.execute(insert, (sid, name) + row[7:12] + (None,))
        startLayer1 = 12 # index of SOL_Z1
        layerWidth = 12 # number of entries per layer
        startCal = 132 # index of SOL_CAL1
        startPh = 142 # index of SOL_PH1
        for i in range(int(row[6])):
            lid += 1 
            startLayer = startLayer1 + i*layerWidth
            cursor.execute(insertLayer, (lid, sid, i+1) +  row[startLayer:startLayer+layerWidth] +  (row[startCal+i], row[startPh+i]))
        return lid 
          
    @staticmethod        
    def writeUsedSoilRowSeparate(sid, lid, name, row, cursor, insert, insertLayer, readCursor, sqlLayer, layerTable):
        """Write data from one row of usersoil table plus separate layer table 
        to soils_sol and soils_sol_layer tables.
        """
        # check whether there is a non-null description item
        if len(row) == 11:
            cursor.execute(insert, (sid, name) +  row[6:] + (None,))
        else:
            cursor.execute(insert, (sid, name) +  row[6:])
        layerRows = readCursor.execute(sqlLayer, (row[0],)).fetchall()
        if layerRows is None:
            ConvertFromArc.error('Failed to find soil layers in table {0} with soil_id {1}'.
                             format(layerTable, row[0]))
            return lid
        for ro in layerRows:
            lid += 1
            cursor.execute(insertLayer, (lid, sid) + ro[2:])
        return lid
    
    def createLanduseTables(self):
        """Write plants_plt and urban_urb tables."""
        print('Writing landuse tables ...')
        qProjDb = os.path.join(self.qProjDir, self.qProjName + '.sqlite')
        with sqlite3.connect(qProjDb) as projConn:
            projCursor = projConn.cursor()
            projCursor.execute('DROP TABLE IF EXISTS {0}'.format(DBUtils._URBAN_URB_NAME))
            projCursor.execute('DROP TABLE IF EXISTS {0}'.format(DBUtils._PLANTS_PLT_NAME))
            projCursor.execute('CREATE TABLE {0} {1}'.format(DBUtils._URBAN_URB_NAME, DBUtils._URBAN_URB_TABLE))
            projCursor.execute('CREATE TABLE {0} {1}'.format(DBUtils._PLANTS_PLT_NAME, DBUtils._PLANTS_PLT_TABLE))
            uNum = 0
            pNum = 0
            for landuse in self.usedLanduses:
                landuse = landuse.lower()
                if landuse.startswith('u'):
                    readTable = 'arc_urban'
                    uNum += 1
                    num = uNum
                    insert = 'INSERT INTO {0} VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)'.format(DBUtils._URBAN_URB_NAME)
                else:
                    readTable = 'arc_plant'
                    pNum += 1
                    num = pNum
                    insert = 'INSERT INTO {0} VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'. \
                            format(DBUtils._PLANTS_PLT_NAME)
                sql = 'SELECT * FROM {0} WHERE name=?'.format(readTable)
                row = projCursor.execute(sql, (landuse,)).fetchone()
                if row is None:
                    ConvertFromArc.error('Cannot find landuse {0} in table {1} in {2}'
                                         .format(landuse, readTable, qProjDb))
                else:
                    projCursor.execute(insert, (num,) + tuple(row[1:]))
            projConn.commit()
        
    
    def createProjectConfig(self):
        """Write project_config table to project database."""
        qProjDb = self.qProjName + '.sqlite'
        with sqlite3.connect(os.path.join(self.qProjDir, qProjDb)) as conn:
            cursor = conn.cursor()
            qRefDb = os.path.join(self.qProjDir, 'swatplus_datasets.sqlite')
            weatherDataDir = os.path.join(self.qProjDir, r'Scenarios\Default\TxtInOut')
            gisType = 'qgis'
            gisVersion = QSWATPlus.__version__
            cursor.execute('DROP TABLE IF EXISTS project_config')
            cursor.execute(DBUtils._CREATEPROJECTCONFIG)
            cursor.execute(DBUtils._INSERTPROJECTCONFIG, 
                           (1, self.qProjName, self.qProjDir, None, 
                            gisType, gisVersion, qProjDb, qRefDb, None, None, weatherDataDir, None, None, None, None, 
                            1, 1, DBUtils._SOILS_SOL_NAME, DBUtils._SOILS_SOL_LAYER_NAME, None, 0, 0))
            conn.commit()
            
    def createWgnTables(self):
        """Create tables wgn and wgn_mon in project database from ArcSWAT TxtInOut wgn files."""
        self.wgnStations = dict()
        qProjDb = os.path.join(self.qProjDir, self.qProjName + '.sqlite')
        pattern = os.path.join(self.arcProjDir, r'Scenarios\Default\TxtInOut\*.wgn')
        stationNames = set()
        stationId = 0
        monId = 0
        with sqlite3.connect(qProjDb) as qConn:
            cursor = qConn.cursor()
            cursor.execute('DROP TABLE IF EXISTS weather_wgn_cli')
            cursor.execute(ConvertFromArc._CREATEWGN)
            cursor.execute('DROP TABLE IF EXISTS weather_wgn_cli_mon')
            cursor.execute(ConvertFromArc._CREATEWGNMON)
            for f in glob.iglob(pattern):
                with open(f, 'r') as wgnFile:
                    header = wgnFile.readline().split()
                    stationName = header[5][5:]
                    if stationName not in stationNames:
                        stationNames.add(stationName)
                        stationId += 1
                        fields = wgnFile.readline().split()
                        latitude = float(fields[2])
                        longitude = float(fields[5])
                        fields = wgnFile.readline().split()
                        elev = float(fields[3])
                        fields = wgnFile.readline().split()
                        rainYears = int(float(fields[2]))
                        cursor.execute(ConvertFromArc._INSERTWGN, 
                                       (stationId, stationName, latitude, longitude, elev, rainYears))
                        self.wgnStations[stationId] = (latitude, longitude)
                        arr = numpy.empty([14, 12], dtype=float)
                        for row in range(14):
                            vals = wgnFile.readline().split()
                            arr[row,:] = tuple(vals)
                        for col in range(12):
                            monId += 1
                            cursor.execute(ConvertFromArc._INSERTWGNMON, 
                                           (monId, stationId, col+1) + tuple(arr[:,col].astype(float).tolist()))
            qConn.commit()
                        
    def createWeatherData(self):
        """Create weather tables and files from ArcSWAT TxtInOut weather files."""
        qProjDb = os.path.join(self.qProjDir, self.qProjName + '.sqlite')
        arcTxtInOutDir = os.path.join(self.arcProjDir, r'Scenarios\Default\TxtInOut')
        qTextInOutDir = os.path.join(self.qProjDir, r'Scenarios\Default\TxtInOut')
        pcpFile = os.path.join(arcTxtInOutDir, 'pcp1.pcp')
        tmpFile = os.path.join(arcTxtInOutDir, 'tmp1.tmp')
        slrFile = os.path.join(arcTxtInOutDir, 'slr1.slr')
        hmdFile = os.path.join(arcTxtInOutDir, 'hmd1.hmd')
        wndFile = os.path.join(arcTxtInOutDir, 'wnd1.wnd')
        with sqlite3.connect(qProjDb) as qConn:
            cursor = qConn.cursor()
            cursor.execute('DROP TABLE IF EXISTS weather_file')
            cursor.execute(ConvertFromArc._CREATEWEATHERFILE)
            cursor.execute('DROP TABLE IF EXISTS weather_sta_cli')
            cursor.execute(ConvertFromArc._CREATEWEATHERSTATION)
            stationId = 0
            if os.path.isfile(pcpFile):
                stationId = self.createWeatherTypeData(stationId, 'pcp', 'precipitation', arcTxtInOutDir, qTextInOutDir, cursor)
            if os.path.isfile(tmpFile):
                stationId = self.createWeatherTypeData(stationId, 'tmp', 'temperature', arcTxtInOutDir, qTextInOutDir, cursor)
            if os.path.isfile(slrFile):
                stationId = self.createWeatherTypeData(stationId, 'slr', 'solar radiation', arcTxtInOutDir, qTextInOutDir, cursor)
            if os.path.isfile(hmdFile):
                stationId = self.createWeatherTypeData(stationId, 'hmd', 'relative humidity', arcTxtInOutDir, qTextInOutDir, cursor)
            if os.path.isfile(wndFile):
                stationId = self.createWeatherTypeData(stationId, 'wnd', 'wind speed', arcTxtInOutDir, qTextInOutDir, cursor)
            qConn.commit()
            
    def createWeatherTypeData(self, lastId, typ, descr, arcTxtInOutDir, qTxtInOutDir, cursor):
        """Create typ data files files from ArcSWAT TxtInOut files.  Return last stationId used."""
        print('Writing {0} data ...'.format(descr))
        stations = dict()
        infileNum = 0
        stationCount = 0
        now = datetime.datetime.now()
        timeNow = now.strftime("%Y-%m-%d %H:%M")
        staFile = os.path.join(qTxtInOutDir, '{0}.cli'.format(typ))
        with open(staFile, 'w') as staF:
            staF.write('{0}.cli : {1} file names - file written by ConvertFromArc {2}\n'.format(typ, descr, timeNow))
            staF.write('filename\n')
            stationNamesToSort = []
            while True:
                infileNum += 1
                inFile = os.path.join(arcTxtInOutDir, '{1}{0!s}.{1}'.format(infileNum, typ))
                if not os.path.isfile(inFile):
                    break
                with open(inFile, 'r') as f:
                    stationNames = f.readline()[8:].split(',') # skip 'Station ' at start of header
                    for name in stationNames:
                        name = name.strip()
                        if name != '': # there is a trailing comma in header, so last station is empty
                            # make new list of stripped names (so can be properly sorted later: may have leading blanks)
                            stationNamesToSort.append(name)
                            stationCount += 1
                            station = ConvertFromArc.WeatherStation(name, typ)
                            stations[stationCount] = station
                    if typ == 'tmp':
                        width = 10
                        numWidth = 5
                    else:
                        width = 5
                    latitudes = f.readline()
                    for i in range(stationCount):
                        start = 7 + width * i
                        stations[i+1].latitude = float(latitudes[start:start+width])
                    longitudes = f.readline()
                    for i in range(stationCount):
                        start = 7 + width * i
                        stations[i+1].longitude = float(longitudes[start:start+width])
                    elevations = f.readline()
                    for i in range(stationCount):
                        start = 7 + width * i
                        stations[i+1].elevation = float(elevations[start:start+width])
                    # write stations to project database
                    for stationId, station in stations.items():
                        self.writeWeatherStation(lastId+stationId, station, cursor)
                    # collect data in arrays
                    dates = []
                    data = []
                    while True:
                        line = f.readline()
                        if line == '':
                            break
                        dates.append(line[:7])
                        if typ == 'tmp':
                            nextData = [(float(line[start:start+numWidth]),
                                         float(line[start+numWidth:start+width])) 
                                         for start in [7+width*i for i in range(stationCount)]]
                        else:
                            nextData = [float(line[start:start+width]) for start in [7+width*i for i in range(stationCount)]]
                        data.append(nextData)
                    # write files
                    for i in range(stationCount):
                        stationId = i+1
                        station = stations[stationId]
                        fileName = '{0}.{1}'.format(station.name, typ)
                        outFile = os.path.join(qTxtInOutDir, fileName)
                        with open(outFile, 'w') as f:
                            f.write('{0}: {2} data - file written by ConvertFromArc {1}\n'
                                    .format(fileName, timeNow, descr))
                            f.write('nbyr     tstep       lat       lon      elev\n')
                            firstYear = int(dates[0][:4])
                            lastYear = int(dates[-1][:4])
                            numYears = lastYear - firstYear + 1
                            f.write(str(numYears).rjust(4))
                            f.write('0'.rjust(10)) # TODO: time step 
                            f.write('{0:.3F}'.format(station.latitude).rjust(10))
                            f.write('{0:.3F}'.format(station.longitude).rjust(10))
                            f.write('{0:.3F}\n'.format(station.elevation).rjust(11))
                            row = 0
                            for date in dates:
                                f.write(date[:4])
                                f.write(str(int(date[4:])).rjust(5))
                                if typ == 'tmp':
                                    maxx, minn = data[row][i]
                                    f.write('{0:.1F}'.format(maxx).rjust(10))
                                    f.write('{0:.1F}\n'.format(minn).rjust(10))
                                else:
                                    f.write('{0:.1F}\n'.format(data[row][i]).rjust(9))
                                row += 1
            # write weather station file names in staFile, in sorted order
            for name in sorted(stationNamesToSort):
                staF.write('{0}.{1}\n'.format(name, typ))
            return lastId + stationCount
                            
    def writeWeatherStation(self, staId, station, cursor):
        """Wtite entries for station in weather_file and weather_sta_cli. """
        fileName = '{0}.{1}'.format(station.name, station.typ)
        cursor.execute(ConvertFromArc._INSERTWEATHERFILE, 
                       (staId, fileName, station.typ,
                        station.latitude, station.longitude))
        indx = ['pcp', 'tmp', 'slr', 'hmd', 'wnd'].index(station.typ)
        files = ['sim', 'sim', 'sim', 'sim', 'sim', 'sim', 'sim']
        files[indx] = fileName
        wgnId = self.nearestWgn(station.latitude, station.longitude)
        cursor.execute(ConvertFromArc._INSERTWEATHERSTATION, 
                       (staId, station.name, wgnId) + tuple(files) + (station.latitude, station.longitude))
                            
    def nearestWgn(self, lat, lon):
        """Return nearest wgn station id, or -1 if none.
        
        Uses sum of squares of latitude and longitude differences as the measure of proximity."""
        result = -1
        currentMeasure = 64800  # 2 * 180 * 180  :  maximum possible value
        for stationId, (latitude, longitude) in self.wgnStations.items():
            latDiff = latitude - lat
            lonDiff = abs(longitude - lon)
            # allow for either side of date line
            if lonDiff > 180:
                lonDiff = 360 - lonDiff 
            measure = latDiff * latDiff + lonDiff * lonDiff
            if measure < currentMeasure:
                currentMeasure = measure
                result = stationId
        return result
    
    def createGISTables(self):
        """Create gis_channels, _lsus, _points, _routing, _subbasins and _water 
        from csv files made from ArcSWAT project database"""
        # subasin - reach relation is 1-1, so use same number for each
        downstreamSubbasin = dict()
        qProjDb = os.path.join(self.qProjDir, self.qProjName + '.sqlite')
        with sqlite3.connect(qProjDb) as conn:
            cursor = conn.cursor()
            # gis_channels
            cursor.execute('DROP TABLE IF EXISTS gis_channels')
            cursor.execute(ConvertFromArc._CREATECHANNELS)
            with open(os.path.join(self.qProjDir, r'csv\Project\Reach.csv'), 'r', newline='') as f:
                reader = csv.reader(f)
                next(reader)  # skip header
                for row in reader:
                    subbasin = int(row[6])
                    channel = subbasin
                    cursor.execute(ConvertFromArc._INSERTCHANNELS, 
                                   (channel, subbasin) + tuple(row[8:15]))
                    downstreamSubbasin[subbasin] = int(row[7])
            # gis_lsus and _subbasins
            cursor.execute('DROP TABLE IF EXISTS gis_lsus')
            cursor.execute('DROP TABLE IF EXISTS gis_subbasins')
            cursor.execute(ConvertFromArc._CREATELSUS)
            cursor.execute(ConvertFromArc._CREATESUBBASINS)
            subbasinLatLonElev = dict()
            with open(os.path.join(self.qProjDir, r'csv\Project\Watershed.csv'), 'r', newline='') as f:
                reader = csv.reader(f)
                next(reader)  # skip header
                for row in reader:
                    subbasin = int(row[3])
                    lsu = subbasin * 10
                    channel = subbasin
                    area = row[4]
                    slo1 = row[5]
                    len1 = row[6]
                    sll = row[7]
                    csl = row[8]
                    wid1 = row[9]
                    dep1 = row[10]
                    lat = row[11]
                    lon = row[12]
                    elev = row[13]
                    elevmin = row[14]
                    elevmax = row[15]
                    lonlat = QgsPointXY(float(lon), float(lat))
                    xy = self.transformToDeg.transform(lonlat)
                    subbasinLatLonElev[subbasin] = (xy.x(), xy.y(), lat, lon, elev)
                    cursor.execute(ConvertFromArc._INSERTLSUS, 
                                   (lsu, QSWATUtils._NOLANDSCAPE, channel, area, slo1, csl, wid1, dep1, lat, lon, elev))
                    cursor.execute(ConvertFromArc._INSERTSUBBASINS, 
                                   (subbasin, area, slo1, len1, sll, lat, lon, elev, elevmin, elevmax))
            # gis_points
            cursor.execute('DROP TABLE IF EXISTS gis_points')
            cursor.execute(ConvertFromArc._CREATEPOINTS)
            reservoirSubbasins = set()  # subbasins with reservoirs
            subbasinToOutlet = dict()
            inletToSubbasin = dict()
            ptsrcToSubbasin = dict()
            ptNum = 0
            with open(os.path.join(self.qProjDir, r'csv\Project\MonitoringPoint.csv'), 'r', newline='') as f:
                reader = csv.reader(f)
                next(reader)  # skip header
                for row in reader:
                    ptNum += 1
                    subbasin = int(row[11])
                    arcType = row[10]
                    if arcType in ['L', 'T', 'O']:
                        qType = 'O'
                        subbasinToOutlet[subbasin] = ptNum
                    elif arcType in ['W', 'I']:
                        qType = 'I'
                        inletToSubbasin[ptNum] = subbasin
                    elif arcType in ['D', 'P']:
                        qType = 'P'
                        ptsrcToSubbasin[ptNum] = subbasin
                    elif arcType == 'R':
                        reservoirSubbasins.add(subbasin)
                        continue  # reservoirs not included in gis_points
                    else:
                        # weather gauge: not included in gis_points
                        continue
                    elev = row[8]
                    if elev == '': # avoid null: arcSWAT only gives elevations to weather gauges
                        elev = 0
                    cursor.execute(ConvertFromArc._INSERTPOINTS, 
                                   (ptNum, subbasin, qType) + tuple(row[4:8]) + (elev,))
            # gis_hrus and _water
            cursor.execute('DROP TABLE IF EXISTS gis_hrus')
            cursor.execute('DROP TABLE IF EXISTS gis_water')
            cursor.execute(ConvertFromArc._CREATEHRUS)
            cursor.execute(ConvertFromArc._CREATEWATER)
            hruToSubbasin = dict()
            # subbasin number from previous row
            lastSubbasin = 0
            # flag to show if water done for current subbasin (since we amalgamate HRUs with landuse WATR)
            waterDone = False
            waterNum = 0
            waters = dict()
            self.usedSoils = set()
            self.usedLanduses = set()
            with open(os.path.join(self.qProjDir, r'csv\Project\hrus.csv'), 'r', newline='') as f:
                reader = csv.reader(f)
                next(reader)  # skip header
                for row in reader:
                    subbasin = int(row[1])
                    lsu = subbasin * 10
                    if subbasin != lastSubbasin:
                        waterDone = False
                    landuse = row[3]
                    self.usedLanduses.add(landuse)
                    soil = row[5]
                    self.usedSoils.add(soil)
                    area = float(row[8])
                    x, y, lat, lon, elev = subbasinLatLonElev[subbasin]
                    if landuse == 'WATR':
                        if subbasin in reservoirSubbasins:
                            wtype = 'RES'
                        else:
                            wtype = 'PND'
                        if not waterDone:
                            waterDone = True
                            waterNum += 1
                            waterArea = float(row[4])  # ARLU field: area in this subbasin which is WATR
                            cursor.execute(ConvertFromArc._INSERTWATER,
                                           (waterNum, wtype, lsu, waterArea, x, y, lat, lon, elev))
                            waters[waterNum] = wtype, subbasin
                    else:
                        hruNum = int(row[11])
                        cursor.execute(ConvertFromArc._INSERTHRUS, 
                                       (hruNum, lsu, row[2]) + tuple(row[2:10]) + (lat, lon, elev))
                        hruToSubbasin[hruNum] = subbasin
                    lastSubbasin = subbasin
            # gis_routing
            cursor.execute('DROP TABLE IF EXISTS gis_routing')
            cursor.execute(ConvertFromArc._CREATEROUTING)
            # route subbasin to outlet and outlet to downstream subbasin
            for subbasin, outlet in subbasinToOutlet.items():
                cursor.execute(ConvertFromArc._INSERTROUTING, 
                               (subbasin, 'SUB', outlet, 'PT', 100))
                # LSUs are just copies of subbasins for ArcSWAT models
                lsu = subbasin * 10
                cursor.execute(ConvertFromArc._INSERTROUTING, 
                               (lsu, 'LSU', outlet, 'PT', 100))
                # subbasin reaches drain to the reservoir if there is one else to the outlet
                channel = subbasin
                if subbasin in reservoirSubbasins:
                    # check if in waters
                    wnum = 0
                    for num, (wtype, wsubbasin) in waters.items():
                        if subbasin == wsubbasin:
                            wnum = num
                            break
                    if wnum > 0:
                        cursor.execute(ConvertFromArc._INSERTROUTING, 
                                       (channel, 'CH', wnum, 'RES', 100))
                    else:
                        # make zero area reservoir
                        waterNum += 1
                        x, y, lat, lon, elev = subbasinLatLonElev[subbasin]
                        cursor.execute(ConvertFromArc._INSERTWATER,
                                       (waterNum, 'RES', subbasin, 0, x, y, lat, lon, elev))
                        waters[waterNum] = 'RES', subbasin
                        cursor.execute(ConvertFromArc._INSERTROUTING, 
                                       (channel, 'CH', waterNum, 'RES', 100))
                else:
                    cursor.execute(ConvertFromArc._INSERTROUTING, 
                                   (channel, 'CH', outlet, 'PT', 100))
                # the outlet point drains to 0, X if a watershed outlet
                # else the downstream subbasins reach
                downSubbasin = downstreamSubbasin[subbasin]
                if downSubbasin == 0:
                    cursor.execute(ConvertFromArc._INSERTROUTING,
                                   (outlet, 'PT', 0, 'X', 100))
                else:
                    downChannel = downSubbasin
                    cursor.execute(ConvertFromArc._INSERTROUTING, 
                                   (outlet, 'PT', downChannel, 'CH', 100))
            # inlets and point sources drain to channels
            for inlet, subbasin in inletToSubbasin.items():
                channel = subbasin
                cursor.execute(ConvertFromArc._INSERTROUTING, 
                               (inlet, 'PT', channel, 'CH', 100))
            for ptsrc, subbasin in ptsrcToSubbasin.items():
                channel = subbasin
                cursor.execute(ConvertFromArc._INSERTROUTING, 
                               (ptsrc, 'PT', channel, 'CH', 100))
            # reservoirs route to points, ponds to channels
            for wnum, (wtype, wsubbasin) in waters.items():
                if wtype == 'RES':
                    cursor.execute(ConvertFromArc._INSERTROUTING, 
                                   (wnum, 'RES', subbasinToOutlet[wsubbasin], 'PT', 100))
                else:
                    channel = wsubbasin
                    cursor.execute(ConvertFromArc._INSERTROUTING, 
                                   (wnum, 'PND', channel, 'CH', 100))
            # HRUs drain to channels
            for hruNum, subbasin in hruToSubbasin.items():
                channel = subbasin
                cursor.execute(ConvertFromArc._INSERTROUTING, 
                                (hruNum, 'HRU', channel, 'CH', 100))
            # checkRouting assumes sqlite3.Row used for row_factory
            conn.row_factory = sqlite3.Row
            msg = DBUtils.checkRouting(conn)
            if msg != '':
                ConvertFromArc.error(msg)
            print('gis_ tables written')
            conn.commit()
    
    def setupTime(self):
        """Read file.cio to setup start/finsh dates and nyskip."""
        print('Writing start/finish dates ...')
        # read file.cio
        cioFile = os.path.join(self.arcProjDir, r'Scenarios\Default\TxtInOut\file.cio')
        if not os.path.isfile(cioFile):
            return
        with open(cioFile, 'r') as f:
            for _ in range(7):
                f.readline()
            line = f.readline()
            nbyr = int(line[:18])
            line = f.readline()
            iyr = int(line[:18])
            line = f.readline()
            idaf = int(line[:18])
            line = f.readline()
            idal = int(line[:18])
            for _ in range(4):
                line = f.readline()
            idt = int(line[:18])
            for _ in range(45):
                line = f.readline()
            nyskip = int(line[:18])
        qProjDb = os.path.join(self.qProjDir, self.qProjName + '.sqlite')
        with sqlite3.connect(qProjDb) as qConn:
            cursor = qConn.cursor()
            cursor.execute('DROP TABLE IF EXISTS time_sim')
            cursor.execute(ConvertFromArc._CREATETIMESIM)
            cursor.execute('DROP TABLE IF EXISTS print_prt')
            cursor.execute(ConvertFromArc._CREATEPRINTPRT)
            cursor.execute(ConvertFromArc._INSERTTIMESIM, (1, idaf, iyr, idal, iyr + nbyr - 1, idt))
            cursor.execute(ConvertFromArc._INSERTPRINTPRT, (1, nyskip, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0))
            qConn.commit()
            
                
            
                                 
    @staticmethod 
    def mapToOrderedPairs(mapping):
        """If mapping is X to percent, create list of (percent, X) ordered by decreasing percent."""
        result = []
        for x, percent in mapping.items():
            ConvertFromArc.insertSort(percent, x, result)
        return result
    
    @staticmethod
    def insertSort(percent, x, result):
        """Insert (percent, x) in result so percentages are ordered decxreasing."""
        for index in range(len(result)):
            nxt, _ = result[index]
            if percent > nxt:
                result.insert(index, (percent, x))
                return
        result.append((percent, x))
        
    @staticmethod
    def getMaxFileOrDir(direc, base, suffix):
        """Find and return the maximum file of the form 'direc\basensuffix' or 'direc\basen if suffix is empty."""
        num = 1
        current = os.path.join(direc, base + str(num) + suffix)
        while True:
            num += 1
            nxt = os.path.join(direc, base + str(num) + suffix)
            if not os.path.exists(nxt):
                return current
            current = nxt
            
    @staticmethod
    def copyFiles(inFile, saveDir):
        """
        Copy files with same basename as infile to saveDir, 
        i.e. regardless of suffix.
        """
        if os.path.isdir(inFile):
            # ESRI grid: need to copy directory to saveDir
            target = os.path.join(saveDir, os.path.split(inFile)[1])
            shutil.copytree(inFile, target)
        else:
            pattern = os.path.splitext(inFile)[0] + '.*'
            for f in glob.iglob(pattern):
                shutil.copy(f, saveDir)    
        
    @staticmethod
    def makeDirs(direc):
        """Make directory dir unless it already exists."""
        if not os.path.exists(direc):
            os.makedirs(direc)
        
    def getChoice(self):
        """Set choice from form."""
        if self._dlg.fullButton.isChecked():
            self.choice = ConvertFromArc._fullChoice
        elif self._dlg.existingButton.isChecked():
            self.choice = ConvertFromArc._existingChoice
        else:
            self.choice = ConvertFromArc._noGISChoice
        
    @staticmethod
    def writeCsvFile(cursor, table, outFile):
        """Write table to csv file outFile."""
        sql = 'SELECT * FROM {0}'.format(table)
        rows = cursor.execute(sql)
        with open(outFile, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([x[0] for x in cursor.description])  # column headers
            for row in rows:
                writer.writerow(row)
        
    @staticmethod
    def copyAllFiles(inDir, outDir):
        """Copy files (containing at least one .) from inDir to OutDir."""
        if os.path.exists(inDir):
            patt = inDir + '\*.*'
            for f in glob.iglob(patt):
                shutil.copy(f, outDir)
                
    @staticmethod
    def question(msg):
        """Ask msg as a question, returning Yes or No."""
        questionBox = QMessageBox()
        questionBox.setWindowTitle('QSWATPlus')
        questionBox.setIcon(QMessageBox.Question)
        questionBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        questionBox.setText(QSWATUtils.trans(msg))
        result = questionBox.exec_()
        return result
    
    @staticmethod
    def error(msg):
        """Report msg as an error."""
        msgbox = QMessageBox()
        msgbox.setWindowTitle('QSWATPlus')
        msgbox.setIcon(QMessageBox.Critical)
        msgbox.setText(QSWATUtils.trans(msg))
        msgbox.exec_()
        return
    
    @staticmethod
    def information(msg):
        """Report msg."""
        msgbox = QMessageBox()
        msgbox.setWindowTitle('QSWATPlus')
        msgbox.setIcon(QMessageBox.Information)
        msgbox.setText(QSWATUtils.trans(msg))
        msgbox.exec_()
        return
    
    @staticmethod
    def exceptionError(msg: str) -> None:
        ConvertFromArc.error('{0}: {1}'.format(msg, traceback.format_exc()))
        return
    
    _CREATEWGN = \
    """
    CREATE TABLE weather_wgn_cli (
        id       INTEGER       NOT NULL
                               PRIMARY KEY,
        name     VARCHAR (255) NOT NULL,
        lat      REAL          NOT NULL,
        lon      REAL          NOT NULL,
        elev     REAL          NOT NULL,
        rain_yrs INTEGER       NOT NULL
    );
    """
    
    _INSERTWGN = 'INSERT INTO weather_wgn_cli VALUES(?,?,?,?,?,?)'
    
    _CREATEWGNMON = \
    """
    CREATE TABLE weather_wgn_cli_mon (
        id          INTEGER NOT NULL
                            PRIMARY KEY,
        weather_wgn_cli_id      INTEGER NOT NULL,
        month       INTEGER NOT NULL,
        tmp_max_ave REAL    NOT NULL,
        tmp_min_ave REAL    NOT NULL,
        tmp_max_sd  REAL    NOT NULL,
        tmp_min_sd  REAL    NOT NULL,
        pcp_ave     REAL    NOT NULL,
        pcp_sd      REAL    NOT NULL,
        pcp_skew    REAL    NOT NULL,
        wet_dry     REAL    NOT NULL,
        wet_wet     REAL    NOT NULL,
        pcp_days    REAL    NOT NULL,
        pcp_hhr     REAL    NOT NULL,
        slr_ave     REAL    NOT NULL,
        dew_ave     REAL    NOT NULL,
        wnd_ave     REAL    NOT NULL,
        FOREIGN KEY (
            weather_wgn_cli_id
        )
        REFERENCES weather_wgn_cli (id) ON DELETE CASCADE
    );
    """
    
    _INSERTWGNMON = 'INSERT INTO weather_wgn_cli_mon VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
    
    _CREATEWEATHERFILE = \
    """
    CREATE TABLE weather_file (
    id       INTEGER       NOT NULL
                           PRIMARY KEY,
    filename VARCHAR (255) NOT NULL,
    type     VARCHAR (255) NOT NULL,
    lat      REAL          NOT NULL,
    lon      REAL          NOT NULL
    );
    """ 
    
    _INSERTWEATHERFILE = 'INSERT INTO weather_file VALUES(?,?,?,?,?)'
    
    _CREATEWEATHERSTATION = \
    """
    CREATE TABLE weather_sta_cli (
    id       INTEGER       NOT NULL
                           PRIMARY KEY,
    name     VARCHAR (255) NOT NULL,
    wgn_id   INTEGER,
    pcp      VARCHAR (255),
    tmp      VARCHAR (255),
    slr      VARCHAR (255),
    hmd      VARCHAR (255),
    wnd      VARCHAR (255),
    wnd_dir  VARCHAR (255),
    atmo_dep VARCHAR (255),
    lat      REAL,
    lon      REAL,
    FOREIGN KEY (
        wgn_id
    )
    REFERENCES weather_wgn_cli (id) ON DELETE SET NULL
    );
    """
    
    _INSERTWEATHERSTATION = 'INSERT INTO weather_sta_cli VALUES(?,?,?,?,?,?,?,?,?,?,?,?)'
    
    _FERTILIZERTABLE = \
    """
    (
    id          INTEGER       NOT NULL
                              PRIMARY KEY,
    name        VARCHAR (255) NOT NULL,
    min_n       REAL          NOT NULL,
    min_p       REAL          NOT NULL,
    org_n       REAL          NOT NULL,
    org_p       REAL          NOT NULL,
    nh3_n       REAL          NOT NULL,
    pathogens   TEXT,
    description TEXT
    )
    """
    
    _PESTICIDETABLE = \
    """
    (
    id          INTEGER       NOT NULL
                              PRIMARY KEY,
    name        VARCHAR (255) NOT NULL,
    soil_ads    REAL          NOT NULL,
    frac_wash   REAL          NOT NULL,
    hl_foliage  REAL          NOT NULL,
    hl_soil     REAL          NOT NULL,
    solub       REAL          NOT NULL,
    aq_hlife    REAL          NOT NULL,
    aq_volat    REAL          NOT NULL,
    mol_wt      REAL          NOT NULL,
    aq_resus    REAL          NOT NULL,
    aq_settle   REAL          NOT NULL,
    ben_act_dep REAL          NOT NULL,
    ben_bury    REAL          NOT NULL,
    ben_hlife   REAL          NOT NULL,
    description TEXT
    )
    """
    
    _TILLAGETABLE = \
    """
    (
    id          INTEGER       NOT NULL
                              PRIMARY KEY,
    name        VARCHAR (255) NOT NULL,
    mix_eff     REAL          NOT NULL,
    mix_dp      REAL          NOT NULL,
    rough       REAL          NOT NULL,
    ridge_ht    REAL          NOT NULL,
    ridge_sp    REAL          NOT NULL,
    description TEXT
    )
    """
    
    _SEPTICTABLE = \
    """
    (
    id          INTEGER       NOT NULL
                              PRIMARY KEY,
    name        VARCHAR (255) NOT NULL,
    q_rate      REAL          NOT NULL,
    bod         REAL          NOT NULL,
    tss         REAL          NOT NULL,
    nh4_n       REAL          NOT NULL,
    no3_n       REAL          NOT NULL,
    no2_n       REAL          NOT NULL,
    org_n       REAL          NOT NULL,
    min_p       REAL          NOT NULL,
    org_p       REAL          NOT NULL,
    fcoli       REAL          NOT NULL,
    description TEXT
    )
    """
    
    _CREATETIMESIM = \
    """
    CREATE TABLE time_sim (
    id        INTEGER NOT NULL
                      PRIMARY KEY,
    day_start INTEGER NOT NULL,
    yrc_start INTEGER NOT NULL,
    day_end   INTEGER NOT NULL,
    yrc_end   INTEGER NOT NULL,
    step      INTEGER NOT NULL
    );
    """
    
    _INSERTTIMESIM = 'INSERT INTO time_sim VALUES(?,?,?,?,?,?)'
    
    _CREATEPRINTPRT = \
    """
    CREATE TABLE print_prt (
    id        INTEGER NOT NULL
                      PRIMARY KEY,
    nyskip    INTEGER NOT NULL,
    day_start INTEGER NOT NULL,
    yrc_start INTEGER NOT NULL,
    day_end   INTEGER NOT NULL,
    yrc_end   INTEGER NOT NULL,
    interval  INTEGER NOT NULL,
    csvout    INTEGER NOT NULL,
    dbout     INTEGER NOT NULL,
    cdfout    INTEGER NOT NULL,
    soilout   INTEGER NOT NULL,
    mgtout    INTEGER NOT NULL,
    hydcon    INTEGER NOT NULL,
    fdcout    INTEGER NOT NULL
    );

    """
    
    _INSERTPRINTPRT = 'INSERT INTO print_prt VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
    
    _CREATECHANNELS = \
    """
    CREATE TABLE gis_channels (
    id       INTEGER PRIMARY KEY
                     UNIQUE
                     NOT NULL,
    subbasin INTEGER,
    areac    REAL,
    len2     REAL,
    slo2     REAL,
    wid2     REAL,
    dep2     REAL,
    elevmin  REAL,
    elevmax  REAL
    )
    """
    
    _INSERTCHANNELS = 'INSERT INTO gis_channels VALUES(?,?,?,?,?,?,?,?,?)'
    
    _CREATEHRUS = \
    """
    CREATE TABLE gis_hrus (
    id      INTEGER PRIMARY KEY
                    UNIQUE
                    NOT NULL,
    lsu     INTEGER,
    arsub   REAL,
    arlsu   REAL,
    landuse TEXT,
    arland  REAL,
    soil    TEXT,
    arso    REAL,
    slp     TEXT,
    arslp   REAL,
    slope   REAL,
    lat     REAL,
    lon     REAL,
    elev    REAL
)
    """
    
    _INSERTHRUS = 'INSERT INTO gis_hrus VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
    
    _CREATELSUS = \
    """
    CREATE TABLE gis_lsus (
    id    INTEGER PRIMARY KEY
                  UNIQUE
                  NOT NULL,
    category   INTEGER,
    channel    INTEGER,
    area  REAL,
    slope REAL,
    csl   REAL,
    wid1  REAL,
    dep1  REAL,
    lat   REAL,
    lon   REAL,
    elev  REAL
    )
    """
    
    _INSERTLSUS = 'INSERT INTO gis_lsus VALUES(?,?,?,?,?,?,?,?,?,?,?)'
    
    _CREATEPOINTS = \
    """
    CREATE TABLE gis_points (
    id       INTEGER PRIMARY KEY
                     UNIQUE
                     NOT NULL,
    subbasin INTEGER,
    ptype    TEXT,
    xpr      REAL,
    ypr      REAL,
    lat      REAL,
    lon      REAL,
    elev     REAL
    )
    """
    
    _INSERTPOINTS = 'INSERT INTO gis_points VALUES(?,?,?,?,?,?,?,?)'
    
    _CREATEROUTING = \
    """
    CREATE TABLE gis_routing (
    sourceid  INTEGER,
    sourcecat TEXT,
    sinkid    INTEGER,
    sinkcat   TEXT,
    percent   REAL
    )
    """
    
    _INSERTROUTING = 'INSERT INTO gis_routing VALUES(?,?,?,?,?)'
    
    _CREATESUBBASINS = \
    """
    CREATE TABLE gis_subbasins (
    id      INTEGER PRIMARY KEY
                    UNIQUE
                    NOT NULL,
    area    REAL,
    slo1    REAL,
    len1    REAL,
    sll     REAL,
    lat     REAL,
    lon     REAL,
    elev    REAL,
    elevmin REAL,
    elevmax REAL
    )
    """
    
    _INSERTSUBBASINS = 'INSERT INTO gis_subbasins VALUES(?,?,?,?,?,?,?,?,?,?)'
    
    _CREATEWATER = \
    """
    CREATE TABLE gis_water (
    id    INTEGER PRIMARY KEY
                  UNIQUE
                  NOT NULL,
    wtype TEXT,
    lsu   INTEGER,
    area  REAL,
    xpr   REAL,
    ypr   REAL,
    lat   REAL,
    lon   REAL,
    elev  REAL
    )
    """
    
    _INSERTWATER = 'INSERT INTO gis_water VALUES(?,?,?,?,?,?,?,?,?)'
    
    class WeatherStation():
        """Name, lat, long, ect for weather station."""
        def __init__(self, name, typ):
            """Constructor."""
            ## name
            self.name = name
            ## type
            self.typ = typ
            ## latitude
            self.latitude = 0
            ## longitude
            self.longitude = 0
            ## elevation
            self.elevation = 0
 
if __name__ == '__main__':
    ## QApplication object needed 
    app = QgsApplication([], True)
    app.initQgis()
    ## main program
    main = ConvertFromArc(sys.argv[1])
    try:
        ## result ignored
        _ = main.run()
    except Exception:
        ConvertFromArc.exceptionError('Error')
    finally:
        exit()    
    