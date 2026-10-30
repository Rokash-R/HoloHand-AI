import os
import math
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

def generate_artistic_studio_background(output_path="assets/studio_background.png", width=1920, height=1080):
    print(f"Creating rich artistic studio backdrop ({width}x{height}) with top and bottom designs...")
    random.seed(42)
    np.random.seed(42)

    # 1. Base Studio Atmosphere (Deep, atmospheric studio wall with subtle ambient gradient)
    img = Image.new("RGBA", (width, height), (14, 16, 22, 255))
    draw = ImageDraw.Draw(img)

    # Ambient vertical gradient: midnight navy at top and bottom, warm studio glow
    base_arr = np.zeros((height, width, 4), dtype=np.float32)
    for y in range(height):
        progress = y / height
        if progress < 0.35:
            t = progress / 0.35
            r = 18 + 14 * t
            g = 20 + 10 * t
            b = 34 + 8 * (1 - t)
        elif progress < 0.65:
            t = (progress - 0.35) / 0.30
            r = 32 * (1 - t) + 24 * t
            g = 30 * (1 - t) + 22 * t
            b = 40 * (1 - t) + 32 * t
        else:
            t = (progress - 0.65) / 0.35
            r = 24 * (1 - t) + 20 * t
            g = 22 * (1 - t) + 20 * t
            b = 32 * (1 - t) + 36 * t
        base_arr[y, :, 0] = r
        base_arr[y, :, 1] = g
        base_arr[y, :, 2] = b
        base_arr[y, :, 3] = 255

    img = Image.fromarray(np.uint8(base_arr), mode="RGBA")

    # 2. Architectural Studio Elements: Acoustic Wood Diffuser Slats
    # Slats on UPPER and LOWER walls
    slat_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    slat_draw = ImageDraw.Draw(slat_layer)

    # Diffuser panel zones: Top flanks, Bottom flanks, and Bottom Center
    diffuser_zones = [
        # Upper left & right diffusers
        (40, 360, 30, 470),
        (width - 360, width - 40, 30, 470),
        # Lower left & right diffusers (Mirroring top in the lower studio)
        (40, 360, 640, 1050),
        (width - 360, width - 40, 640, 1050),
        # Lower center accent diffuser (flanking under the console)
        (440, width - 440, 870, 1060)
    ]

    for p_x1, p_x2, p_y1, p_y2 in diffuser_zones:
        # Slat panel frame with beveled border
        slat_draw.rectangle([p_x1 - 6, p_y1 - 6, p_x2 + 6, p_y2 + 6], fill=(22, 16, 12, 225), outline=(55, 42, 30, 255), width=3)
        slat_width = 10
        gap = 6
        curr_x = p_x1
        while curr_x < p_x2:
            # Warm walnut/mahogany tones with realistic grain variation
            wood_r = random.randint(75, 115)
            wood_g = int(wood_r * random.uniform(0.55, 0.65))
            wood_b = int(wood_r * random.uniform(0.35, 0.45))
            # Slat body
            slat_draw.rectangle([curr_x, p_y1, curr_x + slat_width, p_y2], fill=(wood_r, wood_g, wood_b, 235))
            # Slat edge highlight (bevel)
            slat_draw.line([(curr_x, p_y1), (curr_x, p_y2)], fill=(min(255, wood_r + 40), min(255, wood_g + 25), min(255, wood_b + 20), 200), width=1)
            # Slat shadow
            slat_draw.line([(curr_x + slat_width, p_y1), (curr_x + slat_width, p_y2)], fill=(20, 14, 10, 240), width=2)
            curr_x += slat_width + gap

    # 3. Vibrant Hand-Painted Modern Musical Wall Murals (Upper Mural AND Lower Mural)
    palette = [
        (215, 38, 61),    # Vivid Crimson
        (242, 100, 25),   # Sunset Orange
        (247, 178, 103),  # Warm Gold
        (36, 123, 160),   # Deep Teal
        (112, 193, 179),  # Turquoise
        (85, 37, 130),    # Imperial Purple
        (180, 50, 140),   # Magenta Violet
        (25, 80, 180),    # Royal Blue
        (20, 150, 110),   # Emerald
        (255, 215, 0)     # Luminous Gold
    ]

    mural_zones = [
        # Upper Center Mural
        (390, 28, width - 390, 462),
        # Lower Center Mural (Mirroring top design below the piano)
        (390, 680, width - 390, 850)
    ]

    for mural_x1, mural_y1, mural_x2, mural_y2 in mural_zones:
        mural_w = mural_x2 - mural_x1
        mural_h = mural_y2 - mural_y1

        painting = Image.new("RGBA", (mural_w, mural_h), (25, 20, 32, 255))
        pdraw = ImageDraw.Draw(painting)

        # Flowing painterly strokes and organic color waves
        num_brush_strokes = 140
        for _ in range(num_brush_strokes):
            color = random.choice(palette)
            alpha = random.randint(110, 210)
            col_rgba = (color[0], color[1], color[2], alpha)

            cx = random.uniform(0, mural_w)
            cy = random.uniform(0, mural_h)
            length = random.uniform(80, 320)
            angle = random.uniform(-0.6, 0.6)
            thickness = random.randint(12, 50)

            points = []
            steps = random.randint(6, 12)
            for s in range(steps):
                frac = s / (steps - 1)
                px = cx + length * (frac - 0.5) * math.cos(angle) + random.uniform(-15, 15)
                py = cy + length * (frac - 0.5) * math.sin(angle) + math.sin(frac * math.pi * 2) * random.uniform(15, 45)
                points.append((px, py))

            for i in range(len(points) - 1):
                pdraw.line([points[i], points[i+1]], fill=col_rgba, width=thickness)
                pdraw.ellipse([points[i][0] - thickness//2, points[i][1] - thickness//2,
                               points[i][0] + thickness//2, points[i][1] + thickness//2], fill=col_rgba)

        # Colorful geometric acoustic tiles within the painting
        for _ in range(25):
            color = random.choice(palette)
            qx = random.randint(15, max(20, mural_w - 70))
            qy = random.randint(15, max(20, mural_h - 70))
            qw = random.randint(25, 75)
            qh = random.randint(25, 75)
            pdraw.rectangle([qx, qy, qx + qw, qy + qh], fill=(color[0], color[1], color[2], random.randint(60, 140)),
                            outline=(min(255, color[0] + 50), min(255, color[1] + 50), min(255, color[2] + 50), 200), width=2)

        # Stylized piano keys & sound wave arcs
        for k in range(14):
            kx = 50 + k * 70
            ky = mural_h - random.randint(60, 110)
            kw = random.randint(25, 45)
            kh = random.randint(40, 90)
            key_col = (random.randint(230, 255), random.randint(215, 245), random.randint(170, 210), 180)
            pdraw.rectangle([kx, ky, kx + kw, ky + kh], fill=key_col, outline=(255, 235, 190, 230), width=2)
            if random.random() > 0.4:
                pdraw.rectangle([kx + kw - 10, ky - 14, kx + kw + 10, ky + kh * 0.6], fill=(30, 20, 35, 230))

        # Dynamic musical wave arcs
        for _ in range(12):
            arc_col = (random.randint(240, 255), random.randint(190, 230), random.randint(100, 150), 220)
            start_x = random.uniform(40, mural_w - 40)
            start_y = random.uniform(30, mural_h - 30)
            arc_points = []
            for a in range(20):
                t = a / 19.0
                ax = start_x + t * 220 * math.cos(t * 2.5)
                ay = start_y + t * 140 * math.sin(t * 2.0)
                arc_points.append((ax, ay))
            pdraw.line(arc_points, fill=arc_col, width=random.randint(2, 4))

        # Canvas weave texture
        painting = painting.filter(ImageFilter.GaussianBlur(radius=1.5))
        p_arr = np.array(painting, dtype=np.float32)
        grain = (np.random.randn(mural_h, mural_w, 1) * 8.0)
        p_arr[:, :, :3] = np.clip(p_arr[:, :, :3] + grain, 0, 255)
        painting = Image.fromarray(np.uint8(p_arr), mode="RGBA")

        # Frame layer around painting
        frame_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        fdraw = ImageDraw.Draw(frame_layer)
        fdraw.rectangle([mural_x1 - 16, mural_y1 - 10, mural_x2 + 16, mural_y2 + 16], fill=(8, 10, 14, 180))
        fdraw.rectangle([mural_x1 - 10, mural_y1 - 10, mural_x2 + 10, mural_y2 + 10], fill=(42, 28, 20, 255), outline=(70, 50, 36, 255), width=3)
        fdraw.rectangle([mural_x1 - 3, mural_y1 - 3, mural_x2 + 3, mural_y2 + 3], fill=(160, 130, 70, 255), outline=(215, 185, 110, 255), width=2)

        img.paste(frame_layer, (0, 0), frame_layer)
        img.paste(painting, (mural_x1, mural_y1), painting)

    # 4. Paste acoustic wood slats
    img.paste(slat_layer, (0, 0), slat_layer)

    # 5. Colorful Boutique Studio Acoustic Foam Tiles (Both UPPER flanks and LOWER flanks)
    felt_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    felt_draw = ImageDraw.Draw(felt_layer)

    acoustic_colors = [
        (190, 40, 70),   # Wine Velvet
        (220, 140, 30),  # Amber Felt
        (25, 120, 150),  # Ocean Blue
        (40, 140, 95),   # Moss Green
        (120, 45, 130),  # Plum Purple
        (190, 75, 45)    # Terracotta
    ]

    tile_clusters = [
        # Upper flanks
        (70, 490, 4, 3),
        (width - 330, 490, 4, 3),
        # Lower flanks (Mirroring top design below piano)
        (70, 780, 4, 4),
        (width - 330, 780, 4, 4)
    ]

    for side_offset, start_y, cols, rows in tile_clusters:
        tile_w = 56
        tile_h = 56
        for r_idx in range(rows):
            for c_idx in range(cols):
                tx = side_offset + c_idx * (tile_w + 10) + (18 if r_idx % 2 == 1 else 0)
                ty = start_y + r_idx * (tile_h + 10)
                col = acoustic_colors[(r_idx * 3 + c_idx) % len(acoustic_colors)]
                felt_draw.rectangle([tx, ty, tx + tile_w, ty + tile_h], fill=(col[0], col[1], col[2], 180),
                                    outline=(min(255, col[0] + 45), min(255, col[1] + 45), min(255, col[2] + 45), 235), width=2)
                felt_draw.rectangle([tx + 8, ty + 8, tx + tile_w - 8, ty + tile_h - 8], fill=(int(col[0]*0.85), int(col[1]*0.85), int(col[2]*0.85), 185))

    img.paste(felt_layer, (0, 0), felt_layer)

    # 6. Studio Stage Lighting: CEILING Spotlights AND FLOOR Uplights
    lights_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ldraw = ImageDraw.Draw(lights_layer)

    # Ceiling spotlights (pointing down)
    ceiling_spotlights = [
        (200, 0, (255, 210, 140), 0.35, 1),
        (width * 0.36, 0, (255, 230, 170), 0.45, 1),
        (width * 0.64, 0, (255, 230, 170), 0.45, 1),
        (width - 200, 0, (255, 210, 140), 0.35, 1)
    ]

    # Floor uplights (pointing up from below the piano to light up the lower studio background!)
    floor_uplights = [
        (200, height, (255, 190, 120), 0.40, -1),
        (width * 0.30, height, (120, 220, 255), 0.45, -1),
        (width * 0.70, height, (120, 220, 255), 0.45, -1),
        (width - 200, height, (255, 190, 120), 0.40, -1)
    ]

    for sx, sy, scolor, sintensity, direction in ceiling_spotlights + floor_uplights:
        target_y = sy + direction * 450
        cone_pts = [(sx, sy), (sx - 260, target_y), (sx + 260, target_y)]
        cone_color = (scolor[0], scolor[1], scolor[2], int(45 * sintensity))
        ldraw.polygon(cone_pts, fill=cone_color)

        fixture_y = sy if direction == 1 else sy - 14
        ldraw.rectangle([sx - 18, fixture_y, sx + 18, fixture_y + 14], fill=(35, 35, 42, 255), outline=(70, 70, 80, 255), width=2)
        lamp_y = fixture_y + 10 if direction == 1 else fixture_y - 4
        ldraw.ellipse([sx - 12, lamp_y, sx + 12, lamp_y + 10], fill=(scolor[0], scolor[1], scolor[2], 255))

    lights_layer = lights_layer.filter(ImageFilter.GaussianBlur(radius=16))
    img.paste(lights_layer, (0, 0), lights_layer)

    # 7. Subtle Ambient Vignette (Keeps center legible while retaining vivid upper & lower art)
    vignette = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    vdraw = ImageDraw.Draw(vignette)
    # Mild darkening only at the center keyboard zone so keys stand out razor-sharp
    vdraw.rectangle([0, 510, width, 680], fill=(10, 12, 16, 90))
    vignette = vignette.filter(ImageFilter.GaussianBlur(radius=25))
    img.paste(vignette, (0, 0), vignette)

    # Save final high-res backdrop
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG", quality=95)
    print(f"Artistic studio backdrop successfully saved to: {output_path}")

if __name__ == "__main__":
    generate_artistic_studio_background()
