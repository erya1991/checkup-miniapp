# src/paper_unit_resolver.py

import json
import re
from pathlib import Path

from unit_resolver import (
    resolve_unit,
)

from report_context import (
    output_path,
)


BASE_DIR = Path(__file__).resolve().parent.parent

FINAL_PATH = output_path(
    "_final.json"
)

LIBRARY_PATH = (
    BASE_DIR
    / "data"
    / "metric_library.json"
)

OUTPUT_PATH = output_path(
    "_unit_resolved.json"
)


TARGET_METRICS = {
    "嗜碱性粒细胞绝对值",
    "红细胞比积",
    "血小板比积",
}


# =========================================================
# 基础
# =========================================================

def load_json(path):

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def normalize_metric_name(name):

    if not name:
        return ""

    name = str(name).strip()

    while name.startswith(
        ("*", "＊")
    ):
        name = name[1:].strip()

    return name


# =========================================================
# 标准指标定位
# =========================================================

def find_metric(
    metric_name,
    metrics,
):
    """
    本轮只处理已经确定身份的三个指标。

    只允许：
    standardName
    abbreviation
    aliases

    精确匹配。

    不做 FUZZY。
    """

    target = normalize_metric_name(
        metric_name
    )

    matches = []

    for metric in metrics:

        names = [
            metric.get(
                "standardName"
            ),
            metric.get(
                "abbreviation"
            ),
            *metric.get(
                "aliases",
                []
            ),
        ]

        normalized_names = {
            normalize_metric_name(
                name
            )
            for name in names
            if name
        }

        if target in normalized_names:

            matches.append(
                metric
            )

    if len(matches) == 1:
        return matches[0]

    return None


# =========================================================
# 数值轻量解析
#
# 注意：
#
# 这里不是重新实现 result_parser。
#
# 仅用于 PoC 05-06：
# 当 resultValidation 没有暴露数值字段时，
# 从 resolved 原始字段取得“数值尺度”，
# 用于判断缺失单位对应哪一种表达方式。
# =========================================================

def parse_single_numeric(text):
    """
    支持：

    0.360
    0.10
    119
    54.3

    ↓0.360
    0.360↓
    ↑100.3

    <0.5
    ≤4.00

    返回 float 或 None。
    """

    if text is None:
        return None

    text = str(text).strip()

    if not text:
        return None

    # 删除异常箭头
    text = (
        text
        .replace("↑", "")
        .replace("↓", "")
    )

    # 删除比较符
    text = re.sub(
        r"^(<=|>=|≤|≥|<|>)",
        "",
        text,
    )

    text = text.strip()

    match = re.fullmatch(
        r"-?\d+(?:\.\d+)?",
        text,
    )

    if not match:
        return None

    try:
        return float(text)

    except ValueError:
        return None


def parse_reference_range(text):
    """
    支持：

    0.400~0.500
    ↓0.400~0.500
    0.17～0.35

    返回：

    (low, high)

    无法解析：
    (None, None)
    """

    if text is None:
        return None, None

    text = str(text).strip()

    if not text:
        return None, None

    # -----------------------------------------------------
    # 纸质报告异常箭头：
    #
    # ↓0.400~0.500
    #
    # ↓ 描述的是结果异常状态，
    # 不属于参考范围。
    # -----------------------------------------------------

    text = (
        text
        .replace("↑", "")
        .replace("↓", "")
    )

    text = text.replace(
        "～",
        "~",
    )

    parts = text.split("~")

    if len(parts) != 2:
        return None, None

    low = parse_single_numeric(
        parts[0]
    )

    high = parse_single_numeric(
        parts[1]
    )

    return low, high


# =========================================================
# 从 Result Validation 获取
# =========================================================

def get_structured_numeric(
    result_validation,
):
    """
    尝试兼容现有 result_parser 不同结构。

    如果找不到，
    返回 None / None / None，
    后面从 resolved 原始文本 fallback。
    """

    if not isinstance(
        result_validation,
        dict,
    ):
        return None, None, None

    # -----------------------------------------------------
    # 第一种：
    # 顶层字段
    # -----------------------------------------------------

    numeric_value = (
        result_validation.get(
            "numericValue"
        )
    )

    reference_low = (
        result_validation.get(
            "referenceLow"
        )
    )

    reference_high = (
        result_validation.get(
            "referenceHigh"
        )
    )

    if (
        numeric_value is not None
        or
        reference_low is not None
        or
        reference_high is not None
    ):

        return (
            numeric_value,
            reference_low,
            reference_high,
        )

    # -----------------------------------------------------
    # 第二种：
    # result / reference 嵌套结构
    # -----------------------------------------------------

    result_part = (
        result_validation.get(
            "result"
        )
    )

    reference_part = (
        result_validation.get(
            "reference"
        )
    )

    if isinstance(
        result_part,
        dict,
    ):

        numeric_value = (
            result_part.get(
                "numericValue"
            )
        )

    if isinstance(
        reference_part,
        dict,
    ):

        reference_low = (
            reference_part.get(
                "referenceLow"
            )
        )

        if reference_low is None:

            reference_low = (
                reference_part.get(
                    "low"
                )
            )

        reference_high = (
            reference_part.get(
                "referenceHigh"
            )
        )

        if reference_high is None:

            reference_high = (
                reference_part.get(
                    "high"
                )
            )

    return (
        numeric_value,
        reference_low,
        reference_high,
    )


# =========================================================
# 数值解析总入口
# =========================================================

def get_numeric_values(
    row,
):
    """
    优先：

        resultValidation

    fallback：

        resolved.result
        resolved.reference

    fallback 只用于单位语义判断，
    不覆盖 result_parser 的正式结果。
    """

    result_validation = (
        row.get(
            "resultValidation",
            {}
        )
    )

    (
        result_value,
        reference_low,
        reference_high,
    ) = get_structured_numeric(
        result_validation
    )

    source = (
        "RESULT_VALIDATION"
    )

    # -----------------------------------------------------
    # 如果结构化字段没有取到，
    # 从 resolved 原始字段安全解析。
    # -----------------------------------------------------

    if (
        result_value is None
        and
        reference_low is None
        and
        reference_high is None
    ):

        resolved = row.get(
            "resolved",
            {}
        )

        result_value = (
            parse_single_numeric(
                resolved.get(
                    "result"
                )
            )
        )

        (
            reference_low,
            reference_high,
        ) = parse_reference_range(
            resolved.get(
                "reference"
            )
        )

        source = (
            "RESOLVED_TEXT_FALLBACK"
        )

    return (
        result_value,
        reference_low,
        reference_high,
        source,
    )


# =========================================================
# Main
# =========================================================

def main():

    final_data = load_json(
        FINAL_PATH
    )

    metrics = load_json(
        LIBRARY_PATH
    )

    outputs = []

    print()
    print("=" * 120)
    print(
        "PoC 05-06｜Paper Unit Semantic Resolution"
    )
    print("=" * 120)

    for row in final_data[
        "rows"
    ]:

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

        if (
            metric_name
            not in TARGET_METRICS
        ):
            continue

        # =================================================
        # 标准指标
        # =================================================

        metric = find_metric(
            metric_name,
            metrics,
        )

        if not metric:

            print(
                f"[ERROR] "
                f"标准指标无法唯一定位："
                f"{metric_name}"
            )

            continue

        # =================================================
        # 数值
        # =================================================

        (
            result_value,
            reference_low,
            reference_high,
            numeric_source,
        ) = get_numeric_values(
            row
        )

        # =================================================
        # Unit Resolver
        # =================================================

        resolution = resolve_unit(

            metric_id=
                metric[
                    "metricId"
                ],

            raw_unit=
                resolved.get(
                    "unit"
                ),

            expected_units=
                metric.get(
                    "commonUnits",
                    []
                ),

            result_value=
                result_value,

            reference_low=
                reference_low,

            reference_high=
                reference_high,
        )

        # =================================================
        # Output
        # =================================================

        output = {

            "metricId":
                metric[
                    "metricId"
                ],

            "standardName":
                metric[
                    "standardName"
                ],

            "rawUnit":
                resolved.get(
                    "unit"
                ),

            "expectedUnits":
                metric.get(
                    "commonUnits",
                    []
                ),

            "result":
                result_value,

            "referenceLow":
                reference_low,

            "referenceHigh":
                reference_high,

            "numericSource":
                numeric_source,

            "resolution":
                resolution,
        }

        outputs.append(
            output
        )

        # =================================================
        # Terminal
        # =================================================

        print()
        print(
            f"{metric['standardName']} "
            f"({metric['metricId']})"
        )

        print(
            f"  raw unit      : "
            f"{resolved.get('unit')}"
        )

        print(
            f"  expected      : "
            f"{metric.get('commonUnits')}"
        )

        print(
            f"  result        : "
            f"{result_value}"
        )

        print(
            f"  reference     : "
            f"{reference_low}"
            f" ~ "
            f"{reference_high}"
        )

        print(
            f"  numeric source: "
            f"{numeric_source}"
        )

        print(
            f"  STATUS        : "
            f"{resolution['status']}"
        )

        print(
            f"  normalized    : "
            f"{resolution.get('normalizedUnit')}"
        )

        print(
            f"  reason        : "
            f"{resolution['reason']}"
        )

    # =====================================================
    # Save
    # =====================================================

    output_json = {
        "poc":
            "PoC 05-06",

        "stage":
            "paper_unit_semantic_resolution",

        "targetCount":
            len(outputs),

        "results":
            outputs,
    }

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            output_json,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print("=" * 120)

    print(
        f"Saved: "
        f"{OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
