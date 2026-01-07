# QA Team ViewClipper - Build Instructions

## Quick Build (2 Steps)

### Step 1: Build the EXE
```
build.bat
```
This creates `dist\ViewClipper.exe`

### Step 2: Create the Installer
1. Download & Install **Inno Setup** from: https://jrsoftware.org/isdl.php
2. Open `ViewClipper_Installer.iss` with Inno Setup
3. Press **Ctrl+F9** to compile
4. Installer created at: `installer_output\ViewClipper_Setup_v1.0.0.exe`

---

## Manual Build Steps

### Prerequisites
- Python 3.10+ with venv
- Inno Setup (for installer)

### 1. Setup Environment
```powershell
cd C:\Users\YourPath\Documents\screenshot-tool
.\venv\Scripts\Activate
pip install -r requirements.txt
```

### 2. Build EXE with PyInstaller
```powershell
pyinstaller ViewClipper.spec --noconfirm
```

### 3. Test the EXE
```powershell
.\dist\ViewClipper.exe
```

### 4. Create Installer
- Open Inno Setup Compiler
- File > Open > ViewClipper_Installer.iss
- Build > Compile (Ctrl+F9)

---

## File Structure After Build

```
screenshot-tool/
├── dist/
│   └── ViewClipper.exe          <- Standalone executable
├── installer_output/
│   └── ViewClipper_Setup_v1.0.0.exe  <- Installer for distribution
├── build.bat                    <- Build script
├── ViewClipper.spec             <- PyInstaller config
├── ViewClipper_Installer.iss    <- Inno Setup config
├── version_info.txt             <- Windows version metadata
├── QATeamViewClipper.ico        <- App icon
├── QATeamViewClipper.png        <- App logo
└── ... (source files)
```

---

## Distributing

Share `ViewClipper_Setup_v1.0.0.exe` with users. They:
1. Run the installer
2. Choose install location
3. Optionally add desktop shortcut
4. Optionally start on Windows boot
5. Done! App appears in Start Menu

---

## Troubleshooting

**"Module not found" errors during build:**
```
pip install pywin32 pillow google-api-python-client --break-system-packages
```

**Antivirus blocks EXE:**
This is common with PyInstaller. Users may need to add an exception.

**Icon not showing:**
Make sure `QATeamViewClipper.ico` is in the project folder before building.
