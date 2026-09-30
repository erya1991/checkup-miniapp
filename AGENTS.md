# AGENTS.md｜检查单小程序工程长期规则

> 本文件是 Codex/AI 开发在本仓库中的第一入口。它保存长期稳定的工程原则，不保存某一阶段的全部实现细节。

## 1. 项目使命

「检查单小程序」是一款面向个人及家庭成员的长期检验报告管理工具。用户上传纸质检验报告或医院电子报告截图，经 OCR 结构化、人工安全确认后形成正式检验报告，并基于标准指标体系查看历史结果和趋势。

核心解决：
- 报告难整理；
- 指标难追踪；
- 历史趋势难查看。

本产品不是医院系统，也不是医疗诊断、疾病预测、AI 问诊或用药建议工具。

## 2. 开始任何任务前的读取顺序

执行任何阶段任务前必须按以下顺序读取：

1. 根目录 `AGENTS.md`；
2. `docs/00-baseline/PRODUCT_BASELINE.md`；
3. `docs/00-baseline/TECH_BASELINE.md`；
4. `docs/00-baseline/DEVELOPMENT_RULES.md`；
5. 当前阶段 `docs/stages/<stage>/PLAN.md`；
6. 当前阶段 `docs/stages/<stage>/ACCEPTANCE.md`；
7. 如存在前一阶段，读取前一阶段 `RESULT.md`；
8. 只有当任务涉及相应主题时，再读取 `docs/01-architecture/` 下的专题文档。

不要为了“更全面”而默认重读仓库全部 Markdown；按任务需要读取。

## 3. 不可破坏的产品与数据安全原则

1. OCR 完成后 **不得直接生成正式报告**。
2. 正确数据链必须是：`上传 → OCR → AUTO/REVIEW → 人工确认 → commit → 正式报告`。
3. `OcrResultItem` 是机器识别快照，**不可被人工修改覆盖**。
4. 用户修改的是 `ConfirmationItem`；最终 commit 后才生成 `LabReport` / `LabResult`。
5. 只有 `LabReport` / `LabResult` 属于正式健康历史数据；OCR 临时数据不得进入趋势。
6. `FINAL_REVIEW` 项全部处理为已解决后，才允许正式保存报告。
7. 无法匹配标准指标的项目允许“按原名称保存”，但不得进入跨报告标准指标聚合和趋势。
8. 原始报告图片、原始 OCR 结果和人工修改后的正式结果必须可追溯，互不覆盖。
9. 趋势时间使用检验日期/时间，不得使用上传时间或记录创建时间代替。
10. 同一天多次检测全部保留，不覆盖、不平均。
11. 不兼容单位不得直接画在同一趋势序列；V1.0 不进行任意跨单位数值换算。
12. 参考范围属于某一次具体检验结果，不是标准指标的全局固定属性。
13. 非数值结果允许保存和查看，但不得强行作为普通数值折线点。
14. 疑似重复报告只提示，不直接禁止用户保存。
15. 原始检验报告始终是最终核对依据。

## 4. 技术路线（V1.0 冻结）

- 小程序：uni-app + Vue 3 + TypeScript；
- 管理后台：Vue 3 + Vite + Element Plus + TypeScript；
- 后端：Python 3.12.10 + FastAPI；
- ORM：SQLAlchemy 2.x；
- 数据迁移：Alembic；
- 数据库：PostgreSQL 17；
- 原始文件：腾讯云 COS 私有桶；
- OCR：独立 Python Worker；
- OCR 任务队列：PostgreSQL 持久化任务队列；
- 部署：Docker Compose + Nginx；
- 正式服务器目标：4 CPU / 4 GB RAM / 40 GB SSD / 3 Mbps。

V1.0 默认不引入：
- Redis；
- Celery；
- RabbitMQ / Kafka；
- MongoDB；
- Elasticsearch；
- 微服务；
- Kubernetes；
- 复杂配置中心或算法在线配置中心。

如确有必要改变上述技术路线，必须先形成 `docs/decisions/` 决策记录，并由项目负责人明确确认，不得由 Codex 自行升级或替换架构。

## 5. OCR PoC 与正式产品仓库边界

现有 `checkup-ocr-poc` 继续作为 OCR 技术验证与 Regression 仓库。

正式产品仓库：
- 只接入已经经过 PoC / Regression 验证的 OCR Pipeline 能力；
- 不因业务功能开发随意修改 OCR 算法规则；
- OCR 算法调整应先在 PoC/Regression 中验证，再迁入正式产品；
- 产品工程测试重点是“正确消费 OCR 输出”，算法准确率回归仍由 PoC 仓库承担。

## 6. 阶段式开发规则

1. 只实现当前 `PLAN.md` 明确包含的范围。
2. `PLAN.md` 中“本阶段不做”属于硬边界，不得提前实现。
3. 未明确要求修改的模块，不做顺手重构、技术替换或目录大改。
4. 实现方案必须优先遵循 Product/Tech Baseline；如发生冲突，停止扩展并说明冲突，不得自行重新定义产品或架构。
5. 每个阶段必须以 `ACCEPTANCE.md` 为验收基线。
6. 不得通过删除、跳过或弱化测试来制造“通过”。
7. 阶段验收未通过，不得宣称阶段完成。
8. 阶段完成后必须更新同目录 `RESULT.md`。
9. `RESULT.md` 必须记录：实际完成项、测试/验收结果、设计偏差、已知问题、下一阶段注意事项。
10. 如引入新的长期工程约束，更新对应 baseline 或 decision 文档，而不是只写在聊天或 commit message 中。

### 6.1 Stage 文档职责与 Codex 执行原则

- `PLAN.md`：当前 Stage 的详细设计与实施边界。
- `ACCEPTANCE.md`：当前 Stage 的逐项验收与 PASS/FAIL 基线。
- `RESULT.md`：当前 Stage 的实际实施结果、测试/验收结果、设计偏差、已知问题和最终状态。
- Codex 实施 Prompt：读取 + 执行 + 测试 + 汇报，只负责执行编排。

Codex 必须遵守：

1. Prompt 保持精简，不大篇幅重复 PLAN / ACCEPTANCE 已冻结的详细业务规则；要求按规定顺序读取文档、检查真实代码和 Git status，完成实施、测试、RESULT 更新及事实汇报。
2. 正式实施以当前 Stage 的 PLAN / ACCEPTANCE 为主要实施基线；Prompt 与两者冲突时，以 PLAN / ACCEPTANCE 为准，不降低验收条件。
3. 真实代码与冻结文档冲突时，先分析、记录并报告冲突和实际设计偏差，不得擅自重新定义产品规则或扩大 Stage 范围。
4. 正式编码前必须完成边界确认、PLAN 冻结和 ACCEPTANCE 冻结；人工验收要求不能由自动测试替代，未满足 ACCEPTANCE 的 P0 条件不得标记 PASS。

新 Stage 固定流程：

```text
检查上一 Stage RESULT → 检查当前真实仓库 → 讨论并确认新 Stage 边界
→ 生成并冻结 PLAN.md → 生成并冻结 ACCEPTANCE.md → 生成精简 Codex 实施 Prompt
→ Codex 实施 → 自动测试 / 集成测试 → 项目负责人人工验收
→ 更新 RESULT.md → Stage PASS 后进入下一阶段
```

## 7. 数据、安全与隐私规则

- 不向 Git 提交任何真实用户医疗报告、真实 OCR 医疗数据或真实密钥。
- 测试样本必须使用脱敏数据或专门测试夹具。
- `.env`、密钥、数据库密码、微信 AppSecret、COS SecretKey 永不提交。
- 小程序/浏览器前端不得持有微信 AppSecret、COS SecretKey、数据库密码。
- COS 使用私有桶；查看原图应由后端鉴权后签发短时访问 URL。
- 所有 HealthProfile / Report / Metric / Asset 接口都必须校验当前用户的数据所有权。
- 日志不记录完整检验结果、OCR 全文、永久文件访问链接等敏感内容。

## 8. 数据库与迁移规则

- 数据库结构变更必须通过 Alembic migration，不允许只改 ORM 模型不生成迁移。
- 已应用的 migration 原则上不重写；新增修复 migration。
- 正式数据实体与 OCR 临时实体必须保持边界，禁止为了查询方便合并为一张“万能报告表”。
- 删除涉及 COS 文件时，不能只依赖数据库级联删除，必须明确处理文件清理任务。

## 9. API 与错误处理规则

- API 统一前缀：`/api/v1`。
- 业务错误使用稳定错误码，不依赖中文错误文本作为程序判断条件。
- 所有写操作校验资源所有权、当前状态和幂等性。
- `commit`、开始识别等关键接口必须防止重复点击产生重复业务数据。

## 10. 前端规则

- 小程序全局状态只保存真正全局的信息：登录身份、Token、当前健康档案等。
- 报告列表、指标列表等业务数据优先页面级获取，不构建过度复杂的全局 Store。
- 所有网络请求经过统一 request 层处理鉴权、错误码、登录失效。
- 页面至少处理 loading / success / empty / error；OCR 页面额外处理 processing。
- 优先保证上传、确认、原图核对、趋势可信；V1.0 不追求复杂动画和高级可视化。

## 11. 文档索引

遇到以下问题时优先读取：

- 产品范围/页面/业务规则：`docs/00-baseline/PRODUCT_BASELINE.md`
- 技术路线/模块边界/部署：`docs/00-baseline/TECH_BASELINE.md`
- 工程规范/测试/Git/配置：`docs/00-baseline/DEVELOPMENT_RULES.md`
- 本地环境/软件：`docs/00-baseline/ENVIRONMENT_SETUP.md`
- 术语：`docs/00-baseline/GLOSSARY.md`
- 总体架构：`docs/01-architecture/SYSTEM_ARCHITECTURE.md`
- 数据模型：`docs/01-architecture/DATA_MODEL.md`
- API：`docs/01-architecture/API_CONVENTIONS.md`
- OCR 接入：`docs/01-architecture/OCR_INTEGRATION.md`
- 当前研发任务：`docs/stages/<stage>/PLAN.md`
- 当前验收条件：`docs/stages/<stage>/ACCEPTANCE.md`
- 已完成阶段事实：`docs/stages/<stage>/RESULT.md`
- 长期架构决策：`docs/decisions/`

## 12. Definition of Done

任何研发阶段只有同时满足以下条件才算完成：

- 当前阶段 PLAN 范围全部完成；
- ACCEPTANCE 中 P0 验收项全部通过；
- 相关自动测试通过；
- 主流程手工验收通过；
- 未发现跨用户权限漏洞；
- 文档与实现一致；
- RESULT.md 已更新；
- 没有以“后续再补”为由跳过当前阶段明确要求的 P0 能力。
