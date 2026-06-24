#!/usr/bin/env python3
"""Prepare and slice a GPT Image 2 sprite sheet for the OraKit 404 GIF."""

from __future__ import annotations

import argparse
import math
import os
import shlex
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageOps, ImageSequence

from generate_404_gif import OUT as ROUGH_GIF
from generate_404_gif import font, load_ora_sprite


ROOT = Path(__file__).resolve().parent
TMP_DIR = ROOT / "tmp" / "imagegen"
OUTPUT_DIR = ROOT / "output" / "imagegen"
REFERENCE_OUT = TMP_DIR / "ora-4147-alpha-cola-reference.png"
PROMPT_OUT = TMP_DIR / "ora-4147-alpha-cola-prompt.txt"
SHEET_OUT = OUTPUT_DIR / "ora-4147-alpha-cola-sheet.png"
GIF_OUT = ROOT / "assets" / "ora-4147-alpha-cola-fail.gif"
FRAME_SIZE = (640, 420)
SHEET_COLS = 5
SHEET_ROWS = 3
STAGE_BG = (15, 17, 22)


PROMPT = """\
Use case: illustration-story
Asset type: polished web error-state animation sprite sheet
Primary request: Create a single 15-frame sprite sheet showing Ora 4147 trying to kickflip over a can of Alpha Cola, failing, and landing in a funny harmless wipeout.
Input image role: The reference image shows the exact Ora 4147 character look and the current rough storyboard timing. Preserve the yellow hair, white shirt, black outline, skateboard, playful Sugartown Ora personality, and the Orakit dark/yellow UI mood.
Scene/backdrop: Minimal dark Orakit stage, subtle teal and warm yellow accents, ground line, readable silhouette, no busy background.
Subject: One consistent chibi Ora 4147 character on a skateboard plus one Alpha Cola can.
Composition: 5 columns by 3 rows, 15 equal animation frames, left-to-right and top-to-bottom sequence. Each frame should be the same camera angle and framing. Keep the character large and centered with enough padding for cropping.
Motion beats: approach, crouch, pop, board flip, clear the can, wobble, miss the landing, can tips over, cola spills, Ora slides/falls, final sheepish recovery.
Style: polished 2D cartoon keyframes, crisp black linework, clean cel shading, premium game UI asset, expressive but not overly detailed.
Palette: black, charcoal, warm yellow, cream white, small teal highlights, Alpha Cola can in dark charcoal with yellow label.
Text: no text, no labels, no speech bubbles, no captions, no numbers.
Constraints: no gore, no injury, no logos other than a simple fictional Alpha Cola can mark, no watermark, no panel labels. Make the 15 cells easy to crop into animation frames.
Negative: photorealism, 3D render, messy comic page, motion blur that hides the character, extra characters, readable UI text, brand logos, skateboard brand marks.
"""


def prepare_reference() -> None:
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    canvas = Image.new("RGB", (1800, 1080), (15, 17, 22))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 1800, 116), fill=(24, 27, 35))
    draw.text((48, 32), "Ora 4147 Alpha Cola kickflip reference", fill=(244, 241, 232), font=font(34, True))
    draw.text(
        (48, 76),
        "Preserve character identity. Use the rough frames only as timing/storyboard guidance.",
        fill=(180, 188, 202),
        font=font(21),
    )

    sprite = load_ora_sprite().convert("RGBA")
    sprite.thumbnail((430, 430), Image.Resampling.LANCZOS)
    sprite_card = Image.new("RGBA", (500, 610), (31, 35, 45, 255))
    sprite_card_draw = ImageDraw.Draw(sprite_card)
    sprite_card_draw.rounded_rectangle((0, 0, 499, 609), radius=24, outline=(242, 193, 78), width=5)
    sprite_card_draw.text((36, 34), "Ora 4147 identity", fill=(242, 193, 78), font=font(26, True))
    sprite_card_draw.text((36, 70), "keep this character", fill=(183, 191, 205), font=font(20))
    sprite_card.alpha_composite(sprite, ((500 - sprite.width) // 2, 140))
    canvas.paste(sprite_card.convert("RGB"), (48, 160))

    frames = []
    if ROUGH_GIF.exists():
        with Image.open(ROUGH_GIF) as gif:
            for frame in ImageSequence.Iterator(gif):
                frames.append(frame.convert("RGB"))
    if not frames:
        raise FileNotFoundError(f"Missing rough GIF reference: {ROUGH_GIF}")

    storyboard_x = 600
    storyboard_y = 160
    cell_w = 220
    cell_h = 145
    gap = 20
    draw.text((storyboard_x, 124), "Current rough timing", fill=(242, 193, 78), font=font(26, True))
    for index in range(SHEET_COLS * SHEET_ROWS):
        source = frames[min(index, len(frames) - 1)]
        thumb = ImageOps.fit(source, (cell_w, cell_h), method=Image.Resampling.LANCZOS)
        col = index % SHEET_COLS
        row = index // SHEET_COLS
        x = storyboard_x + col * (cell_w + gap)
        y = storyboard_y + row * (cell_h + 54)
        draw.rounded_rectangle((x - 6, y - 6, x + cell_w + 6, y + cell_h + 6), radius=16, fill=(31, 35, 45))
        canvas.paste(thumb, (x, y))
        draw.text((x, y + cell_h + 12), f"frame {index + 1:02d}", fill=(180, 188, 202), font=font(17, True))

    PROMPT_OUT.write_text(PROMPT, encoding="utf-8")
    canvas.save(REFERENCE_OUT)
    python_exe = shlex.quote(sys.executable)
    default_image_cli = Path.home() / ".codex" / "skills" / ".system" / "imagegen" / "scripts" / "image_gen.py"
    image_cli = shlex.quote(os.environ.get("IMAGE_GEN_CLI", str(default_image_cli)))
    reference_out = shlex.quote(str(REFERENCE_OUT))
    prompt_out = shlex.quote(str(PROMPT_OUT))
    sheet_out = shlex.quote(str(SHEET_OUT))
    script_path = shlex.quote(str(Path(__file__).resolve()))
    print(f"reference={REFERENCE_OUT}")
    print(f"prompt={PROMPT_OUT}")
    print("\nNext OpenAI command:")
    print(
        textwrap.dedent(
            f"""\
            OPENAI_API_KEY=$({python_exe} - <<'PY'
            import os
            from pathlib import Path
            if os.environ.get('OPENAI_API_KEY'):
                print(os.environ['OPENAI_API_KEY'])
            else:
                env_files = (Path('.env'), Path('.env.local'), Path.home() / '.hermes' / '.env')
                for env_file in env_files:
                    if not env_file.exists():
                        continue
                    for line in env_file.read_text(errors='replace').splitlines():
                        s = line.strip()
                        if not s or s.startswith('#') or '=' not in s:
                            continue
                        key, value = s.split('=', 1)
                        if key.strip() == 'OPENAI_API_KEY':
                            print(value.strip().strip('"\\''))
                            raise SystemExit
            PY
            )
            export OPENAI_API_KEY
            {python_exe} {image_cli} edit \\
              --model gpt-image-2 \\
              --image {reference_out} \\
              --prompt-file {prompt_out} \\
              --size 2400x960 \\
              --quality medium \\
              --output-format png \\
              --out {sheet_out} \\
              --force \\
              --no-augment
            {python_exe} {script_path} slice --sheet {sheet_out}
            """
        ).strip()
    )


def extract_sheet_frames(sheet_path: Path, inset: int) -> list[Image.Image]:
    if not sheet_path.exists():
        raise FileNotFoundError(f"Missing sprite sheet: {sheet_path}")

    sheet = Image.open(sheet_path).convert("RGB")
    cell_w = sheet.width // SHEET_COLS
    cell_h = sheet.height // SHEET_ROWS
    frames: list[Image.Image] = []

    for index in range(SHEET_COLS * SHEET_ROWS):
        col = index % SHEET_COLS
        row = index // SHEET_COLS
        left = col * cell_w + inset
        upper = row * cell_h + inset
        right = (col + 1) * cell_w - inset
        lower = (row + 1) * cell_h - inset
        crop = sheet.crop((left, upper, right, lower))
        frame = ImageOps.fit(crop, FRAME_SIZE, method=Image.Resampling.LANCZOS)
        frame = ImageEnhance.Sharpness(frame).enhance(1.08)
        frames.append(frame)
    return frames


def save_gif(frames: list[Image.Image], durations: list[int], gif_path: Path) -> None:
    gif_path.parent.mkdir(parents=True, exist_ok=True)
    paletted = [frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=160) for frame in frames]
    paletted[0].save(
        gif_path,
        save_all=True,
        append_images=paletted[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(gif_path)


def slice_sheet(sheet_path: Path, gif_path: Path, inset: int) -> None:
    frames = extract_sheet_frames(sheet_path, inset)

    durations = [90] * (len(frames) - 3) + [140, 360, 900]
    save_gif(frames, durations, gif_path)


def transform_frame(
    frame: Image.Image,
    dx: int = 0,
    dy: int = 0,
    scale: float = 1.0,
    angle: float = 0,
) -> Image.Image:
    width, height = FRAME_SIZE
    transformed = frame
    if scale != 1.0:
        transformed = transformed.resize(
            (round(width * scale), round(height * scale)),
            Image.Resampling.LANCZOS,
        )
    if angle:
        transformed = transformed.rotate(
            angle,
            resample=Image.Resampling.BICUBIC,
            expand=True,
            fillcolor=STAGE_BG,
        )

    canvas = Image.new("RGB", FRAME_SIZE, STAGE_BG)
    canvas.paste(
        transformed,
        ((width - transformed.width) // 2 + dx, (height - transformed.height) // 2 + dy),
    )
    return canvas


def draw_star(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, fill: tuple[int, int, int, int]) -> None:
    points = []
    for index in range(10):
        angle = -math.pi / 2 + index * math.pi / 5
        distance = radius if index % 2 == 0 else radius * 0.42
        points.append((cx + math.cos(angle) * distance, cy + math.sin(angle) * distance))
    draw.polygon(points, fill=fill)


def overlay_effect(frame: Image.Image, effect: str, variant: int = 0) -> Image.Image:
    image = frame.convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")

    if effect in {"roll", "crouch", "charge"}:
        pulse = 1 + variant * 0.12
        draw.ellipse((102, 322, 330, 354), outline=(242, 193, 78, round(80 * pulse)), width=3)
        for line in range(4):
            y = 300 + line * 10 + variant
            draw.line((42 + line * 18, y, 140 + line * 18, y - 10), fill=(242, 193, 78, 74), width=2)
        if effect == "charge":
            for tick in range(6):
                x = 190 + tick * 12
                draw.line((x, 258 + (tick % 2) * 8, x + 10, 244), fill=(91, 192, 235, 92), width=2)

    if effect in {"pop", "air", "air-wobble", "panic"}:
        for line in range(5):
            y = 190 + line * 28 + variant * 3
            draw.line((42, y + 38, 188, y), fill=(244, 241, 232, 58), width=2)
            draw.line((76, y + 46, 238, y + 5), fill=(242, 193, 78, 50), width=2)

    if effect in {"impact", "slide"}:
        center = (140 + variant * 12, 322 + variant * 2)
        for radius, alpha in [(46, 125), (72, 72), (102, 38)]:
            draw.ellipse(
                (center[0] - radius, center[1] - radius // 3, center[0] + radius, center[1] + radius // 3),
                outline=(242, 193, 78, alpha),
                width=4,
            )
        for spoke in range(10):
            angle = spoke * math.tau / 10
            x1 = center[0] + math.cos(angle) * 16
            y1 = center[1] + math.sin(angle) * 8
            x2 = center[0] + math.cos(angle) * 74
            y2 = center[1] + math.sin(angle) * 32
            draw.line((x1, y1, x2, y2), fill=(244, 241, 232, 72), width=2)

    if effect in {"floor", "floor-hold", "dizzy-a", "dizzy-b", "rub-a", "rub-b", "rub-c"}:
        for offset in range(4):
            draw.ellipse((62 + offset * 28, 337 - offset * 3, 92 + offset * 30, 348 + offset), fill=(92, 52, 22, 64))
        if effect.startswith("dizzy") or effect.startswith("rub"):
            for index, point in enumerate([(286, 170), (326, 142), (366, 168), (398, 206)]):
                radius = 8 + (index % 2) * 4
                shift = 6 if (variant + index) % 2 else -4
                draw_star(draw, point[0] + shift, point[1], radius, (242, 193, 78, 178))
            draw.arc((278, 146, 404, 230), 200, 335, fill=(244, 241, 232, 120), width=3)
            draw.arc((294, 158, 386, 218), 20, 160, fill=(91, 192, 235, 110), width=3)
        if effect.startswith("rub"):
            wobble = 5 if variant % 2 else -5
            draw.arc((305 + wobble, 206, 375 + wobble, 268), 205, 330, fill=(242, 193, 78, 150), width=4)
            draw.ellipse((414, 172, 424, 190), fill=(244, 241, 232, 190))

    if effect in {"recover", "recover-breath"}:
        draw.ellipse((402, 318, 552, 338), fill=(242, 193, 78, 42))
        if effect == "recover-breath":
            draw.arc((446, 180, 536, 246), 300, 35, fill=(244, 241, 232, 88), width=3)

    return image.convert("RGB")


def fade_to_black(frame: Image.Image, amount: float) -> Image.Image:
    return Image.blend(frame, Image.new("RGB", FRAME_SIZE, STAGE_BG), amount)


def directed_loop(sheet_path: Path, gif_path: Path, inset: int) -> None:
    source = extract_sheet_frames(sheet_path, inset)
    frames: list[Image.Image] = []
    durations: list[int] = []

    def add(
        index: int,
        duration: int,
        effect: str = "",
        variant: int = 0,
        dx: int = 0,
        dy: int = 0,
        scale: float = 1.0,
        angle: float = 0,
    ) -> None:
        frame = transform_frame(source[index], dx=dx, dy=dy, scale=scale, angle=angle)
        if effect:
            frame = overlay_effect(frame, effect, variant)
        frames.append(frame)
        durations.append(duration)

    # Deliberate roll-up and crouch hold before the jump.
    add(0, 210, "roll", 0, dx=-2)
    add(1, 120, "roll", 1, dx=2)
    add(1, 100, "roll", 2, dx=5)
    add(2, 120, "crouch", 0, dy=2, scale=0.99)
    add(2, 120, "crouch", 1, dy=1, scale=1.01)
    add(2, 300, "charge", 2, dy=4, scale=0.985)

    # Fast pop, hang time, then a rushed loss of control.
    add(3, 72, "pop", 0, dy=-4, scale=1.015)
    add(4, 64, "air", 0, dy=-10)
    add(5, 64, "air", 1, dy=-14)
    add(6, 70, "air-wobble", 0, dy=-8, angle=-0.8)
    add(7, 78, "air-wobble", 1, dy=-4, angle=1.2)
    add(8, 82, "panic", 0, dx=-2)

    # Impact gets a tiny camera shake and splash accent.
    add(9, 46, "impact", 0, dx=-7, dy=3, angle=-1.4)
    add(9, 46, "impact", 1, dx=6, dy=-2, angle=1.5)
    add(10, 70, "slide", 0, dx=-7)
    add(10, 78, "slide", 1, dx=4)
    add(11, 130, "floor", 0)
    add(11, 230, "floor-hold", 1)

    # Softer recovery: dizzy beat, head rub, breath, then reset.
    add(12, 140, "dizzy-a", 0)
    add(12, 140, "dizzy-b", 1, dx=2)
    add(13, 170, "rub-a", 0)
    add(13, 170, "rub-b", 1, dx=-1)
    add(13, 240, "rub-c", 2)
    add(14, 200, "recover", 0)
    add(14, 360, "recover-breath", 1, scale=1.005)

    last = overlay_effect(source[14], "recover-breath", 2)
    first = overlay_effect(source[0], "roll", 0)
    for amount in (0.2, 0.42, 0.66, 0.86):
        frames.append(fade_to_black(last, amount))
        durations.append(76)
    for amount in (0.86, 0.62, 0.34, 0.12):
        frames.append(fade_to_black(first, amount))
        durations.append(76)

    save_gif(frames, durations, gif_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("prepare", help="Build the reference image and prompt for GPT Image 2.")

    slice_parser = subparsers.add_parser("slice", help="Slice a 5x3 sprite sheet into the app GIF.")
    slice_parser.add_argument("--sheet", type=Path, default=SHEET_OUT)
    slice_parser.add_argument("--out", type=Path, default=GIF_OUT)
    slice_parser.add_argument("--inset", type=int, default=8)

    loop_parser = subparsers.add_parser("directed-loop", help="Retiming pass with holds, effects, recovery, and soft reset.")
    loop_parser.add_argument("--sheet", type=Path, default=SHEET_OUT)
    loop_parser.add_argument("--out", type=Path, default=GIF_OUT)
    loop_parser.add_argument("--inset", type=int, default=8)

    args = parser.parse_args()
    if args.command == "prepare":
        prepare_reference()
    elif args.command == "slice":
        slice_sheet(args.sheet, args.out, args.inset)
    elif args.command == "directed-loop":
        directed_loop(args.sheet, args.out, args.inset)


if __name__ == "__main__":
    main()
