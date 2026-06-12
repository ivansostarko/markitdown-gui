"""Generate the application icon (assets/icon.png + assets/icon.ico).

A programmatic icon — charcoal rounded square holding a white document
page with a folded corner and an "M↓" glyph — so the repository needs
no hand-made binary assets checked in.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SIZE = 512

BG_TOP = (74, 74, 84, 255)  # #4A4A54
BG_BOTTOM = (28, 28, 33, 255)  # #1C1C21
PAGE = (255, 255, 255, 255)
PAGE_FOLD = (215, 215, 222, 255)
INK = (42, 42, 49, 255)  # dark gray "M"
ARROW = (34, 160, 90, 255)  # green download arrow (#22A05A)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_icon() -> Image.Image:
    # Draw at 2x and downscale for smooth edges.
    s = SIZE * 2
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Charcoal rounded-square background with a vertical gradient.
    pad, radius = 56, 220
    for y in range(pad, s - pad):
        t = (y - pad) / (s - 2 * pad)
        color = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(4))
        d.line([(pad, y), (s - pad, y)], fill=color)
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [pad, pad, s - pad, s - pad], radius=radius, fill=255
    )
    img.putalpha(mask)
    d = ImageDraw.Draw(img)

    # White document page with a folded top-right corner.
    px0, py0, px1, py1 = int(s * 0.27), int(s * 0.18), int(s * 0.73), int(s * 0.82)
    fold = int(s * 0.11)
    page_radius = 40
    d.rounded_rectangle([px0, py0, px1, py1], radius=page_radius, fill=PAGE)
    # Cut the top-right corner back to the background, then add the fold flap.
    d.polygon(
        [(px1 - fold, py0 - 2), (px1 + 2, py0 - 2), (px1 + 2, py0 + fold)],
        fill=(0, 0, 0, 0),
    )
    d.polygon(
        [(px1 - fold, py0), (px1 - fold, py0 + fold), (px1, py0 + fold)],
        fill=PAGE_FOLD,
    )

    # "M" on the page.
    cx = (px0 + px1) // 2
    d.text((cx, int(s * 0.43)), "M", font=_font(int(s * 0.30)), fill=INK, anchor="mm")

    # Green down arrow under the M.
    ax, ay = cx, int(s * 0.625)
    w = int(s * 0.052)
    d.line([(ax, ay - int(s * 0.045)), (ax, ay + int(s * 0.05))], fill=ARROW, width=w)
    d.polygon(
        [
            (ax - int(s * 0.085), ay + int(s * 0.035)),
            (ax + int(s * 0.085), ay + int(s * 0.035)),
            (ax, ay + int(s * 0.125)),
        ],
        fill=ARROW,
    )

    return img.resize((SIZE, SIZE), Image.LANCZOS)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    icon = draw_icon()
    icon.save(ASSETS / "icon.png")
    icon.save(
        ASSETS / "icon.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"Wrote {ASSETS / 'icon.png'} and {ASSETS / 'icon.ico'}")


if __name__ == "__main__":
    main()
