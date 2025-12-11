import tkinter as tk
from tkinter import filedialog, messagebox
import json
import os

class HotkeyEntry(tk.Frame):
    """Custom widget for capturing hotkey combinations"""
    def __init__(self, parent, initial_value="", **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(bg='#3c3c3c')
        
        self.hotkey = initial_value
        self.recording = False
        self.modifiers = set()
        
        # Display entry
        self.entry_var = tk.StringVar(value=initial_value)
        self.entry = tk.Entry(
            self,
            textvariable=self.entry_var,
            font=('Arial', 10),
            bg='white',
            fg='black',
            width=12,
            justify='center',
            state='readonly'
        )
        self.entry.pack(side=tk.LEFT, padx=(0, 8))
        
        # Record button
        self.record_btn = tk.Button(
            self,
            text="Set",
            command=self.start_recording,
            bg='#4a4a4a',
            fg='white',
            font=('Arial', 9),
            padx=8,
            pady=2,
            relief=tk.FLAT,
            cursor='hand2'
        )
        self.record_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Clear button
        self.clear_btn = tk.Button(
            self,
            text="Clear",
            command=self.clear_hotkey,
            bg='#5a3a3a',
            fg='white',
            font=('Arial', 9),
            padx=8,
            pady=2,
            relief=tk.FLAT,
            cursor='hand2'
        )
        self.clear_btn.pack(side=tk.LEFT)
        
    def start_recording(self):
        """Start recording hotkey"""
        self.recording = True
        self.modifiers = set()
        self.entry_var.set("Press keys...")
        self.entry.configure(bg='#ffffcc')
        self.record_btn.configure(text="...", bg='#aa4444')
        
        # Bind to top-level window
        self.top = self.winfo_toplevel()
        self.top.bind('<KeyPress>', self.on_key_press)
        self.top.bind('<KeyRelease>', self.on_key_release)
        self.top.focus_set()
        
    def on_key_press(self, event):
        if not self.recording:
            return
            
        key = event.keysym
        
        # Track modifiers
        if key in ('Control_L', 'Control_R'):
            self.modifiers.add('Ctrl')
        elif key in ('Alt_L', 'Alt_R'):
            self.modifiers.add('Alt')
        elif key in ('Shift_L', 'Shift_R'):
            self.modifiers.add('Shift')
        elif key == 'Escape':
            self.cancel_recording()
        else:
            # Non-modifier key pressed - finalize hotkey
            self.finalize_hotkey(key)
            
    def on_key_release(self, event):
        pass
        
    def finalize_hotkey(self, key):
        """Finalize the hotkey combination"""
        self.recording = False
        
        # Build hotkey string
        parts = []
        if 'Ctrl' in self.modifiers:
            parts.append('Ctrl')
        if 'Alt' in self.modifiers:
            parts.append('Alt')
        if 'Shift' in self.modifiers:
            parts.append('Shift')
            
        # Normalize key name
        key_name = self.normalize_key(key)
        if key_name:
            parts.append(key_name)
            
        if parts:
            self.hotkey = '+'.join(parts)
            self.entry_var.set(self.hotkey)
        else:
            self.entry_var.set(self.hotkey)  # Restore previous
            
        self.entry.configure(bg='white')
        self.record_btn.configure(text="Set", bg='#4a4a4a')
        
        # Unbind
        self.top.unbind('<KeyPress>')
        self.top.unbind('<KeyRelease>')
        
    def normalize_key(self, key):
        """Normalize key names"""
        # Function keys
        if key.startswith('F') and key[1:].isdigit():
            return key.upper()
        # Letters
        if len(key) == 1 and key.isalpha():
            return key.upper()
        # Numbers
        if len(key) == 1 and key.isdigit():
            return key
        # Special keys
        special = {
            'space': 'Space',
            'Return': 'Enter',
            'Tab': 'Tab',
            'BackSpace': 'Backspace',
            'Delete': 'Delete',
            'Insert': 'Insert',
            'Home': 'Home',
            'End': 'End',
            'Prior': 'PageUp',
            'Next': 'PageDown',
            'Up': 'Up',
            'Down': 'Down',
            'Left': 'Left',
            'Right': 'Right',
            'Print': 'PrintScreen',
            'Scroll_Lock': 'ScrollLock',
            'Pause': 'Pause',
        }
        return special.get(key, None)
        
    def cancel_recording(self):
        """Cancel recording"""
        self.recording = False
        self.entry_var.set(self.hotkey)
        self.entry.configure(bg='white')
        self.record_btn.configure(text="Set", bg='#4a4a4a')
        self.top.unbind('<KeyPress>')
        self.top.unbind('<KeyRelease>')
        
    def clear_hotkey(self):
        """Clear the hotkey"""
        self.hotkey = ""
        self.entry_var.set("(disabled)")
        
    def get(self):
        """Get current hotkey"""
        return self.hotkey if self.hotkey != "(disabled)" else ""


class SettingsManager:
    def __init__(self):
        self.settings_file = os.path.join(os.path.expanduser('~'), '.screenshot_tool_settings.json')
        self.settings = self.load_settings()
        
    def load_settings(self):
        """Load settings from file or create defaults"""
        defaults = {
            'save_folder': os.path.join(os.path.expanduser('~'), 'Pictures', 'Screenshots'),
            'hotkey_fullscreen': 'Alt+S',
            'hotkey_region': 'Alt+R',
            'hotkey_settings': 'Ctrl+P',
        }
        
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    loaded = json.load(f)
                    defaults.update(loaded)
            except:
                pass
                
        return defaults
        
    def save_settings(self):
        """Save settings to file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
            return True
        except:
            return False
            
    def get(self, key, default=None):
        """Get a setting value"""
        return self.settings.get(key, default)
        
    def set(self, key, value):
        """Set a setting value"""
        self.settings[key] = value
        
    def show_settings_window(self):
        """Show settings GUI"""
        window = tk.Tk()
        window.title("Screenshot Tool - Settings")
        window.configure(bg='#2b2b2b')
        window.resizable(True, True)
        
        # Account for DPI scaling
        try:
            dpi_scale = window.winfo_fpixels('1i') / 72.0
        except:
            dpi_scale = 1.0
        
        # Larger base size to accommodate high DPI
        base_width = 700
        base_height = 600
        
        window.minsize(400, 400)
        
        # Center the window
        window.update_idletasks()
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width - base_width) // 2
        y = (screen_height - base_height) // 2
        window.geometry(f'{base_width}x{base_height}+{x}+{y}')
        window.attributes('-topmost', True)
        window.focus_force()
        
        # Title
        title_label = tk.Label(
            window,
            text="⚙️ Settings",
            bg='#2b2b2b',
            fg='white',
            font=('Arial', 18, 'bold')
        )
        title_label.pack(pady=20)
        
        # Main content frame
        content_frame = tk.Frame(window, bg='#2b2b2b')
        content_frame.pack(fill=tk.BOTH, expand=True, padx=30)
        
        # === Save Location Section ===
        location_frame = tk.Frame(content_frame, bg='#3c3c3c', padx=25, pady=15)
        location_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(
            location_frame,
            text="📁 Save Location",
            bg='#3c3c3c',
            fg='white',
            font=('Arial', 12, 'bold')
        ).pack(anchor='w', pady=(0, 10))
        
        path_frame = tk.Frame(location_frame, bg='#3c3c3c')
        path_frame.pack(fill=tk.X)
        
        path_var = tk.StringVar(value=self.settings['save_folder'])
        
        path_display = tk.Entry(
            path_frame,
            textvariable=path_var,
            font=('Arial', 10),
            bg='white',
            fg='black',
            insertbackground='black',
            relief=tk.FLAT,
            state='readonly'
        )
        path_display.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 10))
        
        def browse_folder():
            folder = filedialog.askdirectory(
                initialdir=self.settings['save_folder'],
                title="Select Screenshot Save Folder"
            )
            if folder:
                path_var.set(folder)
                
        browse_btn = tk.Button(
            path_frame,
            text="📂 Browse",
            command=browse_folder,
            bg='#4a4a4a',
            fg='white',
            padx=15,
            pady=5,
            font=('Arial', 10),
            relief=tk.FLAT,
            cursor='hand2'
        )
        browse_btn.pack(side=tk.LEFT)
        
        # === Hotkeys Section ===
        hotkey_frame = tk.Frame(content_frame, bg='#3c3c3c', padx=25, pady=15)
        hotkey_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(
            hotkey_frame,
            text="⌨️ Hotkeys",
            bg='#3c3c3c',
            fg='white',
            font=('Arial', 12, 'bold')
        ).pack(anchor='w', pady=(0, 10))
        
        # Hotkey rows
        hotkeys_container = tk.Frame(hotkey_frame, bg='#3c3c3c')
        hotkeys_container.pack(fill=tk.X)
        
        # Fullscreen hotkey
        row1 = tk.Frame(hotkeys_container, bg='#3c3c3c')
        row1.pack(fill=tk.X, pady=5)
        tk.Label(row1, text="Capture Fullscreen:", bg='#3c3c3c', fg='white', font=('Arial', 10), width=20, anchor='w').pack(side=tk.LEFT)
        hotkey_fullscreen = HotkeyEntry(row1, self.settings.get('hotkey_fullscreen', 'Alt+S'))
        hotkey_fullscreen.pack(side=tk.LEFT)
        
        # Region hotkey
        row2 = tk.Frame(hotkeys_container, bg='#3c3c3c')
        row2.pack(fill=tk.X, pady=5)
        tk.Label(row2, text="Capture Region:", bg='#3c3c3c', fg='white', font=('Arial', 10), width=20, anchor='w').pack(side=tk.LEFT)
        hotkey_region = HotkeyEntry(row2, self.settings.get('hotkey_region', 'Alt+R'))
        hotkey_region.pack(side=tk.LEFT)
        
        # Settings hotkey
        row3 = tk.Frame(hotkeys_container, bg='#3c3c3c')
        row3.pack(fill=tk.X, pady=5)
        tk.Label(row3, text="Open Settings:", bg='#3c3c3c', fg='white', font=('Arial', 10), width=20, anchor='w').pack(side=tk.LEFT)
        hotkey_settings = HotkeyEntry(row3, self.settings.get('hotkey_settings', 'Ctrl+P'))
        hotkey_settings.pack(side=tk.LEFT)
        
        # Help text
        help_text = tk.Label(
            hotkey_frame,
            text="Click 'Set' and press your desired key combination. Press Escape to cancel.",
            bg='#3c3c3c',
            fg='#888',
            font=('Arial', 9),
            wraplength=550,
            justify='left'
        )
        help_text.pack(anchor='w', pady=(10, 0))
        
        # === Info Section ===
        info_frame = tk.Frame(content_frame, bg='#2b2b2b')
        info_frame.pack(fill=tk.X, pady=10)
        
        info_label = tk.Label(
            info_frame,
            text="⚠️ Changes to hotkeys require restarting the application to take effect.",
            bg='#2b2b2b',
            fg='#ffaa00',
            font=('Arial', 9),
            wraplength=550,
            justify='left'
        )
        info_label.pack()
        
        # === Button frame ===
        button_frame = tk.Frame(window, bg='#2b2b2b')
        button_frame.pack(side=tk.BOTTOM, pady=25)
        
        def save_and_close():
            new_folder = path_var.get()
            
            # Validate folder
            if not new_folder or new_folder.strip() == '':
                messagebox.showerror("Error", "Please select a valid folder")
                return
                
            # Try to create folder if it doesn't exist
            try:
                os.makedirs(new_folder, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"Cannot create folder:\n{str(e)}")
                return
            
            # Check for duplicate hotkeys
            hotkeys = [
                hotkey_fullscreen.get(),
                hotkey_region.get(),
                hotkey_settings.get()
            ]
            active_hotkeys = [h for h in hotkeys if h]
            if len(active_hotkeys) != len(set(active_hotkeys)):
                messagebox.showerror("Error", "Duplicate hotkeys detected! Each action must have a unique hotkey.")
                return
            
            # Save settings
            self.settings['save_folder'] = new_folder
            self.settings['hotkey_fullscreen'] = hotkey_fullscreen.get()
            self.settings['hotkey_region'] = hotkey_region.get()
            self.settings['hotkey_settings'] = hotkey_settings.get()
            
            if self.save_settings():
                # Update config
                from config import Config
                Config.SAVE_FOLDER = self.settings['save_folder']
                Config.ensure_folder()
                
                messagebox.showinfo("Success", "Settings saved!\n\nPlease restart the application for hotkey changes to take effect.")
                window.destroy()
            else:
                messagebox.showerror("Error", "Failed to save settings")
                
        save_btn = tk.Button(
            button_frame,
            text="✅ Save Settings",
            command=save_and_close,
            bg='#2d6a2d',
            fg='white',
            padx=30,
            pady=12,
            font=('Arial', 11, 'bold'),
            relief=tk.FLAT,
            cursor='hand2'
        )
        save_btn.pack(side=tk.LEFT, padx=10)
        
        cancel_btn = tk.Button(
            button_frame,
            text="❌ Cancel",
            command=window.destroy,
            bg='#6a2d2d',
            fg='white',
            padx=30,
            pady=12,
            font=('Arial', 11, 'bold'),
            relief=tk.FLAT,
            cursor='hand2'
        )
        cancel_btn.pack(side=tk.LEFT, padx=10)
        
        window.protocol("WM_DELETE_WINDOW", window.destroy)
        window.mainloop()


# Global settings instance
settings_manager = SettingsManager()