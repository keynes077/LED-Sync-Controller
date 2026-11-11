; Inno Setup script. Build the application first with build_windows.bat.
#define MyAppName "LED CNTRL"
#define MyAppVersion "0.2.1"
#define MyAppPublisher "Keynes"
#define MyAppExeName "LED CNTRL.exe"

[Setup]
AppId={{B5EAE8D0-72E1-4CF4-9C1A-0EDC00100001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\LED CNTRL
DefaultGroupName=LED CNTRL
OutputDir=installer_output
OutputBaseFilename=LED_CNTRL_Setup_0.2.1
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"
Name: "startup"; Description: "Launch LED CNTRL when I sign in to Windows"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "dist\LED CNTRL\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\LED CNTRL"; Filename: "{app}\LED CNTRL.exe"
Name: "{autodesktop}\LED CNTRL"; Filename: "{app}\LED CNTRL.exe"; Tasks: desktopicon
Name: "{userstartup}\LED CNTRL"; Filename: "{app}\LED CNTRL.exe"; Tasks: startup

[Run]
Filename: "{app}\LED CNTRL.exe"; Description: "Launch LED CNTRL"; Flags: nowait postinstall skipifsilent
