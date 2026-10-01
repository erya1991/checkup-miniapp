# Stage 06｜我的指标 / 指标历史与趋势

**状态：READY_FOR_IMPLEMENTATION**

## 1. 阶段目标

Stage 06 承接已经正式 PASS 的 Stage 05。

截至本阶段启动时，正式健康数据链已经稳定为：

```text
ReportAsset
→ OcrTask
→ OcrResultItem
→ ConfirmationItem
→ commit
→ LabReport
→ LabResult
```

其中：

```text
LabReport / LabResult
= 用户 commit 后的正式健康数据
```

Stage 06 的职责是：

> 基于正式 `LabResult`，按 `HealthProfile + StandardMetric` 建立“我的指标”视角，提供最新结果、完整历史、按单位分组的确定数值趋势和轻量关注能力。

本阶段结束时必须形成：

```text
选择 HealthProfile
→ 查看“我的指标”
→ 查看某标准指标最新结果
→ 查看完整历史结果
→ 查看可绘制数值趋势
→ 多单位趋势安全分组/切换
→ 关注 / 取消关注指标
→ 从历史/趋势回到正式报告与原始报告
```

Stage 06 不建立独立 Trend / History / LatestResult 表，不进行任意跨单位数值换算，不重新解释医学结果，不修改正式 `LabReport / LabResult`，不建设 StandardMetric / MetricAlias 管理后台。

---

# 2. 必读基线

实施前必须按根目录 `AGENTS.md` 规定顺序读取：

1. 根目录 `AGENTS.md`；
2. `docs/00-baseline/PRODUCT_BASELINE.md`；
3. `docs/00-baseline/TECH_BASELINE.md`；
4. `docs/00-baseline/DEVELOPMENT_RULES.md`；
5. 本目录 `PLAN.md`；
6. 本目录 `ACCEPTANCE.md`；
7. `docs/stages/05-report-management/RESULT.md`；
8. 本阶段涉及正式数据、指标模型和 API，继续读取：
   - `docs/01-architecture/DATA_MODEL.md`；
   - `docs/01-architecture/API_CONVENTIONS.md`；
   - `docs/01-architecture/SYSTEM_ARCHITECTURE.md`；
   - 与正式报告数据链相关的现有 decision 文档，如真实仓库存在。

同时必须检查当前真实代码中的：

```text
HealthProfile
LabReport
LabResult
StandardMetric
ConfirmationItem
ReportIngestion

Stage 05 report service/router
Stage 05 migration/delete
Stage 05 小程序 reports/report-detail 页面
Stage 04 commit 生成 LabResult 的真实逻辑
现有 PostgreSQL migrations
现有 miniapp package.json / pages.json
```

不得根据旧对话、旧计划或假设直接编码。

---

# 3. Stage 05 当前真实基础

截至 Stage 06 启动时，远程 `main` 的 Stage 05 已正式 PASS。

当前真实实现已经确认：

- `LabResult` 是正式结果数据源；
- `LabResult.health_profile_id` 已持久化；
- `LabResult.standard_metric_id` 可为空；
- `LabResult` 已包含：
  - `metric_name`；
  - `result_text`；
  - `result_numeric`；
  - `comparator`；
  - `unit_original`；
  - `unit_normalized`；
  - `reference_text`；
  - `reference_low`；
  - `reference_high`；
  - `abnormal`；
  - `examination_date`；
  - `examination_time`；
  - `data_source`；
- 正式报告迁移会同步更新：

```text
LabReport.health_profile_id
LabResult.health_profile_id
ReportIngestion.health_profile_id
```

- 正式报告删除会硬删除对应 `LabResult`；
- Stage 05 没有 Trend / History / LatestResult / MetricFavorite 等提前实现；
- 当前 `StandardMetric` 已存在，但 Stage 04 冻结种子仅包含当前正式产品已落库的 12 个指标；
- 当前尚未实现 `MetricAlias`；
- 当前尚未实现 `MetricFavorite`；
- Stage 04 人工修改单位时会将 `unit_normalized` 清空，因此 Stage 06 不能假设所有正式结果都存在标准化单位。

---

# 4. Stage 06 一句话职责

> Stage 06 只消费正式 `LabResult`，把已经可靠关联 `StandardMetric` 的结果按健康档案聚合成长期指标视角，并提供安全、可追溯的历史与趋势展示。

本阶段读取：

```text
HealthProfile
LabReport
LabResult
StandardMetric
MetricFavorite（本阶段新增）
```

本阶段不得把以下临时域直接当作指标历史来源：

```text
ReportIngestion
OcrTask
OcrResultItem
ConfirmationItem
```

---

# 5. “我的指标”的产品定义

“我的指标”定义为：

> 当前 HealthProfile 已经在正式 `LabResult` 中真实出现、且具备非空 `standard_metric_id` 的标准指标集合。

因此：

```text
检验报告
= 按报告查看正式结果

我的指标
= 按 StandardMetric 跨报告查看正式结果
```

“我的指标”不是：

- 全部 StandardMetric 字典；
- OCR 识别结果列表；
- Confirmation 工作区；
- 未 commit 报告中的候选指标；
- 管理员指标配置页；
- 医学解释或健康评分页。

当前 HealthProfile 从未产生正式结果的 StandardMetric，不因为存在于公共字典中就展示在“我的指标”。

---

# 6. 正式数据准入

Stage 06 所有指标列表、最新结果、历史和趋势都必须只来自正式 `LabResult`。

查询基础必须满足：

```text
LabResult.health_profile_id = 当前 health_profile_id
AND
LabResult.standard_metric_id IS NOT NULL
```

并通过 `LabReport` 取得：

- report owner；
- hospital；
- report created_at（仅用于无法用检验时间区分时的稳定排序）；
- report id；
- 正式报告追溯入口。

后端在查询前必须先验证：

```text
HealthProfile.id = health_profile_id
AND
HealthProfile.user_id = current_user.id
AND
HealthProfile.status = ACTIVE
```

必要查询建议继续带上：

```text
LabReport.user_id = current_user.id
```

不得因为前端传入合法 UUID 就跳过 ownership 验证。

---

# 7. `standard_metric_id = NULL` 的硬边界

以下正式结果：

```text
LabResult.standard_metric_id = NULL
```

仍然是正式报告数据，继续由 Stage 05 正式报告详情正常展示。

但 Stage 06 必须：

```text
不进入“我的指标”聚合
不进入 StandardMetric 历史
不进入趋势
不能作为关注指标
```

Stage 06 禁止通过：

```text
metric_name 字符串相等
模糊匹配
同义词猜测
OCR code 猜测
```

将 `standard_metric_id = NULL` 的既往正式结果临时聚到某个 StandardMetric。

原因：跨报告身份统一只能以正式保存时的 `standard_metric_id` 为准。

后续别名与标准指标管理属于 Stage 07。

---

# 8. “我的指标”列表聚合

## 8.1 聚合键

唯一业务聚合身份：

```text
health_profile_id
+
standard_metric_id
```

不能把单位加入指标身份。

例如同一个 WBC 出现两个单位：

```text
×10^9/L
/μL
```

仍然只有一个“白细胞计数（WBC）”指标详情页；单位只影响趋势序列分组。

## 8.2 列表返回内容

每个指标卡片至少返回/展示：

- `StandardMetric.id`；
- `StandardMetric.code`；
- `StandardMetric.name`；
- 是否关注；
- 正式历史记录总数；
- 最新正式结果；
- 最新检验日期；
- 最新检验时间，有则展示；
- 最新结果单位，有则展示；
- 最新结果 `abnormal` 提示，有则展示；
- 可绘制趋势序列数量或等价能力信息，可作为详情判断依据。

最新结果主显示值必须使用：

```text
LabResult.result_text
```

不得重新从 `result_numeric + comparator` 拼接替代正式文本。

## 8.3 最新结果定义

“最新结果”定义为当前 HealthProfile + StandardMetric 下按以下顺序排在第一的正式 `LabResult`：

```text
LabResult.examination_date DESC
→ LabResult.examination_time DESC NULLS LAST
→ LabReport.created_at DESC
→ LabReport.id DESC
→ LabResult.sequence_no ASC
→ LabResult.id ASC
```

其中：

- 检验日期/时间是医学时间主排序；
- `LabReport.created_at / id / LabResult.sequence_no / id` 仅用于同一检验日期/时间无法区分时保证查询稳定；
- 不得把上传时间、OCR 时间、commit 时间作为医学意义上的“最新”；
- 时间完全相同或时间缺失时，技术 tie-breaker 不得被文案解释为“这次检测一定更晚”。

## 8.4 最新结果可以是非数值

必须明确：

```text
最新结果 != 最新可绘制数值结果
```

例如：

```text
2026-07-01  2.1
2026-08-01  2.5
2026-09-01  阴性
```

我的指标最新结果必须显示：

```text
阴性
2026-09-01
```

不能因为“阴性无法画折线”就退回展示 2.5。

## 8.5 列表排序

Stage 06 默认排序：

```text
is_favorite DESC
→ 最新结果的 examination_date DESC
→ 最新结果的 examination_time DESC NULLS LAST
→ StandardMetric.name ASC
→ StandardMetric.code ASC
→ StandardMetric.id ASC
```

即：

- 已关注指标优先；
- 同关注状态内，最近检测的指标优先；
- 不按 abnormal 严重程度排序；
- 不构建“风险优先级”。

## 8.6 分页

指标列表使用服务端分页。

建议：

```text
page >= 1
page_size 默认 20
page_size 最大 100
```

返回与 Stage 05 一致风格：

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0,
  "has_more": false
}
```

其中 `total` 表示当前 HealthProfile 下具备正式历史的 distinct StandardMetric 数量。

---

# 9. 指标详情与历史

## 9.1 详情身份

指标详情必须显式绑定：

```text
health_profile_id
+
standard_metric_id
```

不能只用 `standard_metric_id` 查询后再由前端过滤。

## 9.2 历史范围

历史必须包含该 HealthProfile + StandardMetric 的全部正式 `LabResult`：

- 数值；
- 非数值；
- 带 comparator 的结果；
- 不同单位；
- 同一天多份报告；
- 同一天同一报告中如真实存在多条同标准指标结果，也不得静默覆盖。

不得：

- 去重；
- 求平均；
- 取最大/最小替代；
- 同日合并；
- 因单位不同而从历史中隐藏。

## 9.3 历史排序

历史默认最近在前：

```text
examination_date DESC
→ examination_time DESC NULLS LAST
→ LabReport.created_at DESC
→ LabReport.id DESC
→ LabResult.sequence_no ASC
→ LabResult.id ASC
```

## 9.4 历史分页

历史使用服务端分页。

建议：

```text
page_size 默认 50
page_size 最大 100
```

## 9.5 历史项内容

每条历史至少包含：

- `lab_result_id`；
- `report_id`；
- `metric_name`；
- `result_text`；
- `result_numeric`，可空；
- `comparator`，可空；
- `unit_original`；
- `unit_normalized`；
- display unit；
- `reference_text`；
- `abnormal`；
- `examination_date`；
- `examination_time`；
- 医院，有则返回；
- 报告编号可按现有数据轻量返回。

前端主显示仍然使用 `result_text`。

## 9.6 正式报告追溯

每条历史必须可以通过 `report_id` 回到 Stage 05：

```text
正式报告详情
→ 原始报告
```

Stage 06 不重复建设：

- 原图 API；
- COS 签名；
- 报告详情；
- OCR bbox 查看。

---

# 10. 同一天多份报告

Baseline 已冻结：

> 同一天多次检测全部保留，不覆盖、不平均。

因此 Stage 06 必须保留：

```text
2026-10-01 08:00 WBC 5.1
2026-10-01 14:00 WBC 5.8
```

作为两条历史和两个趋势点。

如果时间未知：

```text
2026-10-01 --:-- WBC 5.1
2026-10-01 --:-- WBC 5.8
```

仍然是两条独立数据。

趋势图不得按日期字符串去重。

每个趋势点必须绑定唯一：

```text
lab_result_id
report_id
```

因此前端图表数据不能使用日期作为唯一 key。

---

# 11. 普通折线图可绘制条件

Stage 06 的普通折线图只绘制“确定数值点”。

可绘制条件：

```text
LabResult.result_numeric IS NOT NULL
AND
LabResult.comparator IN (NULL, '', '=')
```

不得在 Stage 06 重新从 `result_text` 解析数值。

如果：

```text
result_numeric = NULL
```

即使 `result_text` 看起来像数字，也不得由趋势层补做解析。

---

# 12. comparator 结果处理

以下结果即使存在 `result_numeric`：

```text
<0.10
>200
≤5
≥100
```

也不得作为普通精确折线点绘制。

原因：

```text
<0.10 != 0.10
>200 != 200
```

将阈值当作精确值会改变正式数据含义。

因此：

```text
有 comparator 的非等号结果
→ 正常进入历史
→ 不进入普通折线图
```

Stage 06 不设计特殊 censored-value 图形、箭头点或区间估算。

---

# 13. 非数值结果处理

例如：

```text
阴性
阳性
弱阳性
未检出
未见异常
```

必须：

```text
进入完整历史
可以成为“最新结果”
可以回到正式报告
```

不得：

```text
强行映射成 0 / 1
强行进入普通折线图
根据文本推断医学严重程度
```

如果某指标没有任何可绘制数值点，详情页显示：

```text
暂无可绘制数值趋势，历史结果仍可查看。
```

而不是显示空白或错误。

---

# 14. 单位分组

## 14.1 原则

同一个 StandardMetric 的历史可以包含不同单位。

Stage 06 不进行任意跨单位数值换算。

不同单位不得直接画在同一折线序列中。

## 14.2 unit series key

趋势查询时后端计算临时分组键，不持久化：

```text
如果 unit_normalized 非 NULL/非空：
    series_unit = trim(unit_normalized)
否则如果 unit_original 非 NULL/非空：
    series_unit = trim(unit_original)
否则：
    series_unit = NULL
```

内部可使用：

```text
__NO_UNIT__
```

表示无单位序列。

用户显示：

```text
无单位
```

Stage 06 对单位字符串只允许安全的首尾空白处理，不做：

- 大小写等价推断；
- Unicode 单位语义替换；
- 单位字典换算；
- `mg/dL ↔ mmol/L`；
- `/μL ↔ ×10^9/L`；
- 医学量纲推断。

`unit_normalized` 已有值时优先使用它，是因为该值来自正式 commit 前已经确定的 Pipeline/Confirmation 数据；Stage 06 本身不重新标准化单位。

## 14.3 多单位详情

一个 StandardMetric 仍然只有一个指标详情。

如果存在多个可绘制单位序列：

```text
指标详情
→ 单位切换
→ 每次只显示一个单位序列
```

不建议把量纲不同的单位作为多条折线同时放在同一 Y 轴。

默认选中：

> 包含“最近一个可绘制数值点”的单位序列。

若只有一个序列，不需要显示复杂切换控件。

## 14.4 历史不按单位拆开

完整历史仍然统一按检验时间展示：

```text
2026-10-01  5.2 ×10^9/L
2026-08-01  4800 /μL
2026-05-01  4.9 ×10^9/L
```

单位只影响趋势，不影响历史完整性。

---

# 15. 趋势点顺序与 X 轴

趋势 API 返回每个单位序列时，points 按时间正序：

```text
examination_date ASC
→ examination_time ASC NULLS FIRST
→ LabReport.created_at ASC
→ LabReport.id ASC
→ LabResult.sequence_no ASC
→ LabResult.id ASC
```

这里：

- 检验时间仍是主时间；
- time 为 NULL 时不得虚构 00:00、12:00 或其它时间；
- 后续字段只做稳定排序；
- 同一天多个点必须全部保留。

前端不得仅使用 timestamp 作为唯一 identity。

V1.0 可以使用按 points 顺序绘制的 category-like X 轴，以确保同日多点不会因为相同日期被合并。

---

# 16. 趋势点内容与可追溯性

每个趋势点至少包含：

```text
lab_result_id
report_id
examination_date
examination_time
value              # 仅图表坐标使用
result_text         # 用户真实显示值
unit
reference_text
abnormal
```

其中：

```text
value
```

只来源于已持久化 `result_numeric`，用于图表坐标。

用户查看点值仍优先显示：

```text
result_text
```

趋势点必须可以回到对应：

```text
Stage 05 正式报告详情
→ 原始报告
```

可以通过点击趋势点后显示轻量详情及“查看报告”，不要求复杂浮层动画。

---

# 17. 参考范围与 abnormal

## 17.1 参考范围

参考范围属于某一次具体 `LabResult`。

Stage 06 不允许把某一次或某家医院的参考范围提升成 StandardMetric 的全局固定范围。

因此本阶段不做：

```text
全图固定绿色正常区间
StandardMetric 全局 reference_low/reference_high
跨报告统一正常带
```

历史项和趋势点详情继续展示该条记录自己的：

```text
reference_text
```

## 17.2 abnormal

Stage 06 只使用持久化：

```text
LabResult.abnormal
```

不得根据：

```text
result_numeric
reference_low
reference_high
```

重新计算 abnormal。

尤其：

```text
abnormal = NULL
```

不等于“正常”。

Stage 06 不生成趋势结论：

- 持续升高；
- 明显改善；
- 风险加重；
- 建议就医；
- 健康评分。

---

# 18. Trend / History 不落独立业务表

Tech Baseline 已冻结：V1.0 不建立独立 Trend 表。

Stage 06 不增加：

```text
Trend
MetricHistory
LatestResult
ProfileMetricSummary
MetricSnapshot
TrendCache
```

指标列表、latest、history、trend 均基于正式 `LabResult` 实时/按需查询。

允许为了查询效率新增合理数据库索引，但不得通过新增冗余业务表解决当前规模不存在的性能问题。

---

# 19. 关注指标

## 19.1 本阶段纳入范围

Stage 06 正式加入轻量“关注指标”。

只提供：

```text
关注
取消关注
关注指标优先显示
```

不提供：

- 阈值提醒；
- 定时提醒；
- 微信消息推送；
- 目标值；
- 自定义备注；
- 关注原因；
- 健康建议；
- 关注分组。

## 19.2 MetricFavorite 数据模型

新增：

```text
MetricFavorite
```

至少包含：

```text
id
health_profile_id
standard_metric_id
created_at
```

唯一约束：

```text
UNIQUE(health_profile_id, standard_metric_id)
```

不冗余：

```text
user_id
report_id
latest_result_id
```

用户归属通过 HealthProfile 校验。

## 19.3 Favorite 是档案偏好，不是报告数据

关注关系属于：

```text
HealthProfile + StandardMetric
```

不属于某份报告。

因此报告迁移/删除不得自动删除或迁移 Favorite。

例如：

```text
父亲关注 WBC
```

把一份 WBC 报告迁移到母亲后：

```text
父亲的 WBC Favorite 仍属于父亲
母亲不会自动关注 WBC
```

## 19.4 dormant favorite

如果某 HealthProfile 已关注某指标，但之后因为报告迁移/删除导致该 profile 当前没有任何对应正式 `LabResult`：

```text
Favorite 可以继续保留
但“我的指标”列表不显示无历史指标
```

以后再次产生该 StandardMetric 的正式结果时，可自然恢复为“已关注”。

Stage 06 不建设单独“无数据关注项管理页”。

## 19.5 Favorite 幂等

关注接口必须幂等：

```text
重复关注
→ 不产生重复记录
```

取消关注也应安全幂等：

```text
记录不存在
→ 仍可视为已取消
```

---

# 20. StandardMetric 当前范围

Stage 06 不扩充当前 Stage 04 已冻结的 StandardMetric 种子集合。

也不因为 PoC 已支持更多指标，就在本阶段顺手：

- 导入完整 PoC metric library；
- 新建大量 StandardMetric；
- 新建 MetricAlias；
- 修改 OCR matching；
- 回填既往 `standard_metric_id = NULL`。

Stage 06 的功能验收应选择当前正式 StandardMetric 已覆盖、且真实数据可形成历史的指标，例如 WBC / HGB / ALT 等。

StandardMetric 覆盖率扩展属于 Stage 07 主数据管理边界。

---

# 21. StandardMetric status 的历史兼容原则

Stage 06 当前不管理 StandardMetric 状态，但查询设计不得把：

```text
StandardMetric.status = ACTIVE
```

作为历史数据可见性的必要条件。

如果未来 Stage 07 将某 StandardMetric 停用：

- 已经正式保存并引用它的 `LabResult` 历史仍应可查看；
- 不得因为主数据状态变化让用户既往正式健康数据从历史消失。

Stage 06 对已有正式历史只要求 StandardMetric 行仍存在。

---

# 22. 报告迁移后的自然变化

Stage 05 已保证正式报告迁移会同步修改：

```text
LabResult.health_profile_id
```

因此 Stage 06 不增加任何：

```text
trend migration
history sync
latest recompute table
summary refresh task
```

例如：

```text
父亲：WBC 5.1 / 5.3 / 5.5
```

将 5.5 对应报告迁移到母亲后，下一次查询自然变为：

```text
父亲：5.1 / 5.3
母亲：5.5
```

Favorite 仍按各自 HealthProfile 独立存在。

---

# 23. 报告删除后的自然变化

Stage 05 删除正式报告会硬删除对应 `LabResult`。

因此 Stage 06 不增加额外删除同步。

例如：

```text
WBC 5.1 / 5.3 / 5.5
```

删除 5.5 对应报告：

```text
最新结果自然变成 5.3
历史自然变成 2 条
趋势自然变成 2 个点
```

删除最后一条 WBC 正式结果后：

```text
WBC 从“我的指标”列表自然消失
```

即使存在 dormant Favorite，也不把无正式历史的 WBC 展示成一个空指标卡片。

---

# 24. HealthProfile 切换

Stage 06 继续使用 Stage 05 的显式 profile 模式。

所有指标 API 必须显式接收：

```text
health_profile_id
```

小程序页面 `onShow` 时重新读取当前默认 HealthProfile。

从健康档案页切换：

```text
父亲
→ 母亲
```

返回“我的指标”后必须重新加载母亲的数据，不能保留父亲的：

- 指标列表；
- latest；
- history；
- trend；
- Favorite 状态。

需要继续防止旧请求返回覆盖新档案结果，可沿用 Stage 05 请求版本/取消旧响应的思路。

---

# 25. API 范围

Stage 06 建议新增独立 profile metric service/router，保持 `/api/v1` 前缀。

至少：

```text
GET /api/v1/profile-metrics
GET /api/v1/profile-metrics/{standard_metric_id}
GET /api/v1/profile-metrics/{standard_metric_id}/history
GET /api/v1/profile-metrics/{standard_metric_id}/trend

PUT    /api/v1/favorites/{standard_metric_id}
DELETE /api/v1/favorites/{standard_metric_id}
```

## 25.1 指标列表

```text
GET /profile-metrics
?health_profile_id=
&page=
&page_size=
```

## 25.2 指标详情

```text
GET /profile-metrics/{standard_metric_id}
?health_profile_id=
```

至少返回：

```text
standard_metric
favorite
latest
history_count
trend_plottable_count
trend_series_count
```

如果该 HealthProfile 当前没有任何对应正式 `LabResult`：

```text
PROFILE_METRIC_NOT_FOUND
```

不得因为存在 dormant Favorite 就伪造一个空指标详情。

## 25.3 历史

```text
GET /profile-metrics/{standard_metric_id}/history
?health_profile_id=
&page=
&page_size=
```

## 25.4 趋势

```text
GET /profile-metrics/{standard_metric_id}/trend
?health_profile_id=
```

V1.0 不要求日期范围筛选。

一个用户单项长期结果规模有限，趋势可以返回该指标全部可绘制 points。

响应建议包含：

```json
{
  "standard_metric": {},
  "history_count": 0,
  "plottable_count": 0,
  "series": [
    {
      "series_key": "...",
      "unit": "...",
      "points": []
    }
  ]
}
```

series 按“最近一个可绘制点”从新到旧排列，便于前端默认选择第一项。

## 25.5 Favorite

```text
PUT /favorites/{standard_metric_id}?health_profile_id=
DELETE /favorites/{standard_metric_id}?health_profile_id=
```

必须验证：

- HealthProfile 属于 current user；
- StandardMetric 存在；
- 当前请求不允许跨用户创建/删除 Favorite。

Stage 06 UI 只会从已有指标列表/详情发起关注，但 Favorite 数据模型允许在当前历史暂时消失后继续保留。

---

# 26. 业务错误码

至少建议稳定使用：

```text
PROFILE_NOT_FOUND
STANDARD_METRIC_NOT_FOUND
PROFILE_METRIC_NOT_FOUND
```

跨用户资源不得通过不同错误文本泄露资源是否存在。

保持现有统一错误结构和 request_id 机制。

---

# 27. 数据库 migration

Stage 06 需要新增 migration，例如：

```text
0006_metric_trend
```

`down_revision` 必须指向当前真实唯一 head：

```text
0005_report_management
```

至少完成：

## 27.1 新建 MetricFavorite

```text
metric_favorites
```

字段至少：

```text
id
health_profile_id FK
standard_metric_id FK
created_at
```

唯一约束：

```text
health_profile_id + standard_metric_id
```

## 27.2 LabResult 查询索引

允许新增真实需要的复合索引，例如：

```text
(health_profile_id, standard_metric_id, examination_date)
```

具体索引名称遵循当前 migration 风格。

不增加冗余趋势表或 latest 字段。

## 27.3 历史正式数据无回填

Stage 04/05 已有正式 `LabReport / LabResult` 升级到 0006 后必须可直接进入 Stage 06 查询。

不得要求：

- 重新 OCR；
- 重新确认；
- 重新 commit；
- 批量改写 `standard_metric_id`；
- 批量补 `unit_normalized`。

---

# 28. 后端查询实现原则

Stage 06 可以根据当前规模采用清晰、可测试的 SQLAlchemy 查询，不为了“看起来高级”引入复杂缓存层。

必须避免明显的每个指标再循环查询多次报告/StandardMetric 的无界 N+1 设计。

允许：

- 聚合查询；
- window function；
- 子查询；
- 合理批量加载；
- 在服务层做少量最终组装。

但最终业务语义必须以本 PLAN 为准。

不得把指标聚合逻辑主要放到小程序端。

---

# 29. 小程序信息架构

Stage 06 UI 仍以功能可用为主，不进行整体视觉重构。

当前 Stage 05 已有：

```text
首页
→ 检验报告
```

Stage 06 建议把“报告”形成两个简单视角：

```text
[检验报告]  [我的指标]
```

可采用：

- 报告列表页顶部简单切换入口；
- 我的指标页顶部提供回到检验报告入口；

不要求本阶段重构成完整 bottom tabBar。

至少新增页面：

```text
我的指标
指标详情 / 趋势
```

建议路径按现有工程风格，例如：

```text
pages/profile-metrics/index
pages/metric-detail/index
```

具体命名可按真实仓库统一，但不得把页面塞入 Stage 05 报告详情形成难维护巨页。

---

# 30. 我的指标页面状态

页面至少处理：

```text
loading
success
empty
error + retry
加载更多
```

empty 场景包括：

1. 当前档案没有任何正式报告；
2. 有正式报告，但没有任何 `standard_metric_id != NULL` 的正式结果。

文案不要把第二种情况错误说成“没有报告”。

可以轻量提示：

```text
暂无可聚合的标准指标
```

不引导用户自行修改正式报告。

---

# 31. 指标详情页面

至少展示：

- StandardMetric 名称；
- code；
- 当前 Favorite 状态；
- 最新正式结果；
- 最新检验时间；
- 最新单位；
- 最新 abnormal 提示；
- 趋势区域；
- 多单位切换，有多单位时；
- 完整历史；
- 历史项进入正式报告；
- loading / error / retry；
- 无可绘制趋势时的正常空状态。

历史和趋势可以在同一详情页完成，不需要为了形式增加更多页面。

---

# 32. 折线图实现边界

当前 miniapp 尚无图表依赖。

Stage 06 允许两种方式之一：

1. 使用与当前 uni-app + mp-weixin 构建验证兼容的轻量图表依赖；
2. 使用足够简单、可维护的本地图表实现。

如果新增第三方依赖：

- 必须说明目的；
- 更新 lockfile；
- 通过 `pnpm test / typecheck / build:mp-weixin`；
- 不引入大型 Dashboard/UI 框架；
- 不为了一个折线图升级 uni-app、Vue、Vite 主版本。

本阶段图表只要求：

- 单位序列切换；
- 折线；
- 数据点；
- 日期标签；
- 点击/选择点查看正式结果摘要；
- 可以进入对应报告。

不要求：

- 缩放漫游；
- 复杂动画；
- 多轴；
- 医学正常带；
- 预测线；
- 趋势算法；
- AI 解读。

最重要的是：

```text
后端决定哪些点可以画、如何分单位
前端只绘制后端已经分好的 series
```

---

# 33. 前端不得重新做业务推断

小程序不得自行：

- 从 `result_text` 解析数值；
- 判断 `<0.1` 是否取 0.1；
- 判断两个单位是否兼容；
- 换算单位；
- 根据参考范围重新算 abnormal；
- 用 metric_name 合并 standard_metric_id=NULL；
- 用客户端时间决定“最新”。

前端只消费后端已经明确的：

```text
latest
history
series
favorite
```

---

# 34. 权限与隐私

所有 Stage 06 API 都必须满足：

- 当前用户只能读取自己的 HealthProfile 指标；
- 不能通过他人的 `health_profile_id` 读取指标列表；
- 不能通过他人的 profile + 自己知道的 StandardMetric ID 读取 history/trend；
- 不能给他人的 HealthProfile 创建/删除 Favorite；
- 返回不包含 COS object key；
- 返回不包含永久 COS URL；
- 不返回 OCR 全文；
- 普通日志不记录完整检验结果、完整 history/trend payload。

日志继续记录：

```text
request_id
path
status
必要资源 id
error_code
```

不得记录完整医疗数据数组。

---

# 35. Stage 05 行为回归

Stage 06 不能破坏：

- 正式报告列表；
- 正式报告详情；
- 原始报告；
- 报告迁移；
- 疑似重复迁移；
- 正式报告删除；
- FileCleanup；
- Stage 04 commit；
- REVIEW_PENDING；
- KEEP_ORIGINAL_NAME；
- 纯手工报告；
- OcrResultItem 不可变。

尤其必须验证：

```text
迁移报告
→ Stage 06 指标归属自然变化

删除报告
→ Stage 06 latest/history/trend 自然变化
```

但不得为此修改 Stage 05 的迁移/删除为“同步趋势表”。

---

# 36. PostgreSQL 17 集成验证

Stage 06 必须使用真实 PostgreSQL 17 临时数据库验证至少：

```text
0005 → 0006 migration
空库 0001 → 0006 migration
Stage 05 已有正式报告升级后直接聚合
MetricFavorite 唯一约束
报告迁移后指标归属变化
报告删除后 latest/history/trend 变化
同日多份报告不丢失
多单位分组正确
```

临时测试库执行完成后必须删除。

不能只依赖 SQLite 或 mock 证明 PostgreSQL-specific 排序/约束正确。

---

# 37. 后端自动测试重点

至少覆盖：

- profile ownership；
- 只查询正式 LabResult；
- `standard_metric_id = NULL` 排除；
- distinct StandardMetric 聚合；
- latest 排序；
- 非数值可成为 latest；
- 同日多份保留；
- history 完整；
- comparator 排除普通趋势；
- non-numeric 排除普通趋势；
- unit_normalized 优先；
- unit_normalized NULL 回退 unit_original；
- 无单位序列；
- 多单位不混线；
- abnormal 不重算；
- Favorite 幂等与唯一约束；
- Favorite profile 隔离；
- dormant Favorite；
- 报告迁移后的自然变化；
- 报告删除后的自然变化；
- Stage 00～05 全量回归。

---

# 38. Miniapp 自动测试重点

建议对纯函数/页面辅助逻辑测试：

- profile-metrics 路径构造；
- 分页合并；
- history 分页合并；
- Favorite 切换状态；
- 多单位 series 默认选择；
- 无可绘制 trend 空状态；
- report navigation；
- HealthProfile 切换后旧响应不覆盖新数据；
- 同日点不得按日期去重。

最终必须通过：

```text
pnpm test
pnpm typecheck
pnpm build:mp-weixin
```

---

# 39. Admin 回归

Stage 06 不实现管理后台指标业务，但现有 admin-web 必须继续：

```text
pnpm typecheck
pnpm build
```

通过。

不得为了 Stage 06 顺手增加：

- StandardMetric CRUD；
- MetricAlias CRUD；
- OCR 配置后台。

---

# 40. 真实微信小程序人工验收方向

Stage 06 最终必须由项目负责人在真实微信小程序环境至少验证：

1. 我的指标列表及 HealthProfile 切换；
2. 最新结果与历史；
3. 同一天多条结果完整保留；
4. 普通数值折线图；
5. 非数值和 `< / > / ≤ / ≥` 只进历史、不误画精确点；
6. 多单位安全分组与切换；
7. Favorite 按档案隔离并可取消；
8. 从历史/趋势回正式报告与原图；
9. 报告迁移后源/目标档案趋势自然变化；
10. 报告删除后 latest/history/trend 自然变化。

自动测试和构建不能替代本节人工验收。

---

# 41. Stage 07 边界

Stage 06 明确不实现 Stage 07 的：

```text
StandardMetric 管理后台
MetricAlias 数据模型
MetricAlias 管理
StandardMetric 批量扩充后台能力
标准指标启停管理 UI
OCR 问题排查后台业务
```

Stage 07 未来可以改善“未来报告”的标准指标识别/选择能力，但不得未经单独设计就批量改写既往正式 `LabResult.standard_metric_id`。

尤其禁止 Stage 06/07 顺手：

```text
UPDATE lab_results
SET standard_metric_id = ...
WHERE metric_name LIKE ...
```

把既往正式快照重新解释。

如果未来确需既往正式数据重关联，应单独设计正式数据纠错/重关联机制，不属于 Stage 06。

---

# 42. Stage 06 明确不做

本阶段不做：

- 医疗诊断；
- AI 健康解释；
- 疾病风险；
- 用药建议；
- 趋势预测；
- 自动健康评分；
- “改善/恶化”自动判断；
- 任意跨单位换算；
- comparator 特殊估值；
- 非数值映射成数字；
- 全局参考范围；
- 复杂趋势筛选；
- 日期范围选择器；
- Trend/History/Latest 独立业务表；
- Redis/缓存中间件；
- StandardMetric 种子扩充；
- MetricAlias；
- StandardMetric 后台；
- OCR 算法规则修改；
- 正式 LabResult 编辑；
- 大规模 UI 重构。

---

# 43. 预期主要实现范围

具体文件以 Codex 检查真实仓库后为准，但预计包括：

```text
backend/app/models/entities.py
backend/app/models/__init__.py
backend/app/main.py
backend/app/profile_metrics.py 或等价 service
backend/app/api/v1/profile_metrics.py 或等价 router
backend/migrations/versions/0006_*.py
backend/tests/*stage06*
backend/tests/*postgres*（按现有测试组织）

miniapp/src/api.ts
miniapp/src/pages.json
miniapp/src/profile-metrics.ts 或等价辅助文件
miniapp/src/pages/profile-metrics/index.vue
miniapp/src/pages/metric-detail/index.vue
miniapp/tests/*

必要 README / Stage 06 RESULT.md
```

如果实现需要修改 Stage 05 report service，只允许为了复用稳定排序/正式报告导航所需的最小公共函数，不能借机重构整个报告模块。

---

# 44. 文档职责

继续遵循：

```text
PLAN.md       = 详细设计与实施边界
ACCEPTANCE.md = 验收基线
RESULT.md     = 实施事实
Codex Prompt  = 读取 + 执行 + 测试 + 汇报
```

Codex 实施完成后必须更新本目录：

```text
RESULT.md
```

至少记录：

- 实际实现文件；
- migration；
- MetricFavorite；
- profile metrics API；
- latest/history/trend 真实规则；
- 单位分组；
- non-numeric/comparator 处理；
- 小程序页面；
- 图表实现方式和新增依赖（如有）；
- PostgreSQL 集成结果；
- 自动测试；
- 人工验收；
- 已知问题；
- 设计偏差；
- Stage 07 边界。

---

# 45. Definition of Done

Stage 06 只有同时满足以下条件才可判定 PASS：

```text
“我的指标”只读正式 LabResult
+
HealthProfile 隔离正确
+
standard_metric_id=NULL 完全排除跨报告聚合
+
latest 定义稳定且非数值可成为最新结果
+
完整 history 保留同日多份/多单位/非数值
+
普通 trend 只绘制确定数值点
+
< / > / ≤ / ≥ 不伪装为精确点
+
不同单位不混线且不做任意换算
+
参考范围/abnormal 不被重新推断
+
趋势点可追溯至正式报告和原图
+
MetricFavorite 轻量关注可用且按 HealthProfile 隔离
+
报告迁移/删除后指标数据自然变化
+
不建立 Trend/History/Latest 冗余业务表
+
不扩 StandardMetric、不实现 MetricAlias/后台
+
Stage 00～05 回归通过
+
PostgreSQL 17 migration/integration 通过
+
Backend tests/Ruff 通过
+
Miniapp tests/typecheck/build 通过
+
Admin typecheck/build 通过
+
项目负责人真实微信人工验收全部通过
+
RESULT.md 完整
```

任何 P0 验收项未完成：

```text
Stage 06 = FAIL
```

不得使用：

```text
页面能打开
图能画出来
Mock 数据看起来正常
只测一个单位
只测数字结果
SQLite 单测通过
```

替代正式 Stage 06 验收闭环。
