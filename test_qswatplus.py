# -*- coding: utf-8 -*-
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

# derived from http://snorf.net/blog/2014/01/04/writing-unit-tests-for-qgis-python-plugins/

from qgis.PyQt.QtCore import pyqtSlot, QCoreApplication, QFileInfo, QObject, Qt  # @UnresolvedImport
#from qgis.PyQt.QtGui import * # @UnusedWildImport
#from qgis.PyQt.QtWidgets import * # @UnusedWildImport
from qgis.PyQt import QtTest # @UnresolvedImport
from qgis.core import QgsApplication, QgsProject, QgsUnitTypes # @UnresolvedImport
#from qgis.gui import * # @UnusedWildImport
from qgis.analysis import QgsNativeAlgorithms # @UnresolvedImport

import os.path
from osgeo import gdal
import shutil
import filecmp
import unittest
import atexit 
import math
from processing.core.Processing import Processing  # @UnresolvedImport

from QSWATPlus.QSWATPlusMain import QSWATPlus
from QSWATPlus.delineation import Delineation
from QSWATPlus.landscape import Landscape
from QSWATPlus.hrus import HRUs
from QSWATPlus.QSWATUtils import QSWATUtils, FileTypes
from QSWATPlus.parameters import Parameters
from QSWATPlus.selectsubs import SelectSubbasins

# create a new application object
# has to be done before calling initQgis
app = QgsApplication([], True)

if Parameters._ISWIN:
    osGeo4wRoot = os.getenv('OSGEO4W_ROOT')
    QgsApplication.setPrefixPath(osGeo4wRoot + r'\apps\qgis', True)
else:
    QgsApplication.setPrefixPath('/usr')

app.initQgis()

# if len(QgsProject.instance().providerList()) == 0:
#     raise RuntimeError('No data providers available.  Check prefix path setting in test_qswatplus.py.')

# QSWATUtils.information('Providers: {0!s}'.format(QgsProject.instance().providerList()), True)

atexit.register(app.exitQgis)

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
    def __next__(self):
        """Dummy function."""
        raise StopIteration
    def layers(self):
        """Simulate iface.legendInterface().layers()."""
        return list(QgsProject.instance().mapLayers().values())
iface = DummyInterface()

QCoreApplication.setOrganizationName('QGIS')
QCoreApplication.setApplicationName('QGIS3')

#===============================================================================
# Test1:
#   - No MPI
#   - single outlet only
#   - no merging/adding in delineation
#   - slope limit 10
#   - percent filters 20/10/5
#   - change numeric parameters
#===============================================================================

HashTable1 = dict()
if Parameters._ISWIN:
    HashTable1['gis_channels'] = 'f811111beefb322933661fc48525f424'
    HashTable1['gis_points'] = 'a58579e17a502f16a37fd5703b78f24a'
    HashTable1['BASINSDATA'] = '64fe9b6ed9272914603daef10988e8e0'
    HashTable1['LSUSDATA'] = '33bd8b6a95187288dec5917d30281ae2'
    HashTable1['HRUSDATA'] = 'd3744676e57f0a787c0117519abbb5ef'
    HashTable1['WATERDATA'] = '114e03e1996124d1a1361216c15eb41d'
    HashTable1['gis_elevationbands'] = '1a7d614a51eaa888311d51fad468f2a8'
    HashTable1['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
    HashTable1['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
    HashTable1['gis_subbasins'] = 'db828612cc955dbf7ea44d762591bfac'
    HashTable1['gis_lsus'] = '9bdb9073ae7979b4b7a8111fd1f6f049'
    HashTable1['gis_hrus'] = 'fc126100437626a5f169171078772d37'
    HashTable1['gis_routing'] = 'bc87cfc432f6de16c94f0f2f9c60ab8b'
    HashTable1['gis_water'] = 'd41d8cd98f00b204e9800998ecf8427e'
    HashTable1['soils_sol'] = 'a212b2bb0012ae514f21a7cc186befc6'
    HashTable1['soils_sol_layer'] = 'c1ad51d497c67e77de4d7e6cf08479f8'
   
    # tables after adjusting parameters
    HashTable1a = dict()
    HashTable1a['gis_channels'] = 'bbc402053f2a7f69512cbe371059d81e'
    HashTable1a['gis_points'] = HashTable1['gis_points']
    HashTable1a['BASINSDATA'] = HashTable1['BASINSDATA']
    HashTable1a['LSUSDATA'] = HashTable1['LSUSDATA']
    HashTable1a['HRUSDATA'] = HashTable1['HRUSDATA']
    HashTable1a['WATERDATA'] = HashTable1['WATERDATA']
    HashTable1a['gis_elevationbands'] = HashTable1['gis_elevationbands']
    HashTable1a['gis_landexempt'] = HashTable1['gis_landexempt']
    HashTable1a['gis_splithrus'] = HashTable1['gis_splithrus']
    HashTable1a['gis_subbasins'] = '1a158d745b156f4954ede142bb86c012'
    HashTable1a['gis_lsus'] = '983a33f229a27632fe2d68d239554d26'
    HashTable1a['gis_hrus'] = '78f515df74f483bd76c38fb5e971159a'
    HashTable1a['gis_routing'] = HashTable1['gis_routing']
    HashTable1a['gis_water'] = HashTable1['gis_water']
    HashTable1a['soils_sol'] = HashTable1['soils_sol']
    HashTable1a['soils_sol_layer'] = HashTable1['soils_sol_layer']

elif Parameters._ISLINUX:
    HashTable1['gis_channels'] = '43ddf95de066c4e3424cd72757549e2e'
    HashTable1['gis_points'] = '48b27308d98f89285853c8404dcc6c15'
    HashTable1['BASINSDATA'] = '64fe9b6ed9272914603daef10988e8e0'
    HashTable1['LSUSDATA'] = '6e97376328807b675ee3d503b4e5a981'
    HashTable1['HRUSDATA'] = 'c57ae0744297d997a727bb5b2f831561'
    HashTable1['WATERDATA'] = '114e03e1996124d1a1361216c15eb41d'
    HashTable1['gis_elevationbands'] = '1a7d614a51eaa888311d51fad468f2a8'
    HashTable1['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
    HashTable1['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
    HashTable1['gis_subbasins'] = '261182c2bd84e6248b6e7980d440c4e7'
    HashTable1['gis_lsus'] = 'b4e7e02febfbf2e0a403981cd6ecde34'
    HashTable1['gis_hrus'] = '1c4f8ee6786422ec7269607c1d56f9e5'
    HashTable1['gis_routing'] = 'bc87cfc432f6de16c94f0f2f9c60ab8b'
    HashTable1['gis_water'] = 'd41d8cd98f00b204e9800998ecf8427e'
    HashTable1['soils_sol'] = 'a212b2bb0012ae514f21a7cc186befc6'
    HashTable1['soils_sol_layer'] = 'c1ad51d497c67e77de4d7e6cf08479f8'

    # tables after adjusting parameters
    HashTable1a = dict()
    HashTable1a['gis_channels'] = '6b141cde71d3502f1e9dca3408579900'
    HashTable1a['gis_points'] = HashTable1['gis_points']
    HashTable1a['BASINSDATA'] = HashTable1['BASINSDATA']
    HashTable1a['LSUSDATA'] = HashTable1['LSUSDATA']
    HashTable1a['HRUSDATA'] = HashTable1['HRUSDATA']
    HashTable1a['WATERDATA'] = HashTable1['WATERDATA']
    HashTable1a['gis_elevationbands'] = HashTable1['gis_elevationbands']
    HashTable1a['gis_landexempt'] = HashTable1['gis_landexempt']
    HashTable1a['gis_splithrus'] = HashTable1['gis_splithrus']
    HashTable1a['gis_subbasins'] = '3f01208b7153133fe465c85b04f64a4d'
    HashTable1a['gis_lsus'] = '9e9e81429876a4f92e49118344511096'
    HashTable1a['gis_hrus'] = '0e4285a46289de2da35f4df7ef9e09e0'
    HashTable1a['gis_routing'] = HashTable1['gis_routing']
    HashTable1a['gis_water'] = HashTable1['gis_water']
    HashTable1a['soils_sol'] = HashTable1['soils_sol']
    HashTable1a['soils_sol_layer'] = HashTable1['soils_sol_layer']

#===============================================================================
# Test2:
#   - MPI with 12 processes
#   - stream threshold 100 sq km
#   - channel threshold 10 sq km
#   - 7 inlets/outlets
#   - snap threshold set to 600 (fails on default 300)
#   - no merging/adding in delineation
#   - no slope limit
#   - FullHRUs created
#   - 6 elev bands: threshold 2000
#   - area filter 500 ha
#===============================================================================

HashTable2 = dict()
if Parameters._ISWIN:
    HashTable2['gis_channels'] = 'c539491d7f67763243364280cd34fcd7'
    HashTable2['gis_points'] = 'edf24b436b134a0cf8fbedb631e32c57'
    HashTable2['BASINSDATA'] = 'e99dbf8ce6dcec169bf7164838d522b9'
    HashTable2['LSUSDATA'] = '57c049129508e19525d3cff70b067988'
    HashTable2['HRUSDATA'] = '332aa8de3feacf41af49aff5d66a527f'
    HashTable2['WATERDATA'] = 'd41d8cd98f00b204e9800998ecf8427e'
    HashTable2['gis_elevationbands'] = 'e28ea4b5a684d867dc6c949393312a79'
    HashTable2['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
    HashTable2['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
    HashTable2['gis_subbasins'] = '16148f2ccc85fb1e38ed0f1c58f176ee'
    HashTable2['gis_lsus'] = 'c53179e26a253c22f2b478c5e65abb67'
    HashTable2['gis_hrus'] = '66dd607714f9ef547e3f693a4c642d22'
    HashTable2['gis_routing'] = 'daac50c0e601e04f47c0dee7d680f75b'
    HashTable2['gis_water'] = '9c34064431f5979bc9c21b7610fe3027'
    HashTable2['soils_sol'] = 'e6a7ef3e63d6fc82468a367a33edde66'
    HashTable2['soils_sol_layer'] = 'c5c1f8179ca7054fe29165f9015b8e64'
else:
    HashTable2['gis_channels'] = 'd6e10850e509e34635bc5c279f2700d1'
    HashTable2['gis_points'] = '5116e8933d8fca6bd0be3de191296ae7'
    HashTable2['BASINSDATA'] = 'aee0cbd8be405bd40678ebddab871fac'
    HashTable2['LSUSDATA'] = '8b9ce2b4069dca3c21be2cf6362b9f40'
    HashTable2['HRUSDATA'] = '3e19713a6a985fdc1c8d92a14859f63b'
    HashTable2['WATERDATA'] = 'd41d8cd98f00b204e9800998ecf8427e'
    HashTable2['gis_elevationbands'] = 'e28ea4b5a684d867dc6c949393312a79'
    HashTable2['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
    HashTable2['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
    HashTable2['gis_subbasins'] = '58ce262bcc4864d0ec665f6989718b2a'
    HashTable2['gis_lsus'] = '447634aaf2778be4024f3adbefc36f5f'
    HashTable2['gis_hrus'] = 'd6aa394a60547745b9fd2723e081adca'
    HashTable2['gis_routing'] = '7247699894bf482d9a80f507856d3ad6'
    HashTable2['gis_water'] = '4069f4babd327b6bc4022c2ac618fe22'
    HashTable2['soils_sol'] = 'e6a7ef3e63d6fc82468a367a33edde66'
    HashTable2['soils_sol_layer'] = 'c5c1f8179ca7054fe29165f9015b8e64'

#===============================================================================
# Test3:
#   - No MPI
#   - stream threshold 14400 cells; channel threshold 1440 cells
#   - single outlet only
#   - merge subbasins 2 and 6 (poygon ids 23 and 27)
#   - split GRAS into 10% SWRN and 90% RNGE
#   - exempt Landuses CRDY and SWRN
#   - no slope limits
#   - target by area 100
#   - rerun HRU creation
#===============================================================================

HashTable3 = dict()
# HashTable3['gis_channels'] = '5265c40eb6e13d298a4dae6adb7f8809'  # unreliable
# HashTable3['gis_points'] = '74f4adad3f70a25c503db31af93e9ae9'
HashTable3['BASINSDATA'] = '0959c4d9bdf4324560d65a7c5f09b846'
HashTable3['LSUSDATA'] = '08e11a47583bc1af5397624229c33a02'
HashTable3['HRUSDATA'] = '3844bf5150b2fdcaf7efd3c84668e94d'
HashTable3['WATERDATA'] = 'ef4821139bebc7985aad316ccfef45ba'
HashTable3['gis_elevationbands'] = '7cb4deff34d859f54f9167b411613eeb'
HashTable3['gis_landexempt'] = '843f4dfbcb5fa16105cdd5b8108f3d5f'
HashTable3['gis_splithrus'] = '1221c315567ad59dbf8976f1c56c46b4'
# HashTable3['gis_subbasins'] = 'b97f84dd210b4aa89234225d92662f27'
HashTable3['gis_lsus'] = 'bb4940e392bea0ecaab433277fc56e0e'
# HashTable3['gis_hrus'] = 'f537ccd8d6180721090f0a8cb1bae2a2'
# HashTable3['gis_routing'] = '72cf3f50dacf291a169ca616eec1a8d4'
HashTable3['gis_water'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable3['soils_sol'] = 'a212b2bb0012ae514f21a7cc186befc6'
HashTable3['soils_sol_layer'] = 'c1ad51d497c67e77de4d7e6cf08479f8'

#===============================================================================
# Test4:
#   - No MPI
#   - use existing 
#   - no outlet
#   - no merging/adding in delineation
#   - make FullHRs shapefile
#   - no slope limits
#   = channel merge limit set to 10% and readFiles rerun to merge
#   - filter by percent area 10%
#===============================================================================

HashTable4 = dict()
HashTable4['gis_channels'] = 'dc1b237957c1ed757eb23b6648445210'
HashTable4['gis_points'] = 'ef309861d8b9ef3ab99c1fd4b854b676'
HashTable4['BASINSDATA'] = '73184ab8f497da5a8c8538b3c5c67dae'
HashTable4['LSUSDATA'] = '012e79255bbda5c8fbf8f7b0a648abae'
HashTable4['HRUSDATA'] = '74173530ac8bbe41207ce9f4c8730533'
HashTable4['WATERDATA'] = 'dda430a94d7dda7aa6a6cbeaccbbd868'
HashTable4['gis_elevationbands'] = '1a7d614a51eaa888311d51fad468f2a8'
HashTable4['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable4['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable4['gis_subbasins'] = '3cf99391e69169de17a4cfd94cf77863'
HashTable4['gis_lsus'] = '6089b4c20381bf04ff0dbbc2327bf361'
HashTable4['gis_hrus'] = '142a26e8d7493a639f4773099e54d241'
HashTable4['gis_routing'] = '39d0dbfa2527d24a03410b4119d39f5f'
HashTable4['gis_water'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable4['soils_sol'] = 'a212b2bb0012ae514f21a7cc186befc6'
HashTable4['soils_sol_layer'] = 'c1ad51d497c67e77de4d7e6cf08479f8'

#===============================================================================
# Test5:
#   - No MPI
#   - Duffins example (with triple stream reach join)
#   - stream and channel thresholds both 100 ha
#   - merges small subbasins with default 5% threshold in delineation
#   - no slope limits
#   - filter by target 170 HRUs by percentage
#===============================================================================

HashTable5 = dict()
# HashTable5['gis_channels'] = 'd9c1689f457b9f5c65840b9365a16ce7'  # unreliable
# HashTable5['gis_points'] = '333172d7cef8aebc7321c448d7fbf87e'
HashTable5['BASINSDATA'] = '21cc9d4542fdfd063be39dec2dce7d53'
HashTable5['LSUSDATA'] = '0b0b816493f1082e33275c835b3e6bc3'
HashTable5['HRUSDATA'] = 'dc41bc62aa94287f160f5284761c45b5'
HashTable5['WATERDATA'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable5['gis_elevationbands'] = 'd0eb386ed677c19696a7eadbe8bc4b3a'
HashTable5['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable5['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
# HashTable5['gis_subbasins'] = '35545a9ad2419293b459d608d9725041'
HashTable5['gis_lsus'] = '1ab8f6b91f4ddb448c0aa326996c8204'
# HashTable5['gis_hrus'] = '91e65917d5015e31c186be4e306abce4'
# HashTable5['gis_routing'] = '16ac5808a8d2abd6a5f497c5c215cfc4'
HashTable5['gis_water'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable5['soils_sol'] = '8f96b3ce8c689509a56b1741a1814053'
HashTable5['soils_sol_layer'] = 'f953ad6d6eb0d465eafd0a1db572b10d'

#===============================================================================
# Test6:
# using 16 processes is unreliable
#   - MPI 12 processes
#   - Duffins example (with triple stream reach join)
#   - delineation threshold 100 ha
#   - landscape option with stream buffering
#   - slope limits 0.5 and 1
#   - dominant landuse, soil, slope
#   - 5 percent channel merge before readFiles
#===============================================================================

HashTable6 = dict()
HashTable6['gis_channels'] = '84b14dd00e5b6c59d1f1d0af3b5f85af'
HashTable6['gis_points'] = 'c467fc36000fa7208a77cfa812e55057'
HashTable6['BASINSDATA'] = 'f3372dc8d572fbad502bff676f73c81d'
HashTable6['LSUSDATA'] = '77e782bb0afd79f1d441886004d5d1df'
HashTable6['HRUSDATA'] = '8c1430d3903cd13cb3850b5e3416cd07'
HashTable6['WATERDATA'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable6['gis_elevationbands'] = 'dda5bc5d2accf787c577a8b00c392ce7'
HashTable6['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable6['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable6['gis_subbasins'] = '8331e023226501d029e05384db54af81'
HashTable6['gis_lsus'] = '356a1eacbfd5c234d77a03ebb3667125'
HashTable6['gis_hrus'] = '57acc282115733d71f312ec485a941ed'
HashTable6['gis_routing'] = '18de4620fa93bba768ad1be6acd872c8'
HashTable6['gis_water'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable6['soils_sol'] = '8f96b3ce8c689509a56b1741a1814053'
HashTable6['soils_sol_layer'] = 'f953ad6d6eb0d465eafd0a1db572b10d'

#===============================================================================
# Test7:
#   - MPI 12 processes
#   - San Juan example
#   - delineation threshold default
#   - 7 outlets; snap threshold 600
#   - grid size 4
#   - fullHRUs
#   - dominant HRU
#===============================================================================

HashTable7 = dict()
HashTable7['gis_channels'] = '1799303e8ddaf0558fe5130f67e416b0'
HashTable7['gis_points'] = '1d8c5e427f8590e965331c69310b5068'
HashTable7['BASINSDATA'] = '0606c7097d128699daa1aa5f84ff1991'
HashTable7['LSUSDATA'] = 'e8587b7bfde9f2c83eb00871945673fc'
HashTable7['HRUSDATA'] = '63086e7031841d7d0dfb537347e90a83'
HashTable7['WATERDATA'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable7['gis_elevationbands'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable7['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable7['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable7['gis_subbasins'] = '487a0aeb4db7ebcf160af2a67aadc828'
HashTable7['gis_lsus'] = 'eb89cbc190393b7e3a329d50445e888e'
HashTable7['gis_hrus'] = '09ea6fc3dbb05f6911821a0ac73228d9'
HashTable7['gis_routing'] = '470bec874bbc252c2fc14987acc02b95'
HashTable7['gis_water'] = 'fb8d22795c61bab78aed70fd597fe40e'
HashTable7['soils_sol'] = '992437fe26f6a1faa50b612528f31657'
HashTable7['soils_sol_layer'] = '3169334ef95be1d6af6428d672e3d069'

#===============================================================================
# Test8:
#   - No MPI
#   - use existing grid
#   - no outlet
#   - no merging/adding in delineation
#   - drainage by streams 
#   - no slope limits
#   - filter by percent area 25%
#===============================================================================

HashTable8 = dict()
HashTable8['gis_channels'] = '7c9387360d5ec2bd098c546b59fe3cc5'
HashTable8['gis_points'] = 'da0437c7f3992d1c00f5ba8f5f5efa36'
HashTable8['BASINSDATA'] = 'dd19435c0ae94a1305d791ba69cf6d19'
HashTable8['LSUSDATA'] = '1041a5b25159dcf8fa503283bb2f0c5f'
HashTable8['HRUSDATA'] = '1c44274bc32a0acab932310d86d4cfb8'
HashTable8['WATERDATA'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable8['gis_elevationbands'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable8['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable8['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable8['gis_subbasins'] = '094465c45207d26372e6f1ce4d896060'
HashTable8['gis_lsus'] = 'f97ecc36922e41755fec4b4eb1ae1b97'
HashTable8['gis_hrus'] = '81bf5e40d9995ad8d5a6efee08d10d08'
HashTable8['gis_routing'] = 'de73bcc67504fdf3326a48d67c179dc4'
HashTable8['gis_water'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable8['soils_sol'] = '992437fe26f6a1faa50b612528f31657'
HashTable8['soils_sol_layer'] = '3169334ef95be1d6af6428d672e3d069'

#===============================================================================
# Test9:
#   - No MPI
#   - use existing grid
#   - 7 outlets
#   - no merging/adding in delineation
#   - drainage by grid 
#   - no slope limits
#   - filter by percent area 25%
#===============================================================================

HashTable9 = dict()
HashTable9['gis_channels'] = '1002f3843e638f892831bbc2987b82ca'
HashTable9['gis_points'] = 'c7b445143d99ebb2ccab3e3b490871b6'
HashTable9['BASINSDATA'] = 'dd19435c0ae94a1305d791ba69cf6d19'
HashTable9['LSUSDATA'] = '73a57478d8ff4b0ca66615fcba35169b'
HashTable9['HRUSDATA'] = '1c44274bc32a0acab932310d86d4cfb8'
HashTable9['WATERDATA'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable9['gis_elevationbands'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable9['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable9['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable9['gis_subbasins'] = '094465c45207d26372e6f1ce4d896060'
HashTable9['gis_lsus'] = 'e9884296148f1daab508873f0945c699'
HashTable9['gis_hrus'] = '81bf5e40d9995ad8d5a6efee08d10d08'
HashTable9['gis_routing'] = '6bd6797de18c0af22b94f3fd0b949689'
HashTable9['gis_water'] = '6f06be6293b2cec335d74b55bce9df35'
HashTable9['soils_sol'] = '992437fe26f6a1faa50b612528f31657'
HashTable9['soils_sol_layer'] = '3169334ef95be1d6af6428d672e3d069'

#===============================================================================
# Test10:
#   - No MPI
#   - use existing grid
#   - 7 outlets
#   - no merging/adding in delineation
#   - drainage by table 
#   - slope limit 1
#   - filter by landuse soil slope 2/2/2 ha (about 3 DEM cells)
#===============================================================================

HashTable10 = dict()
HashTable10['gis_channels'] = '9e4ff2232d34341352820daf7ab4a024'
HashTable10['gis_points'] = '6b84caf93a3332b31a23fc6c93ef2ae5'
HashTable10['BASINSDATA'] = 'dd19435c0ae94a1305d791ba69cf6d19'
HashTable10['LSUSDATA'] = '9482a3213f206608d87e687fed873f0c'
HashTable10['HRUSDATA'] = '3c37d9c7dc6776910248bf79a511ec0a'
HashTable10['WATERDATA'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable10['gis_elevationbands'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable10['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable10['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable10['gis_subbasins'] = '094465c45207d26372e6f1ce4d896060'
HashTable10['gis_lsus'] = '71c319e6d0f981da88326cf7a3d88717'
HashTable10['gis_hrus'] = '879665f70d31590d6a99ef81abea4820'
HashTable10['gis_routing'] = 'a024c45c32d01dd0706a3a38f51ad557'
HashTable10['gis_water'] = '6f06be6293b2cec335d74b55bce9df35'
HashTable10['soils_sol'] = '992437fe26f6a1faa50b612528f31657'
HashTable10['soils_sol_layer'] = '3169334ef95be1d6af6428d672e3d069'
HashTable10['plants_plt'] = '6082ddc24aa1e5d3511886f2eddfba8c'
HashTable10['urban_urb'] = '94ab13b7ddfd02b2aedde8912744ac17'

#===============================================================================
# Test 11:
# This test is very unreliable with 16 processes.  Changed to 6
# - MPI with 6 processes; 
# - stream threshold 5 sq km; 
# - channel threshold 0.5 sq km;
# - 1 outlet; 
# - lake;  
# - 1% channel merge; 
# - target 500 HRUs.
#===============================================================================

HashTable11 = dict()
HashTable11['gis_channels'] = '9972266008101fd0dc7f7ec83618a350'
HashTable11['gis_points'] = '7576ebcb5ff5e48c7542c40f98e84e5c'
HashTable11['BASINSDATA'] = '189866165b3890ab06af6e3ecc3732e8'
HashTable11['LSUSDATA'] = 'ec557bd5fdd1a460b54688a3e498f04d'
HashTable11['HRUSDATA'] = 'a37efd23da9484fefb9b682f06128ded'
HashTable11['WATERDATA'] = '1b14393e25e608734794c06b6566d507'
HashTable11['LAKEBASINS'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable11['LAKELINKS'] = '4ad9b335aa9d58735e72bb6ff13829b1'
HashTable11['LAKESDATA'] = 'd134901417c1c80cdc302007547adb93'
HashTable11['gis_elevationbands'] = 'c015d42982021c705249f2755571e58a'
HashTable11['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable11['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable11['gis_subbasins'] = 'ecf06c1108d9486c7dae086c1eed4e5f'
HashTable11['gis_lsus'] = 'e2a42c30b070a4e744ae53fe748e2716'
HashTable11['gis_hrus'] = 'a82e74633e2db1dbd232811d86958982'
HashTable11['gis_routing'] = '969a6bfbccb086365b9d0342058b6197'
HashTable11['gis_water'] = '967e5788e2848115d73f60a6c018b439'
HashTable11['soils_sol'] = 'b3b85be1e12b4dd9d67b11ae14187822'
HashTable11['soils_sol_layer'] = 'c827fbf53c8b43430157f4d1c76c6299'

#===============================================================================
# Test 12:
# - MPI with 6 processes; 
# - existing;
# - lake;  
# - 1% channel merge; 
# - target 500 HRUs.
#===============================================================================

HashTable12 = dict()
HashTable12['gis_channels'] = '06d0c80d42f46ea3d31daca6b918b1ba'
HashTable12['gis_points'] = '2b652dd565ca03e3c2c4eabb26d766a8'
HashTable12['BASINSDATA'] = '1d3d581fe0af032035596098d13a346e'
HashTable12['LSUSDATA'] = '4027fca8c4aa3c7260cb9df9eea21354'
HashTable12['HRUSDATA'] = '84241af0b39068eae07d2ba4bc09a91d'
HashTable12['WATERDATA'] = 'f15f76124d5b1ea8d42aeedf3319edf5'
HashTable12['LAKEBASINS'] = 'e7688062747109e112d2222049e80839'
HashTable12['LAKELINKS'] = '7010664035f83e4c00a61befb37f3f88'
HashTable12['LAKESDATA'] = '0c1bd39307c718adebacf5e1a7b655ed'
HashTable12['gis_elevationbands'] = 'c015d42982021c705249f2755571e58a'
HashTable12['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable12['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable12['gis_subbasins'] = '3f38b03098a11e0351a8995925c6c4ce'
HashTable12['gis_lsus'] = '35ba8e91724924c8348544caa8751cce'
HashTable12['gis_hrus'] = '843b86ba553dfd74ad455e41c49c932c'
HashTable12['gis_routing'] = '7ac5115c06539bf9075fe8928015ff68'
HashTable12['gis_water'] = '44d71a339adc80a88685ee52c3203827'
HashTable12['soils_sol'] = 'b3b85be1e12b4dd9d67b11ae14187822'
HashTable12['soils_sol_layer'] = 'c827fbf53c8b43430157f4d1c76c6299'

#===============================================================================
# Test 13:
# - MPI with 8 processes; 
# - stream threshold 5 sq km; 
# - channel threshold 0.5 sq km;
# - 1 outlet; 
# - grid size 4; 
# - lake; 
# - dominant HRUs
#===============================================================================

HashTable13 = dict()
HashTable13['gis_channels'] = '5db7d8513ee094540fec4583ad336c7e'
HashTable13['gis_points'] = '1b3002c1009dbe416871ad5b4de1cd0c'
HashTable13['BASINSDATA'] = '8bbf7fc105ef7636aefb4db1b98a81d2'
HashTable13['LSUSDATA'] = 'c8fce11b4312e8aaf699307ca422f8ae'
HashTable13['HRUSDATA'] = '2f293678bf7f198014c6a61960f1ca48'
HashTable13['WATERDATA'] = '2cb16454f19787e3a73ea64c54fc56a2'
HashTable13['LAKEBASINS'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable13['LAKELINKS'] = 'dd0489e1966de42004b976e18ac62425'
HashTable13['LAKESDATA'] = '6853ee17cf96cd5e8a2e576a900af977'
HashTable13['gis_elevationbands'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable13['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable13['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable13['gis_subbasins'] = 'd5f1600fc04cb260de9bacffdabfd474'
HashTable13['gis_lsus'] = 'fa6322f3751a530dee9ea729c3cdf596'
HashTable13['gis_hrus'] = '36afab7e43129723d042d0ae84b46a31'
HashTable13['gis_routing'] = '38debe3d3f5d70a044a17c104363f575'
HashTable13['gis_water'] = '776b1fcd6a42be0e51a98b92fbf5d46a'
HashTable13['soils_sol'] = '89dce60ed8e00adeaf6e69408837a32d'
HashTable13['soils_sol_layer'] = '1b1e425ca2cd8fd19d2027136a7ff833'

#===============================================================================
# Test 14:
# - MPI with 10 processes; 
# - existing grid
# - stream drainage
# - lake; 
# - dominant HRUs
#===============================================================================

HashTable14 = dict()
HashTable14['gis_channels'] = '4b7b47b70df576c26028ed5657db62f6'
HashTable14['gis_points'] = 'cd4b804dc3248c1a73db361f17a60230'
HashTable14['BASINSDATA'] = 'ecd89b8d77d9922c445d9e22cc669042'
HashTable14['LSUSDATA'] = '26fdf0c9a164b0ff14d29a5138a99079'
HashTable14['HRUSDATA'] = 'a4b859e4d47bab9567ee42ece47ac74f'
HashTable14['WATERDATA'] = 'e91c10bfa2d51b6fe53f7402a060dc83'
HashTable14['LAKEBASINS'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable14['LAKELINKS'] = 'f1434cb64d547ab7cd4e496447fb07ef'
HashTable14['LAKESDATA'] = '6853ee17cf96cd5e8a2e576a900af977'
HashTable14['gis_elevationbands'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable14['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable14['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable14['gis_subbasins'] = '4ffb23ff00bdc8493ca753fc302604fb'
HashTable14['gis_lsus'] = '244ec01dd70b67436009f80bd462c5fc'
HashTable14['gis_hrus'] = '015996e743b0a9193a8e0ae937dd48bc'
HashTable14['gis_routing'] = '22b0ce0161ae320dec98c4a0e28af356'
HashTable14['gis_water'] = '776b1fcd6a42be0e51a98b92fbf5d46a'
HashTable14['soils_sol'] = '89dce60ed8e00adeaf6e69408837a32d'
HashTable14['soils_sol_layer'] = '1b1e425ca2cd8fd19d2027136a7ff833'

#===============================================================================
# Test 15:
#   - MPI 8 process
#   - clipped San Juan DEM: no inlets/outlets file
#   - delineation threshold 6000 ha
#   - landscape by buffer, dem inversion and branch length; use dem inversion
#   - no slope limits
#   - dominant HRU
#===============================================================================

# listen to the QGIS message log
message_log = {}
def log(message, tag, level):
    message_log.setdefault(tag, [])
    message_log[tag].append((message, level,))
QgsApplication.instance().messageLog().messageReceived.connect(log)

class TestQswat(unittest.TestCase):
    """Test cases for QSWAT."""
    def setUp(self):
        """Remove old project; read test project file; prepare for delineation."""
        Processing.initialize()
        if 'native' not in [p.id() for p in QgsApplication.processingRegistry().providers()]:
            QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())
        # SRS path is not set properly.
        self.assertTrue(os.path.exists(QgsApplication.srsDatabaseFilePath()), \
                         'Need to copy resources folder to make directory {0} exist, eg copy OSGeo4W/apps/qgis/resources to OSGeo4W'.format(QgsApplication.srsDatabaseFilePath()))
        ## QSWAT plugin
        self.plugin = QSWATPlus(iface)
        ## Main QSWAT form
        self.dlg = self.plugin._odlg # useful for shorthand later
        ## Test data directory
        self.dataDir = os.path.join(self.plugin.plugin_dir, 'testdata')
        ## Project directory
        self.projDir = os.path.join(self.dataDir, 'test')
        if not os.path.exists(self.projDir):
            os.makedirs(self.projDir)
        QgsProject.instance().removeAllMapLayers()
        QgsProject.instance().clear()
        # clean up from previous runs
        projectDatabase = os.path.join(self.projDir, 'test.sqlite')
        if os.path.exists(projectDatabase):
            os.remove(projectDatabase)
        scenarios = os.path.join(self.projDir, 'Scenarios')
        if os.path.isdir(scenarios):
            shutil.rmtree(scenarios, ignore_errors=True)
        wshed = os.path.join(self.projDir, 'Watershed')
        if os.path.isdir(wshed):
            shutil.rmtree(wshed, ignore_errors=True)
        # start with empty project
        projFile = os.path.join(self.projDir, 'test.qgs')
        shutil.copy(os.path.join(self.dataDir, 'test_proj_qgs'), projFile)
        ## QGSproject instance
        self.proj = QgsProject.instance()
        self.proj.read(projFile)
        self.root = self.proj.layerTreeRoot()
        self.plugin.setupProject(self.proj, True)
        self.assertTrue(os.path.exists(self.plugin._gv.textDir) and os.path.exists(self.plugin._gv.landuseDir), 'Directories not created')
        self.assertTrue(self.dlg.delinButton.isEnabled(), 'Delineate button not enabled')
        ## Delineation object
        self.delin = Delineation(self.plugin._gv, self.plugin._demIsProcessed)
        self.delin.init()
        self.delin._dlg.numProcesses.setValue(0)
        
    def tearDown(self):
        """Clean up: make sure no database connections survive."""
        self.plugin.finish()
        
    def test01(self):
        """No MPI; single outlet only; no merging/adding in delineation; slope limit 10; percent filters 20/10/5; change numeric parameters."""
        print('\nTest 1')
        proj = QgsProject.instance()
        self.delin._dlg.selectDem.setText(self.copyDem('sj_dem.tif'))
        self.assertTrue(os.path.exists(self.delin._dlg.selectDem.text()), 'Failed to copy DEM to source directory')
        ## HRUs object
        self.hrus = HRUs(self.plugin._gv, self.dlg.reportsBox)
        # listener = Listener(self.delin, self.hrus, self.hrus.CreateHRUs)
        numLayers = len(list(proj.mapLayers().values()))
        self.assertEqual(numLayers, 0, 'Unexpected start with {0} layers'.format(numLayers))
        demLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.delin._dlg.selectDem.text(), FileTypes._DEM,
                                                         self.plugin._gv, None, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(demLayer and loaded, 'Failed to load DEM {0}'.format(self.delin._dlg.selectDem.text()))
        self.delin.setDefaultNumCells(demLayer)
        self.delin.addHillshade(self.delin._dlg.selectDem.text(), proj.layerTreeRoot(), demLayer, self.plugin._gv)
        self.assertTrue(demLayer.crs().mapUnits() == QgsUnitTypes.DistanceMeters, 'Map units not meters but {0}'.format(demLayer.crs().mapUnits()))
        QSWATUtils.copyFiles(QFileInfo(os.path.join(self.dataDir, 'sj_out.shp')), self.plugin._gv.shapesDir)
        self.delin._dlg.selectOutlets.setText(os.path.join(self.plugin._gv.shapesDir, 'sj_out.shp'))
        self.assertTrue(os.path.exists(self.delin._dlg.selectOutlets.text()), 'Failed to copy out.shp to Outlet directory')
        self.delin._dlg.useOutlets.setChecked(True)
        QtTest.QTest.mouseClick(self.delin._dlg.delinRunButton2, Qt.LeftButton)
        self.assertTrue(self.delin.areaOfCell > 0, 'Area of cell is ' + str(self.delin.areaOfCell))
        QtTest.QTest.mouseClick(self.delin._dlg.OKButton, Qt.LeftButton)
        self.assertTrue(self.dlg.hrusButton.isEnabled(), 'HRUs button not enabled')
        self.hrus.init()
        hrudlg = self.hrus._dlg
        self.hrus.landuseFile = os.path.join(self.dataDir, 'sj_land.tif')
        numLayers = len(list(proj.mapLayers().values()))
        self.hrus.landuseLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.landuseFile, FileTypes._LANDUSES, 
                                                                       self.plugin._gv, None, QSWATUtils._LANDUSE_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.landuseLayer and loaded, 'Failed to load landuse file {0}'.format(self.hrus.landuseFile))
        self.hrus.soilFile = os.path.join(self.dataDir, 'sj_soil.tif')
        numLayers = len(list(proj.mapLayers().values()))
        self.hrus.soilLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.soilFile, FileTypes._SOILS, 
                                                                    self.plugin._gv, None, QSWATUtils._SOIL_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.soilLayer and loaded, 'Failed to load soil file {0}'.format(self.hrus.soilFile))
        landCombo = hrudlg.selectLanduseTable
        landIndex = landCombo.findText('global_landuses')
        self.assertTrue(landIndex >= 0, 'Cannot find global landuses table')
        landCombo.setCurrentIndex(landIndex)
        soilCombo = hrudlg.selectSoilTable
        soilIndex = soilCombo.findText('global_soils')
        self.assertTrue(soilIndex >= 0, 'Cannot find global soils table')
        soilCombo.setCurrentIndex(soilIndex)
        usersoilCombo = hrudlg.selectUsersoilTable
        usersoilIndex = usersoilCombo.findText('global_usersoil')
        self.assertTrue(usersoilIndex >= 0, 'Cannot find global usersoil table')
        usersoilCombo.setCurrentIndex(usersoilIndex)
        self.plugin._gv.db.usersoilTable = 'global_usersoil'
        hrudlg.slopeBand.setText('10')
        self.assertTrue(hrudlg.isEnabled(), 'HRUs dialog not enabled')
        self.assertFalse(hrudlg.readFromPrevious.isChecked(), 'HRUs set to read from previous')
        self.assertFalse(hrudlg.remerge.isChecked(), 'HRUs set to re-merge')
        self.assertTrue(hrudlg.readFromMaps.isChecked(), 'HRUs not set to read from maps')
        self.assertTrue(hrudlg.insertButton.isEnabled(), 'HRUs insert button not enabled')
        QtTest.QTest.mouseClick(hrudlg.insertButton, Qt.LeftButton)
        lims = self.plugin._gv.db.slopeLimits
        self.assertTrue(len(lims) == 1 and lims[0] == 10, 'Failed to set slope limit of 10: limits list is {0!s}'.format(lims))
        self.assertTrue(hrudlg.elevBandsButton.isEnabled(), 'Elevation bands button not enabled')
        QtTest.QTest.mouseClick(hrudlg.readButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._TOPOREPORT)))
        self.assertTrue(self.dlg.reportsBox.isEnabled() and self.dlg.reportsBox.findText(Parameters._TOPOITEM) >= 0, \
                        'Elevation report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._BASINREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._BASINITEM) >= 0, \
                        'Landuse and soil report not accessible from main form')
        self.assertTrue(hrudlg.splitButton.isEnabled(), 'Split landuses button not enabled')
        self.assertTrue(hrudlg.exemptButton.isEnabled(), 'Exempt landuses button not enabled')
        self.assertTrue(hrudlg.filterLanduseButton.isEnabled(), 'Filter landuse button not enabled')
        QtTest.QTest.mouseClick(hrudlg.filterLanduseButton, Qt.LeftButton)
        self.assertTrue(hrudlg.percentButton.isEnabled(), 'Percent button not enabled')
        QtTest.QTest.mouseClick(hrudlg.percentButton, Qt.LeftButton)
        self.assertTrue(hrudlg.stackedWidget.currentIndex() == 0, 'Wrong threshold page {0} selected'.format(hrudlg.stackedWidget.currentIndex()))
        hrudlg.landuseVal.setText('20')
        self.assertTrue(hrudlg.landuseButton.isEnabled(), 'Landuse button not enabled')
        QtTest.QTest.mouseClick(hrudlg.landuseButton, Qt.LeftButton)
        hrudlg.soilVal.setText('10')
        self.assertTrue(hrudlg.soilButton.isEnabled(), 'Soil button not enabled')
        QtTest.QTest.mouseClick(hrudlg.soilButton, Qt.LeftButton)
        hrudlg.slopeVal.setText('5')
        self.assertTrue(hrudlg.createButton.isEnabled(), 'Create button not enabled')
        QtTest.QTest.mouseClick(hrudlg.createButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._HRUSREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._HRUSITEM) >= 0, \
                        'HRUs report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.shapesDir, 'lsus2.shp')), 'Actual LSUs shapefile not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'rivs.shp')), 'Reaches results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'subs.shp')), 'Watershed results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'lsus.shp')), 'LSUs results template file not created.')
        self.assertEqual(len(self.hrus.CreateHRUs.basins), 25, 'Subbasin count is {0} instead of 25'.format(len(self.hrus.CreateHRUs.basins)))
        self.assertEqual(self.hrus.CreateHRUs.countChannels(), 259, 'Channel count is {0} instead of 259'.format(self.hrus.CreateHRUs.countChannels()))
        self.assertEqual(self.hrus.CreateHRUs.countLsus(), 259, 'LSU count is {0} instead of 259'.format(self.hrus.CreateHRUs.countLsus()))
        self.assertEqual(self.hrus.CreateHRUs.countHRUs(), 851, 'HRU count is {0} instead of 848'.format(self.hrus.CreateHRUs.countHRUs()))
        #self.checkHashes(HashTable1)
        self.assertTrue(self.dlg.editButton.isEnabled(), 'SWAT Editor button not enabled')
        self.assertTrue(self.dlg.paramsButton.isEnabled(), 'Parameters button not enabled')
        params = Parameters(self.plugin._gv)
        params.run()
        pdlg = params._dlg
        self.assertEqual(int(pdlg.burninDepth.text()), 50, 'Wrong burn-in depth {0}'.format(pdlg.burninDepth.text()))
        self.assertAlmostEqual(float(pdlg.widthMult.text()), Parameters._CHANNELWIDTHMULTIPLIER, 
                               'Wrong width multiplier {0}'.format(pdlg.widthMult.text()))
        self.assertAlmostEqual(float(pdlg.widthExp.text()), Parameters._CHANNELWIDTHEXPONENT, 
                               'Wrong width exponent {0}'.format(pdlg.widthExp.text()))
        self.assertAlmostEqual(float(pdlg.depthMult.text()), Parameters._CHANNELDEPTHMULTIPLIER, 
                               'Wrong depth multiplier {0}'.format(pdlg.depthMult.text()))
        self.assertAlmostEqual(float(pdlg.depthExp.text()), Parameters._CHANNELDEPTHEXPONENT, 
                               'Wrong depth exponent {0}'.format(pdlg.depthExp.text()))
        self.assertAlmostEqual(pdlg.reachSlopeMultiplier.value(), Parameters._MULTIPLIER, 
                                'Wrong reach slope multiplier {0}'.format(pdlg.reachSlopeMultiplier.value()))
        self.assertAlmostEqual(pdlg.tributarySlopeMultiplier.value(), Parameters._MULTIPLIER, 
                                'Wrong tributary slope multiplier {0}'.format(pdlg.tributarySlopeMultiplier.value()))
        self.assertAlmostEqual(pdlg.meanSlopeMultiplier.value(), Parameters._MULTIPLIER, 
                                'Wrong mean slope multiplier {0}'.format(pdlg.meanSlopeMultiplier.value()))
        self.assertAlmostEqual(pdlg.mainLengthMultiplier.value(), Parameters._MULTIPLIER, 
                                'Wrong main length multiplier {0}'.format(pdlg.mainLengthMultiplier.value()))
        self.assertAlmostEqual(pdlg.tributaryLengthMultiplier.value(), Parameters._MULTIPLIER, 
                                'Wrong tributary length multiplier {0}'.format(pdlg.tributaryLengthMultiplier.value()))
        pdlg.burninDepth.setText('30')
        pdlg.widthMult.setText('1.5')
        pdlg.widthExp.setText('0.7')
        pdlg.depthMult.setText('0.11')
        pdlg.depthExp.setText('0.3')
        pdlg.reachSlopeMultiplier.setValue(1.5)
        pdlg.tributarySlopeMultiplier.setValue(1.3)
        pdlg.meanSlopeMultiplier.setValue(1.1)
        pdlg.mainLengthMultiplier.setValue(0.9)
        pdlg.tributaryLengthMultiplier.setValue(0.7)
        params.save()
        self.assertEqual(self.plugin._gv.burninDepth, 30, 
                         'Wrong burn-in depth {0}'.format(self.plugin._gv.burninDepth))
        self.assertAlmostEqual(self.plugin._gv.channelWidthMultiplier, 1.5, 
                               'Wrong width multiplier {0}'.format(self.plugin._gv.channelWidthMultiplier))
        self.assertAlmostEqual(self.plugin._gv.channelWidthExponent, 0.7, 
                               'Wrong width exponent {0}'.format(self.plugin._gv.channelWidthExponent))
        self.assertAlmostEqual(self.plugin._gv.channelDepthMultiplier, 0.11, 
                               'Wrong depth multiplier {0}'.format(self.plugin._gv.channelDepthMultiplier))
        self.assertAlmostEqual(self.plugin._gv.channelDepthExponent, 0.3, 
                               'Wrong depth exponent {0}'.format(self.plugin._gv.channelDepthExponent))
        self.assertAlmostEqual(self.plugin._gv.reachSlopeMultiplier, 1.5, 
                                'Wrong reach slope multiplier {}'.format(self.plugin._gv.reachSlopeMultiplier))
        self.assertAlmostEqual(self.plugin._gv.tributarySlopeMultiplier, 1.3, 
                                'Wrong tributary slope multiplier {}'.format(self.plugin._gv.tributarySlopeMultiplier))
        self.assertAlmostEqual(self.plugin._gv.meanSlopeMultiplier, 1.1, 
                                'Wrong mean slope multiplier {}'.format(self.plugin._gv.meanSlopeMultiplier))
        self.assertAlmostEqual(self.plugin._gv.mainLengthMultiplier, 0.9, 
                                'Wrong main length multiplier {}'.format(self.plugin._gv.mainLengthMultiplier))
        self.assertAlmostEqual(self.plugin._gv.tributaryLengthMultiplier, 0.7, 
                                'Wrong tributary length multiplier {}'.format(self.plugin._gv.tributaryLengthMultiplier))
        #self.checkHashes(HashTable1a)
        self.plugin.finish()               
        
    def test02(self):
        """MPI with 12 processes; stream threshold 100 sq km; channel threshold 10 sq km;
        7 inlets/outlets; snap threshold 600; FullHRUs;  6 elev bands;  area filter 500 ha."""
        print('\nTest 2')
        self.delin._dlg.selectDem.setText(self.copyDem('sj_dem.tif'))
        self.assertTrue(os.path.exists(self.delin._dlg.selectDem.text()), 'Failed to copy DEM to source directory')
        self.hrus = HRUs(self.plugin._gv, self.dlg.reportsBox)
        # listener = Listener(self.delin, self.hrus, self.hrus.CreateHRUs)
        QgsProject.instance().removeAllMapLayers()
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.assertEqual(numLayers, 0, 'Unexpected start with {0} layers'.format(numLayers))
        self.delin._dlg.numProcesses.setValue(12 if Parameters._ISWIN else 4)
        demLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.delin._dlg.selectDem.text(), FileTypes._DEM,
                                                         self.plugin._gv, None, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(demLayer and loaded, 'Failed to load DEM {0}'.format(self.delin._dlg.selectDem.text()))
        self.delin.setDefaultNumCells(demLayer)
        self.assertTrue(demLayer.crs().mapUnits() == QgsUnitTypes.DistanceMeters, 'Map units not meters but {0}'.format(demLayer.crs().mapUnits()))
        unitIndex = self.delin._dlg.areaUnitsBox.findText(Parameters._SQKM)
        self.assertTrue(unitIndex >= 0, 'Cannot find sq km area units')
        self.delin._dlg.areaUnitsBox.setCurrentIndex(unitIndex)
        self.delin.setDefaultNumCells(demLayer)
        self.delin._dlg.areaSt.setText('100')
        self.delin._dlg.areaCh.setText('10')
        self.assertTrue(self.delin._dlg.numCellsSt.text() == '14400', 
                        'Unexpected number of stream cells for delineation {0}'.format(self.delin._dlg.numCellsSt.text()))
        self.assertTrue(self.delin._dlg.numCellsCh.text() == '1440', 
                        'Unexpected number of channel cells for delineation {0}'.format(self.delin._dlg.numCellsCh.text()))
        QSWATUtils.copyFiles(QFileInfo(os.path.join(self.dataDir, 'out7.shp')), self.plugin._gv.shapesDir)
        self.delin._dlg.selectOutlets.setText(os.path.join(self.plugin._gv.shapesDir, 'out7.shp'))
        self.assertTrue(os.path.exists(self.delin._dlg.selectOutlets.text()), 'Failed to find outlet file {0}'.format(self.delin._dlg.selectOutlets.text()))
        self.delin._dlg.useOutlets.setChecked(True)
        # QtTest.QTest.mouseClick(self.delin._dlg.delinRunButton2, Qt.LeftButton)
        # self.assertTrue('7 snapped: 1 failed' in self.delin._dlg.snappedLabel.text(), 'Unexpected snapping result: {0}'.format(self.delin._dlg.snappedLabel.text()))
        self.delin._dlg.snapThreshold.setText('600')
        QtTest.QTest.mouseClick(self.delin._dlg.delinRunButton2, Qt.LeftButton)
        self.assertTrue('7 snapped' in self.delin._dlg.snappedLabel.text(), 'Unexpected snapping result: {0}'.format(self.delin._dlg.snappedLabel.text()))
        self.assertTrue(self.delin.areaOfCell > 0, 'Area of cell is ' + str(self.delin.areaOfCell))
        QtTest.QTest.mouseClick(self.delin._dlg.OKButton, Qt.LeftButton)
        self.assertTrue(self.dlg.hrusButton.isEnabled(), 'HRUs button not enabled')
        self.hrus.init()
        hrudlg = self.hrus._dlg
        self.hrus.landuseFile = os.path.join(self.dataDir, 'sj_land.tif')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.hrus.landuseLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.landuseFile, FileTypes._LANDUSES, 
                                                                       self.plugin._gv, None, QSWATUtils._LANDUSE_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.landuseLayer and loaded, 'Failed to load landuse file {0}'.format(self.hrus.landuseFile))
        self.hrus.soilFile = os.path.join(self.dataDir, 'sj_soil.tif')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.hrus.soilLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.soilFile, FileTypes._SOILS, 
                                                                    self.plugin._gv, None, QSWATUtils._SOIL_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.soilLayer and loaded, 'Failed to load soil file {0}'.format(self.hrus.soilFile))
        landCombo = hrudlg.selectLanduseTable
        landIndex = landCombo.findText('global_landuses')
        self.assertTrue(landIndex >= 0, 'Cannot find global landuses table')
        landCombo.setCurrentIndex(landIndex)
        soilCombo = hrudlg.selectSoilTable
        soilIndex = soilCombo.findText('global_soils')
        self.assertTrue(soilIndex >= 0, 'Cannot find global soils table')
        soilCombo.setCurrentIndex(soilIndex)
        usersoilCombo = hrudlg.selectUsersoilTable
        usersoilIndex = usersoilCombo.findText('global_usersoil')
        self.assertTrue(usersoilIndex >= 0, 'Cannot find global usersoil table')
        usersoilCombo.setCurrentIndex(usersoilIndex)
        self.plugin._gv.db.usersoilTable = 'global_usersoil'
        lims = self.plugin._gv.db.slopeLimits
        self.assertTrue(len(lims) == 0, 'Limits list is not empty')
        self.assertTrue(hrudlg.elevBandsButton.isEnabled(), 'Elevation bands button not enabled')
        self.plugin._gv.elevBandsThreshold = 2000
        self.plugin._gv.numElevBands = 6
        hrudlg.generateFullHRUs.setChecked(True)
        QtTest.QTest.mouseClick(hrudlg.readButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.shapesDir, 'hrus1.shp')), 'Full HRUs shapefile not created')
        fullHrusLayer = QSWATUtils.getLayerByLegend(QSWATUtils._FULLHRUSLEGEND, self.root.findLayers())
        self.assertTrue(fullHrusLayer, 'FullHRUs file not loaded')
        self.assertTrue(fullHrusLayer.layer().featureCount() == 722, 'Unexpected number of full HRUs: {0}'.format(fullHrusLayer.layer().featureCount()))
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._TOPOREPORT)))
        self.assertTrue(self.dlg.reportsBox.isEnabled() and self.dlg.reportsBox.findText(Parameters._TOPOITEM) >= 0, \
                        'Elevation report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._BASINREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._BASINITEM) >= 0, \
                        'Landuse and soil report not accessible from main form')
        self.assertTrue(hrudlg.splitButton.isEnabled(), 'Split landuses button not enabled')
        self.assertTrue(hrudlg.exemptButton.isEnabled(), 'Exempt landuses button not enabled')
        self.assertTrue(hrudlg.filterAreaButton.isEnabled(), 'Filter area button not enabled')
        QtTest.QTest.mouseClick(hrudlg.filterAreaButton, Qt.LeftButton)
        self.assertTrue(hrudlg.areaButton.isEnabled(), 'Area button not enabled')
        QtTest.QTest.mouseClick(hrudlg.areaButton, Qt.LeftButton)
        self.assertTrue(hrudlg.stackedWidget.currentIndex() == 1, 'Wrong threshold page {0} selected'.format(hrudlg.stackedWidget.currentIndex()))
        hrudlg.areaVal.setText('500')
        self.assertTrue(hrudlg.createButton.isEnabled(), 'Create button not enabled')
        QtTest.QTest.mouseClick(hrudlg.createButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._HRUSREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._HRUSITEM) >= 0, \
                        'HRUs report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.shapesDir, 'lsus2.shp')), 'Actual LSUs shapefile not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.shapesDir, 'hrus2.shp')), 'Actual HRUs shapefile not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'hrus.shp')), 'HRUs results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'rivs.shp')), 'Reaches results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'subs.shp')), 'Watershed results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'lsus.shp')), 'LSUs results template file not created.')
        self.assertEqual(len(self.hrus.CreateHRUs.basins), 25, 'Subbasin count is {0} instead of 25'.format(len(self.hrus.CreateHRUs.basins)))
        self.assertEqual(self.hrus.CreateHRUs.countChannels(), 242, 'Channel count is {0} instead of 242'.format(self.hrus.CreateHRUs.countChannels()))
        self.assertEqual(self.hrus.CreateHRUs.countLsus(), 242, 'LSU count is {0} instead of 242'.format(self.hrus.CreateHRUs.countLsus()))
        self.assertEqual(self.hrus.CreateHRUs.countHRUs(), 319, 'HRU count is {0} instead of 319'.format(self.hrus.CreateHRUs.countHRUs()))
        #self.checkHashes(HashTable2)
        self.assertTrue(self.dlg.editButton.isEnabled(), 'SWAT Editor button not enabled')
        self.plugin.finish()
        
    def test03(self):
        """No MPI; stream threshold 14400 cells; channel threshold 1440 cells; single outlet; 
        merge subbasins; split and exempts; target by area 400."""
        print('\nTest 3')
        self.delin._dlg.selectDem.setText(self.copyDem('sj_dem.tif'))
        self.assertTrue(os.path.exists(self.delin._dlg.selectDem.text()), 'Failed to copy DEM to source directory')
        self.hrus = HRUs(self.plugin._gv, self.dlg.reportsBox)
        # listener = Listener(self.delin, self.hrus, self.hrus.CreateHRUs)
        QgsProject.instance().removeAllMapLayers()
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.assertEqual(numLayers, 0, 'Not all map layers removed')
        demLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.delin._dlg.selectDem.text(), FileTypes._DEM,
                                                         self.plugin._gv, None, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(demLayer and loaded, 'Failed to load DEM {0}'.format(self.delin._dlg.selectDem.text()))
        self.delin.setDefaultNumCells(demLayer)
        self.assertTrue(demLayer.crs().mapUnits() == QgsUnitTypes.DistanceMeters, 'Map units not meters but {0}'.format(demLayer.crs().mapUnits()))
        unitIndex = self.delin._dlg.areaUnitsBox.findText(Parameters._SQKM)
        self.assertTrue(unitIndex >= 0, 'Cannot find sq km area units')
        self.delin._dlg.areaUnitsBox.setCurrentIndex(unitIndex)
        self.delin.setDefaultNumCells(demLayer)
        self.delin._dlg.numCellsSt.setText('14400')
        self.delin._dlg.numCellsCh.setText('1440')
        self.assertTrue(self.delin._dlg.areaSt.text() == '100', 'Unexpected area for streams {0}'.format(self.delin._dlg.areaSt.text()))
        self.assertTrue(self.delin._dlg.areaCh.text() == '10', 'Unexpected area for channels {0}'.format(self.delin._dlg.areaCh.text()))
        QSWATUtils.copyFiles(QFileInfo(os.path.join(self.dataDir, 'sj_out.shp')), self.plugin._gv.shapesDir)
        self.delin._dlg.selectOutlets.setText(os.path.join(self.plugin._gv.shapesDir, 'sj_out.shp'))
        self.assertTrue(os.path.exists(self.delin._dlg.selectOutlets.text()), 'Failed to copy out.shp to Outlet directory')
        self.delin._dlg.useOutlets.setChecked(True)
        self.delin._dlg.numProcesses.setValue(0)
        QtTest.QTest.mouseClick(self.delin._dlg.delinRunButton2, Qt.LeftButton)
        self.assertTrue(self.delin.areaOfCell > 0, 'Area of cell is ' + str(self.delin.areaOfCell))
        # merge basins 10, 13 and 4
        subbasinsLayer = QSWATUtils.getLayerByLegend(FileTypes.legend(FileTypes._SUBBASINS), self.root.findLayers())
        self.assertTrue(subbasinsLayer, 'No subbasins layer')
        subbasinsLayer.layer().select([10, 13, 4]) # polygon ids 23, 27 and 4
        # this does not seem to work in actually calling mergeSubbasins
        # QtTest.QTest.mouseClick(self.delin._dlg.mergeButton, Qt.LeftButton)
        self.delin.mergeSubbasins()
# no longer included
#         # add reservoirs to 1 and 15
#         self.delin.extraReservoirBasins = {1, 15}
#         # add point sources
#         self.delin._dlg.checkAddPoints.setChecked(True)
#         # this does not seem to work in actually calling addReservoirs
#         # QtTest.QTest.mouseClick(self.delin._dlg.addButton, Qt.LeftButton)
#         self.delin.addReservoirs()
        QtTest.QTest.mouseClick(self.delin._dlg.OKButton, Qt.LeftButton)
        self.assertTrue(self.dlg.hrusButton.isEnabled(), 'HRUs button not enabled')
        self.hrus.init()
        hrudlg = self.hrus._dlg
        self.hrus.landuseFile = os.path.join(self.dataDir, 'sj_land.tif')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.hrus.landuseLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.landuseFile, FileTypes._LANDUSES, 
                                                                       self.plugin._gv, None, QSWATUtils._LANDUSE_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.landuseLayer and loaded, 'Failed to load landuse file {0}'.format(self.hrus.landuseFile))
        self.hrus.soilFile = os.path.join(self.dataDir, 'sj_soil.tif')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.hrus.soilLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.soilFile, FileTypes._SOILS, 
                                                                    self.plugin._gv, None, QSWATUtils._SOIL_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.soilLayer and loaded, 'Failed to load soil file {0}'.format(self.hrus.soilFile))
        landCombo = hrudlg.selectLanduseTable
        landIndex = landCombo.findText('global_landuses')
        self.assertTrue(landIndex >= 0, 'Cannot find global landuses table')
        landCombo.setCurrentIndex(landIndex)
        soilCombo = hrudlg.selectSoilTable
        soilIndex = soilCombo.findText('global_soils')
        self.assertTrue(soilIndex >= 0, 'Cannot find global soils table')
        soilCombo.setCurrentIndex(soilIndex)
        usersoilCombo = hrudlg.selectUsersoilTable
        usersoilIndex = usersoilCombo.findText('global_usersoil')
        self.assertTrue(usersoilIndex >= 0, 'Cannot find global usersoil table')
        usersoilCombo.setCurrentIndex(usersoilIndex)
        self.plugin._gv.db.usersoilTable = 'global_usersoil'
        self.assertTrue(hrudlg.elevBandsButton.isEnabled(), 'Elevation bands button not enabled')
        QtTest.QTest.mouseClick(hrudlg.readButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._TOPOREPORT)))
        self.assertTrue(self.dlg.reportsBox.isEnabled() and self.dlg.reportsBox.findText(Parameters._TOPOITEM) >= 0, \
                        'Elevation report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._BASINREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._BASINITEM) >= 0, \
                        'Landuse and soil report not accessible from main form')
        self.assertTrue(hrudlg.splitButton.isEnabled(), 'Split landuses button not enabled')
        # split GRAS into 10% SWRN and 90% RNGE
        self.plugin._gv.splitLanduses.clear()
        self.plugin._gv.splitLanduses['GRAS'] = dict()
        self.plugin._gv.splitLanduses['GRAS']['SWRN'] = 10
        self.plugin._gv.splitLanduses['GRAS']['RNGE'] = 90
        self.assertTrue(hrudlg.exemptButton.isEnabled(), 'Exempt landuses button not enabled')
        self.plugin._gv.exemptLanduses = ['CRDY', 'SWRN']
        self.assertTrue(hrudlg.targetButton.isEnabled(), 'Target button not enabled')
        QtTest.QTest.mouseClick(hrudlg.targetButton, Qt.LeftButton)
        self.assertTrue(hrudlg.areaButton.isEnabled(), 'Area button not enabled')
        QtTest.QTest.mouseClick(hrudlg.areaButton, Qt.LeftButton)
        self.assertTrue(hrudlg.stackedWidget.currentIndex() == 2, 'Wrong threshold page {0} selected'.format(hrudlg.stackedWidget.currentIndex()))
        hrudlg.targetSlider.setValue(400)
        self.assertTrue(hrudlg.createButton.isEnabled(), 'Create button not enabled')
        QtTest.QTest.mouseClick(hrudlg.createButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._HRUSREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._HRUSITEM) >= 0, \
                        'HRUs report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.shapesDir, 'lsus2.shp')), 'Actual LSUs shapefile not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'rivs.shp')), 'Reaches results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'subs.shp')), 'Watershed results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'lsus.shp')), 'LSUs results template file not created.')
        self.assertEqual(len(self.hrus.CreateHRUs.basins), 26, 'Subbasin count is {0} instead of 26'.format(len(self.hrus.CreateHRUs.basins)))
        self.assertEqual(self.hrus.CreateHRUs.countChannels(), 329, 'Channel count is {0} instead of 329'.format(self.hrus.CreateHRUs.countChannels()))
        self.assertEqual(self.hrus.CreateHRUs.countLsus(), 329, 'LSU count is {0} instead of 329'.format(self.hrus.CreateHRUs.countLsus()))
        self.assertEqual(self.hrus.CreateHRUs.countHRUs(), 557, 'HRU count is {0} instead of 557'.format(self.hrus.CreateHRUs.countHRUs()))
        #if Parameters._ISWIN:
        #    self.checkHashes(HashTable3)
        self.assertTrue(self.dlg.hrusButton.isEnabled(), 'HRUs button not enabled')
        self.hrus = HRUs(self.plugin._gv, self.dlg.reportsBox)
        self.hrus.init()
        hrudlg = self.hrus._dlg
        # landuse and soil files were simply loaded, not copied to Landuses/Soils directories
        self.assertTrue(filecmp.cmp(hrudlg.selectLanduse.text(), os.path.join(self.dataDir, 'sj_land.tif')), 
                         'Landuse file not set: {0} instead of {1}'.format(hrudlg.selectLanduse.text(), os.path.join(self.dataDir, 'sj_land.tif')))
        self.assertEqual(hrudlg.selectLanduseTable.currentText(), 'global_landuses',
                         'Landuse table not set: {}'.format(hrudlg.selectLanduseTable.currentText()))
        self.assertTrue(filecmp.cmp(hrudlg.selectSoil.text(), os.path.join(self.dataDir, 'sj_soil.tif')), 
                         'Soil file not set: {0} instead of {1}'.format(hrudlg.selectSoil.text(), os.path.join(self.dataDir, 'sj_soil.tif')))
        self.assertEqual(hrudlg.selectSoilTable.currentText(), 'global_soils',
                         'Soil table not set: {}'.format(hrudlg.selectSoilTable.currentText()))
        self.assertTrue(hrudlg.usersoilButton.isChecked(), 'Usersoil not selected')
        self.assertTrue(filecmp.cmp(hrudlg.plantSoilDatabase.text(), self.plugin._gv.db.dbFile), 
                         'Soil database not set: {0} instead of {1}'.format(hrudlg.plantSoilDatabase.text(), self.plugin._gv.db.dbFile))
        self.assertTrue(hrudlg.floodplainCombo.currentIndex() == 0, 
                        'Floodplain combo index wrong: {0}'.format(hrudlg.floodplainCombo.currentIndex()))
        self.assertTrue(hrudlg.readFromPrevious.isEnabled(), 'Read from previous not enabled')
        self.assertTrue(hrudlg.readFromPrevious.isChecked(), 'Read from previous not checked')
        QtTest.QTest.mouseClick(hrudlg.readButton, Qt.LeftButton)
        self.assertTrue(hrudlg.targetButton.isChecked, 'Target buitton not checked')
        self.assertTrue(hrudlg.areaButton.isChecked(), 'Area button not checked')
        self.assertTrue(hrudlg.stackedWidget.currentIndex() == 2, 
                        'Wrong threshold page {0} selected'.format(hrudlg.stackedWidget.currentIndex()))
        self.assertTrue(hrudlg.targetSlider.value() == 400, 'Area slider set to wrong value: {0}'.format(hrudlg.targetSlider.value()))
        self.assertTrue(hrudlg.createButton.isEnabled(), 'Create button not enabled')
        QtTest.QTest.mouseClick(hrudlg.createButton, Qt.LeftButton)
        self.assertEqual(len(self.hrus.CreateHRUs.basins), 26, 'Subbasin count after rerun is {0} instead of 26'.format(len(self.hrus.CreateHRUs.basins)))
        self.assertEqual(self.hrus.CreateHRUs.countChannels(), 329, 'Channel count after rerun is {0} instead of 329'.format(self.hrus.CreateHRUs.countChannels()))
        self.assertEqual(self.hrus.CreateHRUs.countLsus(), 329, 'LSU count is {0} instead of 329'.format(self.hrus.CreateHRUs.countLsus()))
        self.assertEqual(self.hrus.CreateHRUs.countHRUs(), 557, 'HRU count after rerun is {0} instead of 557'.format(self.hrus.CreateHRUs.countHRUs()))
        #====This test does not work, because HRU numbering can change, and perhaps numerical accuracy also
        # # check tables again to confirm recalculating HRUs from saved data made no difference
        # self.checkHashes(HashTable3)
        #=======================================================================
        self.assertTrue(self.dlg.editButton.isEnabled(), 'SWAT Editor button not enabled')
        self.plugin.finish()
        
    def test04(self):
        """No MPI; use existing; no outlet; no merging/adding in delineation; FullHRUs; 
        no slope limits; channel merge set to 10 and readFiles rerun; filter by percent area 10%."""
        print('\nTest 4')
        self.delin._dlg.selectDem.setText(self.copyDem('sj_dem.tif'))
        self.assertTrue(os.path.exists(self.delin._dlg.selectDem.text()), 'Failed to copy DEM to source directory')
        self.hrus = HRUs(self.plugin._gv, self.dlg.reportsBox)
        # listener = Listener(self.delin, self.hrus, self.hrus.CreateHRUs)
        QgsProject.instance().removeAllMapLayers()
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.assertEqual(numLayers, 0, 'Not all map layers removed')
        demLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.delin._dlg.selectDem.text(), FileTypes._DEM,
                                                         self.plugin._gv, None, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(demLayer and loaded, 'Failed to load DEM {0}'.format(self.delin._dlg.selectDem.text()))
        self.delin.setDefaultNumCells(demLayer)
        self.assertTrue(demLayer.crs().mapUnits() == QgsUnitTypes.DistanceMeters, 'Map units not meters but {0}'.format(demLayer.crs().mapUnits()))
        self.delin._dlg.tabWidget.setCurrentIndex(1)
        subbasinsFile = os.path.join(self.dataDir, 'sj_demsubbasins.shp')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        subbasinsLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), subbasinsFile, FileTypes._EXISTINGSUBBASINS, 
                                                               self.plugin._gv, demLayer, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(subbasinsLayer and loaded, 'Failed to load subbasins shapefile'.format(subbasinsFile))
        self.delin._dlg.selectSubbasins.setText(subbasinsFile)
        self.plugin._gv.subbasinsFile = subbasinsFile        
        wshedFile = os.path.join(self.dataDir, 'sj_demwshed.shp')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        wshedLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), wshedFile, FileTypes._EXISTINGWATERSHED, 
                                                           self.plugin._gv, None, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(wshedLayer and loaded, 'Failed to load wshed shapefile'.format(wshedFile))
        self.delin._dlg.selectWshed.setText(wshedFile)
        self.plugin._gv.wshedFile = wshedFile
        channelFile = os.path.join(self.dataDir, 'sj_demchannel.shp')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        channelLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), channelFile, FileTypes._STREAMS, 
                                                             self.plugin._gv, None, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(channelLayer and loaded, 'Failed to load channels shapefile'.format(channelFile))
        self.delin._dlg.selectStreams.setText(channelFile)
        self.plugin._gv.channelFile = channelFile
        self.delin._dlg.numProcesses.setValue(0)
        QtTest.QTest.mouseClick(self.delin._dlg.existRunButton, Qt.LeftButton)
        self.assertTrue(self.delin.isDelineated, 'Delineation incomplete')
        QtTest.QTest.mouseClick(self.delin._dlg.OKButton, Qt.LeftButton)
        self.assertTrue(self.dlg.hrusButton.isEnabled(), 'HRUs button not enabled')
        self.hrus.init()
        hrudlg = self.hrus._dlg
        self.hrus.landuseFile = os.path.join(self.dataDir, 'sj_land.tif')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.hrus.landuseLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.landuseFile, FileTypes._LANDUSES, 
                                                                       self.plugin._gv, None, QSWATUtils._LANDUSE_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.landuseLayer and loaded, 'Failed to load landuse file {0}'.format(self.hrus.landuseFile))
        self.hrus.soilFile = os.path.join(self.dataDir, 'sj_soil.tif')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.hrus.soilLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.soilFile, FileTypes._SOILS, 
                                                                    self.plugin._gv, None, QSWATUtils._SOIL_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.soilLayer and loaded, 'Failed to load soil file {0}'.format(self.hrus.soilFile))
        landCombo = hrudlg.selectLanduseTable
        landIndex = landCombo.findText('global_landuses')
        self.assertTrue(landIndex >= 0, 'Cannot find global landuses table')
        landCombo.setCurrentIndex(landIndex)
        soilCombo = hrudlg.selectSoilTable
        soilIndex = soilCombo.findText('global_soils')
        self.assertTrue(soilIndex >= 0, 'Cannot find global soils table')
        soilCombo.setCurrentIndex(soilIndex)
        usersoilCombo = hrudlg.selectUsersoilTable
        usersoilIndex = usersoilCombo.findText('global_usersoil')
        self.assertTrue(usersoilIndex >= 0, 'Cannot find global usersoil table')
        usersoilCombo.setCurrentIndex(usersoilIndex)
        self.plugin._gv.db.usersoilTable = 'global_usersoil'
        self.assertTrue(hrudlg.elevBandsButton.isEnabled(), 'Elevation bands button not enabled')
        hrudlg.generateFullHRUs.setChecked(True)
        self.assertTrue(hrudlg.channelMergeSlider.value() == 0, 'Remerge slider not 0 but {0}'.format(hrudlg.channelMergeSlider.value()))
        QtTest.QTest.mouseClick(hrudlg.readButton, Qt.LeftButton)
        hrudlg.channelMergeSlider.setValue(10)
        self.hrus.changeChannelThreshold()
        self.assertTrue(hrudlg.channelMergeVal.text() == '10', 'Failed to set channel merge value to 10: has value {0}'.format(hrudlg.channelMergeVal.text()))
        self.assertTrue(hrudlg.remerge.isChecked(), 'Remerge button not checked')
        QtTest.QTest.mouseClick(hrudlg.readButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.shapesDir, 'hrus1.shp')), 'Full HRUs file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._TOPOREPORT)))
        self.assertTrue(self.dlg.reportsBox.isEnabled() and self.dlg.reportsBox.findText(Parameters._TOPOITEM) >= 0, \
                        'Elevation report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._BASINREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._BASINITEM) >= 0, \
                        'Landuse and soil report not accessible from main form')
        self.assertTrue(hrudlg.splitButton.isEnabled(), 'Split landuses button not enabled')
        self.assertTrue(hrudlg.exemptButton.isEnabled(), 'Exempt landuses button not enabled')
        self.assertTrue(hrudlg.filterAreaButton.isEnabled(), 'Filter by area button not enabled')
        QtTest.QTest.mouseClick(hrudlg.filterAreaButton, Qt.LeftButton)
        self.assertTrue(hrudlg.percentButton.isEnabled(), 'Area button not enabled')
        QtTest.QTest.mouseClick(hrudlg.percentButton, Qt.LeftButton)
        self.assertTrue(hrudlg.stackedWidget.currentIndex() == 1, 'Wrong threshold page {0} selected'.format(hrudlg.stackedWidget.currentIndex()))
        hrudlg.areaSlider.setValue(10)
        self.assertTrue(hrudlg.createButton.isEnabled(), 'Create button not enabled')
        QtTest.QTest.mouseClick(hrudlg.createButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._HRUSREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._HRUSITEM) >= 0, \
                        'HRUs report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.shapesDir, 'lsus2.shp')), 'Actual LSUs shapefile not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.shapesDir, 'hrus2.shp')), 'Actual HRUs shapefile not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'hrus.shp')), 'HRUs results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'rivs.shp')), 'Reaches results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'subs.shp')), 'Watershed results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'lsus.shp')), 'LSUs results template file not created.')
        self.assertEqual(len(self.hrus.CreateHRUs.basins), 29, 'Subbasin count is {0} instead of 29'.format(len(self.hrus.CreateHRUs.basins)))
        self.assertEqual(self.hrus.CreateHRUs.countChannels(), 107, 'Channel count is {0} instead of 107'.format(self.hrus.CreateHRUs.countChannels()))
        self.assertEqual(self.hrus.CreateHRUs.countLsus(), 107, 'LSU count is {0} instead of 107'.format(self.hrus.CreateHRUs.countLsus()))
        self.assertEqual(self.hrus.CreateHRUs.countHRUs(), 252, 'HRU count is {0} instead of 252'.format(self.hrus.CreateHRUs.countHRUs()))
        #if Parameters._ISWIN:
        #    self.checkHashes(HashTable4)
        self.assertTrue(self.dlg.editButton.isEnabled(), 'SWAT Editor button not enabled')
        self.plugin.finish()
        
    def test05(self):
        """No MPI; Duffins example (with triple stream reach join); delineation threshold 100 ha; merges small subbasins with default 5% threshold;  no slope limits; target 170 HRUs by percentage."""
        print('\nTest 5')
        demFileName = self.copyDem('duff_dem.tif')
        self.delin._dlg.selectDem.setText(demFileName)
        self.assertTrue(os.path.exists(self.delin._dlg.selectDem.text()), 'Failed to copy DEM to source directory')
        self.hrus = HRUs(self.plugin._gv, self.dlg.reportsBox)
        # listener = Listener(self.delin, self.hrus, self.hrus.CreateHRUs)
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.assertEqual(numLayers, 0, 'Unexpected start with {0} layers'.format(numLayers))
        demLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.delin._dlg.selectDem.text(), FileTypes._DEM,
                                                         self.plugin._gv, None, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(demLayer and loaded, 'Failed to load DEM {0}'.format(self.delin._dlg.selectDem.text()))
        self.delin.setDefaultNumCells(demLayer)
        self.assertTrue(demLayer.crs().mapUnits() == QgsUnitTypes.DistanceMeters, 'Map units not meters but {0}'.format(demLayer.crs().mapUnits()))
        unitIndex = self.delin._dlg.areaUnitsBox.findText(Parameters._HECTARES)
        self.assertTrue(unitIndex >= 0, 'Cannot find hectares area units')
        self.delin._dlg.areaUnitsBox.setCurrentIndex(unitIndex)
        self.delin.setDefaultNumCells(demLayer)
        self.delin._dlg.areaSt.setText('100')
        self.delin._dlg.areaCh.setText('100')
        self.assertTrue(self.delin._dlg.numCellsSt.text() == '100', 'Unexpected number of cells for streams {0}'.format(self.delin._dlg.numCellsSt.text()))
        self.assertTrue(self.delin._dlg.numCellsCh.text() == '100', 'Unexpected number of cells for channels{0}'.format(self.delin._dlg.numCellsCh.text()))
        QSWATUtils.copyFiles(QFileInfo(os.path.join(self.dataDir, 'duff_out.shp')), self.plugin._gv.shapesDir)
        self.delin._dlg.selectOutlets.setText(os.path.join(self.plugin._gv.shapesDir, 'duff_out.shp'))
        self.assertTrue(os.path.exists(self.delin._dlg.selectOutlets.text()), 'Failed to copy duff_out.shp to Outlet directory')
        self.delin._dlg.useOutlets.setChecked(True)
        QtTest.QTest.mouseClick(self.delin._dlg.delinRunButton2, Qt.LeftButton)
        self.assertTrue(self.delin.areaOfCell > 0, 'Area of cell is ' + str(self.delin.areaOfCell))
        self.assertTrue(self.delin._dlg.selectSubButton.isEnabled(), 'Select subbasins button not enabled')
        demName = os.path.split(os.path.splitext(demFileName)[0])[1]
        subbasinsFileName = os.path.join(self.plugin._gv.shapesDir, demName + 'subbasins.shp')
        self.assertTrue(os.path.exists(subbasinsFileName), 'Failed to make watershed shapefile {0}'.format(subbasinsFileName))
        subbasinsLayer = QSWATUtils.getLayerByFilename(self.root.findLayers(), subbasinsFileName, FileTypes._WATERSHED, None, None, None)[0]
        self.assertTrue(subbasinsLayer, 'Cannot find watershed layer')
        numSubs = subbasinsLayer.featureCount()
        selSubs = SelectSubbasins(self.plugin._gv, subbasinsLayer)
        selSubs.init()
        selSubs._dlg.checkBox.setChecked(True)
        #QtTest.QTest.mouseClick(selSubs._dlg.pushButton, Qt.LeftButton)
        selSubs.selectByThreshold()
        self.waitCountChanged(subbasinsLayer.selectedFeatureCount, 0)
        #QtTest.QTest.mouseClick(selSubs._dlg.saveButton, Qt.LeftButton)
        selSubs.save()
        self.assertEqual(subbasinsLayer.selectedFeatureCount(), 6, 'Unexpected number of subbasins selected: {0!s}'.format(subbasinsLayer.selectedFeatureCount()))
        self.delin.mergeSubbasins()
        #QtTest.QTest.mouseClick(self.delin._dlg.mergeButton, Qt.LeftButton)
        self.waitCountChanged(subbasinsLayer.featureCount, numSubs)
        self.assertEqual(numSubs, 140, 'Wrong total subbasins {0!s}'.format(numSubs))
        self.assertEqual(subbasinsLayer.featureCount(), 134, 'Wrong number of subbasins merged: {0!s}'.format(subbasinsLayer.featureCount()))
        QtTest.QTest.mouseClick(self.delin._dlg.OKButton, Qt.LeftButton)
        self.assertTrue(self.dlg.hrusButton.isEnabled(), 'HRUs button not enabled')
        self.hrus.init()
        hrudlg = self.hrus._dlg
        self.hrus.landuseFile = os.path.join(self.dataDir, 'duff_landuse.tif')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.hrus.landuseLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.landuseFile, FileTypes._LANDUSES, 
                                                                       self.plugin._gv, None, QSWATUtils._LANDUSE_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.landuseLayer and loaded, 'Failed to load landuse file {0}'.format(self.hrus.landuseFile))
        self.hrus.soilFile = os.path.join(self.dataDir, 'duff_soil.tif')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.hrus.soilLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.soilFile, FileTypes._SOILS, 
                                                                    self.plugin._gv, None, QSWATUtils._SOIL_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.soilLayer and loaded, 'Failed to load soil file {0}'.format(self.hrus.soilFile))
        landCombo = hrudlg.selectLanduseTable
        landIndex = landCombo.findText('global_landuses')
        self.assertTrue(landIndex >= 0, 'Cannot find global landuses table')
        landCombo.setCurrentIndex(landIndex)
        soilCombo = hrudlg.selectSoilTable
        soilIndex = soilCombo.findText('global_soils')
        self.assertTrue(soilIndex >= 0, 'Cannot find global soils table')
        soilCombo.setCurrentIndex(soilIndex)
        usersoilCombo = hrudlg.selectUsersoilTable
        usersoilIndex = usersoilCombo.findText('global_usersoil')
        self.assertTrue(usersoilIndex >= 0, 'Cannot find global usersoil table')
        usersoilCombo.setCurrentIndex(usersoilIndex)
        self.plugin._gv.db.usersoilTable = 'global_usersoil'
        lims = self.plugin._gv.db.slopeLimits
        self.assertTrue(len(lims) == 0, 'Failed to start with empty slope limits: limits list is {0!s}'.format(lims))
        self.assertTrue(hrudlg.elevBandsButton.isEnabled(), 'Elevation bands button not enabled')
        QtTest.QTest.mouseClick(hrudlg.readButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._TOPOREPORT)))
        self.assertTrue(self.dlg.reportsBox.isEnabled() and self.dlg.reportsBox.findText(Parameters._TOPOITEM) >= 0, \
                        'Elevation report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._BASINREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._BASINITEM) >= 0, \
                        'Landuse and soil report not accessible from main form')
        self.assertTrue(hrudlg.splitButton.isEnabled(), 'Split landuses button not enabled')
        self.assertTrue(hrudlg.exemptButton.isEnabled(), 'Exempt landuses button not enabled')
        self.assertTrue(hrudlg.targetButton.isEnabled(), 'Target button not enabled')
        QtTest.QTest.mouseClick(hrudlg.targetButton, Qt.LeftButton)
        self.assertTrue(hrudlg.percentButton.isEnabled(), 'Percent button not enabled')
        QtTest.QTest.mouseClick(hrudlg.percentButton, Qt.LeftButton)
        self.assertTrue(hrudlg.stackedWidget.currentIndex() == 2, 'Wrong threshold page {0} selected'.format(hrudlg.stackedWidget.currentIndex()))
        hrudlg.targetVal.setText('170')
        self.assertTrue(hrudlg.createButton.isEnabled(), 'Create button not enabled')
        QtTest.QTest.mouseClick(hrudlg.createButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._HRUSREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._HRUSITEM) >= 0, \
                        'HRUs report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.shapesDir, 'lsus2.shp')), 'Actual LSUs shapefile not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'rivs.shp')), 'Reaches results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'subs.shp')), 'Watershed results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'lsus.shp')), 'LSUs results template file not created.')
        self.assertEqual(len(self.hrus.CreateHRUs.basins), 134, 'Subbasin count is {0} instead of 134'.format(len(self.hrus.CreateHRUs.basins)))
        self.assertEqual(self.hrus.CreateHRUs.countChannels(), 140, 'Channel count is {0} instead of 140'.format(self.hrus.CreateHRUs.countChannels()))
        self.assertEqual(self.hrus.CreateHRUs.countLsus(), 140, 'LSU count is {0} instead of 140'.format(self.hrus.CreateHRUs.countLsus()))
        self.assertEqual(self.hrus.CreateHRUs.countHRUs(), 170, 'HRU count is {0} instead of 170'.format(self.hrus.CreateHRUs.countHRUs()))
        #if Parameters._ISWIN:
        #    self.checkHashes(HashTable5)
        self.assertTrue(self.dlg.editButton.isEnabled(), 'SWAT Editor button not enabled')
        self.plugin.finish()
        
    def test06(self):
        """MPI 12 processes
            Duffins example (with triple stream reach join)
            channel threshold 100 cells
            stream threshold 300 cells
            landscape option with stream buffering, multiplier 11, slope position 0.15
            slope limits 0.5 and 1
            5 percent channel merge set before readFiles
            dominant landuse, soil, slope."""
        print('\nTest 6')
        demFileName = self.copyDem('duff_dem.tif')
        self.delin._dlg.selectDem.setText(demFileName)
        self.assertTrue(os.path.exists(self.delin._dlg.selectDem.text()), 'Failed to copy DEM to source directory')
        self.hrus = HRUs(self.plugin._gv, self.dlg.reportsBox)
        # listener = Listener(self.delin, self.hrus, self.hrus.CreateHRUs)
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.assertEqual(numLayers, 0, 'Unexpected start with {0} layers'.format(numLayers))
        self.delin._dlg.numProcesses.setValue(12 if Parameters._ISWIN else 4)
        demLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.delin._dlg.selectDem.text(), FileTypes._DEM,
                                                         self.plugin._gv, None, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(demLayer and loaded, 'Failed to load DEM {0}'.format(self.delin._dlg.selectDem.text()))
        self.delin.setDefaultNumCells(demLayer)
        self.assertTrue(demLayer.crs().mapUnits() == QgsUnitTypes.DistanceMeters, 'Map units not meters but {0}'.format(demLayer.crs().mapUnits()))
        unitIndex = self.delin._dlg.areaUnitsBox.findText(Parameters._HECTARES)
        self.assertTrue(unitIndex >= 0, 'Cannot find hectares area units')
        self.delin._dlg.areaUnitsBox.setCurrentIndex(unitIndex)
        self.delin.setDefaultNumCells(demLayer)
        self.delin._dlg.numCellsSt.setText('300')
        self.delin._dlg.numCellsCh.setText('100')
        self.assertTrue(self.delin._dlg.areaSt.text() == '300', 'Unexpected area for streams {0}'.format(self.delin._dlg.areaSt.text()))
        self.assertTrue(self.delin._dlg.areaCh.text() == '100', 'Unexpected area for channels {0}'.format(self.delin._dlg.areaCh.text()))
        QSWATUtils.copyFiles(QFileInfo(os.path.join(self.dataDir, 'duff_out.shp')), self.plugin._gv.shapesDir)
        self.delin._dlg.selectOutlets.setText(os.path.join(self.plugin._gv.shapesDir, 'duff_out.shp'))
        self.assertTrue(os.path.exists(self.delin._dlg.selectOutlets.text()), 'Failed to copy duff_out.shp to Outlet directory')
        self.delin._dlg.useOutlets.setChecked(True)
        QtTest.QTest.mouseClick(self.delin._dlg.delinRunButton2, Qt.LeftButton)
        self.assertTrue(self.delin.areaOfCell > 0, 'Area of cell is ' + str(self.delin.areaOfCell))
        self.assertTrue(self.delin._dlg.selectSubButton.isEnabled(), 'Select subbasins button not enabled')
        demName = os.path.split(os.path.splitext(demFileName)[0])[1]
        subbasinsFileName = os.path.join(self.plugin._gv.shapesDir, demName + 'subbasins.shp')
        self.assertTrue(os.path.exists(subbasinsFileName), 'Failed to make watershed shapefile {0}'.format(subbasinsFileName))
        subbasinsLayer = QSWATUtils.getLayerByFilename(self.root.findLayers(), subbasinsFileName, FileTypes._WATERSHED, None, None, None)[0]
        self.assertTrue(subbasinsLayer, 'Cannot find watershed layer')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        L = Landscape(self.plugin._gv, None, self.delin._dlg.numProcesses.value(), None)
        L.init()
        L._dlg.methodTab.setCurrentIndex(0)
        self.assertTrue(L._dlg.bufferMultiplier.isEnabled(), 'Buffer multipler not enabled')
        L._dlg.bufferMultiplier.setValue(11)
        self.assertTrue(L._dlg.slopePositionSpinBox.isEnabled(), 'Slope position spin box not enabled')
        L._dlg.slopePositionSpinBox.setValue(0.15)
        QtTest.QTest.mouseClick(L._dlg.createButton, Qt.LeftButton)
        QtTest.QTest.mouseClick(L._dlg.doneButton, Qt.LeftButton)
        self.waitLayerAdded(numLayers)
        floodLayer = QSWATUtils.getLayerByLegend(FileTypes.legend(FileTypes._BUFFERFLOOD), self.root.findLayers())
        self.assertIsNotNone(floodLayer, 'Cannot find buffer floodplain layer')
        QtTest.QTest.mouseClick(self.delin._dlg.OKButton, Qt.LeftButton)
        self.assertTrue(self.dlg.hrusButton.isEnabled(), 'HRUs button not enabled')
        self.hrus.init()
        hrudlg = self.hrus._dlg
        self.hrus.landuseFile = os.path.join(self.dataDir, 'duff_landuse.tif')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.hrus.landuseLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.landuseFile, FileTypes._LANDUSES, 
                                                                       self.plugin._gv, None, QSWATUtils._LANDUSE_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.landuseLayer and loaded, 'Failed to load landuse file {0}'.format(self.hrus.landuseFile))
        self.hrus.soilFile = os.path.join(self.dataDir, 'duff_soil.tif')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.hrus.soilLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.soilFile, FileTypes._SOILS, 
                                                                    self.plugin._gv, None, QSWATUtils._SOIL_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.soilLayer and loaded, 'Failed to load soil file {0}'.format(self.hrus.soilFile))
        landCombo = hrudlg.selectLanduseTable
        landIndex = landCombo.findText('global_landuses')
        self.assertTrue(landIndex >= 0, 'Cannot find global landuses table')
        landCombo.setCurrentIndex(landIndex)
        soilCombo = hrudlg.selectSoilTable
        soilIndex = soilCombo.findText('global_soils')
        self.assertTrue(soilIndex >= 0, 'Cannot find global soils table')
        soilCombo.setCurrentIndex(soilIndex)
        usersoilCombo = hrudlg.selectUsersoilTable
        usersoilIndex = usersoilCombo.findText('global_usersoil')
        self.assertTrue(usersoilIndex >= 0, 'Cannot find global usersoil table')
        usersoilCombo.setCurrentIndex(usersoilIndex)
        self.plugin._gv.db.usersoilTable = 'global_usersoil'
        floodCombo = hrudlg.floodplainCombo
        self.assertTrue(floodCombo.count() == 2, 'Not 2 items in floodplaain combo box')
        floodCombo.setCurrentIndex(1)
        lims = self.plugin._gv.db.slopeLimits
        self.assertTrue(len(lims) == 0, 'Failed to start with empty slope limits: limits list is {0!s}'.format(lims))
        hrudlg.slopeBand.setText('1')
        QtTest.QTest.mouseClick(hrudlg.insertButton, Qt.LeftButton)
        lims = self.plugin._gv.db.slopeLimits
        self.assertTrue(len(lims) == 1 and lims[0] == 1, 'Failed to set slope limit of 1: limits list is {0!s}'.format(lims))
        hrudlg.slopeBand.setText('0.5')
        QtTest.QTest.mouseClick(hrudlg.insertButton, Qt.LeftButton)
        lims = self.plugin._gv.db.slopeLimits
        self.assertTrue(len(lims) == 2 and lims[0] == 0.5 and lims[1] == 1, 'Failed to set slope limits of 0.5, 1: limits list is {0!s}'.format(lims))
        self.assertTrue(hrudlg.elevBandsButton.isEnabled(), 'Elevation bands button not enabled')
        hrudlg.channelMergeVal.setText('5')
        self.hrus.readChannelThreshold()
        self.assertTrue(hrudlg.channelMergeSlider.value() == 5, 'Failed to set channel mrege slider to 5: has value {0}'.format(hrudlg.channelMergeSlider.value()))
        QtTest.QTest.mouseClick(hrudlg.readButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._TOPOREPORT)))
        self.assertTrue(self.dlg.reportsBox.isEnabled() and self.dlg.reportsBox.findText(Parameters._TOPOITEM) >= 0, \
                        'Elevation report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._BASINREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._BASINITEM) >= 0, \
                        'Landuse and soil report not accessible from main form')
        self.assertTrue(hrudlg.splitButton.isEnabled(), 'Split landuses button not enabled')
        self.assertTrue(hrudlg.exemptButton.isEnabled(), 'Exempt landuses button not enabled')
        self.assertTrue(hrudlg.dominantLanduseButton.isEnabled(), 'Dominant landuse button not enabled')
        QtTest.QTest.mouseClick(hrudlg.dominantLanduseButton, Qt.LeftButton)
        self.assertFalse(hrudlg.areaPercentChoiceGroup.isEnabled(), 'Area percent choice group enabled')
        self.assertFalse(hrudlg.landuseSoilSlopeGroup.isEnabled(), ' Landuse soil slope group enabled')
        self.assertFalse(hrudlg.areaGroup.isEnabled(), 'Area group enabled')
        self.assertFalse(hrudlg.targetGroup.isEnabled(), 'Target group enabled')
        self.assertTrue(hrudlg.createButton.isEnabled(), 'Create button not enabled')
        QtTest.QTest.mouseClick(hrudlg.createButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._HRUSREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._HRUSITEM) >= 0, \
                        'HRUs report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.shapesDir, 'lsus2.shp')), 'Actual LSUs shapefile not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'rivs.shp')), 'Reaches results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'subs.shp')), 'Watershed results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'lsus.shp')), 'LSUs results template file not created.')
        self.assertEqual(len(self.hrus.CreateHRUs.basins), 41, 'Subbasin count is {0} instead of 41'.format(len(self.hrus.CreateHRUs.basins)))
        self.assertEqual(self.hrus.CreateHRUs.countChannels(), 127, 'Channel count is {0} instead of 127'.format(self.hrus.CreateHRUs.countChannels()))
        self.assertEqual(self.hrus.CreateHRUs.countLsus(), 253, 'LSU count is {0} instead of 253'.format(self.hrus.CreateHRUs.countLsus()))
        self.assertEqual(self.hrus.CreateHRUs.countHRUs(), 253, 'HRU count is {0} instead of 253'.format(self.hrus.CreateHRUs.countHRUs()))
        #if Parameters._ISWIN:
        #    self.checkHashes(HashTable6)
        self.assertTrue(self.dlg.editButton.isEnabled(), 'SWAT Editor button not enabled')
        self.plugin.finish()
        
    def test07(self):
        """MPI with 12 processes; delineation threshod default; 7 inlets/outlets; snap threshold 600; grid size 4; FullHRUs; dominant HRU."""
        print('\nTest 7')
        self.delin._dlg.selectDem.setText(self.copyDem('sj_dem.tif'))
        self.assertTrue(os.path.exists(self.delin._dlg.selectDem.text()), 'Failed to copy DEM to source directory')
        self.hrus = HRUs(self.plugin._gv, self.dlg.reportsBox)
        # listener = Listener(self.delin, self.hrus, self.hrus.CreateHRUs)
        QgsProject.instance().removeAllMapLayers()
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.assertEqual(numLayers, 0, 'Unexpected start with {0} layers'.format(numLayers))
        self.delin._dlg.numProcesses.setValue(12 if Parameters._ISWIN else 4)
        demLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.delin._dlg.selectDem.text(), FileTypes._DEM,
                                                         self.plugin._gv, None, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(demLayer and loaded, 'Failed to load DEM {0}'.format(self.delin._dlg.selectDem.text()))
        self.delin.setDefaultNumCells(demLayer)
        QSWATUtils.copyFiles(QFileInfo(os.path.join(self.dataDir, 'out7.shp')), self.plugin._gv.shapesDir)
        self.delin._dlg.selectOutlets.setText(os.path.join(self.plugin._gv.shapesDir, 'out7.shp'))
        self.assertTrue(os.path.exists(self.delin._dlg.selectOutlets.text()), 'Failed to find outlet file {0}'.format(self.delin._dlg.selectOutlets.text()))
        self.delin._dlg.useOutlets.setChecked(True)
        # QtTest.QTest.mouseClick(self.delin._dlg.delinRunButton2, Qt.LeftButton)
        # self.assertTrue('7 snapped: 1 failed' in self.delin._dlg.snappedLabel.text(), 'Unexpected snapping result: {0}'.format(self.delin._dlg.snappedLabel.text()))
        self.delin._dlg.snapThreshold.setText('600')
        QtTest.QTest.mouseClick(self.delin._dlg.gridBox, Qt.LeftButton)
        self.delin._dlg.gridSize.setValue(4)
        QtTest.QTest.mouseClick(self.delin._dlg.delinRunButton2, Qt.LeftButton)
        self.assertTrue('7 snapped' in self.delin._dlg.snappedLabel.text(), 'Unexpected snapping result: {0}'.format(self.delin._dlg.snappedLabel.text()))
        self.assertTrue(self.delin.areaOfCell > 0, 'Area of cell is ' + str(self.delin.areaOfCell))
        QtTest.QTest.mouseClick(self.delin._dlg.OKButton, Qt.LeftButton)
        self.assertTrue(self.dlg.hrusButton.isEnabled(), 'HRUs button not enabled')
        self.hrus.init()
        hrudlg = self.hrus._dlg
        self.hrus.landuseFile = os.path.join(self.dataDir, 'sj_land.tif')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.hrus.landuseLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.landuseFile, FileTypes._LANDUSES, 
                                                                       self.plugin._gv, None, QSWATUtils._LANDUSE_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.landuseLayer and loaded, 'Failed to load landuse file {0}'.format(self.hrus.landuseFile))
        self.hrus.soilFile = os.path.join(self.dataDir, 'sj_soil.tif')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.hrus.soilLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.soilFile, FileTypes._SOILS, 
                                                                    self.plugin._gv, None, QSWATUtils._SOIL_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.soilLayer and loaded, 'Failed to load soil file {0}'.format(self.hrus.soilFile))
        landCombo = hrudlg.selectLanduseTable
        landIndex = landCombo.findText('global_landuses')
        self.assertTrue(landIndex >= 0, 'Cannot find global landuses table')
        landCombo.setCurrentIndex(landIndex)
        soilCombo = hrudlg.selectSoilTable
        soilIndex = soilCombo.findText('global_soils')
        self.assertTrue(soilIndex >= 0, 'Cannot find global soils table')
        soilCombo.setCurrentIndex(soilIndex)
        usersoilCombo = hrudlg.selectUsersoilTable
        usersoilIndex = usersoilCombo.findText('global_usersoil')
        self.assertTrue(usersoilIndex >= 0, 'Cannot find global usersoil table')
        usersoilCombo.setCurrentIndex(usersoilIndex)
        self.plugin._gv.db.usersoilTable = 'global_usersoil'
        lims = self.plugin._gv.db.slopeLimits
        self.assertTrue(len(lims) == 0, 'Limits list is not empty')
        hrudlg.generateFullHRUs.setChecked(True)
        QtTest.QTest.mouseClick(hrudlg.readButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.shapesDir, 'hrus1.shp')), 'Full HRUs shapefile not created')
        fullHrusLayer = QSWATUtils.getLayerByLegend(QSWATUtils._FULLHRUSLEGEND, self.root.findLayers())
        self.assertTrue(fullHrusLayer, 'FullHRUs file not loaded')
        self.assertTrue(fullHrusLayer.layer().featureCount() == 39429, 'Unexpected number of full HRUs: {0}'.format(fullHrusLayer.layer().featureCount()))
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._TOPOREPORT)))
        self.assertTrue(self.dlg.reportsBox.isEnabled() and self.dlg.reportsBox.findText(Parameters._TOPOITEM) >= 0, \
                        'Elevation report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._BASINREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._BASINITEM) >= 0, \
                        'Landuse and soil report not accessible from main form')
        self.assertTrue(hrudlg.splitButton.isEnabled(), 'Split landuses button not enabled')
        self.assertTrue(hrudlg.exemptButton.isEnabled(), 'Exempt landuses button not enabled')
        self.assertTrue(hrudlg.dominantHRUButton.isEnabled(), 'Dominant HRU button not enabled')
        QtTest.QTest.mouseClick(hrudlg.dominantHRUButton, Qt.LeftButton)
        self.assertFalse(hrudlg.areaPercentChoiceGroup.isEnabled(), 'Area percent choice group enabled')
        self.assertFalse(hrudlg.landuseSoilSlopeGroup.isEnabled(), ' Landuse soil slope group enabled')
        self.assertFalse(hrudlg.areaGroup.isEnabled(), 'Area group enabled')
        self.assertFalse(hrudlg.targetGroup.isEnabled(), 'Target group enabled')
        self.assertTrue(hrudlg.createButton.isEnabled(), 'Create button not enabled')
        QtTest.QTest.mouseClick(hrudlg.createButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._HRUSREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._HRUSITEM) >= 0, \
                        'HRUs report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.shapesDir, 'lsus1.shp')), 'Actual LSUs shapefile not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.shapesDir, 'hrus2.shp')), 'Actual HRUs shapefile not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'hrus.shp')), 'HRUs results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'rivs.shp')), 'Reaches results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'subs.shp')), 'Watershed results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'lsus.shp')), 'LSUs results template file not created.')
        self.assertEqual(len(self.hrus.CreateHRUs.basins), 35161, 'Subbasin count is {0} instead of 35161'.format(len(self.hrus.CreateHRUs.basins)))
        self.assertEqual(self.hrus.CreateHRUs.countChannels(), 35161, 'Channel count is {0} instead of 35161'.format(self.hrus.CreateHRUs.countChannels()))
        self.assertEqual(self.hrus.CreateHRUs.countLsus(), 35161, 'LSU count is {0} instead of 35161'.format(self.hrus.CreateHRUs.countLsus()))
        self.assertEqual(self.hrus.CreateHRUs.countHRUs(), 35161, 'HRU count is {0} instead of 35161'.format(self.hrus.CreateHRUs.countHRUs()))
        #if Parameters._ISWIN:
        #    self.checkHashes(HashTable7)
        self.assertTrue(self.dlg.editButton.isEnabled(), 'SWAT Editor button not enabled')
        self.plugin.finish()
        
    def test08(self):
        """No MPI; use existing; use grid; stream drainage; reuse; no outlet; no merging/adding in delineation; filter by percent area 25."""
        print('\nTest 8')
        self.delin._dlg.selectDem.setText(self.copyDem('sj_dem.tif'))
        self.assertTrue(os.path.exists(self.delin._dlg.selectDem.text()), 'Failed to copy DEM to source directory')
        self.hrus = HRUs(self.plugin._gv, self.dlg.reportsBox)
        # listener = Listener(self.delin, self.hrus, self.hrus.CreateHRUs)
        QgsProject.instance().removeAllMapLayers()
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.assertEqual(numLayers, 0, 'Not all map layers removed')
        demLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.delin._dlg.selectDem.text(), FileTypes._DEM,
                                                         self.plugin._gv, None, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(demLayer and loaded, 'Failed to load DEM {0}'.format(self.delin._dlg.selectDem.text()))
        self.delin.setDefaultNumCells(demLayer)
        self.assertTrue(demLayer.crs().mapUnits() == QgsUnitTypes.DistanceMeters, 'Map units not meters but {0}'.format(demLayer.crs().mapUnits()))
        self.delin._dlg.tabWidget.setCurrentIndex(1)
        subbasinsFile = os.path.join(self.dataDir, 'grid.shp')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        subbasinsLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), subbasinsFile, FileTypes._EXISTINGWATERSHED, 
                                                               self.plugin._gv, None, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(subbasinsLayer and loaded, 'Failed to load grid shapefile {0}'.format(subbasinsFile))
        self.delin._dlg.selectSubbasins.setText(subbasinsFile)
        self.plugin._gv.subbasinsFile = subbasinsFile
        channelFile = os.path.join(self.dataDir, 'gridchannels.shp')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        channelLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), channelFile, FileTypes._GRIDSTREAMS, 
                                                             self.plugin._gv, None, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(channelLayer and loaded, 'Failed to load channels shapefile {0}'.format(channelFile))
        self.delin._dlg.selectStreams.setText(channelFile)
        self.plugin._gv.streamFile = channelFile
        self.delin._dlg.numProcesses.setValue(0)
        self.assertTrue(self.delin._dlg.useGrid.isEnabled(), 'Use grid not enabled')
        self.assertFalse(self.delin._dlg.useGrid.isChecked(), 'Use grid already checked')
        QtTest.QTest.mouseClick(self.delin._dlg.useGrid, Qt.LeftButton)
        # this fails: self.assertTrue(self.delin._dlg.useGrid.isChecked(), 'Use grid not checked')
        # so
        self.delin._dlg.useGrid.setChecked(True)
        self.delin.changeUseGrid()
        self.assertTrue(self.plugin._gv.useGridModel, 'Not set to use grid')
        self.assertTrue(self.delin._dlg.drainGridButton.isEnabled(), 'Watershed drainage option not enabled')
        self.assertTrue(self.delin._dlg.drainStreamsButton.isEnabled(), 'Streams drainage option not enabled')
        self.assertTrue(self.delin._dlg.drainTableButton.isEnabled(), 'Table drainage option not enabled')
        QtTest.QTest.mouseClick(self.delin._dlg.drainStreamsButton, Qt.LeftButton)
        self.assertTrue(self.delin._dlg.reuseButton.isEnabled(), 'Reuse button not enabled')
        QtTest.QTest.mouseClick(self.delin._dlg.reuseButton, Qt.LeftButton)
        QtTest.QTest.mouseClick(self.delin._dlg.existRunButton, Qt.LeftButton)
        self.assertTrue(self.delin.isDelineated, 'Delineation incomplete')
        QtTest.QTest.mouseClick(self.delin._dlg.OKButton, Qt.LeftButton)
        self.assertTrue(self.dlg.hrusButton.isEnabled(), 'HRUs button not enabled')
        self.hrus.init()
        hrudlg = self.hrus._dlg
        self.hrus.landuseFile = os.path.join(self.dataDir, 'sj_land.tif')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.hrus.landuseLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.landuseFile, FileTypes._LANDUSES, 
                                                                       self.plugin._gv, None, QSWATUtils._LANDUSE_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.landuseLayer and loaded, 'Failed to load landuse file {0}'.format(self.hrus.landuseFile))
        self.hrus.soilFile = os.path.join(self.dataDir, 'sj_soil.tif')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.hrus.soilLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.soilFile, FileTypes._SOILS, 
                                                                    self.plugin._gv, None, QSWATUtils._SOIL_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.soilLayer and loaded, 'Failed to load soil file {0}'.format(self.hrus.soilFile))
        landCombo = hrudlg.selectLanduseTable
        landIndex = landCombo.findText('global_landuses')
        self.assertTrue(landIndex >= 0, 'Cannot find global landuses table')
        landCombo.setCurrentIndex(landIndex)
        soilCombo = hrudlg.selectSoilTable
        soilIndex = soilCombo.findText('global_soils')
        self.assertTrue(soilIndex >= 0, 'Cannot find global soils table')
        soilCombo.setCurrentIndex(soilIndex)
        usersoilCombo = hrudlg.selectUsersoilTable
        usersoilIndex = usersoilCombo.findText('global_usersoil')
        self.assertTrue(usersoilIndex >= 0, 'Cannot find global usersoil table')
        usersoilCombo.setCurrentIndex(usersoilIndex)
        self.plugin._gv.db.usersoilTable = 'global_usersoil'
        self.assertTrue(hrudlg.elevBandsButton.isEnabled(), 'Elevation bands button not enabled')
        QtTest.QTest.mouseClick(hrudlg.readButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._TOPOREPORT)))
        self.assertTrue(self.dlg.reportsBox.isEnabled() and self.dlg.reportsBox.findText(Parameters._TOPOITEM) >= 0, \
                        'Elevation report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._BASINREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._BASINITEM) >= 0, \
                        'Landuse and soil report not accessible from main form')
        self.assertTrue(hrudlg.splitButton.isEnabled(), 'Split landuses button not enabled')
        self.assertTrue(hrudlg.exemptButton.isEnabled(), 'Exempt landuses button not enabled')
        self.assertTrue(hrudlg.filterAreaButton.isEnabled(), 'Filter by area button not enabled')
        QtTest.QTest.mouseClick(hrudlg.filterAreaButton, Qt.LeftButton)
        self.assertTrue(hrudlg.percentButton.isEnabled(), 'Percent button not enabled')
        QtTest.QTest.mouseClick(hrudlg.percentButton, Qt.LeftButton)
        self.assertTrue(hrudlg.stackedWidget.currentIndex() == 1, 'Wrong threshold page {0} selected'.format(hrudlg.stackedWidget.currentIndex()))
        hrudlg.areaSlider.setValue(25)
        self.assertTrue(hrudlg.createButton.isEnabled(), 'Create button not enabled')
        QtTest.QTest.mouseClick(hrudlg.createButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._HRUSREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._HRUSITEM) >= 0, \
                        'HRUs report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.shapesDir, 'lsus1.shp')), 'Actual LSUs shapefile not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'rivs.shp')), 'Reaches results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'subs.shp')), 'Watershed results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'lsus.shp')), 'LSUs results template file not created.')
        self.assertEqual(len(self.hrus.CreateHRUs.basins), 35161, 'Subbasin count is {0} instead of 35161'.format(len(self.hrus.CreateHRUs.basins)))
        self.assertEqual(self.hrus.CreateHRUs.countChannels(), 35161, 'Channel count is {0} instead of 35161'.format(self.hrus.CreateHRUs.countChannels()))
        self.assertEqual(self.hrus.CreateHRUs.countLsus(), 35161, 'LSU count is {0} instead of 35161'.format(self.hrus.CreateHRUs.countLsus()))
        self.assertEqual(self.hrus.CreateHRUs.countHRUs(), 36672, 'HRU count is {0} instead of 36672'.format(self.hrus.CreateHRUs.countHRUs()))
        #if Parameters._ISWIN:
        #    self.checkHashes(HashTable8)
        self.assertTrue(self.dlg.editButton.isEnabled(), 'SWAT Editor button not enabled')
        self.plugin.finish()
        
    def test09(self):
        """No MPI; use existing; use grid; grid drainage; recalculate; 7 outlets; no merging/adding in delineation; filter by percent area 25."""
        print('\nTest 9')
        self.delin._dlg.selectDem.setText(self.copyDem('sj_dem.tif'))
        self.assertTrue(os.path.exists(self.delin._dlg.selectDem.text()), 'Failed to copy DEM to source directory')
        self.hrus = HRUs(self.plugin._gv, self.dlg.reportsBox)
        # listener = Listener(self.delin, self.hrus, self.hrus.CreateHRUs)
        QgsProject.instance().removeAllMapLayers()
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.assertEqual(numLayers, 0, 'Not all map layers removed')
        demLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.delin._dlg.selectDem.text(), FileTypes._DEM,
                                                         self.plugin._gv, None, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(demLayer and loaded, 'Failed to load DEM {0}'.format(self.delin._dlg.selectDem.text()))
        self.delin.setDefaultNumCells(demLayer)
        self.assertTrue(demLayer.crs().mapUnits() == QgsUnitTypes.DistanceMeters, 'Map units not meters but {0}'.format(demLayer.crs().mapUnits()))
        self.delin._dlg.tabWidget.setCurrentIndex(1)
        subbasinsFile = os.path.join(self.dataDir, 'grid.shp')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        subbasinsLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), subbasinsFile, FileTypes._EXISTINGWATERSHED, 
                                                               self.plugin._gv, demLayer, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(subbasinsLayer and loaded, 'Failed to load grid shapefile'.format(subbasinsFile))
        self.delin._dlg.selectSubbasins.setText(subbasinsFile)
        self.plugin._gv.subbasinsFile = subbasinsFile
        QSWATUtils.copyFiles(QFileInfo(os.path.join(self.dataDir, 'out7.shp')), self.plugin._gv.shapesDir)
        self.delin._dlg.selectExistOutlets.setText(os.path.join(self.plugin._gv.shapesDir, 'out7.shp'))
        self.assertTrue(os.path.exists(self.delin._dlg.selectExistOutlets.text()), 'Failed to find outlet file {0}'.format(self.delin._dlg.selectOutlets.text()))
        self.delin._dlg.numProcesses.setValue(0)
        self.assertTrue(self.delin._dlg.useGrid.isEnabled(), 'Use grid not enabled')
        self.assertFalse(self.delin._dlg.useGrid.isChecked(), 'Use grid already checked')
        QtTest.QTest.mouseClick(self.delin._dlg.useGrid, Qt.LeftButton)
        # this fails: self.assertTrue(self.delin._dlg.useGrid.isChecked(), 'Use grid not checked')
        # so
        self.delin._dlg.useGrid.setChecked(True)
        self.delin.changeUseGrid()
        self.assertTrue(self.plugin._gv.useGridModel, 'Not set to use grid')
        self.assertTrue(self.delin._dlg.drainGridButton.isEnabled(), 'Watershed drainage option not enabled')
        self.assertTrue(self.delin._dlg.drainStreamsButton.isEnabled(), 'Streams drainage option not enabled')
        self.assertTrue(self.delin._dlg.drainTableButton.isEnabled(), 'Table drainage option not enabled')
        QtTest.QTest.mouseClick(self.delin._dlg.drainGridButton, Qt.LeftButton)
        self.assertTrue(self.delin._dlg.recalcButton.isEnabled(), 'Recalculate button not enabled')
        QtTest.QTest.mouseClick(self.delin._dlg.recalcButton, Qt.LeftButton)
        QtTest.QTest.mouseClick(self.delin._dlg.existRunButton, Qt.LeftButton)
        self.assertTrue(self.delin.isDelineated, 'Delineation incomplete')
        QtTest.QTest.mouseClick(self.delin._dlg.OKButton, Qt.LeftButton)
        self.assertTrue(self.dlg.hrusButton.isEnabled(), 'HRUs button not enabled')
        self.hrus.init()
        hrudlg = self.hrus._dlg
        self.hrus.landuseFile = os.path.join(self.dataDir, 'sj_land.tif')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.hrus.landuseLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.landuseFile, FileTypes._LANDUSES, 
                                                                       self.plugin._gv, None, QSWATUtils._LANDUSE_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.landuseLayer and loaded, 'Failed to load landuse file {0}'.format(self.hrus.landuseFile))
        self.hrus.soilFile = os.path.join(self.dataDir, 'sj_soil.tif')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.hrus.soilLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.soilFile, FileTypes._SOILS, 
                                                                    self.plugin._gv, None, QSWATUtils._SOIL_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.soilLayer and loaded, 'Failed to load soil file {0}'.format(self.hrus.soilFile))
        landCombo = hrudlg.selectLanduseTable
        landIndex = landCombo.findText('global_landuses')
        self.assertTrue(landIndex >= 0, 'Cannot find global landuses table')
        landCombo.setCurrentIndex(landIndex)
        soilCombo = hrudlg.selectSoilTable
        soilIndex = soilCombo.findText('global_soils')
        self.assertTrue(soilIndex >= 0, 'Cannot find global soils table')
        soilCombo.setCurrentIndex(soilIndex)
        usersoilCombo = hrudlg.selectUsersoilTable
        usersoilIndex = usersoilCombo.findText('global_usersoil')
        self.assertTrue(usersoilIndex >= 0, 'Cannot find global usersoil table')
        usersoilCombo.setCurrentIndex(usersoilIndex)
        self.plugin._gv.db.usersoilTable = 'global_usersoil'
        self.assertTrue(hrudlg.elevBandsButton.isEnabled(), 'Elevation bands button not enabled')
        QtTest.QTest.mouseClick(hrudlg.readButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._TOPOREPORT)))
        self.assertTrue(self.dlg.reportsBox.isEnabled() and self.dlg.reportsBox.findText(Parameters._TOPOITEM) >= 0, \
                        'Elevation report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._BASINREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._BASINITEM) >= 0, \
                        'Landuse and soil report not accessible from main form')
        self.assertTrue(hrudlg.splitButton.isEnabled(), 'Split landuses button not enabled')
        self.assertTrue(hrudlg.exemptButton.isEnabled(), 'Exempt landuses button not enabled')
        self.assertTrue(hrudlg.filterAreaButton.isEnabled(), 'Filter by area button not enabled')
        QtTest.QTest.mouseClick(hrudlg.filterAreaButton, Qt.LeftButton)
        self.assertTrue(hrudlg.percentButton.isEnabled(), 'Percent button not enabled')
        QtTest.QTest.mouseClick(hrudlg.percentButton, Qt.LeftButton)
        self.assertTrue(hrudlg.stackedWidget.currentIndex() == 1, 'Wrong threshold page {0} selected'.format(hrudlg.stackedWidget.currentIndex()))
        hrudlg.areaSlider.setValue(25)
        self.assertTrue(hrudlg.createButton.isEnabled(), 'Create button not enabled')
        QtTest.QTest.mouseClick(hrudlg.createButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._HRUSREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._HRUSITEM) >= 0, \
                        'HRUs report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.shapesDir, 'lsus1.shp')), 'Actual LSUs shapefile not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'rivs.shp')), 'Reaches results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'subs.shp')), 'Watershed results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'lsus.shp')), 'LSUs results template file not created.')
        self.assertEqual(len(self.hrus.CreateHRUs.basins), 35161, 'Subbasin count is {0} instead of 35161'.format(len(self.hrus.CreateHRUs.basins)))
        self.assertEqual(self.hrus.CreateHRUs.countChannels(), 35161, 'Channel count is {0} instead of 35161'.format(self.hrus.CreateHRUs.countChannels()))
        self.assertEqual(self.hrus.CreateHRUs.countLsus(), 35161, 'LSU count is {0} instead of 35161'.format(self.hrus.CreateHRUs.countLsus()))
        self.assertEqual(self.hrus.CreateHRUs.countHRUs(), 36672, 'HRU count is {0} instead of 36672'.format(self.hrus.CreateHRUs.countHRUs()))
        #if Parameters._ISWIN:
        #    self.checkHashes(HashTable9)
        self.assertTrue(self.dlg.editButton.isEnabled(), 'SWAT Editor button not enabled')
        self.plugin.finish()
        
    def test10(self):
        """No MPI; use existing grid; 7 outlets; no merging/adding in delineation; drainage by table; reuse; slope limit 1; filter by landuse soil slope 2/2/2 ha"""
        print('\nTest 10')
        self.delin._dlg.selectDem.setText(self.copyDem('sj_dem.tif'))
        self.assertTrue(os.path.exists(self.delin._dlg.selectDem.text()), 'Failed to copy DEM to source directory')
        self.hrus = HRUs(self.plugin._gv, self.dlg.reportsBox)
        # listener = Listener(self.delin, self.hrus, self.hrus.CreateHRUs)
        QgsProject.instance().removeAllMapLayers()
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.assertEqual(numLayers, 0, 'Not all map layers removed')
        demLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.delin._dlg.selectDem.text(), FileTypes._DEM,
                                                         self.plugin._gv, None, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(demLayer and loaded, 'Failed to load DEM {0}'.format(self.delin._dlg.selectDem.text()))
        self.delin.setDefaultNumCells(demLayer)
        self.assertTrue(demLayer.crs().mapUnits() == QgsUnitTypes.DistanceMeters, 'Map units not meters but {0}'.format(demLayer.crs().mapUnits()))
        self.delin._dlg.tabWidget.setCurrentIndex(1)
        subbasinsFile = os.path.join(self.dataDir, 'grid.shp')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        subbasinsLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), subbasinsFile, FileTypes._EXISTINGWATERSHED, 
                                                               self.plugin._gv, demLayer, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(subbasinsLayer and loaded, 'Failed to load grid shapefile'.format(subbasinsFile))
        self.delin._dlg.selectSubbasins.setText(subbasinsFile)
        self.plugin._gv.subbasinsFile = subbasinsFile
        QSWATUtils.copyFiles(QFileInfo(os.path.join(self.dataDir, 'out7.shp')), self.plugin._gv.shapesDir)
        self.delin._dlg.selectExistOutlets.setText(os.path.join(self.plugin._gv.shapesDir, 'out7.shp'))
        self.assertTrue(os.path.exists(self.delin._dlg.selectExistOutlets.text()), 'Failed to find outlet file {0}'.format(self.delin._dlg.selectOutlets.text()))
        self.delin._dlg.numProcesses.setValue(0)
        self.assertTrue(self.delin._dlg.useGrid.isEnabled(), 'Use grid not enabled')
        self.assertFalse(self.delin._dlg.useGrid.isChecked(), 'Use grid already checked')
        QtTest.QTest.mouseClick(self.delin._dlg.useGrid, Qt.LeftButton)
        # this fails: self.assertTrue(self.delin._dlg.useGrid.isChecked(), 'Use grid not checked')
        # so
        self.delin._dlg.useGrid.setChecked(True)
        self.delin.changeUseGrid()
        self.assertTrue(self.plugin._gv.useGridModel, 'Not set to use grid')
        self.assertTrue(self.delin._dlg.drainGridButton.isEnabled(), 'Watershed drainage option not enabled')
        self.assertTrue(self.delin._dlg.drainStreamsButton.isEnabled(), 'Streams drainage option not enabled')
        self.assertTrue(self.delin._dlg.drainTableButton.isEnabled(), 'Table drainage option not enabled')
        QtTest.QTest.mouseClick(self.delin._dlg.drainTableButton, Qt.LeftButton)
        self.delin._dlg.selectStreams.setText(os.path.join(self.dataDir, 'testdrainage.csv'))
        self.assertTrue(self.delin._dlg.reuseButton.isEnabled(), 'Recalculate button not enabled')
        QtTest.QTest.mouseClick(self.delin._dlg.reuseButton, Qt.LeftButton)
        QtTest.QTest.mouseClick(self.delin._dlg.existRunButton, Qt.LeftButton)
        self.assertTrue(self.delin.isDelineated, 'Delineation incomplete')
        QtTest.QTest.mouseClick(self.delin._dlg.OKButton, Qt.LeftButton)
        self.assertTrue(self.dlg.hrusButton.isEnabled(), 'HRUs button not enabled')
        self.hrus.init()
        hrudlg = self.hrus._dlg
        self.hrus.landuseFile = os.path.join(self.dataDir, 'sj_land.tif')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.hrus.landuseLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.landuseFile, FileTypes._LANDUSES, 
                                                                       self.plugin._gv, None, QSWATUtils._LANDUSE_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.landuseLayer and loaded, 'Failed to load landuse file {0}'.format(self.hrus.landuseFile))
        self.hrus.soilFile = os.path.join(self.dataDir, 'sj_soil.tif')
        numLayers = len(list(QgsProject.instance().mapLayers().values()))
        self.hrus.soilLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.soilFile, FileTypes._SOILS, 
                                                                    self.plugin._gv, None, QSWATUtils._SOIL_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.soilLayer and loaded, 'Failed to load soil file {0}'.format(self.hrus.soilFile))
        landCombo = hrudlg.selectLanduseTable
        landIndex = landCombo.findText('global_landuses')
        self.assertTrue(landIndex >= 0, 'Cannot find global landuses table')
        landCombo.setCurrentIndex(landIndex)
        soilCombo = hrudlg.selectSoilTable
        soilIndex = soilCombo.findText('global_soils')
        self.assertTrue(soilIndex >= 0, 'Cannot find global soils table')
        soilCombo.setCurrentIndex(soilIndex)
        usersoilCombo = hrudlg.selectUsersoilTable
        usersoilIndex = usersoilCombo.findText('global_usersoil')
        self.assertTrue(usersoilIndex >= 0, 'Cannot find global usersoil table')
        usersoilCombo.setCurrentIndex(usersoilIndex)
        self.plugin._gv.db.usersoilTable = 'global_usersoil'
        lims = self.plugin._gv.db.slopeLimits
        self.assertTrue(len(lims) == 0, 'Failed to start with empty slope limits: limits list is {0!s}'.format(lims))
        hrudlg.slopeBand.setText('1')
        QtTest.QTest.mouseClick(hrudlg.insertButton, Qt.LeftButton)
        lims = self.plugin._gv.db.slopeLimits
        self.assertTrue(len(lims) == 1 and lims[0] == 1, 'Failed to set slope limit of 1: limits list is {0!s}'.format(lims))
        self.assertTrue(hrudlg.elevBandsButton.isEnabled(), 'Elevation bands button not enabled')
        QtTest.QTest.mouseClick(hrudlg.readButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._TOPOREPORT)))
        self.assertTrue(self.dlg.reportsBox.isEnabled() and self.dlg.reportsBox.findText(Parameters._TOPOITEM) >= 0, \
                        'Elevation report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._BASINREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._BASINITEM) >= 0, \
                        'Landuse and soil report not accessible from main form')
        self.assertTrue(hrudlg.splitButton.isEnabled(), 'Split landuses button not enabled')
        self.assertTrue(hrudlg.exemptButton.isEnabled(), 'Exempt landuses button not enabled')
        self.assertTrue(hrudlg.filterLanduseButton.isEnabled(), 'Filter by landuse soil and slope button not enabled')
        QtTest.QTest.mouseClick(hrudlg.filterLanduseButton, Qt.LeftButton)
        self.assertTrue(hrudlg.areaButton.isEnabled(), 'Area button not enabled')
        QtTest.QTest.mouseClick(hrudlg.areaButton, Qt.LeftButton)
        self.assertTrue(hrudlg.stackedWidget.currentIndex() == 0, 'Wrong threshold page {0} selected'.format(hrudlg.stackedWidget.currentIndex()))
        self.assertTrue(hrudlg.landuseSlider.isEnabled(), 'Landuse slider not enabled')
        hrudlg.landuseSlider.setValue(2)
        self.assertTrue(hrudlg.landuseButton.isEnabled(), 'Landuse button not enabled')
        QtTest.QTest.mouseClick(hrudlg.landuseButton, Qt.LeftButton)
        self.assertTrue(hrudlg.soilSlider.isEnabled(), 'Soil slider not enabled')
        hrudlg.soilSlider.setValue(2)
        self.assertTrue(hrudlg.soilButton.isEnabled(), 'Soil button not enabled')
        QtTest.QTest.mouseClick(hrudlg.soilButton, Qt.LeftButton)
        self.assertTrue(hrudlg.slopeSlider.isEnabled(), 'Slope slider not enabled')
        hrudlg.slopeSlider.setValue(2)
        self.assertTrue(hrudlg.createButton.isEnabled(), 'Create button not enabled')
        QtTest.QTest.mouseClick(hrudlg.createButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._HRUSREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._HRUSITEM) >= 0, \
                        'HRUs report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.shapesDir, 'lsus1.shp')), 'Actual LSUs shapefile not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'rivs.shp')), 'Reaches results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'subs.shp')), 'Watershed results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'lsus.shp')), 'LSUs results template file not created.')
        self.assertEqual(len(self.hrus.CreateHRUs.basins), 35161, 'Subbasin count is {0} instead of 35161'.format(len(self.hrus.CreateHRUs.basins)))
        self.assertEqual(self.hrus.CreateHRUs.countChannels(), 35161, 'Channel count is {0} instead of 35161'.format(self.hrus.CreateHRUs.countChannels()))
        self.assertEqual(self.hrus.CreateHRUs.countLsus(), 35161, 'LSU count is {0} instead of 35161'.format(self.hrus.CreateHRUs.countLsus()))
        self.assertEqual(self.hrus.CreateHRUs.countHRUs(), 45569, 'HRU count is {0} instead of 47104'.format(self.hrus.CreateHRUs.countHRUs()))
        #if Parameters._ISWIN:
        #    self.checkHashes(HashTable10)
        self.assertTrue(self.dlg.editButton.isEnabled(), 'SWAT Editor button not enabled')
        self.plugin.finish()
        
    def test11(self):
        """MPI with 6 processes; stream threshold 5 sq km; channel threshold 0.5 sq km;
        1 outlet; lake;  1% channel merge; target 500 HRUs."""
        print('\nTest 11')
        self.delin._dlg.selectDem.setText(self.copyDem('ravn_dem.tif'))
        self.assertTrue(os.path.exists(self.delin._dlg.selectDem.text()), 'Failed to copy DEM to source directory')
        self.hrus = HRUs(self.plugin._gv, self.dlg.reportsBox)
        # listener = Listener(self.delin, self.hrus, self.hrus.CreateHRUs)
        QgsProject.instance().removeAllMapLayers()
        numLayers = len(QgsProject.instance().mapLayers().values())
        self.assertEqual(numLayers, 0, 'Unexpected start with {0} layers'.format(numLayers))
        self.delin._dlg.numProcesses.setValue(6 if Parameters._ISWIN else 4)
        demLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.delin._dlg.selectDem.text(), FileTypes._DEM, self.plugin._gv, None, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(demLayer and loaded, 'Failed to load DEM {0}'.format(self.delin._dlg.selectDem.text()))
        self.delin.setDefaultNumCells(demLayer)
        self.assertTrue(demLayer.crs().mapUnits() == QgsUnitTypes.DistanceMeters, 'Map units not meters but {0}'.format(demLayer.crs().mapUnits()))
        unitIndex = self.delin._dlg.areaUnitsBox.findText(Parameters._SQKM)
        self.assertTrue(unitIndex >= 0, 'Cannot find sq km area units')
        self.delin._dlg.areaUnitsBox.setCurrentIndex(unitIndex)
        self.delin.setDefaultNumCells(demLayer)
        self.delin._dlg.areaSt.setText('5')
        self.delin._dlg.areaCh.setText('0.5')
        self.assertTrue(self.delin._dlg.numCellsSt.text() == '5555', 
                        'Unexpected number of stream cells for delineation {0}'.format(self.delin._dlg.numCellsSt.text()))
        self.assertTrue(self.delin._dlg.numCellsCh.text() == '555', 
                        'Unexpected number of channel cells for delineation {0}'.format(self.delin._dlg.numCellsCh.text()))
        QSWATUtils.copyFiles(QFileInfo(os.path.join(self.dataDir, 'ravn_outlet.shp')), self.plugin._gv.shapesDir)
        self.delin._dlg.selectOutlets.setText(os.path.join(self.plugin._gv.shapesDir, 'ravn_outlet.shp'))
        self.assertTrue(os.path.exists(self.delin._dlg.selectOutlets.text()), 'Failed to find outlet file {0}'.format(self.delin._dlg.selectOutlets.text()))
        self.delin._dlg.useOutlets.setChecked(True)
        QtTest.QTest.mouseClick(self.delin._dlg.delinRunButton2, Qt.LeftButton)
        self.assertTrue('1 snapped' in self.delin._dlg.snappedLabel.text(), 'Unexpected snapping result: {0}'.format(self.delin._dlg.snappedLabel.text()))
        self.assertTrue(self.delin.areaOfCell > 0, 'Area of cell is ' + str(self.delin.areaOfCell))
        QSWATUtils.copyFiles(QFileInfo(os.path.join(self.dataDir, 'Ravn.shp')), self.plugin._gv.shapesDir)
        self.delin._dlg.selectLakes.setText(os.path.join(self.plugin._gv.shapesDir, 'Ravn.shp'))
        lakesLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.delin._dlg.selectLakes.text(), FileTypes._LAKES, self.plugin._gv, demLayer, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(lakesLayer and loaded, 'Failed to load lakes shapefile {0}'.format(self.delin._dlg.selectLakes.text()))
        self.plugin._gv.lakeFile = self.delin._dlg.selectLakes.text()
        self.lakesDone = False
        self.lakePointsAdded = False
        QtTest.QTest.mouseClick(self.delin._dlg.OKButton, Qt.LeftButton)
        self.assertTrue(self.dlg.hrusButton.isEnabled(), 'HRUs button not enabled')
        self.hrus.init()
        hrudlg = self.hrus._dlg
        self.hrus.landuseFile = os.path.join(self.dataDir, 'ravn_landuse.tif')
        numLayers = len(QgsProject.instance().mapLayers().values())
        self.hrus.landuseLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.landuseFile, FileTypes._LANDUSES, self.plugin._gv, None, QSWATUtils._LANDUSE_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.landuseLayer and loaded, 'Failed to load landuse file {0}'.format(self.hrus.landuseFile))
        self.hrus.soilFile = os.path.join(self.dataDir, 'ravn_soil.tif')
        numLayers = len(QgsProject.instance().mapLayers().values())
        self.hrus.soilLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.soilFile, FileTypes._SOILS, self.plugin._gv, None, QSWATUtils._SOIL_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.soilLayer and loaded, 'Failed to load soil file {0}'.format(self.hrus.soilFile))
        landuse_lookup = os.path.join(self.dataDir, 'ravn_landuse.csv')
        landuse_table = self.hrus._db.readCsvFile(landuse_lookup, 'landuse', self.hrus._db.landuseTableNames)
        landCombo = hrudlg.selectLanduseTable
        landCombo.insertItem(0, landuse_table)
        landIndex = landCombo.findText(landuse_table)
        self.assertTrue(landIndex >= 0, 'Cannot find landuse table {0}'.format(landuse_table))
        landCombo.setCurrentIndex(landIndex)
        soil_lookup = os.path.join(self.dataDir, 'ravn_soil.csv')
        soil_table = self.hrus._db.readCsvFile(soil_lookup, 'soil', self.hrus._db.soilTableNames)
        soilCombo = hrudlg.selectSoilTable
        soilCombo.insertItem(0, soil_table)
        soilIndex = soilCombo.findText(soil_table)
        self.assertTrue(soilIndex >= 0, 'Cannot find soil table {0}'.format(soil_table))
        soilCombo.setCurrentIndex(soilIndex)
        usersoil_lookup = os.path.join(self.dataDir, 'ravn_usersoil.csv')
        usersoil_table = self.hrus._db.readCsvFile(usersoil_lookup, 'usersoil', self.hrus._db.usersoilTableNames)
        usersoilCombo = hrudlg.selectUsersoilTable
        usersoilCombo.insertItem(0, usersoil_table)
        usersoilIndex = usersoilCombo.findText(usersoil_table)
        self.assertTrue(usersoilIndex >= 0, 'Cannot find usersoil table {0}'.format(usersoil_table))
        usersoilCombo.setCurrentIndex(usersoilIndex)
        self.plugin._gv.db.usersoilTable = usersoil_table
        lims = self.plugin._gv.db.slopeLimits
        self.assertTrue(len(lims) == 0, 'Limits list is not empty')
        self.assertTrue(hrudlg.elevBandsButton.isEnabled(), 'Elevation bands button not enabled')
        hrudlg.channelMergeVal.setText('1')
        QtTest.QTest.mouseClick(hrudlg.readButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._TOPOREPORT)))
        self.assertTrue(self.dlg.reportsBox.isEnabled() and self.dlg.reportsBox.findText(Parameters._TOPOITEM) >= 0, \
                        'Elevation report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._BASINREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._BASINITEM) >= 0, \
                        'Landuse and soil report not accessible from main form')
        self.assertTrue(hrudlg.splitButton.isEnabled(), 'Split landuses button not enabled')
        self.assertTrue(hrudlg.exemptButton.isEnabled(), 'Exempt landuses button not enabled')
        self.assertTrue(hrudlg.targetButton.isEnabled(), 'Target button not enabled')
        QtTest.QTest.mouseClick(hrudlg.targetButton, Qt.LeftButton)
        self.assertTrue(hrudlg.stackedWidget.currentIndex() == 2, 'Wrong threshold page {0} selected'.format(hrudlg.stackedWidget.currentIndex()))
        hrudlg.targetVal.setText('500')
        self.assertTrue(hrudlg.createButton.isEnabled(), 'Create button not enabled')
        QtTest.QTest.mouseClick(hrudlg.createButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._HRUSREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._HRUSITEM) >= 0, \
                        'HRUs report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.shapesDir, 'lsus2.shp')), 'Actual LSUs shapefile not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'rivs.shp')), 'Reaches results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'subs.shp')), 'Watershed results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'lsus.shp')), 'LSUs results template file not created.')
        self.assertEqual(len(self.hrus.CreateHRUs.basins), 5, 'Subbasin count is {0} instead of 5'.format(len(self.hrus.CreateHRUs.basins)))
        self.assertEqual(self.hrus.CreateHRUs.countChannels(), 75, 'Channel count is {0} instead of 75'.format(self.hrus.CreateHRUs.countChannels()))
        self.assertEqual(self.hrus.CreateHRUs.countLsus(), 75, 'LSU count is {0} instead of 75'.format(self.hrus.CreateHRUs.countLsus()))
        self.assertEqual(self.hrus.CreateHRUs.countHRUs(), 500, 'HRU count is {0} instead of 500'.format(self.hrus.CreateHRUs.countHRUs()))
        #if Parameters._ISWIN:
        #    self.checkHashes(HashTable11)
        self.assertTrue(self.dlg.editButton.isEnabled(), 'SWAT Editor button not enabled')
        self.plugin.finish()
        
    def test12(self):
        """MPI with 6 processes; existing;
        lake;  1% channel merge; target 500 HRUs."""
        print('\nTest 12')
        self.delin._dlg.selectDem.setText(self.copyDem('ravn_dem.tif'))
        self.assertTrue(os.path.exists(self.delin._dlg.selectDem.text()), 'Failed to copy DEM to source directory')
        self.hrus = HRUs(self.plugin._gv, self.dlg.reportsBox)
        # listener = Listener(self.delin, self.hrus, self.hrus.CreateHRUs)
        QgsProject.instance().removeAllMapLayers()
        numLayers = len(QgsProject.instance().mapLayers().values())
        self.assertEqual(numLayers, 0, 'Unexpected start with {0} layers'.format(numLayers))
        demLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.delin._dlg.selectDem.text(), FileTypes._DEM, self.plugin._gv, None, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(demLayer and loaded, 'Failed to load DEM {0}'.format(self.delin._dlg.selectDem.text()))
        self.delin.setDefaultNumCells(demLayer)
        self.delin._dlg.tabWidget.setCurrentIndex(1)
        QSWATUtils.copyFiles(QFileInfo(os.path.join(self.dataDir, 'ravn_demsubbasins.shp')), self.plugin._gv.shapesDir)
        subbasinsFile = os.path.join(self.plugin._gv.shapesDir, 'ravn_demsubbasins.shp')
        numLayers = len(QgsProject.instance().mapLayers().values())
        subbasinsLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), subbasinsFile, FileTypes._EXISTINGSUBBASINS, self.plugin._gv, demLayer, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(subbasinsLayer and loaded, 'Failed to load subbasins shapefile'.format(subbasinsFile))
        self.delin._dlg.selectSubbasins.setText(subbasinsFile)
        self.plugin._gv.subbasinsFile = subbasinsFile 
        QSWATUtils.copyFiles(QFileInfo(os.path.join(self.dataDir, 'ravn_demwshed.shp')), self.plugin._gv.shapesDir)       
        wshedFile = os.path.join(self.plugin._gv.shapesDir, 'ravn_demwshed.shp')
        numLayers = len(QgsProject.instance().mapLayers().values())
        wshedLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), wshedFile, FileTypes._EXISTINGWATERSHED, self.plugin._gv, demLayer, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(wshedLayer and loaded, 'Failed to load wshed shapefile'.format(wshedFile))
        self.delin._dlg.selectWshed.setText(wshedFile)
        self.plugin._gv.wshedFile = wshedFile
        channelFile = os.path.join(self.dataDir, 'ravn_demchannel.shp')
        numLayers = len(QgsProject.instance().mapLayers().values())
        channelLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), channelFile, FileTypes._CHANNELS, self.plugin._gv, demLayer, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(channelLayer and loaded, 'Failed to load channels shapefile'.format(channelFile))
        self.delin._dlg.selectStreams.setText(channelFile)
        self.plugin._gv.channelFile = channelFile
        self.delin._dlg.numProcesses.setValue(6 if Parameters._ISWIN else 4)
        self.delin._dlg.useOutlets.setChecked(False)
        QtTest.QTest.mouseClick(self.delin._dlg.existRunButton, Qt.LeftButton)
        QSWATUtils.copyFiles(QFileInfo(os.path.join(self.dataDir, 'Ravn2.shp')), self.plugin._gv.shapesDir)
        self.delin._dlg.selectLakes.setText(os.path.join(self.plugin._gv.shapesDir, 'Ravn2.shp'))
        lakesLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.delin._dlg.selectLakes.text(), FileTypes._LAKES, self.plugin._gv, demLayer, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(lakesLayer and loaded, 'Failed to load lakes shapefile {0}'.format(self.delin._dlg.selectLakes.text()))
        self.plugin._gv.lakeFile = self.delin._dlg.selectLakes.text()
        self.lakesDone = False
        self.lakePointsAdded = False
        QtTest.QTest.mouseClick(self.delin._dlg.OKButton, Qt.LeftButton)
        self.assertTrue(self.dlg.hrusButton.isEnabled(), 'HRUs button not enabled')
        self.hrus.init()
        hrudlg = self.hrus._dlg
        self.hrus.landuseFile = os.path.join(self.dataDir, 'ravn_landuse.tif')
        numLayers = len(QgsProject.instance().mapLayers().values())
        self.hrus.landuseLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.landuseFile, FileTypes._LANDUSES, self.plugin._gv, None, QSWATUtils._LANDUSE_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.landuseLayer and loaded, 'Failed to load landuse file {0}'.format(self.hrus.landuseFile))
        self.hrus.soilFile = os.path.join(self.dataDir, 'ravn_soil.tif')
        numLayers = len(QgsProject.instance().mapLayers().values())
        self.hrus.soilLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.soilFile, FileTypes._SOILS, self.plugin._gv, None, QSWATUtils._SOIL_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.soilLayer and loaded, 'Failed to load soil file {0}'.format(self.hrus.soilFile))
        landuse_lookup = os.path.join(self.dataDir, 'ravn_landuse.csv')
        landuse_table = self.hrus._db.readCsvFile(landuse_lookup, 'landuse', self.hrus._db.landuseTableNames)
        landCombo = hrudlg.selectLanduseTable
        landCombo.insertItem(0, landuse_table)
        landIndex = landCombo.findText(landuse_table)
        self.assertTrue(landIndex >= 0, 'Cannot find landuse table {0}'.format(landuse_table))
        landCombo.setCurrentIndex(landIndex)
        soil_lookup = os.path.join(self.dataDir, 'ravn_soil.csv')
        soil_table = self.hrus._db.readCsvFile(soil_lookup, 'soil', self.hrus._db.soilTableNames)
        soilCombo = hrudlg.selectSoilTable
        soilCombo.insertItem(0, soil_table)
        soilIndex = soilCombo.findText(soil_table)
        self.assertTrue(soilIndex >= 0, 'Cannot find soil table {0}'.format(soil_table))
        soilCombo.setCurrentIndex(soilIndex)
        usersoil_lookup = os.path.join(self.dataDir, 'ravn_usersoil.csv')
        usersoil_table = self.hrus._db.readCsvFile(usersoil_lookup, 'usersoil', self.hrus._db.usersoilTableNames)
        usersoilCombo = hrudlg.selectUsersoilTable
        usersoilCombo.insertItem(0, usersoil_table)
        usersoilIndex = usersoilCombo.findText(usersoil_table)
        self.assertTrue(usersoilIndex >= 0, 'Cannot find usersoil table {0}'.format(usersoil_table))
        usersoilCombo.setCurrentIndex(usersoilIndex)
        self.plugin._gv.db.usersoilTable = usersoil_table
        lims = self.plugin._gv.db.slopeLimits
        self.assertTrue(len(lims) == 0, 'Limits list is not empty')
        self.assertTrue(hrudlg.elevBandsButton.isEnabled(), 'Elevation bands button not enabled')
        hrudlg.channelMergeVal.setText('1')
        QtTest.QTest.mouseClick(hrudlg.readButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._TOPOREPORT)))
        self.assertTrue(self.dlg.reportsBox.isEnabled() and self.dlg.reportsBox.findText(Parameters._TOPOITEM) >= 0, \
                        'Elevation report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._BASINREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._BASINITEM) >= 0, \
                        'Landuse and soil report not accessible from main form')
        self.assertTrue(hrudlg.splitButton.isEnabled(), 'Split landuses button not enabled')
        self.assertTrue(hrudlg.exemptButton.isEnabled(), 'Exempt landuses button not enabled')
        self.assertTrue(hrudlg.targetButton.isEnabled(), 'Target button not enabled')
        QtTest.QTest.mouseClick(hrudlg.targetButton, Qt.LeftButton)
        self.assertTrue(hrudlg.stackedWidget.currentIndex() == 2, 'Wrong threshold page {0} selected'.format(hrudlg.stackedWidget.currentIndex()))
        hrudlg.targetVal.setText('500')
        self.assertTrue(hrudlg.createButton.isEnabled(), 'Create button not enabled')
        QtTest.QTest.mouseClick(hrudlg.createButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._HRUSREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._HRUSITEM) >= 0, \
                        'HRUs report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.shapesDir, 'lsus2.shp')), 'Actual LSUs shapefile not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'rivs.shp')), 'Reaches results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'subs.shp')), 'Watershed results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'lsus.shp')), 'LSUs results template file not created.')
        self.assertEqual(len(self.hrus.CreateHRUs.basins), 5, 'Subbasin count is {0} instead of 5'.format(len(self.hrus.CreateHRUs.basins)))
        self.assertEqual(self.hrus.CreateHRUs.countChannels(), 74, 'Channel count is {0} instead of 74'.format(self.hrus.CreateHRUs.countChannels()))
        self.assertEqual(self.hrus.CreateHRUs.countLsus(), 74, 'LSU count is {0} instead of 74'.format(self.hrus.CreateHRUs.countLsus()))
        self.assertEqual(self.hrus.CreateHRUs.countHRUs(), 500, 'HRU count is {0} instead of 500'.format(self.hrus.CreateHRUs.countHRUs()))
        #if Parameters._ISWIN:
        #    self.checkHashes(HashTable12)
        self.assertTrue(self.dlg.editButton.isEnabled(), 'SWAT Editor button not enabled')
        self.plugin.finish()
        
    def test13(self):
        """MPI with 8 processes; stream threshold 5 sq km; channel threshold 0.5 sq km;
        1 outlet; grid size 4; lake; dominant HRUs."""
        print('\nTest 13')
        self.delin._dlg.selectDem.setText(self.copyDem('ravn_dem.tif'))
        self.assertTrue(os.path.exists(self.delin._dlg.selectDem.text()), 'Failed to copy DEM to source directory')
        self.hrus = HRUs(self.plugin._gv, self.dlg.reportsBox)
        # listener = Listener(self.delin, self.hrus, self.hrus.CreateHRUs)
        QgsProject.instance().removeAllMapLayers()
        numLayers = len(QgsProject.instance().mapLayers().values())
        self.assertEqual(numLayers, 0, 'Unexpected start with {0} layers'.format(numLayers))
        self.delin._dlg.numProcesses.setValue(8 if Parameters._ISWIN else 4)
        demLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.delin._dlg.selectDem.text(), FileTypes._DEM, self.plugin._gv, None, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(demLayer and loaded, 'Failed to load DEM {0}'.format(self.delin._dlg.selectDem.text()))
        self.delin.setDefaultNumCells(demLayer)
        self.assertTrue(demLayer.crs().mapUnits() == QgsUnitTypes.DistanceMeters, 'Map units not meters but {0}'.format(demLayer.crs().mapUnits()))
        unitIndex = self.delin._dlg.areaUnitsBox.findText(Parameters._SQKM)
        self.assertTrue(unitIndex >= 0, 'Cannot find sq km area units')
        self.delin._dlg.areaUnitsBox.setCurrentIndex(unitIndex)
        self.delin.setDefaultNumCells(demLayer)
        self.delin._dlg.areaSt.setText('5')
        self.delin._dlg.areaCh.setText('0.5')
        self.assertTrue(self.delin._dlg.numCellsSt.text() == '5555', 
                        'Unexpected number of stream cells for delineation {0}'.format(self.delin._dlg.numCellsSt.text()))
        self.assertTrue(self.delin._dlg.numCellsCh.text() == '555', 
                        'Unexpected number of channel cells for delineation {0}'.format(self.delin._dlg.numCellsCh.text()))
        QSWATUtils.copyFiles(QFileInfo(os.path.join(self.dataDir, 'ravn_outlet.shp')), self.plugin._gv.shapesDir)
        self.delin._dlg.selectOutlets.setText(os.path.join(self.plugin._gv.shapesDir, 'ravn_outlet.shp'))
        self.assertTrue(os.path.exists(self.delin._dlg.selectOutlets.text()), 'Failed to find outlet file {0}'.format(self.delin._dlg.selectOutlets.text()))
        self.delin._dlg.useOutlets.setChecked(True)
        QtTest.QTest.mouseClick(self.delin._dlg.gridBox, Qt.LeftButton)
        self.delin._dlg.gridSize.setValue(4)
        QtTest.QTest.mouseClick(self.delin._dlg.delinRunButton2, Qt.LeftButton)
        self.assertTrue('1 snapped' in self.delin._dlg.snappedLabel.text(), 'Unexpected snapping result: {0}'.format(self.delin._dlg.snappedLabel.text()))
        self.assertTrue(self.delin.areaOfCell > 0, 'Area of cell is ' + str(self.delin.areaOfCell))
        QSWATUtils.copyFiles(QFileInfo(os.path.join(self.dataDir, 'Ravn.shp')), self.plugin._gv.shapesDir)
        self.delin._dlg.selectLakes.setText(os.path.join(self.plugin._gv.shapesDir, 'Ravn.shp'))
        lakesLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.delin._dlg.selectLakes.text(), FileTypes._LAKES, self.plugin._gv, demLayer, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(lakesLayer and loaded, 'Failed to load lakes shapefile {0}'.format(self.delin._dlg.selectLakes.text()))
        self.plugin._gv.lakeFile = self.delin._dlg.selectLakes.text()
        self.lakesDone = False
        self.lakePointsAdded = False
        self.gridLakesAdded = False
        gridLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.plugin._gv.subbasinsFile, FileTypes._GRID, self.plugin._gv, demLayer, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.delin.makeGridLakes(lakesLayer, gridLayer)
        QtTest.QTest.mouseClick(self.delin._dlg.OKButton, Qt.LeftButton)
        self.assertTrue(self.dlg.hrusButton.isEnabled(), 'HRUs button not enabled')
        self.hrus.init()
        hrudlg = self.hrus._dlg
        self.hrus.landuseFile = os.path.join(self.dataDir, 'ravn_landuse.tif')
        numLayers = len(QgsProject.instance().mapLayers().values())
        self.hrus.landuseLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.landuseFile, FileTypes._LANDUSES, self.plugin._gv, None, QSWATUtils._LANDUSE_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.landuseLayer and loaded, 'Failed to load landuse file {0}'.format(self.hrus.landuseFile))
        self.hrus.soilFile = os.path.join(self.dataDir, 'ravn_soil.tif')
        numLayers = len(QgsProject.instance().mapLayers().values())
        self.hrus.soilLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.soilFile, FileTypes._SOILS, self.plugin._gv, None, QSWATUtils._SOIL_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.soilLayer and loaded, 'Failed to load soil file {0}'.format(self.hrus.soilFile))
        landuse_lookup = os.path.join(self.dataDir, 'ravn_landuse.csv')
        landuse_table = self.hrus._db.readCsvFile(landuse_lookup, 'landuse', self.hrus._db.landuseTableNames)
        landCombo = hrudlg.selectLanduseTable
        landCombo.insertItem(0, landuse_table)
        landIndex = landCombo.findText(landuse_table)
        self.assertTrue(landIndex >= 0, 'Cannot find landuse table {0}'.format(landuse_table))
        landCombo.setCurrentIndex(landIndex)
        soil_lookup = os.path.join(self.dataDir, 'ravn_soil.csv')
        soil_table = self.hrus._db.readCsvFile(soil_lookup, 'soil', self.hrus._db.soilTableNames)
        soilCombo = hrudlg.selectSoilTable
        soilCombo.insertItem(0, soil_table)
        soilIndex = soilCombo.findText(soil_table)
        self.assertTrue(soilIndex >= 0, 'Cannot find soil table {0}'.format(soil_table))
        soilCombo.setCurrentIndex(soilIndex)
        usersoil_lookup = os.path.join(self.dataDir, 'ravn_usersoil.csv')
        usersoil_table = self.hrus._db.readCsvFile(usersoil_lookup, 'usersoil', self.hrus._db.usersoilTableNames)
        usersoilCombo = hrudlg.selectUsersoilTable
        usersoilCombo.insertItem(0, usersoil_table)
        usersoilIndex = usersoilCombo.findText(usersoil_table)
        self.assertTrue(usersoilIndex >= 0, 'Cannot find usersoil table {0}'.format(usersoil_table))
        usersoilCombo.setCurrentIndex(usersoilIndex)
        self.plugin._gv.db.usersoilTable = usersoil_table
        lims = self.plugin._gv.db.slopeLimits
        self.assertTrue(len(lims) == 0, 'Limits list is not empty')
        self.assertTrue(hrudlg.elevBandsButton.isEnabled(), 'Elevation bands button not enabled')
        hrudlg.channelMergeVal.setText('1')
        QtTest.QTest.mouseClick(hrudlg.readButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._TOPOREPORT)))
        self.assertTrue(self.dlg.reportsBox.isEnabled() and self.dlg.reportsBox.findText(Parameters._TOPOITEM) >= 0, \
                        'Elevation report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._BASINREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._BASINITEM) >= 0, \
                        'Landuse and soil report not accessible from main form')
        self.assertTrue(hrudlg.splitButton.isEnabled(), 'Split landuses button not enabled')
        self.assertTrue(hrudlg.exemptButton.isEnabled(), 'Exempt landuses button not enabled')
        self.assertTrue(hrudlg.dominantHRUButton.isEnabled(), 'Dominant HRU button not enabled')
        QtTest.QTest.mouseClick(hrudlg.dominantHRUButton, Qt.LeftButton)
        self.assertFalse(hrudlg.areaPercentChoiceGroup.isEnabled(), 'Area percent choice group enabled')
        self.assertFalse(hrudlg.landuseSoilSlopeGroup.isEnabled(), ' Landuse soil slope group enabled')
        self.assertFalse(hrudlg.areaGroup.isEnabled(), 'Area group enabled')
        self.assertFalse(hrudlg.targetGroup.isEnabled(), 'Target group enabled')
        self.assertTrue(hrudlg.createButton.isEnabled(), 'Create button not enabled')
        QtTest.QTest.mouseClick(hrudlg.createButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._HRUSREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._HRUSITEM) >= 0, \
                        'HRUs report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.shapesDir, 'lsus1.shp')), 'Actual LSUs shapefile not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'rivs.shp')), 'Reaches results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'subs.shp')), 'Watershed results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'lsus.shp')), 'LSUs results template file not created.')
        self.assertEqual(len(self.hrus.CreateHRUs.basins), 5319, 'Subbasin count is {0} instead of 5319'.format(len(self.hrus.CreateHRUs.basins)))
        self.assertEqual(self.hrus.CreateHRUs.countChannels(), 5310, 'Channel count is {0} instead of 5310'.format(self.hrus.CreateHRUs.countChannels()))
        self.assertEqual(self.hrus.CreateHRUs.countLsus(), 5310, 'LSU count is {0} instead of 5310'.format(self.hrus.CreateHRUs.countLsus()))
        self.assertEqual(self.hrus.CreateHRUs.countHRUs(), 5310, 'HRU count is {0} instead of 5310'.format(self.hrus.CreateHRUs.countHRUs()))
        #if Parameters._ISWIN:
        #    self.checkHashes(HashTable13)
        self.assertTrue(self.dlg.editButton.isEnabled(), 'SWAT Editor button not enabled')
        self.plugin.finish()
        
    def test14(self):
        """MPI with 10 processes; existing grid; stream drainage; lake; dominant HRUs."""
        print('\nTest 14')
        self.delin._dlg.selectDem.setText(self.copyDem('ravn_dem.tif'))
        self.assertTrue(os.path.exists(self.delin._dlg.selectDem.text()), 'Failed to copy DEM to source directory')
        self.hrus = HRUs(self.plugin._gv, self.dlg.reportsBox)
        # listener = Listener(self.delin, self.hrus, self.hrus.CreateHRUs)
        QgsProject.instance().removeAllMapLayers()
        numLayers = len(QgsProject.instance().mapLayers().values())
        self.assertEqual(numLayers, 0, 'Unexpected start with {0} layers'.format(numLayers))
        self.delin._dlg.numProcesses.setValue(10 if Parameters._ISWIN else 4)
        demLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.delin._dlg.selectDem.text(), FileTypes._DEM, self.plugin._gv, None, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(demLayer and loaded, 'Failed to load DEM {0}'.format(self.delin._dlg.selectDem.text()))
        self.delin.setDefaultNumCells(demLayer)
        self.assertTrue(demLayer.crs().mapUnits() == QgsUnitTypes.DistanceMeters, 'Map units not meters but {0}'.format(demLayer.crs().mapUnits()))
        self.delin._dlg.tabWidget.setCurrentIndex(1)
        QSWATUtils.copyFiles(QFileInfo(os.path.join(self.dataDir, 'ravn_grid.shp')), self.plugin._gv.shapesDir)
        subbasinsFile = os.path.join(self.plugin._gv.shapesDir, 'ravn_grid.shp')
        self.delin._dlg.selectSubbasins.setText(subbasinsFile)
        numLayers = len(QgsProject.instance().mapLayers().values())
        subbasinsLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), subbasinsFile, FileTypes._EXISTINGWATERSHED, self.plugin._gv, demLayer, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(subbasinsLayer and loaded, 'Failed to load grid shapefile {0}'.format(subbasinsFile))
        self.plugin._gv.subbasinsFile = subbasinsFile
        QSWATUtils.copyFiles(QFileInfo(os.path.join(self.dataDir, 'ravn_gridstreams.shp')), self.plugin._gv.shapesDir)
        streamFile = os.path.join(self.plugin._gv.shapesDir, 'ravn_gridstreams.shp')
        self.delin._dlg.selectStreams.setText(streamFile)
        numLayers = len(QgsProject.instance().mapLayers().values())
        streamLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), streamFile, FileTypes._GRIDSTREAMS, self.plugin._gv, demLayer, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(streamLayer and loaded, 'Failed to load streams shapefile {0}'.format(streamFile))
        self.plugin._gv.streamFile = streamFile
        self.delin._dlg.numProcesses.setValue(0)
        self.assertTrue(self.delin._dlg.useGrid.isEnabled(), 'Use grid not enabled')
        self.assertFalse(self.delin._dlg.useGrid.isChecked(), 'Use grid already checked')
        QtTest.QTest.mouseClick(self.delin._dlg.useGrid, Qt.LeftButton)
        # this fails: self.assertTrue(self.delin._dlg.useGrid.isChecked(), 'Use grid not checked')
        # so
        self.delin._dlg.useGrid.setChecked(True)
        self.delin.changeUseGrid()
        self.assertTrue(self.plugin._gv.useGridModel, 'Not set to use grid')
        self.assertTrue(self.delin._dlg.drainGridButton.isEnabled(), 'Watershed drainage option not enabled')
        self.assertTrue(self.delin._dlg.drainStreamsButton.isEnabled(), 'Streams drainage option not enabled')
        self.assertTrue(self.delin._dlg.drainTableButton.isEnabled(), 'Table drainage option not enabled')
        QtTest.QTest.mouseClick(self.delin._dlg.drainStreamsButton, Qt.LeftButton)
        self.assertTrue(self.delin._dlg.reuseButton.isEnabled(), 'Reuse button not enabled')
        QtTest.QTest.mouseClick(self.delin._dlg.reuseButton, Qt.LeftButton)
        QtTest.QTest.mouseClick(self.delin._dlg.existRunButton, Qt.LeftButton)
        QSWATUtils.copyFiles(QFileInfo(os.path.join(self.dataDir, 'Ravn.shp')), self.plugin._gv.shapesDir)
        lakeFile = os.path.join(self.plugin._gv.shapesDir, 'Ravn.shp')
        self.delin._dlg.selectLakes.setText(lakeFile)
        lakesLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), lakeFile, FileTypes._LAKES, self.plugin._gv, demLayer, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(lakesLayer and loaded, 'Failed to load lakes shapefile {0}'.format(self.delin._dlg.selectLakes.text()))
        self.plugin._gv.lakeFile = lakeFile
        self.lakesDone = False
        self.lakePointsAdded = False
        self.gridLakesAdded = False
        QtTest.QTest.mouseClick(self.delin._dlg.OKButton, Qt.LeftButton)
        self.assertTrue(self.dlg.hrusButton.isEnabled(), 'HRUs button not enabled')
        self.hrus.init()
        hrudlg = self.hrus._dlg
        self.hrus.landuseFile = os.path.join(self.dataDir, 'ravn_landuse.tif')
        numLayers = len(QgsProject.instance().mapLayers().values())
        self.hrus.landuseLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.landuseFile, FileTypes._LANDUSES, self.plugin._gv, None, QSWATUtils._LANDUSE_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.landuseLayer and loaded, 'Failed to load landuse file {0}'.format(self.hrus.landuseFile))
        self.hrus.soilFile = os.path.join(self.dataDir, 'ravn_soil.tif')
        numLayers = len(QgsProject.instance().mapLayers().values())
        self.hrus.soilLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.soilFile, FileTypes._SOILS, self.plugin._gv, None, QSWATUtils._SOIL_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.soilLayer and loaded, 'Failed to load soil file {0}'.format(self.hrus.soilFile))
        landuse_lookup = os.path.join(self.dataDir, 'ravn_landuse.csv')
        landuse_table = self.hrus._db.readCsvFile(landuse_lookup, 'landuse', self.hrus._db.landuseTableNames)
        landCombo = hrudlg.selectLanduseTable
        landCombo.insertItem(0, landuse_table)
        landIndex = landCombo.findText(landuse_table)
        self.assertTrue(landIndex >= 0, 'Cannot find landuse table {0}'.format(landuse_table))
        landCombo.setCurrentIndex(landIndex)
        soil_lookup = os.path.join(self.dataDir, 'ravn_soil.csv')
        soil_table = self.hrus._db.readCsvFile(soil_lookup, 'soil', self.hrus._db.soilTableNames)
        soilCombo = hrudlg.selectSoilTable
        soilCombo.insertItem(0, soil_table)
        soilIndex = soilCombo.findText(soil_table)
        self.assertTrue(soilIndex >= 0, 'Cannot find soil table {0}'.format(soil_table))
        soilCombo.setCurrentIndex(soilIndex)
        usersoil_lookup = os.path.join(self.dataDir, 'ravn_usersoil.csv')
        usersoil_table = self.hrus._db.readCsvFile(usersoil_lookup, 'usersoil', self.hrus._db.usersoilTableNames)
        usersoilCombo = hrudlg.selectUsersoilTable
        usersoilCombo.insertItem(0, usersoil_table)
        usersoilIndex = usersoilCombo.findText(usersoil_table)
        self.assertTrue(usersoilIndex >= 0, 'Cannot find usersoil table {0}'.format(usersoil_table))
        usersoilCombo.setCurrentIndex(usersoilIndex)
        self.plugin._gv.db.usersoilTable = usersoil_table
        lims = self.plugin._gv.db.slopeLimits
        self.assertTrue(len(lims) == 0, 'Limits list is not empty')
        self.assertTrue(hrudlg.elevBandsButton.isEnabled(), 'Elevation bands button not enabled')
        hrudlg.channelMergeVal.setText('1')
        QtTest.QTest.mouseClick(hrudlg.readButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._TOPOREPORT)))
        self.assertTrue(self.dlg.reportsBox.isEnabled() and self.dlg.reportsBox.findText(Parameters._TOPOITEM) >= 0, \
                        'Elevation report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._BASINREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._BASINITEM) >= 0, \
                        'Landuse and soil report not accessible from main form')
        self.assertTrue(hrudlg.splitButton.isEnabled(), 'Split landuses button not enabled')
        self.assertTrue(hrudlg.exemptButton.isEnabled(), 'Exempt landuses button not enabled')
        self.assertTrue(hrudlg.dominantHRUButton.isEnabled(), 'Dominant HRU button not enabled')
        QtTest.QTest.mouseClick(hrudlg.dominantHRUButton, Qt.LeftButton)
        self.assertFalse(hrudlg.areaPercentChoiceGroup.isEnabled(), 'Area percent choice group enabled')
        self.assertFalse(hrudlg.landuseSoilSlopeGroup.isEnabled(), ' Landuse soil slope group enabled')
        self.assertFalse(hrudlg.areaGroup.isEnabled(), 'Area group enabled')
        self.assertFalse(hrudlg.targetGroup.isEnabled(), 'Target group enabled')
        self.assertTrue(hrudlg.createButton.isEnabled(), 'Create button not enabled')
        QtTest.QTest.mouseClick(hrudlg.createButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._HRUSREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._HRUSITEM) >= 0, \
                        'HRUs report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.shapesDir, 'lsus1.shp')), 'Actual LSUs shapefile not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'rivs.shp')), 'Reaches results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'subs.shp')), 'Watershed results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'lsus.shp')), 'LSUs results template file not created.')
        self.assertEqual(len(self.hrus.CreateHRUs.basins), 5319, 'Subbasin count is {0} instead of 5319'.format(len(self.hrus.CreateHRUs.basins)))
        self.assertEqual(self.hrus.CreateHRUs.countChannels(), 5310, 'Channel count is {0} instead of 5310'.format(self.hrus.CreateHRUs.countChannels()))
        self.assertEqual(self.hrus.CreateHRUs.countLsus(), 5310, 'LSU count is {0} instead of 5310'.format(self.hrus.CreateHRUs.countLsus()))
        self.assertEqual(self.hrus.CreateHRUs.countHRUs(), 5310, 'HRU count is {0} instead of 5310'.format(self.hrus.CreateHRUs.countHRUs()))
        #if Parameters._ISWIN:
        #    self.checkHashes(HashTable14)
        self.assertTrue(self.dlg.editButton.isEnabled(), 'SWAT Editor button not enabled')
        self.plugin.finish()
        
    def test15(self):
        """MPI 8 processes; clipped San Juan DEM: no inlets/outlets file; delineation threshold 6000 ha; 
        landscape by buffer, inversion and branch (use inversion); no slope limits; dominant HRU"""
        print('\nTest 15')
        self.delin._dlg.selectDem.setText(self.copyDem('sj_dem_clip.tif'))
        self.assertTrue(os.path.exists(self.delin._dlg.selectDem.text()), 'Failed to copy DEM to source directory')
        ## HRUs object
        self.hrus = HRUs(self.plugin._gv, self.dlg.reportsBox)
        # listener = Listener(self.delin, self.hrus, self.hrus.CreateHRUs)
        numLayers = len(QgsProject.instance().mapLayers().values())
        self.assertEqual(numLayers, 0, 'Unexpected start with {0} layers'.format(numLayers))
        demLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.delin._dlg.selectDem.text(), FileTypes._DEM, 
                                                         self.plugin._gv, True, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(demLayer and loaded, 'Failed to load DEM {0}'.format(self.delin._dlg.selectDem.text()))
        self.assertTrue(demLayer.crs().mapUnits() == QgsUnitTypes.DistanceMeters, 'Map units not meters but {0}'.format(demLayer.crs().mapUnits()))
        unitIndex = self.delin._dlg.areaUnitsBox.findText(Parameters._HECTARES)
        self.assertTrue(unitIndex >= 0, 'Cannot find hectare area units')
        self.delin._dlg.areaUnitsBox.setCurrentIndex(unitIndex)
        self.delin.setDefaultNumCells(demLayer)
        self.delin._dlg.areaSt.setText('6000')
        self.delin._dlg.areaCh.setText('600')
        self.assertTrue(self.delin._dlg.numCellsSt.text() == '8640', 
                        'Unexpected number of stream cells for delineation {0}'.format(self.delin._dlg.numCellsSt.text()))
        self.assertTrue(self.delin._dlg.numCellsCh.text() == '864', 
                        'Unexpected number of channel cells for delineation {0}'.format(self.delin._dlg.numCellsCh.text()))
        self.delin._dlg.useOutlets.setChecked(False)
        QtTest.QTest.mouseClick(self.delin._dlg.delinRunButton2, Qt.LeftButton)
        self.assertTrue(self.delin.areaOfCell > 0, 'Area of cell is ' + str(self.delin.areaOfCell))
        self.delin._dlg.tabWidget_2.setCurrentIndex(0)
        self.assertTrue(self.delin._dlg.landscapeButton.isEnabled(), 'Landscape button not enabled')
        QtTest.QTest.mouseClick(self.delin._dlg.landscapeButton, Qt.LeftButton)
        lscape = self.delin.L
        self.assertTrue(lscape is not None, 'Landscape module not started')
        self.assertFalse(lscape._dlg.hillslopesCheckBox.isChecked(), 'Calculate hillslopes is checked')
        self.assertTrue(lscape._dlg.floodplainCheckBox.isChecked(), 'Calculate floodplain is not checked')
        self.assertTrue(lscape._dlg.slopePositionSpinBox.isEnabled(), 'Slope position spinbox not enabled')
        self.assertTrue(lscape._dlg.slopePositionSpinBox.value() == 0.10, 'Slope position spinbox has wrong value {0}'.format(lscape._dlg.slopePositionSpinBox.value()))
        self.assertTrue(lscape._dlg.createButton.isEnabled(), 'Lansdscape create button not enabled')
        lscape._dlg.methodTab.setCurrentIndex(0)
        self.assertTrue(lscape._dlg.bufferMultiplier.isEnabled(), 'Buffer multipler not enabled')
        self.assertTrue(lscape._dlg.bufferMultiplier.value() == 10, 'Buffer multiplier has wrong value {0}'.format(lscape._dlg.bufferMultiplier.value()))
        QtTest.QTest.mouseClick(lscape._dlg.createButton, Qt.LeftButton)
        bufferFloodLayer = QSWATUtils.getLayerByLegend(QSWATUtils._BUFFERFLOODLEGEND, self.root.findLayers())
        self.assertTrue(bufferFloodLayer, 'Buffer flood layer not created')
        lscape._dlg.methodTab.setCurrentIndex(1)
        self.assertTrue(lscape._dlg.ridgeThresholdCells.isEnabled(), 'Ridge threshold cells not enabled')
        self.assertTrue(lscape._dlg.ridgeThresholdCells.text() == '8640', 'Ridge threshold cells has wrong value {0}'.format(lscape._dlg.ridgeThresholdCells.text()))
        areaUnitIndex = lscape._dlg.areaUnitsBox.findText(Parameters._HECTARES)
        self.assertTrue(areaUnitIndex >= 0, 'Cannot find hectare area units for ')
        lscape._dlg.areaUnitsBox.setCurrentIndex(areaUnitIndex)
        lscape.changeRidgeArea()
        self.assertTrue(lscape._dlg.ridgeThresholdArea.isEnabled(), 'Ridge threshold area not enabled')
        self.assertTrue(lscape._dlg.ridgeThresholdArea.text() == '6000', 'Ridge threshold area has wrong value {0}'.format(lscape._dlg.ridgeThresholdArea.text()))
        QtTest.QTest.mouseClick(lscape._dlg.createButton, Qt.LeftButton)
        invFloodLayer = QSWATUtils.getLayerByLegend(QSWATUtils._INVFLOODLEGEND, self.root.findLayers())
        self.assertTrue(invFloodLayer, 'Inversion flood layer not created')
        lscape._dlg.methodTab.setCurrentIndex(2)
        self.assertTrue(lscape._dlg.branchThreshold.isEnabled(), 'Branch threshold not enabled')
        branchThresh = int(2 * math.sqrt(8640 * self.plugin._gv.topo.dx * self.plugin._gv.topo.dy))
        self.assertTrue(int(lscape._dlg.branchThreshold.text()) == branchThresh, 'Branch threshold has wrong value {0}'.format(lscape._dlg.branchThreshold.text()))
        QtTest.QTest.mouseClick(lscape._dlg.createButton, Qt.LeftButton)
        branchFloodLayer = QSWATUtils.getLayerByLegend(QSWATUtils._BRANCHFLOODLEGEND, self.root.findLayers())
        self.assertTrue(branchFloodLayer, 'Branch flood layer not created')
        self.assertTrue(lscape._dlg.doneButton.isEnabled(), 'Landscape done button not enabled')
        QtTest.QTest.mouseClick(lscape._dlg.doneButton, Qt.LeftButton)
        QtTest.QTest.mouseClick(self.delin._dlg.OKButton, Qt.LeftButton)
        self.assertTrue(self.dlg.hrusButton.isEnabled(), 'HRUs button not enabled')
        self.hrus.init()
        hrudlg = self.hrus._dlg
        self.assertTrue(hrudlg.HRUsTab.isTabEnabled(0), 'Landuse and soil tab not enabled')
        self.assertFalse(hrudlg.HRUsTab.isTabEnabled(1), 'HRUs tab enabled at start')
        self.assertTrue(hrudlg.HRUsTab.currentIndex() == 0, 'Create HRUs not starting with landuse and soil tab')
        self.hrus.landuseFile = os.path.join(self.dataDir, 'sj_land.tif')
        numLayers = len(QgsProject.instance().mapLayers().values())
        self.hrus.landuseLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.landuseFile, FileTypes._LANDUSES, 
                                                                       self.plugin._gv, None, QSWATUtils._LANDUSE_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.landuseLayer and loaded, 'Failed to load landuse file {0}'.format(self.hrus.landuseFile))
        self.hrus.soilFile = os.path.join(self.dataDir, 'sj_soil.tif')
        numLayers = len(QgsProject.instance().mapLayers().values())
        self.hrus.soilLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), self.hrus.soilFile, FileTypes._SOILS, 
                                                                    self.plugin._gv, None, QSWATUtils._SOIL_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(self.hrus.soilLayer and loaded, 'Failed to load soil file {0}'.format(self.hrus.soilFile))
        landCombo = hrudlg.selectLanduseTable
        landIndex = landCombo.findText('global_landuses')
        self.assertTrue(landIndex >= 0, 'Cannot find global landuses table')
        landCombo.setCurrentIndex(landIndex)
        soilCombo = hrudlg.selectSoilTable
        soilIndex = soilCombo.findText('global_soils')
        self.assertTrue(soilIndex >= 0, 'Cannot find global soils table')
        soilCombo.setCurrentIndex(soilIndex)
        usersoilCombo = hrudlg.selectUsersoilTable
        usersoilIndex = usersoilCombo.findText('global_usersoil')
        self.assertTrue(usersoilIndex >= 0, 'Cannot find global usersoil table')
        usersoilCombo.setCurrentIndex(usersoilIndex)
        self.plugin._gv.db.usersoilTable = 'global_usersoil'
        QtTest.QTest.mouseClick(hrudlg.readButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._TOPOREPORT)))
        self.assertTrue(self.dlg.reportsBox.isEnabled() and self.dlg.reportsBox.findText(Parameters._TOPOITEM) >= 0, \
                        'Elevation report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._BASINREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._BASINITEM) >= 0, \
                        'Landuse and soil report not accessible from main form')
        self.assertTrue(hrudlg.HRUsTab.isTabEnabled(1), 'HRUs tab not enabled after doing landuse and soil')
        hrudlg.HRUsTab.setCurrentIndex(1)
        self.assertTrue(hrudlg.splitButton.isEnabled(), 'Split landuses button not enabled')
        self.assertTrue(hrudlg.exemptButton.isEnabled(), 'Exempt landuses button not enabled')
        self.assertTrue(hrudlg.floodplainCombo.count() == 4, 'Unexpected number of floodplain maps {0}'.format(hrudlg.floodplainCombo.count() - 1))
        invFloodIndex = hrudlg.floodplainCombo.findText('invflood', Qt.MatchContains)
        self.assertTrue(invFloodIndex > 0, 'Flood by inversion raster not in combo box')
        hrudlg.floodplainCombo.setCurrentIndex(invFloodIndex)
        self.assertTrue(hrudlg.dominantHRUButton.isEnabled(), 'Dominant HRU button not enabled')
        QtTest.QTest.mouseClick(hrudlg.dominantHRUButton, Qt.LeftButton)
        self.assertFalse(hrudlg.stackedWidget.isEnabled(), 'Stacked widget not disabled')
        self.assertTrue(hrudlg.createButton.isEnabled(), 'Create button not enabled')
        QtTest.QTest.mouseClick(hrudlg.createButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._HRUSREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._HRUSITEM) >= 0, \
                        'HRUs report not accessible from main form')
        self.assertEqual(len(self.hrus.CreateHRUs.basins), 51, 'Subbasin count is {0} instead of 51'.format(len(self.hrus.CreateHRUs.basins)))
        self.assertEqual(self.hrus.CreateHRUs.countChannels(), 518, 'Channel count is {0} instead of 518'.format(self.hrus.CreateHRUs.countChannels()))
        self.assertEqual(self.hrus.CreateHRUs.countLsus(), 518, 'LSU count is {0} instead of 518'.format(self.hrus.CreateHRUs.countLsus()))
        self.assertEqual(self.hrus.CreateHRUs.countHRUs(), 518, 'HRU count is {0} instead of 518'.format(self.hrus.CreateHRUs.countHRUs()))
        #self.checkHashes(HashTable6)
        self.assertTrue(self.dlg.editButton.isEnabled(), 'SWAT Editor button not enabled')
        
    def copyDem(self, demFile):
        """Copy DEM to Source directory as GeoTIFF."""
        inFileName = os.path.join(self.dataDir, demFile)
        outFileName = os.path.join(self.plugin._gv.demDir, demFile)
        inDs = gdal.Open(inFileName, gdal.GA_ReadOnly)
        driver = gdal.GetDriverByName('GTiff')
        outDs = driver.CreateCopy(outFileName, inDs, 0)
        if outDs is None:
            raise RuntimeError('Failed to create dem in geoTiff format')
        QSWATUtils.copyPrj(inFileName, outFileName)
        return outFileName
    
    def waitLayerAdded(self, numLayers):
        """Wait for a new layer to be added."""
        timeout = 20 # seconds
        count = 0
        while count < timeout:
            QtTest.QTest.qWait(1000) # wait 1000ms
            # parse message log for critical errors
#             if QSWATUtils._QSWATNAME in message_log:
#                 while message_log[QSWATUtils._QSWATNAME]:
#                     message, level = message_log[QSWATUtils._QSWATNAME].pop()
#                     self.assertNotEqual(level, QgsMessageLog.CRITICAL, \
#                                         'Critical error in message log:\n{}'.format(message))
            # check if any layers have been added
            if len(list(QgsProject.instance().mapLayers().values())) > numLayers:
                break
            count += 1
            
    def waitCountChanged(self, counter, num):
        """Wait for counter to be different from num."""
        timeout = 20 # seconds
        count = 0
        while count < timeout:
            QtTest.QTest.qWait(1000) # wait 1000ms
            if not counter() == num:
                break
            count += 1
            
    def checkHashes(self, hashes):
        """Check predefined hashes against project database tables.  Also checks gis_routing table."""
        with self.plugin._gv.db.conn as conn:
            self.assertTrue(conn, 'Failed to connect to project database {0}'.format(self.plugin._gv.db.dbFile))
            # useful in setting up tests: print hash but don't check
            for table in hashes.keys():
                print(table + ': ' +  self.plugin._gv.db.hashDbTable(conn, table))
#            return
            # end of setup
            for (table, val) in hashes.items():
                newval = self.plugin._gv.db.hashDbTable(conn, table)
                self.assertEqual(val, newval, 'Wrong hash value {0} for table {1}'.format(newval, table))
            errors, warnings = self.plugin._gv.db.checkRouting(conn)
            for error in errors:
                print(error)
            for warning in warnings:
                print(warning)
            self.assertEqual(len(errors), 0, 'One or more errors in gis_routing')
            
# this does not work, but why is mysterious
class Listener(QObject):
    """Listener for messages."""
    def __init__(self, o1, o2, o3):
        """Constructor."""
        QObject.__init__(self)
        o1.progress_signal.connect(self.listen_progress)
        o2.progress_signal.connect(self.listen_progress)
        o3.progress_signal.connect(self.listen_progress)
        
    @pyqtSlot(str)
    def listen_progress(self, msg):
        """Print msg."""
        print(msg + '\n')
            
if __name__ == '__main__':
#    import monkeytype
#    with monkeytype.trace():
    unittest.main()
