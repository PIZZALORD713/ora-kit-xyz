#!/usr/bin/env python3
"""Generate the Ora 4147 Alpha Cola wipeout GIF for empty/error states."""

from __future__ import annotations

import math
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "assets" / "ora-4147-alpha-cola-fail.gif"
ORA_4147_URL = "https://nfts.visitsugartown.com/nfts/oras/4147.png"
WIDTH = 640
HEIGHT = 420


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def load_ora_sprite() -> Image.Image:
    try:
        with urllib.request.urlopen(ORA_4147_URL, timeout=25) as response:
            image = Image.open(BytesIO(response.read())).convert("RGBA")
    except Exception:
        image = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((130, 95, 382, 360), fill=(242, 193, 78, 255), outline=(8, 9, 12, 255), width=10)
        draw.ellipse((200, 190, 225, 215), fill=(8, 9, 12, 255))
        draw.ellipse((290, 190, 315, 215), fill=(8, 9, 12, 255))
        draw.arc((220, 225, 300, 290), 20, 160, fill=(8, 9, 12, 255), width=8)

    image.thumbnail((300, 300), Image.Resampling.LANCZOS)
    background = Image.new("RGBA", image.size, image.getpixel((0, 0)))
    diff = ImageChops.difference(image, background).convert("L")
    mask = diff.point(lambda value: 0 if value < 30 else 255).filter(ImageFilter.GaussianBlur(1.2))
    image.putalpha(mask)
    bbox = image.getbbox()
    if bbox:
        image = image.crop(bbox)
    image.thumbnail((230, 230), Image.Resampling.LANCZOS)
    return image


def draw_can(draw: ImageDraw.ImageDraw, x: int, y: int, angle: float = 0, spill: bool = False) -> None:
    can = Image.new("RGBA", (88, 118), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(can)
    cdraw.rounded_rectangle((18, 8, 70, 110), radius=18, fill=(20, 24, 31, 255), outline=(242, 193, 78, 255), width=4)
    cdraw.ellipse((18, 2, 70, 22), fill=(58, 67, 82, 255), outline=(242, 193, 78, 255), width=3)
    cdraw.rectangle((24, 42, 64, 75), fill=(242, 193, 78, 255))
    cdraw.text((30, 46), "A", fill=(8, 9, 12, 255), font=font(24, True))
    cdraw.text((24, 77), "COLA", fill=(244, 241, 232, 255), font=font(11, True))
    can = can.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    draw.bitmap((x - can.width // 2, y - can.height // 2), can)
    if spill:
        draw.ellipse((x - 86, y + 36, x + 34, y + 56), fill=(91, 192, 235, 80))
        for offset in [(-58, 15), (-31, 8), (4, 18), (26, 2)]:
            draw.ellipse((x + offset[0], y + offset[1], x + offset[0] + 10, y + offset[1] + 5), fill=(91, 192, 235, 155))


def draw_board(draw: ImageDraw.ImageDraw, cx: int, cy: int, angle: float, shadow: bool = False) -> None:
    board = Image.new("RGBA", (126, 40), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(board)
    bdraw.rounded_rectangle((5, 8, 121, 32), radius=16, fill=(98, 195, 112, 255), outline=(8, 9, 12, 255), width=3)
    bdraw.line((18, 18, 105, 18), fill=(91, 192, 235, 255), width=4)
    bdraw.ellipse((21, 28, 39, 39), fill=(8, 9, 12, 255))
    bdraw.ellipse((87, 28, 105, 39), fill=(8, 9, 12, 255))
    board = board.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    if shadow:
        draw.ellipse((cx - 60, cy + 18, cx + 72, cy + 38), fill=(0, 0, 0, 65))
    draw.bitmap((cx - board.width // 2, cy - board.height // 2), board)


def base_frame() -> Image.Image:
    frame = Image.new("RGBA", (WIDTH, HEIGHT), (17, 19, 24, 255))
    draw = ImageDraw.Draw(frame)
    for radius, alpha in [(360, 32), (240, 24), (130, 18)]:
        draw.ellipse((WIDTH - radius, -radius // 2, WIDTH + radius // 2, radius), fill=(91, 192, 235, alpha))
        draw.ellipse((-radius // 2, HEIGHT - radius, radius, HEIGHT + radius // 2), fill=(242, 193, 78, alpha))
    draw.rectangle((0, 310, WIDTH, HEIGHT), fill=(13, 16, 22, 255))
    draw.line((0, 311, WIDTH, 311), fill=(52, 59, 73, 255), width=3)
    draw.text((24, 20), "404 / EMPTY WALLET MOVE", fill=(242, 193, 78, 255), font=font(18, True))
    draw.text((24, 44), "Ora 4147 attempts the Alpha Cola kickflip.", fill=(174, 182, 196, 255), font=font(18))
    return frame


def paste_center(frame: Image.Image, sprite: Image.Image, cx: int, cy: int, angle: float) -> None:
    rotated = sprite.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    shadow_y = min(328, cy + 96)
    shadow_w = max(52, int(160 - abs(cy - 230) * 0.45))
    ImageDraw.Draw(frame).ellipse((cx - shadow_w // 2, shadow_y, cx + shadow_w // 2, shadow_y + 18), fill=(0, 0, 0, 72))
    frame.alpha_composite(rotated, (cx - rotated.width // 2, cy - rotated.height // 2))


def make_frames() -> list[Image.Image]:
    sprite = load_ora_sprite()
    frames: list[Image.Image] = []
    positions = [
        (118, 230, -4, 0, 0, False, ""),
        (158, 222, 0, 0, 0, False, ""),
        (205, 205, 7, 0, 0, False, ""),
        (253, 180, 18, 0, 0, False, ""),
        (302, 148, 34, 30, 0, False, "commit"),
        (340, 134, 52, 95, 0, False, ""),
        (367, 160, 82, 178, 0, False, ""),
        (388, 212, 112, 254, 0, False, ""),
        (414, 260, 132, 316, -25, True, "uh oh"),
        (453, 290, 105, 370, -66, True, ""),
        (489, 306, 70, 410, -86, True, "not the landing"),
        (518, 312, 34, 450, -95, True, ""),
        (530, 314, 16, 468, -96, True, ""),
        (530, 314, 16, 468, -96, True, "address not found"),
        (530, 314, 16, 468, -96, True, ""),
    ]
    can_x, can_y = 437, 270
    for cx, cy, angle, board_angle, can_angle, spill, caption in positions:
        frame = base_frame()
        draw = ImageDraw.Draw(frame)
        draw_can(draw, can_x, can_y, can_angle, spill)
        if board_angle:
            draw_board(draw, cx + 20, cy + 88, board_angle, shadow=True)
        paste_center(frame, sprite, cx, cy, angle)
        if caption:
            width = draw.textlength(caption.upper(), font=font(20, True))
            draw.rounded_rectangle((WIDTH - width - 52, 80, WIDTH - 24, 119), radius=14, fill=(28, 32, 40, 235), outline=(242, 193, 78, 255), width=2)
            draw.text((WIDTH - width - 38, 90), caption.upper(), fill=(244, 241, 232, 255), font=font(20, True))
        frames.append(frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=128))
    return frames


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    frames = make_frames()
    frames[0].save(
        OUT,
        save_all=True,
        append_images=frames[1:],
        duration=[90] * (len(frames) - 2) + [420, 900],
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(OUT)


if __name__ == "__main__":
    main()
