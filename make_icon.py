import os
from PIL import Image, ImageDraw, ImageFilter

def create_app_icon():
    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Outer rounded rectangle background (Dark Slate Blue)
    padding = 24
    corner_radius = 96
    bg_color = (20, 25, 38, 255)
    border_color = (0, 168, 255, 255)
    
    # Draw background with rounded corners
    draw.rounded_rectangle(
        [padding, padding, size - padding, size - padding],
        radius=corner_radius,
        fill=bg_color,
        outline=border_color,
        width=8
    )

    # Inner glowing circle
    center = size // 2
    r_outer = 160
    draw.ellipse(
        [center - r_outer, center - r_outer, center + r_outer, center + r_outer],
        fill=(13, 71, 161, 180),
        outline=(0, 229, 255, 255),
        width=6
    )

    # Lightning / Link arrow symbol in center
    points = [
        (center + 20, center - 130),
        (center - 70, center + 10),
        (center + 10, center + 10),
        (center - 20, center + 130),
        (center + 70, center - 10),
        (center - 10, center - 10),
    ]
    draw.polygon(points, fill=(0, 229, 255, 255))
    
    # Add inner highlight
    points_inner = [
        (center + 15, center - 100),
        (center - 50, center + 5),
        (center + 5, center + 5),
        (center - 15, center + 100),
        (center + 50, center - 5),
        (center - 5, center - 5),
    ]
    draw.polygon(points_inner, fill=(255, 255, 255, 230))

    # Save PNG
    img.save("app_icon.png")

    # Generate multi-size ICO file for Windows EXE
    icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    img.save("app_icon.ico", format="ICO", sizes=icon_sizes)
    print("Created app_icon.png and app_icon.ico successfully!")

def create_ui_icons():
    # 1. Play / Extract Icon (24x24)
    img_play = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
    d = ImageDraw.Draw(img_play)
    d.polygon([(14, 8), (38, 24), (14, 40)], fill=(255, 255, 255, 255))
    img_play.save("icon_extract.png")

    # 2. Copy Clipboard Icon (24x24)
    img_copy = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
    d = ImageDraw.Draw(img_copy)
    d.rounded_rectangle([14, 14, 38, 40], radius=4, outline=(255, 255, 255, 255), width=3)
    d.rounded_rectangle([10, 8, 32, 34], radius=4, fill=(255, 255, 255, 220), outline=(255, 255, 255, 255), width=3)
    img_copy.save("icon_copy.png")

    # 3. Cancel Icon (24x24)
    img_cancel = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
    d = ImageDraw.Draw(img_cancel)
    d.line([(14, 14), (34, 34)], fill=(255, 255, 255, 255), width=5)
    d.line([(34, 14), (14, 34)], fill=(255, 255, 255, 255), width=5)
    img_cancel.save("icon_cancel.png")

    print("Created UI icon PNGs successfully!")

if __name__ == "__main__":
    create_app_icon()
    create_ui_icons()
