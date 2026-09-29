# src/report_pipeline.py

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from report_context import (
    DEFAULT_REPORT_ID,
)


# =========================================================
# Project
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

SRC_DIR = BASE_DIR / "src"

OUTPUT_DIR = BASE_DIR / "output"


# =========================================================
# Python environments
# =========================================================

NORMAL_PYTHON = Path(os.environ.get("OCR_NORMAL_PYTHON", str(BASE_DIR / ".venv" / "Scripts" / "python.exe")))

PADDLE_PYTHON = Path(os.environ.get("OCR_PADDLE_PYTHON", str(
    BASE_DIR / ".venv-paddle" / "Scripts" / "python.exe")))


# =========================================================
# Pipeline stages
# =========================================================

PIPELINE_STAGES = [

    {
        "stage": "01",
        "name": "RapidOCR Baseline",
        "script": "paper_ocr_baseline.py",
        "env": "normal",
    },

    {
        "stage": "02",
        "name": "Layout Detection",
        "script": "paper_layout_parser.py",
        "env": "normal",
    },

    {
        "stage": "03",
        "name": "Block Row Reconstruction",
        "script": "paper_row_parser.py",
        "env": "normal",
    },

    {
        "stage": "04",
        "name": "Metric Matching",
        "script": "paper_metric_matcher.py",
        "env": "normal",
    },

    {
        "stage": "05",
        "name": "Result Structuring",
        "script": "paper_result_parser.py",
        "env": "normal",
    },

    # =====================================================
    # PoC 06-02
    # 自动发现风险字段
    # =====================================================

    {
        "stage": "06",
        "name": "Dynamic Retry Target Selector",
        "script": "paper_retry_selector.py",
        "env": "normal",
    },

    {
        "stage": "07",
        "name": "Dynamic Round1 Retry Prepare",
        "script": "paper_retry_prepare.py",
        "env": "normal",
    },

    {
        "stage": "08",
        "name": "PaddleOCR Round1",
        "script": "paper_paddle_retry.py",
        "env": "paddle",
    },

    # =====================================================
    # Round2
    #
    # 当前暂时保留 PoC 05 已验证版本。
    # 下一阶段再动态化。
    # =====================================================

    {
    "stage": "08",
    "name": "PaddleOCR Round1",
    "script": "paper_paddle_retry.py",
    "env": "paddle",
},

{
    "stage": "09",
    "name": "Dynamic Round2 Target Selector",
    "script": "paper_retry_round2_selector.py",
    "env": "normal",
},

{
    "stage": "10",
    "name": "Dynamic Round2 Full Cell Prepare",
    "script": "paper_retry_round2_prepare.py",
    "env": "normal",
},

{
    "stage": "11",
    "name": "PaddleOCR Round2",
    "script": "paper_paddle_retry_round2.py",
    "env": "paddle",
},

{
    "stage": "12",
    "name": "Round2 Evidence Fusion",
    "script": "paper_retry_round2_resolve.py",
    "env": "normal",
},

{
    "stage": "13",
    "name": "Apply OCR Retry + Final Validation",
    "script": "paper_retry_apply.py",
    "env": "normal",
},

{
    "stage": "14",
    "name": "Unit Semantic Resolution",
    "script": "paper_unit_resolver.py",
    "env": "normal",
},

{
    "stage": "15",
    "name": "Final Unit-aware Validation",
    "script": "paper_final_unit_apply.py",
    "env": "normal",
},
]


# =========================================================
# Helpers
# =========================================================

def ensure_environment():

    errors = []

    if not NORMAL_PYTHON.exists():

        errors.append(
            f"未找到普通 Python 环境："
            f"{NORMAL_PYTHON}"
        )

    if not PADDLE_PYTHON.exists():

        errors.append(
            f"未找到 Paddle Python 环境："
            f"{PADDLE_PYTHON}"
        )

    if errors:

        print()
        print("=" * 100)
        print("环境检查失败")
        print("=" * 100)

        for error in errors:
            print(error)

        raise SystemExit(1)


def get_python(env_name):

    if env_name == "paddle":
        return PADDLE_PYTHON

    return NORMAL_PYTHON


def parse_args():

    parser = argparse.ArgumentParser(
        description="纸质检验报告 OCR Pipeline"
    )

    parser.add_argument(
        "report_id",
        nargs="?",
        default=DEFAULT_REPORT_ID,
        help="samples 目录中的报告文件名，不包含扩展名",
    )

    args = parser.parse_args()
    report_id = args.report_id.strip()

    if (
        not report_id
        or "/" in report_id
        or "\\" in report_id
        or ".." in report_id
    ):
        parser.error(
            "report_id 不能为空，也不能包含 /、\\ 或 .."
        )

    return report_id


def build_report_paths(report_id):

    return {
        "final_result": (
            OUTPUT_DIR
            / f"{report_id}_final_unit_resolved.json"
        ),
        "pipeline_summary": (
            OUTPUT_DIR
            / f"{report_id}_pipeline_summary.json"
        ),
    }


def run_stage(
    stage,
    report_id,
):

    script_path = (
        SRC_DIR
        / stage["script"]
    )

    if not script_path.exists():

        return {
            "stage": stage["stage"],
            "name": stage["name"],
            "script": stage["script"],
            "status": "FAILED",
            "returnCode": None,
            "error":
                f"脚本不存在：{script_path}",
        }

    python_path = get_python(
        stage["env"]
    )

    print()
    print()
    print("#" * 120)

    print(
        f"PIPELINE STAGE "
        f"{stage['stage']} "
        f"| "
        f"{stage['name']}"
    )

    print("#" * 120)

    print(
        f"Environment : "
        f"{stage['env']}"
    )

    print(
        f"Python      : "
        f"{python_path}"
    )

    print(
        f"Script      : "
        f"{stage['script']}"
    )

    print()

    started_at = datetime.now()

    child_env = os.environ.copy()
    child_env["REPORT_ID"] = report_id
    child_env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        [
            str(python_path),
            str(script_path),
        ],
        cwd=str(BASE_DIR),
        env=child_env,
        check=False,
    )

    finished_at = datetime.now()

    duration = (
        finished_at
        - started_at
    ).total_seconds()

    if result.returncode == 0:

        status = "SUCCESS"
        error = None

    else:

        status = "FAILED"

        error = (
            f"Stage returned "
            f"{result.returncode}"
        )

    return {
        "stage":
            stage["stage"],

        "name":
            stage["name"],

        "script":
            stage["script"],

        "environment":
            stage["env"],

        "status":
            status,

        "returnCode":
            result.returncode,

        "durationSeconds":
            round(
                duration,
                2,
            ),

        "error":
            error,
    }


# =========================================================
# Final summary
# =========================================================

def load_final_result(final_result_path):

    if not final_result_path.exists():
        return None

    with final_result_path.open(
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


def build_pipeline_summary(
    stage_results,
    started_at,
    finished_at,
    report_id,
    final_result_path,
):

    final_result = (
        load_final_result(
            final_result_path
        )
    )

    final_summary = None

    if final_result:

        final_summary = (
            final_result.get(
                "summary"
            )
        )

    success_count = sum(
        1
        for item in stage_results
        if item["status"] == "SUCCESS"
    )

    failed_count = sum(
        1
        for item in stage_results
        if item["status"] == "FAILED"
    )

    return {

        "pipeline":
            "PoC 06-01",

        "report":
            report_id,

        "startedAt":
            started_at.isoformat(),

        "finishedAt":
            finished_at.isoformat(),

        "durationSeconds":
            round(
                (
                    finished_at
                    - started_at
                ).total_seconds(),
                2,
            ),

        "stageCount":
            len(stage_results),

        "successStages":
            success_count,

        "failedStages":
            failed_count,

        "pipelineStatus":
            (
                "SUCCESS"
                if failed_count == 0
                else "FAILED"
            ),

        "finalResult":
            final_summary,

        "stages":
            stage_results,
    }


def save_pipeline_summary(
    summary,
    pipeline_summary_path,
):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with pipeline_summary_path.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            summary,
            f,
            ensure_ascii=False,
            indent=2,
        )


# =========================================================
# Terminal summary
# =========================================================

def print_final_summary(
    summary,
    pipeline_summary_path,
    final_result_path,
):

    print()
    print()
    print("=" * 120)

    print(
        "PoC 06-01｜REPORT PIPELINE SUMMARY"
    )

    print("=" * 120)

    print(
        f"Pipeline status : "
        f"{summary['pipelineStatus']}"
    )

    print(
        f"Stages          : "
        f"{summary['successStages']}"
        f"/"
        f"{summary['stageCount']}"
    )

    print(
        f"Duration        : "
        f"{summary['durationSeconds']} s"
    )

    final_result = (
        summary.get(
            "finalResult"
        )
    )

    if final_result:

        print()

        print(
            f"Total metrics    : "
            f"{final_result.get('total')}"
        )

        print(
            f"FINAL_AUTO       : "
            f"{final_result.get('finalAuto')}"
        )

        print(
            f"FINAL_REVIEW     : "
            f"{final_result.get('finalReview')}"
        )

        print(
            f"Auto pass rate   : "
            f"{final_result.get('finalAutoRate')}%"
        )

    print()

    print(
        f"Pipeline summary : "
        f"{pipeline_summary_path}"
    )

    print(
        f"Final report     : "
        f"{final_result_path}"
    )

    print("=" * 120)


# =========================================================
# Main
# =========================================================

def main():

    report_id = parse_args()
    os.environ["REPORT_ID"] = report_id

    report_paths = build_report_paths(
        report_id
    )
    final_result_path = report_paths[
        "final_result"
    ]
    pipeline_summary_path = report_paths[
        "pipeline_summary"
    ]

    sample_image = (
        BASE_DIR
        / "samples"
        / f"{report_id}.jpg"
    )

    if not sample_image.exists():
        raise SystemExit(
            "Sample image not found:\n"
            f"samples/{report_id}.jpg"
        )

    print()
    print("=" * 120)

    print(
        "PoC 06-01｜纸质检验报告完整流水线"
    )

    print("=" * 120)

    print()

    print(
        f"Report ID : {report_id}"
    )

    print(
        "说明：当前流程按 report_id 隔离报告与 Retry 输出。"
    )

    ensure_environment()

    pipeline_started_at = (
        datetime.now()
    )

    stage_results = []

    # =====================================================
    # Execute
    # =====================================================

    for stage in PIPELINE_STAGES:

        result = run_stage(
            stage,
            report_id,
        )

        stage_results.append(
            result
        )

        if (
            result["status"]
            != "SUCCESS"
        ):

            print()
            print("=" * 120)

            print(
                f"PIPELINE STOPPED"
            )

            print(
                f"Stage "
                f"{result['stage']} "
                f"failed:"
            )

            print(
                result["name"]
            )

            print(
                result["error"]
            )

            print("=" * 120)

            break

    pipeline_finished_at = (
        datetime.now()
    )

    # =====================================================
    # Summary
    # =====================================================

    summary = (
        build_pipeline_summary(
            stage_results,
            pipeline_started_at,
            pipeline_finished_at,
            report_id,
            final_result_path,
        )
    )

    save_pipeline_summary(
        summary,
        pipeline_summary_path,
    )

    print_final_summary(
        summary,
        pipeline_summary_path,
        final_result_path,
    )

    # =====================================================
    # Process exit status
    # =====================================================

    if (
        summary[
            "pipelineStatus"
        ]
        != "SUCCESS"
    ):

        sys.exit(1)


# =========================================================
# Entry
# =========================================================

if __name__ == "__main__":
    main()
