# Stage 03｜OCR Worker 正式接入与待确认结果生成

**状态：READY_FOR_IMPLEMENTATION**

## 1. 阶段目标

本阶段承接已验收通过的 Stage 02。

Stage 02 已经完成真实微信登录、健康档案、私有 COS 原图上传与 `ReportIngestion.READY`。Stage 03 的目标不是重新验证 OCR 算法，而是把已经通过 PoC / Regression 验证的 OCR Pipeline 正式接入产品工程体系，形成可靠、可恢复、可追溯的异步识别链路。

本阶段结束时，系统必须形成以下真实链路：

```text
ReportIngestion.READY
→ 用户开始识别
→ 冻结本次 OCR 输入
→ 创建 OcrTask.QUEUED
→ PostgreSQL 持久化任务队列
→ 独立 OCR Worker 原子领取任务
→ OcrTask.PROCESSING
→ 从私有 COS 读取原始图片
→ 按 page_no 调用已验证 OCR Pipeline
→ 保存 OCR 审计产物
→ 持久化 OcrResultItem 机器快照
→ FINAL_AUTO / FINAL_REVIEW
→ OcrTask.SUCCEEDED
→ ReportIngestion.PENDING_CONFIRMATION
→ 小程序显示“识别完成，待确认”
```

Stage 03 的最终产物是：

> **可追溯、不可被人工覆盖的 OCR 机器候选结果。**

本阶段**不进行人工确认，不生成正式健康数据**。

---

## 2. 必读基线

实施前必须按 `AGENTS.md` 顺序读取：

1. 根目录 `AGENTS.md`；
2. `docs/00-baseline/PRODUCT_BASELINE.md`；
3. `docs/00-baseline/TECH_BASELINE.md`；
4. `docs/00-baseline/DEVELOPMENT_RULES.md`；
5. 本目录 `PLAN.md`；
6. 本目录 `ACCEPTANCE.md`；
7. `docs/stages/02-profile-upload/RESULT.md`；
8. 本阶段涉及 OCR，继续读取：
   - `docs/01-architecture/OCR_INTEGRATION.md`
   - `docs/01-architecture/DATA_MODEL.md`
   - `docs/01-architecture/API_CONVENTIONS.md`
   - `docs/01-architecture/SYSTEM_ARCHITECTURE.md`

不得为了 Stage 03 重做 Stage 00～02 已验收能力。

---

## 3. Stage 02 已知真实基础

Stage 02 已于 2026-09-29 验收通过，可直接复用：

- FastAPI + SQLAlchemy 2 + Alembic；
- PostgreSQL 17；
- 微信真实登录与系统 Token；
- User / HealthProfile；
- ReportIngestion；
- ReportAsset；
- 私有 Tencent COS；
- 小程序通过受限临时凭证直传 COS；
- 原图短时签名预览；
- 单图、多图上传；
- 图片追加、排序、删除；
- 上传失败重试；
- 页面退出后从服务端恢复 ingestion；
- `ReportIngestion.UPLOADING ↔ READY`；
- Backend tests、Ruff、小程序与管理端 typecheck/build 基础。

当前关键实现集中在：

- `backend/app/api/v1/business.py`
- `backend/app/core/cos.py`
- `backend/app/models/entities.py`
- `backend/migrations/versions/0002_profile_upload.py`
- `miniapp/src/api.ts`
- `miniapp/src/pages/upload/index.vue`

现有 `backend/tests/test_stage02.py` 使用 SQLite 做快速业务测试，因此 Stage 03 的 PostgreSQL 队列锁语义必须额外增加真实 PostgreSQL 集成验证，不能仅以 SQLite 单测替代。

---

## 4. 阶段边界说明

### 4.1 Stage 03 只负责机器识别结果

本阶段负责：

```text
原始图片
→ OCR Task
→ OCR Pipeline
→ OCR 审计产物
→ OcrResultItem
→ FINAL_AUTO / FINAL_REVIEW
→ PENDING_CONFIRMATION
```

本阶段不负责：

```text
ConfirmationItem
→ 用户编辑/确认
→ 疑似重复
→ commit
→ LabReport
→ LabResult
```

上述内容属于 Stage 04。

### 4.2 关于长期架构中的 ConfirmationItem

`TECH_BASELINE.md` / `SYSTEM_ARCHITECTURE.md` 描述的是产品完整数据链，其中包含：

```text
OcrResultItem → ConfirmationItem → commit
```

本阶段经项目负责人确认，仅落到 `OcrResultItem` 与 `PENDING_CONFIRMATION`。

这不改变最终数据模型和安全原则，只调整阶段交付边界：

- Stage 03：生成不可变机器快照；
- Stage 04：从成功 OCR run 初始化可编辑确认工作区。

Codex 不得为了“补全总体链路”提前实现 Stage 04。

### 4.3 不新增无必要的 OcrResult 表

现有 `DATA_MODEL.md` 已冻结：

```text
ReportIngestion 1 ─ N OcrTask
OcrTask 1 ─ N OcrResultItem
```

Stage 03 默认不新增单独 `OcrResult` 表。

报告级 OCR 信息、Pipeline 版本、input manifest、artifact root、报告基本信息候选、结果汇总等归属于 `OcrTask`；逐条机器识别事实归属于 `OcrResultItem`。

如实施中出现必须新增实体的真实理由，先记录冲突，不得自行扩展数据模型。

---

# 5. 本阶段 P0 范围

## 5.1 ReportIngestion 状态扩展

Stage 03 正式使用：

```text
UPLOADING
↕
READY
↓
QUEUED
↓
PROCESSING
↓
PENDING_CONFIRMATION
```

异常路径：

```text
QUEUED / PROCESSING
↓
OCR_FAILED
```

重试：

```text
OCR_FAILED
→ 创建新的 OcrTask run
→ QUEUED
```

规则：

1. 只有 `READY` 可以首次开始 OCR；
2. `QUEUED / PROCESSING / PENDING_CONFIRMATION` 不允许再次创建重复首次任务；
3. `OCR_FAILED` 只能通过明确的 OCR retry 创建新 run；
4. `PENDING_CONFIRMATION` 表示机器识别已完成，但尚未产生正式健康数据；
5. 不得使用 `COMPLETED`、`CONFIRMED` 等可能混淆正式确认语义的状态代替。

当前 `report_ingestions.status` 为 `String(16)`，`PENDING_CONFIRMATION` 超出长度，本阶段 migration 必须同步扩展字段长度。

---

## 5.2 OCR 输入冻结

用户首次成功执行“开始识别”后，必须冻结本次输入。

创建 OcrTask 时保存 `input_manifest`，至少包含：

- `asset_id`
- `page_no`
- `cos_object_key`
- `mime_type`
- `file_size`

如当前工程已有可靠 checksum 可一并保存；不得为了 Stage 03 反向重构 Stage 02 上传链路补大量图片元数据。

输入冻结后：

- 原图仍可预览；
- 不得新增上传授权；
- 不得登记新 Asset；
- 不得调整页序；
- 不得删除 Asset；
- 不得用 retry 替换原始 ReportAsset。

后端必须真正校验状态，不能只在小程序隐藏按钮。

建议统一返回稳定业务错误码：

```text
INGESTION_INPUT_FROZEN
```

如用户发现原图本身有误，MVP 通过重新创建一份 ReportIngestion 处理，不在 Stage 03 建复杂输入版本管理。

---

## 5.3 OcrTask

新增正式 OcrTask 模型。

至少需要表达：

- `id`
- `ingestion_id`
- `run_no`
- `status`
- `pipeline_version`
- `input_manifest`
- `report_candidates`
- `result_summary`
- `artifact_root`
- `attempt_count`
- `next_attempt_at`
- `locked_at`
- `lease_expires_at`
- `worker_id`
- `last_error_code`
- `last_error_message`
- `created_at`
- `started_at`
- `finished_at`
- `updated_at`

关键约束：

```text
UNIQUE(ingestion_id, run_no)
```

状态：

```text
QUEUED
PROCESSING
SUCCEEDED
FAILED
```

`last_error_message` 仅用于内部排查，不得保存 OCR 全文、完整检验结果、Secret 或永久文件 URL。

---

## 5.4 PostgreSQL 持久化任务队列

继续遵循冻结技术路线：

- PostgreSQL 17；
- 不引入 Redis；
- 不引入 Celery；
- 不引入 RabbitMQ / Kafka；
- OCR Worker 独立 Python 进程；
- MVP OCR 并发固定为 1。

任务领取必须具有数据库级原子性。

推荐使用 PostgreSQL：

```sql
SELECT ...
FOR UPDATE SKIP LOCKED
```

或 SQLAlchemy 等价实现。

要求：

1. 同一个 QUEUED task 不能被两个 Worker 同时领取；
2. Worker 领取后进入 `PROCESSING`；
3. 设置 `locked_at / lease_expires_at / worker_id`；
4. Worker 正常完成后清理 lease；
5. Worker 异常退出后，超过 lease 的 PROCESSING task 必须能够恢复；
6. QUEUED task 在 API / Worker 重启后不得丢失；
7. 不允许通过“启动时把所有 PROCESSING 直接标成功”恢复任务。

### 自动执行尝试

允许同一个 OcrTask 对可恢复的基础设施异常进行有限自动重试。

要求：

- `attempt_count` 可追踪；
- 最大执行尝试建议固定为 3；
- 重试必须有最小退避，避免死循环；
- 可恢复错误重新进入可领取状态；
- 达到上限后 `FAILED`；
- 算法确定性业务失败不做无限重跑。

“自动执行尝试”不等于业务 OCR retry。

### 业务 OCR retry

用户对一个已经 `FAILED` 的 run 执行重试时：

- 必须新建新的 `OcrTask`；
- `run_no + 1`；
- 重新保存 input manifest；
- 旧 task 和旧机器结果不得覆盖。

---

## 5.5 OCR Pipeline 正式接入

本阶段不是 OCR 算法研发阶段。

正式仓库只允许接入已经经过 PoC / Regression 验证的能力。

必须遵守：

1. 不重新设计 OCR threshold；
2. 不重新发明 Retry / Evidence / 单位恢复算法；
3. 不因产品接入顺手调整指标匹配规则；
4. 不把“为了跑通产品”产生的算法修改直接留在正式仓库；
5. 算法变更应先回到独立 PoC / Regression 验证，再迁入正式产品。

### Pipeline 来源与冻结基线

当前已确认 OCR PoC 技术结项：

```text
OCR POC = PASSED
```

已验证工程为：

```text
checkup-ocr-poc
```

统一 Pipeline 入口为：

```powershell
python src/report_pipeline.py <report_id>
```

PoC 已验证的核心链路包括：

```text
Orientation Normalization
→ RapidOCR Baseline
→ Layout Detection
→ Row Parser
→ Metric Matcher
→ Result Parser
→ Dynamic Retry Selector
→ PaddleOCR Round1
→ Round2 Retry
→ Evidence Fusion
→ Retry Apply / Rematch
→ Unit Resolver
→ Final Validation
→ FINAL_AUTO / FINAL_REVIEW
```

已验证运行环境包含：

```text
Python 3.12.10

.venv
  RapidOCR + 业务解析

.venv-paddle
  PaddleOCR
  PP-OCRv6_medium_rec
  CPU
```

以及 ONNX Runtime、OpenCV、Shapely、NumPy。

Stage 03 实施时必须以该已验证 PoC / Regression snapshot 的真实源码、配置、模型和指标库为来源。

**技术总结报告只能作为接入说明，不能替代 OCR Pipeline 源码。**

如果 Codex 在当前工作区无法读取 `checkup-ocr-poc` 的已验证源码：

> 不得根据总结报告重新实现一套 OCR 算法来冒充正式接入。

应停止算法复制/重写，保留已经完成的非算法工程工作，并明确记录缺少的源码/路径阻塞；Stage 03 不得因此宣称 PASS。

### 正式仓库运行边界

正式产品运行时不能依赖开发机上的绝对 sibling 路径。

实施时应：

1. 读取已验证 `checkup-ocr-poc` snapshot；
2. 确定正式运行所需的最小 Pipeline runtime、模型、指标库与配置；
3. 将经过验证的 runtime 以可版本追踪的方式接入 `checkup-miniapp/backend`；
4. 记录来源版本 / commit / snapshot 标识；
5. 保持 PoC / Regression 仓库继续承担算法准确率与 Safety Regression。

不得把本机绝对路径作为正式运行依赖。

### Regression Gate

PoC 已建立 Frozen Regression，当前技术结项记录：

```text
paper_report_01
paper_report_02
paper_report_03

Frozen Regression = 3 / 3 PASS
Core logic tests = 15 / 15 PASS
Safety Regression = 0
```

凡 Stage 03 接入过程中修改以下任一算法核心：

```text
Orientation
Layout
Row Parser
Metric Matcher
Result Parser
Retry
Evidence Fusion
Unit Resolver
Final Validator
```

必须在 `checkup-ocr-poc` 执行：

```powershell
.\.venv\Scripts\python.exe tests\run_regression.py
```

并确认不存在 `SAFETY_REGRESSION`。

即使 Stage 03 只做 adapter / packaging、没有修改算法规则，也必须在采用的 PoC snapshot 上至少执行一次现有 Frozen Regression，并把 snapshot / commit 与回归结果记录进 `RESULT.md`。

不得为了让测试 PASS 而直接修改 frozen baseline。

### 工程适配

正式接入后应提供稳定的产品侧 adapter，使 Worker 依赖统一输入输出契约，而不是依赖 PoC 的手工目录和脚本约定。

不得要求正式运行依赖：

```text
samples/
output/
人工复制图片
固定 report_id 文件名
```

建议逻辑契约：

```text
run_pipeline(
    ordered_assets,
    work_dir,
    task_context
) -> normalized_pipeline_result
```

具体函数名和目录按当前工程结构决定，不做无关大重构。

OCR 依赖应根据已验证 PoC snapshot 明确并固定；不得由 Codex擅自更换 OCR 引擎。

---

## 5.6 COS 原图读取与 OCR 审计产物

### 原图读取

Worker 使用服务端 COS 永久凭据读取当前 task `input_manifest` 中的私有原图。

要求：

- 按 page_no 顺序下载；
- 临时目录不使用真实姓名、医院名称等敏感信息；
- Worker 结束后清理本地临时图片与临时中间文件；
- OCR 不修改、不覆盖、不删除原始 ReportAsset；
- Stage 03 不改变原图长期保留规则。

### OCR Artifact

成功 run 必须保留可审计 OCR 产物。

PoC 已验证并保留的可追溯链路包括：

- 原始图片；
- 规范化工作图片；
- raw OCR；
- layout；
- rows；
- matcher；
- retry target；
- PaddleOCR 证据；
- evidence fusion；
- unit 处理；
- final 结果。

正式产品不要求为了“表结构好看”把每一个中间 JSON 拆成数据库表，但不得丢失支撑最终机器判定所需的审计证据。

推荐 COS 路径：

```text
users/{user_id}/ingestions/{ingestion_id}/ocr/run-001/
```

至少应长期保留：

- 原始 OCR 输出；
- 最终 Pipeline 输出；
- Pipeline version；
- 能支持后续问题排查的关键 evidence。

如现有 Pipeline 自带：

```text
raw_ocr.json
layout.json
rows.json
matched.json
final.json
```

可以按验证后的实际产物保留，不强制为了统一命名重写算法输出。

`OcrTask.artifact_root` 必须能够定位本次 run 的审计产物。

任务只有在要求的 OCR 快照与审计产物可靠保存后才能标记 `SUCCEEDED`。

---

## 5.7 OcrResultItem

新增不可变机器识别快照。

至少需要表达以下语义：

### 来源

- `ocr_task_id`
- `sequence_no`
- `source_asset_id`
- `page_no`
- `bbox`（Pipeline 可提供时）

### OCR 原始字段

- 原始指标名称；
- 原始结果；
- 原始单位；
- 原始参考范围。

### Pipeline 结构化候选

- 标准指标候选 code/key；
- 标准指标候选名称；
- `result_text`；
- 可解析数值；
- comparator；
- normalized unit；
- reference text；
- 可解析参考下限/上限；
- abnormal flag。

### 安全判定

必须保留 Pipeline 的最终判定：

```text
FINAL_AUTO
FINAL_REVIEW
```

并保留：

- `review_reasons`
- 必要 evidence 摘要
- 原始/规范化 payload（如为后续确认所必需）
- Pipeline 可提供时的 REVIEW 原因分类，例如 `SAFE_REVIEW` / `PIPELINE_GAP`

其中：

- `SAFE_REVIEW` 表示证据不足、需要人工确认，是正常安全行为；
- `PIPELINE_GAP` 表示存在已知通用规则缺口，但最终仍安全进入 REVIEW；
- 两者都不能被业务层转换为 AUTO。

### 不可变原则

`OcrResultItem` 表示“机器当时识别了什么”。

因此：

- Stage 03 不提供编辑 OcrResultItem 的用户 API；
- Stage 04 人工修改不得 UPDATE 覆盖 OcrResultItem；
- retry 新建 OcrTask / 新建 OcrResultItem；
- 旧 run 的结果必须可追溯。

---

## 5.8 报告级候选信息

Pipeline 已经可靠输出的报告级信息允许保存到：

```text
OcrTask.report_candidates
```

例如：

- 医院名称候选；
- 报告名称/类型候选；
- 检验日期/时间候选；
- 报告日期候选；
- 报告编号候选；
- 患者姓名候选。

原则：

```text
识别到 → 保存候选
不确定 → 保存 evidence / review 提示
识别不到 → NULL
```

Stage 03 不为了补齐这些字段重新开启算法研发。

候选值不是正式报告信息，不得写入 LabReport。

---

## 5.9 已知 PoC Gap 的 Stage 03 处理原则

PoC 当前已明确存在但不阻塞 MVP 的能力缺口，包括：

```text
RBC: 1012/L → 10^12/L 尚未自动语义恢复
多行文字型参考条件尚不能稳定完整归属
```

当前 Pipeline 对这些问题的安全行为是：

```text
FINAL_REVIEW
```

Stage 03 的目标是**忠实接入已验证 Pipeline**，因此：

- 不在产品接入阶段顺手修复上述算法 Gap；
- 不为了减少 REVIEW 修改安全阈值；
- 不把 `PIPELINE_GAP` 当作 OCR 任务失败；
- 如后续需要修复，先回 `checkup-ocr-poc` 增加样本、规则与 Regression，再迁入产品。

以上 Gap 不阻塞 Stage 03 PASS，前提是仍然安全进入 REVIEW。

---

## 5.10 标准指标库的阶段边界

PoC 当前使用 `metric_library.json` 支撑 Metric Matcher。

技术结项建议未来产品化为正式基础数据，例如 StandardMetric / MetricAlias / CommonUnit，并通过管理后台维护。

Stage 03 不提前完成这一整套产品化：

- OCR Worker 允许继续使用本次冻结 PoC snapshot 自带的指标库；
- OcrResultItem 保存标准指标候选 code/key/name；
- 不在 Stage 03 建管理后台维护；
- 不把 OCR typo 作为正式 alias 沉淀；
- 正式 StandardMetric / MetricAlias 与人工选择能力留给后续确认/管理阶段按产品基线落地。

---

## 5.11 结果汇总

成功任务应形成最小 `result_summary`，供小程序处理页显示，例如：

- `total_count`
- `auto_count`
- `review_count`

其中：

```text
auto_count = FINAL_AUTO 数量
review_count = FINAL_REVIEW 数量
```

`FINAL_REVIEW > 0` 是正常成功结果，不得因此把任务标记为 FAILED。

---

# 6. API 范围

API 继续使用 `/api/v1`。

## 6.1 开始识别

```text
POST /api/v1/ingestions/{id}/recognize
```

要求：

- 当前用户拥有 ingestion；
- ingestion = READY；
- 至少 1 张有效 UPLOADED ReportAsset；
- 创建 input manifest；
- 创建 `OcrTask(run_no=1, QUEUED)`；
- 将 ingestion 原子更新为 `QUEUED`；
- API 立即返回，不同步执行 OCR；
- 防止重复点击产生重复 task。

幂等规则：

- READY：创建首次 task；
- QUEUED / PROCESSING：返回当前 active task，不创建第二条；
- PENDING_CONFIRMATION：返回当前已完成状态，不创建新 task；
- OCR_FAILED：要求使用 retry 接口。

建议响应为 task + ingestion 状态摘要。

---

## 6.2 获取 OCR 状态

建议：

```text
GET /api/v1/ingestions/{id}/ocr
```

至少返回：

- ingestion status；
- latest task id；
- run_no；
- task status；
- attempt_count；
- started / finished time；
- success 时的 total / auto / review count；
- failure 时稳定 `error_code`。

不得向小程序返回：

- 内部 Python traceback；
- OCR 全文；
- Secret；
- 永久 COS URL。

Stage 03 不要求返回完整逐项可编辑确认数据。

---

## 6.3 OCR retry

建议：

```text
POST /api/v1/ingestions/{id}/ocr/retry
```

仅允许：

```text
ReportIngestion.OCR_FAILED
+
latest OcrTask.FAILED
```

成功后：

- 新建 `run_no + 1`；
- task = QUEUED；
- ingestion = QUEUED；
- 不删除旧 task；
- 不覆盖旧 OcrResultItem / artifact。

重复点击仍需幂等保护，不能连续生成多个 active retry task。

---

# 7. 失败分类与恢复

## 7.1 可自动重试的基础设施错误

例如：

- COS 临时读取失败；
- OCR artifact 上传临时失败；
- 数据库临时连接错误；
- Worker 非正常退出后的 lease 恢复；
- 明确可恢复的临时 IO 错误。

处理：

```text
attempt_count + 1
→ 未到上限：重新进入可领取状态
→ 达到上限：FAILED / OCR_FAILED
```

---

## 7.2 确定性 OCR 业务失败

例如：

- 图片无法解码；
- Pipeline 输出格式非法；
- 无法形成任何有效结构化检验行；
- 当前正式 Pipeline 明确返回不可处理结果。

这类失败不应无限重复运行同一输入。

最终：

```text
OcrTask.FAILED
ReportIngestion.OCR_FAILED
```

用户可执行显式 retry；如果输入本身有问题，引导重新创建上传任务。

---

## 7.3 不属于失败的情况

以下情况必须正常 `SUCCEEDED`：

- 某一指标无法标准匹配；
- 单位无法可靠恢复；
- 部分指标需要 REVIEW；
- 报告基本信息存在缺失；
- `FINAL_REVIEW > 0`。

这些属于后续人工确认需要处理的正常情况。

---

# 8. Worker 最小能力

必须有独立可运行 Worker 入口。

Worker 至少完成：

```text
启动
→ 轮询可领取任务
→ 恢复过期 lease
→ 原子 claim
→ 下载冻结输入
→ 调用 OCR adapter
→ 保存 OCR artifact
→ 事务性写入 OcrResultItem
→ 更新 OcrTask
→ 更新 ReportIngestion
→ 清理本地临时文件
→ 继续轮询
```

要求：

- OCR 并发 = 1；
- API 进程不执行长 OCR；
- Worker 与 API 共用 PostgreSQL；
- Worker 与 API 共用正式 COS 配置；
- Worker 支持优雅退出；
- 普通日志只记录 task_id、ingestion_id、状态、耗时、error_code 等；
- 不记录完整 OCR 文本和完整检验结果。

应在 `backend/README.md` 或根 `README.md` 记录本地 Worker 启动方式。

Stage 03 不要求完成 Stage 08 的生产 Docker/Nginx 正式部署。

---

# 9. 数据库迁移

新增 migration：

```text
0003_ocr_integration
```

至少：

1. 扩展 `report_ingestions.status` 长度以支持 `PENDING_CONFIRMATION`；
2. 创建 `ocr_tasks`；
3. 创建 `ocr_result_items`；
4. 建立必要外键；
5. 建立 `ingestion_id / status / next_attempt_at` 等队列查询需要的索引；
6. 建立 `(ingestion_id, run_no)` 唯一约束；
7. OcrResultItem 建立 task / source asset 必要索引。

要求：

- 既有 `0002_profile_upload` 数据库可升级；
- 全新 PostgreSQL 可从 `0001 → 0002 → 0003`；
- 不重写已验收的 0001 / 0002 migration；
- 不手工 SQL 绕过 Alembic。

---

# 10. 小程序 P0

## 10.1 图片确认页接入开始识别

现有 `miniapp/src/pages/upload/index.vue` 中 Stage 02 占位提示改为真实操作。

READY 状态：

```text
[开始识别]
```

点击：

```text
POST recognize
→ 成功创建/取得 task
→ 跳转 OCR 处理中页
```

要求：

- 防重复点击；
- 调用失败明确提示；
- 未达到 READY 不允许开始；
- 开始识别后上传/追加/排序/删除 UI 进入只读。

---

## 10.2 P06 识别处理中页

新增最小 OCR 处理页。

至少展示：

### QUEUED

```text
报告已进入识别队列
```

### PROCESSING

```text
正在识别报告
```

### PENDING_CONFIRMATION

```text
识别完成，待确认
共识别 X 项
自动候选 X 项
待重点核对 X 项
```

### OCR_FAILED

```text
识别失败
[重新识别]
[返回重新上传]
```

“返回重新上传”允许用户开启新的 ReportIngestion，不得修改已冻结输入。

Stage 03 成功页不实现指标逐条编辑，不实现 Stage 04 确认页。

---

## 10.3 状态恢复

用户不需要停留在处理页面。

要求：

- `onShow` 重新从 API 获取真实状态；
- 页面可轮询但不得依赖单一前端计时器作为事实来源；
- 离开页面再进入后状态正确；
- 小程序关闭再打开仍可恢复；
- Worker 尚未运行时保持 QUEUED，不伪造进度；
- Worker 完成后显示服务端成功状态。

---

# 11. 管理后台

Stage 03 不开发正式管理后台 OCR 页面。

`admin-web` 保持现有占位业务状态，只要求：

- typecheck 通过；
- build 通过；
- 不被 Stage 03 后端修改破坏。

不得提前实现：

- OCR 在线参数配置；
- Pipeline threshold 配置；
- 标准指标后台；
- OCR 人工修正后台；
- 用户正式健康数据后台。

---

# 12. 权限与安全

必须保证：

1. User A 不得开始 User B ingestion OCR；
2. User A 不得查看 User B OCR 状态；
3. User A 不得对 User B OCR 进行 retry；
4. Worker 只能根据数据库 task 读取其冻结的 COS object key；
5. 前端不能获取 COS 永久 Secret；
6. OCR artifact 使用私有 COS；
7. object key / artifact path 不使用真实姓名或医院名称；
8. 日志不记录 OCR 全文、完整检验结果、微信 Secret、COS Secret、Token；
9. OcrResultItem 不允许用户侧修改。

---

# 13. Stage 02 技术债处理边界

Stage 02 已知：

> COS 上传成功，但 ReportAsset 注册失败时可能留下未关联孤儿对象。

该问题继续作为正式上线前文件清理技术债保留。

Stage 03：

- 不把这项清理机制夹带进 OCR 接入；
- Worker 只处理已经成功登记的 ReportAsset；
- 不因为本阶段引入 OCR Worker 就顺手建设通用 COS GC 系统。

现有 Asset 删除失败 `file_cleanups.PENDING` 机制保持，不做无关重构。

---

# 14. 测试要求

## 14.1 Backend 快速测试

继续运行现有测试，并新增 Stage 03 测试。

至少覆盖：

- READY 开始识别；
- 非 READY 拒绝；
- recognize 幂等；
- 输入 manifest 正确；
- OCR 后 Asset 冻结；
- 跨用户 recognize / status / retry 隔离；
- OcrTask 状态流转；
- FINAL_AUTO / FINAL_REVIEW 映射；
- `FINAL_REVIEW > 0` 仍为成功；
- 结果持久化事务；
- OcrResultItem 不被 retry 覆盖；
- retry 新建 run；
- 终态失败；
- 失败不产生虚假成功结果；
- API 错误码。

单测允许 mock COS 与 Pipeline，避免每次 pytest 都运行重 OCR。

---

## 14.2 PostgreSQL 队列集成测试

由于 Stage 02 快速测试主要使用 SQLite，本阶段必须增加真实 PostgreSQL 17 队列验证。

至少验证：

1. 两个独立 DB session 同时尝试 claim 同一 task；
2. 只有一个 session 成功领取；
3. `FOR UPDATE SKIP LOCKED` 或等价逻辑真实生效；
4. QUEUED task 重启后仍存在；
5. PROCESSING lease 过期后可以恢复；
6. `(ingestion_id, run_no)` 唯一约束真实有效。

不得用 SQLite 结果宣称 PostgreSQL 队列正确。

---

## 14.3 PoC Frozen Regression

在正式接入采用的 `checkup-ocr-poc` snapshot 上执行现有 Regression。

至少记录：

```text
tests/run_regression.py
snapshot / commit
Frozen Regression
Core logic tests
Safety Regression
```

要求：

- 不通过修改 frozen baseline 制造 PASS；
- `Safety Regression > 0` 时 Stage 03 不得 PASS；
- 如 Stage 03 未修改算法规则，也必须证明接入来源 snapshot 是已通过回归的版本。

## 14.4 Pipeline 工程接入验证

需要至少一次真实已验证 Pipeline smoke test：

```text
私有 COS 原图
→ Worker
→ 正式 adapter
→ OCR Pipeline
→ OcrResultItem
→ PENDING_CONFIRMATION
```

测试样本必须脱敏、人工构造或经许可使用。

真实家庭医疗报告不得提交 Git。

算法准确率回归不在正式产品仓库重复建设。

---

## 14.5 Frontend

必须：

- `miniapp/pnpm typecheck`
- `miniapp/pnpm build:mp-weixin`
- `admin-web/pnpm typecheck`
- `admin-web/pnpm build`

---

# 15. 本阶段明确不做

Stage 03 不得实现：

- `ConfirmationItem`；
- 识别结果逐条人工编辑；
- REVIEW resolved；
- 指标人工修改；
- 标准指标人工选择；
- 按原名称保存交互；
- 手工新增指标；
- 纯手工报告；
- 疑似重复判断；
- commit；
- LabReport；
- LabResult；
- 正式报告列表；
- 正式报告详情；
- 我的指标；
- 指标历史；
- 趋势图；
- 关注指标；
- 管理后台正式业务；
- OCR 算法在线配置；
- OCR 准确率重新研究；
- Redis；
- Celery；
- RabbitMQ；
- Kafka；
- 微服务；
- Kubernetes；
- Stage 02 孤儿 COS 通用清理系统。

---

# 16. 最终交付物

完成 Stage 03 后至少存在：

- `0003_ocr_integration` migration；
- OcrTask 模型；
- OcrResultItem 模型；
- PostgreSQL 持久化队列；
- lease / Worker 崩溃恢复机制；
- 独立 OCR Worker 入口；
- 已验证 OCR Pipeline 产品 adapter；
- 私有 COS 原图下载能力；
- OCR artifact 持久化能力；
- recognize API；
- OCR status API；
- OCR retry API；
- 输入冻结业务校验；
- 小程序“开始识别”真实入口；
- 小程序 P06 识别处理中页；
- Backend 自动测试；
- PostgreSQL 队列集成验证；
- Pipeline smoke test；
- 小程序/管理端 typecheck/build；
- 更新后的 README；
- `docs/stages/03-ocr-integration/RESULT.md`。

---

# 17. Stage 04 交接条件

Stage 04 可以假设 Stage 03 已提供：

```text
ReportIngestion.PENDING_CONFIRMATION
+
latest OcrTask.SUCCEEDED
+
完整不可变 OcrResultItem
+
原始 ReportAsset
+
OCR artifact
+
total/auto/review summary
```

Stage 04 才负责：

```text
初始化 ConfirmationItem
→ 用户确认/修正
→ REVIEW 全部 resolved
→ 疑似重复
→ commit
→ LabReport / LabResult
```

不得在 Stage 03 提前实现。

---

# 18. Definition of Done

只有同时满足：

```text
Stage 02 基线未破坏
+
READY 可真实开始 OCR
+
输入在识别后被冻结
+
OcrTask 可靠持久化
+
PostgreSQL 原子领取真实验证
+
Worker 崩溃/重启不丢任务
+
私有 COS 原图可由 Worker 读取
+
已验证 Pipeline 正式接入
+
采用的 PoC snapshot Frozen Regression 通过且 Safety Regression = 0
+
多页按 page_no 输入
+
OCR 审计产物可追溯
+
OcrResultItem 不可被人工覆盖
+
FINAL_AUTO / FINAL_REVIEW 正确持久化
+
失败可恢复/可显式 retry
+
retry 新建 run 且历史保留
+
小程序可恢复 QUEUED / PROCESSING / SUCCESS / FAILED 状态
+
成功终态 = PENDING_CONFIRMATION
+
未产生 ConfirmationItem / LabReport / LabResult
+
自动测试与真实 PostgreSQL 队列验证通过
+
至少一次真实 Pipeline 工程闭环通过
+
ACCEPTANCE 全部 P0 PASS
+
RESULT.md 更新
```

Stage 03 才可以标记为 PASS。

完成后停止，不进入 Stage 04。
