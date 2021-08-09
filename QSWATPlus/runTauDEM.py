# -*- coding: utf-8 -*-
"""
/***************************************************************************
 runTauDEM
 Run TauDEM on DEM and outlets shapefile to make stream network and watershed shapefile
                              -------------------
        begin                : 2015-10-17
        copyright            : (C) 2015 by Chris George
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

import sys
import os
from osgeo import gdal, ogr
from .TauDEMUtils import TauDEMUtils
from .QSWATTopology import QSWATTopology
from .QSWATUtils import QSWATUtils # type: ignore 
from .parameters import Parameters

def main(demFile, outletFile):
    if not os.path.exists(demFile):
        print('Cannot find DEM {0}'.format(demFile))
        return -1
    if not os.path.exists(outletFile):
        print('Cannot find outlets file {0}'.format(outletFile))
        return -1
    gdal.AllRegister()
    demDs = gdal.Open(demFile, gdal.GA_ReadOnly)
    numCols = demDs.RasterXSize
    numRows = demDs.RasterYSize
    demDs = None
    cellThreshold = str(int((numCols * numRows) * 0.01))
    (base, suffix) = os.path.splitext(demFile)
    felFile = base + 'fel' + suffix
    ok = TauDEMUtils.runPitFill(demFile, None, felFile, 0, None)   
    if not ok:
        return -1
    sd8File = base + 'sd8' + suffix
    pFile = base + 'p' + suffix
    ok = TauDEMUtils.runD8FlowDir(felFile, sd8File, pFile, 0, None)   
    if not ok:
        return -1
    slpFile = base + 'slp' + suffix
    angFile = base + 'ang' + suffix
    ok = TauDEMUtils.runDinfFlowDir(felFile, slpFile, angFile, 0, None)  
    if not ok:
        return -1
    ad8File = base + 'ad8' + suffix
    ok = TauDEMUtils.runAreaD8(pFile, ad8File, None, None, 0, None)   
    if not ok:
        return -1
    scaFile = base + 'sca' + suffix
    ok = TauDEMUtils.runAreaDinf(angFile, scaFile, None, 0, None)  
    if not ok:
        return -1
    gordFile = base + 'gord' + suffix
    plenFile = base + 'plen' + suffix
    tlenFile = base + 'tlen' + suffix
    ok = TauDEMUtils.runGridNet(pFile, plenFile, tlenFile, gordFile, None, 0, None)  
    if not ok:
        return -1
    srcFile = base + 'src' + suffix
    ok = TauDEMUtils.runThreshold(ad8File, srcFile, cellThreshold, 0, None) 
    if not ok:
        return -1
    ordFile = base + 'ord' + suffix
    streamFile = base + 'net.shp'
    treeFile = base + 'tree.dat'
    coordFile = base + 'coord.dat'
    wFile = base + 'w' + suffix
    ok = TauDEMUtils.runStreamNet(felFile, pFile, ad8File, srcFile, None, ordFile, treeFile, coordFile,
                                  streamFile, wFile, False, 0, None)
    if not ok:
        return -1
    outletBase = os.path.splitext(outletFile)[0]
    outletMovedFile = outletBase + '_moved.shp'
    ok = TauDEMUtils.runMoveOutlets(pFile, srcFile, outletFile, outletMovedFile, 0, None)
    if not ok:
        return -1
    ok = TauDEMUtils.runAreaD8(pFile, ad8File, outletMovedFile, None, 0, None)   
    if not ok:
        return -1
    ok = TauDEMUtils.runGridNet(pFile, plenFile, tlenFile, gordFile, outletMovedFile, 0, None)  
    if not ok:
        return -1
    ok = TauDEMUtils.runThreshold(ad8File, srcFile, cellThreshold, 0, None) 
    if not ok:
        return -1
    ok = TauDEMUtils.runStreamNet(felFile, pFile, ad8File, srcFile, outletMovedFile, ordFile, treeFile, coordFile,
                                  streamFile, wFile, False, 0, None)
    if not ok:
        return -1
    subbasinsFile = base + 'subbasins.shp'
    createWatershedShapefile(wFile, subbasinsFile)
    return 0

def createWatershedShapefile(wFile, subbasinsFile):
        """Create watershed shapefile subbasinsFile from watershed grid wFile."""
        QSWATUtils.tryRemoveFiles(subbasinsFile)
        driver = ogr.GetDriverByName('ESRI Shapefile')
        if driver is None:
            TauDEMUtils.error('ESRI Shapefile driver is not available - cannot write watershed shapefile', False)
            return
        ds = driver.CreateDataSource(subbasinsFile)
        if ds is None:
            TauDEMUtils.error('Cannot create watershed shapefile {0}'.format(subbasinsFile), False)
            return
        base = os.path.splitext(subbasinsFile)[0]
        subbasinsLayer = ds.CreateLayer(base, geom_type=ogr.wkbPolygon)
        if subbasinsLayer is None:
            TauDEMUtils.error('Cannot create layer for watershed shapefile {0}'.format(subbasinsFile), False)
            return
        idFieldDef = ogr.FieldDefn(QSWATTopology._POLYGONID, ogr.OFTInteger)
        if idFieldDef is None:
            TauDEMUtils.error('Cannot create field {0}'.format(QSWATTopology._POLYGONID), False)
            return
        index = subbasinsLayer.CreateField(idFieldDef)
        if index != 0:
            TauDEMUtils.error('Cannot create field {0} in {1}'.format(QSWATTopology._POLYGONID, subbasinsFile), False)
            return
        areaFieldDef = ogr.FieldDefn(Parameters._AREA, ogr.OFTReal)
        if areaFieldDef is None:
            TauDEMUtils.error('Cannot create field {0}'.format(Parameters._AREA), False)
            return
        areaFieldDef.SetWidth(20)
        areaFieldDef.SetPrecision(0)
        index = subbasinsLayer.CreateField(areaFieldDef)
        if index != 0:
            TauDEMUtils.error('Cannot create field {0} in {1}'.format(Parameters._AREA, subbasinsFile), False)
            return
        subbasinFieldDef = ogr.FieldDefn(QSWATTopology._SUBBASIN, ogr.OFTInteger)
        if subbasinFieldDef is None:
            TauDEMUtils.error('Cannot create field {0}'.format(QSWATTopology._SUBBASIN), False)
            return
        index = subbasinsLayer.CreateField(subbasinFieldDef)
        if index != 0:
            TauDEMUtils.error('Cannot create field {0} in {1}'.format(QSWATTopology._SUBBASIN, subbasinsFile), False)
            return
        sourceRaster = gdal.Open(wFile, gdal.GA_ReadOnly)
        if sourceRaster is None:
            TauDEMUtils.error('Cannot open watershed grid {0}'.format(wFile), False)
            return
        band = sourceRaster.GetRasterBand(1)
        nodata = band.GetNoDataValue()
        featuresToDelete = []
        # We could use band as a mask, but that removes any subbasins with wsno 0
        # so we run with no mask, which produces an unwanted polygon with PolygonId
        # set to the wFile's nodata value.  This we will remove later.
        gdal.Polygonize(band, None, subbasinsLayer, 0, ['8CONNECTED=8'], callback=None)
        ds = None  # closes data source
        QSWATUtils.copyPrj(wFile, subbasinsFile)
        ds = driver.Open(subbasinsFile, 1)
        subbasinsLayer = ds.GetLayer()
        # get areas of subbasins
        for i in range(subbasinsLayer.GetFeatureCount()):
            feature = subbasinsLayer.GetFeature(i)
            basin = feature.GetField(QSWATTopology._POLYGONID)
            if basin == nodata:
                featuresToDelete.append(i)
            else:
                area = feature.GetGeometryRef().GetArea() / 1E4 # convert to hectares
                feature.SetField(Parameters._AREA, area)
                subbasinsLayer.SetFeature(feature)
        # get rid of any basin corresponding to nodata in wFile
        for i in featuresToDelete:
            subbasinsLayer.DeleteFeature(i)

if __name__ == '__main__':
    if len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        print('You must provide a DEM and a point shapefile')
        
