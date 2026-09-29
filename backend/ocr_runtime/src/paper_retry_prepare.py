import json
from pathlib import Path

import cv2

from report_context import (
    get_report_id,
    output_path,
)

BASE_DIR = Path(__file__).resolve().parent.parent


REPORT_ID = get_report_id()


# =========================================================
# 当前报告输入
# =========================================================

IMAGE_PATH = BASE_DIR / "output" / REPORT_ID / "normalized_input.jpg"

OCR_PATH = output_path(
    "_ocr.json"
)

ROWS_PATH = output_path(
    "_rows.json"
)


# =========================================================
# 当前报告独立 Retry 工作目录
#
# output/
# └─ {REPORT_ID}/
#    └─ paper_retry/
# =========================================================

RETRY_DIR = (
    BASE_DIR
    / "output"
    / REPORT_ID
    / "paper_retry"
)

RETRY_TARGETS_PATH = (
    RETRY_DIR
    / "paper_retry_targets.json"
)

MANIFEST_PATH = (
    RETRY_DIR
    / "paper_retry_manifest.json"
)
def load_dynamic_retry_targets():
    """
    PoC 06-02B

    Retry Target 不再人工写死，
    统一读取 paper_retry_selector.py 的输出。

    同时保留 camelCase / snake_case 两套字段，
    兼容前面 PoC 阶段已有代码。
    """

    if not RETRY_TARGETS_PATH.exists():

        raise FileNotFoundError(
            "未找到动态 Retry Target 文件：\n"
            f"{RETRY_TARGETS_PATH}\n\n"
            "请先执行：\n"
            "python src/paper_retry_selector.py"
        )

    with RETRY_TARGETS_PATH.open(
        "r",
        encoding="utf-8",
    ) as f:

        data = json.load(f)

    raw_targets = data.get(
        "targets",
        []
    )

    targets = []

    for item in raw_targets:

        target = dict(item)

        # =================================================
        # Compatibility aliases
        # =================================================

        target["target_id"] = (
            item.get("targetId")
        )

        target["block_id"] = (
            item.get("blockId")
        )

        target["row_index"] = (
            item.get("rowIndex")
        )

        target["row_metric"] = (
            item.get("rowMetric")
        )

        target["original_text"] = (
            item.get("originalText")
        )

        # 单个 reason 保持兼容
        if not target.get("reason"):

            reasons = item.get(
                "reasons",
                []
            )

            if reasons:

                target["reason"] = (
                    reasons[0]
                )

        targets.append(
            target
        )

    return targets

# =========================================================
# 本轮 PoC 明确需要验证的 7 个字段
#
# 注意：
# 这是当前样本的测试清单，
# 不属于生产环境硬编码规则。
# =========================================================



def load_json(path: Path):
    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def find_row(rows, metric_name):

    for row in rows:
        if row.get("metric") == metric_name:
            return row

    return None


def get_ocr_item_map(ocr_items):

    return {
        item["index"]: item
        for item in ocr_items
    }


def union_bbox(items):

    xs = []
    ys = []

    for item in items:
        for x, y in item["bbox"]:
            xs.append(float(x))
            ys.append(float(y))

    return (
        min(xs),
        min(ys),
        max(xs),
        max(ys),
    )


def expand_bbox(
    bbox,
    image_width,
    image_height,
):

    x1, y1, x2, y2 = bbox

    width = x2 - x1
    height = y2 - y1

    # 文本识别模型需要一点上下文，
    # 但不能扩得太大把相邻列带进来。
    pad_x = max(10, width * 0.08)
    pad_y = max(8, height * 0.25)

    x1 = max(
        0,
        int(x1 - pad_x),
    )

    y1 = max(
        0,
        int(y1 - pad_y),
    )

    x2 = min(
        image_width,
        int(x2 + pad_x),
    )

    y2 = min(
        image_height,
        int(y2 + pad_y),
    )

    return x1, y1, x2, y2


def save_variants(
    crop,
    target_id,
):

    paths = {}

    # ---------------------------------------------
    # V1：原始局部图
    # ---------------------------------------------

    v1_path = (
        RETRY_DIR
        / f"{target_id}_v1_raw.png"
    )

    cv2.imwrite(
        str(v1_path),
        crop,
    )

    paths["v1_raw"] = str(
        v1_path.relative_to(BASE_DIR)
    ).replace("\\", "/")

    # ---------------------------------------------
    # V2：2倍放大
    # ---------------------------------------------

    upscale = cv2.resize(
        crop,
        None,
        fx=2.0,
        fy=2.0,
        interpolation=cv2.INTER_CUBIC,
    )

    v2_path = (
        RETRY_DIR
        / f"{target_id}_v2_upscale.png"
    )

    cv2.imwrite(
        str(v2_path),
        upscale,
    )

    paths["v2_upscale"] = str(
        v2_path.relative_to(BASE_DIR)
    ).replace("\\", "/")

    # ---------------------------------------------
    # V3：灰度 + 自适应对比度
    #
    # baseline 阶段不做预处理；
    # 当前已经属于异常字段定向复核，
    # 因此允许局部增强作为第二视角。
    # ---------------------------------------------

    gray = cv2.cvtColor(
        upscale,
        cv2.COLOR_BGR2GRAY,
    )

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8),
    )

    enhanced = clahe.apply(gray)

    v3_path = (
        RETRY_DIR
        / f"{target_id}_v3_enhanced.png"
    )

    cv2.imwrite(
        str(v3_path),
        enhanced,
    )

    paths["v3_enhanced"] = str(
        v3_path.relative_to(BASE_DIR)
    ).replace("\\", "/")

    return paths


def main():

    RETRY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    image = cv2.imread(
        str(IMAGE_PATH)
    )

    if image is None:
        raise RuntimeError(
            f"无法读取图片：{IMAGE_PATH}"
        )

    image_height, image_width = (
        image.shape[:2]
    )

    ocr_data = load_json(
        OCR_PATH
    )

    row_data = load_json(
        ROWS_PATH
    )

    ocr_map = get_ocr_item_map(
        ocr_data["items"]
    )

    rows = row_data["rows"]

    manifest_items = []
    retry_targets = (
        load_dynamic_retry_targets()
    )

    print()
    print(
        f"Dynamic retry targets loaded: "
        f"{len(retry_targets)}"
    )

    for target in retry_targets:

        row = find_row(
            rows,
            target["rowMetric"],
        )

        if row is None:
            print(
                f"[SKIP] 未找到行："
                f"{target['rowMetric']}"
            )
            continue

        field = target["field"]

        indexes = (
            row
            .get("ocr_indexes", {})
            .get(field, [])
        )

        if not indexes:
            print(
                f"[SKIP] "
                f"{target['targetId']} "
                f"没有 {field} OCR bbox"
            )
            continue

        items = [
            ocr_map[index]
            for index in indexes
            if index in ocr_map
        ]

        if not items:
            continue

        bbox = union_bbox(items)

        expanded = expand_bbox(
            bbox,
            image_width,
            image_height,
        )

        x1, y1, x2, y2 = expanded

        crop = image[
            y1:y2,
            x1:x2
        ]

        variants = save_variants(
            crop,
            target["targetId"],
        )

        original_text = row.get(
            field
        )

        manifest_items.append(
            {
                **target,

                "blockId":
                    row.get("block_id"),

                "rowIndex":
                    row.get("row_index"),

                "originalText":
                    original_text,

                "ocrIndexes":
                    indexes,

                "cropBbox": {
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                },

                "variants":
                    variants,
            }
        )

        print(
            f"[OK] "
            f"{target['targetId']:<10} "
            f"{field:<7} "
            f"{original_text}"
        )

    manifest = {
        "poc": "PoC 05-05",
        "stage":
            "paper_retry_prepare",

        "sourceImage":
            f"samples/{REPORT_ID}.jpg",

        "workingImage":
            f"output/{REPORT_ID}/normalized_input.jpg",

        "targetCount":
            len(manifest_items),

        "targets":
            manifest_items,
    }

    with MANIFEST_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            manifest,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(
        f"Retry targets: "
        f"{len(manifest_items)}"
    )

    print(
        f"Manifest: "
        f"{MANIFEST_PATH}"
    )


if __name__ == "__main__":
    main()
