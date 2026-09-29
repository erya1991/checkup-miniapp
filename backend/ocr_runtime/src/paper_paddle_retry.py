import json
import os
import re
import unicodedata
from pathlib import Path

from paddleocr import TextRecognition

from report_context import (
    get_report_id,
)


BASE_DIR = Path(__file__).resolve().parent.parent
REPORT_ID = get_report_id()

# =========================================================
# 当前报告独立 Round1 Retry 目录
# =========================================================

RETRY_DIR = (
    BASE_DIR
    / "output"
    / REPORT_ID
    / "paper_retry"
)

MANIFEST_PATH = (
    RETRY_DIR
    / "paper_retry_manifest.json"
)

OUTPUT_PATH = (
    RETRY_DIR
    / "paper_paddle_retry.json"
)


MODEL_NAME = "PP-OCRv6_medium_rec"

MIN_SCORE = 0.95


def load_json(path):

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def normalize_text(text):

    text = unicodedata.normalize(
        "NFKC",
        text or "",
    )

    text = re.sub(
        r"\s+",
        "",
        text,
    )

    return text.strip()


def result_to_dict(result):
    """
    兼容 PaddleOCR / PaddleX 不同版本的
    Result 对象。
    """

    if isinstance(result, dict):
        return result

    # PaddleX Result 常见 json 属性
    if hasattr(result, "json"):

        value = result.json

        if callable(value):
            value = value()

        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                pass

        if isinstance(value, dict):
            return value

    if hasattr(result, "to_dict"):

        value = result.to_dict()

        if isinstance(value, dict):
            return value

    return {}


def extract_recognition(output):

    output = list(output)

    if not output:
        return None, None

    data = result_to_dict(
        output[0]
    )

    # 常见：
    # {
    #   "res": {
    #       "rec_text": "...",
    #       "rec_score": 0.99
    #   }
    # }

    if "res" in data:
        data = data["res"]

    text = data.get(
        "rec_text"
    )

    score = data.get(
        "rec_score"
    )

    if text is None:
        return None, None

    try:
        score = float(score)
    except Exception:
        score = None

    return str(text), score


def decide_candidate(
    original_text,
    variants,
):
    """
    自动采用规则仍沿用电子报告阶段原则：

    1. 至少有两个有效 Paddle 结果
    2. 所有有效版本结果一致
    3. 所有有效结果 score >= 0.95
    4. 与 RapidOCR 原始值不同

    否则不自动修改。
    """

    valid = [
        item
        for item in variants
        if item["text"]
        and item["score"] is not None
    ]

    if len(valid) < 2:
        return {
            "decision": "REVIEW",
            "candidate": None,
            "reason":
                "INSUFFICIENT_PADDLE_RESULTS",
        }

    normalized = [
        normalize_text(
            item["text"]
        )
        for item in valid
    ]

    same = (
        len(set(normalized)) == 1
    )

    scores_ok = all(
        item["score"] >= MIN_SCORE
        for item in valid
    )

    if not same:
        return {
            "decision": "REVIEW",
            "candidate": None,
            "reason":
                "PADDLE_VARIANTS_DISAGREE",
        }

    candidate = valid[0]["text"]

    if not scores_ok:
        return {
            "decision": "REVIEW",
            "candidate": candidate,
            "reason":
                "LOW_PADDLE_SCORE",
        }

    if (
        normalize_text(candidate)
        ==
        normalize_text(original_text)
    ):
        # 对这批字段来说：
        # Paddle 与 Rapid 一致并不代表问题已经解决，
        # 因为这些字段本来就是高风险字段。
        return {
            "decision": "REVIEW",
            "candidate": candidate,
            "reason":
                "AGREES_WITH_RAPID_BUT_RISK_REMAINS",
        }

    return {
        "decision":
            "ACCEPTED_CANDIDATE",

        "candidate":
            candidate,

        "reason":
            "MULTI_VARIANT_AGREEMENT_HIGH_SCORE",
    }


def main():

    manifest = load_json(
        MANIFEST_PATH
    )

    print(
        f"Loading Paddle model: "
        f"{MODEL_NAME}"
    )

    model = TextRecognition(
        model_name=MODEL_NAME,
        model_dir=os.environ.get("OCR_PADDLE_MODEL_DIR") or None,
        device="cpu",
    )

    results = []

    print()
    print("=" * 120)
    print(
        "PoC 05-05｜PaddleOCR Paper Retry"
    )
    print("=" * 120)

    for target in manifest[
        "targets"
    ]:

        variant_results = []

        for variant_name, rel_path in (
            target["variants"].items()
        ):

            image_path = (
                BASE_DIR
                / rel_path
            )

            try:

                output = model.predict(
                    input=str(image_path),
                    batch_size=1,
                )

                text, score = (
                    extract_recognition(
                        output
                    )
                )

            except Exception as e:

                text = None
                score = None

                print(
                    f"[ERROR] "
                    f"{target['targetId']} "
                    f"{variant_name}: {e}"
                )

            variant_results.append(
                {
                    "variant":
                        variant_name,

                    "text":
                        text,

                    "score":
                        score,
                }
            )

        decision = decide_candidate(
            target["originalText"],
            variant_results,
        )

        result = {
            **target,

            "paddleResults":
                variant_results,

            **decision,
        }

        results.append(result)

        print()
        print(
            f"{target['targetId']} "
            f"| {target['field']} "
            f"| Rapid={target['originalText']}"
        )

        for item in variant_results:

            score_text = (
                f"{item['score']:.4f}"
                if item["score"] is not None
                else "-"
            )

            print(
                f"  {item['variant']:<15}"
                f" → "
                f"{str(item['text']):<25}"
                f" score={score_text}"
            )

        print(
            f"  DECISION: "
            f"{decision['decision']}"
        )

        print(
            f"  CANDIDATE: "
            f"{decision['candidate']}"
        )

        print(
            f"  REASON: "
            f"{decision['reason']}"
        )

    output = {
        "poc": "PoC 05-05",

        "stage":
            "paper_paddle_retry",

        "model":
            MODEL_NAME,

        "minScore":
            MIN_SCORE,

        "targetCount":
            len(results),

        "results":
            results,
    }

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
        f"Saved: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
