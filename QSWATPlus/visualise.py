# -*- coding: utf-8 -*-
'''
/***************************************************************************
 QSWATPlus
                                 A QGIS plugin
 Create SWATPlus inputs
                              -------------------
        begin                : 2014-07-18
        copyright            : (C) 2014 by Chris George
        email                : cgeorge@mcmaster.ca
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
'''
# Import the PyQt and QGIS libraries
from PyQt5.QtCore import *  # @UnusedWildImport
from PyQt5.QtGui import *  # @UnusedWildImport
from PyQt5.QtWidgets import * # @UnusedWildImport
from PyQt5.QtXml import * # @UnusedWildImport
from qgis.core import * # @UnusedWildImport
from qgis.gui import * # @UnusedWildImport
import os
# import random
import numpy
import sqlite3
import subprocess
from osgeo.gdalconst import * # @UnusedWildImport
import glob
from datetime import date
# from PIL import Image
import math
import csv
import traceback

# Import the code for the dialog
from .visualisedialog import VisualiseDialog
from .QSWATUtils import QSWATUtils, FileTypes
from .QSWATTopology import QSWATTopology
from .swatgraph import SWATGraph
from .parameters import Parameters
from .jenks import jenks  # @UnresolvedImport
# from .images2gif import writeGif
from . import imageio

class Visualise(QObject):
    """Support visualisation of SWAT outputs, using data in SWAT output database."""
    
    _TOTALS = 'Totals'
    _DAILYMEANS = 'Daily means'
    _MONTHLYMEANS = 'Monthly means'
    _ANNUALMEANS = 'Annual means'
    _MAXIMA = 'Maxima'
    _MINIMA = 'Minima'
    _AREA = 'AREAkm2'
    _MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    _NORTHARROW = 'apps/qgis/svg/wind_roses/WindRose_01.svg'
    
    def __init__(self, gv):
        """Initialise class variables."""
        QObject.__init__(self)
        self._gv = gv
        self._dlg = VisualiseDialog()
        self._dlg.setWindowFlags(self._dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint & Qt.WindowMinimizeButtonHint)
        self._dlg.move(self._gv.visualisePos)
        ## variables found in various tables that do not contain values used in results
        # note we also exclude variables that do not have typr REAL
        self.ignoredVars = ['id', 'output_type_id', 'output_interval_id', 'time', 'year', 'unit', 'plantnm', 'ob_typ', 
                            'props', 'type', 'obj_type', 'hyd_typ', 'resnum', 'hru', 'area', 'vol']
        ## tables not suitable for visualisation
        self.ignoredTables = ['crop_yld_', 'deposition_', 'hydin_', 'hydout_', 'ru_', 'basin_psc_']
        ## tables only included when plotting
        self.plotOnlyTables = ['reservoir_', 'wetland_']
        ## current scenario
        self.scenario = ''
        ## Current output database
        self.db = ''
        ## Current connection
        self.conn = None
        ## Current table
        self.table = ''
        ## Number of subbasins in current watershed TODO:
        self.numSubbasins = 0
        ## number of landscape units in current watershed TODO:
        self.numLSUs = 0
        ## number of HURUs in current watershed TODO:
        self.numHRUs = 0
#         ## map SWATBasin -> SWATBasin -> SWATChannel -> LSUId -> hruNum-set
#         self.topology = None 
#         ## map SWATBasin -> SWATChannel -> LSUId -> reservoir number
#         self.reservoirs = None 
#         ## map SWATBasin -> SWATChannel -> LSUId -> pond number
#         self.ponds = None
        ## Data read from db table
        #
        # data takes the form
        # layerId -> gis_id -> variable_name -> year -> time -> value
        self.staticData = dict()
        ## Data to write to shapefile
        #
        # takes the form subbasin number -> variable_name -> value for static use
        # takes the form layerId -> date -> subbasin number -> val for animation
        # where date is YYYY or YYYYMM or YYYYDDD according to period of input
        self.resultsData = dict()
        ## Areas of subbasins (drainage area for reaches)
        self.areas = dict()
#         ## Flag to indicate areas available
#         self.hasAreas = False
        ## true if output is daily
        self.isDaily = False
        ## true if output is monthly
        self.isMonthly = False
        ## true if output is annual
        self.isAnnual = False
        ## true if output is average annual
        self.isAA = False
        ## julian start day
        self.julianStartDay = 0
        ## julian finish day
        self.julianFinishDay = 0
        ## start year of period (of output: includes any nyskip)
        self.startYear = 0
        ## start month of period
        self.startMonth = 0
        ## start day of period
        self.startDay = 0
        ## finish year of period
        self.finishYear = 0
        ## finish month of period
        self.finishMonth = 0
        ## finish day of period
        self.finishDay = 0
        ## length of simulation in days
        self.periodDays = 0
        ## length of simulation in months (may be fractional)
        self.periodMonths = 0
        ## length of simulation in years (may be fractional)
        self.periodYears = 0
        ## print interval
        self.interval = 1 # default value
        ## map canvas title
        self.mapTitle = None
        ## flag to decide if we need to create a new results file:
        # changes to summary method or result variable don't need a new file
        self.resultsFileUpToDate = False
        ## flag to decide if we need to reread data because period has changed
        self.periodsUpToDate = False
        ## current streams results layer
        self.rivResultsLayer = None
        ## current subbasins results layer
        self.subResultsLayer = None
        ## current LSUs results layer
        self.lsuResultsLayer = None
        ## current HRUs results layer
        self.hruResultsLayer = None
        ## current resultsFile
        self.resultsFile = ''
        ## flag to indicate if summary has changed since last write to results file
        self.summaryChanged = True
        ## current animation layer
        self.animateLayer = None
        ## current animation file (a temporary file)
        self.animateFile = ''
        ## map layerId -> index of animation variable in results file
        self.animateIndexes = dict()
        ## all values involved in animation, for calculating Jenks breaks
        self.allAnimateVals = []
        ## timer used to run animation
        self.animateTimer = QTimer()
        ## flag to indicate if animation running
        self.animating = False
        ## flag to indicate if animation paused
        self.animationPaused = False
        ## animation variable
        self.animateVar = ''
        ## flag to indicate if capturing video
        self.capturing = False
        ## base filename of capture stills
        self.stillFileBase = ''
        ## name of latest video file
        self.videoFile = ''
        ## number of next still frame
        self.currentStillNumber = 0
        ## flag to indicate if stream renderer being changed by code
        self.internalChangeToRivRenderer = False
        ## flag to indicate if subbasin renderer being changed by code
        self.internalChangeToSubRenderer = False
        ## flag to indicate if LSU renderer being changed by code
        self.internalChangeToLSURenderer = False
        ## flag to indicate if HRU renderer being changed by code
        self.internalChangeToHRURenderer = False
        ## flag to indicate if colours for rendering streams should be inherited from existing results layer
        self.keepRivColours = False
        ## flag to indicate if colours for rendering subbasins should be inherited from existing results layer
        self.keepSubColours = False
        ## flag to indicate if colours for rendering LSUs should be inherited from existing results layer
        self.keepLSUColours = False
        ## flag to indicate if colours for rendering HRUs should be inherited from existing results layer
        self.keepHRUColours = False
        ## flag for HRU results for current scenario: 0 for limited HRUs or multiple but no hru table; 1 for single HRUs; 2 for multiple
        self.HRUsSetting = 0
        ## map sub -> LSU -> HRU numbers
        self.hruNums = dict()
        ## file with observed data for plotting
        self.observedFileName = ''
        ## project title
        self.title = ''
        ## count to keep layout titles unique
        self.compositionCount = 0
        ## animation layout
        self.animationLayout = None
        ## animation template DOM document
        self.animationDOM = None
        ## animation template file
        self.animationTemplate = ''
        ## flag to show when user has perhaps changed the animation template
        self.animationTemplateDirty = False
        # empty animation and png directories
        self.clearAnimationDir()
        self.clearPngDir()
        
    def init(self):
        """Initialise the visualise form."""
        self.setSummary()
        self.fillScenarios()
        self._dlg.scenariosCombo.activated.connect(self.setupDb)
        self._dlg.scenariosCombo.setCurrentIndex(self._dlg.scenariosCombo.findText('Default'))
        if self.db == '':
            self.setupDb()
        self._dlg.outputCombo.activated.connect(self.setVariables)
        self._dlg.summaryCombo.activated.connect(self.changeSummary)
        self._dlg.addButton.clicked.connect(self.addClick)
        self._dlg.allButton.clicked.connect(self.allClick)
        self._dlg.delButton.clicked.connect(self.delClick)
        self._dlg.clearButton.clicked.connect(self.clearClick)
        self._dlg.resultsFileButton.clicked.connect(self.setResultsFile)
        self._dlg.tabWidget.setCurrentIndex(0)
        self._dlg.tabWidget.currentChanged.connect(self.modeChange)
        self._dlg.saveButton.clicked.connect(self.makeResults)
        self._dlg.printButton.clicked.connect(self.printResults)
        self._dlg.canvasAnimation.clicked.connect(self.changeAnimationMode)
        self._dlg.printAnimation.clicked.connect(self.changeAnimationMode)
        self.changeAnimationMode()
        self._dlg.animationVariableCombo.activated.connect(self.setupAnimateLayer)
        self._dlg.slider.valueChanged.connect(self.changeAnimate)
        self._dlg.slider.sliderPressed.connect(self.pressSlider)
        self._dlg.playCommand.clicked.connect(self.doPlay)
        self._dlg.pauseCommand.clicked.connect(self.doPause)
        self._dlg.rewindCommand.clicked.connect(self.doRewind)
        self._dlg.recordButton.clicked.connect(self.record)
        self._dlg.recordButton.setStyleSheet("background-color: green; border: none;")
        self._dlg.playButton.clicked.connect(self.playRecording)
        self._dlg.spinBox.valueChanged.connect(self.changeSpeed)
        self.animateTimer.timeout.connect(self.doStep)
        self.setupTable()
        self._dlg.unitPlot.activated.connect(self.plotSetUnit)
        self._dlg.unitEdit.textEdited.connect(self.plotEditUnit)
        self._dlg.unitEdit.returnPressed.connect(self.plotEditUnit)
        self._dlg.variablePlot.activated.connect(self.plotSetVar)
        self._dlg.addPlot.clicked.connect(self.doAddPlot)
        self._dlg.deletePlot.clicked.connect(self.doDelPlot)
        self._dlg.copyPlot.clicked.connect(self.doCopyPlot)
        self._dlg.upPlot.clicked.connect(self.doUpPlot)
        self._dlg.downPlot.clicked.connect(self.doDownPlot)
        self._dlg.observedFileButton.clicked.connect(self.setObservedFile)
        self._dlg.addObserved.clicked.connect(self.addObervedPlot)
        self._dlg.plotButton.clicked.connect(self.writePlotData)
        self._dlg.closeButton.clicked.connect(self.doClose)
        self._dlg.destroyed.connect(self.doClose)
        proj = QgsProject.instance()
        root = proj.layerTreeRoot()
        self.setBackgroundLayers(root)
        leftShortCut = QShortcut(QKeySequence(Qt.Key_Left), self._dlg)
        rightShortCut = QShortcut(QKeySequence(Qt.Key_Right), self._dlg)
        leftShortCut.activated.connect(self.animateStepLeft)
        rightShortCut.activated.connect(self.animateStepRight)
        self.title = proj.title()
        observedFileName, found = proj.readEntry(self.title, 'observed/observedFile', '')
        if found:
            self.observedFileName = observedFileName
            self._dlg.observedFileEdit.setText(observedFileName)
        animationGroup = root.findGroup(QSWATUtils._ANIMATION_GROUP_NAME)
        animationGroup.visibilityChanged.connect(self.setAnimateLayer)
        animationGroup.removedChildren.connect(self.setAnimateLayer)
        animationGroup.addedChildren.connect(self.setAnimateLayer)
        # in case restart with existing animation layers
        self.setAnimateLayer()
            
    def run(self):
        """Do visualisation."""
        self.init()
        self._dlg.show()
        self._dlg.exec_()
        self._gv.visualisePos = self._dlg.pos()
        
    def fillScenarios(self):
        """Put scenarios in scenariosCombo and months in start and finish month combos."""
        pattern = QSWATUtils.join(self._gv.scenariosDir, '*')
        for direc in glob.iglob(pattern):
            db = QSWATUtils.join(QSWATUtils.join(direc, Parameters._RESULTS), Parameters._OUTPUTDB)
            if os.path.exists(db):
                self._dlg.scenariosCombo.addItem(os.path.split(direc)[1])
        for month in Visualise._MONTHS:
            m = QSWATUtils.trans(month)
            self._dlg.startMonth.addItem(m)
            self._dlg.finishMonth.addItem(m)
        for i in range(31):
            self._dlg.startDay.addItem(str(i+1))
            self._dlg.finishDay.addItem(str(i+1))
            
    def setBackgroundLayers(self, root):
        """Reduce visible layers to channels, actual LSUs and subbasins by making all others not visible.
        Leave Results group in case we already have some layers there."""
        slopeGroup = root.findGroup(QSWATUtils._SLOPE_GROUP_NAME)
        if slopeGroup is not None:
            slopeGroup.setItemVisibilityCheckedRecursive(False)
        soilGroup = root.findGroup(QSWATUtils._SOIL_GROUP_NAME)
        if soilGroup is not None:
            soilGroup.setItemVisibilityCheckedRecursive(False)
        watershedLayers = QSWATUtils.getLayersInGroup(QSWATUtils._WATERSHED_GROUP_NAME, root)
        if self._gv.useGridModel:
            # make grid and grid streams visible
            keepVisible = lambda n: n.startswith(QSWATUtils._GRIDSTREAMSLEGEND) or \
                                    n.startswith(QSWATUtils._GRIDLEGEND)
        else:  
            # make subbasins, channels and actual LSUs visible
            keepVisible = lambda n: n.startswith(QSWATUtils._SUBBASINSLEGEND) or \
                                    n.startswith(QSWATUtils._CHANNELSLEGEND) or \
                                    n.startswith(QSWATUtils._ACTLSUSLEGEND)
        for layer in watershedLayers:
            layer.setItemVisibilityChecked(keepVisible(layer.name()))
    
    def setupDb(self):
        """Set current database and connection to it; put table names in outputCombo."""
        self.resultsFileUpToDate = False
        self.scenario = self._dlg.scenariosCombo.currentText()
        self.setConnection(self.scenario)
        scenDir = QSWATUtils.join(self._gv.scenariosDir, self.scenario)
        txtInOutDir = QSWATUtils.join(scenDir, Parameters._TXTINOUT)
        self.db = QSWATUtils.join(QSWATUtils.join(scenDir, Parameters._RESULTS), Parameters._OUTPUTDB)
        self.conn =  sqlite3.connect(self.db)
        if self.conn is None:
            QSWATUtils.error('Failed to connect to output database {0}'.format(self.db), self.isBatch)
        else:
            self.conn.row_factory = sqlite3.Row
        simFile = QSWATUtils.join(txtInOutDir, Parameters._SIM)
        if not os.path.exists(simFile):
            QSWATUtils.error('Cannot find simulation file {0}'.format(simFile), self._gv.isBatch)
            return
        prtFile = QSWATUtils.join(txtInOutDir, Parameters._PRT)
        if not os.path.exists(prtFile):
            QSWATUtils.error('Cannot find print file {0}'.format(prtFile), self._gv.isBatch)
            return
        self.readPrt(prtFile, simFile)
#         self.topology, self.reservoirs, self.ponds = self._gv.db.createTopology()
        self.populateOutputTables()

    def populateOutputTables(self):
        """Add daily, monthly and annual output tables to output combo"""
        self._dlg.outputCombo.clear()
        self._dlg.outputCombo.addItem('')
        tables = []
        # if we are plotting and have at least one non-observed row, only include tables of same frequency
        isPlot = self._dlg.tabWidget.currentIndex() == 2
        plotTable = self.getPlotTable() if isPlot else ''
        keepDaily = plotTable == '' or Visualise.tableIsDaily(plotTable)
        if keepDaily:
            self.addTablesByTerminator(tables, '_day')
        keepMonthly = plotTable == '' or Visualise.tableIsMonthly(plotTable)
        if keepMonthly:
            self.addTablesByTerminator(tables, '_mon')
        keepYearly = plotTable == '' or Visualise.tableIsYearly(plotTable)
        if keepYearly:
            self.addTablesByTerminator(tables, '_yr')
        if self._dlg.tabWidget.currentIndex() == 0:  # static
            self.addTablesByTerminator(tables, '_aa')
        for table in tables:
            self._dlg.outputCombo.addItem(table)
        self._dlg.outputCombo.setCurrentIndex(0)
        self.table = ''
        self.plotSetUnit()
        self._dlg.variablePlot.clear()
        self._dlg.variablePlot.addItem('')
        self.updateCurrentPlotRow(0)
        
    def setConnection(self, scenario):
        """Set connection to scenario output database."""
        scenDir = QSWATUtils.join(self._gv.scenariosDir, scenario)
        outDir = QSWATUtils.join(scenDir, Parameters._RESULTS)
        self.db = QSWATUtils.join(outDir, Parameters._OUTPUTDB)
        self.conn =  sqlite3.connect(self.db)
        if self.conn is None:
            QSWATUtils.error('Failed to connect to output database {0}'.format(self.db), self.isBatch)
        else:
            #self.conn.isolation_level = None # means autocommit
            self.conn.row_factory = sqlite3.Row
        
    def addTablesByTerminator(self, tables, terminator):
        """Add to tables table names terminating with terminator, provided they have data.
        
        The names added are sorted."""
        sql = 'SELECT name FROM sqlite_master WHERE TYPE="table"'
        tempTables = []
        for row in self.conn.execute(sql):
            table = row[0]
            if self._dlg.tabWidget.currentIndex() != 2 and table.startswith('basin_'):
                continue
            if table.endswith(terminator):
                ignore = False
                # check table is not ignored
                for ignored in self.ignoredTables:
                    if table.startswith(ignored):
                        ignore = True
                        break
                if ignore:
                    continue
                for plotOnly in self.plotOnlyTables:
                    if table.startswith(plotOnly):
                        ignore = self._dlg.tabWidget.currentIndex() != 2
                        break
                if ignore:
                    continue
                # check table has data and a gis_id
                sql2 = self._gv.db.sqlSelect(table, '*', '', '')
                row2 = self.conn.execute(sql2).fetchone()
                if row2 is not None and 'gis_id' in row2.keys():
                    tempTables.append(table)
        tables.extend(sorted(tempTables))    
        
    def restrictOutputTablesByTerminator(self, terminator):
        """RestrictOutputTables combo to those ending with terminator."""
        toDelete = []
        for indx in range(self._dlg.outputCombo.count()):
            txt = self._dlg.outputCombo.itemText(indx)
            if txt == '' or txt.endswith(terminator):
                continue
            toDelete.append(indx)
        # remove from bottom as indexes affected by removal
        for indx in reversed(toDelete):
            self._dlg.outputCombo.removeItem(indx)
        
    def setupTable(self):
        """Initialise the plot table."""
        self._dlg.tableWidget.setHorizontalHeaderLabels(['Scenario', 'Table', 'Unit', 'Variable'])
        self._dlg.tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._dlg.tableWidget.setSelectionMode(QAbstractItemView.SingleSelection)
        self._dlg.tableWidget.setColumnWidth(0, 100)
        self._dlg.tableWidget.setColumnWidth(1, 100)
        self._dlg.tableWidget.setColumnWidth(2, 45)
        self._dlg.tableWidget.setColumnWidth(4, 90)
        
    def setVariables(self):
        """Fill variables combos from selected table; set default results file name."""
        table = self._dlg.outputCombo.currentText()
        if self.table == table:
            # no change: do nothing
            return
        self.table = table 
        if self.table == '':
            return
        if not self.conn:
            return
        self.isDaily, self.isMonthly, self.isAnnual, self.isAA = Visualise.tableIsDailyMonthlyOrAnnual(self.table)
        scenDir = QSWATUtils.join(self._gv.scenariosDir, self.scenario)
        outDir = QSWATUtils.join(scenDir, Parameters._RESULTS)
        outFile = QSWATUtils.join(outDir, self.table + 'results.shp')
        self._dlg.resultsFileEdit.setText(outFile)
        self.resultsFileUpToDate = False
        self._dlg.summaryBox.setVisible(not self.isAA)
        # add gis id numbers to unitPlot combo
        self.setGisIdPlot()
        self._dlg.variableCombo.clear()
        self._dlg.animationVariableCombo.clear()
        self._dlg.animationVariableCombo.addItem('')
        self._dlg.variablePlot.clear()
        self._dlg.variablePlot.addItem('')
        self._dlg.variableList.clear()
        sql = 'PRAGMA TABLE_INFO({0})'.format(table)
        for row in self.conn.execute(sql):
            var = row[1]
            varType = row[2]
            # only include fields of type REAL
            if varType == 'REAL' and not var in self.ignoredVars:
                self._dlg.variableCombo.addItem(var)
                self._dlg.animationVariableCombo.addItem(var)
                self._dlg.variablePlot.addItem(var)
        self.updateCurrentPlotRow(1)
                
    def plotting(self):
        """Return true if plot tab open and plot table has a selected row."""
        if self._dlg.tabWidget.currentIndex() != 2:
            return False
        indexes = self._dlg.tableWidget.selectedIndexes()
        return indexes is not None and len(indexes) > 0
                
    def setSummary(self):
        """Fill summary combo."""
        self._dlg.summaryCombo.clear()
        self._dlg.summaryCombo.addItem(Visualise._TOTALS)
        self._dlg.summaryCombo.addItem(Visualise._DAILYMEANS)
        self._dlg.summaryCombo.addItem(Visualise._MONTHLYMEANS)
        self._dlg.summaryCombo.addItem(Visualise._ANNUALMEANS)
        self._dlg.summaryCombo.addItem(Visualise._MAXIMA)
        self._dlg.summaryCombo.addItem(Visualise._MINIMA)
        
    def readSim(self, simFile):
        """Read time.sim file.  This just sets outer limits for start and end dates.  Return true if no errors."""
        try:
            with open(simFile, 'r') as sim:
                # skip first line
                sim.readline()
                # skip headings
                sim.readline()
                dates = sim.readline().split()
                self.julianStartDay = int(dates[0])
                # interpret 0 as 1
                if self.julianStartDay == 0:
                    self.julianStartDay = 1
                self.startYear = int(dates[1])
                self.julianFinishDay = int(dates[2])
                self.finishYear = int(dates[3])
                # interpret Julian 0 as last day of year
                if self.julianFinishDay == 0:
                    self.julianFinishDay = 366 if self.isLeap(self.finishYear) else 365
                # STEP can be ignored - does not affect outputs
                return True
        except Exception:
            QSWATUtils.exceptionError('Failed to read {0}'.format(simFile), self._gv.isBatch)
            return False
                    

    def readPrt(self, prtFile, simFile):
        """Read print.prt file to get print period and print interval.  Return true if no errors."""
        # first read time.sim to reset start/finish dates to simulation
        if not self.readSim(simFile):
            return False
        try:
            with open(prtFile, 'r') as prt:
                # skip first line
                prt.readline()
                # skip headings
                prt.readline()
                dates = prt.readline().split()
                nyskip = int(dates[0])
                self.startYear += nyskip
                startDay = int(dates[1])
                if startDay > 0 and startDay >  self.julianStartDay:
                    self.julianStartDay = startDay
                finishDay = int(dates[3])
                if finishDay > 0 and finishDay < self.julianFinishDay:
                    self.julianFinishDay = finishDay
                startYear = int(dates[2])
                if startYear > 0 and startYear > self.startYear:
                    self.startYear  = startYear
                finishYear = int(dates[4])
                if finishYear > 0 and finishYear < self.finishYear:
                    self.finishYear = finishYear
                # make sure finish day matches the year if set to year end
                if self.julianFinishDay in {365, 366}:
                    self.julianFinishDay = 366 if self.isLeap(self.finishYear) else 365
                self.interval = int(dates[5])
                if self.interval == 0:
                    self.interval = 1 # defensive coding
            self.setDates()
            return True
        except Exception:
            QSWATUtils.exceptionError('Failed to read {0}: {1}'.format(prtFile), self._gv.isBatch)
            return False
        
    def setDates(self):
        """Set requested start and finish dates to smaller period of length of scenario and requested dates (if any)."""
        startDate = self.julianToDate(self.julianStartDay, self.startYear)
        finishDate = self.julianToDate(self.julianFinishDay, self.finishYear)
        requestedStartDate = self.readStartDate()
        if requestedStartDate is None:
            self.setStartDate(startDate)
        else:
            if requestedStartDate < startDate:
                QSWATUtils.information('Chosen period starts earlier than scenario {0} period: changing chosen start'.format(self.scenario), self._gv.isBatch)
                self.setStartDate(startDate)
        requestedFinishDate = self.readFinishDate()
        if requestedFinishDate is None:
            self.setFinishDate(finishDate)
        else:
            if requestedFinishDate > finishDate:
                QSWATUtils.information('Chosen period finishes than scenario {0} period: changing chosen finish'.format(self.scenario), self._gv.isBatch)
                self.setFinishDate(finishDate)
        
    def setPeriods(self):
        """Define period of current scenario in days, months and years.  Return true if OK."""
        requestedStartDate = self.readStartDate()
        requestedFinishDate = self.readFinishDate()
        if requestedStartDate is None or requestedFinishDate is None:
            QSWATUtils.error('Cannot read chosen period', self._gv.isBatch)
            return False
        if requestedFinishDate <= requestedStartDate:
            QSWATUtils.error('Finish date must be later than start date', self._gv.isBatch)
            return False
        self.periodsUpToDate = self.startDay == requestedStartDate.day and \
            self.startMonth == requestedStartDate.month and \
            self.startYear == requestedStartDate.year and \
            self.finishDay == requestedFinishDate.day and \
            self.finishMonth == requestedFinishDate.month and \
            self.finishYear == requestedFinishDate.year
        if self.periodsUpToDate:
            return True
        self.startDay = requestedStartDate.day
        self.startMonth = requestedStartDate.month
        self.startYear = requestedStartDate.year
        self.finishDay = requestedFinishDate.day
        self.finishMonth = requestedFinishDate.month
        self.finishYear = requestedFinishDate.year
        self.julianStartDay = int(requestedStartDate.strftime('%j'))
        self.julianFinishDay = int(requestedFinishDate.strftime('%j'))
        self.periodDays = 0
        self.periodMonths = 0
        self.periodYears = 0
        for year in range(self.startYear, self.finishYear + 1):
            leapAdjust = 1 if self.isLeap(year) else 0
            yearDays = 365 + leapAdjust
            start = self.julianStartDay if year == self.startYear else 1
            finish = self.julianFinishDay if year == self.finishYear else yearDays
            numDays = finish - start + 1
            self.periodDays += numDays
            fracYear = numDays / yearDays
            self.periodYears += fracYear
            self.periodMonths += fracYear * 12
        # QSWATUtils.loginfo('Period is {0} days, {1} months, {2} years'.format(self.periodDays, self.periodMonths, self.periodYears))
        return True
                
    def  readStartDate(self):
        """Return date from start date from form.  None if any problems."""
        try:
            day = int(self._dlg.startDay.currentText())
            month = Visualise._MONTHS.index(self._dlg.startMonth.currentText()) + 1
            year = int(self._dlg.startYear.text())
            return date(year, month, day)
        except Exception:
            return None
                
    def  readFinishDate(self):
        """Return date from finish date from form.  None if any problems."""
        try:
            day = int(self._dlg.finishDay.currentText())
            month = Visualise._MONTHS.index(self._dlg.finishMonth.currentText()) + 1
            year = int(self._dlg.finishYear.text())
            return date(year, month, day)
        except Exception:
            return None
        
    def setStartDate(self, date):
        """Set start date on form."""
        self._dlg.startDay.setCurrentIndex(date.day - 1)
        self._dlg.startYear.setText(str(date.year))
        self._dlg.startMonth.setCurrentIndex(date.month - 1)
            
    def setFinishDate(self, date):
        """Set finish date on form."""        
        self._dlg.finishDay.setCurrentIndex(date.day - 1)
        self._dlg.finishYear.setText(str(date.year))
        self._dlg.finishMonth.setCurrentIndex(date.month - 1)
            
        
    def addClick(self):
        """Append item to variableList."""
        self.resultsFileUpToDate = False
        var = self._dlg.variableCombo.currentText()
        items = self._dlg.variableList.findItems(var, Qt.MatchExactly)
        if not items or items == []:
            item = QListWidgetItem()
            item.setText(var)
            self._dlg.variableList.addItem(item)
            
    def allClick(self):
        """Clear variableList and insert all items from variableCombo."""
        self.resultsFileUpToDate = False
        self._dlg.variableList.clear()
        for i in range(self._dlg.variableCombo.count()):
            item = QListWidgetItem()
            item.setText(self._dlg.variableCombo.itemText(i))
            self._dlg.variableList.addItem(item)
        
    def delClick(self):
        """Delete item from variableList."""
        self.resultsFileUpToDate = False
        items = self._dlg.variableList.selectedItems()
        if len(items) > 0:
            row = self._dlg.variableList.indexFromItem(items[0]).row()
            self._dlg.variableList.takeItem(row)
    
    def clearClick(self):
        """Clear variableList."""
        self.resultsFileUpToDate = False
        self._dlg.variableList.clear()
        
    def doClose(self):
        """Close the db connection, timer, clean up from animation, and close the form."""
        self.conn = None
        self.animateTimer.stop()
        # empty animation and png directories
        self.clearAnimationDir()
        self.clearPngDir()
        # remove animation layers
        proj = QgsProject.instance()
        for animation in QSWATUtils.getLayersInGroup(QSWATUtils._ANIMATION_GROUP_NAME, proj.layerTreeRoot()):
            proj.removeMapLayer(animation.layerId())
        self._dlg.close()
        
    def plotSetUnit(self):
        """Update the unitEdit box and set the unit value in the current row."""
        unitStr = self._dlg.unitPlot.currentText()
        self._dlg.unitEdit.setText(unitStr)
        self.updateCurrentPlotRow(2)
        
    def plotEditUnit(self):
        """If the unitEdit contains a string in the unitPlot combo box, 
        Update the current index of the combo box, and set the unit value in the current row."""
        unitStr = self._dlg.unitEdit.text()
        index = self._dlg.unitPlot.findText(unitStr)
        if index >= 1: # avoid initial empty text as well as 'not found' value of -1
            self._dlg.unitPlot.setCurrentIndex(index)
            self.updateCurrentPlotRow(2)
        
    def plotSetVar(self):
        """Update the variable in the current plot row."""
        self.updateCurrentPlotRow(3)
        
    def writePlotData(self):
        """Write data for plot rows to csv file."""
        if not self.conn:
            return
        if not self.setPeriods():
            return
        if not self.checkFrequencyConsistent():
            QSWATUtils.error(u'All rows in the table must have the same frequency: annual, monthly or daily', self._gv.isBatch)
            return
        numRows = self._dlg.tableWidget.rowCount()
        plotData = dict()
        labels = dict()
        dates = []
        datesDone = False
        for i in range(numRows):
            plotData[i] = []
            scenario = self._dlg.tableWidget.item(i, 0).text()
            table = self._dlg.tableWidget.item(i, 1).text()
            gisId = self._dlg.tableWidget.item(i, 2).text()
            var = self._dlg.tableWidget.item(i, 3).text()
            if scenario == '' or table == '' or gisId == '' or var == '':
                QSWATUtils.information('Row {0!s} is incomplete'.format(i+1), self._gv.isBatch)
                return
            if scenario == 'observed' and table == '-':
                if os.path.exists(self.observedFileName):
                    labels[i] = 'observed-{0}'.format(var.strip()) # last label has an attached newline, so strip it
                    plotData[i] = self.readObservedFile(var)
                else:
                    QSWATUtils.error('Cannot find observed data file {0}'.format(self.observedFileName), self._gv.isBatch)
                    return
            else:
                num = int(gisId)
                where = 'gis_id={0}'.format(num)
                labels[i] = '{0}-{1}-{2!s}-{3}'.format(scenario, table, num, var)
                if scenario != self.scenario:
                    # need to change database
                    self.setConnection(scenario)
                    self.readData('', False, table, var, where)
                    # restore database
                    self.setConnection(self.scenario)
                else:
                    self.readData('', False, table, var, where)
                isDaily, isMonthly, isAnnual, _ = Visualise.tableIsDailyMonthlyOrAnnual(table)
                (year, tim) = self.startYearTime(isDaily, isMonthly)
                (finishYear, finishTime) = self.finishYearTime(isDaily, isMonthly)
                layerData = self.staticData['']
                while year < finishYear or (year == finishYear and tim <= finishTime):
                    if not num in layerData:
                        QSWATUtils.error('Insufficient data for unit {0} for plot {1!s}'.format(num, i+1), self._gv.isBatch)
                        return
                    unitData = layerData[num]
                    if not var in unitData:
                        QSWATUtils.error('Insufficient data for variable {0} for plot {1!s}'.format(var, i+1), self._gv.isBatch)
                        return
                    varData = unitData[var]
                    if not year in varData:
                        QSWATUtils.error('Insufficient data for year {0} for plot {1!s}'.format(year, i+1), self._gv.isBatch)
                        return
                    yearData = varData[year]
                    if isAnnual:
                        # time values in yearData are arbitrary and should be ignored
                        # there should be just one record
                        if len(yearData) == 0:
                            QSWATUtils.error(u'Insufficient data for year {0} for plot {1!s}'.format(year, i+1), self._gv.isBatch)
                            return
                        for val in yearData.values():
                            break
                    else:
                        if not tim in yearData:
                            if isDaily:
                                ref = 'day {0!s}'.format(tim)
                            else:
                                ref = 'month (0!s)'.format(tim)
                            QSWATUtils.error(u'Insufficient data for {0} for year {1} for plot {2!s}'.format(ref, year, i+1), self._gv.isBatch)
                            return
                        val = yearData[tim]
                    plotData[i].append('{:.3g}'.format(val))
                    if not datesDone:
                        if isDaily:
                            dates.append(str(year * 1000 + tim))
                        elif isAnnual:
                            dates.append(str(year))
                        else:
                            dates.append(str(year) + '/' + str(tim))
                    (year, tim) = self.nextDate(year, tim, isDaily, isMonthly, isAnnual)
                datesDone = True
        # data all collected: write csv file
        csvFile, _ = QFileDialog.getSaveFileName(None, 'Choose a csv file', self._gv.scenariosDir, 'CSV files (*.csv)')
        if not csvFile:
            return
        with open(csvFile, 'w', newline='') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)  # quote fields containing delimeter or other special characters 
            headers = ['Date']
            for i in range(numRows):
                headers.append(str(labels[i]))
            writer.writerow(headers)
            for d in range(len(dates)):
                row = [str(dates[d])]
                for i in range(numRows):
                    if not i in plotData:
                        QSWATUtils.error('Missing data for plot {0!s}'.format(i+1), self._gv.isBatch)
                        writer.writerow(row)
                        return
                    if not d in range(len(plotData[i])):
                        QSWATUtils.error('Missing data for date {0} for plot {1!s}'.format(dates[d], i+1), self._gv.isBatch)
                        writer.writerow(row)
                        return
                    row.append(str(plotData[i][d]))
                writer.writerow(row)
#         commands = []
#         settings = QSettings()
#         commands.append(QSWATUtils.join(QSWATUtils.join(settings.value('/QSWATPlus/EditorDir'), Parameters._SWATGRAPH), Parameters._SWATGRAPH))
#         commands.append(csvFile)
#         subprocess.Popen(commands)
# above replaced with swatGraph form
        graph = SWATGraph(csvFile)
        graph.run()
    
    def readData(self, layerId, isStatic, table, var, where):
        """Read data from database table into staticData."""
        if not self.conn:
            return
        # clear existing data for layerId
        self.staticData[layerId] = dict()
        layerData = self.staticData[layerId]
        #self.areas = dict()
        #self.hasAreas = False
        self.resultsData[layerId] = dict()
        if isStatic:
            varz = self.varList(True)
        else:
            varz = ['[' + var + ']']
        numVars = len(varz)
        isDaily = Visualise.tableIsDaily(table)
        isMonthly = Visualise.tableIsMonthly(table)
        if isDaily:
            selectString = '[jday], [yr], [gis_id], ' + ', '.join(varz)
            sql = self._gv.db.sqlSelect(table, selectString, '[yr], [jday]', where)
            preLen = 3
        elif isMonthly:
            selectString = '[mon], [yr], [gis_id], ' + ', '.join(varz)
            sql = self._gv.db.sqlSelect(table, selectString, '[yr], [mon]', where)
            preLen = 3
        else: # annual or average annual
            selectString = '[yr], [gis_id], ' + ', '.join(varz)
            sql = self._gv.db.sqlSelect(table, selectString, '[yr]', where)
            preLen = 2
        cursor = self.conn.cursor()
        # QSWATUtils.information('SQL: {0}'.format(sql), self._gv.isBatch)
        for row in cursor.execute(sql):
            if isDaily or isMonthly:
                tim = int(row[0])
                year = int(row[1])
                gisId = int(row[2])
            else:
                tim = int(row[0])
                year = tim
                gisId = int(row[1])
            if not self.inPeriod(year, tim, table, isDaily, isMonthly):
                continue
#             if self.hasAreas:
#                 area = float(row[3])
#             if isStatic and self.hasAreas and not unit in self.areas:
#                 self.areas[unit] = area
            if not gisId in layerData:
                layerData[gisId] = dict()
            for i in range(numVars):
                # remove square brackets from each var
                var = varz[i][1:-1]
                rawVal = row[i+preLen]
                if rawVal is None:
                    val = 0
                else:
                    val = float(rawVal)
                if not var in layerData[gisId]:
                    layerData[gisId][var] = dict()
                if not year in layerData[gisId][var]:
                    layerData[gisId][var][year] = dict()
                layerData[gisId][var][year][tim] = val
        self.summaryChanged = True
        
    def inPeriod(self, year, tim, table, isDaily, isMonthly):
        """
        Return true if year and tim are within requested period.
        
        Assumes self.[julian]startYear/Month/Day and self.[julian]finishYear/Month/Day already set.
        Assumes tim is within 1..365/6 when daily, and within 1..12 when monthly.
        """
        if year < self.startYear or year > self.finishYear:
            return False
        if Visualise.tableIsYearly(table):
            return True
        if isDaily:
            if year == self.startYear:
                return tim >= self.julianStartDay
            if year == self.finishYear:
                return tim <= self.julianFinishDay
            return True
        if isMonthly:
            if year == self.startYear:
                return tim >= self.startMonth
            if year == self.finishYear:
                return tim <= self.finishMonth
            return True
        # annual or average annual
        return True
    
    def checkFrequencyConsistent(self):
        """Check all non-observed rows are daily, monthly or annual."""
        isDaily = False
        isMonthly = False
        isAnnual = False
        frequencySet = False
        numRows = self._dlg.tableWidget.rowCount()
        for i in range(numRows):
            table = self._dlg.tableWidget.item(i, 1).text()
            if table == '-':  # observed
                continue
            if Visualise.tableIsMonthly(table):
                if frequencySet:
                    if not isMonthly:
                        return False
                else:
                    isMonthly = True
                    frequencySet = True
            elif Visualise.tableIsAnnual(table):
                if frequencySet:
                    if not isAnnual:
                        return False
                else:
                    isAnnual = True
                    frequencySet = True
            elif Visualise.tableIsDaily(table):
                if frequencySet:
                    if not isDaily:
                        return False
                else:
                    isDaily = True
                    frequencySet = True
            else:
                # can we get here?  Assume it is OK
                pass
        return True  # no problem found
            
                
    def summariseData(self, layerId, isStatic):
        """if isStatic, summarise data in staticData, else store all data for animate variable, saving in resultsData."""
        layerData = self.staticData[layerId]
        if isStatic:
            for index, vym in layerData.items():
                for var, ym in vym.items():
                    val = self.summarise(ym)
                    if index not in self.resultsData:
                        self.resultsData[index] = dict()
                    self.resultsData[index][var] = val
        else:
            self.allAnimateVals = []
            if not layerId in self.resultsData:
                self.resultsData[layerId] = dict()
            results = self.resultsData[layerId]
            for index, vym in layerData.items():
                for ym in vym.values():
                    for y, mval in ym.items():
                        for m, val in mval.items():
                            dat = self.makeDate(y, m)
                            if not dat in results:
                                results[dat] = dict()
                            results[dat][index] = val
                            self.allAnimateVals.append(val)
                            
    def makeDate(self, year, tim):
        """
        Make date number from year and tim according to period.
        
        tim is time field, which may be year, month or day according to period.
        """
        if self.isDaily:
            return year * 1000 + tim
        elif self.isMonthly:
            return year * 100 + tim
        else: # annual or average annual
            return year
            
        
    def startYearTime(self, isDaily, isMonthly):
        """Return (year, tim) pair for start date according to period."""
        if isDaily:
            return (self.startYear, self.julianStartDay)
        elif isMonthly:
            return (self.startYear, self.startMonth)
        else: # annual or average annual
            return (self.startYear, self.startYear)
            
        
    def finishYearTime(self, isDaily, isMonthly):
        """Return (year, tim) pair for finish date according to period."""
        if isDaily:
            return (self.finishYear, self.julianFinishDay)
        elif isMonthly:
            return (self.finishYear, self.finishMonth)
        else: # annual or average annual
            return (self.finishYear, self.finishYear)
            
        
    def nextDate(self, year, tim, isDaily, isMonthly, isAnnual):
        """Get next (year, tim) pair according to period.
        
        self.interval only used for daily data"""
        if isAnnual:
            return (year + 1, year + 1)
        elif isDaily:
            tim += self.interval
            yearLength = 366 if self.isLeap(year) else 365
            while tim > yearLength:
                year += 1
                tim -= yearLength
                yearLength = 366 if self.isLeap(year) else 365
            return (year, tim)
        elif isMonthly:
            tim += 1
            if tim == 13:
                year += 1
                tim = 1
            return (year, tim)
        else:
            return (year, tim)
    
    @staticmethod
    def tableIsDailyMonthlyOrAnnual(table):
        """Return isdaily, isMonthly, isAnnual, isAverageAnnual tuple of booleans for table."""
        return Visualise.tableIsDaily(table), Visualise.tableIsMonthly(table), \
            Visualise.tableIsAnnual(table), Visualise.tableIsAvAnnual(table)
    
    @staticmethod
    def tableIsDaily(table):
        """Return true if daily."""
        return table.endswith('_day')
    
    @staticmethod
    def tableIsMonthly(table):
        """Return true if monthly."""
        return table.endswith('_mon')
    
    @staticmethod
    def tableIsAnnual(table):
        """Return true if annual."""
        return table.endswith('_yr')
    
    @staticmethod
    def tableIsAvAnnual(table):
        """Return true if average annual."""
        return table.endswith('_aa')
    
    @staticmethod
    def tableIsYearly(table):
        """Return true if annual or average annual."""
        return Visualise.tableIsAnnual(table) or Visualise.tableIsAvAnnual(table)
        
    def summarise(self, data):
        """Summarise values according to summary method."""
        if self.isAA:
            # there will only be one value, so total will simply return it
            return self.summariseTotal(data)
        if self._dlg.summaryCombo.currentText() == Visualise._TOTALS:
            return self.summariseTotal(data)
        elif self._dlg.summaryCombo.currentText() == Visualise._ANNUALMEANS:
            return self.summariseAnnual(data)
        elif self._dlg.summaryCombo.currentText() == Visualise._MONTHLYMEANS:
            return self.summariseMonthly(data)
        elif self._dlg.summaryCombo.currentText() == Visualise._DAILYMEANS:
            return self.summariseDaily(data)
        elif self._dlg.summaryCombo.currentText() == Visualise._MAXIMA:
            return self.summariseMaxima(data)
        elif self._dlg.summaryCombo.currentText() == Visualise._MINIMA:
            return self.summariseMinima(data)
        else:
            QSWATUtils.error('Internal error: unknown summary method: please report', self._gv.isBatch)
            
    def summariseTotal(self, data):
        """Sum values and return."""
        total = 0
        for mv in data.values():
            for v in mv.values():
                total += v
        return total
        
    def summariseAnnual(self, data):
        """Return total divided by period in years."""
        return self.summariseTotal(data) / self.periodYears
        
    def summariseMonthly(self, data):
        """Return total divided by period in months."""
        return self.summariseTotal(data) / self.periodMonths
        
    def summariseDaily(self, data):
        """Return total divided by period in days."""
        return self.summariseTotal(data) / self.periodDays
        
    def summariseMaxima(self, data):
        """Return maximum of values."""
        maxv = 0
        for mv in data.values():
            for v in mv.values():
                maxv = max(maxv, v)
        return maxv
        
    def summariseMinima(self, data):
        """Return minimum of values."""
        minv = float('inf')
        for mv in data.values():
            for v in mv.values():
                minv = min(minv, v)
        return minv
                
    @staticmethod
    def isLeap(year):
        """Return true if year is a leap year."""
        if year % 4 == 0:
            if year % 100 == 0:
                return year % 400 == 0
            else:
                return True
        else:
            return False
            
    def setGisIdPlot(self):
        """Add gis id numbers to unitPlot combo."""
        if self.conn is None or self.table == '':
            return
        self._dlg.unitPlot.clear()
        self._dlg.unitPlot.addItem('')
        sql = 'SELECT [gis_id] FROM {0}'.format(self.table)
        firstId = None
        try:
            for row in self.conn.execute(sql):
                gisId = row[0]
                if firstId is None:
                    firstId = gisId
                elif gisId == firstId:
                    return
                self._dlg.unitPlot.addItem(str(gisId))
            self._dlg.unitPlot.setCurrentIndex(0)
        except sqlite3.OperationalError:
            QSWATUtils.error('Table {0} in {1} has no gis_id column'.format(self.table, self.db), self._gv.isBatch)
            
    def varList(self, bracket):
        """Return variables in variableList as a list of strings, with square brackets if bracket is true."""
        result = []
        numRows = self._dlg.variableList.count()
        for row in range(numRows):
            var = self._dlg.variableList.item(row).text()
            # bracket variables when using in sql, to avoid reserved words and '/'
            if bracket:
                var = '[' + var + ']'
            result.append(var)
        return result
    
    def setResultsFile(self):
        """Set results file by asking user."""
        try:
            path = os.path.split(self._dlg.resultsFileEdit.text())[0]
        except Exception:
            path = ''
        base = self.selectBase()
        if base is None:
            return
        resultsFileName, _ = QFileDialog.getSaveFileName(None, base + 'results', path, QgsProject.instance().fileVectorFilters())
        if not resultsFileName:
            return
        direc, resName = os.path.split(resultsFileName)
        direcUp, direcName = os.path.split(direc)
        if direcName == Parameters._RESULTS:
            ## check we are not overwriting a template
            direcUpUp = os.path.split(direcUp)[0]
            if QSWATUtils.samePath(direcUpUp, self._gv.scenariosDir):
                base = os.path.splitext(resName)[0]
                if base == Parameters._SUBS or base == Parameters._RIVS or base == Parameters._HRUS or base == Parameters._LSUS:
                    QSWATUtils.information('The file {0} should not be overwritten: please choose another file name.'.format(os.path.splitext(resultsFileName)[0] + '.shp'), self._gv.isBatch)
                    return
        elif direcName == Parameters._ANIMATION:
            ## check we are not using the Animation directory
            direcUpUp = os.path.split(direcUp)[0]
            if QSWATUtils.samePath(direcUpUp, self._gv.resultsDir):
                QSWATUtils.information('Please do not use {0} for results as it can be overwritten by animation.'.format(os.path.splitext(resultsFileName)[0] + '.shp'), self._gv.isBatch)
                return
        self._dlg.resultsFileEdit.setText(resultsFileName)
        self.resultsFileUpToDate = False
        
    def setObservedFile(self):
        """Get an observed data file from the user."""
        try:
            path = os.path.split(self._dlg.observedFileEdit.text())[0]
        except Exception:
            path = ''
        observedFileName, _ = QFileDialog.getOpenFileName(None, 'Choose observed data file', path, 'CSV files (*.csv);;Any file (*.*)')
        if not observedFileName:
            return
        self.observedFileName = observedFileName
        self._dlg.observedFileEdit.setText(observedFileName)
        proj = QgsProject.instance()
        proj.writeEntry(self.title, 'observed/observedFile', self.observedFileName)
        proj.write()
        
    def selectBase(self):
        """Return base name of shapefile used for results according to table name and availability of actual hrus file"""
        if self.table.startswith('aquifer_') or self.table.startswith('channel_'):
            return Parameters._RIVS
        if self.table.startswith('lsunit_'):
            return Parameters._LSUS
        if self.table.startswith('basin_'):
            return Parameters._SUBS
        resultsDir = os.path.split(self.db)[0]
        hasHRUs = os.path.exists(QSWATUtils.join(resultsDir, Parameters._HRUS + '.shp'))
        if self.table.startswith('hru_'):
            if hasHRUs:
                return Parameters._HRUS
            else:
                return Parameters._LSUS  # TODO: should check numLSUs = numHRUs
        QSWATUtils.error('Do not know how to show results for table {0}'.format(self.table), self._gv.isBatch)
        return None
        
    def createResultsFile(self):
        """
        Create results shapefile.
        
        Assumes:
        - resultsFileEdit contains suitable text for results file name
        - one or more variables is selected in variableList (and uses the first one)
        - resultsData is suitably populated
        """
        nextResultsFile = self._dlg.resultsFileEdit.text()
        proj = QgsProject.instance()
        root = proj.layerTreeRoot()
        if os.path.exists(nextResultsFile):
            reply = QSWATUtils.question('Results file {0} already exists.  Do you wish to overwrite it?'.format(nextResultsFile), self._gv.isBatch, True)
            if reply != QMessageBox.Yes:
                return False
            if nextResultsFile == self.resultsFile:
                # remove existing layer so new one replaces it
                QSWATUtils.removeLayerAndFiles(self.resultsFile, root)
            else:
                QSWATUtils.tryRemoveFiles(nextResultsFile)
                self.resultsFile = nextResultsFile
        else:
            self.resultsFile = nextResultsFile
        resultsDir = os.path.split(self.db)[0]
        baseName = self.selectBase()
        if baseName is None:
            return False
        resultsBase = QSWATUtils.join(resultsDir, baseName) + '.shp'
        outdir, outfile = os.path.split(self.resultsFile)
        outbase = os.path.splitext(outfile)[0]
        QSWATUtils.copyShapefile(resultsBase, outbase, outdir)
        selectVar = self._dlg.variableList.selectedItems()[0].text()[:10]
        legend = '{0} {1} {2}'.format(self.scenario, selectVar, self._dlg.summaryCombo.currentText())
        if baseName == Parameters._SUBS:
            self.subResultsLayer = QgsVectorLayer(self.resultsFile, legend, 'ogr')
            self.subResultsLayer.rendererChanged.connect(self.changeSubRenderer)
            self.internalChangeToSubRenderer = True
            self.keepSubColours = False
            layer = self.subResultsLayer
        elif baseName == Parameters._LSUS:
            self.lsuResultsLayer = QgsVectorLayer(self.resultsFile, legend, 'ogr')
            self.lsuResultsLayer.rendererChanged.connect(self.changeLSURenderer)
            self.internalChangeToLSURenderer = True
            self.keepLSUColours = False
            layer = self.lsuResultsLayer
        elif baseName == Parameters._HRUS:
            self.hruResultsLayer = QgsVectorLayer(self.resultsFile, legend, 'ogr')
            self.hruResultsLayer.rendererChanged.connect(self.changeHRURenderer)
            self.internalChangeToHRURenderer = True
            self.keepHRUColours = False
            layer = self.hruResultsLayer
        else:
            self.rivResultsLayer = QgsVectorLayer(self.resultsFile, legend, 'ogr')
            self.rivResultsLayer.rendererChanged.connect(self.changeRivRenderer)
            self.internalChangeToRivRenderer = True
            self.keepRivColours = False
            layer = self.rivResultsLayer
#         if self.hasAreas:
#             field = QgsField(Visualise._AREA, QVariant.Double, len=20, prec=0)
#             if not layer.dataProvider().addAttributes([field]):
#                 QSWATUtils.error('Could not add field {0} to results file {1}'.format(Visualise._AREA, self.resultsFile), self._gv.isBatch)
#                 return False
        varz = self.varList(False)
        for var in varz:
            field = QgsField(var, QVariant.Double)
            if not layer.dataProvider().addAttributes([field]):
                QSWATUtils.error('Could not add field {0} to results file {1}'.format(var, self.resultsFile), self._gv.isBatch)
                return False
        layer.updateFields()
        self.updateResultsFile() 
        layer = proj.addMapLayer(layer, False)
        resultsGroup = root.findGroup(QSWATUtils._RESULTS_GROUP_NAME)
        resultsGroup.insertLayer(0, layer)
        if baseName == Parameters._SUBS:
            self.subResultsLayer = layer
            # add labels
            self.subResultsLayer.loadNamedStyle(QSWATUtils.join(self._gv.plugin_dir, 'subresults.qml'))
            self.internalChangeToSubRenderer = False
        elif baseName == Parameters._LSUS:
            self.lsuResultsLayer = layer
            self.internalChangeToLSURenderer = False
        elif baseName == Parameters._HRUS:
            self.hruResultsLayer = layer
            self.internalChangeToHRURenderer = False
        else:
            self.rivResultsLayer = layer
            self.internalChangeToRivRenderer = False
        return True
        
    def updateResultsFile(self):
        """Write resultsData to resultsFile."""
        base = self.selectBase()
        if base is None:
            return
        layer = self.subResultsLayer if base == Parameters._SUBS \
                else self.lsuResultsLayer if base == Parameters._LSUS \
                else self.hruResultsLayer if base == Parameters._HRUS else self.rivResultsLayer
        varz = self.varList(False)
        varIndexes = dict()
#         if self.hasAreas:
#             varIndexes[Visualise._AREA] = self._gv.topo.getIndex(layer, Visualise._AREA)
        for var in varz:
            varIndexes[var] = self._gv.topo.getIndex(layer, var)
        layer.startEditing()
        for f in layer.getFeatures():
            fid = f.id()
            if base == Parameters._HRUS:
                # May be split HRUs; just use first
                # This is inadequate for some variables, but no way to know of correct val is sum of vals, mean, etc.
                unitText = f[QSWATTopology._HRUS]
                if 'PND' in unitText or 'RES' in unitText:
                    continue
                unit = int(unitText.split(',')[0]) 
            elif base == Parameters._LSUS:
                unit = f[QSWATTopology._LSUID]
            elif base == Parameters._SUBS:
                unit = f[QSWATTopology._SUBBASIN]
            else:
                unit = f[QSWATTopology._CHANNEL]
#             if self.hasAreas:
#                 area = self.areas.get(unit, None)
#                 if area is None:
#                     if base == Parameters._HRUS:
#                         ref = 'HRU {0!s}'.format(unit)
#                     elif base == Parameters._LSUS:
#                         ref = 'LSU {0!s}'.format(unit)
#                     else:
#                         ref = 'subbasin {0!s}'.format(unit)
#                     QSWATUtils.error('Cannot get area for {0}: have you run SWAT and saved data since running QSWAT?'.format(ref), self._gv.isBatch)
#                     return
#                 if not layer.changeAttributeValue(fid, varIndexes[Visualise._AREA], float(area)):
#                     QSWATUtils.error('Could not set attribute {0} in results file {1}'.format(Visualise._AREA, self.resultsFile), self._gv.isBatch)
#                     return
            for var in varz:
                subData = self.resultsData.get(unit, None)
                if subData is not None:
                    data = subData.get(var, None)
                else:
                    data = None
                if data is None:
                    if base == Parameters._HRUS:
                        ref = 'HRU {0!s}'.format(unit)
                    elif base == Parameters._LSUS:
                        ref = 'LSU {0!s}'.format(unit)
                    elif base == Parameters._SUBS:
                        ref = 'subbasin {0!s}'.format(unit)
                    else:
                        ref = 'channel {0!s}'.format(unit)
                    QSWATUtils.error('Cannot get data for variable {0} in {1}: have you run SWAT+ and saved data since running QSWAT+?'.format(var, ref), self._gv.isBatch)
                    return
                if not layer.changeAttributeValue(fid, varIndexes[var], float(data) if isinstance(data, numpy.float64) else data):
                    QSWATUtils.error('Could not set attribute {0} in results file {1}'.format(var, self.resultsFile), self._gv.isBatch)
                    return
        layer.commitChanges()
        self.summaryChanged = False
        
    def colourResultsFile(self):
        """
        Colour results layer according to current results variable and update legend.
        
        if createColour is false the existing colour ramp and number of classes can be reused
        """
        base = self.selectBase()
        if base is None:
            return
        if base == Parameters._SUBS:
            layer = self.subResultsLayer
            keepColours = self.keepSubColours
            symbol = QgsFillSymbol()
        elif base == Parameters._LSUS:
            layer = self.lsuResultsLayer
            keepColours = self.keepLSUColours
            symbol = QgsFillSymbol()
        elif base == Parameters._HRUS:
            layer = self.hruResultsLayer
            keepColours = self.keepHRUColours
            symbol = QgsFillSymbol()
        else:
            layer = self.rivResultsLayer
            keepColours = self.keepRivColours
            props = {'width_expression': QSWATTopology._PENWIDTH}
            symbol = QgsLineSymbol.createSimple(props)
            symbol.setWidth(1.0)
        selectVar = self._dlg.variableList.selectedItems()[0].text()
        selectVarShort = selectVar[:10]
        layer.setName('{0} {1} {2}'.format(self.scenario, selectVar, self._dlg.summaryCombo.currentText()))
        if not keepColours:
            count = 5
            opacity = 1 if base == Parameters._RIVS else 65
        else:
            # same layer as currently - try to use same range size and colours, and same opacity
            try:
                oldRenderer = layer.renderer()
                oldRanges = oldRenderer.ranges()
                count = len(oldRanges)
                ramp = oldRenderer.sourceColorRamp()
                opacity = layer.opacity()
            except Exception:
                # don't care if no suitable colours, so no message, just revert to defaults
                keepColours = False
                count = 5
                opacity = 1 if base == Parameters._RIVS else 65
        if not keepColours:
            ramp = self.chooseColorRamp(self.table, selectVar)
        labelFmt = QgsRendererRangeLabelFormat('%1 - %2', 0)
        renderer = QgsGraduatedSymbolRenderer.createRenderer(layer, selectVarShort, count, 
                                                             QgsGraduatedSymbolRenderer.Jenks, symbol, 
                                                             ramp, labelFmt)
        renderer.calculateLabelPrecision()
        # previous line should be enough to update precision, but in practice seems we need to recreate renderer
        precision = renderer.labelFormat().precision()
        QSWATUtils.loginfo('Precision: {0}'.format(precision))
        # default seems too high
        labelFmt = QgsRendererRangeLabelFormat('%1 - %2', precision-1)
        # should be enough to update labelFmt, but seems to be necessary to make renderer again to reflect new precision
        renderer = QgsGraduatedSymbolRenderer.createRenderer(layer, selectVarShort, count, 
                                                             QgsGraduatedSymbolRenderer.Jenks, symbol, 
                                                             ramp, labelFmt)
        if base == Parameters._SUBS:
            self.internalChangeToSubRenderer = True
        elif base == Parameters._LSUS:
            self.internalChangeToLSURenderer = True
        elif base == Parameters._HRUS:
            self.internalChangeToHRURenderer = True
        else:
            self.internalChangeToRivRenderer = True
        layer.setRenderer(renderer)
        layer.setOpacity(opacity)
        layer.triggerRepaint()
        self._gv.iface.layerTreeView().refreshLayerSymbology(layer.id())
        canvas = self._gv.iface.mapCanvas()
        if self.mapTitle is not None:
            canvas.scene().removeItem(self.mapTitle)
        self.mapTitle = MapTitle(canvas, self.title, layer)
        canvas.update()
        if base == Parameters._SUBS:
            self.internalChangeToSubRenderer = False
            self.keepSubColours = keepColours
        elif base == Parameters._LSUS:
            self.internalChangeToLSURenderer = False
            self.keepLSUColours = keepColours
        elif base == Parameters._HRUS:
            self.internalChangeToHRURenderer = False
            self.keepHRUColours = keepColours
        else:
            self.internalChangeToRivRenderer = False
            self.keepRivColours = keepColours
            
    def resultsLayerExists(self):
        """Return true if current results layer has not been removed."""
        base = self.selectBase()
        if base is None:
            return False
        if base == Parameters._SUBS:
            layer = self.subResultsLayer
        if base == Parameters._LSUS:
            layer = self.lsuResultsLayer
        elif base == Parameters._HRUS:
            layer = self.hruResultsLayer
        else:
            layer = self.rivResultsLayer
        if layer is None:
            return False
        try:
            # a removed layer will fail with a RuntimeError 
            layer.objectName()
            return True
        except RuntimeError:
            return False
        
    def createAnimationLayer(self):
        """
        Create animation with new shapefile or existing one.
        
        Assumes:
        - animation variable is set
        """
        proj = QgsProject.instance()
        root = proj.layerTreeRoot()
        base = self.selectBase()
        if base is None:
            return False
        resultsBase = QSWATUtils.join(self._gv.resultsDir, base) + '.shp'
        animateFileBase = QSWATUtils.join(self._gv.animationDir, base) + '.shp'
        animateFile, num = QSWATUtils.nextFileName(animateFileBase, 0)
        QSWATUtils.copyShapefile(resultsBase, base + str(num), self._gv.animationDir)
        if not self.stillFileBase or self.stillFileBase == '':
            self.stillFileBase = QSWATUtils.join(self._gv.pngDir, Parameters._STILLPNG)
        self.currentStillNumber = 0
        animateLayer = QgsVectorLayer(animateFile, '{0} {1}'.format(self.scenario, self.animateVar), 'ogr')
        provider = animateLayer.dataProvider()
        field = QgsField(self.animateVar, QVariant.Double)
        if not provider.addAttributes([field]):
            QSWATUtils.error(u'Could not add field {0} to animation file {1}'.format(self.animateVar, animateFile), self._gv.isBatch)
            return False
        animateLayer.updateFields()
        animateIndex = self._gv.topo.getProviderIndex(provider, self.animateVar)
        # place layer at top of animation group if new,
        # else above current animation layer, and mark that for removal
        animationGroup = root.findGroup(QSWATUtils._ANIMATION_GROUP_NAME)
        if self._dlg.newAnimation.isChecked():
            layerToRemoveId = None
            index = 0
        else:
            animations = animationGroup.findLayers()
            if len(animations) == 1:
                layerToRemoveId = animations[0].layerId()
                index = 0
            else:
                currentLayerId = self._gv.iface.activeLayer().id()
                for i in range(len(animations)):
                    if animations[i].layerId() == currentLayerId:
                        index = i 
                        layerToRemoveId = currentLayerId
                        break
                layerToRemoveId = None
                index = 0
        self.animateLayer = proj.addMapLayer(animateLayer, False)
        animationGroup.insertLayer(index, self.animateLayer)
        if layerToRemoveId is not None:
            proj.removeMapLayer(layerToRemoveId)
        self.animateIndexes[self.animateLayer.id()] = animateIndex
        # add labels if based on subbasins
        if base == Parameters._SUBS:
            self.animateLayer.loadNamedStyle(QSWATUtils.join(self._gv.plugin_dir, 'subsresults.qml'))
        return True
            
    def colourAnimationLayer(self):
        """Colour animation layer.
        
        Assumes allAnimateVals is suitably populated.
        """
        base = self.selectBase()
        if base is None:
            return
        count = 5
        opacity = 1 if base == Parameters._RIVS else 65
        ramp = self.chooseColorRamp(self.table, self.animateVar)
        # replaced by Cython code
        #=======================================================================
        # breaks, minimum = self.getJenksBreaks(self.allAnimateVals, count)
        # QSWATUtils.loginfo('Breaks: {0!s}'.format(breaks))
        #=======================================================================
        cbreaks = jenks(self.allAnimateVals, count)
        QSWATUtils.loginfo('Breaks: {0!s}'.format(cbreaks))
        rangeList = []
        for i in range(count):
            # adjust min and max by 1% to avoid rounding errors causing values to be outside the range
            minVal = cbreaks[0] * 0.99 if i == 0 else cbreaks[i]
            maxVal = cbreaks[count] * 1.01 if i == count-1 else cbreaks[i+1]
            colourVal = i / (count - 1)
            colour = ramp.color(colourVal)
            rangeList.append(self.makeSymbologyForRange(minVal, maxVal, colour, 4))
        renderer = QgsGraduatedSymbolRenderer(self.animateVar[:10], rangeList)
        renderer.setMode(QgsGraduatedSymbolRenderer.Custom)
        renderer.calculateLabelPrecision()
        precision = renderer.labelFormat().precision()
        QSWATUtils.loginfo('Animation precision: {0}'.format(precision-1))
        # repeat with calculated precision
        rangeList = []
        for i in range(count):
            # adjust min and max by 1% to avoid rounding errors causing values to be outside the range
            minVal = cbreaks[0] * 0.99 if i == 0 else cbreaks[i]
            maxVal = cbreaks[count] * 1.01 if i == count-1 else cbreaks[i+1]
            colourVal = i / (count - 1)
            colour = ramp.color(colourVal)
            # default precision too high
            rangeList.append(self.makeSymbologyForRange(minVal, maxVal, colour, precision-1))
        renderer = QgsGraduatedSymbolRenderer(self.animateVar[:10], rangeList)
        renderer.setMode(QgsGraduatedSymbolRenderer.Custom)
        self.animateLayer.setRenderer(renderer)
        self.animateLayer.setOpacity(opacity)
        self._gv.iface.layerTreeView().refreshLayerSymbology(self.animateLayer.id())
        self._gv.iface.setActiveLayer(self.animateLayer)
#         animations = QSWATUtils.getLayersInGroup(QSWATUtils._ANIMATION_GROUP_NAME, li, visible=True)
#         if len(animations) > 0:
#             canvas = self._gv.iface.mapCanvas()
#             if self.mapTitle is not None:
#                 canvas.scene().removeItem(self.mapTitle)
#             self.mapTitle = MapTitle(canvas, self.title, animations[0])
#             canvas.update()
        
    def createAnimationComposition(self):
        """Create print composer to capture each animation step."""
        proj = QgsProject.instance()
        root = proj.layerTreeRoot()
        animationLayers = QSWATUtils.getLayersInGroup(QSWATUtils._ANIMATION_GROUP_NAME, root)
        watershedLayers = QSWATUtils.getLayersInGroup(QSWATUtils._WATERSHED_GROUP_NAME, root, visible=True)
        # choose template file and set its width and height
        # width and height here need to be updated if template file is changed
        count = self._dlg.composeCount.value()
        isLandscape = self._dlg.composeLandscape.isChecked()
        if count == 1:
            if isLandscape:
                templ = '1Landscape.qpt'
                width = 230.0
                height = 160.0
            else:
                templ = '1Portrait.qpt'
                width = 190.0
                height = 200.0
        elif count == 2:
            if isLandscape:
                templ = '2Landscape.qpt'
                width = 125.0
                height = 120.0
            else:
                templ = '2Portrait.qpt'
                width = 150.0
                height = 120.0
        elif count == 3:
            if isLandscape:
                templ = '3Landscape.qpt'
                width = 90.0
                height = 110.0
            else:
                templ = '3Portrait.qpt'
                width = 150.0
                height = 80.0
        elif count == 4:
            if isLandscape:
                templ = '4Landscape.qpt'
                width = 95.0
                height = 80.0
            else:
                templ = '4Portrait.qpt'
                width = 85.0
                height = 85.0
        elif count == 6:
            if isLandscape:
                templ = '6Landscape.qpt'
                width = 90.0
                height = 40.0
            else:
                templ = '6Portrait.qpt'
                width = 55.0
                height = 80.0
        else:
            QSWATUtils.error('There are composition templates only for 1, 2, 3, 4 or 6 result maps, not for {0}'.format(count), self._gv.isBatch)
            return
        templateIn = QSWATUtils.join(self._gv.plugin_dir, 'PrintTemplate' + templ)
        self.animationTemplate = QSWATUtils.join(self._gv.resultsDir, 'AnimationTemplate.qpt')
        # make substitution table
        subs = dict()
        northArrow = QSWATUtils.join(os.getenv('OSGEO4W_ROOT'), Visualise._NORTHARROW)
        if not os.path.isfile(northArrow):
            # may be qgis-ltr for example
            northArrowRel = Visualise._NORTHARROW.replace('qgis', QSWATUtils.qgisName(), 1)
            northArrow = QSWATUtils.join(os.getenv('OSGEO4W_ROOT'), northArrowRel)
        if not os.path.isfile(northArrow):
            QSWATUtils.error('Failed to find north arrow {0}.  You will need to repair the layout.'.format(northArrow), self._gv.isBatch)
        subs['%%NorthArrow%%'] = northArrow
        subs['%%ProjectName%%'] = self.title
        numLayers = len(animationLayers)
        if count > numLayers:
            QSWATUtils.error(u'You want to make a print of {0} maps, but you only have {1} animation layers'.format(count, numLayers), self._gv.isBatch)
            return
        extent = self._gv.iface.mapCanvas().extent()
        xmax = extent.xMaximum()
        xmin = extent.xMinimum()
        ymin = extent.yMinimum()
        ymax = extent.yMaximum()
        QSWATUtils.loginfo('Map canvas extent {0}, {1}, {2}, {3}'.format(str(int(xmin + 0.5)), str(int(ymin + 0.5)), 
                                                                         str(int(xmax + 0.5)), str(int(ymax + 0.5))))
        # need to expand either x or y extent to fit map shape
        xdiff = ((ymax - ymin) / height) * width - (xmax - xmin)
        if xdiff > 0:
            # need to expand x extent
            xmin = xmin - xdiff / 2
            xmax = xmax + xdiff / 2
        else:
            # expand y extent
            ydiff = (((xmax - xmin) / width) * height) - (ymax - ymin)
            ymin = ymin - ydiff / 2
            ymax = ymax + ydiff / 2
        QSWATUtils.loginfo('Map extent set to {0}, {1}, {2}, {3}'.format(str(int(xmin + 0.5)), str(int(ymin + 0.5)), 
                                                                         str(int(xmax + 0.5)), str(int(ymax + 0.5))))
        # estimate of segment size for scale
        # aim is approx 10mm for 1 segment
        # we make size a power of 10 so that segments are 1km, or 10, or 100, etc.
        segSize = 10 ** int(math.log10((xmax - xmin) / (width / 10)) + 0.5)
        layerStr = '<Layer source="{0}" provider="ogr" name="{1}">{2}</Layer>'
        for i in range(count):
            layer = animationLayers[i].layer()
            subs['%%LayerId{0}%%'.format(i)] = layer.id()
            subs['%%LayerName{0}%%'.format(i)] = layer.name()
            subs['%%YMin{0}%%'.format(i)] = str(ymin)
            subs['%%XMin{0}%%'.format(i)] = str(xmin)
            subs['%%YMax{0}%%'.format(i)] = str(ymax)
            subs['%%XMax{0}%%'.format(i)] = str(xmax)
            subs['%%ScaleSegSize%%'] = str(segSize)
            subs['%%Layer{0}%%'.format(i)] = layerStr.format(QSWATUtils.layerFilename(layer), layer.name(), layer.id())
        for i in range(6):  # 6 entries in template for background layers
            if i < len(watershedLayers):
                wLayer = watershedLayers[i].layer()
                subs['%%WshedLayer{0}%%'.format(i)] = layerStr.format(QSWATUtils.layerFilename(wLayer), wLayer.name(), wLayer.id())
            else:  # remove unused ones
                subs['%%WshedLayer{0}%%'.format(i)] = ''
        with open(templateIn, 'rU') as inFile:
            with open(self.animationTemplate, 'w') as outFile:
                for line in inFile:
                    outFile.write(Visualise.replaceInLine(line, subs))
        QSWATUtils.loginfo('Print layout template {0} written'.format(self.animationTemplate))
        self.animationDOM = QDomDocument()
        f = QFile(self.animationTemplate)
        if f.open(QIODevice.ReadOnly):
            OK = self.animationDOM.setContent(f)
            if not OK:
                QSWATUtils.error('Cannot parse template file {0}'.format(self.animationTemplate), self._gv.isBatch)
                return
        else:
            QSWATUtils.error('Cannot open template file {0}'.format(self.animationTemplate), self._gv.isBatch) 
            return 
        if not self._gv.isBatch:
            QSWATUtils.information("""
            The layout designer is about to start, showing the current layout for the animation.
            
            You can change the layout as you wish, and then you should 'Save as Template' in the designer menu, using {0} as the template file.  
            If this file already exists: you will have to confirm overwriting it.
            Then close the layout designer.
            If you don't change anything you can simply close the layout designer without saving.
            
            Then start the animation running.
            """.format(self.animationTemplate), False) 
            title = 'Animation base'
            # remove layout from layout manager, in case still there
            try:
                proj.layoutManager().removeLayout(self.animationLayout)
            except:
                pass
            # clean up in case previous one remains
            self.animationLayout = None
            self.animationLayout = QgsPrintLayout(proj)
            self.animationLayout.initializeDefaults()
            self.animationLayout.setName(title)
            self.setDateInTemplate()
            items = self.animationLayout.loadFromTemplate(self.animationDOM, QgsReadWriteContext())
            ok = proj.layoutManager().addLayout(self.animationLayout)
            if not ok:
                QSWATUtils.error('Failed to add animation layout to layout manager.  Try removing some.', self._gv.isBatch)
                return
            designer = self._gv.iface.openLayoutDesigner(layout=self.animationLayout)
            self.animationTemplateDirty = True
                                           
    def rereadAnimationTemplate(self):
        """Reread animation template file."""
        self.animationTemplateDirty = False
        self.animationDOM = QDomDocument()
        f = QFile(self.animationTemplate)
        if f.open(QIODevice.ReadOnly):
            OK = self.animationDOM.setContent(f)[0]
            if not OK:
                QSWATUtils.error('Cannot parse template file {0}'.format(self.animationTemplate), self._gv.isBatch)
                return
        else:
            QSWATUtils.error('Cannot open template file {0}'.format(self.animationTemplate), self._gv.isBatch) 
            return
        
    def setDateInTemplate(self):
        """Set current animation date in title field."""
        itms = self.animationDOM.elementsByTagName('LayoutItem')
        for i in range(itms.length()):
            itm = itms.item(i)
            attr = itm.attributes().namedItem('id').toAttr()
            if attr is not None and attr.value() == 'Date':
                title = itm.attributes().namedItem('labelText').toAttr()
                if title is None:
                    QSWATUtils.error('Cannot find template date label', self._gv.isBatch)
                    return
                title.setValue(self._dlg.dateLabel.text())
                return
        QSWATUtils.error('Cannot find template date label', self._gv.isBatch)
        return

#     def setDateInComposer(self):
#         """Set current animation date in title field."""
#         labels = self.animationDOM.elementsByTagName('ComposerLabel')
#         for i in range(labels.length()):
#             label = labels.item(i)
#             item = label.namedItem('ComposerItem')
#             attr = item.attributes().namedItem('id').toAttr()
#             if attr is not None and attr.value() == 'Date':
#                 title = label.attributes().namedItem('labelText').toAttr()
#                 if title is None:
#                     QSWATUtils.error('Cannot find composer date label', self._gv.isBatch)
#                     return
#                 title.setValue(self._dlg.dateLabel.text())
#                 return
#         QSWATUtils.error('Cannot find composer date label', self._gv.isBatch)
#         return
        
    def changeAnimate(self):
        """
        Display animation data for current slider value.
        
        Get date from slider value; read animation data for date; write to animation file; redisplay.
        """
        try:
            if self._dlg.animationVariableCombo.currentText() == '':
                QSWATUtils.information('Please choose an animation variable', self._gv.isBatch)
                self.doRewind()
                return
            if self.capturing:
                self.capture()
            dat = self.sliderValToDate()
            date = self.dateToString(dat)
            self._dlg.dateLabel.setText(date)
            if self._dlg.canvasAnimation.isChecked():
                animateLayers = [self.animateLayer]
            else:
                root = QgsProject.instance().layerTreeRoot()
                animateTreeLayers = QSWATUtils.getLayersInGroup(QSWATUtils._ANIMATION_GROUP_NAME, root, visible=False)
                animateLayers = [layer.layer() for layer in animateTreeLayers]
            for animateLayer in animateLayers:
                layerId = animateLayer.id()
                data = self.resultsData[layerId][dat]
                self.mapTitle.updateLine2(date)
                provider = animateLayer.dataProvider()
                animateIndex = self.animateIndexes[layerId]
                base = self.selectBase()
                if base is None:
                    return
                unitIdx = provider.fieldNameIndex(QSWATTopology._HRUS)
                if unitIdx < 0:
                    unitIdx = provider.fieldNameIndex(QSWATTopology._LSUID)
                if unitIdx < 0:
                    unitIdx = provider.fieldNameIndex(QSWATTopology._SUBBASIN)
                if unitIdx < 0:
                    unitIdx = provider.fieldNameIndex(QSWATTopology._CHANNEL)
                if unitIdx < 0:
                    QSWATUtils.error('Cannot find unit column in {0}'.format(provider.dataSourceUri()), self._gv.isBatch)
                    continue
                mmap = dict()
                for f in provider.getFeatures():
                    fid = f.id()
                    if base == Parameters._HRUS:
                        # May be split HRUs; just use first
                        # This is inadequate for some variables, but no way to know if correct val is sum of vals, mean, etc.
                        unitText = f[unitIdx]
                        if 'PND' in unitText:
                            continue
                        unit = int(unitText.split(',')[0])
                    else:
                        unit = f[unitIdx]
                    if unit in data:
                        val = data[unit]
                    else:
                        if base == Parameters._HRUS:
                            ref = 'HRU {0!s}'.format(unit)
                        elif base == Parameters._LSUS:
                            ref = 'LSU {0!s}'.format(unit)
                        elif base == Parameters._SUBS:
                            ref = 'subbasin {0!s}'.format(unit)
                        else:
                            ref = 'channel {0!s}'.format(unit)
                        QSWATUtils.error('Cannot get data for {0}: have you run SWAT+ and saved data since running QSWAT+?'.format(ref), self._gv.isBatch)
                        return
                    mmap[fid] = {animateIndex: float(val) if isinstance(val, numpy.float64) else val}
                if not provider.changeAttributeValues(mmap):
                    source = animateLayer.publicSource()
                    QSWATUtils.error('Could not set attribute {0} in animation file {1}'.format(self.animateVar, source), self._gv.isBatch)
                    self.animating = False
                    return
                animateLayer.triggerRepaint()
            self._dlg.dateLabel.repaint()
        except Exception:
            self.animating = False
            raise
        
    def capture(self):
        """Make image file of current canvas."""
        if self.animateLayer is None:
            return
        self.animateLayer.triggerRepaint()
        canvas = self._gv.iface.mapCanvas()
        canvas.refresh()
        canvas.update()
        self.currentStillNumber += 1
        base, suffix = os.path.splitext(self.stillFileBase)
        nextStillFile = base + '{0:05d}'.format(self.currentStillNumber) + suffix
        # this does not capture the title
        #self._gv.iface.mapCanvas().saveAsImage(nextStillFile)
        composingAnimation = self._dlg.printAnimation.isChecked()
        if composingAnimation:
            proj = QgsProject.instance()
            # remove layout if any
            try:
                proj.layoutManager().removeLayout(self.animationLayout)
            except:
                pass
            # clean up old layout
            self.animationLayout = None
            if self.animationTemplateDirty:
                self.rereadAnimationTemplate()
            title = 'Animation {0}'.format(self.compositionCount)
            self.compositionCount += 1
            self.animationLayout = QgsPrintLayout(proj)
            self.animationLayout.initializeDefaults()
            self.animationLayout.setName(title)
            self.setDateInTemplate()
            _ = self.animationLayout.loadFromTemplate(self.animationDOM, QgsReadWriteContext())
            ok = proj.layoutManager().addLayout(self.animationLayout)
            if not ok:
                QSWATUtils.error('Failed to add animation layout to layout manager.  Try removing some.', self._gv.isBatch)
                return
            exporter = QgsLayoutExporter(self.animationLayout)
            settings = QgsLayoutExporter.ImageExportSettings()
            settings.exportMetadata = False
            res = exporter.exportToImage(nextStillFile,  settings)
            if res != QgsLayoutExporter.Success:
                QSWATUtils.error('Failed with result {1} to save layout as image file {0}'.format(nextStillFile, res), self._gv.isBatch)
        else:
            # tempting bot omits canvas title
            # canvas.saveAsImage(nextStillFile)
            canvasId = canvas.winId()
            screen = QGuiApplication.primaryScreen()
            pixMap = screen.grabWindow(canvasId)
            pixMap.save(nextStillFile)
        
        # no longer used
    #===========================================================================
    # def minMax(self, layer, var):
    #     """
    #     Return minimum and maximum of values for var in layer.
    #     
    #     Subbasin values of 0 indicate subbasins upstream from inlets and are ignored.
    #     """
    #     minv = float('inf')
    #     maxv = 0
    #     for f in layer.getFeatures():
    #         sub = f.attribute(QSWATTopology._SUBBASIN)
    #         if sub == 0:
    #             continue
    #         val = f.attribute(var)
    #         minv = min(minv, val)
    #         maxv = max(maxv, val)
    #     # increase/decrease by 1% to ensure no rounding errors cause values to be outside all ranges
    #     maxv *= 1.01
    #     minv *= 0.99
    #     return minv, maxv
    #===========================================================================
    
    # no longer used
    #===========================================================================
    # def dataList(self, var):
    #     """Make list of data values for var from resultsData for creating Jenks breaks."""
    #     res = []
    #     for subvals in self.resultsData.values():
    #         res.append(subvals[var])
    #     return res
    #===========================================================================
    
    def makeSymbologyForRange(self, minv, maxv, colour, precision):
        """Create a range from minv to maxv with the colour."""
        base = self.selectBase()
        if base == Parameters._RIVS:
            props = {'width_expression': QSWATTopology._PENWIDTH}
            symbol = QgsLineSymbol.createSimple(props)
            symbol.setWidth(1.0)
        else:
            symbol = QgsFillSymbol()
        symbol.setColor(colour)
        if precision >= 0:
            strng = '{0:.' + str(precision) + 'F} - {1:.' + str(precision) + 'F}'
            # minv and maxv came from numpy: make them normal floats
            title = strng.format(float(minv), float(maxv))
        else:
            factor = int(10 ** abs(precision))
            minv1 = int(minv / factor + 0.5) * factor
            maxv1 = int(maxv / factor + 0.5) * factor
            title = '{0} - {1}'.format(minv1, maxv1)
        rng = QgsRendererRange(minv, maxv, symbol, title)
        return rng
    
    def chooseColorRamp(self, table, var):
        """Select a colour ramp."""
        chaWater = ['floin', 'floout', 'evap', 'tloss']
        aqWater = ['flo', 'stor', 'rchrg', 'seep', 'revap' 'flo_cha', 'flo_res', 'flo_ls']
        wbWater = ['snowmlt', 'sq_gen', 'latq', 'wtryld', 'perc', 'tloss', 'sq_cont', 'sw', 
                   'qtile', 'irr', 'sq_run', 'lq_run', 'ovbank', 'surqcha', 'surqres', 
                   'surq_ls', 'latq_cha', 'latq_res', 'latq_ls']
        wbPrecip = ['prec', 'snow', 'et', 'eplant', 'esoil', 'pet']
        style = QgsStyle().defaultStyle()
        if table.startswith('channel') and var not in chaWater or \
            table.startswith('aquifer') and var not in aqWater or \
            '_ls_' in table or \
            '_nb_' in table or \
            '_wb_' in table and var not in wbWater and var not in wbPrecip:
            # sediments and pollutants
            ramp = style.colorRamp('RdYlGn').clone()
            ramp.invert()
            return ramp
        elif table.startswith('channel') and var in chaWater or \
            table.startswith('aquifer') and var in aqWater or \
            '_wb_' in table and var in wbWater:
            # water
            return style.colorRamp('YlGnBu')
        elif '_wb_' in table and var in wbPrecip:
            # precipitation and transpiration:
            return style.colorRamp('GnBu')
        else:
            return style.colorRamp('YlOrRd')
        
    def modeChange(self):
        """Main tab has changed.  Show/hide Animation group."""
        root = QgsProject.instance().layerTreeRoot()
        expandAnimation = self._dlg.tabWidget.currentIndex() == 1
        animationGroup = root.findGroup(QSWATUtils._ANIMATION_GROUP_NAME)
        animationGroup.setItemVisibilityCheckedRecursive(expandAnimation)
        # model = QgsLayerTreeModel(root)
        # view = self._gv.iface.layerTreeView()
        # TODO: how to link model and view so as to be able to expand the animation group? 
            
    def makeResults(self):
        """
        Create a results file and display.
        
        Only creates a new file if the variables have changed.
        If variables unchanged, only makes and writes summary data if necessary.
        """
        if self.table == '':
            QSWATUtils.information('Please choose a SWAT output table', self._gv.isBatch)
            return
        if self._dlg.resultsFileEdit.text() == '':
            QSWATUtils.information('Please choose a results file', self._gv.isBatch)
            return
        if self._dlg.variableList.count() == 0:
            QSWATUtils.information('Please choose some variables', self._gv.isBatch)
            return
        if len(self._dlg.variableList.selectedItems()) == 0:
            QSWATUtils.information('Please select a variable for display', self._gv.isBatch)
            return
        if not self.setPeriods():
            return
        self.resultsFileUpToDate = self.resultsFileUpToDate and self.resultsFile == self._dlg.resultsFileEdit.text()
        if not self.resultsFileUpToDate or not self.periodsUpToDate:
            self.readData('', True, self.table, '', '')
            self.periodsUpToDate = True
        if self.summaryChanged:
            self.summariseData('', True)
        if self.resultsFileUpToDate and self.resultsLayerExists():
            if self.summaryChanged:
                self.updateResultsFile()
        else:
            if self.createResultsFile():
                self.resultsFileUpToDate = True
            else:
                return
        self.colourResultsFile()
        
    def printResults(self):
        """Create print composer by instantiating template file."""
        proj = QgsProject.instance()
        root = proj.layerTreeRoot()
        resultsLayers = QSWATUtils.getLayersInGroup(QSWATUtils._RESULTS_GROUP_NAME, root)
        watershedLayers = QSWATUtils.getLayersInGroup(QSWATUtils._WATERSHED_GROUP_NAME, root, visible=True)
        # choose template file and set its width and height
        # width and height here need to be updated if template file is changed
        count = self._dlg.printCount.value()
        if count == 1:
            if self._dlg.landscapeButton.isChecked():
                templ = '1Landscape.qpt'
                width = 230.0
                height = 160.0
            else:
                templ = '1Portrait.qpt'
                width = 190.0
                height = 200.0
        elif count == 2:
            if self._dlg.landscapeButton.isChecked():
                templ = '2Landscape.qpt'
                width = 125.0
                height = 120.0
            else:
                templ = '2Portrait.qpt'
                width = 150.0
                height = 120.0
        elif count == 3:
            if self._dlg.landscapeButton.isChecked():
                templ = '3Landscape.qpt'
                width = 90.0
                height = 110.0
            else:
                templ = '3Portrait.qpt'
                width = 150.0
                height = 80.0
        elif count == 4:
            if self._dlg.landscapeButton.isChecked():
                templ = '4Landscape.qpt'
                width = 95.0
                height = 80.0
            else:
                templ = '4Portrait.qpt'
                width = 85.0
                height = 85.0
        elif count == 6:
            if self._dlg.landscapeButton.isChecked():
                templ = '6Landscape.qpt'
                width = 90.0
                height = 40.0
            else:
                templ = '6Portrait.qpt'
                width = 55.0
                height = 80.0
        else:
            QSWATUtils.error('There are composition templates only for 1, 2, 3, 4 or 6 result maps, not for {0}'.format(count), self._gv.isBatch)
            return
        templateIn = QSWATUtils.join(self._gv.plugin_dir, 'PrintTemplate' + templ)
        templateOut = QSWATUtils.join(self._gv.resultsDir, self.title + templ)
        # make substitution table
        subs = dict()
        northArrow = QSWATUtils.join(os.getenv('OSGEO4W_ROOT'), Visualise._NORTHARROW)
        if not os.path.isfile(northArrow):
            # may be qgis-ltr for example
            northArrowRel = Visualise._NORTHARROW.replace('qgis', QSWATUtils.qgisName(), 1)
            northArrow = QSWATUtils.join(os.getenv('OSGEO4W_ROOT'), northArrowRel)
        if not os.path.isfile(northArrow):
            QSWATUtils.error('Failed to find north arrow {0}.  You will need to repair the layout.'.format(northArrow), self._gv.isBatch)
        subs['%%NorthArrow%%'] = northArrow
        subs['%%ProjectName%%'] = self.title
        numLayers = len(resultsLayers)
        if count > numLayers:
            QSWATUtils.error(u'You want to make a print of {0} maps, but you only have {1} results layers'.format(count, numLayers), self._gv.isBatch)
            return
        extent = self._gv.iface.mapCanvas().extent()
        xmax = extent.xMaximum()
        xmin = extent.xMinimum()
        ymin = extent.yMinimum()
        ymax = extent.yMaximum()
        QSWATUtils.loginfo('Map canvas extent {0}, {1}, {2}, {3}'.format(str(int(xmin + 0.5)), str(int(ymin + 0.5)), 
                                                                         str(int(xmax + 0.5)), str(int(ymax + 0.5))))
        # need to expand either x or y extent to fit map shape
        xdiff = ((ymax - ymin) / height) * width - (xmax - xmin)
        if xdiff > 0:
            # need to expand x extent
            xmin = xmin - xdiff / 2
            xmax = xmax + xdiff / 2
        else:
            # expand y extent
            ydiff = (((xmax - xmin) / width) * height) - (ymax - ymin)
            ymin = ymin - ydiff / 2
            ymax = ymax + ydiff / 2
        QSWATUtils.loginfo('Map extent set to {0}, {1}, {2}, {3}'.format(str(int(xmin + 0.5)), str(int(ymin + 0.5)), 
                                                                         str(int(xmax + 0.5)), str(int(ymax + 0.5))))
        # estimate of segment size for scale
        # aim is approx 10mm for 1 segment
        # we make size a power of 10 so that segments are 1km, or 10, or 100, etc.
        segSize = 10 ** int(math.log10((xmax - xmin) / (width / 10)) + 0.5)
        layerStr = '<Layer source="{0}" provider="ogr" name="{1}">{2}</Layer>'
        for i in range(count):
            layer = resultsLayers[i].layer()
            subs['%%LayerId{0}%%'.format(i)] = layer.id()
            subs['%%LayerName{0}%%'.format(i)] = layer.name()
            subs['%%YMin{0}%%'.format(i)] = str(ymin)
            subs['%%XMin{0}%%'.format(i)] = str(xmin)
            subs['%%YMax{0}%%'.format(i)] = str(ymax)
            subs['%%XMax{0}%%'.format(i)] = str(xmax)
            subs['%%ScaleSegSize%%'] = str(segSize)
            subs['%%Layer{0}%%'.format(i)] = layerStr.format(QSWATUtils.layerFilename(layer), layer.name(), layer.id())
        for i in range(6):  # 6 entries in template for background layers
            if i < len(watershedLayers):
                wLayer = watershedLayers[i].layer()
                subs['%%WshedLayer{0}%%'.format(i)] = layerStr.format(QSWATUtils.layerFilename(wLayer), wLayer.name(), wLayer.id())
            else:  # remove unused ones
                subs['%%WshedLayer{0}%%'.format(i)] = ''
        with open(templateIn, 'rU') as inFile:
            with open(templateOut, 'w') as outFile:
                for line in inFile:
                    outFile.write(Visualise.replaceInLine(line, subs))
        QSWATUtils.loginfo('Print composer template {0} written'.format(templateOut))
        templateDoc = QDomDocument()
        f = QFile(templateOut)
        if f.open(QIODevice.ReadOnly):
            OK = templateDoc.setContent(f)
            if not OK:
                QSWATUtils.error('Cannot parse template file {0}'.format(templateOut), self._gv.isBatch)
                return
        else:
            QSWATUtils.error('Cannot open template file {0}'.format(templateOut), self._gv.isBatch) 
            return 
        title = '{0}{1} {2}'.format(self.title, templ, str(self.compositionCount))
        self.compositionCount += 1
        layout = QgsPrintLayout(proj)
        layout.initializeDefaults()
        layout.setName(title)
        items = layout.loadFromTemplate(templateDoc, QgsReadWriteContext())
        ok = proj.layoutManager().addLayout(layout)
        if not ok:
            QSWATUtils.error('Failed to add layout to layout manager.  Try removing some.', self._gv.isBatch)
            return
        designer = self._gv.iface.openLayoutDesigner(layout=layout)
        # if you quit from layout manager and then try to make another layout, 
        # the pointer gets reused and there is a 'destroyed by C==' error
        # This prevents the reuse.
        layout = None
        
    @staticmethod
    def replaceInLine(inLine, table):
        """Use table of replacements to replace keys with itsms in returned line."""
        for patt, sub in table.items():
            inLine = inLine.replace(patt, sub)
        return inLine
    
    def changeAnimationMode(self):
        """Reveal or hide compose options group."""
        if self._dlg.printAnimation.isChecked():
            self._dlg.composeOptions.setVisible(True)
            root = QgsProject.instance().layerTreeRoot()
            self._dlg.composeCount.setValue(QSWATUtils.countLayersInGroup(QSWATUtils._ANIMATION_GROUP_NAME, root))
        else:
            self._dlg.composeOptions.setVisible(False)
               
    def setupAnimateLayer(self):
        """
        Set up for animation.
        
        Collect animation data from database table according to animation variable; 
        set slider minimum and maximum;
        create animation layer;
        set speed accoring to spin box;
        set slider at minimum and display data for start time.
        """
        if self._dlg.animationVariableCombo.currentText() == '':
            return
        # can take a while so set a wait cursor
        self._dlg.setCursor(Qt.WaitCursor)
        self.doRewind()
        self._dlg.calculateLabel.setText('Calculating breaks ...')
        self._dlg.repaint()
        try:
            if not self.setPeriods():
                return
            self.animateVar = self._dlg.animationVariableCombo.currentText()
            if not self.createAnimationLayer():
                return
            lid = self.animateLayer.id()
            self.readData(lid, False, self.table, self.animateVar, '')
            self.summariseData(lid, False)
            if self.isDaily:
                animateLength = self.periodDays
            elif self.isAnnual:
                animateLength = int(self.periodYears + 0.5)
            elif self.isMonthly:
                animateLength = int(self.periodMonths + 0.5)
            else:
                animateLength = 0
            self._dlg.slider.setMinimum(1)
            self._dlg.slider.setMaximum(animateLength)
            self.colourAnimationLayer()
            self._dlg.slider.setValue(1)
            sleep = self._dlg.spinBox.value()
            self.changeSpeed(sleep)
            self.resetSlider()
            self.changeAnimate()
        finally:
            self._dlg.calculateLabel.setText('')
            self._dlg.setCursor(Qt.ArrowCursor)
            
    def saveVideo(self):
        """Save animated GIF if still files found."""
        # capture final frame
        self.capture()
        # remove animation layout
        try:
            QgsProject.instance().layoutManager().removeLayout(self.animationLayout)
        except:
            pass
        fileNames = sorted((fn for fn in os.listdir(self._gv.pngDir) if fn.endswith('.png')))
        if fileNames == []:
            return
        if self._dlg.printAnimation.isChecked():
            base = QSWATUtils.join(self._gv.resultsDir, 'Video.gif')
            self.videoFile = QSWATUtils.nextFileName(base, 0)[0]
        else:
            resultsDir = os.path.split(self.db)[0]
            self.videoFile = QSWATUtils.join(resultsDir, self.animateVar + 'Video.gif')
        try:
            os.remove(self.videoFile)
        except:
            pass
        period = 1.0 / self._dlg.spinBox.value()
        try:
            with imageio.get_writer('file://' + self.videoFile, mode='I', loop=1, duration=period) as writer:
                for filename in fileNames:
                    image = imageio.imread(QSWATUtils.join(self._gv.pngDir, filename))
                    writer.append_data(image)
            # clear the png files:
            self.clearPngDir()
            QSWATUtils.information('Animated gif {0} written'.format(self.videoFile), self._gv.isBatch)
        except Exception:
            self.videoFile = ''
            QSWATUtils.error("""
            Failed to generate animated gif: {0}.
            The .png files are in {1}: suggest you try using GIMP.
            """.format(traceback.format_exc(), self._gv.pngDir), self._gv.isBatch)
        
    def doPlay(self):
        """Set animating and not pause."""
        if self._dlg.animationVariableCombo.currentText() == '':
            QSWATUtils.information('Please choose an animation variable', self._gv.isBatch)
            return
        self.animating = True
        self.animationPaused = False
        
    def doPause(self):
        """If animating change pause from on to off, or off to on."""
        if self.animating:
            self.animationPaused = not self.animationPaused
            
    def doRewind(self):
        """Turn off animating and pause and set slider to minimum."""
        self.animating = False
        self.animationPaused = False
        self.resetSlider()
        
    def doStep(self):
        """Move slide one step to right unless at maximum."""
        if self.animating and not self.animationPaused:
            val = self._dlg.slider.value()
            if val < self._dlg.slider.maximum():
                self._dlg.slider.setValue(val + 1)
                
    def animateStepLeft(self):
        """Stop any running animation and if possible move the animation slider one step left."""
        if self._dlg.tabWidget.currentIndex() == 1:
            self.animating = False
            self.animationPaused = False
            val = self._dlg.slider.value()
            if val > self._dlg.slider.minimum():
                self._dlg.slider.setValue(val - 1)
                
    def animateStepRight(self):
        """Stop any running animation and if possible move the animation slider one step right."""
        if self._dlg.tabWidget.currentIndex() == 1:
            self.animating = False
            self.animationPaused = False
            val = self._dlg.slider.value()
            if val < self._dlg.slider.maximum():
                self._dlg.slider.setValue(val + 1)
    
    def changeSpeed(self, val):
        """
        Starts or restarts the timer with speed set to val.
        
        Runs in a try ... except so that timer gets stopped if any exception.
        """
        try:
            self.animateTimer.start(1000 // val)
        except Exception:
            self.animating = False
            self.animateTimer.stop()
            # raise last exception again
            raise
           
    def pressSlider(self):
        """Turn off animating and pause."""
        self.animating = False
        self.animationPaused = False
        
    def resetSlider(self):
        """Move slide to minimum."""
        self._dlg.slider.setValue(self._dlg.slider.minimum())
        
    def sliderValToDate(self):
        """Convert slider value to date."""
        if self.isDaily:
            return self.addDays( self.julianStartDay + self._dlg.slider.value() - 1,  self.startYear)
        elif self.isAnnual:
            return  self.startYear + self._dlg.slider.value() - 1
        elif self.isMonthly:
            totalMonths =  self.startMonth + self._dlg.slider.value() - 2
            year = totalMonths // 12
            month = totalMonths % 12 + 1
            return ( self.startYear + year) * 100 + month
        else:
            return self.startYear
            
    def addDays(self, days, year):
        """Make Julian date from year + days."""
        leapAdjust = 1 if self.isLeap(year) else 0
        lenYear = 365 + leapAdjust
        if days <= lenYear:
            return (year) * 1000 + days
        else:
            return self.addDays(days - lenYear, year + 1)
            
    def julianToDate(self, day, year):
        """
        Return datetime.date from year and number of days.
        
        The day may exceed the length of year, in which case a later year
        will be returned.
        """
        if day <= 31:
            return date(year, 1, day)
        day -= 31
        leapAdjust = 1 if self.isLeap(year) else 0
        if day <= 28 + leapAdjust:
            return date(year, 2, day)
        day -= 28 + leapAdjust
        if day <= 31:
            return date(year, 3, day)
        day -= 31
        if day <= 30:
            return date(year, 4, day)
        day -= 30
        if day <= 31:
            return date(year, 5, day)
        day -= 31
        if day <= 30:
            return date(year, 6, day)
        day -= 30
        if day <= 31:
            return date(year, 7, day)
        day -= 31
        if day <= 31:
            return date(year, 8, day)
        day -= 31
        if day <= 30:
            return date(year, 9, day)
        day -= 30
        if day <= 31:
            return date(year, 10, day)
        day -= 31
        if day <= 30:
            return date(year, 11, day)
        day -= 30
        if day <= 31:
            return date(year, 12, day)
        else:
            return self.julianToDate(day - 31, year + 1)
        
    def dateToString(self, dat):
        """Convert integer date to string."""
        if self.isDaily:
            return self.julianToDate(dat%1000, dat//1000).strftime("%d %B %Y")
        if self.isMonthly:
            return date(dat//100, dat%100, 1).strftime("%B %Y")
        # annual or average annual
        return str(dat)

    def record(self):
        """Switch between recording and not."""
        self.capturing = not self.capturing
        if self.capturing:
            # clear any existing png files (can be left eg if making gif failed)
            self.clearPngDir()
            if self._dlg.printAnimation.isChecked():
                self.createAnimationComposition()
            self._dlg.recordButton.setStyleSheet('background-color: red; border: none;')
            self._dlg.recordLabel.setText('Stop recording')
            self._dlg.playButton.setEnabled(False)
        else:
            self._dlg.setCursor(Qt.WaitCursor)
            self._dlg.recordButton.setStyleSheet('background-color: green; border: none;')
            self._dlg.recordLabel.setText('Start recording')
            self.saveVideo()
            self._dlg.playButton.setEnabled(True)
            self._dlg.setCursor(Qt.ArrowCursor)
    
    def playRecording(self):
        """Use default application to play video file (an animated gif)."""
        # stop recording if necessary
        if self.capturing:
            self.record()
        if not os.path.exists(self.videoFile):
            QSWATUtils.information('No video file for {0} exists at present'.format(self.animateVar), self._gv.isBatch)
            return
        if os.name == 'nt': # Windows
            os.startfile(self.videoFile)
        elif os.name == 'posix': # Linux
            subprocess.call(('xdg-open', self.videoFile))
    
    def changeSummary(self):
        """Flag change to summary method."""
        self.summaryChanged = True
        
    def changeRivRenderer(self):
        """If user changes the stream renderer, flag to retain colour scheme."""
        if not self.internalChangeToRivRenderer:
            self.keepRivColours = True
        
    def changeSubRenderer(self):
        """If user changes the subbasin renderer, flag to retain colour scheme."""
        if not self.internalChangeToSubRenderer:
            self.keepSubColours = True
        
    def changeLSURenderer(self):
        """If user changes the LSU renderer, flag to retain colour scheme."""
        if not self.internalChangeToLSURenderer:
            self.keepLSUColours = True
        
    def changeHRURenderer(self):
        """If user changes the HRU renderer, flag to retain colour scheme."""
        if not self.internalChangeToHRURenderer:
            self.keepHRUColours = True
            
    def updateCurrentPlotRow(self, colChanged):
        """
        Update current plot row according to the colChanged index.
        
        If there are no rows, first makes one.
        """
        if not self.plotting():
            return
        indexes = self._dlg.tableWidget.selectedIndexes()
        if not indexes or indexes == []:
            self.doAddPlot()
            indexes = self._dlg.tableWidget.selectedIndexes()
        row = indexes[0].row()
        if colChanged == 0:
            self._dlg.tableWidget.item(row, 0).setText(self.scenario)
        elif colChanged == 1:
            if self._dlg.tableWidget.item(row, 1).text() == '-':
                # observed plot: do not change
                return
            self._dlg.tableWidget.item(row, 1).setText(self.table)
            self._dlg.unitLabel.setText(self.tableUnitName(self.table))
            self._dlg.tableWidget.item(row, 2).setText('')
            self._dlg.tableWidget.item(row, 3).setText('')
        elif colChanged == 2:
            self._dlg.tableWidget.item(row, 2).setText(self._dlg.unitPlot.currentText())
        else:
            self._dlg.tableWidget.item(row, 3).setText(self._dlg.variablePlot.currentText())
            
    _unitNames = {'basin_': 'Basin',
                  'lsunit_': 'LSU',
                  'hru_': 'HRU',
                  'region_': 'Region',
                  'channel_sd_': 'Channel_SD',
                  #'_sd': 'HRU-LTE',
                  'channel_': 'Channel',
                  'aquifer_': 'Aquifer',
                  'reservoir_': 'Reservoir',
                  'wetland_': 'Wetland',
                  'hydin_': 'Hydrograph in',
                  'hydout_': 'Hydrograph out',
                  'ru_': 'Routing unit'}
            
    def tableUnitName(self, table):
        """Return name for table unit."""
        for key, uname in self._unitNames.items():
            if key in table:
                return uname 
        return 'Unknown'
    
    def countPlots(self):
        """Return number of non-observed plots."""
        size = self._dlg.tableWidget.rowCount()
        result = size
        for row in range(size):
            if self._dlg.tableWidget.item(row, 1).text() == '-':
                # observed row
                result -= 1
        return result
            
    def doAddPlot(self):
        """Add a plot row and make it current."""
        unit = self._dlg.unitPlot.currentText()
        size = self._dlg.tableWidget.rowCount()
        if size > 0 and self._dlg.tableWidget.item(size-1, 1).text() == '-':
            # last plot was observed: need to reset variables
            self.table = ''
            self.setVariables()
        var = self._dlg.variablePlot.currentText()
        self._dlg.tableWidget.insertRow(size)
        self._dlg.tableWidget.setItem(size, 0, QTableWidgetItem(self.scenario))
        self._dlg.tableWidget.setItem(size, 1, QTableWidgetItem(self.table))
        self._dlg.tableWidget.setItem(size, 2, QTableWidgetItem(unit))
        self._dlg.tableWidget.setItem(size, 3, QTableWidgetItem(var))
        for col in range(4):
            self._dlg.tableWidget.item(size, col).setTextAlignment(Qt.AlignCenter)
        self._dlg.tableWidget.selectRow(size)
        if self.countPlots() == 1:
            # just added first row - reduce tables to those with same frequency
            if Visualise.tableIsDaily(self.table):
                self.restrictOutputTablesByTerminator('_day')
            elif Visualise.tableIsMonthly(self.table):
                self.restrictOutputTablesByTerminator('_mon')
            elif Visualise.tableIsAnnual(self.table):
                self.restrictOutputTablesByTerminator('_yr')
                
    def getPlotTable(self):
        """Return the table of a non-observed plot, or empty string if none."""
        for row in range(self._dlg.tableWidget.rowCount()):
            table = self._dlg.tableWidget.item(row, 1).text()
            if table == '-':  # observed
                continue
            else:
                return table
        return ''
        
    def doDelPlot(self):
        """Delete current plot row."""
        indexes = self._dlg.tableWidget.selectedIndexes()
        if not indexes or indexes == []:
            QSWATUtils.information('Please select a row for deletion', self._gv.isBatch)
            return
        row = indexes[0].row()
        if row in range(self._dlg.tableWidget.rowCount()):
            self._dlg.tableWidget.removeRow(row)
        if self.countPlots() == 0:
            # no non-observed plots - restore output tables combo so any frequency can be chosen
            self.populateOutputTables()
        
    def doCopyPlot(self):
        """Add a copy of the current plot row and make it current."""
        indexes = self._dlg.tableWidget.selectedIndexes()
        if not indexes or indexes == []:
            QSWATUtils.information('Please select a row to copy', self._gv.isBatch)
            return
        row = indexes[0].row()
        size = self._dlg.tableWidget.rowCount()
        if row in range(size):
            self._dlg.tableWidget.insertRow(size)
            for col in range(4):
                self._dlg.tableWidget.setItem(size, col, QTableWidgetItem(self._dlg.tableWidget.item(row, col)))
        self._dlg.tableWidget.selectRow(size)
        
    def doUpPlot(self):
        """Move current plot row up 1 place and keep it current."""
        indexes = self._dlg.tableWidget.selectedIndexes()
        if not indexes or indexes == []:
            QSWATUtils.information('Please select a row to move up', self._gv.isBatch)
            return
        row = indexes[0].row()
        if 1 <= row < self._dlg.tableWidget.rowCount():
            for col in range(4):
                item = self._dlg.tableWidget.takeItem(row, col)
                self._dlg.tableWidget.setItem(row, col, self._dlg.tableWidget.takeItem(row-1, col))
                self._dlg.tableWidget.setItem(row-1, col, item)
        self._dlg.tableWidget.selectRow(row-1)
                
    def doDownPlot(self):
        """Move current plot row down 1 place and keep it current."""
        indexes = self._dlg.tableWidget.selectedIndexes()
        if not indexes or indexes == []:
            QSWATUtils.information('Please select a row to move down', self._gv.isBatch)
            return
        row = indexes[0].row()
        if 0 <= row < self._dlg.tableWidget.rowCount() - 1:
            for col in range(4):
                item = self._dlg.tableWidget.takeItem(row, col)
                self._dlg.tableWidget.setItem(row, col, self._dlg.tableWidget.takeItem(row+1, col))
                self._dlg.tableWidget.setItem(row+1, col, item)
        self._dlg.tableWidget.selectRow(row+1)
        
    def addObervedPlot(self):
        """Add a row for an observed plot, and make it current."""
        if not os.path.exists(self.observedFileName):
            return
        self.setObservedVars()
        size = self._dlg.tableWidget.rowCount()
        self._dlg.tableWidget.insertRow(size)
        self._dlg.tableWidget.setItem(size, 0, QTableWidgetItem('observed'))
        self._dlg.tableWidget.setItem(size, 1, QTableWidgetItem('-'))
        self._dlg.tableWidget.setItem(size, 2, QTableWidgetItem('-'))
        self._dlg.tableWidget.setItem(size, 3, QTableWidgetItem(self._dlg.variablePlot.currentText()))
        for col in range(4):
            self._dlg.tableWidget.item(size, col).setTextAlignment(Qt.AlignHCenter)
        self._dlg.tableWidget.selectRow(size)
        
    def setObservedVars(self):
        """Add variables from 1st line of observed data file, ignoring 'date' if it occurs as the first column."""
        with open(self.observedFileName, 'r') as obs:
            line = obs.readline()
            varz = line.split(',')
            if len(varz) == 0:
                QSWATUtils.error('Cannot find variables in first line of observed data file {0}'.format(self.observedFileName), self._gv.isBatch)
                return
            col1 = varz[0].strip().lower()
            start = 1 if col1 == 'date' else 0
            self._dlg.variablePlot.clear()
            for var in varz[start:]:
                self._dlg.variablePlot.addItem(var.strip())
            
    def readObservedFile(self, var):
        """
        Read data for var from observed data file, returning a list of data as strings.
        
        Note that dates are not checked even if present in the observed data file.
        """
        result = []
        with open(self.observedFileName, 'r') as obs:
            line = obs.readline()
            varz = [var1.strip() for var1 in line.split(',')]
            if len(varz) == 0:
                QSWATUtils.error('Cannot find variables in first line of observed data file {0}'.format(self.observedFileName), self._gv.isBatch)
                return result
            try:
                idx = varz.index(var)
            except Exception:
                QSWATUtils.error('Cannot find variable {0} in first line of observed data file {1}'.format(var, self.observedFileName), self._gv.isBatch)
                return result
            while line:
                line = obs.readline()
                vals = line.split(',')
                if 0 <= idx < len(vals):
                    result.append(vals[idx].strip()) # strip any newline
                else:
                    break # finish if e.g. a blank line
        return result
        
        
    # code from http://danieljlewis.org/files/2010/06/Jenks.pdf
    # described at http://danieljlewis.org/2010/06/07/jenks-natural-breaks-algorithm-in-python/
    # amended following style of http://www.macwright.org/simple-statistics/docs/simple_statistics.html#section-116
 
    # no longer used - replaced by Cython
    #===========================================================================
    # @staticmethod
    # def getJenksBreaks( dataList, numClass ):
    #     """Return Jenks breaks for dataList with numClass classes."""
    #     if not dataList:
    #         return [], 0
    #     # Use of sample unfortunate because gives poor animation results.
    #     # Tends to overestimate lower limit and underestimate upper limit, and areas go white in animation.
    #     # But can take a long time to calculate!
    #     # QGIS internal code uses 1000 here but 4000 runs in reasonable time
    #     maxSize = 4000
    #     # use a sample if size exceeds maxSize
    #     size = len(dataList)
    #     if size > maxSize:
    #         origSize = size
    #         size = max(maxSize, size / 10)
    #         QSWATUtils.loginfo('Jenks breaks: using a sample of size {0!s} from {1!s}'.format(size, origSize))
    #         sample = random.sample(dataList, size)
    #     else:
    #         sample = dataList
    #     sample.sort()
    #     # at most one class: return singleton list
    #     if numClass <= 1:
    #         return [sample.last()]
    #     if numClass >= size:
    #         # nothing useful to do
    #         return sample
    #     lowerClassLimits = []
    #     varianceCombinations = []
    #     variance = 0
    #     for i in range(0,size+1):
    #         temp1 = []
    #         temp2 = []
    #         # initialize with lists of zeroes
    #         for j in range(0,numClass+1):
    #             temp1.append(0)
    #             temp2.append(0)
    #         lowerClassLimits.append(temp1)
    #         varianceCombinations.append(temp2)
    #     for i in range(1,numClass+1):
    #         lowerClassLimits[1][i] = 1
    #         varianceCombinations[1][i] = 0
    #         for j in range(2,size+1):
    #             varianceCombinations[j][i] = float('inf')
    #     for l in range(2,size+1):
    #         # sum of values seen so far
    #         summ = 0
    #         # sum of squares of values seen so far
    #         sumSquares = 0
    #         # for each potential number of classes. w is the number of data points considered so far
    #         w = 0
    #         i4 = 0
    #         for m in range(1,l+1):
    #             lowerClassLimit = l - m + 1
    #             val = float(sample[lowerClassLimit-1])
    #             w += 1
    #             summ += val
    #             sumSquares += val * val
    #             variance = sumSquares - (summ * summ) / w
    #             i4 = lowerClassLimit - 1
    #             if i4 != 0:
    #                 for j in range(2,numClass+1):
    #                     # if adding this element to an existing class will increase its variance beyond the limit, 
    #                     # break the class at this point, setting the lower_class_limit.
    #                     if varianceCombinations[l][j] >= (variance + varianceCombinations[i4][j - 1]):
    #                         lowerClassLimits[l][j] = lowerClassLimit
    #                         varianceCombinations[l][j] = variance + varianceCombinations[i4][j - 1]
    #         lowerClassLimits[l][1] = 1
    #         varianceCombinations[l][1] = variance
    #     k = size
    #     kclass = []
    #     for i in range(0,numClass+1):
    #         kclass.append(0)
    #     kclass[numClass] = float(sample[size - 1])
    #     countNum = numClass
    #     while countNum >= 2:#print "rank = " + str(lowerClassLimits[k][countNum])
    #         idx = int((lowerClassLimits[k][countNum]) - 2)
    #         #print "val = " + str(sample[idx])
    #         kclass[countNum - 1] = sample[idx]
    #         k = int((lowerClassLimits[k][countNum] - 1))
    #         countNum -= 1
    #     return kclass, sample[0]
    #===========================================================================
    
    # copied like above but not used
#===============================================================================
#     @staticmethod
#     def getGVF( sample, numClass ):
#         """
#         The Goodness of Variance Fit (GVF) is found by taking the
#         difference between the squared deviations
#         from the array mean (SDAM) and the squared deviations from the
#         class means (SDCM), and dividing by the SDAM
#         """
#         breaks = Visualise.getJenksBreaks(sample, numClass)
#         sample.sort()
#         size = len(sample)
#         listMean = sum(sample)/size
#         print listMean
#         SDAM = 0.0
#         for i in range(0,size):
#             sqDev = (sample[i] - listMean)**2
#             SDAM += sqDev
#         SDCM = 0.0
#         for i in range(0,numClass):
#             if breaks[i] == 0:
#                 classStart = 0
#             else:
#                 classStart = sample.index(breaks[i])
#             classStart += 1
#             classEnd = sample.index(breaks[i+1])
#             classList = sample[classStart:classEnd+1]
#         classMean = sum(classList)/len(classList)
#         print classMean
#         preSDCM = 0.0
#         for j in range(0,len(classList)):
#             sqDev2 = (classList[j] - classMean)**2
#             preSDCM += sqDev2
#             SDCM += preSDCM
#         return (SDAM - SDCM)/SDAM
# 
#     # written by Drew
#     # used after running getJenksBreaks()
#     @staticmethod
#     def classify(value, breaks):
#         """
#         Return index of value in breaks.
#         
#         Returns i such that
#         breaks = [] and i = -1, or
#         value < breaks[1] and i = 1, or 
#         breaks[i-1] <= value < break[i], or
#         value >= breaks[len(breaks) - 1] and i = len(breaks) - 1
#         """
#         for i in range(1, len(breaks)):
#             if value < breaks[i]:
#                 return i
#         return len(breaks) - 1 
#===============================================================================

    def setAnimateLayer(self):
        """Set self.animateLayer to first visible layer in Animations group, retitle as appropriate."""
        canvas = self._gv.iface.mapCanvas()
        root = QgsProject.instance().layerTreeRoot()
        animationLayers = QSWATUtils.getLayersInGroup(QSWATUtils._ANIMATION_GROUP_NAME, root, visible=True)
        if len(animationLayers) == 0:
            if self.mapTitle is not None:
                canvas.scene().removeItem(self.mapTitle)
                self.mapTitle = None
            self.animateLayer = None
            return
        for treeLayer in animationLayers:
            mapLayer = treeLayer.layer()
            if self.mapTitle is None:
                self.mapTitle = MapTitle(canvas, self.title, mapLayer)
                canvas.update()
                self.animateLayer = mapLayer
                return
            elif mapLayer == self.mapTitle.layer:
                # nothing to do
                return
            else:
                # first visible animation layer not current titleLayer
                canvas.scene().removeItem(self.mapTitle)
                dat = self.sliderValToDate()
                date = self.dateToString(dat)
                self.mapTitle = MapTitle(canvas, self.title, mapLayer, line2=date)
                canvas.update()
                self.animateLayer = mapLayer
                return
        # if we get here, no visible animation layers
        if self.mapTitle is not None:
            canvas.scene().removeItem(self.mapTitle)
            self.mapTitle = None
        self.animateLayer = None
        return     
    
    def clearAnimationDir(self):
        """Remove shape files from animation directory."""
        if os.path.exists(self._gv.animationDir):
            pattern = QSWATUtils.join(self._gv.animationDir, '*.shp')
            for f in glob.iglob(pattern):
                QSWATUtils.tryRemoveFiles(f)
                
    def clearPngDir(self):
        """Remove .png files from Png directory."""
        if os.path.exists(self._gv.pngDir):
            pattern = QSWATUtils.join(self._gv.pngDir, '*.png')
            for f in glob.iglob(pattern):
                try:
                    os.remove(f)
                except:
                    pass
        self.currentStillNumber = 0
        

class MapTitle(QgsMapCanvasItem):  # @UndefinedVariable
    
    """Item for displaying title at top left of map canvas."""
    
    def __init__(self, canvas, title, layer, line2=None):
        """Initialise rectangle for displaying project name, layer name,  plus line2, if any, below them."""
        super().__init__(canvas)
        ## normal font
        self.normFont = QFont()
        ## normal metrics object
        self.metrics = QFontMetricsF(self.normFont)
        # bold metrics object
        boldFont = QFont()
        boldFont.setBold(True)
        metricsBold = QFontMetricsF(boldFont)
        ## titled layer
        self.layer = layer
        ## project line of title
        self.line0 = 'Project: {0}'.format(title)
        ## First line of title
        self.line1 = layer.name()
        ## second line of title (or None)
        self.line2 = line2
        rect0 = metricsBold.boundingRect(self.line0)
        rect1 = self.metrics.boundingRect(self.line1)
        ## bounding rectange of first 2 lines 
        self.rect01 = QRectF(0, rect0.top() + rect0.height(),
                            max(rect0.width(), rect1.width()),
                            rect0.height() + rect1.height())
        ## bounding rectangle
        self.rect = None
        if line2 is None:
            self.rect = self.rect01
        else:
            self.updateLine2(line2)
    
    def paint(self, painter, option, widget):  # @UnusedVariable
        """Paint the text."""
#         if self.line2 is None:
#             painter.drawText(self.rect, Qt.AlignLeft, '{0}\n{1}'.format(self.line0, self.line1))
#         else:
#             painter.drawText(self.rect, Qt.AlignLeft, '{0}\n{1}\n{2}'.format(self.line0, self.line1, self.line2))
        text = QTextDocument()
        text.setDefaultFont(self.normFont)
        if self.line2 is None:
            text.setHtml('<p><b>{0}</b><br/>{1}</p>'.format(self.line0, self.line1))
        else:
            text.setHtml('<p><b>{0}</b><br/>{1}<br/>{2}</p>'.format(self.line0, self.line1, self.line2))
        text.drawContents(painter)

    def boundingRect(self):
        """Return the bounding rectangle."""
        return self.rect
    
    def updateLine2(self, line2):
        """Change second line."""
        self.line2 = line2
        rect2 = self.metrics.boundingRect(self.line2)
        self.rect = QRectF(0, self.rect01.top(), 
                            max(self.rect01.width(), rect2.width()), 
                            self.rect01.height() + rect2.height())
        

       
    