# Stage 06｜我的指标 / 指标历史与趋势｜ACCEPTANCE

> 本文件是 Stage 06 的正式验收基线。除明确说明外均为 P0。任何 P0 未通过，Stage 06 不得标记 PASS。

---

# A. 阶段边界与 migration

## A01｜只从 Stage 05 PASS 基线继续【P0】

实施前确认当前 `main` 的 Stage 05 `RESULT.md` 为正式 PASS，并检查真实代码，不基于旧对话假设。

- PASS
- FAIL

## A02｜存在独立 Stage 06 migration【P0】

新增 Stage 06 migration，`down_revision` 指向当前真实唯一 head `0005_report_management`。

- PASS
- FAIL

## A03｜新增 MetricFavorite【P0】

数据库存在正式 `MetricFavorite / metric_favorites` 数据模型。

- PASS
- FAIL

## A04｜MetricFavorite 唯一约束【P0】

必须保证：

```text
UNIQUE(health_profile_id, standard_metric_id)
```

- PASS
- FAIL

## A05｜MetricFavorite 不冗余 user/report/latest【P0】

不得为了方便查询新增不必要的：

```text
user_id
report_id
latest_result_id
```

- PASS
- FAIL

## A06｜LabResult 存在合理 profile+metric 查询索引【P0】

Stage 06 migration 增加适合当前查询的复合索引或证明当前真实索引已满足且文档记录原因。

不得新增趋势业务表替代索引。

- PASS
- FAIL

## A07｜不新增 Trend/History/Latest 业务表【P0】

不得新增：

```text
Trend
MetricHistory
LatestResult
ProfileMetricSummary
MetricSnapshot
TrendCache
```

或等价冗余正式数据表。

- PASS
- FAIL

## A08｜不新增 LabResult latest/trend 冗余字段【P0】

不得增加：

```text
is_latest
trend_group_id
converted_value
```

等本阶段不需要的持久字段。

- PASS
- FAIL

## A09｜Stage 05 正式报告无需回填【P0】

Stage 05 已存在的 `LabReport / LabResult` 升级 0006 后可直接进入 Stage 06 查询。

不得要求重新 OCR / 确认 / commit。

- PASS
- FAIL

---

# B. 正式数据准入与标准指标边界

## B01｜“我的指标”只查询 LabResult【P0】

不得从以下临时域补指标历史：

```text
ReportIngestion
OcrTask
OcrResultItem
ConfirmationItem
```

- PASS
- FAIL

## B02｜必须显式 health_profile_id【P0】

指标列表、详情、历史、趋势、Favorite 都必须明确使用 `health_profile_id`。

- PASS
- FAIL

## B03｜HealthProfile ownership【P0】

查询前验证：

```text
HealthProfile.user_id = current_user.id
HealthProfile.status = ACTIVE
```

- PASS
- FAIL

## B04｜只聚合 standard_metric_id 非空结果【P0】

```text
standard_metric_id IS NULL
```

不得进入“我的指标”。

- PASS
- FAIL

## B05｜NULL 标准指标不进入 history/trend【P0】

`standard_metric_id = NULL` 的正式结果继续可在 Stage 05 报告详情查看，但不得被 Stage 06 聚合。

- PASS
- FAIL

## B06｜禁止 metric_name 字符串聚合 NULL 指标【P0】

不得通过同名、模糊匹配、别名猜测合并 `standard_metric_id = NULL`。

- PASS
- FAIL

## B07｜Stage 06 不扩 StandardMetric 种子【P0】

不得把 PoC 指标库批量导入正式 StandardMetric。

- PASS
- FAIL

## B08｜Stage 06 不实现 MetricAlias【P0】

不存在 Stage 06 新增 MetricAlias 表、API、后台或 OCR alias 回填。

- PASS
- FAIL

## B09｜历史不因 StandardMetric status 隐藏【P0】

Stage 06 查询不得把 `StandardMetric.status = ACTIVE` 作为既往正式历史可见的必要条件。

- PASS
- FAIL

---

# C. 我的指标列表

## C01｜按 profile + StandardMetric 聚合【P0】

每个指标身份唯一由：

```text
health_profile_id + standard_metric_id
```

确定。

- PASS
- FAIL

## C02｜不同单位不拆成多个指标卡片【P0】

同一个 StandardMetric 即使有多个单位，列表仍只有一个指标卡片。

- PASS
- FAIL

## C03｜只展示真实出现过的指标【P0】

当前 HealthProfile 从未产生正式 LabResult 的 StandardMetric 不出现在“我的指标”。

- PASS
- FAIL

## C04｜history_count 正确【P0】

列表历史总数必须等于该 profile + StandardMetric 下正式 LabResult 数量。

- PASS
- FAIL

## C05｜列表返回标准指标身份【P0】

至少包括：

```text
id
code
name
```

- PASS
- FAIL

## C06｜列表返回 Favorite 状态【P0】

关注状态与当前 HealthProfile 对应。

- PASS
- FAIL

## C07｜列表返回 latest【P0】

每个指标存在最新正式结果摘要。

- PASS
- FAIL

## C08｜最新主值使用 result_text【P0】

不得用重新拼接的 numeric/comparator 覆盖正式 `result_text`。

- PASS
- FAIL

## C09｜列表分页【P0】

服务端支持 page/page_size/total/has_more。

- PASS
- FAIL

## C10｜列表 Favorite 优先【P0】

已关注指标排在未关注指标之前。

- PASS
- FAIL

## C11｜同 Favorite 状态按最近检测优先【P0】

不按 abnormal 风险程度排序。

- PASS
- FAIL

## C12｜列表 empty 语义正确【P0】

有正式报告但没有任何可聚合 StandardMetric 时，不错误显示“没有报告”。

- PASS
- FAIL

---

# D. 最新结果定义

## D01｜主排序使用 examination_date【P0】

最新结果首先按：

```text
examination_date DESC
```

- PASS
- FAIL

## D02｜同日优先 examination_time【P0】

```text
examination_time DESC NULLS LAST
```

- PASS
- FAIL

## D03｜技术 tie-breaker 稳定【P0】

检验时间无法区分时使用稳定 tie-breaker，例如 PLAN 冻结的 report created/id + result sequence/id。

- PASS
- FAIL

## D04｜不把上传/OCR/commit 时间当医学最新时间【P0】

这些字段只能作为无法区分时的技术 tie-breaker，不能替代检验时间。

- PASS
- FAIL

## D05｜非数值可以成为最新结果【P0】

最新一条为“阴性/阳性”等非数值时，列表必须显示该真实最新结果。

- PASS
- FAIL

## D06｜最新结果不得退回最新数值【P0】

不能因为最新结果无法绘图而展示更早的数值结果作为 latest。

- PASS
- FAIL

## D07｜同日多份报告不覆盖【P0】

准备同一日多份包含同 StandardMetric 的正式报告，latest 选择稳定，history 中全部保留。

- PASS
- FAIL

---

# E. 指标详情与历史

## E01｜详情显式绑定 profile + metric【P0】

不能只根据 StandardMetric 跨 HealthProfile 查询。

- PASS
- FAIL

## E02｜不存在历史则 PROFILE_METRIC_NOT_FOUND【P0】

当前 profile 没有该指标正式历史时，不伪造空指标详情。

- PASS
- FAIL

## E03｜历史包含全部正式结果【P0】

包括：

- 数值；
- 非数值；
- comparator；
- 多单位；
- 同日多份。

- PASS
- FAIL

## E04｜历史不去重【P0】

不得同日去重、同值去重或按 report 去重。

- PASS
- FAIL

## E05｜历史不平均【P0】

不得将同日多次结果平均后只显示一条。

- PASS
- FAIL

## E06｜历史最近在前【P0】

排序符合 PLAN 冻结规则。

- PASS
- FAIL

## E07｜历史分页【P0】

支持服务端分页和加载更多。

- PASS
- FAIL

## E08｜历史保留正式 result_text【P0】

主展示值使用正式文本。

- PASS
- FAIL

## E09｜历史单位信息完整【P0】

能返回 original/normalized 或等价数据，并提供用户展示单位。

- PASS
- FAIL

## E10｜历史 reference_text 正确【P0】

每条记录使用自身参考范围，不使用全局范围。

- PASS
- FAIL

## E11｜历史 abnormal 直接读取【P0】

不得重新计算。

- PASS
- FAIL

## E12｜历史可进入正式报告【P0】

每条历史具有 report_id 并可打开 Stage 05 正式详情。

- PASS
- FAIL

## E13｜正式报告原图链路复用【P0】

从历史进入报告后仍可查看 Stage 05 原始报告，不新增第二套原图实现。

- PASS
- FAIL

---

# F. 趋势可绘制规则

## F01｜只有 result_numeric 非空才可能画【P0】

- PASS
- FAIL

## F02｜普通数值 comparator NULL 可画【P0】

- PASS
- FAIL

## F03｜普通数值 comparator 空串可画【P0】

如真实数据允许空串，行为与 PLAN 一致。

- PASS
- FAIL

## F04｜comparator '=' 可画【P0】

- PASS
- FAIL

## F05｜`<` 不画普通精确点【P0】

例如 `<0.10` 只能进历史。

- PASS
- FAIL

## F06｜`>` 不画普通精确点【P0】

- PASS
- FAIL

## F07｜`<= / ≤` 不画普通精确点【P0】

- PASS
- FAIL

## F08｜`>= / ≥` 不画普通精确点【P0】

- PASS
- FAIL

## F09｜非数值不强制转换为数字【P0】

阴性/阳性/未检出等不映射成 0/1。

- PASS
- FAIL

## F10｜趋势层不重新解析 result_text【P0】

`result_numeric = NULL` 时，即使文本看似数字，也不由 Stage 06 补解析。

- PASS
- FAIL

## F11｜无可绘制点是正常空状态【P0】

页面显示“暂无可绘制数值趋势，历史结果仍可查看”或等价明确文案。

- PASS
- FAIL

## F12｜趋势 points 全部绑定 lab_result_id/report_id【P0】

不得只用日期作为 point identity。

- PASS
- FAIL

## F13｜同日多点全部返回【P0】

同一天两个或更多可绘制结果不得被图表数据层合并。

- PASS
- FAIL

## F14｜趋势正序【P0】

series points 按 PLAN 冻结的时间正序稳定返回。

- PASS
- FAIL

## F15｜NULL examination_time 不虚构时间【P0】

不得补成 00:00/12:00 或上传时间。

- PASS
- FAIL

## F16｜图表坐标来自已持久化 numeric【P0】

`value` 仅由正式 `result_numeric` 得出。

- PASS
- FAIL

## F17｜用户点值仍显示 result_text【P0】

图上点选摘要不应用 float 格式覆盖正式文本。

- PASS
- FAIL

## F18｜趋势点可回正式报告【P0】

点击/选择点后可进入对应 Stage 05 report detail。

- PASS
- FAIL

---

# G. 单位分组

## G01｜unit_normalized 优先【P0】

非空时使用 trim 后 `unit_normalized` 作为趋势分组单位。

- PASS
- FAIL

## G02｜normalized 缺失回退 original【P0】

`unit_normalized` NULL/空时使用 trim 后 `unit_original`。

- PASS
- FAIL

## G03｜两者都缺失进入“无单位”序列【P0】

数值仍可正常画图。

- PASS
- FAIL

## G04｜不同单位不混入同一 series【P0】

- PASS
- FAIL

## G05｜不进行跨单位换算【P0】

不得出现任意：

```text
mg/dL → mmol/L
/μL → ×10^9/L
```

等 Stage 06 新换算逻辑。

- PASS
- FAIL

## G06｜不做单位语义猜测【P0】

除 trim 外不把不同文本强行判断为等价单位。

- PASS
- FAIL

## G07｜同 StandardMetric 多单位仍只有一个详情【P0】

- PASS
- FAIL

## G08｜多单位可切换【P0】

用户可以分别查看每个单位的折线序列。

- PASS
- FAIL

## G09｜默认选择最近可绘制序列【P0】

默认单位序列包含该指标最近一个可绘制数值点。

- PASS
- FAIL

## G10｜历史不按单位拆散【P0】

完整历史仍按时间统一展示。

- PASS
- FAIL

---

# H. 参考范围与 abnormal

## H01｜不创建 StandardMetric 全局参考范围【P0】

- PASS
- FAIL

## H02｜不画固定全局正常带【P0】

- PASS
- FAIL

## H03｜每条历史保留自身 reference_text【P0】

- PASS
- FAIL

## H04｜趋势点详情使用自身 reference_text【P0】

- PASS
- FAIL

## H05｜abnormal 不重新计算【P0】

- PASS
- FAIL

## H06｜abnormal NULL 不显示为“正常”【P0】

- PASS
- FAIL

## H07｜不生成医学趋势结论【P0】

不得自动显示：

```text
持续升高
恶化
改善
高风险
建议就医
```

- PASS
- FAIL

---

# I. MetricFavorite

## I01｜Favorite 属于 HealthProfile + StandardMetric【P0】

- PASS
- FAIL

## I02｜关注幂等【P0】

重复 PUT 不产生重复记录或 500。

- PASS
- FAIL

## I03｜取消关注幂等【P0】

重复 DELETE 安全。

- PASS
- FAIL

## I04｜Favorite 跨 HealthProfile 隔离【P0】

父亲关注 WBC 不影响母亲 WBC。

- PASS
- FAIL

## I05｜报告迁移不迁移 Favorite【P0】

- PASS
- FAIL

## I06｜报告删除不自动删除 Favorite【P0】

- PASS
- FAIL

## I07｜dormant Favorite 可保留【P0】

删除/迁移最后一条结果后 Favorite 数据可以继续存在。

- PASS
- FAIL

## I08｜无历史 dormant Favorite 不显示空卡片【P0】

“我的指标”仍只展示当前有正式 LabResult 的指标。

- PASS
- FAIL

## I09｜历史重新出现后 Favorite 状态恢复【P0】

同 profile 后续再次产生该 StandardMetric 正式结果时，列表自然显示已关注。

- PASS
- FAIL

## I10｜Stage 06 不实现关注提醒【P0】

不存在阈值、消息、定时提醒等功能。

- PASS
- FAIL

---

# J. HealthProfile 与跨用户隔离

## J01｜指标列表跨用户隔离【P0】

- PASS
- FAIL

## J02｜指标详情跨用户隔离【P0】

- PASS
- FAIL

## J03｜history 跨用户隔离【P0】

- PASS
- FAIL

## J04｜trend 跨用户隔离【P0】

- PASS
- FAIL

## J05｜Favorite PUT 跨用户隔离【P0】

- PASS
- FAIL

## J06｜Favorite DELETE 跨用户隔离【P0】

- PASS
- FAIL

## J07｜无资源存在性泄露【P0】

跨用户请求不得通过差异化敏感信息暴露对方指标/关注是否存在。

- PASS
- FAIL

## J08｜切换默认 HealthProfile 后页面刷新【P0】

真实小程序从父亲切到母亲后，“我的指标”重新加载。

- PASS
- FAIL

## J09｜旧 profile 响应不能覆盖新 profile【P0】

慢请求场景下不得出现切换后又闪回前一个成员数据。

- PASS
- FAIL

---

# K. 报告迁移与删除后的自然一致性

## K01｜迁移后源 profile 指标历史减少【P0】

- PASS
- FAIL

## K02｜迁移后目标 profile 指标历史增加【P0】

- PASS
- FAIL

## K03｜迁移后 latest 自然重算【P0】

无需额外同步表。

- PASS
- FAIL

## K04｜迁移后 trend 自然变化【P0】

- PASS
- FAIL

## K05｜迁移不创建 Trend/History 同步任务【P0】

- PASS
- FAIL

## K06｜删除非最新报告后 history/trend 减少【P0】

- PASS
- FAIL

## K07｜删除最新报告后 latest 回退到下一条正式结果【P0】

- PASS
- FAIL

## K08｜删除最后一条标准指标结果后列表消失【P0】

- PASS
- FAIL

## K09｜删除后无需等待 COS cleanup 才更新指标【P0】

只要数据库 LabResult 已删除，Stage 06 查询立即变化。

- PASS
- FAIL

## K10｜其它报告/指标不受影响【P0】

- PASS
- FAIL

---

# L. API 与响应语义

## L01｜存在 profile metrics 列表 API【P0】

至少等价于：

```text
GET /api/v1/profile-metrics
```

- PASS
- FAIL

## L02｜存在 profile metric detail API【P0】

- PASS
- FAIL

## L03｜存在 history API【P0】

- PASS
- FAIL

## L04｜存在 trend API【P0】

- PASS
- FAIL

## L05｜存在 Favorite PUT/DELETE API【P0】

- PASS
- FAIL

## L06｜PROFILE_NOT_FOUND 稳定错误【P0】

- PASS
- FAIL

## L07｜STANDARD_METRIC_NOT_FOUND 稳定错误【P0】

- PASS
- FAIL

## L08｜PROFILE_METRIC_NOT_FOUND 稳定错误【P0】

- PASS
- FAIL

## L09｜普通 API 不返回 COS object key【P0】

- PASS
- FAIL

## L10｜普通 API 不返回永久 COS URL【P0】

- PASS
- FAIL

## L11｜普通 API 不返回 OCR 全文【P0】

- PASS
- FAIL

## L12｜日志不记录完整 history/trend 医疗数组【P0】

- PASS
- FAIL

---

# M. 小程序“我的指标”页面

## M01｜从报告视角可进入“我的指标”【P0】

Stage 05 检验报告入口可以清晰切换/进入我的指标。

- PASS
- FAIL

## M02｜可从“我的指标”回到检验报告【P0】

- PASS
- FAIL

## M03｜当前 HealthProfile 清晰展示【P0】

- PASS
- FAIL

## M04｜支持切换健康档案入口【P0】

- PASS
- FAIL

## M05｜loading【P0】

- PASS
- FAIL

## M06｜empty【P0】

- PASS
- FAIL

## M07｜error/retry【P0】

- PASS
- FAIL

## M08｜加载更多【P0】

- PASS
- FAIL

## M09｜指标卡片展示最新正式 result_text【P0】

- PASS
- FAIL

## M10｜指标卡片展示日期/单位/abnormal 提示【P0】

- PASS
- FAIL

## M11｜Favorite 状态可见【P0】

- PASS
- FAIL

## M12｜点击进入指标详情【P0】

- PASS
- FAIL

---

# N. 小程序指标详情 / 趋势

## N01｜StandardMetric 名称/code 正确【P0】

- PASS
- FAIL

## N02｜最新结果正确【P0】

- PASS
- FAIL

## N03｜Favorite 可关注【P0】

- PASS
- FAIL

## N04｜Favorite 可取消【P0】

- PASS
- FAIL

## N05｜数值 trend 正常显示【P0】

- PASS
- FAIL

## N06｜多单位可切换【P0】

- PASS
- FAIL

## N07｜无可绘制点显示正常空状态【P0】

- PASS
- FAIL

## N08｜同日多点不合并【P0】

- PASS
- FAIL

## N09｜点击 trend point 可查看真实结果摘要【P0】

- PASS
- FAIL

## N10｜trend point 可打开正式报告【P0】

- PASS
- FAIL

## N11｜完整历史列表正常显示【P0】

- PASS
- FAIL

## N12｜非数值历史正常显示【P0】

- PASS
- FAIL

## N13｜comparator 历史正常显示【P0】

- PASS
- FAIL

## N14｜历史项可打开正式报告【P0】

- PASS
- FAIL

## N15｜报告原图继续可查看【P0】

- PASS
- FAIL

## N16｜不显示自动医学解释【P0】

- PASS
- FAIL

---

# O. Backend 自动验证

## O01｜Backend Tests【P0】

从 `backend` 运行仓库当前标准命令，例如：

```text
.venv/Scripts/python.exe -m pytest -q
```

全部现有 + Stage 06 测试通过。

不得删除、skip 或弱化 Stage 00～05 测试制造 PASS。

- PASS
- FAIL

## O02｜Backend Ruff【P0】

运行仓库当前标准 Ruff 命令。

- PASS
- FAIL

## O03｜只正式数据聚合测试【P0】

未 commit ingestion 不进入指标。

- PASS
- FAIL

## O04｜NULL StandardMetric 排除测试【P0】

- PASS
- FAIL

## O05｜latest 排序测试【P0】

覆盖同日、有时间、无时间、稳定 tie-breaker。

- PASS
- FAIL

## O06｜非数值 latest 测试【P0】

- PASS
- FAIL

## O07｜同日多份 history 测试【P0】

- PASS
- FAIL

## O08｜comparator trend 排除测试【P0】

- PASS
- FAIL

## O09｜non-numeric trend 排除测试【P0】

- PASS
- FAIL

## O10｜unit_normalized 优先测试【P0】

- PASS
- FAIL

## O11｜unit_original fallback 测试【P0】

- PASS
- FAIL

## O12｜无单位 trend 测试【P0】

- PASS
- FAIL

## O13｜多单位不混线测试【P0】

- PASS
- FAIL

## O14｜abnormal 不重算测试【P0】

- PASS
- FAIL

## O15｜Favorite 幂等/唯一约束测试【P0】

- PASS
- FAIL

## O16｜跨用户六类接口测试【P0】

列表、详情、history、trend、favorite PUT、favorite DELETE。

- PASS
- FAIL

## O17｜迁移后 Stage 06 自然变化测试【P0】

- PASS
- FAIL

## O18｜删除后 Stage 06 自然变化测试【P0】

- PASS
- FAIL

---

# P. PostgreSQL 17 集成验证

## P01｜0005 → 0006 migration【P0】

真实 PostgreSQL 17 临时库验证通过。

- PASS
- FAIL

## P02｜空库完整 migration【P0】

```text
0001 → ... → 0006
```

通过。

- PASS
- FAIL

## P03｜Stage 05 既有正式报告升级后直接聚合【P0】

- PASS
- FAIL

## P04｜MetricFavorite UNIQUE 生效【P0】

并发或重复插入不能产生重复 favorite。

- PASS
- FAIL

## P05｜同日多份结果 PostgreSQL 排序正确【P0】

- PASS
- FAIL

## P06｜NULL examination_time 排序正确【P0】

符合 PLAN 的 DESC NULLS LAST / trend ASC NULLS FIRST 语义。

- PASS
- FAIL

## P07｜多单位分组正确【P0】

- PASS
- FAIL

## P08｜迁移后 profile aggregation 正确【P0】

- PASS
- FAIL

## P09｜删除后 latest/history/trend 正确【P0】

- PASS
- FAIL

## P10｜临时 PostgreSQL 测试库全部删除【P0】

- PASS
- FAIL

---

# Q. Miniapp 自动验证

## Q01｜Miniapp Tests【P0】

```text
pnpm test
```

- PASS
- FAIL

## Q02｜Miniapp Typecheck【P0】

```text
pnpm typecheck
```

- PASS
- FAIL

## Q03｜Miniapp Build【P0】

```text
pnpm build:mp-weixin
```

- PASS
- FAIL

## Q04｜分页合并测试【P0】

- PASS
- FAIL

## Q05｜多单位默认选择测试【P0】

- PASS
- FAIL

## Q06｜同日 point identity 不去重测试【P0】

- PASS
- FAIL

## Q07｜HealthProfile 切换旧响应保护【P0】

- PASS
- FAIL

## Q08｜如果新增图表依赖，lockfile 与构建一致【P0】

未新增依赖则记录为 N/A，不算 FAIL。

- PASS
- FAIL
- N/A

---

# R. Admin 回归

## R01｜Admin Typecheck【P0】

```text
pnpm typecheck
```

- PASS
- FAIL

## R02｜Admin Build【P0】

```text
pnpm build
```

- PASS
- FAIL

## R03｜未实现 StandardMetric 后台【P0】

- PASS
- FAIL

## R04｜未实现 MetricAlias 后台【P0】

- PASS
- FAIL

---

# S. Stage 00～05 回归

## S01｜Stage 04 commit 幂等仍通过【P0】

- PASS
- FAIL

## S02｜REVIEW_PENDING 阻断仍通过【P0】

- PASS
- FAIL

## S03｜KEEP_ORIGINAL_NAME 仍通过【P0】

且对应 `standard_metric_id=NULL` 不进入 Stage 06 聚合。

- PASS
- FAIL

## S04｜纯手工报告仍可 commit【P0】

- PASS
- FAIL

## S05｜疑似重复保存仍通过【P0】

- PASS
- FAIL

## S06｜OcrResultItem 不可变仍通过【P0】

- PASS
- FAIL

## S07｜Stage 05 正式报告列表/详情仍通过【P0】

- PASS
- FAIL

## S08｜Stage 05 原图 preview 仍通过【P0】

- PASS
- FAIL

## S09｜Stage 05 报告迁移仍通过【P0】

- PASS
- FAIL

## S10｜Stage 05 报告删除/FileCleanup 仍通过【P0】

- PASS
- FAIL

---

# T. 真实微信小程序人工验收

以下必须由项目负责人真实执行。Codex、自动测试、接口调用或构建成功不能替代。

## T01｜我的指标 + HealthProfile 切换【P0】

准备两个 HealthProfile，且至少一个有多个可聚合标准指标。

验证：

```text
首页
→ 检验报告
→ 我的指标
```

检查：

- 当前档案正确；
- 指标卡片来自正式报告；
- latest 正确；
- 切换另一个 HealthProfile 后数据完全切换；
- 不串档案。

- PASS
- FAIL

## T02｜最新结果 + 完整历史【P0】

选择当前已有 StandardMetric 覆盖的真实测试指标，例如 WBC / HGB / ALT。

准备至少 3 条正式历史。

核对：

- 最新结果正确；
- 日期正确；
- 历史全部保留；
- 单位/参考范围/abnormal 显示来自原正式结果；
- 点击历史可进入正确正式报告；
- 原图可继续查看。

- PASS
- FAIL

## T03｜同一天多份报告【P0】

准备同一天至少两份含同一 StandardMetric 的正式报告。

确认：

- history 中两条都存在；
- trend 中两个点都存在；
- 没有平均、覆盖或去重；
- 两个点都能追溯到各自报告。

- PASS
- FAIL

## T04｜非数值与 comparator【P0】

准备至少：

```text
一个非数值结果
一个 < / > / ≤ / ≥ 结果
```

确认：

- 两者都正常出现在历史；
- 如果是最新记录，可以成为 latest；
- 不被当作普通精确折线点；
- 页面没有错误或误导文案。

- PASS
- FAIL

## T05｜普通数值趋势【P0】

准备至少 3 个同单位、可绘制确定数值点。

确认：

- 折线顺序正确；
- 数值点正确；
- 日期正确；
- 点击点可看到正式 result_text；
- 可进入对应正式报告。

- PASS
- FAIL

## T06｜多单位趋势【P0】

准备同一 StandardMetric 至少两个不同单位序列。

确认：

- 仍只有一个指标详情；
- 历史统一展示；
- 趋势单位可切换；
- 两个单位没有被直接连成同一条折线；
- 系统没有自动换算数值。

- PASS
- FAIL

## T07｜Favorite【P0】

验证：

```text
未关注
→ 关注
→ 返回列表
→ 已关注优先
→ 再进入
→ 取消关注
```

并切换另一个 HealthProfile，确认关注状态互不影响。

- PASS
- FAIL

## T08｜正式报告迁移后的自然变化【P0】

选择一份包含目标 StandardMetric 的测试报告：

```text
源 HealthProfile
→ 记录迁移前 latest/history/trend
→ Stage 05 迁移到目标 HealthProfile
→ 返回 Stage 06
```

确认：

- 源档案对应结果消失；
- 目标档案对应结果出现；
- latest/history/trend 自动变化；
- 无需额外刷新同步任务；
- Favorite 没有被自动迁移。

- PASS
- FAIL

## T09｜正式报告删除后的自然变化【P0】

删除当前指标的一份测试正式报告。

确认：

- history 对应条目消失；
- trend 对应点消失；
- 删除的是最新报告时 latest 正确回退；
- 删除最后一条时指标从列表消失；
- 其它指标/报告不受影响。

- PASS
- FAIL

---

# U. Stage 07 / OCR 边界

## U01｜未实现 MetricAlias 数据模型【P0】

- PASS
- FAIL

## U02｜未实现 StandardMetric 管理 API/UI【P0】

- PASS
- FAIL

## U03｜未扩充 StandardMetric 种子库【P0】

- PASS
- FAIL

## U04｜未批量回填历史 standard_metric_id【P0】

- PASS
- FAIL

## U05｜未修改 OCR metric matching【P0】

- PASS
- FAIL

## U06｜未修改 AUTO/REVIEW threshold【P0】

- PASS
- FAIL

## U07｜未实现 AI 趋势解释/健康评分【P0】

- PASS
- FAIL

## U08｜未进行任意跨单位数值换算【P0】

- PASS
- FAIL

## U09｜未提供正式 LabResult 编辑【P0】

- PASS
- FAIL

## U10｜未大规模重构 UI【P0】

Stage 06 仅保证功能可用和必要交互。

- PASS
- FAIL

---

# V. 文档与 RESULT

## V01｜README/必要技术说明一致【P0】

如果新增图表依赖、页面、后台运行要求或 migration 使用说明，应同步必要 README。

- PASS
- FAIL

## V02｜Stage 06 RESULT.md 完整【P0】

最终 RESULT 至少记录：

- 实际完成内容；
- 实际修改文件；
- migration；
- MetricFavorite；
- profile metrics APIs；
- latest/history/trend 实际规则；
- unit series；
- comparator/non-numeric 实际处理；
- 小程序页面；
- 图表实现方式/依赖；
- PostgreSQL 集成；
- 自动测试；
- 人工验收；
- 已知问题；
- 设计偏差；
- Stage 07 边界。

- PASS
- FAIL

## V03｜人工验收未完成前不得标 PASS【P0】

即使自动测试全部通过，只要 T01～T09 未由项目负责人真实微信验收：

```text
Stage 06 != PASS
```

- PASS
- FAIL

---

# Z. 最终判定

Stage 06 只有以下全部满足才能：

```text
Stage 06 = PASS
```

必须同时满足：

```text
A～V 全部 P0 PASS

+
只消费正式 LabResult
+
HealthProfile 隔离正确
+
standard_metric_id=NULL 不进入跨报告聚合
+
我的指标 distinct StandardMetric 聚合正确
+
latest 定义正确
+
非数值可成为 latest
+
同日多份历史完整
+
history 不去重/不平均
+
trend 只绘制确定数值
+
< / > / ≤ / ≥ 不作为普通精确点
+
不同单位不混线、不换算
+
参考范围属于单次结果
+
abnormal 不重新推断
+
趋势点可追溯正式报告和原图
+
MetricFavorite 按 HealthProfile 隔离且幂等
+
迁移/删除后指标数据自然变化
+
不存在 Trend/History/Latest 冗余业务表
+
StandardMetric / MetricAlias Stage 07 边界未突破
+
Stage 00～05 全量回归
+
PostgreSQL 17 集成 PASS
+
Backend Tests/Ruff PASS
+
Miniapp Tests/Typecheck/Build PASS
+
Admin Typecheck/Build PASS
+
负责人真实微信 T01～T09 全部 PASS
+
RESULT.md 完整
```

任意 P0 未完成：

```text
Stage 06 = FAIL
```

不得使用：

```text
图能显示
测试数据只有一条线
只有数值型指标能用
前端自行处理了单位
Mock 看起来正常
SQLite 测试通过
```

替代 Stage 06 正式验收闭环。
