"""Run the vendored Pipeline on a caller-supplied permitted test image.

Arguments: image normal-python paddle-python
This uses an in-memory COS stand-in; real private COS is a separate acceptance gate.
"""

import io
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

from app import ocr_pipeline


def main() -> None:
    image_path = Path(sys.argv[1])
    image = image_path.read_bytes()
    mime_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    normal_python, paddle_python = sys.argv[2:4]
    artifacts = []

    class FakeCos:
        def get_object(self, **_kwargs):
            return {"Body": io.BytesIO(image)}

        def put_object(self, **kwargs):
            artifacts.append(kwargs["Key"])

    with tempfile.TemporaryDirectory(prefix="stage03-smoke-") as directory:
        ocr_pipeline.client = FakeCos
        ocr_pipeline.get_settings = lambda: SimpleNamespace(
            cos_bucket="private-test", ocr_work_dir=directory,
            ocr_normal_python=normal_python, ocr_paddle_python=paddle_python,
            ocr_page_timeout_seconds=1800,
        )
        task = SimpleNamespace(
            id="smoke-task", ingestion_id="smoke-ingestion", run_no=1, attempt_count=1,
            input_manifest=[{"asset_id": "test-image", "page_no": 1,
                             "cos_object_key": "synthetic/test" + image_path.suffix,
                             "mime_type": mime_type,
                             "file_size": len(image)}],
        )
        rows, _, summary, root = ocr_pipeline.run_pipeline(task, "smoke-user")
        assert len(rows) == summary["total_count"]
        assert summary["total_count"] == summary["auto_count"] + summary["review_count"]
        assert any(key.endswith("_ocr.json") for key in artifacts)
        assert any(key.endswith("_final_unit_resolved.json") for key in artifacts)
        assert all(key.startswith(root) for key in artifacts)
        assert not list(Path(directory).iterdir()), "temporary OCR work directory was not cleaned"
        print(f"vendored Pipeline smoke: PASS; rows={len(rows)}; artifacts={len(artifacts)}")


if __name__ == "__main__":
    main()
