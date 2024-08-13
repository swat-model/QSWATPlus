# QSWATPlus

QGIS plugin for creating inputs for SWAT+.

## Build
The repository holds an Eclipse project.  It was created on Windows but runs in Eclipse on Windows and Linux (Ubuntu at least) and Macs.

There is a Makefile that should provide enough information to build QSWATPlus.   

Note that the only interesting projects in the Makefile are QSWATPlus, QSWATPlusLinux3_64 and QSWATPlusMac3_64.
QSWATPlus3_32 is 32-bit for use with 32-bit Microsoft Office.  QSWATPlus3_64 is only for 64-bit Microsoft Office and QGIS before 3.16.14 using Python 3.7.  QSWATPlus3_9 is 64 bit, only for Windows QGIS using Python 3.9, and QSWATPlus3_12 is only for Windows QGIS using Python 3.12.

### Build on Windows
64-bit QGIS Desktop does not include Python development files (Python.h and other header files, and python27.lib).  So to compile the Cython files it is necessary to install the _OSGeo4W Network Installer (64 bit)_:

- download the installer osgeo4w-setup-x86\_64.exe and run it
- select _Advanced Install_
- include the packages QGIS, GDAL and GRASS GIS (probably the default)
- select _Install from Internet_
- use the default root directory  _C:\OSGeo4W64_, choose _All Users_  if you have admin privileges, create icons if you wish
- take default local package directory
- use _Direct Connection_ or as appropriate for your internet connection
- choose a download site
- in the *Select Packages* form you need to include _qgis-ltr_ in the *Desktop* section with version at least 3.4.6
- in the *Select Packages* form you need to include _python devel_ in the _Libs_ section
- finish to install.

For the 32 bit version of QGIS you can use the standalone installer.

For both 32 and 64 bit QGIS you will need to add the cython package.  To do this, run OSGeo4W.bat in the top QGIS directory as administrator.  (Find it in Windows Explorer and right click to get _Run as administrator_)  Then use the command _pip install cython_.  If you get a message _Fatal error in launcher: Unable to create process using '"'_ then use the command _python -m pip install cython_.

The compilation of the cython files generates some warnings that you can ignore.

You also need to install Microsoft's [Visual C++ for Python](https://www.microsoft.com/en-gb/download/details.aspx?id=44266).  Download this (_VCForPython27.msi_) but instead of just running it immediately (which would install it under your home directory) start a command shell and use the command _msixec /i pathtomsi ALLUSERS=1_
where _pathtomsi_ is the full path, e.g. _C:\Users\<user>\Downloads\VCForPython27.msi_.  Then it will install in _C:\Program Files (x86)\Common Files\Microsoft_.  You will need administrator privileges to do this.

You also need to install [MinGW](http://www.mingw.org/).  MinGW supplies the version of make we need, namely _mingw32-make_, and also the appropriate versions of utilities like _mkdir_.  We assume it is installed in C:\Mingw.

### Environment variables for Windows
The following need to be set to run make assuming  _VCforP_  is the path to _Visual C++ for Python\9.0_, e.g  _C:\Program Files (x86)\Common Files\Microsoft\Visual C++ for Python\9.0_ 

- HOME: User's home directory
- INCLUDE: VCforP\VC\Include;VCforP\WinSDK\Include
- LIB: VCforP\VC\Lib\amd64;VCforP\WinSDK\Lib\x64 (64 bit) or VCforP\VC\Lib;VCforP\WinSDK\Lib (32 bit)
- OSGEO4W_ROOT: Path to QGIS e.g. C:\OSgeo4W64
- PATH: C:\MinGW\bin;C:\MinGW\msys\1.0\bin;VCforP\VC\bin\amd64;%OSGEO4W\_ROOT%\bin (64 bit) or C:\MinGW\bin;C:\MinGW\msys\1.0\bin;VCforP\VC\bin;%OSGEO4W\_ROOT%\bin (32 bit)
- QSWAT\_PROJECT: 	QSWATPlus

### Build on Linux
The only environment variable required is QSWAT\_PROJECT, set to QSWATPlusLinux3\_64.

The project location for make in Eclipse is hard-wired to /media/sf\_Public/QSWATPlus3.  This was used since the QSWATPlus3 source directory was shared between Windows and a Linux virtual machine.  Change this in Eclipse with  _Run -> External Tools -> External Tools Configuration_  and change  _Working Directory_  as appropriate for the  _make QSWATPlus3\_64_  and  _clean QSWATPlus3\_64_  programs.

