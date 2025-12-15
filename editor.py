import tkinter as tk
from tkinter import colorchooser, font, simpledialog
from PIL import Image, ImageDraw, ImageTk, ImageFont
import os
import math

class ImageEditor:
    def __init__(self, img):
        self.original_img = img.copy()
        self.img = img.copy()
        self.draw = ImageDraw.Draw(self.img)
        self.result = None
        
        # Undo system
        self.history = [self.img.copy()]
        self.max_history = 20
        
        # Drawing state
        self.tool = None
        self.color = (255, 0, 0)
        self.weight = 5
        self.start_x = None
        self.start_y = None
        self.temp_items = []
        
        # Preview/drag state - unified for ALL elements
        self.preview_mode = False
        self.preview_items = []
        self.preview_data = None
        self.dragging = False
        self.drag_start_x = None
        self.drag_start_y = None
        
        # Text-specific state
        self.text_mode = False
        self.text_position = None
        self.text_buffer = ""
        
        # Highlighter state
        self.highlighter_points = []
        self.highlighter_opacity = 100  # 0-255
        
        # Setup window
        self.root = tk.Tk()
        self.root.title("Edit Screenshot")
        self.root.configure(bg='#2b2b2b')
        self.root.resizable(True, True)
        
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
        
    def create_toolbar(self):
        toolbar = tk.Frame(self.root, bg='#3c3c3c', padx=5, pady=5)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        tools = [
            ('✏️ Text', 'text'),
            ('➡️ Arrow', 'arrow'),
            ('— H-Line', 'hline'),
            ('| V-Line', 'vline'),
            ('⬜ Rectangle', 'rect'),
            ('⬭ Circle', 'circle'),
            ('⬯ Ellipse', 'ellipse'),
            ('🖍️ Highlight', 'highlight'),
        ]
        
        self.tool_buttons = {}
        for text, tool_name in tools:
            btn = tk.Button(
                toolbar, text=text,
                command=lambda t=tool_name: self.select_tool(t),
                bg='#4a4a4a', fg='white', padx=10, pady=5,
                relief=tk.RAISED, font=('Arial', 9)
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.tool_buttons[tool_name] = btn
        
        tk.Frame(toolbar, bg='#666', width=2).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        tk.Label(toolbar, text='Weight:', bg='#3c3c3c', fg='white', font=('Arial', 9)).pack(side=tk.LEFT, padx=5)
        
        self.weight_var = tk.IntVar(value=5)
        weights = [('Thin', 2), ('Medium', 3), ('Thick', 5), ('X-Thick', 8)]
        
        for text, weight in weights:
            btn = tk.Radiobutton(
                toolbar, text=text, variable=self.weight_var, value=weight,
                command=lambda w=weight: self.set_weight(w),
                bg='#3c3c3c', fg='white', selectcolor='#555',
                font=('Arial', 8), indicatoron=0, padx=8, pady=2
            )
            btn.pack(side=tk.LEFT, padx=1)
            
        tk.Frame(toolbar, bg='#666', width=2).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        tk.Button(
            toolbar, text='🎨 Color', command=self.pick_color,
            bg='#4a4a4a', fg='white', padx=10, pady=5, font=('Arial', 9)
        ).pack(side=tk.LEFT, padx=5)
        
        self.color_indicator = tk.Label(
            toolbar, text='   ', bg=self.rgb_to_hex(self.color),
            width=3, relief=tk.SUNKEN
        )
        self.color_indicator.pack(side=tk.LEFT, padx=2)
        
        tk.Frame(toolbar, bg='#666', width=2).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        tk.Button(
            toolbar, text='↶ Undo (Ctrl+Z)', command=self.undo,
            bg='#4a4a4a', fg='white', padx=10, pady=5, font=('Arial', 9)
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            toolbar, text='✅ Save', command=self.save,
            bg='#2d6a2d', fg='white', padx=15, pady=5, font=('Arial', 9, 'bold')
        ).pack(side=tk.RIGHT, padx=5)
        
        tk.Button(
            toolbar, text='❌ Cancel', command=self.cancel,
            bg='#6a2d2d', fg='white', padx=15, pady=5, font=('Arial', 9, 'bold')
        ).pack(side=tk.RIGHT, padx=2)
        
        self.status_label = tk.Label(
            toolbar, text='Select a tool', bg='#3c3c3c', fg='#cccccc',
            padx=10, font=('Arial', 9), width=45, anchor='w'
        )
        self.status_label.pack(side=tk.LEFT, padx=20)
        
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
        window_width = self.display_img.width + 20
        window_height = self.display_img.height + toolbar_height + 30
        
        window_width = max(window_width, 400)
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
        
        for name, btn in self.tool_buttons.items():
            if name == tool_name:
                btn.configure(bg='#6a6a9a', relief=tk.SUNKEN)
            else:
                btn.configure(bg='#4a4a4a', relief=tk.RAISED)
            
        tool_hints = {
            'text': 'Text - Click, type, drag to position',
            'arrow': 'Arrow - Drag to draw, then drag to reposition',
            'hline': 'H-Line - Drag to draw, then drag to reposition',
            'vline': 'V-Line - Drag to draw, then drag to reposition',
            'rect': 'Rectangle - Drag to draw, then drag to reposition',
            'circle': 'Circle - Drag to draw, then drag to reposition',
            'ellipse': 'Ellipse - Drag to draw, then drag to reposition',
            'highlight': 'Highlight - Freehand draw, click outside to place',
        }
        self.status_label.config(text=tool_hints.get(tool_name, 'Tool selected'))
        
    def set_weight(self, weight):
        self.weight = weight
        
    def pick_color(self):
        color = colorchooser.askcolor(initialcolor=self.rgb_to_hex(self.color))
        if color[0]:
            self.color = tuple(int(c) for c in color[0])
            self.color_indicator.config(bg=color[1])
            
    def rgb_to_hex(self, rgb):
        return f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
    
    def get_base_font_size(self):
        return 20 + self.weight * 2
    
    def get_dpi_scale(self):
        try:
            dpi_scale = self.root.winfo_fpixels('1i') / 72.0
            return dpi_scale
        except:
            return 1.0
    
    def get_canvas_font_size(self):
        dpi_scale = self.get_dpi_scale()
        size = max(10, int(self.get_base_font_size() * self.scale / dpi_scale))
        return size
    
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
            self.status_label.config(text='↶ Undone')
        else:
            self.status_label.config(text='❌ Nothing to undo')
    
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
                self.status_label.config(text='🖱️ Dragging...')
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
            self.status_label.config(text='📦 Drag to move, click outside to place')
            return
        
        if not self.tool or self.start_x is None or self.tool == 'text':
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
                self.status_label.config(text='📦 Drag to move, click outside to place')
            else:
                self.cleanup_temp_items()
                self.highlighter_points = []
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
        self.status_label.config(text='📦 Drag to move, click outside to place')
    
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
                outline='blue', width=2, dash=(4, 4)
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
        self.status_label.config(text='📦 Drag to move, click outside to place')

    def draw_highlighter(self, points, color, weight, opacity):
        """Draw semi-transparent highlighter stroke on image"""
        if len(points) < 2:
            return
        
        # Create overlay for transparency
        overlay = Image.new('RGBA', self.img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Highlighter is thicker
        line_width = max(8, weight * 3)
        
        # Draw line segments
        rgba_color = (color[0], color[1], color[2], opacity)
        
        for i in range(len(points) - 1):
            x1, y1 = int(points[i][0]), int(points[i][1])
            x2, y2 = int(points[i + 1][0]), int(points[i + 1][1])
            overlay_draw.line([(x1, y1), (x2, y2)], fill=rgba_color, width=line_width)
            # Draw circles at joints for smooth appearance
            r = line_width // 2
            overlay_draw.ellipse([x1 - r, y1 - r, x1 + r, y1 + r], fill=rgba_color)
        
        # Draw final circle
        if points:
            x, y = int(points[-1][0]), int(points[-1][1])
            r = line_width // 2
            overlay_draw.ellipse([x - r, y - r, x + r, y + r], fill=rgba_color)
        
        # Composite onto main image
        if self.img.mode != 'RGBA':
            self.img = self.img.convert('RGBA')
        
        self.img = Image.alpha_composite(self.img, overlay)
        self.img = self.img.convert('RGB')
        self.draw = ImageDraw.Draw(self.img)

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
            # Calculate offset from drag
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
            
        else:
            # For shapes, get coords from canvas item
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
        self.status_label.config(text='✓ Element placed')

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
        arrow_length = 18 + weight * 3
        arrow_width = 7 + weight * 1.2
        
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
            self.save()
            
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
        
    def save(self):
        if self.preview_mode:
            self.commit_preview()
        elif self.text_mode and self.text_buffer:
            self.create_element_preview()
            self.commit_preview()
            
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
    """Open editor and return edited image (or None if cancelled)"""
    editor = ImageEditor(img)
    return editor.run()