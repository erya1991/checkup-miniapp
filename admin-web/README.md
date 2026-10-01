# Admin Web（Stage 07：等待人工验收）

Vue 3 + Vite + TypeScript + Element Plus + Vue Router。独立登录、标准指标、别名、OCR 指标问题和只读任务页。没有新增依赖。

先在 backend 所用的安全环境 / 根目录不提交的 `.env` 配置：

- `ADMIN_USERNAME`：单管理员账号；
- `ADMIN_PASSWORD_HASH`：PBKDF2-SHA256 hash，600000 次迭代；
- `ADMIN_JWT_SECRET`：至少 32 字符的独立随机 secret，必须不同于普通用户 `JWT_SECRET`。

在 backend 目录生成 hash（隐藏密码输入，只输出 hash；不要提交真实凭据）：

```powershell
.venv/Scripts/python.exe -c "from getpass import getpass; from app.core.admin_auth import password_hash; print(password_hash(getpass('Admin password: ')))"
```

在验收目标环境执行 `.venv/Scripts/alembic.exe upgrade head` 到 `0007_standard_metric_admin` 并重启 API。工程验证只迁移 UUID 临时测试库，没有升级业务库或配置真实管理员。

```powershell
pnpm install
pnpm typecheck
pnpm dev --host 127.0.0.1
pnpm build
```

开发页面为 `http://127.0.0.1:5173/`，未登录进入 `/login`。Vite 将 `/api` 代理到 `http://127.0.0.1:8000`；其它 API 地址可通过 Vite 进程环境 `ADMIN_API_TARGET` 配置。生产构建使用同源 `/api/v1/admin`，由部署网关提供 API 和 history fallback。

Token 存在当前 tab 的 sessionStorage，有效期 8 小时；请求统一处理 Authorization、401、错误码；退出时清除 Token。

| 页面 | 能力 |
| --- | --- |
| 标准指标 | code/name 搜索、status/category 筛选和分页；新增、编辑 name/category、停用/恢复；详情展示引用数量和别名 |
| 指标别名 | 全局搜索、分页；新增、编辑文本/type、停用/恢复；目标创建后只读 |
| OCR 指标问题 | 未匹配名称、缺失产品 code、停用 code；预填创建 Alias / StandardMetric，由管理员确认保存，或恢复主数据 |
| OCR 任务 | status / pipeline version 筛选、分页；只读技术字段和数量摘要 |

普通用户 Token 不能调用 Admin API；Admin Token 不能访问用户业务数据 API。pending 引用阻止停用。Alias 只影响未来首次确认与搜索，REVIEW 仍需人工确认，旧工作区和正式历史不回填。无物理删除、OCR 重跑或算法配置入口。

负责人执行 [ACCEPTANCE T01～T13](../docs/stages/07-admin/ACCEPTANCE.md) 并反馈 PASS/FAIL。工程结果见 [RESULT](../docs/stages/07-admin/RESULT.md)；构建不能替代真实 Admin Web / 微信人工验收。
