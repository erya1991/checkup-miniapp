# src/paper_retry_apply.py

import json
from pathlib import Path

from metric_matcher import (
    load_json,
    match_metric,
    build_unit_status,
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


# =========================================================
# 路径
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
REPORT_ID = get_report_id()


# 原始双栏行重建结果
ROWS_PATH = output_path(
    "_rows.json"
)


# 标准指标库
LIBRARY_PATH = (
    BASE_DIR
    / "data"
    / "metric_library.json"
)


# ---------------------------------------------------------
# Round1
#
# 第一轮 PaddleOCR 局部复核结果
# ---------------------------------------------------------

ROUND1_RETRY_DIR = (
    BASE_DIR
    / "output"
    / REPORT_ID
    / "paper_retry"
)

RETRY_PATH = (
    ROUND1_RETRY_DIR
    / "paper_paddle_retry.json"
)


# ---------------------------------------------------------
# Round2
#
# 第二轮：
# 完整单元格裁剪
# +
# OCR Consensus
# +
# Metric Library Evidence Fusion
#
# 同一个字段存在 Round2 时，
# Round2 优先于 Round1。
# ---------------------------------------------------------

ROUND2_RETRY_DIR = (
    BASE_DIR
    / "output"
    / REPORT_ID
    / "paper_retry_round2"
)

ROUND2_RETRY_PATH = (
    ROUND2_RETRY_DIR
    / "paper_retry_round2_resolved.json"
)


# 最终结果
OUTPUT_PATH = output_path(
    "_final.json"
)


# =========================================================
# Metric name preprocess
# =========================================================

def clean_metric_for_match(text):
    """
    与 paper_metric_matcher.py 保持一致。

    纸质报告中：

        *红细胞比积
        *平均红细胞体积

    '*' 表示报告版式中的省内互认标记，
    不是指标名称本身。

    因此：

        原始 OCR：
        *红细胞比积

        匹配输入：
        红细胞比积

    原始 OCR 数据仍然保留，
    这里只处理传给 metric matcher 的文本。
    """

    if not text:
        return ""

    text = str(text).strip()

    while text.startswith(
        ("*", "＊")
    ):
        text = text[1:].strip()

    return text


# =========================================================
# Retry Map
# =========================================================

def retry_key(
    block_id,
    row_index,
    field,
):
    """
    用：

        block_id
        row_index
        field

    唯一定位一个需要二次 OCR 的字段。
    """

    return (
        block_id,
        row_index,
        field,
    )


def build_retry_map(
    retry_data,
):
    """
    将 Paddle Retry JSON 转换成快速查询 Map。

    key:

        (
            blockId,
            rowIndex,
            field
        )
    """

    retry_map = {}

    for item in retry_data.get(
        "results",
        []
    ):

        key = retry_key(
            item.get("blockId"),
            item.get("rowIndex"),
            item.get("field"),
        )

        retry_map[key] = item

    return retry_map


# =========================================================
# Apply Retry
# =========================================================

def apply_retry(
    row,
    retry_map,
):
    """
    将已经通过 OCR + 业务证据验证的修正候选，
    应用到当前 row。

    非 ACCEPTED_CANDIDATE：
    不修改原始值，
    进入 unresolved。

    重要原则：

    原始 OCR 永远保留。
    """

    updated = dict(row)

    applied = []
    unresolved = []

    for field in (
        "metric",
        "result",
        "reference",
        "unit",
    ):

        key = retry_key(
            row.get("block_id"),
            row.get("row_index"),
            field,
        )

        retry = retry_map.get(
            key
        )

        if not retry:
            continue

        decision = retry.get(
            "decision"
        )

        candidate = retry.get(
            "candidate"
        )

        # -------------------------------------------------
        # 自动采用
        # -------------------------------------------------

        if (
            decision
            == "ACCEPTED_CANDIDATE"
            and candidate
        ):

            old_value = updated.get(
                field
            )

            new_value = candidate

            # A unit crop can include the neighbouring reference text in a
            # combined column. Never replace an existing unit with a longer
            # numeric phrase ending in that same unit.
            old_unit = str(old_value or "").strip()
            new_unit = str(new_value).strip()
            if field == "unit" and old_unit and new_unit.endswith(old_unit):
                prefix = new_unit[:-len(old_unit)].strip()
                if prefix and any(char.isdigit() for char in prefix):
                    unresolved.append({
                        "field": field,
                        "original": old_value,
                        "candidate": candidate,
                        "reason": "UNIT_CANDIDATE_CONTAINS_REFERENCE",
                    })
                    continue

            updated[field] = (
                new_value
            )

            applied.append(
                {
                    "field":
                        field,

                    "from":
                        old_value,

                    "to":
                        new_value,

                    "reason":
                        retry.get(
                            "reason"
                        ),
                }
            )

        # -------------------------------------------------
        # 二次 OCR 仍未解决
        # -------------------------------------------------

        else:

            unresolved.append(
                {
                    "field":
                        field,

                    "original":
                        retry.get(
                            "originalText"
                        ),

                    "candidate":
                        candidate,

                    "reason":
                        retry.get(
                            "reason"
                        ),
                }
            )

    return (
        updated,
        applied,
        unresolved,
    )


# =========================================================
# Result Validation
# =========================================================

def get_validation_status(
    structured,
):
    """
    读取 result_parser 的异常校验结构。
    """

    return structured.get(
        "abnormal",
        {},
    ).get("validationStatus")


# =========================================================
# FINAL Status
# =========================================================

def final_decision(
    match,
    unit_status,
    structured,
    unresolved_retry,
):
    """
    FINAL_AUTO 必须同时满足：

    1.
    metricMatch = AUTO_MATCHED

    2.
    unitStatus = MATCH

    3.
    resultValidation != CONFLICT

    4.
    result parser 不要求人工确认

    5.
    已触发的 OCR Retry 全部解决

    任意条件不满足：

        FINAL_REVIEW
    """

    reasons = []

    # -----------------------------------------------------
    # 1. 标准指标匹配
    # -----------------------------------------------------

    metric_status = (
        match.get("status")
    )

    if (
        metric_status
        != "AUTO_MATCHED"
    ):
        reasons.append(
            "METRIC_NOT_AUTO_MATCHED"
        )

    # -----------------------------------------------------
    # 2. 单位校验
    #
    # 当前 PoC 保持严格策略：
    #
    # expected unit 存在，
    # 但 OCR 单位错误/缺失，
    # 均不能 FINAL_AUTO。
    # -----------------------------------------------------

    unit_code = unit_status.get(
        "unitStatus"
    )

    if unit_code != "MATCH":

        reasons.append(
            f"UNIT_{unit_code}"
        )

    # -----------------------------------------------------
    # 3. 数值 / 参考范围业务冲突
    # -----------------------------------------------------

    validation_status = (
        get_validation_status(
            structured
        )
    )

    if (
        validation_status
        == "CONFLICT"
    ):
        reasons.append(
            "RESULT_CONFLICT"
        )

    # -----------------------------------------------------
    # 4. Result Parser 是否要求确认
    # -----------------------------------------------------

    if structured.get(
        "confirmation",
        {},
    ).get("needConfirmation"):
        reasons.append(
            "RESULT_NEEDS_CONFIRMATION"
        )

    # -----------------------------------------------------
    # 5. 已触发 Retry，但仍无法确认
    # -----------------------------------------------------

    if unresolved_retry:

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

    # =====================================================
    # 1. 读取基础数据
    # =====================================================

    row_data = load_json(
        ROWS_PATH
    )

    metrics = load_json(
        LIBRARY_PATH
    )

    # =====================================================
    # 2. Round1 Paddle Retry
    # =====================================================

    if not RETRY_PATH.exists():

        raise FileNotFoundError(
            "未找到 Round1 Retry 文件：\n"
            f"{RETRY_PATH}\n"
            "\n"
            "请先执行 paper_paddle_retry.py"
        )

    retry_data = load_json(
        RETRY_PATH
    )

    retry_map = build_retry_map(
        retry_data
    )

    print(
        f"Round1 retry loaded: "
        f"{len(retry_map)}"
    )

    # =====================================================
    # 3. Round2 Evidence Fusion
    #
    # Round2 覆盖 Round1。
    # =====================================================

    if ROUND2_RETRY_PATH.exists():

        round2_data = load_json(
            ROUND2_RETRY_PATH
        )

        round2_map = build_retry_map(
            round2_data
        )

        retry_map.update(
            round2_map
        )

        print(
            f"Round2 retry loaded: "
            f"{len(round2_map)}"
        )

    else:

        print(
            "Round2 retry file not found."
        )

        print(
            "Only Round1 retry results "
            "will be used."
        )

    # =====================================================
    # 4. 初始化统计
    # =====================================================

    final_rows = []

    stats = {
        "total": 0,

        "finalAuto": 0,
        "finalReview": 0,

        "retryApplied": 0,
        "retryUnresolved": 0,
    }

    print()
    print("=" * 120)
    print(
        "PoC 05-05｜Paper Final Validation"
    )
    print("=" * 120)
    print()

    # =====================================================
    # 5. 逐行执行最终判断
    # =====================================================

    for row in row_data.get(
        "rows",
        []
    ):

        stats["total"] += 1

        # -------------------------------------------------
        # 5.1 应用 Round1 / Round2 修正
        # -------------------------------------------------

        (
            updated,
            applied,
            unresolved,
        ) = apply_retry(
            row,
            retry_map,
        )

        stats[
            "retryApplied"
        ] += len(
            applied
        )

        stats[
            "retryUnresolved"
        ] += len(
            unresolved
        )

        # =================================================
        # 5.2 Metric Matcher
        # =================================================

        metric_name = (
            clean_metric_for_match(
                updated.get(
                    "metric",
                    "",
                )
            )
        )

        raw_unit = updated.get(
            "unit",
            "",
        )

        match = match_metric(
            metric_name,
            raw_unit,
            metrics,
        )

        unit_status = (
            build_unit_status(
                match
            )
        )

        # =================================================
        # 5.3 Result Parser
        #
        # 先处理纸质报告特有的：
        #
        # 119 + ↓130~175
        #
        # ↓ 从参考范围移回结果值。
        # =================================================

        adapted = adapt_paper_row(
            updated
        )

        structured = (
            structure_row(
                adapted
            )
        )

        # =================================================
        # 5.4 FINAL Status
        # =================================================

        (
            final_status,
            final_reasons,
        ) = final_decision(
            match,
            unit_status,
            structured,
            unresolved,
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

        # =================================================
        # 5.5 保存完整审计数据
        # =================================================

        final_row = {
            "blockId":
                row.get(
                    "block_id"
                ),

            "rowIndex":
                row.get(
                    "row_index"
                ),

            # ---------------------------------------------
            # 原始 Row Parser 数据
            # ---------------------------------------------

            "raw": {
                "metric":
                    row.get(
                        "metric"
                    ),

                "result":
                    row.get(
                        "result"
                    ),

                "reference":
                    row.get(
                        "reference"
                    ),

                "unit":
                    row.get(
                        "unit"
                    ),
            },

            # ---------------------------------------------
            # OCR Retry 后真正用于业务解析的数据
            # ---------------------------------------------

            "resolved": {
                "metric":
                    updated.get(
                        "metric"
                    ),

                "result":
                    updated.get(
                        "result"
                    ),

                "reference":
                    updated.get(
                        "reference"
                    ),

                "unit":
                    updated.get(
                        "unit"
                    ),
            },

            # ---------------------------------------------
            # Retry 审计记录
            # ---------------------------------------------

            "retry": {
                "applied":
                    applied,

                "unresolved":
                    unresolved,
            },

            # ---------------------------------------------
            # 标准指标匹配
            # ---------------------------------------------

            "metricMatch":
                match,

            # ---------------------------------------------
            # 单位校验
            # ---------------------------------------------

            "unitValidation":
                unit_status,

            # ---------------------------------------------
            # 结果值 + 参考范围结构化
            # ---------------------------------------------

            "resultValidation":
                structured,

            # ---------------------------------------------
            # 最终状态
            # ---------------------------------------------

            "finalStatus":
                final_status,

            "finalReasons":
                final_reasons,
        }

        final_rows.append(
            final_row
        )

        # =================================================
        # 5.6 Terminal
        # =================================================

        raw_metric = str(
            row.get(
                "metric",
                ""
            )
        )

        resolved_metric = str(
            updated.get(
                "metric",
                ""
            )
        )

        print(
            f"{raw_metric:<24}"
            f" → "
            f"{resolved_metric:<24}"
            f" | "
            f"{str(match.get('status')):<13}"
            f" | unit="
            f"{str(unit_status.get('unitStatus')):<10}"
            f" | "
            f"{final_status}"
        )

        # -------------------------------------------------
        # 如果 OCR Retry 发生修正
        # -------------------------------------------------

        for change in applied:

            print(
                "    ├─ OCR修正："
                f"{change['field']} "
                f"{change['from']} "
                f"→ "
                f"{change['to']}"
            )

        # -------------------------------------------------
        # Retry 未解决
        # -------------------------------------------------

        for issue in unresolved:

            print(
                "    ├─ OCR未解决："
                f"{issue['field']} "
                f"| "
                f"{issue['reason']}"
            )

        # -------------------------------------------------
        # FINAL REVIEW 原因
        # -------------------------------------------------

        if final_reasons:

            print(
                "    └─ FINAL："
                + ", ".join(
                    final_reasons
                )
            )

    # =====================================================
    # 6. 自动通过率
    # =====================================================

    if stats["total"]:

        auto_rate = (
            stats["finalAuto"]
            / stats["total"]
            * 100
        )

    else:

        auto_rate = 0

    stats[
        "finalAutoRate"
    ] = round(
        auto_rate,
        1,
    )

    # =====================================================
    # 7. 保存最终 JSON
    # =====================================================

    output = {
        "poc":
            "PoC 05-05",

        "stage":
            "paper_final_validation",

        "retryStrategy": {
            "round1":
                "PaddleOCR multi-variant retry",

            "round2":
                "OCR consensus + metric library evidence fusion",

            "round2OverridesRound1":
                True,
        },

        "finalRule": {
            "metric":
                "AUTO_MATCHED",

            "unit":
                "MATCH",

            "result":
                "NO_CONFLICT_AND_NO_CONFIRMATION",

            "ocrRetry":
                "ALL_TRIGGERED_RETRIES_RESOLVED",
        },

        "summary":
            stats,

        "rows":
            final_rows,
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
    # 8. FINAL SUMMARY
    # =====================================================

    print()
    print("=" * 120)
    print(
        "FINAL SUMMARY"
    )
    print("=" * 120)

    print(
        f"总指标：          "
        f"{stats['total']}"
    )

    print(
        f"Paddle修正成功：  "
        f"{stats['retryApplied']}"
    )

    print(
        f"二次OCR未解决：   "
        f"{stats['retryUnresolved']}"
    )

    print()

    print(
        f"FINAL_AUTO：      "
        f"{stats['finalAuto']}"
    )

    print(
        f"FINAL_REVIEW：    "
        f"{stats['finalReview']}"
    )

    print(
        f"最终自动通过率：   "
        f"{stats['finalAutoRate']}%"
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
