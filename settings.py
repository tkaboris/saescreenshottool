import tkinter as tk
from tkinter import filedialog, messagebox, ttk
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
        self.entry_var = tk.StringVar(value=initial_value if initial_value else "(disabled)")
        self.entry = tk.Entry(
            self,
            textvariable=self.entry_var,
            font=('Arial', 9),
            bg='white',
            fg='black',
            width=12,
            justify='center',
            state='readonly'
        )
        self.entry.pack(side=tk.LEFT, padx=(0, 6), ipady=2)
        
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
        self.record_btn.pack(side=tk.LEFT, padx=(0, 4))
        
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
            self.entry_var.set(self.hotkey if self.hotkey else "(disabled)")
            
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
        self.entry_var.set(self.hotkey if self.hotkey else "(disabled)")
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
        return self.hotkey if self.hotkey and self.hotkey != "(disabled)" else ""


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
            'hotkey_predefined': '',  # Disabled by default
            'predefined_top_offset': 0,
            'predefined_bottom_offset': 50,  # Default to exclude taskbar
            'predefined_left_offset': 0,
            'predefined_right_offset': 0,
            # Output options
            'region_copy_to_clipboard': True,  # Default: copy to clipboard
            'fullscreen_copy_to_clipboard': False,  # Default: save to file
            'predefined_copy_to_clipboard': False,  # Default: save to file
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
        window.title("ViewClipper - Settings")
        window.configure(bg='#2b2b2b')
        window.resizable(True, True)
        
        # Much larger window for high DPI displays
        base_width = 900
        base_height = 1100
        
        window.minsize(700, 900)
        
        # Center the window
        window.update_idletasks()
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width - base_width) // 2
        y = max(10, (screen_height - base_height) // 2)
        window.geometry(f'{base_width}x{base_height}+{x}+{y}')
        window.attributes('-topmost', True)
        window.focus_force()
        
        # Create scrollable canvas
        main_canvas = tk.Canvas(window, bg='#2b2b2b', highlightthickness=0)
        scrollbar = tk.Scrollbar(window, orient="vertical", command=main_canvas.yview)
        scrollable_frame = tk.Frame(main_canvas, bg='#2b2b2b')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        # Enable mousewheel scrolling
        def on_mousewheel(event):
            main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        main_canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(
            scrollable_frame,
            text="⚙️ ViewClipper Settings",
            bg='#2b2b2b',
            fg='white',
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=12, padx=20, anchor='w')
        
        # Main content frame
        content_frame = tk.Frame(scrollable_frame, bg='#2b2b2b')
        content_frame.pack(fill=tk.BOTH, expand=True, padx=15)
        
        # === Save Location Section ===
        location_frame = tk.Frame(content_frame, bg='#3c3c3c', padx=15, pady=10)
        location_frame.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(
            location_frame,
            text="📁 Save Location",
            bg='#3c3c3c',
            fg='white',
            font=('Arial', 11, 'bold')
        ).pack(anchor='w', pady=(0, 6))
        
        path_frame = tk.Frame(location_frame, bg='#3c3c3c')
        path_frame.pack(fill=tk.X)
        
        path_var = tk.StringVar(value=self.settings['save_folder'])
        
        path_display = tk.Entry(
            path_frame,
            textvariable=path_var,
            font=('Arial', 9),
            bg='white',
            fg='black',
            insertbackground='black',
            relief=tk.FLAT,
            state='readonly'
        )
        path_display.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 8))
        
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
            padx=10,
            pady=4,
            font=('Arial', 9),
            relief=tk.FLAT,
            cursor='hand2'
        )
        browse_btn.pack(side=tk.LEFT)
        
        # === Hotkeys Section ===
        hotkey_frame = tk.Frame(content_frame, bg='#3c3c3c', padx=15, pady=10)
        hotkey_frame.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(
            hotkey_frame,
            text="⌨️ Hotkeys",
            bg='#3c3c3c',
            fg='white',
            font=('Arial', 11, 'bold')
        ).pack(anchor='w', pady=(0, 6))
        
        # Hotkey rows
        hotkeys_container = tk.Frame(hotkey_frame, bg='#3c3c3c')
        hotkeys_container.pack(fill=tk.X)
        
        # Fullscreen hotkey
        row1 = tk.Frame(hotkeys_container, bg='#3c3c3c')
        row1.pack(fill=tk.X, pady=3)
        tk.Label(row1, text="Capture Fullscreen:", bg='#3c3c3c', fg='white', font=('Arial', 9), width=18, anchor='w').pack(side=tk.LEFT)
        hotkey_fullscreen = HotkeyEntry(row1, self.settings.get('hotkey_fullscreen', 'Alt+S'))
        hotkey_fullscreen.pack(side=tk.LEFT)
        
        # Region hotkey
        row2 = tk.Frame(hotkeys_container, bg='#3c3c3c')
        row2.pack(fill=tk.X, pady=3)
        tk.Label(row2, text="Capture Region:", bg='#3c3c3c', fg='white', font=('Arial', 9), width=18, anchor='w').pack(side=tk.LEFT)
        hotkey_region = HotkeyEntry(row2, self.settings.get('hotkey_region', 'Alt+R'))
        hotkey_region.pack(side=tk.LEFT)
        
        # Predefined area hotkey
        row3 = tk.Frame(hotkeys_container, bg='#3c3c3c')
        row3.pack(fill=tk.X, pady=3)
        tk.Label(row3, text="Capture Predefined:", bg='#3c3c3c', fg='white', font=('Arial', 9), width=18, anchor='w').pack(side=tk.LEFT)
        hotkey_predefined = HotkeyEntry(row3, self.settings.get('hotkey_predefined', ''))
        hotkey_predefined.pack(side=tk.LEFT)
        
        # Settings hotkey
        row4 = tk.Frame(hotkeys_container, bg='#3c3c3c')
        row4.pack(fill=tk.X, pady=3)
        tk.Label(row4, text="Open Settings:", bg='#3c3c3c', fg='white', font=('Arial', 9), width=18, anchor='w').pack(side=tk.LEFT)
        hotkey_settings = HotkeyEntry(row4, self.settings.get('hotkey_settings', 'Ctrl+P'))
        hotkey_settings.pack(side=tk.LEFT)
        
        # Help text
        tk.Label(
            hotkey_frame,
            text="Click 'Set' and press your desired key combination. Press Escape to cancel.",
            bg='#3c3c3c',
            fg='#888',
            font=('Arial', 8),
            wraplength=450,
            justify='left'
        ).pack(anchor='w', pady=(6, 0))
        
        # === Output Options Section ===
        output_frame = tk.Frame(content_frame, bg='#3c3c3c', padx=15, pady=10)
        output_frame.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(
            output_frame,
            text="📋 Output Options",
            bg='#3c3c3c',
            fg='white',
            font=('Arial', 11, 'bold')
        ).pack(anchor='w', pady=(0, 6))
        
        tk.Label(
            output_frame,
            text="Choose whether to copy to clipboard (for pasting) or save to file:",
            bg='#3c3c3c',
            fg='#aaa',
            font=('Arial', 9)
        ).pack(anchor='w', pady=(0, 8))
        
        # Custom toggle button class
        class ToggleButton(tk.Frame):
            def __init__(self, parent, text, initial_value=False, **kwargs):
                super().__init__(parent, bg='#3c3c3c', **kwargs)
                self.value = tk.BooleanVar(value=initial_value)
                
                self.label = tk.Label(
                    self, text=text, bg='#3c3c3c', fg='white',
                    font=('Arial', 9), width=18, anchor='w'
                )
                self.label.pack(side=tk.LEFT, padx=(0, 10))
                
                # Toggle button frame
                self.btn_frame = tk.Frame(self, bg='#555', padx=1, pady=1)
                self.btn_frame.pack(side=tk.LEFT)
                
                self.file_btn = tk.Button(
                    self.btn_frame, text="💾 Save File",
                    command=lambda: self.set_value(False),
                    font=('Arial', 9), padx=8, pady=3,
                    relief=tk.FLAT, cursor='hand2'
                )
                self.file_btn.pack(side=tk.LEFT, padx=1)
                
                self.clip_btn = tk.Button(
                    self.btn_frame, text="📋 Clipboard",
                    command=lambda: self.set_value(True),
                    font=('Arial', 9), padx=8, pady=3,
                    relief=tk.FLAT, cursor='hand2'
                )
                self.clip_btn.pack(side=tk.LEFT, padx=1)
                
                self.update_buttons()
                
            def set_value(self, val):
                self.value.set(val)
                self.update_buttons()
                
            def update_buttons(self):
                if self.value.get():
                    # Clipboard selected
                    self.clip_btn.configure(bg='#4a9f4a', fg='white')
                    self.file_btn.configure(bg='#4a4a4a', fg='#aaa')
                else:
                    # File selected
                    self.file_btn.configure(bg='#4a9f4a', fg='white')
                    self.clip_btn.configure(bg='#4a4a4a', fg='#aaa')
                    
            def get(self):
                return self.value.get()
        
        # Toggle buttons for each capture type
        clipboard_toggles = {}
        
        region_toggle = ToggleButton(
            output_frame, "Region capture:",
            self.settings.get('region_copy_to_clipboard', True)
        )
        region_toggle.pack(fill=tk.X, pady=4)
        clipboard_toggles['region'] = region_toggle
        
        fullscreen_toggle = ToggleButton(
            output_frame, "Fullscreen capture:",
            self.settings.get('fullscreen_copy_to_clipboard', False)
        )
        fullscreen_toggle.pack(fill=tk.X, pady=4)
        clipboard_toggles['fullscreen'] = fullscreen_toggle
        
        predefined_toggle = ToggleButton(
            output_frame, "Predefined capture:",
            self.settings.get('predefined_copy_to_clipboard', False)
        )
        predefined_toggle.pack(fill=tk.X, pady=4)
        clipboard_toggles['predefined'] = predefined_toggle
        
        # === Predefined Area Section ===
        predefined_frame = tk.Frame(content_frame, bg='#3c3c3c', padx=15, pady=10)
        predefined_frame.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(
            predefined_frame,
            text="📐 Predefined Capture Area",
            bg='#3c3c3c',
            fg='white',
            font=('Arial', 11, 'bold')
        ).pack(anchor='w', pady=(0, 4))
        
        tk.Label(
            predefined_frame,
            text="Define margins to exclude from screen edges (in pixels)",
            bg='#3c3c3c',
            fg='#aaa',
            font=('Arial', 9)
        ).pack(anchor='w', pady=(0, 6))
        
        # Offset inputs grid
        offsets_container = tk.Frame(predefined_frame, bg='#3c3c3c')
        offsets_container.pack(fill=tk.X)
        
        # Top offset
        top_row = tk.Frame(offsets_container, bg='#3c3c3c')
        top_row.pack(fill=tk.X, pady=2)
        tk.Label(top_row, text="Top margin:", bg='#3c3c3c', fg='white', font=('Arial', 9), width=12, anchor='w').pack(side=tk.LEFT)
        top_var = tk.StringVar(value=str(self.settings.get('predefined_top_offset', 0)))
        top_entry = tk.Entry(top_row, textvariable=top_var, font=('Arial', 9), width=7, justify='center')
        top_entry.pack(side=tk.LEFT, padx=(0, 6), ipady=2)
        tk.Label(top_row, text="px  (exclude browser tabs)", bg='#3c3c3c', fg='#888', font=('Arial', 8)).pack(side=tk.LEFT)
        
        # Bottom offset
        bottom_row = tk.Frame(offsets_container, bg='#3c3c3c')
        bottom_row.pack(fill=tk.X, pady=2)
        tk.Label(bottom_row, text="Bottom margin:", bg='#3c3c3c', fg='white', font=('Arial', 9), width=12, anchor='w').pack(side=tk.LEFT)
        bottom_var = tk.StringVar(value=str(self.settings.get('predefined_bottom_offset', 50)))
        bottom_entry = tk.Entry(bottom_row, textvariable=bottom_var, font=('Arial', 9), width=7, justify='center')
        bottom_entry.pack(side=tk.LEFT, padx=(0, 6), ipady=2)
        tk.Label(bottom_row, text="px  (exclude taskbar)", bg='#3c3c3c', fg='#888', font=('Arial', 8)).pack(side=tk.LEFT)
        
        # Left offset
        left_row = tk.Frame(offsets_container, bg='#3c3c3c')
        left_row.pack(fill=tk.X, pady=2)
        tk.Label(left_row, text="Left margin:", bg='#3c3c3c', fg='white', font=('Arial', 9), width=12, anchor='w').pack(side=tk.LEFT)
        left_var = tk.StringVar(value=str(self.settings.get('predefined_left_offset', 0)))
        left_entry = tk.Entry(left_row, textvariable=left_var, font=('Arial', 9), width=7, justify='center')
        left_entry.pack(side=tk.LEFT, padx=(0, 6), ipady=2)
        tk.Label(left_row, text="px", bg='#3c3c3c', fg='#888', font=('Arial', 8)).pack(side=tk.LEFT)
        
        # Right offset
        right_row = tk.Frame(offsets_container, bg='#3c3c3c')
        right_row.pack(fill=tk.X, pady=2)
        tk.Label(right_row, text="Right margin:", bg='#3c3c3c', fg='white', font=('Arial', 9), width=12, anchor='w').pack(side=tk.LEFT)
        right_var = tk.StringVar(value=str(self.settings.get('predefined_right_offset', 0)))
        right_entry = tk.Entry(right_row, textvariable=right_var, font=('Arial', 9), width=7, justify='center')
        right_entry.pack(side=tk.LEFT, padx=(0, 6), ipady=2)
        tk.Label(right_row, text="px", bg='#3c3c3c', fg='#888', font=('Arial', 8)).pack(side=tk.LEFT)
        
        # Preview info
        preview_label = tk.Label(
            predefined_frame,
            text="",
            bg='#3c3c3c',
            fg='#88ff88',
            font=('Arial', 9)
        )
        preview_label.pack(anchor='w', pady=(6, 0))
        
        def update_preview(*args):
            try:
                top = int(top_var.get() or 0)
                bottom = int(bottom_var.get() or 0)
                left = int(left_var.get() or 0)
                right = int(right_var.get() or 0)
                # Get screen size for preview
                import ctypes
                ctypes.windll.user32.SetProcessDPIAware()
                sw = ctypes.windll.user32.GetSystemMetrics(0)
                sh = ctypes.windll.user32.GetSystemMetrics(1)
                width = sw - left - right
                height = sh - top - bottom
                preview_label.config(
                    text=f"Capture area: {width} × {height} px  (from {left},{top} to {sw-right},{sh-bottom})",
                    fg='#88ff88' if width > 0 and height > 0 else '#ff8888'
                )
            except:
                preview_label.config(text="Enter valid numbers", fg='#ff8888')
        
        # Bind updates
        top_var.trace_add('write', update_preview)
        bottom_var.trace_add('write', update_preview)
        left_var.trace_add('write', update_preview)
        right_var.trace_add('write', update_preview)
        update_preview()
        
        # === Info Section ===
        info_frame = tk.Frame(content_frame, bg='#2b2b2b')
        info_frame.pack(fill=tk.X, pady=8)
        
        tk.Label(
            info_frame,
            text="⚠️ Changes to hotkeys require restarting the application.",
            bg='#2b2b2b',
            fg='#ffaa00',
            font=('Arial', 9),
            wraplength=450,
            justify='left'
        ).pack()
        
        # === Button frame ===
        button_frame = tk.Frame(scrollable_frame, bg='#2b2b2b')
        button_frame.pack(pady=15)
        
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
            
            # Validate offsets
            try:
                top_offset = int(top_var.get() or 0)
                bottom_offset = int(bottom_var.get() or 0)
                left_offset = int(left_var.get() or 0)
                right_offset = int(right_var.get() or 0)
                
                if any(v < 0 for v in [top_offset, bottom_offset, left_offset, right_offset]):
                    messagebox.showerror("Error", "Offset values cannot be negative")
                    return
            except ValueError:
                messagebox.showerror("Error", "Offset values must be valid numbers")
                return
            
            # Check for duplicate hotkeys
            hotkeys = [
                hotkey_fullscreen.get(),
                hotkey_region.get(),
                hotkey_predefined.get(),
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
            self.settings['hotkey_predefined'] = hotkey_predefined.get()
            self.settings['hotkey_settings'] = hotkey_settings.get()
            self.settings['predefined_top_offset'] = top_offset
            self.settings['predefined_bottom_offset'] = bottom_offset
            self.settings['predefined_left_offset'] = left_offset
            self.settings['predefined_right_offset'] = right_offset
            
            # Save clipboard options
            self.settings['region_copy_to_clipboard'] = clipboard_toggles['region'].get()
            self.settings['fullscreen_copy_to_clipboard'] = clipboard_toggles['fullscreen'].get()
            self.settings['predefined_copy_to_clipboard'] = clipboard_toggles['predefined'].get()
            
            if self.save_settings():
                # Update config
                from config import Config
                Config.SAVE_FOLDER = self.settings['save_folder']
                Config.ensure_folder()
                
                messagebox.showinfo("Success", "Settings saved!\n\nPlease restart the application for hotkey changes to take effect.")
                window.destroy()
            else:
                messagebox.showerror("Error", "Failed to save settings")
        
        # Unbind mousewheel when closing
        def on_close():
            main_canvas.unbind_all("<MouseWheel>")
            window.destroy()
                
        save_btn = tk.Button(
            button_frame,
            text="✅ Save Settings",
            command=save_and_close,
            bg='#2d6a2d',
            fg='white',
            padx=20,
            pady=8,
            font=('Arial', 10, 'bold'),
            relief=tk.FLAT,
            cursor='hand2'
        )
        save_btn.pack(side=tk.LEFT, padx=10)
        
        cancel_btn = tk.Button(
            button_frame,
            text="❌ Cancel",
            command=on_close,
            bg='#6a2d2d',
            fg='white',
            padx=20,
            pady=8,
            font=('Arial', 10, 'bold'),
            relief=tk.FLAT,
            cursor='hand2'
        )
        cancel_btn.pack(side=tk.LEFT, padx=10)
        
        window.protocol("WM_DELETE_WINDOW", on_close)
        window.mainloop()


# Global settings instance
settings_manager = SettingsManager()