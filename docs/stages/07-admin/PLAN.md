# Stage 07｜StandardMetric / MetricAlias 管理与 OCR 轻量管理能力

> 状态：**FROZEN / 待实施**
>
> 本文是 Stage 07 的详细设计与实施边界。  
> 本阶段实施必须遵循：
>
> ```text
> PLAN.md       = 详细设计与实施边界
> ACCEPTANCE.md = 验收基线
> RESULT.md     = 实施事实
> Codex Prompt  = 读取 + 执行 + 测试 + 汇报
> ```
>
> 本 PLAN 已在 Stage 06 = PASS、`main` 最新正式基线
> `b2b60f3854b66e5d04ad99568849f42e5844ce27`
> 的真实代码基础上冻结。

---

# 1. Stage 07 目标

Stage 07 建设正式产品侧的标准指标主数据管理、指标别名管理和轻量 OCR 排查能力，使系统从“Stage 04 固定 12 条 StandardMetric 种子”演进为“可由管理员持续维护的标准指标体系”。

本阶段核心目标：

```text
StandardMetric 可新增 / 编辑 / 停用 / 恢复
+
MetricAlias 正式落库并可管理
+
Stage 04 标准指标搜索支持 Alias
+
Alias 可在 Confirmation 首次初始化时参与安全的精确预关联
+
OCR 未匹配名称 / 产品主数据缺失 code 可进入轻量后台排查
+
管理员可从高频 OCR 问题创建 StandardMetric / MetricAlias
+
既往 OcrResultItem / ConfirmationItem / LabResult 不被重新解释
+
Stage 06 历史与趋势保持稳定
```

Stage 07 的重点不是提高 OCR 模糊匹配准确率，而是建设：

> **产品侧 StandardMetric 主数据 + Alias 映射 + OCR 问题反馈闭环。**

---

# 2. 当前正式基线

进入 Stage 07 时必须继续满足：

```text
Stage 00～06：全部 PASS
main HEAD：
b2b60f3854b66e5d04ad99568849f42e5844ce27
```

当前已交付：

- 微信登录；
- HealthProfile；
- 报告上传与 COS 私有原图；
- OCR PostgreSQL 持久化任务队列；
- 独立 OCR Worker；
- OcrResultItem 不可变机器快照；
- Stage 04 Confirmation 工作区；
- REVIEW 人工确认；
- StandardMetric 手工选择；
- KEEP_ORIGINAL_NAME；
- 手工补项 / 纯手工报告；
- commit 生成 LabReport / LabResult；
- 正式报告查看 / 迁移 / 删除；
- Stage 06 我的指标；
- StandardMetric 跨报告聚合；
- latest / history / trend；
- 同日多次检测；
- 非数值 / comparator 安全处理；
- 多单位独立趋势；
- MetricFavorite；
- HealthProfile 隔离。

Stage 07 不得破坏上述任何既有能力。

---

# 3. 当前真实代码事实

Stage 07 实施必须以真实代码为准，不得依据旧设计文档假设代码已存在。

当前确认事实：

## 3.1 StandardMetric

当前模型：

```text
StandardMetric
- id
- code
- name
- status
- created_at
- updated_at
```

Stage 04 当前正式 seed：

```text
ALT
AST
TP
ALB
TBIL
DBIL
WBC
RBC
HGB
PLT
GLU
CREA
```

共 12 项。

当前尚未实现：

```text
MetricAlias
StandardMetric 管理 API
StandardMetric 管理 Admin UI
Alias 管理 API
Alias 管理 Admin UI
OCR 指标问题管理
```

## 3.2 PoC OCR 指标库

正式仓库内冻结 runtime：

```text
backend/ocr_runtime/data/metric_library.json
```

当前包含约 74 个 OCR 指标身份。

OCR library 与产品 StandardMetric 当前不是同一份主数据。

OCR matcher 当前输出：

```text
metricId
standardName
matchType
score
...
```

产品通过：

```text
OcrResultItem.standard_metric_code
```

与：

```text
StandardMetric.code
```

进行后续产品映射。

## 3.3 Stage 04 当前映射逻辑

当前 Confirmation 首次初始化时：

```text
ACTIVE StandardMetric
→ 建立 code → id 映射
→ OcrResultItem.standard_metric_code
→ ConfirmationItem.standard_metric_id
```

不存在 Alias 查询。

如果 OCR 已识别出 code，但产品 StandardMetric 不存在：

```text
ConfirmationItem.standard_metric_id = NULL
```

## 3.4 Stage 06 当前消费逻辑

Stage 06 只消费正式：

```text
LabResult.standard_metric_id
```

且：

```text
standard_metric_id = NULL
```

的正式结果不会进入：

- 我的指标；
- StandardMetric history；
- trend；
- Favorite。

Stage 06 不使用：

- metric_name 模糊匹配；
- Alias 猜测；
- OCR code 猜测；
- OCR 临时结果。

## 3.5 Admin Web

当前 Admin Web 仅是骨架：

```text
Vue 3
Vite
Element Plus
TypeScript
Vue Router
```

当前没有：

- Admin 登录；
- Admin Token；
- API request 封装；
- StandardMetric 页面；
- OCR 排查页面。

---

# 4. Stage 07 一句话职责

> Stage 07 负责正式产品侧标准指标主数据、指标别名、未来 Confirmation 精确预关联和轻量 OCR 问题排查；不负责重新设计 OCR 算法，也不负责重新解释既往正式医疗数据。

---

# 5. 核心安全原则

Stage 07 必须继续遵守整个产品的安全数据链：

```text
上传
→ OCR
→ OcrResultItem
→ ConfirmationItem
→ 人工确认
→ commit
→ LabReport / LabResult
→ Stage 06 history / trend
```

任何 Stage 07 功能都不得绕过：

```text
OCR → Confirmation → commit
```

直接修改正式历史。

特别禁止：

```text
MetricAlias
→ 自动批量 UPDATE LabResult.standard_metric_id
```

以及：

```text
StandardMetric 修改
→ 自动改写既往 OcrResultItem / ConfirmationItem / LabResult
```

---

# 6. Stage 07 功能范围

本阶段包含：

## 6.1 StandardMetric 管理

支持：

- 列表；
- 搜索；
- 新增；
- 编辑名称；
- 编辑轻量分类；
- 停用；
- 恢复；
- 查看使用情况摘要；
- 查看关联 Alias。

不支持：

- 物理删除；
- 修改 code；
- StandardMetric 合并；
- StandardMetric 拆分；
- 历史 LabResult 重关联。

## 6.2 MetricAlias 管理

支持：

- Alias 新增；
- Alias 编辑；
- Alias 停用；
- Alias 恢复；
- 按 StandardMetric 查看 Alias；
- Alias 全局搜索；
- 唯一性与冲突检查。

## 6.3 Stage 04 标准指标搜索增强

原：

```text
code
name
```

扩展为：

```text
code
name
MetricAlias.alias
```

最终返回仍然是：

```text
StandardMetric
```

Alias 不作为可保存业务身份。

## 6.4 Product Exact Metric Resolver

在 Confirmation 首次初始化时增加产品侧确定性映射。

允许：

```text
OCR code exact
StandardMetric code/name exact
MetricAlias exact
```

禁止：

```text
模糊匹配
相似度评分
医学推断
单位推断
OCR threshold
AUTO/REVIEW 改判
```

## 6.5 OCR 待处理指标名称

Admin 提供轻量问题列表，帮助发现：

- OCR 未匹配名称；
- OCR 已识别 code 但产品 StandardMetric 缺失；
- OCR code 对应产品 StandardMetric 已停用。

## 6.6 OCR Task 轻量只读页

允许管理员查看：

- OcrTask id；
- ingestion id；
- run_no；
- status；
- pipeline_version；
- attempt_count；
- created / started / finished 时间；
- last_error_code；
- result_summary。

本阶段只用于工程排查。

---

# 7. 本阶段明确不做

Stage 07 不实现：

```text
修改 OCR matcher
修改 OCR threshold
修改 fuzzy score
修改 unit scoring
修改 Retry 规则
修改 FINAL_AUTO / FINAL_REVIEW 判定
动态把数据库 Alias 注入 PoC matcher
在线 OCR 算法参数配置
OCR 模型管理
OCR 模型切换
OCR Pipeline 在线发布
```

同时不实现：

```text
历史 LabResult 批量重关联
正式 LabResult 编辑
正式 LabResult 合并
历史报告重新 OCR
历史报告重新 commit
StandardMetric merge
复杂主数据版本系统
复杂 MetricCategory 数据模型
参考范围主数据
单位换算规则后台
复杂 RBAC
多管理员组织体系
完整 OCR 原图诊断台
全项目 UI 重构
```

---

# 8. StandardMetric 数据模型

Stage 07 在现有 StandardMetric 基础上扩展：

```text
StandardMetric
- id
- code
- name
- category          ← Stage 07 新增，可空
- status
- created_at
- updated_at
```

## 8.1 code

规则：

```text
创建时允许填写
创建成功后永久只读
```

code：

- 必填；
- 去首尾空格；
- 建议统一大写；
- 最大长度继续遵守现有数据库限制；
- 全局唯一；
- 创建后不允许 PATCH 修改。

原因：

```text
PoC metricId
→ OcrResultItem.standard_metric_code
→ StandardMetric.code
```

已构成稳定接口身份。

code 不属于普通展示文案。

## 8.2 name

允许：

```text
编辑
```

name 表示当前产品侧 canonical display name。

名称修改：

```text
不修改 LabResult.metric_name
不修改 OcrResultItem.standard_metric_name
不修改 ConfirmationItem.metric_name
```

## 8.3 category

Stage 07 使用轻量字符串分类。

示例：

```text
血常规
肝功能
肾功能
血脂
血糖
电解质
心肌标志物
肿瘤标志物
甲状腺功能
其他
```

category：

- 可空；
- 管理后台可编辑；
- 不建设独立 MetricCategory 表；
- 不建设分类多级树；
- 不建设多对多分类。

Stage 07 的业务逻辑不得依赖 category 才能正确运行。

## 8.4 status

允许：

```text
ACTIVE
INACTIVE
```

Stage 07 不引入复杂状态机。

ACTIVE：

- 可作为未来手工选择目标；
- 可作为 Alias 目标；
- 可用于 Product Exact Resolver；
- 可创建新 Alias。

INACTIVE：

- 不再用于未来自动预关联；
- 不再用于新的手工标准指标选择；
- 不再允许创建 ACTIVE Alias；
- 既往历史继续存在。

---

# 9. StandardMetric 删除规则

Stage 07 不提供：

```text
DELETE StandardMetric
```

即使当前尚未被 LabResult 使用，也不物理删除。

原因：

- code 是稳定接口身份；
- 未来可能已存在 OCR 快照引用；
- 避免后台误删造成历史语义变化；
- 停用已足以满足维护需求。

错误 StandardMetric 的处理方式：

```text
停用错误 StandardMetric
+
创建新的正确 StandardMetric
```

---

# 10. StandardMetric 停用规则

## 10.1 正式 LabResult 引用

正式 LabResult 已经引用该指标时：

```text
允许停用
```

停用后：

- LabResult 保持不变；
- Stage 06 指标仍然显示；
- latest 继续存在；
- history 继续存在；
- trend 继续存在；
- Favorite 继续保留。

`INACTIVE` 不代表既往正式医疗结果失效。

## 10.2 未完成 Confirmation 引用

如果仍存在：

```text
ReportIngestion.status = PENDING_CONFIRMATION
+
ConfirmationItem.standard_metric_id = 当前 StandardMetric.id
```

则：

```text
禁止停用
```

返回稳定错误，例如：

```text
STANDARD_METRIC_IN_USE_BY_PENDING_CONFIRMATION
```

并提供最小引用数量。

原因：

当前 Stage 04 commit 会再次校验 StandardMetric 必须 ACTIVE。

如果允许管理员在用户待确认过程中直接停用，会导致既有工作区无法 commit。

## 10.3 已 CONFIRMED 的 ConfirmationItem

已经产生正式报告的 ConfirmationItem 不阻止停用。

判断核心应以：

```text
未完成 ReportIngestion
```

为边界，而不是简单判断数据库是否存在 ConfirmationItem。

---

# 11. MetricAlias 数据模型

Stage 07 新增：

```text
MetricAlias
- id
- standard_metric_id
- alias
- normalized_alias
- alias_type
- status
- created_at
- updated_at
```

关系：

```text
StandardMetric 1 ─ N MetricAlias
```

Alias 不允许：

```text
Alias → Alias
Alias → 多个 StandardMetric
Alias 层级
Alias 链式解析
```

---

# 12. alias_type

Stage 07 支持轻量类型：

```text
SYNONYM
ABBREVIATION
OCR_VARIANT
HOSPITAL_NAME
```

含义：

### SYNONYM

常见中文同义名称。

### ABBREVIATION

常见英文名称 / 缩写。

### OCR_VARIANT

OCR 经常出现的可确认变体。

### HOSPITAL_NAME

特定医院常见检验项目名称。

alias_type：

- 只用于管理；
- 不参与匹配优先级；
- 不参与评分；
- 不改变 AUTO / REVIEW；
- 不产生医学推断。

---

# 13. Alias normalization

Stage 07 必须使用确定性 normalization。

建议与当前冻结 OCR matcher 的名称标准化保持兼容语义：

```text
Unicode NFKC
→ strip
→ 去前导 * / ＊
→ Γ / ɣ 统一为 γ
→ casefold / 大小写统一
→ 移除匹配用途的空格和简单分隔符
```

至少考虑：

```text
空白
-
_
.
/
·
中文 / 英文括号
[]
【】
```

Normalization：

```text
只用于唯一性检查和 exact lookup
```

不得覆盖用户输入的原始 alias。

数据库同时保存：

```text
alias
normalized_alias
```

---

# 14. Alias 唯一性规则

核心规则：

> ACTIVE MetricAlias 的 normalized_alias 必须全局唯一。

不采用：

```text
standard_metric_id + normalized_alias
```

作为唯一身份。

因为同一个归一化名称不能同时指向两个 StandardMetric。

例如禁止：

```text
谷丙转氨酶 → ALT
谷丙转氨酶 → XYZ
```

同时还必须做 namespace 冲突检查。

新增 / 启用 Alias 时：

```text
normalized_alias
```

不得与以下 ACTIVE 主数据发生冲突：

```text
其它 ACTIVE MetricAlias.normalized_alias
其它 ACTIVE StandardMetric.code normalized
其它 ACTIVE StandardMetric.name normalized
```

与自身 StandardMetric 的 code/name 重复也拒绝，因为属于无意义 Alias。

稳定错误可包括：

```text
METRIC_ALIAS_CONFLICT
METRIC_ALIAS_DUPLICATE
```

---

# 15. Alias 状态

支持：

```text
ACTIVE
INACTIVE
```

Stage 07 不提供 Alias 物理删除。

INACTIVE Alias：

- 不参与 Product Exact Resolver；
- 不参与 Stage 04 标准指标搜索；
- 仍保留管理审计信息。

恢复 ACTIVE 时必须重新执行冲突检查。

---

# 16. Alias 与历史数据的边界

Alias 新增、编辑、停用、恢复：

**不得修改：**

```text
OcrResultItem
ConfirmationItem（已经初始化）
LabResult
LabReport
MetricFavorite
```

尤其禁止任何类似：

```sql
UPDATE lab_results
SET standard_metric_id = :metric_id
WHERE normalized(metric_name) = :alias
```

Stage 07 不建设历史数据重解释能力。

---

# 17. Product Exact Metric Resolver

Stage 07 增加一个产品业务侧 resolver。

该 resolver：

```text
不是 OCR matcher
不是 AI
不是 fuzzy matching
```

只进行产品侧确定性 identity resolution。

## 17.1 调用时点

仅在：

```text
Confirmation workspace 第一次初始化
```

时调用。

已经存在 ConfirmationItem 时：

```text
不得重新运行并覆盖
```

## 17.2 解析优先级

建议冻结为：

```text
1. OcrResultItem.standard_metric_code
   → ACTIVE StandardMetric.code exact

2. 如果 1 未命中：
   raw_metric normalized
   → ACTIVE StandardMetric.name / code exact

3. 如果仍未命中：
   raw_metric normalized
   → ACTIVE MetricAlias.normalized_alias exact

4. 未命中：
   standard_metric_id = NULL
```

其中：

```text
OCR code exact
```

优先级最高。

不得在 OCR 已给出有效 code 的情况下，再通过 Alias 静默替换到另一个 StandardMetric。

---

# 18. Alias 对 AUTO / REVIEW 的影响

Alias 不能改变 OCR 安全判定。

因此：

```text
OcrResultItem.final_decision
```

仍完全由冻结 OCR Pipeline 决定。

如果原项目是：

```text
FINAL_REVIEW
```

即使 Alias 精确命中：

```text
ConfirmationItem.standard_metric_id
```

可以预填，但：

```text
review_status = PENDING
resolution = NULL
```

用户仍需人工处理。

Alias 不允许：

```text
REVIEW → AUTO
PENDING → RESOLVED
```

## 18.1 FINAL_AUTO 边界

如果现有 OCR：

```text
FINAL_AUTO
+
standard_metric_code 可以映射 ACTIVE StandardMetric
```

继续按现有 Stage 04 行为处理。

Stage 07 不使用 Alias 去“挽救”一个没有可靠 OCR identity 的 FINAL_AUTO 项后自动 RESOLVED。

如遇真实 OCR 输出出现：

```text
FINAL_AUTO
+
standard_metric_code = NULL
```

Stage 07 不通过 Alias 自动变成安全 AUTO。

此类异常必须继续遵循现有确认安全规则或作为实现期需核查的 Pipeline 契约问题。

---

# 19. Alias 生效时间

Alias 生效边界不是“下一次 OCR run”，而是：

> 下一次 Confirmation workspace 首次初始化。

因此：

### 场景 A

```text
OCR 已完成
ConfirmationItem 尚未初始化
管理员新增 Alias
用户第一次进入确认页
```

允许 Alias 参与本次首次初始化。

### 场景 B

```text
ConfirmationItem 已初始化
管理员新增 Alias
```

原工作区：

```text
不自动变化
```

### 场景 C

```text
报告已经 commit
```

LabResult：

```text
永不因 Alias 自动改变
```

---

# 20. Stage 04 StandardMetric 搜索增强

当前：

```text
GET /api/v1/standard-metrics?q=
```

Stage 07 保持兼容路径。

搜索范围改为：

```text
ACTIVE StandardMetric.code
ACTIVE StandardMetric.name
ACTIVE MetricAlias.alias
```

最终响应仍为：

```text
StandardMetric
```

例如用户搜索：

```text
谷丙转氨酶
```

Alias 命中后返回：

```text
丙氨酸氨基转移酶（ALT）
```

不返回：

```text
MetricAlias
```

作为最终业务 identity。

同一 StandardMetric 被多个 Alias 命中时：

```text
结果去重
```

---

# 21. StandardMetric 名称修改后的展示规则

Stage 07 必须冻结两层展示语义。

## 21.1 Stage 06 我的指标

Stage 06：

```text
StandardMetric.name
StandardMetric.code
```

表示当前统一身份。

因此 StandardMetric.name 修改后：

```text
我的指标列表
指标详情
history 顶部 identity
trend identity
```

显示当前最新 StandardMetric.name。

聚合 identity 仍然使用：

```text
StandardMetric.id
```

不得因为 name 修改拆成新指标。

## 21.2 既往正式报告

正式报告中的主项目名称：

```text
LabResult.metric_name
```

属于当时 commit 后的正式数据快照。

不得随 StandardMetric.name 修改。

因此报告详情：

```text
主名称：
LabResult.metric_name

标准指标辅助信息：
当前 StandardMetric.name + code
```

可分别体现：

```text
当时正式报告事实
+
当前产品统一身份
```

---

# 22. StandardMetric 停用后的 Stage 06 规则

Stage 06 当前设计已经满足：

```text
StandardMetric.status
```

不是历史可见性的必要条件。

Stage 07 必须保持：

```text
INACTIVE StandardMetric
+
已有 LabResult
```

仍然进入：

- 我的指标；
- latest；
- history；
- trend；
- Favorite。

不得：

```text
WHERE StandardMetric.status = ACTIVE
```

过滤历史查询。

普通用户侧无需增加“已停用”警告。

INACTIVE 是后台主数据维护状态，不表示历史检测数据错误。

---

# 23. OCR 待处理指标名称

Admin 新增：

```text
OCR 指标问题
```

用于发现产品侧主数据缺口。

至少分为三个问题类型。

---

# 24. OCR Issue Type A｜UNMATCHED_NAME

条件建议：

```text
OcrResultItem.raw_metric 非空
+
standard_metric_code IS NULL
```

按产品 normalization 后的名称聚合。

展示：

```text
representative_name
normalized_name
occurrence_count
ingestion_count
latest_seen_at
sample_names
```

sample_names：

- 只返回少量不同原始名称示例；
- 不返回结果值；
- 不返回完整医疗报告。

支持操作：

```text
创建 Alias
```

管理员选择目标 ACTIVE StandardMetric。

---

# 25. OCR Issue Type B｜PRODUCT_METRIC_MISSING

条件：

```text
OcrResultItem.standard_metric_code IS NOT NULL
+
当前不存在 ACTIVE StandardMetric.code
```

例如：

```text
OCR code = GLOB
OCR standard name = 球蛋白
```

但产品 StandardMetric 不存在。

Admin 显示：

```text
ocr_code
ocr_standard_name
occurrence_count
ingestion_count
latest_seen_at
```

支持：

```text
创建 StandardMetric
```

创建弹窗预填：

```text
code = ocr_code
name = ocr_standard_name
```

管理员确认后真正创建。

不得：

```text
自动导入全部 74 项 PoC library
```

---

# 26. OCR Issue Type C｜PRODUCT_METRIC_INACTIVE

条件：

```text
OcrResultItem.standard_metric_code
→ 对应 StandardMetric 存在
→ status = INACTIVE
```

该问题只用于提醒管理员：

```text
未来此 OCR code 不会再自动进入产品标准指标关联
```

允许后台：

```text
查看
恢复 StandardMetric
```

不允许：

```text
自动改到另一个 StandardMetric
```

---

# 27. OCR Issue 统计范围

不得简单统计所有历史 OcrTask。

因为 Stage 03 retry：

```text
新建 OcrTask
不覆盖旧 run
```

同一 ingestion 可能存在多个成功 run。

Stage 07 OCR metric issue 聚合默认只使用：

> 每个 ReportIngestion 的最新成功 OcrTask。

选择逻辑：

```text
status = SUCCEEDED
→ run_no 最大
```

或等价稳定实现。

避免：

```text
一次报告 retry 三次
→ 同一名称被统计三遍
```

---

# 28. 已被 Alias 覆盖的历史 OCR 未匹配名称

OcrResultItem 必须保持不可变。

因此新增 Alias 后：

```text
历史 OcrResultItem.standard_metric_code
```

仍然不会被改写。

OCR issue 查询层可以判断：

```text
normalized raw_metric
→ 当前 ACTIVE Alias 已覆盖
```

默认不再作为“待处理 UNMATCHED_NAME”显示。

允许后台可选展示：

```text
已解决 / 已覆盖
```

但本阶段 P0 不要求建设复杂 issue 状态表。

即：

```text
issue 状态可以由当前主数据实时计算
```

不新增：

```text
OcrMetricIssue
```

冗余业务表。

---

# 29. 是否需要独立 OCR Issue 表

Stage 07 默认：

```text
不建立独立 OcrMetricIssue 表
```

待处理列表实时基于：

```text
OcrTask
OcrResultItem
StandardMetric
MetricAlias
```

聚合查询。

理由：

- 当前数据规模小；
- issue 本质是主数据覆盖缺口；
- Alias / StandardMetric 创建后可自然变化；
- 避免 issue 与真实 OCR 快照失同步。

如实施验证发现查询明显无法满足当前规模，再单独提出，不得自行增加复杂缓存 / 汇总体系。

---

# 30. OCR Task Admin

Admin 提供轻量只读列表。

字段建议：

```text
task_id
ingestion_id
run_no
status
pipeline_version
attempt_count
created_at
started_at
finished_at
last_error_code
result_summary.total_count
result_summary.auto_count
result_summary.review_count
```

允许筛选：

```text
status
pipeline_version
```

可选：

```text
时间范围
```

不提供：

```text
重跑
强制成功
改状态
改 attempt
改 lease
改 worker
改 OcrResultItem
```

---

# 31. OCR Task 医疗数据隐私

Admin OCR Task 页面默认不展示：

```text
完整 raw OCR
完整 result_text
完整 reference
完整报告结果
COS object key
永久 COS URL
```

Stage 07 的 OCR 排查重点是：

```text
任务状态
pipeline version
错误码
metric identity coverage
```

不是完整医疗数据人工审核。

---

# 32. Admin 身份模型

Stage 07 采用：

> 单管理员 + 独立 Admin 身份 + 独立 admin-scoped JWT。

本阶段不建设：

```text
AdminUser 表
Role
Permission
MenuPermission
Organization
复杂 RBAC
多管理员审计
```

管理员凭据来自安全环境配置。

具体环境变量名称实施时可按现有配置风格定义，例如：

```text
ADMIN_USERNAME
ADMIN_PASSWORD_HASH
ADMIN_JWT_SECRET
```

不得把明文密码提交 Git。

如果采用单独 ADMIN_JWT_SECRET：

- 长度要求应满足现有 Token 安全规则；
- 不与微信用户 JWT 混用。

---

# 33. Admin Token 安全边界

Admin Token：

```text
只能访问 /api/v1/admin/*
```

普通用户 Token：

```text
不能访问 /api/v1/admin/*
```

Admin Token 也不能作为普通用户 Token 调用：

```text
/health-profiles
/reports
/profile-metrics
```

不得通过管理员身份绕过 HealthProfile 所有权体系直接操作普通用户正式医疗数据。

---

# 34. Admin API 路径

统一：

```text
/api/v1/admin/*
```

建议 API：

```text
POST /api/v1/admin/auth/login
GET  /api/v1/admin/me
```

StandardMetric：

```text
GET   /api/v1/admin/standard-metrics
POST  /api/v1/admin/standard-metrics
GET   /api/v1/admin/standard-metrics/{id}
PATCH /api/v1/admin/standard-metrics/{id}
```

MetricAlias：

```text
GET   /api/v1/admin/metric-aliases
POST  /api/v1/admin/metric-aliases
PATCH /api/v1/admin/metric-aliases/{id}
```

或：

```text
GET /api/v1/admin/standard-metrics/{id}/aliases
```

具体资源路径可以实施时小幅调整，但必须保持：

- `/api/v1/admin` 独立；
- 稳定错误码；
- 不提供 delete。

OCR：

```text
GET /api/v1/admin/ocr-metric-issues
GET /api/v1/admin/ocr-tasks
```

---

# 35. StandardMetric Admin API

## 35.1 列表

至少支持：

```text
q
status
category
page
page_size
```

返回至少：

```text
id
code
name
category
status
alias_count
formal_result_count
pending_confirmation_count
created_at
updated_at
```

计数可以按当前规模实时查询，不要求新增冗余统计字段。

## 35.2 新增

输入：

```text
code
name
category
```

默认：

```text
status = ACTIVE
```

创建时检查：

- code 唯一；
- code/name 与 ACTIVE Alias namespace 冲突；
- name 非空；
- code 非空。

## 35.3 编辑

允许 PATCH：

```text
name
category
status
```

禁止：

```text
code
```

如果请求包含 code：

```text
拒绝
```

不得静默忽略。

---

# 36. MetricAlias Admin API

## 36.1 新增

输入：

```text
standard_metric_id
alias
alias_type
```

默认：

```text
status = ACTIVE
```

目标 StandardMetric 必须：

```text
存在
+
ACTIVE
```

## 36.2 编辑

允许：

```text
alias
alias_type
status
standard_metric_id
```

其中如果允许修改 `standard_metric_id`，必须按一次完整重新绑定处理：

- 新目标必须 ACTIVE；
- 重新 normalization；
- 重新冲突检查；
- 不修改历史数据。

也可以在实施时选择更保守设计：

```text
standard_metric_id 创建后只读
```

本 PLAN 推荐：

> `standard_metric_id` 创建后只读。

如果映射错误：

```text
停用旧 Alias
+
新建正确 Alias
```

与 StandardMetric code 稳定原则保持一致。

---

# 37. Admin Web 页面

Stage 07 Admin Web 以功能可用为主。

至少提供：

```text
登录
首页 / 导航
StandardMetric 列表
StandardMetric 新增 / 编辑
StandardMetric 详情 + Alias
OCR 指标问题
OCR Task
```

## 37.1 StandardMetric 列表

展示：

```text
code
name
category
status
Alias 数量
正式结果引用数量
待确认引用数量
更新时间
```

操作：

```text
新增
编辑
停用
恢复
查看 Alias
```

## 37.2 StandardMetric 详情

展示：

```text
基本信息
Alias 列表
引用统计
```

Alias 操作：

```text
新增
编辑
停用
恢复
```

## 37.3 OCR 指标问题

至少两个主要 Tab：

```text
未匹配名称
产品主数据缺失 code
```

可额外：

```text
已停用 code
```

支持：

```text
从未匹配名称创建 Alias
从缺失 code 创建 StandardMetric
```

## 37.4 OCR Task

只读表格。

---

# 38. Admin Web UI 原则

本阶段不进行：

- 大规模视觉重构；
- 完整 Design System；
- 高级表格组件抽象；
- 动效体系；
- 大量响应式适配；
- 复杂 dashboard。

必须保证：

```text
可登录
可导航
可搜索
可新增
可编辑
可停用 / 恢复
错误反馈清楚
loading / empty / error 可用
```

---

# 39. Migration

当前 migration HEAD：

```text
0006_metric_trend
```

Stage 07 新增：

```text
0007_standard_metric_admin
```

名称可略有不同，但必须是新 migration。

## 39.1 Migration 内容

预计包含：

```text
standard_metrics.category
metric_aliases
必要唯一约束
必要索引
```

不得重写：

```text
0001～0006
```

---

# 40. MetricAlias 数据库约束

建议：

```text
id PRIMARY KEY
standard_metric_id FK
alias NOT NULL
normalized_alias NOT NULL
alias_type NOT NULL
status NOT NULL
created_at NOT NULL
updated_at NOT NULL
```

建议索引：

```text
standard_metric_id
status
normalized_alias
```

ACTIVE-only 唯一性如使用 PostgreSQL partial unique index：

```text
UNIQUE(normalized_alias)
WHERE status = 'ACTIVE'
```

如果 SQLite 单元测试兼容导致 partial index 行为复杂，可以选择业务层 + PostgreSQL 真实集成验证保证，但最终 PostgreSQL 必须具备可靠并发安全约束。

优先保证：

> 两个并发请求不能创建两个 ACTIVE 同 normalized_alias。

---

# 41. StandardMetric namespace 冲突

StandardMetric 新增 / 修改 name / 恢复 ACTIVE 时，也应检查：

```text
normalized code
normalized name
```

是否与 ACTIVE MetricAlias 冲突。

Stage 07 应建立一个统一的 identity conflict service，而不是 Admin API、Confirmation resolver、Alias API 各写一套不同 normalization。

---

# 42. 事务与并发

主数据写操作必须事务化。

至少考虑：

```text
并发创建相同 code
并发创建相同 normalized Alias
Alias 创建与 StandardMetric rename 并发
StandardMetric 停用与用户 Confirmation commit 并发
```

尤其 StandardMetric 停用：

需要在数据库事务中确保：

```text
检查 pending Confirmation 引用
+
修改 status
```

之间不会出现明显竞态导致新 commit 被异常阻断。

当前规模不要求设计复杂全局锁，但实现必须基于 PostgreSQL 正确处理。

---

# 43. StandardMetric 停用与 Confirmation 并发策略

推荐：

```text
停用 StandardMetric 时锁定 StandardMetric 行
→ 检查 PENDING_CONFIRMATION 引用
→ 无引用再设 INACTIVE
```

Confirmation 继续沿用：

```text
active_metric()
```

最终 commit 前再次校验 ACTIVE。

如果极端并发下：

```text
管理员刚停用
+
用户同时 commit
```

允许其中一个事务先完成，另一个得到稳定错误。

不得：

```text
为了避免并发
→ commit 时忽略 status
```

---

# 44. Stage 04 Confirmation 初始化修改边界

Stage 07 允许修改：

```text
backend/app/confirmation.py
```

但仅限：

```text
Product Exact Metric Resolver
```

相关最小变更。

不得：

- 重构整个 confirmation；
- 改 REVIEW 规则；
- 改 commit 准入；
- 改 duplicate_check；
- 改 Result parsing；
- 改 manual item；
- 改 OcrResultItem 不可变边界。

---

# 45. OcrResultItem 不可变

Stage 07 必须继续保证：

```text
Admin
Alias
StandardMetric
OCR issue
```

均不能 UPDATE / DELETE OcrResultItem。

以下字段全部继续作为机器快照：

```text
raw_metric
raw_result
raw_unit
raw_reference
standard_metric_code
standard_metric_name
result_text
result_numeric
...
final_decision
evidence
payload
```

---

# 46. 历史 ConfirmationItem 不重算

已经初始化：

```text
ConfirmationItem
```

Stage 07 不批量重算。

即使：

```text
Alias 新增
StandardMetric 新增
StandardMetric rename
```

都不自动修改既有 ConfirmationItem。

如果用户已经进入确认页但尚未 commit：

```text
原工作区保持稳定
```

用户仍可通过 Stage 04 手工选择新的 StandardMetric。

---

# 47. 历史 LabResult 不回填

Stage 07 migration 和实现都不得：

```text
批量 UPDATE lab_results.standard_metric_id
```

既有：

```text
standard_metric_id = NULL
```

继续保持 NULL。

既有：

```text
standard_metric_id != NULL
```

继续保持原 ID。

即使新增 Alias 能精确命中历史 `metric_name`，也不自动回填。

---

# 48. StandardMetric Seed 扩充边界

Stage 07 不在 migration 中自动导入全部 PoC 74 项。

Stage 04 的 12 项 seed：

```text
保留
```

后续扩充：

```text
通过 Admin StandardMetric 管理
```

OCR issue 中的：

```text
PRODUCT_METRIC_MISSING
```

提供主数据补充入口。

这样产品主数据增长是：

```text
真实 OCR 使用反馈
→ 管理员确认
→ StandardMetric
```

而不是：

```text
PoC library 全量复制
```

---

# 49. PoC OCR matcher 职责边界

当前：

```text
backend/ocr_runtime/src/metric_matcher.py
backend/ocr_runtime/src/paper_metric_matcher.py
backend/ocr_runtime/data/metric_library.json
```

继续属于冻结 OCR runtime。

Stage 07 不修改：

```text
AUTO_THRESHOLD
REVIEW_THRESHOLD
MIN_MARGIN
exact_match
fuzzy_match
unit scoring
short name guard
topCandidates
```

也不修改：

```text
PIPELINE_VERSION
```

---

# 50. Product Alias 与 PoC Alias 的关系

PoC library 当前已有：

```text
aliases
abbreviation
categories
```

Stage 07 MetricAlias 是：

> 产品主数据。

二者不是同一存储。

Stage 07 不进行：

```text
数据库 MetricAlias
→ 实时写入 metric_library.json
```

也不进行：

```text
PoC metric_library aliases
→ migration 批量写入 MetricAlias
```

后续 OCR 算法优化流程：

```text
产品后台发现高频问题
→ 人工确认
→ PoC 仓库调整 metric library / matcher
→ Regression
→ 新 Pipeline version
→ 再迁入产品 runtime
```

---

# 51. OCR 算法优化后续阶段边界

Stage 07 只积累：

```text
高频未匹配名称
缺失产品 StandardMetric code
已停用 code
任务失败情况
```

不负责把这些问题自动变成算法规则。

真正算法优化必须继续遵守：

```text
checkup-ocr-poc
→ Regression
→ 安全验证
→ 明确版本迁入 checkup-miniapp
```

---

# 52. Stage 07 与 Stage 06 的兼容

必须验证：

## 52.1 StandardMetric rename

```text
Stage 06
→ 自动显示新 name
→ 聚合 ID 不变
→ history 数量不变
→ trend 不变
```

## 52.2 StandardMetric INACTIVE

```text
Stage 06
→ 仍显示历史
→ latest 不消失
→ history 不消失
→ trend 不消失
→ Favorite 不删除
```

## 52.3 新建 StandardMetric

如果没有任何正式 LabResult：

```text
不出现在“我的指标”
```

符合 Stage 06：

```text
我的指标 != StandardMetric 字典
```

## 52.4 新建 Alias

```text
既有 Stage 06 数据完全不变
```

---

# 53. Stage 07 与 Stage 05 的兼容

正式报告详情：

```text
LabResult.metric_name
```

继续作为主显示项目名称。

StandardMetric rename：

```text
不修改 LabResult.metric_name
```

StandardMetric stop：

```text
不影响正式报告查看
```

Stage 07 不允许修改：

- 报告迁移；
- 报告删除；
- FileCleanup；
- 原图 preview；
- 正式报告权限模型。

---

# 54. Stage 07 与 Stage 04 的兼容

必须继续保证：

```text
REVIEW_PENDING
KEEP_ORIGINAL_NAME
STANDARD_METRIC_SELECTED
AUTO 主动修改
手工补项
纯手工报告
commit 幂等
duplicate check
OcrResultItem 不可变
```

Alias 只增强：

```text
标准指标搜索
首次 workspace 标准指标预关联
```

---

# 55. KEEP_ORIGINAL_NAME

Alias 不影响 KEEP_ORIGINAL_NAME 的产品意义。

用户仍可明确选择：

```text
按原名称保存
```

则：

```text
ConfirmationItem.standard_metric_id = NULL
```

最终：

```text
LabResult.standard_metric_id = NULL
```

即使当前已经存在能命中的 Alias：

```text
用户显式 KEEP_ORIGINAL_NAME
```

优先。

不得在 commit 时重新通过 Alias 绑定。

---

# 56. 手工报告 / 手工补项

手工新增 ConfirmationItem：

仍然可以：

```text
选择 StandardMetric
或
standard_metric_id = NULL
```

Stage 07 StandardMetric 搜索支持 Alias 后：

```text
手工录入时也可以通过 Alias 搜索找到 canonical StandardMetric
```

但 Alias 不自动猜测手工输入的 metric_name。

除非用户显式通过标准指标搜索选择。

---

# 57. OCR issue 数据隐私

后台 OCR issue 不需要展示完整报告。

UNMATCHED_NAME 默认只返回：

```text
metric name
count
last_seen
少量原始名称样例
```

不得返回：

```text
result_text
reference
完整 OCR payload
患者名称
健康档案名称
COS URL
```

如果实现需要调试 ID，可返回内部：

```text
ocr_task_id / ingestion_id
```

但 UI 不需要默认展示医疗内容。

---

# 58. 日志

Admin 请求日志继续只记录：

```text
request_id
path
status
duration
必要资源 id
error_code
```

不得记录：

```text
完整 OCR metric issue 数组
完整 LabResult
完整 OcrResultItem.payload
管理员密码
Admin JWT
```

认证失败不得把输入密码写日志。

---

# 59. API 错误格式

继续遵守：

```json
{
  "code": "METRIC_ALIAS_CONFLICT",
  "message": "METRIC_ALIAS_CONFLICT",
  "request_id": "...",
  "details": {}
}
```

建议稳定错误：

```text
ADMIN_AUTH_REQUIRED
ADMIN_AUTH_INVALID
STANDARD_METRIC_NOT_FOUND
STANDARD_METRIC_CODE_CONFLICT
STANDARD_METRIC_CODE_IMMUTABLE
STANDARD_METRIC_IN_USE_BY_PENDING_CONFIRMATION
METRIC_ALIAS_NOT_FOUND
METRIC_ALIAS_DUPLICATE
METRIC_ALIAS_CONFLICT
METRIC_ALIAS_TARGET_INACTIVE
INVALID_METRIC_ALIAS
```

具体命名实施时可小幅调整，但 ACCEPTANCE 冻结后必须稳定。

---

# 60. Admin 登录暴力保护边界

Stage 07 不引入 Redis。

可采用最小方案：

- 环境配置管理员；
- 密码 hash；
- JWT；
- 正确认证失败码；
- 不输出敏感日志。

复杂：

```text
IP 限流
验证码
锁定策略
多因素认证
```

不属于本阶段 P0。

生产部署前可在 Stage 08 进一步强化。

---

# 61. Admin 前端 Token 存储

Admin Web 不使用微信登录。

Admin Token 可按当前 V1.0 Web 管理后台采用最简单安全可用方案存储。

不得：

- 写死 token；
- 写死管理员密码；
- 提交真实凭据。

前端必须统一 request 封装处理：

```text
Authorization
401
Admin 登录失效
稳定错误码
```

---

# 62. 测试范围

Stage 07 必须新增后端自动测试。

至少覆盖：

## StandardMetric

```text
新增
code 唯一
code 不可修改
name 修改
category 修改
停用
恢复
正式 LabResult 引用仍可停用
PENDING Confirmation 引用阻止停用
```

## MetricAlias

```text
新增
编辑
停用
恢复
normalized 唯一
并发唯一
与 StandardMetric name/code 冲突
INACTIVE StandardMetric 不可创建 ACTIVE Alias
```

## Exact Resolver

```text
OCR code exact 优先
StandardMetric name exact
Alias exact
未命中 NULL
Alias 不改 REVIEW 状态
已有 Confirmation 不重算
```

## Stage 04 搜索

```text
code
name
alias
inactive 不返回
多 alias 命中同 metric 去重
```

## OCR Issue

```text
UNMATCHED_NAME
PRODUCT_METRIC_MISSING
PRODUCT_METRIC_INACTIVE
只统计每 ingestion 最新成功 run
Alias 覆盖后问题自然消失
不修改 OcrResultItem
```

## Admin Auth

```text
无 token 拒绝
普通 user token 拒绝
admin token 成功
admin token 不能伪装普通 user
```

---

# 63. PostgreSQL 17 集成验证

必须真实验证：

```text
0006 → 0007
空库 0001 → 0007
MetricAlias PostgreSQL 唯一约束
并发 alias 创建
StandardMetric code 唯一
停用与 pending confirmation 约束
```

如新增 partial unique index：

必须在 PostgreSQL 17 实测。

---

# 64. 既有回归

Stage 07 完成后必须至少完整回归：

```text
Backend pytest
Ruff
Miniapp tests
Miniapp typecheck
Miniapp 微信构建
Admin typecheck
Admin build
git diff --check
```

还必须验证：

```text
Stage 04 commit
REVIEW_PENDING
KEEP_ORIGINAL_NAME
纯手工报告
OcrResultItem 不可变
Stage 05 报告列表/详情/原图
Stage 05 迁移/删除
Stage 06 我的指标
Stage 06 history/trend
MetricFavorite
```

---

# 65. OCR Frozen Regression

因为 Stage 07 明确不修改：

```text
backend/ocr_runtime
```

正常实现不需要因为 Stage 07 业务变更重新定义 OCR 算法基线。

但实施结束必须验证：

```text
OCR runtime 文件未被修改
PIPELINE_VERSION 未被修改
```

如果实际实现意外触碰 OCR runtime：

```text
停止
报告偏差
不得直接继续
```

---

# 66. Stage 03 已知 ORM / migration 漂移

当前存在已知独立工程问题：

> Stage 03 OCR 索引存在既有 ORM / migration 漂移。

Stage 07：

```text
不得顺手修复
```

创建 0007 时：

```text
不得因为 Alembic metadata diff
→ 自动加入 OCR task index 修复
```

如果 autogenerate 出现与 Stage 07 无关的 Stage 03 diff：

```text
明确排除
```

除非 Stage 07 实施过程中确认存在不可绕过的真实阻塞，并先由项目负责人确认扩大范围。

---

# 67. Migration autogenerate 规则

Codex 可以使用 autogenerate 辅助检查，但最终 migration 必须人工核对：

只允许包含：

```text
Stage 07 明确批准的 schema 变化
```

不得包含：

- 旧索引同步；
- 无关 nullable 修改；
- 无关 constraint rename；
- PostgreSQL 默认值顺手统一；
- 历史 migration 改写。

---

# 68. 预期主要实现文件

具体以 Codex 检查真实仓库为准，但预计包括：

```text
backend/app/models/entities.py
backend/app/models/__init__.py
backend/app/core/config.py
backend/app/core/admin_auth.py           （如采用独立文件）
backend/app/admin_metrics.py             （名称可调整）
backend/app/api/v1/admin_auth.py
backend/app/api/v1/admin_metrics.py
backend/app/api/v1/admin_ocr.py
backend/app/api/v1/confirmation.py
backend/app/confirmation.py
backend/app/main.py

backend/migrations/versions/0007_*.py

backend/tests/test_stage07*.py
backend/tests/verify_postgres_stage07*.py

admin-web/src/*
admin-web/package.json                   （仅确有需要时）
```

Stage 07 不预设必须拆多少 service 文件。

优先：

```text
清晰
可测试
少重复
不过度抽象
```

---

# 69. Miniapp 修改范围

Stage 07 小程序侧原则上只需要兼容：

```text
GET /standard-metrics
```

Alias 搜索增强。

如果现有页面无需任何改动即可消费相同响应结构：

```text
不修改 Miniapp
```

不得为了 Stage 07 顺手：

- 重构确认页；
- 重构报告页；
- 重构指标页；
- UI 打磨。

---

# 70. Admin Web 依赖

当前已有：

```text
Vue
Vue Router
Element Plus
```

Stage 07 尽量不引入新的大型前端依赖。

如确需：

```text
axios
```

等通用请求依赖，可评估，但原生 fetch 也足够。

禁止为了本阶段引入：

- Pinia（如果仅为简单 Admin 状态）；
- 大型表格框架；
- UI 二次封装框架；
- 图表库；
- 权限框架。

---

# 71. 数据模型文档同步

Stage 07 完成后，如实现与概念基线一致，应至少更新必要技术说明。

尤其：

```text
DATA_MODEL
```

当前已定义：

```text
StandardMetric 1 ─ N MetricAlias
```

如果实际字段 / 状态语义新增了长期规则，应更新相应 architecture 文档。

不得把所有 Stage 07 细节复制进 AGENTS.md。

只有长期稳定工程原则才进入 baseline / decision。

---

# 72. 是否需要新 Decision

当前三个关键决定：

```text
Alias 不进入 OCR matcher
StandardMetric 轻量 category
单管理员独立 Admin auth
```

都没有改变总体技术路线。

默认：

```text
不要求新增 architecture decision
```

如果实施过程中提出：

```text
数据库动态控制 OCR matcher
复杂 RBAC
独立 Admin 服务
Redis
```

则属于架构变化，必须停止并形成 decision。

---

# 73. 人工验收重点

Stage 07 人工验收至少应覆盖：

```text
1. Admin 登录；
2. 创建 StandardMetric；
3. 修改名称；
4. 修改 category；
5. 停用 / 恢复未被 pending workspace 引用的 StandardMetric；
6. pending Confirmation 引用时停用被阻止；
7. 新增 Alias；
8. Alias 冲突被拒绝；
9. 小程序 StandardMetric 搜索可通过 Alias 找到 canonical metric；
10. 新 OCR REVIEW 项在首次 Confirmation 初始化时可被 Alias 预关联，但仍为待确认；
11. 已存在 ConfirmationItem 不因新 Alias 自动变化；
12. 已有正式 LabResult 不因新 Alias 自动变化；
13. OCR 未匹配高频名称可在 Admin 看见；
14. 可从 OCR 未匹配名称创建 Alias；
15. OCR code 产品主数据缺失可创建 StandardMetric；
16. StandardMetric rename 后 Stage 06 使用新主数据名称；
17. 既往正式报告主项目名仍保持 LabResult.metric_name；
18. StandardMetric 停用后 Stage 06 历史 / 趋势仍存在；
19. OcrResultItem 前后内容不变；
20. OCR runtime / Pipeline version 未变化。
```

---

# 74. Stage 07 实施顺序建议

建议按以下顺序实施：

```text
A. Migration + 模型
→ StandardMetric.category
→ MetricAlias

B. normalization / identity conflict 基础能力

C. Admin Auth

D. StandardMetric / MetricAlias Admin API

E. Stage 04 StandardMetric 搜索 Alias 支持

F. Product Exact Metric Resolver

G. OCR metric issue 查询

H. OCR Task 只读查询

I. Admin Web

J. PostgreSQL 集成验证

K. Stage 04 / 05 / 06 回归

L. 人工验收

M. RESULT.md
```

不得先改 OCR matcher。

---

# 75. 实施过程中需要特别检查的真实代码点

Codex 正式实施前必须重新读取最新真实仓库，并检查：

```text
StandardMetric
OcrTask
OcrResultItem
ConfirmationItem
LabResult
MetricFavorite

backend/migrations/versions/*
backend/migrations/data/standard_metrics_v1.json

backend/app/confirmation.py
backend/app/api/v1/confirmation.py
backend/app/profile_metrics.py
backend/app/reports.py
backend/app/ocr_pipeline.py

backend/ocr_runtime/src/metric_matcher.py
backend/ocr_runtime/src/paper_metric_matcher.py
backend/ocr_runtime/data/metric_library.json

admin-web/*
```

只用于确认边界。

不得因为读取了 OCR runtime 就顺手修改。

---

# 76. 实施偏差处理

如果真实代码与本 PLAN 冲突：

```text
先报告
```

不能：

```text
自行扩大范围
自行重新定义规则
```

特别是如果实现 Product Exact Resolver 发现：

```text
FINAL_AUTO + 无 code
```

等真实情况与预期不同：

必须记录真实事实，并根据安全原则最小处理，不得通过 Alias 自动提高 AUTO 信任等级。

---

# 77. Definition of Done

Stage 07 只有同时满足以下条件才可以 PASS：

```text
StandardMetric 管理可用
+
code 创建后不可修改
+
StandardMetric 可停用 / 恢复
+
pending Confirmation 引用安全保护成立
+
MetricAlias 数据模型和 CRUD 可用
+
Alias normalization / 唯一冲突安全
+
Stage 04 搜索可通过 Alias 找到 canonical StandardMetric
+
Product Exact Resolver 只做 exact，不改 OCR 判定
+
Alias 只影响未来首次 Confirmation 初始化
+
既有 ConfirmationItem 不重算
+
既有 LabResult 不回填
+
OCR 未匹配问题可查询
+
缺失产品 StandardMetric code 可查询
+
OCR Task 轻量只读管理可用
+
Admin 单管理员独立认证可用
+
Stage 06 历史兼容成立
+
OcrResultItem 不可变
+
OCR runtime 未修改
+
Stage 03 既有 migration 漂移未被顺手修改
+
自动测试全部通过
+
PostgreSQL 17 专项通过
+
负责人真实人工验收通过
+
RESULT.md 完整
```

---

# 78. Stage 07 最终数据边界

冻结后的目标数据关系：

```text
PoC OCR Matcher
        │
        │  metricId / raw_metric / FINAL_AUTO|REVIEW
        ▼
OcrResultItem
（不可变）
        │
        │ Product Exact Resolver
        │ code exact / name exact / alias exact
        ▼
ConfirmationItem
（用户确认工作区）
        │
        │ REVIEW 仍人工处理
        ▼
commit
        │
        ▼
LabResult
        │
        │ standard_metric_id
        ▼
StandardMetric
   │
   ├── MetricAlias
   │
   └── Stage 06 History / Trend
```

核心不变量：

```text
MetricAlias
可以帮助未来确认
但不能重新解释过去

StandardMetric
可以改变当前主数据展示
但不能覆盖既往正式报告事实

Admin
可以管理主数据
但不能直接编辑正式 LabResult

OCR 排查
可以发现问题
但不能在线修改算法
```

---

# 79. Stage 07 与后续阶段边界

Stage 07 完成后，后续可以单独规划：

## OCR 算法优化阶段

基于 Stage 07 积累：

- 高频未匹配；
- Alias；
- 缺失指标；
- OCR failure；

回到 PoC：

```text
算法修改
→ Regression
→ 新 Pipeline Version
→ 正式迁入
```

## 数据修复阶段（如未来确有需要）

如果未来需要：

```text
历史 LabResult 重关联
```

必须单独设计：

- 审计；
- 人工确认；
- 可回滚；
- 影响趋势；
- 影响 Favorite；
- 影响重复检测；
- 影响报告展示。

不得作为 Stage 07 顺手能力。

## UI 总体打磨阶段

所有核心业务能力稳定后再统一进行：

- 小程序视觉；
- Admin 视觉；
- 交互一致性；
- 空状态；
- 响应式；
- 细节动效。

Stage 07 只要求功能可用。

---

# 80. Stage 07 冻结结论

Stage 07 最终冻结为：

```text
正式产品 StandardMetric 主数据管理
+
MetricAlias 主数据
+
Alias 搜索
+
未来 Confirmation 精确预关联
+
OCR 未匹配 / 主数据缺失反馈闭环
+
OCR Task 轻量只读排查
+
单管理员独立 Admin Web
```

同时明确禁止：

```text
Alias 进入 OCR matcher
OCR 算法在线修改
历史 LabResult 自动重关联
正式数据编辑
复杂 RBAC
PoC 74 项自动全量导入
Stage 03 migration 漂移顺手修复
全项目 UI 重构
```

本 PLAN 冻结后，下一步应生成：

```text
docs/stages/07-admin/ACCEPTANCE.md
```

并以本 PLAN 作为 Stage 07 验收基线的详细设计来源。
