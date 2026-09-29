from pathlib import Path
import json
import re

from result_parser import (
    structure_row,
)

from report_context import (
    output_path,
)


BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_JSON = output_path(
    "_matched.json"
)

OUTPUT_JSON = output_path(
    "_structured.json"
)


ABNORMAL_PREFIX_PATTERN = re.compile(
    r"^\s*([↑↓])\s*"
)

ABNORMAL_SUFFIX_PATTERN = re.compile(
    r"(?<=\d)\s*([↑↓])\s*$"
)


def load_json(path):

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def extract_reference_abnormal(
    reference,
):
    """
    纸质报告中可能出现：

    ↓4.30~5.80
    ↑82.0~100.0

    箭头实际描述的是“当前结果”，
    而不是参考范围。

    返回：
    marker
    clean_reference
    """

    if not reference:
        return None, reference

    reference = reference.strip()

    match = (
        ABNORMAL_PREFIX_PATTERN
        .match(reference)
    )

    if match:
        marker = match.group(1)
        clean_reference = (
            ABNORMAL_PREFIX_PATTERN.sub(
                "",
                reference,
                count=1,
            )
        )
        return marker, clean_reference

    # 同一行的箭头也可能被 OCR 排在参考范围末尾。
    # 仅接受紧跟数字的单个尾随箭头，保留其它文本给后续校验。
    match = ABNORMAL_SUFFIX_PATTERN.search(
        reference
    )

    if match:
        return (
            match.group(1),
            reference[:match.start()].rstrip(),
        )

    return None, reference


def adapt_paper_row(row):

    adapted = dict(row)

    raw_result = (
        row.get("result")
        or ""
    )

    raw_reference = (
        row.get("reference")
        or ""
    )

    marker, clean_reference = (
        extract_reference_abnormal(
            raw_reference
        )
    )

    # 永远保留纸质 OCR 原始字段
    adapted["paperRawFields"] = {
        "result": raw_result,
        "reference": raw_reference,
    }

    adapted[
        "paperAbnormalMarker"
    ] = marker

    if marker:

        # result_parser 已验证：
        #
        # 119↓
        # 100.3↑
        #
        # 所以只在结构化输入层
        # 把纸质版式中的箭头移回结果。
        adapted["result"] = (
            f"{raw_result}{marker}"
        )

        adapted[
            "reference"
        ] = clean_reference

    return adapted


def main():

    data = load_json(
        INPUT_JSON
    )

    rows = data["rows"]

    output_rows = []

    stats = {
        "total": len(rows),
        "referenceArrowMoved": 0,
        "needConfirmation": 0,
        "validationConflict": 0,
    }

    print()
    print("=" * 120)
    print(
        "PoC 05-04｜纸质报告结果结构化"
    )
    print("=" * 120)

    for row in rows:

        adapted = (
            adapt_paper_row(
                row
            )
        )

        if adapted.get(
            "paperAbnormalMarker"
        ):
            stats[
                "referenceArrowMoved"
            ] += 1

        structured = (
            structure_row(
                adapted
            )
        )

        if structured.get(
            "confirmation",
            {},
        ).get("needConfirmation"):
            stats[
                "needConfirmation"
            ] += 1

        validation_status = (
            structured.get(
                "abnormal",
                {},
            ).get("validationStatus")
        )

        if (
            validation_status
            == "CONFLICT"
        ):
            stats[
                "validationConflict"
            ] += 1

        output_rows.append(
            structured
        )

    result = {
        "poc": "PoC 05-04",
        "stage":
            "paper_result_structuring",

        "summary": stats,

        "rows": output_rows,
    }

    with OUTPUT_JSON.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print("处理完成")
    print(
        f"总指标："
        f"{stats['total']}"
    )

    print(
        "参考范围箭头迁移："
        f"{stats['referenceArrowMoved']}"
    )

    print(
        "异常状态冲突："
        f"{stats['validationConflict']}"
    )

    print(
        "需人工确认："
        f"{stats['needConfirmation']}"
    )

    print()
    print(
        "输出："
        f"{OUTPUT_JSON}"
    )


if __name__ == "__main__":
    main()
