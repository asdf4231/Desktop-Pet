"""Split the supplied character image into independently animated body parts.

The source artwork is never repainted. Each layer keeps the original pixels and
only masks away the areas owned by another articulated part.
"""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src" / "shaqiu_pet" / "assets"
SOURCE = ASSETS / "character.png"

POLYGONS: dict[str, tuple[tuple[int, int], ...]] = {
    "character_head": (
        (0, 0),
        (790, 0),
        (790, 600),
        (720, 650),
        (650, 690),
        (570, 700),
        (500, 695),
        (430, 720),
        (350, 720),
        (280, 695),
        (210, 700),
        (130, 680),
        (60, 640),
        (0, 610),
    ),
    "character_arm_left": (
        (225, 690),
        (190, 730),
        (145, 755),
        (95, 835),
        (52, 925),
        (30, 985),
        (42, 1023),
        (72, 1038),
        (95, 1028),
        (140, 1040),
        (195, 1022),
        (218, 950),
        (205, 860),
        (255, 770),
        (238, 700),
    ),
    "character_arm_right": (
        (565, 690),
        (615, 730),
        (665, 750),
        (720, 830),
        (755, 925),
        (768, 985),
        (752, 1022),
        (724, 1038),
        (696, 1030),
        (655, 1042),
        (603, 1020),
        (574, 950),
        (584, 860),
        (535, 770),
        (558, 700),
    ),
    "character_torso": (
        (155, 610),
        (285, 640),
        (500, 640),
        (635, 680),
        (660, 790),
        (625, 1045),
        (655, 1105),
        (625, 1190),
        (510, 1205),
        (410, 1185),
        (300, 1200),
        (175, 1195),
        (125, 1085),
        (150, 960),
        (165, 820),
    ),
    "character_leg_left": (
        (185, 1135),
        (300, 1120),
        (315, 1190),
        (380, 1170),
        (400, 1200),
        (382, 1310),
        (392, 1380),
        (320, 1400),
        (225, 1400),
        (218, 1320),
        (190, 1210),
    ),
    "character_leg_right": (
        (405, 1130),
        (545, 1125),
        (558, 1200),
        (590, 1270),
        (560, 1400),
        (442, 1400),
        (410, 1310),
        (405, 1190),
    ),
    "character_tail": (
        (535, 1035),
        (620, 1038),
        (690, 1080),
        (750, 1140),
        (755, 1210),
        (710, 1260),
        (615, 1265),
        (555, 1210),
        (520, 1135),
    ),
}


def _polygon_mask(size: tuple[int, int], points: tuple[tuple[int, int], ...]) -> Image.Image:
    scale = 4
    high = Image.new("L", (size[0] * scale, size[1] * scale), 0)
    draw = ImageDraw.Draw(high)
    draw.polygon([(x * scale, y * scale) for x, y in points], fill=255)
    return high.resize(size, Image.Resampling.LANCZOS).point(
        lambda value: 255 if value >= 128 else 0
    )


def _extract(source: Image.Image, mask: Image.Image) -> Image.Image:
    layer = source.copy()
    alpha = Image.composite(source.getchannel("A"), Image.new("L", source.size, 0), mask)
    layer.putalpha(alpha)
    return layer


def main() -> None:
    source = Image.open(SOURCE).convert("RGBA")
    layers = {}
    for name, points in POLYGONS.items():
        layers[name] = _extract(source, _polygon_mask(source.size, points))

    for name, layer in layers.items():
        layer.save(ASSETS / f"{name}.png", optimize=True)

    order = (
        "character_leg_left",
        "character_leg_right",
        "character_tail",
        "character_torso",
        "character_arm_left",
        "character_arm_right",
        "character_head",
    )
    preview = Image.new("RGBA", source.size, (0, 0, 0, 0))
    for name in order:
        preview.alpha_composite(layers[name])
    preview.save(ROOT / ".preview" / "character_layers_neutral.png", optimize=True)


if __name__ == "__main__":
    main()
