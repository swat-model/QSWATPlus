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

from PyQt5.QtCore import * # @UnusedWildImport 
from PyQt5.QtGui import * # @UnusedWildImport
from PyQt5.QtWidgets import * # @UnusedWildImport
from PyQt5 import QtTest
from qgis.core import * # @UnusedWildImport
from qgis.gui import * # @UnusedWildImport

import os.path
from osgeo import gdal
import shutil
import filecmp
import unittest
import atexit 
#from processing.core.Processing import Processing

from QSWATPlus import QSWATPlus
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
HashTable1['gis_channels'] = '3ba8ba06fcf681df31614baa59abd86e'
HashTable1['gis_points'] = '6a8773238af3410a0a2260bf62285811'
HashTable1['BASINSDATA'] = '3be2e009cccdcd91d07f28d18f9e7430'
HashTable1['LSUSDATA'] = 'e3585f152ca5d24a022adc0ef2e0552c'
HashTable1['HRUSDATA'] = 'ed89523f4fb7d04e9a2adf21a10cfb16'
HashTable1['WATERDATA'] = 'f9fb42dbd1ccf65df4c9185e6cb67868'
HashTable1['gis_elevationbands'] = '1a7d614a51eaa888311d51fad468f2a8'
HashTable1['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable1['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable1['gis_subbasins'] = 'bb4e63d390bf3cfb830a4faf77278ca4'
HashTable1['gis_lsus'] = '18db6950fe57aa652f4c295c1a6a11a9'
HashTable1['gis_hrus'] = '24512e6c398e0b15c9e1326fe5758dd4'
HashTable1['gis_routing'] = '313c2e1ced26c0636be6e2bf4f40d83c'
HashTable1['soils_sol'] = 'a212b2bb0012ae514f21a7cc186befc6'
HashTable1['soils_sol_layer'] = 'c1ad51d497c67e77de4d7e6cf08479f8'

# tables after adjusting parameters
HashTable1a = dict()
HashTable1a['gis_channels'] = '3052842790e2a6a214dd690948244026'
HashTable1a['gis_points'] = HashTable1['gis_points']
HashTable1a['BASINSDATA'] = HashTable1['BASINSDATA']
HashTable1a['LSUSDATA'] = HashTable1['LSUSDATA']
HashTable1a['HRUSDATA'] = HashTable1['HRUSDATA']
HashTable1a['WATERDATA'] = HashTable1['WATERDATA']
HashTable1a['gis_elevationbands'] = HashTable1['gis_elevationbands']
HashTable1a['gis_landexempt'] = HashTable1['gis_landexempt']
HashTable1a['gis_splithrus'] = HashTable1['gis_splithrus']
HashTable1a['gis_subbasins'] = '5b7e5026e3e5e2602675243d786899e2'
HashTable1a['gis_lsus'] = '50fb091e9d1b184ac0ccc9845d546a99'
HashTable1a['gis_hrus'] = 'a3bfb448bdbe63761b340e0b25da7e1e'
HashTable1a['gis_routing'] = HashTable1['gis_routing']
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
HashTable2['gis_channels'] = '4613ecfc9f48e0cfa38a04b8e24b2fbc'
HashTable2['gis_points'] = '930325873b4c7738755ed12f082c75a1'
HashTable2['BASINSDATA'] = '6751faf209b1c55e7f0f3033323b429c'
HashTable2['LSUSDATA'] = '6a9764d54a9cd3bcad76ede3584c34af'
HashTable2['HRUSDATA'] = 'c8f70c75bb49d2ab22c4a6b2398bc766'
HashTable2['WATERDATA'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable2['gis_elevationbands'] = 'e28ea4b5a684d867dc6c949393312a79'
HashTable2['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable2['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable2['gis_subbasins'] = 'e58f998dc4f0a931077bff802d0156e0'
HashTable2['gis_lsus'] = 'a79585cc3a4885a2d501170f8d5b9fd4'
HashTable2['gis_hrus'] = '64a578e488d58587f6821ef8737e9aa7'
HashTable2['gis_routing'] = '967f779f9d6fa605adbfe3a1d83781de'
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
HashTable3['BASINSDATA'] = 'de271648a6ddfc60339c29146053c546'
HashTable3['LSUSDATA'] = '32d6049075080f4077819de539d4b9e3'
HashTable3['HRUSDATA'] = '36e9a7fdf48e8d33ac80dd8a99bbffbd'
HashTable3['WATERDATA'] = '806ae46da6ec916fe1dc294d63ce439c'
HashTable3['gis_elevationbands'] = '7cb4deff34d859f54f9167b411613eeb'
HashTable3['gis_landexempt'] = '843f4dfbcb5fa16105cdd5b8108f3d5f'
HashTable3['gis_splithrus'] = '1221c315567ad59dbf8976f1c56c46b4'
# HashTable3['gis_subbasins'] = 'b97f84dd210b4aa89234225d92662f27'
HashTable3['gis_lsus'] = '38a0d309713522667f6b598f8c2cc08e'
# HashTable3['gis_hrus'] = 'f537ccd8d6180721090f0a8cb1bae2a2'
# HashTable3['gis_routing'] = '72cf3f50dacf291a169ca616eec1a8d4'
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
HashTable4['gis_channels'] = 'e71991edc172ef6e387b382bb8cac0c0'
HashTable4['gis_points'] = '8cdbd48802bc4a00c088f4a753522f59'
HashTable4['BASINSDATA'] = 'cf0617af5b3623fd4a72904633a80120'
HashTable4['LSUSDATA'] = '05c14c47e6ab65d99d722253fc5ab5be'
HashTable4['HRUSDATA'] = '84c79a10828faa29f75e3de4b01505b9'
HashTable4['WATERDATA'] = '8004dee65fef9d05b704f408277e0c99'
HashTable4['gis_elevationbands'] = '1a7d614a51eaa888311d51fad468f2a8'
HashTable4['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable4['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable4['gis_subbasins'] = '698db0065812ab9134863266a08b2382'
HashTable4['gis_lsus'] = '3905699bdfeedba1ac52b153a406dd21'
HashTable4['gis_hrus'] = 'e6166578fff313d9d0f94791e2befda7'
HashTable4['gis_routing'] = 'c12f213a168919d95660a5718467cb5b'
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
HashTable5['BASINSDATA'] = '10c0c1c0ef984046e4b59a67afa2eeda'
HashTable5['LSUSDATA'] = '1408a449f668e9c50fb099020ab4eb23'
HashTable5['HRUSDATA'] = 'd2938d60afcb861b2b947b5ba1cac024'
HashTable5['WATERDATA'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable5['gis_elevationbands'] = 'd0eb386ed677c19696a7eadbe8bc4b3a'
HashTable5['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable5['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
# HashTable5['gis_subbasins'] = '35545a9ad2419293b459d608d9725041'
HashTable5['gis_lsus'] = 'f1a82893447f46698f81aa96c79aef27'
# HashTable5['gis_hrus'] = '91e65917d5015e31c186be4e306abce4'
# HashTable5['gis_routing'] = '16ac5808a8d2abd6a5f497c5c215cfc4'
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
HashTable6['gis_channels'] = 'e1ff3bbaf1f695d9c65401318842ec30'
HashTable6['gis_points'] = '01e87111da52f8565dc6443947139557'
HashTable6['BASINSDATA'] = '2002404c42ae67eda0d7c6f77b7feb92'
HashTable6['LSUSDATA'] = '8001a3bd6b44bee5d731c84d6261fbba'
HashTable6['HRUSDATA'] = '276ad563cbe5a0b3619e95baa589aaed'
HashTable6['WATERDATA'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable6['gis_elevationbands'] = 'dda5bc5d2accf787c577a8b00c392ce7'
HashTable6['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable6['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable6['gis_subbasins'] = '98209c05f44a877f2ef76a4ffa700ff4'
HashTable6['gis_lsus'] = 'ff70c47e2b81f65c6c9a6eeac82786c9'
HashTable6['gis_hrus'] = '0a7d82506d98f0d8d750cc439ffc3494'
HashTable6['gis_routing'] = 'b27edb57b980f6c91c1cef9c3331d997'
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
HashTable7['gis_channels'] = '0e825cc3e47512a0dd168340281ed79d'
HashTable7['gis_points'] = 'c25837318dd34dbd45d94aa733701863'
HashTable7['BASINSDATA'] = 'c0d79c527aad714fbe567076bfd93883'
HashTable7['LSUSDATA'] = '42ce0947cd46ec3b5f2ba6abc1e1ba5f'
HashTable7['HRUSDATA'] = 'af386478e427b41279b6f04765303c7a'
HashTable7['WATERDATA'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable7['gis_elevationbands'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable7['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable7['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable7['gis_subbasins'] = '60180900b0689b52c8b45f31ab4ec34f'
HashTable7['gis_lsus'] = '00fe79ad358ef0789950f49dc6327a4a'
HashTable7['gis_hrus'] = 'bbf9ec5e2f06dd117b9585dcd866b971'
HashTable7['gis_routing'] = '6775e71224ffc728f2da292a5c0697c2'
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
HashTable8['gis_channels'] = 'caad28e20227914c51a8a130a6a13169'
HashTable8['gis_points'] = '3728417c73c135183dd8a5c42a948246'
HashTable8['BASINSDATA'] = '9df065eb0ef49770fc87376cdf6dae39'
HashTable8['LSUSDATA'] = '092b5c2a5deff442ac06e9fe4338eb03'
HashTable8['HRUSDATA'] = '879e3c9afb91687b5417a9063669193e'
HashTable8['WATERDATA'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable8['gis_elevationbands'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable8['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable8['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable8['gis_subbasins'] = '7ca11b71d8254d661cf06e57d4a074bf'
HashTable8['gis_lsus'] = '8f72ea360f0631a4846bf34a2825d051'
HashTable8['gis_hrus'] = '78c206e34feb3d0b6d17138c2c32d427'
HashTable8['gis_routing'] = '2474f7dbcd62b0257f63d1d8e9c80aeb'
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
HashTable9['gis_channels'] = 'd7b6c8aff1d050fcf19e1f6d92ae2b2e'
HashTable9['gis_points'] = '09aeba5fcf5322d5a24d6430aa205ae4'
HashTable9['BASINSDATA'] = '9df065eb0ef49770fc87376cdf6dae39'
HashTable9['LSUSDATA'] = '18fceaf2c6539069b77f450baf7b747a'
HashTable9['HRUSDATA'] = '879e3c9afb91687b5417a9063669193e'
HashTable9['WATERDATA'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable9['gis_elevationbands'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable9['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable9['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable9['gis_subbasins'] = '7ca11b71d8254d661cf06e57d4a074bf'
HashTable9['gis_lsus'] = '89d452b1997dc7abb011909bef7dcedc'
HashTable9['gis_hrus'] = '78c206e34feb3d0b6d17138c2c32d427'
HashTable9['gis_routing'] = 'a0e95e05c836607be74403878c16e5c3'
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
HashTable10['gis_channels'] = 'dead436376edbef68cd2b503a79f1965'
HashTable10['gis_points'] = '5d98fcd8423ac60d87975e2145c95b08'
HashTable10['BASINSDATA'] = '9df065eb0ef49770fc87376cdf6dae39'
HashTable10['LSUSDATA'] = '52f6f1f76d0ea7c892994464ad25cced'
HashTable10['HRUSDATA'] = '31e0a408a06b6a3b7f37b292b95702b6'
HashTable10['WATERDATA'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable10['gis_elevationbands'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable10['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable10['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable10['gis_subbasins'] = '7ca11b71d8254d661cf06e57d4a074bf'
HashTable10['gis_lsus'] = '37f9529763ecde9c241a8418211ebc60'
HashTable10['gis_hrus'] = '3e9e44ef6ecaba95ce0f771468612447'
HashTable10['gis_routing'] = 'ca6f1df6a1781f5c070d331f78680c91'
HashTable10['soils_sol'] = '992437fe26f6a1faa50b612528f31657'
HashTable10['soils_sol_layer'] = '3169334ef95be1d6af6428d672e3d069'
HashTable10['plants_plt'] = '2262f96863a7750b4dc53fb1fdd33d69'
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
HashTable11['gis_channels'] = 'ffe74a9ef57f7c49e90fd1790e842d69'
HashTable11['gis_points'] = '06ec94d2e00746c6d00c65e40f2e7a4c'
HashTable11['BASINSDATA'] = '79ad2690606d0a91e64f0217daf779b3'
HashTable11['LSUSDATA'] = '2b2706bab8b0337b53f932f32c28380e'
HashTable11['HRUSDATA'] = '5985b1d96231c8df9d363883e9c099aa'
HashTable11['WATERDATA'] = '5ab564771e1c72b25966197fd7a754a8'
HashTable11['LAKEBASINS'] = 'df2bdae9a7aefc1273406bc55f96e7c1'
HashTable11['LAKELINKS'] = '4cdaf1be9a4dacc166b5cdd2a045d532'
HashTable11['LAKESDATA'] = '62c7e5bb4e8e466fb019138d670f0c2f'
HashTable11['gis_elevationbands'] = 'c015d42982021c705249f2755571e58a'
HashTable11['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable11['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable11['gis_subbasins'] = '6df9912b3dee77088d6ab2dab986e7d6'
HashTable11['gis_lsus'] = 'e09b645a65864996e87c9a8e33ba58d2'
HashTable11['gis_hrus'] = '1e75f7e24c21b6a69be272a8103ecf61'
HashTable11['gis_routing'] = '2e12d102590882f28570e7bb2002baae'
HashTable11['gis_water'] = 'f47b9c5d93eaca32c9eb7c8dd0c61335'
HashTable11['soils_sol'] = '635a0c1078f013bc8a3be1307e70581c'
HashTable11['soils_sol_layer'] = 'fc3d820a0fa620cc8776e5fbd811e0fc'
HashTable11['plants_plt'] = '2262f96863a7750b4dc53fb1fdd33d69'
HashTable11['urban_urb'] = '94ab13b7ddfd02b2aedde8912744ac17'

#===============================================================================
# Test 12:
# - MPI with 6 processes; 
# - existing;
# - lake;  
# - 1% channel merge; 
# - target 500 HRUs.
#===============================================================================

HashTable12 = dict()
HashTable12['gis_channels'] = '5d6a1a8e64cc8dc517444e096ae5ec3a'
HashTable12['gis_points'] = 'd95fe13f3b63a06406ca7c5a11fed92f'
HashTable12['BASINSDATA'] = 'bc6f08e902303c13c1dc00983fb42b8f'
HashTable12['LSUSDATA'] = 'ea97fa2192e614a74cca920995393419'
HashTable12['HRUSDATA'] = '388990cceeb0ce948659c9750e526e65'
HashTable12['WATERDATA'] = '28e52b7e4fa21576e4e120e745c49c98'
HashTable12['LAKEBASINS'] = 'e7688062747109e112d2222049e80839'
HashTable12['LAKELINKS'] = 'd553336f474de1d5ec5f41d1f15aefb8'
HashTable12['LAKESDATA'] = 'a6f60edb2e40d78cfb6413c421da0d1e'
HashTable12['gis_elevationbands'] = 'c015d42982021c705249f2755571e58a'
HashTable12['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable12['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable12['gis_subbasins'] = '8e7d8530532be78a0a98e5c12c34da11'
HashTable12['gis_lsus'] = '682d9cce2a84185c51e354650093ab23'
HashTable12['gis_hrus'] = 'c68060e84357e77a9ce5a575aebf1263'
HashTable12['gis_routing'] = '2cc8db7851689eed16353dfd00b4997d'
HashTable12['gis_water'] = 'b7853497a7f84dbf5d18c1fd436d5b8f'
HashTable12['soils_sol'] = '635a0c1078f013bc8a3be1307e70581c'
HashTable12['soils_sol_layer'] = 'fc3d820a0fa620cc8776e5fbd811e0fc'
HashTable12['plants_plt'] = '2262f96863a7750b4dc53fb1fdd33d69'
HashTable12['urban_urb'] = '94ab13b7ddfd02b2aedde8912744ac17'

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
HashTable13['gis_channels'] = '07150baec1ebef83435fdbbb2e004f15'
HashTable13['gis_points'] = '4910843e5715431ab4af0e1709d3625d'
HashTable13['BASINSDATA'] = 'c994fa17f9415f6b7607e327474eeca1'
HashTable13['LSUSDATA'] = '197efe494967d490f398670ff079c4d4'
HashTable13['HRUSDATA'] = '43c514366f3de68ce8c7ad555d5a0d23'
HashTable13['WATERDATA'] = '94938c0f5dd92178216d68943f96bc07'
HashTable13['LAKEBASINS'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable13['LAKELINKS'] = 'dc0afa5ece57d262954bbc269b4a2e62'
HashTable13['LAKESDATA'] = 'd4b1e37c676898fb9039b4885b050b0c'
HashTable13['gis_elevationbands'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable13['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable13['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable13['gis_subbasins'] = 'bd384dbea8b64c9d3bd09d31587548bd'
HashTable13['gis_lsus'] = '1ae7c75ce5bad016c731653ce53b8ce9'
HashTable13['gis_hrus'] = 'e3fc5953e076ac64818a7946fa1a5712'
HashTable13['gis_routing'] = '45e35318acf0317568893e0218963d31'
HashTable13['gis_water'] = 'b8b81bd3d843586e40ed58e1daa51ac9'
HashTable13['soils_sol'] = '1c13df70d2d40f74b03c7d9434bc1832'
HashTable13['soils_sol_layer'] = 'ffdf99f5cc1e3617e5666c479041fa7d'
HashTable13['plants_plt'] = '2262f96863a7750b4dc53fb1fdd33d69'
HashTable13['urban_urb'] = '94ab13b7ddfd02b2aedde8912744ac17'

#===============================================================================
# Test 14:
# - MPI with 10 processes; 
# - existing grid
# - stream drainage
# - lake; 
# - dominant HRUs
#===============================================================================

HashTable14 = dict()
HashTable14['gis_channels'] = 'fe3cf1b18b5ac4a907987ff856a3802e'
HashTable14['gis_points'] = '41d1d42c929ebc63270f92bfc575fb35'
HashTable14['BASINSDATA'] = '52eca1167cf45ebeb0ba5f4624a91e4d'
HashTable14['LSUSDATA'] = '757bc4b02f2c236d3df14dbbb486a0ae'
HashTable14['HRUSDATA'] = '646674e7180a1f9319594db295820174'
HashTable14['WATERDATA'] = 'f0c5ea422de917ca8aff54a5b4d58db3'
HashTable14['LAKEBASINS'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable14['LAKELINKS'] = '57fcaa6f8edafac3f5bd33bae7dbdfbe'
HashTable14['LAKESDATA'] = 'd4b1e37c676898fb9039b4885b050b0c'
HashTable14['gis_elevationbands'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable14['gis_landexempt'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable14['gis_splithrus'] = 'd41d8cd98f00b204e9800998ecf8427e'
HashTable14['gis_subbasins'] = '76e6ef6fca93b74b33ccf718386c2e86'
HashTable14['gis_lsus'] = '0aae520a3ec4b54605dc35135bb6e664'
HashTable14['gis_hrus'] = '784845a7bcd712176780b9659fc0d1d7'
HashTable14['gis_routing'] = '66c19913c0e2e1fa7360bd93c8967664'
HashTable14['gis_water'] = '030ba1158cea9fa3788f6b2bc17bbd45'
HashTable14['soils_sol'] = '1c13df70d2d40f74b03c7d9434bc1832'
HashTable14['soils_sol_layer'] = 'ffdf99f5cc1e3617e5666c479041fa7d'
HashTable14['plants_plt'] = '2262f96863a7750b4dc53fb1fdd33d69'
HashTable14['urban_urb'] = '94ab13b7ddfd02b2aedde8912744ac17'

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
        # SRS path is not set properly.
        self.assertTrue(os.path.exists(QgsApplication.srsDatabaseFilePath()), \
                         'Need to copy resources folder to make directory {0} exist, eg copy OSGeo4W/apps/qgis/resources to OSGeo4W'.format(QgsApplication.srsDatabaseFilePath()))
        ## QSWAT plugin
        self.plugin = QSWATPlus.QSWATPlus(iface)
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
        self.checkHashes(HashTable1)
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
        self.checkHashes(HashTable1a)
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
        self.delin._dlg.numProcesses.setValue(12)
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
        self.checkHashes(HashTable2)
        self.assertTrue(self.dlg.editButton.isEnabled(), 'SWAT Editor button not enabled')
        self.plugin.finish()
        
    def test03(self):
        """No MPI; stream threshold 14400 cells; channel threshold 1440 cells; single outlet; 
        merge subbasins; split and exempts; target by area 100; rerun HRU creation."""
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
        hrudlg.targetSlider.setValue(100)
        self.assertTrue(hrudlg.createButton.isEnabled(), 'Create button not enabled')
        QtTest.QTest.mouseClick(hrudlg.createButton, Qt.LeftButton)
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.textDir, Parameters._HRUSREPORT)))
        self.assertTrue(self.dlg.reportsBox.findText(Parameters._HRUSITEM) >= 0, \
                        'HRUs report not accessible from main form')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.shapesDir, 'lsus2.shp')), 'Actual LSUs shapefile not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'rivs.shp')), 'Reaches results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'subs.shp')), 'Watershed results template file not created.')
        self.assertTrue(os.path.exists(os.path.join(self.plugin._gv.resultsDir, 'lsus.shp')), 'LSUs results template file not created.')
        self.checkHashes(HashTable3)
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
        self.assertTrue(hrudlg.targetSlider.value() == 100, 'Area slider set to wrong value: {0}'.format(hrudlg.targetSlider.value()))
        self.assertTrue(hrudlg.createButton.isEnabled(), 'Create button not enabled')
        QtTest.QTest.mouseClick(hrudlg.createButton, Qt.LeftButton)
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
        self.checkHashes(HashTable4)
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
        self.checkHashes(HashTable5)
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
        self.delin._dlg.numProcesses.setValue(12)
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
        self.checkHashes(HashTable6)
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
        self.delin._dlg.numProcesses.setValue(12)
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
        self.assertTrue(fullHrusLayer.layer().featureCount() == 39418, 'Unexpected number of full HRUs: {0}'.format(fullHrusLayer.layer().featureCount()))
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
        self.checkHashes(HashTable7)
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
        self.checkHashes(HashTable8)
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
        self.checkHashes(HashTable9)
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
        self.checkHashes(HashTable10)
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
        self.delin._dlg.numProcesses.setValue(6)
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
        self.checkHashes(HashTable11)
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
        channelFile = os.path.join(self.dataDir, 'ravn_demchannel1.shp')
        numLayers = len(QgsProject.instance().mapLayers().values())
        channelLayer, loaded = QSWATUtils.getLayerByFilename(self.root.findLayers(), channelFile, FileTypes._CHANNELS, self.plugin._gv, demLayer, QSWATUtils._WATERSHED_GROUP_NAME)
        self.waitLayerAdded(numLayers)
        self.assertTrue(channelLayer and loaded, 'Failed to load channels shapefile'.format(channelFile))
        self.delin._dlg.selectStreams.setText(channelFile)
        self.plugin._gv.channelFile = channelFile
        self.delin._dlg.numProcesses.setValue(6)
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
        self.checkHashes(HashTable12)
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
        self.delin._dlg.numProcesses.setValue(8)
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
        self.checkHashes(HashTable13)
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
        self.delin._dlg.numProcesses.setValue(10)
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
        self.checkHashes(HashTable14)
        self.assertTrue(self.dlg.editButton.isEnabled(), 'SWAT Editor button not enabled')
        self.plugin.finish()
        
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
