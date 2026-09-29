from pathlib import Path
import json
import re
import unicodedata


BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_JSON = (
    BASE_DIR
    / "output"
    / "electronic_report_matched.json"
)

OUTPUT_JSON = (
    BASE_DIR
    / "output"
    / "electronic_report_structured.json"
)


# ============================================================
# 常量
# ============================================================

ABNORMAL_NORMAL = "NORMAL"
ABNORMAL_HIGH = "HIGH"
ABNORMAL_LOW = "LOW"
ABNORMAL_UNKNOWN = "UNKNOWN"


RESULT_TYPE_NUMERIC = "NUMERIC"
RESULT_TYPE_TEXT = "TEXT"
RESULT_TYPE_UNKNOWN = "UNKNOWN"


REFERENCE_TYPE_RANGE = "RANGE"
REFERENCE_TYPE_UPPER_LIMIT = "UPPER_LIMIT"
REFERENCE_TYPE_LOWER_LIMIT = "LOWER_LIMIT"
REFERENCE_TYPE_TEXT = "TEXT"
REFERENCE_TYPE_UNKNOWN = "UNKNOWN"
REFERENCE_TYPE_EMPTY = "EMPTY"


VALIDATION_CONSISTENT = "CONSISTENT"
VALIDATION_CONFLICT = "CONFLICT"
VALIDATION_CALCULATED_ONLY = "CALCULATED_ONLY"
VALIDATION_REPORT_ONLY = "REPORT_ONLY"
VALIDATION_NOT_APPLICABLE = "NOT_APPLICABLE"
VALIDATION_UNKNOWN = "UNKNOWN"


# ============================================================
# 基础工具
# ============================================================

def load_json(path):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def normalize_text(text):
    if text is None:
        return ""

    text = unicodedata.normalize(
        "NFKC",
        str(text),
    )

    text = (
        text.strip()
        .replace(" ", "")
        .replace("\t", "")
        .replace("\n", "")
    )

    return text


def normalize_math_symbols(text):
    """
    统一常见数学符号。
    """

    text = normalize_text(text)

    replacements = {
        "＝": "=",
        "＜": "<",
        "＞": ">",
        "≦": "≤",
        "≧": "≥",
        "=>": ">=",
        "=<": "<=",
        "～": "~",
        "〜": "~",
        "－": "-",
        "—": "-",
        "–": "-",
    }

    for source, target in (
        replacements.items()
    ):
        text = text.replace(
            source,
            target,
        )

    return text


def safe_float(value):
    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return None


# ============================================================
# 医院异常标记解析
# ============================================================

def parse_report_abnormal(raw_result):
    """
    从医院原始结果中读取异常标记。

    支持：

    ↑
    ↑↑
    ↓
    ↓↓
    H
    L
    """

    if not raw_result:
        return ABNORMAL_UNKNOWN

    text = normalize_text(
        raw_result
    )

    upper_text = text.upper()

    if (
        "↑" in text
        or re.search(
            r"(?<![A-Z])H$",
            upper_text,
        )
    ):
        return ABNORMAL_HIGH

    if (
        "↓" in text
        or re.search(
            r"(?<![A-Z])L$",
            upper_text,
        )
    ):
        return ABNORMAL_LOW

    return ABNORMAL_UNKNOWN


def remove_abnormal_marks(text):
    if not text:
        return ""

    text = normalize_text(text)

    text = (
        text.replace("↑", "")
        .replace("↓", "")
    )

    # 删除末尾独立 H / L
    text = re.sub(
        r"(?i)(?<![A-Z])[HL]$",
        "",
        text,
    )

    return text.strip()


# ============================================================
# 检验结果解析
# ============================================================

def parse_result(raw_result):
    """
    将：

    23
    64.7↓
    205 ↑
    <0.5
    ≤4.00
    阴性

    转换为结构化结果。
    """

    raw_result = (
        ""
        if raw_result is None
        else str(raw_result)
    )

    display_value = (
        raw_result.strip()
    )

    report_abnormal = (
        parse_report_abnormal(
            raw_result
        )
    )

    cleaned = (
        remove_abnormal_marks(
            raw_result
        )
    )

    cleaned = (
        normalize_math_symbols(
            cleaned
        )
    )

    # -------------------------
    # 数值型
    #
    # 支持：
    # 23
    # 23.4
    # <0.5
    # ≤4
    # >=1.5
    # -------------------------

    numeric_pattern = re.compile(
        r"^(<=|>=|≤|≥|<|>|=)?"
        r"([-+]?"
        r"(?:\d+(?:\.\d+)?|\.\d+))$"
    )

    match = numeric_pattern.match(
        cleaned
    )

    if match:

        comparator = (
            match.group(1)
            or "="
        )

        comparator = (
            comparator
            .replace("≤", "<=")
            .replace("≥", ">=")
        )

        numeric_value = safe_float(
            match.group(2)
        )

        return {
            "type": RESULT_TYPE_NUMERIC,
            "comparator": comparator,
            "numericValue": numeric_value,
            "textValue": None,
            "displayValue": display_value,
            "reportAbnormal": (
                report_abnormal
            ),
            "parseSuccess": True,
        }

    # -------------------------
    # 文本型
    # -------------------------

    if cleaned:

        return {
            "type": RESULT_TYPE_TEXT,
            "comparator": None,
            "numericValue": None,
            "textValue": cleaned,
            "displayValue": (
                display_value
            ),
            "reportAbnormal": (
                report_abnormal
            ),
            "parseSuccess": True,
        }

    return {
        "type": RESULT_TYPE_UNKNOWN,
        "comparator": None,
        "numericValue": None,
        "textValue": None,
        "displayValue": (
            display_value
        ),
        "reportAbnormal": (
            report_abnormal
        ),
        "parseSuccess": False,
    }


# ============================================================
# 参考范围解析
# ============================================================

def parse_reference(
    raw_reference,
):
    """
    支持：

    9~50
    9～50
    65.0 - 85.0

    <=5
    ≤5
    <5

    >=1.5
    ≥1.5
    >1.5

    阴性
    未检出
    """

    raw_reference = (
        ""
        if raw_reference is None
        else str(raw_reference)
    )

    display_value = (
        raw_reference.strip()
    )

    cleaned = (
        normalize_math_symbols(
            raw_reference
        )
    )

    if not cleaned:

        return {
            "type": (
                REFERENCE_TYPE_EMPTY
            ),
            "low": None,
            "high": None,
            "operator": None,
            "textValue": None,
            "displayValue": (
                display_value
            ),
            "parseSuccess": True,
        }

    # OCR may render a dash between two positive bounds twice. Keep a
    # negative-to-negative range such as -5--1 untouched: its second minus
    # is the sign of the upper bound.
    if re.fullmatch(
        r"\+?(?:\d+(?:\.\d+)?|\.\d+)--\+?(?:\d+(?:\.\d+)?|\.\d+)",
        cleaned,
    ):
        cleaned = cleaned.replace("--", "-", 1)

    # -------------------------
    # 范围型
    # -------------------------

    range_pattern = re.compile(
        r"^([-+]?"
        r"(?:\d+(?:\.\d+)?|\.\d+))"
        r"\s*[~\-]\s*"
        r"([-+]?"
        r"(?:\d+(?:\.\d+)?|\.\d+))$"
    )

    match = range_pattern.match(
        cleaned
    )

    if match:

        low = safe_float(
            match.group(1)
        )

        high = safe_float(
            match.group(2)
        )

        # OCR极端情况下可能反了
        if (
            low is not None
            and high is not None
            and low > high
        ):
            low, high = (
                high,
                low,
            )

        return {
            "type": (
                REFERENCE_TYPE_RANGE
            ),
            "low": low,
            "high": high,
            "operator": None,
            "textValue": None,
            "displayValue": (
                display_value
            ),
            "parseSuccess": True,
        }

    # -------------------------
    # 单边范围
    # -------------------------

    limit_pattern = re.compile(
        r"^(<=|>=|≤|≥|<|>)"
        r"([-+]?"
        r"(?:\d+(?:\.\d+)?|\.\d+))$"
    )

    match = limit_pattern.match(
        cleaned
    )

    if match:

        operator = (
            match.group(1)
            .replace("≤", "<=")
            .replace("≥", ">=")
        )

        value = safe_float(
            match.group(2)
        )

        if operator in {
            "<",
            "<=",
        }:

            return {
                "type": (
                    REFERENCE_TYPE_UPPER_LIMIT
                ),
                "low": None,
                "high": value,
                "operator": operator,
                "textValue": None,
                "displayValue": (
                    display_value
                ),
                "parseSuccess": True,
            }

        return {
            "type": (
                REFERENCE_TYPE_LOWER_LIMIT
            ),
            "low": value,
            "high": None,
            "operator": operator,
            "textValue": None,
            "displayValue": (
                display_value
            ),
            "parseSuccess": True,
        }

    # -------------------------
    # 单纯一个数字
    #
    # 不猜它到底表示什么范围。
    # -------------------------

    if re.fullmatch(
        r"[-+]?"
        r"(?:\d+(?:\.\d+)?|\.\d+)",
        cleaned,
    ):

        return {
            "type": (
                REFERENCE_TYPE_UNKNOWN
            ),
            "low": None,
            "high": None,
            "operator": None,
            "textValue": cleaned,
            "displayValue": (
                display_value
            ),
            "parseSuccess": False,
        }

    # -------------------------
    # 文本参考范围
    # -------------------------

    return {
        "type": (
            REFERENCE_TYPE_TEXT
        ),
        "low": None,
        "high": None,
        "operator": None,
        "textValue": cleaned,
        "displayValue": (
            display_value
        ),
        "parseSuccess": True,
    }


# ============================================================
# 普通精确数值异常判断
# ============================================================

def calculate_exact_numeric_abnormal(
    value,
    reference,
):
    ref_type = reference[
        "type"
    ]

    # -------------------------
    # 区间
    # -------------------------

    if (
        ref_type
        == REFERENCE_TYPE_RANGE
    ):

        low = reference["low"]
        high = reference["high"]

        if (
            low is None
            or high is None
        ):
            return (
                ABNORMAL_UNKNOWN
            )

        if value < low:
            return ABNORMAL_LOW

        if value > high:
            return ABNORMAL_HIGH

        return ABNORMAL_NORMAL

    # -------------------------
    # 上限
    # -------------------------

    if (
        ref_type
        == REFERENCE_TYPE_UPPER_LIMIT
    ):

        high = reference[
            "high"
        ]

        if high is None:
            return (
                ABNORMAL_UNKNOWN
            )

        operator = reference[
            "operator"
        ]

        if operator == "<":
            if value < high:
                return (
                    ABNORMAL_NORMAL
                )

            return (
                ABNORMAL_HIGH
            )

        # <=
        if value <= high:
            return ABNORMAL_NORMAL

        return ABNORMAL_HIGH

    # -------------------------
    # 下限
    # -------------------------

    if (
        ref_type
        == REFERENCE_TYPE_LOWER_LIMIT
    ):

        low = reference["low"]

        if low is None:
            return (
                ABNORMAL_UNKNOWN
            )

        operator = reference[
            "operator"
        ]

        if operator == ">":
            if value > low:
                return (
                    ABNORMAL_NORMAL
                )

            return ABNORMAL_LOW

        # >=
        if value >= low:
            return ABNORMAL_NORMAL

        return ABNORMAL_LOW

    return ABNORMAL_UNKNOWN


# ============================================================
# 带比较符结果的保守异常判断
# ============================================================

def calculate_bounded_abnormal(
    comparator,
    value,
    reference,
):
    """
    对：

    <0.5
    <=0.5
    >100

    这类结果进行保守判断。

    只有能够确定异常状态时才返回，
    否则 UNKNOWN。
    """

    ref_type = reference[
        "type"
    ]

    # ========================================================
    # 参考范围：low ~ high
    # ========================================================

    if (
        ref_type
        == REFERENCE_TYPE_RANGE
    ):

        low = reference["low"]
        high = reference["high"]

        if (
            low is None
            or high is None
        ):
            return ABNORMAL_UNKNOWN

        # x < 某值
        if comparator == "<":

            if value <= low:
                return ABNORMAL_LOW

            return ABNORMAL_UNKNOWN

        if comparator == "<=":

            if value < low:
                return ABNORMAL_LOW

            return ABNORMAL_UNKNOWN

        # x > 某值
        if comparator == ">":

            if value >= high:
                return ABNORMAL_HIGH

            return ABNORMAL_UNKNOWN

        if comparator == ">=":

            if value > high:
                return ABNORMAL_HIGH

            return ABNORMAL_UNKNOWN

    # ========================================================
    # 参考范围：< high / <= high
    # ========================================================

    if (
        ref_type
        == REFERENCE_TYPE_UPPER_LIMIT
    ):

        high = reference["high"]

        if high is None:
            return ABNORMAL_UNKNOWN

        # 检测值 < x
        if comparator in {
            "<",
            "<=",
        }:

            if value <= high:
                return ABNORMAL_NORMAL

            return ABNORMAL_UNKNOWN

        if comparator == ">":

            if value >= high:
                return ABNORMAL_HIGH

            return ABNORMAL_UNKNOWN

        if comparator == ">=":

            if value > high:
                return ABNORMAL_HIGH

            return ABNORMAL_UNKNOWN

    # ========================================================
    # 参考范围：> low / >= low
    # ========================================================

    if (
        ref_type
        == REFERENCE_TYPE_LOWER_LIMIT
    ):

        low = reference["low"]

        if low is None:
            return ABNORMAL_UNKNOWN

        if comparator in {
            ">",
            ">=",
        }:

            if value >= low:
                return ABNORMAL_NORMAL

            return ABNORMAL_UNKNOWN

        if comparator == "<":

            if value <= low:
                return ABNORMAL_LOW

            return ABNORMAL_UNKNOWN

        if comparator == "<=":

            if value < low:
                return ABNORMAL_LOW

            return ABNORMAL_UNKNOWN

    return ABNORMAL_UNKNOWN


# ============================================================
# 根据结果和参考范围计算异常状态
# ============================================================

def calculate_abnormal(
    result,
    reference,
):
    if (
        result["type"]
        != RESULT_TYPE_NUMERIC
    ):
        return ABNORMAL_UNKNOWN

    value = result[
        "numericValue"
    ]

    if value is None:
        return ABNORMAL_UNKNOWN

    comparator = (
        result[
            "comparator"
        ]
        or "="
    )

    if comparator == "=":

        return (
            calculate_exact_numeric_abnormal(
                value,
                reference,
            )
        )

    return calculate_bounded_abnormal(
        comparator,
        value,
        reference,
    )


# ============================================================
# 医院异常标记 vs 系统计算结果
# ============================================================

def validate_abnormal(
    report_abnormal,
    calculated_abnormal,
):
    """
    返回一致性状态。
    """

    report_known = (
        report_abnormal
        in {
            ABNORMAL_HIGH,
            ABNORMAL_LOW,
        }
    )

    calculated_known = (
        calculated_abnormal
        in {
            ABNORMAL_NORMAL,
            ABNORMAL_HIGH,
            ABNORMAL_LOW,
        }
    )

    # -------------------------
    # 两边都有明确结论
    # -------------------------

    if (
        report_known
        and calculated_known
    ):

        if (
            report_abnormal
            == calculated_abnormal
        ):
            return (
                VALIDATION_CONSISTENT
            )

        return (
            VALIDATION_CONFLICT
        )

    # -------------------------
    # 医院未标异常，
    # 系统可以计算
    # -------------------------

    if (
        not report_known
        and calculated_known
    ):
        return (
            VALIDATION_CALCULATED_ONLY
        )

    # -------------------------
    # 医院标了，
    # 系统没法算
    # -------------------------

    if (
        report_known
        and not calculated_known
    ):
        return (
            VALIDATION_REPORT_ONLY
        )

    return (
        VALIDATION_NOT_APPLICABLE
    )


# ============================================================
# 最终异常状态
# ============================================================

def determine_final_abnormal(
    report_abnormal,
    calculated_abnormal,
    validation_status,
):
    """
    最终展示状态遵循：

    1. 医院明确 ↑↓ 时优先使用医院标记
    2. 医院未标时使用系统计算
    3. 两者冲突时仍保留医院原标记，
       但强制人工确认
    """

    if (
        report_abnormal
        in {
            ABNORMAL_HIGH,
            ABNORMAL_LOW,
        }
    ):
        return report_abnormal

    if (
        calculated_abnormal
        in {
            ABNORMAL_NORMAL,
            ABNORMAL_HIGH,
            ABNORMAL_LOW,
        }
    ):
        return (
            calculated_abnormal
        )

    return ABNORMAL_UNKNOWN


# ============================================================
# 文本结果简单处理
# ============================================================

def calculate_text_status(
    result,
    reference,
):
    """
    文本型结果只做极保守处理。

    如果结果和参考文本完全一致，
    可以认为符合参考文本。

    其他情况不自行判断医学异常。
    """

    if (
        result["type"]
        != RESULT_TYPE_TEXT
    ):
        return ABNORMAL_UNKNOWN

    if (
        reference["type"]
        != REFERENCE_TYPE_TEXT
    ):
        return ABNORMAL_UNKNOWN

    result_text = normalize_text(
        result["textValue"]
    )

    reference_text = (
        normalize_text(
            reference[
                "textValue"
            ]
        )
    )

    if (
        result_text
        and reference_text
        and result_text
        == reference_text
    ):
        return ABNORMAL_NORMAL

    return ABNORMAL_UNKNOWN


# ============================================================
# 人工确认规则
# ============================================================

def determine_confirmation(
    row,
    result,
    reference,
    validation_status,
):
    reasons = []

    metric_match = row.get(
        "metricMatch",
        {},
    )

    metric_status = (
        metric_match.get(
            "status"
        )
    )

    unit_status = (
        metric_match.get(
            "unitStatus"
        )
    )

    # -------------------------
    # 标准指标
    # -------------------------

    if metric_status == "REVIEW":

        reasons.append(
            "METRIC_REVIEW"
        )

    elif (
        metric_status
        == "UNMATCHED"
    ):

        reasons.append(
            "METRIC_UNMATCHED"
        )

    # -------------------------
    # 单位
    # -------------------------

    if unit_status == "WARNING":

        reasons.append(
            "UNIT_WARNING"
        )

    # -------------------------
    # 结果解析
    # -------------------------

    if not result[
        "parseSuccess"
    ]:

        reasons.append(
            "RESULT_PARSE_FAILED"
        )

    # -------------------------
    # 参考范围解析
    # -------------------------

    raw_reference = (
        row.get(
            "reference",
            ""
        )
    )

    if (
        raw_reference
        and not reference[
            "parseSuccess"
        ]
    ):

        reasons.append(
            "REFERENCE_PARSE_FAILED"
        )

    # -------------------------
    # 医院标记与系统计算冲突
    # -------------------------

    if (
        validation_status
        == VALIDATION_CONFLICT
    ):

        reasons.append(
            "ABNORMAL_CONFLICT"
        )

    return {
        "needConfirmation": (
            len(reasons) > 0
        ),
        "reasons": reasons,
    }


# ============================================================
# 单条检验结果结构化
# ============================================================

def structure_row(row):
    raw_result = row.get(
        "result",
        "",
    )

    raw_reference = row.get(
        "reference",
        "",
    )

    result = parse_result(
        raw_result
    )

    reference = parse_reference(
        raw_reference
    )

    # -------------------------
    # 数值异常判断
    # -------------------------

    calculated_abnormal = (
        calculate_abnormal(
            result,
            reference,
        )
    )

    # -------------------------
    # 文本参考值
    # -------------------------

    if (
        calculated_abnormal
        == ABNORMAL_UNKNOWN
        and result["type"]
        == RESULT_TYPE_TEXT
    ):

        calculated_abnormal = (
            calculate_text_status(
                result,
                reference,
            )
        )

    report_abnormal = (
        result[
            "reportAbnormal"
        ]
    )

    validation_status = (
        validate_abnormal(
            report_abnormal,
            calculated_abnormal,
        )
    )

    final_abnormal = (
        determine_final_abnormal(
            report_abnormal,
            calculated_abnormal,
            validation_status,
        )
    )

    confirmation = (
        determine_confirmation(
            row,
            result,
            reference,
            validation_status,
        )
    )

    return {
        **row,

        "structuredResult": {
            "type": (
                result["type"]
            ),
            "comparator": (
                result["comparator"]
            ),
            "numericValue": (
                result[
                    "numericValue"
                ]
            ),
            "textValue": (
                result[
                    "textValue"
                ]
            ),
            "displayValue": (
                result[
                    "displayValue"
                ]
            ),
            "parseSuccess": (
                result[
                    "parseSuccess"
                ]
            ),
        },

        "structuredReference": {
            "type": (
                reference["type"]
            ),
            "low": (
                reference["low"]
            ),
            "high": (
                reference["high"]
            ),
            "operator": (
                reference[
                    "operator"
                ]
            ),
            "textValue": (
                reference[
                    "textValue"
                ]
            ),
            "displayValue": (
                reference[
                    "displayValue"
                ]
            ),
            "parseSuccess": (
                reference[
                    "parseSuccess"
                ]
            ),
        },

        "abnormal": {
            "report": (
                report_abnormal
            ),
            "calculated": (
                calculated_abnormal
            ),
            "final": (
                final_abnormal
            ),
            "validationStatus": (
                validation_status
            ),
        },

        "confirmation": (
            confirmation
        ),
    }


# ============================================================
# 控制台显示
# ============================================================

def print_row(row):
    metric_name = (
        row.get(
            "metric",
            ""
        )
    )

    result = row[
        "structuredResult"
    ]

    reference = row[
        "structuredReference"
    ]

    abnormal = row[
        "abnormal"
    ]

    confirmation = row[
        "confirmation"
    ]

    metric_match = row.get(
        "metricMatch",
        {},
    )

    standard_name = (
        metric_match.get(
            "standardName"
        )
        or "-"
    )

    result_display = (
        result[
            "displayValue"
        ]
    )

    reference_display = (
        reference[
            "displayValue"
        ]
    )

    confirm_flag = (
        "⚠"
        if confirmation[
            "needConfirmation"
        ]
        else "✓"
    )

    print(
        f"{row.get('row', 0):02d} | "
        f"{metric_name:<20} | "
        f"{standard_name:<20} | "
        f"{result_display:<12} | "
        f"{reference_display:<16} | "
        f"report={abnormal['report']:<7} | "
        f"calc={abnormal['calculated']:<7} | "
        f"final={abnormal['final']:<7} | "
        f"{abnormal['validationStatus']:<18} | "
        f"{confirm_flag}"
    )

    if (
        confirmation[
            "needConfirmation"
        ]
    ):

        print(
            "     └─ "
            + ", ".join(
                confirmation[
                    "reasons"
                ]
            )
        )


# ============================================================
# 主流程
# ============================================================

def main():
    data = load_json(
        INPUT_JSON
    )

    rows = data["rows"]

    structured_rows = []

    stats = {
        "total": 0,

        "numericResults": 0,
        "textResults": 0,
        "unknownResults": 0,

        "referenceRange": 0,
        "referenceUpperLimit": 0,
        "referenceLowerLimit": 0,
        "referenceText": 0,
        "referenceUnknown": 0,
        "referenceEmpty": 0,

        "normal": 0,
        "high": 0,
        "low": 0,
        "abnormalUnknown": 0,

        "consistent": 0,
        "conflict": 0,
        "calculatedOnly": 0,
        "reportOnly": 0,

        "needConfirmation": 0,
    }

    print()
    print("=" * 180)
    print(
        "检验结果 + 参考范围结构化 PoC"
    )
    print("=" * 180)
    print()

    for row in rows:
        stats["total"] += 1

        structured = (
            structure_row(row)
        )

        structured_rows.append(
            structured
        )

        # ====================================================
        # 结果类型统计
        # ====================================================

        result_type = (
            structured[
                "structuredResult"
            ]["type"]
        )

        if (
            result_type
            == RESULT_TYPE_NUMERIC
        ):
            stats[
                "numericResults"
            ] += 1

        elif (
            result_type
            == RESULT_TYPE_TEXT
        ):
            stats[
                "textResults"
            ] += 1

        else:
            stats[
                "unknownResults"
            ] += 1

        # ====================================================
        # 参考范围统计
        # ====================================================

        reference_type = (
            structured[
                "structuredReference"
            ]["type"]
        )

        reference_map = {
            REFERENCE_TYPE_RANGE:
                "referenceRange",

            REFERENCE_TYPE_UPPER_LIMIT:
                "referenceUpperLimit",

            REFERENCE_TYPE_LOWER_LIMIT:
                "referenceLowerLimit",

            REFERENCE_TYPE_TEXT:
                "referenceText",

            REFERENCE_TYPE_UNKNOWN:
                "referenceUnknown",

            REFERENCE_TYPE_EMPTY:
                "referenceEmpty",
        }

        stat_key = (
            reference_map.get(
                reference_type
            )
        )

        if stat_key:
            stats[stat_key] += 1

        # ====================================================
        # 最终异常状态统计
        # ====================================================

        final_abnormal = (
            structured[
                "abnormal"
            ]["final"]
        )

        if (
            final_abnormal
            == ABNORMAL_NORMAL
        ):
            stats["normal"] += 1

        elif (
            final_abnormal
            == ABNORMAL_HIGH
        ):
            stats["high"] += 1

        elif (
            final_abnormal
            == ABNORMAL_LOW
        ):
            stats["low"] += 1

        else:
            stats[
                "abnormalUnknown"
            ] += 1

        # ====================================================
        # 一致性统计
        # ====================================================

        validation_status = (
            structured[
                "abnormal"
            ]["validationStatus"]
        )

        if (
            validation_status
            == VALIDATION_CONSISTENT
        ):
            stats[
                "consistent"
            ] += 1

        elif (
            validation_status
            == VALIDATION_CONFLICT
        ):
            stats[
                "conflict"
            ] += 1

        elif (
            validation_status
            == VALIDATION_CALCULATED_ONLY
        ):
            stats[
                "calculatedOnly"
            ] += 1

        elif (
            validation_status
            == VALIDATION_REPORT_ONLY
        ):
            stats[
                "reportOnly"
            ] += 1

        # ====================================================
        # 人工确认
        # ====================================================

        if (
            structured[
                "confirmation"
            ]["needConfirmation"]
        ):
            stats[
                "needConfirmation"
            ] += 1

        print_row(
            structured
        )

    # ========================================================
    # 输出统计
    # ========================================================

    print()
    print("=" * 120)
    print("结构化统计")
    print("=" * 120)

    print(
        f"总指标数：             "
        f"{stats['total']}"
    )

    print()
    print("结果类型：")

    print(
        f"数值型：               "
        f"{stats['numericResults']}"
    )

    print(
        f"文本型：               "
        f"{stats['textResults']}"
    )

    print(
        f"无法解析：             "
        f"{stats['unknownResults']}"
    )

    print()
    print("参考范围：")

    print(
        f"区间型：               "
        f"{stats['referenceRange']}"
    )

    print(
        f"上限型：               "
        f"{stats['referenceUpperLimit']}"
    )

    print(
        f"下限型：               "
        f"{stats['referenceLowerLimit']}"
    )

    print(
        f"文本型：               "
        f"{stats['referenceText']}"
    )

    print(
        f"未知格式：             "
        f"{stats['referenceUnknown']}"
    )

    print(
        f"为空：                 "
        f"{stats['referenceEmpty']}"
    )

    print()
    print("最终异常状态：")

    print(
        f"正常：                 "
        f"{stats['normal']}"
    )

    print(
        f"偏高：                 "
        f"{stats['high']}"
    )

    print(
        f"偏低：                 "
        f"{stats['low']}"
    )

    print(
        f"无法判断：             "
        f"{stats['abnormalUnknown']}"
    )

    print()
    print("医院标记 vs 系统计算：")

    print(
        f"一致：                 "
        f"{stats['consistent']}"
    )

    print(
        f"冲突：                 "
        f"{stats['conflict']}"
    )

    print(
        f"仅系统计算：           "
        f"{stats['calculatedOnly']}"
    )

    print(
        f"仅医院标记：           "
        f"{stats['reportOnly']}"
    )

    print()
    print(
        f"需要人工确认：         "
        f"{stats['needConfirmation']}"
    )

    # ========================================================
    # 保存 JSON
    # ========================================================

    output = {
        "summary": stats,
        "rows": structured_rows,
    }

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(
        "最终结构化结果已保存："
        f"{OUTPUT_JSON}"
    )


if __name__ == "__main__":
    main()
