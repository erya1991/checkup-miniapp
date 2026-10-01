# Stage 06｜我的指标 / 指标历史与趋势：实施结果

实施及工程验证日期：2026-10-01。

**Stage 06 = PASS（要求的工程验证通过；项目负责人真实微信 T01～T09 人工验收全部 PASS）。**

最终收尾日期：2026-10-01。项目负责人在本次收尾指令中明确反馈 T01～T09 逐项 PASS，均记录为“负责人真实微信人工验收 PASS”。结合既有 PostgreSQL 17 验证和本次全部必要自动回归，冻结 ACCEPTANCE 的适用 P0 均满足；Q08 未新增依赖，按冻结条件为 N/A。人工证据来自负责人反馈，未以 Codex 自动验证替代。

## 1. 实施前基线与范围

开始时分支为 main，HEAD、本地 origin/main、远程 main 的最新 SHA 均为 `6ee06eafd395918351d127eed778736cb3134285`。Stage 05 RESULT 已正式 PASS。工作区仅有负责人提供的未跟踪 Stage 06 PLAN / ACCEPTANCE，未覆盖或修改它们。

依序读取 AGENTS、三个 baseline、Stage 06 PLAN / ACCEPTANCE、Stage 05 RESULT，再读取 DATA_MODEL、API_CONVENTIONS、SYSTEM_ARCHITECTURE 和相关 D-0003/D-0004。核对真实 HealthProfile、StandardMetric、LabReport、LabResult、Stage 04 commit、Stage 05 迁移/删除、migration head、前端页面和依赖后实施。

初版提交为 `b26b588a253e6b8b9c2480f37e790a10ccb65e14`（`stage06 初版提交`）。最终收尾开始时，HEAD 与 `origin/codex/stage06-metric-trend` 均已指向该提交，工作区 clean；本地/远程 main 均为上述 Stage 05 基线，没有未知新增提交。初版已经 commit 并 push，不能再描述为未提交的工作区修改。

本次最终 PASS 收尾为初版之后的独立文档提交，标题 `docs: finalize stage 06 acceptance`，仅修改下列四份文档。该最终提交的完整 SHA 以 `git log -1 --format=%H -- docs/stages/06-metric-trend/RESULT.md` 定位；分支推送、main 合入与远程最终 SHA 以实际 Git 核对和本轮最终汇报为准。

## 2. 实际修改文件

初版实施新增或修改 19 个实现、测试和说明文件，见下表。初版提交实际包含 21 个文件，另含负责人提供并冻结的 PLAN / ACCEPTANCE；两份冻结文档未由 Codex改写。本次最终收尾只修改 `docs/stages/06-metric-trend/RESULT.md`、根 `README.md`、`backend/README.md`、`docs/stages/06-metric-trend/README.md`，不修改业务代码、测试、migration、PLAN / ACCEPTANCE。

| 范围 | 文件 |
| --- | --- |
| 后端注册/模型 | `backend/app/main.py`、`backend/app/models/entities.py`、`backend/app/models/__init__.py` |
| 指标查询/API | `backend/app/profile_metrics.py`、`backend/app/api/v1/profile_metrics.py` |
| Migration | `backend/migrations/versions/0006_metric_trend.py` |
| 后端测试 | `backend/tests/test_stage06.py`、`backend/tests/verify_postgres_metrics.py` |
| 旧阶段专项兼容 | `backend/tests/verify_postgres_reports.py`（只将两处 head 固定为 0005，所有原有断言保留） |
| 小程序注册/入口 | `miniapp/src/pages.json`、`miniapp/src/pages/reports/index.vue` |
| 页面/图表/辅助逻辑 | `miniapp/src/pages/profile-metrics/index.vue`、`miniapp/src/pages/metric-detail/index.vue`、`miniapp/src/components/MetricTrendChart.vue`、`miniapp/src/profile-metrics.ts` |
| 小程序测试 | `miniapp/tests/profile-metrics.test.mjs` |
| 文档 | 根 `README.md`、`backend/README.md`、本 `RESULT.md` |

未修改 Stage 04 commit、Stage 05 report service/router、OCR Pipeline/matching/AUTO/REVIEW、StandardMetric 种子、历史 0001～0005 migration 或 admin-web 业务代码。

## 3. Migration 与数据模型

新增唯一 head `0006_metric_trend`，down_revision 为 `0005_report_management`：

- 新建 `metric_favorites`，仅含 id、health_profile_id FK、standard_metric_id FK、created_at。
- 命名 UNIQUE：`uq_metric_favorites_profile_metric(health_profile_id, standard_metric_id)`。
- 新增 `ix_lab_results_profile_metric_date(health_profile_id, standard_metric_id, examination_date)`。
- ORM 与这两项 Stage 06 结构一致。
- 不新增 user_id/report_id/latest_result_id 冗余字段，不新增 Trend/History/Latest 或同等业务表。
- 不回填或重写正式 LabResult；升级前后完整正式字段快照一致，既有报告直接可查询。

测试仅迁移隔离临时库，未迁移开发/目标业务数据库。部署或实机验收环境需自行执行 `alembic upgrade head` 并重启 API；目标环境 migration 未被记为本轮部署证据。

## 4. APIs 与实际查询

统一前缀 `/api/v1`，全部显式接收 health_profile_id：

| 方法 | 路径 | 实际返回/行为 |
| --- | --- | --- |
| GET | `/profile-metrics` | StandardMetric 身份、is_favorite、latest、history_count、trend_plottable_count、trend_series_count；服务端分页默认20、最大100 |
| GET | `/profile-metrics/{standard_metric_id}` | 上述单指标详情；无正式历史时 PROFILE_METRIC_NOT_FOUND |
| GET | `/profile-metrics/{standard_metric_id}/history` | 完整正式结果分页；默认50、最大100 |
| GET | `/profile-metrics/{standard_metric_id}/trend` | standard_metric、history_count、plottable_count、按单位分组的全部确定数值 points |
| PUT | `/favorites/{standard_metric_id}` | 关注，UNIQUE + PostgreSQL ON CONFLICT DO NOTHING，重复/并发幂等 |
| DELETE | `/favorites/{standard_metric_id}` | 取消关注，重复请求安全，返回 is_favorite=false |

每次先验证本人 ACTIVE HealthProfile；正式查询同时约束 LabResult 档案、LabReport owner 和档案。只读正式 LabResult，并要求 standard_metric_id 非空。不存在公共字典全量展示、未 commit 临时域补历史、同名字符串聚合或前端补映射。StandardMetric status 不作为既往正式历史过滤条件。

列表通过 row_number 窗口取得每指标 latest，通过批量 GROUP BY 取得历史/可绘制点/单位数，再一次 join 组装卡片；包括鉴权共4条 SQL 的测试证明不会随指标数产生无界 N+1。关注优先，其次最新检验日期/时间，再按标准指标 name/code/id；total 是正式出现的 distinct StandardMetric 数。

latest/history 使用 examination_date DESC、examination_time DESC NULLS LAST、report.created_at DESC、report.id DESC、result.sequence_no ASC、result.id ASC。技术字段只保证稳定，不替代检验时间。最新结果允许为“阴性”等非数值，主展示保留正式 result_text。history 保留同日、多报告、同报告重复标准指标、多单位、非数值和 comparator 的全部独立结果；不去重或平均。

trend 只接受持久化 result_numeric 非空且 comparator 为 NULL/空串/=。<、>、<=、>=、≤、≥及其它非等号 comparator 留在 history，不绘为精确点。即使文本看似数字，只要 numeric 为 NULL 也不重新解析。普通趋势无点时正常返回空 series。points 按冻结正序排序，每点保留 lab_result_id/report_id、真实检验日期/可空时间、value、result_text、unit、reference_text、abnormal。

单位只做首尾空白 trim：优先非空 normalized，再回退非空 original，两者缺失为无单位。使用带前缀的临时 series_key 避免真实单位与无单位哨兵碰撞，不写入数据库。区分大小写及不同文本，不进行换算或语义推断。同一指标只有一个身份/详情。series 的最近可绘制点顺序通过同次窗口查询取得，默认第一序列；每次只显示一个单位。

reference_text 与 abnormal 直接取单次正式记录。NULL abnormal 不表达“正常”，无固定正常带或医学趋势结论。响应不包含 COS object key、永久 URL、OCR 全文；普通日志沿用 request_id/path/status，不记录医疗数组。

## 5. Favorite 与报告生命周期

Favorite 是档案偏好，独立于报告。不同档案关注互不影响，迁移/删除不会迁移或删除 Favorite。

Stage 05 迁移/硬删除直接改变 LabResult，Stage 06 下一次查询自然改变 latest/history/trend，无额外同步表或任务。最后一条正式结果消失后，指标退出列表，dormant Favorite 保留；新正式历史出现或报告迁回时恢复已关注状态。

本轮既验证 API 删除后 COS 失败、正式指标立即变化，也在 PostgreSQL 中直接执行数据库删除逻辑、保留待清理项后核对查询。因此指标更新不依赖真实 COS cleanup 完成。本轮没有删除真实 COS 文件。

## 6. 小程序实际实现

新增“我的指标”和“指标详情与趋势”，从报告页进入，提供返回检验报告/我的指标和切换健康档案入口。

列表具备 loading、success、语义正确的 empty、持久 error/retry、服务端分页加载更多；显示当前档案、标准指标名/code、最新 result_text/单位/检验时间/abnormal、关注和历史数。

详情包含最新正式结果、关注/取消关注、按单位切换的数值趋势、点摘要/对应报告、完整历史和加载更多。全部主值使用 result_text，时间缺失明确写“时间未记录”。非数值/comparator 正常保留历史；无可绘制点显示“暂无可绘制数值趋势，历史结果仍可查看”。

本地 `MetricTrendChart.vue` 以 view/button/scroll-view 绘制折线和独立点，按服务器 points 顺序构造 category-like X 坐标；44px 点选热区、日期/时间标签、横向滑动、选中摘要和报告导航。日期不作为唯一 key，多个同日/同值点不合并。参考范围只在记录摘要展示。

onShow 重取默认档案和真实 APIs，请求版本在 onHide/onUnload 失效，旧列表/详情/分页/Favorite 响应不能写回新页面上下文。页面读取微信/uni-app 字体设置并采用相对字号和可换行内容。负责人已反馈冻结 T01～T09 全部 PASS；未提供独立字体档位、设备或版本明细，不补造此类执行记录。

复用统一 request 层、原生导航、按钮和 scroll-view；从历史/趋势进入 Stage 05 正式报告详情，再复用其原图入口。不另建原图/COS 实现。

**新增依赖：无。** package.json 和 lockfile 未修改；未升级 uni-app/Vue/Vite 或引入图表/Dashboard 框架。

## 7. 初版实施自动验证结果

下表为初版实施时实际执行的验证，保留原有 PostgreSQL 17 专项和回归证据；既有后端66项、小程序21项完整保留，无删除/skip/弱化：

| cwd | 命令 | 实际结果 |
| --- | --- | --- |
| backend | `.venv/Scripts/python.exe -m pytest -q` | PASS，84 passed，0 skipped；其中 Stage 06 为18项 |
| backend | `.venv/Scripts/ruff.exe check . --no-cache` | PASS，All checks passed |
| backend | `.venv/Scripts/alembic.exe heads` | 唯一 `0006_metric_trend (head)` |
| backend | `.venv/Scripts/python.exe tests/verify_postgres_metrics.py` | PASS，两座真实 PostgreSQL 17 临时库；0005→0006、空库升级、回退再升级、全部 Stage 06 场景 |
| backend | `.venv/Scripts/python.exe tests/verify_postgres_reports.py` | PASS，Stage 05 全部原断言/并发/事务/清理回归；两座临时库删除 |
| backend | `.venv/Scripts/python.exe tests/verify_postgres_confirmation.py` | PASS，Stage 04 原全部断言/快照/并发commit/回滚；两座临时库删除 |
| backend | `.venv/Scripts/python.exe tests/verify_postgres_queue.py` | PASS，Stage 03 在0006 head下的双会话/SKIP LOCKED/Worker锁/lease恢复/唯一约束 |
| miniapp | `pnpm test` | PASS，29 tests，0 skipped；Stage 06新增8项 |
| miniapp | `pnpm typecheck` | PASS |
| miniapp | `pnpm build:mp-weixin` | PASS，产物 `miniapp/dist/build/mp-weixin` |
| admin-web | `pnpm typecheck` | PASS |
| admin-web | `pnpm build` | PASS |
| root | `git diff --check` | PASS；另检查本轮未跟踪新增文件空白 |
| backend | 独立查询 pg_database 的 `checkup_stage0%` | PASS，剩余测试库为空列表 |

PostgreSQL Stage 06 验证包括：升级前已有正式快照完整保持；NULL时间排序；同日全部保留；非数值latest；所有 comparator 准入；normalized优先/original回退/无单位；Favorite双会话并发和数据库UNIQUE；主数据停用后历史仍可见；六类接口跨用户隔离；迁移后源/目标自然变化；删除后latest/history/trend变化；dormant保留和恢复；其它正式报告不受影响。两个临时库均在 finally 删除，并查询确认不存在。初次测试失败创建的临时库也已 finally 清理，最终独立查询无残留。

Stage 00～05 回归还由全量 pytest/miniapp tests 覆盖正式列表/详情/原图、commit幂等、REVIEW_PENDING、KEEP_ORIGINAL_NAME、纯手工报告、疑似重复、机器快照不可变、完整删除和FileCleanup。历史阶段人工 PASS 事实保持；没有把它们作为本轮 T01～T09 的人工证据。

### 7.1 最终收尾自动回归（2026-10-01）

| cwd | 本次重新执行命令/核对 | 实际结果 |
| --- | --- | --- |
| backend | `.venv/Scripts/python.exe -m pytest -q` | PASS，84 passed，0 skipped |
| backend | `.venv/Scripts/ruff.exe check . --no-cache` | PASS，All checks passed |
| miniapp | `pnpm test` | PASS，29 tests，0 skipped |
| miniapp | `pnpm typecheck` | PASS |
| miniapp | `pnpm build:mp-weixin` | PASS，微信产物构建完成 |
| admin-web | `pnpm typecheck` | PASS |
| admin-web | `pnpm build` | PASS |
| root | `git diff --check` | PASS |
| backend | `.venv/Scripts/alembic.exe heads` | 唯一 `0006_metric_trend (head)` |
| backend | 独立只读查询 server_version / pg_database | PostgreSQL 17.11；`checkup_stage0%` 临时测试库剩余 `[]` |

已对照初版 `b26b588` 核对：本次没有业务代码、migration、测试或 PostgreSQL 验证脚本变更，之前 Stage 03～06 的 PostgreSQL 17 验证事实仍有效。按最终收尾范围未重复运行全部 PostgreSQL 专项；本次表格中的服务器版本及残留库核查为重新执行的只读验证，不冒充专项重跑。

## 8. 设计偏差与已知问题

- Stage 06 产品/数据语义无 PLAN / ACCEPTANCE 设计偏差。API采用等价 is_favorite 字段；本地图表为冻结允许方案。
- **既有 Stage 03 schema 差异**：0003 migration 创建 `ix_ocr_tasks_queue(status,next_attempt_at)`，当前 ORM 是 `ix_ocr_tasks_status(status)`。额外执行的全库 `alembic check` 因这两项历史差异失败，不能宣称全库零漂移。新专项分别比较0005升级前和0006升级后，严格证明除本阶段新表/索引外仅这两项既有差异，且升级前后相同；任何其它差异会失败。没有修改 OCR ORM、旧migration或删掉既有断言来消除差异。此项为非 Stage 06 阻塞项，留待独立工程维护；本轮不修复。
- 冻结要求的真实微信 T01～T09 已由项目负责人完成并逐项反馈 PASS；对应指标、交互和报告/原图链路人工验收已满足。未提供设备、版本、独立字体档位或生产部署明细，不推断额外验证。
- Codex 初版实施及本次收尾未执行目标业务库升级、部署、真实微信操作或真实 COS 删除；真实微信人工操作按负责人反馈归属。Stage PASS 不额外代表生产部署或上线验证。
- 保留已有非阻塞警告：FastAPI/Starlette TestClient弃用、Node模块类型提示、Admin大产物，以及uni-app更新提示；未为消除警告升级依赖。
- 验证阶段修正了新测试缺失原图夹具、字体字段类型兼容、迁移测试必须显式重复确认和新代码Ruff格式问题，最终要求的测试均通过。

## 9. Stage 07 与后续边界

未实现 StandardMetric/MetricAlias 管理API/UI、MetricAlias模型、指标种子扩充、OCR算法或AUTO/REVIEW修改、历史正式结果重关联/回填、正式结果编辑、冗余Trend/History/Latest表或医学解释。

Stage 06 最终 PASS 后，本轮仅完成文档和 Git 收尾，未进入 Stage 07。Stage 07 仍需独立边界确认及冻结 PLAN / ACCEPTANCE 后另行授权；既往正式数据重关联需独立设计，不能靠同名猜测批量 UPDATE。

## 10. 项目负责人真实微信 T01～T09 人工验收记录

证据来源：项目负责人于 2026-10-01 在最终收尾指令中明确声明真实微信人工验收已全部完成，并逐项反馈 T01～T09 PASS。下表保留对应验收内容，结果均归属“负责人真实微信人工验收 PASS”，不是 Codex 实机执行或自动测试代验。

| 编号 | 操作与核对 | 当前结果 |
| --- | --- | --- |
| T01 | 首页→检验报告→我的指标，核对当前档案/正式卡片/latest；切换另一档案返回，核对数据完全切换且无旧请求闪回 | 负责人真实微信人工验收 PASS |
| T02 | 某标准指标准备≥3条正式历史，核对latest/日期/单位/各自参考和异常标记；从历史进入报告及原图 | 负责人真实微信人工验收 PASS |
| T03 | 同日≥2份同标准指标报告，核对两条history、两个独立trend点及各自报告，无平均/覆盖 | 负责人真实微信人工验收 PASS |
| T04 | 准备非数值及<、>、≤或≥结果，核对完整history、latest可显示真实新结果、普通图不画阈值或非数值点；无点指标显示正常空状态 | 负责人真实微信人工验收 PASS |
| T05 | ≥3个同单位确定数值，核对折线顺序/日期；点选查看正式result_text/本条参考，进入正确报告 | 负责人真实微信人工验收 PASS |
| T06 | 同标准指标准备≥2种单位，核对仍为一个详情、历史统一、单位可切换、默认最近可绘制序列、不混线不换算 | 负责人真实微信人工验收 PASS |
| T07 | 关注→返回列表确认优先→再进详情取消；切换另一档案核对关注独立 | 负责人真实微信人工验收 PASS |
| T08 | 记录源/目标latest/history/trend及Favorite；在Stage 05迁移测试报告，必要时明确重复确认；返回核对自然归属变化、Favorite不随报告迁移 | 负责人真实微信人工验收 PASS |
| T09 | 依次测试删除非最新、最新及最后一条报告，核对history/点减少、latest回退、最后指标退出列表，其它报告/指标不受影响 | 负责人真实微信人工验收 PASS |

T01～T09 全部 PASS。负责人未提供设备、微信版本等明细，本记录不补造未提供的执行信息。

## 11. 冻结验收逐项证据

下表的“工程PASS”只指已执行测试、PostgreSQL 验证或明确源码/构建核对；UI/真实交互证据由对应 T01～T09 的负责人真实微信 PASS 反馈补齐。Q08 因无新增依赖为 N/A；其余适用 P0 均 PASS，Stage 06 最终 PASS。自动验证与负责人证据分别归属，不扩展为未提供的设备/环境记录。

| 编号 | 验收项 | 本轮状态 | 实际证据与边界 |
| --- | --- | --- | --- |
| A01 | 只从 Stage 05 PASS 基线继续 | 工程PASS | 0006模型/migration核对；PG17两座库及正式快照跨升级比对 |
| A02 | 存在独立 Stage 06 migration | 工程PASS | 0006模型/migration核对；PG17两座库及正式快照跨升级比对 |
| A03 | 新增 MetricFavorite | 工程PASS | 0006模型/migration核对；PG17两座库及正式快照跨升级比对 |
| A04 | MetricFavorite 唯一约束 | 工程PASS | 0006模型/migration核对；PG17两座库及正式快照跨升级比对 |
| A05 | MetricFavorite 不冗余 user/report/latest | 工程PASS | 0006模型/migration核对；PG17两座库及正式快照跨升级比对 |
| A06 | LabResult 存在合理 profile+metric 查询索引 | 工程PASS | 0006模型/migration核对；PG17两座库及正式快照跨升级比对 |
| A07 | 不新增 Trend/History/Latest 业务表 | 工程PASS | 0006模型/migration核对；PG17两座库及正式快照跨升级比对 |
| A08 | 不新增 LabResult latest/trend 冗余字段 | 工程PASS | 0006模型/migration核对；PG17两座库及正式快照跨升级比对 |
| A09 | Stage 05 正式报告无需回填 | 工程PASS | 0006模型/migration核对；PG17两座库及正式快照跨升级比对 |
| B01 | “我的指标”只查询 LabResult | 工程PASS | test_stage06正式/NULL/临时域隔离与停用历史测试；种子及OCR未修改 |
| B02 | 必须显式 health_profile_id | 工程PASS | test_stage06正式/NULL/临时域隔离与停用历史测试；种子及OCR未修改 |
| B03 | HealthProfile ownership | 工程PASS | test_stage06正式/NULL/临时域隔离与停用历史测试；种子及OCR未修改 |
| B04 | 只聚合 standard_metric_id 非空结果 | 工程PASS | test_stage06正式/NULL/临时域隔离与停用历史测试；种子及OCR未修改 |
| B05 | NULL 标准指标不进入 history/trend | 工程PASS | test_stage06正式/NULL/临时域隔离与停用历史测试；种子及OCR未修改 |
| B06 | 禁止 metric_name 字符串聚合 NULL 指标 | 工程PASS | test_stage06正式/NULL/临时域隔离与停用历史测试；种子及OCR未修改 |
| B07 | Stage 06 不扩 StandardMetric 种子 | 工程PASS | test_stage06正式/NULL/临时域隔离与停用历史测试；种子及OCR未修改 |
| B08 | Stage 06 不实现 MetricAlias | 工程PASS | test_stage06正式/NULL/临时域隔离与停用历史测试；种子及OCR未修改 |
| B09 | 历史不因 StandardMetric status 隐藏 | 工程PASS | test_stage06正式/NULL/临时域隔离与停用历史测试；种子及OCR未修改 |
| C01 | 按 profile + StandardMetric 聚合 | 工程PASS | 列表distinct/计数/分页/关注与最近检测排序测试；卡片源码与构建 |
| C02 | 不同单位不拆成多个指标卡片 | 工程PASS | 列表distinct/计数/分页/关注与最近检测排序测试；卡片源码与构建 |
| C03 | 只展示真实出现过的指标 | 工程PASS | 列表distinct/计数/分页/关注与最近检测排序测试；卡片源码与构建 |
| C04 | history_count 正确 | 工程PASS | 列表distinct/计数/分页/关注与最近检测排序测试；卡片源码与构建 |
| C05 | 列表返回标准指标身份 | 工程PASS | 列表distinct/计数/分页/关注与最近检测排序测试；卡片源码与构建 |
| C06 | 列表返回 Favorite 状态 | 工程PASS | 列表distinct/计数/分页/关注与最近检测排序测试；卡片源码与构建 |
| C07 | 列表返回 latest | 工程PASS | 列表distinct/计数/分页/关注与最近检测排序测试；卡片源码与构建 |
| C08 | 最新主值使用 result_text | 工程PASS | 列表distinct/计数/分页/关注与最近检测排序测试；卡片源码与构建 |
| C09 | 列表分页 | 工程PASS | 列表distinct/计数/分页/关注与最近检测排序测试；卡片源码与构建 |
| C10 | 列表 Favorite 优先 | 工程PASS | 列表distinct/计数/分页/关注与最近检测排序测试；卡片源码与构建 |
| C11 | 同 Favorite 状态按最近检测优先 | 工程PASS | 列表distinct/计数/分页/关注与最近检测排序测试；卡片源码与构建 |
| C12 | 列表 empty 语义正确 | 工程PASS | 列表distinct/计数/分页/关注与最近检测排序测试；卡片源码与构建 |
| D01 | 主排序使用 examination_date | 工程PASS | 医学日期时间/NULL/报告与结果tie-breaker/非数值latest测试；PG17排序 |
| D02 | 同日优先 examination_time | 工程PASS | 医学日期时间/NULL/报告与结果tie-breaker/非数值latest测试；PG17排序 |
| D03 | 技术 tie-breaker 稳定 | 工程PASS | 医学日期时间/NULL/报告与结果tie-breaker/非数值latest测试；PG17排序 |
| D04 | 不把上传/OCR/commit 时间当医学最新时间 | 工程PASS | 医学日期时间/NULL/报告与结果tie-breaker/非数值latest测试；PG17排序 |
| D05 | 非数值可以成为最新结果 | 工程PASS | 医学日期时间/NULL/报告与结果tie-breaker/非数值latest测试；PG17排序 |
| D06 | 最新结果不得退回最新数值 | 工程PASS | 医学日期时间/NULL/报告与结果tie-breaker/非数值latest测试；PG17排序 |
| D07 | 同日多份报告不覆盖 | 工程PASS | 医学日期时间/NULL/报告与结果tie-breaker/非数值latest测试；PG17排序 |
| E01 | 详情显式绑定 profile + metric | 工程PASS | 完整history、独立ID、分页与正式字段断言；Stage05正式报告/原图回归 |
| E02 | 不存在历史则 PROFILE_METRIC_NOT_FOUND | 工程PASS | 完整history、独立ID、分页与正式字段断言；Stage05正式报告/原图回归 |
| E03 | 历史包含全部正式结果 | 工程PASS | 完整history、独立ID、分页与正式字段断言；Stage05正式报告/原图回归 |
| E04 | 历史不去重 | 工程PASS | 完整history、独立ID、分页与正式字段断言；Stage05正式报告/原图回归 |
| E05 | 历史不平均 | 工程PASS | 完整history、独立ID、分页与正式字段断言；Stage05正式报告/原图回归 |
| E06 | 历史最近在前 | 工程PASS | 完整history、独立ID、分页与正式字段断言；Stage05正式报告/原图回归 |
| E07 | 历史分页 | 工程PASS | 完整history、独立ID、分页与正式字段断言；Stage05正式报告/原图回归 |
| E08 | 历史保留正式 result_text | 工程PASS | 完整history、独立ID、分页与正式字段断言；Stage05正式报告/原图回归 |
| E09 | 历史单位信息完整 | 工程PASS | 完整history、独立ID、分页与正式字段断言；Stage05正式报告/原图回归 |
| E10 | 历史 reference_text 正确 | 工程PASS | 完整history、独立ID、分页与正式字段断言；Stage05正式报告/原图回归 |
| E11 | 历史 abnormal 直接读取 | 工程PASS | 完整history、独立ID、分页与正式字段断言；Stage05正式报告/原图回归 |
| E12 | 历史可进入正式报告 | PASS（工程＋负责人实机） | 完整history、独立ID、分页与正式字段断言；Stage05正式报告/原图回归；负责人实机T02 PASS |
| E13 | 正式报告原图链路复用 | PASS（工程＋负责人实机） | 完整history、独立ID、分页与正式字段断言；Stage05正式报告/原图回归；负责人实机T02 PASS |
| F01 | 只有 result_numeric 非空才可能画 | 工程PASS | 七类非等号comparator及numeric NULL/0/=测试；PG17同日点/正序；图表身份测试 |
| F02 | 普通数值 comparator NULL 可画 | 工程PASS | 七类非等号comparator及numeric NULL/0/=测试；PG17同日点/正序；图表身份测试 |
| F03 | 普通数值 comparator 空串可画 | 工程PASS | 七类非等号comparator及numeric NULL/0/=测试；PG17同日点/正序；图表身份测试 |
| F04 | comparator '=' 可画 | 工程PASS | 七类非等号comparator及numeric NULL/0/=测试；PG17同日点/正序；图表身份测试 |
| F05 | `<` 不画普通精确点 | 工程PASS | 七类非等号comparator及numeric NULL/0/=测试；PG17同日点/正序；图表身份测试 |
| F06 | `>` 不画普通精确点 | 工程PASS | 七类非等号comparator及numeric NULL/0/=测试；PG17同日点/正序；图表身份测试 |
| F07 | `<= / ≤` 不画普通精确点 | 工程PASS | 七类非等号comparator及numeric NULL/0/=测试；PG17同日点/正序；图表身份测试 |
| F08 | `>= / ≥` 不画普通精确点 | 工程PASS | 七类非等号comparator及numeric NULL/0/=测试；PG17同日点/正序；图表身份测试 |
| F09 | 非数值不强制转换为数字 | 工程PASS | 七类非等号comparator及numeric NULL/0/=测试；PG17同日点/正序；图表身份测试 |
| F10 | 趋势层不重新解析 result_text | 工程PASS | 七类非等号comparator及numeric NULL/0/=测试；PG17同日点/正序；图表身份测试 |
| F11 | 无可绘制点是正常空状态 | 工程PASS | 七类非等号comparator及numeric NULL/0/=测试；PG17同日点/正序；图表身份测试 |
| F12 | 趋势 points 全部绑定 lab_result_id/report_id | 工程PASS | 七类非等号comparator及numeric NULL/0/=测试；PG17同日点/正序；图表身份测试 |
| F13 | 同日多点全部返回 | 工程PASS | 七类非等号comparator及numeric NULL/0/=测试；PG17同日点/正序；图表身份测试 |
| F14 | 趋势正序 | 工程PASS | 七类非等号comparator及numeric NULL/0/=测试；PG17同日点/正序；图表身份测试 |
| F15 | NULL examination_time 不虚构时间 | 工程PASS | 七类非等号comparator及numeric NULL/0/=测试；PG17同日点/正序；图表身份测试 |
| F16 | 图表坐标来自已持久化 numeric | 工程PASS | 七类非等号comparator及numeric NULL/0/=测试；PG17同日点/正序；图表身份测试 |
| F17 | 用户点值仍显示 result_text | PASS（工程＋负责人实机） | 七类非等号comparator及numeric NULL/0/=测试；PG17同日点/正序；图表身份测试；负责人实机T05 PASS |
| F18 | 趋势点可回正式报告 | PASS（工程＋负责人实机） | 七类非等号comparator及numeric NULL/0/=测试；PG17同日点/正序；图表身份测试；负责人实机T03/T05 PASS |
| G01 | unit_normalized 优先 | 工程PASS | 五种单位、trim、无单位哨兵隔离、原单位回退测试；PG17分组与默认series |
| G02 | normalized 缺失回退 original | 工程PASS | 五种单位、trim、无单位哨兵隔离、原单位回退测试；PG17分组与默认series |
| G03 | 两者都缺失进入“无单位”序列 | 工程PASS | 五种单位、trim、无单位哨兵隔离、原单位回退测试；PG17分组与默认series |
| G04 | 不同单位不混入同一 series | 工程PASS | 五种单位、trim、无单位哨兵隔离、原单位回退测试；PG17分组与默认series |
| G05 | 不进行跨单位换算 | 工程PASS | 五种单位、trim、无单位哨兵隔离、原单位回退测试；PG17分组与默认series |
| G06 | 不做单位语义猜测 | 工程PASS | 五种单位、trim、无单位哨兵隔离、原单位回退测试；PG17分组与默认series |
| G07 | 同 StandardMetric 多单位仍只有一个详情 | 工程PASS | 五种单位、trim、无单位哨兵隔离、原单位回退测试；PG17分组与默认series |
| G08 | 多单位可切换 | PASS（工程＋负责人实机） | 五种单位、trim、无单位哨兵隔离、原单位回退测试；PG17分组与默认series；负责人实机T06 PASS |
| G09 | 默认选择最近可绘制序列 | PASS（工程＋负责人实机） | 五种单位、trim、无单位哨兵隔离、原单位回退测试；PG17分组与默认series；负责人实机T06 PASS |
| G10 | 历史不按单位拆散 | 工程PASS | 五种单位、trim、无单位哨兵隔离、原单位回退测试；PG17分组与默认series |
| H01 | 不创建 StandardMetric 全局参考范围 | 工程PASS | 本条reference/abnormal断言；既有abnormalLabel回归；页面无全局正常带或医学解释 |
| H02 | 不画固定全局正常带 | 工程PASS | 本条reference/abnormal断言；既有abnormalLabel回归；页面无全局正常带或医学解释 |
| H03 | 每条历史保留自身 reference_text | 工程PASS | 本条reference/abnormal断言；既有abnormalLabel回归；页面无全局正常带或医学解释 |
| H04 | 趋势点详情使用自身 reference_text | 工程PASS | 本条reference/abnormal断言；既有abnormalLabel回归；页面无全局正常带或医学解释 |
| H05 | abnormal 不重新计算 | 工程PASS | 本条reference/abnormal断言；既有abnormalLabel回归；页面无全局正常带或医学解释 |
| H06 | abnormal NULL 不显示为“正常” | 工程PASS | 本条reference/abnormal断言；既有abnormalLabel回归；页面无全局正常带或医学解释 |
| H07 | 不生成医学趋势结论 | 工程PASS | 本条reference/abnormal断言；既有abnormalLabel回归；页面无全局正常带或医学解释 |
| I01 | Favorite 属于 HealthProfile + StandardMetric | 工程PASS | Favorite幂等/唯一/档案/dormant恢复测试；PG17双会话并发UNIQUE |
| I02 | 关注幂等 | 工程PASS | Favorite幂等/唯一/档案/dormant恢复测试；PG17双会话并发UNIQUE |
| I03 | 取消关注幂等 | 工程PASS | Favorite幂等/唯一/档案/dormant恢复测试；PG17双会话并发UNIQUE |
| I04 | Favorite 跨 HealthProfile 隔离 | 工程PASS | Favorite幂等/唯一/档案/dormant恢复测试；PG17双会话并发UNIQUE |
| I05 | 报告迁移不迁移 Favorite | 工程PASS | Favorite幂等/唯一/档案/dormant恢复测试；PG17双会话并发UNIQUE |
| I06 | 报告删除不自动删除 Favorite | 工程PASS | Favorite幂等/唯一/档案/dormant恢复测试；PG17双会话并发UNIQUE |
| I07 | dormant Favorite 可保留 | 工程PASS | Favorite幂等/唯一/档案/dormant恢复测试；PG17双会话并发UNIQUE |
| I08 | 无历史 dormant Favorite 不显示空卡片 | 工程PASS | Favorite幂等/唯一/档案/dormant恢复测试；PG17双会话并发UNIQUE |
| I09 | 历史重新出现后 Favorite 状态恢复 | 工程PASS | Favorite幂等/唯一/档案/dormant恢复测试；PG17双会话并发UNIQUE |
| I10 | Stage 06 不实现关注提醒 | 工程PASS | Favorite幂等/唯一/档案/dormant恢复测试；PG17双会话并发UNIQUE |
| J01 | 指标列表跨用户隔离 | 工程PASS | 六类接口/ACTIVE/不存在资源同错误测试；页面guard慢响应与失效测试 |
| J02 | 指标详情跨用户隔离 | 工程PASS | 六类接口/ACTIVE/不存在资源同错误测试；页面guard慢响应与失效测试 |
| J03 | history 跨用户隔离 | 工程PASS | 六类接口/ACTIVE/不存在资源同错误测试；页面guard慢响应与失效测试 |
| J04 | trend 跨用户隔离 | 工程PASS | 六类接口/ACTIVE/不存在资源同错误测试；页面guard慢响应与失效测试 |
| J05 | Favorite PUT 跨用户隔离 | 工程PASS | 六类接口/ACTIVE/不存在资源同错误测试；页面guard慢响应与失效测试 |
| J06 | Favorite DELETE 跨用户隔离 | 工程PASS | 六类接口/ACTIVE/不存在资源同错误测试；页面guard慢响应与失效测试 |
| J07 | 无资源存在性泄露 | 工程PASS | 六类接口/ACTIVE/不存在资源同错误测试；页面guard慢响应与失效测试 |
| J08 | 切换默认 HealthProfile 后页面刷新 | PASS（工程＋负责人实机） | 六类接口/ACTIVE/不存在资源同错误测试；页面guard慢响应与失效测试；负责人实机T01 PASS |
| J09 | 旧 profile 响应不能覆盖新 profile | 工程PASS | 六类接口/ACTIVE/不存在资源同错误测试；页面guard慢响应与失效测试 |
| K01 | 迁移后源 profile 指标历史减少 | 工程PASS | API及PG17迁移/删除/最后结果/dormant/其它报告测试；COS失败时指标立即变化 |
| K02 | 迁移后目标 profile 指标历史增加 | 工程PASS | API及PG17迁移/删除/最后结果/dormant/其它报告测试；COS失败时指标立即变化 |
| K03 | 迁移后 latest 自然重算 | 工程PASS | API及PG17迁移/删除/最后结果/dormant/其它报告测试；COS失败时指标立即变化 |
| K04 | 迁移后 trend 自然变化 | 工程PASS | API及PG17迁移/删除/最后结果/dormant/其它报告测试；COS失败时指标立即变化 |
| K05 | 迁移不创建 Trend/History 同步任务 | 工程PASS | API及PG17迁移/删除/最后结果/dormant/其它报告测试；COS失败时指标立即变化 |
| K06 | 删除非最新报告后 history/trend 减少 | 工程PASS | API及PG17迁移/删除/最后结果/dormant/其它报告测试；COS失败时指标立即变化 |
| K07 | 删除最新报告后 latest 回退到下一条正式结果 | 工程PASS | API及PG17迁移/删除/最后结果/dormant/其它报告测试；COS失败时指标立即变化 |
| K08 | 删除最后一条标准指标结果后列表消失 | 工程PASS | API及PG17迁移/删除/最后结果/dormant/其它报告测试；COS失败时指标立即变化 |
| K09 | 删除后无需等待 COS cleanup 才更新指标 | 工程PASS | API及PG17迁移/删除/最后结果/dormant/其它报告测试；COS失败时指标立即变化 |
| K10 | 其它报告/指标不受影响 | 工程PASS | API及PG17迁移/删除/最后结果/dormant/其它报告测试；COS失败时指标立即变化 |
| L01 | 存在 profile metrics 列表 API | 工程PASS | 六条route、错误/request_id/响应隐私和日志断言；沿用统一安全日志 |
| L02 | 存在 profile metric detail API | 工程PASS | 六条route、错误/request_id/响应隐私和日志断言；沿用统一安全日志 |
| L03 | 存在 history API | 工程PASS | 六条route、错误/request_id/响应隐私和日志断言；沿用统一安全日志 |
| L04 | 存在 trend API | 工程PASS | 六条route、错误/request_id/响应隐私和日志断言；沿用统一安全日志 |
| L05 | 存在 Favorite PUT/DELETE API | 工程PASS | 六条route、错误/request_id/响应隐私和日志断言；沿用统一安全日志 |
| L06 | PROFILE_NOT_FOUND 稳定错误 | 工程PASS | 六条route、错误/request_id/响应隐私和日志断言；沿用统一安全日志 |
| L07 | STANDARD_METRIC_NOT_FOUND 稳定错误 | 工程PASS | 六条route、错误/request_id/响应隐私和日志断言；沿用统一安全日志 |
| L08 | PROFILE_METRIC_NOT_FOUND 稳定错误 | 工程PASS | 六条route、错误/request_id/响应隐私和日志断言；沿用统一安全日志 |
| L09 | 普通 API 不返回 COS object key | 工程PASS | 六条route、错误/request_id/响应隐私和日志断言；沿用统一安全日志 |
| L10 | 普通 API 不返回永久 COS URL | 工程PASS | 六条route、错误/request_id/响应隐私和日志断言；沿用统一安全日志 |
| L11 | 普通 API 不返回 OCR 全文 | 工程PASS | 六条route、错误/request_id/响应隐私和日志断言；沿用统一安全日志 |
| L12 | 日志不记录完整 history/trend 医疗数组 | 工程PASS | 六条route、错误/request_id/响应隐私和日志断言；沿用统一安全日志 |
| M01 | 从报告视角可进入“我的指标” | PASS（工程＋负责人实机） | 列表源码/路径/分页/guard/font测试与微信构建；负责人实机T01/T02/T07 PASS |
| M02 | 可从“我的指标”回到检验报告 | PASS（工程＋负责人实机） | 列表源码/路径/分页/guard/font测试与微信构建；负责人实机T01/T02/T07 PASS |
| M03 | 当前 HealthProfile 清晰展示 | PASS（工程＋负责人实机） | 列表源码/路径/分页/guard/font测试与微信构建；负责人实机T01/T02/T07 PASS |
| M04 | 支持切换健康档案入口 | PASS（工程＋负责人实机） | 列表源码/路径/分页/guard/font测试与微信构建；负责人实机T01/T02/T07 PASS |
| M05 | loading | PASS（工程＋负责人实机） | 列表源码/路径/分页/guard/font测试与微信构建；负责人实机T01/T02/T07 PASS |
| M06 | empty | PASS（工程＋负责人实机） | 列表源码/路径/分页/guard/font测试与微信构建；负责人实机T01/T02/T07 PASS |
| M07 | error/retry | PASS（工程＋负责人实机） | 列表源码/路径/分页/guard/font测试与微信构建；负责人实机T01/T02/T07 PASS |
| M08 | 加载更多 | PASS（工程＋负责人实机） | 列表源码/路径/分页/guard/font测试与微信构建；负责人实机T01/T02/T07 PASS |
| M09 | 指标卡片展示最新正式 result_text | PASS（工程＋负责人实机） | 列表源码/路径/分页/guard/font测试与微信构建；负责人实机T01/T02/T07 PASS |
| M10 | 指标卡片展示日期/单位/abnormal 提示 | PASS（工程＋负责人实机） | 列表源码/路径/分页/guard/font测试与微信构建；负责人实机T01/T02/T07 PASS |
| M11 | Favorite 状态可见 | PASS（工程＋负责人实机） | 列表源码/路径/分页/guard/font测试与微信构建；负责人实机T01/T02/T07 PASS |
| M12 | 点击进入指标详情 | PASS（工程＋负责人实机） | 列表源码/路径/分页/guard/font测试与微信构建；负责人实机T01/T02/T07 PASS |
| N01 | StandardMetric 名称/code 正确 | PASS（工程＋负责人实机） | 详情与本地图表源码、几何/身份/默认单位/导航/Favorite测试与微信构建；负责人实机T02～T09 PASS |
| N02 | 最新结果正确 | PASS（工程＋负责人实机） | 详情与本地图表源码、几何/身份/默认单位/导航/Favorite测试与微信构建；负责人实机T02～T09 PASS |
| N03 | Favorite 可关注 | PASS（工程＋负责人实机） | 详情与本地图表源码、几何/身份/默认单位/导航/Favorite测试与微信构建；负责人实机T02～T09 PASS |
| N04 | Favorite 可取消 | PASS（工程＋负责人实机） | 详情与本地图表源码、几何/身份/默认单位/导航/Favorite测试与微信构建；负责人实机T02～T09 PASS |
| N05 | 数值 trend 正常显示 | PASS（工程＋负责人实机） | 详情与本地图表源码、几何/身份/默认单位/导航/Favorite测试与微信构建；负责人实机T02～T09 PASS |
| N06 | 多单位可切换 | PASS（工程＋负责人实机） | 详情与本地图表源码、几何/身份/默认单位/导航/Favorite测试与微信构建；负责人实机T02～T09 PASS |
| N07 | 无可绘制点显示正常空状态 | PASS（工程＋负责人实机） | 详情与本地图表源码、几何/身份/默认单位/导航/Favorite测试与微信构建；负责人实机T02～T09 PASS |
| N08 | 同日多点不合并 | PASS（工程＋负责人实机） | 详情与本地图表源码、几何/身份/默认单位/导航/Favorite测试与微信构建；负责人实机T02～T09 PASS |
| N09 | 点击 trend point 可查看真实结果摘要 | PASS（工程＋负责人实机） | 详情与本地图表源码、几何/身份/默认单位/导航/Favorite测试与微信构建；负责人实机T02～T09 PASS |
| N10 | trend point 可打开正式报告 | PASS（工程＋负责人实机） | 详情与本地图表源码、几何/身份/默认单位/导航/Favorite测试与微信构建；负责人实机T02～T09 PASS |
| N11 | 完整历史列表正常显示 | PASS（工程＋负责人实机） | 详情与本地图表源码、几何/身份/默认单位/导航/Favorite测试与微信构建；负责人实机T02～T09 PASS |
| N12 | 非数值历史正常显示 | PASS（工程＋负责人实机） | 详情与本地图表源码、几何/身份/默认单位/导航/Favorite测试与微信构建；负责人实机T02～T09 PASS |
| N13 | comparator 历史正常显示 | PASS（工程＋负责人实机） | 详情与本地图表源码、几何/身份/默认单位/导航/Favorite测试与微信构建；负责人实机T02～T09 PASS |
| N14 | 历史项可打开正式报告 | PASS（工程＋负责人实机） | 详情与本地图表源码、几何/身份/默认单位/导航/Favorite测试与微信构建；负责人实机T02～T09 PASS |
| N15 | 报告原图继续可查看 | PASS（工程＋负责人实机） | 详情与本地图表源码、几何/身份/默认单位/导航/Favorite测试与微信构建；负责人实机T02～T09 PASS |
| N16 | 不显示自动医学解释 | PASS（工程＋负责人实机） | 详情与本地图表源码、几何/身份/默认单位/导航/Favorite测试与微信构建；负责人实机T02～T09 PASS |
| O01 | Backend Tests | 工程PASS | 全量pytest 84 passed、0 skipped；原66项保留；Ruff最终PASS |
| O02 | Backend Ruff | 工程PASS | 全量pytest 84 passed、0 skipped；原66项保留；Ruff最终PASS |
| O03 | 只正式数据聚合测试 | 工程PASS | 全量pytest 84 passed、0 skipped；原66项保留；Ruff最终PASS |
| O04 | NULL StandardMetric 排除测试 | 工程PASS | 全量pytest 84 passed、0 skipped；原66项保留；Ruff最终PASS |
| O05 | latest 排序测试 | 工程PASS | 全量pytest 84 passed、0 skipped；原66项保留；Ruff最终PASS |
| O06 | 非数值 latest 测试 | 工程PASS | 全量pytest 84 passed、0 skipped；原66项保留；Ruff最终PASS |
| O07 | 同日多份 history 测试 | 工程PASS | 全量pytest 84 passed、0 skipped；原66项保留；Ruff最终PASS |
| O08 | comparator trend 排除测试 | 工程PASS | 全量pytest 84 passed、0 skipped；原66项保留；Ruff最终PASS |
| O09 | non-numeric trend 排除测试 | 工程PASS | 全量pytest 84 passed、0 skipped；原66项保留；Ruff最终PASS |
| O10 | unit_normalized 优先测试 | 工程PASS | 全量pytest 84 passed、0 skipped；原66项保留；Ruff最终PASS |
| O11 | unit_original fallback 测试 | 工程PASS | 全量pytest 84 passed、0 skipped；原66项保留；Ruff最终PASS |
| O12 | 无单位 trend 测试 | 工程PASS | 全量pytest 84 passed、0 skipped；原66项保留；Ruff最终PASS |
| O13 | 多单位不混线测试 | 工程PASS | 全量pytest 84 passed、0 skipped；原66项保留；Ruff最终PASS |
| O14 | abnormal 不重算测试 | 工程PASS | 全量pytest 84 passed、0 skipped；原66项保留；Ruff最终PASS |
| O15 | Favorite 幂等/唯一约束测试 | 工程PASS | 全量pytest 84 passed、0 skipped；原66项保留；Ruff最终PASS |
| O16 | 跨用户六类接口测试 | 工程PASS | 全量pytest 84 passed、0 skipped；原66项保留；Ruff最终PASS |
| O17 | 迁移后 Stage 06 自然变化测试 | 工程PASS | 全量pytest 84 passed、0 skipped；原66项保留；Ruff最终PASS |
| O18 | 删除后 Stage 06 自然变化测试 | 工程PASS | 全量pytest 84 passed、0 skipped；原66项保留；Ruff最终PASS |
| P01 | 0005 → 0006 migration | 工程PASS | PG17两座库增量/空库/回退/并发/查询验证；独立pg_database核查无测试库残留 |
| P02 | 空库完整 migration | 工程PASS | PG17两座库增量/空库/回退/并发/查询验证；独立pg_database核查无测试库残留 |
| P03 | Stage 05 既有正式报告升级后直接聚合 | 工程PASS | PG17两座库增量/空库/回退/并发/查询验证；独立pg_database核查无测试库残留 |
| P04 | MetricFavorite UNIQUE 生效 | 工程PASS | PG17两座库增量/空库/回退/并发/查询验证；独立pg_database核查无测试库残留 |
| P05 | 同日多份结果 PostgreSQL 排序正确 | 工程PASS | PG17两座库增量/空库/回退/并发/查询验证；独立pg_database核查无测试库残留 |
| P06 | NULL examination_time 排序正确 | 工程PASS | PG17两座库增量/空库/回退/并发/查询验证；独立pg_database核查无测试库残留 |
| P07 | 多单位分组正确 | 工程PASS | PG17两座库增量/空库/回退/并发/查询验证；独立pg_database核查无测试库残留 |
| P08 | 迁移后 profile aggregation 正确 | 工程PASS | PG17两座库增量/空库/回退/并发/查询验证；独立pg_database核查无测试库残留 |
| P09 | 删除后 latest/history/trend 正确 | 工程PASS | PG17两座库增量/空库/回退/并发/查询验证；独立pg_database核查无测试库残留 |
| P10 | 临时 PostgreSQL 测试库全部删除 | 工程PASS | PG17两座库增量/空库/回退/并发/查询验证；独立pg_database核查无测试库残留 |
| Q01 | Miniapp Tests | 工程PASS | pnpm test 29通过、0 skipped；typecheck与微信构建PASS；纯函数/慢请求/几何/font测试 |
| Q02 | Miniapp Typecheck | 工程PASS | pnpm test 29通过、0 skipped；typecheck与微信构建PASS；纯函数/慢请求/几何/font测试 |
| Q03 | Miniapp Build | 工程PASS | pnpm test 29通过、0 skipped；typecheck与微信构建PASS；纯函数/慢请求/几何/font测试 |
| Q04 | 分页合并测试 | 工程PASS | pnpm test 29通过、0 skipped；typecheck与微信构建PASS；纯函数/慢请求/几何/font测试 |
| Q05 | 多单位默认选择测试 | 工程PASS | pnpm test 29通过、0 skipped；typecheck与微信构建PASS；纯函数/慢请求/几何/font测试 |
| Q06 | 同日 point identity 不去重测试 | 工程PASS | pnpm test 29通过、0 skipped；typecheck与微信构建PASS；纯函数/慢请求/几何/font测试 |
| Q07 | HealthProfile 切换旧响应保护 | 工程PASS | pnpm test 29通过、0 skipped；typecheck与微信构建PASS；纯函数/慢请求/几何/font测试 |
| Q08 | 如果新增图表依赖，lockfile 与构建一致 | N/A（未新增依赖） | pnpm test 29通过、0 skipped；typecheck与微信构建PASS；纯函数/慢请求/几何/font测试 |
| R01 | Admin Typecheck | 工程PASS | admin typecheck/build PASS；后台业务未修改，未新增指标/别名管理 |
| R02 | Admin Build | 工程PASS | admin typecheck/build PASS；后台业务未修改，未新增指标/别名管理 |
| R03 | 未实现 StandardMetric 后台 | 工程PASS | admin typecheck/build PASS；后台业务未修改，未新增指标/别名管理 |
| R04 | 未实现 MetricAlias 后台 | 工程PASS | admin typecheck/build PASS；后台业务未修改，未新增指标/别名管理 |
| S01 | Stage 04 commit 幂等仍通过 | 工程PASS | 原Stage00-05全量测试完整保留；Stage03/04/05 PostgreSQL全部原断言通过 |
| S02 | REVIEW_PENDING 阻断仍通过 | 工程PASS | 原Stage00-05全量测试完整保留；Stage03/04/05 PostgreSQL全部原断言通过 |
| S03 | KEEP_ORIGINAL_NAME 仍通过 | 工程PASS | 原Stage00-05全量测试完整保留；Stage03/04/05 PostgreSQL全部原断言通过 |
| S04 | 纯手工报告仍可 commit | 工程PASS | 原Stage00-05全量测试完整保留；Stage03/04/05 PostgreSQL全部原断言通过 |
| S05 | 疑似重复保存仍通过 | 工程PASS | 原Stage00-05全量测试完整保留；Stage03/04/05 PostgreSQL全部原断言通过 |
| S06 | OcrResultItem 不可变仍通过 | 工程PASS | 原Stage00-05全量测试完整保留；Stage03/04/05 PostgreSQL全部原断言通过 |
| S07 | Stage 05 正式报告列表/详情仍通过 | 工程PASS | 原Stage00-05全量测试完整保留；Stage03/04/05 PostgreSQL全部原断言通过 |
| S08 | Stage 05 原图 preview 仍通过 | 工程PASS | 原Stage00-05全量测试完整保留；Stage03/04/05 PostgreSQL全部原断言通过 |
| S09 | Stage 05 报告迁移仍通过 | 工程PASS | 原Stage00-05全量测试完整保留；Stage03/04/05 PostgreSQL全部原断言通过 |
| S10 | Stage 05 报告删除/FileCleanup 仍通过 | 工程PASS | 原Stage00-05全量测试完整保留；Stage03/04/05 PostgreSQL全部原断言通过 |
| T01 | 我的指标 + HealthProfile 切换 | 负责人真实微信人工验收 PASS | 项目负责人2026-10-01最终收尾指令逐项反馈PASS；自动验证未替代 |
| T02 | 最新结果 + 完整历史 | 负责人真实微信人工验收 PASS | 项目负责人2026-10-01最终收尾指令逐项反馈PASS；自动验证未替代 |
| T03 | 同一天多份报告 | 负责人真实微信人工验收 PASS | 项目负责人2026-10-01最终收尾指令逐项反馈PASS；自动验证未替代 |
| T04 | 非数值与 comparator | 负责人真实微信人工验收 PASS | 项目负责人2026-10-01最终收尾指令逐项反馈PASS；自动验证未替代 |
| T05 | 普通数值趋势 | 负责人真实微信人工验收 PASS | 项目负责人2026-10-01最终收尾指令逐项反馈PASS；自动验证未替代 |
| T06 | 多单位趋势 | 负责人真实微信人工验收 PASS | 项目负责人2026-10-01最终收尾指令逐项反馈PASS；自动验证未替代 |
| T07 | Favorite | 负责人真实微信人工验收 PASS | 项目负责人2026-10-01最终收尾指令逐项反馈PASS；自动验证未替代 |
| T08 | 正式报告迁移后的自然变化 | 负责人真实微信人工验收 PASS | 项目负责人2026-10-01最终收尾指令逐项反馈PASS；自动验证未替代 |
| T09 | 正式报告删除后的自然变化 | 负责人真实微信人工验收 PASS | 项目负责人2026-10-01最终收尾指令逐项反馈PASS；自动验证未替代 |
| U01 | 未实现 MetricAlias 数据模型 | 工程PASS | 真实修改范围核对；种子/OCR/旧migration/正式报告服务/admin未修改 |
| U02 | 未实现 StandardMetric 管理 API/UI | 工程PASS | 真实修改范围核对；种子/OCR/旧migration/正式报告服务/admin未修改 |
| U03 | 未扩充 StandardMetric 种子库 | 工程PASS | 真实修改范围核对；种子/OCR/旧migration/正式报告服务/admin未修改 |
| U04 | 未批量回填历史 standard_metric_id | 工程PASS | 真实修改范围核对；种子/OCR/旧migration/正式报告服务/admin未修改 |
| U05 | 未修改 OCR metric matching | 工程PASS | 真实修改范围核对；种子/OCR/旧migration/正式报告服务/admin未修改 |
| U06 | 未修改 AUTO/REVIEW threshold | 工程PASS | 真实修改范围核对；种子/OCR/旧migration/正式报告服务/admin未修改 |
| U07 | 未实现 AI 趋势解释/健康评分 | 工程PASS | 真实修改范围核对；种子/OCR/旧migration/正式报告服务/admin未修改 |
| U08 | 未进行任意跨单位数值换算 | 工程PASS | 真实修改范围核对；种子/OCR/旧migration/正式报告服务/admin未修改 |
| U09 | 未提供正式 LabResult 编辑 | 工程PASS | 真实修改范围核对；种子/OCR/旧migration/正式报告服务/admin未修改 |
| U10 | 未大规模重构 UI | 工程PASS | 真实修改范围核对；种子/OCR/旧migration/正式报告服务/admin未修改 |
| V01 | README/必要技术说明一致 | 工程PASS | README及RESULT核对；工程、人工、Git与部署证据分别记录；Stage06最终PASS；负责人T01～T09全部PASS |
| V02 | Stage 06 RESULT.md 完整 | 工程PASS | README及RESULT核对；工程、人工、Git与部署证据分别记录；Stage06最终PASS；负责人T01～T09全部PASS |
| V03 | 人工验收未完成前不得标 PASS | 工程PASS | README及RESULT核对；工程、人工、Git与部署证据分别记录；Stage06最终PASS；负责人T01～T09全部PASS |

最终判定：Stage 06 = PASS（全部适用 P0 满足；要求的工程验证与最终自动回归通过；负责人真实微信 T01～T09 全部 PASS；Q08 按条件 N/A；未进入 Stage 07）。
