# src/report_context.py

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


DEFAULT_REPORT_ID = "paper_report_01"


def get_report_id():
    """
    报告唯一标识。

    优先读取环境变量 REPORT_ID。

    report_pipeline.py 后续会统一设置该变量，
    所有子脚本不需要分别解析命令行参数。

    当前为了兼容旧执行方式，
    未设置时默认仍使用 paper_report_01。
    """

    report_id = os.environ.get(
        "REPORT_ID",
        DEFAULT_REPORT_ID,
    ).strip()

    if not report_id:
        report_id = DEFAULT_REPORT_ID

    # 基础安全限制：
    # report_id 只允许作为文件名，
    # 不允许包含目录。
    if (
        "/" in report_id
        or "\\" in report_id
        or ".." in report_id
    ):
        raise ValueError(
            f"非法 report_id: {report_id}"
        )

    return report_id


def sample_path(
    suffix=".jpg",
):
    report_id = get_report_id()

    return (
        PROJECT_ROOT
        / "samples"
        / f"{report_id}{suffix}"
    )


def output_path(
    suffix,
):
    """
    例如：

    output_path("_ocr.json")
    →
    output/paper_report_01_ocr.json
    """

    report_id = get_report_id()

    return (
        PROJECT_ROOT
        / "output"
        / f"{report_id}{suffix}"
    )