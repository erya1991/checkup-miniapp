# Stage 03｜验收标准

**阶段：OCR Worker 正式接入与待确认结果生成**

> 本文档是 Stage 03 是否完成的唯一阶段验收基线。所有 P0 项全部 PASS 才允许 Stage 03 = PASS。

---

# A. 基线与数据库

## A01｜Stage 02 已验收能力未被破坏【P0】

验证：

- 真实微信登录链路仍可用；
- HealthProfile 仍可正常 CRUD / 切换；
- ReportIngestion / ReportAsset 上传链路仍正常；
- 私有 COS 上传、预览仍正常；
- Stage 02 既有后端测试全部通过；
- 小程序、管理端仍可 typecheck/build。

- [ ] PASS
- [ ] FAIL

---

## A02｜0003 Migration 可从既有库升级【P0】

Given：数据库当前为 `0002_profile_upload`。

When：

```text
alembic upgrade head
```

Then：

- 成功升级到 `0003_ocr_integration`；
- 不重写 0001 / 0002；
- 既有 User / HealthProfile / ReportIngestion / ReportAsset 数据不丢失。

记录：

```text
Command:
Before:
After:
Result:
```

- [ ] PASS
- [ ] FAIL

---

## A03｜干净 PostgreSQL 可完整迁移到 0003【P0】

新建唯一命名临时空库，从头执行：

```text
0001_foundation
→ 0002_profile_upload
→ 0003_ocr_integration
```

确认 head 正确后只删除本次临时库。

- [ ] PASS
- [ ] FAIL

---

## A04｜状态字段支持 PENDING_CONFIRMATION【P0】

`report_ingestions.status` 实际数据库字段可以可靠保存：

```text
PENDING_CONFIRMATION
```

不得依赖 SQLite 忽略 varchar 长度来制造通过。

- [ ] PASS
- [ ] FAIL

---

## A05｜未引入新大型基础设施【P0】

仓库和运行环境不得新增：

- Redis；
- Celery；
- RabbitMQ；
- Kafka；
- MongoDB；
- Elasticsearch；
- 微服务；
- Kubernetes。

- [ ] PASS
- [ ] FAIL

---

# B. 开始识别与输入冻结

## B01｜READY 可以开始识别【P0】

Given：

- 当前用户拥有 ingestion；
- ingestion = READY；
- 至少存在 1 张有效 `ReportAsset.UPLOADED`。

When：

```text
POST /api/v1/ingestions/{id}/recognize
```

Then：

- 创建 OcrTask；
- `run_no = 1`；
- task = QUEUED；
- ingestion = QUEUED；
- API 立即返回；
- HTTP 请求中不执行长 OCR。

- [ ] PASS
- [ ] FAIL

---

## B02｜非 READY 不创建首次 OCR 任务【P0】

至少验证：

- UPLOADING；
- OCR_FAILED；
- 非法/不存在 ingestion。

不能通过首次 recognize 创建错误 task。

- [ ] PASS
- [ ] FAIL

---

## B03｜开始识别接口幂等【P0】

对同一个已 QUEUED 或 PROCESSING ingestion 连续点击/调用 recognize。

Then：

- 返回当前 active task；
- 不创建第二条 active task；
- 不重复增加 run_no。

对 `PENDING_CONFIRMATION` 再调用 recognize 也不得重新跑 OCR。

- [ ] PASS
- [ ] FAIL

---

## B04｜input_manifest 冻结正确【P0】

创建 task 时，manifest 至少包含当时全部：

- asset_id；
- page_no；
- cos_object_key；
- mime_type；
- file_size。

顺序与 `ReportAsset.page_no` 一致。

后续 Worker 以 manifest 为本次 run 的输入依据。

- [ ] PASS
- [ ] FAIL

---

## B05｜识别开始后后端真正冻结图片输入【P0】

ingestion 进入 QUEUED 后验证：

- 获取新上传授权被拒绝；
- 登记新 Asset 被拒绝；
- Asset 排序被拒绝；
- Asset 删除被拒绝；
- 原图预览仍允许。

前端隐藏按钮不能替代后端校验。

建议业务错误码：

```text
INGESTION_INPUT_FROZEN
```

- [ ] PASS
- [ ] FAIL

---

# C. OcrTask 与 PostgreSQL 队列

## C01｜OcrTask 数据结构完整【P0】

至少能表达：

- ingestion；
- run_no；
- status；
- pipeline_version；
- input_manifest；
- artifact_root；
- report candidates；
- result summary；
- attempt_count；
- lease；
- error；
- started / finished timestamps。

并存在：

```text
UNIQUE(ingestion_id, run_no)
```

- [ ] PASS
- [ ] FAIL

---

## C02｜真实 PostgreSQL 原子领取【P0】

必须在 PostgreSQL 17 上验证，不得仅使用 SQLite。

构造 1 个 QUEUED task，同时使用两个独立数据库 session / Worker 尝试领取。

Then：

```text
最多只有一个领取成功
```

第二个 session 不得得到同一个 task。

实现使用：

```text
FOR UPDATE SKIP LOCKED
```

或可证明具有等价 PostgreSQL 原子语义的方案。

记录：

```text
Test/Command:
Session A:
Session B:
Result:
```

- [ ] PASS
- [ ] FAIL

---

## C03｜QUEUED 任务重启不丢【P0】

创建 QUEUED task 后：

- 停止 API；
- 停止 Worker；
- 重新启动。

Then：

- task 仍存在；
- Worker 可以继续领取；
- 不依赖内存队列。

- [ ] PASS
- [ ] FAIL

---

## C04｜PROCESSING lease 恢复【P0】

模拟：

```text
Worker claim
→ task = PROCESSING
→ Worker 非正常退出
→ lease 超时
```

Then：

- task 不会永久卡死；
- 可以重新进入可处理状态；
- 不直接伪造 SUCCEEDED。

- [ ] PASS
- [ ] FAIL

---

## C05｜Worker 并发固定为 1【P0】

MVP 正式配置与启动方式明确：

```text
OCR concurrency = 1
```

不得在本阶段建设并发任务池或复杂调度框架。

- [ ] PASS
- [ ] FAIL

---

# D. OCR Pipeline 正式接入

## D01｜使用已验证 Pipeline，不重新实现算法【P0】

检查实际代码和变更说明：

- OCR 能力来源于已验证 `checkup-ocr-poc` / Regression snapshot；
- 接入链路与已验证 Pipeline 保持一致：
  `Orientation → RapidOCR → Layout → Row Parser → Matcher → Result Parser → Retry → PaddleOCR → Evidence Fusion → Unit Resolver → Final Validation`；
- 没有为了产品接入自行重写一套 OCR；
- 没有未经 Regression 验证修改 threshold / Retry / Evidence / 单位恢复核心规则；
- RESULT 记录本次接入的 Pipeline 来源、snapshot/commit 与运行环境。

已知 PoC 运行基线包括：

```text
Python 3.12.10
RapidOCR
PaddleOCR
PP-OCRv6_medium_rec / CPU
ONNX Runtime
OpenCV
Shapely
NumPy
```

具体依赖版本必须从已验证 PoC 工程读取并记录，禁止凭技术总结报告猜版本。

如无法取得已验证 Pipeline 源码，本项不得 PASS。

- [ ] PASS
- [ ] FAIL

---

## D02｜正式 adapter 不依赖 PoC 手工目录【P0】

正式 Worker 不要求：

```text
samples/
output/
人工复制图片
固定 report_id 文件名
```

Worker 可用 task + COS 原图直接调用正式 adapter。

- [ ] PASS
- [ ] FAIL

---

## D03｜真实私有 COS 原图可读取【P0】

使用一个 Stage 02 已登记 ReportAsset：

- 原始对象仍为私有；
- Worker 使用服务端权限读取；
- 不生成永久公开 URL；
- 小程序不获得 COS 永久 Secret。

- [ ] PASS
- [ ] FAIL

---

## D04｜多页严格按 page_no 输入【P0】

至少使用 2 页输入验证。

Given：

```text
page_no = 1
page_no = 2
```

Worker 调用 Pipeline 的顺序必须为：

```text
1 → 2
```

不得依赖 COS 列表顺序、上传时间或文件名排序。

- [ ] PASS
- [ ] FAIL

---

## D05｜Frozen Regression 通过【P0】

在本次正式接入采用的 `checkup-ocr-poc` snapshot 上执行：

```powershell
.\.venv\Scripts\python.exe tests\run_regression.py
```

至少记录：

- snapshot / commit；
- Frozen Regression；
- Core logic tests；
- Safety Regression。

历史技术结项记录为：

```text
Frozen Regression = 3 / 3 PASS
Core logic tests = 15 / 15 PASS
Safety Regression = 0
```

如果当前已验证 PoC 后续增加了测试，应记录真实当前结果，不得为了匹配历史数字删除测试。

硬规则：

```text
Safety Regression > 0
→ Stage 03 不得 PASS
```

不得通过直接修改 frozen baseline 制造 PASS。

- [ ] PASS
- [ ] FAIL

---

## D06｜本地临时文件可清理【P0】

一次成功任务和一次失败任务结束后：

- 临时图片不长期残留；
- 临时中间文件不长期残留；
- 不在仓库根目录生成 OCR 输出；
- 原始 COS 对象不受影响。

- [ ] PASS
- [ ] FAIL

---

# E. OCR Artifact 与机器结果

## E01｜成功 run 保存 OCR 审计产物【P0】

成功 task 必须存在可定位 artifact root。

至少能追溯：

- 原始 OCR 输出；
- 最终 Pipeline 输出；
- Pipeline version；
- 关键 evidence。

artifact 位于私有 COS 或项目已冻结的等价长期私有存储。

- [ ] PASS
- [ ] FAIL

---

## E02｜OcrResultItem 正确持久化【P0】

成功识别后，数据库真实存在本 run 对应 OcrResultItem。

至少抽查：

- 原始指标名称；
- 原始结果；
- 原始单位；
- 原始参考范围；
- 标准指标候选；
- 结构化结果；
- normalized unit；
- 来源 page；
- FINAL decision。

- [ ] PASS
- [ ] FAIL

---

## E03｜FINAL_AUTO / FINAL_REVIEW 正确映射【P0】

使用已知 Pipeline 输出样本，至少同时覆盖：

```text
FINAL_AUTO
FINAL_REVIEW
```

数据库值与 Pipeline 最终判定一致。

业务层不得自行依据单一 confidence 改写 FINAL decision。

- [ ] PASS
- [ ] FAIL

---

## E04｜REVIEW 是成功结果，不是任务失败【P0】

Given：识别结果存在 1 条或多条 `FINAL_REVIEW`。

Then：

```text
OcrTask = SUCCEEDED
ReportIngestion = PENDING_CONFIRMATION
```

不得因为存在 REVIEW 设置 `OCR_FAILED`。

- [ ] PASS
- [ ] FAIL

---

## E05｜报告级候选可追溯【P0】

Pipeline 能输出的报告级候选被保存到 task 级数据。

例如存在时抽查：

- 医院候选；
- 检验时间候选；
- 报告号候选。

识别不到允许为空，不得伪造默认值。

- [ ] PASS
- [ ] FAIL

---

## E06｜result_summary 正确【P0】

成功 run 至少返回：

- total_count；
- auto_count；
- review_count。

并满足：

```text
total_count = auto_count + review_count
```

如 Pipeline 明确定义其它安全分类，需在 RESULT 解释，但不得弱化 FINAL_REVIEW。

- [ ] PASS
- [ ] FAIL

---

## E07｜SAFE_REVIEW / PIPELINE_GAP 保持安全语义【P0】

对 Pipeline 能提供原因分类的 REVIEW 项抽查：

- SAFE_REVIEW 保持 REVIEW；
- PIPELINE_GAP 保持 REVIEW；
- 业务层不自行将其改写为 AUTO；
- REVIEW 项仍允许整个 OCR task 成功。

已知不阻塞 MVP 的 Gap（如 RBC `1012/L`、多行文字参考条件）不得在 Stage 03 通过降低安全边界“修复”。

- [ ] PASS
- [ ] FAIL

---

## E08｜OcrResultItem 保持不可变机器快照【P0】

Stage 03：

- 不存在用户编辑 OcrResultItem API；
- 小程序不能修改 OcrResultItem；
- retry 不 UPDATE 覆盖旧 run 的 items；
- 旧 run 可继续审计。

- [ ] PASS
- [ ] FAIL

---

# F. 失败与 Retry

## F01｜可恢复基础设施错误有限自动重试【P0】

模拟至少一种明确可恢复错误。

Then：

- attempt_count 增加；
- 未达到上限时可重新处理；
- 不紧密死循环；
- 不立即产生第二个业务 run。

- [ ] PASS
- [ ] FAIL

---

## F02｜达到自动尝试上限进入 OCR_FAILED【P0】

持续制造可恢复错误直到上限。

Then：

```text
OcrTask = FAILED
ReportIngestion = OCR_FAILED
```

并保存稳定 error_code。

- [ ] PASS
- [ ] FAIL

---

## F03｜确定性 OCR 失败不会无限重跑【P0】

模拟：

- 图片不可解码；
- Pipeline 输出非法；
- 无有效结构化结果；

至少一种。

Then：

- 最终 FAILED；
- 不无限循环；
- 不写入虚假成功 OcrResultItem；
- ingestion = OCR_FAILED。

- [ ] PASS
- [ ] FAIL

---

## F04｜显式 retry 创建新 run【P0】

Given：

```text
run 1 = FAILED
```

When：

```text
POST /api/v1/ingestions/{id}/ocr/retry
```

Then：

```text
run 2 = QUEUED
```

并满足：

- run 1 保留；
- run_no 递增；
- 不覆盖 run 1；
- ingestion = QUEUED。

- [ ] PASS
- [ ] FAIL

---

## F05｜Retry 幂等【P0】

对一个已经创建 active retry task 的 ingestion 连续点击 retry。

Then：

- 不创建 run 3；
- 返回当前 active run。

- [ ] PASS
- [ ] FAIL

---

# G. API、权限与安全

## G01｜OCR 状态 API 可恢复真实状态【P0】

调用：

```text
GET /api/v1/ingestions/{id}/ocr
```

或最终 PLAN 等价路径。

分别验证：

- QUEUED；
- PROCESSING；
- PENDING_CONFIRMATION；
- OCR_FAILED。

返回值来自数据库真实状态，不依赖前端本地缓存。

- [ ] PASS
- [ ] FAIL

---

## G02｜跨用户开始 OCR 被拒绝【P0】

User A 对 User B ingestion 调用 recognize。

不得创建 task，不得泄露资源存在性。

- [ ] PASS
- [ ] FAIL

---

## G03｜跨用户 OCR 状态读取被拒绝【P0】

User A 不得读取 User B OCR task / summary。

- [ ] PASS
- [ ] FAIL

---

## G04｜跨用户 Retry 被拒绝【P0】

User A 不得 retry User B ingestion。

- [ ] PASS
- [ ] FAIL

---

## G05｜前端与日志不泄露敏感信息【P0】

检查：

- API 不返回 COS 永久 Secret；
- API 不返回 Python traceback；
- 普通日志不记录完整 OCR 全文；
- 普通日志不记录完整检验结果；
- 普通日志不记录 Token；
- 普通日志不记录永久文件 URL。

允许日志记录：

- request_id；
- user_id 内部 ID；
- ingestion_id；
- task_id；
- run_no；
- status；
- duration；
- error_code。

- [ ] PASS
- [ ] FAIL

---

# H. 小程序

## H01｜READY 页面真实开始识别【P0】

Stage 02 的占位提示已替换。

Given：ingestion = READY。

When：点击“开始识别”。

Then：

- 调用真实 recognize API；
- 不 mock OCR 成功；
- 成功后进入识别处理中页。

- [ ] PASS
- [ ] FAIL

---

## H02｜防重复点击【P0】

连续快速点击“开始识别”。

Then：

- UI 不产生多次有效提交；
- 后端幂等继续兜底；
- 最终只有一个 active task。

- [ ] PASS
- [ ] FAIL

---

## H03｜识别开始后图片 UI 只读【P0】

进入 QUEUED / PROCESSING 后：

- 原图仍能查看；
- 追加图片不可操作；
- 删除不可操作；
- 排序不可操作；
- 页面明确提示已进入识别。

- [ ] PASS
- [ ] FAIL

---

## H04｜P06 处理页状态完整【P0】

至少展示：

- QUEUED；
- PROCESSING；
- PENDING_CONFIRMATION；
- OCR_FAILED。

不得用固定倒计时伪造 OCR 进度。

- [ ] PASS
- [ ] FAIL

---

## H05｜离开页面后可恢复【P0】

流程：

```text
开始识别
→ 离开处理页
→ 返回首页/关闭小程序
→ 再进入对应任务
```

Then：

- 从 API 恢复真实状态；
- 不依赖前端内存；
- Worker 仍在后台独立处理。

- [ ] PASS
- [ ] FAIL

---

## H06｜成功状态只提示“待确认”【P0】

OCR 完成后页面可以显示：

```text
识别完成，待确认
共识别 X 项
自动候选 X 项
待重点核对 X 项
```

但本阶段不得：

- 进入逐项人工确认；
- 编辑指标；
- commit；
- 生成正式报告。

- [ ] PASS
- [ ] FAIL

---

## H07｜失败可触发真实 Retry【P0】

OCR_FAILED 页面点击“重新识别”：

- 调用真实 retry API；
- 新 run 创建；
- 页面重新进入 QUEUED / PROCESSING。

同时应提供返回重新上传/新建任务的可达路径。

- [ ] PASS
- [ ] FAIL

---

# I. 自动测试、Lint 与构建

## I01｜Backend Tests【P0】

运行：

```text
backend/.venv/Scripts/python.exe -m pytest -q
```

或当前平台等价命令。

要求：

- Stage 01/02 既有测试全部继续通过；
- Stage 03 新测试全部通过；
- 不删除或跳过旧测试制造 PASS。

记录：

```text
Command:
Tests:
Passed:
Failed:
Warnings:
```

- [ ] PASS
- [ ] FAIL

---

## I02｜Backend Ruff【P0】

运行：

```text
backend/.venv/Scripts/ruff.exe check . --no-cache
```

或当前平台等价命令。

- [ ] PASS
- [ ] FAIL

---

## I03｜PostgreSQL Queue Integration【P0】

必须单独记录真实 PostgreSQL 17 队列测试结果。

至少覆盖：

- 双 session 原子 claim；
- SKIP LOCKED / 等价锁语义；
- lease 恢复；
- run_no 唯一约束。

- [ ] PASS
- [ ] FAIL

---

## I04｜PoC Regression 记录完整【P0】

`RESULT.md` 中必须记录：

```text
PoC source:
Snapshot/Commit:
Regression command:
Frozen Regression:
Core logic:
Safety Regression:
```

如 Stage 03 对 OCR 算法核心有任何改动，还必须说明该改动已先在 PoC / Regression 中验证。

- [ ] PASS
- [ ] FAIL

---

## I05｜Miniapp Typecheck【P0】

```text
miniapp/pnpm typecheck
```

- [ ] PASS
- [ ] FAIL

---

## I06｜Miniapp Build【P0】

```text
miniapp/pnpm build:mp-weixin
```

- [ ] PASS
- [ ] FAIL

---

## I07｜Admin Web 未被破坏【P0】

至少：

```text
admin-web/pnpm typecheck
admin-web/pnpm build
```

- [ ] PASS
- [ ] FAIL

---

# J. 真实工程闭环验收

## J01｜真实 OCR 主流程【P0】

使用脱敏、人工构造或经许可的真实格式测试报告，在真实微信开发者工具 / 正式本地工程环境完成：

```text
微信登录
↓
选择健康档案
↓
上传 1..N 张报告图片
↓
ReportIngestion = READY
↓
点击开始识别
↓
OcrTask = QUEUED
↓
Worker 领取
↓
PROCESSING
↓
Worker 从私有 COS 下载原图
↓
正式 OCR Pipeline
↓
保存 OCR artifact
↓
写入 OcrResultItem
↓
SUCCEEDED
↓
ReportIngestion = PENDING_CONFIRMATION
↓
小程序显示 total / AUTO / REVIEW 汇总
```

并人工确认：

- 原始图片仍存在；
- 图片未被 OCR 覆盖；
- 没有生成正式 LabReport / LabResult。

- [ ] PASS
- [ ] FAIL

---

## J02｜多页真实流程【P0】

至少使用一份 2 页或以上报告。

确认：

- page_no 顺序正确；
- Pipeline 接收到的页序正确；
- OcrResultItem 可追溯到来源页；
- 原图仍可逐页预览。

- [ ] PASS
- [ ] FAIL

---

## J03｜Worker 重启恢复【P0】

至少一次人工/集成方式验证：

```text
task 已持久化
→ Worker 停止
→ Worker 重启
→ 任务继续处理或按 lease 正确恢复
```

不得丢任务，不得直接标成功。

- [ ] PASS
- [ ] FAIL

---

# K. 阶段边界

## K01｜未提前实现 ConfirmationItem【P0】

Stage 03 不创建正式可编辑确认工作区。

允许存在后续阶段的类型声明/空目录，但不得产生真实业务行为。

- [ ] PASS
- [ ] FAIL

---

## K02｜未生成正式健康数据【P0】

数据库中不得因为 OCR 成功自动产生：

- LabReport；
- LabResult；
- 趋势数据；
- 指标历史正式数据。

- [ ] PASS
- [ ] FAIL

---

## K03｜未提前实现 Stage 04 交互【P0】

小程序不得提前具备：

- REVIEW resolved；
- 指标编辑；
- 标准指标人工选择；
- 按原名称保存；
- 手工新增指标；
- 疑似重复确认；
- commit。

- [ ] PASS
- [ ] FAIL

---

## K04｜未把算法研究混入产品阶段【P0】

Stage 03 RESULT 中不得用“本阶段重新调参后样本准确率提升”作为主要成果。

若确有算法问题：

- 回 PoC / Regression 修复；
- 验证后再迁入产品。

- [ ] PASS
- [ ] FAIL

---

# L. 文档与最终判定

## L01｜README 更新【P0】

至少记录：

- Stage 03 当前状态；
- OCR Worker 本地启动方式；
- 必要 OCR 依赖安装方式；
- 不提交真实医疗数据和密钥；
- 当前成功终态为 `PENDING_CONFIRMATION`。

- [ ] PASS
- [ ] FAIL

---

## L02｜RESULT.md 完整【P0】

必须记录：

- 实际完成项；
- 实际变更文件；
- migration；
- Pipeline 来源/版本；
- OCR 依赖；
- 自动测试；
- PostgreSQL queue 验证；
- 真实 Pipeline smoke test；
- 人工主流程；
- 设计偏差；
- 已知问题；
- Stage 04 注意事项。

不得只写“代码已完成”。

- [ ] PASS
- [ ] FAIL

---

# M. 最终判定

Stage 03 只有在以下条件全部满足时才能标记为 `PASS`：

```text
A～L 所有 P0 = PASS
+
真实 PostgreSQL 队列锁语义已验证
+
至少一次已验证正式 OCR Pipeline 工程闭环通过
+
真实私有 COS 原图输入通过
+
多页输入通过
+
失败/重试通过
+
Worker 恢复通过
+
小程序处理页恢复通过
+
OcrResultItem 可追溯且未被人工覆盖
+
成功终态 = PENDING_CONFIRMATION
+
未创建 ConfirmationItem
+
未生成 LabReport / LabResult
+
RESULT.md 已更新
```

任意 P0 未完成则：

```text
Stage 03 = FAIL
```

不得以“接口写完”“Mock 已通过”“OCR PoC 以前验证过”替代正式产品工程闭环验收。
