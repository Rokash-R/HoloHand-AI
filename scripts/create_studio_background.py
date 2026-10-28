import os
import math
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

def generate_artistic_studio_background(output_path="assets/studio_background.png", width=1920, height=1080):
    print(f"Creating rich artistic studio backdrop ({width}x{height})...")
    random.seed(42)
    np.random.seed(42)

    # 1. Base Studio Atmosphere (Deep, atmospheric studio wall with subtle ambient gradient)
    img = Image.new("RGBA", (width, height), (14, 16, 22, 255))
    draw = ImageDraw.Draw(img)

    # Deep vertical gradient: darker at bottom where keyboard sits, atmospheric glow in upper half
    base_arr = np.zeros((height, width, 4), dtype=np.float32)
    for y in range(height):
        # Vertical blend from midnight navy (top) to warm dark mahogany/slate (center) to deep dark chassis (bottom)
        progress = y / height
        if progress < 0.45:
            t = progress / 0.45
            r = 18 + 12 * t
            g = 20 + 8 * t
            b = 32 + 10 * (1 - t)
        else:
            t = (progress - 0.45) / 0.55
            r = 30 * (1 - t) + 12 * t
            g = 28 * (1 - t) + 14 * t
            b = 36 * (1 - t) + 18 * t
        base_arr[y, :, 0] = r
        base_arr[y, :, 1] = g
        base_arr[y, :, 2] = b
        base_arr[y, :, 3] = 255

    img = Image.fromarray(np.uint8(base_arr), mode="RGBA")

    # 2. Architectural Studio Elements: Acoustic Wood Diffuser Slats (Real studio acoustic panels)
    # Slats on upper left and upper right background walls
    slat_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    slat_draw = ImageDraw.Draw(slat_layer)

    # Left acoustic diffuser wall (x: 20 to 360, y: 30 to 480)
    # Right acoustic diffuser wall (x: width-360 to width-20, y: 30 to 480)
    for panel_x_start, panel_x_end in [(40, 360), (width - 360, width - 40)]:
        # Slat panel frame
        slat_draw.rectangle([panel_x_start - 6, 24, panel_x_end + 6, 466], fill=(22, 16, 12, 220), outline=(50, 38, 28, 255), width=3)
        slat_width = 10
        gap = 6
        curr_x = panel_x_start
        while curr_x < panel_x_end:
            # Warm walnut/mahogany tones with realistic grain variation
            wood_r = random.randint(75, 110)
            wood_g = int(wood_r * random.uniform(0.55, 0.65))
            wood_b = int(wood_r * random.uniform(0.35, 0.45))
            # Slat body
            slat_draw.rectangle([curr_x, 30, curr_x + slat_width, 460], fill=(wood_r, wood_g, wood_b, 230))
            # Slat edge highlight (bevel)
            slat_draw.line([(curr_x, 30), (curr_x, 460)], fill=(min(255, wood_r + 40), min(255, wood_g + 25), min(255, wood_b + 20), 200), width=1)
            # Slat shadow
            slat_draw.line([(curr_x + slat_width, 30), (curr_x + slat_width, 460)], fill=(20, 14, 10, 240), width=2)
            curr_x += slat_width + gap

    # 3. Vibrant Hand-Painted Modern Musical Wall Mural / Canvas Painting
    # Center-upper background: x: 380 to width-380 (approx 1160px wide, 430px tall)
    mural_x1, mural_y1 = 390, 28
    mural_x2, mural_y2 = width - 390, 462
    mural_w = mural_x2 - mural_x1
    mural_h = mural_y2 - mural_y1

    painting = Image.new("RGBA", (mural_w, mural_h), (25, 20, 32, 255))
    pdraw = ImageDraw.Draw(painting)

    # Base colorful atmospheric color blocking for the painting (abstract vibrant music symphony)
    # Rich palette: Cobalt Blue, Crimson, Burnt Orange, Golden Amber, Emerald, Violet, Magenta, Turquoise
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

    # Flowing painterly strokes and organic color waves (Impasto / Oil painting effect)
    num_brush_strokes = 240
    for _ in range(num_brush_strokes):
        color = random.choice(palette)
        alpha = random.randint(110, 210)
        col_rgba = (color[0], color[1], color[2], alpha)

        # Spline / flowing ribbon strokes mimicking music waves and strings
        cx = random.uniform(0, mural_w)
        cy = random.uniform(0, mural_h)
        length = random.uniform(80, 380)
        angle = random.uniform(-0.6, 0.6)  # Gentle sweeping curves
        thickness = random.randint(14, 65)

        points = []
        steps = random.randint(6, 14)
        for s in range(steps):
            frac = s / (steps - 1)
            px = cx + length * (frac - 0.5) * math.cos(angle) + random.uniform(-15, 15)
            py = cy + length * (frac - 0.5) * math.sin(angle) + math.sin(frac * math.pi * 2) * random.uniform(20, 60)
            points.append((px, py))

        # Draw stroke segments
        for i in range(len(points) - 1):
            pdraw.line([points[i], points[i+1]], fill=col_rgba, width=thickness)
            pdraw.ellipse([points[i][0] - thickness//2, points[i][1] - thickness//2,
                           points[i][0] + thickness//2, points[i][1] + thickness//2], fill=col_rgba)

    # Add palette-knife / impasto textural highlights and musical geometric motifs
    # Colorful geometric acoustic tiles within the painting
    for _ in range(35):
        color = random.choice(palette)
        qx = random.randint(20, mural_w - 90)
        qy = random.randint(20, mural_h - 90)
        qw = random.randint(30, 95)
        qh = random.randint(30, 95)
        pdraw.rectangle([qx, qy, qx + qw, qy + qh], fill=(color[0], color[1], color[2], random.randint(60, 140)),
                        outline=(min(255, color[0] + 50), min(255, color[1] + 50), min(255, color[2] + 50), 200), width=2)

    # Stylized hand-painted golden piano keys & sound wave arcs in the artwork
    for k in range(16):
        kx = 70 + k * 65
        ky = mural_h - random.randint(100, 180)
        kw = random.randint(30, 50)
        kh = random.randint(60, 140)
        # Golden & Ivory stylized key motifs
        key_col = (random.randint(230, 255), random.randint(215, 245), random.randint(170, 210), 180)
        pdraw.rectangle([kx, ky, kx + kw, ky + kh], fill=key_col, outline=(255, 235, 190, 230), width=2)
        if random.random() > 0.4:
            # Black key accent
            pdraw.rectangle([kx + kw - 12, ky - 20, kx + kw + 14, ky + kh * 0.6], fill=(30, 20, 35, 230))

    # Dynamic violin / cello / harp graceful curved arcs
    for _ in range(18):
        arc_col = (random.randint(240, 255), random.randint(190, 230), random.randint(100, 150), 220)
        start_x = random.uniform(50, mural_w - 50)
        start_y = random.uniform(50, mural_h - 50)
        arc_points = []
        for a in range(25):
            t = a / 24.0
            ax = start_x + t * 250 * math.cos(t * 2.5)
            ay = start_y + t * 180 * math.sin(t * 2.0)
            arc_points.append((ax, ay))
        pdraw.line(arc_points, fill=arc_col, width=random.randint(2, 5))

    # Apply artistic texture filter to the painting (painterly canvas texture)
    painting_blurred = painting.filter(ImageFilter.GaussianBlur(radius=1.8))
    # Blend sharp and blurred for painterly softness
    painting = Image.blend(painting, painting_blurred, 0.35)

    # Add real canvas weave grain onto the painting
    p_arr = np.array(painting, dtype=np.float32)
    grain = (np.random.randn(mural_h, mural_w, 1) * 9.0)
    # Add horizontal & vertical thread weave
    y_weave = (np.sin(np.arange(mural_h) * 0.8)[:, None, None] * 4.0)
    x_weave = (np.sin(np.arange(mural_w) * 0.8)[None, :, None] * 4.0)
    p_arr[:, :, :3] = np.clip(p_arr[:, :, :3] + grain + y_weave + x_weave, 0, 255)
    painting = Image.fromarray(np.uint8(p_arr), mode="RGBA")

    # Real gallery frame around the painting: Deep walnut wood with brushed brass inner liner
    frame_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    fdraw = ImageDraw.Draw(frame_layer)

    # Frame outer shadow (cast shadow onto wall)
    fdraw.rectangle([mural_x1 - 18, mural_y1 - 10, mural_x2 + 18, mural_y2 + 22], fill=(8, 10, 14, 180))

    # Frame outer wood (Walnut / Mahogany)
    fdraw.rectangle([mural_x1 - 12, mural_y1 - 12, mural_x2 + 12, mural_y2 + 12], fill=(42, 28, 20, 255), outline=(70, 50, 36, 255), width=3)
    # Brushed brass inner fillet
    fdraw.rectangle([mural_x1 - 4, mural_y1 - 4, mural_x2 + 4, mural_y2 + 4], fill=(160, 130, 70, 255), outline=(215, 185, 110, 255), width=2)

    # Paste painting into main image
    img.paste(frame_layer, (0, 0), frame_layer)
    img.paste(painting, (mural_x1, mural_y1), painting)

    # 4. Paste acoustic wood slats over wall
    img.paste(slat_layer, (0, 0), slat_layer)

    # 5. Colorful Boutique Studio Acoustic Foam Tiles (Hexagon & Diamond sound baffles on flanks)
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

    # Cluster of designer acoustic tiles on left side (x: 45 to 350, y: 490 to 760)
    # and right side (x: width-350 to width-45, y: 490 to 760)
    for side_offset, is_right in [(70, False), (width - 330, True)]:
        cols = 4
        rows = 4
        tile_w = 56
        tile_h = 56
        for r_idx in range(rows):
            for c_idx in range(cols):
                tx = side_offset + c_idx * (tile_w + 10) + (18 if r_idx % 2 == 1 else 0)
                ty = 490 + r_idx * (tile_h + 10)
                col = acoustic_colors[(r_idx * 3 + c_idx) % len(acoustic_colors)]
                # Diamond / Beveled square tile
                felt_draw.rectangle([tx, ty, tx + tile_w, ty + tile_h], fill=(col[0], col[1], col[2], 175),
                                    outline=(min(255, col[0] + 45), min(255, col[1] + 45), min(255, col[2] + 45), 230), width=2)
                # Soft center tactile texture
                felt_draw.rectangle([tx + 8, ty + 8, tx + tile_w - 8, ty + tile_h - 8], fill=(int(col[0]*0.85), int(col[1]*0.85), int(col[2]*0.85), 180))

    img.paste(felt_layer, (0, 0), felt_layer)

    # 6. Studio Stage Lighting & Sconce Glows (Real atmospheric lighting cones)
    lights_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ldraw = ImageDraw.Draw(lights_layer)

    # 4 warm ceiling spotlights casting cones onto the mural & diffusers
    spotlights = [
        (200, 0, (255, 210, 140), 0.35),
        (width * 0.36, 0, (255, 230, 170), 0.45),
        (width * 0.64, 0, (255, 230, 170), 0.45),
        (width - 200, 0, (255, 210, 140), 0.35)
    ]

    for sx, sy, scolor, sintensity in spotlights:
        # Spotlight cone
        cone_pts = [(sx, sy), (sx - 280, 520), (sx + 280, 520)]
        cone_color = (scolor[0], scolor[1], scolor[2], int(45 * sintensity))
        ldraw.polygon(cone_pts, fill=cone_color)
        # Fixture housing
        ldraw.rectangle([sx - 18, 0, sx + 18, 14], fill=(35, 35, 42, 255), outline=(70, 70, 80, 255), width=2)
        ldraw.ellipse([sx - 12, 10, sx + 12, 20], fill=(255, 240, 200, 255))

    # Soft ambient glow at edges (vibrant, warm studio atmosphere)
    lights_layer = lights_layer.filter(ImageFilter.GaussianBlur(radius=16))
    img.paste(lights_layer, (0, 0), lights_layer)

    # 7. Overall Studio Vignette & Subtle Warm Room Tint
    # Keep the center/bottom workspace visible with clean contrast
    vignette = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    vdraw = ImageDraw.Draw(vignette)
    # Darken bottom area where piano keybed and docks sit for maximum readability
    vdraw.rectangle([0, 540, width, height], fill=(10, 12, 16, 170))
    vdraw.rectangle([0, 720, width, height], fill=(8, 9, 12, 210))
    vignette = vignette.filter(ImageFilter.GaussianBlur(radius=30))
    img.paste(vignette, (0, 0), vignette)

    # Save final high-res backdrop
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG", quality=95)
    print(f"Artistic studio backdrop successfully saved to: {output_path}")

if __name__ == "__main__":
    generate_artistic_studio_background()
