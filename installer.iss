[Setup]
AppName=ScrapMaster Desktop
AppVersion=1.0.0
DefaultDirName={pf}\ScrapMaster
DefaultGroupName=ScrapMaster
OutputDir=dist
OutputBaseFilename=ScrapMaster_Installer
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin

[Files]
Source: "dist\ScrapMaster.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "data\*"; DestDir: "{app}\data"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\ScrapMaster"; Filename: "{app}\ScrapMaster.exe"
Name: "{group}\Uninstall ScrapMaster"; Filename: "{uninstallexe}"
Name: "{commondesktop}\ScrapMaster"; Filename: "{app}\ScrapMaster.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\ScrapMaster.exe"; Description: "Launch ScrapMaster"; Flags: nowait postinstall skipifsilent

[Registry]
; Auto-start on Windows boot
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "ScrapMaster"; ValueData: """{app}\ScrapMaster.exe"""; Flags: uninsdeletevalue; Tasks: autostart

[Tasks]
Name: "autostart"; Description: "Start ScrapMaster automatically on Windows startup"; GroupDescription: "Startup options:"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Create data directory if it doesn't exist
    if not DirExists(ExpandConstant('{app}\data')) then
      CreateDir(ExpandConstant('{app}\data'));
  end;
end;