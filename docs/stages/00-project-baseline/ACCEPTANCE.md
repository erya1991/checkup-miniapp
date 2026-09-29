# 阶段 00｜ACCEPTANCE

## 1. 仓库文件验收

- [ ] A00-01 根目录存在 `AGENTS.md`。
- [ ] A00-02 存在 PRODUCT / TECH / DEVELOPMENT / ENVIRONMENT / GLOSSARY baseline。
- [ ] A00-03 存在 SYSTEM_ARCHITECTURE / DATA_MODEL / API_CONVENTIONS / OCR_INTEGRATION。
- [ ] A00-04 存在阶段模板 PLAN / ACCEPTANCE / RESULT。
- [ ] A00-05 阶段 01 已有完整 PLAN + ACCEPTANCE。
- [ ] A00-06 `.env.example` 存在且不包含真实密钥。
- [ ] A00-07 `.gitignore` 能排除 `.env`、虚拟环境、node_modules、OCR/真实医疗临时数据。

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

- [ ] A00-08 Git 可用。
- [ ] A00-09 Python 3.12 可用，当前目标 3.12.10。
- [ ] A00-10 Node 主版本 24。
- [ ] A00-11 pnpm 主版本 12。
- [ ] A00-12 Docker 与 Docker Compose v2 可用。
- [ ] A00-13 微信开发者工具可正常启动。

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
- [ ] A00-14 能正确回答 Ingestion → OCR → Confirmation → commit → LabReport/LabResult。
- [ ] A00-15 明确 FINAL_REVIEW 必须处理完成。
- [ ] A00-16 明确 V1.0 不使用 Redis/Celery。
- [ ] A00-17 正确定位当前下一阶段为 01-foundation。

## 4. 安全验收

- [ ] A00-18 Git 工作区不存在真实 AppSecret/COS SecretKey/数据库生产密码。
- [ ] A00-19 不向仓库加入真实用户检验报告。

## 5. 退出条件

A00-01 ～ A00-19 全部 PASS 后，阶段 00 通过，可开始阶段 01。
