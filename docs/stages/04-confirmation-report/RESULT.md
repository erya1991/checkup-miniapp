# Stage 04｜检验结果人工确认与正式报告生成：实施结果

**Stage 04 = PASS（2026-09-30）**。

代码、migration、后端测试、PostgreSQL 集成与两端构建已通过；项目负责人已在真实微信小程序中完成 W01～W04 人工验收并反馈全部 PASS。结合既有工程验证，冻结 ACCEPTANCE 的全部 P0 已有通过证据，Stage 04 完成验收收口。人工记录来自负责人本次反馈，工程验证仍单独注明；本次仅更新 README 与本 RESULT，未修改业务代码、数据库或测试，未重复运行完整验收链路。Stage 05 尚未开始实施。

## 1. 实际完成项

- 新增 StandardMetric、ConfirmationItem、LabReport、LabResult，临时域/正式域独立；ingestion 增加医院、检验日期/时间、编号、分类、初始化时间、confirmed_at。
- 首次 GET confirmation 在 ingestion 行锁下从最新成功 run 的 OcrResultItem 初始化；检查来源、总数、连续序号、原图/manifest 页关系。全部初始化写入在同一事务，失败回滚；唯一约束防并发重复。保存后工作区冻结。
- AUTO 默认 RESOLVED/OCR_AUTO/ACCEPTED，允许主动修改；REVIEW 默认 PENDING，支持 ACCEPTED/CORRECTED/STANDARD_METRIC_SELECTED/KEEP_ORIGINAL_NAME/REMOVED。人工编辑不 UPDATE/DELETE OcrResultItem，REMOVED 仍留审计。
- 非数值结果保留文本；简单数值/比较符及区间保守解析，不可靠时留空。人工改变结果/参考/单位/身份后清空旧 abnormal；新单位清空旧 normalized unit，不做医学判断或跨单位换算。
- 漏识别手工补项和后续编辑；READY/OCR_FAILED 有有效原图可幂等转 MANUAL，复用统一确认页，保留失败 run 和原始资产。
- 报告级信息人工填写/持久化、本人 ACTIVE 档案保存前调整；日期不使用上传或创建时间补齐。
- StandardMetric 12 条版本化最小 seed，一次迁移落库；code/name 只读搜索。未知 OCR code 保持 NULL，不从 runtime 反写数据库，不做管理后台。
- 疑似重复返回最小候选摘要、允许返回修改或明确继续；凭证绑定当前数据、保存版本和当前候选集。
- commit 全量再校验、ingestion/档案行锁、单 PostgreSQL 事务生成报告和全部非 REMOVED 结果，同事务更新 CONFIRMED/confirmed_at。来源 UNIQUE 和已保存返回保障双击/超时/并发幂等，不依赖 COS 写操作。
- 小程序真实确认 API、REVIEW 优先、AUTO 编辑、标准选择、按原名保存、补录、原图核对、档案调整、重复提示及最小成功反馈；OCR 完成页/旧任务列表/READY/失败手工入口已接通。响应丢失后支持幂等恢复。

## 2. 实际变更文件与 Git 范围

- 后端既有文件：`backend/app/models/entities.py`、`backend/app/models/__init__.py`、`backend/app/api/v1/business.py`（行锁读取刷新）、`backend/app/main.py`（确认路由/错误 details/安全日志）。
- 后端新增：`backend/app/confirmation.py`、`backend/app/api/v1/confirmation.py`、`backend/migrations/versions/0004_confirmation_report.py`、`backend/migrations/data/standard_metrics_v1.json`、`backend/tests/test_stage04.py`、`backend/tests/verify_postgres_confirmation.py`。
- 小程序：`miniapp/package.json`、`miniapp/src/api.ts`、`miniapp/src/ingestion-tasks.ts`、`miniapp/src/pages.json`、`miniapp/src/pages/ocr/index.vue`、`miniapp/src/pages/upload/index.vue`、`miniapp/src/pages/confirmation/index.vue`、`miniapp/src/confirmation.ts`、`miniapp/tests/ingestion-tasks.test.mjs`、`miniapp/tests/confirmation.test.mjs`。
- 当前保留的工程文档：根 `README.md`、`backend/README.md`、本 RESULT。
- Stage 04 实施没有改写冻结 `PLAN.md` / `ACCEPTANCE.md`、0001～0003、Worker/Pipeline/runtime、Admin 业务代码或依赖版本。
- 本次文档收尾开始时工作区干净；负责人已完成此前实现的提交、推送与文档删除。已移除过期的未提交/未推送描述及旧工作区计数。本次变更仅为根 README 与本 RESULT，Git 操作由负责人后续自行执行。

## 3. Migration 与本地旧任务

Migration：`0004_confirmation_report`，down_revision=`0003_ocr`，新增报告确认字段及四张表、外键、索引、来源唯一约束；保留已应用历史迁移。

下表是实施时 migration / 初始化的工程验证快照，计数不代表负责人完成人工验收后的当前业务数据。本次文档收尾不查询或修改数据库。

| 验证 | Before | After / 实际结果 |
| --- | --- | --- |
| 本地既有 PostgreSQL 17.11 | alembic `0003_ocr` | `alembic upgrade head` → `0004_confirmation_report` PASS |
| 本地数据计数 | User 1、Profile 3、ingestion 3、asset 5、OcrTask 3、OcrResultItem 108 | 六项数量全部保持不变 |
| 原有首个待确认任务 | 59 项，无 ConfirmationItem | 幂等初始化 59 项，其中 2 项 PENDING；无需重新 OCR |
| 全部本地机器快照 | 108 条快照内容摘要 | 初始化前后所有字段摘要相同；未输出医疗全文 |
| 实施时本地正式域 | 无正式报告 | 当时 LabReport 0、LabResult 0；Codex 未替用户处理 REVIEW/commit |
| 临时旧库 | 在 0003 真实反射表中写合成老任务 | 升至 0004，双 session 初始化同一组 ID、快照不变 PASS |
| 临时空库 | 唯一命名空 PostgreSQL 17 | 0001 → 0002 → 0003 → 0004 完整迁移 PASS |

已执行的本地迁移命令 cwd=`backend`：`.venv/Scripts/alembic.exe current`、`.venv/Scripts/alembic.exe upgrade head`。实施时仅初始化真实旧任务候选；其后负责人已完成 REVIEW 处理与最终 commit，并确认 W01/W02 PASS，无需重新 OCR。

## 4. StandardMetric seed 来源和边界

- 文件：`backend/migrations/data/standard_metrics_v1.json`，版本 `stage04-v1`，SHA-256 `d50ef440bfb510d851b3b0b64b32a1ad6b83848dc597a7288aedfc7e8e94a2d5`。
- 实现侧逐项核对当前冻结 Stage 03 `metric_library.json` 的身份 code，选取 ALT、AST、TP、ALB、TBIL、DBIL、WBC、RBC、HGB、PLT、GLU、CREA 作为最小集合；中文名称为产品显示名，原报告名称独立保留。
- 只迁入 code/name/status 等身份，不迁入 aliases、全局参考范围、单位换算、安全规则或算法参数。UUID 由固定命名空间和 code 确定，数据库 code UNIQUE。
- seed 经 Git 文件版本追踪，由 0004 bulk_insert 一次执行；业务启动、Worker 和确认初始化只查询正式表，不加载 runtime 指标库建主数据。
- 未纳入这 12 项的 OCR code 不表示不能保存：NULL 关联，REVIEW 通过选指标或 KEEP_ORIGINAL_NAME 明确解决。以后扩充采用新 seed 版本/新增迁移，不重写 0004。

## 5. duplicate、事务与幂等

重复范围严格为同 User + 同 HealthProfile + 已 commit LabReport。

1. 强规则：NFKC/去空白/casefold 后非空 report_no 相同，且医院相同或任一方医院缺失。
2. 组合规则：检验日期相同、非空医院规范化相同、指标集合 Jaccard（交集/并集）≥ **0.8**。集合优先 standard_metric_id，没有关联时用规范化 metric_name。
3. 不同档案不比较；无医院且无报告号不猜测重复。重复仅提示，不覆盖、不合并、不平均。
4. 最终 commit 重新计算候选集；HMAC-SHA256 acknowledgement 绑定当前报告字段、所有确认项值/状态/更新时间、ingestion 更新时间和候选集。任一编辑或新候选变化都要求重新确认。

API 对当前用户 ingestion `SELECT FOR UPDATE`；保存前工作区初始化、编辑、补项、手工转换全部共享该锁。commit 还锁当前 ACTIVE 档案，串行同档案保存，使并发生成的重复候选在最终检查时可见。service 不单独 commit，router 一次 commit/异常 rollback。

正式数据唯一约束：`LabReport.source_ingestion_id`、`LabResult.source_confirmation_item_id`；确认来源唯一约束：`ConfirmationItem.source_ocr_result_item_id`。已 CONFIRMED 返回已有报告，不再写正式项目。报告/结果日期由确认字段复制，来源为最终 ConfirmationItem。事务不做 COS 上传、复制、路径迁移。

## 6. 自动测试、集成与构建

以下保留此前实际执行的工程验证结果。本次纯文档收尾不重跑 pytest、OCR、PostgreSQL 集成或两端构建。

| cwd | Command | Tests / Passed / Failed / Warnings |
| --- | --- | --- |
| backend | `.venv/Scripts/python.exe -m pytest -q` | **52 / 52 / 0**；1 条上游 Starlette/httpx 弃用警告；无 skip/删除/弱化测试 |
| backend | `.venv/Scripts/ruff.exe check . --no-cache` | PASS，All checks passed |
| backend | `.venv/Scripts/python.exe tests/verify_postgres_confirmation.py` | PASS；PostgreSQL 17、旧库与空库迁移、并发初始化、真实除零数据库异常回滚、两个独立 session commit、幂等重试、三来源 UNIQUE、OCR 不变；两座本次临时库删除 |
| backend | `.venv/Scripts/python.exe tests/verify_postgres_queue.py` | PASS；SKIP LOCKED、单 Worker advisory lock、自定义短 lease/renew/restart、run_no UNIQUE；临时库删除 |
| miniapp | `pnpm test` | **13 / 13 / 0**，无 skip；Node 提示既有未声明 package module type |
| miniapp | `pnpm typecheck` | PASS |
| miniapp | `pnpm build:mp-weixin` | PASS，确认页已生成于 dist/build/mp-weixin；uni-app 仅提示可更新，未升级 |
| admin-web | `pnpm typecheck` | PASS |
| admin-web | `pnpm build` | PASS；既有 >500kB chunk 警告，未扩大 Stage 04 优化范围 |

后端测试包括 Stage 01～03 原 17 项回归及 Stage 04 的来源异常/初始化回滚、五种处理、AUTO 修改、手工编辑/纯手工、报告日期、档案权限、只读主数据、重复凭证失效、commit 字段再校验、缺失来源禁止保存、正式值/来源/日期、半途异常回滚、安全日志和小程序 PUT 契约。小程序测试覆盖状态路由、REVIEW 分组、编辑 payload、NULL 身份/文本结果及已保存响应丢失后的恢复。

补充结构核对：对已升级本地 PostgreSQL 的五个 Stage 04 涉及表执行 Alembic compare_metadata，ORM 与实际 migration 无差异；seed 的全部 code 均存在于冻结库；`git diff --check` PASS。没有修改 PoC/runtime 文件来完成这些检查。

首次默认只读沙箱 pytest 无可写临时目录，重用正式命令并允许测试临时写入后通过；未改测试以绕过环境限制。创建新页面/seed 目录及构建也只允许本任务目录与产物的必要写入。静态检查和自动测试不是人工验收。

## 7. 真实微信小程序人工验收

验收执行者为项目负责人；以下按其 2026-09-30 本次反馈记录，Codex 未代操作微信小程序，未补写未反馈的人工操作。正式字段、来源与机器快照不变的工程核对保留在第 6、10 节。

| 项目 | 最终结果 | 负责人实际反馈 |
| --- | --- | --- |
| W01 OCR 完整确认 | PASS（负责人实机人工验收） | REVIEW_PENDING 阻断、原图查看、REVIEW 确认正确、REVIEW 人工修改、AUTO 主动修改、StandardMetric 选择、按原名称保存、手工补项、退出重进恢复、最终 commit、已保存状态：全部 PASS |
| W02 老任务 | PASS（负责人实机人工验收） | Stage 03 老任务无需重新 OCR、多次进入项目无重复：全部 PASS；结合 W01 完成确认与 commit |
| W03 纯手工 | PASS（负责人实机人工验收） | READY → 手工录入、手工新增 2 项、文本结果保存、原图保留、退出重进、commit：全部 PASS |
| W04 疑似重复 | PASS（负责人实机人工验收） | 疑似重复提示、返回修改、仍然保存、原报告未覆盖、修改数据后重新判断：全部 PASS |

工程构建产物位置：`D:\git\checkup-miniapp\miniapp\dist\build\mp-weixin`。

负责人确认：W01 处理完成后，任务列表仍显示“自动 57 项 / 待核对 2 项”。这些数字来自 Stage 03 `OcrTask.result_summary` 的 OCR 初始机器识别摘要，不是 Confirmation 实时处理进度。重新进入确认页后，REVIEW 处理状态、AUTO 人工修改、手工补项、报告信息均保留，Confirmation 数据没有丢失，因此退出重进恢复 PASS。

负责人确认 KEEP_ORIGINAL_NAME 可用。业务语义为 `metric_name = 用户确认后的原报告名称`、`standard_metric_id = NULL`、`resolution = KEEP_ORIGINAL_NAME`；允许正式保存，未来不得直接参与 StandardMetric 趋势聚合。当前状态二次展示不够明确，按第 8 节记录后续 UI 优化。

前端超时重试（P05）、OCR_FAILED 转手工（U02）及 REVIEW 删除入口的未明确反馈部分保留为工程验证：既有 helper 模拟响应丢失恢复、后端/PG 幂等测试、失败手工转换保留原图测试和页面可达入口核对；不声称负责人额外执行了这些场景。

## 8. 设计差异、已知问题与范围

- 确认更新增加等价 PUT（小程序使用），保留 PATCH；原因是当前 uni.request 类型未声明 PATCH。未做强制类型绕过或框架升级。
- workspace 采用首次 GET/编辑的按需初始化，不把确认初始化异常引入 Worker 成功结算；保存必须是已初始化完整工作区。符合旧任务补偿范围，Worker/OCR 算法未改。
- duplicate 在最终 commit 计算并返回提示，不新增持久化 duplicate_status 或独立重复检查页面；报告信息仍存 ingestion，acknowledgement 使用当前版本 fingerprint。
- 人工编辑后的 abnormal 采用安全清空策略，不实现新的医学判断；用户新单位不擅自归一化。Stage 04 只需文本保存和可信正式值，趋势单位处理不提前实现。
- 12 条 seed 是最小主数据，无法覆盖全部冻结 OCR code；不影响按原名称保存。API 查询只读、最多 100 条。
- 真实微信 W01～W04 已由负责人验收通过；超时恢复等未明确反馈的操作仅记录既有工程验证，不补写人工过程。
- 识别任务记录中的 AUTO/REVIEW 数字当前表示 OCR 初始机器结果，不是 Confirmation 实时处理进度；任务卡片文案留待后续统一 UI/交互优化，不阻塞 Stage 04。
- KEEP_ORIGINAL_NAME 当前缺少更明确的状态展示；留待后续统一 UI/交互优化，不阻塞 Stage 04。本次不修改上述两项 UI。
- UI 沿用现有功能版，未做大规模视觉精修。Stage 02 已有的 COS 上传成功但登记失败孤儿对象清理债务继续记录，未扩大实现。
- 未实现正式报告列表/详情/删除/已保存档案迁移、指标历史/趋势/关注、任何主数据或 OCR 管理后台；没有 Trend/MetricAlias/MetricFavorite/AuditLog 扩展。

## 9. 下一阶段注意事项

Stage 04 已验收通过并停止于本阶段。Stage 05 尚未开始实施，必须另行明确启动，查询只用正式 LabReport/LabResult，保持来源追溯和原图私有访问。正式删除须处理 COS 清理，档案迁移属于保存后正式域能力。后续标准指标聚合排除 NULL 身份，使用 examination_date/time 和兼容单位，同一天多次检测保留。两项 UI 展示问题统一留到后续整体 UI/交互优化阶段。

## 10. ACCEPTANCE 逐项核对

下表按冻结 ACCEPTANCE 逐项记录证据：工程验证使用既有测试/集成/代码核对记录；人工验收只引用负责人本次真实微信 W01～W04 反馈；同时使用两类证据的项分别注明。未发现既无现有工程证据、又无本次实际操作证据的 P0。最终 Stage 04 = PASS。

| 编号 | 验收项 | 结果 | 证据 / 未验边界 |
| --- | --- | --- | --- |
| A01 | Stage 03 已验收能力未被破坏 | PASS（工程） | 既有 pytest/PG 队列回归；本地与两座临时库 migration；独立域表/约束 |
| A02 | 0004 Migration 可从 Stage 03 既有数据库升级 | PASS（工程） | 既有 pytest/PG 队列回归；本地与两座临时库 migration；独立域表/约束 |
| A03 | 干净 PostgreSQL 可完整迁移到 Stage 04 | PASS（工程） | 既有 pytest/PG 队列回归；本地与两座临时库 migration；独立域表/约束 |
| A04 | 正式域与临时域数据表保持分离 | PASS（工程） | 既有 pytest/PG 队列回归；本地与两座临时库 migration；独立域表/约束 |
| B01 | Stage 03 既有 PENDING\_CONFIRMATION 可补初始化 | PASS（工程） | test_stage04 来源/初始化异常回滚；PG 双 session 初始化；本地 59 项老任务 |
| B02 | Confirmation 初始化幂等 | PASS（工程） | test_stage04 来源/初始化异常回滚；PG 双 session 初始化；本地 59 项老任务 |
| B03 | 初始化失败不留下半套工作区 | PASS（工程） | test_stage04 来源/初始化异常回滚；PG 双 session 初始化；本地 59 项老任务 |
| B04 | 初始化来源只取成功 OCR 机器快照 | PASS（工程） | test_stage04 来源/初始化异常回滚；PG 双 session 初始化；本地 59 项老任务 |
| C01 | FINAL\_AUTO 默认 RESOLVED | PASS（工程） | test_old_workspace；AUTO/REVIEW 初始化与最终候选字段；机器快照比对 |
| C02 | FINAL\_REVIEW 默认 PENDING | PASS（工程） | test_old_workspace；AUTO/REVIEW 初始化与最终候选字段；机器快照比对 |
| C03 | AUTO / REVIEW 数量与 OCR 来源一致 | PASS（工程） | test_old_workspace；AUTO/REVIEW 初始化与最终候选字段；机器快照比对 |
| C04 | 初始化使用 Pipeline 最终候选但不覆盖原始名称事实 | PASS（工程） | test_old_workspace；AUTO/REVIEW 初始化与最终候选字段；机器快照比对 |
| D01 | 人工确认正确不修改 OcrResultItem | PASS（工程） | 五种处理前后完整 OcrResultItem 字段比对，选择/删除不改快照 |
| D02 | 人工修改不覆盖 OcrResultItem | PASS（工程） | 五种处理前后完整 OcrResultItem 字段比对，选择/删除不改快照 |
| D03 | 删除错误识别不删除 OcrResultItem | PASS（工程） | 五种处理前后完整 OcrResultItem 字段比对，选择/删除不改快照 |
| D04 | 选择标准指标不修改 OCR standard candidate | PASS（工程） | 五种处理前后完整 OcrResultItem 字段比对，选择/删除不改快照 |
| E01 | 确认正确 | PASS（工程） | test_review_actions 五种参数化场景，API 修改后 GET 读回 |
| E02 | 人工修改 | PASS（工程） | test_review_actions 五种参数化场景，API 修改后 GET 读回 |
| E03 | 选择标准指标 | PASS（工程） | test_review_actions 五种参数化场景，API 修改后 GET 读回 |
| E04 | 按原名称保存 | PASS（工程） | test_review_actions 五种参数化场景，API 修改后 GET 读回 |
| E05 | 删除错误识别 | PASS（工程） | test_review_actions 五种参数化场景，API 修改后 GET 读回 |
| F01 | AUTO 默认不要求逐项操作 | PASS（工程） | test_complete_ocr_commit；未逐项点击 AUTO 可保存，主动修改来源与机器值独立 |
| F02 | AUTO 可以主动编辑 | PASS（工程） | test_complete_ocr_commit；未逐项点击 AUTO 可保存，主动修改来源与机器值独立 |
| F03 | AUTO 修改后来源机器值仍可追溯 | PASS（工程） | test_complete_ocr_commit；未逐项点击 AUTO 可保存，主动修改来源与机器值独立 |
| G01 | 非数值结果可保存 | PASS（工程） | test_manual_results_safe_parse；保留文本/简单数字/比较符，复杂结果和旧 abnormal 留空 |
| G02 | 简单数值可以安全结构化 | PASS（工程） | test_manual_results_safe_parse；保留文本/简单数字/比较符，复杂结果和旧 abnormal 留空 |
| G03 | 无法安全解析时不伪造 numeric | PASS（工程） | test_manual_results_safe_parse；保留文本/简单数字/比较符，复杂结果和旧 abnormal 留空 |
| G04 | 修改结果后旧 abnormal 不被盲目沿用 | PASS（工程） | test_manual_results_safe_parse；保留文本/简单数字/比较符，复杂结果和旧 abnormal 留空 |
| H01 | 医院信息可以人工填写或修改 | PASS（工程） | report_info/invalid_fields/complete_commit；日期必填与正式日期复制，空时间/编号可保存 |
| H02 | 检验日期为正式必填字段 | PASS（工程） | report_info/invalid_fields/complete_commit；日期必填与正式日期复制，空时间/编号可保存 |
| H03 | 检验时间允许为空 | PASS（工程） | report_info/invalid_fields/complete_commit；日期必填与正式日期复制，空时间/编号可保存 |
| H04 | 报告编号允许为空 | PASS（工程） | report_info/invalid_fields/complete_commit；日期必填与正式日期复制，空时间/编号可保存 |
| H05 | 报告信息退出重进可恢复 | PASS（人工验收） | 负责人 W01 确认报告信息退出重进仍保留；W03 手工流程退出重进 PASS |
| H06 | 正式报告时间不使用上传时间 | PASS（工程） | report_info/invalid_fields/complete_commit；日期必填与正式日期复制，空时间/编号可保存 |
| I01 | 正式保存前可调整所属档案 | PASS（工程） | complete_commit 与跨用户/profile 校验；duplicate profile 修改旧凭证失效 |
| I02 | 不能调整到他人 HealthProfile | PASS（工程） | complete_commit 与跨用户/profile 校验；duplicate profile 修改旧凭证失效 |
| I03 | 切换档案后重复检测使用新档案 | PASS（工程） | complete_commit 与跨用户/profile 校验；duplicate profile 修改旧凭证失效 |
| J01 | 正式 StandardMetric 基础数据存在 | PASS（工程） | migration 12 条 seed/code UNIQUE；搜索、映射/未知 code 测试；runtime 无反写 |
| J02 | StandardMetric 可只读查询 | PASS（工程） | migration 12 条 seed/code UNIQUE；搜索、映射/未知 code 测试；runtime 无反写 |
| J03 | OCR candidate 可映射正式 StandardMetric | PASS（工程） | migration 12 条 seed/code UNIQUE；搜索、映射/未知 code 测试；runtime 无反写 |
| J04 | 未知 OCR code 不自动创建 StandardMetric | PASS（工程） | migration 12 条 seed/code UNIQUE；搜索、映射/未知 code 测试；runtime 无反写 |
| J05 | 不运行时反写 PoC metric\_library | PASS（工程） | migration 12 条 seed/code UNIQUE；搜索、映射/未知 code 测试；runtime 无反写 |
| J06 | 按原名称保存不会进入标准指标身份 | PASS（工程） | migration 12 条 seed/code UNIQUE；搜索、映射/未知 code 测试；runtime 无反写 |
| K01 | 可以新增漏识别项目 | PASS（工程） | 手工新增/修改/GET 和正式 MANUAL 来源测试 |
| K02 | 手工项可继续编辑 | PASS（工程验证） | 既有手工新增/修改/GET 与正式 MANUAL 来源测试；确认页已采用项编辑入口核对。负责人 W01/W03 另确认补项退出重进保留，未补写手工项再编辑的人工操作 |
| K03 | 手工项 commit 后生成正式 LabResult | PASS（工程） | 手工新增/修改/GET 和正式 MANUAL 来源测试 |
| L01 | 纯手工模式仍要求原始报告图片 | PASS（工程） | manual_fallback/文本参数化场景；有图/合法状态、失败 run 留存、纯手工正式生成 |
| L02 | READY 报告可进入手工录入 | PASS（工程） | manual_fallback/文本参数化场景；有图/合法状态、失败 run 留存、纯手工正式生成 |
| L03 | OCR\_FAILED 可转为手工录入 | PASS（工程） | manual_fallback/文本参数化场景；有图/合法状态、失败 run 留存、纯手工正式生成 |
| L04 | 纯手工报告可以完整 commit | PASS（工程） | manual_fallback/文本参数化场景；有图/合法状态、失败 run 留存、纯手工正式生成 |
| M01 | 无重复时正常 commit | PASS（工程） | duplicates fingerprint 参数化、组合规则、不同档案隔离、继续保存保留两份 |
| M02 | 同档案强重复可以识别 | PASS（工程） | duplicates fingerprint 参数化、组合规则、不同档案隔离、继续保存保留两份 |
| M03 | 日期 + 医院 + 指标集合组合重复可提示 | PASS（工程） | duplicates fingerprint 参数化、组合规则、不同档案隔离、继续保存保留两份 |
| M04 | 疑似重复只提示，不禁止保存 | PASS（工程） | duplicates fingerprint 参数化、组合规则、不同档案隔离、继续保存保留两份 |
| M05 | 重复提示不覆盖旧报告 | PASS（工程） | duplicates fingerprint 参数化、组合规则、不同档案隔离、继续保存保留两份 |
| M06 | 不同 HealthProfile 不互相提示重复 | PASS（工程） | duplicates fingerprint 参数化、组合规则、不同档案隔离、继续保存保留两份 |
| M07 | 重复 acknowledgement 对数据修改失效 | PASS（工程） | duplicates fingerprint 参数化、组合规则、不同档案隔离、继续保存保留两份 |
| N01 | 存在 REVIEW PENDING 时禁止 commit | PASS（工程） | 完整 OCR flow、空/全部移除、commit 字段再校验、NULL 身份场景 |
| N02 | 全部 REVIEW resolved 后可以继续 | PASS（工程） | 完整 OCR flow、空/全部移除、commit 字段再校验、NULL 身份场景 |
| N03 | 没有正式保留项目禁止 commit | PASS（工程） | 完整 OCR flow、空/全部移除、commit 字段再校验、NULL 身份场景 |
| N04 | 正式项目指标名不能为空 | PASS（工程） | 完整 OCR flow、空/全部移除、commit 字段再校验、NULL 身份场景 |
| N05 | 正式项目结果不能为空 | PASS（工程） | 完整 OCR flow、空/全部移除、commit 字段再校验、NULL 身份场景 |
| N06 | 未匹配 StandardMetric 不阻止 commit | PASS（工程） | 完整 OCR flow、空/全部移除、commit 字段再校验、NULL 身份场景 |
| O01 | LabReport 与 LabResult 单事务生成 | PASS（工程） | pytest 与 PG 真实数据库异常回滚；状态/数量/REMOVED；service 无 COS 操作 |
| O02 | 成功 commit 状态一致 | PASS（工程） | pytest 与 PG 真实数据库异常回滚；状态/数量/REMOVED；service 无 COS 操作 |
| O03 | REMOVED 项不生成 LabResult | PASS（工程） | pytest 与 PG 真实数据库异常回滚；状态/数量/REMOVED；service 无 COS 操作 |
| O04 | commit 事务不依赖 COS 写操作 | PASS（工程） | pytest 与 PG 真实数据库异常回滚；状态/数量/REMOVED；service 无 COS 操作 |
| P01 | 重复 commit 返回同一正式报告 | PASS（工程） | PG 双独立 session commit、已保存重试、数据库两来源 UNIQUE |
| P02 | LabReport source\_ingestion\_id 数据库唯一 | PASS（工程） | PG 双独立 session commit、已保存重试、数据库两来源 UNIQUE |
| P03 | 并发 commit 只生成一份报告 | PASS（工程） | PG 双独立 session commit、已保存重试、数据库两来源 UNIQUE |
| P04 | LabResult source\_confirmation\_item 不重复 | PASS（工程） | PG 双独立 session commit、已保存重试、数据库两来源 UNIQUE |
| P05 | 前端超时重试安全 | PASS（工程验证） | miniapp/tests/confirmation.test.mjs 模拟成功响应丢失后 CONFIRMATION_LOCKED 恢复；后端已保存重试及 PG 并发/唯一约束通过；非负责人实机超时模拟 |
| Q01 | LabReport 数据来源正确 | PASS（工程） | complete_commit/手工 commit 核对最终报告/结果/来源/数量/检验日期 |
| Q02 | LabResult 数量正确 | PASS（工程） | complete_commit/手工 commit 核对最终报告/结果/来源/数量/检验日期 |
| Q03 | OCR\_AUTO 正式来源正确 | PASS（工程） | complete_commit/手工 commit 核对最终报告/结果/来源/数量/检验日期 |
| Q04 | OCR\_CORRECTED 正式来源正确 | PASS（工程） | complete_commit/手工 commit 核对最终报告/结果/来源/数量/检验日期 |
| Q05 | MANUAL 正式来源正确 | PASS（工程） | complete_commit/手工 commit 核对最终报告/结果/来源/数量/检验日期 |
| Q06 | KEEP\_ORIGINAL\_NAME 正式保存正确 | PASS（工程） | complete_commit/手工 commit 核对最终报告/结果/来源/数量/检验日期 |
| Q07 | 正式检验时间复制正确 | PASS（工程） | complete_commit/手工 commit 核对最终报告/结果/来源/数量/检验日期 |
| R01 | OCR\_AUTO 链路可追溯 | PASS（工程） | 完整来源外键、机器/人工/正式值比对，REMOVED 留存，MANUAL 关联 ingestion/原图 |
| R02 | 人工修改链路同时保留机器值与人工值 | PASS（工程） | 完整来源外键、机器/人工/正式值比对，REMOVED 留存，MANUAL 关联 ingestion/原图 |
| R03 | REMOVED 仍可审计 | PASS（工程） | 完整来源外键、机器/人工/正式值比对，REMOVED 留存，MANUAL 关联 ingestion/原图 |
| R04 | MANUAL 可追溯到原始报告 ingestion | PASS（工程） | 完整来源外键、机器/人工/正式值比对，REMOVED 留存，MANUAL 关联 ingestion/原图 |
| S01 | 跨用户读取 Confirmation 被拒绝 | PASS（工程） | 跨用户六类操作拒绝；ACTIVE/profile 归属；异常日志无合成敏感值 |
| S02 | 跨用户修改 ConfirmationItem 被拒绝 | PASS（工程） | 跨用户六类操作拒绝；ACTIVE/profile 归属；异常日志无合成敏感值 |
| S03 | 跨用户手工新增被拒绝 | PASS（工程） | 跨用户六类操作拒绝；ACTIVE/profile 归属；异常日志无合成敏感值 |
| S04 | 跨用户修改报告信息被拒绝 | PASS（工程） | 跨用户六类操作拒绝；ACTIVE/profile 归属；异常日志无合成敏感值 |
| S05 | 跨用户 commit 被拒绝 | PASS（工程） | 跨用户六类操作拒绝；ACTIVE/profile 归属；异常日志无合成敏感值 |
| S06 | 普通日志不泄露医疗全文 | PASS（工程） | 跨用户六类操作拒绝；ACTIVE/profile 归属；异常日志无合成敏感值 |
| T01 | PENDING\_CONFIRMATION 进入真实确认页 | PASS（人工验收） | 负责人 W01/W02：原有待确认任务进入确认页、无需重 OCR，最终 commit PASS |
| T02 | 确认页展示报告级信息 | PASS（工程＋人工） | 确认页报告字段/档案/原图入口代码核对；负责人 W01 确认报告信息填写及退出重进保留 PASS |
| T03 | REVIEW 优先展示且醒目标记 | PASS（工程＋人工） | groupedItems 测试与确认页待确认区域优先、warning 标记核对；负责人 W01 REVIEW 阻断及处理 PASS，非逐一反馈样式检查 |
| T04 | AUTO 默认采用并可展开编辑 | PASS（工程＋人工） | 既有 AUTO 默认采用/完整 commit 测试；负责人 W01 AUTO 主动修改、退出重进保留、最终 commit PASS |
| T05 | 原图可核对 | PASS（工程＋人工） | 鉴权原图工程验证；负责人 W01 原图查看、W03 原图保留 PASS |
| T06 | REVIEW 五种处理均有可达交互 | PASS（工程＋人工） | 负责人 W01 确认正确、人工修改、StandardMetric 选择、按原名称保存 PASS；删除按钮绑定 REMOVED 可达，五种处理参数化测试及移除后 commit 测试通过，未补写人工删除操作 |
| T07 | 可以添加漏识别项目 | PASS（人工验收） | 负责人 W01 手工补项、W03 手工新增 2 项与文本保存 PASS |
| T08 | 页面退出重进恢复真实进度 | PASS（人工验收） | 负责人 W01：REVIEW 状态、AUTO 修改、手工补项、报告信息均保留；W03 退出重进 PASS；任务卡片 57/2 为机器初始摘要 |
| T09 | REVIEW 未完成时最终保存有明确提示 | PASS（工程＋人工） | 负责人 W01 REVIEW_PENDING 阻断 PASS；页面 pending 数量提示/定位待确认区域代码及后端禁止生成正式报告测试通过 |
| T10 | commit 成功只显示最小成功反馈 | PASS（工程＋人工） | 负责人 W01 最终 commit、已保存状态 PASS；成功页仅报告保存成功/项目数/完成入口，未建设正式详情 |
| U01 | READY 可以选择手工录入 | PASS（人工验收） | 负责人 W03 READY → 手工录入、原图保留、2 项录入及 commit PASS |
| U02 | OCR\_FAILED 可以转手工录入 | PASS（工程验证） | test_manual_failed_ocr_preserves_history_requires_assets_and_legal_state 通过；失败页保留原图转手工按钮调用 /manual 后进入统一确认页；非负责人实机失败场景 |
| U03 | 手工录入复用同一 Confirmation 页面 | PASS（工程） | READY/OCR_FAILED 后端转换测试与统一确认页代码 |
| V01 | Backend Tests | PASS（工程） | 第 6 节实际命令与最终结果；全部自动检查通过 |
| V02 | Backend Ruff | PASS（工程） | 第 6 节实际命令与最终结果；全部自动检查通过 |
| V03 | PostgreSQL commit Integration | PASS（工程） | 第 6 节实际命令与最终结果；全部自动检查通过 |
| V04 | Miniapp Tests | PASS（工程） | 第 6 节实际命令与最终结果；全部自动检查通过 |
| V05 | Miniapp Typecheck | PASS（工程） | 第 6 节实际命令与最终结果；全部自动检查通过 |
| V06 | Miniapp Build | PASS（工程） | 第 6 节实际命令与最终结果；全部自动检查通过 |
| V07 | Admin Web 未被破坏 | PASS（工程） | 第 6 节实际命令与最终结果；全部自动检查通过 |
| W01 | Stage 03 OCR 报告完整确认流程 | PASS（人工验收） | 负责人真实微信 W01 全部 PASS，具体操作见第 7 节；正式字段/机器快照由既有工程验证核对 |
| W02 | Stage 03 老任务兼容 | PASS（人工验收） | 负责人真实微信 W02 PASS：老任务无需重 OCR、多次进入无重复；结合 W01 完成 commit |
| W03 | 纯手工报告完整流程 | PASS（人工验收） | 负责人真实微信 W03 全部 PASS：READY 手工、2 项/文本结果、原图保留、退出重进、commit；MANUAL 正式来源由工程验证核对 |
| W04 | 疑似重复真实流程 | PASS（人工验收） | 负责人真实微信 W04 全部 PASS：提示、返回修改、仍然保存、原报告未覆盖、修改后重新判断 |
| X01 | 未提前实现 Stage 05 报告管理 | PASS（工程） | git 范围核对，无 Stage 05/06/07 业务或 OCR 算法改动 |
| X02 | 未提前实现 Stage 06 指标趋势 | PASS（工程） | git 范围核对，无 Stage 05/06/07 业务或 OCR 算法改动 |
| X03 | 未提前实现 Stage 07 管理后台业务 | PASS（工程） | git 范围核对，无 Stage 05/06/07 业务或 OCR 算法改动 |
| X04 | 没有把 OCR 算法研发混入 Stage 04 | PASS（工程） | git 范围核对，无 Stage 05/06/07 业务或 OCR 算法改动 |
| Y01 | README 与 Stage 状态更新 | PASS（文档核对） | README 与本 RESULT 已同步 Stage 04 PASS、commit 正式数据边界及 Stage 05 未开始状态；无失效文档引用 |
| Y02 | RESULT.md 完整 | PASS（文档核对） | 实施/迁移/seed/重复/事务/自动测试/PG/负责人实机验收/设计差异/已知问题/下一阶段边界均记录；过期状态已清理 |

共 119 项 P0，全部按表中注明的工程、负责人实机人工或文档核对证据 PASS，无未通过项。既有自动测试与 PostgreSQL 集成通过，W01～W04 真实主流程通过，文档已同步。按冻结 Z 最终判定，**Stage 04 = PASS**；Stage 05 尚未开始实施。
