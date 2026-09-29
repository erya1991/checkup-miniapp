"""Normalize paper report orientation using OCR table-header geometry."""

from itertools import combinations, product
from pathlib import Path
import shutil
import unicodedata

import cv2


HEADERS = ("检验项目", "结果", "参考范围", "单位")
HEADER_ALIASES = {
    "项目": "检验项目",
    "参考区间": "参考范围",
    "参考区间-单位": "参考范围",
}
ROTATIONS = ("0", "90_CW", "90_CCW", "180")


def _header_text(value):
    return "".join(unicodedata.normalize("NFKC", str(value)).split())


def _rotated_geometry(item, rotation, image_width, image_height):
    x, y = float(item["center_x"]), float(item["center_y"])
    width, height = float(item["width"]), float(item["height"])
    if rotation == "90_CW":
        return image_height - y, x, height, width
    if rotation == "90_CCW":
        return y, image_width - x, height, width
    if rotation == "180":
        return image_width - x, image_height - y, width, height
    return x, y, width, height


def detect_orientation(items, image_width, image_height):
    """Require at least three aligned headers in their semantic left-to-right order."""
    observations = {header: [] for header in HEADERS}
    for item in items:
        label = _header_text(item.get("text", ""))
        label = HEADER_ALIASES.get(label, label)
        if label in observations and float(item.get("confidence", 0)) >= 0.8:
            observations[label].append(item)

    best = {}
    for rotation in ROTATIONS:
        candidates = []
        for count in (4, 3):
            for labels in combinations(HEADERS, count):
                if any(not observations[label] for label in labels):
                    continue
                for group in product(*(observations[label] for label in labels)):
                    geometry = [
                        _rotated_geometry(item, rotation, image_width, image_height)
                        for item in group
                    ]
                    xs = [entry[0] for entry in geometry]
                    ys = [entry[1] for entry in geometry]
                    heights = sorted(entry[3] for entry in geometry)
                    widths = sorted(entry[2] for entry in geometry)
                    median_height = heights[len(heights) // 2]
                    median_width = widths[len(widths) // 2]
                    y_spread = max(ys) - min(ys)
                    min_gap = max(8.0, median_width * 0.25)
                    if y_spread > max(20.0, median_height * 1.5):
                        continue
                    if any(right - left <= min_gap for left, right in zip(xs, xs[1:])):
                        continue
                    candidates.append({
                        "headers": list(labels),
                        "headerCount": count,
                        "ySpread": round(y_spread, 2),
                        "ocrIndexes": [item["index"] for item in group],
                    })
        if candidates:
            best[rotation] = min(
                candidates,
                key=lambda candidate: (-candidate["headerCount"], candidate["ySpread"]),
            )

    counts = {rotation: best.get(rotation, {}).get("headerCount", 0) for rotation in ROTATIONS}
    ranked = sorted(ROTATIONS, key=lambda rotation: counts[rotation], reverse=True)
    winner = ranked[0]
    confident = counts[winner] >= 3 and counts[winner] > counts[ranked[1]]
    applied = winner if confident else "0"
    return {
        "orientationStatus": (
            "UNCERTAIN" if not confident else "NORMAL" if applied == "0" else "ROTATED"
        ),
        "rotationApplied": applied,
        "orientationMethod": "TABLE_HEADER_GEOMETRY",
        "orientationEvidence": {
            "detectedHeaders": {
                label: [item["index"] for item in observations[label]]
                for label in HEADERS
            },
            "candidateHeaderCounts": counts,
            "selectedHeaders": best.get(winner) if confident else None,
        },
    }


def prepare_working_image(source_path: Path, working_path: Path, items):
    image = cv2.imread(str(source_path))
    if image is None:
        raise ValueError(f"无法读取原始报告图片：{source_path}")
    image_height, image_width = image.shape[:2]
    decision = detect_orientation(items, image_width, image_height)
    rotation = decision["rotationApplied"]
    working_path.parent.mkdir(parents=True, exist_ok=True)
    if rotation == "0":
        shutil.copyfile(source_path, working_path)
    else:
        operation = {
            "90_CW": cv2.ROTATE_90_CLOCKWISE,
            "90_CCW": cv2.ROTATE_90_COUNTERCLOCKWISE,
            "180": cv2.ROTATE_180,
        }[rotation]
        rotated = cv2.rotate(image, operation)
        if not cv2.imwrite(str(working_path), rotated):
            raise OSError(f"无法写入方向归一化图片：{working_path}")
    return decision
