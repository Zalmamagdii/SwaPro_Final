# -*- coding: utf-8 -*-
"""License Plate Generation Script"""

import cv2
import numpy as np
import random
import os
import urllib.request
import pathlib
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO
from skimage.exposure import match_histograms
import arabic_reshaper
from bidi.algorithm import get_display
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
#from remove_background import remove_background
import json
import string

app = Flask(__name__)
CORS(app)

# ─────────────────────────── 1. Settings ───────────────────────────
TEMPLATE_PATH = r"C:\Users\DELL\Documents\Automation\final\tailadmin-free-tailwind-dashboard-template-main\template.jpg"      # Empty plate template
MODEL_PATH = r"C:\Users\DELL\Documents\Automation\final\tailadmin-free-tailwind-dashboard-template-main\best (2).pt"
OUT_PATH = "scene_adapt_noise.jpg"                       # Final output
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Bold.ttf"

# Base directory for Iranian plate generator files
IRAN_PLATE_DIR = r"C:\Users\DELL\Documents\Automation\final2\SwaPro\tailadmin-free-tailwind-dashboard-template-main\iranian-license-plate-generator"

# ─────────────────────────── 2. Install required packages ───────────────────────────
# Please run these commands in your terminal:
# pip install ultralytics scikit-image opencv-python pillow arabic-reshaper python-bidi flask flask-cors

# ─────────────────────────── 3. Generate Arabic plate ─────────────────────────
FONT_PATH = "Amiri-Bold.ttf"
if not pathlib.Path(FONT_PATH).exists():
    urllib.request.urlretrieve(FONT_URL, FONT_PATH)

def convert_to_arabic(nums):
    m = {'1':'١','2':'٢','3':'٣','4':'٤','5':'٥','6':'٦','7':'٧','8':'٨','9':'٩'}
    return [m[n] for n in nums]

def draw_centered(draw, items, area, font, rtl=False, spacing=10):
    l,t,r,b   = area
    widths    = [draw.textbbox((0,0),ch,font=font)[2] for ch in items]
    total_w   = sum(widths) + spacing*(len(items)-1)
    start_x   = (r-total_w) if rtl else l + ((r-l)-total_w)//2
    items     = items[::-1] if rtl else items
    widths    = widths[::-1] if rtl else widths
    max_h     = max(draw.textbbox((0,0),ch,font=font)[3] for ch in items)
    y         = t + ((b-t)-max_h)//2
    x         = start_x
    for i,ch in enumerate(items):
        draw.text((x,y), ch, font=font, fill="black")
        x += widths[i] + spacing

def generate_iran_plates():
    # Load configuration data from the correct path
    config_path = os.path.join(IRAN_PLATE_DIR, 'config.json')
    with open(config_path, 'r') as file:
        data = json.load(file)

    numbers = data['numbers']
    mini_numbers = data['mini_numbers']
    chars = data['chars']

    # Random selections for plate number
    random_1 = random.choice(numbers)
    random_2 = random.choice(numbers)
    random_char = random.choice(chars)
    random_3 = random.choice(numbers)
    random_4 = random.choice(numbers)
    random_5 = random.choice(numbers)

    mini_random_1 = random.choice(mini_numbers)
    while mini_random_1["ch"] == '0':
        mini_random_1 = random.choice(mini_numbers)
    mini_random_2 = random.choice(mini_numbers)

    plate_text = (
        random_1['ch'] + random_2['ch'] + '-' +
        random_char['ch'] + '-' +
        random_3['ch'] + random_4['ch'] + random_5['ch'] + '-' +
        mini_random_1['ch'] + mini_random_2['ch']
    )

    # Select background and text color
    char_color = 'black'
    if random_char['ch'] in ['T', 'EIN']:
        background = Image.open(os.path.join(IRAN_PLATE_DIR, "templates/taxi.png"))
    elif random_char['ch'] in ['P', 'TH']:
        background = Image.open(os.path.join(IRAN_PLATE_DIR, "templates/police.png"))
        char_color = 'white'
    elif random_char['ch'] == 'A':
        background = Image.open(os.path.join(IRAN_PLATE_DIR, "templates/gov.png"))
        char_color = 'white'
    elif random_char['ch'] == 'Z':
        background = Image.open(os.path.join(IRAN_PLATE_DIR, "templates/blue.png"))
        char_color = 'white'
    elif random_char['ch'] == 'SH':
        background = Image.open(os.path.join(IRAN_PLATE_DIR, "templates/artesh.png"))
    else:
        background = Image.open(os.path.join(IRAN_PLATE_DIR, "templates/savari.png"))

    new_image = Image.new("RGBA", background.size)

    # Process and place each character
    overlay1 = Image.open(os.path.join(IRAN_PLATE_DIR, f"chars/{random_1['ch']}.png"))
    overlay1 = overlay1.resize(random_1['size'])
    new_image.paste(overlay1, [100, random_1['position'][1]])

    final_image = Image.alpha_composite(background.convert("RGBA"), new_image)

    overlay2 = Image.open(os.path.join(IRAN_PLATE_DIR, f"chars/{random_2['ch']}.png"))
    overlay2 = overlay2.resize(random_2['size'])
    new_image.paste(overlay2, [180, random_2['position'][1]])
    final_image = Image.alpha_composite(final_image.convert("RGBA"), new_image)

    overlaych = Image.open(os.path.join(IRAN_PLATE_DIR, f"chars/{random_char['ch']}.png"))
    overlaych = overlaych.resize(random_char['size'])
    new_image.paste(overlaych, random_char['position'])
    final_image = Image.alpha_composite(final_image.convert("RGBA"), new_image)

    overlay3 = Image.open(os.path.join(IRAN_PLATE_DIR, f"chars/{random_3['ch']}.png"))
    overlay3 = overlay3.resize(random_3['size'])
    new_image.paste(overlay3, [390, random_3['position'][1]])
    final_image = Image.alpha_composite(final_image.convert("RGBA"), new_image)

    overlay4 = Image.open(os.path.join(IRAN_PLATE_DIR, f"chars/{random_4['ch']}.png"))
    overlay4 = overlay4.resize(random_4['size'])
    new_image.paste(overlay4, [470, random_4['position'][1]])
    final_image = Image.alpha_composite(final_image.convert("RGBA"), new_image)

    overlay5 = Image.open(os.path.join(IRAN_PLATE_DIR, f"chars/{random_5['ch']}.png"))
    overlay5 = overlay5.resize(random_5['size'])
    new_image.paste(overlay5, [550, random_5['position'][1]])
    final_image = Image.alpha_composite(final_image.convert("RGBA"), new_image)

    overlay6 = Image.open(os.path.join(IRAN_PLATE_DIR, f"chars/{mini_random_1['ch']}.png"))
    overlay6 = overlay6.resize(mini_random_1['size'])
    new_image.paste(overlay6, [655, mini_random_1['position'][1]])
    final_image = Image.alpha_composite(final_image.convert("RGBA"), new_image)

    overlay7 = Image.open(os.path.join(IRAN_PLATE_DIR, f"chars/{mini_random_2['ch']}.png"))
    overlay7 = overlay7.resize(mini_random_2['size'])
    new_image.paste(overlay7, [720, mini_random_2['position'][1]])
    final_image = Image.alpha_composite(final_image.convert("RGBA"), new_image)

    # Save the image with a unique name
    SYNTH_PATH = f"{plate_text}.png"
    final_image.save(SYNTH_PATH)

    return SYNTH_PATH

def generate_egypt_plate():
    # تحميل الخط
    bold_font_path = r"C:\Users\DELL\Documents\Automation\final2\SwaPro\Amiri-Bold.ttf"
    

    template_path = r"C:\Users\DELL\Documents\Automation\final2\SwaPro\tailadmin-free-tailwind-dashboard-template-main\template.jpg"
    template = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(template)

    plate_width, plate_height = template.size
    separator_x = plate_width // 2
    digit_area = (10, 90, separator_x - 15, 280)
    letter_area = (separator_x + 10, 90, plate_width - 20, 280)

    allowed_letters = list("سصقكمنويربعدجطحتزل")
    arabic_letters_pool = allowed_letters
    digits_pool = list("123456789")

    num_letters = random.randint(1, 3)
    num_digits = random.randint(1, 3)

    arabic_letters_list = random.choices(arabic_letters_pool, k=num_letters)
    digits_list = random.choices(digits_pool, k=num_digits)

    def convert_to_arabic_numerals(digit_list):
        numeral_map = { '1': '١', '2': '٢', '3': '٣', '4': '٤',
                       '5': '٥', '6': '٦', '7': '٧', '8': '٨', '9': '٩'}
        return [numeral_map[d] for d in digit_list]

    digits_arabic = convert_to_arabic_numerals(digits_list)

    def find_max_font_size(text_list, area, spacing, font_path):
        left, top, right, bottom = area
        max_width = right - left
        max_height = bottom - top

        for font_size in range(100, 10, -1):
            font = ImageFont.truetype(font_path, font_size)
            widths = [draw.textbbox((0, 0), ch, font=font)[2] for ch in text_list]
            total_width = sum(widths) + spacing * (len(text_list) - 1 if len(text_list) > 1 else 0)
            heights = [draw.textbbox((0, 0), ch, font=font)[3] - draw.textbbox((0, 0), ch, font=font)[1] for ch in text_list]
            max_h = max(heights)

            if total_width <= max_width and max_h <= max_height:
                return font_size
        return 10

    def draw_text_list_centered(draw, items, area, font, fill, spacing, rtl=False):
        left, top, right, bottom = area
        widths = [draw.textbbox((0, 0), ch, font=font)[2] for ch in items]
        total_width = sum(widths) + spacing * (len(items) - 1 if len(items) > 1 else 0)

        x_start = (
            right - ((right - left) - total_width) // 2 - total_width if rtl
            else left + ((right - left) - total_width) // 2
        )

        max_height = 0
        bboxes = []
        for item in items:
            bbox = draw.textbbox((0, 0), item, font=font)
            bboxes.append(bbox)
            height = bbox[3] - bbox[1]
            max_height = max(max_height, height)

        y_center = top + ((bottom - top) - max_height) // 2

        items_draw = items[::-1] if rtl else items
        widths_draw = widths[::-1] if rtl else widths
        bboxes_draw = bboxes[::-1] if rtl else bboxes

        x = x_start
        for i, item in enumerate(items_draw):
            bbox = bboxes_draw[i]
            item_height = bbox[3] - bbox[1]
            item_y = y_center + (max_height - item_height) // 2 - bbox[1]
            draw.text((x, item_y), item, font=font, fill=fill)
            x += widths_draw[i] + spacing

    # إعداد الخطوط بالحجم المناسب تلقائيًا
    digits_font_size = find_max_font_size(digits_arabic, digit_area, spacing=10, font_path=bold_font_path)
    letters_font_size = find_max_font_size(arabic_letters_list, letter_area, spacing=10, font_path=bold_font_path)

    digits_font = ImageFont.truetype(bold_font_path, digits_font_size)
    letters_font = ImageFont.truetype(bold_font_path, letters_font_size)

    draw_text_list_centered(draw, digits_arabic, digit_area, digits_font, 'black', spacing=10, rtl=False)
    draw_text_list_centered(draw, arabic_letters_list, letter_area, letters_font, 'black', spacing=10, rtl=True)
    
    # Save the image with a unique name
    SYNTH_PATH = f"egypt_plate_{''.join(digits_list)}_{''.join(arabic_letters_list)}.png"
    template.save(SYNTH_PATH)
    return SYNTH_PATH

def generate_iraq_plate():
    # 1️⃣ تحميل الخلفية
    background_path = r"C:\Users\DELL\Documents\Automation\final2\SwaPro\tailadmin-free-tailwind-dashboard-template-main\iranian-license-plate-generator\Iraq template.jpg"
    background = Image.open(background_path).convert("RGB")
    draw = ImageDraw.Draw(background)

    # 2️⃣ إعداد الخط
    font_path = r"C:\Users\DELL\Documents\Automation\final2\SwaPro\license-plate-generator\fonts\FE-FONT.TTF"
    font_size = int(background.height * 0.65)
    font = ImageFont.truetype(font_path, font_size)

    # 3️⃣ توليد النص العشوائي
    letter = random.choice("ABCDEFGHJKLMNPRSTUVWXYZ")
    digits = ''.join(random.choices("0123456789", k=5))
    gov_code = random.choice([f"{i:02d}" for i in range(11, 32)])

    # 4️⃣ إعداد المسافات بين الأجزاء
    spacing_letter_and_code = 70   # بين كود المحافظة والحرف
    spacing_letter_and_digits = 40 # بين الحرف والأرقام

    # 5️⃣ تحديد نقطة البداية
    x = int(background.width * 0.11)
    y = int((background.height - font.getbbox("X")[3]) / 2)

    # 6️⃣ رسم كود المحافظة
    draw.text((x, y), gov_code, font=font, fill="black")
    x += font.getbbox(gov_code)[2] + spacing_letter_and_code

    # 7️⃣ رسم الحرف
    draw.text((x, y), letter, font=font, fill="black")
    x += font.getbbox(letter)[2] + spacing_letter_and_digits

    # 8️⃣ رسم الأرقام
    draw.text((x, y), digits, font=font, fill="black")

    # Save the image with a unique name
    SYNTH_PATH = f"iraq_plate_{gov_code}_{letter}_{digits}.png"
    background.save(SYNTH_PATH)
    return SYNTH_PATH

def generate_qatar_plate():
    # font_url = r"C:\Users\DELL\Documents\Automation\final2\SwaPro\FiraSans-Regular.otf"
    font_path = r"C:\Users\DELL\Documents\Automation\final2\SwaPro\FiraSans-Regular.otf"
    # urllib.request.urlretrieve(font_url, font_path)

    background_path = r"C:\Users\DELL\Documents\Automation\final2\SwaPro\tailadmin-free-tailwind-dashboard-template-main\iranian-license-plate-generator\Qatar template.jpg"
    background = Image.open(background_path).convert("RGB")
    draw = ImageDraw.Draw(background)

    font_size = int(background.height * 0.7)
    font = ImageFont.truetype(font_path, font_size)

    num_digits = random.choice([5, 6])
    plate_number = ''.join(random.choices("0123456789", k=num_digits))

    custom_x = 415
    custom_y = 20

    draw.text((custom_x, custom_y), plate_number, font=font, fill="black")
    
    # Save the image with a unique name
    SYNTH_PATH = f"qatar_plate_{plate_number}.png"
    background.save(SYNTH_PATH)
    return SYNTH_PATH

def generate_germany_plate():
    def find_font_size_that_fits(max_height, max_width, space_after_b, space_after_letters, margin_right=30):
        font_size = find_font_size(max_height)
        while font_size > 0:
            fnt = ImageFont.truetype(r"C:\Users\DELL\Documents\Automation\final2\SwaPro\tailadmin-free-tailwind-dashboard-template-main\FE-FONT.TTF", font_size)
            b_width = fnt.getbbox("B")[2] - fnt.getbbox("B")[0]
            letters_width = fnt.getbbox("WW")[2] - fnt.getbbox("WW")[0]
            numbers_width = fnt.getbbox("8888")[2] - fnt.getbbox("8888")[0]
            total_width = b_width + space_after_b + letters_width + space_after_letters + numbers_width

            if total_width + margin_right <= max_width:
                return font_size
            font_size -= 1
        return 10

    def find_font_size(max_height):
        for size in range(10, 1000):
            fnt = ImageFont.truetype(r"C:\Users\DELL\Documents\Automation\final2\SwaPro\tailadmin-free-tailwind-dashboard-template-main\FE-FONT.TTF", size)
            bbox = fnt.getbbox("X")
            height = bbox[3] - bbox[1]
            if height > max_height:
                return size - 1
        return -1

    def draw_text(img, offset, size, text):
        fnt = ImageFont.truetype(r"C:\Users\DELL\Documents\Automation\final2\SwaPro\tailadmin-free-tailwind-dashboard-template-main\FE-FONT.TTF", size)
        d = ImageDraw.Draw(img)
        d.text(offset, text, font=fnt, fill=(0, 0, 0))
        bbox = fnt.getbbox(text)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        return width, height

    def draw_image(img, offset, size, image_filename, angle):
        d_img = Image.open(image_filename)
        rotated_img = d_img.rotate(angle)
        rotated_img.thumbnail(size, Image.Resampling.LANCZOS)
        if rotated_img.mode == "RGBA":
            img.paste(rotated_img, offset, mask=rotated_img)
        else:
            img.paste(rotated_img, offset)
        return rotated_img.size

    # إنشاء الصورة الخلفية
    img = Image.new('RGB', (1918, 427), color=(255, 255, 255))
    ger_plate = r"C:\Users\DELL\Documents\Automation\final2\SwaPro\tailadmin-free-tailwind-dashboard-template-main\german_plate.png"
    draw_image(img, (0, 0), (1918, 427), ger_plate, 0)

    max_height = 372 - 45
    x_start = 230
    x_end_limit = 1830
    margin_right = 30

    space_after_b = 30
    space_after_decals = 20
    space_after_letters = 40

    base_decal_width = int(((302 - 45) / 2) + 30)
    decal1_width = int(base_decal_width * 1.0)
    decal2_width = int(base_decal_width * 1.2)
    decal_total_width = max(decal1_width, decal2_width) + space_after_decals

    available_text_width = x_end_limit - x_start - decal_total_width - margin_right

    font_size = find_font_size_that_fits(
        max_height, available_text_width, space_after_b, space_after_letters, margin_right=margin_right
    )

    y = 65
    numbers_x_offset = 5
    numbers_y_offset = 0
    sticker1_y_offset = -10
    sticker2_y_offset = 150

    x = x_start
    width_b, _ = draw_text(img, (x, y), font_size, "B")
    x += width_b + space_after_b + 5

    decal1_size = (decal1_width, int((372 - 45) / 2 + 10))
    decal2_size = (decal2_width, int((372 - 45) / 2 + 10 * 1.2))

    saftey = r"C:\Users\DELL\Documents\Automation\final2\SwaPro\tailadmin-free-tailwind-dashboard-template-main\2013_date_seal.png"
    draw_image(img, (x, y + sticker1_y_offset), decal1_size, saftey, 0)
    berlin = r"C:\Users\DELL\Documents\Automation\final2\SwaPro\tailadmin-free-tailwind-dashboard-template-main\berlin.png"
    draw_image(img, (x, y + sticker2_y_offset), decal2_size, berlin, 0)

    x += max(decal1_size[0], decal2_size[0]) + space_after_decals

    german_letters = "ABCDEFGHIKLMNOPRSTUVWXYZ"
    random_letters = ''.join(random.choices(german_letters, k=2))
    width_letters, _ = draw_text(img, (x, y), font_size, random_letters)
    x += width_letters + space_after_letters

    random_numbers = ''.join(random.choices(string.digits, k=4))
    draw_text(img, (x + numbers_x_offset, y + numbers_y_offset), font_size, random_numbers)

    # Save the image with a unique name
    SYNTH_PATH = f"german_plate_{random_letters}_{random_numbers}.png"
    img.save(SYNTH_PATH)
    return SYNTH_PATH

def generate_germany_plate_bayern():
    def find_font_size_that_fits(max_height, max_width, space_after_b, space_after_letters, margin_right=30):
        font_size = find_font_size(max_height)
        while font_size > 0:
            fnt = ImageFont.truetype(r"C:\Users\DELL\Documents\Automation\final2\SwaPro\tailadmin-free-tailwind-dashboard-template-main\FE-FONT.TTF", font_size)
            b_width = fnt.getbbox("B")[2] - fnt.getbbox("M")[0]
            letters_width = fnt.getbbox("WW")[2] - fnt.getbbox("WW")[0]
            numbers_width = fnt.getbbox("8888")[2] - fnt.getbbox("8888")[0]
            total_width = b_width + space_after_b + letters_width + space_after_letters + numbers_width

            if total_width + margin_right <= max_width:
                return font_size
            font_size -= 1
        return 10

    def find_font_size(max_height):
        for size in range(10, 1000):
            fnt = ImageFont.truetype(r"C:\Users\DELL\Documents\Automation\final2\SwaPro\tailadmin-free-tailwind-dashboard-template-main\FE-FONT.TTF", size)
            bbox = fnt.getbbox("X")
            height = bbox[3] - bbox[1]
            if height > max_height:
                return size - 1
        return -1

    def draw_text(img, offset, size, text):
        fnt = ImageFont.truetype(r"C:\Users\DELL\Documents\Automation\final2\SwaPro\tailadmin-free-tailwind-dashboard-template-main\FE-FONT.TTF", size)
        d = ImageDraw.Draw(img)
        d.text(offset, text, font=fnt, fill=(0, 0, 0))
        bbox = fnt.getbbox(text)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        return width, height

    def draw_image(img, offset, size, image_filename, angle):
        d_img = Image.open(image_filename)
        rotated_img = d_img.rotate(angle)
        rotated_img.thumbnail(size, Image.Resampling.LANCZOS)
        if rotated_img.mode == "RGBA":
            img.paste(rotated_img, offset, mask=rotated_img)
        else:
            img.paste(rotated_img, offset)
        return rotated_img.size

    # إنشاء الصورة الخلفية
    img = Image.new('RGB', (1918, 427), color=(255, 255, 255))
    ger_plate = r"C:\Users\DELL\Documents\Automation\final2\SwaPro\tailadmin-free-tailwind-dashboard-template-main\german_plate.png"
    draw_image(img, (0, 0), (1918, 427), ger_plate, 0)

    max_height = 372 - 45
    x_start = 230
    x_end_limit = 1830
    margin_right = 30

    space_after_b = 30
    space_after_decals = 20
    space_after_letters = 40

    base_decal_width = int(((302 - 45) / 2) + 30)
    decal1_width = int(base_decal_width * 1.0)
    decal2_width = int(base_decal_width * 1.2)
    decal_total_width = max(decal1_width, decal2_width) + space_after_decals

    available_text_width = x_end_limit - x_start - decal_total_width - margin_right

    font_size = find_font_size_that_fits(
        max_height, available_text_width, space_after_b, space_after_letters, margin_right=margin_right
    )

    y = 65
    numbers_x_offset = 5
    numbers_y_offset = 0
    sticker1_y_offset = -10
    sticker2_y_offset = 150

    x = x_start
    width_b, _ = draw_text(img, (x, y), font_size, "M")
    x += width_b + space_after_b + 5

    decal1_size = (decal1_width, int((372 - 45) / 2 + 10))
    decal2_size = (decal2_width, int((372 - 45) / 2 + 10 * 1.2))

    saftey = r"C:\Users\DELL\Documents\Automation\final2\SwaPro\tailadmin-free-tailwind-dashboard-template-main\2014_date_seal.png"
    draw_image(img, (x, y + sticker1_y_offset), decal1_size, saftey, 0)
    bayern = r"C:\Users\DELL\Documents\Automation\final2\SwaPro\tailadmin-free-tailwind-dashboard-template-main\bayern.png"
    draw_image(img, (x, y + sticker2_y_offset), decal2_size, bayern, 0)

    x += max(decal1_size[0], decal2_size[0]) + space_after_decals

    german_letters = "ABCDEFGHIKLMNOPRSTUVWXYZ"
    random_letters = ''.join(random.choices(german_letters, k=2))
    width_letters, _ = draw_text(img, (x, y), font_size, random_letters)
    x += width_letters + space_after_letters

    random_numbers = ''.join(random.choices(string.digits, k=4))
    draw_text(img, (x + numbers_x_offset, y + numbers_y_offset), font_size, random_numbers)

    # Save the image with a unique name
    SYNTH_PATH = f"german_plate_bayern_{random_letters}_{random_numbers}.png"
    img.save(SYNTH_PATH)
    return SYNTH_PATH

def process_image(scene_bgr, country='IT'):
    # ─────────────────────────── 5. خط الأنابيب التكيفى ──────────────────────
    VIGNETTE_STRENGTH = 0.25
    GAUSS_BLUR_K      = (3, 3)
    CLAHE_CLIP        = 2.0
    JPEG_QUALITY      = 95
    CENTER_MARGIN     = 0.15
    SIGMA_MIN, SIGMA_MAX = 1, 15

    pose_model = YOLO(MODEL_PATH)
    results    = pose_model(scene_bgr, verbose=False)
    src_pts    = results[0].keypoints.xy[0].cpu().numpy().astype(np.float32)

    # ترتيب النقاط: TL, TR, BR, BL
    sums, diff = src_pts.sum(1), np.diff(src_pts, axis=1).reshape(-1)
    ordered    = np.zeros_like(src_pts)
    ordered[0] = src_pts[np.argmin(sums)]       # TL
    ordered[2] = src_pts[np.argmax(sums)]       # BR
    ordered[1] = src_pts[np.argmin(diff)]       # TR
    ordered[3] = src_pts[np.argmax(diff)]       # BL
    src_pts    = ordered

    # أبعاد افتراضية من المشهد
    top_w  = np.linalg.norm(src_pts[1] - src_pts[0])
    bot_w  = np.linalg.norm(src_pts[2] - src_pts[3])
    left_h = np.linalg.norm(src_pts[3] - src_pts[0])
    right_h= np.linalg.norm(src_pts[2] - src_pts[1])
    dst_w  = int(round(max((top_w+bot_w)/2, 100)))
    dst_h  = int(round(max((left_h+right_h)/2, 30)))

    dst_pts = np.float32([[0,0],[dst_w-1,0],[dst_w-1,dst_h-1],[0,dst_h-1]])
    M       = cv2.getPerspectiveTransform(src_pts, dst_pts)
    style_bgr= cv2.warpPerspective(scene_bgr, M, (dst_w, dst_h))

    # Generate plate based on country selection
    if country == 'IR':
        SYNTH_PATH = generate_iran_plates()
    elif country == 'EG':
        SYNTH_PATH = generate_egypt_plate()
    elif country == 'IQ':
        SYNTH_PATH = generate_iraq_plate()
    elif country == 'QA':
        SYNTH_PATH = generate_qatar_plate()
    elif country == 'DE-BER':
        SYNTH_PATH = generate_germany_plate()
    elif country == 'DE-BAY':
        SYNTH_PATH = generate_germany_plate_bayern()

    synthetic_bgr = cv2.imread(SYNTH_PATH)
    synthetic_bgr = cv2.resize(synthetic_bgr, (dst_w, dst_h))

    def add_vignette(im):
        r,c  = im.shape[:2]
        kx,ky= cv2.getGaussianKernel(c, c/1.5), cv2.getGaussianKernel(r, r/1.5)
        mask = (ky @ kx.T) / np.max(ky @ kx.T)
        return (im * (1 - VIGNETTE_STRENGTH*(1-mask))[...,None]).astype(np.uint8)

    def estimate_sigma(photo):
        gray  = cv2.cvtColor(photo, cv2.COLOR_BGR2GRAY)
        resid = gray.astype(np.float32) - cv2.GaussianBlur(gray,(5,5),0)
        return np.clip(np.std(resid), SIGMA_MIN, SIGMA_MAX)

    σ = estimate_sigma(scene_bgr)
    def realism(im):
        im = add_vignette(im)
        im = np.clip(im + np.random.normal(0, σ, im.shape), 0, 255).astype(np.uint8)
        im = cv2.GaussianBlur(im, GAUSS_BLUR_K, 0)
        L,a,b = cv2.split(cv2.cvtColor(im, cv2.COLOR_BGR2LAB))
        L     = cv2.createCLAHE(clipLimit=CLAHE_CLIP).apply(L)
        im    = cv2.cvtColor(cv2.merge((L,a,b)), cv2.COLOR_LAB2BGR)
        _,enc = cv2.imencode('.jpg', im, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
        return cv2.imdecode(enc, 1)

    plate_real = realism(synthetic_bgr)

    # مطابقة هيستوجرام مركزية
    h,w = plate_real.shape[:2]; m=CENTER_MARGIN
    y1,y2 = int(h*m), int(h*(1-m)); x1,x2 = int(w*m), int(w*(1-m))
    plate_rgb = cv2.cvtColor(plate_real, cv2.COLOR_BGR2RGB)
    crop_rgb  = cv2.cvtColor(style_bgr[y1:y2, x1:x2], cv2.COLOR_BGR2RGB)
    plate_fin = cv2.cvtColor(
        match_histograms(plate_rgb, crop_rgb, channel_axis=-1).astype(np.uint8),
        cv2.COLOR_RGB2BGR)

    # وارب ثم لصق
    M_inv  = cv2.getPerspectiveTransform(dst_pts, src_pts)
    warp   = cv2.warpPerspective(plate_fin, M_inv, (scene_bgr.shape[1], scene_bgr.shape[0]))
    mask   = cv2.threshold(cv2.cvtColor(warp, cv2.COLOR_BGR2GRAY),1,255,cv2.THRESH_BINARY)[1]
    mask3  = cv2.merge([mask]*3)
    scene_nop = cv2.inpaint(scene_bgr, mask, 3, cv2.INPAINT_TELEA)
    scene_nop[mask3>0] = warp[mask3>0]

    

    # Convert the result to base64
    _, buffer = cv2.imencode('.jpg', scene_nop)
    result_base64 = base64.b64encode(buffer).decode('utf-8')
    return result_base64

@app.route('/process-image', methods=['POST'])
def handle_process_images():
    try:
        data = request.json
        images = data.get('images', [])
        country = data.get('country', '')  # Get country from request

        if not images or len(images) > 5:
            return jsonify({'success': False, 'error': 'Please send 1 to 2 images.'})

        results = []
        for img_base64 in images:
            try:
                image_data = img_base64.split(',')[1]  # Remove the data URL prefix
                image_bytes = base64.b64decode(image_data)
                nparr = np.frombuffer(image_bytes, np.uint8)
                scene_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                # Process each image with country selection
                result = process_image(scene_bgr, country)
                results.append({'success': True, 'result': result})
            except Exception as e:
                results.append({'success': False, 'error': str(e)})

        return jsonify(results)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(port=5000)