# Stage 02｜实施结果

**状态：PASS**（2026-09-29）。项目负责人已反馈真实微信小程序与私有 COS 的 Stage 02 人工验收全部通过；本轮重新执行的自动检查、构建和 PostgreSQL 迁移也全部通过。本阶段止于 `ReportIngestion.READY`，未进入 OCR。

## 1. 实际完成内容与文件

- 后端完成微信 code 登录、User 去重、系统 Token、HealthProfile CRUD/切换、ReportIngestion、单对象 COS 临时授权、ReportAsset 登记/排序/删除及原图短时签名预览。数据权限按当前 User 校验。
- 小程序完成首次无档案引导、档案管理、拍照/相册多图上传、进度与失败重试、预览/追加/排序/删除，以及退出页面后从后端恢复任务和图片页序。
- Alembic `0002_profile_upload` 建立 User、HealthProfile、ReportIngestion、ReportAsset 及上传授权、文件清理辅助表。Stage 02 状态仅使用 `UPLOADING ↔ READY`。
- 主要代码在 `backend/app/api/v1/business.py`、`backend/app/core/auth.py`、`backend/app/core/cos.py`、`backend/app/models/entities.py`、`backend/migrations/versions/0002_profile_upload.py`、`miniapp/src/api.ts`、`miniapp/src/cos.ts` 和 `miniapp/src/pages/`。本轮收口实际修改：`backend/pyproject.toml`、本 `RESULT.md`。

## 2. 环境、依赖与迁移

Python 3.12.10；FastAPI 0.141.1；SQLAlchemy 2.1.1；Alembic 1.20.0；PostgreSQL 17；PyJWT 2.15.1；COS Python SDK 1.9.44；qcloud-python-sts 1.3.5；httpx 0.28.1，`socksio` 1.0.0；Node 24.14.0；pnpm 12.6.0；uni-app `3.0.0-5000720260410001`；cos-wx-sdk-v5 1.8.0。

本轮将正式后端依赖改为 `httpx[socks]>=0.28,<1`。重新执行 `.venv/Scripts/python.exe -m pip install -e '.[dev]'` 后，确认 `socksio` 已由项目依赖解析，`pip check` 显示 `No broken requirements found`；不依赖手工单独安装。

现有 PostgreSQL 容器为 healthy，`.venv/Scripts/alembic.exe upgrade head`、`current` 确认 `0002_profile_upload (head)`。另创建唯一命名临时空库，完整执行 `0001_foundation → 0002_profile_upload` 并确认 head，随后只删除该临时库。Stage 02 migration 含 downgrade，但本次未执行 downgrade。

## 3. 本轮自动化复核

| 检查 | 结果 |
| --- | --- |
| `backend/.venv/Scripts/python.exe -m pytest -q` | PASS：8 passed、0 failed；1 条上游 TestClient 弃用警告。微信与 COS 外部服务在自动测试中 mock |
| `backend/.venv/Scripts/ruff.exe check . --no-cache` | PASS：All checks passed |
| `miniapp/pnpm typecheck` | PASS |
| `miniapp/pnpm build:mp-weixin` | PASS：微信小程序产物构建完成 |
| `admin-web/pnpm typecheck` | PASS |
| `admin-web/pnpm build` | PASS：Vite 构建完成，主 chunk >500 kB 提示 |
| 既有库及全新临时 PostgreSQL `alembic upgrade head` | PASS：均到 `0002_profile_upload (head)` |

## 4. 人工验收与 ACCEPTANCE 编号

以下人工结果由项目负责人在真实环境完成并于 2026-09-29 提供；Codex 本轮未独立操作微信开发者工具或读取 COS 控制台。真实微信登录、首次本人档案、家庭成员新增/切换/编辑/删除、单图/多图上传、预览/排序/删除、退出重进后恢复、READY、上传失败提示及后端恢复后重试均已通过。COS Bucket 已确认私有读写，原始对象 URL 无授权不可访问；上传后不触发 OCR，也无 Stage 03 结果页面。

| 编号 | 结论与依据 |
| --- | --- |
| A01、A02 | PASS：健康检查人工通过；PostgreSQL、迁移、双前端构建复核通过 |
| B01～B05 | PASS：真实微信登录人工通过；User 去重、未认证拒绝为自动测试；AppSecret 留在服务端，`.env` 不在 Git tracked |
| C01～C05 | PASS：无档案引导及家庭成员创建、编辑、删除、切换由人工验收；API 持久化有自动测试 |
| C06 | PASS：跨用户档案 GET/PATCH/DELETE 自动测试 |
| D01～D03 | PASS：档案归属、他人档案拒绝有自动测试；退出重进任务与页序恢复人工通过 |
| E01～E04 | PASS：用户确认私有 Bucket 与无授权不可访问；STS 单对象 PutObject、短时效期及随机 key 由代码和测试验证 |
| E05～E08 | PASS：单图、多图、失败重试及真实小程序上传环境人工通过；域名/白名单按已通过的真实环境验收记录 |
| F01～F06 | PASS：图片预览、追加、排序、删除、READY 人工通过；排序完整性和删空状态有自动测试 |
| G01～G03 | PASS：跨用户 ingestion、授权、Asset 操作自动测试 |
| G04 | PASS：`.env` 被 Git 忽略且未被跟踪；源码/示例未写入真实 Secret |
| H01～H05 | PASS：本轮 8 个后端测试、Ruff、小程序和管理端 typecheck/build 均通过 |
| I01 | PASS：项目负责人反馈完整 Stage 02 微信开发者工具主流程通过 |
| J01 | PASS：未启用 OcrTask、OCR Worker、识别结果、确认项或正式报告；人工页面验收确认无 Stage 03 内容 |

## 5. 配置与安全收口

`backend/app/main.py` 已将 `httpx`、`httpcore` 日志级别设为 `WARNING`；`exchange_wechat_code()` 在微信返回非零业务 `errcode` 时仅记录 `errcode`、`errmsg`。现有业务日志格式保持不变，不记录 AppSecret、`js_code`、完整微信请求 URL、Authorization Token 或 COS Secret。

`.env.example` 和 README 已明确列出 `JWT_SECRET`，README 要求至少 32 字符；真实值仅存在本地未跟踪的 `.env`。`git check-ignore .env` 命中，`git ls-files .env` 为空。COS 使用服务端永久凭据申请 900 秒、单 object key、仅 PutObject 的临时凭证，Bucket 私有；原图预览由服务端鉴权后签发 300 秒 URL。

## 6. 已接受的 PLAN 差异

- 保留计划中的 `PATCH /health-profiles/{id}`，同时提供等价 PUT 供微信小程序更新档案。
- 增加 UploadAuthorization、FileCleanup 辅助表，以约束一次上传授权及记录 COS 删除失败；增加当前用户 ingestion 列表与私有图片预览接口，以支持退出重进恢复。
- 本地 SOCKS 代理场景纳入正式 `httpx[socks]` 依赖。以上未改变 V1.0 技术路线或 Stage 02 业务边界。

## 7. 已知问题与后续事项

**保留的非阻塞技术债：**COS 文件直传成功后若 ReportAsset 注册失败，可能留下未关联对象。Stage 02 不实现定时清理，也不引入 Redis、Celery 或消息队列；正式上线前需设计并验证过期未登记对象清理。Asset 删除失败已有 `file_cleanups.PENDING` 记录，需排查并重试。

Stage 02 验收已完成，**具备进入 Stage 03 的阶段条件**；本次未创建 Stage 03 PLAN，未开始 OCR 工作。
