# Stage 05｜正式报告管理：实施结果

日期：2026-09-30。

**工程实现与自动验证已通过；当前 Stage 05 = FAIL（待负责人真实微信人工验收，不是最终 PASS）。** 冻结 ACCEPTANCE 的 V01～V06 尚无负责人实机反馈，不能由单测、API、代码核对或构建替代。Stage 04 原 PASS 事实保持，本轮新增工程回归全部通过。

## 1. 实际完成内容

完成正式报告列表、只读详情、私有多页原图、整份报告档案迁移、疑似重复迁移确认、完整数据库硬删除、COS ingestion prefix 即时清理和持久重试消费者。首页 draft 仅取未完成状态，识别任务页默认排除 CONFIRMED，Stage 04 commit 成功后使用返回的 report_id 进入正式详情。

正式内容只读取 LabReport / LabResult；原图通过 source_ingestion_id 追溯。未增加正式编辑接口、软删除、趋势/历史/关注/指标管理后台，未修改 OCR Pipeline 或 AUTO/REVIEW 判定。

## 2. 实际修改文件

初次 Stage 05 实施共 23 个实现/测试/运行说明/RESULT 文件：

- 后端新增：`backend/app/reports.py`、`backend/app/api/v1/reports.py`、`backend/app/cleanup_worker.py`。
- 后端修改：`backend/app/models/entities.py`、`backend/app/main.py`、`backend/app/core/cos.py`。
- Migration：`backend/migrations/versions/0005_report_management.py`。
- 测试：新增 `backend/tests/test_stage05.py`、`backend/tests/verify_postgres_reports.py`；调整 `backend/tests/verify_postgres_confirmation.py` 为明确升级至 0004（原有断言完整保留）。
- 小程序新增：`miniapp/src/reports.ts`、`miniapp/src/pages/reports/index.vue`、`miniapp/src/pages/report-detail/index.vue`、`miniapp/src/pages/report-assets/index.vue`、`miniapp/tests/reports.test.mjs`。
- 小程序修改：`miniapp/src/pages.json`、`miniapp/src/pages/index/index.vue`、`miniapp/src/pages/ingestion-tasks/index.vue`、`miniapp/src/pages/confirmation/index.vue`。
- 文档：`README.md`、`backend/README.md`、`deploy/README.md`、本 `RESULT.md`。

初次实施时用户的 Stage 05 PLAN / ACCEPTANCE 和 AGENTS.md 改动均保持未覆盖，未修改 0001～0004 migration。

本次回归修复仅修改 7 个文件：`backend/app/cleanup_worker.py`、`backend/tests/test_stage05.py`、`backend/tests/verify_postgres_reports.py`、`miniapp/src/reports.ts`、`miniapp/src/pages/report-detail/index.vue`、`miniapp/tests/reports.test.mjs`、本 `RESULT.md`。未修改 PLAN / ACCEPTANCE、基线、README 或 migration。

## 3. Migration

`0005_report_management`，down_revision=`0004_confirmation_report`，当前唯一 head。

只新增 `FileCleanup.target_type`（非空、默认 OBJECT），CHECK 约束只允许 OBJECT/PREFIX；历史记录增量升级后回填 OBJECT。未增加 report/user/ingestion/retry_count/error_message 等额外字段，LabReport/LabResult 业务结构保持不变。

两座临时 PostgreSQL 17 库验证了 0004 → 0005 和空库 0001 → 0005，升级前已建立 Stage 04 合成正式报告，升级后可直接查询，无需重新 OCR/确认/commit。**本轮没有升级开发人员当前业务数据库**；实机验收前需按第 11 节对正常目标环境执行 migration。

## 4. 报告 API / 列表 / 详情 / 原图

统一 `/api/v1` 前缀：

| 方法 | 路径 | 实际行为 |
| --- | --- | --- |
| GET | `/reports?health_profile_id=&page=&page_size=` | 必须指定本人 ACTIVE 档案；仅正式报告；page>=1，默认20，最大100；items/total/page/page_size/has_more |
| GET | `/reports/{report_id}` | 统一 report_for 所有权及档案校验，返回基本信息、项目数、正式 results |
| GET | `/reports/{report_id}/assets` | source ingestion 原图 id/page_no/mime_type/file_size，无 object key |
| GET | `/reports/{report_id}/assets/{asset_id}/preview` | 双资源归属校验，复用 preview_url，300 秒私有 URL；稳定错误码 |
| POST | `/reports/{report_id}/migrate` | 目标 health_profile_id 和可选 duplicate_acknowledgement |
| DELETE | `/reports/{report_id}` | 数据库完整硬删除提交后返回204，COS即时失败不改变删除成功 |

报告排序为 examination_date DESC → examination_time DESC NULLS LAST → created_at DESC → id DESC。计数只读持久化 LabResult.abnormal，NULL/空/NORMAL 不计有异常标记。详情 sequence_no ASC，metric_name/result_text 为主展示，单位优先 unit_normalized，NULL/空串时回退 unit_original，两者均缺失则不展示；仅选择显示值，不换算、不修改正式值或 OCR 快照。标准名称辅助，未关联项完整保留；没有医学重推断，也不展示内部来源/处理枚举。

小程序三个真实 API 页面具备 loading/empty/error/retry；列表默认档案、onShow 重载、加载更多及请求版本防旧响应覆盖；原图按 page_no、多页、uni.previewImage 放大、单页签名/图片失败重试，短时 URL 只存在页面内。COS 失败不会阻断正式详情。

## 5. 报告迁移

report 行锁 → source ingestion 行锁 → 目标 ACTIVE profile 行锁，目标锁与 Stage 04 commit 一致；同事务更新 LabReport.health_profile_id、全部 LabResult.health_profile_id、ReportIngestion.health_profile_id。中途异常全量 rollback；相同档案为不写数据的 no-op。

重复只比较目标档案的其它正式报告，排除当前 report，保持 Stage 04 非空编号强规则、日期/医院/指标集合 Jaccard >= 0.8 组合规则。HMAC acknowledgement 绑定 report_id、目标档案、当前正式核心字段、指标身份集合和候选集合；换目标失效。取消不修改数据，明确继续不会覆盖旧报告。未读取 Confirmation 重建正式值。

小程序在详情页内选择全部本人其它 ACTIVE 档案、明确确认、展示重复候选摘要、取消/仍然迁移，成功刷新详情归属。没有建立独立迁移页。

OCR 报告迁移前后自动比对 ConfirmationItem/OcrResultItem/OcrTask/ReportAsset 的全部字段快照及正式结果，完全一致；原图 object key 不变。

## 6. 完整删除 / COS cleanup

统一 ownership，锁定 report/source ingestion；同事务先登记 FileCleanup(PREFIX,PENDING)，再按外键顺序硬删除：LabResult → LabReport → 全部 ConfirmationItem（包括 REMOVED）→ 全部 OcrResultItem / OcrTask runs → ReportAsset → UploadAuthorization → ReportIngestion。StandardMetric 等公共主数据不删。登记或中途删除失败，整个事务 rollback。

目标为 `users/{user_id}/ingestions/{ingestion_id}/`，覆盖 original、ocr、manifest、retry/evidence 及 ingestion 范围孤儿对象。数据库 commit 后立即尝试 COS：成功 DONE；失败 PENDING，但接口仍204，正式医疗数据不恢复。删除后详情/原图/原 ingestion 均不存在，不能继续签发新的 URL。重复 DELETE 为安全404，不生成第二份清理记录。

`python -m app.cleanup_worker` 为可执行独立消费者，与 API/OCR Worker 同 codebase。每10秒扫描 PENDING，处理记录持有 FOR UPDATE SKIP LOCKED 行锁；OBJECT 先检查是否仍有任意 ReportAsset 引用同一 cos_object_key：有引用时不调用 COS、不删除 Asset，保留 PENDING；解除引用后才删除单对象。PREFIX 用 Marker 分页列举并逐个删除，循环复核 prefix 为空后才 DONE。网络/数据库失败继续重试，不增加新中间件或配置字段。COS SDK普通 INFO日志已抑制，cleanup日志只记标识与稳定错误码，不记录医疗全文/SQL绑定值/object prefix。

COS 分页/失败/重试使用合成 SDK 替身（2105 个对象）验证；PostgreSQL cleanup 使用合成 COS 替身。**未对真实 COS 文件执行删除测试，也未把真实云存储清理或进程部署标为已验收。**

## 7. 实际自动验证结果

以下均在本轮实际执行，未删除/skip/弱化既有测试：

| cwd | 命令 | 最终结果 |
| --- | --- | --- |
| backend | `.venv/Scripts/python.exe -m pytest -q` | PASS，66 passed，0 skipped；原有52项完整保留，Stage05共14项（本次新增3项） |
| backend | `.venv/Scripts/ruff.exe check . --no-cache` | PASS，All checks passed |
| backend | `.venv/Scripts/alembic.exe heads` | `0005_report_management (head)` |
| backend | `.venv/Scripts/python.exe tests/verify_postgres_reports.py` | PASS，真实PostgreSQL17，两座临时库均删除并查询核实不存在 |
| backend | `.venv/Scripts/python.exe tests/verify_postgres_confirmation.py` | PASS，Stage04两座临时库最终删除 |
| backend | `.venv/Scripts/python.exe tests/verify_postgres_queue.py` | PASS，Stage03队列在0005 head下验证，临时库finally删除 |
| miniapp | `pnpm test` | PASS，21 tests，0 skipped；原有13项完整保留，本次新增单位展示回归1项 |
| miniapp | `pnpm typecheck` | PASS |
| miniapp | `pnpm build:mp-weixin` | PASS，微信产物在dist/build/mp-weixin |
| admin-web | `pnpm typecheck` | PASS |
| admin-web | `pnpm build` | PASS |

Stage05 PostgreSQL实际场景：历史 OBJECT回填；既有正式报告无需重建；部分迁移后真实DB错误 rollback；双独立session迁移vs迁移；迁移vs目标新commit的重复串行；cleanup登记失败和后段删除失败 rollback；迁移vs删除；并发重复DELETE仅一份PREFIX；正式域/确认/OCR/上传全链清空；PREFIX持久留存；COS失败不恢复数据；OBJECT/PREFIX消费者重试与重复处理；本次增加有 ReportAsset 引用时重复消费仍不调用 COS / 保留 PENDING，完整删除解除引用后 COS 失败保留 PENDING、重试成功 DONE、再次消费不重复删除。数据库名只由固定测试前缀和UUID生成，业务库不作为测试库。

本次新增后端回归通过实际 API 构造“原图删除失败 → 保留 Asset / OBJECT PENDING”，分别覆盖未 commit 和已 commit 正式报告；重复消费不触发 COS 删除，原图预览仍可用，显式重试删除可完成。无引用 OBJECT 的 COS 失败、成功重试和重复消费均通过。小程序回归覆盖 normalized 优先、NULL/空串回退、两者缺失和存储值不变。

## 8. Stage 04 回归

原有 test_stage04.py 未修改；commit幂等、REVIEW_PENDING阻断、KEEP_ORIGINAL_NAME、纯手工commit、重复保存不覆盖、机器快照不可变、原有私有preview均通过完整pytest。PostgreSQL原专项仍保留所有断言：并发初始化、真实异常rollback、并发commit/超时重试、三类来源唯一约束、正式日期和来源快照一致。

旧专项将 `head` 改为明确 `0004_confirmation_report`，使其既有“Stage04 head=0004”断言保持原意；新增专项负责0005和升级后的业务操作。没有弱化现有验收。Stage04历史负责人W01～W04 PASS未被当作本轮Stage05人工证据。

## 9. 设计偏差 / 已知问题

- 无产品/数据规则偏差，无新依赖，无OCR算法改动。独立PG脚本名为 verify_postgres_reports.py，与PLAN建议文件名等价。
- 真实微信V01～V06未执行；页面编译与逻辑测试不等于实机效果验证。
- 目标业务库未升级、cleanup进程未替负责人部署；需验收前按第11节启动。消费者未运行时不能宣称失败文件已最终清除。
- COS失败后允许短时文件留存，PENDING重试成功才最终清理；这是冻结的一致性策略。已发出的300秒私有URL不能由产品API主动撤销，删除后不再签发新的URL。
- 保留既有非阻塞警告：FastAPI/Starlette TestClient弃用提示、Node模块类型提示、Admin产物较大提示。未为消除警告扩大依赖/重构范围。
- 本次已修复：Stage02原图删除失败后遗留的 OBJECT/PENDING 曾可能误删仍被 ReportAsset 引用的原图；现以全局引用检查保护，未 commit / 已 commit 场景及 PostgreSQL 17 回归通过。有引用时保持 PENDING 属于保护行为，不能据此宣称文件已删除。
- 本次已修复：正式详情此前优先显示 unit_original；现优先 unit_normalized，缺失时回退原单位，六组展示回归通过。
- 本次整仓 `git diff --check` 通过。

## 10. Git / Stage 06 边界

本次修复开始时 main 工作区干净；结束时仅第2节列出的7个文件为未提交修改。未commit、未push、未切换分支。本轮不实现我的指标、历史、趋势、关注、单位趋势分组、StandardMetric/MetricAlias/OCR后台。

下一阶段只在Stage05负责人实机验收收口后另行授权；Stage06应直接查询LabResult，未关联标准指标不得纳入标准聚合，迁移/删除已自然更新其数据基础。

## 11. 负责人真实微信人工验收待办

准备：在backend对正常目标数据库执行 `.venv/Scripts/alembic.exe upgrade head`，重启API，持续启动 `.venv/Scripts/python.exe -m app.cleanup_worker`；将本轮miniapp/dist/build/mp-weixin导入真实微信开发者工具，检查既有HTTPS/COS合法域名及私有权限配置。使用测试档案/报告，不以真实隐私数据做破坏性验收。

- V01：首页→检验报告；已commit显示、未commit不显示；日期/医院/数量/异常标记；切换档案隔离。
- V02：数值/非数值、单位/参考范围/abnormal、标准/未关联项、顺序；无正式编辑入口。
- V03：多页原图、页序、放大、返回、再次进入。
- V04：两个本人管理测试档案间整份迁移，源消失/目标出现/正式值不变/原图可看。
- V05：目标疑似重复→取消不迁移；再次明确仍然迁移且不覆盖旧报告。
- V06：危险二次确认，完整说明结果/原图/识别数据不可恢复；删除后列表/详情/原图/任务记录不可再访问，其它报告不受影响。

上述六项全部待负责人反馈。COS故障无需负责人在生产环境人为制造，已由自动/临时数据库验证承担。

## 12. 当前 Stage 05 判定与逐项验收证据

工程实现和自动验证通过；V01～V06待真实微信人工验收。按冻结Z条件，当前 **FAIL（待人工验收）**，不得标PASS。以下“工程”仅表示自动测试、真实临时PostgreSQL或明确的源码/构建核对，不表示负责人实机执行；前端交互仍须V节最终验收。

| 编号 | 验收项 | 本轮结果 | 证据 / 验证边界 |
| --- | --- | --- | --- |
| A01 | Stage 04 已正式 PASS | PASS（工程/文档） | Stage04 RESULT现行PASS；Stage05正式域查询/升级既有报告验证 |
| A02 | Stage 04 已有正式报告无需重新 commit | PASS（工程/文档） | Stage04 RESULT现行PASS；Stage05正式域查询/升级既有报告验证 |
| A03 | 正式域与 OCR/确认域继续分离 | PASS（工程/文档） | Stage04 RESULT现行PASS；Stage05正式域查询/升级既有报告验证 |
| B01 | 新增 migration 不重写历史 migration | PASS（工程/文档） | 0005 migration、ORM结构核对、PG默认值/空库增量升级 |
| B02 | FileCleanup 支持 OBJECT / PREFIX | PASS（工程/文档） | 0005 migration、ORM结构核对、PG默认值/空库增量升级 |
| B03 | 历史 FileCleanup 默认保持 OBJECT | PASS（工程/文档） | 0005 migration、ORM结构核对、PG默认值/空库增量升级 |
| B04 | 不为正式报告增加软删除字段 | PASS（工程/文档） | 0005 migration、ORM结构核对、PG默认值/空库增量升级 |
| B05 | 不为 Stage 06 提前新增趋势数据表 | PASS（工程/文档） | 0005 migration、ORM结构核对、PG默认值/空库增量升级 |
| C01 | 列表必须指定 HealthProfile | PASS（工程/文档） | test_stage05 正式列表/多档案/分页/时间及稳定排序/计数 |
| C02 | HealthProfile 必须属于当前 User | PASS（工程/文档） | test_stage05 正式列表/多档案/分页/时间及稳定排序/计数 |
| C03 | 只返回正式 LabReport | PASS（工程/文档） | test_stage05 正式列表/多档案/分页/时间及稳定排序/计数 |
| C04 | 不同 HealthProfile 不混合 | PASS（工程/文档） | test_stage05 正式列表/多档案/分页/时间及稳定排序/计数 |
| C05 | 默认使用检验日期排序 | PASS（工程/文档） | test_stage05 正式列表/多档案/分页/时间及稳定排序/计数 |
| C06 | 同日时间排序正确 | PASS（工程/文档） | test_stage05 正式列表/多档案/分页/时间及稳定排序/计数 |
| C07 | 稳定排序 | PASS（工程/文档） | test_stage05 正式列表/多档案/分页/时间及稳定排序/计数 |
| C08 | 服务端分页 | PASS（工程/文档） | test_stage05 正式列表/多档案/分页/时间及稳定排序/计数 |
| C09 | page\_size 有上限 | PASS（工程/文档） | test_stage05 正式列表/多档案/分页/时间及稳定排序/计数 |
| C10 | 列表项目数量正确 | PASS（工程/文档） | test_stage05 正式列表/多档案/分页/时间及稳定排序/计数 |
| C11 | 异常标记数量只读正式 abnormal | PASS（工程/文档） | test_stage05 正式列表/多档案/分页/时间及稳定排序/计数 |
| D01 | 只能查看当前用户正式报告 | PASS（工程/文档） | test_stage05 正式详情/数值文本/标准身份；详情源码与无编辑API核对 |
| D02 | 报告基本信息完整 | PASS（工程/文档） | test_stage05 正式详情/数值文本/标准身份；详情源码与无编辑API核对 |
| D03 | 正式结果按 sequence\_no | PASS（工程/文档） | test_stage05 正式详情/数值文本/标准身份；详情源码与无编辑API核对 |
| D04 | metric\_name 为主名称 | PASS（工程/文档） | test_stage05 正式详情/数值文本/标准身份；详情源码与无编辑API核对 |
| D05 | StandardMetric 可辅助展示 | PASS（工程/文档） | test_stage05 正式详情/数值文本/标准身份；详情源码与无编辑API核对 |
| D06 | standard\_metric\_id = NULL 可正常展示 | PASS（工程/文档） | test_stage05 正式详情/数值文本/标准身份；详情源码与无编辑API核对 |
| D07 | KEEP\_ORIGINAL\_NAME 不暴露工程枚举 | PASS（工程/文档） | test_stage05 正式详情/数值文本/标准身份；详情源码与无编辑API核对 |
| D08 | 非数值结果正常展示 | PASS（工程/文档） | test_stage05 正式详情/数值文本/标准身份；详情源码与无编辑API核对 |
| D09 | result\_text 为用户主展示值 | PASS（工程/文档） | test_stage05 正式详情/数值文本/标准身份；详情源码与无编辑API核对 |
| D10 | abnormal = NULL 不显示“正常” | PASS（工程/文档） | test_stage05 正式详情/数值文本/标准身份；详情源码与无编辑API核对 |
| D11 | Stage 05 不重新计算 abnormal | PASS（工程/文档） | test_stage05 正式详情/数值文本/标准身份；详情源码与无编辑API核对 |
| D12 | 普通详情不强制展示 data\_source | PASS（工程/文档） | test_stage05 正式详情/数值文本/标准身份；详情源码与无编辑API核对 |
| D13 | 正式结果不可编辑 | PASS（工程/文档） | test_stage05 正式详情/数值文本/标准身份；详情源码与无编辑API核对 |
| E01 | 正式报告可找到 source ingestion | PASS（工程/文档） | test_stage05 多页资产/交叉归属/300秒preview/文件失败与独立详情 |
| E02 | 正式报告资产只属于 source ingestion | PASS（工程/文档） | test_stage05 多页资产/交叉归属/300秒preview/文件失败与独立详情 |
| E03 | 多页顺序正确 | PASS（工程/文档） | test_stage05 多页资产/交叉归属/300秒preview/文件失败与独立详情 |
| E04 | 原图列表不返回 cos\_object\_key | PASS（工程/文档） | test_stage05 多页资产/交叉归属/300秒preview/文件失败与独立详情 |
| E05 | 预览使用短时 URL | PASS（工程/文档） | test_stage05 多页资产/交叉归属/300秒preview/文件失败与独立详情 |
| E06 | 跨用户原图列表被拒绝 | PASS（工程/文档） | test_stage05 多页资产/交叉归属/300秒preview/文件失败与独立详情 |
| E07 | 跨用户 preview 被拒绝 | PASS（工程/文档） | test_stage05 多页资产/交叉归属/300秒preview/文件失败与独立详情 |
| E08 | 单页预览失败不破坏正式报告详情 | PASS（工程/文档） | test_stage05 多页资产/交叉归属/300秒preview/文件失败与独立详情 |
| F01 | 迁移必须整份执行 | PASS（工程/文档） | test_stage05 迁移三处一致/no-op/全OCR来源快照；PG迁移回滚 |
| F02 | 只能迁移到当前用户 ACTIVE HealthProfile | PASS（工程/文档） | test_stage05 迁移三处一致/no-op/全OCR来源快照；PG迁移回滚 |
| F03 | 跨用户目标档案禁止 | PASS（工程/文档） | test_stage05 迁移三处一致/no-op/全OCR来源快照；PG迁移回滚 |
| F04 | LabReport profile 更新 | PASS（工程/文档） | test_stage05 迁移三处一致/no-op/全OCR来源快照；PG迁移回滚 |
| F05 | 全部 LabResult profile 更新 | PASS（工程/文档） | test_stage05 迁移三处一致/no-op/全OCR来源快照；PG迁移回滚 |
| F06 | ReportIngestion profile 更新 | PASS（工程/文档） | test_stage05 迁移三处一致/no-op/全OCR来源快照；PG迁移回滚 |
| F07 | 三处 profile 始终一致 | PASS（工程/文档） | test_stage05 迁移三处一致/no-op/全OCR来源快照；PG迁移回滚 |
| F08 | 正式值不因迁移改变 | PASS（工程/文档） | test_stage05 迁移三处一致/no-op/全OCR来源快照；PG迁移回滚 |
| F09 | 来源链不被重建 | PASS（工程/文档） | test_stage05 迁移三处一致/no-op/全OCR来源快照；PG迁移回滚 |
| F10 | 同档案迁移安全 no-op | PASS（工程/文档） | test_stage05 迁移三处一致/no-op/全OCR来源快照；PG迁移回滚 |
| G01 | 目标档案重新进行重复检测 | PASS（工程/文档） | test_stage05 编号/组合重复参数化、取消/换目标凭证失效/明确继续 |
| G02 | 重复检测只比较目标档案 | PASS（工程/文档） | test_stage05 编号/组合重复参数化、取消/换目标凭证失效/明确继续 |
| G03 | 当前 report 从 duplicate candidates 排除 | PASS（工程/文档） | test_stage05 编号/组合重复参数化、取消/换目标凭证失效/明确继续 |
| G04 | 强报告编号规则继续有效 | PASS（工程/文档） | test_stage05 编号/组合重复参数化、取消/换目标凭证失效/明确继续 |
| G05 | 日期 + 医院 + 指标集合规则继续有效 | PASS（工程/文档） | test_stage05 编号/组合重复参数化、取消/换目标凭证失效/明确继续 |
| G06 | 疑似重复只提示不禁止 | PASS（工程/文档） | test_stage05 编号/组合重复参数化、取消/换目标凭证失效/明确继续 |
| G07 | 取消重复迁移不修改任何数据 | PASS（工程/文档） | test_stage05 编号/组合重复参数化、取消/换目标凭证失效/明确继续 |
| G08 | 旧 acknowledgement 对新目标失效 | PASS（工程/文档） | test_stage05 编号/组合重复参数化、取消/换目标凭证失效/明确继续 |
| H01 | 迁移单事务 | PASS（工程/文档） | verify_postgres_reports 双session迁移、目标commit、删除并发及真实DB异常 |
| H02 | 迁移中途数据库异常完整回滚 | PASS（工程/文档） | verify_postgres_reports 双session迁移、目标commit、删除并发及真实DB异常 |
| H03 | 并发迁移同一报告安全 | PASS（工程/文档） | verify_postgres_reports 双session迁移、目标commit、删除并发及真实DB异常 |
| H04 | 迁移与删除并发安全 | PASS（工程/文档） | verify_postgres_reports 双session迁移、目标commit、删除并发及真实DB异常 |
| H05 | 迁移与目标档案 commit 的重复检测可串行 | PASS（工程/文档） | verify_postgres_reports 双session迁移、目标commit、删除并发及真实DB异常 |
| I01 | 删除必须先验证 ownership | PASS（工程/文档） | test_stage05 与PG完整硬删除/REMOVED/全部runs/授权链；公共主数据源码核对 |
| I02 | 删除 LabResult | PASS（工程/文档） | test_stage05 与PG完整硬删除/REMOVED/全部runs/授权链；公共主数据源码核对 |
| I03 | 删除 LabReport | PASS（工程/文档） | test_stage05 与PG完整硬删除/REMOVED/全部runs/授权链；公共主数据源码核对 |
| I04 | 删除 ConfirmationItem | PASS（工程/文档） | test_stage05 与PG完整硬删除/REMOVED/全部runs/授权链；公共主数据源码核对 |
| I05 | 删除全部 OcrResultItem | PASS（工程/文档） | test_stage05 与PG完整硬删除/REMOVED/全部runs/授权链；公共主数据源码核对 |
| I06 | 删除全部 OcrTask | PASS（工程/文档） | test_stage05 与PG完整硬删除/REMOVED/全部runs/授权链；公共主数据源码核对 |
| I07 | 删除 ReportAsset 数据库记录 | PASS（工程/文档） | test_stage05 与PG完整硬删除/REMOVED/全部runs/授权链；公共主数据源码核对 |
| I08 | 删除 UploadAuthorization | PASS（工程/文档） | test_stage05 与PG完整硬删除/REMOVED/全部runs/授权链；公共主数据源码核对 |
| I09 | 删除 ReportIngestion | PASS（工程/文档） | test_stage05 与PG完整硬删除/REMOVED/全部runs/授权链；公共主数据源码核对 |
| I10 | StandardMetric 不受影响 | PASS（工程/文档） | test_stage05 与PG完整硬删除/REMOVED/全部runs/授权链；公共主数据源码核对 |
| I11 | 删除采用单数据库事务 | PASS（工程/文档） | test_stage05 与PG完整硬删除/REMOVED/全部runs/授权链；公共主数据源码核对 |
| J01 | 删除事务中创建 PREFIX cleanup | PASS（工程/文档） | test_stage05 cleanup成功/失败204/重试/2105对象分页；PG持久消费者 |
| J02 | 清理目标为完整 ingestion prefix | PASS（工程/文档） | test_stage05 cleanup成功/失败204/重试/2105对象分页；PG持久消费者 |
| J03 | FileCleanup 创建失败则 DB 删除 rollback | PASS（工程/文档） | test_stage05 cleanup成功/失败204/重试/2105对象分页；PG持久消费者 |
| J04 | DB commit 后即时尝试 COS cleanup | PASS（工程/文档） | test_stage05 cleanup成功/失败204/重试/2105对象分页；PG持久消费者 |
| J05 | COS 即时失败不恢复正式报告 | PASS（工程/文档） | test_stage05 cleanup成功/失败204/重试/2105对象分页；PG持久消费者 |
| J06 | COS 即时失败仍返回正式删除成功 | PASS（工程/文档） | test_stage05 cleanup成功/失败204/重试/2105对象分页；PG持久消费者 |
| J07 | COS 失败保持 PENDING | PASS（工程/文档） | test_stage05 cleanup成功/失败204/重试/2105对象分页；PG持久消费者 |
| J08 | PREFIX cleanup 可分页处理 | PASS（工程/文档） | test_stage05 cleanup成功/失败204/重试/2105对象分页；PG持久消费者 |
| J09 | 对象已经不存在视为成功 | PASS（工程/文档） | test_stage05 cleanup成功/失败204/重试/2105对象分页；PG持久消费者 |
| J10 | 重复执行 PREFIX cleanup 安全 | PASS（工程/文档） | test_stage05 cleanup成功/失败204/重试/2105对象分页；PG持久消费者 |
| J11 | PENDING cleanup 有真实消费者 | PASS（工程/文档） | test_stage05 cleanup成功/失败204/重试/2105对象分页；PG持久消费者 |
| J12 | 历史 OBJECT cleanup 仍可处理 | PASS（工程/文档） | test_stage05 cleanup成功/失败204/重试/2105对象分页；PG持久消费者 |
| K01 | 删除后报告列表立即消失 | PASS（工程/文档） | test_stage05 删除后详情/原图/任务拒绝及正式行清除；列表来源源码核对 |
| K02 | 删除后详情不可读取 | PASS（工程/文档） | test_stage05 删除后详情/原图/任务拒绝及正式行清除；列表来源源码核对 |
| K03 | 删除后原图 API 不再签发新 URL | PASS（工程/文档） | test_stage05 删除后详情/原图/任务拒绝及正式行清除；列表来源源码核对 |
| K04 | 删除后识别任务记录不重新出现 | PASS（工程/文档） | test_stage05 删除后详情/原图/任务拒绝及正式行清除；列表来源源码核对 |
| K05 | 删除后 Stage 06 数据基础自然消失 | PASS（工程/文档） | test_stage05 删除后详情/原图/任务拒绝及正式行清除；列表来源源码核对 |
| L01 | 跨用户报告列表隔离 | PASS（工程/文档） | 跨用户六类接口测试；既有日志回归+cleanup敏感异常捕获验证 |
| L02 | 跨用户详情隔离 | PASS（工程/文档） | 跨用户六类接口测试；既有日志回归+cleanup敏感异常捕获验证 |
| L03 | 跨用户 asset 列表隔离 | PASS（工程/文档） | 跨用户六类接口测试；既有日志回归+cleanup敏感异常捕获验证 |
| L04 | 跨用户 preview 隔离 | PASS（工程/文档） | 跨用户六类接口测试；既有日志回归+cleanup敏感异常捕获验证 |
| L05 | 跨用户迁移隔离 | PASS（工程/文档） | 跨用户六类接口测试；既有日志回归+cleanup敏感异常捕获验证 |
| L06 | 跨用户删除不影响数据 | PASS（工程/文档） | 跨用户六类接口测试；既有日志回归+cleanup敏感异常捕获验证 |
| L07 | 普通 API 不返回永久 COS URL | PASS（工程/文档） | 跨用户六类接口测试；既有日志回归+cleanup敏感异常捕获验证 |
| L08 | 普通 API 不暴露 COS Secret | PASS（工程/文档） | 跨用户六类接口测试；既有日志回归+cleanup敏感异常捕获验证 |
| L09 | 日志不包含完整检验结果 | PASS（工程/文档） | 跨用户六类接口测试；既有日志回归+cleanup敏感异常捕获验证 |
| L10 | Cleanup 日志不输出医疗全文 | PASS（工程/文档） | 跨用户六类接口测试；既有日志回归+cleanup敏感异常捕获验证 |
| M01 | 首页存在正式报告入口 | 工程核对通过（非实机） | reports页面onShow/状态/当前档案/版本防覆盖源码核对+路由分页逻辑测试+构建 |
| M02 | 列表使用当前默认 HealthProfile | 工程核对通过（非实机） | reports页面onShow/状态/当前档案/版本防覆盖源码核对+路由分页逻辑测试+构建 |
| M03 | 切换 HealthProfile 后报告列表切换 | 工程核对通过（非实机） | reports页面onShow/状态/当前档案/版本防覆盖源码核对+路由分页逻辑测试+构建 |
| M04 | 列表支持 loading | 工程核对通过（非实机） | reports页面onShow/状态/当前档案/版本防覆盖源码核对+路由分页逻辑测试+构建 |
| M05 | 列表支持 empty | 工程核对通过（非实机） | reports页面onShow/状态/当前档案/版本防覆盖源码核对+路由分页逻辑测试+构建 |
| M06 | 列表支持 error/retry | 工程核对通过（非实机） | reports页面onShow/状态/当前档案/版本防覆盖源码核对+路由分页逻辑测试+构建 |
| M07 | 列表支持加载更多 | 工程核对通过（非实机） | reports页面onShow/状态/当前档案/版本防覆盖源码核对+路由分页逻辑测试+构建 |
| M08 | 点击报告进入正式详情 | 工程核对通过（非实机） | reports页面onShow/状态/当前档案/版本防覆盖源码核对+路由分页逻辑测试+构建 |
| N01 | 基本信息正确 | 工程核对通过（非实机） | 详情/原图源码核对、正式API与页序测试+类型检查/构建；非实机 |
| N02 | 正式结果列表正确 | 工程核对通过（非实机） | 详情/原图源码核对、正式API与页序测试+类型检查/构建；非实机 |
| N03 | 非数值结果正确 | 工程核对通过（非实机） | 详情/原图源码核对、正式API与页序测试+类型检查/构建；非实机 |
| N04 | 未关联 StandardMetric 项可查看 | 工程核对通过（非实机） | 详情/原图源码核对、正式API与页序测试+类型检查/构建；非实机 |
| N05 | 原始报告入口可达 | 工程核对通过（非实机） | 详情/原图源码核对、正式API与页序测试+类型检查/构建；非实机 |
| N06 | 多页原图顺序正确 | 工程核对通过（非实机） | 详情/原图源码核对、正式API与页序测试+类型检查/构建；非实机 |
| N07 | 原图可放大查看 | 工程核对通过（非实机） | 详情/原图源码核对、正式API与页序测试+类型检查/构建；非实机 |
| N08 | 原图加载失败有错误提示和重试 | 工程核对通过（非实机） | 详情/原图源码核对、正式API与页序测试+类型检查/构建；非实机 |
| O01 | 迁移只展示当前用户其它档案 | 工程核对通过（非实机） | 详情选择/确认/删除源码核对；duplicate取消继续和删除跳转逻辑测试；非实机 |
| O02 | 迁移前有明确确认 | 工程核对通过（非实机） | 详情选择/确认/删除源码核对；duplicate取消继续和删除跳转逻辑测试；非实机 |
| O03 | duplicate 迁移有二次提示 | 工程核对通过（非实机） | 详情选择/确认/删除源码核对；duplicate取消继续和删除跳转逻辑测试；非实机 |
| O04 | 用户可取消 duplicate 迁移 | 工程核对通过（非实机） | 详情选择/确认/删除源码核对；duplicate取消继续和删除跳转逻辑测试；非实机 |
| O05 | 用户可明确继续 duplicate 迁移 | 工程核对通过（非实机） | 详情选择/确认/删除源码核对；duplicate取消继续和删除跳转逻辑测试；非实机 |
| O06 | 迁移成功后详情归属刷新 | 工程核对通过（非实机） | 详情选择/确认/删除源码核对；duplicate取消继续和删除跳转逻辑测试；非实机 |
| O07 | 删除必须二次确认 | 工程核对通过（非实机） | 详情选择/确认/删除源码核对；duplicate取消继续和删除跳转逻辑测试；非实机 |
| O08 | 删除成功返回列表并刷新 | 工程核对通过（非实机） | 详情选择/确认/删除源码核对；duplicate取消继续和删除跳转逻辑测试；非实机 |
| P01 | 首页不把 CONFIRMED 当当前 draft | 工程核对通过（非实机） | unfinished六状态测试、首页任务过滤、成功report_id路由源码核对 |
| P02 | 当前 ingestion 只取未完成状态 | 工程核对通过（非实机） | unfinished六状态测试、首页任务过滤、成功report_id路由源码核对 |
| P03 | 识别任务记录与正式报告分离 | 工程核对通过（非实机） | unfinished六状态测试、首页任务过滤、成功report_id路由源码核对 |
| P04 | Stage 04 commit 后可查看正式报告 | 工程核对通过（非实机） | unfinished六状态测试、首页任务过滤、成功report_id路由源码核对 |
| Q01 | Stage 04 commit 幂等仍通过 | PASS（工程/文档） | 原Stage00～04全量pytest；Stage04 PG专项；未改既有业务测试 |
| Q02 | REVIEW\_PENDING 阻断仍通过 | PASS（工程/文档） | 原Stage00～04全量pytest；Stage04 PG专项；未改既有业务测试 |
| Q03 | KEEP\_ORIGINAL\_NAME 仍通过 | PASS（工程/文档） | 原Stage00～04全量pytest；Stage04 PG专项；未改既有业务测试 |
| Q04 | 纯手工报告仍可 commit | PASS（工程/文档） | 原Stage00～04全量pytest；Stage04 PG专项；未改既有业务测试 |
| Q05 | 疑似重复保存仍通过 | PASS（工程/文档） | 原Stage00～04全量pytest；Stage04 PG专项；未改既有业务测试 |
| Q06 | OcrResultItem 不可变仍通过 | PASS（工程/文档） | 原Stage00～04全量pytest；Stage04 PG专项；未改既有业务测试 |
| Q07 | 原有私有 COS preview 未被破坏 | PASS（工程/文档） | 原Stage00～04全量pytest；Stage04 PG专项；未改既有业务测试 |
| R01 | Backend Tests | PASS（工程/文档） | 第7节实际完整pytest/Ruff结果 |
| R02 | Backend Ruff | PASS（工程/文档） | 第7节实际完整pytest/Ruff结果 |
| S01 | 0004 → 0005 migration | PASS（工程/文档） | verify_postgres_reports实际PostgreSQL17临时库验证及finally删除/查询核实 |
| S02 | 空库完整 migration | PASS（工程/文档） | verify_postgres_reports实际PostgreSQL17临时库验证及finally删除/查询核实 |
| S03 | Stage 04 既有正式报告升级后可直接查询 | PASS（工程/文档） | verify_postgres_reports实际PostgreSQL17临时库验证及finally删除/查询核实 |
| S04 | 迁移事务 rollback | PASS（工程/文档） | verify_postgres_reports实际PostgreSQL17临时库验证及finally删除/查询核实 |
| S05 | 迁移并发一致性 | PASS（工程/文档） | verify_postgres_reports实际PostgreSQL17临时库验证及finally删除/查询核实 |
| S06 | 迁移 vs 删除并发 | PASS（工程/文档） | verify_postgres_reports实际PostgreSQL17临时库验证及finally删除/查询核实 |
| S07 | 删除事务 rollback | PASS（工程/文档） | verify_postgres_reports实际PostgreSQL17临时库验证及finally删除/查询核实 |
| S08 | 删除完整链路核对 | PASS（工程/文档） | verify_postgres_reports实际PostgreSQL17临时库验证及finally删除/查询核实 |
| S09 | FileCleanup PREFIX 保留 | PASS（工程/文档） | verify_postgres_reports实际PostgreSQL17临时库验证及finally删除/查询核实 |
| S10 | 临时测试数据库全部删除 | PASS（工程/文档） | verify_postgres_reports实际PostgreSQL17临时库验证及finally删除/查询核实 |
| T01 | Miniapp Tests | PASS（工程/文档） | 第7节miniapp实际test/typecheck/build命令结果 |
| T02 | Miniapp Typecheck | PASS（工程/文档） | 第7节miniapp实际test/typecheck/build命令结果 |
| T03 | Miniapp Build | PASS（工程/文档） | 第7节miniapp实际test/typecheck/build命令结果 |
| U01 | Admin Typecheck | PASS（工程/文档） | 第7节admin实际typecheck/build命令结果 |
| U02 | Admin Build | PASS（工程/文档） | 第7节admin实际typecheck/build命令结果 |
| V01 | 正式报告列表完整流程 | 待人工验收 | 必须负责人真实微信执行；本轮无反馈，不以工程证据替代 |
| V02 | 正式报告详情 | 待人工验收 | 必须负责人真实微信执行；本轮无反馈，不以工程证据替代 |
| V03 | 原始报告查看 | 待人工验收 | 必须负责人真实微信执行；本轮无反馈，不以工程证据替代 |
| V04 | 正式报告迁移 | 待人工验收 | 必须负责人真实微信执行；本轮无反馈，不以工程证据替代 |
| V05 | 疑似重复迁移 | 待人工验收 | 必须负责人真实微信执行；本轮无反馈，不以工程证据替代 |
| V06 | 正式报告删除 | 待人工验收 | 必须负责人真实微信执行；本轮无反馈，不以工程证据替代 |
| W01 | 未实现我的指标 | PASS（工程/文档） | Git文件范围与新增模型/API/页面核对，无Stage06/07或OCR算法变化 |
| W02 | 未实现指标历史 | PASS（工程/文档） | Git文件范围与新增模型/API/页面核对，无Stage06/07或OCR算法变化 |
| W03 | 未实现趋势折线图 | PASS（工程/文档） | Git文件范围与新增模型/API/页面核对，无Stage06/07或OCR算法变化 |
| W04 | 未实现关注指标 | PASS（工程/文档） | Git文件范围与新增模型/API/页面核对，无Stage06/07或OCR算法变化 |
| W05 | 未实现单位趋势分组 | PASS（工程/文档） | Git文件范围与新增模型/API/页面核对，无Stage06/07或OCR算法变化 |
| W06 | 未实现 StandardMetric 管理后台 | PASS（工程/文档） | Git文件范围与新增模型/API/页面核对，无Stage06/07或OCR算法变化 |
| W07 | 未实现 MetricAlias 管理 | PASS（工程/文档） | Git文件范围与新增模型/API/页面核对，无Stage06/07或OCR算法变化 |
| W08 | 未实现 OCR 管理后台业务 | PASS（工程/文档） | Git文件范围与新增模型/API/页面核对，无Stage06/07或OCR算法变化 |
| W09 | 未修改 OCR 算法规则 | PASS（工程/文档） | Git文件范围与新增模型/API/页面核对，无Stage06/07或OCR算法变化 |
| X01 | 必要基线与 README 保持一致 | PASS（工程/文档） | README/backend/deploy/本RESULT核对；保留待人工验收和非PASS状态 |
| X02 | Stage 05 RESULT.md 完整 | PASS（工程/文档） | README/backend/deploy/本RESULT核对；保留待人工验收和非PASS状态 |
| X03 | 人工验收未完成前不得标 PASS | PASS（工程/文档） | README/backend/deploy/本RESULT核对；保留待人工验收和非PASS状态 |
