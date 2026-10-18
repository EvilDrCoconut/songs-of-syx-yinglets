"""
Converts the Yinglet source art in art/ into the formats Songs of Syx expects
and writes it into the mod's asset folder.

Usage:  python tools/import_sprites.py [SOURCE_DIR] [GAME_DIR]
Needs:  pip install pillow

Format rules (from the game's own loaders, init/race/appearence/*.java):
  * Face sheets (sprite/race/face): exactly 416 px wide, height a multiple of 60.
    Left 208 px = 4 colour frames of 52x60 (art inside the 40x48 window at +6,+6),
    right 208 px = normal map. Frame index = column + row * 4.
    Face files share one folder with every vanilla race, so ours get a "Yinglet" prefix.
  * Addons (sprite/race/face/addon): 104 px wide, one variant per 36 px row.
    Left 52x36 cell = colour, right cell = normal map, art inside the 40x24 window at +6,+6.
"""
import io
import os
import sys
import zipfile

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "art")
GAME = sys.argv[2] if len(sys.argv) > 2 else "M:/SteamLibrary/steamapps/common/Songs of Syx"
OUT = os.path.join(ROOT, "src/main/resources/mod-files/assets/sprite/race")

FLAT_NORMAL = (128, 128, 255, 255)
GRID_GREEN = (0, 255, 0, 255)
GRID_BLUE = (0, 0, 132, 255)

# source file (relative to SRC/face) -> output name in sprite/race/face
FACES = {
    "Skull.png": "YingletSkull",
    "Ears.png": "YingletEars",
    "Eyes.png": "YingletEyes",
    "Eyebrows.png": "YingletEyebrow",
    "Nose.png": "YingletNose",
    "Mouth.png": "YingletMouth",
    "Feature.png": "YingletFeature",
    "Hair.png": "YingletHair",
    "Chest.png": "YingletChest",
    "Make-Up.png": "YingletMakeup",
    "SlaveCollar.png": "YingletSlaveCollar",
    "baby.png": "YingletBaby",
}

# source file (relative to SRC/face/addon) -> (output name, first row of the 48 px face window to keep)
# The kept 24 rows must match the addon's OFFY in init/race/sprite/YINGLET.txt.
ADDONS = {
    "CrownYinglet.png": ("CrownYinglet", 0),
    "Eyepatch.png": ("YingletEyePatch", 8),
    "RaidVailYinglet.png": ("RaidVailYinglet", 23),
}


def vanilla(path):
    with zipfile.ZipFile(os.path.join(GAME, "base/data.zip")) as z:
        return Image.open(io.BytesIO(z.read("data/assets/" + path))).convert("RGBA")


def save(im, *parts):
    path = os.path.join(OUT, *parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)
    print("wrote", os.path.relpath(path, ROOT), im.size)


def body():
    """Copies the body sheet, restoring grid lines that were painted over."""
    im = Image.open(os.path.join(SRC, "Yinglet.png")).convert("RGBA")
    ref = vanilla("sprite/race/Human.png")
    if im.size != ref.size:
        raise SystemExit(f"Yinglet.png is {im.size}, must be {ref.size}")
    p, r = im.load(), ref.load()
    fixed = 0
    for y in range(im.height):
        for x in range(im.width):
            if r[x, y] == GRID_GREEN and p[x, y] == GRID_BLUE:
                p[x, y] = GRID_GREEN
                fixed += 1
    if fixed:
        print(f"restored {fixed} grid pixels in Yinglet.png")
    save(im, "Yinglet.png")


def fill_empty_frames(sheet, src):
    """The game crashes on a face frame with no art in it ("... is out of bounds 416 60"),
    so every empty frame gets a copy of the sheet's first frame as a placeholder."""
    cells = [(6 + 52 * fx, 6 + 60 * fy) for fy in range(sheet.height // 60) for fx in range(4)]
    windows = [sheet.crop((x, y, x + 40, y + 48)) for x, y in cells]
    filled = [i for i, w in enumerate(windows) if w.getchannel("A").getbbox()]
    if not filled:
        raise SystemExit(f"{src} has no art in any frame")
    empty = [i for i in range(len(cells)) if i not in filled]
    for i in empty:
        sheet.paste(windows[filled[0]], cells[i])
    if empty:
        print(f"  {src}: frames {empty} were empty, filled with a copy of frame {filled[0]}")


def faces():
    for src, name in FACES.items():
        im = Image.open(os.path.join(SRC, "face", src)).convert("RGBA")
        if im.width > 208 or im.height % 60:
            raise SystemExit(f"{src} is {im.size}: needs width <= 208 and height a multiple of 60")
        out = Image.new("RGBA", (416, im.height), (0, 0, 0, 0))
        out.paste(im, (0, 0))
        fill_empty_frames(out, src)
        out.paste(Image.new("RGBA", (208, im.height), FLAT_NORMAL), (208, 0))
        save(out, "face", name + ".png")


def addons():
    template = vanilla("sprite/race/face/addon/EyePatch.png").crop((0, 0, 104, 36))
    template.paste(Image.new("RGBA", (40, 24), (0, 0, 0, 0)), (6, 6))  # empty colour window
    for src, (name, top) in ADDONS.items():
        im = Image.open(os.path.join(SRC, "face", "addon", src)).convert("RGBA")
        frames = im.width // 52
        out = Image.new("RGBA", (104, 36 * frames))
        for i in range(frames):
            window = im.crop((i * 52 + 6, 6, i * 52 + 46, 54))
            art = window.getchannel("A").getbbox()
            if art and (art[1] < top or art[3] > top + 24):
                print(f"  warning: {src} frame {i} art spans rows {art[1]}-{art[3]}, "
                      f"only rows {top}-{top + 24} fit in an addon and the rest is cut off")
            cell = template.copy()
            cell.paste(window.crop((0, top, 40, top + 24)), (6, 6))
            out.paste(cell, (0, 36 * i))
        save(out, "face", "addon", name + ".png")


# Placeholder race icons (race picker, menus) are built from these face layers until the
# spriter supplies real ones as SRC/icon/24.png and SRC/icon/32.png (same layout as the
# vanilla sprite/icon/<size>/race/Human.png: colour cell + normal cell, art window at +6,+6).
ICON_LAYERS = [  # (face output name, frame, tint)
    ("YingletChest", 0, (210, 169, 151)),
    ("YingletEars", 0, (210, 169, 151)),
    ("YingletSkull", 0, (210, 169, 151)),
    ("YingletMouth", 0, (210, 169, 151)),
    ("YingletNose", 0, (210, 169, 151)),
    ("YingletEyes", 0, (60, 104, 153)),
    ("YingletEyebrow", 0, (196, 174, 153)),
    ("YingletHair", 0, (196, 174, 153)),
]


def icons():
    face = Image.new("RGBA", (40, 48), (0, 0, 0, 0))
    for name, frame, tint in ICON_LAYERS:
        sheet = Image.open(os.path.join(OUT, "face", name + ".png")).convert("RGBA")
        x, y = 6 + 52 * (frame % 4), 6 + 60 * (frame // 4)
        layer = sheet.crop((x, y, x + 40, y + 48))
        r, g, b, a = layer.split()
        r, g, b = (ch.point(lambda v, t=t: v * t // 255) for ch, t in zip((r, g, b), tint))
        face.alpha_composite(Image.merge("RGBA", (r, g, b, a)))
    x1, y1, x2, y2 = face.getchannel("A").getbbox()
    side = max(x2 - x1, y2 - y1)
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(face.crop((cx - side // 2, cy - side // 2, cx - side // 2 + side, cy - side // 2 + side)))

    for size in (24, 32):
        given = os.path.join(SRC, "icon", f"{size}.png")
        if os.path.exists(given):
            save(Image.open(given).convert("RGBA"), "..", "icon", str(size), "race", "Yinglet.png")
            continue
        art = square.resize((size, size), Image.LANCZOS)
        cell = size + 12
        out = vanilla(f"sprite/icon/{size}/race/Human.png")
        out.paste(Image.new("RGBA", (size, size), (0, 0, 0, 0)), (6, 6))
        out.paste(art, (6, 6))
        normal = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        normal.paste(Image.new("RGBA", (size, size), FLAT_NORMAL), (0, 0), art.getchannel("A"))
        out.paste(Image.new("RGBA", (size, size), (0, 0, 0, 0)), (cell + 6, 6))
        out.paste(normal, (cell + 6, 6))
        save(out, "..", "icon", str(size), "race", "Yinglet.png")


if __name__ == "__main__":
    body()
    faces()
    addons()
    icons()
