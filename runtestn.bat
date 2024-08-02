SET OSGEO4W_ROOT=C:\Program Files\QGIS 3.34.9
call "%OSGEO4W_ROOT%\bin\o4w_env.bat"
set PYTHONHOME=%OSGEO4W_ROOT%\apps\Python312
set PYTHONPATH=%OSGEO4W_ROOT%\apps\qgis-ltr\python
rem QGIS binaries
set PATH=%PATH%;%OSGEO4W_ROOT%\apps\qgis-ltr\bin;%OSGEO4W_ROOT%\apps\qgis-ltr\python;%OSGEO4W_ROOT%\apps\Python312;%OSGEO4W_ROOT%\apps\Python312\Scripts;%OSGEO4W_ROOT%\apps\qt5\bin;%OSGEO4W_ROOT%\bin 
rem disable QGIS console messages
set QGIS_DEBUG=-1

rem default QGIS plugins
set PYTHONPATH=%PYTHONPATH%;%OSGEO4W_ROOT%\apps\qgis-ltr\python\plugins;%OSGEO4W_ROOT%\apps\qgis-ltr\python\plugins\processing
rem user installed plugins
set PYTHONPATH=%PYTHONPATH%;%USERPROFILE%\AppData/Roaming/QGIS/QGIS3/profiles/default\python\plugins
set QGIS_PREFIX_PATH=%OSGEO4W_ROOT%\apps\qgis-ltr
set QT_PLUGIN_PATH=%OSGEO4W_ROOT%\apps\qgis-ltr\qtplugins;%OSGEO4W_ROOT%\apps\qt5\plugins

IF [%1] == [] (
  "%OSGEO4W_ROOT%\bin\python3.exe" -m unittest -v test_qswatplus
) ELSE (
  "%OSGEO4W_ROOT%\bin\python3.exe" -m unittest -v test_qswatplus.TestQswat.test%1
)

