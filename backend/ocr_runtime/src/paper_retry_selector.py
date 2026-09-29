# src/paper_retry_selector.py

import json
import re
import unicodedata
from pathlib import Path

from metric_matcher import (
    load_json,
    match_metric,
    build_unit_status,
    normalize_metric_name,
)

from result_parser import (
    structure_row,
)

from paper_result_parser import (
    adapt_paper_row,
)

from report_context import (
    get_report_id,
    output_path,
)


BASE_DIR = Path(__file__).resolve().parent.parent

REPORT_ID = get_report_id()

ROWS_PATH = output_path(
    "_rows.json"
)

LIBRARY_PATH = (
    BASE_DIR
    / "data"
    / "metric_library.json"
)

RETRY_DIR = (
    BASE_DIR
    / "output"
    / REPORT_ID
    / "paper_retry"
)

OUTPUT_PATH = (
    RETRY_DIR
    / "paper_retry_targets.json"
)


# =========================================================
# 基础
# =========================================================

def normalize_text(text):

    text = unicodedata.normalize(
        "NFKC",
        str(text or ""),
    )

    text = re.sub(
        r"\s+",
        "",
        text,
    )

    text = text.lstrip("*＊")

    return text.strip().lower()


def clean_metric_name(text):

    return normalize_text(text)


# =========================================================
# 标准库索引
# =========================================================

def build_metric_index(metrics):

    result = {}

    for metric in metrics:

        metric_id = metric.get(
            "metricId"
        )

        if metric_id:
            result[metric_id] = metric

    return result


def strong_names(metric):
    """
    一个标准指标的“强名称”：

    standardName
    abbreviation
    aliases

    如果 OCR 原名不属于这些名称，
    但 matcher 却 AUTO_MATCHED，
    说明自动匹配主要依赖 FUZZY / 残缺名称，
    应视为 HIGH_RISK_AUTO。
    """

    names = []

    standard_name = metric.get(
        "standardName"
    )

    if standard_name:
        names.append(
            standard_name
        )

    abbreviation = metric.get(
        "abbreviation"
    )

    if abbreviation:
        names.append(
            abbreviation
        )

    names.extend(
        metric.get(
            "aliases",
            []
        )
    )

    return {
        normalize_metric_name(name)
        for name in names
        if name
    }


# =========================================================
# 从 matcher 结果中尽量找到 metricId
#
# 兼容当前 PoC 演进过程中可能存在的不同结构。
# =========================================================

def recursive_find_metric_id(value):

    if isinstance(value, dict):

        for key in (
            "metricId",
            "metric_id",
            "id",
        ):

            candidate = value.get(
                key
            )

            if isinstance(
                candidate,
                str,
            ):
                return candidate

        for child in value.values():

            found = (
                recursive_find_metric_id(
                    child
                )
            )

            if found:
                return found

    elif isinstance(value, list):

        for child in value:

            found = (
                recursive_find_metric_id(
                    child
                )
            )

            if found:
                return found

    return None


def get_match_type(match):
    """
    只作为 fallback。

    主逻辑尽量不依赖 matcher 内部字段名。
    """

    for key in (
        "matchType",
        "match_type",
        "method",
        "type",
    ):

        value = match.get(
            key
        )

        if isinstance(
            value,
            str,
        ):
            return value.upper()

    return None


# =========================================================
# HIGH RISK AUTO
# =========================================================

def is_high_risk_auto(
    raw_metric,
    match,
    metric_index,
):

    if (
        match.get("status")
        != "AUTO_MATCHED"
    ):
        return False

    metric_id = (
        recursive_find_metric_id(
            match
        )
    )

    # -----------------------------------------------------
    # 优先通过标准库判断：
    #
    # OCR原始名称是否属于该指标的
    # 标准名/正规Alias/缩写。
    #
    # 如果不是但却 AUTO，
    # 则说明存在 fuzzy / residual 风险。
    # -----------------------------------------------------

    if (
        metric_id
        and metric_id in metric_index
    ):
        if get_match_type(match) not in (
            "EXACT",
            "ALIAS",
            "ABBREVIATION",
        ):
            return True

        raw = normalize_metric_name(
            clean_metric_name(raw_metric)
        )

        # 与 Matcher 使用同一名称规范化规则，
        # 但只有唯一指向当前 metricId 才解除高风险标记。
        owners = {
            candidate_id
            for candidate_id, metric
            in metric_index.items()
            if raw in strong_names(metric)
        }

        return owners != {metric_id}

    # -----------------------------------------------------
    # 找不到 metricId 时，
    # fallback 到 matchType
    # -----------------------------------------------------

    match_type = get_match_type(
        match
    )

    if match_type == "FUZZY":
        return True

    return False


# =========================================================
# Target
# =========================================================

def make_target(
    row,
    field,
    reason,
    extra=None,
):

    block_id = row.get(
        "block_id"
    )

    row_index = row.get(
        "row_index"
    )

    target_id = (
        f"b{block_id}_"
        f"r{row_index}_"
        f"{field}"
    )

    target = {
        "targetId":
            target_id,

        "blockId":
            block_id,

        "rowIndex":
            row_index,

        "rowMetric":
            row.get(
                "metric"
            ),

        "field":
            field,

        "originalText":
            row.get(
                field
            ),

        "reason":
            reason,
    }

    if extra:
        target.update(
            extra
        )

    return target


def add_target(
    target_map,
    target,
):
    """
    同一行同一字段只生成一次 Retry。

    如果多个规则同时命中，
    reason 合并保存。
    """

    key = (
        target["blockId"],
        target["rowIndex"],
        target["field"],
    )

    if key not in target_map:

        target[
            "reasons"
        ] = [
            target["reason"]
        ]

        target_map[key] = target

        return

    existing = target_map[
        key
    ]

    reason = target[
        "reason"
    ]

    if (
        reason
        not in existing["reasons"]
    ):

        existing[
            "reasons"
        ].append(
            reason
        )


# =========================================================
# Selector
# =========================================================

def select_retry_targets(
    rows,
    metrics,
):

    metric_index = (
        build_metric_index(
            metrics
        )
    )

    target_map = {}

    diagnostics = []

    for row in rows:

        raw_metric = (
            row.get(
                "metric",
                ""
            )
        )

        raw_unit = (
            row.get(
                "unit",
                ""
            )
        )

        match_input = (
            clean_metric_name(
                raw_metric
            )
        )

        # =================================================
        # Metric Matcher
        # =================================================

        match = match_metric(
            match_input,
            raw_unit,
            metrics,
        )

        match_status = (
            match.get(
                "status"
            )
        )

        # -------------------------------------------------
        # 1. REVIEW / UNMATCHED
        # -------------------------------------------------

        if match_status in (
            "REVIEW",
            "UNMATCHED",
        ):

            add_target(
                target_map,
                make_target(
                    row,
                    field="metric",
                    reason=(
                        f"METRIC_{match_status}"
                    ),
                    extra={
                        "matchStatus":
                            match_status,
                    },
                ),
            )

        # -------------------------------------------------
        # 2. 高风险 AUTO
        #
        # 例如：
        #
        # 巴细胞绝对值
        # → 淋巴细胞绝对值
        #
        # 即使 matcher AUTO，
        # 也要进入二次 OCR。
        # -------------------------------------------------

        elif is_high_risk_auto(
            raw_metric,
            match,
            metric_index,
        ):

            add_target(
                target_map,
                make_target(
                    row,
                    field="metric",
                    reason=
                        "HIGH_RISK_AUTO",
                    extra={
                        "matchStatus":
                            match_status,
                    },
                ),
            )

        # =================================================
        # Unit Validation
        # =================================================

        unit_status = (
            build_unit_status(
                match
            )
        )

        unit_code = (
            unit_status.get(
                "unitStatus"
            )
        )

        # -------------------------------------------------
        # 单位存在但校验失败：
        # 进入 Paddle OCR。
        #
        # 例如：
        #
        # 109/L
        #
        # -------------------------------------------------

        if (
            unit_code != "MATCH"
            and raw_unit not in (
                None,
                "",
            )
        ):

            add_target(
                target_map,
                make_target(
                    row,
                    field="unit",
                    reason=
                        "UNIT_WARNING_VISIBLE",
                    extra={
                        "unitStatus":
                            unit_code,
                    },
                ),
            )

        # -------------------------------------------------
        # 单位为空：
        #
        # 不做 Paddle Retry。
        #
        # 后续交给 Unit Resolver。
        # -------------------------------------------------

        unit_missing = (
            raw_unit in (
                None,
                "",
            )
            and unit_code != "MATCH"
        )

        # =================================================
        # Result Validation
        # =================================================

        adapted = adapt_paper_row(
            row
        )

        structured = structure_row(
            adapted
        )

        validation_status = (
            structured.get(
                "abnormal",
                {},
            ).get("validationStatus")
        )

        need_confirmation = (
            structured.get(
                "confirmation",
                {},
            ).get("needConfirmation")
        )

        # -------------------------------------------------
        # 数值冲突：
        #
        # result + reference 都重新识别。
        #
        # 不根据业务逻辑猜哪一个错。
        # -------------------------------------------------

        if (
            validation_status
            == "CONFLICT"
        ):

            add_target(
                target_map,
                make_target(
                    row,
                    field="result",
                    reason=
                        "RESULT_CONFLICT",
                ),
            )

            if row.get(
                "reference"
            ):

                add_target(
                    target_map,
                    make_target(
                        row,
                        field="reference",
                        reason=
                            "REFERENCE_CONFLICT",
                    ),
                )

        # -------------------------------------------------
        # Result Parser 明确要求确认，
        # 但不是 conflict 时：
        # 先重新识别 result。
        # -------------------------------------------------

        elif need_confirmation:

            add_target(
                target_map,
                make_target(
                    row,
                    field="result",
                    reason=
                        "RESULT_NEEDS_CONFIRMATION",
                ),
            )

        diagnostics.append(
            {
                "blockId":
                    row.get(
                        "block_id"
                    ),

                "rowIndex":
                    row.get(
                        "row_index"
                    ),

                "metric":
                    raw_metric,

                "metricMatchStatus":
                    match_status,

                "highRiskAuto":
                    is_high_risk_auto(
                        raw_metric,
                        match,
                        metric_index,
                    ),

                "unitStatus":
                    unit_code,

                "unitMissing":
                    unit_missing,

                "resultValidationStatus":
                    validation_status,

                "resultNeedConfirmation":
                    bool(
                        need_confirmation
                    ),
            }
        )

    targets = list(
        target_map.values()
    )

    targets.sort(
        key=lambda x: (
            x["blockId"],
            x["rowIndex"],
            x["field"],
        )
    )

    return (
        targets,
        diagnostics,
    )


# =========================================================
# Main
# =========================================================

def main():

    row_data = load_json(
        ROWS_PATH
    )

    metrics = load_json(
        LIBRARY_PATH
    )

    targets, diagnostics = (
        select_retry_targets(
            row_data.get(
                "rows",
                []
            ),
            metrics,
        )
    )

    reason_counts = {}

    for target in targets:

        for reason in target.get(
            "reasons",
            []
        ):

            reason_counts[
                reason
            ] = (
                reason_counts.get(
                    reason,
                    0,
                )
                + 1
            )

    output = {
        "poc":
            "PoC 06-02A",

        "stage":
            "dynamic_retry_target_selection",

        "rules": {
            "metricReview":
                True,

            "metricUnmatched":
                True,

            "highRiskAuto":
                (
                    "AUTO match but OCR metric "
                    "is not a strong standard name, "
                    "alias or abbreviation"
                ),

            "visibleUnitWarning":
                True,

            "missingUnitPaddleRetry":
                False,

            "resultConflict":
                True,
        },

        "targetCount":
            len(targets),

        "reasonCounts":
            reason_counts,

        "targets":
            targets,

        "diagnostics":
            diagnostics,
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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
    print("=" * 120)
    print(
        "PoC 06-02A｜Dynamic Retry Target Selector"
    )
    print("=" * 120)
    print()

    print(
        f"Rows           : "
        f"{len(row_data.get('rows', []))}"
    )

    print(
        f"Retry targets  : "
        f"{len(targets)}"
    )

    print()

    for target in targets:

        print(
            f"{target['targetId']:<20}"
            f" | "
            f"{target['field']:<10}"
            f" | "
            f"{str(target['originalText']):<25}"
            f" | "
            f"{','.join(target['reasons'])}"
        )

    print()

    print("Reason summary:")

    for (
        reason,
        count,
    ) in reason_counts.items():

        print(
            f"  {reason:<30}"
            f"{count}"
        )

    print()

    print(
        f"Saved: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
