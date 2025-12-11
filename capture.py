from mss import mss
from PIL import Image
import os
import tkinter as tk
from config import Config
import ctypes

def get_dpi_scale():
    """Get Windows DPI scaling factor"""
    try:
        # Try to get DPI awareness
        awareness = ctypes.c_int()
        ctypes.windll.shcore.GetProcessDpiAwareness(0, ctypes.byref(awareness))
        
        # Get actual DPI
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        
        # Get DPI for primary monitor
        dc = user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(dc, 88)  # LOGPIXELSX
        user32.ReleaseDC(0, dc)
        
        return dpi / 96.0  # 96 is standard DPI
    except:
        return 1.0

class RegionSelector:
    def __init__(self):
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.selected_region = None
        self.dpi_scale = get_dpi_scale()
        
    def select_region(self):
        """Show fullscreen overlay to select region"""
        root = tk.Tk()
        root.attributes('-fullscreen', True)
        root.attributes('-alpha', 0.3)  # Semi-transparent
        root.configure(background='grey')
        root.attributes('-topmost', True)
        
        canvas = tk.Canvas(root, cursor="cross", bg='grey', highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        
        def on_mouse_down(event):
            self.start_x = event.x
            self.start_y = event.y
            
        def on_mouse_move(event):
            if self.start_x and self.start_y:
                if self.rect:
                    canvas.delete(self.rect)
                self.rect = canvas.create_rectangle(
                    self.start_x, self.start_y, event.x, event.y,
                    outline='red', width=2
                )
                
        def on_mouse_up(event):
            x1, y1 = min(self.start_x, event.x), min(self.start_y, event.y)
            x2, y2 = max(self.start_x, event.x), max(self.start_y, event.y)
            
            # Convert Tkinter coordinates to actual screen pixels (for DPI scaling)
            scale = self.dpi_scale
            self.selected_region = (
                int(x1 * scale),
                int(y1 * scale),
                int((x2 - x1) * scale),
                int((y2 - y1) * scale)
            )
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
        return self.selected_region

def capture_fullscreen():
    """Capture entire screen"""
    with mss() as sct:
        monitor = sct.monitors[1]  # Primary monitor
        screenshot = sct.grab(monitor)
        img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
        return img

def capture_region(region):
    """Capture specific region (x, y, width, height) in actual pixels"""
    with mss() as sct:
        monitor = {"top": region[1], "left": region[0], 
                   "width": region[2], "height": region[3]}
        screenshot = sct.grab(monitor)
        img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
        return img

def save_screenshot(img):
    """Save image with unique filename"""
    Config.ensure_folder()
    filepath = os.path.join(Config.SAVE_FOLDER, Config.get_filename())
    img.save(filepath)
    return filepath