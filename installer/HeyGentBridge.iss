; HeyGent 브릿지 윈도우 인스톨러 (Inno Setup 6)
;
; 빌드 (PowerShell):
;   & "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer\HeyGentBridge.iss
;
; 사전 조건: dist/HeyGentBridge/ 폴더가 PyInstaller --onedir 로 미리 만들어져 있어야 한다.
;
; 결과물: installer/Output/HeyGentBridgeSetup.exe

#define MyAppName "HeyGent 브릿지"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "HeyGent"
#define MyAppExeName "HeyGentBridge.exe"

[Setup]
AppId={{8E5D6F2C-9A4B-4D1E-B3F0-1C2A7B9D8E4F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\HeyGent
DefaultGroupName=HeyGent
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=Output
OutputBaseFilename=HeyGentBridgeSetup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=..\bridge\assets\icon.ico
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면에 바로가기 만들기"; GroupDescription: "추가 작업:"; Flags: unchecked
Name: "startmenuicon"; Description: "시작 메뉴에 바로가기 만들기"; GroupDescription: "추가 작업:"

[Files]
; PyInstaller --onedir 결과물을 통째로 포함.
Source: "..\dist\HeyGentBridge\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startmenuicon
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "지금 HeyGent 브릿지 실행"; Flags: nowait postinstall skipifsilent
