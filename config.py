import os
from datetime import datetime
from settings import settings_manager


class Config:
    # Load from settings
    SAVE_FOLDER = settings_manager.get('save_folder')
    
    # Hotkey (managed by main.py now)
    HOTKEY = 'ctrl+shift+s'
    
    # Filename pattern
    @staticmethod
    def get_filename():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")[:-3]
        return f"screenshot_{timestamp}.png"
    
    # Ensure save folder exists
    @staticmethod
    def ensure_folder():
        os.makedirs(Config.SAVE_FOLDER, exist_ok=True)