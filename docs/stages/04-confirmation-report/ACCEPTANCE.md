# Stage 04｜验收标准

**阶段：检验结果人工确认与正式报告生成**

> 本文档是 Stage 04 是否完成的唯一阶段验收基线。所有 P0 项全部 PASS 才允许 Stage 04 = PASS。

* * *

# A. 基线与 Migration

## A01｜Stage 03 已验收能力未被破坏【P0】

验证：

*   微信登录仍正常；
    
*   HealthProfile CRUD / 切换仍正常；
    
*   私有 COS 上传和原图预览仍正常；
    
*   OCR recognize / retry 仍正常；
    
*   PostgreSQL OCR Queue / Worker 仍正常；
    
*   `FINAL_AUTO / FINAL_REVIEW` 仍来自原 OCR Pipeline；
    
*   Stage 03 既有后端测试继续通过；
    
*   miniapp / admin-web 仍可 typecheck/build。
    

不得为了 Stage 04 修改 OCR 安全判定制造更少 REVIEW。

*   PASS
    
*   FAIL
    

* * *

## A02｜0004 Migration 可从 Stage 03 既有数据库升级【P0】

Given：

```

alembic current = 0003_ocr
```

When：

```

alembic upgrade head
```

Then：

*   成功升级到 Stage 04 migration；
    
*   不重写 0001 / 0002 / 0003；
    
*   已有 User / HealthProfile / ReportIngestion / ReportAsset / OcrTask / OcrResultItem 数据不丢失；
    
*   已有 `PENDING_CONFIRMATION` ingestion 保持可用。
    

记录：

```

Command:
Before:
After:
Result:
```

*   PASS
    
*   FAIL
    

* * *

## A03｜干净 PostgreSQL 可完整迁移到 Stage 04【P0】

使用唯一命名临时空数据库执行：

```

0001
→ 0002
→ 0003
→ 0004
```

要求：

*   upgrade head 成功；
    
*   表、索引、外键、唯一约束正确；
    
*   无手工 SQL 隐藏步骤；
    
*   验证后只删除本次临时数据库。
    
*   PASS
    
*   FAIL
    

* * *

## A04｜正式域与临时域数据表保持分离【P0】

数据库中必须明确区分：

```

导入 / OCR / 确认域：
ReportIngestion
ReportAsset
OcrTask
OcrResultItem
ConfirmationItem

正式报告域：
LabReport
LabResult
```

不得为了方便查询合并为一张万能报告表。

*   PASS
    
*   FAIL
    

* * *

# B. Confirmation 工作区初始化

## B01｜Stage 03 既有 PENDING\_CONFIRMATION 可补初始化【P0】

构造或使用 Stage 03 已存在的真实：

```

ReportIngestion.PENDING_CONFIRMATION
+
OcrTask.SUCCEEDED
+
OcrResultItem
+
无 ConfirmationItem
```

首次打开确认 API。

Then：

*   自动初始化 ConfirmationItem；
    
*   不要求重新 OCR；
    
*   ingestion 保持 PENDING\_CONFIRMATION；
    
*   OcrTask / OcrResultItem 不变。
    

如当前本地数据库仍保留 Stage 03 人工验收任务，可优先验证原有任务；自动测试仍必须构造独立 fixture。

*   PASS
    
*   FAIL
    

* * *

## B02｜Confirmation 初始化幂等【P0】

连续多次：

```

GET /ingestions/{id}/confirmation
```

或并发触发初始化。

Then：

*   不重复生成 ConfirmationItem；
    
*   每个 OcrResultItem 最多对应 1 个 ConfirmationItem；
    
*   item 数量稳定。
    

数据库必须存在相应唯一约束。

*   PASS
    
*   FAIL
    

* * *

## B03｜初始化失败不留下半套工作区【P0】

模拟来源异常或事务异常。

Then：

*   不出现部分 OcrResultItem 已初始化、部分未初始化的永久状态；
    
*   可以后续安全重试；
    
*   OcrResultItem 不被修改。
    
*   PASS
    
*   FAIL
    

* * *

## B04｜初始化来源只取成功 OCR 机器快照【P0】

确认：

```

ConfirmationItem
```

来源于成功 `OcrTask` 的 `OcrResultItem`。

不得：

*   从前端传入 OCR 数据初始化；
    
*   从 artifact JSON 绕过 OcrResultItem 重新生成；
    
*   使用失败 OCR run 作为正式确认来源。
    
*   PASS
    
*   FAIL
    

* * *

# C. AUTO / REVIEW 初始化语义

## C01｜FINAL\_AUTO 默认 RESOLVED【P0】

Given：

```

OcrResultItem.final_decision = FINAL_AUTO
```

初始化后：

```

ConfirmationItem.review_status = RESOLVED
source_type = OCR_AUTO
```

用户不需要逐行点击确认。

*   PASS
    
*   FAIL
    

* * *

## C02｜FINAL\_REVIEW 默认 PENDING【P0】

Given：

```

OcrResultItem.final_decision = FINAL_REVIEW
```

初始化后：

```

ConfirmationItem.review_status = PENDING
```

不得因为页面打开或数据已经有候选值自动 resolved。

*   PASS
    
*   FAIL
    

* * *

## C03｜AUTO / REVIEW 数量与 OCR 来源一致【P0】

选取一份同时存在 AUTO 和 REVIEW 的成功 OCR 数据。

验证 Confirmation 初始化后：

*   来源项目总数一致；
    
*   AUTO 项状态正确；
    
*   REVIEW 项状态正确；
    
*   REMOVED / MANUAL 尚未凭空产生。
    
*   PASS
    
*   FAIL
    

* * *

## C04｜初始化使用 Pipeline 最终候选但不覆盖原始名称事实【P0】

抽查至少一项：

*   result\_text；
    
*   result\_numeric；
    
*   comparator；
    
*   normalized unit；
    
*   reference；
    
*   abnormal；
    
*   standard metric candidate。
    

确认 ConfirmationItem 使用可提交候选，同时：

```

OcrResultItem.raw_*
```

保持原值。

*   PASS
    
*   FAIL
    

* * *

# D. OcrResultItem 不可变

## D01｜人工确认正确不修改 OcrResultItem【P0】

保存前后比较来源 OcrResultItem。

必须完全保持机器快照。

*   PASS
    
*   FAIL
    

* * *

## D02｜人工修改不覆盖 OcrResultItem【P0】

将某一 OCR 候选结果从 A 修改为 B。

Then：

```

OcrResultItem = A
ConfirmationItem = B
```

不得：

```

OcrResultItem = B
```

*   PASS
    
*   FAIL
    

* * *

## D03｜删除错误识别不删除 OcrResultItem【P0】

用户删除错误识别后：

```

OcrResultItem 仍存在
ConfirmationItem.resolution = REMOVED
```

*   PASS
    
*   FAIL
    

* * *

## D04｜选择标准指标不修改 OCR standard candidate【P0】

用户手工选择其它正式 StandardMetric。

Then：

*   OcrResultItem 原 candidate 保持不变；
    
*   ConfirmationItem.standard\_metric\_id 记录用户最终选择。
    
*   PASS
    
*   FAIL
    

* * *

# E. REVIEW 五种处理方式

## E01｜确认正确【P0】

对 REVIEW 项选择“确认正确”。

Then：

```

review_status = RESOLVED
resolution = ACCEPTED
```

候选值保持。

*   PASS
    
*   FAIL
    

* * *

## E02｜人工修改【P0】

修改至少：

*   result；
    
*   unit；
    
*   reference；
    

中的一种，并验证指标名称也允许修改。

Then：

```

review_status = RESOLVED
resolution = CORRECTED
source_type = OCR_CORRECTED
```

修改值重新进入页面仍正确。

*   PASS
    
*   FAIL
    

* * *

## E03｜选择标准指标【P0】

对未确定或需调整身份的 REVIEW 项选择正式 StandardMetric。

Then：

```

standard_metric_id = selected metric
review_status = RESOLVED
```

刷新后保持。

*   PASS
    
*   FAIL
    

* * *

## E04｜按原名称保存【P0】

对不存在合适 StandardMetric 的 REVIEW 项选择：

```

按原名称保存
```

Then：

```

standard_metric_id = NULL
review_status = RESOLVED
resolution = KEEP_ORIGINAL_NAME
```

*   PASS
    
*   FAIL
    

* * *

## E05｜删除错误识别【P0】

选择删除。

Then：

```

resolution = REMOVED
review_status = RESOLVED
```

不得物理删除机器来源数据。

*   PASS
    
*   FAIL
    

* * *

# F. AUTO 主动修改

## F01｜AUTO 默认不要求逐项操作【P0】

一份 REVIEW 已全部处理的报告中，即使存在大量 AUTO，没有逐条点击 AUTO，也允许进入最终 commit 条件判断。

整份报告仍必须用户最终点击 commit。

*   PASS
    
*   FAIL
    

* * *

## F02｜AUTO 可以主动编辑【P0】

选择一条 FINAL\_AUTO 项进行修改。

Then：

```

source_type = OCR_CORRECTED
resolution = CORRECTED
review_status = RESOLVED
```

*   PASS
    
*   FAIL
    

* * *

## F03｜AUTO 修改后来源机器值仍可追溯【P0】

验证：

```

OcrResultItem
→ ConfirmationItem
```

同时存在修改前机器值和修改后用户值。

*   PASS
    
*   FAIL
    

* * *

# G. 人工编辑数据安全

## G01｜非数值结果可保存【P0】

至少验证：

```

阴性
阳性
未见异常
```

或等价人工构造非数值结果。

要求：

*   result\_text 正确；
    
*   result\_numeric 可以为 NULL；
    
*   不因无法解析数字拒绝正式保存。
    
*   PASS
    
*   FAIL
    

* * *

## G02｜简单数值可以安全结构化【P0】

人工录入如：

```

3.5
<0.5
```

如果当前实现支持安全解析：

*   result\_text 保留；
    
*   numeric/comparator 正确。
    

不得因为结构化失败丢弃原文本。

*   PASS
    
*   FAIL
    

* * *

## G03｜无法安全解析时不伪造 numeric【P0】

复杂文本结果无法确定时：

```

result_text 保留
result_numeric = NULL
```

不得猜测数值。

*   PASS
    
*   FAIL
    

* * *

## G04｜修改结果后旧 abnormal 不被盲目沿用【P0】

人工改变结果或参考范围后：

*   能安全重新判断则重新计算；
    
*   不能安全判断允许 abnormal = NULL；
    
*   不允许保留明显与新结果矛盾的 OCR abnormal 事实。
    
*   PASS
    
*   FAIL
    

* * *

# H. 报告级信息

## H01｜医院信息可以人工填写或修改【P0】

OCR 没有报告级候选时，医院字段仍可正常人工输入。

不得依赖 `report_candidates` 必须存在。

*   PASS
    
*   FAIL
    

* * *

## H02｜检验日期为正式必填字段【P0】

不填写检验日期执行 commit：

```

INVALID_REPORT_DATE
```

或最终稳定等价错误码。

不得使用上传日期自动补齐并静默保存。

*   PASS
    
*   FAIL
    

* * *

## H03｜检验时间允许为空【P0】

仅有：

```

examination_date
```

没有时间，也可以正常 commit。

*   PASS
    
*   FAIL
    

* * *

## H04｜报告编号允许为空【P0】

没有报告编号不阻止 commit。

*   PASS
    
*   FAIL
    

* * *

## H05｜报告信息退出重进可恢复【P0】

填写报告信息后：

```

离开页面
→ 关闭小程序
→ 再进入
```

数据从服务端恢复。

*   PASS
    
*   FAIL
    

* * *

## H06｜正式报告时间不使用上传时间【P0】

构造：

```

examination_date = 2026-08-01
ingestion.created_at = 2026-09-30
```

commit 后 LabReport / LabResult 正式检验日期必须为：

```

2026-08-01
```

不得变成 2026-09-30。

*   PASS
    
*   FAIL
    

* * *

# I. HealthProfile 调整

## I01｜正式保存前可调整所属档案【P0】

用户拥有：

```

本人
父亲
```

某 ingestion 原属于本人。

在确认页切换到父亲。

Then：

*   ReportIngestion.health\_profile\_id 更新为父亲；
    
*   ConfirmationItem 保留；
    
*   原图不需要重新上传。
    
*   PASS
    
*   FAIL
    

* * *

## I02｜不能调整到他人 HealthProfile【P0】

User A 使用 User B 的 profile id。

必须拒绝且不泄露对方信息。

*   PASS
    
*   FAIL
    

* * *

## I03｜切换档案后重复检测使用新档案【P0】

Profile 修改后，旧 duplicate acknowledgement 不得继续无条件有效。

*   PASS
    
*   FAIL
    

* * *

# J. StandardMetric

## J01｜正式 StandardMetric 基础数据存在【P0】

数据库存在正式 StandardMetric。

至少：

*   code；
    
*   name；
    
*   status；
    
*   code 唯一。
    
*   PASS
    
*   FAIL
    

* * *

## J02｜StandardMetric 可只读查询【P0】

小程序可通过 API：

*   按 name 查询；
    
*   按 code 查询。
    

不得要求管理后台才能完成用户确认流程。

*   PASS
    
*   FAIL
    

* * *

## J03｜OCR candidate 可映射正式 StandardMetric【P0】

当：

```

OcrResultItem.standard_metric_code
```

存在于正式 StandardMetric 时，Confirmation 初始化可以关联对应正式 ID。

*   PASS
    
*   FAIL
    

* * *

## J04｜未知 OCR code 不自动创建 StandardMetric【P0】

构造不存在的 OCR standard code。

Then：

```

ConfirmationItem.standard_metric_id = NULL
```

数据库不得自动新增全局 StandardMetric。

*   PASS
    
*   FAIL
    

* * *

## J05｜不运行时反写 PoC metric\_library【P0】

确认产品启动、Worker 执行、Confirmation 初始化均不会：

```

读取 OCR runtime metric_library
→ 自动 INSERT / UPDATE 正式 StandardMetric
```

正式 seed 与 OCR runtime 解耦。

*   PASS
    
*   FAIL
    

* * *

## J06｜按原名称保存不会进入标准指标身份【P0】

KEEP\_ORIGINAL\_NAME commit 后：

```

LabResult.standard_metric_id = NULL
```

不得因为名称相似自动挂到其它正式指标。

*   PASS
    
*   FAIL
    

* * *

# K. 手工新增漏识别指标

## K01｜可以新增漏识别项目【P0】

在 OCR 报告确认页新增一项。

Then：

```

source_ocr_result_item_id = NULL
source_type = MANUAL
resolution = MANUAL_ADDED
review_status = RESOLVED
```

*   PASS
    
*   FAIL
    

* * *

## K02｜手工项可继续编辑【P0】

新增后修改：

*   metric；
    
*   result；
    
*   unit；
    
*   reference；
    
*   StandardMetric。
    

退出重进后保持。

*   PASS
    
*   FAIL
    

* * *

## K03｜手工项 commit 后生成正式 LabResult【P0】

commit 后存在对应 LabResult：

```

data_source = MANUAL
```

并能追溯到 source ConfirmationItem。

*   PASS
    
*   FAIL
    

* * *

# L. 纯手工报告兜底

## L01｜纯手工模式仍要求原始报告图片【P0】

没有任何有效 ReportAsset 时，不允许直接创建正式纯手工报告。

至少存在 1 张原图。

*   PASS
    
*   FAIL
    

* * *

## L02｜READY 报告可进入手工录入【P0】

上传图片后不运行 OCR，用户选择手工录入。

Then：

```

mode = MANUAL
status = PENDING_CONFIRMATION
```

进入统一 Confirmation 流程。

*   PASS
    
*   FAIL
    

* * *

## L03｜OCR\_FAILED 可转为手工录入【P0】

已有 OCR\_FAILED ingestion。

选择手工录入。

Then：

*   原始图片继续复用；
    
*   失败 OcrTask 保留；
    
*   不覆盖历史错误；
    
*   mode = MANUAL；
    
*   status = PENDING\_CONFIRMATION。
    
*   PASS
    
*   FAIL
    

* * *

## L04｜纯手工报告可以完整 commit【P0】

至少：

```

1 张原图
+
合法检验日期
+
1 条 MANUAL ConfirmationItem
```

能够生成：

```

LabReport
+
LabResult
```

*   PASS
    
*   FAIL
    

* * *

# M. 疑似重复

## M01｜无重复时正常 commit【P0】

数据库没有匹配正式报告。

Then：

*   不显示错误重复提示；
    
*   正常 commit。
    
*   PASS
    
*   FAIL
    

* * *

## M02｜同档案强重复可以识别【P0】

构造已存在正式报告，并使用相同或足够强的：

*   report\_no；
    
*   医院；
    
*   HealthProfile。
    

新报告 commit 时识别为疑似重复。

*   PASS
    
*   FAIL
    

* * *

## M03｜日期 + 医院 + 指标集合组合重复可提示【P0】

构造无可靠 report\_no，但：

```

同 HealthProfile
+
同检验日期
+
同医院
+
指标集合高度重合
```

应进入疑似重复候选。

最终实现阈值必须在 RESULT 记录。

*   PASS
    
*   FAIL
    

* * *

## M04｜疑似重复只提示，不禁止保存【P0】

首次 commit：

```

DUPLICATE_CONFIRM_REQUIRED
```

或等价稳定业务结果。

用户明确选择：

```

仍然保存
```

后允许正常 commit。

*   PASS
    
*   FAIL
    

* * *

## M05｜重复提示不覆盖旧报告【P0】

继续保存后：

*   旧 LabReport 保留；
    
*   新 LabReport 新增；
    
*   不合并；
    
*   不覆盖；
    
*   不平均结果。
    
*   PASS
    
*   FAIL
    

* * *

## M06｜不同 HealthProfile 不互相提示重复【P0】

同样的医院、日期、报告号分别属于：

```

本人
父亲
```

不得当作同一人的重复报告。

*   PASS
    
*   FAIL
    

* * *

## M07｜重复 acknowledgement 对数据修改失效【P0】

流程：

```

检测到重复
→ 用户确认继续
→ 修改日期/档案/报告号/项目
```

再次 commit 必须使用当前数据重新判断。

不得无条件复用旧确认。

*   PASS
    
*   FAIL
    

* * *

# N. commit 准入

## N01｜存在 REVIEW PENDING 时禁止 commit【P0】

只要存在至少一条：

```

review_status = PENDING
```

commit 必须拒绝：

```

REVIEW_PENDING
```

并返回必要 pending count。

*   PASS
    
*   FAIL
    

* * *

## N02｜全部 REVIEW resolved 后可以继续【P0】

所有 REVIEW 分别通过合法处理 resolved。

不得因为还有大量未逐项点击的 AUTO 阻止 commit。

*   PASS
    
*   FAIL
    

* * *

## N03｜没有正式保留项目禁止 commit【P0】

所有项目均：

```

REMOVED
```

或手工报告尚无项目。

commit 返回：

```

NO_REPORT_ITEMS
```

或稳定等价错误。

*   PASS
    
*   FAIL
    

* * *

## N04｜正式项目指标名不能为空【P0】

非 REMOVED 项 metric\_name 为空时拒绝 commit。

*   PASS
    
*   FAIL
    

* * *

## N05｜正式项目结果不能为空【P0】

非 REMOVED 项 result\_text 为空时拒绝 commit。

单位、参考范围允许为空。

*   PASS
    
*   FAIL
    

* * *

## N06｜未匹配 StandardMetric 不阻止 commit【P0】

存在：

```

KEEP_ORIGINAL_NAME
standard_metric_id = NULL
```

只要其它条件满足，整份报告可正常 commit。

*   PASS
    
*   FAIL
    

* * *

# O. commit 事务性

## O01｜LabReport 与 LabResult 单事务生成【P0】

制造 commit 中途异常。

Then：

```

0 LabReport
0 部分 LabResult
ingestion 仍 PENDING_CONFIRMATION
```

不得留下半份正式报告。

*   PASS
    
*   FAIL
    

* * *

## O02｜成功 commit 状态一致【P0】

成功事务后同时满足：

```

1 LabReport
N LabResult
ReportIngestion.status = CONFIRMED
confirmed_at != NULL
```

*   PASS
    
*   FAIL
    

* * *

## O03｜REMOVED 项不生成 LabResult【P0】

ConfirmationItem 保留，但：

```

resolution = REMOVED
→ 0 对应 LabResult
```

*   PASS
    
*   FAIL
    

* * *

## O04｜commit 事务不依赖 COS 写操作【P0】

commit 不进行：

*   原图复制；
    
*   OCR Artifact 复制；
    
*   COS 上传；
    
*   COS 路径迁移。
    

正式报告通过已有资源关系追溯原图。

*   PASS
    
*   FAIL
    

* * *

# P. commit 幂等与并发

## P01｜重复 commit 返回同一正式报告【P0】

同一 ingestion 成功 commit 后再次调用 commit。

Then：

*   返回同一 report\_id；
    
*   LabReport 数量仍为 1；
    
*   LabResult 不重复。
    
*   PASS
    
*   FAIL
    

* * *

## P02｜LabReport source\_ingestion\_id 数据库唯一【P0】

数据库存在：

```

UNIQUE(source_ingestion_id)
```

不能只依赖 Python 代码 if 判断。

*   PASS
    
*   FAIL
    

* * *

## P03｜并发 commit 只生成一份报告【P0】

必须在 PostgreSQL 17 验证。

两个独立 session / 请求同时 commit 同一个 ingestion。

Then：

```

LabReport = 1
LabResult 每个 ConfirmationItem最多 1 条
```

另一个请求返回同一正式报告或等价幂等结果。

*   PASS
    
*   FAIL
    

* * *

## P04｜LabResult source\_confirmation\_item 不重复【P0】

数据库或等价硬约束保证同一 ConfirmationItem 不生成多条正式结果。

*   PASS
    
*   FAIL
    

* * *

## P05｜前端超时重试安全【P0】

模拟：

```

服务端 commit 已成功
前端未收到响应
→ 用户再次点击
```

不得产生重复正式数据。

*   PASS
    
*   FAIL
    

* * *

# Q. LabReport / LabResult 正式数据

## Q01｜LabReport 数据来源正确【P0】

commit 后抽查：

*   HealthProfile；
    
*   hospital；
    
*   examination\_date；
    
*   examination\_time；
    
*   report\_no；
    
*   category；
    
*   source\_ingestion\_id。
    

必须来自最终确认数据。

*   PASS
    
*   FAIL
    

* * *

## Q02｜LabResult 数量正确【P0】

满足：

```

LabResult 数量
=
ConfirmationItem 中非 REMOVED 数量
```

*   PASS
    
*   FAIL
    

* * *

## Q03｜OCR\_AUTO 正式来源正确【P0】

未修改 AUTO 项：

```

LabResult.data_source = OCR_AUTO
```

*   PASS
    
*   FAIL
    

* * *

## Q04｜OCR\_CORRECTED 正式来源正确【P0】

人工修改 OCR 项：

```

LabResult.data_source = OCR_CORRECTED
```

正式值为 ConfirmationItem 最终值，不是旧 OCR 值。

*   PASS
    
*   FAIL
    

* * *

## Q05｜MANUAL 正式来源正确【P0】

手工新增项：

```

LabResult.data_source = MANUAL
```

*   PASS
    
*   FAIL
    

* * *

## Q06｜KEEP\_ORIGINAL\_NAME 正式保存正确【P0】

正式 LabResult：

```

metric_name = 用户确认名称
standard_metric_id = NULL
```

*   PASS
    
*   FAIL
    

* * *

## Q07｜正式检验时间复制正确【P0】

LabResult 中用于未来历史/趋势的日期和时间必须与 LabReport 的检验日期/时间一致。

不得使用 `created_at` 替代。

*   PASS
    
*   FAIL
    

* * *

# R. 完整追溯

## R01｜OCR\_AUTO 链路可追溯【P0】

能够从 LabResult 找到：

```

LabResult
→ ConfirmationItem
→ OcrResultItem
→ OcrTask
→ ReportAsset
```

*   PASS
    
*   FAIL
    

* * *

## R02｜人工修改链路同时保留机器值与人工值【P0】

构造：

```

OCR 值 = A
用户修改 = B
正式值 = B
```

验收：

```

OcrResultItem = A
ConfirmationItem = B
LabResult = B
```

*   PASS
    
*   FAIL
    

* * *

## R03｜REMOVED 仍可审计【P0】

错误 OCR 项：

```

OcrResultItem 保留
ConfirmationItem.REMOVED 保留
无 LabResult
```

*   PASS
    
*   FAIL
    

* * *

## R04｜MANUAL 可追溯到原始报告 ingestion【P0】

手工项虽然没有 OcrResultItem，但仍通过：

```

LabResult
→ ConfirmationItem
→ ReportIngestion
→ ReportAsset
```

关联原始报告。

*   PASS
    
*   FAIL
    

* * *

# S. 权限与安全

## S01｜跨用户读取 Confirmation 被拒绝【P0】

User A 不得读取 User B confirmation。

不得泄露 B 是否存在该资源。

*   PASS
    
*   FAIL
    

* * *

## S02｜跨用户修改 ConfirmationItem 被拒绝【P0】

User A 不得 PATCH User B item。

*   PASS
    
*   FAIL
    

* * *

## S03｜跨用户手工新增被拒绝【P0】

User A 不得向 User B ingestion 添加 MANUAL item。

*   PASS
    
*   FAIL
    

* * *

## S04｜跨用户修改报告信息被拒绝【P0】

包括：

*   hospital；
    
*   date；
    
*   report\_no；
    
*   health\_profile。
    
*   PASS
    
*   FAIL
    

* * *

## S05｜跨用户 commit 被拒绝【P0】

User A 对 User B ingestion commit：

*   不生成 LabReport；
    
*   不生成 LabResult；
    
*   不泄露报告信息。
    
*   PASS
    
*   FAIL
    

* * *

## S06｜普通日志不泄露医疗全文【P0】

日志不得记录：

*   完整 OCR 全文；
    
*   全部 LabResult；
    
*   完整 Confirmation 内容；
    
*   Token；
    
*   COS Secret；
    
*   永久文件 URL。
    

允许：

*   request\_id；
    
*   user\_id 内部 ID；
    
*   ingestion\_id；
    
*   report\_id；
    
*   status；
    
*   error\_code；
    
*   item count。
    
*   PASS
    
*   FAIL
    

* * *

# T. 小程序确认页面

## T01｜PENDING\_CONFIRMATION 进入真实确认页【P0】

从：

*   OCR 完成页；
    
*   ingestion task 列表；
    
*   重新打开旧任务；
    

进入：

```

/pages/confirmation/...
```

或最终等价路径。

不得继续显示“下一阶段开放”。

*   PASS
    
*   FAIL
    

* * *

## T02｜确认页展示报告级信息【P0】

至少：

*   当前 HealthProfile；
    
*   医院；
    
*   检验日期；
    
*   检验时间；
    
*   报告编号；
    
*   原图入口。
    
*   PASS
    
*   FAIL
    

* * *

## T03｜REVIEW 优先展示且醒目标记【P0】

页面明确展示：

```

待确认 X 项
```

REVIEW 不得和 AUTO 混在一起导致用户难以发现。

*   PASS
    
*   FAIL
    

* * *

## T04｜AUTO 默认采用并可展开编辑【P0】

页面无需逐条确认 AUTO。

但用户能够主动进入编辑。

*   PASS
    
*   FAIL
    

* * *

## T05｜原图可核对【P0】

确认页或指标编辑页可以打开来源原始报告。

使用后端短时鉴权 URL。

不得公开 COS 对象。

*   PASS
    
*   FAIL
    

* * *

## T06｜REVIEW 五种处理均有可达交互【P0】

至少可以完成：

*   确认正确；
    
*   人工修改；
    
*   选择标准指标；
    
*   按原名称保存；
    
*   删除错误识别。
    
*   PASS
    
*   FAIL
    

* * *

## T07｜可以添加漏识别项目【P0】

确认页存在清晰入口并真实写入后端。

*   PASS
    
*   FAIL
    

* * *

## T08｜页面退出重进恢复真实进度【P0】

完成部分 REVIEW 后：

```

退出
→ 重进
```

已完成项不丢失。

*   PASS
    
*   FAIL
    

* * *

## T09｜REVIEW 未完成时最终保存有明确提示【P0】

点击 commit 时如仍有 PENDING：

*   页面提示还有待确认项目；
    
*   不生成正式报告；
    
*   可以定位/回到待确认区域。
    
*   PASS
    
*   FAIL
    

* * *

## T10｜commit 成功只显示最小成功反馈【P0】

例如：

```

报告保存成功
X 项检验结果已保存
```

本阶段不得顺手建设完整正式报告详情。

*   PASS
    
*   FAIL
    

* * *

# U. 纯手工小程序流程

## U01｜READY 可以选择手工录入【P0】

已上传至少 1 张图片时存在明确手工入口。

*   PASS
    
*   FAIL
    

* * *

## U02｜OCR\_FAILED 可以转手工录入【P0】

识别失败后，不强迫重新上传。

用户可以保留现有原图进入手工确认。

*   PASS
    
*   FAIL
    

* * *

## U03｜手工录入复用同一 Confirmation 页面【P0】

不得复制建设第二套平行确认系统。

*   PASS
    
*   FAIL
    

* * *

# V. 自动测试、Lint 与构建

## V01｜Backend Tests【P0】

运行：

```

backend/.venv/Scripts/python.exe -m pytest -q
```

或当前平台等价命令。

要求：

*   Stage 01～03 既有测试继续通过；
    
*   Stage 04 新测试全部通过；
    
*   不删除、skip 或弱化测试制造 PASS。
    

记录：

```

Command:
Tests:
Passed:
Failed:
Warnings:
```

*   PASS
    
*   FAIL
    

* * *

## V02｜Backend Ruff【P0】

运行：

```

backend/.venv/Scripts/ruff.exe check . --no-cache
```

或等价命令。

*   PASS
    
*   FAIL
    

* * *

## V03｜PostgreSQL commit Integration【P0】

单独记录 PostgreSQL 17 集成验证：

*   migration；
    
*   source\_ingestion 唯一；
    
*   source\_confirmation\_item 唯一；
    
*   并发 commit；
    
*   transaction rollback；
    
*   Stage 03 老任务初始化。
    
*   PASS
    
*   FAIL
    

* * *

## V04｜Miniapp Tests【P0】

如本阶段新增了状态路由、confirmation helper、业务状态计算等可测试逻辑，运行对应测试。

不得只依赖人工点击验证核心状态判断。

记录：

```

Command:
Result:
```

*   PASS
    
*   FAIL
    

* * *

## V05｜Miniapp Typecheck【P0】

运行：

```

pnpm typecheck
```

*   PASS
    
*   FAIL
    

* * *

## V06｜Miniapp Build【P0】

运行：

```

pnpm build:mp-weixin
```

*   PASS
    
*   FAIL
    

* * *

## V07｜Admin Web 未被破坏【P0】

至少：

```

pnpm typecheck
pnpm build
```

*   PASS
    
*   FAIL
    

* * *

# W. 真实主流程人工验收

## W01｜Stage 03 OCR 报告完整确认流程【P0】

使用一份存在 AUTO + REVIEW 的真实、脱敏或经许可测试报告。

完成：

```

PENDING_CONFIRMATION
↓
打开确认页
↓
原图可查看
↓
填写/确认报告信息
↓
REVIEW 全部处理
↓
至少修改 1 条 AUTO
↓
至少手工新增 1 条漏识别项目
↓
至少选择 1 次 StandardMetric
↓
至少执行 1 次 KEEP_ORIGINAL_NAME
↓
最终 commit
↓
CONFIRMED
```

人工核对：

*   OcrResultItem 未变化；
    
*   原图仍存在；
    
*   LabReport 正确；
    
*   LabResult 正确；
    
*   数据来源正确；
    
*   未匹配指标 standard\_metric\_id = NULL。
    
*   PASS
    
*   FAIL
    

* * *

## W02｜Stage 03 老任务兼容【P0】

验证升级前已经存在的 `PENDING_CONFIRMATION` 任务。

要求：

```

不重新 OCR
→ 打开确认
→ workspace 初始化
→ 正常完成确认和 commit
```

*   PASS
    
*   FAIL
    

* * *

## W03｜纯手工报告完整流程【P0】

实际完成：

```

上传原图
↓
进入手工录入
↓
填写报告信息
↓
手工新增至少 2 项
↓
commit
```

确认：

*   无 OcrResultItem 也可完成；
    
*   原图仍可追溯；
    
*   LabResult.data\_source = MANUAL。
    
*   PASS
    
*   FAIL
    

* * *

## W04｜疑似重复真实流程【P0】

先正式保存一份测试报告。

再创建疑似相同报告。

验证：

```

提示重复
↓
不自动覆盖
↓
允许返回修改
↓
允许明确“仍然保存”
↓
生成第二份独立正式报告
```

*   PASS
    
*   FAIL
    

* * *

# X. 阶段边界

## X01｜未提前实现 Stage 05 报告管理【P0】

Stage 04 不得新增完整：

*   正式报告列表；
    
*   正式报告详情；
    
*   正式报告删除；
    
*   正式报告迁移；
    
*   报告管理页面体系。
    

commit 成功最小反馈不算 Stage 05 报告详情。

*   PASS
    
*   FAIL
    

* * *

## X02｜未提前实现 Stage 06 指标趋势【P0】

不得新增：

*   我的指标正式页面；
    
*   指标历史；
    
*   趋势折线图；
    
*   Trend 表；
    
*   单位趋势分组；
    
*   关注指标。
    
*   PASS
    
*   FAIL
    

* * *

## X03｜未提前实现 Stage 07 管理后台业务【P0】

不得建设：

*   StandardMetric 管理页面；
    
*   MetricAlias 管理页面；
    
*   OCR 问题排查后台；
    
*   正式医疗数据管理后台。
    

Stage 04 StandardMetric 仅为只读基础数据。

*   PASS
    
*   FAIL
    

* * *

## X04｜没有把 OCR 算法研发混入 Stage 04【P0】

不得通过：

*   修改 OCR threshold；
    
*   修改 AUTO/REVIEW 规则；
    
*   修改 Retry/Evidence 安全规则；
    

来减少人工确认工作。

发现算法问题应记录并回到 PoC / Regression 验证。

*   PASS
    
*   FAIL
    

* * *

# Y. 文档与 RESULT

## Y01｜README 与 Stage 状态更新【P0】

Stage 04 完成时更新必要 README：

*   当前链路已到正式报告生成；
    
*   OCR 后必须人工确认；
    
*   commit 才产生正式数据；
    
*   Stage 05 尚未实现正式报告管理。
    
*   PASS
    
*   FAIL
    

* * *

## Y02｜RESULT.md 完整【P0】

必须记录：

*   实际完成项；
    
*   实际变更文件；
    
*   migration；
    
*   Confirmation 初始化方案；
    
*   StandardMetric seed 来源和边界；
    
*   duplicate 实际规则；
    
*   commit 事务与幂等实现；
    
*   自动测试；
    
*   PostgreSQL 集成验证；
    
*   小程序人工验收；
    
*   纯手工流程；
    
*   Stage 03 老数据兼容；
    
*   已知问题；
    
*   设计偏差；
    
*   Stage 05 注意事项。
    

不得只写：

```

代码完成
```

*   PASS
    
*   FAIL
    

* * *

# Z. 最终判定

Stage 04 只有在以下全部满足时才能标记：

```

PASS
```

必须同时满足：

```

A～Y 所有 P0 = PASS
+
Stage 03 老 PENDING_CONFIRMATION 可无损进入确认
+
OcrResultItem 始终不可变
+
ConfirmationItem 初始化幂等
+
AUTO 默认采用且允许修改
+
REVIEW 全部必须 resolved
+
五种 REVIEW 处理方式通过
+
手工新增漏识别通过
+
纯手工报告通过
+
报告级信息确认通过
+
HealthProfile 保存前调整通过
+
StandardMetric 最小正式主数据通过
+
KEEP_ORIGINAL_NAME 通过
+
疑似重复提示且允许继续保存
+
commit validation 通过
+
PostgreSQL transaction rollback 通过
+
重复/并发 commit 幂等通过
+
LabReport / LabResult 正式生成正确
+
原始图片 → OCR → Confirmation → 正式结果完整追溯
+
正式日期使用 examination_date
+
跨用户权限隔离通过
+
真实小程序主流程通过
+
自动测试 / Ruff / typecheck / build 全部通过
+
RESULT.md 已更新
```

任意 P0 未完成：

```

Stage 04 = FAIL
```

不得以：

```

页面能打开
接口已经写完
SQLite 单测通过
Mock commit 成功
```

替代正式 Stage 04 工程闭环验收。