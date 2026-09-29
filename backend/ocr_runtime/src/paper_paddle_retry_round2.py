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

ROUND2_RETRY_DIR = (
    BASE_DIR
    / "output"
    / REPORT_ID
    / "paper_retry_round2"
)

MANIFEST_PATH = (
    ROUND2_RETRY_DIR
    / "paper_retry_round2_manifest.json"
)

OUTPUT_PATH = (
    ROUND2_RETRY_DIR
    / "paper_paddle_retry_round2.json"
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

    if isinstance(result, dict):
        return result

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


def decide(variants):

    valid = [
        item
        for item in variants
        if (
            item["text"]
            and item["score"] is not None
        )
    ]

    if len(valid) != 3:

        return {
            "decision": "REVIEW",
            "candidate": None,
            "reason":
                "INCOMPLETE_ROUND2_RESULTS",
        }

    texts = [
        normalize_text(
            item["text"]
        )
        for item in valid
    ]

    if len(set(texts)) != 1:

        return {
            "decision": "REVIEW",
            "candidate": None,
            "reason":
                "ROUND2_VARIANTS_DISAGREE",
        }

    if not all(
        item["score"] >= MIN_SCORE
        for item in valid
    ):

        return {
            "decision": "REVIEW",
            "candidate":
                valid[0]["text"],
            "reason":
                "ROUND2_LOW_SCORE",
        }

    return {
        "decision":
            "ACCEPTED_CANDIDATE",

        "candidate":
            valid[0]["text"],

        "reason":
            "ROUND2_FULL_CELL_AGREEMENT_HIGH_SCORE",
    }


def main():

    manifest = load_json(
        MANIFEST_PATH
    )

    model = TextRecognition(
        model_name=MODEL_NAME,
        model_dir=os.environ.get("OCR_PADDLE_MODEL_DIR") or None,
        device="cpu",
    )

    results = []

    print()
    print("=" * 110)
    print(
        "PoC 05-05D｜Round2 Full Cell Paddle Retry"
    )
    print("=" * 110)

    for target in manifest[
        "targets"
    ]:

        variants = []

        for (
            variant_name,
            rel_path,
        ) in target[
            "variants"
        ].items():

            path = (
                BASE_DIR
                / rel_path
            )

            output = model.predict(
                input=str(path),
                batch_size=1,
            )

            text, score = (
                extract_recognition(
                    output
                )
            )

            variants.append(
                {
                    "variant":
                        variant_name,

                    "text":
                        text,

                    "score":
                        score,
                }
            )

        decision = decide(
            variants
        )

        result = {
            **target,

            "paddleResults":
                variants,

            **decision,
        }

        results.append(
            result
        )

        print()
        print(
            f"{target['targetId']} "
            f"| Rapid="
            f"{target['originalText']}"
        )

        for item in variants:

            score_text = (
                f"{item['score']:.4f}"
                if item["score"]
                is not None
                else "-"
            )

            print(
                f"  "
                f"{item['variant']:<20}"
                f" → "
                f"{str(item['text']):<25}"
                f" score="
                f"{score_text}"
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

    result_json = {
        "poc": "PoC 05-05D",

        "stage":
            "paper_paddle_retry_round2",

        "strategy":
            "FULL_METRIC_CELL_CROP",

        "minScore":
            MIN_SCORE,

        "results":
            results,
    }

    with OUTPUT_PATH.open(
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
        f"Saved: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
