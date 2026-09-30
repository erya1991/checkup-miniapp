# Backend（Stage 05，待真实微信人工验收）

提供健康检查、微信 code 登录、健康档案、COS 原图资产、OCR 任务/持久化队列/独立 Worker，以及 Stage 04 确认和 commit。`0003_ocr` 增加不可变机器快照；`0004_confirmation_report` 增加报告确认字段及 StandardMetric / ConfirmationItem / LabReport / LabResult。识别成功只到 `PENDING_CONFIRMATION`；用户处理全部 REVIEW 并显式 commit 后才生成正式数据。Stage 04 已 PASS。Stage 05 正式报告管理工程已实现并验证，仍待负责人执行真实微信 V01～V06，当前不得判定 PASS，见 Stage 05 RESULT。

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

配置读取仓库根目录 `.env` 或进程环境变量；`DATABASE_URL` 必填。常规 pytest mock 微信身份交换和 COS 服务端操作；独立的 PostgreSQL 队列脚本使用唯一命名临时数据库。COS 授权仅对一个随机 object key 开放 15 分钟 PutObject；登记时后端 HEAD 验证对象大小；原图预览通过短时签名 URL。删除原图时同步调用 COS 删除，失败保留 Asset 和持久化 `file_cleanups.PENDING`，用户可重试删除。已有导入任务的健康档案禁止删除。

Stage 04 路由（前缀 `/api/v1`）：

| 方法 | 路径 | 行为 |
| --- | --- | --- |
| GET | `/ingestions/{id}/confirmation` | ingestion 行锁下幂等初始化旧 OCR 工作区，返回报告信息、确认项、原图页信息 |
| PATCH / PUT | `/ingestions/{id}/confirmation` | 修改医院、检验日期/时间、编号、分类、本人 ACTIVE 档案 |
| POST | `/ingestions/{id}/confirmation/items` | 手工补项 |
| PATCH / PUT | `/ingestions/{id}/confirmation/items/{item_id}` | 五种处理和最终值编辑，不修改 OcrResultItem |
| POST | `/ingestions/{id}/manual` | READY/OCR_FAILED 保留原图转手工；重复转换幂等 |
| GET | `/standard-metrics?q=` | code/name 只读搜索，最多 100 条 |
| POST | `/ingestions/{id}/commit` | 校验、重复检查、单事务创建，重复请求返回相同 report_id |

`app/confirmation.py` 负责来源校验、编辑、保守数值解析、duplicate 和 commit；API 模块负责资源所有权、行锁、单次 commit/rollback 和序列化。commit 还锁定当前档案以串行处理同档案的并发重复检查；不同 ingestion 不会仅靠 Python if 保障幂等。三个来源字段分别具有数据库 UNIQUE。疑似重复错误 `DUPLICATE_CONFIRM_REQUIRED` 的 details 包含最小候选摘要和绑定当前值/保存版本/候选集的 HMAC acknowledgement；用户明确继续后再传 `duplicate_acknowledgement`。数据修改后重新提示。检验日期必须人工填写，绝不补上传日期。

seed v1 在 migration 中一次性导入，未知 code 不自动建主数据；未来扩充需新版本和新增迁移，不能修改已应用的 0004。PostgreSQL Stage 04 验证脚本验证两座临时库、真实数据库异常回滚、并发初始化与 commit，最后仅删除本次创建的库。普通请求异常日志不输出 SQL 参数，避免医疗值进入日志。

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

Stage 04 专项脚本固定执行到 `0004_confirmation_report`，保留全部原有断言；Stage 05 的 `tests/verify_postgres_reports.py` 独立验证 0004 → 0005 及空库 → head，在升级前建立真实 Stage 04 合成正式报告，核对升级后直接查询、事务回滚、迁移/删除/目标 commit 并发、完整删除与 cleanup 重试。两座 UUID 临时库最终删除并验证不存在，COS 使用合成替身。现有 `tests/verify_postgres_queue.py` 同时验证当前 head 下的队列行为。所有样本为合成数据。
