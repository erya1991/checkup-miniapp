import json
import re
import unicodedata
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

UNIT_SEMANTICS_PATH = (
    BASE_DIR
    / "data"
    / "unit_semantics.json"
)


# =========================================================
# 基础
# =========================================================

def load_json(path):

    with Path(path).open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def normalize_unit_text(unit):
    """
    基础单位文本规范化。

    这里只做字符表示规范化，
    不做医学语义推断。
    """

    if unit is None:
        return ""

    unit = unicodedata.normalize(
        "NFKC",
        str(unit),
    )

    unit = unit.strip()

    unit = re.sub(
        r"\s+",
        "",
        unit,
    )

    unit = unit.replace(
        "／",
        "/",
    )

    # L统一大写
    unit = re.sub(
        r"/l$",
        "/L",
        unit,
        flags=re.IGNORECASE,
    )

    return unit


# =========================================================
# Expected unit normalization
# =========================================================

def canonicalize_expected_unit(unit):

    unit = normalize_unit_text(
        unit
    )

    # Unicode superscript
    replacements = {
        "⁰": "0",
        "¹": "1",
        "²": "2",
        "³": "3",
        "⁴": "4",
        "⁵": "5",
        "⁶": "6",
        "⁷": "7",
        "⁸": "8",
        "⁹": "9",
    }

    # 10⁹/L → 10^9/L
    match = re.match(
        r"^10([⁰¹²³⁴⁵⁶⁷⁸⁹]+)/L$",
        unit,
    )

    if match:

        exponent = "".join(
            replacements.get(
                ch,
                ch,
            )
            for ch in match.group(1)
        )

        return (
            f"10^{exponent}/L"
        )

    return unit


def flatten_power_unit(unit):
    """
    将：

        10^9/L

    转成 OCR 可能出现的扁平形式：

        109/L

    以及：

        10^12/L
        →
        1012/L

    注意：

    这个函数本身绝不意味着单位已经确认。
    只有与某个指标“唯一的预期单位”匹配时，
    才能作为单位恢复候选。
    """

    unit = canonicalize_expected_unit(
        unit
    )

    match = re.fullmatch(
        r"10\^(\d+)/L",
        unit,
    )

    if not match:
        return None

    exponent = match.group(1)

    return f"10{exponent}/L"


# =========================================================
# Explicit unit resolver
# =========================================================

def resolve_visible_unit(
    raw_unit,
    expected_units,
):
    """
    处理报告中实际存在 OCR 单位的情况。

    优先级：

    1. EXACT
    2. SUPERSCRIPT_FLATTENED
    3. UNRESOLVED
    """

    raw = normalize_unit_text(
        raw_unit
    )

    expected = [
        canonicalize_expected_unit(
            unit
        )
        for unit in expected_units
    ]

    expected = list(
        dict.fromkeys(
            expected
        )
    )

    if not raw:

        return {
            "status":
                "SOURCE_UNIT_MISSING",

            "rawUnit":
                raw_unit,

            "normalizedUnit":
                None,

            "reason":
                "NO_SOURCE_UNIT",
        }

    # -----------------------------------------------------
    # Exact
    # -----------------------------------------------------

    for canonical in expected:

        if (
            normalize_unit_text(raw)
            ==
            normalize_unit_text(canonical)
        ):

            return {
                "status":
                    "UNIT_MATCH",

                "rawUnit":
                    raw_unit,

                "normalizedUnit":
                    canonical,

                "reason":
                    "EXACT_UNIT_MATCH",
            }

    # -----------------------------------------------------
    # 上标扁平化
    #
    # 例如：
    #
    # expected = 10^9/L
    # OCR      = 109/L
    # -----------------------------------------------------

    candidates = []

    for canonical in expected:

        flattened = flatten_power_unit(
            canonical
        )

        if (
            flattened
            and
            normalize_unit_text(
                flattened
            )
            ==
            raw
        ):

            candidates.append(
                canonical
            )

    # 只有唯一候选才能自动恢复
    if len(candidates) == 1:

        return {
            "status":
                "UNIT_NORMALIZED",

            "rawUnit":
                raw_unit,

            "normalizedUnit":
                candidates[0],

            "reason":
                "SUPERSCRIPT_FLATTENED",

            "evidence": {
                "raw":
                    raw,

                "expectedCandidate":
                    candidates[0],
            },
        }

    if len(candidates) > 1:

        return {
            "status":
                "UNIT_REVIEW",

            "rawUnit":
                raw_unit,

            "normalizedUnit":
                None,

            "reason":
                "AMBIGUOUS_FLATTENED_UNIT",

            "candidates":
                candidates,
        }

    return {
        "status":
            "UNIT_REVIEW",

        "rawUnit":
            raw_unit,

        "normalizedUnit":
            None,

        "reason":
            "NO_UNIT_MATCH",
    }


# =========================================================
# Missing unit semantic resolver
# =========================================================

def values_fit_profile(
    values,
    profile,
):
    """
    判断：
    result + referenceLow + referenceHigh

    是否全部符合某一单位表达的数值尺度。
    """

    numeric_values = [
        float(value)
        for value in values
        if value is not None
    ]

    if not numeric_values:
        return False

    min_value = profile.get(
        "valueMin"
    )

    max_value = profile.get(
        "valueMax"
    )

    for value in numeric_values:

        if (
            min_value is not None
            and value < min_value
        ):
            return False

        if (
            max_value is not None
            and value > max_value
        ):
            return False

    return True


def resolve_missing_unit(
    metric_id,
    result_value,
    reference_low,
    reference_high,
    semantics,
):
    """
    源报告没有单位时，
    只能在已有明确 metric semantic profile 的情况下
    尝试确定表示方式。

    仍然保留：
        sourceUnit = None

    这里只生成：
        semanticUnit
    """

    profiles = semantics.get(
        "profiles",
        {}
    )

    config = profiles.get(
        metric_id
    )

    if not config:

        return {
            "status":
                "UNIT_REVIEW",

            "rawUnit":
                None,

            "normalizedUnit":
                None,

            "reason":
                "NO_MISSING_UNIT_PROFILE",
        }

    if not config.get(
        "allowMissingSourceUnit"
    ):

        return {
            "status":
                "UNIT_REVIEW",

            "rawUnit":
                None,

            "normalizedUnit":
                None,

            "reason":
                "MISSING_UNIT_NOT_ALLOWED",
        }

    values = [
        result_value,
        reference_low,
        reference_high,
    ]

    candidates = []

    for profile in config.get(
        "representations",
        []
    ):

        if values_fit_profile(
            values,
            profile,
        ):

            candidates.append(
                profile
            )

    # -----------------------------------------------------
    # 唯一表达模型
    # -----------------------------------------------------

    if len(candidates) == 1:

        candidate = candidates[0]

        return {
            "status":
                "UNIT_SEMANTICALLY_RESOLVED",

            # 真实报告仍然没有单位
            "rawUnit":
                None,

            # 业务规范化单位
            "normalizedUnit":
                candidate[
                    "canonicalUnit"
                ],

            "reason":
                "MISSING_SOURCE_UNIT_MATCHES_UNIQUE_VALUE_PROFILE",

            "evidence": {
                "result":
                    result_value,

                "referenceLow":
                    reference_low,

                "referenceHigh":
                    reference_high,

                "profile":
                    candidate,
            },
        }

    # -----------------------------------------------------
    # 多种表达模型都满足
    # -----------------------------------------------------

    if len(candidates) > 1:

        return {
            "status":
                "UNIT_REVIEW",

            "rawUnit":
                None,

            "normalizedUnit":
                None,

            "reason":
                "AMBIGUOUS_VALUE_PROFILE",

            "candidates":
                candidates,
        }

    return {
        "status":
            "UNIT_REVIEW",

        "rawUnit":
            None,

        "normalizedUnit":
            None,

        "reason":
            "VALUE_PROFILE_NOT_MATCHED",
    }


# =========================================================
# Public API
# =========================================================

def resolve_unit(
    metric_id,
    raw_unit,
    expected_units,
    result_value=None,
    reference_low=None,
    reference_high=None,
):
    """
    Unit Resolver 总入口。
    """

    # -----------------------------------------------------
    # 源报告存在单位
    # -----------------------------------------------------

    if raw_unit not in (
        None,
        "",
    ):

        return resolve_visible_unit(
            raw_unit,
            expected_units,
        )

    # -----------------------------------------------------
    # 源报告单位为空
    # -----------------------------------------------------

    semantics = load_json(
        UNIT_SEMANTICS_PATH
    )

    return resolve_missing_unit(
        metric_id,
        result_value,
        reference_low,
        reference_high,
        semantics,
    )