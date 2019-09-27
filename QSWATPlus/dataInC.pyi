# -*- coding: utf-8 -*-


from qgis.core import * # @UnusedWildImport
from qgis.gui import * # @UnusedWildImport

from typing import Set, List, Tuple, Dict

class CellData:

    cellCount: int
    area: float
    totalElevation: float
    totalSlope: float
    totalLatitude: float
    totalLongitude: float
    crop: int
    actHRUNum: int
    
    def __init__(self, count: int, area: float, elevation: float, slope: float, x: float, y: float, crop: int) -> None: ...
        
    def addCell(self, area: float, elevation: float, slope: float, x: float, y: float) -> None: ...
        
    def addCells(self, cd: CellData) -> None: ...
        
    def multiply(self, factor: float) -> None: ...
        

class WaterBody:

    
    cellCount: int
    area: float
    originalArea: float
    totalElevation: float
    totalLatitude: float
    totalLongitude: float
    id: int
    channelRole: int
    waterRole: int
        
    def __init__(self, count: int, area: float, elevation: float, x: float, y: float) -> None: ...
        
    def addCell(self, area: float, elevation: float, x: float, y: float) -> None: ...
        
    def addWater(self, wb: WaterBody, keepOriginal: int) -> None: ...
        
    def multiply(self, factor: float) -> None: ...
        
    def setInlet(self) -> None: ...
        
    def setOutlet(self) -> None: ...
        
    def setReservoir(self) -> None: ...
        
    def setPond(self) -> None: ...
        
    def isInlet(self) -> bool: ...
    
    def isOutlet(self) -> bool: ...
    
    def isUnknown(self) -> bool: ...
    
    def isReservoir(self) -> bool: ...
    
    def isPond(self) -> bool: ...
    
    def copy(self) -> WaterBody: ... 


class LSUData:

    cellCount: int
    area: float
    outletElevation: float
    sourceElevation: float
    channelLength: float
    farElevation: float
    farDistance: float
    farPointX: float
    farPointY: float
    totalElevation: float
    totalSlope: float
    totalLatitude: float
    totalLongitude: float
    cropSoilSlopeArea: float
    hruMap: Dict[int, CellData]
    cropSoilSlopeNumbers: Dict[int, Dict[int, Dict[int, int]]]
    cropAreas: Dict[int, float]
    originalCropAreas: Dict[int, float]
    soilAreas: Dict[int, float]
    originalSoilAreas: Dict[int, float]
    slopeAreas: Dict[int, float]
    originalSlopeAreas: Dict[int, float]
    waterBody: WaterBody
    lastHru: int
    
    def __init__(self) -> None: ...
                        
    def cropSoilAreas(self, crop: int) -> Dict[int, float]: ...
    
    def cropSoilArea(self, crop: int, soil: int) -> float: ...
    
    def cropArea(self, crop: int) -> float: ...
    
    def cropSoilSlopeAreas(self, crop: int, soil: int) -> Dict[int, float]: ...
    
    def getDominantHRU(self, waterLanduse: int, allowWater: bool) -> Tuple[int, int, int]: ...
            
    def redistribute(self, factor: float) -> None: ...
            
    def redistributeNodataAndWater(self, chLink: int, lscape: int, chLinksByLakes: List[int], waterLanduse: int) -> None: ...
            
    def removeHRU(self, hru: int, crop: int, soil: int, slope: int) -> None: ...
                
    def removeWaterHRUs(self, waterLanduse: int) -> None: ...
                  
    def setCropAreas(self, isOriginal: bool) -> None: ...
        
    def setSoilAreas(self, isOriginal: bool) -> None: ...
    
    def setSlopeAreas(self, isOriginal: bool) -> None: ...
                    
    def nextHruNumber(self) -> int: ...
                    
    def getHruNumber(self, crop: int, soil: int, slope: int) -> int: ...
    
    def copy(self) -> LSUData: ...
    
    def copyHRUMap(self) -> Dict[int, CellData]: ...
    
    def copyCropSoilSlopeNumbers(self) -> Dict[int, Dict[int, Dict[int, int]]]: ...
    
    @staticmethod
    def copyAreaMap(amap: Dict[int, float]) -> Dict[int, float]: ...
    
    def merge(self, lsuData: LSUData) -> None: ...
        
    def makeReservoir(self, threshold: float) -> None: ...
        
    @staticmethod
    def mergeMaps(map1: Dict[int, float], map2: Dict[int, float]) -> None: ...
    
class BasinData:
    
    lsus: Dict[int, Dict[int, LSUData]]
    mergedLsus: Dict[int, Dict[int, LSUData]]
    farDistance: float
    minElevation: float
    maxElevation: float
    waterLanduse: int
    waterId: int
    
    def __init__(self, waterLanduse: int, farDistance: float, waterId: int) -> None: ...
        
    def getLsus(self) -> Dict[int, Dict[int, LSUData]]: ...
        
    def addCell(self, channel: int, landscape: int, crop: int, soil: int, slope: int, area: float, 
                      elevation: float, slopeValue: float, distSt: float, distCh: float, x: float, y: float,  _gv: object) -> None: ...
    
    @staticmethod
    def getHruNumber(channelLandscapeCropSoilSlopeNumbers: Dict[int, Dict[int, Dict[int, Dict[int, Dict[int, int]]]]], 
                      lastHru: int, channel: int, landscape: int, crop: int, soil: int, slope: int) -> int: ...
    
    def merge(self, channel: int, target: int) -> None: ...
    
    def setAreas(self, bisOriginal: int, chLinksByLakes: List[int], waterLanduse: int) -> None: ...
            
    def cropAreas(self, isOriginal: bool) -> Dict[int, float]: ...
            
    def soilAreas(self, isOriginal: bool) -> Dict[int, float]: ...
            
    def slopeAreas(self, isOriginal: bool) -> Dict[int, float]: ...
    
    def subbasinCellCount(self) -> int: ...
    
    def subbasinArea(self) -> float: ...
    
    def totalElevation(self) -> float: ...
    
    def totalSlope(self) -> float: ...
    
    def copyLsus(self) -> None: ...
    
    @staticmethod
    def channelArea(channelData: Dict[int, LSUData]) -> float: ...
    
    @staticmethod
    def dominantKey(table: Dict[int, float]) -> Tuple[int, float]: ... 

class ReachData:
    upperX: float
    upperY: float
    upperZ: float
    lowerX: float
    lowerY: float
    lowerZ: float
        
    def __init__(self, x1: float, y1: float, z1: float, x2: float, y2: float, z2: float) -> None: ... 
        
class MergedChannelData:
    
    areaC: float
    length: float
    slope: float
    minEl: float
    maxEl: float
    
    def __init__(self, areaC: float, length: float, slope: float, minEl: float, maxEl: float) -> None: ... 
        
    def add(self, areaC: float, length: float, slope: float, minEl: float, maxEl: float) -> None: ... 
        
class LakeData:

    inChLinks: Dict[int, Tuple[int, QgsPointXY, float]]
    lakeChLinks: Set[int]
    outChLink: int
    outPoint: Tuple[int, int, QgsPointXY, float]
    otherOutChLinks: Set[int]
    area: float
    elevation: float
    centroid: QgsPointXY
    waterRole: int
        
    def __init__(self, area: float, centroid: QgsPointXY, waterRole: int) -> None: ... 
        
        
