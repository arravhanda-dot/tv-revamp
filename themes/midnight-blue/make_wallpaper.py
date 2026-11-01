#!/usr/bin/env python3
"""Draws themes/midnight-blue/wallpaper.jpg: pitch black at the top fading into deep blue.

A black-to-blue gradient with a soft cobalt glow low on the screen, behind the dock, and a
faint second glow top right behind the buttons. It is kept dark so the clock, the names and the
glass stay readable.

Dark gradients band badly on TVs that decode wallpapers in 16-bit colour (RGB_565, the
launcher's default), so the picture carries a fixed fine grain (seeded, so every run draws the
same file). The grain breaks each band into noise that the eye averages back into a smooth ramp.

Run from the repository root (needs Pillow):
    python3 themes/midnight-blue/make_wallpaper.py
"""
import random
from pathlib import Path

from PIL import Image

W, H = 1920, 1080
OUT = Path(__file__).resolve().parent / "wallpaper.jpg"

TOP = (0, 0, 0)            # pitch black
BOTTOM = (4, 18, 58)       # deep navy
GLOW = (22, 70, 190)       # cobalt, behind the dock
GLOW2 = (10, 34, 96)       # dimmer blue, top right


def clamp(v):
    return 0 if v < 0 else 255 if v > 255 else int(v + 0.5)


def smooth(t):
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    return t * t * (3 - 2 * t)


def main():
    rng = random.Random(1080)
    img = Image.new("RGB", (W, H))
    px = img.load()
    # The main glow: a wide ellipse centred low and slightly left, like light under the dock.
    gx, gy, grx, gry = W * 0.42, H * 1.02, W * 0.75, H * 0.62
    # The second glow: small, top right, behind the Inputs / Wi-Fi / Settings pills.
    hx, hy, hrx, hry = W * 0.92, H * -0.10, W * 0.45, H * 0.45
    for y in range(H):
        v = smooth(y / (H - 1)) ** 1.6  # stays black for longer, then deepens into blue
        base = [TOP[i] + (BOTTOM[i] - TOP[i]) * v for i in range(3)]
        dy1 = ((y - gy) / gry) ** 2
        dy2 = ((y - hy) / hry) ** 2
        for x in range(W):
            d1 = ((x - gx) / grx) ** 2 + dy1
            d2 = ((x - hx) / hrx) ** 2 + dy2
            g1 = (1 - smooth(d1 ** 0.5)) ** 2 * 0.55
            g2 = (1 - smooth(d2 ** 0.5)) ** 2 * 0.30
            n = rng.uniform(-2.2, 2.2)
            px[x, y] = tuple(
                clamp(base[i] + GLOW[i] * g1 + GLOW2[i] * g2 + n) for i in range(3))
    img.save(OUT, "JPEG", quality=88, optimize=True, subsampling=0)
    print("%s %d KB" % (OUT, OUT.stat().st_size // 1024))


if __name__ == "__main__":
    main()
