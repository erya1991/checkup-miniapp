# Stage 03｜OCR Worker 正式接入与待确认结果生成：实施结果

**状态：PASS（2026-09-29）**。代码、迁移、自动测试、PostgreSQL 队列、PoC Regression 和真实私有 COS / Worker 工程闭环已通过；项目负责人随后反馈真实微信主流程、页面恢复、Worker 停启恢复及任务记录回访均通过。按 `ACCEPTANCE.md` 核对，Stage 03 P0 已满足。本阶段止于 `ReportIngestion.PENDING_CONFIRMATION`，未进入 Stage 04；真实微信人工验收结论来自项目负责人反馈，Codex 未独立操作微信开发者工具。

## 1. 实际完成项

- 从 `READY` 原子创建 `OcrTask.QUEUED`，冻结按 `page_no` 排序的 `asset_id / page_no / cos_object_key / mime_type / file_size` manifest。重复 recognize 返回当前任务；失败后的显式 retry 创建 `run_no + 1`。
- 上传授权、Asset 登记、排序、删除在识别开始后由后端返回 `INGESTION_INPUT_FROZEN`；原图签名预览继续可用。
- PostgreSQL 队列用 `FOR UPDATE SKIP LOCKED` 领取，保存 worker/lease/attempt/退避状态。独立 Worker 固定单任务处理，并用 PostgreSQL advisory lock 阻止同一数据库启动第二个活跃 Worker；异常退出可在 lease 到期后重领，最多 3 次自动尝试。
- Worker 按 manifest 从私有 COS 下载原图，在隔离临时目录按页调用已验证 Pipeline。各 run/attempt 的 raw OCR、layout、rows、matcher、retry/evidence、unit、final 和规范化工作图等实际输出上传到私有 COS；原始 ReportAsset 不覆盖。成功后持久化不可编辑的 `OcrResultItem`、汇总及 `PENDING_CONFIRMATION`；`FINAL_REVIEW` 仍属于成功。
- J03 发现的固定 30 分钟 lease 已改为 `OCR_TASK_LEASE_SECONDS`，默认仍为 1800 秒；领取与续租使用同一配置，heartbeat 在短 lease 下相应缩短。本地人工 J03 使用 120 秒，仅为验收配置，不改变默认生产语义。
- 小程序 READY 页接真实“开始识别”，识别后图片只读；P06 从数据库状态 API 显示 QUEUED、PROCESSING、待确认和失败，失败可显式创建新 run。没有逐项确认、commit 或正式报告能力。
- 人工验收发现新建第二份任务后旧的 `PENDING_CONFIRMATION` 缺少入口；首页增加“识别任务记录”，列表由 `/api/v1/ingestions?health_profile_id=...` 按当前用户和档案筛选、创建时间倒序读取。每条显示创建时间、图片数、状态及成功 OCR 汇总；复用上传页和 OCR 状态页打开旧任务，保留“新建另一份上传任务”。

## 2. 实际变更文件

- 数据与后端：`backend/migrations/versions/0003_ocr.py`、`backend/app/models/entities.py`、`backend/app/models/__init__.py`、`backend/app/api/v1/ocr.py`、`backend/app/api/v1/business.py`、`backend/app/ocr_queue.py`、`backend/app/ocr_worker.py`、`backend/app/ocr_pipeline.py`、`backend/app/main.py`、`backend/app/db/session.py`、`backend/app/core/config.py`、`backend/pyproject.toml`、`backend/ocr-paddle-requirements.txt`。
- 冻结运行时：`backend/ocr_runtime/src/` 中 21 个 PoC Pipeline/依赖脚本，`backend/ocr_runtime/data/metric_library.json`、`unit_semantics.json`，`backend/ocr_runtime/models/PP-OCRv6_medium_rec/` 的 5 个模型/说明文件，以及 `backend/ocr_runtime/README.md`。
- 验证：`backend/tests/test_stage03.py`、`backend/tests/verify_postgres_queue.py`、`backend/tests/verify_pipeline_smoke.py`、`backend/tests/make_synthetic_report.py`、`backend/tests/verify_private_cos_pipeline.py`。
- 前端：`miniapp/src/api.ts`、`miniapp/src/pages.json`、`miniapp/src/pages/index/index.vue`、`miniapp/src/pages/upload/index.vue`、`miniapp/src/pages/ocr/index.vue`、`miniapp/src/pages/ingestion-tasks/index.vue`、`miniapp/src/ingestion-tasks.ts`、`miniapp/tests/ingestion-tasks.test.mjs`、`miniapp/package.json`。
- 配置及文档：`.env.example`、`.gitignore`、根 `README.md`、`backend/README.md`、本 `RESULT.md`。Stage 03 的 `PLAN.md` 与 `ACCEPTANCE.md` 为实施前已存在的未跟踪文件，本次没有改写。

## 3. Migration 与 Pipeline 来源

- 现有本地 PostgreSQL 17 数据库：`alembic current` 起点 `0002_profile_upload`，`alembic upgrade head` 成功到 `0003_ocr`。独立唯一命名临时空库完整执行 `0001 → 0002 → 0003` 并在验证后删除。
- PoC source：`D:\chen\project list\checkup-ocr-poc`。该本地 PoC 目录 **没有 Git commit**；其原始 `src/*.py` + `metric_library.json` + `unit_semantics.json` 共 33 文件的内容快照 SHA-256 为 `9f0c4c4c61351c84894a37cc4f44d3f8dd77003b40bcbd67a1bf34bc825ab6e6`。产品只保留运行依赖脚本，算法规则和指标库未改；适配只涉及解释器/模型路径及产品侧输入输出包装。
- OCR 依赖从实际 PoC 两套 `.venv` 读取：普通环境 RapidOCR 3.9.2、ONNX Runtime 1.30.0、OpenCV 5.0.0.93、NumPy 2.5.3、Shapely 2.1.2、Pillow 12.3.0、RapidFuzz 3.14.6；Paddle 环境 PaddleOCR 3.7.0、PaddlePaddle 3.3.0、PaddleX 3.7.2、NumPy 2.3.5、OpenCV contrib 4.10.0.84、Pillow 12.1.0。模型 `PP-OCRv6_medium_rec` 的 `inference.pdiparams` SHA-256 为 `1b01c79a914587933f615569e75de54f2e638ebb5d3f3b3c1b38c24ede8c7319`，已复制到产品后端。
- 生产代码通过后端内 `ocr_runtime/`、两套配置解释器和私有 COS 工作，不依赖 PoC sibling 路径；独立安装与启动命令见 README。

## 4. 实际自动与集成验证

| 验证 | 实际结果 |
| --- | --- |
| PoC Frozen Regression：`.\.venv\Scripts\python.exe tests\run_regression.py` | 原 PoC snapshot 3/3 PASS；Core logic 15/15 PASS；Safety Regression 0。首次只读沙箱运行因无法写 PoC `output/` 失败，获授权重跑后通过；未改 frozen baseline |
| Backend pytest：`.venv\Scripts\python.exe -m pytest -q` | 17 passed，0 failed；1 条上游 TestClient 弃用警告。覆盖 Stage 02 原有测试、recognize/冻结/权限/retry、REVIEW 成功、有限自动重试、失败临时目录清理、lease 配置、旧成功任务可达及跨用户/档案隔离 |
| Ruff：`.venv\Scripts\ruff.exe check . --no-cache` | PASS；冻结 PoC 源码由 `ocr_runtime` 排除出产品 Ruff 规则，避免自动改写已验证算法 |
| PostgreSQL 17 queue：`tests/verify_postgres_queue.py` | PASS：双 session `SKIP LOCKED`、单 Worker advisory lock、2 秒自定义 lease 的领取与续租、实际到期后的新 Worker 重领、旧 worker 不得结算、`UNIQUE(ingestion_id, run_no)`。使用独立临时库并删除 |
| 已验证 PoC 测试图的产品 Pipeline smoke | PASS：24 行、60 个输出文件；使用内存 COS 替身与 PoC 解释器，不作为真实 COS 证据 |
| 完全合成图片的 Pipeline smoke | PASS：5 行、21 个输出文件；本地临时目录清理通过 |
| 产品仓库独立运行 | PASS：`backend/.venv` 安装 `.[dev,ocr]`，`backend/.venv-paddle` 安装冻结 Paddle 依赖；两套环境 `pip check` 均通过。仅用这两套本地解释器、打包源码/模型对合成图片跑出 5 行、21 个产物，不依赖 PoC 路径 |
| 合成 PNG 输入 | PASS：Stage 02 支持的 PNG 字节通过产品适配器识别出 5 行、21 个产物，临时目录清理通过 |
| 完全合成两页 + 真实私有 COS | PASS：按 page_no 得到 10 行、43 个上传对象；仅使用脚本创建的测试键，最后调用 COS 删除 |
| 完全合成两页 + 真实私有 COS + 临时 PostgreSQL 17 + 真实 Worker | PASS：使用产品仓库自己的两套 OCR 环境和打包模型再次通过；10 条 `OcrResultItem`、`OcrTask.SUCCEEDED`、`ReportIngestion.PENDING_CONFIRMATION`；临时库删除 |
| Miniapp `pnpm test:tasks` / `pnpm typecheck` / `pnpm build:mp-weixin` | 4 项任务筛选与状态路由测试 PASS / PASS / PASS；首次只读沙箱构建无法创建新页面产物目录，允许写入构建产物后重跑通过 |
| Admin Web `pnpm typecheck` / `pnpm build` | PASS / PASS；Vite 提示主 chunk >500 kB，与 Stage 03 无关 |

## 5. 人工验收、偏差与已知问题

- **J01 真实微信主流程：PASS（项目负责人反馈）。**真实上传 3 张报告图片，完成 `READY → OCR → PENDING_CONFIRMATION`；识别 59 项，其中 AUTO 57、REVIEW 2。PROCESSING 期间离开页面、关闭小程序后重新进入，均从服务端恢复真实状态。OCR 成功后 3 张原始图片仍可查看，未生成正式报告数据。
- **J02 多页流程：PASS（项目负责人反馈及既有工程验证）。**3 张原图的页序和内容正确，均可逐页查看；既有两页真实私有 COS + Worker 工程验证已确认按 `page_no` 输入并持久化可追溯的 `OcrResultItem`。
- **J03 Worker 恢复：PASS（项目负责人反馈）。**Worker 在任务 `PROCESSING` 时实际停止，使用本地 `OCR_TASK_LEASE_SECONDS=120` 重新启动；lease 到期后自动恢复同一任务并成功识别，没有通过用户 Retry 创建新 run。自动 PostgreSQL 队列验证另覆盖 2 秒短 lease 的真实到期与重领。默认 lease 仍为 1800 秒。
- **识别任务记录回访与档案隔离：PASS（项目负责人反馈）。**新任务没有覆盖旧任务；此前 3 张图片、59 项结果的 `PENDING_CONFIRMATION` 旧任务可重新打开，汇总仍为 59 / 57 / 2，原图仍可查看。切换健康档案后列表只显示当前 HealthProfile 的任务，切回本人后原任务重新显示；另有 API 权限与前端路由测试覆盖。
- 当前小程序 UI 为功能版，本阶段不继续视觉优化。Stage 03 未创建 `ConfirmationItem`，未实现逐项确认或 commit，也未生成 `LabReport / LabResult`；这些能力属于后续阶段。
- PoC 没有 Git commit，使用实际文件内容快照哈希标记来源；未伪造 commit。
- PoC 最终行不稳定提供结构化报告级候选与 `SAFE_REVIEW / PIPELINE_GAP` 逐行分类时，任务候选保持空值、分类保持空值，保留原始 final/reason/evidence；未用业务层猜测或改写 AUTO/REVIEW。
- PoC 已知 RBC `1012/L` 与多行文字参考条件 Gap 继续安全进入 REVIEW；未修改算法、阈值或 frozen baseline。
- 人工构造 COS 测试与本次真实微信小程序上传的 3 页流程是两类证据；后者补齐了先前缺少的用户操作路径。Stage 02 已记录的上传成功但 Asset 登记失败可能留下孤儿 COS 对象，仍是正式上线前的文件清理技术债，不属于本阶段扩展范围。

## 6. Stage 04 注意事项

Stage 04 应从成功 OCR run 的不可变 `OcrResultItem` 初始化独立 `ConfirmationItem` 工作区，人工处理 REVIEW 后才允许 commit。不得 UPDATE 机器快照，不得把本阶段候选直接写成 `LabReport / LabResult` 或进入趋势。正式标准指标/别名后台能力按后续阶段设计，不在本阶段从 PoC 指标库自动反写。
