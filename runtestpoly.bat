SET OSGEO4W_ROOT=C:\OSGeo4W64
set PYTHONPATH=%PYTHONPATH%;%OSGEO4W_ROOT%\apps\qgis\python
rem QGIS binaries
set PATH=%PATH%;%OSGEO4W_ROOT%\apps\qgis\bin;%OSGEO4W_ROOT%\apps\qgis\python 
rem disable QGIS console messages
set QGIS_DEBUG=-1

rem default QGIS plugins
set PYTHONPATH=%PYTHONPATH%;%OSGEO4W_ROOT%\apps\qgis\python\plugins
rem user installed plugins
set PYTHONPATH=%PYTHONPATH%;%USERPROFILE%\AppData/Roaming/QGIS/QGIS3/profiles/default\python\plugins

python3 -m unittest -v test_polygonize
python3 -m unittest -v test_polygonizeInC
