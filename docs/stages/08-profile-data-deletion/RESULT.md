# Stage 08｜健康档案隐私删除与数据生命周期闭环

实施与最终收尾日期：2026-10-03。

**Stage 08 = PASS。** 代码实现、最终自动回归、PostgreSQL 17 专项及既有回归全部 PASS；项目负责人已反馈真实微信人工验收 T01～T06 全部 PASS。结合本次重新执行的收尾回归，冻结 ACCEPTANCE 的所有适用 P0 条件满足。

## 基线与范围

- 实施起点 main / origin/main 均为 `bdb0fffb3f7d29d4739477ed3c37004e070ded9d`；Stage 07 RESULT 已正式 PASS。本次收尾重新 fetch 并核对真实引用，当前 Git 证据见末节。
- 初次检查发现 PLAN / ACCEPTANCE 在未跟踪的 `08-production` 下；负责人要求重新执行后，实际目录已归位到 `08-profile-data-deletion`，旧 README 删除、新目录未跟踪为本轮开始前已有改动。
- 按 DEVELOPMENT_RULES 的 `stage/XX-name` 规范创建 `stage/08-profile-data-deletion`。初版实现已在 `fdd53c7` 提交并存在于远端阶段分支；本次只提交最终验收文档，不推送或合入 main。
- 唯一实施基线为本目录 PLAN / ACCEPTANCE；保持原文。只实现档案隐私删除，不进入 Stage 09、Stage 10 或部署发布。
- 按序读取 AGENTS、Product/Tech/Development baseline、Stage08 PLAN/ACCEPTANCE、Stage07 RESULT，再核对 Stage02～06 RESULT、DATA_MODEL/API_CONVENTIONS/SYSTEM_ARCHITECTURE、各工程README及指定真实代码。仓库无PROJECT_CONTEXT.md；不使用旧对话替代现状。

## 实际实现

- 新增 0008，前置 0007；只新增 nullable TIMESTAMPTZ `file_cleanups.not_before` 与 `(status, not_before, created_at)` 索引。
- 新增 deletion-impact 与整档案物理删除 service：同事务先登记每个 ingestion 的 PREFIX cleanup，再依 FK 顺序删除正式、确认、OCR、图片、授权、导入、Favorite 和档案。
- 默认档案按剩余 ACTIVE 的 `created_at ASC, id ASC` 替换，最后一个删除后为 NULL。
- 用户侧生命周期写入使用按 User ID 区分的 PostgreSQL transaction advisory lock，先于业务行锁；覆盖 ingestion、确认/commit、报告迁移/删除、Favorite、档案 CRUD/默认选择。不同用户不互相串行。
- 删除按 task → ingestion 取锁，匹配原 OCR Worker 顺序；看到 PROCESSING 返回 409 PROFILE_DELETE_BUSY，调用方整事务 rollback。不改 Worker、queue、算法或强制取消。
- 有未来有效授权时，包含 consumed 授权，取最晚 expires_at + 60 秒；无未来授权用 NULL，立即 due。上传记录额外取实际 STS expired_time 与本地15分钟的较晚值。
- cleanup 扫描与实际处理入口都检查 due time；OBJECT 引用保护、PREFIX 幂等/重试和 Stage 05 即时清理保持。
- 小程序在既有档案页请求影响摘要、显示不可恢复确认、处理 PROCESSING、刷新列表/default；丢失204时按服务器列表恢复，不自动重试危险删除。

主要变更文件：

| 范围 | 文件 |
| --- | --- |
| 新服务 | `backend/app/profile_deletion.py`、`profile_lifecycle.py` |
| API与锁接入 | `backend/app/api/v1/business.py`、`backend/app/reports.py`、`backend/app/profile_metrics.py` |
| 清理与模型 | `backend/app/cleanup_worker.py`、`backend/app/models/entities.py`（仅FileCleanup） |
| Migration | `backend/migrations/versions/0008_profile_data_deletion.py` |
| 新测试 | `backend/tests/test_stage08.py`、`verify_postgres_profile_deletion.py` |
| 旧测试兼容 | `backend/tests/test_stage02.py`、`verify_postgres_metrics.py`、`verify_postgres_stage07.py`，具体理由见差异节 |
| Miniapp | `miniapp/src/pages/profiles/index.vue`、`src/profile-deletion.ts`、`tests/profile-deletion.test.mjs` |
| 文档 | 根/backend/miniapp README、DATA_MODEL、API_CONVENTIONS、stages索引、本目录README和RESULT |

删除范围以锁内重新查询的当前归属为准：已迁出源档案的报告、正式结果、来源ingestion保留在目标档案；从其它档案迁入的完整链随当前档案删除。用户侧按User串行，避免跨profile迁移产生相反锁序。deletion-impact为实时预览而非删除凭证，DELETE始终重新检查ownership和PROCESSING。跨用户及不存在统一404，Admin Token拒绝；DB提交成功后COS失败仍204，重复删除404且不新增cleanup。

## 设计差异与处理

- PLAN 第8节建议通用 max(now, expiry)+60秒，但第26节及 ACCEPTANCE M01 要求无未来授权立即 due；以 ACCEPTANCE 为准，无未来授权使用 NULL。
- Stage 02 原测试要求软删除行 DELETED，与 Stage 08 明确物理删除直接冲突。仅替换这一旧契约断言为“行不存在”，并增加 default replacement 校验；未删除测试或跳过测试。
- Stage 06/07 PG schema 专项需区分历史 schema 与最新 ORM：保留历史断言，投影历史 metadata 后验证，再升级最新 head 执行业务回归。0001～0007 不修改。

## 分批验证与最终收尾回归

- Stage 04～06 后端：67 passed。
- Stage 08 + Stage 02 后端：17 passed。
- Miniapp：42 tests passed；typecheck PASS。
- Stage08独立PG专项初次通过后，修正测试脚本lint绑定与旧schema投影，最终完整重跑仍PASS。
- 首次 PG 合成夹具缺少 OCR manifest/summary，随后相似报告触发重复确认；修正夹具并按既有 acknowledgement 协议确认，不弱化产品校验。
- 首次新增测试误引不存在的Admin token helper，改为调用既有真实Admin登录fixture；Ruff指出import/测试闭包绑定及metadata投影缩进问题，修正后全量通过。没有删除或skip测试。

实施阶段全量验证使用 `runtime/stage08-full`，124项全部通过。最终环境为 Python3.12.10、PostgreSQL17.11。以下均在负责人2026-10-03全部人工验收反馈后重新执行，不以实施结束时或其它Stage的PASS替代本次收尾结果。业务实现与测试文件均未修改，未删除、skip或弱化任何测试。

| cwd | 命令 / 检查 | 真实结果 |
| --- | --- | --- |
| backend | `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp runtime/stage08-final` | PASS，124 passed，0 failed，0 skipped，72.55秒；既有113项+Stage08新增11项；1条既有TestClient弃用提示 |
| backend | `.venv/Scripts/ruff.exe check . --no-cache` | PASS，All checks passed |
| backend | `.venv/Scripts/alembic.exe heads` | 唯一 `0008_profile_data_deletion (head)` |
| backend | `.venv/Scripts/python.exe tests/verify_postgres_profile_deletion.py` | PASS，增量/空库两库、全链删除、五故障点、真实并发、late object/retry；两库finally删除并核验 |
| backend | `.venv/Scripts/python.exe tests/verify_postgres_queue.py` | PASS，Stage03 SKIP LOCKED、Worker锁、lease/renew/recovery、UNIQUE |
| backend | `.venv/Scripts/python.exe tests/verify_postgres_confirmation.py` | PASS，Stage04迁移、并发初始化/commit、回滚、来源UNIQUE、OCR不可变；两库删除 |
| backend | `.venv/Scripts/python.exe tests/verify_postgres_reports.py` | PASS，Stage05迁移、三处归属、迁移/删除并发、回滚、全链清理、OBJECT保护、PREFIX重试；两库删除 |
| backend | `.venv/Scripts/python.exe tests/verify_postgres_metrics.py` | PASS，Stage06历史schema、正式快照、排序/单位/趋势、Favorite并发和权限、迁移删除；两库删除 |
| backend | `.venv/Scripts/python.exe tests/verify_postgres_stage07.py` | PASS，Stage07历史schema、主数据/Alias/namespace、pending与commit/init并发、adapter、快照；两库删除 |
| miniapp | `pnpm test` | PASS，42 tests，0 failed，0 skipped；原32项+新增10项 |
| miniapp | `pnpm typecheck` | PASS |
| miniapp | `pnpm build:mp-weixin` | PASS，Build complete；`dist/build/mp-weixin` |
| admin-web | `pnpm test` | PASS，7 tests，0 failed，0 skipped |
| admin-web | `pnpm typecheck` | PASS |
| admin-web | `pnpm build` | PASS，Vite构建完成 |
| root | `git diff --check` | PASS |
| backend | 独立查询 `pg_database WHERE datname LIKE 'checkup_stage0%'` | 0残留（所有专项结束后再次查询） |

本次 Stage08 PostgreSQL 两座隔离库实际覆盖：

- `0007→0008`，历史OBJECT/PREFIX与PENDING/DONE四种组合所有字段保持，not_before均NULL；空库`0001→0008`；新字段时区、nullable及索引与ORM一致。
- 多ingestion合成档案含两份OCR/MANUAL正式报告、失败/成功多run、REMOVED/MANUAL确认、全部草稿状态、Favorite、Asset及各类Authorization。删除后逐表为0，另一档案所有存留私有字段快照和公共主数据不变，每个ingestion一个PREFIX。
- 在cleanup INSERT、LabResult DELETE、LabReport DELETE、OCR DELETE、HealthProfile DELETE注入真实PG除零异常，每次完整数据库快照与失败前完全一致，含default和cleanup。
- 每库验证commit、migrate源档案、migrate目标档案、实际upload authorization API、Favorite、实际new ingestion API、实际default API的双方获胜顺序；双session使用`pg_blocking_pids`确认真实等待后再放行，不是串行伪并发。遍历所有FK检查无orphan，default不悬空。
- 实际QUEUED claim：删除未提交时Worker SKIP LOCKED跳过；Worker已claim未提交时删除等待、随后看到PROCESSING并BUSY回滚；任务终态后再次删除成功。无queue/Worker修改。
- consumed且未过期授权参与最长窗口，max expires_at+60秒前不调用对应PREFIX清理；DB删除后加入合成late original及retry/evidence对象；到期首次COS失败仍PENDING，重试清空并DONE，重复消费无重复操作。
- 每次只删除脚本本轮生成的UUID测试库，finally执行并检查不存在；另用独立连接查询所有`checkup_stage0%`，无残留。不操作业务库或真实COS。

## 冻结边界与已知限制

- 本次重新核验：相对 Stage07 / origin/main 基线 `bdb0fffb3f7d29d4739477ed3c37004e070ded9d`，Stage08 HEAD 的 `backend/ocr_runtime/**`、`ocr_worker.py`、`ocr_queue.py`、`ocr_pipeline.py`、0001～0007及 `backend/migrations/data/standard_metrics_v1.json` 全部diff=0；这些路径的工作区diff也为0，冻结目录无新增未跟踪文件。
- Pipeline Version保持 `poc-sha256:9f0c4c4c61351c84894a37cc4f44d3f8dd77003b40bcbd67a1bf34bc825ab6e6`；matcher、threshold、fuzzy、unit scoring、retry/evidence、AUTO/REVIEW均未修改。
- 模型仅FileCleanup新增字段/索引；StandardMetric/MetricAlias/OcrResultItem/LabReport/LabResult既有语义和字段均不修改；隐私删除允许DELETE机器快照，不UPDATE快照。
- PG完整metadata比较仍恰为Stage03历史`ix_ocr_tasks_status` / `ix_ocr_tasks_queue`两项差异。本轮不修复，也不宣称全库alembic check无差异。
- Codex工程验证只操作隔离数据库与合成COS替身；本次收尾未迁移真实业务库、启动或重启验收进程、执行真实COS删除或部署。负责人实机验收单独归属，不以工程测试/构建替代。
- 保留既有非阻塞提示：TestClient弃用提示、Node模块类型提示、uni-app更新通知、Admin大包提示；不为本阶段升级依赖或拆包。

## ACCEPTANCE 证据归属

| 验收组 | 状态 / 证据 |
| --- | --- |
| A/B | 工程PASS：Git/基线/Stage07现状、独立0008、冻结diff与PG schema |
| C～J/P/Q | PASS：Stage08 API测试、全表快照、默认/最后档案、权限与PROCESSING；负责人对应真实操作见AN，T01～T06全部PASS |
| K～O/S～V/AA～AE | 工程PASS：Stage08真实PG双session、原子回滚、迁移、due/late/retry、临时库独立核验 |
| R/W/X/Y | PASS：API删除后旧路由拒绝、Miniapp实际接入和10项逻辑测试/typecheck/build；负责人真实微信T01～T06全部PASS |
| Z/AF～AJ/AL | 工程PASS：全量124项、Ruff、Stage03～07全部PG专项、Admin测试/构建 |
| AK/AM | 工程PASS：冻结diff、日志隐私测试及静态核对 |
| AN01～AN06 | PASS：项目负责人2026-10-03真实微信人工验收反馈，T01～T06逐项PASS |
| AO/AP/AQ | 工程PASS：未进入09/10/部署；文档同步、RESULT完整 |
| AR/AS | PASS：所有适用P0、最终自动/PG回归及负责人真实微信T01～T06全部满足，Stage08最终PASS |

## 人工验收

以上结果来自项目负责人 2026-10-03 真实微信小程序人工验收反馈，不以自动测试、API 测试或 PostgreSQL 专项替代。

负责人已明确逐项反馈以下T01～T06全部PASS。下表保留冻结验收场景与对应结果；不补造设备型号、样本细节或截图证据。

| 编号 | 操作 | 预期 | 状态 |
| --- | --- | --- | --- |
| T01 | 空档案删除：新建空测试档案→管理→明确确认永久删除 | 档案消失，页面正常；取消不删除另有自动测试证据 | 负责人真实微信人工验收 PASS |
| T02 | 已使用档案完整删除：含正式报告、指标历史/趋势和Favorite的测试档案→查看影响摘要→确认删除 | 档案、报告、指标、关注退出查询；旧原图入口不可访问；其它档案不受影响 | 负责人真实微信人工验收 PASS |
| T03 | 未完成任务随档案删除：READY/OCR_FAILED/PENDING_CONFIRMATION中的至少一个未完成任务→删除所属档案 | 无需逐任务删除；任务记录消失，旧任务不可重新打开 | 负责人真实微信人工验收 PASS |
| T04 | 删除当前默认档案：至少两个档案，删除当前默认档案 | 自动选择剩余档案；首页、报告、我的指标使用替换档案，无旧上下文 | 负责人真实微信人工验收 PASS |
| T05 | 删除最后一个档案并重新创建：删除最后档案→首页→重新创建 | 显示“还没有健康档案”，可重新创建；无悬空default/selected | 负责人真实微信人工验收 PASS |
| T06 | PROCESSING OCR删除阻断、终态后再次删除 | 真实OCR进入PROCESSING→删除被阻断→HealthProfile与OCR任务保持→OCR正常离开PROCESSING→再次删除成功 | 负责人真实微信人工验收 PASS |

T06真实执行链明确为：

```text
真实 OCR 进入 PROCESSING
→ 删除被阻断
→ HealthProfile 与 OCR 任务保持
→ OCR 正常离开 PROCESSING
→ 再次删除成功
```

COS故障、late object和not_before由工程/PG替身验证，不要求负责人制造真实COS故障。人工PASS仅依据负责人反馈记录。

## Git与停止点

收尾开始时执行 `git status`、分支、最近3条log、`git fetch origin` 与引用核验，工作区clean，分支为 `stage/08-profile-data-deletion`，HEAD / origin/stage/08-profile-data-deletion均为 `fdd53c708090faf4554c0d83688bdf35171579f8`。main / origin/main均为 `bdb0fffb3f7d29d4739477ed3c37004e070ded9d`。Stage08业务实现已提交并推送，不再沿用初次实施结束时“实现未提交、HEAD仍是main”的旧描述。

本次提交标题为 `docs: finalize stage 08 acceptance`，仅包含根/backend/miniapp README、阶段索引、本目录README与RESULT六份文档；无业务实现、测试、PLAN或ACCEPTANCE修改。完整收尾提交SHA可通过 `git log -1 --format=%H -- docs/stages/08-profile-data-deletion/RESULT.md` 定位，实际SHA同时记录在本轮最终汇报。

最终交付分支仍为 `stage/08-profile-data-deletion`；文档提交后工作区clean，较远端同名分支领先1个提交。本轮收尾提交未push，Stage08未合入main；main / origin/main保持上述Stage07基线。不重写历史，不执行force push。

Stage08最终PASS。本轮止于Stage08验收收尾。下一阶段仅记录为 **Stage 09｜整体产品化 + 统一 UI / UX 打磨**：首页产品化、信息架构、异常标记/待处理事项轻量展示、小程序整体视觉统一、页面交互与状态统一、历史UI/UX债务、Admin基础视觉与交互一致性。Stage09尚未实施，详细PLAN/ACCEPTANCE需另行冻结。

之后为 **Stage 10｜上线前可靠性、安全与运行体系收口**，再进入部署与发布；本轮未实施Stage10或部署发布。
