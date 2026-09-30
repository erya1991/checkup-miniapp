# 检查单小程序 Checkup Miniapp

面向个人及家庭成员的长期检验报告管理工具。

核心闭环：

`健康档案 → 上传报告 → OCR → AUTO/REVIEW → 人工确认 → 正式报告 → 指标历史 → 趋势 → 原始报告核对`

> 本产品用于检验报告整理、归档与趋势查看，不提供医疗诊断、疾病预测、AI 问诊或用药建议。

## 仓库结构

```text
checkup-miniapp/
├─ AGENTS.md
├─ README.md
├─ .env.example
├─ miniapp/                  # uni-app 微信小程序
├─ backend/                  # FastAPI + OCR Worker
├─ admin-web/                # Vue3 管理后台
├─ deploy/                   # Docker Compose / Nginx / scripts
├─ scripts/                  # 本地辅助脚本
└─ docs/
   ├─ 00-baseline/           # 长期产品/技术/研发基线
   ├─ 01-architecture/       # 专题技术设计
   ├─ stages/                # 分阶段计划、验收、结果
   └─ decisions/             # 长期架构决策记录
```

## 当前阶段

Stage 00～04 已验收通过。**Stage 04 = PASS**，已完成人工确认工作区、报告信息确认、AUTO/REVIEW 处理、StandardMetric 选择、手工补项/纯手工兜底、疑似重复提示，以及事务安全、幂等的正式 `LabReport / LabResult` 生成。项目负责人已在真实微信小程序中完成 W01～W04 人工验收，逐项证据见 [Stage 04 RESULT](docs/stages/04-confirmation-report/RESULT.md)。

OCR 成功只到 `PENDING_CONFIRMATION`，必须经过用户人工确认和最终 commit；只有 commit 后的 `LabReport / LabResult` 才是正式健康数据。**Stage 05 正式报告管理已实现，工程自动验证通过，待负责人真实微信 V01～V06 验收，当前不得判定 PASS**。正式列表/详情仅查询 LabReport / LabResult；支持原图、整份档案迁移、完整硬删除和持久化 COS prefix 清理。Stage 06/07 未进入，证据见 [Stage 05 RESULT](docs/stages/05-report-management/RESULT.md)。

## 本地运行

| 工程 | 已实现入口 | 操作 |
| --- | --- | --- |
| PostgreSQL 17 | 根目录 `compose.yaml` | 复制 `.env.example` 为 `.env`，执行 `docker compose up -d postgres` |
| Backend | `GET /api/v1/health` | 按 `backend/README.md` 创建 Python 3.12 虚拟环境、安装依赖、执行迁移并启动 |
| Miniapp | 登录、档案、上传、OCR 状态/任务记录、统一确认页 | 在 `miniapp/` 执行 `pnpm install`、`pnpm test`、`pnpm typecheck`、`pnpm build:mp-weixin`；将 `dist/build/mp-weixin` 导入微信开发者工具 |
| Admin Web | `/` 占位首页 | 在 `admin-web/` 执行 `pnpm install`、`pnpm dev`、`pnpm build` |

两个前端分别维护 `pnpm-lock.yaml`。真实 `.env` 不提交。后端运行前需将 `.env.example` 复制为 `.env`，设置 `DATABASE_URL`、至少 32 字符随机 `JWT_SECRET`、`WECHAT_APP_ID`、`WECHAT_APP_SECRET`、`COS_SECRET_ID`、`COS_SECRET_KEY`、`COS_BUCKET`、`COS_REGION`。执行 `docker compose up -d postgres`，在 `backend/` 执行 `.venv/Scripts/alembic.exe upgrade head` 和 `.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`。后端通过微信服务端 code 交换用户身份，签发自己的 Token；COS 永久密钥只在服务端使用。

微信开发者工具运行时，在 `miniapp/` 设置 `VITE_API_BASE_URL=https://<你的 API 域名>/api/v1` 并构建；开发者工具使用真实 AppID。微信公众平台应配置 HTTPS API 为 request 合法域名，COS 的 `https://<Bucket>.cos.<Region>.myqcloud.com` 为 request、uploadFile、downloadFile 合法域名，并按腾讯 COS 小程序接入要求配置白名单。COS Bucket 必须是私有读写。`miniapp/src/manifest.json` 保持 URL 合法域名检查开启。Stage 02 的真实验收结果见 `docs/stages/02-profile-upload/RESULT.md`。

Stage 03 后端安装与启动（在 `backend/`）：

```powershell
# Python 3.12.10；普通环境包含 FastAPI、RapidOCR 和已验证解析依赖
.venv\Scripts\python.exe -m pip install -e ".[dev,ocr]"
# 独立 Paddle 环境；已验证模型文件在 backend/ocr_runtime/models/
py -3.12 -m venv .venv-paddle
.venv-paddle\Scripts\python.exe -m pip install -r ocr-paddle-requirements.txt
.venv\Scripts\alembic.exe upgrade head
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# 在另一个终端中启动唯一 Worker（concurrency=1）
.venv\Scripts\python.exe -m app.ocr_worker
```

普通环境和 Paddle 环境的路径由 `.env` 的 `OCR_NORMAL_PYTHON`、`OCR_PADDLE_PYTHON` 指定；Linux 部署需填相应 Linux 解释器路径。`OCR_TASK_LEASE_SECONDS` 默认 1800 秒；J03 人工验收可设为 60 或 120 秒，修改后重启 Worker 并创建新 OCR 任务。Worker 续租间隔会随 lease 缩短。`OCR_WORK_DIR` 是临时目录，不能放入 Git。`backend/ocr_runtime/README.md` 记录 PoC 内容哈希、模型哈希和仅限运行入口的适配。正式运行不需要 PoC sibling 目录。使用真实私有 COS 凭据前先配置服务端环境；前端不持有永久 COS 密钥。

自动验证：在 `backend/` 执行 `.venv/Scripts/python.exe -m pytest -q`、`.venv/Scripts/ruff.exe check . --no-cache`、`.venv/Scripts/python.exe tests/verify_postgres_queue.py`、`.venv/Scripts/python.exe tests/verify_postgres_confirmation.py`；在 `miniapp/` 执行 `pnpm test`、`pnpm typecheck`、`pnpm build:mp-weixin`；在 `admin-web/` 执行 `pnpm typecheck`、`pnpm build`。PostgreSQL 脚本创建唯一命名临时库并自行删除，要求 PostgreSQL 17 及创建临时库权限。PoC Frozen Regression 继续在独立 PoC 仓库执行。真实医疗报告、OCR 输出和密钥不得提交；本仓库测试只使用合成或经许可的数据。

Stage 04 migration 为 `0004_confirmation_report`，从 `0003_ocr` 增量升级，不改写前三个版本。迁移导入 `backend/migrations/data/standard_metrics_v1.json` 的 12 条产品侧最小标准指标；启动、Worker 和确认 API 不从 OCR 指标库反写主数据。旧待确认任务首次访问 `/ingestions/{id}/confirmation` 幂等初始化，无需重新识别。纯手工录入仍必须先上传原图。确认更新支持 PATCH/PUT，小程序使用 PUT。commit 成功显示结果数量、完成反馈，并使用返回的 report_id 进入正式报告详情。

验收证据：Backend 52 passed、Ruff PASS；PostgreSQL 17 迁移/并发初始化/事务回滚/并发 commit/唯一约束 PASS，原有 59 项任务初始化幂等且全部机器快照未变；Miniapp 13 tests/typecheck/build PASS；Admin typecheck/build PASS。以上为已执行的工程验证；真实微信 W01～W04 已由项目负责人手动验收，全部 PASS。本次仅更新文档，未重复执行上述测试链路。

## Codex 使用方式

每个新 Codex 会话不需要粘贴全部历史需求。先要求 Codex：

1. 读取根目录 `AGENTS.md`；
2. 读取当前阶段 `PLAN.md` 与 `ACCEPTANCE.md`；
3. 按 `AGENTS.md` 指引按需读取 baseline / architecture；
4. 不扩大当前阶段范围；
5. 完成后执行验收并更新 `RESULT.md`。

推荐阶段 Prompt：

```text
当前开始执行研发阶段 XX。
请先读取根目录 AGENTS.md，然后读取当前阶段 PLAN.md 和 ACCEPTANCE.md，
并按 AGENTS.md 指引读取必要的 baseline / architecture 文档。
严格限制在 PLAN.md 范围内实施，不提前开发后续阶段能力。
完成后运行 ACCEPTANCE.md 要求的自动测试和手工检查，
并更新当前阶段 RESULT.md，记录完成项、测试结果、设计偏差、已知问题和下一阶段注意事项。
```

## 重要说明

OCR PoC / Regression 继续保留在独立 `checkup-ocr-poc` 仓库。正式产品只接入已验证的 Pipeline 能力。即使识别结果含 `FINAL_REVIEW`，OCR task 仍可成功；最终状态为“识别完成，待确认”。Stage 04 只编辑 `ConfirmationItem`，不覆盖机器快照；全部 REVIEW resolved 后，由用户 commit 生成正式数据。

Stage 05 运行补充（在 `backend/`）：

```powershell
# 正常升级目标环境；不属于测试数据库操作
.venv/Scripts/alembic.exe upgrade head
# 重启 API，并另开终端持续运行清理消费者
.venv/Scripts/python.exe -m app.cleanup_worker
# 独立临时 PostgreSQL 17 验证
.venv/Scripts/python.exe tests/verify_postgres_reports.py
```

`0005_report_management` 只增加 `FileCleanup.target_type`，历史记录默认为 OBJECT。正式报告删除先在同一事务登记 PREFIX cleanup 并硬删除完整来源链；事务提交后尝试即时 COS 删除，失败仍返回 204 并保留 PENDING。cleanup worker 每 10 秒重试 PENDING，按行锁跳过其它消费者正在处理的记录，支持 OBJECT 与分页 PREFIX，只有成功才置 DONE。运行账户需具备 COS 列举对象、删除对象权限。消费者必须与 API/OCR Worker 一起持续运行；没有引入新中间件。本轮验证只操作临时测试库与合成 COS 替身，未迁移开发人员业务数据库、未删除真实 COS 文件，真实微信验收前须执行上述正常 migration 并启动/重启进程。
