import json
import re
import statistics
import unicodedata
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

from report_context import (
    output_path,
)


OCR_PATH = output_path(
    "_ocr.json"
)

LAYOUT_PATH = output_path(
    "_layout.json"
)

OUTPUT_PATH = output_path(
    "_rows.json"
)


# =========================================================
# 基础读取
# =========================================================

def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"未找到文件：{path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = text.strip()

    return text


# =========================================================
# Result Anchor
# =========================================================

RESULT_PATTERN = re.compile(
    r"""
    ^
    [↑↓]?
    (?:<=|>=|<|>|≤|≥)?
    -?
    \d+
    (?:\.\d+)?
    [↑↓]?
    $
    """,
    re.VERBOSE,
)


def is_result_anchor(text: str) -> bool:
    """
    判断 OCR 文本是否可以作为结果列 Row Anchor。

    支持：

    6.17
    119
    0.360

    ↑162
    64.7↓

    <0.5
    <=4.00
    ≤4.00

    不接受：

    3.50~9.50
    ↓4.30~5.80

    因为这些属于参考范围。
    """

    text = normalize_text(text)

    text = text.replace(" ", "")
    text = text.replace(",", "")

    # 参考范围不能作为 Result Anchor
    if "~" in text or "～" in text:
        return False

    return bool(RESULT_PATTERN.fullmatch(text))


# =========================================================
# Block item
# =========================================================

def item_in_x_range(
    item: dict,
    min_x: float,
    max_x: float,
) -> bool:

    x = float(item["center_x"])

    return min_x <= x < max_x


def get_block_items(
    ocr_items: list[dict],
    block: dict,
) -> list[dict]:
    """
    获取某个 Table Block 内表头以下的 OCR item。
    """

    min_x = block["x_range"]["min"]
    max_x = block["x_range"]["max"]

    body_start_y = block["body_start_y"]
    body_end_y = block.get("body_end_y")

    header_indexes = {
        header["index"]
        for header in block["headers"]
    }

    result = []

    for item in ocr_items:

        if item["index"] in header_indexes:
            continue

        if item["center_y"] <= body_start_y:
            continue

        if body_end_y is not None and item["center_y"] >= body_end_y:
            continue

        if not item_in_x_range(
            item,
            min_x,
            max_x,
        ):
            continue

        result.append(item)

    return result


# =========================================================
# Column
# =========================================================

def detect_column(
    item: dict,
    block: dict,
) -> str | None:

    x = float(item["center_x"])

    for column_name, column in block["columns"].items():

        if (
            column["min_x"]
            <= x
            < column["max_x"]
        ):
            return column_name

    return None


def group_items_by_column(
    block_items: list[dict],
    block: dict,
) -> dict[str, list[dict]]:

    result = {
        "metric": [],
        "result": [],
        "reference": [],
        "unit": [],
    }

    for item in block_items:

        column = detect_column(
            item,
            block,
        )

        if column:
            result[column].append(item)

    for column in result:
        result[column].sort(
            key=lambda x: (
                x["center_y"],
                x["center_x"],
            )
        )

    return result


# =========================================================
# Row tolerance
# =========================================================

def calculate_row_tolerance(
    block_items: list[dict],
) -> float:
    """
    根据当前 Block OCR 字高动态计算同行允许误差。

    当前纸质报告：
    OCR文字高度约 30~40px；
    相邻数据行约 50~60px。

    因此 tolerance 控制在约 20px 左右，
    既允许轻微倾斜，又避免串到下一行。
    """

    heights = [
        float(item["height"])
        for item in block_items
        if item.get("height")
    ]

    if not heights:
        return 20.0

    median_height = statistics.median(
        heights
    )

    tolerance = median_height * 0.60

    tolerance = max(
        14.0,
        min(
            tolerance,
            24.0,
        ),
    )

    return round(tolerance, 2)


# =========================================================
# Anchor detection
# =========================================================

def find_result_anchors(
    result_items: list[dict],
) -> list[dict]:

    anchors = []

    for item in result_items:

        if is_result_anchor(
            item["text"]
        ):
            anchors.append(item)

    anchors.sort(
        key=lambda x: x["center_y"]
    )

    return anchors


def recover_first_row_boundary_items(
    ocr_items: list[dict],
    block: dict,
    columns: dict[str, list[dict]],
    anchors: list[dict],
    tolerance: float,
) -> tuple[list[dict], list[dict]]:
    """仅为首行缺失的字段救回 bbox 穿过表体边界的 OCR item。"""
    if not anchors:
        return [], []

    first_anchor_y = float(anchors[0]["center_y"])
    next_anchor_y = (
        float(anchors[1]["center_y"])
        if len(anchors) > 1 else None
    )
    first_row_limit = (
        (first_anchor_y + next_anchor_y) / 2
        if next_anchor_y is not None else None
    )
    body_start_y = float(block["body_start_y"])
    header_indexes = {header["index"] for header in block["headers"]}

    # 已有首行候选的列不补偿，避免把相邻行文字再次拼入首行。
    missing_columns = {
        column
        for column in ("metric", "reference", "unit")
        if not any(
            abs(float(item["center_y"]) - first_anchor_y) <= tolerance
            and (
                first_row_limit is None
                or float(item["center_y"]) <= first_row_limit
            )
            for item in columns[column]
        )
    }

    recovered = []
    evidence = []
    for item in ocr_items:
        if item["index"] in header_indexes:
            continue
        center_y = float(item["center_y"])
        if center_y > body_start_y:
            continue
        if not item_in_x_range(
            item, block["x_range"]["min"], block["x_range"]["max"]
        ):
            continue
        column = detect_column(item, block)
        if column not in missing_columns:
            continue
        bbox_bottom = max(float(point[1]) for point in item["bbox"])
        distance = abs(center_y - first_anchor_y)
        if bbox_bottom <= body_start_y or distance > tolerance:
            continue

        recovered.append(item)
        event = {
            "ocr_index": item["index"],
            "column": column,
            "text": item["text"],
            "center_y": center_y,
            "bbox_bottom": bbox_bottom,
            "body_start_y": body_start_y,
            "first_anchor_y": first_anchor_y,
            "distance": round(distance, 2),
        }
        evidence.append(event)
        print(
            "[BODY BOUNDARY RECOVERY] "
            f"column={column} item={item['text']} index={item['index']} "
            f"center_y={center_y} bbox_bottom={bbox_bottom} "
            f"body_start_y={body_start_y} first_anchor={first_anchor_y} "
            f"distance={round(distance, 2)} decision=RECOVER"
        )

    return recovered, evidence


def estimate_column_y_offset(
    items: list[dict],
    anchors: list[dict],
    tolerance: float,
) -> dict:
    """从未分配的 item-anchor 位移中寻找有多行支持的集中簇。"""
    evidence = {
        "status": "NOT_APPLIED",
        "offset": 0.0,
        "support": 0,
        "supportedRows": 0,
        "dispersion": None,
        "secondSupport": 0,
        "reason": "INSUFFICIENT_EVIDENCE",
    }
    if len(items) < 4 or len(anchors) < 4:
        return evidence

    anchor_ys = [float(anchor["center_y"]) for anchor in anchors]
    row_spacing = statistics.median(
        later - earlier
        for earlier, later in zip(anchor_ys, anchor_ys[1:])
    )
    search_limit = min(tolerance, row_spacing * 0.55)
    cluster_radius = max(3.0, min(4.0, tolerance * 0.20))
    pairs = [
        (item["index"], row_index, float(item["center_y"]) - anchor_y)
        for item in items
        for row_index, anchor_y in enumerate(anchor_ys, start=1)
        if abs(float(item["center_y"]) - anchor_y) <= search_limit
    ]
    if not pairs:
        return evidence

    clusters = []
    for seed in sorted({offset for _, _, offset in pairs}):
        # 一个 item 在同一个 offset 簇内只贡献一次证据。
        by_item = {}
        for index, row_index, offset in sorted(
            pairs, key=lambda pair: (abs(pair[2] - seed), pair[1])
        ):
            if abs(offset - seed) <= cluster_radius:
                by_item.setdefault(index, (row_index, offset))
        if not by_item:
            continue
        offsets = [offset for _, offset in by_item.values()]
        center = statistics.median(offsets)
        clusters.append(
            {
                "offset": center,
                "support": len(by_item),
                "supportedRows": len({row for row, _ in by_item.values()}),
                "dispersion": statistics.median(
                    abs(offset - center) for offset in offsets
                ),
            }
        )

    clusters.sort(
        key=lambda cluster: (
            cluster["supportedRows"],
            cluster["support"],
            -cluster["dispersion"],
        ),
        reverse=True,
    )
    distinct = []
    for cluster in clusters:
        if all(
            abs(cluster["offset"] - other["offset"]) > 2 * cluster_radius
            for other in distinct
        ):
            distinct.append(cluster)
        if len(distinct) == 2:
            break

    best = distinct[0]
    second_rows = distinct[1]["supportedRows"] if len(distinct) > 1 else 0
    evidence.update(
        estimatedOffset=round(best["offset"], 2),
        support=best["support"],
        supportedRows=best["supportedRows"],
        dispersion=round(best["dispersion"], 2),
        secondSupport=second_rows,
        searchLimit=round(search_limit, 2),
    )

    minimum_support = max(4, (min(len(items), len(anchors)) + 1) // 2)
    if best["support"] < minimum_support or best["supportedRows"] < 4:
        return evidence
    if best["dispersion"] > cluster_radius:
        evidence["reason"] = "DISPERSED_EVIDENCE"
        return evidence
    if best["supportedRows"] - second_rows < max(
        2, (best["supportedRows"] + 4) // 5
    ):
        evidence["reason"] = "COMPETING_CLUSTERS"
        return evidence
    if abs(best["offset"]) < max(5.0, tolerance * 0.30):
        evidence["reason"] = "SMALL_OFFSET"
        return evidence

    def matched_count(offset: float) -> int:
        return sum(
            any(
                abs(float(item["center_y"]) - (anchor_y + offset))
                <= tolerance
                for anchor_y in anchor_ys
            )
            for item in items
        )

    if matched_count(best["offset"]) < matched_count(0.0) - max(
        1, len(items) // 10
    ):
        evidence["reason"] = "MATCH_COVERAGE_LOSS"
        return evidence

    evidence.update(
        status="APPLIED",
        offset=round(best["offset"], 2),
        reason="STRONG_OFFSET_CLUSTER",
    )
    return evidence


# =========================================================
# Row matching
# =========================================================

AMBIGUITY_DELTA = 2.0


def assign_items_to_anchors(
    items: list[dict],
    anchors: list[dict],
    tolerance: float,
    column: str,
    column_y_offset: float = 0.0,
    log_multi_candidates: bool = True,
) -> tuple[list[list[dict]], list[list[dict]]]:
    """
    每个 OCR item 只归属给容差内距离最近的一个 Result Anchor。
    几乎等距时保留歧义证据；距离相同则稳定选择上方 anchor。
    """
    assigned = [[] for _ in anchors]
    ambiguities = [[] for _ in anchors]

    for item in items:
        item_y = float(item["center_y"])
        candidates = [
            (
                abs(item_y - (float(anchor["center_y"]) + column_y_offset)),
                row_index,
                float(anchor["center_y"]),
            )
            for row_index, anchor in enumerate(anchors, start=1)
            if (
                abs(item_y - (float(anchor["center_y"]) + column_y_offset))
                <= tolerance
            )
        ]
        if not candidates:
            continue

        candidates.sort(key=lambda candidate: (candidate[0], candidate[1]))
        nearest_distance, nearest_row, _ = candidates[0]
        assigned[nearest_row - 1].append(item)

        if len(candidates) > 1:
            is_ambiguous = (
                candidates[1][0] - nearest_distance <= AMBIGUITY_DELTA
            )
            if log_multi_candidates:
                print(
                    f"[ROW ASSIGN] column={column} "
                    f"item={item['text']} index={item['index']} item_y={item_y} "
                    f"column_y_offset={column_y_offset}"
                )
                for distance, row_index, anchor_y in candidates:
                    print(
                        f"  row {row_index} | anchor={anchor_y} "
                        f"| expected_y={round(anchor_y + column_y_offset, 2)} "
                        f"| distance={round(distance, 2)}"
                    )
                print(
                    f"  assigned=row {nearest_row} "
                    f"| ambiguous={is_ambiguous}"
                )

            if is_ambiguous:
                ambiguities[nearest_row - 1].append(
                    {
                        "ocr_index": item["index"],
                        "text": item["text"],
                        "item_y": item_y,
                        "assigned_row": nearest_row,
                        "column_y_offset": column_y_offset,
                        "candidates": [
                            {
                                "row_index": row_index,
                                "anchor_y": anchor_y,
                                "expected_y": round(
                                    anchor_y + column_y_offset, 2
                                ),
                                "distance": round(distance, 2),
                            }
                            for distance, row_index, anchor_y in candidates
                        ],
                    }
                )

    return assigned, ambiguities


def recover_offset_first_row_items(
    ocr_items: list[dict],
    block: dict,
    columns: dict[str, list[dict]],
    anchors: list[dict],
    tolerance: float,
    column_offsets: dict[str, dict],
) -> tuple[list[dict], list[dict]]:
    """补偿后首行新出现空列时，沿用 bbox 跨界条件寻找该列文字。"""
    if not anchors:
        return [], []

    first_anchor_y = float(anchors[0]["center_y"])
    body_start_y = float(block["body_start_y"])
    header_indexes = {header["index"] for header in block["headers"]}
    included_indexes = {
        item["index"]
        for items in columns.values()
        for item in items
    }
    missing_columns = set()
    for column in ("metric", "reference", "unit"):
        offset_info = column_offsets[column]
        if offset_info["status"] != "APPLIED":
            continue
        assigned, _ = assign_items_to_anchors(
            columns[column], anchors, tolerance, column,
            offset_info["offset"], log_multi_candidates=False,
        )
        if not assigned[0]:
            missing_columns.add(column)

    recovered = []
    evidence = []
    for item in ocr_items:
        if item["index"] in header_indexes or item["index"] in included_indexes:
            continue
        center_y = float(item["center_y"])
        if center_y > body_start_y:
            continue
        if not item_in_x_range(
            item, block["x_range"]["min"], block["x_range"]["max"]
        ):
            continue
        column = detect_column(item, block)
        if column not in missing_columns:
            continue
        bbox_bottom = max(float(point[1]) for point in item["bbox"])
        offset = column_offsets[column]["offset"]
        raw_distance = abs(center_y - first_anchor_y)
        compensated_distance = abs(center_y - (first_anchor_y + offset))
        if (
            bbox_bottom <= body_start_y
            or raw_distance > tolerance
            or compensated_distance > tolerance
        ):
            continue

        recovered.append(item)
        event = {
            "ocr_index": item["index"],
            "column": column,
            "text": item["text"],
            "center_y": center_y,
            "bbox_bottom": bbox_bottom,
            "first_anchor_y": first_anchor_y,
            "column_y_offset": offset,
            "compensated_distance": round(compensated_distance, 2),
        }
        evidence.append(event)
        print(
            "[COLUMN OFFSET BOUNDARY] "
            f"column={column} item={item['text']} index={item['index']} "
            f"offset={offset} compensated_distance="
            f"{round(compensated_distance, 2)} decision=RECOVER"
        )

    return recovered, evidence


def merge_field_items(
    items: list[dict],
) -> tuple[str | None, list[int]]:
    """
    同一字段如果被 OCR 拆成多个框，
    暂时按空间顺序拼接。

    原始 OCR item index 始终保留。
    """

    if not items:
        return None, []

    sorted_items = sorted(
        items,
        key=lambda x: (
            x["center_y"],
            x["center_x"],
        ),
    )

    text = "".join(
        normalize_text(
            item["text"]
        )
        for item in sorted_items
    )

    indexes = [
        item["index"]
        for item in sorted_items
    ]

    return text, indexes


def build_rows(
    block: dict,
    column_items: dict,
    tolerance: float,
    column_offsets: dict[str, dict],
) -> list[dict]:

    anchors = find_result_anchors(
        column_items["result"]
    )

    assigned_items = {}
    assignment_ambiguities = {}
    for column in ("metric", "reference", "unit"):
        assigned_items[column], assignment_ambiguities[column] = (
            assign_items_to_anchors(
                column_items[column], anchors, tolerance, column,
                column_offsets[column]["offset"],
            )
        )

    rows = []

    for row_index, anchor in enumerate(
        anchors,
        start=1,
    ):

        anchor_y = float(
            anchor["center_y"]
        )

        metric_items = assigned_items["metric"][row_index - 1]
        reference_items = assigned_items["reference"][row_index - 1]
        unit_items = assigned_items["unit"][row_index - 1]

        metric_text, metric_indexes = (
            merge_field_items(metric_items)
        )

        reference_text, reference_indexes = (
            merge_field_items(reference_items)
        )

        unit_text, unit_indexes = (
            merge_field_items(unit_items)
        )

        # A combined reference/unit column can contain both fields in one
        # OCR box. Split only an explicit trailing unit token; preserve the
        # shared source index for evidence. Unsplit text stays unconfirmed.
        if block.get("combined_reference_unit") and reference_text:
            combined = re.fullmatch(
                r"(.+?)\s+([A-Za-zµμ][A-Za-z0-9µμ^]*/[A-Za-z][A-Za-z0-9]*)",
                reference_text,
            )
            if combined:
                reference_text = combined.group(1)
                unit_text = combined.group(2)
                unit_indexes = list(reference_indexes)

        missing_fields = []

        if not metric_text:
            missing_fields.append("metric")

        if not reference_text:
            missing_fields.append("reference")

        # unit 允许为空。
        #
        # 某些检验项目本身就是无单位指标，
        # 因此不能因为 unit 为空直接判断行异常。

        row = {
            "block_id": block["block_id"],
            "row_index": row_index,

            "anchor_y": anchor_y,

            "metric": metric_text,
            "result": normalize_text(
                anchor["text"]
            ),
            "reference": reference_text,
            "unit": unit_text,

            "ocr_indexes": {
                "metric": metric_indexes,
                "result": [
                    anchor["index"]
                ],
                "reference": reference_indexes,
                "unit": unit_indexes,
            },

            "confidence": {
                "result": anchor[
                    "confidence"
                ],
            },

            "missing_fields": missing_fields,
        }

        ambiguous_fields = {
            column: assignment_ambiguities[column][row_index - 1]
            for column in ("metric", "reference", "unit")
            if assignment_ambiguities[column][row_index - 1]
        }
        if ambiguous_fields:
            row["assignment_ambiguities"] = ambiguous_fields

        rows.append(row)

    return rows


def count_duplicate_assigned_indexes(rows: list[dict]) -> dict[str, int]:
    counts = {}
    for column in ("metric", "reference", "unit"):
        owners = {}
        for row in rows:
            for index in row["ocr_indexes"][column]:
                owners.setdefault(index, set()).add(row["row_index"])
        counts[column] = sum(len(row_indexes) > 1 for row_indexes in owners.values())
    return counts


# =========================================================
# Parse
# =========================================================

def parse_rows(
    ocr_data: dict,
    layout_data: dict,
) -> dict:

    ocr_items = ocr_data["items"]

    all_blocks = []

    all_rows = []

    for block in layout_data[
        "table_blocks"
    ]:

        block_items = get_block_items(
            ocr_items,
            block,
        )

        columns = group_items_by_column(
            block_items,
            block,
        )

        tolerance = calculate_row_tolerance(
            block_items
        )

        anchors = find_result_anchors(
            columns["result"]
        )

        recovered_items, recovery_evidence = (
            recover_first_row_boundary_items(
                ocr_items, block, columns, anchors, tolerance
            )
        )
        if recovered_items:
            columns = group_items_by_column(
                block_items + recovered_items, block
            )

        column_offsets = {
            column: estimate_column_y_offset(
                columns[column], anchors, tolerance
            )
            for column in ("metric", "reference", "unit")
        }

        offset_boundary_items, offset_boundary_evidence = (
            recover_offset_first_row_items(
                ocr_items, block, columns, anchors, tolerance,
                column_offsets,
            )
        )
        if offset_boundary_items:
            columns = group_items_by_column(
                block_items + recovered_items + offset_boundary_items,
                block,
            )

        rows = build_rows(
            block,
            columns,
            tolerance,
            column_offsets,
        )

        duplicate_indexes = count_duplicate_assigned_indexes(rows)

        block_result = {
            "block_id": block["block_id"],

            "row_tolerance": tolerance,

            "result_anchor_count": len(
                anchors
            ),

            "row_count": len(rows),

            "column_item_count": {
                column: len(items)
                for column, items
                in columns.items()
            },

            "duplicate_assigned_indexes": duplicate_indexes,

            "body_boundary_recovery": recovery_evidence,

            "column_offset_boundary_recovery": offset_boundary_evidence,

            "column_y_offsets": column_offsets,

            "rows": rows,
        }

        all_blocks.append(
            block_result
        )

        all_rows.extend(rows)

    return {
        "poc": "PoC 05-03",

        "stage":
            "paper_block_row_reconstruction",

        "source_ocr":
            "str(OCR_PATH)",

        "source_layout":
            "str(LAYOUT_PATH)",

        "block_count": len(all_blocks),

        "total_row_count": len(
            all_rows
        ),

        "body_boundary_recovery_count": sum(
            len(block["body_boundary_recovery"])
            for block in all_blocks
        ),

        "blocks": all_blocks,

        # 当前保持：
        #
        # Block 1 top -> bottom
        # Block 2 top -> bottom
        #
        # 暂不改变医院报告本身的数据顺序。
        "rows": all_rows,
    }


# =========================================================
# Print
# =========================================================

def print_rows(data: dict) -> None:

    print("=" * 120)
    print(
        "PoC 05-03｜Paper Block Row Reconstruction"
    )
    print("=" * 120)

    print(
        f"Blocks     : "
        f"{data['block_count']}"
    )

    print(
        f"Total rows : "
        f"{data['total_row_count']}"
    )

    print(
        "BODY_BOUNDARY_RECOVERY count = "
        f"{data['body_boundary_recovery_count']}"
    )

    print()

    for block in data["blocks"]:

        print("-" * 120)

        print(
            f"Block {block['block_id']}"
            f" | anchors="
            f"{block['result_anchor_count']}"
            f" | rows="
            f"{block['row_count']}"
            f" | tolerance="
            f"{block['row_tolerance']}"
        )

        print("COLUMN Y OFFSET")
        for column in ("metric", "reference", "unit"):
            info = block["column_y_offsets"][column]
            print(
                f"  {column}: status={info['status']} "
                f"offset={info['offset']:+.2f} "
                f"support={info['support']} "
                f"rows={info['supportedRows']} "
                f"dispersion={info['dispersion']} "
                f"second={info['secondSupport']} "
                f"reason={info['reason']}"
            )

        for column in ("metric", "reference", "unit"):
            print(
                f"Duplicate assigned {column} indexes : "
                f"{block['duplicate_assigned_indexes'][column]}"
            )

        print()

        print(
            f"{'#':<4}"
            f"{'Y':<10}"
            f"{'检验项目':<28}"
            f"{'结果':<14}"
            f"{'参考范围':<22}"
            f"{'单位':<12}"
            f"{'状态'}"
        )

        print("-" * 120)

        for row in block["rows"]:

            status = (
                "OK"
                if not row["missing_fields"]
                else
                "MISSING:"
                + ",".join(
                    row["missing_fields"]
                )
            )

            print(
                f"{row['row_index']:<4}"
                f"{row['anchor_y']:<10.2f}"
                f"{(row['metric'] or ''):<28}"
                f"{(row['result'] or ''):<14}"
                f"{(row['reference'] or ''):<22}"
                f"{(row['unit'] or ''):<12}"
                f"{status}"
            )

        print()

    print("-" * 120)


# =========================================================
# Save
# =========================================================

def save_result(data: dict) -> None:

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(
        f"Rows JSON saved: {OUTPUT_PATH}"
    )


def main():

    ocr_data = load_json(
        OCR_PATH
    )

    layout_data = load_json(
        LAYOUT_PATH
    )

    data = parse_rows(
        ocr_data,
        layout_data,
    )

    print_rows(data)

    save_result(data)


if __name__ == "__main__":
    main()
