; Inno Setup Script for QA Team ViewClipper
; Download Inno Setup from: https://jrsoftware.org/isdl.php

#define MyAppName "QA Team ViewClipper"
#define MyAppVersion "1.1.0"
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

; Close applications using files
CloseApplications=force
CloseApplicationsFilter=*.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Start ViewClipper when Windows starts (background mode)"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
; Main executable (built by PyInstaller)
Source: "dist\ViewClipper.exe"; DestDir: "{app}"; Flags: ignoreversion

; Icon file (for shortcuts)
Source: "QATeamViewClipper.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu shortcut - launches in background mode (no arguments)
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\QATeamViewClipper.ico"

; Desktop shortcut - opens Settings window directly (--settings argument)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--settings"; IconFilename: "{app}\QATeamViewClipper.ico"; Tasks: desktopicon

; Startup shortcut - launches in background mode (no arguments)
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon

; Uninstaller in Start Menu
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
; Option to run app after install (in background mode)
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up app folder completely on uninstall
Type: filesandordirs; Name: "{app}"
; Clean up screenshots folder if it exists in app directory
Type: filesandordirs; Name: "{app}\screenshots"
; Clean up any local data
Type: filesandordirs; Name: "{localappdata}\ViewClipper"
; Clean up Programs folder (per-user install location)
Type: filesandordirs; Name: "{localappdata}\Programs\{#MyAppName}"
; Clean up settings file in user home
Type: files; Name: "{userappdata}\.screenshot_tool_settings.json"
Type: files; Name: "{userdocs}\.screenshot_tool_settings.json"

[Code]
// Pascal Script code to handle killing the running process before uninstall

function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
begin
  // Try to kill any running instance of ViewClipper before uninstalling
  // taskkill /F /IM forces the process to terminate
  Exec('taskkill.exe', '/F /IM ViewClipper.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  
  // Small delay to ensure process is fully terminated
  Sleep(500);
  
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDir: String;
begin
  // After uninstall completes, ensure the app directory is removed
  if CurUninstallStep = usPostUninstall then
  begin
    AppDir := ExpandConstant('{app}');
    if DirExists(AppDir) then
    begin
      // Try to remove the directory
      DelTree(AppDir, True, True, True);
    end;
  end;
end;

// Also kill process during installation (in case updating)
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  // Kill any running instance before installing/updating
  Exec('taskkill.exe', '/F /IM ViewClipper.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(500);
  Result := '';
end;