import os
from pathlib import Path

def print_tree(directory, prefix="", ignore_dirs=None):
    """Print directory tree structure."""
    if ignore_dirs is None:
        ignore_dirs = {'__pycache__', 'venv', '.venv', 'build', 'dist', '.git', 'node_modules', '.idea'}
    
    directory = Path(directory)
    entries = sorted(directory.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    
    # Filter out ignored directories
    entries = [e for e in entries if e.name not in ignore_dirs]
    
    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        print(f"{prefix}{connector}{entry.name}")
        
        if entry.is_dir():
            extension = "    " if is_last else "│   "
            print_tree(entry, prefix + extension, ignore_dirs)

if __name__ == "__main__":
    import sys
    
    # Use current directory or provided path
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    
    print(f"\n📁 Project Structure: {Path(target).resolve().name}")
    print("=" * 50)
    print_tree(target)
    print("\n" + "=" * 50)
    print("To show contents of a file, run:")
    print("  python print_structure.py --show <filename>")