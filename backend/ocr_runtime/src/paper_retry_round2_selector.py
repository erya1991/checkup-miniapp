# src/paper_retry_round2_selector.py

import json
from pathlib import Path

from report_context import (
    get_report_id,
)


BASE_DIR = Path(__file__).resolve().parent.parent
REPORT_ID = get_report_id()


# =========================================================
# 当前报告 Round1 Retry
# =========================================================

ROUND1_RETRY_DIR = (
    BASE_DIR
    / "output"
    / REPORT_ID
    / "paper_retry"
)

ROUND1_TARGET_PATH = (
    ROUND1_RETRY_DIR
    / "paper_retry_targets.json"
)

ROUND1_RESULT_PATH = (
    ROUND1_RETRY_DIR
    / "paper_paddle_retry.json"
)


# =========================================================
# 当前报告 Round2 Retry
# =========================================================

ROUND2_RETRY_DIR = (
    BASE_DIR
    / "output"
    / REPORT_ID
    / "paper_retry_round2"
)

OUTPUT_PATH = (
    ROUND2_RETRY_DIR
    / "paper_retry_round2_targets.json"
)


# =========================================================
# Basic
# =========================================================

def load_json(path):

    if not path.exists():

        raise FileNotFoundError(
            f"未找到文件：\n{path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


def make_key(
    block_id,
    row_index,
    field,
):

    return (
        block_id,
        row_index,
        field,
    )


# =========================================================
# Main selector
# =========================================================

def main():

    target_data = load_json(
        ROUND1_TARGET_PATH
    )

    round1_data = load_json(
        ROUND1_RESULT_PATH
    )

    # -----------------------------------------------------
    # Round1 原始 Target 索引
    # -----------------------------------------------------

    target_map = {}

    for item in target_data.get(
        "targets",
        []
    ):

        key = make_key(
            item.get("blockId"),
            item.get("rowIndex"),
            item.get("field"),
        )

        target_map[key] = item

    # -----------------------------------------------------
    # 筛选 Round2
    #
    # 当前 PoC 只对 metric 字段做 Full Cell Round2。
    #
    # 条件：
    #
    # Round1 已触发
    # +
    # field = metric
    # +
    # Round1 未 ACCEPTED
    # -----------------------------------------------------

    round2_targets = []

    for result in round1_data.get(
        "results",
        []
    ):

        field = result.get(
            "field"
        )

        decision = result.get(
            "decision"
        )

        # Round2 当前只处理指标名称
        if field != "metric":
            continue

        # Round1 已经可靠解决
        if (
            decision
            == "ACCEPTED_CANDIDATE"
        ):
            continue

        block_id = result.get(
            "blockId"
        )

        row_index = result.get(
            "rowIndex"
        )

        key = make_key(
            block_id,
            row_index,
            field,
        )

        original_target = (
            target_map.get(
                key,
                {}
            )
        )

        target_id = (
            original_target.get(
                "targetId"
            )
            or result.get(
                "targetId"
            )
            or (
                f"b{block_id}_"
                f"r{row_index}_metric"
            )
        )

        target = {

            "targetId":
                target_id,

            "blockId":
                block_id,

            "rowIndex":
                row_index,

            "rowMetric":
                original_target.get(
                    "rowMetric"
                )
                or result.get(
                    "rowMetric"
                ),

            "field":
                "metric",

            "originalText":
                result.get(
                    "originalText"
                )
                or original_target.get(
                    "originalText"
                ),

            # Round1 风险来源
            "round1Reasons":
                original_target.get(
                    "reasons",
                    []
                ),

            # Round1 OCR 结论
            "round1Decision":
                decision,

            "round1Candidate":
                result.get(
                    "candidate"
                ),

            "round1Reason":
                result.get(
                    "reason"
                ),

            # Round2 为什么触发
            "round2Reason":
                "ROUND1_METRIC_UNRESOLVED",
        }

        round2_targets.append(
            target
        )

    # -----------------------------------------------------
    # 稳定排序
    # -----------------------------------------------------

    round2_targets.sort(
        key=lambda x: (
            x.get("blockId"),
            x.get("rowIndex"),
        )
    )

    output = {

        "poc":
            "PoC 06-02C",

        "stage":
            "dynamic_round2_target_selection",

        "rule":
            (
                "Round1 unresolved metric "
                "→ Full Cell Round2"
            ),

        "targetCount":
            len(round2_targets),

        "targets":
            round2_targets,
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
    # Terminal
    # =====================================================

    print()
    print("=" * 120)
    print(
        "PoC 06-02C｜Dynamic Round2 Selector"
    )
    print("=" * 120)

    print()

    print(
        f"Round1 targets : "
        f"{len(target_data.get('targets', []))}"
    )

    print(
        f"Round2 targets : "
        f"{len(round2_targets)}"
    )

    print()

    for target in round2_targets:

        print(
            f"{target['targetId']:<22}"
            f" | "
            f"{str(target['originalText']):<24}"
            f" | "
            f"{','.join(target['round1Reasons'])}"
            f" | "
            f"{target['round1Reason']}"
        )

    print()

    print(
        f"Saved: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
