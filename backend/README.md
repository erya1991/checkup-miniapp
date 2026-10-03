# Backend（Stage 08 = PASS）

提供健康检查、微信 code 登录、健康档案、COS 原图资产、OCR 任务/持久化队列/独立 Worker，以及 Stage 04 确认和 commit。`0003_ocr` 增加不可变机器快照；`0004_confirmation_report` 增加报告确认字段及 StandardMetric / ConfirmationItem / LabReport / LabResult。识别成功只到 `PENDING_CONFIRMATION`；用户处理全部 REVIEW 并显式 commit 后才生成正式数据。Stage 04 已 PASS。Stage 05 正式报告管理已通过最终自动回归，负责人已确认真实微信 V01～V06 全部 PASS，最终 Stage 05 = PASS（2026-10-01），见 [Stage 05 RESULT](../docs/stages/05-report-management/RESULT.md)。

在仓库根目录复制 `.env.example` 为不提交的 `.env`，设置 `POSTGRES_*` 与一致的 `DATABASE_URL`，以及至少 32 字符的 `JWT_SECRET`、微信 `WECHAT_APP_ID` / `WECHAT_APP_SECRET`、私有 COS 的 `COS_SECRET_ID` / `COS_SECRET_KEY` / `COS_BUCKET` / `COS_REGION`。先运行 `docker compose up -d postgres`。永久密钥不得进入 Git 或小程序。

PowerShell（在 `backend/`）：

```powershell
& 'C:\Users\65410\AppData\Local\Programs\Python\Python312\python.exe' -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev,ocr]'
py -3.12 -m venv .venv-paddle
.\.venv-paddle\Scripts\python.exe -m pip install -r ocr-paddle-requirements.txt
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

第一行解释器路径是本次开发机的实测位置；其它开发机请替换为自己的 Python 3.12.x 路径。访问 `http://127.0.0.1:8000/api/v1/health`。

另开终端执行 `.\.venv\Scripts\python.exe -m app.ocr_worker`。Worker 固定单任务执行；`.env` 的 `OCR_NORMAL_PYTHON` 与 `OCR_PADDLE_PYTHON` 分别指向这两套环境，`OCR_WORK_DIR` 指向未跟踪临时目录。`OCR_TASK_LEASE_SECONDS` 默认 1800 秒；J03 可设为 60 或 120 秒，重启 Worker 后对新 OCR 任务生效，heartbeat 续租间隔按 lease 缩短。PoC 运行源码与模型已随 `backend/ocr_runtime/` 固定，来源和哈希见其 README。Worker 从冻结的 manifest 按页序读取私有 COS 原图，并把所有输出放在每次 run/attempt 专用的私有 COS 前缀。成功后可通过 `GET /api/v1/ingestions/{id}/ocr` 读取汇总状态。

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\python.exe tests\verify_postgres_queue.py
.\.venv\Scripts\python.exe tests\verify_postgres_confirmation.py
```

配置读取仓库根目录 `.env` 或进程环境变量；`DATABASE_URL` 必填。常规 pytest mock 微信身份交换和 COS 服务端操作；独立的 PostgreSQL 队列脚本使用唯一命名临时数据库。COS 授权仅对一个随机 object key 开放 15 分钟 PutObject；登记时后端 HEAD 验证对象大小；原图预览通过短时签名 URL。删除原图时同步调用 COS 删除，失败保留 Asset 和持久化 `file_cleanups.PENDING`，用户可重试删除。Stage 08 支持已有导入任务的整档案隐私删除，PROCESSING OCR 暂时阻断，详见下文。

Stage 04 路由（前缀 `/api/v1`）：

| 方法 | 路径 | 行为 |
| --- | --- | --- |
| GET | `/ingestions/{id}/confirmation` | ingestion 行锁下幂等初始化旧 OCR 工作区，返回报告信息、确认项、原图页信息 |
| PATCH / PUT | `/ingestions/{id}/confirmation` | 修改医院、检验日期/时间、编号、分类、本人 ACTIVE 档案 |
| POST | `/ingestions/{id}/confirmation/items` | 手工补项 |
| PATCH / PUT | `/ingestions/{id}/confirmation/items/{item_id}` | 五种处理和最终值编辑，不修改 OcrResultItem |
| POST | `/ingestions/{id}/manual` | READY/OCR_FAILED 保留原图转手工；重复转换幂等 |
| GET | `/standard-metrics?q=` | ACTIVE code/name/Alias 搜索，返回 canonical StandardMetric，最多 100 条 |
| POST | `/ingestions/{id}/commit` | 校验、重复检查、单事务创建，重复请求返回相同 report_id |

`app/confirmation.py` 负责来源校验、编辑、保守数值解析、duplicate 和 commit；API 模块负责资源所有权、行锁、单次 commit/rollback 和序列化。commit 还锁定当前档案以串行处理同档案的并发重复检查；不同 ingestion 不会仅靠 Python if 保障幂等。三个来源字段分别具有数据库 UNIQUE。疑似重复错误 `DUPLICATE_CONFIRM_REQUIRED` 的 details 包含最小候选摘要和绑定当前值/保存版本/候选集的 HMAC acknowledgement；用户明确继续后再传 `duplicate_acknowledgement`。数据修改后重新提示。检验日期必须人工填写，绝不补上传日期。

seed v1 在 0004 中一次性导入 12 项，未知 code 不自动建主数据；Stage 07 后由管理员逐项确认扩充，不能修改已应用的 0004。PostgreSQL Stage 04 验证脚本验证两座临时库、真实数据库异常回滚、并发初始化与 commit，最后仅删除本次创建的库。普通请求异常日志不输出 SQL 参数，避免医疗值进入日志。

## Stage 05 正式报告管理与清理进程

迁移 `0005_report_management` 只增加 `file_cleanups.target_type`（OBJECT/PREFIX，历史默认 OBJECT）。正常目标环境先执行 `.venv/Scripts/alembic.exe upgrade head`，然后重启 API。测试不会迁移业务库。

| 方法 | 路径（前缀 /api/v1） | 行为 |
| --- | --- | --- |
| GET | `/reports?health_profile_id=&page=&page_size=` | 当前用户 ACTIVE 档案内正式报告，按检验日期/时间排序，分页上限 100 |
| GET | `/reports/{id}` | 只读正式详情、按 sequence_no 排列 LabResult |
| GET | `/reports/{id}/assets` | 来源 ingestion 原图必要元数据，按 page_no |
| GET | `/reports/{id}/assets/{asset_id}/preview` | 鉴权 300 秒私有访问 URL |
| POST | `/reports/{id}/migrate` | 三处 profile 同事务更新，目标档案重新查重，允许确认后继续 |
| DELETE | `/reports/{id}` | 完整来源链硬删除；持久化 PREFIX cleanup；提交后 204 |

另开终端持续执行 `.venv/Scripts/python.exe -m app.cleanup_worker`。这与 OCR Worker 为不同进程，不修改 OCR 算法。清理消费者每 10 秒扫描 PENDING，以 `FOR UPDATE SKIP LOCKED` 避免重复消费者互相阻塞；OBJECT 删除单对象，PREFIX 按 COS Marker 分页列出并逐个删除，重新检查前缀为空才 DONE。对象已不存在/前缀为空可安全重复执行。网络/数据库临时失败后继续重试，不输出 SQL 绑定值、医疗全文、对象 prefix 或密钥。配置沿用现有 DATABASE_URL/COS_*，需 COS 列举/删除权限。API 在删除事务完成后也即时尝试一次清理；失败保持 PENDING，正式报告不恢复，204 不变。重复 DELETE 已不存在的报告返回 404，不重新创建 cleanup。

Stage 04/05 专项保留原迁移、revision 和全部业务断言，先核查旧阶段 schema，再升级当前 head 运行最新服务；Stage 05 用最新服务生成合成旧报告后回退至 0004，再验证 0004 → 0005 的数据兼容。两座 UUID 临时库最终删除，COS 使用合成替身。队列专项验证当前 head。所有样本为合成数据。


## Stage 06 profile metrics

新增 migration `0006_metric_trend`，前置0005；只新建四字段MetricFavorite及profile+metric+date查询索引，不改写正式数据。

| 方法 | 路径（前缀 /api/v1） | 行为 |
| --- | --- | --- |
| GET | `/profile-metrics?health_profile_id=&page=&page_size=` | 已正式出现的标准指标，关注优先，默认20最大100 |
| GET | `/profile-metrics/{id}?health_profile_id=` | latest、history_count、趋势能力、关注状态 |
| GET | `/profile-metrics/{id}/history?health_profile_id=&page=&page_size=` | 全部正式历史，默认50最大100 |
| GET | `/profile-metrics/{id}/trend?health_profile_id=` | 确定数值的单位分组序列，最近可绘制序列优先 |
| PUT / DELETE | `/favorites/{id}?health_profile_id=` | 幂等关注/取消，归属当前档案 |

所有接口校验本人ACTIVE档案，不从临时域补数据。未关联StandardMetric结果不聚合；停用主数据的既往历史仍可见。latest/history以正式检验日期/时间及冻结稳定规则排序，result_text主展示；trend只有非空numeric且comparator为NULL/空/=，不解析文本、不换算单位、不重算abnormal。原图入口复用正式报告API。

正常验收/部署环境需 `alembic upgrade head` 并重启API。初版工程验证仅操作临时库，Codex 未升级业务库。最终收尾只修改文档，保留原 PostgreSQL 17 专项证据并重跑必要自动回归。新增专项命令（backend目录）：

```powershell
.venv/Scripts/python.exe tests/verify_postgres_metrics.py
```

真实PostgreSQL17，两座临时库验证增量/空库升级、并发UNIQUE、六类API权限、旧正式快照保持和迁移删除自然变化；finally删除并核实无残留。新增表/索引与ORM一致，但全库存在已验证的Stage03历史索引差异：migration的ix_ocr_tasks_queue(status,next_attempt_at)与ORM的ix_ocr_tasks_status(status)不一致；不能将全库alembic check记为PASS。初版专项验证其升级前后保持相同，未修改OCR或既有migration；最终收尾保留这一非阻塞记录。

工程测试及负责人真实微信T01～T09记录见 [Stage 06 RESULT](../docs/stages/06-metric-trend/RESULT.md)，Stage 06 最终 PASS。该专项按历史 metadata 检查原 schema 和既有 drift，再升级最新 head 执行业务断言；Stage 07 专项另检查完整当前 metadata。

## Stage 07 主数据与 Admin

Stage 07 migration `0007_standard_metric_admin`：只增加可空 category、MetricAlias、该表 FK/CHECK/索引/ACTIVE partial unique index；不改旧 migration、seed 或历史医疗数据。当前 head 为 Stage 08 的0008。管理员配置与启动见 [Admin README](../admin-web/README.md)。

## Stage 08 整档案隐私删除

`GET /api/v1/health-profiles/{id}/deletion-impact` 返回本人档案 id/name、正式报告数、未完成/全部 ingestion 数、Favorite 数和 PROCESSING task 数，不返回医疗明细或对象 key。未完成数为当前归属且 status != CONFIRMED 的 ingestion 数。

`DELETE /api/v1/health-profiles/{id}` 返回204。`profile_deletion.py` 在单事务内登记全部 ingestion PREFIX cleanup，并物理删除 LabResult、LabReport、ConfirmationItem、OcrResultItem、OcrTask、ReportAsset、UploadAuthorization、ReportIngestion、MetricFavorite、HealthProfile。公共 StandardMetric/MetricAlias 保留。默认档案从同用户剩余 ACTIVE 中按 created_at、id 升序选择，没有则 NULL。历史软删除档案不做批量 backfill。

存在 PROCESSING task 时返回409 `PROFILE_DELETE_BUSY`，details只有 processing_count；未找到或跨用户为404 `PROFILE_NOT_FOUND`，重复删除同样404；数据库失败返回500 `PROFILE_DELETE_FAILED`并整体回滚。COS故障不改变已成功提交的204。

`profile_lifecycle.py` 的 User 级 transaction advisory lock 先于用户侧业务行锁，覆盖同用户档案创建/编辑/default、新 ingestion、上传授权、确认/commit、报告迁移/删除、Favorite；跨用户无全局锁。整档案删除按 task → ingestion 顺序，兼容现有 Worker claim/finish，看到 PROCESSING 即回滚。Worker/queue/lease/runtime均未修改。后续生命周期写入口须先使用此 helper，再取业务行锁，不能绕过 API 的锁契约。

`0008_profile_data_deletion` 新增 `file_cleanups.not_before TIMESTAMPTZ NULL` 和 `(status,not_before,created_at)` 索引。无未来有效授权为NULL，立即due；含consumed的未来授权取最晚 expires_at + 60秒。授权签发记录取真实 STS expired_time 与本地15分钟的较晚值。cleanup扫描及执行入口双重检查not_before，继续使用OBJECT引用保护、PREFIX全量删除、失败PENDING重试；Stage05 NULL仍即时处理。

Stage08最终PASS（2026-10-03）。最终Backend124项（0 failed、0 skipped）、Ruff、PostgreSQL17.11 Stage08及03～07专项全部通过；独立查询临时库0残留，唯一head为 `0008_profile_data_deletion`。负责人2026-10-03真实微信T01～T06全部PASS，实机结果不以自动/API/PG验证替代。Codex本次回归仅使用UUID隔离库和合成COS替身，未执行业务库迁移或部署。其它目标环境沿用 `.venv/Scripts/alembic.exe upgrade head` 后重启API/cleanup worker的运行步骤。专项命令：`.venv/Scripts/python.exe tests/verify_postgres_profile_deletion.py`，证据见 [Stage08 RESULT](../docs/stages/08-profile-data-deletion/RESULT.md)。

| 方法 | 路径（前缀 /api/v1/admin） | 行为 |
| --- | --- | --- |
| POST / GET | `/auth/login` / `/me` | 独立登录 / 身份，8小时 admin scope/audience JWT |
| GET / POST | `/standard-metrics` | q/status/category 分页查询与新增 |
| GET / PATCH | `/standard-metrics/{id}` | 引用摘要；编辑 name/category/status；显式拒绝 code |
| GET / POST | `/metric-aliases` | q/status/standard_metric_id 分页查询与新增 |
| PATCH | `/metric-aliases/{id}` | 编辑 alias/type/status；显式拒绝目标修改 |
| GET | `/ocr-metric-issues` | 最新成功 run 的名称/缺失 code/停用 code 聚合 |
| GET | `/ocr-tasks` | status/pipeline_version 分页，只读技术字段和数量摘要 |

分页默认20、最大100。写事务以 PostgreSQL advisory transaction lock 串行化跨表 namespace 校验；停用锁定指标行并检查 pending；首次确认、选择和 commit 的 ACTIVE 校验持共享行锁。Admin 校验错误不回显密码，日志不含凭据或医疗全文。Issue 按当前规模实时计算，不建独立表。

专项命令：`.venv/Scripts/python.exe tests/verify_postgres_stage07.py`。真实 PG17 验证空库/增量/回退、实际 UNIQUE、并发 Alias/code/rename、pending 与 commit/init 竞态、旧快照和历史兼容，finally 删除临时库并核查不存在。Stage 03 两项 index drift 保持原状，完整 `alembic check` 不记为通过。

**Stage 07 = PASS（2026-10-03）**，负责人真实人工验收 T01～T13 全部 PASS，最终自动及五组 PG17 回归通过，见 [RESULT](../docs/stages/07-admin/RESULT.md)。Confirmation API 批量返回 canonical 摘要；产品 adapter 仅 AUTO_MATCHED / REVIEW 映射 code/name，UNMATCHED 为 NULL，完整候选证据保留。更新代码后需重启 API / OCR Worker；既有 OCR 快照不修复、不重算，T11 已用新任务复验。
