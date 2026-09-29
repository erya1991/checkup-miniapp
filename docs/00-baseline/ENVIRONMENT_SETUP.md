# ENVIRONMENT_SETUP｜本地开发环境与软件清单

## 1. 版本基线

为了复用已经验证通过的 OCR PoC 环境，正式 MVP 暂不追最新 Python。

| 软件 | 项目基线 | 说明 |
|---|---|---|
| Python | 3.12.10 | 与现有 OCR PoC 已验证环境保持一致 |
| Node.js | 24 LTS | 小程序和 Admin 前端 |
| pnpm | 12.x | 前端包管理，项目后续用 packageManager 锁定 |
| PostgreSQL | 17.x | 本地通过 Docker 运行 |
| Git | 当前稳定版 | 版本管理 |
| Docker Desktop | 当前稳定版 | Windows 本地容器环境 |
| VS Code | 当前稳定版 | 主开发 IDE |
| 微信开发者工具 | 当前稳定版 | 微信小程序运行/调试 |
| Chrome / Edge | 当前稳定版 | Admin Web 调试 |

> Python 3.12 后续虽进入安全修复阶段，但 V1.0 首先保持 OCR 兼容性；升级到其它 Python 主版本需要单独回归 OCR Pipeline 后再决定。

## 2. 必须安装

### 已验证可继续使用

项目负责人已人工确认：
- Git 2.53.0.windows.1；
- Python 3.12.10；
- Node.js 24.14.0；
- pnpm 12.6.0；
- Docker 29.6.1；
- Docker Compose 5.3.0；
- 微信开发者工具已安装并可正常使用。

如果 Docker 当前安装的是 Docker Desktop，确保 Windows 下 Docker Engine 可正常启动。

## 3. 暂时不需要本机直接安装

- PostgreSQL Server：使用 Docker；
- Nginx：本地阶段不要求，生产部署再使用；
- Redis：V1.0 不使用；
- RabbitMQ/Kafka：V1.0 不使用；
- Java/JDK：本项目后端不依赖（你其它项目可继续保留）。

## 4. Windows 环境验证

PowerShell 执行：

```powershell
git --version
py -3.12 --version
node --version
pnpm --version
docker --version
docker compose version
```

预期：
- Python 为 3.12.x，研发基线优先使用已有 3.12.10；
- Node 主版本为 24；
- pnpm 主版本为 12；
- Docker Desktop 自带的 Docker Compose 可用，`docker compose` CLI 命令可正常执行；不锁定具体 Compose 大版本。

仓库还提供：

```powershell
./scripts/check-env.ps1
```

用于一次性检查关键命令。

## 5. Python 虚拟环境

后端进入 `backend/` 后建议：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
```

项目依赖必须安装到 `.venv`，不要依赖全局 Python 包。

## 6. Node/pnpm

前端两个工程：
- `miniapp/`；
- `admin-web/`。

两者统一 pnpm，不混用 npm/yarn。

工程初始化后通过各自 `package.json` 的 `packageManager` 字段锁定 pnpm 主版本。

## 7. PostgreSQL

阶段 01 使用 Docker Compose 启动 PostgreSQL 17。

不要求 Windows 本地安装 PostgreSQL 服务。

数据库凭据来自 `.env`，不得写死在 compose 或源码真实环境中。

## 8. 腾讯云 COS / 微信小程序配置

阶段 01 不要求真实接通。

阶段 02 开始前准备：
- 微信小程序 AppID / AppSecret；
- 腾讯云 COS Bucket；
- COS Region；
- 服务端 SecretId / SecretKey；
- 将真实值只写入本机/服务器 `.env` 或 Secret 管理方式。

## 9. VS Code 建议扩展

非强制，但推荐：
- Python；
- Pylance；
- Ruff；
- Vue - Official；
- Docker；
- EditorConfig（如果后续加入 `.editorconfig`）。

Codex 插件/CLI 按当前使用方式配置即可。

## 10. 环境原则

- 不为解决依赖问题随意升级 Python 主版本；
- 不同时保留 npm/yarn/pnpm 多套锁文件；
- 数据库使用容器保证环境一致；
- 所有需要部署的配置必须能由 `.env.example` 看出所需变量；
- 任何真实 Secret 不进入 Git。
