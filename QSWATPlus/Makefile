#/***************************************************************************
# QSWATPlus3
#
# Create SWAT+ inputs
#                             -------------------
#        begin                : 2014-07-18
#        copyright            : (C) 2014 by Chris George
#        email                : cgeorge@mcmaster.ca
# ***************************************************************************/
#
#/***************************************************************************
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU General Public License as published by  *
# *   the Free Software Foundation; either version 2 of the License, or     *
# *   (at your option) any later version.                                   *
# *                                                                         *
# ***************************************************************************/
# On Windows this makefile needs to be made using mingw32-make
# (since eg pyuic4 is a .bat script not recognised an an executable by a Unix-style make)
# On windows the command to generate .pyd from .pyx may have to be run in the 32-bit OSGeo4W shell
# For Linux the Makefile assumes it is being run in a 64-bit machine, with special code for 32-bit

#################################################
# Edit the following to match your sources lists
#################################################

#Add iso code for any locales you want to support here (space separated)
# default is no locales
# LOCALES = af
LOCALES =

# If locales are enabled, set the name of the lrelease binary on your system. If
# you have trouble compiling the translations, you may have to specify the full path to
# lrelease
#LRELEASE = lrelease
#LRELEASE = lrelease-qt4

# translation
SOURCES = $(PY_FILES)

PACKAGE = QSWATPlus

TESTOUTPUT = testdata/test

ifeq ($(QSWAT_PROJECT), QSWATPlus3_9)
	COMPILER = msvc
	METADATA = metadata3_9.txt
	PLUGINNAME = QSWATPlus3_9
	DOXYGEN = 'C:\Program Files\doxygen\bin\doxygen.exe'
	OBJ_FILES = $(PYX_FILES:.pyx=.cp39-win_amd64.pyd)
	BAT_FILES = $(addprefix ../, runnose.bat runtestpoly.bat runcovernose.bat runtestn.bat)
	TEST_FILES = $(addprefix ../, test_qswatplus.py test_dbutils.py test_polygonize.py test_polygonizeInC.py test_polygonizeInC2.py)
	HUC_FILES = $(addprefix ../, runHUC64.bat runHUC.py)
	EXTRAPACKAGES = imageio rtree
	QGISDIR = AppData/Roaming/QGIS/QGIS3/profiles/default
	CPFILE = cp -vuf
	CPDIR = cp -vufr
else ifeq ($(QSWAT_PROJECT), QSWATPlus3_64)
	COMPILER = msvc
	METADATA = metadata3_64.txt
	PLUGINNAME = QSWATPlus3_64
	DOXYGEN = 'C:\Program Files\doxygen\bin\doxygen.exe'
	OBJ_FILES = $(PYX_FILES:.pyx=.cp37-win_amd64.pyd)
	BAT_FILES = $(addprefix ../, runnose.bat runtestpoly.bat runcovernose.bat runtestn.bat)
	TEST_FILES = $(addprefix ../, test_qswatplus.py test_dbutils.py test_polygonize.py test_polygonizeInC.py test_polygonizeInC2.py)
	HUC_FILES = $(addprefix ../, runHUC64.bat runHUC.py)
	EXTRAPACKAGES = imageio rtree
	QGISDIR = AppData/Roaming/QGIS/QGIS3/profiles/default
	CPFILE = cp -vuf
	CPDIR = cp -vufr
else ifeq ($(QSWAT_PROJECT), QSWATPlus3_32)
	COMPILER = msvc
	METADATA = metadata3_32.txt
	PLUGINNAME = QSWATPlus3_32
	DOXYGEN = 'C:\Program Files\doxygen\bin\doxygen.exe'
	OBJ_FILES = $(PYX_FILES:.pyx=.cp37-win32.pyd)
	BAT_FILES = $(addprefix ../, runnose.bat runtestpoly.bat runcovernose.bat runtestn.bat)
	TEST_FILES = $(addprefix ../, test_qswatplus.py test_dbutils.py test_polygonize.py test_polygonizeInC.py test_polygonizeInC2.py)
	EXTRAPACKAGES = imageio rtree
	QGISDIR = AppData/Roaming/QGIS/QGIS3/profiles/default
	CPFILE = cp -vuf
	CPDIR = cp -vufr
else ifeq ($(QSWAT_PROJECT), QSWATPlusLinux3_64)
	COMPILER = unix
	METADATA = metadatalinux3_64.txt
	PLUGINNAME = QSWATPlusLinux3_64
	DOXYGEN = doxygen
	OBJ_FILES = $(PYX_FILES:.pyx=.cpython-311-x86_64-linux-gnu.so)
	BAT_FILES = $(addprefix ../, runtestn.sh runnose.sh)
	TEST_FILES = $(addprefix ../, test_qswatplus.py test_dbutils.py test_polygonize.py test_polygonizeInC.py test_polygonizeInC2.py)
	HUC_FILES = $(addprefix ../, runHUC.py)
	EXTRAPACKAGES = imageio
	QGISDIR = .local/share/QGIS/QGIS3/profiles/default
	TESTOUTPUT = $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)/$(PACKAGE)/testdata/test
	CPFILE = cp -vuf
	CPDIR = cp -vufR
else ifeq ($(QSWAT_PROJECT), QSWATPlusLinux3_32)
	COMPILER = unix
	METADATA = metadatalinux3_32.txt
	PLUGINNAME = QSWATPlusLinux3_32
	DOXYGEN = doxygen
	OBJ_FILES = $(PYX_FILES:.pyx=.cpython-38-i386-linux-gnu.so)
	BAT_FILES = $(addprefix ../, runtestn.sh runnose.sh)
	TEST_FILES = $(addprefix ../, test_qswatplus.py)
	HUC_FILES = $(addprefix ../, runHUC.py)
	EXTRAPACKAGES = imageio
	QGISDIR = .local/share/QGIS/QGIS3/profiles/default
	TESTOUTPUT = $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)/$(PACKAGE)/testdata/test
	CPFILE = cp -vuf
	CPDIR = cp -vufR
else ifeq ($(QSWAT_PROJECT), QSWATPlusMac3_64)
	COMPILER = unix
	METADATA = metadatamac3_64.txt
	PLUGINNAME = QSWATPlusMac3_64
	DOXYGEN = doxygen
	OBJ_FILES = $(PYX_FILES:.pyx=.cpython-39-darwin.so)
	BAT_FILES = $(addprefix ../, runtestn.sh)
	TEST_FILES = $(addprefix ../, test_qswatplus.py)
	HUC_FILES = $(addprefix ../, runHUC.py)
	EXTRAPACKAGES = imageio
	QGISDIR = Library/Application Support/QGIS/QGIS3/profiles/default
	CPFILE = rsync -av
	CPDIR = rsync -av
#else ifeq ($(QSWAT_PROJECT), QSWATPlusMac3_32)
#	COMPILER = unix
#	METADATA = metadatamac3_32.txt
#	PLUGINNAME = QSWATPlusMac3_32
#	DOXYGEN = doxygen
#	OBJ_FILES = $(PYX_FILES:.pyx=.cpython-38-i386-darwin.so)
#	BAT_FILES = 
#	EXTRAPACKAGES = imageio
#	QGISDIR=Library/Application Support/QGIS/QGIS3/profiles/default
#	CPFILE = rsync -av
#	CPDIR = rsync -av
endif

INIT_FILE =  __init__.py 

PY_FILES = \
	QSWATPlusMain.py qswatdialog.py cythoninit.py delineation.py delineationdialog.py hrus.py hrusdialog.py \
	outletsdialog.py exempt.py exemptdialog.py split.py splitdialog.py selectlu.py selectludialog.py parameters.py parametersdialog.py \
	elevationbands.py elevationbandsdialog.py selectsubs.py selectsubsdialog.py about.py aboutdialog.py visualise.py visualisedialog.py \
	QSWATBatch.py QSWATUtils.py DBUtils.py landscape.py landscapedialog.py floodplain.py polygonize.py QSWATTopology.py TauDEMUtils.py \
	globals.py raster.py swatgraph.py graphdialog.py graphdialog1.py setuppyx.py setuppyx3.9.py convertFromArc.py convertdialog.py exporttable.py exporttabledialog.py  \
	ui_convert.py ui_graph.py comparedialog.py gwflow.py gwflowdialog.py

PYX_FILES =  jenks.pyx dataInC.pyx polygonizeInC.pyx polygonizeInC2.pyx

C_FILES = $(PYX_FILES:.pyx=.c)

UI_FILES = ui_qswat.py ui_delineation.py ui_hrus.py ui_outlets.py ui_exempt.py ui_split.py ui_selectlu.py ui_parameters.py ui_elevationbands.py \
			ui_selectsubs.py ui_landscape.py ui_about.py ui_visualise.py ui_graph.py ui_graph1.py ui_convert.py ui_exporttable.py ui_comparescenarios.py \
			ui_gwflow.py

QML_FILES = dem.qml fullhrus.qml outlets.qml stream.qml subresults.qml wshed.qml existingwshed.qml floodwhite.qml grid.qml gridpoly.qml \
			drainchannels.qml drainarrows.qml channelandreservoir.qml channel.qml lsus.qml rivresults.qml \
			ptsrcandreservoir.qml lakes.qml lakesnores.qml polygons.qml

QPT_FILES = PrintTemplate1Landscape.qpt PrintTemplate1Portrait.qpt PrintTemplate2Landscape.qpt \
			PrintTemplate2Portrait.qpt PrintTemplate3Landscape.qpt PrintTemplate3Portrait.qpt \
			PrintTemplate4Landscape.qpt PrintTemplate4Portrait.qpt PrintTemplate6Landscape.qpt \
			PrintTemplate6Portrait.qpt

INI_FILES = gwflow.ini

EXTRAS = Changelog.txt swatplus32.png

EXTRA_DIRS =

COMPILED_RESOURCE_FILES = resources_rc.py

GLOBALDATA = GlobalData

TOOLS = Tools

TESTDATA = testdata

PEP8EXCLUDE=pydev,resources_rc.py,conf.py,third_party,ui


#################################################
# Normally you would not need to edit below here
#################################################

HELP = help/build/html

PLUGIN_UPLOAD = $(c)/plugin_upload.py

RESOURCES_SRC=$(shell grep '^ *<file' resources.qrc | sed 's@</file>@@g;s/.*>//g' | tr '\n' ' ')



HTML = html

default: deploy

compile: $(COMPILED_RESOURCE_FILES) $(OBJ_FILES)

%.cp39-win_amd64.pyd : %.pyx
	@echo
	@echo "------"
	@echo "Cython"
	@echo "------"
	python setuppyx3.9.py build_ext --inplace --compiler=$(COMPILER)

%.cp37-win_amd64.pyd : %.pyx
	@echo
	@echo "------"
	@echo "Cython"
	@echo "------"
	python setuppyx.py build_ext --inplace --compiler=$(COMPILER)

%.cp37-win32.pyd : %.pyx
	@echo
	@echo "------"
	@echo "Cython"
	@echo "------"
	python setuppyx.py build_ext --inplace --compiler=$(COMPILER)

%.cpython-311-x86_64-linux-gnu.so : %.pyx
	python3 setuppyx.py build_ext --inplace --compiler=$(COMPILER)

%.cpython-39-darwin.so : %.pyx
	@echo
	@echo "------"
	@echo "Cython"
	@echo "------"
	/usr/local/bin/python3.9 setuppyx.py build_ext --inplace --compiler=$(COMPILER)

# 32 bit Linux
# this is a hack to mimic what distutils.setup can do
%.cpython-38-i386-linux-gnu.so : %.pyx
	python3 setuppyx.py build_ext --inplace --compiler=$(COMPILER)
	mkdir -p build/temp.linux-i386-3.6
	i686-linux-gnu-gcc-7 -pthread -DNDEBUG -g -fwrapv -O2 -Wall -Wdate-time -D_FORTIFY_SOURCE=2 -fPIC -I/usr/include/python3.6m -c $*.c -o build/temp.linux-i386-3.6/$*.o	
	i686-linux-gnu-gcc-7 -pthread -shared -Wl,-O1 -Wl,-Bsymbolic-functions -Wl,-Bsymbolic-functions -Wl,-z,relro -Wdate-time -D_FORTIFY_SOURCE=2 build/temp.linux-i386-3.6/$*.o -o $@

# similar hack to 32-bit Linux
%.cpython-37m-darwin.so : %.pyx
	#python3 setuppyx.py build_ext --inplace --compiler=$(COMPILER)
	/usr/local/bin/cython *.pyx
	mkdir -p build/temp.macosx-10.14-x86_64-3.7
	xcrun -sdk macosx clang -arch x86_64 -Wno-unused-result -Wsign-compare -Wunreachable-code -fno-common -dynamic -DNDEBUG -g -fwrapv -O3 -Wall -I/Library/Python/3.7/site-packages/numpy/core/include -I/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.7/include/python3.7m -c $*.c -o build/temp.macosx-10.14-x86_64-3.7/$*.o
	xcrun -sdk macosx clang -arch x86_64 -Wno-unused-result -Wsign-compare -Wunreachable-code -fno-common -dynamiclib -DNDEBUG -g -fwrapv -O3 -Wall -L/Applications/QGIS3.10.app/Contents/Frameworks/Python.framework/Versions/3.7/lib -lpython3.7m build/temp.macosx-10.14-x86_64-3.7/$*.o -o $@



%_rc.py : %.qrc
	pyrcc5 -o $*_rc.py  $<

#%.py : %.ui
#	pyuic5 -o $@ $<
# instead of the above, run 
# the script make_uis.py in QGIS 
# to compile .ui files to .py


%.qm : %.ts
	$(LRELEASE) $<

# test: compile transcompile
test: compile
	@echo
	@echo "----------------------"
	@echo "Regression Test Suite"
	@echo "----------------------"

	@# Preceding dash means that make will continue in case of errors
	@-export PYTHONPATH=`pwd`:$(PYTHONPATH); \
		export QGIS_DEBUG=0; \
		export QGIS_LOG_FILE=/dev/null; \
		nosetests -v --with-id --with-coverage --cover-package=. \
		3>&1 1>&2 2>&3 3>&- || true
	@echo "----------------------"
	@echo "If you get a 'no module named qgis.core error, try sourcing"
	@echo "the helper script we have provided first then run make test."
	@echo "e.g. source run-env-linux.sh <path to qgis install>; make test"
	@echo "----------------------"

# deploy: archclean compile doc transcompile
# deploy: archclean compile
deploy: compile
	@echo
	@echo "------------------------------------------"
	@echo "Deploying plugin to your AppData/Roaming/QGIS/QGIS3/profiles/default directory."
	@echo "------------------------------------------"
	# The deploy  target only works on unix like operating system where
	# the Python plugin directory is located at:
	# $(HOME)/$(QGISDIR)/python/plugins
	mkdir -p "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)/$(PACKAGE)"
	$(CPFILE) $(INIT_FILE) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)"
	$(CPFILE) $(PY_FILES) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)/$(PACKAGE)"
	$(CPFILE) $(PYX_FILES) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)/$(PACKAGE)"
	$(CPFILE) $(OBJ_FILES) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)/$(PACKAGE)"
	$(CPFILE) $(UI_FILES) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)/$(PACKAGE)"
	$(CPFILE) $(QML_FILES) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)/$(PACKAGE)"
	$(CPFILE) $(QPT_FILES) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)/$(PACKAGE)"
	$(CPFILE) $(INI_FILES) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)/$(PACKAGE)"
	$(CPFILE) $(BAT_FILES) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)"
	$(CPFILE) $(TEST_FILES) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)"
	$(CPFILE) $(HUC_FILES) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)"
	$(CPFILE) $(COMPILED_RESOURCE_FILES) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)/$(PACKAGE)"
	$(CPFILE) $(EXTRAS) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)/$(PACKAGE)"
	$(CPFILE) $(METADATA) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)/metadata.txt"
#	$(CPDIR) i18n "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)"
#	$(CPDIR) $(HELP) $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)"
#	$(CPDIR) $(HTML) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)"
	$(CPDIR) $(GLOBALDATA) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)"
	$(CPDIR) $(EXTRAPACKAGES) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)/$(PACKAGE)"
#	$(CPDIR) $(TOOLS) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)"
# remove test outputs before copying test data
	rm -vfr $(TESTOUTPUT)
	$(CPDIR) $(TESTDATA) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)/$(PACKAGE)"

# The dclean target deletes any .git entry
dclean:
	@echo
	@echo "-----------------------------------"
	@echo "Removing any compiled python files."
	@echo "-----------------------------------"
	find $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME) -iname ".git" -prune -exec rm -Rf {} \;

derase:
	@echo
	@echo "-------------------------"
	@echo "Removing deployed plugin."
	@echo "-------------------------"
	rm -Rf $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)

zip: deploy dclean
	@echo
	@echo "---------------------------"
	@echo "Creating plugin zip bundle."
	@echo "---------------------------"
	# The zip target deploys the plugin and creates a zip file with the deployed
	# content. You can then upload the zip file on http://plugins.qgis.org
	rm -f $(PLUGINNAME).zip
	cd $(HOME)/$(QGISDIR)/python/plugins; zip -9r $(CURDIR)/$(PLUGINNAME).zip $(PLUGINNAME)

package: compile
	# Create a zip package of the plugin named $(PLUGINNAME).zip.
	# This requires use of git (your plugin development directory must be a
	# git repository).
	# To use, pass a valid commit or tag as follows:
	#   make package VERSION=Version_0.3.2
	@echo
	@echo "------------------------------------"
	@echo "Exporting plugin to zip package.	"
	@echo "------------------------------------"
	rm -f $(PLUGINNAME).zip
	git archive --prefix=$(PLUGINNAME)/ -o $(PLUGINNAME).zip $(VERSION)
	echo "Created package: $(PLUGINNAME).zip"


upload: zip
	@echo
	@echo "-------------------------------------"
	@echo "Uploading plugin to QGIS Plugin repo."
	@echo "-------------------------------------"
	$(PLUGIN_UPLOAD) $(PLUGINNAME).zip

transup:
	@echo
	@echo "------------------------------------------------"
	@echo "Updating translation files with any new strings."
	@echo "------------------------------------------------"
	@chmod +x scripts/update-strings.sh
	@scripts/update-strings.sh $(LOCALES)

transcompile:
	@echo
	@echo "----------------------------------------"
	@echo "Compiled translation files to .qm files."
	@echo "----------------------------------------"
	@chmod +x scripts/compile-strings.sh
	@scripts/compile-strings.sh $(LRELEASE) $(LOCALES)

transclean:
	@echo
	@echo "------------------------------------"
	@echo "Removing compiled translation files."
	@echo "------------------------------------"
	rm -f i18n/*.qm

doc:
	@echo
	@echo "------------------------------------"
#	@echo "Building documentation using sphinx."
	@echo "Building documentation using doxygen."
	@echo "------------------------------------"
#	cd help; make html
	$(DOXYGEN)

pylint:
	@echo
	@echo "-----------------"
	@echo "Pylint violations"
	@echo "-----------------"
	@pylint --reports=n --rcfile=pylintrc . || true
	@echo
	@echo "----------------------"
	@echo "If you get a 'no module named qgis.core' error, try sourcing"
	@echo "the helper script we have provided first then run make pylint."
	@echo "e.g. source run-env-linux.sh <path to qgis install>; make pylint"
	@echo "----------------------"


# Run pep8 style checking
#http://pypi.python.org/pypi/pep8
pep8:
	@echo
	@echo "-----------"
	@echo "PEP8 issues"
	@echo "-----------"
	@pep8 --repeat --ignore=E203,E121,E122,E123,E124,E125,E126,E127,E128 --exclude $(PEP8EXCLUDE) . || true
	@echo "-----------"
	@echo "Ignored in PEP8 check:"
	@echo $(PEP8EXCLUDE)


clean:
	@echo
	@echo "---------------------------------------------------------"
	@echo "Removing rcc generated files, and all compiled files."
	@echo "Also removing html, test, coverage and build directories."
	@echo "---------------------------------------------------------"
#	rm -f $(COMPILED_RESOURCE_FILES) $(C_FILES) $(OBJ_FILES)
	rm -f $(C_FILES) $(OBJ_FILES)
	rm -fr $(HTML)
	rm -fr $(TESTOUTPUT)
	rm -rf cover
	rm -rf build

# forces 32/64 bit dependent files to be recompiled
archclean:
	@echo
	@echo "---------------------"
	@echo "Removing object files"
	@echo "---------------------"
	rm -f $(OBJ_FILES)
	rm -f $(C_FILES)

