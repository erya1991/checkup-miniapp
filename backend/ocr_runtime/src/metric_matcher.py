from pathlib import Path
import json
import re
import unicodedata

from rapidfuzz import fuzz


BASE_DIR = Path(__file__).resolve().parent.parent

ROWS_JSON = (
    BASE_DIR
    / "output"
    / "electronic_report_rows.json"
)

METRIC_LIBRARY_JSON = (
    BASE_DIR
    / "data"
    / "metric_library.json"
)

OUTPUT_JSON = (
    BASE_DIR
    / "output"
    / "electronic_report_matched.json"
)


# ============================================================
# 匹配阈值
# ============================================================

AUTO_THRESHOLD = 90
REVIEW_THRESHOLD = 75
MIN_MARGIN = 8

# OCR 原始指标名称过短时，
# 禁止仅依靠模糊匹配直接自动绑定。
#
# 例如：
# 糖 -> 葡萄糖
# 酶 -> 某某酶
# 酸 -> 某某酸
#
# EXACT / ALIAS / ABBREVIATION 不受影响。
SHORT_NAME_MAX_LENGTH = 2


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


def normalize_metric_name(text):
    """
    指标名称标准化。

    只用于匹配，
    不覆盖 OCR 原始名称。
    """

    if not text:
        return ""

    text = unicodedata.normalize(
        "NFKC",
        text,
    )

    text = text.strip()
    # Printed mutual-recognition markers precede some formal metric names.
    text = text.lstrip("*＊")

    text = (
        text.replace("Γ", "γ")
        .replace("ɣ", "γ")
    )

    text = text.upper()

    text = re.sub(
        r"[\s\-_./·（）()\[\]【】]+",
        "",
        text,
    )

    return text


def get_effective_name_length(text):
    """
    获取用于匹配安全判断的有效名称长度。

    例如：

    糖       -> 1
    尿酸     -> 2
    总蛋白   -> 3
    CK       -> 2

    CK 等正式缩写会在 exact_match 阶段
    提前完成精确匹配，
    因此不会受到短名称 FUZZY 限制。
    """

    normalized = normalize_metric_name(
        text
    )

    return len(normalized)


def normalize_unit(unit):
    """
    单位只进行格式标准化，
    当前不做跨单位数值换算。
    """

    if not unit:
        return ""

    unit = unicodedata.normalize(
        "NFKC",
        unit,
    )

    unit = unit.strip()

    unit = (
        unit.replace("μ", "u")
        .replace("µ", "u")
        .replace("／", "/")
        .replace(" ", "")
    )

    return unit.lower()


def metric_names(metric):
    """
    返回一个标准指标参与匹配的所有名称。
    """

    names = [
        metric.get(
            "standardName",
            "",
        ),
        metric.get(
            "abbreviation",
            "",
        ),
    ]

    names.extend(
        metric.get(
            "aliases",
            [],
        )
    )

    return [
        name
        for name in names
        if name
    ]


# ============================================================
# 精确匹配
# ============================================================

def exact_match(
    raw_name,
    metrics,
):
    raw_normalized = (
        normalize_metric_name(
            raw_name
        )
    )

    if not raw_normalized:
        return None

    for metric in metrics:

        standard_name = (
            metric.get(
                "standardName",
                "",
            )
        )

        # 标准名称
        if (
            raw_normalized
            == normalize_metric_name(
                standard_name
            )
        ):
            return {
                "metric": metric,
                "matchType": "EXACT",
                "nameScore": 100.0,
                "matchedName": (
                    standard_name
                ),
            }

        # 别名
        for alias in metric.get(
            "aliases",
            [],
        ):
            if (
                raw_normalized
                == normalize_metric_name(
                    alias
                )
            ):
                return {
                    "metric": metric,
                    "matchType": "ALIAS",
                    "nameScore": 100.0,
                    "matchedName": alias,
                }

        # 英文缩写
        abbreviation = (
            metric.get(
                "abbreviation",
                "",
            )
        )

        if (
            abbreviation
            and raw_normalized
            == normalize_metric_name(
                abbreviation
            )
        ):
            return {
                "metric": metric,
                "matchType": (
                    "ABBREVIATION"
                ),
                "nameScore": 100.0,
                "matchedName": (
                    abbreviation
                ),
            }

    return None


# ============================================================
# 名称模糊匹配
# ============================================================

def containment_score(
    source,
    target,
):
    """
    用于处理 OCR 截断 / 漏字。

    例如：

    天冬氨酸氨
    ->
    天冬氨酸氨基转移酶
    """

    if (
        len(source) < 4
        or len(target) < 4
    ):
        return 0.0

    if (
        source in target
        or target in source
    ):
        coverage = (
            min(
                len(source),
                len(target),
            )
            / max(
                len(source),
                len(target),
            )
        )

        return (
            90
            + coverage * 8
        )

    return 0.0


def calculate_name_score(
    raw_name,
    candidate_name,
):
    source = normalize_metric_name(
        raw_name
    )

    target = normalize_metric_name(
        candidate_name
    )

    if not source or not target:
        return 0.0

    if source == target:
        return 100.0

    containment = (
        containment_score(
            source,
            target,
        )
    )

    normal_ratio = fuzz.ratio(
        source,
        target,
    )

    partial_ratio = (
        fuzz.partial_ratio(
            source,
            target,
        )
    )

    # partial_ratio 对很短的字符串容易过度乐观，
    # 因此适当降权。
    fuzzy_score = max(
        normal_ratio,
        partial_ratio * 0.92,
    )

    return max(
        containment,
        fuzzy_score,
    )


# ============================================================
# 单位检查
# ============================================================

def check_unit(
    raw_unit,
    metric,
):
    """
    判断当前 OCR 单位是否符合候选标准指标。

    注意：
    单位只能辅助指标匹配，
    不能单独决定指标是什么。
    """

    common_units = (
        metric.get(
            "commonUnits",
            [],
        )
    )

    # 无量纲指标
    if not common_units:
        return {
            "unitMatch": True,
            "unitWarning": False,
        }

    # OCR 没有识别到单位
    if not raw_unit:
        return {
            "unitMatch": False,
            "unitWarning": True,
        }

    source = normalize_unit(
        raw_unit
    )

    targets = [
        normalize_unit(unit)
        for unit
        in common_units
    ]

    matched = (
        source in targets
    )

    return {
        "unitMatch": matched,
        "unitWarning": (
            not matched
        ),
    }


# ============================================================
# 单候选评分
# ============================================================

def score_metric(
    raw_name,
    raw_unit,
    metric,
):
    best_name_score = 0.0
    best_candidate_name = None

    for candidate_name in (
        metric_names(metric)
    ):
        score = (
            calculate_name_score(
                raw_name,
                candidate_name,
            )
        )

        if (
            score
            > best_name_score
        ):
            best_name_score = score
            best_candidate_name = (
                candidate_name
            )

    unit_result = check_unit(
        raw_unit,
        metric,
    )

    final_score = (
        best_name_score
    )

    # 单位只能轻度加分。
    #
    # 防止出现：
    # U/L -> 自动判断为某个酶类指标
    if (
        best_name_score >= 70
        and unit_result[
            "unitMatch"
        ]
    ):
        final_score += 3

    final_score = min(
        final_score,
        100,
    )

    return {
        "metric": metric,
        "nameScore": round(
            best_name_score,
            2,
        ),
        "score": round(
            final_score,
            2,
        ),
        "matchedName": (
            best_candidate_name
        ),
        **unit_result,
    }


# ============================================================
# 模糊匹配
# ============================================================

def fuzzy_match(
    raw_name,
    raw_unit,
    metrics,
):
    raw_name_length = (
        get_effective_name_length(
            raw_name
        )
    )

    is_short_name = (
        raw_name_length
        <= SHORT_NAME_MAX_LENGTH
    )

    candidates = [
        score_metric(
            raw_name,
            raw_unit,
            metric,
        )
        for metric in metrics
    ]

    if not candidates:
        return {
            "metric": None,
            "status": "UNMATCHED",
            "matchType": None,
            "score": 0.0,
            "nameScore": 0.0,
            "margin": 0.0,
            "matchedName": None,
            "unitMatch": None,
            "unitWarning": False,
            "rawNameLength": (
                raw_name_length
            ),
            "shortNameGuard": (
                is_short_name
            ),
            "topCandidates": [],
        }

    candidates.sort(
        key=lambda item: (
            item["score"]
        ),
        reverse=True,
    )

    best = candidates[0]

    second_score = (
        candidates[1]["score"]
        if len(candidates) > 1
        else 0
    )

    margin = (
        best["score"]
        - second_score
    )

    # ========================================================
    # 短名称安全规则
    # ========================================================

    if is_short_name:

        # 糖 -> 葡萄糖
        #
        # 可以作为推荐候选，
        # 但不能仅靠 FUZZY 自动绑定。
        if (
            best["score"]
            >= REVIEW_THRESHOLD
        ):
            status = "REVIEW"
            match_type = "FUZZY"

        else:
            status = "UNMATCHED"
            match_type = None

    # ========================================================
    # 普通名称
    # ========================================================

    elif (
        best["score"]
        >= AUTO_THRESHOLD
        and margin
        >= MIN_MARGIN
    ):
        status = "AUTO_MATCHED"
        match_type = "FUZZY"

    elif (
        best["score"]
        >= REVIEW_THRESHOLD
    ):
        status = "REVIEW"
        match_type = "FUZZY"

    else:
        status = "UNMATCHED"
        match_type = None

    # ========================================================
    # Top候选
    # ========================================================

    top_candidates = []

    for item in candidates[:3]:

        if item["score"] <= 0:
            continue

        metric = item["metric"]

        top_candidates.append(
            {
                "metricId": (
                    metric[
                        "metricId"
                    ]
                ),
                "standardName": (
                    metric[
                        "standardName"
                    ]
                ),
                "abbreviation": (
                    metric.get(
                        "abbreviation"
                    )
                ),
                "score": (
                    item["score"]
                ),
                "nameScore": (
                    item[
                        "nameScore"
                    ]
                ),
                "candidateUnitMatch": (
                    item[
                        "unitMatch"
                    ]
                ),
            }
        )

    # 注意：
    # return 必须位于 for 循环外面。
    return {
        **best,
        "status": status,
        "matchType": match_type,
        "margin": round(
            margin,
            2,
        ),
        "rawNameLength": (
            raw_name_length
        ),
        "shortNameGuard": (
            is_short_name
        ),
        "topCandidates": (
            top_candidates
        ),
    }


# ============================================================
# 匹配入口
# ============================================================

def match_metric(
    raw_name,
    raw_unit,
    metrics,
):
    # 精确匹配
    exact = exact_match(
        raw_name,
        metrics,
    )

    if exact:

        unit_result = (
            check_unit(
                raw_unit,
                exact["metric"],
            )
        )

        return {
            **exact,
            "score": 100.0,
            "status": "AUTO_MATCHED",
            "margin": 100.0,
            "rawNameLength": (
                get_effective_name_length(
                    raw_name
                )
            ),
            "shortNameGuard": False,
            "topCandidates": [],
            **unit_result,
        }

    # 模糊匹配
    return fuzzy_match(
        raw_name,
        raw_unit,
        metrics,
    )


# ============================================================
# 单位状态
# ============================================================

def build_unit_status(
    match,
):
    """
    AUTO_MATCHED / REVIEW：
        可以针对当前候选指标检查单位。

    UNMATCHED：
        因为不知道真正是什么指标，
        所以单位不做正式判断。
    """

    status = match["status"]

    if status == "UNMATCHED":
        return {
            "unitStatus": (
                "NOT_CHECKED"
            ),
            "unitMatch": None,
            "unitWarning": False,
        }

    if match["unitMatch"]:
        return {
            "unitStatus": "MATCH",
            "unitMatch": True,
            "unitWarning": False,
        }

    return {
        "unitStatus": "WARNING",
        "unitMatch": False,
        "unitWarning": True,
    }


# ============================================================
# 构建正式输出
# ============================================================

def build_match_output(
    row,
    match,
):
    candidate_metric = (
        match.get("metric")
    )

    unit_status = (
        build_unit_status(
            match
        )
    )

    # UNMATCHED：
    # 正式 metricId 不能写入错误候选。
    if (
        match["status"]
        == "UNMATCHED"
        or candidate_metric is None
    ):
        metric_id = None
        standard_name = None
        abbreviation = None

    else:
        metric_id = (
            candidate_metric.get(
                "metricId"
            )
        )

        standard_name = (
            candidate_metric.get(
                "standardName"
            )
        )

        abbreviation = (
            candidate_metric.get(
                "abbreviation"
            )
        )

    return {
        **row,
        "metricMatch": {
            "metricId": metric_id,
            "standardName": (
                standard_name
            ),
            "abbreviation": (
                abbreviation
            ),
            "matchType": (
                match.get(
                    "matchType"
                )
            ),
            "status": (
                match["status"]
            ),
            "score": (
                match["score"]
            ),
            "nameScore": (
                match["nameScore"]
            ),
            "margin": (
                match["margin"]
            ),
            "matchedName": (
                match.get(
                    "matchedName"
                )
            ),

            # 保留短名称安全规则调试信息
            "rawNameLength": (
                match.get(
                    "rawNameLength"
                )
            ),
            "shortNameGuard": (
                match.get(
                    "shortNameGuard",
                    False,
                )
            ),

            "unitStatus": (
                unit_status[
                    "unitStatus"
                ]
            ),
            "unitMatch": (
                unit_status[
                    "unitMatch"
                ]
            ),
            "unitWarning": (
                unit_status[
                    "unitWarning"
                ]
            ),
            "topCandidates": (
                match[
                    "topCandidates"
                ]
            ),
        },
    }


# ============================================================
# 控制台显示
# ============================================================

def print_match_result(
    raw_name,
    match,
):
    candidate_metric = (
        match.get("metric")
    )

    if (
        match["status"]
        == "UNMATCHED"
        or candidate_metric is None
    ):
        display_name = "未匹配"
        display_abbreviation = "-"

    else:
        display_name = (
            candidate_metric.get(
                "standardName"
            )
            or "-"
        )

        display_abbreviation = (
            candidate_metric.get(
                "abbreviation"
            )
            or "-"
        )

    match_type_display = (
        match.get(
            "matchType"
        )
        or "-"
    )

    unit_status = (
        build_unit_status(
            match
        )
    )

    if (
        unit_status[
            "unitStatus"
        ]
        == "MATCH"
    ):
        unit_flag = "✓"

    elif (
        unit_status[
            "unitStatus"
        ]
        == "WARNING"
    ):
        unit_flag = "⚠"

    else:
        unit_flag = "-"

    print(
        f"{raw_name:<22} "
        f"→ "
        f"{display_name:<22} "
        f"{display_abbreviation:<8} "
        f"| {match_type_display:<8} "
        f"| score={match['score']:6.2f} "
        f"| unit={unit_flag} "
        f"| {match['status']}"
    )

    # 短名称被安全规则拦截时，
    # 控制台明确提示原因。
    if (
        match.get(
            "shortNameGuard",
            False,
        )
        and match["status"]
        == "REVIEW"
    ):
        print(
            "      └─ 短名称安全规则："
            "禁止 FUZZY 自动绑定"
        )

    # REVIEW候选
    if (
        match["status"]
        == "REVIEW"
    ):
        print(
            "      └─ 建议确认，候选："
        )

        for candidate in (
            match[
                "topCandidates"
            ]
        ):
            print(
                "         "
                + f"{candidate['standardName']} "
                + f"({candidate['abbreviation']}) "
                + f"score="
                + f"{candidate['score']:.2f}"
            )

    # UNMATCHED候选
    if (
        match["status"]
        == "UNMATCHED"
        and match[
            "topCandidates"
        ]
    ):
        print(
            "      └─ 未达到匹配阈值，"
            "仅供参考的候选："
        )

        for candidate in (
            match[
                "topCandidates"
            ]
        ):
            print(
                "         "
                + f"{candidate['standardName']} "
                + f"({candidate['abbreviation']}) "
                + f"score="
                + f"{candidate['score']:.2f}"
            )


# ============================================================
# 主流程
# ============================================================

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
        "shortNameReview": 0,
        "unitMatched": 0,
        "unitWarning": 0,
        "unitNotChecked": 0,
    }

    print()
    print("=" * 120)
    print("标准指标匹配 PoC")
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

        match = match_metric(
            raw_name,
            raw_unit,
            metrics,
        )

        # 匹配统计
        if (
            match["status"]
            == "AUTO_MATCHED"
        ):
            stats[
                "autoMatched"
            ] += 1

        elif (
            match["status"]
            == "REVIEW"
        ):
            stats[
                "review"
            ] += 1

        else:
            stats[
                "unmatched"
            ] += 1

        if (
            match.get(
                "shortNameGuard",
                False,
            )
            and match["status"]
            == "REVIEW"
        ):
            stats[
                "shortNameReview"
            ] += 1

        # 单位统计
        unit_status = (
            build_unit_status(
                match
            )
        )

        if (
            unit_status[
                "unitStatus"
            ]
            == "MATCH"
        ):
            stats[
                "unitMatched"
            ] += 1

        elif (
            unit_status[
                "unitStatus"
            ]
            == "WARNING"
        ):
            stats[
                "unitWarning"
            ] += 1

        else:
            stats[
                "unitNotChecked"
            ] += 1

        # JSON 输出
        output = (
            build_match_output(
                row,
                match,
            )
        )

        output_rows.append(
            output
        )

        # 控制台输出
        print_match_result(
            raw_name,
            match,
        )

    print()
    print("=" * 120)
    print("匹配统计")
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
        f"其中短名称保护：  "
        f"{stats['shortNameReview']}"
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
        "summary": stats,
        "thresholds": {
            "autoThreshold": (
                AUTO_THRESHOLD
            ),
            "reviewThreshold": (
                REVIEW_THRESHOLD
            ),
            "minMargin": (
                MIN_MARGIN
            ),
            "shortNameMaxLength": (
                SHORT_NAME_MAX_LENGTH
            ),
        },
        "rows": output_rows,
    }

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            result_json,
            file,
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
