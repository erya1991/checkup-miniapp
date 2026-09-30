# DEVELOPMENT_RULES｜研发规范

## 1. 总原则

- 按阶段交付，不一次性生成全部系统；
- Product Baseline 决定“做什么”；
- Tech Baseline 决定“怎么组织”；
- 当前阶段 PLAN 决定“这一次做什么”；
- 当前 ACCEPTANCE 决定“怎样算完成”。

## 2. 仓库边界

- `miniapp/`：微信小程序；
- `backend/`：FastAPI、数据库访问、OCR Worker 接入；
- `admin-web/`：轻量后台；
- `deploy/`：部署配置；
- `docs/`：产品与工程上下文；
- `scripts/`：本地检查和运维辅助。

不得在根目录堆放临时脚本或 OCR 输出。

## 3. 分支与提交建议

单人/小团队 MVP 推荐：
- `main` 保持可运行；
- 每个阶段使用 `stage/XX-name` 分支；
- 阶段验收通过后合并 main；
- 阶段内提交尽量按可验证小步拆分。

Commit 示例：
- `chore: initialize backend foundation`
- `feat: add health profile api`
- `test: cover report commit idempotency`
- `docs: record stage 02 result`

不要把大量无关修改塞进同一提交。

## 4. Python/后端

- Python 固定 3.12.10，除非形成明确升级决策；
- 使用独立虚拟环境；
- 配置从环境变量读取；
- API router / service / persistence 职责分离，但不为了“分层”制造过度抽象；
- 数据库变更统一 Alembic；
- 业务错误使用稳定 code；
- 所有关键写操作验证资源所有权和当前状态；
- 关键事务必须有自动测试。

推荐代码质量工具：
- pytest；
- ruff；
- 类型检查可在工程稳定后逐步增加，不作为阶段 01 阻塞项，除非 PLAN 明确要求。

## 5. 前端

- TypeScript；
- 网络请求统一封装；
- 不在页面散落 Token/错误处理逻辑；
- 小程序全局 Store 只保存真正全局状态；
- 页面处理 loading/empty/error；
- 不提前建设复杂通用组件体系；
- UI 第一目标是可用和业务正确，再做视觉打磨。

## 6. 环境变量

- 根目录保留 `.env.example`；
- 真实 `.env` 不提交；
- 新增环境变量时同步更新 `.env.example` 和相关说明；
- Secret 不写入源码、测试、README、截图或 RESULT.md。

## 7. 数据库

- 表结构变更必须 migration；
- migration 要能在空库执行；
- 不允许直接操作生产数据库手工“补字段”替代 migration；
- 重要唯一约束/外键/索引必须在模型与迁移中一致；
- 迁移执行后一般不改历史 migration，使用新 migration 修复。

## 8. API

统一前缀：`/api/v1`。

推荐错误响应至少包含：

```json
{
  "code": "REVIEW_PENDING",
  "message": "存在待确认项目",
  "request_id": "...",
  "details": {}
}
```

前端逻辑依赖 `code`，不依赖中文 `message`。

## 9. 日志

记录：
- request_id；
- user_id（内部 ID）；
- ingestion_id / task_id / report_id；
- status；
- duration；
- error_code。

不记录：
- 完整报告图片；
- OCR 全文；
- 完整检验结果；
- Secret；
- 永久可访问文件 URL。

## 10. 测试分层

### OCR Regression
继续由独立 PoC 仓库承担算法准确率回归。

### 正式产品工程测试
重点测试：
- 权限隔离；
- 状态机；
- commit 事务和幂等；
- REVIEW 准入；
- 趋势规则；
- 删除/迁移后的数据一致性；
- 文件权限边界。

## 11. 测试数据

仓库内只能保存：
- 人工构造；
- 完全脱敏；
- 经明确许可用于测试的 fixtures。

真实家庭成员报告不得进入 Git 历史。

## 12. Codex 修改规则

- 修改前先读取当前阶段文档；
- 先说明当前任务涉及哪些目录/文件；
- 不因发现“代码可以更漂亮”而扩大重构；
- 如需新依赖，说明目的并更新锁文件；
- 如需改变长期架构，先记录冲突，不自行实施；
- 实施后执行当前 ACCEPTANCE 中要求的命令；
- 将实际结果写入 RESULT.md。

### Stage 文档分工

- `PLAN.md` = 详细设计与实施边界。
- `ACCEPTANCE.md` = 逐项验收与 PASS/FAIL 基线。
- `RESULT.md` = 实施事实，包括实际完成项、测试/验收结果、设计偏差和最终状态。
- Codex Prompt = 读取 + 执行 + 测试 + 汇报；保持精简，不重复 PLAN / ACCEPTANCE 中已冻结的大段需求。

每个 Stage 正式编码前必须完成：`边界确认 → PLAN 冻结 → ACCEPTANCE 冻结`。正式实施依据当前 PLAN / ACCEPTANCE，Prompt 冲突时以两者为准。发现文档与真实代码冲突，先分析、记录并报告；实际设计偏差写入 RESULT，不自行重新定义规则或扩大范围。完整 Stage 流程见 AGENTS.md 第 6.1 节。

## 13. 阶段完成定义

页面可打开并不等于完成。

完成 = 实现 + 权限 + 异常路径 + 测试 + 文档 + 当前验收全部通过。

ACCEPTANCE 中要求的项目负责人人工验收不能由自动测试、接口调用或构建成功替代。P0 条件未全部满足时不得标记 PASS；RESULT 必须如实记录已执行的验证、待验项和当前状态。
