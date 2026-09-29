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
# 当前报告基础输入
# =========================================================

IMAGE_PATH = BASE_DIR / "output" / REPORT_ID / "normalized_input.jpg"

ROWS_PATH = output_path(
    "_rows.json"
)

LAYOUT_PATH = output_path(
    "_layout.json"
)


# =========================================================
# 当前报告 Round2 工作目录
# =========================================================

ROUND2_RETRY_DIR = (
    BASE_DIR
    / "output"
    / REPORT_ID
    / "paper_retry_round2"
)

ROUND2_TARGETS_PATH = (
    ROUND2_RETRY_DIR
    / "paper_retry_round2_targets.json"
)

OUTPUT_DIR = ROUND2_RETRY_DIR


def load_dynamic_round2_targets():
    """
    PoC 06-02C

    Round2 不再写死 metric_01 / metric_04 / metric_06。

    统一读取：

    paper_retry_round2_targets.json
    """

    if not ROUND2_TARGETS_PATH.exists():

        raise FileNotFoundError(
            "未找到 Round2 Target 文件：\n"
            f"{ROUND2_TARGETS_PATH}\n\n"
            "请先执行：\n"
            "python src/paper_retry_round2_selector.py"
        )

    with ROUND2_TARGETS_PATH.open(
        "r",
        encoding="utf-8",
    ) as f:

        data = json.load(f)

    targets = []

    for item in data.get(
        "targets",
        []
    ):

        target = dict(
            item
        )

        # -------------------------------------------------
        # 兼容之前 Round2 Prepare 使用的 snake_case
        # -------------------------------------------------

        target[
            "target_id"
        ] = item.get(
            "targetId"
        )

        target[
            "block_id"
        ] = item.get(
            "blockId"
        )

        target[
            "row_index"
        ] = item.get(
            "rowIndex"
        )

        target[
            "original_text"
        ] = item.get(
            "originalText"
        )

        targets.append(
            target
        )

    return targets

MANIFEST_PATH = (
    OUTPUT_DIR
    / "paper_retry_round2_manifest.json"
)




def load_json(path):

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def find_row(rows, metric):

    for row in rows:
        if row.get("metric") == metric:
            return row

    return None


def find_block(layout, block_id):

    for block in layout["table_blocks"]:
        if block["block_id"] == block_id:
            return block

    return None


def save_variants(
    image,
    target,
    row,
    block,
):

    image_h, image_w = image.shape[:2]

    metric_column = (
        block["columns"]["metric"]
    )

    # -----------------------------------------------------
    # 使用“整列单元格”而不是 OCR bbox
    # -----------------------------------------------------

    x1 = int(
        max(
            0,
            metric_column["min_x"] + 5,
        )
    )

    x2 = int(
        min(
            image_w,
            metric_column["max_x"] - 5,
        )
    )

    anchor_y = float(
        row["anchor_y"]
    )

    # 当前报告相邻行约 50~60 px。
    # 保留约 ±28px 基本能够覆盖整行，
    # 又不会吃到上下两行。
    y1 = int(
        max(
            0,
            anchor_y - 30,
        )
    )

    y2 = int(
        min(
            image_h,
            anchor_y + 30,
        )
    )

    crop = image[
        y1:y2,
        x1:x2
    ]

    paths = {}

    # -----------------------------------------------------
    # V1：完整单元格原图
    # -----------------------------------------------------

    path1 = (
        OUTPUT_DIR
        / f"{target['targetId']}_v1_cell.png"
    )

    cv2.imwrite(
        str(path1),
        crop,
    )

    paths["v1_cell"] = str(
        path1.relative_to(BASE_DIR)
    ).replace("\\", "/")

    # -----------------------------------------------------
    # V2：3x 放大
    # -----------------------------------------------------

    upscale = cv2.resize(
        crop,
        None,
        fx=3.0,
        fy=3.0,
        interpolation=cv2.INTER_CUBIC,
    )

    path2 = (
        OUTPUT_DIR
        / f"{target['targetId']}_v2_cell_3x.png"
    )

    cv2.imwrite(
        str(path2),
        upscale,
    )

    paths["v2_cell_3x"] = str(
        path2.relative_to(BASE_DIR)
    ).replace("\\", "/")

    # -----------------------------------------------------
    # V3：3x + 灰度 + CLAHE
    # -----------------------------------------------------

    gray = cv2.cvtColor(
        upscale,
        cv2.COLOR_BGR2GRAY,
    )

    clahe = cv2.createCLAHE(
        clipLimit=1.8,
        tileGridSize=(8, 8),
    )

    enhanced = clahe.apply(gray)

    path3 = (
        OUTPUT_DIR
        / f"{target['targetId']}_v3_cell_enhanced.png"
    )

    cv2.imwrite(
        str(path3),
        enhanced,
    )

    paths["v3_cell_enhanced"] = str(
        path3.relative_to(BASE_DIR)
    ).replace("\\", "/")

    return {
        "cropBbox": {
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
        },
        "variants": paths,
    }


def main():

    OUTPUT_DIR.mkdir(
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

    row_data = load_json(
        ROWS_PATH
    )

    layout = load_json(
        LAYOUT_PATH
    )

    rows = row_data["rows"]

    outputs = []

    round2_targets = load_dynamic_round2_targets()

    print()

    print(
        f"Dynamic Round2 targets loaded: "
        f"{len(round2_targets)}"
    )

    for target in round2_targets:

        row = find_row(
            rows,
            target["rowMetric"],
        )

        if row is None:
            print(
                f"[SKIP] 找不到："
                f"{target['rowMetric']}"
            )
            continue

        block = find_block(
            layout,
            row["block_id"],
        )

        if block is None:
            continue

        crop_info = save_variants(
            image,
            target,
            row,
            block,
        )

        outputs.append(
            {
                **target,

                "field": "metric",

                "blockId":
                    row["block_id"],

                "rowIndex":
                    row["row_index"],

                "anchorY":
                    row["anchor_y"],

                "originalText":
                    row["metric"],

                **crop_info,
            }
        )

        print(
            f"[OK] "
            f"{target['targetId']} "
            f"{row['metric']}"
        )

    manifest = {
        "poc": "PoC 05-05D",
        "stage":
            "paper_retry_round2_prepare",

        "sourceImage":
            f"samples/{REPORT_ID}.jpg",

        "workingImage":
            f"output/{REPORT_ID}/normalized_input.jpg",

        "strategy":
            "FULL_METRIC_CELL_CROP",

        "targetCount":
            len(outputs),

        "targets":
            outputs,
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
        f"Round2 targets: {len(outputs)}"
    )

    print(
        f"Manifest: {MANIFEST_PATH}"
    )


if __name__ == "__main__":
    main()
