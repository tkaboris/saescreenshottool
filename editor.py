import tkinter as tk
from tkinter import colorchooser, ttk
from PIL import Image, ImageDraw, ImageTk, ImageFont, ImageFilter, PngImagePlugin
import os
import math
import sys
from datetime import datetime


def get_resource_path(filename):
    """Get path to resource, works for dev and PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        # Running as compiled exe
        return os.path.join(sys._MEIPASS, filename)
    else:
        # Running as script - look in same directory as this file
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


class ToolTip:
    """Simple tooltip for widgets"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind('<Enter>', self.show)
        widget.bind('<Leave>', self.hide)
    
    def show(self, event=None):
        if self.tip_window:
            return
        x, y, _, _ = self.widget.bbox("insert") if hasattr(self.widget, 'bbox') else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(
            tw, text=self.text, justify=tk.LEFT,
            background="#333", foreground="white",
            relief=tk.SOLID, borderwidth=1,
            font=("Arial", 9), padx=6, pady=3
        )
        label.pack()
    
    def hide(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class ImageEditor:
    def __init__(self, img):
        self.original_img = img.copy()
        self.img = img.copy()
        self.draw = ImageDraw.Draw(self.img)
        self.result = None
        self.save_action = None  # Will be 'local' or 'cloud'
        
        # Undo system
        self.history = [self.img.copy()]
        self.max_history = 20
        
        # Drawing state
        self.tool = None
        self.color = (255, 255, 0)  # Yellow default
        self.weight = 3
        self.start_x = None
        self.start_y = None
        self.temp_items = []
        
        # Preview/drag state
        self.preview_mode = False
        self.preview_items = []
        self.preview_data = None
        self.dragging = False
        self.drag_start_x = None
        self.drag_start_y = None
        
        # Text state
        self.text_mode = False
        self.text_position = None
        self.text_buffer = ""
        
        # Highlighter state
        self.highlighter_points = []
        self.highlighter_opacity = 100
        
        # Mode system
        self.current_mode = "general"  # general, howto, qa
        
        # Step counter for How-To mode
        self.step_counter = 1
        
        # Setup window
        self.root = tk.Tk()
        self.root.title("QA Team - ViewClipper")
        self.root.configure(bg='#2b2b2b')
        self.root.resizable(True, True)
        
        # Set window icon
        self.set_window_icon()
        
        self.tool_buttons = {}
        self.create_toolbar()
        self.setup_canvas()
        
        # Bind events
        self.canvas.bind('<ButtonPress-1>', self.on_mouse_down)
        self.canvas.bind('<B1-Motion>', self.on_mouse_move)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_release)
        self.root.bind('<Key>', self.on_key_press)
        self.root.bind('<Escape>', lambda e: self.handle_escape())
        self.root.bind('<Return>', lambda e: self.handle_return())
        self.root.protocol("WM_DELETE_WINDOW", self.cancel)
        self.root.bind('<Control-z>', lambda e: self.undo())
    
    def set_window_icon(self):
        """Set the window icon"""
        try:
            icon_path = get_resource_path('QATeamViewClipper.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
            else:
                # Try PNG as fallback (works on some systems)
                png_path = get_resource_path('QATeamViewClipper.png')
                if os.path.exists(png_path):
                    icon_img = ImageTk.PhotoImage(Image.open(png_path))
                    self.root.iconphoto(True, icon_img)
                    self._icon_img = icon_img  # Keep reference
        except Exception as e:
            print(f"Could not set icon: {e}")
        
    def create_toolbar(self):
        toolbar = tk.Frame(self.root, bg='#3c3c3c', padx=10, pady=8)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        # Mode selector
        mode_frame = tk.Frame(toolbar, bg='#3c3c3c')
        mode_frame.pack(side=tk.LEFT, padx=(0, 12))
        
        self.mode_var = tk.StringVar(value="🎯 General")
        self.mode_dropdown = ttk.Combobox(
            mode_frame,
            textvariable=self.mode_var,
            values=["🎯 General", "📖 How-To", "🐛 QA"],
            state="readonly",
            width=11,
            font=('Arial', 10)
        )
        self.mode_dropdown.pack(side=tk.LEFT)
        self.mode_dropdown.bind('<<ComboboxSelected>>', self.on_mode_change)
        
        # Separator
        self.add_separator(toolbar)
        
        # Core tools (always visible)
        core_tools = [
            ('→', 'arrow', 'Arrow'),
            ('—', 'hline', 'Horizontal Line'),
            ('|', 'vline', 'Vertical Line'),
            ('□', 'rect', 'Rectangle'),
            ('○', 'circle', 'Circle'),
            ('⬭', 'ellipse', 'Ellipse'),
            ('T', 'text', 'Text'),
            ('🖍', 'highlight', 'Highlighter'),
            ('▦', 'blur', 'Blur/Redact'),
        ]
        
        for icon, tool_name, tooltip in core_tools:
            btn = tk.Button(
                toolbar, text=icon,
                command=lambda t=tool_name: self.select_tool(t),
                bg='#4a4a4a', fg='white',
                width=3, height=1,
                relief=tk.RAISED, font=('Arial', 11),
                cursor='hand2', padx=4, pady=2
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.tool_buttons[tool_name] = btn
            ToolTip(btn, tooltip)
        
        # Separator
        self.add_separator(toolbar)
        
        # Mode-specific stamps frame (will be populated based on mode)
        self.stamps_frame = tk.Frame(toolbar, bg='#3c3c3c')
        self.stamps_frame.pack(side=tk.LEFT, padx=4)
        self.update_mode_stamps()
        
        # Separator
        self.add_separator(toolbar)
        
        # Weight control with label
        weight_frame = tk.Frame(toolbar, bg='#3c3c3c')
        weight_frame.pack(side=tk.LEFT, padx=6)
        
        tk.Label(
            weight_frame, text='Size:', bg='#3c3c3c', fg='#aaa',
            font=('Arial', 9)
        ).pack(side=tk.LEFT, padx=(0, 4))
        
        tk.Button(
            weight_frame, text='-',
            command=lambda: self.adjust_weight(-1),
            bg='#4a4a4a', fg='white', width=2,
            font=('Arial', 10, 'bold'), relief=tk.RAISED, cursor='hand2'
        ).pack(side=tk.LEFT)
        
        self.weight_label = tk.Label(
            weight_frame, text='3', bg='#555', fg='white',
            font=('Arial', 10, 'bold'), width=2, relief=tk.SUNKEN
        )
        self.weight_label.pack(side=tk.LEFT, padx=3)
        ToolTip(self.weight_label, 'Line Weight / Size')
        
        tk.Button(
            weight_frame, text='+',
            command=lambda: self.adjust_weight(1),
            bg='#4a4a4a', fg='white', width=2,
            font=('Arial', 10, 'bold'), relief=tk.RAISED, cursor='hand2'
        ).pack(side=tk.LEFT)
        
        # Separator
        self.add_separator(toolbar)
        
        # Color picker
        color_frame = tk.Frame(toolbar, bg='#3c3c3c')
        color_frame.pack(side=tk.LEFT, padx=6)
        
        self.color_btn = tk.Button(
            color_frame, text='🎨',
            command=self.pick_color,
            bg='#4a4a4a', fg='white', width=3,
            font=('Arial', 11), relief=tk.RAISED, cursor='hand2'
        )
        self.color_btn.pack(side=tk.LEFT, padx=(0, 4))
        ToolTip(self.color_btn, 'Pick Color')
        
        self.color_indicator = tk.Label(
            color_frame, text='    ', bg=self.rgb_to_hex(self.color),
            width=3, relief=tk.SUNKEN, height=1
        )
        self.color_indicator.pack(side=tk.LEFT)
        
        # Separator
        self.add_separator(toolbar)
        
        # Undo
        undo_btn = tk.Button(
            toolbar, text='↶',
            command=self.undo,
            bg='#4a4a4a', fg='white', width=3,
            font=('Arial', 11), relief=tk.RAISED, cursor='hand2'
        )
        undo_btn.pack(side=tk.LEFT, padx=4)
        ToolTip(undo_btn, 'Undo (Ctrl+Z)')
        
        # --- NEW SAVE BUTTONS ---
        
        # Spacer
        tk.Frame(toolbar, bg='#3c3c3c', width=20).pack(side=tk.RIGHT)

        tk.Button(
            toolbar, text='❌ Cancel',
            command=self.cancel,
            bg='#6a2d2d', fg='white',
            font=('Arial', 9, 'bold'), relief=tk.RAISED, cursor='hand2',
            padx=8, pady=4
        ).pack(side=tk.RIGHT, padx=2)

        tk.Button(
            toolbar, text='☁️ Cloud',
            command=lambda: self.save(action='cloud'),
            bg='#2d4a6a', fg='white',
            font=('Arial', 9, 'bold'), relief=tk.RAISED, cursor='hand2',
            padx=8, pady=4
        ).pack(side=tk.RIGHT, padx=2)
        
        tk.Button(
            toolbar, text='💾 Disk',
            command=lambda: self.save(action='local'),
            bg='#2d6a2d', fg='white',
            font=('Arial', 9, 'bold'), relief=tk.RAISED, cursor='hand2',
            padx=8, pady=4
        ).pack(side=tk.RIGHT, padx=2)

        # Status label (Moved to bottom or left of buttons)
        self.status_label = tk.Label(
            toolbar, text='Select a tool', bg='#3c3c3c', fg='#aaa',
            font=('Arial', 9), anchor='e'
        )
        self.status_label.pack(side=tk.RIGHT, padx=10, fill=tk.X, expand=True)
    
    def add_separator(self, parent):
        tk.Frame(parent, bg='#666', width=2).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=4)
    
    def on_mode_change(self, event=None):
        mode_text = self.mode_var.get()
        if "General" in mode_text:
            self.current_mode = "general"
        elif "How-To" in mode_text:
            self.current_mode = "howto"
            self.step_counter = 1  # Reset step counter
        elif "QA" in mode_text:
            self.current_mode = "qa"
        
        self.update_mode_stamps()
        self.status_label.config(text=f'Mode: {self.current_mode.upper()}')
    
    def update_mode_stamps(self):
        """Update stamps frame based on current mode"""
        # Clear existing stamps
        for widget in self.stamps_frame.winfo_children():
            widget.destroy()
        
        # Remove old stamp buttons from tool_buttons
        stamp_tools = ['step', 'pointer', 'magnifier', 'tip', 'warning', 
                       'bug', 'fail', 'pass', 'question', 'critical', 'high', 'med', 'low']
        for t in stamp_tools:
            self.tool_buttons.pop(t, None)
        
        stamps = []
        if self.current_mode == "howto":
            stamps = [
                ('①', 'step', 'Step Number (auto 1-9)'),
                ('👆', 'pointer', 'Pointer'),
                ('🔍', 'magnifier', 'Magnifier'),
                ('💡', 'tip', 'Tip'),
                ('⚠', 'warning', 'Warning'),
            ]
        elif self.current_mode == "qa":
            stamps = [
                ('🐛', 'bug', 'Bug'),
                ('❌', 'fail', 'Fail'),
                ('✅', 'pass', 'Pass'),
                ('❓', 'question', 'Question'),
                ('⚠', 'warning', 'Warning'),
                ('‼', 'critical', 'CRITICAL'),
                ('!', 'high', 'HIGH'),
                ('●', 'med', 'MED'),
                ('○', 'low', 'LOW'),
            ]
        
        for icon, tool_name, tooltip in stamps:
            btn = tk.Button(
                self.stamps_frame, text=icon,
                command=lambda t=tool_name: self.select_tool(t),
                bg='#5a5a6a', fg='white',
                width=3, height=1,
                relief=tk.RAISED, font=('Arial', 11),
                cursor='hand2', padx=2
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.tool_buttons[tool_name] = btn
            ToolTip(btn, tooltip)
    
    def adjust_weight(self, delta):
        self.weight = max(1, min(12, self.weight + delta))
        self.weight_label.config(text=str(self.weight))
        
    def setup_canvas(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        max_width = int(screen_width * 0.9)
        max_height = int(screen_height * 0.85)
        img_width, img_height = self.img.size
        
        if img_width > max_width or img_height > max_height:
            self.scale = min(max_width / img_width, max_height / img_height)
            new_width = int(img_width * self.scale)
            new_height = int(img_height * self.scale)
            self.display_img = self.img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        else:
            self.display_img = self.img.copy()
            self.scale = 1.0
            
        self.photo = ImageTk.PhotoImage(self.display_img)
        
        self.canvas = tk.Canvas(
            self.root, width=self.display_img.width, height=self.display_img.height,
            bg='#2b2b2b', highlightthickness=0
        )
        self.canvas.pack(padx=10, pady=10)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        self.canvas.focus_set()
        
        toolbar_height = 50
        window_width = max(self.display_img.width + 20, 750)
        window_height = self.display_img.height + toolbar_height + 30
        window_height = max(window_height, 300)
        
        x_pos = (screen_width - window_width) // 2
        y_pos = (screen_height - window_height) // 2
        
        self.root.geometry(f'{window_width}x{window_height}+{x_pos}+{y_pos}')
        self.root.attributes('-topmost', True)
        self.root.focus_force()
        
    def select_tool(self, tool_name):
        if self.preview_mode:
            self.commit_preview()
        if self.text_mode and self.text_buffer:
            self.create_element_preview()
        
        self.tool = tool_name
        self.text_mode = False
        self.text_buffer = ""
        self.highlighter_points = []
        self.cleanup_temp_items()
        
        # Update button highlighting
        for name, btn in self.tool_buttons.items():
            if name == tool_name:
                btn.configure(bg='#6a6a9a', relief=tk.SUNKEN)
            else:
                btn.configure(bg='#5a5a6a' if name in ['step','pointer','magnifier','tip','warning','bug','fail','pass','question','critical','high','med','low'] else '#4a4a4a', relief=tk.RAISED)
        
        tool_hints = {
            'arrow': 'Arrow - drag to draw',
            'hline': 'H-Line - drag to draw',
            'vline': 'V-Line - drag to draw',
            'rect': 'Rectangle - drag to draw',
            'circle': 'Circle - drag to draw',
            'ellipse': 'Ellipse - drag to draw',
            'text': 'Text - click, type, Enter to place',
            'highlight': 'Highlight - freehand draw',
            'blur': 'Blur - drag over area to redact',
            'step': f'Step {self.step_counter} - click to place',
            'pointer': 'Pointer - click to place',
            'magnifier': 'Magnifier - click to place',
            'tip': 'Tip - click to place',
            'warning': 'Warning - click to place',
            'bug': 'Bug - click to place',
            'fail': 'Fail - click to place',
            'pass': 'Pass - click to place',
            'question': 'Question - click to place',
            'critical': 'CRITICAL - click to place',
            'high': 'HIGH - click to place',
            'med': 'MED - click to place',
            'low': 'LOW - click to place',
        }
        self.status_label.config(text=tool_hints.get(tool_name, 'Tool selected'))
        
    def pick_color(self):
        color = colorchooser.askcolor(initialcolor=self.rgb_to_hex(self.color))
        if color[0]:
            self.color = tuple(int(c) for c in color[0])
            self.color_indicator.config(bg=color[1])
            
    def rgb_to_hex(self, rgb):
        return f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
    
    def get_base_font_size(self):
        return 16 + self.weight * 2
    
    def get_dpi_scale(self):
        try:
            return self.root.winfo_fpixels('1i') / 72.0
        except:
            return 1.0
    
    def get_canvas_font_size(self):
        dpi_scale = self.get_dpi_scale()
        return max(10, int(self.get_base_font_size() * self.scale / dpi_scale))
    
    def get_pil_font_size(self):
        return self.get_base_font_size()
        
    def save_to_history(self):
        self.history.append(self.img.copy())
        if len(self.history) > self.max_history:
            self.history.pop(0)
            
    def undo(self):
        if self.preview_mode:
            self.cancel_preview()
            return
        if self.text_mode:
            self.cancel_preview()
            return
            
        if len(self.history) > 1:
            self.history.pop()
            self.img = self.history[-1].copy()
            self.draw = ImageDraw.Draw(self.img)
            self.refresh_canvas()
            self.status_label.config(text='Undone')
        else:
            self.status_label.config(text='Nothing to undo')
    
    def cleanup_temp_items(self):
        for item in self.temp_items:
            self.canvas.delete(item)
        self.temp_items.clear()
    
    def cleanup_preview_items(self):
        for item in self.preview_items:
            self.canvas.delete(item)
        self.preview_items.clear()
            
    def on_mouse_down(self, event):
        if self.preview_mode and self.preview_items:
            if self.is_click_on_preview(event.x, event.y):
                self.dragging = True
                self.drag_start_x = event.x
                self.drag_start_y = event.y
                self.status_label.config(text='Dragging...')
                return
            else:
                self.commit_preview()
        
        if not self.tool:
            return
        
        if self.text_mode and self.text_buffer:
            self.create_element_preview()
            return
            
        self.start_x = int(event.x / self.scale)
        self.start_y = int(event.y / self.scale)
        
        if self.tool == 'text':
            self.start_text_mode(self.start_x, self.start_y)
        elif self.tool == 'highlight':
            self.highlighter_points = [(self.start_x, self.start_y)]
        elif self.tool in ['step', 'pointer', 'magnifier', 'tip', 'warning', 
                           'bug', 'fail', 'pass', 'question', 'critical', 'high', 'med', 'low']:
            # Stamp tools - place on click
            self.place_stamp(self.start_x, self.start_y)
    
    def place_stamp(self, x, y):
        """Place a stamp at the given position"""
        stamp_map = {
            'step': self.get_step_number(),
            'pointer': '👆',
            'magnifier': '🔍',
            'tip': '💡',
            'warning': '⚠️',
            'bug': '🐛',
            'fail': '❌',
            'pass': '✅',
            'question': '❓',
        }
        
        badge_map = {
            'critical': ('CRITICAL', '#ff0000', '#ffffff'),
            'high': ('HIGH', '#ff6600', '#ffffff'),
            'med': ('MED', '#ffcc00', '#000000'),
            'low': ('LOW', '#00cc00', '#ffffff'),
        }
        
        if self.tool in stamp_map:
            stamp_text = stamp_map[self.tool]
            self.preview_data = {
                'type': 'stamp',
                'stamp': stamp_text,
                'x': x,
                'y': y,
                'color': self.color  # Store selected color
            }
            
            # Draw on canvas with selected color
            item = self.canvas.create_text(
                x * self.scale, y * self.scale,
                text=stamp_text,
                font=('Arial', int(48 * self.scale)),
                fill=self.rgb_to_hex(self.color),
                anchor=tk.CENTER
            )
            self.preview_items.append(item)
            
            if self.tool == 'step':
                self.step_counter = min(9, self.step_counter + 1)
                self.status_label.config(text=f'Next: Step {self.step_counter}')
                
        elif self.tool in badge_map:
            text, bg_color, fg_color = badge_map[self.tool]
            self.preview_data = {
                'type': 'badge',
                'text': text,
                'bg_color': bg_color,
                'fg_color': fg_color,
                'x': x,
                'y': y
            }
            
            # Draw badge on canvas
            pad = 4
            font_size = int(14 * self.scale)
            
            # Create text first to get size
            text_item = self.canvas.create_text(
                x * self.scale, y * self.scale,
                text=text,
                font=('Arial', font_size, 'bold'),
                fill=fg_color,
                anchor=tk.CENTER
            )
            bbox = self.canvas.bbox(text_item)
            
            # Create background
            bg_item = self.canvas.create_rectangle(
                bbox[0] - pad, bbox[1] - pad,
                bbox[2] + pad, bbox[3] + pad,
                fill=bg_color, outline=''
            )
            self.canvas.tag_raise(text_item)
            
            self.preview_items.append(bg_item)
            self.preview_items.append(text_item)
        
        self.add_preview_border()
        self.preview_mode = True
        self.start_x = None
        self.start_y = None
        self.status_label.config(text='Drag to move, click outside to place')
    
    def get_step_number(self):
        """Get circled number for current step"""
        numbers = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨']
        idx = min(self.step_counter - 1, 8)
        return numbers[idx]
    
    def is_click_on_preview(self, x, y):
        for item in self.preview_items:
            bbox = self.canvas.bbox(item)
            if bbox and bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]:
                return True
        return False
            
    def on_mouse_move(self, event):
        if self.dragging and self.preview_mode:
            dx = event.x - self.drag_start_x
            dy = event.y - self.drag_start_y
            
            for item in self.preview_items:
                self.canvas.move(item, dx, dy)
            
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            return
        
        if not self.tool or self.start_x is None or self.tool == 'text':
            return
        
        # Skip for stamp tools
        if self.tool in ['step', 'pointer', 'magnifier', 'tip', 'warning',
                         'bug', 'fail', 'pass', 'question', 'critical', 'high', 'med', 'low']:
            return
        
        if self.tool == 'highlight':
            px = int(event.x / self.scale)
            py = int(event.y / self.scale)
            self.highlighter_points.append((px, py))
            
            if len(self.highlighter_points) >= 2:
                p1 = self.highlighter_points[-2]
                p2 = self.highlighter_points[-1]
                
                color = self.rgb_to_hex(self.color)
                width = max(8, int(self.weight * 3 * self.scale))
                
                item = self.canvas.create_line(
                    p1[0] * self.scale, p1[1] * self.scale,
                    p2[0] * self.scale, p2[1] * self.scale,
                    fill=color, width=width, capstyle=tk.ROUND, joinstyle=tk.ROUND,
                    stipple='gray50'
                )
                self.temp_items.append(item)
            return
        
        if self.tool == 'blur':
            # Show blur preview rectangle
            self.cleanup_temp_items()
            
            sx, sy = self.start_x * self.scale, self.start_y * self.scale
            ex, ey = event.x, event.y
            
            # Draw dashed rectangle to show blur area
            item = self.canvas.create_rectangle(
                sx, sy, ex, ey,
                outline='#ff6600', width=2, dash=(4, 4)
            )
            self.temp_items.append(item)
            
            # Add "BLUR" text in center
            cx, cy = (sx + ex) / 2, (sy + ey) / 2
            text_item = self.canvas.create_text(
                cx, cy, text='BLUR', fill='#ff6600',
                font=('Arial', 10, 'bold')
            )
            self.temp_items.append(text_item)
            return
            
        self.cleanup_temp_items()
        
        end_x, end_y = event.x, event.y
        color = self.rgb_to_hex(self.color)
        width = max(1, int(self.weight * self.scale))
        sx, sy = self.start_x * self.scale, self.start_y * self.scale
        
        if self.tool == 'arrow':
            item = self.canvas.create_line(sx, sy, end_x, end_y, arrow=tk.LAST, fill=color, width=width)
            self.temp_items.append(item)
        elif self.tool == 'hline':
            item = self.canvas.create_line(sx, sy, end_x, sy, fill=color, width=width)
            self.temp_items.append(item)
        elif self.tool == 'vline':
            item = self.canvas.create_line(sx, sy, sx, end_y, fill=color, width=width)
            self.temp_items.append(item)
        elif self.tool == 'rect':
            item = self.canvas.create_rectangle(sx, sy, end_x, end_y, outline=color, width=width)
            self.temp_items.append(item)
        elif self.tool == 'circle':
            radius = ((end_x - sx)**2 + (end_y - sy)**2)**0.5
            item = self.canvas.create_oval(sx - radius, sy - radius, sx + radius, sy + radius, outline=color, width=width)
            self.temp_items.append(item)
        elif self.tool == 'ellipse':
            item = self.canvas.create_oval(sx, sy, end_x, end_y, outline=color, width=width)
            self.temp_items.append(item)

    def on_mouse_release(self, event):
        if self.dragging:
            self.dragging = False
            self.status_label.config(text='Drag to move, click outside to place')
            return
        
        if not self.tool or self.start_x is None or self.tool == 'text':
            return
        
        # Skip for stamp tools (handled in mouse_down)
        if self.tool in ['step', 'pointer', 'magnifier', 'tip', 'warning',
                         'bug', 'fail', 'pass', 'question', 'critical', 'high', 'med', 'low']:
            return
        
        if self.tool == 'highlight':
            if len(self.highlighter_points) >= 2:
                self.preview_data = {
                    'type': 'highlight',
                    'points': self.highlighter_points.copy(),
                    'color': self.color,
                    'weight': self.weight,
                    'opacity': self.highlighter_opacity
                }
                
                self.preview_items = self.temp_items.copy()
                self.temp_items = []
                
                self.add_preview_border()
                
                self.preview_mode = True
                self.start_x = None
                self.start_y = None
                self.status_label.config(text='Drag to move, click outside to place')
            else:
                self.cleanup_temp_items()
                self.highlighter_points = []
            return
        
        if self.tool == 'blur':
            end_x = int(event.x / self.scale)
            end_y = int(event.y / self.scale)
            
            # Ensure valid rectangle
            x1, y1 = min(self.start_x, end_x), min(self.start_y, end_y)
            x2, y2 = max(self.start_x, end_x), max(self.start_y, end_y)
            
            if x2 - x1 > 5 and y2 - y1 > 5:
                self.preview_data = {
                    'type': 'blur',
                    'x1': x1, 'y1': y1,
                    'x2': x2, 'y2': y2
                }
                
                # Show pixelated preview on canvas
                self.cleanup_temp_items()
                
                # Create pixelated preview
                preview_rect = self.canvas.create_rectangle(
                    x1 * self.scale, y1 * self.scale,
                    x2 * self.scale, y2 * self.scale,
                    fill='#888888', stipple='gray50', outline='#ff6600', width=2
                )
                self.preview_items.append(preview_rect)
                
                self.add_preview_border()
                self.preview_mode = True
                self.status_label.config(text='Drag to move, click outside to place')
            else:
                self.cleanup_temp_items()
            
            self.start_x = None
            self.start_y = None
            return
        
        end_x = int(event.x / self.scale)
        end_y = int(event.y / self.scale)
        
        self.preview_data = {
            'type': self.tool,
            'start_x': self.start_x,
            'start_y': self.start_y,
            'end_x': end_x,
            'end_y': end_y,
            'color': self.color,
            'weight': self.weight
        }
        
        self.preview_items = self.temp_items.copy()
        self.temp_items = []
        
        self.add_preview_border()
        
        self.preview_mode = True
        self.start_x = None
        self.start_y = None
        self.status_label.config(text='Drag to move, click outside to place')
    
    def add_preview_border(self):
        if not self.preview_items:
            return
        
        min_x, min_y, max_x, max_y = None, None, None, None
        for item in self.preview_items:
            bbox = self.canvas.bbox(item)
            if bbox:
                if min_x is None:
                    min_x, min_y, max_x, max_y = bbox
                else:
                    min_x = min(min_x, bbox[0])
                    min_y = min(min_y, bbox[1])
                    max_x = max(max_x, bbox[2])
                    max_y = max(max_y, bbox[3])
        
        if min_x is not None:
            padding = 5
            border = self.canvas.create_rectangle(
                min_x - padding, min_y - padding,
                max_x + padding, max_y + padding,
                outline='#0088ff', width=2, dash=(4, 4)
            )
            self.preview_items.append(border)
        
    def start_text_mode(self, x, y):
        self.text_mode = True
        self.text_position = (x, y)
        self.text_buffer = ""
        self.status_label.config(text='Type text, Enter when done')
        self.show_text_preview()
        
    def show_text_preview(self):
        self.cleanup_temp_items()
        
        if self.text_position and self.text_buffer:
            x, y = self.text_position
            text_item = self.canvas.create_text(
                x * self.scale, y * self.scale,
                text=self.text_buffer,
                anchor=tk.NW,
                fill=self.rgb_to_hex(self.color),
                font=('Arial', self.get_canvas_font_size())
            )
            self.temp_items.append(text_item)
        elif self.text_position:
            x, y = self.text_position
            dot = self.canvas.create_oval(
                x * self.scale - 3, y * self.scale - 3,
                x * self.scale + 3, y * self.scale + 3,
                fill=self.rgb_to_hex(self.color), outline=''
            )
            self.temp_items.append(dot)
            
    def on_key_press(self, event):
        if not self.text_mode or self.preview_mode:
            return
            
        if event.keysym == 'BackSpace':
            if self.text_buffer:
                self.text_buffer = self.text_buffer[:-1]
                self.show_text_preview()
        elif event.char and event.char.isprintable():
            self.text_buffer += event.char
            self.show_text_preview()
    
    def create_element_preview(self):
        if not self.text_buffer or not self.text_position:
            return
        
        self.cleanup_temp_items()
        
        x, y = self.text_position
        
        text_item = self.canvas.create_text(
            x * self.scale, y * self.scale,
            text=self.text_buffer,
            anchor=tk.NW,
            fill=self.rgb_to_hex(self.color),
            font=('Arial', self.get_canvas_font_size())
        )
        self.preview_items.append(text_item)
        
        self.preview_data = {
            'type': 'text',
            'text': self.text_buffer,
            'color': self.color,
            'font_size': self.get_pil_font_size()
        }
        
        self.add_preview_border()
        
        self.preview_mode = True
        self.text_mode = False
        self.status_label.config(text='Drag to move, click outside to place')

    def draw_highlighter(self, points, color, weight, opacity):
        if len(points) < 2:
            return
        
        overlay = Image.new('RGBA', self.img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        line_width = max(8, weight * 3)
        rgba_color = (color[0], color[1], color[2], opacity)
        
        for i in range(len(points) - 1):
            x1, y1 = int(points[i][0]), int(points[i][1])
            x2, y2 = int(points[i + 1][0]), int(points[i + 1][1])
            overlay_draw.line([(x1, y1), (x2, y2)], fill=rgba_color, width=line_width)
            r = line_width // 2
            overlay_draw.ellipse([x1 - r, y1 - r, x1 + r, y1 + r], fill=rgba_color)
        
        if points:
            x, y = int(points[-1][0]), int(points[-1][1])
            r = line_width // 2
            overlay_draw.ellipse([x - r, y - r, x + r, y + r], fill=rgba_color)
        
        if self.img.mode != 'RGBA':
            self.img = self.img.convert('RGBA')
        
        self.img = Image.alpha_composite(self.img, overlay)
        self.img = self.img.convert('RGB')
        self.draw = ImageDraw.Draw(self.img)

    def apply_blur(self, x1, y1, x2, y2):
        """Apply pixelation blur to region"""
        # Clamp to image bounds
        x1 = max(0, min(x1, self.img.width - 1))
        y1 = max(0, min(y1, self.img.height - 1))
        x2 = max(0, min(x2, self.img.width))
        y2 = max(0, min(y2, self.img.height))
        
        if x2 <= x1 or y2 <= y1:
            return
        
        # Extract region
        region = self.img.crop((x1, y1, x2, y2))
        
        # Pixelate by downscaling then upscaling
        pixel_size = 10
        small_w = max(1, (x2 - x1) // pixel_size)
        small_h = max(1, (y2 - y1) // pixel_size)
        
        small = region.resize((small_w, small_h), Image.Resampling.NEAREST)
        pixelated = small.resize((x2 - x1, y2 - y1), Image.Resampling.NEAREST)
        
        # Paste back
        self.img.paste(pixelated, (x1, y1))
        self.draw = ImageDraw.Draw(self.img)

    def draw_stamp(self, stamp_text, x, y, color=None):
        """Draw stamp emoji/text on image"""
        if color is None:
            color = self.color  # Use selected color
        
        try:
            # Try to use a font that supports emojis
            font_obj = ImageFont.truetype("seguiemj.ttf", 48)
        except:
            try:
                font_obj = ImageFont.truetype("arial.ttf", 48)
            except:
                font_obj = ImageFont.load_default()
        
        # Get text size for centering
        bbox = self.draw.textbbox((0, 0), stamp_text, font=font_obj)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        # Draw with selected color
        self.draw.text((x - text_w // 2, y - text_h // 2), stamp_text, fill=color, font=font_obj)

    def draw_badge(self, text, x, y, bg_color, fg_color):
        """Draw severity badge on image"""
        try:
            font_obj = ImageFont.truetype("arial.ttf", 14)
        except:
            font_obj = ImageFont.load_default()
        
        # Get text size
        bbox = self.draw.textbbox((0, 0), text, font=font_obj)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        pad = 4
        # Draw background
        self.draw.rectangle(
            [x - text_w // 2 - pad, y - text_h // 2 - pad,
             x + text_w // 2 + pad, y + text_h // 2 + pad],
            fill=bg_color
        )
        
        # Draw text
        self.draw.text((x - text_w // 2, y - text_h // 2), text, fill=fg_color, font=font_obj)

    def commit_preview(self):
        if not self.preview_mode or not self.preview_data:
            return
        
        data = self.preview_data
        
        main_item = self.preview_items[0] if self.preview_items else None
        if not main_item:
            self.cancel_preview()
            return
        
        if data['type'] == 'text':
            coords = self.canvas.coords(main_item)
            if coords:
                x = int(coords[0] / self.scale)
                y = int(coords[1] / self.scale)
            else:
                x, y = 0, 0
            
            try:
                font_obj = ImageFont.truetype("arial.ttf", data['font_size'])
            except:
                font_obj = ImageFont.load_default()
            
            self.draw.text((x, y), data['text'], fill=data['color'], font=font_obj)
            
        elif data['type'] == 'highlight':
            preview_items_no_border = self.preview_items[:-1] if len(self.preview_items) > 1 else self.preview_items
            
            if preview_items_no_border:
                first_item = preview_items_no_border[0]
                item_coords = self.canvas.coords(first_item)
                
                if item_coords and len(data['points']) >= 2:
                    orig_x = data['points'][0][0] * self.scale
                    orig_y = data['points'][0][1] * self.scale
                    
                    curr_x = item_coords[0]
                    curr_y = item_coords[1]
                    
                    offset_x = (curr_x - orig_x) / self.scale
                    offset_y = (curr_y - orig_y) / self.scale
                    
                    adjusted_points = [(p[0] + offset_x, p[1] + offset_y) for p in data['points']]
                else:
                    adjusted_points = data['points']
            else:
                adjusted_points = data['points']
            
            self.draw_highlighter(adjusted_points, data['color'], data['weight'], data['opacity'])
            
        elif data['type'] == 'blur':
            # Get current position from preview item
            bbox = self.canvas.bbox(main_item)
            if bbox:
                x1 = int(bbox[0] / self.scale)
                y1 = int(bbox[1] / self.scale)
                x2 = int(bbox[2] / self.scale)
                y2 = int(bbox[3] / self.scale)
                self.apply_blur(x1, y1, x2, y2)
                
        elif data['type'] == 'stamp':
            coords = self.canvas.coords(main_item)
            if coords:
                x = int(coords[0] / self.scale)
                y = int(coords[1] / self.scale)
                stamp_color = data.get('color', self.color)
                self.draw_stamp(data['stamp'], x, y, stamp_color)
                
        elif data['type'] == 'badge':
            # Find center from text item (second item, after bg)
            if len(self.preview_items) >= 2:
                text_item = self.preview_items[1]
                coords = self.canvas.coords(text_item)
            else:
                coords = self.canvas.coords(main_item)
            
            if coords:
                x = int(coords[0] / self.scale)
                y = int(coords[1] / self.scale)
                self.draw_badge(data['text'], x, y, data['bg_color'], data['fg_color'])
            
        else:
            item_coords = self.canvas.coords(main_item)
            if not item_coords:
                self.cancel_preview()
                return
            
            if data['type'] in ['arrow', 'hline', 'vline']:
                curr_sx, curr_sy = item_coords[0], item_coords[1]
                curr_ex, curr_ey = item_coords[2], item_coords[3]
            else:
                curr_sx, curr_sy = item_coords[0], item_coords[1]
                curr_ex, curr_ey = item_coords[2], item_coords[3]
            
            x1 = int(curr_sx / self.scale)
            y1 = int(curr_sy / self.scale)
            x2 = int(curr_ex / self.scale)
            y2 = int(curr_ey / self.scale)
            
            color = data['color']
            weight = data['weight']
            
            if data['type'] == 'arrow':
                self.draw_arrow(x1, y1, x2, y2, color, weight)
            elif data['type'] == 'hline':
                self.draw.line([x1, y1, x2, y1], fill=color, width=weight)
            elif data['type'] == 'vline':
                self.draw.line([x1, y1, x1, y2], fill=color, width=weight)
            elif data['type'] == 'rect':
                self.draw.rectangle([x1, y1, x2, y2], outline=color, width=weight)
            elif data['type'] == 'circle':
                self.draw.ellipse([x1, y1, x2, y2], outline=color, width=weight)
            elif data['type'] == 'ellipse':
                self.draw.ellipse([x1, y1, x2, y2], outline=color, width=weight)
        
        self.save_to_history()
        self.cleanup_preview_items()
        self.preview_mode = False
        self.preview_data = None
        self.text_buffer = ""
        self.text_position = None
        self.highlighter_points = []
        self.refresh_canvas()
        self.status_label.config(text='Element placed')

    def cancel_preview(self):
        self.cleanup_preview_items()
        self.cleanup_temp_items()
        self.preview_mode = False
        self.preview_data = None
        self.text_mode = False
        self.text_buffer = ""
        self.text_position = None
        self.highlighter_points = []
        self.dragging = False
        self.status_label.config(text='Cancelled')
        
    def draw_arrow(self, x1, y1, x2, y2, color, weight):
        self.draw.line([x1, y1, x2, y2], fill=color, width=weight)
        
        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_length = 15 + weight * 2
        arrow_width = 6 + weight
        
        tip_x, tip_y = x2, y2
        base_left_x = x2 - arrow_length * math.cos(angle) - arrow_width * math.sin(angle)
        base_left_y = y2 - arrow_length * math.sin(angle) + arrow_width * math.cos(angle)
        base_right_x = x2 - arrow_length * math.cos(angle) + arrow_width * math.sin(angle)
        base_right_y = y2 - arrow_length * math.sin(angle) - arrow_width * math.cos(angle)
    
        self.draw.polygon(
            [(tip_x, tip_y), (base_left_x, base_left_y), (base_right_x, base_right_y)],
            fill=color, outline=color
        )
        
    def handle_return(self):
        if self.text_mode and not self.preview_mode:
            if self.text_buffer:
                self.create_element_preview()
        elif self.preview_mode:
            self.commit_preview()
        else:
            self.save('local')  # Default to local save on Enter
            
    def handle_escape(self):
        if self.text_mode or self.preview_mode:
            self.cancel_preview()
        else:
            self.cancel()
            
    def refresh_canvas(self):
        if self.scale != 1.0:
            self.display_img = self.img.resize(
                (int(self.img.width * self.scale), int(self.img.height * self.scale)),
                Image.Resampling.LANCZOS
            )
        else:
            self.display_img = self.img.copy()
            
        self.photo = ImageTk.PhotoImage(self.display_img)
        self.canvas.delete('all')
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
    
    def add_metadata(self, img):
        """Add ViewClipper metadata to image"""
        meta = PngImagePlugin.PngInfo()
        meta.add_text("viewclipper_version", "1.0")
        meta.add_text("viewclipper_mode", self.current_mode)
        meta.add_text("viewclipper_captured_at", datetime.now().isoformat())
        return meta
        
    def save(self, action='local'):
        """
        action: 'local' or 'cloud'
        """
        if self.preview_mode:
            self.commit_preview()
        elif self.text_mode and self.text_buffer:
            self.create_element_preview()
            self.commit_preview()
        
        self.save_action = action
        self.metadata = self.add_metadata(self.img)
        self.result = self.img
        self.root.quit()
        self.root.destroy()
        
    def cancel(self):
        self.result = None
        self.root.quit()
        self.root.destroy()
        
    def run(self):
        self.root.mainloop()
        return self.result


def edit_image(img):
    """
    Open editor and return tuple: (image, metadata, action)
    action will be 'local' or 'cloud'
    """
    editor = ImageEditor(img)
    result = editor.run()
    
    if result and hasattr(editor, 'metadata'):
        return (result, editor.metadata, editor.save_action)
    return None