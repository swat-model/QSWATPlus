; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

#define MyAppName "QSWATPlus3_64"
#define MyAppVersion "2.5"
#define MyAppSubVersion "3"
#define MyAppPublisher "SWAT"
#define MyAppURL "https://swat.tamu.edu/"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{6E4708E2-2338-4F19-AE25-1D7945D75EA0}
AppName={#MyAppName}
AppVersion={#MyAppVersion}.{#MyAppSubVersion}
;AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={userappdata}\QGIS\QGIS3\profiles\default\python\plugins
UsePreviousAppDir=no
DisableDirPage=yes
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=no
OutputDir=C:\QSWATPlusPub
OutputBaseFilename={#MyAppName}install{#MyAppVersion}.{#MyAppSubVersion}
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; use no for testing, yes for delivery??
UsePreviousPrivileges=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[InstallDelete]
; replaced by QSWATPlusMain.py
Type: files; Name: "{code:QGISPLuginDir}\{#MyAppName}\QSWATPlus\QSWATPlus.py"; 
; was installed in wrong blace
Type: filesandordirs; Name: "{code:QGISPLuginDir}\{#MyAppName}\testdata";
; clean up  TauDEM539Bin
Type: files; Name: "C:\SWAT\SWATPlus\TauDEM539Bin\*";

[Files]
Source: "C:\Users\Chris\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\{#MyAppName}\*"; DestDir: "{code:QGISPLuginDir}\{#MyAppName}";  Excludes: "testdata\test,__pycache__"; Flags: ignoreversion recursesubdirs createallsubdirs   
Source: "C:\SWAT\SWATPlus\TauDEM539BinWithDLLs\*"; DestDir: "C:\SWAT\SWATPlus\TauDEM539Bin";  Flags: ignoreversion 
Source: "{#SourcePath}Databases\QSWATPlusProj.sqlite"; DestDir: "C:\SWAT\SWATPlus\Databases";  Flags: ignoreversion
Source: "{#SourcePath}Databases\plant.csv"; DestDir: "C:\SWAT\SWATPlus\Databases";  Flags: ignoreversion

[Code]
var
   QGISPluginDirHasRun : Boolean;
   QGISPluginDirResult: String;

function MainQGISPluginDir(Param: String): String; forward;

function QGISPluginDir(Param: String): String;
begin
  if not QGISPluginDirHasRun then begin
    if IsAdminInstallMode then begin
      QGISPluginDirResult := MainQGISPluginDir(Param);
    end else begin
      QGISPluginDirResult := ExpandConstant('{app}');
    end
  end;
  QGISPluginDirHasRun := True;
  Result := QGISPluginDirResult
end;

function MainQGISPluginDir(Param: String): String;
var
  QGISDirectory: String;
  MainQGISPluginDirResult: String;
begin
  if DirExists(ExpandConstant('{pf64}/QGIS 3.16')) then begin
    QGISDirectory := ExpandConstant('{pf64}/QGIS 3.16');
  end else 
    if DirExists(ExpandConstant('{pf64}/QGIS 3.18')) then begin
      QGISDirectory := ExpandConstant('{pf64}/QGIS 3.18');
    end else 
      if DirExists(ExpandConstant('{sd}/OSGeo4W64')) then begin
        QGISDirectory := ExpandConstant('{sd}/OSGeo4W64');
      end else begin
        QGISDirectory := ExpandConstant('{pf64}');
        if not BrowseForFolder('Please locate QGIS directory', QGISDirectory, False) then
          QGISDirectory := '';
  end;       
  if QGISDirectory = ''  then begin
    MainQGISPluginDirResult := '';
  end else
    if DirExists(QGISDirectory + '/apps/qgis-ltr') then begin
      MainQGISPluginDirResult :=  QGISDirectory + '/apps/qgis-ltr/python/plugins';
    end else
      if DirExists(QGISDirectory + '/apps/qgis') then begin
        MainQGISPluginDirResult :=  QGISDirectory + '/apps/qgis/python/plugins';
      end else
        if DirExists(QGISDirectory + '/apps/qgis-dev') then begin
          MainQGISPluginDirResult :=  QGISDirectory + '/apps/qgis-dev/python/plugins';
        end;
  //MsgBox('Result: ' + MainQGISPluginDirResult, mbInformation, MB_OK);
  Result := MainQGISPluginDirResult
end;


