; Inno Setup Script for QA Team ViewClipper
; Download Inno Setup from: https://jrsoftware.org/isdl.php

#define MyAppName "QA Team ViewClipper"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "QA Team"
#define MyAppExeName "ViewClipper.exe"

[Setup]
; App identity
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://qateam.com
AppSupportURL=https://qateam.com/support
AppUpdatesURL=https://qateam.com/updates

; Install location
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Output settings - installer will be created here
OutputDir=installer_output
OutputBaseFilename=ViewClipper_Setup_v{#MyAppVersion}

; Compression
Compression=lzma2/ultra64
SolidCompression=yes

; Visual settings
SetupIconFile=QATeamViewClipper.ico
WizardStyle=modern
WizardImageFile=compiler:WizModernImage.bmp
WizardSmallImageFile=compiler:WizModernSmallImage.bmp

; Privileges (per-user install doesn't require admin)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Uninstaller
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Start ViewClipper when Windows starts"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
; Main executable (built by PyInstaller)
Source: "dist\ViewClipper.exe"; DestDir: "{app}"; Flags: ignoreversion

; Icon files (for shortcuts and system tray)
Source: "QATeamViewClipper.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "QATeamViewClipper.png"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu shortcut - opens Settings
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--settings"; IconFilename: "{app}\QATeamViewClipper.ico"

; Desktop shortcut (optional) - opens Settings
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--settings"; IconFilename: "{app}\QATeamViewClipper.ico"; Tasks: desktopicon

; Startup shortcut (optional) - runs in background
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon

; Uninstaller in Start Menu
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"



[UninstallDelete]
; CRITICAL FIX: Remove the app directory on uninstall
Type: filesandordirs; Name: "{app}"