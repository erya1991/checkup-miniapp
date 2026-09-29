"""Create a fully synthetic OCR acceptance image with no personal health data."""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main() -> None:
    destination = Path(sys.argv[1])
    destination.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1600, 1100), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 39)
    title_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 48)
    draw.text((560, 85), "检验报告（合成测试）", font=title_font, fill="black")
    draw.text((100, 175), "测试编号：SYNTHETIC-001", font=font, fill="black")
    columns = (100, 675, 970, 1290)
    for x, label in zip(columns, ("检验项目", "结果", "参考范围", "单位"), strict=True):
        draw.text((x, 280), label, font=font, fill="black")
    rows = (
        ("白细胞计数", "6.17", "3.50~9.50", "10^9/L"),
        ("红细胞计数", "4.61", "4.30~5.80", "10^12/L"),
        ("血红蛋白", "143", "130~175", "g/L"),
        ("血小板计数", "230", "125~350", "10^9/L"),
        ("葡萄糖", "5.2", "3.9~6.1", "mmol/L"),
    )
    for row_number, values in enumerate(rows):
        y = 385 + row_number * 125
        for x, value in zip(columns, values, strict=True):
            draw.text((x, y), value, font=font, fill="black")
    image.save(destination, format="JPEG", quality=95)
    print(f"synthetic report generated: {destination.name}")


if __name__ == "__main__":
    main()
