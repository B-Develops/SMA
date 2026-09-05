from PIL import Image, ImageDraw, ImageFont
import os

os.makedirs('app/static/icons', exist_ok=True)

BG_DARK = (10, 25, 47)
BG_RED = (229, 62, 62)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def get_font(size):
    for path in ['arialbd.ttf', 'arial.ttf']:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def draw_car_icon(size):
    img = Image.new('RGB', (size, size), BG_DARK)
    draw = ImageDraw.Draw(img)

    font_large = get_font(int(size * 0.20))
    font_small = get_font(int(size * 0.10))

    margin = int(size * 0.08)
    radius = int(size * 0.15)
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius,
        fill=BG_RED
    )

    cx, cy = size // 2, size // 2
    body_top = int(size * 0.32)
    body_bottom = int(size * 0.62)
    body_left = int(size * 0.22)
    body_right = int(size * 0.78)

    draw.rounded_rectangle(
        [body_left, body_top, body_right, body_bottom],
        radius=int(size * 0.06),
        fill=BLACK
    )

    # Windshield
    draw.polygon([
        (body_left + int(size*0.20), body_top),
        (body_right - int(size*0.10), body_top),
        (body_right - int(size*0.05), body_top + int(size*0.10)),
        (body_left + int(size*0.25), body_top + int(size*0.08))
    ], fill=WHITE)

    wheel_r = int(size * 0.07)
    fw_x = int(size * 0.75)
    fw_y = body_bottom + int(size * 0.02)
    draw.ellipse([fw_x - wheel_r, fw_y - wheel_r, fw_x + wheel_r, fw_y + wheel_r], fill=WHITE)
    rw_x = int(size * 0.35)
    rw_y = body_bottom + int(size * 0.02)
    draw.ellipse([rw_x - wheel_r, rw_y - wheel_r, rw_x + wheel_r, rw_y + wheel_r], fill=WHITE)

    # 'SM' text
    text = 'S M'
    try:
        ts = draw.textlength(text, font=font_small)
    except Exception:
        ts = size * 0.5
    draw.text((cx - ts // 2, body_bottom + int(size*0.10)), text, fill=WHITE, font=font_small)

    return img


sizes = [16, 32, 72, 96, 128, 192, 512]
for sz in sizes:
    icon = draw_car_icon(sz)
    icon.save(f'app/static/icons/icon-{sz}.png')
    print(f'Created icon-{sz}.png ({sz}x{sz})')

# Favicon ICO (16 + 32)
favicon_32 = draw_car_icon(32)
favicon_16 = draw_car_icon(16)
favicon_32.save('app/static/icons/favicon.ico', format='ICO', append_images=[favicon_16])
print('Created favicon.ico')

# Apple touch icon
draw_car_icon(180).save('app/static/icons/apple-touch-icon.png')
print('Created apple-touch-icon.png (180x180)')

# Maskable icon (extra padding)
mask_img = Image.new('RGB', (540, 540), BG_DARK)
icon_512 = draw_car_icon(512)
mask_img.paste(icon_512, (14, 14))
mask_img.save('app/static/icons/maskable-512.png')
print('Created maskable-512.png (540x540 padded)')
