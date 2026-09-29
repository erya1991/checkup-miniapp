# src/paper_ocr_baseline.py

import json
import importlib
from pathlib import Path
from typing import Any


# ---------------------------------------------------------
# 路径
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 使用运行时导入，兼容作为包运行和直接执行，同时避免静态检查器解析失败。
_report_context = importlib.import_module(
    f"{__package__}.report_context" if __package__ else "report_context"
)
get_report_id = _report_context.get_report_id
sample_path = _report_context.sample_path
output_path = _report_context.output_path
_orientation = importlib.import_module(
    f"{__package__}.paper_orientation_normalizer"
    if __package__ else "paper_orientation_normalizer"
)
prepare_working_image = _orientation.prepare_working_image


REPORT_ID = get_report_id()

IMAGE_PATH = sample_path(
    ".jpg"
)

OUTPUT_PATH = output_path(
    "_ocr.json"
)

WORKING_IMAGE_PATH = (
    PROJECT_ROOT / "output" / REPORT_ID / "normalized_input.jpg"
)


# ---------------------------------------------------------
# RapidOCR 兼容导入
# ---------------------------------------------------------

try:
    # 新版 RapidOCR
    from rapidocr import RapidOCR  # type: ignore[import-not-found]
    RAPIDOCR_PACKAGE = "rapidocr"
except ImportError:
    # 兼容之前常见的 rapidocr_onnxruntime
    from rapidocr_onnxruntime import RapidOCR  # type: ignore[import-not-found]
    RAPIDOCR_PACKAGE = "rapidocr_onnxruntime"


def normalize_bbox(box: Any) -> list[list[float]]:
    """
    将 bbox 统一转换为：
    [
        [x1, y1],
        [x2, y2],
        [x3, y3],
        [x4, y4]
    ]
    """
    normalized = []

    for point in box:
        x = float(point[0])
        y = float(point[1])
        normalized.append([x, y])

    return normalized


def calculate_geometry(box: list[list[float]]) -> dict:
    """
    根据四点 bbox 计算：
    center_x
    center_y
    width
    height

    单次 OCR 结果只做几何统计；方向归一化在两次 OCR 之间完成。
    """

    xs = [p[0] for p in box]
    ys = [p[1] for p in box]

    min_x = min(xs)
    max_x = max(xs)
    min_y = min(ys)
    max_y = max(ys)

    return {
        "center_x": round((min_x + max_x) / 2, 2),
        "center_y": round((min_y + max_y) / 2, 2),
        "width": round(max_x - min_x, 2),
        "height": round(max_y - min_y, 2),
    }


def parse_rapidocr_result(raw_result: Any) -> list[dict]:
    """
    同时兼容：

    1. 新版 RapidOCR：
       result.boxes
       result.txts
       result.scores

    2. 旧版 rapidocr_onnxruntime：
       result = [
           [box, text, score],
           ...
       ]
    """

    items = []

    # -----------------------------------------------------
    # 新版 RapidOCR Output
    # -----------------------------------------------------
    if (
        hasattr(raw_result, "boxes")
        and hasattr(raw_result, "txts")
        and hasattr(raw_result, "scores")
    ):
        boxes = raw_result.boxes
        texts = raw_result.txts
        scores = raw_result.scores

        if boxes is None or texts is None or scores is None:
            return []

        for index, (box, text, score) in enumerate(
            zip(boxes, texts, scores),
            start=1,
        ):
            bbox = normalize_bbox(box)
            geometry = calculate_geometry(bbox)

            items.append(
                {
                    "index": index,
                    "text": str(text),
                    "confidence": round(float(score), 6),
                    "bbox": bbox,
                    **geometry,
                }
            )

        return items

    # -----------------------------------------------------
    # 旧版 RapidOCR
    # -----------------------------------------------------
    if isinstance(raw_result, (list, tuple)):
        for index, item in enumerate(raw_result, start=1):

            if not item or len(item) < 3:
                continue

            box, text, score = item[0], item[1], item[2]

            bbox = normalize_bbox(box)
            geometry = calculate_geometry(bbox)

            items.append(
                {
                    "index": index,
                    "text": str(text),
                    "confidence": round(float(score), 6),
                    "bbox": bbox,
                    **geometry,
                }
            )

    return items


def read_ocr(engine, image_path: Path) -> list[dict]:
    result = engine(str(image_path))
    raw_result = result
    if (
        isinstance(result, tuple)
        and len(result) == 2
        and isinstance(result[1], (float, int, list, tuple, dict))
    ):
        raw_result = result[0]
    return parse_rapidocr_result(raw_result)


def run_ocr() -> tuple[list[dict], dict]:

    if not IMAGE_PATH.exists():
        raise FileNotFoundError(
            f"未找到测试图片：{IMAGE_PATH}\n"
            f"请确认文件已经放到 samples/{REPORT_ID}.jpg"
        )

    print("=" * 100)
    print("PoC 05｜纸质检验报告 OCR Baseline")
    print("=" * 100)

    print(f"RapidOCR package : {RAPIDOCR_PACKAGE}")
    print(f"Image            : {IMAGE_PATH}")
    print()

    engine = RapidOCR()

    initial_items = read_ocr(engine, IMAGE_PATH)
    orientation = prepare_working_image(
        IMAGE_PATH, WORKING_IMAGE_PATH, initial_items
    )
    print(f"Working image    : {WORKING_IMAGE_PATH}")
    print(f"Orientation      : {orientation['orientationStatus']}")
    print(f"Rotation applied : {orientation['rotationApplied']}")
    print(f"Header evidence  : {orientation['orientationEvidence']}")
    print()
    items = (
        read_ocr(engine, WORKING_IMAGE_PATH)
        if orientation["rotationApplied"] != "0"
        else initial_items
    )
    return items, orientation


def print_result(items: list[dict]) -> None:

    print(
        f"{'index':<7}"
        f"{'confidence':<13}"
        f"{'center_x':<12}"
        f"{'center_y':<12}"
        f"{'width':<10}"
        f"{'height':<10}"
        f"text"
    )

    print("-" * 120)

    for item in items:
        print(
            f"{item['index']:<7}"
            f"{item['confidence']:<13.6f}"
            f"{item['center_x']:<12.2f}"
            f"{item['center_y']:<12.2f}"
            f"{item['width']:<10.2f}"
            f"{item['height']:<10.2f}"
            f"{item['text']}"
        )

    print("-" * 120)
    print(f"OCR items: {len(items)}")


def save_result(items: list[dict], orientation: dict) -> None:

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    output = {
        "poc": "PoC 05",
        "stage": "paper_report_baseline",
        "sourceImage": str(
            IMAGE_PATH.relative_to(PROJECT_ROOT)
        ).replace("\\", "/"),
        "workingImage": str(
            WORKING_IMAGE_PATH.relative_to(PROJECT_ROOT)
        ).replace("\\", "/"),
        **orientation,
        "ocrEngine": "RapidOCR",
        "preprocessing": (
            "NONE" if orientation["rotationApplied"] == "0"
            else f"ROTATE_{orientation['rotationApplied']}"
        ),
        "itemCount": len(items),
        "items": items,
    }

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(f"JSON saved: {OUTPUT_PATH}")


def main():

    items, orientation = run_ocr()

    print_result(items)

    save_result(items, orientation)


if __name__ == "__main__":
    main()
