# src/paper_final_unit_apply.py

import json
from pathlib import Path

from report_context import (
    output_path,
)


BASE_DIR = Path(__file__).resolve().parent.parent


# =========================================================
# 输入 / 输出
# =========================================================

FINAL_PATH = output_path(
    "_final.json"
)

UNIT_RESOLVED_PATH = output_path(
    "_unit_resolved.json"
)

OUTPUT_PATH = output_path(
    "_final_unit_resolved.json"
)


# =========================================================
# FINAL 可接受单位状态
# =========================================================

ACCEPTED_UNIT_STATUSES = {
    "UNIT_MATCH",
    "UNIT_NORMALIZED",
    "UNIT_SEMANTICALLY_RESOLVED",
}


# =========================================================
# 基础
# =========================================================

def load_json(path):

    if not path.exists():
        raise FileNotFoundError(
            f"未找到文件：{path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def normalize_metric_name(name):
    """
    仅用于指标名称关联。

    去除纸质报告版式中的：
    * / ＊
    """

    if not name:
        return ""

    text = str(name).strip()

    while text.startswith(
        ("*", "＊")
    ):
        text = text[1:].strip()

    return text


# =========================================================
# Unit Resolution Map
# =========================================================

def build_unit_resolution_map(
    unit_data,
):
    """
    使用 standardName 建立映射：

        红细胞比积
        →
        UNIT_SEMANTICALLY_RESOLVED

    当前阶段只使用已经通过 PoC 05-06A
    验证的单位解析结果。
    """

    result = {}

    for item in unit_data.get(
        "results",
        []
    ):

        standard_name = (
            normalize_metric_name(
                item.get(
                    "standardName"
                )
            )
        )

        if not standard_name:
            continue

        result[
            standard_name
        ] = item

    return result


# =========================================================
# 获取有效单位状态
# =========================================================

def get_effective_unit_resolution(
    row,
    unit_resolution_map,
):
    """
    优先级：

    1. PoC 05-06 Unit Resolver
    2. 原有 unitValidation

    不修改 raw OCR unit。
    """

    resolved = row.get(
        "resolved",
        {}
    )

    metric_name = (
        normalize_metric_name(
            resolved.get(
                "metric"
            )
        )
    )

    # -----------------------------------------------------
    # 05-06 Unit Resolver 有结果
    # -----------------------------------------------------

    semantic_result = (
        unit_resolution_map.get(
            metric_name
        )
    )

    if semantic_result:

        resolution = (
            semantic_result.get(
                "resolution",
                {}
            )
        )

        return {
            "source":
                "UNIT_RESOLVER",

            "status":
                resolution.get(
                    "status"
                ),

            "rawUnit":
                semantic_result.get(
                    "rawUnit"
                ),

            "normalizedUnit":
                resolution.get(
                    "normalizedUnit"
                ),

            "reason":
                resolution.get(
                    "reason"
                ),

            "evidence":
                resolution.get(
                    "evidence"
                ),

            "metricId":
                semantic_result.get(
                    "metricId"
                ),

            "standardName":
                semantic_result.get(
                    "standardName"
                ),
        }

    # -----------------------------------------------------
    # 其他指标沿用原单位校验
    # -----------------------------------------------------

    old_validation = row.get(
        "unitValidation",
        {}
    )

    old_status = (
        old_validation.get(
            "unitStatus"
        )
    )

    if old_status == "MATCH":

        return {
            "source":
                "ORIGINAL_UNIT_VALIDATION",

            "status":
                "UNIT_MATCH",

            "rawUnit":
                resolved.get(
                    "unit"
                ),

            "normalizedUnit":
                resolved.get(
                    "unit"
                ),

            "reason":
                "ORIGINAL_UNIT_MATCH",
        }

    return {
        "source":
            "ORIGINAL_UNIT_VALIDATION",

        "status":
            "UNIT_REVIEW",

        "rawUnit":
            resolved.get(
                "unit"
            ),

        "normalizedUnit":
            None,

        "reason":
            f"ORIGINAL_UNIT_{old_status}",
    }


# =========================================================
# FINAL Decision
# =========================================================

def calculate_final_status(
    row,
    effective_unit,
):
    """
    PoC 05-06 最终规则。

    FINAL_AUTO：

    1. 指标必须 AUTO_MATCHED
    2. 单位状态属于：
       UNIT_MATCH
       UNIT_NORMALIZED
       UNIT_SEMANTICALLY_RESOLVED
    3. 数值校验无 CONFLICT
    4. Result Parser 不要求人工确认
    5. 已触发 OCR Retry 全部解决
    """

    reasons = []

    # -----------------------------------------------------
    # 1. Metric Match
    # -----------------------------------------------------

    metric_match = row.get(
        "metricMatch",
        {}
    )

    if (
        metric_match.get(
            "status"
        )
        != "AUTO_MATCHED"
    ):

        reasons.append(
            "METRIC_NOT_AUTO_MATCHED"
        )

    # -----------------------------------------------------
    # 2. Unit
    # -----------------------------------------------------

    unit_status = (
        effective_unit.get(
            "status"
        )
    )

    if (
        unit_status
        not in ACCEPTED_UNIT_STATUSES
    ):

        reasons.append(
            f"UNIT_{unit_status}"
        )

    # -----------------------------------------------------
    # 3. Result Validation
    # -----------------------------------------------------

    result_validation = row.get(
        "resultValidation",
        {}
    )

    if (
        result_validation.get(
            "abnormal",
            {},
        ).get("validationStatus")
        == "CONFLICT"
    ):

        reasons.append(
            "RESULT_CONFLICT"
        )

    if result_validation.get(
        "confirmation",
        {},
    ).get("needConfirmation"):

        reasons.append(
            "RESULT_NEEDS_CONFIRMATION"
        )

    # -----------------------------------------------------
# 4. OCR Retry
#
# 注意：
#
# OCR 层 unresolved 不一定意味着 FINAL unresolved。
#
# 例如：
#
# Rapid / Paddle：
#     109/L
#
# OCR 无法判断是否是 10^9/L，
# 所以在 PoC 05-05 中是 unresolved。
#
# 但 PoC 05-06 Unit Resolver 可以结合：
#
#     当前标准指标
#     +
#     唯一预期单位
#     +
#     上标扁平化规则
#
# 将其可靠恢复为：
#
#     10^9/L
#
# 此时旧的 unit OCR unresolved
# 已被上层语义解析解决，
# 不应继续阻止 FINAL_AUTO。
# -----------------------------------------------------

    retry = row.get(
        "retry",
        {}
    )

    unresolved = retry.get(
        "unresolved",
        []
    )

    effective_unresolved = []

    for issue in unresolved:

        field = issue.get(
            "field"
        )

        # 单位 OCR 问题已被 Unit Resolver 解决。
        if (
            field == "unit"
            and effective_unit.get(
                "status"
            ) in ACCEPTED_UNIT_STATUSES
        ):
            # 保留原 retry 记录用于审计，但不再影响 FINAL 状态。
            continue

        effective_unresolved.append(
            issue
        )

    if effective_unresolved:

        reasons.append(
            "OCR_RETRY_UNRESOLVED"
        )

    # -----------------------------------------------------
    # FINAL
    # -----------------------------------------------------

    if reasons:

        return (
            "FINAL_REVIEW",
            reasons,
        )

    return (
        "FINAL_AUTO",
        [],
    )


# =========================================================
# Main
# =========================================================

def main():

    final_data = load_json(
        FINAL_PATH
    )

    unit_data = load_json(
        UNIT_RESOLVED_PATH
    )

    unit_resolution_map = (
        build_unit_resolution_map(
            unit_data
        )
    )

    print()
    print("=" * 120)
    print(
        "PoC 05-06B｜Final Validation With Unit Semantics"
    )
    print("=" * 120)
    print()

    print(
        f"Unit semantic resolutions loaded: "
        f"{len(unit_resolution_map)}"
    )

    print()

    output_rows = []

    stats = {
        "total": 0,

        "finalAuto": 0,
        "finalReview": 0,

        "unitMatch": 0,
        "unitNormalized": 0,
        "unitSemanticallyResolved": 0,
        "unitReview": 0,
    }

    review_rows = []

    # =====================================================
    # 逐行重新执行 FINAL
    # =====================================================

    for row in final_data.get(
        "rows",
        []
    ):

        stats["total"] += 1

        # -------------------------------------------------
        # 有效单位状态
        # -------------------------------------------------

        effective_unit = (
            get_effective_unit_resolution(
                row,
                unit_resolution_map,
            )
        )

        unit_status = (
            effective_unit.get(
                "status"
            )
        )

        # -------------------------------------------------
        # Unit Stats
        # -------------------------------------------------

        if unit_status == "UNIT_MATCH":

            stats[
                "unitMatch"
            ] += 1

        elif (
            unit_status
            == "UNIT_NORMALIZED"
        ):

            stats[
                "unitNormalized"
            ] += 1

        elif (
            unit_status
            == "UNIT_SEMANTICALLY_RESOLVED"
        ):

            stats[
                "unitSemanticallyResolved"
            ] += 1

        else:

            stats[
                "unitReview"
            ] += 1

        # -------------------------------------------------
        # FINAL
        # -------------------------------------------------

        (
            final_status,
            final_reasons,
        ) = calculate_final_status(
            row,
            effective_unit,
        )

        if (
            final_status
            == "FINAL_AUTO"
        ):

            stats[
                "finalAuto"
            ] += 1

        else:

            stats[
                "finalReview"
            ] += 1

        # -------------------------------------------------
        # 输出 Row
        # -------------------------------------------------

        output_row = dict(
            row
        )

        # 保留 05-05 的最终状态
        output_row[
            "previousFinalStatus"
        ] = row.get(
            "finalStatus"
        )

        output_row[
            "previousFinalReasons"
        ] = row.get(
            "finalReasons",
            []
        )

        # 新增统一单位解析结果
        output_row[
            "effectiveUnit"
        ] = effective_unit

        # 覆盖为 05-06 最终判定
        output_row[
            "finalStatus"
        ] = final_status

        output_row[
            "finalReasons"
        ] = final_reasons

        output_rows.append(
            output_row
        )

        # -------------------------------------------------
        # Terminal
        # -------------------------------------------------

        resolved = row.get(
            "resolved",
            {}
        )

        metric_name = (
            normalize_metric_name(
                resolved.get(
                    "metric"
                )
            )
        )

        raw_unit = resolved.get(
            "unit"
        )

        normalized_unit = (
            effective_unit.get(
                "normalizedUnit"
            )
        )

        print(
            f"{metric_name:<24}"
            f" | rawUnit="
            f"{str(raw_unit):<10}"
            f" | "
            f"{unit_status:<30}"
            f" | normalized="
            f"{str(normalized_unit):<10}"
            f" | "
            f"{final_status}"
        )

        if final_reasons:

            print(
                "    └─ "
                + ", ".join(
                    final_reasons
                )
            )

            review_rows.append(
                {
                    "metric":
                        metric_name,

                    "finalReasons":
                        final_reasons,
                }
            )

    # =====================================================
    # 自动通过率
    # =====================================================

    if stats["total"]:

        rate = (
            stats["finalAuto"]
            / stats["total"]
            * 100
        )

    else:

        rate = 0

    stats[
        "finalAutoRate"
    ] = round(
        rate,
        1,
    )

    # =====================================================
    # 输出 JSON
    # =====================================================

    output = {
        "poc":
            "PoC 05-06B",

        "stage":
            "paper_final_validation_with_unit_semantics",

        "unitAcceptedStatuses": [
            "UNIT_MATCH",
            "UNIT_NORMALIZED",
            "UNIT_SEMANTICALLY_RESOLVED",
        ],

        "summary":
            stats,

        "reviewRows":
            review_rows,

        "rows":
            output_rows,
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

    # =====================================================
    # Summary
    # =====================================================

    print()
    print("=" * 120)
    print(
        "FINAL SUMMARY｜PoC 05-06B"
    )
    print("=" * 120)

    print(
        f"总指标：                    "
        f"{stats['total']}"
    )

    print()

    print(
        f"UNIT_MATCH：                "
        f"{stats['unitMatch']}"
    )

    print(
        f"UNIT_NORMALIZED：           "
        f"{stats['unitNormalized']}"
    )

    print(
        f"UNIT_SEMANTICALLY_RESOLVED："
        f"{stats['unitSemanticallyResolved']}"
    )

    print(
        f"UNIT_REVIEW：               "
        f"{stats['unitReview']}"
    )

    print()

    print(
        f"FINAL_AUTO：                "
        f"{stats['finalAuto']}"
    )

    print(
        f"FINAL_REVIEW：              "
        f"{stats['finalReview']}"
    )

    print(
        f"最终自动通过率：             "
        f"{stats['finalAutoRate']}%"
    )

    print()

    if review_rows:

        print("剩余 FINAL_REVIEW：")

        for item in review_rows:

            print(
                f"  - "
                f"{item['metric']}"
                f" | "
                f"{', '.join(item['finalReasons'])}"
            )

    print()

    print(
        f"Output: "
        f"{OUTPUT_PATH}"
    )


# =========================================================
# Entry
# =========================================================

if __name__ == "__main__":
    main()
