# Frozen OCR runtime for Stage 03

Source: `D:\chen\project list\checkup-ocr-poc` local verified PoC snapshot, 2026-09-29. That PoC directory has no Git commits; its `src/*.py`, `data/metric_library.json`, and `data/unit_semantics.json` (33 files before pruning) have aggregate SHA-256 `9f0c4c4c61351c84894a37cc4f44d3f8dd77003b40bcbd67a1bf34bc825ab6e6` when sorted by relative path and hashed as path bytes followed by file bytes.

Only the scripts needed by `report_pipeline.py` and their direct imports are retained here. The algorithm rules, metric library, and unit semantics are copied unchanged. Product packaging changes are limited to:

- `report_pipeline.py`: normal and Paddle interpreter paths can be supplied through `OCR_NORMAL_PYTHON` and `OCR_PADDLE_PYTHON`.
- `paper_paddle_retry.py` and `paper_paddle_retry_round2.py`: `OCR_PADDLE_MODEL_DIR` supplies the bundled model directory.
- `app/ocr_pipeline.py`: creates isolated per-task work directories, copies this runtime, feeds ordered COS images, and archives Pipeline output. It does not alter OCR decisions.

Bundled model: `PP-OCRv6_medium_rec` CPU, copied from the verified local PaddleX official model cache. `inference.pdiparams` SHA-256: `1b01c79a914587933f615569e75de54f2e638ebb5d3f3b3c1b38c24ede8c7319`. The model files remain private to the backend deployment; the application never sends them to the miniapp.

The PaddleOCR `models/PP-OCRv6_medium_rec/inference.pdiparams` model is managed by Git LFS (about 76 MB). On a new machine, server, or fresh clone, install Git LFS and run `git lfs pull` after cloning. A file of about 133 bytes is only an LFS pointer, not the complete model. Confirm the full model has been pulled before starting the OCR Worker.

Verified Python packages: see `backend/pyproject.toml` `ocr` extra and `backend/ocr-paddle-requirements.txt`. Normal and Paddle interpreters are separate because their verified NumPy/OpenCV versions differ. Production runtime reads these files and this bundled model from `backend/`; no sibling PoC checkout is required. The PoC remains the source of algorithm regression and frozen baselines.
