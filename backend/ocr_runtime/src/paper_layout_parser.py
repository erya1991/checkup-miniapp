# src/paper_layout_parser.py

import json
import statistics
import unicodedata
from pathlib import Path
try:
    from .report_context import output_path  # type: ignore[reportMissingImports]
except ImportError:
    from importlib import import_module

    output_path = import_module("report_context").output_path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_PATH = output_path(
    "_ocr.json"
)

OUTPUT_PATH = output_path(
    "_layout.json"
)


# ---------------------------------------------------------
# 表头定义
# ---------------------------------------------------------

HEADER_ORDER = [
    "metric",
    "result",
    "reference",
    "unit",
]

HEADER_TEXT_MAP = {
    "检验项目": "metric",
    "项目": "metric",
    "结果": "result",
    "参考范围": "reference",
    "参考区间": "reference",
    "参考区间-单位": "reference_unit",
    "单位": "unit",
    "简称": "auxiliary",
    "检验方法": "auxiliary",
}


def normalize_text(text: str) -> str:
    """
    只做最基础的文本规范化。

    PoC 阶段暂不做：
    - OCR 错字纠正
    - 模糊匹配
    - Alias
    """
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace(" ", "")
    text = text.replace("\t", "")
    text = text.strip()

    return text


def load_ocr_items() -> list[dict]:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"未找到 OCR 输出文件：{INPUT_PATH}\n"
            "请先运行 paper_ocr_baseline.py"
        )

    with INPUT_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("items", [])


def get_page_bounds(items: list[dict]) -> dict:
    """
    根据所有 OCR bbox 估算页面实际可见范围。
    """

    xs = []
    ys = []

    for item in items:
        for x, y in item["bbox"]:
            xs.append(float(x))
            ys.append(float(y))

    return {
        "min_x": min(xs),
        "max_x": max(xs),
        "min_y": min(ys),
        "max_y": max(ys),
    }


def find_header_candidates(items: list[dict]) -> list[dict]:
    """
    找出：
    检验项目 / 结果 / 参考范围 / 单位

    当前阶段使用精确文本匹配。
    """

    candidates = []

    for item in items:
        normalized = normalize_text(item["text"])

        header_type = HEADER_TEXT_MAP.get(normalized)

        if not header_type:
            continue

        candidates.append(
            {
                **item,
                "header_type": header_type,
                "normalized_text": normalized,
            }
        )

    return candidates


def calculate_header_y_tolerance(
    candidates: list[dict],
) -> float:
    """
    动态计算同一表头行允许的 Y 偏差。

    使用表头 OCR 高度的中位数作为基础。
    """

    if not candidates:
        return 25.0

    heights = [
        float(item["height"])
        for item in candidates
        if item.get("height")
    ]

    if not heights:
        return 25.0

    median_height = statistics.median(heights)

    # 当前报告文字高度约 30~40px，
    # 允许一定的拍照倾斜。
    tolerance = max(
        20.0,
        median_height * 0.8,
    )

    return round(tolerance, 2)


def group_header_rows(
    candidates: list[dict],
    tolerance: float,
) -> list[list[dict]]:
    """
    根据 center_y 把表头候选聚成同一视觉行。

    双栏报告的两组表头虽然 X 不同，
    但 Y 基本处于同一水平区域，
    因此这里应聚成一个 Header Row。
    """

    if not candidates:
        return []

    sorted_items = sorted(
        candidates,
        key=lambda x: x["center_y"],
    )

    groups = []

    for item in sorted_items:

        best_group = None
        best_distance = None

        for group in groups:

            group_center_y = statistics.mean(
                x["center_y"]
                for x in group
            )

            distance = abs(
                item["center_y"] - group_center_y
            )

            if distance <= tolerance:
                if (
                    best_distance is None
                    or distance < best_distance
                ):
                    best_group = group
                    best_distance = distance

        if best_group is None:
            groups.append([item])
        else:
            best_group.append(item)

    return groups


def extract_blocks_from_header_row(
    header_row: list[dict],
) -> list[list[dict]]:
    """
    将同一表头行按照 X 从左向右排序。

    自动寻找重复模式：

    metric
    result
    reference
    unit

    如果出现：

    metric result reference unit
    metric result reference unit

    则识别为两个 Table Block。
    """

    items = sorted(
        header_row,
        key=lambda x: x["center_x"],
    )

    blocks = []

    current = []

    for item in items:

        core_count = sum(
            item["header_type"] in HEADER_ORDER
            for item in current
        )
        expected_type = HEADER_ORDER[core_count]

        if item["header_type"] == expected_type:
            current.append(item)

            if core_count + 1 == len(HEADER_ORDER):
                blocks.append(current)
                current = []

        elif item["header_type"] == "reference_unit" and expected_type == "reference":
            current.append({**item, "header_type": "reference",
                            "combined_reference_unit": True})
            blocks.append(current)
            current = []

        elif item["header_type"] == "auxiliary" and current:
            current.append(item)

        else:
            # 当前序列中断。
            #
            # 如果当前 item 本身又是 metric，
            # 则重新开始一组。
            if item["header_type"] == "metric":
                current = [item]
            else:
                current = []

    return blocks


def calculate_block_geometry(
    blocks: list[list[dict]],
    page_bounds: dict,
) -> list[dict]:
    """
    根据表头中心点生成 Table Block 和列区间。

    注意：
    当前仅建立几何区域，
    暂不进行数据行解析。
    """

    if not blocks:
        return []

    blocks = sorted(
        blocks,
        key=lambda block: block[0]["center_x"],
    )

    block_results = []

    # -----------------------------------------------------
    # 先计算各 Block 之间的分割线
    # -----------------------------------------------------

    separators = []

    for i in range(len(blocks) - 1):

        current_last = blocks[i][-1]
        next_first = blocks[i + 1][0]

        separator = (
            current_last["center_x"]
            + next_first["center_x"]
        ) / 2

        separators.append(separator)

    # -----------------------------------------------------
    # 生成 Block
    # -----------------------------------------------------

    for index, block in enumerate(blocks):

        core = {
            item["header_type"]: item
            for item in block
            if item["header_type"] in HEADER_ORDER
        }
        metric = core["metric"]
        result = core["result"]
        reference = core["reference"]
        unit = core.get("unit")
        combined_reference_unit = any(
            item.get("combined_reference_unit") for item in block
        )
        ordered_headers = sorted(block, key=lambda item: item["center_x"])

        def column_bounds(header_type):
            position = next(
                index for index, item in enumerate(ordered_headers)
                if item["header_type"] == header_type
            )
            current = ordered_headers[position]
            left = (
                block_min_x if position == 0 else
                (ordered_headers[position - 1]["center_x"] + current["center_x"]) / 2
            )
            right = (
                block_max_x if position == len(ordered_headers) - 1 else
                (current["center_x"] + ordered_headers[position + 1]["center_x"]) / 2
            )
            return round(left, 2), round(right, 2)

        if index == 0:
            block_min_x = page_bounds["min_x"]
        else:
            block_min_x = separators[index - 1]

        if index == len(blocks) - 1:
            block_max_x = page_bounds["max_x"]
        else:
            block_max_x = separators[index]

        # -------------------------------------------------
        # 四列之间的动态分割线
        # -------------------------------------------------

        metric_min, metric_max = column_bounds("metric")
        result_min, result_max = column_bounds("result")
        reference_min, reference_max = column_bounds("reference")
        unit_min, unit_max = (
            column_bounds("unit") if unit is not None else
            (round(block_max_x, 2), round(block_max_x, 2))
        )

        header_bottom = max(
            max(point[1] for point in item["bbox"])
            for item in block
        )

        block_results.append(
            {
                "block_id": index + 1,

                "header_center_y": round(
                    statistics.mean(
                        item["center_y"]
                        for item in block
                    ),
                    2,
                ),

                "body_start_y": float(header_bottom),
                "combined_reference_unit": combined_reference_unit,

                "x_range": {
                    "min": round(block_min_x, 2),
                    "max": round(block_max_x, 2),
                },

                "columns": {
                    "metric": {
                        "center_x": metric["center_x"],
                        "min_x": metric_min,
                        "max_x": metric_max,
                    },

                    "result": {
                        "center_x": result["center_x"],
                        "min_x": result_min,
                        "max_x": result_max,
                    },

                    "reference": {
                        "center_x": reference["center_x"],
                        "min_x": reference_min,
                        "max_x": reference_max,
                    },

                    "unit": {
                        "center_x": unit["center_x"] if unit is not None else block_max_x,
                        "min_x": unit_min,
                        "max_x": unit_max,
                    },
                },

                "headers": [
                    {
                        "type": item["header_type"],
                        "text": item["text"],
                        "index": item["index"],
                        "center_x": item["center_x"],
                        "center_y": item["center_y"],
                        "confidence": item["confidence"],
                    }
                    for item in block
                ],
            }
        )

    return block_results


def parse_layout(items: list[dict]) -> dict:

    page_bounds = get_page_bounds(items)

    candidates = find_header_candidates(items)

    tolerance = calculate_header_y_tolerance(
        candidates
    )

    header_rows = group_header_rows(
        candidates,
        tolerance,
    )

    blocks = []

    header_row_debug = []

    for row_index, row in enumerate(
        header_rows,
        start=1,
    ):

        row_blocks = extract_blocks_from_header_row(
            row
        )

        header_row_debug.append(
            {
                "row_id": row_index,
                "center_y": round(
                    statistics.mean(
                        item["center_y"]
                        for item in row
                    ),
                    2,
                ),
                "candidate_count": len(row),
                "detected_block_count": len(
                    row_blocks
                ),
            }
        )

        # A second header row can be another page stacked below the first.
        # Horizontal block separators apply only within the same header row.
        row_geometry = calculate_block_geometry(row_blocks, page_bounds)
        next_header_top = (
            min(point[1] for item in header_rows[row_index]
                for point in item["bbox"])
            if row_index < len(header_rows) else None
        )
        for block in row_geometry:
            block["block_id"] = len(blocks) + 1
            if next_header_top is not None:
                block["body_end_y"] = float(next_header_top)
            blocks.append(block)

    return {
        "poc": "PoC 05-02",
        "stage": "paper_layout_detection",

        "source": str(
            INPUT_PATH.relative_to(PROJECT_ROOT)
        ).replace("\\", "/"),

        "page_bounds": page_bounds,

        "header_detection": {
            "candidate_count": len(candidates),
            "y_tolerance": tolerance,
            "header_row_count": len(header_rows),
            "header_rows": header_row_debug,
        },

        "table_block_count": len(blocks),

        "table_blocks": blocks,
    }


def print_layout(layout: dict) -> None:

    print("=" * 100)
    print("PoC 05-02｜Paper Report Layout Detection")
    print("=" * 100)

    header_info = layout["header_detection"]

    print(
        f"Header candidates : "
        f"{header_info['candidate_count']}"
    )

    print(
        f"Header rows       : "
        f"{header_info['header_row_count']}"
    )

    print(
        f"Y tolerance       : "
        f"{header_info['y_tolerance']}"
    )

    print(
        f"Table blocks      : "
        f"{layout['table_block_count']}"
    )

    print()

    for block in layout["table_blocks"]:

        print("-" * 100)

        print(
            f"Block {block['block_id']} | "
            f"x={block['x_range']['min']:.2f}"
            f" ~ "
            f"{block['x_range']['max']:.2f}"
            f" | "
            f"header_y="
            f"{block['header_center_y']:.2f}"
        )

        print()

        print(
            f"{'column':<12}"
            f"{'center_x':<14}"
            f"{'min_x':<14}"
            f"{'max_x':<14}"
        )

        print("-" * 54)

        for column_name in HEADER_ORDER:

            column = block["columns"][
                column_name
            ]

            print(
                f"{column_name:<12}"
                f"{column['center_x']:<14.2f}"
                f"{column['min_x']:<14.2f}"
                f"{column['max_x']:<14.2f}"
            )

        print()

    print("-" * 100)


def save_layout(layout: dict) -> None:

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            layout,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(
        f"Layout JSON saved: {OUTPUT_PATH}"
    )


def main():

    items = load_ocr_items()

    layout = parse_layout(items)

    print_layout(layout)

    save_layout(layout)


if __name__ == "__main__":
    main()
