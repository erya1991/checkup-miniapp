# Stage 07｜StandardMetric / MetricAlias 管理与 OCR 轻量管理：实施结果

实施与工程验证日期：2026-10-01。

**AUTOMATED PASS / WAITING MANUAL ACCEPTANCE**

自动验证通过。负责人真实 Admin Web / 微信 T01～T13 全部 PENDING，Stage 07 尚未最终 PASS。本结果不把接口测试、SQLite 单元测试、PostgreSQL 专项或构建成功记作负责人人工验收。

## 1. 基线与实际范围

开始分支 main；`git fetch origin main` 后 HEAD / origin/main 均为 `b2b60f3854b66e5d04ad99568849f42e5844ce27`，领先/落后 0/0。实施分支 `codex/stage07-admin`。初始工作区只有负责人提供的未跟踪 PLAN / ACCEPTANCE，两者未改写。

按 AGENTS 顺序读取根规则、Product/Tech/Development baseline、Stage 07 PLAN/ACCEPTANCE、Stage 06 RESULT，再按主题读取 DATA_MODEL、API_CONVENTIONS。核对真实模型、migration、Stage 04 确认、Stage 05 正式报告、Stage 06 聚合、OCR adapter/runtime 边界和 Admin 骨架。Stage 06 已正式 PASS。

实现按模型/normalization → 认证/主数据 API → 搜索/首次确认解析 → OCR 查询 → Admin Web → PG17/回归顺序推进。没有进入后续算法、历史修复、部署或 UI 打磨阶段。

本轮修改处于工作区，未 commit / push；没有升级配置的业务数据库、写入真实管理员配置或部署。全部 PostgreSQL 工程验证使用 UUID 隔离测试库和合成数据。

## 2. 实际能力与关键文件

| 范围 | 文件 / 实际行为 |
| --- | --- |
| 模型 / migration | `backend/app/models/entities.py`、`models/__init__.py`、`migrations/versions/0007_standard_metric_admin.py` |
| 产品 identity | `backend/app/metric_identity.py`：统一 normalization、exact resolver、PG namespace transaction lock |
| Admin 认证 | `backend/app/core/admin_auth.py`、`core/config.py`、`core/auth.py`、`.env.example` |
| 主数据 | `backend/app/admin_metrics.py`、`api/v1/admin.py`：列表/搜索/分页/新增/编辑/停用/恢复、引用统计、稳定错误 |
| OCR 只读排查 | `backend/app/admin_ocr.py`、`api/v1/admin.py`：三个 issue 类型和 Task status/version 筛选 |
| 注册 / 错误 | `backend/app/main.py`：注册 Admin，Admin 请求校验错误不回显敏感输入 |
| 确认最小兼容 | `backend/app/confirmation.py`、`api/v1/confirmation.py`：首次 exact 预关联、Alias 搜索、共享指标行锁 |
| Admin Web | `admin-web/src/api.ts`、`auth.ts`、`router.ts`、`App.vue`；登录/指标/详情/全局别名/问题/只读任务六页；MetricDialog、AliasDialog、AliasTable；`vite.config.ts` 开发 API 代理 |
| 新测试 | `backend/tests/test_stage07.py`（22项）、`verify_postgres_stage07.py` |
| 旧专项兼容 | `verify_postgres_confirmation.py`、`verify_postgres_reports.py`、`verify_postgres_metrics.py`；保留原断言，区分旧 schema 检查与最新业务回归 |
| 说明 | 根 / backend / admin-web README、`docs/01-architecture/DATA_MODEL.md`、本 RESULT |

StandardMetric code 去首尾空白并大写，创建后 PATCH 包含 code 即明确拒绝；name/category 可修改。无删除 API。Alias 保留原始输入、目标创建后只读，支持四种 type，停用/恢复重新检查。无 AdminUser/RBAC、复杂分类或 Issue 表。前后端均未新增依赖；package 与锁文件未修改。

Admin 使用配置的单管理员、PBKDF2-SHA256 600000 次迭代 hash、独立 >=32 字符 secret（不能等于 User secret）、scope/admin + audience JWT，8小时有效期。普通 Token 不能访问 Admin；Admin 不能冒充普通用户。前端 sessionStorage，统一 request / 401 / 稳定错误反馈。页面含 loading、empty、error/retry、分页和基础导航；真实 UI 使用验收仍待负责人执行。

普通 `/api/v1/standard-metrics?q=` 响应仍为 canonical StandardMetric 的兼容数组，按 code/name/ACTIVE Alias 搜索，以 EXISTS 避免同指标重复。停用的指标/别名不作为新选择。小程序原代码无需修改。

首次 Confirmation 初始化才执行 resolver：可靠 OCR code exact 优先；未命中才 raw_metric normalized canonical name/code exact，再 Alias exact。不使用 fuzzy、单位、参考范围或结果推断。已有工作区立即返回既有项目，不重算；commit、手工补项不调用 Alias resolver。KEEP_ORIGINAL_NAME 明确保持 NULL。REVIEW 命中仍 PENDING、resolution NULL。可靠 code 的 AUTO 保持原行为；无可靠 code 映射的 AUTO 只预填，仍需人工处理。

OCR issue 只投影名称/code/技术数量，按每 ingestion 最新 SUCCEEDED run_no 聚合，failed run 和旧成功 run 不重复计入。返回出现次数、报告数、最近时间，未匹配少量名称样例；当前 ACTIVE 主数据覆盖后动态退出 pending 列表，不修改机器快照。Task 只返回 id/ingestion/run/status/version/attempt/时间/错误码/三个整数数量；不返回患者、结果全文、reference、payload、COS key/URL，无任何写任务操作。

## 3. Migration 与模型结果

唯一 head `0007_standard_metric_admin`，down_revision `0006_metric_trend`。

- 只新增 `standard_metrics.category VARCHAR(80) NULL`。
- 新增 `metric_aliases`：id、standard_metric_id FK、alias、normalized_alias、alias_type、status、created_at、updated_at。
- CHECK 限定 ACTIVE/INACTIVE 与四种 alias_type。
- 索引 standard_metric_id、status、normalized_alias。
- PostgreSQL partial unique index `uq_metric_aliases_active_normalized(normalized_alias) WHERE status='ACTIVE'`；SQLite 单测使用对应 partial index。
- 0001～0006 与 12项 seed 原样保留；未全量导入 PoC 74项，未 backfill 任何 Confirmation/OCR/LabResult。
- 完整当前 metadata 比较只剩原 Stage 03 的两项差异：ORM `ix_ocr_tasks_status(status)`；migration `ix_ocr_tasks_queue(status,next_attempt_at)`。0007 不修复这两项，不宣称全库 `alembic check` PASS。

跨表写操作持 PG advisory transaction lock，使 Alias 与主数据 rename/create/restore 的检查和写入串行化；唯一索引仍保护直接或并发写入。停用持指标排他行锁，检查 PENDING_CONFIRMATION 引用并返回最小 `pending_count`；已 CONFIRMED / 正式引用不阻断。首次解析及 ACTIVE 校验持共享行锁，不取消 commit 校验。真实并发验证涵盖初始化与停用、commit 与停用。

## 4. 实际自动验证

执行环境 Python **3.12.10**、PostgreSQL **17.11**。未删除、skip 或弱化既有测试。

| cwd | 最终执行命令 | 结果 |
| --- | --- | --- |
| backend | `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp runtime/stage07-pytest-final-02` | PASS：106 passed，0 skipped，含既有84项 + Stage 07 22项 |
| backend | `.venv/Scripts/ruff.exe check . --no-cache` | PASS：All checks passed |
| backend | `.venv/Scripts/alembic.exe heads` | 唯一 `0007_standard_metric_admin (head)` |
| backend | `.venv/Scripts/python.exe tests/verify_postgres_stage07.py` | PASS：两座真实 PG17 隔离库、PG001～PG009，finally 删除并验证不存在 |
| backend | `.venv/Scripts/python.exe tests/verify_postgres_queue.py` | PASS：Stage 03 SKIP LOCKED / Worker锁 / lease / UNIQUE，当前0007 head |
| backend | `.venv/Scripts/python.exe tests/verify_postgres_confirmation.py` | PASS：Stage 04 原迁移、并发初始化/commit、真实回滚、来源UNIQUE、不可变快照；两库删除 |
| backend | `.venv/Scripts/python.exe tests/verify_postgres_reports.py` | PASS：Stage 05 原迁移、查询、迁移/删除/commit并发、回滚、全链清理、重试；两库删除 |
| backend | `.venv/Scripts/python.exe tests/verify_postgres_metrics.py` | PASS：Stage 06 原迁移/回退、旧快照、排序/准入/多单位、Favorite并发、权限、迁移删除；两库删除 |
| miniapp | `pnpm test` | PASS：29 tests，0 skipped |
| miniapp | `pnpm typecheck` | PASS |
| miniapp | `pnpm build:mp-weixin` | PASS：Build complete，`dist/build/mp-weixin` |
| admin-web | `pnpm typecheck` | PASS |
| admin-web | `pnpm build` | PASS：Vite build 完成，`dist/` |
| root | `git diff --check` + 新增自编文件空白核查 | PASS |
| backend | 独立查询 `pg_database` 中 `checkup_stage0%` | 无临时测试库残留 |

分批证据：模型接入后 Stage 04 35项通过；normalization/认证基础8项通过；Admin/解析/OCR 新测试与Stage04/06联合73项通过；随后全量104项通过，最终补充手工不自动绑定、canonical exact与长度边界后全量106项通过。

PG17 专项实际验证：0006→0007；空库0001→0007；回退0006再升级；迁移前后 OCR/Confirmation/正式/Favorite 完整快照一致；code 与 partial ACTIVE alias 直接数据库 UNIQUE；两个并发相同 code/normalized Alias 只成功一个；Alias与rename namespace竞态一个成功一个稳定拒绝；恢复冲突；pending保护；commit/deactivate竞态；首次初始化持共享锁时 deactivate阻塞，初始化提交后管理员收到pending错误；旧工作区不重算；正式NULL身份不回填；rename/inactive 后历史、趋势、收藏继续存在。完整模型差异仍只剩既有Stage03两项索引漂移。

## 5. 冲突、安全处理与已知问题

1. 实施前 `ensure_workspace` 对所有 FINAL_AUTO 直接 RESOLVED，即使 code 未映射。冻结 Stage 07 的 RV007 不允许 Alias 静默提升异常 AUTO。最小处理为只有可靠 ACTIVE OCR code exact 才自动 RESOLVED；其它解析可预填但保持 PENDING，机器 final_decision/source 快照不改。测试明确验证该异常组合。这是确认初始化的安全兼容处理，不是 OCR 判定调整。
2. 旧 PG04/05 脚本只升级到旧 schema 后调用最新服务，出现 `standard_metrics.category does not exist`。保留原迁移revision检查及所有业务断言，在旧schema断言后升级head再跑最新服务；PG05先用最新服务生成合成正式数据后回退0004再跑原增量迁移；PG06用历史metadata投影检查旧schema，再在head跑业务。PG07另检查完整metadata。没有删断言或修改历史migration。
3. 首次全量pytest为103通过+1 setup权限错误，原因是系统旧pytest临时目录访问被拒绝。改用仓库ignored runtime内的独立basetemp并关闭cache后，104及最终106项完整通过；未跳过测试。
4. 非阻塞工具提示：FastAPI TestClient 的既有 httpx/Starlette deprecation；小程序 Node 模块类型提示和uni-app升级通知；Admin包约1.07MB触发Vite chunk>500KB提醒。未为本阶段升级依赖或进行无关拆包。
5. 现有 StandardMetric.name 无全局唯一约束。normalized canonical name/code 对应多个ID时 resolver 保守返回NULL，不猜测；没有自行增加新的主数据唯一规则。

没有其它已知未实现的冻结业务能力。真实 UI/微信验收、目标环境迁移/管理员配置/启动与部署不属于已执行证据。最后停止在等待负责人反馈状态。

## 6. 冻结边界核对

| 边界 | 工程证据 |
| --- | --- |
| OcrResultItem immutable | Stage04/07自动测试、PG快照比较通过；Admin/OCR查询无写接口 |
| Alias不提升REVIEW | PENDING/resolution NULL断言、REVIEW_PENDING阻断通过 |
| 旧Confirmation不重算 | Alias/StandardMetric新增后重复进入保持相同；PG完整字段比较 |
| 旧LabResult不回填 | migration/主数据操作前后正式快照一致，NULL保持NULL |
| 停用不隐藏历史 | Stage06/07与PG detail/history/trend/favorite断言通过；profile_metrics.py未修改 |
| OCR runtime / matcher | `git diff` 对 `backend/ocr_runtime` 为空 |
| Pipeline Version | `backend/app/ocr_pipeline.py` 未修改；仍为 `poc-sha256:9f0c4c4c61351c84894a37cc4f44d3f8dd77003b40bcbd67a1bf34bc825ab6e6` |
| OCR thresholds / fuzzy / unit / retry | runtime、adapter、queue、Worker均未修改；无动态DB Alias注入 |
| 0001～0006 | 对旧migration的Git diff为空，0007独立新增 |
| Stage03 drift | PG完整metadata比较仍为原两项索引差异，未修复 |
| PoC库 / seed | 未修改PoC仓库；12项seed文件未改，空库升级只有12项、0 Alias |
| Miniapp / 既有报告服务 | miniapp源码、reports/profile_metrics/cleanup服务未修改 |
| 凭据 / 日志 | 仅example新增空配置；合成认证测试覆盖错误响应与日志不含密码/token |

## 7. 负责人 T01～T13 人工验收

验收准备：按 `admin-web/README.md` 在目标环境迁移0007、配置独立管理员、重启API/Admin，微信端继续使用真实API与私有COS；只使用专门测试或脱敏报告。工程测试数据库已删除，不能直接作为人工样本。T06需未首次打开确认页的REVIEW任务；T07需已初始化工作区；T08需既有按原名保存的正式结果；T09/T10需已有标准指标正式历史且T10无pending引用。不要通过手工SQL修改真实医疗数据制造场景。

以下保留冻结验收步骤和预期。每项由负责人反馈 PASS/FAIL、执行环境、必要的失败说明；全部仍 PENDING。

| 编号 | 负责人步骤 | 预期 | 状态 |
| --- | --- | --- | --- |
| T01 | 未登录直访管理页；错误密码、正确密码登录；确认进入后台；普通用户Token调用Admin API；Admin Token调用用户业务API | 未登录正确处理；错误拒绝、正确成功；双向权限隔离 | PENDING |
| T02 | 新建测试指标填写code/name/category；保存；修改name/category；尝试修改code | 创建/编辑成功；code只读且API拒绝，反馈清晰 | PENDING |
| T03 | 无pending引用指标停用/恢复；准备PENDING_CONFIRMATION引用某ACTIVE指标；Admin尝试停用 | 普通操作成功；pending阻止停用，工作区继续可处理 | PENDING |
| T04 | 新增不同类型Alias；编辑；停用/恢复；尝试normalized重复和与其它指标code/name冲突 | 正常维护成功；重复/冲突拒绝，恢复重新检查；目标只读 | PENDING |
| T05 | 创建清晰测试Alias；微信确认页进入标准指标选择；用Alias搜索并选择 | 返回并保存canonical StandardMetric | PENDING |
| T06 | 准备FINAL_REVIEW且尚未初始化workspace；Admin新增能exact命中raw_metric的Alias；微信首次打开确认页 | 可以预关联，但仍待确认；必须人工处理后才能commit | PENDING |
| T07 | 首次打开未匹配报告形成Confirmation；退出；Admin新增命中Alias；再次进入 | 原项目状态/身份不自动变；仍可手工选择新指标 | PENDING |
| T08 | 既有已commit且standard_metric_id=NULL项目；Admin新增命中Alias；查看正式报告/我的指标 | 正式数据不重关联，不自动进入聚合 | PENDING |
| T09 | 有正式历史的指标记录原报告名称；Admin rename；查看Stage06和旧正式详情 | Stage06当前canonical名更新、ID/历史不分裂；报告主名仍原LabResult.metric_name | PENDING |
| T10 | 无pending引用但有历史/trend的指标停用；查看我的指标/latest/history/trend/favorite | 既有数据和收藏继续可见；仅未来选择/预关联受影响 | PENDING |
| T11 | OCR指标问题查看未匹配名称；选可确认条目；创建Alias；返回刷新 | 有轻量次数/时间；创建成功后退出pending列表；机器快照不修改 | PENDING |
| T12 | 找到OCR code已识别但产品缺失的条目；创建标准指标，检查code/name预填并确认；返回 | 单项补充成功；不导入全库，不重算旧OCR/Confirmation | PENDING |
| T13 | 打开Task页；按status与pipeline version筛选；查看摘要 | 工程字段/数量可读，无重跑/改状态/强制成功/改结果功能 | PENDING |

## 8. 验收项归属与下一步

| 验收组 | 当前证据 / 状态 |
| --- | --- |
| SM / SD / MA / AN / NS / MB / SS / ER / RV / ET / HD | 工程实现与自动测试已通过；相关真实操作仍由T02～T08验收 |
| RN / IA / Stage04～06回归 | 自动与PG历史兼容通过；真实微信T05～T10待验 |
| OI / PM / PI / IS / OT / AU / AA | API、合成与PG工程验证通过；真实Admin T01/T11～T13待验 |
| AW001～AW024 | 页面已实现，typecheck/build通过；浏览器点击与真实使用PENDING，不标人工PASS |
| AW025 / 不做事项 | 未做全站视觉重构；无超范围功能 |
| MG / PG / OF / SAFE / AT / DOC | 必要工程项通过，保留Stage03既有drift，RESULT已更新；SAFE对应人工确认仍待T01～T13 |

下一步由负责人完成上述真实人工验收并反馈。出现FAIL按Stage07边界修复、复验并记录；只有T01～T13及全部适用P0/SAFE满足后，才能单独执行最终PASS文档收尾。当前不进入Stage08、OCR算法优化、历史数据修复或全项目UI打磨。
