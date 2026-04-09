#!/usr/bin/env python3
"""
Generate og-image.png (1200x630) and twitter-image.png (1200x600) for
aisalespipeline.com social media sharing.

These were referenced in the meta tags but never created — every share
link was getting a broken image preview.
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

OUT = Path('/Users/teddy/ai-sales-pipeline/images')

# Brand colors (from index.html CSS)
DARK_BG = (10, 10, 10)
DARK_ALT = (17, 17, 17)
ORANGE = (255, 107, 53)
BLUE_ACCENT = (0, 212, 255)
WHITE = (255, 255, 255)
GRAY = (180, 180, 180)


def create_image(width, height, output_path, title_size=72):
    """Create a branded social media image."""
    img = Image.new('RGB', (width, height), DARK_BG)
    draw = ImageDraw.Draw(img)

    # Background gradient simulation (dark with orange glow on right)
    for y in range(height):
        # Vertical gradient from dark to slightly lighter
        gradient_factor = y / height
        r = int(10 + 7 * gradient_factor)
        g = int(10 + 5 * gradient_factor)
        b = int(10 + 5 * gradient_factor)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Orange glow circle on right side
    glow_x, glow_y, glow_r = int(width * 0.85), int(height * 0.5), int(height * 0.6)
    for r in range(glow_r, 0, -10):
        alpha = int(40 * (1 - r / glow_r))
        if alpha < 1:
            continue
        # Approximate alpha by darker orange tints
        draw.ellipse(
            [(glow_x - r, glow_y - r), (glow_x + r, glow_y + r)],
            outline=(ORANGE[0], ORANGE[1] // 2, 0)
        )

    # Try to load a system font
    title_font = None
    subtitle_font = None
    small_font = None
    for font_path in [
        '/System/Library/Fonts/SFNS.ttf',
        '/System/Library/Fonts/HelveticaNeue.ttc',
        '/System/Library/Fonts/Helvetica.ttc',
        '/Library/Fonts/Arial.ttf',
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
    ]:
        try:
            title_font = ImageFont.truetype(font_path, title_size)
            subtitle_font = ImageFont.truetype(font_path, 36)
            small_font = ImageFont.truetype(font_path, 28)
            break
        except (OSError, IOError):
            continue

    if title_font is None:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Title — main headline
    title = "AI Sales Pipeline"
    bbox = draw.textbbox((0, 0), title, font=title_font)
    title_w = bbox[2] - bbox[0]
    title_h = bbox[3] - bbox[1]
    title_x = 80
    title_y = int(height * 0.32)
    draw.text((title_x, title_y), title, fill=WHITE, font=title_font)

    # Subtitle
    subtitle = "The AI CRM That Follows Up"
    draw.text((title_x, title_y + title_h + 30), subtitle, fill=ORANGE, font=subtitle_font)

    # Subtitle line 2
    subtitle2 = "for Real Estate Agents"
    draw.text((title_x, title_y + title_h + 80), subtitle2, fill=ORANGE, font=subtitle_font)

    # Bottom tagline
    tagline = "Respond to every lead in 60 seconds. 24/7. Built by a real agent."
    draw.text((title_x, height - 100), tagline, fill=GRAY, font=small_font)

    # Domain in bottom right
    domain = "aisalespipeline.com"
    bbox = draw.textbbox((0, 0), domain, font=small_font)
    domain_w = bbox[2] - bbox[0]
    draw.text((width - domain_w - 80, height - 100), domain, fill=ORANGE, font=small_font)

    # Top accent line
    draw.rectangle([(0, 0), (width, 6)], fill=ORANGE)

    img.save(output_path, 'PNG', optimize=True)
    file_size = output_path.stat().st_size / 1024
    print(f"  ✓ {output_path.name} ({width}x{height}, {file_size:.1f} KB)")


def main():
    print("🎨 Generating social media images")
    OUT.mkdir(exist_ok=True)

    # Open Graph image — 1200x630 is the Facebook/LinkedIn standard
    create_image(1200, 630, OUT / 'og-image.png', title_size=84)

    # Twitter Card image — 1200x600 is the Twitter summary_large_image standard
    create_image(1200, 600, OUT / 'twitter-image.png', title_size=84)

    print("\n✅ Done")


if __name__ == '__main__':
    main()
