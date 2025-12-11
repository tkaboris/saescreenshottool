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
        self.preview_items = []  # Canvas items being previewed
        self.preview_data = None  # Data needed to commit the element
        self.dragging = False
        self.drag_start_x = None
        self.drag_start_y = None
        
        # Text-specific state
        self.text_mode = False
        self.text_position = None
        self.text_buffer = ""
        
        # Setup window
        self.root = tk.Tk()
        self.root.title("Edit Screenshot")
        self.root.configure(bg='#2b2b2b')
        
        # Will set size after we know image dimensions
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
        ]
        
        for text, tool_name in tools:
            btn = tk.Button(
                toolbar, text=text,
                command=lambda t=tool_name: self.select_tool(t),
                bg='#4a4a4a', fg='white', padx=10, pady=5,
                relief=tk.RAISED, font=('Arial', 9)
            )
            btn.pack(side=tk.LEFT, padx=2)
        
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
        
        # Now size and position window based on actual canvas size
        toolbar_height = 50  # Approximate toolbar height
        window_width = self.display_img.width + 20  # +20 for padding
        window_height = self.display_img.height + toolbar_height + 30
        
        # Minimum window size
        window_width = max(window_width, 400)
        window_height = max(window_height, 300)
        
        # Center window
        x_pos = (screen_width - window_width) // 2
        y_pos = (screen_height - window_height) // 2
        
        self.root.geometry(f'{window_width}x{window_height}+{x_pos}+{y_pos}')
        self.root.attributes('-topmost', True)
        self.root.focus_force()
        
    def select_tool(self, tool_name):
        # Commit any pending preview
        if self.preview_mode:
            self.commit_preview()
        if self.text_mode and self.text_buffer:
            self.create_element_preview()
        
        self.tool = tool_name
        self.text_mode = False
        self.text_buffer = ""
        self.cleanup_temp_items()
            
        tool_hints = {
            'text': 'Text - Click, type, drag to position',
            'arrow': 'Arrow - Drag to draw, then drag to reposition',
            'hline': 'H-Line - Drag to draw, then drag to reposition',
            'vline': 'V-Line - Drag to draw, then drag to reposition',
            'rect': 'Rectangle - Drag to draw, then drag to reposition',
            'circle': 'Circle - Drag to draw, then drag to reposition',
            'ellipse': 'Ellipse - Drag to draw, then drag to reposition'
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
        """Base font size based on weight"""
        return 20 + self.weight * 2
    
    def get_dpi_scale(self):
        """Get Windows DPI scaling factor"""
        try:
            dpi_scale = self.root.winfo_fpixels('1i') / 72.0
            return dpi_scale
        except:
            return 1.0
    
    def get_canvas_font_size(self):
        """Font size for canvas display - accounts for both image scale AND DPI scale"""
        dpi_scale = self.get_dpi_scale()
        size = max(10, int(self.get_base_font_size() * self.scale / dpi_scale))
        return size
    
    def get_pil_font_size(self):
        """Font size for PIL drawing - actual pixel size in the full image"""
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
        """Clean up temporary canvas items"""
        for item in self.temp_items:
            self.canvas.delete(item)
        self.temp_items.clear()
    
    def cleanup_preview_items(self):
        """Clean up preview canvas items"""
        for item in self.preview_items:
            self.canvas.delete(item)
        self.preview_items.clear()
            
    def on_mouse_down(self, event):
        # If in preview mode, check if clicking inside or outside
        if self.preview_mode and self.preview_items:
            if self.is_click_on_preview(event.x, event.y):
                # Start dragging
                self.dragging = True
                self.drag_start_x = event.x
                self.drag_start_y = event.y
                self.status_label.config(text='🖱️ Dragging...')
                return
            else:
                # Click outside - commit
                self.commit_preview()
                # Don't return - allow starting new element
        
        if not self.tool:
            return
        
        # If typing text, create preview first
        if self.text_mode and self.text_buffer:
            self.create_element_preview()
            return
            
        self.start_x = int(event.x / self.scale)
        self.start_y = int(event.y / self.scale)
        
        if self.tool == 'text':
            self.start_text_mode(self.start_x, self.start_y)
    
    def is_click_on_preview(self, x, y):
        """Check if click is on any preview item"""
        for item in self.preview_items:
            bbox = self.canvas.bbox(item)
            if bbox and bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]:
                return True
        return False
            
    def on_mouse_move(self, event):
        # Handle dragging preview items
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
            
        # Clear previous temp preview
        self.cleanup_temp_items()
        
        # Draw preview
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
        # Stop dragging
        if self.dragging:
            self.dragging = False
            self.status_label.config(text='📦 Drag to move, click outside to place')
            return
        
        if not self.tool or self.start_x is None or self.tool == 'text':
            return
        
        end_x = int(event.x / self.scale)
        end_y = int(event.y / self.scale)
        
        # Store the data for this shape
        self.preview_data = {
            'type': self.tool,
            'start_x': self.start_x,
            'start_y': self.start_y,
            'end_x': end_x,
            'end_y': end_y,
            'color': self.color,
            'weight': self.weight
        }
        
        # Convert temp items to preview items
        self.preview_items = self.temp_items.copy()
        self.temp_items = []
        
        # Add bounding box
        self.add_preview_border()
        
        self.preview_mode = True
        self.start_x = None
        self.start_y = None
        self.status_label.config(text='📦 Drag to move, click outside to place')
    
    def add_preview_border(self):
        """Add dashed border around preview items"""
        if not self.preview_items:
            return
        
        # Get combined bounding box
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
        """Start text input mode"""
        self.text_mode = True
        self.text_position = (x, y)
        self.text_buffer = ""
        self.status_label.config(text='Type text, Enter when done')
        self.show_text_preview()
        
    def show_text_preview(self):
        """Show text as user types"""
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
        """Handle keyboard input"""
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
        """Create draggable preview for text element"""
        if not self.text_buffer or not self.text_position:
            return
        
        self.cleanup_temp_items()
        
        x, y = self.text_position
        
        # Create text on canvas
        text_item = self.canvas.create_text(
            x * self.scale, y * self.scale,
            text=self.text_buffer,
            anchor=tk.NW,
            fill=self.rgb_to_hex(self.color),
            font=('Arial', self.get_canvas_font_size())
        )
        self.preview_items.append(text_item)
        
        # Store preview data
        self.preview_data = {
            'type': 'text',
            'text': self.text_buffer,
            'color': self.color,
            'font_size': self.get_pil_font_size()
        }
        
        # Add border
        self.add_preview_border()
        
        self.preview_mode = True
        self.text_mode = False
        self.status_label.config(text='📦 Drag to move, click outside to place')

    def commit_preview(self):
        """Commit the previewed element to the image"""
        if not self.preview_mode or not self.preview_data:
            return
        
        data = self.preview_data
        
        # Get position from first preview item (not the border)
        main_item = self.preview_items[0] if self.preview_items else None
        if not main_item:
            self.cancel_preview()
            return
        
        # Get current position from canvas item
        if data['type'] == 'text':
            coords = self.canvas.coords(main_item)
            if coords:
                x = int(coords[0] / self.scale)
                y = int(coords[1] / self.scale)
            else:
                x, y = 0, 0
            
            # Draw text with PIL font
            try:
                font_obj = ImageFont.truetype("arial.ttf", data['font_size'])
            except:
                font_obj = ImageFont.load_default()
            
            self.draw.text((x, y), data['text'], fill=data['color'], font=font_obj)
            
        else:
            # For shapes, get bbox and calculate offset
            bbox = self.canvas.bbox(main_item)
            if not bbox:
                self.cancel_preview()
                return
            
            # Calculate how much the shape moved from original position
            orig_sx = data['start_x'] * self.scale
            orig_sy = data['start_y'] * self.scale
            
            # Find current center or start of the shape
            item_coords = self.canvas.coords(main_item)
            if item_coords:
                if data['type'] in ['arrow', 'hline', 'vline']:
                    # Line: first two coords are start
                    curr_sx, curr_sy = item_coords[0], item_coords[1]
                    curr_ex, curr_ey = item_coords[2], item_coords[3]
                else:
                    # Oval/rect: first two are top-left
                    curr_sx, curr_sy = item_coords[0], item_coords[1]
                    curr_ex, curr_ey = item_coords[2], item_coords[3]
                
                # Convert to image coordinates
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
        self.refresh_canvas()
        self.status_label.config(text='✓ Element placed')

    def cancel_preview(self):
        """Cancel without committing"""
        self.cleanup_preview_items()
        self.cleanup_temp_items()
        self.preview_mode = False
        self.preview_data = None
        self.text_mode = False
        self.text_buffer = ""
        self.text_position = None
        self.dragging = False
        self.status_label.config(text='Cancelled')
        
    def draw_arrow(self, x1, y1, x2, y2, color, weight):
        """Draw arrow with arrowhead"""
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
        """Handle Enter key"""
        if self.text_mode and not self.preview_mode:
            if self.text_buffer:
                self.create_element_preview()
        elif self.preview_mode:
            self.commit_preview()
        else:
            self.save()
            
    def handle_escape(self):
        """Handle Escape key"""
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