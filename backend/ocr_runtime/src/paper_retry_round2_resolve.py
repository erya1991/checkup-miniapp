# src/paper_retry_round2_resolve.py

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from metric_matcher import (
    match_metric,
    build_unit_status,
)

from report_context import (
    get_report_id,
    output_path,
)


BASE_DIR = Path(__file__).resolve().parent.parent
REPORT_ID = get_report_id()


# =========================================================
# Paths
# =========================================================

ROWS_PATH = output_path(
    "_rows.json"
)

ROUND2_RETRY_DIR = (
    BASE_DIR
    / "output"
    / REPORT_ID
    / "paper_retry_round2"
)

ROUND2_PATH = (
    ROUND2_RETRY_DIR
    / "paper_paddle_retry_round2.json"
)

LIBRARY_PATH = (
    BASE_DIR
    / "data"
    / "metric_library.json"
)

OUTPUT_PATH = (
    ROUND2_RETRY_DIR
    / "paper_retry_round2_resolved.json"
)


# =========================================================
# Thresholds
# =========================================================

MIN_OCR_SCORE = 0.95

MIN_TEXT_VOTES = 2

MIN_CANONICAL_VOTES = 2


# =========================================================
# Basic
# =========================================================

def load_json(path):

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


def normalize(text):

    text = unicodedata.normalize(
        "NFKC",
        str(text or ""),
    )

    text = re.sub(
        r"\s+",
        "",
        text,
    )

    text = text.lstrip(
        "*＊"
    )

    return text.strip().lower()


# =========================================================
# Row Map
# =========================================================

def build_row_map(rows):

    result = {}

    for row in rows:

        key = (
            row.get(
                "block_id"
            ),
            row.get(
                "row_index"
            ),
        )

        result[key] = row

    return result


# =========================================================
# Strong Library Index
# =========================================================

def build_strong_name_index(
    metrics,
):
    """
    Strong Match 只允许：

    standardName
    alias
    abbreviation

    不使用 FUZZY。
    """

    index = defaultdict(
        list
    )

    for metric in metrics:

        standard_name = metric.get(
            "standardName"
        )

        metric_id = metric.get(
            "metricId"
        )

        names = []

        if standard_name:

            names.append(
                (
                    standard_name,
                    "EXACT",
                )
            )

        abbreviation = metric.get(
            "abbreviation"
        )

        if abbreviation:

            names.append(
                (
                    abbreviation,
                    "ABBREVIATION",
                )
            )

        for alias in metric.get(
            "aliases",
            []
        ):

            names.append(
                (
                    alias,
                    "ALIAS",
                )
            )

        for (
            name,
            match_type,
        ) in names:

            key = normalize(
                name
            )

            if not key:
                continue

            index[key].append(
                {
                    "metricId":
                        metric_id,

                    "standardName":
                        standard_name,

                    "matchedName":
                        name,

                    "matchType":
                        match_type,
                }
            )

    return index


def strong_library_match(
    text,
    name_index,
):

    key = normalize(
        text
    )

    matches = name_index.get(
        key,
        []
    )

    metric_ids = {
        item.get(
            "metricId"
        )
        for item in matches
        if item.get(
            "metricId"
        )
    }

    # 必须唯一指向一个标准指标
    if len(metric_ids) != 1:
        return None

    priority = {
        "EXACT": 0,
        "ALIAS": 1,
        "ABBREVIATION": 2,
    }

    matches = sorted(
        matches,
        key=lambda item: (
            priority.get(
                item.get(
                    "matchType"
                ),
                99,
            )
        ),
    )

    return matches[0]


# =========================================================
# Matcher helpers
# =========================================================

def recursive_find(
    obj,
    keys,
):

    if isinstance(
        obj,
        dict,
    ):

        for key in keys:

            if key in obj:
                return obj[key]

        for value in obj.values():

            found = recursive_find(
                value,
                keys,
            )

            if found is not None:
                return found

    elif isinstance(
        obj,
        list,
    ):

        for value in obj:

            found = recursive_find(
                value,
                keys,
            )

            if found is not None:
                return found

    return None


def get_metric_id(
    match,
):

    return recursive_find(
        match,
        {
            "metricId",
            "metric_id",
        },
    )


def get_standard_name(
    match,
):

    return recursive_find(
        match,
        {
            "standardName",
            "standard_name",
        },
    )


def get_match_score(
    match,
):

    return recursive_find(
        match,
        {
            "score",
            "matchScore",
            "match_score",
        },
    )


def get_match_margin(
    match,
):

    return recursive_find(
        match,
        {
            "margin",
            "scoreMargin",
            "score_margin",
        },
    )


# =========================================================
# High-quality Paddle results
# =========================================================

def get_high_quality_paddle(
    item,
):

    return [
        result
        for result in item.get(
            "paddleResults",
            []
        )
        if (
            result.get(
                "text"
            )
            and
            result.get(
                "score"
            )
            is not None
            and
            result.get(
                "score"
            )
            >= MIN_OCR_SCORE
        )
    ]


# =========================================================
# Stage 1
#
# OCR Text Consensus
# +
# Strong Library Match
# =========================================================

def try_strong_text_consensus(
    item,
    name_index,
):

    high_quality = (
        get_high_quality_paddle(
            item
        )
    )

    if (
        len(high_quality)
        < MIN_TEXT_VOTES
    ):

        return {
            "accepted":
                False,

            "reason":
                "INSUFFICIENT_HIGH_QUALITY_OCR",
        }

    # -----------------------------------------------------
    # 按 OCR 文本分组
    # -----------------------------------------------------

    groups = defaultdict(
        list
    )

    for result in high_quality:

        groups[
            normalize(
                result["text"]
            )
        ].append(
            result
        )

    ranked_groups = sorted(
        groups.values(),
        key=lambda group: (
            len(group),
            sum(
                item["score"]
                for item in group
            )
            / len(group),
        ),
        reverse=True,
    )

    best_group = (
        ranked_groups[0]
    )

    if (
        len(best_group)
        < MIN_TEXT_VOTES
    ):

        return {
            "accepted":
                False,

            "reason":
                "NO_OCR_TEXT_CONSENSUS",
        }

    candidate = (
        best_group[0][
            "text"
        ]
    )

    # -----------------------------------------------------
    # Strong Library Match
    # -----------------------------------------------------

    library_match = (
        strong_library_match(
            candidate,
            name_index,
        )
    )

    if not library_match:

        return {
            "accepted":
                False,

            "candidate":
                candidate,

            "reason":
                "NO_STRONG_LIBRARY_MATCH",
        }

    best_metric_id = (
        library_match[
            "metricId"
        ]
    )

    # -----------------------------------------------------
    # 检查其它高质量 OCR 组是否强匹配到不同指标
    # -----------------------------------------------------

    conflicts = []

    for group in ranked_groups[1:]:

        other_candidate = (
            group[0][
                "text"
            ]
        )

        other_match = (
            strong_library_match(
                other_candidate,
                name_index,
            )
        )

        if (
            other_match
            and
            other_match.get(
                "metricId"
            )
            != best_metric_id
        ):

            conflicts.append(
                {
                    "candidate":
                        other_candidate,

                    "metricId":
                        other_match.get(
                            "metricId"
                        ),

                    "standardName":
                        other_match.get(
                            "standardName"
                        ),
                }
            )

    if conflicts:

        return {
            "accepted":
                False,

            "candidate":
                candidate,

            "reason":
                "CONFLICTING_STRONG_LIBRARY_CANDIDATES",

            "conflicts":
                conflicts,
        }

    return {
        "accepted":
            True,

        # 保留 OCR 修正后的正常名称
        "candidate":
            candidate,

        "reason":
            "OCR_CONSENSUS_AND_STRONG_LIBRARY_MATCH",

        "acceptanceMode":
            "STRONG_TEXT_CONSENSUS",

        "ocrVotes":
            len(
                best_group
            ),

        "ocrScores": [
            round(
                value[
                    "score"
                ],
                4,
            )
            for value
            in best_group
        ],

        "libraryMatch":
            library_match,
    }


# =========================================================
# Stage 2
#
# Canonical Metric Consensus
#
# Rapid文字 != Paddle文字
# 也可以接受。
#
# 但必须：
#
# Rapid AUTO
# +
# Paddle >= 2 个高质量结果 AUTO
# +
# 都指向同一个 metricId
# +
# 单位均 MATCH
# +
# 不存在另一个标准指标冲突
# =========================================================

def try_canonical_metric_consensus(
    item,
    row,
    metrics,
):

    rapid_text = item.get(
        "originalText"
    )

    unit = row.get(
        "unit"
    )

    # -----------------------------------------------------
    # Rapid
    # -----------------------------------------------------

    rapid_match = match_metric(
        rapid_text,
        unit,
        metrics,
    )

    if (
        rapid_match.get(
            "status"
        )
        != "AUTO_MATCHED"
    ):

        return {
            "accepted":
                False,

            "reason":
                "RAPID_NOT_AUTO_MATCHED",
        }

    rapid_metric_id = (
        get_metric_id(
            rapid_match
        )
    )

    if not rapid_metric_id:

        return {
            "accepted":
                False,

            "reason":
                "RAPID_NO_METRIC_ID",
        }

    rapid_unit_status = (
        build_unit_status(
            rapid_match
        )
    )

    if (
        rapid_unit_status.get(
            "unitStatus"
        )
        != "MATCH"
    ):

        return {
            "accepted":
                False,

            "reason":
                "RAPID_UNIT_NOT_MATCHED",
        }

    # -----------------------------------------------------
    # Paddle
    # -----------------------------------------------------

    votes = []

    conflicts = []

    high_quality = (
        get_high_quality_paddle(
            item
        )
    )

    for paddle in high_quality:

        paddle_text = (
            paddle.get(
                "text"
            )
        )

        paddle_match = (
            match_metric(
                paddle_text,
                unit,
                metrics,
            )
        )

        if (
            paddle_match.get(
                "status"
            )
            != "AUTO_MATCHED"
        ):
            continue

        paddle_metric_id = (
            get_metric_id(
                paddle_match
            )
        )

        if not paddle_metric_id:
            continue

        paddle_unit_status = (
            build_unit_status(
                paddle_match
            )
        )

        if (
            paddle_unit_status.get(
                "unitStatus"
            )
            != "MATCH"
        ):
            continue

        evidence = {

            "text":
                paddle_text,

            "ocrScore":
                paddle.get(
                    "score"
                ),

            "metricId":
                paddle_metric_id,

            "standardName":
                get_standard_name(
                    paddle_match
                ),

            "matchScore":
                get_match_score(
                    paddle_match
                ),

            "margin":
                get_match_margin(
                    paddle_match
                ),
        }

        if (
            paddle_metric_id
            == rapid_metric_id
        ):

            votes.append(
                evidence
            )

        else:

            conflicts.append(
                evidence
            )

    # -----------------------------------------------------
    # 任何高质量标准指标冲突
    # 都不能自动通过
    # -----------------------------------------------------

    if conflicts:

        return {
            "accepted":
                False,

            "reason":
                "CANONICAL_METRIC_CONFLICT",

            "rapidMetricId":
                rapid_metric_id,

            "conflicts":
                conflicts,
        }

    if (
        len(votes)
        < MIN_CANONICAL_VOTES
    ):

        return {
            "accepted":
                False,

            "reason":
                "INSUFFICIENT_CANONICAL_VOTES",

            "rapidMetricId":
                rapid_metric_id,

            "votes":
                votes,
        }

    standard_name = (
        get_standard_name(
            rapid_match
        )
    )

    if not standard_name:

        return {
            "accepted":
                False,

            "reason":
                "CANONICAL_STANDARD_NAME_MISSING",
        }

    return {
        "accepted":
            True,

        # -------------------------------------------------
        # 这里与 Strong 模式不同：
        #
        # 我们已经确认的是“标准指标身份”，
        # 因此直接使用 canonical standardName。
        #
        # raw OCR 仍然保存在原始数据中。
        # -------------------------------------------------

        "candidate":
            standard_name,

        "reason":
            "RAPID_PADDLE_CANONICAL_CONSENSUS",

        "acceptanceMode":
            "CANONICAL_METRIC_CONSENSUS",

        "metricId":
            rapid_metric_id,

        "standardName":
            standard_name,

        "rapidEvidence": {

            "text":
                rapid_text,

            "matchScore":
                get_match_score(
                    rapid_match
                ),

            "margin":
                get_match_margin(
                    rapid_match
                ),
        },

        "paddleVotes":
            votes,
    }


# =========================================================
# Resolve
# =========================================================

def resolve_target(
    item,
    row,
    metrics,
    name_index,
):

    # =====================================================
    # 1. Strong OCR Text Consensus
    # =====================================================

    strong_result = (
        try_strong_text_consensus(
            item,
            name_index,
        )
    )

    if strong_result.get(
        "accepted"
    ):

        return {
            "decision":
                "ACCEPTED_CANDIDATE",

            **strong_result,
        }

    # =====================================================
    # 2. Canonical Metric Consensus
    # =====================================================

    canonical_result = (
        try_canonical_metric_consensus(
            item,
            row,
            metrics,
        )
    )

    if canonical_result.get(
        "accepted"
    ):

        return {
            "decision":
                "ACCEPTED_CANDIDATE",

            **canonical_result,
        }

    # =====================================================
    # 3. REVIEW
    # =====================================================

    return {
        "decision":
            "REVIEW",

        # Strong阶段如果已经形成 OCR 候选，
        # 可以保留作人工审核参考。
        "candidate":
            strong_result.get(
                "candidate"
            ),

        "reason":
            canonical_result.get(
                "reason"
            )
            or
            strong_result.get(
                "reason"
            ),

        "strongEvidence":
            strong_result,

        "canonicalEvidence":
            canonical_result,
    }


# =========================================================
# Main
# =========================================================

def main():

    rows_data = load_json(
        ROWS_PATH
    )

    round2_data = load_json(
        ROUND2_PATH
    )

    metrics = load_json(
        LIBRARY_PATH
    )

    row_map = build_row_map(
        rows_data.get(
            "rows",
            []
        )
    )

    name_index = (
        build_strong_name_index(
            metrics
        )
    )

    results = []

    print()
    print("=" * 120)
    print(
        "PoC 06-02C｜Round2 Evidence Fusion"
    )
    print("=" * 120)

    for item in round2_data.get(
        "results",
        []
    ):

        key = (
            item.get(
                "blockId"
            ),
            item.get(
                "rowIndex"
            ),
        )

        row = row_map.get(
            key,
            {}
        )

        decision = resolve_target(
            item,
            row,
            metrics,
            name_index,
        )

        output_item = {
            **item,
            **decision,
        }

        results.append(
            output_item
        )

        print()
        print(
            f"{item.get('targetId')} "
            f"| Rapid="
            f"{item.get('originalText')}"
        )

        print(
            f"  FINAL DECISION: "
            f"{decision['decision']}"
        )

        print(
            f"  CANDIDATE: "
            f"{decision.get('candidate')}"
        )

        print(
            f"  REASON: "
            f"{decision.get('reason')}"
        )

        if decision.get(
            "acceptanceMode"
        ):

            print(
                f"  MODE: "
                f"{decision.get('acceptanceMode')}"
            )

        if decision.get(
            "metricId"
        ):

            print(
                f"  CANONICAL: "
                f"{decision.get('standardName')} "
                f"({decision.get('metricId')})"
            )

        library_match = (
            decision.get(
                "libraryMatch"
            )
        )

        if library_match:

            print(
                f"  LIBRARY: "
                f"{library_match.get('standardName')} "
                f"({library_match.get('metricId')}) "
                f"| "
                f"{library_match.get('matchType')}"
            )

    # =====================================================
    # Summary
    # =====================================================

    accepted = sum(
        1
        for item in results
        if (
            item.get(
                "decision"
            )
            == "ACCEPTED_CANDIDATE"
        )
    )

    review = (
        len(results)
        - accepted
    )

    output = {

        "poc":
            "PoC 06-02C",

        "stage":
            "round2_evidence_fusion",

        "rules": {

            "minOcrScore":
                MIN_OCR_SCORE,

            "minTextVotes":
                MIN_TEXT_VOTES,

            "minCanonicalVotes":
                MIN_CANONICAL_VOTES,

            "priority": [
                "STRONG_TEXT_CONSENSUS",
                "CANONICAL_METRIC_CONSENSUS",
                "REVIEW",
            ],
        },

        "summary": {

            "total":
                len(results),

            "accepted":
                accepted,

            "review":
                review,
        },

        "results":
            results,
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
        f"ACCEPTED_CANDIDATE : "
        f"{accepted}"
    )

    print(
        f"REVIEW             : "
        f"{review}"
    )

    print()

    print(
        f"Saved: "
        f"{OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
