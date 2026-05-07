from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
PNG_PATH = ASSETS / "mediaflow.png"
ICO_PATH = ASSETS / "mediaflow.ico"


def rounded_rectangle_mask(size, radius):
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    return mask


def draw_icon(size):
    scale = size / 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    bg = Image.new("RGBA", (size, size), (16, 24, 38, 255))
    bg_draw = ImageDraw.Draw(bg)
    for y in range(size):
        t = y / max(1, size - 1)
        r = int(32 + 8 * t)
        g = int(51 + 28 * t)
        b = int(80 + 64 * t)
        bg_draw.line((0, y, size, y), fill=(r, g, b, 255))
    img.alpha_composite(bg)

    mask = rounded_rectangle_mask((size, size), int(52 * scale))
    img.putalpha(mask)

    draw = ImageDraw.Draw(img)
    inset = int(22 * scale)
    draw.rounded_rectangle(
        (inset, inset, size - inset, size - inset),
        radius=int(42 * scale),
        outline=(72, 137, 255, 220),
        width=max(2, int(9 * scale)),
    )

    play = [
        (int(98 * scale), int(73 * scale)),
        (int(98 * scale), int(183 * scale)),
        (int(184 * scale), int(128 * scale)),
    ]
    draw.polygon(play, fill=(238, 246, 255, 255))

    draw.arc(
        (int(56 * scale), int(58 * scale), int(202 * scale), int(198 * scale)),
        start=300,
        end=58,
        fill=(33, 197, 129, 230),
        width=max(2, int(12 * scale)),
    )
    draw.arc(
        (int(54 * scale), int(56 * scale), int(204 * scale), int(200 * scale)),
        start=126,
        end=236,
        fill=(44, 125, 233, 235),
        width=max(2, int(12 * scale)),
    )

    return img


def main():
    ASSETS.mkdir(exist_ok=True)
    png = draw_icon(512)
    png.save(PNG_PATH)
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    png.save(ICO_PATH, sizes=sizes)
    print(f"Wrote {PNG_PATH}")
    print(f"Wrote {ICO_PATH}")


if __name__ == "__main__":
    main()
