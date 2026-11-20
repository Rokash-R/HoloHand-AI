import os
import math
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

def generate_grand_real_studio_background(output_paths=None, width=1920, height=1080):
    if output_paths is None:
        output_paths = [
            "assets/home_studio_background.png",
            "src/textures/home_bg.jpg"
        ]

    print(f"Creating Grand Photorealistic Full-Screen Studio Backdrop ({width}x{height})...")
    random.seed(42)
    np.random.seed(42)

    # 1. Base Studio Atmosphere (Deep, atmospheric dark slate-navy studio wall)
    base_arr = np.zeros((height, width, 4), dtype=np.float32)
    for y in range(height):
        progress = y / height
        # Natural vertical ambient falloff (darker floor, gentle ambient ceiling glow)
        if progress < 0.40:
            t = progress / 0.40
            r = 14 + 10 * t
            g = 18 + 10 * t
            b = 30 + 12 * t
        elif progress < 0.75:
            t = (progress - 0.40) / 0.35
            r = 24 * (1 - t) + 16 * t
            g = 28 * (1 - t) + 18 * t
            b = 42 * (1 - t) + 28 * t
        else:
            t = (progress - 0.75) / 0.25
            r = 16 * (1 - t) + 10 * t
            g = 18 * (1 - t) + 12 * t
            b = 28 * (1 - t) + 18 * t
        base_arr[y, :, 0] = r
        base_arr[y, :, 1] = g
        base_arr[y, :, 2] = b
        base_arr[y, :, 3] = 255

    img = Image.fromarray(np.uint8(base_arr), mode="RGBA")

    # 2. Photorealistic Architectural Wood Diffuser Columns (Left & Right Flanks)
    slat_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    slat_draw = ImageDraw.Draw(slat_layer)

    flanks = [
        # Left acoustic tower (full screen height from 0 to height)
        (0, 240, 0, height),
        # Right acoustic tower (full screen height from 0 to height)
        (width - 240, width, 0, height),
    ]

    for p_x1, p_x2, p_y1, p_y2 in flanks:
        # Acoustic slat framework
        slat_draw.rectangle([p_x1, p_y1, p_x2, p_y2], fill=(12, 14, 20, 255))

        slat_width = 13
        gap = 7
        curr_x = p_x1 + 6
        while curr_x < p_x2 - 10:
            # Rich natural walnut wood tones
            wood_r = random.randint(80, 110)
            wood_g = int(wood_r * 0.58)
            wood_b = int(wood_r * 0.38)

            # Slat body
            slat_draw.rectangle([curr_x, p_y1, curr_x + slat_width, p_y2], fill=(wood_r, wood_g, wood_b, 245))
            # Slat 3D highlight (left edge)
            slat_draw.line([(curr_x, p_y1), (curr_x, p_y2)], fill=(min(255, wood_r + 35), min(255, wood_g + 25), min(255, wood_b + 20), 220), width=1)
            # Slat 3D shadow (right edge)
            slat_draw.line([(curr_x + slat_width, p_y1), (curr_x + slat_width, p_y2)], fill=(14, 10, 8, 255), width=2)

            curr_x += slat_width + gap

        # Vertical LED strip accent separating diffuser from center stage
        led_x = p_x2 if p_x1 == 0 else p_x1
        slat_draw.line([(led_x, 0), (led_x, height)], fill=(0, 210, 255, 180), width=2)

    img.paste(slat_layer, (0, 0), slat_layer)

    # 3. Clean Studio Stage Lighting (Realistic Overhead Beams onto Center Stage)
    lights_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ldraw = ImageDraw.Draw(lights_layer)

    # 3 Warm Studio Spotlights centered over the 3 studio stations (Cyan, Violet, Emerald)
    spotlights = [
        (width * 0.31, 0, (0, 215, 255), 0.45),      # Piano stage light
        (width * 0.50, 0, (215, 80, 255), 0.40),     # Drums stage light
        (width * 0.69, 0, (0, 240, 185), 0.45),      # Gesture FX stage light
    ]

    for sx, sy, scolor, sintensity in spotlights:
        target_y = height * 0.90
        cone_pts = [(sx, sy), (sx - 360, target_y), (sx + 360, target_y)]
        cone_color = (scolor[0], scolor[1], scolor[2], int(38 * sintensity))
        ldraw.polygon(cone_pts, fill=cone_color)

        # Fixture
        ldraw.rectangle([sx - 24, sy, sx + 24, sy + 14], fill=(28, 30, 38, 255), outline=(50, 56, 70, 255), width=2)
        ldraw.ellipse([sx - 15, sy + 8, sx + 15, sy + 16], fill=(scolor[0], scolor[1], scolor[2], 255))

    lights_layer = lights_layer.filter(ImageFilter.GaussianBlur(radius=28))
    img.paste(lights_layer, (0, 0), lights_layer)

    # 4. Subtle Architectural Geometric Grid & Floor Seams
    grid_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(grid_layer)

    # Subtle horizontal studio panels across center
    for y_pos in [280, 540, 800]:
        gdraw.line([(240, y_pos), (width - 240, y_pos)], fill=(45, 55, 75, 45), width=1)

    # Clean floor baseline
    gdraw.line([(0, height - 90), (width, height - 90)], fill=(0, 200, 255, 55), width=1)

    img.paste(grid_layer, (0, 0), grid_layer)

    # 5. Fine Natural Film Grain for Authentic High-End Tactile Feel
    arr = np.array(img, dtype=np.float32)
    grain = (np.random.randn(height, width, 1) * 2.5)
    arr[:, :, :3] = np.clip(arr[:, :, :3] + grain, 0, 255)
    img = Image.fromarray(np.uint8(arr), mode="RGBA")

    # Save to all target paths
    for path in output_paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if path.lower().endswith(".jpg") or path.lower().endswith(".jpeg"):
            rgb_img = img.convert("RGB")
            rgb_img.save(path, "JPEG", quality=98)
        else:
            img.save(path, "PNG", quality=98)
        print(f"Grand studio background saved to: {path}")

if __name__ == "__main__":
    generate_grand_real_studio_background()
