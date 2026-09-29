# 阶段 00｜ACCEPTANCE

## 1. 仓库文件验收

- [x] A00-01 根目录存在 `AGENTS.md`。
- [x] A00-02 存在 PRODUCT / TECH / DEVELOPMENT / ENVIRONMENT / GLOSSARY baseline。
- [x] A00-03 存在 SYSTEM_ARCHITECTURE / DATA_MODEL / API_CONVENTIONS / OCR_INTEGRATION。
- [x] A00-04 存在阶段模板 PLAN / ACCEPTANCE / RESULT。
- [x] A00-05 阶段 01 已有完整 PLAN + ACCEPTANCE。
- [x] A00-06 `.env.example` 存在且不包含真实密钥。
- [x] A00-07 `.gitignore` 能排除 `.env`、虚拟环境、node_modules、OCR/真实医疗临时数据。

## 2. 本机环境验收

PowerShell：

```powershell
git --version
py -3.12 --version
node --version
pnpm --version
docker --version
docker compose version
```

- [x] A00-08 Git 可用。
- [x] A00-09 Python 3.12 可用，当前目标 3.12.10。
- [x] A00-10 Node 主版本 24。
- [x] A00-11 pnpm 主版本 12。
- [x] A00-12 Docker 可用，Docker Desktop 自带的 `docker compose` CLI 可执行，不锁定 Compose 大版本。
- [x] A00-13 微信开发者工具可正常启动。

也可执行：

```powershell
./scripts/check-env.ps1
```

## 3. Codex 上下文验收

在一个新的 Codex 会话中只给出：

```text
请读取 AGENTS.md，并告诉我：
1. 项目核心数据链；
2. 为什么 OCR 不能直接生成正式报告；
3. V1.0 是否使用 Redis/Celery；
4. 当前应该先执行哪个阶段。
```

预期：
- [x] A00-14 能正确回答 Ingestion → OCR → Confirmation → commit → LabReport/LabResult。
- [x] A00-15 明确 FINAL_REVIEW 必须处理完成。
- [x] A00-16 明确 V1.0 不使用 Redis/Celery。
- [x] A00-17 正确定位当前下一阶段为 01-foundation。

## 4. 安全验收

- [x] A00-18 Git 工作区不存在真实 AppSecret/COS SecretKey/数据库生产密码。
- [x] A00-19 不向仓库加入真实用户检验报告。

## 5. 退出条件

A00-01 ～ A00-19 全部 PASS 后，阶段 00 通过，可开始阶段 01。
