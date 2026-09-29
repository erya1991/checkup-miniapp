from pathlib import Path
import json

from metric_matcher import (
    load_json,
    match_metric,
    build_match_output,
    build_unit_status,
    print_match_result,
    AUTO_THRESHOLD,
    REVIEW_THRESHOLD,
    MIN_MARGIN,
)

from report_context import (
    output_path,
)


BASE_DIR = Path(__file__).resolve().parent.parent

ROWS_JSON = output_path(
    "_rows.json"
)

METRIC_LIBRARY_JSON = (
    BASE_DIR
    / "data"
    / "metric_library.json"
)

OUTPUT_JSON = output_path(
    "_matched.json"
)


def normalize_paper_metric_for_match(
    raw_name: str,
) -> str:
    """
    纸质报告版式标记清洗。

    当前报告说明：
    * 表示省内互认项目。

    '*' 并不是指标名称的一部分，
    因此仅从“匹配输入”中移除。

    原始 OCR metric 字段仍然保留，
    不静默覆盖。
    """

    if not raw_name:
        return ""

    text = raw_name.strip()

    while text.startswith(
        ("*", "＊")
    ):
        text = text[1:].strip()

    return text


def main():

    row_data = load_json(
        ROWS_JSON
    )

    metrics = load_json(
        METRIC_LIBRARY_JSON
    )

    rows = row_data["rows"]

    output_rows = []

    stats = {
        "total": 0,
        "autoMatched": 0,
        "review": 0,
        "unmatched": 0,
        "unitMatched": 0,
        "unitWarning": 0,
        "unitNotChecked": 0,
    }

    print()
    print("=" * 120)
    print(
        "PoC 05-04｜纸质报告标准指标匹配"
    )
    print("=" * 120)
    print()

    for row in rows:

        stats["total"] += 1

        raw_name = row.get(
            "metric",
            "",
        )

        raw_unit = row.get(
            "unit",
            "",
        )

        match_input_name = (
            normalize_paper_metric_for_match(
                raw_name
            )
        )

        match = match_metric(
            match_input_name,
            raw_unit,
            metrics,
        )

        status = match["status"]

        if status == "AUTO_MATCHED":
            stats["autoMatched"] += 1

        elif status == "REVIEW":
            stats["review"] += 1

        else:
            stats["unmatched"] += 1

        unit_status = (
            build_unit_status(
                match
            )
        )

        if (
            unit_status["unitStatus"]
            == "MATCH"
        ):
            stats["unitMatched"] += 1

        elif (
            unit_status["unitStatus"]
            == "WARNING"
        ):
            stats["unitWarning"] += 1

        else:
            stats[
                "unitNotChecked"
            ] += 1

        output = build_match_output(
            row,
            match,
        )

        # 保留：
        # OCR原始名称 VS 实际用于匹配的名称
        output["metricMatch"][
            "matchInputName"
        ] = match_input_name

        output_rows.append(
            output
        )

        print_match_result(
            raw_name,
            match,
        )

        if (
            raw_name
            != match_input_name
        ):
            print(
                "      "
                f"└─ 匹配预处理："
                f"{raw_name}"
                f" → "
                f"{match_input_name}"
            )

    print()
    print("=" * 120)
    print("纸质报告匹配统计")
    print("=" * 120)

    print(
        f"总指标数：        "
        f"{stats['total']}"
    )

    print(
        f"自动匹配：        "
        f"{stats['autoMatched']}"
    )

    print(
        f"待人工确认：      "
        f"{stats['review']}"
    )

    print(
        f"未匹配：          "
        f"{stats['unmatched']}"
    )

    print()
    print("单位校验：")

    print(
        f"单位匹配：        "
        f"{stats['unitMatched']}"
    )

    print(
        f"单位异常/缺失：   "
        f"{stats['unitWarning']}"
    )

    print(
        f"未执行单位校验：  "
        f"{stats['unitNotChecked']}"
    )

    result_json = {
        "poc": "PoC 05-04",
        "stage":
            "paper_metric_matching",

        "summary": stats,

        "thresholds": {
            "autoThreshold":
                AUTO_THRESHOLD,
            "reviewThreshold":
                REVIEW_THRESHOLD,
            "minMargin":
                MIN_MARGIN,
        },

        "rows": output_rows,
    }

    with OUTPUT_JSON.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            result_json,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(
        "匹配结果已保存："
        f"{OUTPUT_JSON}"
    )


if __name__ == "__main__":
    main()