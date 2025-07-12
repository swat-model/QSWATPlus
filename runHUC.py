# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QSWAT
                                 A QGIS plugin
 Run HUC project
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


from qgis.core import QgsApplication, QgsProject, QgsRasterLayer, QgsVectorLayer, QgsExpression,  QgsFeatureRequest, QgsCoordinateTransform, QgsCoordinateReferenceSystem # @UnresolvedImport
#from PyQt5.QtCore import * # @UnusedWildImport
import atexit
import sys
import os
import glob
from osgeo import gdal, ogr  # type: ignore
from multiprocessing import Pool
import sqlite3

from QSWATPlus.QSWATPlusMain import QSWATPlus  # @UnresolvedImport
from QSWATPlus.delineation import Delineation  # @UnresolvedImport
from QSWATPlus.hrus import HRUs  # @UnresolvedImport
import traceback


osGeo4wRoot = os.getenv('OSGEO4W_ROOT')
QgsApplication.setPrefixPath(osGeo4wRoot + r'\apps\qgis-ltr', True)


# create a new application object
# without this importing processing causes the following error:
# QWidget: Must construct a QApplication before a QPaintDevice
# and initQgis crashes
app = QgsApplication([], True)


QgsApplication.initQgis()


atexit.register(QgsApplication.exitQgis)

class DummyInterface(object):
    """Dummy iface."""
    def __getattr__(self, *args, **kwargs):  # @UnusedVariable
        """Dummy function."""
        def dummy(*args, **kwargs):  # @UnusedVariable
            return self
        return dummy
    def __iter__(self):
        """Dummy function."""
        return self
    def next(self):
        """Dummy function."""
        raise StopIteration
    def layers(self):
        """Simulate iface.legendInterface().layers()."""
        return QgsProject.instance().mapLayers().values()
iface = DummyInterface()

#QCoreApplication.setOrganizationName('QGIS')
#QCoreApplication.setApplicationName('QGIS2')

class runHUC():
    
    """Run HUC14/12/10/8 project."""
    
    def __init__(self, projDir, logFile):
        """Initialize"""
        ## project directory
        self.projDir = projDir
        ## QSWAT plugin
        self.plugin = QSWATPlus(iface)
        ## QGIS project
        self.proj = QgsProject.instance()
        projName = os.path.split(self.projDir)[1]
        self.proj.read(self.projDir + '/{0}.qgs'.format(projName))
        self.plugin.setupProject(self.proj, True, isHUC=True, logFile=logFile)
        ## main dialogue
        self.dlg = self.plugin._odlg
        ## delineation object
        self.delin = None
        ## hrus object
        self.hrus = None
        # Prevent annoying "error 4 .shp not recognised" messages.
        # These should become exceptions but instead just disappear.
        # Safer in any case to raise exceptions if something goes wrong.
        gdal.UseExceptions()
        ogr.UseExceptions()
        
    def runProject(self, dataDir, scale, minHRUha):
        """Run QSWAT+ project."""
        gv = self.plugin._gv
        #print('Dem is processed is {0}'.format(self.plugin._demIsProcessed))
        self.delin = Delineation(gv, self.plugin._demIsProcessed)
        self.delin._dlg.tabWidget.setCurrentIndex(1)
        self.delin._dlg.selectDem.setText(self.projDir + '/Watershed/Rasters/DEM/dem.tif')
        self.delin._dlg.drainStreamsButton.setChecked(True)
        self.delin._dlg.selectSubbasins.setText(self.projDir + '/Watershed/Shapes/subbasins.shp')
        self.delin._dlg.selectWshed.setText(self.projDir + '/Watershed/Shapes/demwshed.shp')
        self.delin._dlg.selectStreams.setText(self.projDir + '/Watershed/Shapes/channels.shp')
        self.delin._dlg.selectExistOutlets.setText(self.projDir + '/Watershed/Shapes/points.shp')
        self.delin._dlg.recalcButton.setChecked(False)  # want to use length field in channels shapefile
        self.delin._dlg.snapThreshold.setText('300')
        # use MPI on HUC10 and HUC8 projects
        numProc = 0 if scale >= 12 else 8
        self.delin._dlg.numProcesses.setValue(numProc)
        gv.HUCDataDir = dataDir
        gv.useGridModel = False
        gv.existingWshed = True
        self.delin.runExisting()
        self.delin.finishDelineation()
        self.delin._dlg.close()
        self.hrus = HRUs(gv, self.dlg.reportsBox)
        self.hrus.init()
        hrudlg = self.hrus._dlg
        self.hrus.landuseFile = self.projDir + '/Watershed/Rasters/Landuse/landuse.tif'
        self.hrus.landuseLayer = QgsRasterLayer(self.hrus.landuseFile, 'landuse')
        self.hrus.soilFile = self.projDir + '/Watershed/Rasters/Soil/soil.tif'
        self.hrus.soilLayer = QgsRasterLayer(self.hrus.soilFile, 'soil')
        #landCombo = hrudlg.selectLanduseTable
        #landIndex = landCombo.findText('nlcd2001_landuses')
        #landCombo.setCurrentIndex(landIndex)
        #self.hrus.landuseTable = 'nlcd2001_landuses'
        huc2 = os.path.split(self.projDir)[1][3:5]
        isCDL = 'Fields_CDL' in self.projDir
        self.hrus.landuseTable = 'landuse_fields_CDL_{0}'.format(huc2) if isCDL else 'landuse_fields_{0}'.format(huc2)
        hrudlg.SSURGOButton.setChecked(True)
        gv.db.useSSURGO = True
        gv.db.slopeLimits = [2,8]
        gv.elevBandsThreshold = 500
        gv.numElevBands = 5
        if not self.hrus.readFiles():
            hrudlg.close()
            return 
        hrudlg.filterAreaButton.setChecked(True)
        hrudlg.areaButton.setChecked(True)
        hrudlg.areaVal.setText(str(minHRUha))
        self.hrus.calcHRUs()
        result = self.hrus.HRUsAreCreated()
        hrudlg.close()
        return result
        
    def addInlet(self, inletId):
        """Add watershed inlet."""
        gv = self.plugin._gv
        db = gv.db
        # get point from demnet.shp
        pointsFile = gv.projDir + '/Watershed/Shapes/points.shp'
        pointsLayer = QgsVectorLayer(pointsFile, 'points', 'ogr')
        exp = QgsExpression('"ID" = {0}'.format(inletId))
        point = next(pointsLayer.getFeatures(QgsFeatureRequest(exp)))
        geom = point.geometry()
        pointXY = geom.asPoint()
        transformToLatLong = QgsCoordinateTransform(pointsLayer.crs(), QgsCoordinateReferenceSystem('EPSG:4326'), QgsProject.instance())
        geom.transform(transformToLatLong)
        pointll = geom.asPoint()
        # to find subbasin, find zero length channel with inletId as LINKNO, and then subbasin of its downstream channel
        channelsFile = gv.projDir + '/Watershed/Shapes/channels.shp'
        channelsLayer = QgsVectorLayer(channelsFile, 'channels', 'ogr')
        channelsProvider = channelsLayer.dataProvider()
        dsLinkNoIndex = channelsProvider.fieldNameIndex('DSLINKNO1')
        basinNoIndex = channelsProvider.fieldNameIndex('BasinNo')
        exp1 = QgsExpression('"LINKNO" = {0}'.format(inletId))
        channel = next(channelsLayer.getFeatures(QgsFeatureRequest(exp1).setFlags(QgsFeatureRequest.NoGeometry)))
        dsLinkNo = channel[dsLinkNoIndex]
        exp2 = QgsExpression('"LINKNO" = {0}'.format(dsLinkNo))
        channel = next(channelsLayer.getFeatures(QgsFeatureRequest(exp2).setFlags(QgsFeatureRequest.NoGeometry)))
        basinNo = channel[basinNoIndex]
        channelIndex = channelsProvider.fieldNameIndex('Channel')
        channelNo = channel[channelIndex]
        subbasinsFile = gv.projDir + '/Watershed/Shapes/subbasins.shp'
        subbasinsLayer = QgsVectorLayer(subbasinsFile, 'subbasins', 'ogr')
        subbasinsProvider = subbasinsLayer.dataProvider()
        subIndex = subbasinsProvider.fieldNameIndex('Subbasin')
        exp3 = QgsExpression('"PolygonId" = {0}'.format(basinNo))
        sub = next(subbasinsLayer.getFeatures(QgsFeatureRequest(exp3).setFlags(QgsFeatureRequest.NoGeometry)))
        basin = sub[subIndex]
        projName = os.path.split(gv.projDir)[1]
        projDb = gv.projDir + '/' + projName + '.sqlite'
        with sqlite3.connect(projDb) as conn:
            # add inlet to gis_points
            table = 'gis_points'
            elev = 0 # only used for weather gauges
            typ = 'I'
            sql2 = 'INSERT INTO ' + table + ' VALUES(?,?,?,?,?,?,?,?)'
            conn.execute(sql2, (inletId, basin, typ, 
                           float(pointXY.x()), float(pointXY.y()), float(pointll.y()), float(pointll.x()), 
                           float(elev)))
            # route to channel
            sql3 = 'INSERT INTO gis_routing VALUES(?,?,?,?,?,?)'
            conn.execute(sql3, (inletId, 'PT', 'tot', channelNo, 'CH', 100))
            
def runProject(d, dataDir, scale, minHRUha):
    """Run a QSWAT+ project on directory d"""
    # seems clumsy to keep opening logFile, rather than opening once and passing handle
    # but there may be many instances of this function and we want to avoid too many open files
    if os.path.isdir(d):
        logFile = d + '/LogFile.txt'
        with open(logFile, 'w') as f:
            f.write('Running project {0}\n'.format(d))
        sys.stdout.write('Running project {0}\n'.format(d))
        sys.stdout.flush()
        try:
            huc = runHUC(d, logFile)
            if huc.runProject(dataDir, scale, minHRUha):
                with open(logFile, 'a') as f:
                    f.write('Completed project {0}\n'.format(d))
            else:
                with open(logFile, 'a') as f:
                    f.write('ERROR: incomplete project {0}\n'.format(d))     
        except Exception:
            with open(logFile, 'a') as f:
                f.write('ERROR: exception: {0}\n'.format(traceback.format_exc()))
            sys.stdout.write('ERROR: exception: {0}\n'.format(traceback.format_exc()))
            sys.stdout.flush()
            
if __name__ == '__main__':
    #for arg in sys.argv:
    #    print('Argument: {0}'.format(arg))
    # set True for debugging, normally false
    debugging = False  
    if debugging:
        #direc = r'K:\HUCModels\Models4\SWATPlus\Fields_CDL\HUC12\0202000206\huc0202000206\huc0202000206.qgs'
        #direc = r"K:/HUCModels/Models4/SWATPlus/Fields_CDL/HUC12/02/huc0202000308/huc0202000308.qgs"
        #direc = r'K:/HUCModels/Models4/SWATPlus/Fields_CDL/HUC14/02040303/huc020403030102/huc020403030102.qgs'
        #direc = r'K:/HUCModels/Models4/SWATPlus/Fields_CDL/HUC12/02/huc0203010104/huc0203010104.qgs'
        direc = r"K:\HUCModels\Models5\SWATPlus\Fields_CDL\HUC14\01\huc010500010207\huc010500010207.qgs" 
        dataDir = "K:/Data" 
        scale = 14 
        minHRUha = 1 
        inletId = 0
    else:
        if len(sys.argv) < 5:
            print('You must supply a directory or project file, a scale (14, 12, 10 or 8), a minimum HRU size in ha, and 0 or a inlet number as argument')
            exit()
        direc = sys.argv[1]
        print('direc is {0}'.format(direc))
        dataDir = sys.argv[2]
        print('dataDir is {0}'.format(dataDir))
        scale = int(sys.argv[3])
        print('Scale is {0}'.format(scale))
        minHRUha = int(sys.argv[4])
        print('Minimum HRU size {0} ha'.format(minHRUha))
        inletId = int(sys.argv[5])
        print('inletId is {0}'.format(inletId))
    if inletId > 0:
        # add inlet point with this id to points table of existing project
        print('Adding inlet {0} to project {1}'.format(inletId, direc))
        huc = runHUC(direc, None)
        huc.addInlet(inletId)
    elif direc.endswith('.qgs'):
        d, _ = os.path.split(direc)
        print('Running project {0}'.format(d))
        try:
            huc = runHUC(d, None)
            huc.runProject(dataDir, scale, minHRUha)
            print('Completed project {0}'.format(d))
        except Exception:
            print('ERROR: exception: {0}'.format(traceback.format_exc()))
    else:
        pattern = direc + '/huc*'
        dirs = glob.glob(pattern)
        cpuCount = os.cpu_count()
        numProcesses = min(cpuCount, 24)
        chunk = 1 
        args = [(d, dataDir, scale, minHRUha) for d in dirs]
        with Pool(processes=numProcesses) as pool:
            res = pool.starmap_async(runProject, args, chunk)
            _ = res.get()
        sys.stdout.flush()
    app.exitQgis()
    app.deleteLater()
    app.exit()
    del app     
        
