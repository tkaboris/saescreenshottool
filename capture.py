from mss import mss
from PIL import Image, ImageDraw, ImageTk, ImageFont, ImageFilter, PngImagePlugin
import os
from config import Config
import ctypes
import time
import io
import win32clipboard
import tkinter as tk
from tkinter import colorchooser
import math
import sys
from datetime import datetime


def set_dpi_awareness():
    """Set process DPI awareness to get correct screen dimensions"""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except:
                pass


set_dpi_awareness()


def get_dpi_scale():
    """Get Windows DPI scaling factor"""
    try:
        dc = ctypes.windll.user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(dc, 88)
        ctypes.windll.user32.ReleaseDC(0, dc)
        return dpi / 96.0
    except:
        return 1.0


def get_screen_size():
    """Get actual physical screen size in pixels"""
    try:
        width = ctypes.windll.user32.GetSystemMetrics(0)
        height = ctypes.windll.user32.GetSystemMetrics(1)
        return width, height
    except:
        return 1920, 1080


def get_resource_path(filename):
    """Get path to resource, works for dev and PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


class RegionSelector:
    def __init__(self):
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.selected_region = None
        self.dpi_scale = get_dpi_scale()
        
    def select_region(self):
        """Show fullscreen overlay to select region"""
        screen_width, screen_height = get_screen_size()
        
        root = tk.Tk()
        root.overrideredirect(True)
        root.geometry(f"{screen_width}x{screen_height}+0+0")
        root.attributes('-alpha', 0.3)
        root.configure(background='grey')
        root.attributes('-topmost', True)
        root.lift()
        root.focus_force()
        
        canvas = tk.Canvas(root, cursor="cross", bg='grey', highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        
        label = tk.Label(
            root, 
            text="Drag to select region • ESC to cancel",
            bg='#333', fg='white', font=('Arial', 14, 'bold'),
            padx=20, pady=10
        )
        label.place(relx=0.5, y=30, anchor='center')
        
        def on_mouse_down(event):
            self.start_x = event.x
            self.start_y = event.y
            
        def on_mouse_move(event):
            if self.start_x is not None and self.start_y is not None:
                if self.rect:
                    canvas.delete(self.rect)
                self.rect = canvas.create_rectangle(
                    self.start_x, self.start_y, event.x, event.y,
                    outline='red', width=3, fill='white', stipple='gray50'
                )
                
        def on_mouse_up(event):
            if self.start_x is None or self.start_y is None:
                return
                
            x1, y1 = min(self.start_x, event.x), min(self.start_y, event.y)
            x2, y2 = max(self.start_x, event.x), max(self.start_y, event.y)
            
            if (x2 - x1) < 10 or (y2 - y1) < 10:
                self.selected_region = None
            else:
                self.selected_region = (int(x1), int(y1), int(x2 - x1), int(y2 - y1))
            root.quit()
            root.destroy()
        
        def on_escape(event):
            self.selected_region = None
            root.quit()
            root.destroy()
            
        canvas.bind('<ButtonPress-1>', on_mouse_down)
        canvas.bind('<B1-Motion>', on_mouse_move)
        canvas.bind('<ButtonRelease-1>', on_mouse_up)
        root.bind('<Escape>', on_escape)
        
        root.mainloop()
        time.sleep(0.1)
        return self.selected_region


class LightshotRegionCapture:
    """Lightshot-style region capture with integrated editing toolbar"""
    
    def __init__(self, default_to_clipboard=True):
        self.root = None
        self.canvas = None
        self.full_screenshot = None
        self.photo = None
        self.dim_overlay = None
        
        self.default_to_clipboard = default_to_clipboard
        
        self.selecting = True
        self.start_x = None
        self.start_y = None
        self.current_rect = None
        self.selection = None
        
        self.tool = None
        self.color = (255, 0, 0)
        self.weight = 3
        self.drawing = False
        self.draw_start_x = None
        self.draw_start_y = None
        self.temp_items = []
        self.drawn_items = []
        
        self.text_mode = False
        self.text_position = None
        self.text_buffer = ""
        self.text_cursor = None
        
        self.highlighter_points = []
        
        self.toolbar_frame = None
        self.tool_buttons = {}
        
        self.result = None
        self.save_action = None
        self.metadata = None
        
        self.img = None
        self.draw = None
    
    def capture_and_edit(self):
        """Main entry point - capture screen and start selection/editing"""
        screen_width, screen_height = get_screen_size()
        
        with mss() as sct:
            monitor = {"top": 0, "left": 0, "width": screen_width, "height": screen_height}
            screenshot = sct.grab(monitor)
            self.full_screenshot = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
        
        self.img = self.full_screenshot.copy()
        self.draw = ImageDraw.Draw(self.img)
        
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.geometry(f"{screen_width}x{screen_height}+0+0")
        self.root.attributes('-topmost', True)
        self.root.lift()
        self.root.focus_force()
        
        self.canvas = tk.Canvas(self.root, width=screen_width, height=screen_height, 
                                highlightthickness=0, cursor="cross")
        self.canvas.pack()
        
        self.photo = ImageTk.PhotoImage(self.img)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo, tags="screenshot")
        
        self.dim_overlay = self.canvas.create_rectangle(
            0, 0, screen_width, screen_height,
            fill='black', stipple='gray50', tags="dim"
        )
        
        self.instruction_label = tk.Label(
            self.root,
            text="Drag to select region • ESC to cancel",
            bg='#333', fg='white', font=('Arial', 12, 'bold'),
            padx=15, pady=8
        )
        self.instruction_label.place(relx=0.5, y=30, anchor='center')
        
        self.canvas.bind('<ButtonPress-1>', self.on_mouse_down)
        self.canvas.bind('<B1-Motion>', self.on_mouse_move)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_up)
        self.root.bind('<Escape>', self.on_escape)
        self.root.bind('<Return>', self.on_enter)
        self.root.bind('<Key>', self.on_key_press)
        
        self.root.mainloop()
        
        if self.result:
            return (self.result, self.metadata, self.save_action)
        return None
    
    def on_mouse_down(self, event):
        if self.selecting:
            self.start_x = event.x
            self.start_y = event.y
        elif self.tool:
            self.drawing = True
            self.draw_start_x = event.x
            self.draw_start_y = event.y
            
            if self.tool == 'text':
                self.start_text_mode(event.x, event.y)
            elif self.tool == 'highlight':
                self.highlighter_points = [(event.x, event.y)]
    
    def on_mouse_move(self, event):
        if self.selecting and self.start_x is not None:
            if self.current_rect:
                self.canvas.delete(self.current_rect)
            
            self.current_rect = self.canvas.create_rectangle(
                self.start_x, self.start_y, event.x, event.y,
                outline='red', width=2, tags="selection"
            )
            
            self.update_dim_overlay(self.start_x, self.start_y, event.x, event.y)
            
        elif self.drawing and self.tool:
            if self.tool == 'highlight':
                self.highlighter_points.append((event.x, event.y))
                if len(self.highlighter_points) >= 2:
                    p1 = self.highlighter_points[-2]
                    p2 = self.highlighter_points[-1]
                    item = self.canvas.create_line(
                        p1[0], p1[1], p2[0], p2[1],
                        fill=self.rgb_to_hex(self.color), width=self.weight * 3,
                        capstyle=tk.ROUND, stipple='gray50', tags="drawing"
                    )
                    self.temp_items.append(item)
            elif self.tool == 'blur':
                self.cleanup_temp_items()
                item = self.canvas.create_rectangle(
                    self.draw_start_x, self.draw_start_y, event.x, event.y,
                    outline='#ff6600', width=2, dash=(4, 4), tags="temp"
                )
                self.temp_items.append(item)
            elif self.tool != 'text':
                self.cleanup_temp_items()
                self.draw_preview_shape(event.x, event.y)
    
    def on_mouse_up(self, event):
        if self.selecting and self.start_x is not None:
            x1, y1 = min(self.start_x, event.x), min(self.start_y, event.y)
            x2, y2 = max(self.start_x, event.x), max(self.start_y, event.y)
            
            if (x2 - x1) >= 10 and (y2 - y1) >= 10:
                self.selection = (x1, y1, x2, y2)
                self.selecting = False
                
                self.instruction_label.place_forget()
                
                if self.current_rect:
                    self.canvas.delete(self.current_rect)
                self.current_rect = self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    outline='#00aaff', width=2, tags="selection"
                )
                
                self.update_dim_overlay(x1, y1, x2, y2)
                self.show_toolbar()
                self.canvas.config(cursor="arrow")
            else:
                self.start_x = None
                self.start_y = None
                if self.current_rect:
                    self.canvas.delete(self.current_rect)
                    self.current_rect = None
                    
        elif self.drawing and self.tool:
            self.drawing = False
            
            if self.tool == 'text':
                pass
            elif self.tool == 'highlight':
                if len(self.highlighter_points) >= 2:
                    self.commit_highlighter()
                self.highlighter_points = []
            elif self.tool == 'blur':
                self.commit_blur(event.x, event.y)
            else:
                self.commit_shape(event.x, event.y)
            
            self.cleanup_temp_items()
    
    def update_dim_overlay(self, x1, y1, x2, y2):
        """Update the dim overlay to have a clear hole where selection is"""
        self.canvas.delete("dim")
        
        screen_width, screen_height = get_screen_size()
        
        self.canvas.create_rectangle(0, 0, screen_width, y1, 
                                     fill='black', stipple='gray50', tags="dim")
        self.canvas.create_rectangle(0, y2, screen_width, screen_height,
                                     fill='black', stipple='gray50', tags="dim")
        self.canvas.create_rectangle(0, y1, x1, y2,
                                     fill='black', stipple='gray50', tags="dim")
        self.canvas.create_rectangle(x2, y1, screen_width, y2,
                                     fill='black', stipple='gray50', tags="dim")
    
    def show_toolbar(self):
        """Show editing toolbar positioned near the selection"""
        if not self.selection:
            return
        
        x1, y1, x2, y2 = self.selection
        screen_width, screen_height = get_screen_size()
        
        self.toolbar_frame = tk.Frame(self.root, bg='#3c3c3c', padx=5, pady=5)
        
        tools = [
            ('→', 'arrow', 'Arrow'),
            ('□', 'rect', 'Rectangle'),
            ('○', 'circle', 'Circle'),
            ('—', 'line', 'Line'),
            ('T', 'text', 'Text'),
            ('🖍', 'highlight', 'Highlighter'),
            ('▦', 'blur', 'Blur'),
        ]
        
        for icon, tool_name, tooltip in tools:
            btn = tk.Button(
                self.toolbar_frame, text=icon,
                command=lambda t=tool_name: self.select_tool(t),
                bg='#4a4a4a', fg='white',
                width=3, font=('Arial', 10),
                relief=tk.RAISED, cursor='hand2'
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.tool_buttons[tool_name] = btn
        
        tk.Frame(self.toolbar_frame, bg='#666', width=2).pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=2)
        
        self.color_btn = tk.Button(
            self.toolbar_frame, text='🎨',
            command=self.pick_color,
            bg='#4a4a4a', fg='white',
            width=3, font=('Arial', 10),
            relief=tk.RAISED, cursor='hand2'
        )
        self.color_btn.pack(side=tk.LEFT, padx=2)
        
        self.color_indicator = tk.Label(
            self.toolbar_frame, text='  ', bg=self.rgb_to_hex(self.color),
            width=2, relief=tk.SUNKEN
        )
        self.color_indicator.pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            self.toolbar_frame, text='-',
            command=lambda: self.adjust_weight(-1),
            bg='#4a4a4a', fg='white', width=2,
            font=('Arial', 9), relief=tk.RAISED, cursor='hand2'
        ).pack(side=tk.LEFT, padx=1)
        
        self.weight_label = tk.Label(
            self.toolbar_frame, text=str(self.weight), bg='#555', fg='white',
            width=2, font=('Arial', 9)
        )
        self.weight_label.pack(side=tk.LEFT)
        
        tk.Button(
            self.toolbar_frame, text='+',
            command=lambda: self.adjust_weight(1),
            bg='#4a4a4a', fg='white', width=2,
            font=('Arial', 9), relief=tk.RAISED, cursor='hand2'
        ).pack(side=tk.LEFT, padx=1)
        
        tk.Frame(self.toolbar_frame, bg='#666', width=2).pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=2)
        
        tk.Button(
            self.toolbar_frame, text='↶',
            command=self.undo,
            bg='#4a4a4a', fg='white', width=3,
            font=('Arial', 10), relief=tk.RAISED, cursor='hand2'
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Frame(self.toolbar_frame, bg='#666', width=2).pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=2)
        
        save_bg = '#2d6a2d' if not self.default_to_clipboard else '#4a4a4a'
        clip_bg = '#4a9f4a' if self.default_to_clipboard else '#4a4a4a'
        
        tk.Button(
            self.toolbar_frame, text='💾',
            command=lambda: self.save('local'),
            bg=save_bg, fg='white', width=3,
            font=('Arial', 10), relief=tk.RAISED, cursor='hand2'
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            self.toolbar_frame, text='☁️',
            command=lambda: self.save('cloud'),
            bg='#2d4a6a', fg='white', width=3,
            font=('Arial', 10), relief=tk.RAISED, cursor='hand2'
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            self.toolbar_frame, text='📋',
            command=self.copy_and_close,
            bg=clip_bg, fg='white', width=3,
            font=('Arial', 10), relief=tk.RAISED, cursor='hand2'
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            self.toolbar_frame, text='❌',
            command=self.cancel,
            bg='#6a2d2d', fg='white', width=3,
            font=('Arial', 10), relief=tk.RAISED, cursor='hand2'
        ).pack(side=tk.LEFT, padx=2)
        
        toolbar_width = 560
        toolbar_height = 40
        
        toolbar_x = (x1 + x2) // 2 - toolbar_width // 2
        toolbar_x = max(10, min(toolbar_x, screen_width - toolbar_width - 10))
        
        space_above = y1 - 50
        space_below = screen_height - y2 - 50
        
        if space_above >= toolbar_height:
            toolbar_y = y1 - toolbar_height - 10
        elif space_below >= toolbar_height:
            toolbar_y = y2 + 10
        else:
            toolbar_y = 10
        
        self.toolbar_frame.place(x=toolbar_x, y=toolbar_y)
    
    def select_tool(self, tool_name):
        # If switching away from text tool and have uncommitted text, commit it first
        if self.text_mode and self.text_buffer:
            self.commit_text()
        
        self.tool = tool_name
        self.text_mode = False
        self.text_buffer = ""
        
        for name, btn in self.tool_buttons.items():
            if name == tool_name:
                btn.configure(bg='#6a6a9a', relief=tk.SUNKEN)
            else:
                btn.configure(bg='#4a4a4a', relief=tk.RAISED)
    
    def pick_color(self):
        color = colorchooser.askcolor(initialcolor=self.rgb_to_hex(self.color))
        if color[0]:
            self.color = tuple(int(c) for c in color[0])
            self.color_indicator.config(bg=color[1])
    
    def adjust_weight(self, delta):
        self.weight = max(1, min(12, self.weight + delta))
        self.weight_label.config(text=str(self.weight))
    
    def rgb_to_hex(self, rgb):
        return f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
    
    def cleanup_temp_items(self):
        for item in self.temp_items:
            self.canvas.delete(item)
        self.temp_items.clear()
    
    def draw_preview_shape(self, end_x, end_y):
        """Draw preview of shape on canvas"""
        color = self.rgb_to_hex(self.color)
        width = self.weight
        sx, sy = self.draw_start_x, self.draw_start_y
        
        if self.tool == 'arrow':
            item = self.canvas.create_line(sx, sy, end_x, end_y, 
                                           arrow=tk.LAST, fill=color, width=width, tags="temp")
        elif self.tool == 'line':
            item = self.canvas.create_line(sx, sy, end_x, end_y, 
                                           fill=color, width=width, tags="temp")
        elif self.tool == 'rect':
            item = self.canvas.create_rectangle(sx, sy, end_x, end_y, 
                                                outline=color, width=width, tags="temp")
        elif self.tool == 'circle':
            radius = ((end_x - sx)**2 + (end_y - sy)**2)**0.5
            item = self.canvas.create_oval(sx - radius, sy - radius, 
                                           sx + radius, sy + radius,
                                           outline=color, width=width, tags="temp")
        else:
            return
        
        self.temp_items.append(item)
    
    def commit_shape(self, end_x, end_y):
        """Commit shape to both canvas and PIL image"""
        color = self.color
        width = self.weight
        sx, sy = self.draw_start_x, self.draw_start_y
        
        if self.tool == 'arrow':
            self.draw.line([sx, sy, end_x, end_y], fill=color, width=width)
            self.draw_arrow_head(sx, sy, end_x, end_y, color, width)
            self.canvas.create_line(sx, sy, end_x, end_y,
                                   arrow=tk.LAST, fill=self.rgb_to_hex(color), 
                                   width=width, tags="drawing")
            self.drawn_items.append(('arrow', sx, sy, end_x, end_y, color, width))
            
        elif self.tool == 'line':
            self.draw.line([sx, sy, end_x, end_y], fill=color, width=width)
            self.canvas.create_line(sx, sy, end_x, end_y,
                                   fill=self.rgb_to_hex(color), width=width, tags="drawing")
            self.drawn_items.append(('line', sx, sy, end_x, end_y, color, width))
            
        elif self.tool == 'rect':
            self.draw.rectangle([sx, sy, end_x, end_y], outline=color, width=width)
            self.canvas.create_rectangle(sx, sy, end_x, end_y,
                                        outline=self.rgb_to_hex(color), width=width, tags="drawing")
            self.drawn_items.append(('rect', sx, sy, end_x, end_y, color, width))
            
        elif self.tool == 'circle':
            radius = int(((end_x - sx)**2 + (end_y - sy)**2)**0.5)
            self.draw.ellipse([sx - radius, sy - radius, sx + radius, sy + radius],
                             outline=color, width=width)
            self.canvas.create_oval(sx - radius, sy - radius, sx + radius, sy + radius,
                                   outline=self.rgb_to_hex(color), width=width, tags="drawing")
            self.drawn_items.append(('circle', sx, sy, radius, color, width))
        
        self.refresh_display()
    
    def draw_arrow_head(self, x1, y1, x2, y2, color, weight):
        """Draw arrow head on PIL image"""
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
            fill=color
        )
    
    def commit_highlighter(self):
        """Commit highlighter strokes to PIL image"""
        if len(self.highlighter_points) < 2:
            return
        
        overlay = Image.new('RGBA', self.img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        line_width = max(8, self.weight * 3)
        rgba_color = (self.color[0], self.color[1], self.color[2], 100)
        
        for i in range(len(self.highlighter_points) - 1):
            x1, y1 = self.highlighter_points[i]
            x2, y2 = self.highlighter_points[i + 1]
            overlay_draw.line([(x1, y1), (x2, y2)], fill=rgba_color, width=line_width)
            r = line_width // 2
            overlay_draw.ellipse([x1 - r, y1 - r, x1 + r, y1 + r], fill=rgba_color)
        
        x, y = self.highlighter_points[-1]
        r = line_width // 2
        overlay_draw.ellipse([x - r, y - r, x + r, y + r], fill=rgba_color)
        
        if self.img.mode != 'RGBA':
            self.img = self.img.convert('RGBA')
        self.img = Image.alpha_composite(self.img, overlay)
        self.img = self.img.convert('RGB')
        self.draw = ImageDraw.Draw(self.img)
        
        self.drawn_items.append(('highlight', self.highlighter_points.copy(), self.color, self.weight))
        self.refresh_display()
    
    def commit_blur(self, end_x, end_y):
        """Apply blur/pixelation to region"""
        x1, y1 = min(self.draw_start_x, end_x), min(self.draw_start_y, end_y)
        x2, y2 = max(self.draw_start_x, end_x), max(self.draw_start_y, end_y)
        
        if x2 - x1 < 5 or y2 - y1 < 5:
            return
        
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(self.img.width, x2)
        y2 = min(self.img.height, y2)
        
        region = self.img.crop((x1, y1, x2, y2))
        pixel_size = 10
        small_w = max(1, (x2 - x1) // pixel_size)
        small_h = max(1, (y2 - y1) // pixel_size)
        small = region.resize((small_w, small_h), Image.Resampling.NEAREST)
        pixelated = small.resize((x2 - x1, y2 - y1), Image.Resampling.NEAREST)
        self.img.paste(pixelated, (x1, y1))
        self.draw = ImageDraw.Draw(self.img)
        
        self.canvas.create_rectangle(x1, y1, x2, y2, 
                                     fill='#888888', stipple='gray50', 
                                     outline='#666', tags="drawing")
        
        self.drawn_items.append(('blur', x1, y1, x2, y2))
        self.refresh_display()
    
    def start_text_mode(self, x, y):
        """Start text entry mode"""
        self.text_mode = True
        self.text_position = (x, y)
        self.text_buffer = ""
        
        self.text_cursor = self.canvas.create_text(
            x, y, text="|", anchor=tk.NW,
            fill=self.rgb_to_hex(self.color),
            font=('Arial', 12 + self.weight * 2),
            tags="text_cursor"
        )
    
    def on_key_press(self, event):
        """Handle keyboard input"""
        if self.text_mode:
            if event.keysym == 'BackSpace':
                if self.text_buffer:
                    self.text_buffer = self.text_buffer[:-1]
                    self.update_text_preview()
            elif event.keysym == 'Return':
                self.commit_text()
            elif event.char and event.char.isprintable():
                self.text_buffer += event.char
                self.update_text_preview()
    
    def update_text_preview(self):
        """Update text preview on canvas"""
        self.canvas.delete("text_cursor")
        if self.text_position:
            x, y = self.text_position
            display_text = self.text_buffer + "|" if self.text_buffer else "|"
            self.text_cursor = self.canvas.create_text(
                x, y, text=display_text, anchor=tk.NW,
                fill=self.rgb_to_hex(self.color),
                font=('Arial', 12 + self.weight * 2),
                tags="text_cursor"
            )
    
    def commit_text(self):
        """Commit text to image"""
        if not self.text_buffer or not self.text_position:
            self.text_mode = False
            self.canvas.delete("text_cursor")
            return
        
        x, y = self.text_position
        font_size = 12 + self.weight * 2
        
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        self.draw.text((x, y), self.text_buffer, fill=self.color, font=font)
        
        self.canvas.delete("text_cursor")
        self.canvas.create_text(x, y, text=self.text_buffer, anchor=tk.NW,
                               fill=self.rgb_to_hex(self.color),
                               font=('Arial', font_size), tags="drawing")
        
        self.drawn_items.append(('text', x, y, self.text_buffer, self.color, font_size))
        
        self.text_mode = False
        self.text_buffer = ""
        self.text_position = None
        self.refresh_display()
    
    def undo(self):
        """Undo last drawing operation"""
        # First commit any uncommitted text
        if self.text_mode and self.text_buffer:
            self.commit_text()
        
        if not self.drawn_items:
            return
        
        self.drawn_items.pop()
        
        self.img = self.full_screenshot.copy()
        self.draw = ImageDraw.Draw(self.img)
        
        for item in self.drawn_items:
            self.replay_item(item)
        
        self.canvas.delete("drawing")
        self.refresh_display()
        
        for item in self.drawn_items:
            self.redraw_canvas_item(item)
    
    def replay_item(self, item):
        """Replay a drawing item onto the PIL image"""
        item_type = item[0]
        
        if item_type == 'arrow':
            _, sx, sy, ex, ey, color, width = item
            self.draw.line([sx, sy, ex, ey], fill=color, width=width)
            self.draw_arrow_head(sx, sy, ex, ey, color, width)
        elif item_type == 'line':
            _, sx, sy, ex, ey, color, width = item
            self.draw.line([sx, sy, ex, ey], fill=color, width=width)
        elif item_type == 'rect':
            _, sx, sy, ex, ey, color, width = item
            self.draw.rectangle([sx, sy, ex, ey], outline=color, width=width)
        elif item_type == 'circle':
            _, sx, sy, radius, color, width = item
            self.draw.ellipse([sx - radius, sy - radius, sx + radius, sy + radius],
                             outline=color, width=width)
        elif item_type == 'text':
            _, x, y, text, color, font_size = item
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
            self.draw.text((x, y), text, fill=color, font=font)
        elif item_type == 'highlight':
            _, points, color, weight = item
            overlay = Image.new('RGBA', self.img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            line_width = max(8, weight * 3)
            rgba_color = (color[0], color[1], color[2], 100)
            for i in range(len(points) - 1):
                x1, y1 = points[i]
                x2, y2 = points[i + 1]
                overlay_draw.line([(x1, y1), (x2, y2)], fill=rgba_color, width=line_width)
            if self.img.mode != 'RGBA':
                self.img = self.img.convert('RGBA')
            self.img = Image.alpha_composite(self.img, overlay)
            self.img = self.img.convert('RGB')
            self.draw = ImageDraw.Draw(self.img)
        elif item_type == 'blur':
            _, x1, y1, x2, y2 = item
            region = self.img.crop((x1, y1, x2, y2))
            pixel_size = 10
            small_w = max(1, (x2 - x1) // pixel_size)
            small_h = max(1, (y2 - y1) // pixel_size)
            small = region.resize((small_w, small_h), Image.Resampling.NEAREST)
            pixelated = small.resize((x2 - x1, y2 - y1), Image.Resampling.NEAREST)
            self.img.paste(pixelated, (x1, y1))
            self.draw = ImageDraw.Draw(self.img)
    
    def redraw_canvas_item(self, item):
        """Redraw a single item on the canvas"""
        item_type = item[0]
        
        if item_type == 'arrow':
            _, sx, sy, ex, ey, color, width = item
            self.canvas.create_line(sx, sy, ex, ey, arrow=tk.LAST,
                                   fill=self.rgb_to_hex(color), width=width, tags="drawing")
        elif item_type == 'line':
            _, sx, sy, ex, ey, color, width = item
            self.canvas.create_line(sx, sy, ex, ey,
                                   fill=self.rgb_to_hex(color), width=width, tags="drawing")
        elif item_type == 'rect':
            _, sx, sy, ex, ey, color, width = item
            self.canvas.create_rectangle(sx, sy, ex, ey,
                                        outline=self.rgb_to_hex(color), width=width, tags="drawing")
        elif item_type == 'circle':
            _, sx, sy, radius, color, width = item
            self.canvas.create_oval(sx - radius, sy - radius, sx + radius, sy + radius,
                                   outline=self.rgb_to_hex(color), width=width, tags="drawing")
        elif item_type == 'text':
            _, x, y, text, color, font_size = item
            self.canvas.create_text(x, y, text=text, anchor=tk.NW,
                                   fill=self.rgb_to_hex(color),
                                   font=('Arial', font_size), tags="drawing")
        elif item_type == 'highlight':
            _, points, color, weight = item
            line_width = max(8, weight * 3)
            for i in range(len(points) - 1):
                self.canvas.create_line(points[i][0], points[i][1],
                                       points[i+1][0], points[i+1][1],
                                       fill=self.rgb_to_hex(color), width=line_width,
                                       capstyle=tk.ROUND, stipple='gray50', tags="drawing")
        elif item_type == 'blur':
            _, x1, y1, x2, y2 = item
            self.canvas.create_rectangle(x1, y1, x2, y2,
                                        fill='#888888', stipple='gray50',
                                        outline='#666', tags="drawing")
    
    def refresh_display(self):
        """Refresh the canvas display with current image"""
        self.photo = ImageTk.PhotoImage(self.img)
        self.canvas.delete("screenshot")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo, tags="screenshot")
        self.canvas.tag_lower("screenshot")
    
    def add_metadata(self):
        """Add ViewClipper metadata to image"""
        meta = PngImagePlugin.PngInfo()
        meta.add_text("viewclipper_version", "1.0")
        meta.add_text("viewclipper_mode", "region")
        meta.add_text("viewclipper_captured_at", datetime.now().isoformat())
        return meta
    
    def crop_to_selection(self):
        """Crop image to selected region"""
        if not self.selection:
            return self.img
        
        x1, y1, x2, y2 = self.selection
        return self.img.crop((x1, y1, x2, y2))
    
    def save(self, action='local'):
        """Save the cropped region"""
        if self.text_mode and self.text_buffer:
            self.commit_text()
        
        self.result = self.crop_to_selection()
        self.metadata = self.add_metadata()
        self.save_action = action
        self.root.quit()
        self.root.destroy()
    
    def copy_and_close(self):
        """Copy to clipboard and close"""
        if self.text_mode and self.text_buffer:
            self.commit_text()
        
        cropped = self.crop_to_selection()
        copy_to_clipboard(cropped)
        print("📋 Copied to clipboard!")
        
        self.result = None
        self.root.quit()
        self.root.destroy()
    
    def cancel(self):
        """Cancel and close"""
        self.result = None
        self.root.quit()
        self.root.destroy()
    
    def on_escape(self, event):
        """Handle escape key"""
        if self.text_mode:
            self.text_mode = False
            self.text_buffer = ""
            self.canvas.delete("text_cursor")
        else:
            self.cancel()
    
    def on_enter(self, event):
        """Handle enter key - action depends on settings"""
        if self.text_mode and self.text_buffer:
            self.commit_text()
        elif self.selection and not self.text_mode:
            if self.default_to_clipboard:
                self.copy_and_close()
            else:
                self.save('local')


class FullscreenEditor:
    """Fullscreen capture with scaled display and toolbar ABOVE the screenshot"""
    
    def __init__(self, default_to_clipboard=False):
        self.root = None
        self.canvas = None
        self.full_screenshot = None
        self.photo = None
        
        self.default_to_clipboard = default_to_clipboard
        
        # Scale factor for display
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        # Drawing state
        self.tool = None
        self.color = (255, 0, 0)
        self.weight = 3
        self.drawing = False
        self.draw_start_x = None
        self.draw_start_y = None
        self.temp_items = []
        self.drawn_items = []
        
        # Text state
        self.text_mode = False
        self.text_position = None
        self.text_buffer = ""
        self.text_cursor = None
        
        # Highlighter state
        self.highlighter_points = []
        
        # Toolbar
        self.toolbar_frame = None
        self.tool_buttons = {}
        
        # Result
        self.result = None
        self.save_action = None
        self.metadata = None
        
        # PIL drawing surface (full resolution)
        self.img = None
        self.draw = None
    
    def capture_and_edit(self):
        """Capture fullscreen and show editor with scaled preview"""
        screen_width, screen_height = get_screen_size()
        
        # Capture full screen at full resolution
        with mss() as sct:
            monitor = {"top": 0, "left": 0, "width": screen_width, "height": screen_height}
            screenshot = sct.grab(monitor)
            self.full_screenshot = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
        
        # Create working copy at full resolution
        self.img = self.full_screenshot.copy()
        self.draw = ImageDraw.Draw(self.img)
        
        # Calculate scale to fit screenshot with toolbar above
        toolbar_height = 60
        margin = 20
        available_height = screen_height - toolbar_height - margin * 2
        available_width = screen_width - margin * 2
        
        scale_x = available_width / screen_width
        scale_y = available_height / screen_height
        self.scale = min(scale_x, scale_y, 0.95)  # Max 95% to ensure margin
        
        display_width = int(screen_width * self.scale)
        display_height = int(screen_height * self.scale)
        
        # Center the scaled screenshot
        self.offset_x = (screen_width - display_width) // 2
        self.offset_y = toolbar_height + margin
        
        # Create fullscreen window with dark background
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.geometry(f"{screen_width}x{screen_height}+0+0")
        self.root.configure(bg='#2b2b2b')
        self.root.attributes('-topmost', True)
        self.root.lift()
        self.root.focus_force()
        
        # Create canvas
        self.canvas = tk.Canvas(self.root, width=screen_width, height=screen_height,
                                highlightthickness=0, bg='#2b2b2b', cursor="arrow")
        self.canvas.pack()
        
        # Create scaled display image
        self.display_img = self.img.resize((display_width, display_height), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(self.display_img)
        self.canvas.create_image(self.offset_x, self.offset_y, anchor=tk.NW, 
                                image=self.photo, tags="screenshot")
        
        # Draw border around screenshot
        self.canvas.create_rectangle(
            self.offset_x - 2, self.offset_y - 2,
            self.offset_x + display_width + 2, self.offset_y + display_height + 2,
            outline='#00aaff', width=2, tags="border"
        )
        
        # Bind events
        self.canvas.bind('<ButtonPress-1>', self.on_mouse_down)
        self.canvas.bind('<B1-Motion>', self.on_mouse_move)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_up)
        self.root.bind('<Escape>', self.on_escape)
        self.root.bind('<Return>', self.on_enter)
        self.root.bind('<Key>', self.on_key_press)
        
        # Show toolbar at top
        self.show_toolbar()
        
        self.root.mainloop()
        
        if self.result:
            return (self.result, self.metadata, self.save_action)
        return None
    
    def display_to_image(self, dx, dy):
        """Convert display coordinates to image coordinates"""
        ix = int((dx - self.offset_x) / self.scale)
        iy = int((dy - self.offset_y) / self.scale)
        return ix, iy
    
    def image_to_display(self, ix, iy):
        """Convert image coordinates to display coordinates"""
        dx = int(ix * self.scale + self.offset_x)
        dy = int(iy * self.scale + self.offset_y)
        return dx, dy
    
    def is_in_image_area(self, x, y):
        """Check if coordinates are within the image area"""
        display_width = int(self.img.width * self.scale)
        display_height = int(self.img.height * self.scale)
        return (self.offset_x <= x <= self.offset_x + display_width and
                self.offset_y <= y <= self.offset_y + display_height)
    
    def on_mouse_down(self, event):
        if not self.is_in_image_area(event.x, event.y):
            return
            
        if self.tool:
            self.drawing = True
            self.draw_start_x = event.x
            self.draw_start_y = event.y
            
            if self.tool == 'text':
                self.start_text_mode(event.x, event.y)
            elif self.tool == 'highlight':
                self.highlighter_points = [(event.x, event.y)]
    
    def on_mouse_move(self, event):
        if self.drawing and self.tool:
            if self.tool == 'highlight':
                if self.is_in_image_area(event.x, event.y):
                    self.highlighter_points.append((event.x, event.y))
                    if len(self.highlighter_points) >= 2:
                        p1 = self.highlighter_points[-2]
                        p2 = self.highlighter_points[-1]
                        item = self.canvas.create_line(
                            p1[0], p1[1], p2[0], p2[1],
                            fill=self.rgb_to_hex(self.color), 
                            width=max(1, int(self.weight * 3 * self.scale)),
                            capstyle=tk.ROUND, stipple='gray50', tags="drawing"
                        )
                        self.temp_items.append(item)
            elif self.tool == 'blur':
                self.cleanup_temp_items()
                item = self.canvas.create_rectangle(
                    self.draw_start_x, self.draw_start_y, event.x, event.y,
                    outline='#ff6600', width=2, dash=(4, 4), tags="temp"
                )
                self.temp_items.append(item)
            elif self.tool != 'text':
                self.cleanup_temp_items()
                self.draw_preview_shape(event.x, event.y)
    
    def on_mouse_up(self, event):
        if self.drawing and self.tool:
            self.drawing = False
            
            if self.tool == 'text':
                pass
            elif self.tool == 'highlight':
                if len(self.highlighter_points) >= 2:
                    self.commit_highlighter()
                self.highlighter_points = []
            elif self.tool == 'blur':
                self.commit_blur(event.x, event.y)
            else:
                self.commit_shape(event.x, event.y)
            
            self.cleanup_temp_items()
    
    def show_toolbar(self):
        """Show editing toolbar at top center"""
        screen_width, _ = get_screen_size()
        
        self.toolbar_frame = tk.Frame(self.root, bg='#3c3c3c', padx=5, pady=5)
        
        tools = [
            ('→', 'arrow', 'Arrow'),
            ('□', 'rect', 'Rectangle'),
            ('○', 'circle', 'Circle'),
            ('—', 'line', 'Line'),
            ('T', 'text', 'Text'),
            ('🖍', 'highlight', 'Highlighter'),
            ('▦', 'blur', 'Blur'),
        ]
        
        for icon, tool_name, tooltip in tools:
            btn = tk.Button(
                self.toolbar_frame, text=icon,
                command=lambda t=tool_name: self.select_tool(t),
                bg='#4a4a4a', fg='white',
                width=3, font=('Arial', 10),
                relief=tk.RAISED, cursor='hand2'
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.tool_buttons[tool_name] = btn
        
        tk.Frame(self.toolbar_frame, bg='#666', width=2).pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=2)
        
        self.color_btn = tk.Button(
            self.toolbar_frame, text='🎨',
            command=self.pick_color,
            bg='#4a4a4a', fg='white',
            width=3, font=('Arial', 10),
            relief=tk.RAISED, cursor='hand2'
        )
        self.color_btn.pack(side=tk.LEFT, padx=2)
        
        self.color_indicator = tk.Label(
            self.toolbar_frame, text='  ', bg=self.rgb_to_hex(self.color),
            width=2, relief=tk.SUNKEN
        )
        self.color_indicator.pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            self.toolbar_frame, text='-',
            command=lambda: self.adjust_weight(-1),
            bg='#4a4a4a', fg='white', width=2,
            font=('Arial', 9), relief=tk.RAISED, cursor='hand2'
        ).pack(side=tk.LEFT, padx=1)
        
        self.weight_label = tk.Label(
            self.toolbar_frame, text=str(self.weight), bg='#555', fg='white',
            width=2, font=('Arial', 9)
        )
        self.weight_label.pack(side=tk.LEFT)
        
        tk.Button(
            self.toolbar_frame, text='+',
            command=lambda: self.adjust_weight(1),
            bg='#4a4a4a', fg='white', width=2,
            font=('Arial', 9), relief=tk.RAISED, cursor='hand2'
        ).pack(side=tk.LEFT, padx=1)
        
        tk.Frame(self.toolbar_frame, bg='#666', width=2).pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=2)
        
        tk.Button(
            self.toolbar_frame, text='↶',
            command=self.undo,
            bg='#4a4a4a', fg='white', width=3,
            font=('Arial', 10), relief=tk.RAISED, cursor='hand2'
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Frame(self.toolbar_frame, bg='#666', width=2).pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=2)
        
        save_bg = '#2d6a2d' if not self.default_to_clipboard else '#4a4a4a'
        clip_bg = '#4a9f4a' if self.default_to_clipboard else '#4a4a4a'
        
        tk.Button(
            self.toolbar_frame, text='💾',
            command=lambda: self.save('local'),
            bg=save_bg, fg='white', width=3,
            font=('Arial', 10), relief=tk.RAISED, cursor='hand2'
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            self.toolbar_frame, text='☁️',
            command=lambda: self.save('cloud'),
            bg='#2d4a6a', fg='white', width=3,
            font=('Arial', 10), relief=tk.RAISED, cursor='hand2'
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            self.toolbar_frame, text='📋',
            command=self.copy_and_close,
            bg=clip_bg, fg='white', width=3,
            font=('Arial', 10), relief=tk.RAISED, cursor='hand2'
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            self.toolbar_frame, text='❌',
            command=self.cancel,
            bg='#6a2d2d', fg='white', width=3,
            font=('Arial', 10), relief=tk.RAISED, cursor='hand2'
        ).pack(side=tk.LEFT, padx=2)
        
        toolbar_width = 560
        toolbar_x = (screen_width - toolbar_width) // 2
        self.toolbar_frame.place(x=toolbar_x, y=10)
    
    def select_tool(self, tool_name):
        if self.text_mode and self.text_buffer:
            self.commit_text()
        
        self.tool = tool_name
        self.text_mode = False
        self.text_buffer = ""
        
        for name, btn in self.tool_buttons.items():
            if name == tool_name:
                btn.configure(bg='#6a6a9a', relief=tk.SUNKEN)
            else:
                btn.configure(bg='#4a4a4a', relief=tk.RAISED)
    
    def pick_color(self):
        color = colorchooser.askcolor(initialcolor=self.rgb_to_hex(self.color))
        if color[0]:
            self.color = tuple(int(c) for c in color[0])
            self.color_indicator.config(bg=color[1])
    
    def adjust_weight(self, delta):
        self.weight = max(1, min(12, self.weight + delta))
        self.weight_label.config(text=str(self.weight))
    
    def rgb_to_hex(self, rgb):
        return f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
    
    def cleanup_temp_items(self):
        for item in self.temp_items:
            self.canvas.delete(item)
        self.temp_items.clear()
    
    def draw_preview_shape(self, end_x, end_y):
        color = self.rgb_to_hex(self.color)
        width = max(1, int(self.weight * self.scale))
        sx, sy = self.draw_start_x, self.draw_start_y
        
        if self.tool == 'arrow':
            item = self.canvas.create_line(sx, sy, end_x, end_y,
                                           arrow=tk.LAST, fill=color, width=width, tags="temp")
        elif self.tool == 'line':
            item = self.canvas.create_line(sx, sy, end_x, end_y,
                                           fill=color, width=width, tags="temp")
        elif self.tool == 'rect':
            item = self.canvas.create_rectangle(sx, sy, end_x, end_y,
                                                outline=color, width=width, tags="temp")
        elif self.tool == 'circle':
            radius = ((end_x - sx)**2 + (end_y - sy)**2)**0.5
            item = self.canvas.create_oval(sx - radius, sy - radius,
                                           sx + radius, sy + radius,
                                           outline=color, width=width, tags="temp")
        else:
            return
        self.temp_items.append(item)
    
    def commit_shape(self, end_x, end_y):
        color = self.color
        width = self.weight
        
        # Convert display coords to image coords
        img_sx, img_sy = self.display_to_image(self.draw_start_x, self.draw_start_y)
        img_ex, img_ey = self.display_to_image(end_x, end_y)
        
        # Draw on full-resolution image
        if self.tool == 'arrow':
            self.draw.line([img_sx, img_sy, img_ex, img_ey], fill=color, width=width)
            self.draw_arrow_head(img_sx, img_sy, img_ex, img_ey, color, width)
            self.drawn_items.append(('arrow', img_sx, img_sy, img_ex, img_ey, color, width))
        elif self.tool == 'line':
            self.draw.line([img_sx, img_sy, img_ex, img_ey], fill=color, width=width)
            self.drawn_items.append(('line', img_sx, img_sy, img_ex, img_ey, color, width))
        elif self.tool == 'rect':
            self.draw.rectangle([img_sx, img_sy, img_ex, img_ey], outline=color, width=width)
            self.drawn_items.append(('rect', img_sx, img_sy, img_ex, img_ey, color, width))
        elif self.tool == 'circle':
            radius = int(((img_ex - img_sx)**2 + (img_ey - img_sy)**2)**0.5)
            self.draw.ellipse([img_sx - radius, img_sy - radius, img_sx + radius, img_sy + radius],
                             outline=color, width=width)
            self.drawn_items.append(('circle', img_sx, img_sy, radius, color, width))
        
        self.refresh_display()
    
    def draw_arrow_head(self, x1, y1, x2, y2, color, weight):
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
            fill=color
        )
    
    def commit_highlighter(self):
        if len(self.highlighter_points) < 2:
            return
        
        # Convert all points to image coordinates
        img_points = [self.display_to_image(x, y) for x, y in self.highlighter_points]
        
        overlay = Image.new('RGBA', self.img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        line_width = max(8, self.weight * 3)
        rgba_color = (self.color[0], self.color[1], self.color[2], 100)
        
        for i in range(len(img_points) - 1):
            x1, y1 = img_points[i]
            x2, y2 = img_points[i + 1]
            overlay_draw.line([(x1, y1), (x2, y2)], fill=rgba_color, width=line_width)
            r = line_width // 2
            overlay_draw.ellipse([x1 - r, y1 - r, x1 + r, y1 + r], fill=rgba_color)
        
        x, y = img_points[-1]
        r = line_width // 2
        overlay_draw.ellipse([x - r, y - r, x + r, y + r], fill=rgba_color)
        
        if self.img.mode != 'RGBA':
            self.img = self.img.convert('RGBA')
        self.img = Image.alpha_composite(self.img, overlay)
        self.img = self.img.convert('RGB')
        self.draw = ImageDraw.Draw(self.img)
        
        self.drawn_items.append(('highlight', img_points, self.color, self.weight))
        self.refresh_display()
    
    def commit_blur(self, end_x, end_y):
        img_x1, img_y1 = self.display_to_image(min(self.draw_start_x, end_x), 
                                                min(self.draw_start_y, end_y))
        img_x2, img_y2 = self.display_to_image(max(self.draw_start_x, end_x),
                                                max(self.draw_start_y, end_y))
        
        if img_x2 - img_x1 < 5 or img_y2 - img_y1 < 5:
            return
        
        img_x1 = max(0, img_x1)
        img_y1 = max(0, img_y1)
        img_x2 = min(self.img.width, img_x2)
        img_y2 = min(self.img.height, img_y2)
        
        region = self.img.crop((img_x1, img_y1, img_x2, img_y2))
        pixel_size = 10
        small_w = max(1, (img_x2 - img_x1) // pixel_size)
        small_h = max(1, (img_y2 - img_y1) // pixel_size)
        small = region.resize((small_w, small_h), Image.Resampling.NEAREST)
        pixelated = small.resize((img_x2 - img_x1, img_y2 - img_y1), Image.Resampling.NEAREST)
        self.img.paste(pixelated, (img_x1, img_y1))
        self.draw = ImageDraw.Draw(self.img)
        
        self.drawn_items.append(('blur', img_x1, img_y1, img_x2, img_y2))
        self.refresh_display()
    
    def start_text_mode(self, x, y):
        self.text_mode = True
        self.text_position = (x, y)
        self.text_buffer = ""
        
        font_size = max(8, int((12 + self.weight * 2) * self.scale))
        self.text_cursor = self.canvas.create_text(
            x, y, text="|", anchor=tk.NW,
            fill=self.rgb_to_hex(self.color),
            font=('Arial', font_size),
            tags="text_cursor"
        )
    
    def on_key_press(self, event):
        if self.text_mode:
            if event.keysym == 'BackSpace':
                if self.text_buffer:
                    self.text_buffer = self.text_buffer[:-1]
                    self.update_text_preview()
            elif event.keysym == 'Return':
                self.commit_text()
            elif event.char and event.char.isprintable():
                self.text_buffer += event.char
                self.update_text_preview()
    
    def update_text_preview(self):
        self.canvas.delete("text_cursor")
        if self.text_position:
            x, y = self.text_position
            display_text = self.text_buffer + "|" if self.text_buffer else "|"
            font_size = max(8, int((12 + self.weight * 2) * self.scale))
            self.text_cursor = self.canvas.create_text(
                x, y, text=display_text, anchor=tk.NW,
                fill=self.rgb_to_hex(self.color),
                font=('Arial', font_size),
                tags="text_cursor"
            )
    
    def commit_text(self):
        if not self.text_buffer or not self.text_position:
            self.text_mode = False
            self.canvas.delete("text_cursor")
            return
        
        # Convert display position to image position
        img_x, img_y = self.display_to_image(self.text_position[0], self.text_position[1])
        font_size = 12 + self.weight * 2
        
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        # Draw on full-resolution image
        self.draw.text((img_x, img_y), self.text_buffer, fill=self.color, font=font)
        
        self.canvas.delete("text_cursor")
        
        self.drawn_items.append(('text', img_x, img_y, self.text_buffer, self.color, font_size))
        
        self.text_mode = False
        self.text_buffer = ""
        self.text_position = None
        self.refresh_display()
    
    def undo(self):
        if self.text_mode and self.text_buffer:
            self.commit_text()
        
        if not self.drawn_items:
            return
        
        self.drawn_items.pop()
        
        self.img = self.full_screenshot.copy()
        self.draw = ImageDraw.Draw(self.img)
        
        for item in self.drawn_items:
            self.replay_item(item)
        
        self.refresh_display()
    
    def replay_item(self, item):
        item_type = item[0]
        
        if item_type == 'arrow':
            _, sx, sy, ex, ey, color, width = item
            self.draw.line([sx, sy, ex, ey], fill=color, width=width)
            self.draw_arrow_head(sx, sy, ex, ey, color, width)
        elif item_type == 'line':
            _, sx, sy, ex, ey, color, width = item
            self.draw.line([sx, sy, ex, ey], fill=color, width=width)
        elif item_type == 'rect':
            _, sx, sy, ex, ey, color, width = item
            self.draw.rectangle([sx, sy, ex, ey], outline=color, width=width)
        elif item_type == 'circle':
            _, sx, sy, radius, color, width = item
            self.draw.ellipse([sx - radius, sy - radius, sx + radius, sy + radius],
                             outline=color, width=width)
        elif item_type == 'text':
            _, x, y, text, color, font_size = item
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
            self.draw.text((x, y), text, fill=color, font=font)
        elif item_type == 'highlight':
            _, points, color, weight = item
            overlay = Image.new('RGBA', self.img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            line_width = max(8, weight * 3)
            rgba_color = (color[0], color[1], color[2], 100)
            for i in range(len(points) - 1):
                x1, y1 = points[i]
                x2, y2 = points[i + 1]
                overlay_draw.line([(x1, y1), (x2, y2)], fill=rgba_color, width=line_width)
            if self.img.mode != 'RGBA':
                self.img = self.img.convert('RGBA')
            self.img = Image.alpha_composite(self.img, overlay)
            self.img = self.img.convert('RGB')
            self.draw = ImageDraw.Draw(self.img)
        elif item_type == 'blur':
            _, x1, y1, x2, y2 = item
            region = self.img.crop((x1, y1, x2, y2))
            pixel_size = 10
            small_w = max(1, (x2 - x1) // pixel_size)
            small_h = max(1, (y2 - y1) // pixel_size)
            small = region.resize((small_w, small_h), Image.Resampling.NEAREST)
            pixelated = small.resize((x2 - x1, y2 - y1), Image.Resampling.NEAREST)
            self.img.paste(pixelated, (x1, y1))
            self.draw = ImageDraw.Draw(self.img)
    
    def refresh_display(self):
        """Refresh the scaled display"""
        display_width = int(self.img.width * self.scale)
        display_height = int(self.img.height * self.scale)
        self.display_img = self.img.resize((display_width, display_height), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(self.display_img)
        self.canvas.delete("screenshot")
        self.canvas.create_image(self.offset_x, self.offset_y, anchor=tk.NW,
                                image=self.photo, tags="screenshot")
        self.canvas.tag_lower("screenshot")
    
    def add_metadata(self):
        meta = PngImagePlugin.PngInfo()
        meta.add_text("viewclipper_version", "1.0")
        meta.add_text("viewclipper_mode", "fullscreen")
        meta.add_text("viewclipper_captured_at", datetime.now().isoformat())
        return meta
    
    def save(self, action='local'):
        if self.text_mode and self.text_buffer:
            self.commit_text()
        
        self.result = self.img  # Return full resolution image
        self.metadata = self.add_metadata()
        self.save_action = action
        self.root.quit()
        self.root.destroy()
    
    def copy_and_close(self):
        if self.text_mode and self.text_buffer:
            self.commit_text()
        
        copy_to_clipboard(self.img)  # Copy full resolution image
        print("📋 Copied to clipboard!")
        
        self.result = None
        self.root.quit()
        self.root.destroy()
    
    def cancel(self):
        self.result = None
        self.root.quit()
        self.root.destroy()
    
    def on_escape(self, event):
        if self.text_mode:
            self.text_mode = False
            self.text_buffer = ""
            self.canvas.delete("text_cursor")
        else:
            self.cancel()
    
    def on_enter(self, event):
        if self.text_mode and self.text_buffer:
            self.commit_text()
        elif not self.text_mode:
            if self.default_to_clipboard:
                self.copy_and_close()
            else:
                self.save('local')


class PredefinedEditor(FullscreenEditor):
    """Predefined area capture with scaled display and toolbar"""
    
    def __init__(self, top_offset, bottom_offset, left_offset, right_offset, default_to_clipboard=False):
        super().__init__(default_to_clipboard)
        self.top_offset = top_offset
        self.bottom_offset = bottom_offset
        self.left_offset = left_offset
        self.right_offset = right_offset
    
    def capture_and_edit(self):
        """Capture predefined area and show editor"""
        screen_width, screen_height = get_screen_size()
        
        # Calculate predefined region
        x1 = self.left_offset
        y1 = self.top_offset
        img_width = screen_width - self.left_offset - self.right_offset
        img_height = screen_height - self.top_offset - self.bottom_offset
        
        if img_width <= 0 or img_height <= 0:
            raise ValueError(f"Invalid predefined area: {img_width}x{img_height}")
        
        # Capture predefined region
        with mss() as sct:
            monitor = {"top": y1, "left": x1, "width": img_width, "height": img_height}
            screenshot = sct.grab(monitor)
            self.full_screenshot = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
        
        self.img = self.full_screenshot.copy()
        self.draw = ImageDraw.Draw(self.img)
        
        # Calculate scale
        toolbar_height = 60
        margin = 20
        available_height = screen_height - toolbar_height - margin * 2
        available_width = screen_width - margin * 2
        
        scale_x = available_width / img_width
        scale_y = available_height / img_height
        self.scale = min(scale_x, scale_y, 0.95)
        
        display_width = int(img_width * self.scale)
        display_height = int(img_height * self.scale)
        
        self.offset_x = (screen_width - display_width) // 2
        self.offset_y = toolbar_height + margin
        
        # Create window
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.geometry(f"{screen_width}x{screen_height}+0+0")
        self.root.configure(bg='#2b2b2b')
        self.root.attributes('-topmost', True)
        self.root.lift()
        self.root.focus_force()
        
        self.canvas = tk.Canvas(self.root, width=screen_width, height=screen_height,
                                highlightthickness=0, bg='#2b2b2b', cursor="arrow")
        self.canvas.pack()
        
        self.display_img = self.img.resize((display_width, display_height), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(self.display_img)
        self.canvas.create_image(self.offset_x, self.offset_y, anchor=tk.NW,
                                image=self.photo, tags="screenshot")
        
        self.canvas.create_rectangle(
            self.offset_x - 2, self.offset_y - 2,
            self.offset_x + display_width + 2, self.offset_y + display_height + 2,
            outline='#00aaff', width=2, tags="border"
        )
        
        self.canvas.bind('<ButtonPress-1>', self.on_mouse_down)
        self.canvas.bind('<B1-Motion>', self.on_mouse_move)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_up)
        self.root.bind('<Escape>', self.on_escape)
        self.root.bind('<Return>', self.on_enter)
        self.root.bind('<Key>', self.on_key_press)
        
        self.show_toolbar()
        
        self.root.mainloop()
        
        if self.result:
            return (self.result, self.metadata, self.save_action)
        return None
    
    def add_metadata(self):
        meta = PngImagePlugin.PngInfo()
        meta.add_text("viewclipper_version", "1.0")
        meta.add_text("viewclipper_mode", "predefined")
        meta.add_text("viewclipper_captured_at", datetime.now().isoformat())
        return meta


def capture_fullscreen():
    """Capture entire screen using physical dimensions"""
    screen_width, screen_height = get_screen_size()
    
    with mss() as sct:
        monitor = {
            "top": 0,
            "left": 0,
            "width": screen_width,
            "height": screen_height
        }
        screenshot = sct.grab(monitor)
        img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
        return img


def capture_region(region):
    """Capture specific region (x, y, width, height) in actual pixels"""
    with mss() as sct:
        monitor = {
            "top": region[1], 
            "left": region[0], 
            "width": region[2], 
            "height": region[3]
        }
        screenshot = sct.grab(monitor)
        img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
        return img


def capture_predefined(top_offset, bottom_offset, left_offset=0, right_offset=0):
    """Capture screen with predefined margins/offsets."""
    screen_width, screen_height = get_screen_size()
    
    x = left_offset
    y = top_offset
    width = screen_width - left_offset - right_offset
    height = screen_height - top_offset - bottom_offset
    
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid predefined area: {width}x{height}")
    
    return capture_region((x, y, width, height))


def copy_to_clipboard(img):
    """Copy PIL Image to Windows clipboard"""
    output = io.BytesIO()
    img.convert('RGB').save(output, 'BMP')
    data = output.getvalue()[14:]
    output.close()
    
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
    finally:
        win32clipboard.CloseClipboard()


def save_screenshot(img, metadata=None):
    """Save image with unique filename and optional metadata"""
    Config.ensure_folder()
    filepath = os.path.join(Config.SAVE_FOLDER, Config.get_filename())
    if metadata:
        img.save(filepath, pnginfo=metadata)
    else:
        img.save(filepath)
    return filepath