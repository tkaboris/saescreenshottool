from PIL import Image
import sys

filepath = sys.argv[1] if len(sys.argv) > 1 else input("Enter PNG path: ")

img = Image.open(filepath)
print("\n📋 ViewClipper Metadata:")
print("-" * 40)

if hasattr(img, 'text'):
    for key, value in img.text.items():
        print(f"  {key}: {value}")
else:
    print("  No metadata found")