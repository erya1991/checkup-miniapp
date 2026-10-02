"""Product adapter around the frozen PoC scripts; no OCR rules live here."""

import json
import os
import shutil
import subprocess
import tempfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.core.config import get_settings
from app.core.cos import client

RUNTIME = Path(__file__).resolve().parents[1] / "ocr_runtime"
PIPELINE_VERSION = "poc-sha256:9f0c4c4c61351c84894a37cc4f44d3f8dd77003b40bcbd67a1bf34bc825ab6e6"


class OcrExecutionError(Exception):
    def __init__(self, code: str, recoverable: bool = False):
        self.code = code
        self.recoverable = recoverable
        super().__init__(code)


def decimal_value(value: object) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def map_row(row: dict, asset: dict, sequence_no: int,
            ocr_items: dict[int, dict] | None = None) -> dict:
    status = row.get("finalStatus")
    if status not in {"FINAL_AUTO", "FINAL_REVIEW"}:
        raise OcrExecutionError("OCR_OUTPUT_INVALID")
    raw = row.get("raw") or {}
    resolved = row.get("resolved") or {}
    match = row.get("metricMatch") or {}
    # UNMATCHED may retain a best candidate for audit, but it is not an identity.
    metric = (match.get("metric") or {}) if match.get("status") in {"AUTO_MATCHED", "REVIEW"} else {}
    validation = row.get("resultValidation") or {}
    structured = validation.get("structuredResult") or {}
    reference = validation.get("structuredReference") or {}
    unit = row.get("effectiveUnit") or {}
    abnormal = validation.get("abnormal") or {}
    reasons = row.get("finalReasons") or []
    source_indexes = validation.get("ocr_indexes") or {}
    result_indexes = source_indexes.get("result") or source_indexes.get("metric") or []
    source_ocr = (ocr_items or {}).get(result_indexes[0]) if result_indexes else None
    return {
        "sequence_no": sequence_no,
        "source_asset_id": asset["asset_id"], "page_no": asset["page_no"],
        "bbox": row.get("bbox") or (source_ocr or {}).get("bbox"),
        "raw_metric": raw.get("metric"), "raw_result": raw.get("result"),
        "raw_unit": raw.get("unit"), "raw_reference": raw.get("reference"),
        "standard_metric_code": metric.get("metricId"),
        "standard_metric_name": metric.get("standardName"),
        "result_text": structured.get("displayValue") or resolved.get("result"),
        "result_numeric": decimal_value(structured.get("numericValue")),
        "comparator": structured.get("comparator"),
        "normalized_unit": unit.get("normalizedUnit") or resolved.get("unit"),
        "reference_text": reference.get("displayValue") or resolved.get("reference"),
        "reference_low": decimal_value(reference.get("low")),
        "reference_high": decimal_value(reference.get("high")),
        "abnormal": abnormal.get("final"),
        "final_decision": status, "review_reasons": reasons,
        "review_category": row.get("reviewCategory"),
        "evidence": {"retry": row.get("retry"), "effectiveUnit": unit,
                     "resultValidation": validation, "metricMatch": row.get("metricMatch"),
                     "bbox_coordinate_space": "normalized_input"},
        "payload": row,
    }


def run_pipeline(task, user_id: str) -> tuple[list[dict], dict, dict, str]:
    """Read manifest in page order, run each page, then archive every output file."""
    cfg = get_settings()
    if not task.input_manifest or not cfg.cos_bucket:
        raise OcrExecutionError("OCR_INPUT_INVALID")
    work_parent = Path(cfg.ocr_work_dir).resolve()
    work_parent.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []
    candidates: dict = {}
    root = (f"users/{user_id}/ingestions/{task.ingestion_id}/ocr/"
            f"run-{task.run_no:03d}/attempt-{task.attempt_count:03d}/")
    with tempfile.TemporaryDirectory(prefix="ocr-", dir=work_parent) as name:
        work = Path(name)
        shutil.copytree(RUNTIME / "src", work / "src", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(RUNTIME / "data", work / "data")
        (work / "samples").mkdir()
        (work / "output").mkdir()
        ordered = sorted(task.input_manifest, key=lambda item: item["page_no"])
        if [a["page_no"] for a in ordered] != list(range(1, len(ordered) + 1)):
            raise OcrExecutionError("OCR_INPUT_ORDER_INVALID")
        for asset in ordered:
            report_id = f"page_{asset['page_no']:03d}"
            image = work / "samples" / f"{report_id}.jpg"
            try:
                response = client().get_object(Bucket=cfg.cos_bucket, Key=asset["cos_object_key"])
                with image.open("wb") as destination:
                    remaining = asset["file_size"] + 1
                    while remaining:
                        chunk = response["Body"].read(min(1024 * 1024, remaining))
                        if not chunk:
                            break
                        destination.write(chunk)
                        remaining -= len(chunk)
            except Exception as exc:
                raise OcrExecutionError("OCR_COS_READ_FAILED", recoverable=True) from exc
            if image.stat().st_size != asset["file_size"]:
                raise OcrExecutionError("OCR_INPUT_SIZE_MISMATCH")
            env = os.environ.copy()
            env["OCR_NORMAL_PYTHON"] = str(Path(cfg.ocr_normal_python).resolve())
            env["OCR_PADDLE_PYTHON"] = str(Path(cfg.ocr_paddle_python).resolve())
            env["OCR_PADDLE_MODEL_DIR"] = str(RUNTIME / "models" / "PP-OCRv6_medium_rec")
            env["PYTHONIOENCODING"] = "utf-8"
            result = subprocess.run(
                [env["OCR_NORMAL_PYTHON"], str(work / "src" / "report_pipeline.py"), report_id],
                cwd=work, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                check=False, timeout=cfg.ocr_page_timeout_seconds,
            )
            if result.returncode:
                raise OcrExecutionError("OCR_PIPELINE_FAILED")
            final_path = work / "output" / f"{report_id}_final_unit_resolved.json"
            summary_path = work / "output" / f"{report_id}_pipeline_summary.json"
            ocr_path = work / "output" / f"{report_id}_ocr.json"
            try:
                final = json.loads(final_path.read_text(encoding="utf-8"))
                pipeline = json.loads(summary_path.read_text(encoding="utf-8"))
                ocr = json.loads(ocr_path.read_text(encoding="utf-8"))
                ocr_items = {item["index"]: item for item in ocr.get("items", [])}
                if pipeline.get("pipelineStatus") != "SUCCESS" or not final.get("rows"):
                    raise OcrExecutionError("OCR_OUTPUT_INVALID")
                for row in final["rows"]:
                    all_rows.append(map_row(row, asset, len(all_rows) + 1, ocr_items))
            except (OSError, ValueError, TypeError, KeyError) as exc:
                raise OcrExecutionError("OCR_OUTPUT_INVALID") from exc
        # Upload all produced JSON and working images, including retry/evidence stages.
        # Original ReportAsset objects remain untouched in their original/ prefix.
        try:
            for artifact in (work / "output").rglob("*"):
                if artifact.is_file():
                    key = root + artifact.relative_to(work / "output").as_posix()
                    with artifact.open("rb") as body:
                        client().put_object(Bucket=cfg.cos_bucket, Key=key, Body=body)
            manifest = {"pipeline_version": PIPELINE_VERSION,
                        "pages": [{"page_no": a["page_no"], "asset_id": a["asset_id"]}
                                  for a in ordered]}
            client().put_object(Bucket=cfg.cos_bucket, Key=root + "manifest.json",
                                Body=json.dumps(manifest).encode("utf-8"))
        except Exception as exc:
            raise OcrExecutionError("OCR_ARTIFACT_WRITE_FAILED", recoverable=True) from exc
    auto = sum(row["final_decision"] == "FINAL_AUTO" for row in all_rows)
    result_summary = {"total_count": len(all_rows), "auto_count": auto,
                      "review_count": len(all_rows) - auto}
    return all_rows, candidates, result_summary, root
