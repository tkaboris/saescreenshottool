from mss import mss
from PIL import Image
import os
from config import Config
import ctypes
import time
import io
import win32clipboard


def set_dpi_awareness():
    """Set process DPI awareness to get correct screen dimensions"""
    try:
        # Try Windows 10+ method first
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except:
        try:
            # Fallback to Windows 8.1 method
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
        except:
            try:
                # Fallback to older method
                ctypes.windll.user32.SetProcessDPIAware()
            except:
                pass


# Set DPI awareness at module load time
set_dpi_awareness()


def get_dpi_scale():
    """Get Windows DPI scaling factor"""
    try:
        dc = ctypes.windll.user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(dc, 88)  # LOGPIXELSX
        ctypes.windll.user32.ReleaseDC(0, dc)
        return dpi / 96.0  # 96 is standard DPI
    except:
        return 1.0


def get_screen_size():
    """Get actual physical screen size in pixels"""
    try:
        width = ctypes.windll.user32.GetSystemMetrics(0)  # SM_CXSCREEN
        height = ctypes.windll.user32.GetSystemMetrics(1)  # SM_CYSCREEN
        return width, height
    except:
        return 1920, 1080


class RegionSelector:
    def __init__(self):
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.selected_region = None
        self.dpi_scale = get_dpi_scale()
        
    def select_region(self):
        """Show fullscreen overlay to select region"""
        import tkinter as tk
        
        # Get actual physical screen dimensions
        screen_width, screen_height = get_screen_size()
        
        root = tk.Tk()
        root.overrideredirect(True)  # Remove window decorations
        
        # Position at 0,0 and set to physical screen size
        root.geometry(f"{screen_width}x{screen_height}+0+0")
        root.attributes('-alpha', 0.3)
        root.configure(background='grey')
        root.attributes('-topmost', True)
        root.lift()
        root.focus_force()
        
        canvas = tk.Canvas(root, cursor="cross", bg='grey', highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Instructions label
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
            
            # Ensure minimum size
            if (x2 - x1) < 10 or (y2 - y1) < 10:
                self.selected_region = None
            else:
                # Since we're using physical screen size for the window,
                # canvas coordinates already match physical pixels
                self.selected_region = (
                    int(x1),
                    int(y1),
                    int(x2 - x1),
                    int(y2 - y1)
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
        
        # Small delay to ensure window is fully closed before capture
        time.sleep(0.1)
        
        return self.selected_region


def capture_fullscreen():
    """Capture entire screen using physical dimensions"""
    screen_width, screen_height = get_screen_size()
    
    with mss() as sct:
        # Use explicit monitor definition with physical dimensions
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
    # Create fresh mss instance to avoid threading issues
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
    """
    Capture screen with predefined margins/offsets.
    
    Args:
        top_offset: Pixels to exclude from top
        bottom_offset: Pixels to exclude from bottom (taskbar area)
        left_offset: Pixels to exclude from left
        right_offset: Pixels to exclude from right
    
    Returns:
        PIL Image of the captured region
    """
    screen_width, screen_height = get_screen_size()
    
    x = left_offset
    y = top_offset
    width = screen_width - left_offset - right_offset
    height = screen_height - top_offset - bottom_offset
    
    # Validate dimensions
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid predefined area: {width}x{height}")
    
    return capture_region((x, y, width, height))


def copy_to_clipboard(img):
    """Copy PIL Image to Windows clipboard"""
    # Convert to BMP format for clipboard
    output = io.BytesIO()
    img.convert('RGB').save(output, 'BMP')
    data = output.getvalue()[14:]  # Remove BMP header
    output.close()
    
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
    finally:
        win32clipboard.CloseClipboard()


def save_screenshot(img):
    """Save image with unique filename"""
    Config.ensure_folder()
    filepath = os.path.join(Config.SAVE_FOLDER, Config.get_filename())
    img.save(filepath)
    return filepath