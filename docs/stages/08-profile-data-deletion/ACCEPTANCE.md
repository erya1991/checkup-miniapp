# Stage 08｜健康档案隐私删除与数据生命周期闭环｜ACCEPTANCE

> 本文是 Stage 08 的冻结验收基线。
>
> **所有适用 P0 必须 PASS，且项目负责人完成真实微信人工验收后，Stage 08 才能最终判定 PASS。**
>
> 工程自动测试、SQLite 单测、API 可调用、页面能打开，均不能替代需要的真实 PostgreSQL 与负责人实机证据。

---

# 1. 验收原则

Stage 08 只验收一个主题：

```text
HealthProfile 完整隐私删除与数据生命周期
```

核心安全目标：

```text
用户明确删除一个 HealthProfile
→ 产品健康数据立即退出查询
→ DB 私有健康数据完整删除
→ 私有文件进入可靠最终清理
→ 不影响其它 HealthProfile
→ 不允许并发重新长出 orphan 数据
```

---

# 2. P0 阻断项总览

以下任一发生，Stage 08 必须 FAIL：

- [ ] HealthProfile 有历史数据时仍只能返回 `PROFILE_HAS_INGESTIONS`
- [ ] 删除后仍存在该 profile 的 LabReport / LabResult
- [ ] 删除后仍存在该 profile 的 MetricFavorite
- [ ] 删除后仍存在该 profile 当前归属的 ingestion / OCR / Confirmation / Asset
- [ ] 任一 ingestion 没有可靠 PREFIX cleanup
- [ ] 活跃上传临时凭据可能在 cleanup DONE 后重新产生孤儿文件
- [ ] `PROCESSING` OCR 可以被直接删除并在之后继续写 artifact
- [ ] 删除中途异常留下半删除状态
- [ ] 跨用户可以查看删除影响或删除他人 profile
- [ ] 删除 profile 误删其它 HealthProfile 的报告 / Favorite / 文件
- [ ] Stage 05 单份报告删除 / cleanup 回归
- [ ] OCR runtime / matcher / threshold / retry 被修改
- [ ] 0001～0007 被改写
- [ ] 负责人真实微信人工验收未完成

---

# A. 基线与范围

## A01｜Stage 07 最终 PASS【P0】

确认当前最新 Stage 07 RESULT 已正式 PASS，且负责人 T01～T13 已完成。

- [ ] PASS
- [ ] FAIL

## A02｜当前 main / HEAD 已重新核对【P0】

实施开始必须记录：

```text
branch
HEAD
origin/main
working tree
```

不得用旧对话中的 SHA 替代真实核对。

- [ ] PASS
- [ ] FAIL

## A03｜按 AGENTS 顺序读取基线【P0】

至少记录已读取：

```text
AGENTS.md
PRODUCT_BASELINE
TECH_BASELINE
DEVELOPMENT_RULES
Stage08 PLAN
Stage08 ACCEPTANCE
Stage07 RESULT
```

并按主题读取 Stage 02～07 RESULT 与架构文档。

- [ ] PASS
- [ ] FAIL

## A04｜Stage 08 只做 HealthProfile 数据生命周期【P0】

不得把以下夹带进本阶段：

```text
UI 总重构
首页 Dashboard
异常推送
AI 解读
账号注销
部署发布
```

- [ ] PASS
- [ ] FAIL

---

# B. Migration

## B01｜存在独立 0008 migration【P0】

新增：

```text
0008_profile_data_deletion
```

或最终等价命名。

down_revision 必须是当前真实：

```text
0007_standard_metric_admin
```

- [ ] PASS
- [ ] FAIL

## B02｜0001～0007 完全未修改【P0】

Git diff 核对所有已应用 migration。

- [ ] PASS
- [ ] FAIL

## B03｜FileCleanup 增加 not_before【P0】

数据库实际存在 nullable：

```text
file_cleanups.not_before
```

或语义完全等价字段。

必须支持 timezone-aware 时间。

- [ ] PASS
- [ ] FAIL

## B04｜历史 cleanup 保持立即语义【P0】

已有 cleanup 升级后：

```text
not_before = NULL
```

NULL 必须表示：

```text
立即可处理
```

- [ ] PASS
- [ ] FAIL

## B05｜Stage 03 已知 index drift 未顺手修复【P0】

当前既有：

```text
ORM ix_ocr_tasks_status
migration ix_ocr_tasks_queue
```

差异不得在 Stage 08 顺手修改。

- [ ] PASS
- [ ] FAIL

## B06｜没有新增复杂 deletion job / recycle bin【P0】

不得新增：

```text
profile_delete_jobs
recycle_bin
soft-delete history
```

除非 PLAN 经负责人重新修改。

- [ ] PASS
- [ ] FAIL

---

# C. Deletion Impact API

## C01｜存在删除影响预览【P0】

存在：

```text
GET /api/v1/health-profiles/{profile_id}/deletion-impact
```

或冻结后最终等价 API。

- [ ] PASS
- [ ] FAIL

## C02｜只允许读取本人 profile【P0】

User A 查询 User B profile：

```text
404 PROFILE_NOT_FOUND
```

- [ ] PASS
- [ ] FAIL

## C03｜返回 profile 最小身份【P0】

至少包含：

```text
id
display_name
```

用于确认删除对象。

- [ ] PASS
- [ ] FAIL

## C04｜report_count 正确【P0】

只统计当前仍归属该 profile 的正式 LabReport。

- [ ] PASS
- [ ] FAIL

## C05｜unfinished_ingestion_count 正确【P0】

未完成 ingestion 数量真实来自数据库。

不得由前端本地列表猜测。

- [ ] PASS
- [ ] FAIL

## C06｜total_ingestion_count 正确【P0】

包括当前仍属于该 profile 的全部 ingestion。

- [ ] PASS
- [ ] FAIL

## C07｜favorite_count 正确【P0】

真实统计 MetricFavorite。

- [ ] PASS
- [ ] FAIL

## C08｜processing_ocr_count 正确【P0】

真实统计：

```text
OcrTask.status = PROCESSING
```

不得只看 ingestion.status。

- [ ] PASS
- [ ] FAIL

## C09｜Impact 不返回医疗明细【P0】

不得返回：

- LabResult；
- 指标名称；
- 结果值；
- 医院；
- report_no；
- OCR payload；
- COS key / URL。

- [ ] PASS
- [ ] FAIL

---

# D. 空 HealthProfile 删除

## D01｜空 profile 可以删除【P0】

没有任何 ingestion / favorite 的 ACTIVE profile：

```text
DELETE
→ 204
```

- [ ] PASS
- [ ] FAIL

## D02｜HealthProfile 行物理删除【P0】

删除后：

```text
SELECT HealthProfile WHERE id = target
→ 0 rows
```

不能只：

```text
status = DELETED
```

- [ ] PASS
- [ ] FAIL

## D03｜删除后列表不可见【P0】

```text
GET /health-profiles
```

不返回目标 profile。

- [ ] PASS
- [ ] FAIL

## D04｜删除后单项读取 404【P0】

```text
GET /health-profiles/{id}
→ PROFILE_NOT_FOUND
```

- [ ] PASS
- [ ] FAIL

---

# E. MetricFavorite 清理

## E01｜目标 profile Favorite 全部删除【P0】

删除前存在 N 条 MetricFavorite。

删除后：

```text
N = 0
```

- [ ] PASS
- [ ] FAIL

## E02｜其它 profile Favorite 不受影响【P0】

同用户其它 HealthProfile 的 Favorite 数量、StandardMetric 关系完全不变。

- [ ] PASS
- [ ] FAIL

## E03｜StandardMetric 不删除【P0】

删除 HealthProfile 前后公共：

```text
StandardMetric
```

数量和目标数据不变。

- [ ] PASS
- [ ] FAIL

## E04｜MetricAlias 不删除【P0】

公共 MetricAlias 不受影响。

- [ ] PASS
- [ ] FAIL

---

# F. 正式报告清理

## F01｜删除目标 profile 全部 LabResult【P0】

删除后目标 profile 原有正式结果全部不存在。

- [ ] PASS
- [ ] FAIL

## F02｜删除目标 profile 全部 LabReport【P0】

删除后目标 profile 原有正式报告全部不存在。

- [ ] PASS
- [ ] FAIL

## F03｜多份正式报告全部清理【P0】

至少构造 2 个不同 ingestion / LabReport。

不得只删除第一份。

- [ ] PASS
- [ ] FAIL

## F04｜OCR 与 MANUAL 正式报告均可清理【P0】

至少覆盖：

```text
OCR 来源报告
MANUAL 来源报告
```

- [ ] PASS
- [ ] FAIL

## F05｜其它 profile 正式报告不受影响【P0】

对比删除前后其它 profile：

- LabReport；
- LabResult；
- 正式值；
- report_id；

完全不变。

- [ ] PASS
- [ ] FAIL

---

# G. Confirmation 清理

## G01｜OCR ConfirmationItem 全部删除【P0】

- [ ] PASS
- [ ] FAIL

## G02｜MANUAL ConfirmationItem 全部删除【P0】

- [ ] PASS
- [ ] FAIL

## G03｜REMOVED ConfirmationItem 也删除【P0】

隐私删除不能因为 `resolution=REMOVED` 就保留工作区历史。

- [ ] PASS
- [ ] FAIL

## G04｜其它 ingestion Confirmation 不受影响【P0】

- [ ] PASS
- [ ] FAIL

---

# H. OCR 数据清理

## H01｜全部 OcrResultItem 删除【P0】

包括成功、失败 retry 历史所对应的所有机器结果。

- [ ] PASS
- [ ] FAIL

## H02｜全部 OcrTask 删除【P0】

包括：

```text
QUEUED
FAILED
SUCCEEDED
retry run
```

PROCESSING 见专门阻断项。

- [ ] PASS
- [ ] FAIL

## H03｜多个 run 全部删除【P0】

至少构造：

```text
run 1 FAILED
run 2 SUCCEEDED
```

删除后均不存在。

- [ ] PASS
- [ ] FAIL

## H04｜删除不是“修改 OCR 快照”【P0】

Stage 08 不新增 UPDATE OcrResultItem 的业务逻辑。

- [ ] PASS
- [ ] FAIL

---

# I. Upload / Asset / Ingestion 清理

## I01｜ReportAsset 全部删除【P0】

- [ ] PASS
- [ ] FAIL

## I02｜UploadAuthorization 全部删除【P0】

包括：

- consumed；
- unconsumed；
- expired；
- 尚未 expired。

- [ ] PASS
- [ ] FAIL

## I03｜ReportIngestion 全部删除【P0】

目标 profile 当前归属的全部 ingestion 最终不存在。

- [ ] PASS
- [ ] FAIL

## I04｜覆盖 UPLOADING【P0】

- [ ] PASS
- [ ] FAIL

## I05｜覆盖 READY【P0】

- [ ] PASS
- [ ] FAIL

## I06｜覆盖 QUEUED【P0】

在没有被 Worker 抢成 PROCESSING 的安全场景可以删除。

- [ ] PASS
- [ ] FAIL

## I07｜覆盖 OCR_FAILED【P0】

- [ ] PASS
- [ ] FAIL

## I08｜覆盖 PENDING_CONFIRMATION【P0】

- [ ] PASS
- [ ] FAIL

## I09｜覆盖 CONFIRMED【P0】

- [ ] PASS
- [ ] FAIL

---

# J. PROCESSING OCR 安全阻断

## J01｜存在 PROCESSING 时 DELETE 返回 409【P0】

稳定错误：

```text
PROFILE_DELETE_BUSY
```

- [ ] PASS
- [ ] FAIL

## J02｜返回最小 processing_count【P0】

允许 details：

```text
processing_count
```

不得返回 OCR 文本。

- [ ] PASS
- [ ] FAIL

## J03｜阻断时 HealthProfile 不变【P0】

- [ ] PASS
- [ ] FAIL

## J04｜阻断时正式数据不变【P0】

- [ ] PASS
- [ ] FAIL

## J05｜阻断时 ingestion / OCR 不变【P0】

- [ ] PASS
- [ ] FAIL

## J06｜阻断时不提交 profile PREFIX cleanup【P0】

数据库不得留下“删除没发生但文件未来会被 cleanup”的危险记录。

- [ ] PASS
- [ ] FAIL

## J07｜OCR 结束后可再次删除【P0】

PROCESSING 转为：

```text
SUCCEEDED / FAILED / 其它允许终态
```

后再次删除可以按正常流程执行。

- [ ] PASS
- [ ] FAIL

---

# K. QUEUED vs Worker Claim

## K01｜真实 PostgreSQL 并发验证【P0】

必须使用 PostgreSQL 17 双 session / Worker 语义。

- [ ] PASS
- [ ] FAIL

## K02｜Deletion 先锁定时 Worker 不得 claim 已删除任务【P0】

最终：

```text
Profile deleted
task deleted
无 OcrResultItem 回写
```

- [ ] PASS
- [ ] FAIL

## K03｜Worker 先 claim 时删除必须转 BUSY【P0】

最终：

```text
task PROCESSING
profile 仍存在
delete rollback
```

- [ ] PASS
- [ ] FAIL

## K04｜不存在“删除成功后任务继续写回”【P0】

这是 Stage 08 安全阻断项。

- [ ] PASS
- [ ] FAIL

---

# L. FileCleanup PREFIX 登记

## L01｜每个 ingestion 都登记 PREFIX cleanup【P0】

如果 profile 有 N 个 ingestion：

```text
本次 profile 删除至少存在 N 个对应 PREFIX cleanup
```

已有等价可复用 cleanup 时允许安全复用，但不得遗漏 ingestion。

- [ ] PASS
- [ ] FAIL

## L02｜prefix 格式正确【P0】

必须为：

```text
users/{user_id}/ingestions/{ingestion_id}/
```

- [ ] PASS
- [ ] FAIL

## L03｜target_type = PREFIX【P0】

- [ ] PASS
- [ ] FAIL

## L04｜初始 status = PENDING【P0】

- [ ] PASS
- [ ] FAIL

## L05｜cleanup 必须在 DB 删除事务提交前持久化【P0】

如果 cleanup INSERT / flush 失败：

```text
整个 profile 删除 rollback
```

- [ ] PASS
- [ ] FAIL

## L06｜不得只删除 ReportAsset object key【P0】

必须是完整 ingestion prefix。

- [ ] PASS
- [ ] FAIL

---

# M. not_before 与临时上传凭据

## M01｜无未来有效授权时 cleanup 可立即 due【P0】

没有：

```text
expires_at > now
```

的 UploadAuthorization 时：

```text
not_before <= now
```

或使用 NULL 表示立即 due，须在 RESULT 明确实际实现。

- [ ] PASS
- [ ] FAIL

## M02｜存在未来授权时 not_before 覆盖最大 expires_at【P0】

至少：

```text
not_before > max(expires_at)
```

- [ ] PASS
- [ ] FAIL

## M03｜包含安全余量【P0】

最终实现必须包含明确的小型 clock-skew/safety grace。

PLAN 推荐：

```text
60 seconds
```

实际值必须记录 RESULT。

- [ ] PASS
- [ ] FAIL

## M04｜consumed 但未过期凭据仍纳入窗口【P0】

不能假设 consumed 后 STS Token 立刻物理失效。

- [ ] PASS
- [ ] FAIL

## M05｜not_before 前 worker 不标 DONE【P0】

- [ ] PASS
- [ ] FAIL

## M06｜not_before 到达后 worker 可执行 PREFIX cleanup【P0】

- [ ] PASS
- [ ] FAIL

## M07｜模拟晚到 object 最终被删除【P0】

流程：

```text
Profile DB 删除
→ cleanup 尚未 due
→ 合成 late object 出现在 prefix
→ not_before 到达
→ worker
→ prefix 最终为空
```

- [ ] PASS
- [ ] FAIL

---

# N. Cleanup 失败与重试

## N01｜COS 临时失败保持 PENDING【P0】

- [ ] PASS
- [ ] FAIL

## N02｜COS 失败不恢复 HealthProfile【P0】

数据库已提交删除后，不得重新创建：

```text
HealthProfile
LabReport
LabResult
```

- [ ] PASS
- [ ] FAIL

## N03｜COS 失败时用户删除仍视为成功【P0】

如果数据库事务已经成功：

```text
DELETE → 204
```

- [ ] PASS
- [ ] FAIL

## N04｜后续 worker 可重试成功【P0】

- [ ] PASS
- [ ] FAIL

## N05｜对象已经不存在视为成功【P0】

- [ ] PASS
- [ ] FAIL

## N06｜重复 cleanup 幂等【P0】

- [ ] PASS
- [ ] FAIL

## N07｜OBJECT 旧逻辑不被破坏【P0】

Stage 02 / Stage 05 OBJECT cleanup 继续：

- 有 ReportAsset 引用时保护；
- 无引用后可删除；
- 失败可 PENDING；
- 重试可 DONE。

- [ ] PASS
- [ ] FAIL

## N08｜Stage 05 report delete 仍可立即 cleanup【P0】

旧调用未设置 not_before 时不得被统一延迟。

- [ ] PASS
- [ ] FAIL

---

# O. 单数据库事务

## O01｜完整 Profile DB 删除单事务【P0】

以下必须全部成功或全部 rollback：

```text
FileCleanup registration
LabResult
LabReport
ConfirmationItem
OcrResultItem
OcrTask
ReportAsset
UploadAuthorization
ReportIngestion
MetricFavorite
User.default_health_profile_id
HealthProfile
```

- [ ] PASS
- [ ] FAIL

## O02｜FileCleanup 创建失败完整 rollback【P0】

- [ ] PASS
- [ ] FAIL

## O03｜中间正式数据删除失败完整 rollback【P0】

- [ ] PASS
- [ ] FAIL

## O04｜中间 OCR 数据删除失败完整 rollback【P0】

- [ ] PASS
- [ ] FAIL

## O05｜HealthProfile 最终 DELETE 失败完整 rollback【P0】

- [ ] PASS
- [ ] FAIL

## O06｜rollback 不留下本次新增 cleanup【P0】

- [ ] PASS
- [ ] FAIL

---

# P. default_health_profile_id

## P01｜删除非默认档案不改变默认值【P0】

- [ ] PASS
- [ ] FAIL

## P02｜删除默认档案自动选择 replacement【P0】

存在其它 ACTIVE profile 时选择稳定 replacement。

- [ ] PASS
- [ ] FAIL

## P03｜replacement 排序稳定【P0】

推荐：

```text
created_at ASC
id ASC
```

RESULT 必须记录最终规则。

- [ ] PASS
- [ ] FAIL

## P04｜删除最后一个档案后 default = NULL【P0】

- [ ] PASS
- [ ] FAIL

## P05｜不得保留已删除 profile ID【P0】

- [ ] PASS
- [ ] FAIL

---

# Q. 跨用户权限

## Q01｜Impact 跨用户 404【P0】

- [ ] PASS
- [ ] FAIL

## Q02｜DELETE 跨用户 404【P0】

- [ ] PASS
- [ ] FAIL

## Q03｜跨用户删除不产生 cleanup【P0】

- [ ] PASS
- [ ] FAIL

## Q04｜跨用户删除不改变任何医疗数据【P0】

- [ ] PASS
- [ ] FAIL

## Q05｜Admin Token 不能冒充普通用户删除【P0】

Stage 07 Admin JWT 调用普通用户 profile API 必须被拒绝。

- [ ] PASS
- [ ] FAIL

## Q06｜无资源存在性泄露【P0】

随机 UUID 与他人 UUID 对当前用户表现应保持统一资源不存在语义。

- [ ] PASS
- [ ] FAIL

---

# R. DELETE 重试与客户端恢复

## R01｜重复 DELETE 安全【P0】

成功后第二次调用允许：

```text
404 PROFILE_NOT_FOUND
```

但不能 500。

- [ ] PASS
- [ ] FAIL

## R02｜重复 DELETE 不影响其它 profile【P0】

- [ ] PASS
- [ ] FAIL

## R03｜重复 DELETE 不制造新的危险 cleanup【P0】

- [ ] PASS
- [ ] FAIL

## R04｜204 响应丢失后刷新可恢复【P0】

模拟：

```text
服务端已删
客户端未收到成功
→ 刷新 profile list
```

目标 profile 不存在时前端按删除已完成恢复。

- [ ] PASS
- [ ] FAIL

---

# S. 删除 vs UploadAuthorization

## S01｜删除事务与授权创建并发安全【P0】

真实 PostgreSQL 验证。

- [ ] PASS
- [ ] FAIL

## S02｜Profile 删除后不能留下新 UploadAuthorization【P0】

- [ ] PASS
- [ ] FAIL

## S03｜删除前已经成功签发的授权被纳入 not_before【P0】

- [ ] PASS
- [ ] FAIL

## S04｜晚到文件最终可清除【P0】

与 M07 联合验证。

- [ ] PASS
- [ ] FAIL

---

# T. 删除 vs Stage 04 commit

## T01｜真实 PostgreSQL 双 session 验证【P0】

- [ ] PASS
- [ ] FAIL

## T02｜commit 先完成时 profile delete 可清除新正式报告【P0】

- [ ] PASS
- [ ] FAIL

## T03｜delete 先完成时 commit 不得重新生成报告【P0】

- [ ] PASS
- [ ] FAIL

## T04｜不存在指向已删除 profile 的 LabReport【P0】

- [ ] PASS
- [ ] FAIL

## T05｜不存在指向已删除 profile 的 LabResult【P0】

- [ ] PASS
- [ ] FAIL

---

# U. 删除 vs Stage 05 migrate

## U01｜真实 PostgreSQL 并发验证【P0】

- [ ] PASS
- [ ] FAIL

## U02｜迁移先成功时三处归属一致【P0】

如果报告最终迁出源 profile：

```text
LabReport
LabResult
ReportIngestion
```

必须全部属于目标 profile。

- [ ] PASS
- [ ] FAIL

## U03｜已成功迁出的报告不得被源 profile 删除误删【P0】

如果 migrate 已完成并成为并发赢家，源 profile 删除只能清理仍属于源 profile 的数据。

- [ ] PASS
- [ ] FAIL

## U04｜delete 先成功时 migrate 安全失败【P0】

不得产生半迁移。

- [ ] PASS
- [ ] FAIL

## U05｜不存在三处 profile 不一致【P0】

- [ ] PASS
- [ ] FAIL

---

# V. 删除 vs Favorite

## V01｜Favorite PUT 与删除并发无 orphan【P0】

真实 PostgreSQL 或能证明 FK + transaction 的并发验证。

- [ ] PASS
- [ ] FAIL

## V02｜删除成功后 Favorite = 0【P0】

- [ ] PASS
- [ ] FAIL

---

# W. 删除后的产品查询

## W01｜HealthProfile 列表立即消失【P0】

无需等待 COS cleanup。

- [ ] PASS
- [ ] FAIL

## W02｜正式报告列表无法再查询该 profile【P0】

- [ ] PASS
- [ ] FAIL

## W03｜报告详情无法通过旧 report_id 再打开【P0】

- [ ] PASS
- [ ] FAIL

## W04｜原图 API 不再签发新的 preview URL【P0】

- [ ] PASS
- [ ] FAIL

## W05｜识别任务记录不再出现目标 ingestion【P0】

- [ ] PASS
- [ ] FAIL

## W06｜我的指标无法再查询目标 profile【P0】

- [ ] PASS
- [ ] FAIL

## W07｜Favorite 不再查询【P0】

- [ ] PASS
- [ ] FAIL

## W08｜其它 profile 查询正常【P0】

- [ ] PASS
- [ ] FAIL

---

# X. Miniapp 删除交互

## X01｜健康档案管理页仍为删除入口【P0】

不要求新建隐私中心。

- [ ] PASS
- [ ] FAIL

## X02｜删除前真实请求 impact【P0】

不得只用前端本地数组统计。

- [ ] PASS
- [ ] FAIL

## X03｜确认文案明确“永久删除”【P0】

必须明确无法恢复。

- [ ] PASS
- [ ] FAIL

## X04｜确认文案明确删除范围【P0】

至少包含：

```text
检验报告
指标历史
关注指标
原始图片
识别数据
```

或用户可理解的等价表达。

- [ ] PASS
- [ ] FAIL

## X05｜可展示报告 / 任务 / Favorite 数量【P0】

必须与 impact API 一致。

- [ ] PASS
- [ ] FAIL

## X06｜取消确认不调用 DELETE【P0】

- [ ] PASS
- [ ] FAIL

## X07｜PROCESSING impact 明确阻断【P0】

用户看得懂：

```text
正在识别，完成后再删除
```

不得只显示工程错误码。

- [ ] PASS
- [ ] FAIL

## X08｜并发变成 PROCESSING 时 409 正确提示【P0】

Impact=0 后到 DELETE 之间被 Worker claim 的场景。

- [ ] PASS
- [ ] FAIL

## X09｜删除成功刷新 profile list【P0】

- [ ] PASS
- [ ] FAIL

## X10｜删除默认 profile 后 selected 切换【P0】

- [ ] PASS
- [ ] FAIL

## X11｜删除最后一个 profile 显示空状态【P0】

并提供创建档案入口。

- [ ] PASS
- [ ] FAIL

## X12｜不保留已删除 profile 前端上下文【P0】

- [ ] PASS
- [ ] FAIL

---

# Y. Miniapp 自动验证

## Y01｜pnpm test【P0】

所有既有 + Stage 08 测试通过。

记录：

```text
Tests:
Passed:
Skipped:
Failed:
```

- [ ] PASS
- [ ] FAIL

## Y02｜Impact helper 测试【P0】

- [ ] PASS
- [ ] FAIL

## Y03｜PROCESSING 阻断 UI helper 测试【P0】

- [ ] PASS
- [ ] FAIL

## Y04｜成功刷新 / default replacement 测试【P0】

- [ ] PASS
- [ ] FAIL

## Y05｜最后 profile 空状态测试【P0】

- [ ] PASS
- [ ] FAIL

## Y06｜204 响应丢失恢复测试【P0】

- [ ] PASS
- [ ] FAIL

## Y07｜pnpm typecheck【P0】

- [ ] PASS
- [ ] FAIL

## Y08｜pnpm build:mp-weixin【P0】

- [ ] PASS
- [ ] FAIL

---

# Z. Backend 自动测试

## Z01｜全量 pytest【P0】

运行当前标准命令：

```text
.venv/Scripts/python.exe -m pytest -q
```

如继续需要仓库内 basetemp，应使用当前已验证等价方式。

不得 skip / 删除 / 弱化 Stage 00～07 测试。

- [ ] PASS
- [ ] FAIL

## Z02｜Ruff【P0】

```text
.venv/Scripts/ruff.exe check . --no-cache
```

- [ ] PASS
- [ ] FAIL

## Z03｜Stage 08 空 profile 测试【P0】

- [ ] PASS
- [ ] FAIL

## Z04｜完整已使用 profile 测试【P0】

- [ ] PASS
- [ ] FAIL

## Z05｜多 ingestion 测试【P0】

- [ ] PASS
- [ ] FAIL

## Z06｜Favorite 测试【P0】

- [ ] PASS
- [ ] FAIL

## Z07｜default / last profile 测试【P0】

- [ ] PASS
- [ ] FAIL

## Z08｜PROCESSING rollback 测试【P0】

- [ ] PASS
- [ ] FAIL

## Z09｜FileCleanup not_before 测试【P0】

- [ ] PASS
- [ ] FAIL

## Z10｜late object / retry / idempotence 测试【P0】

- [ ] PASS
- [ ] FAIL

## Z11｜跨用户测试【P0】

- [ ] PASS
- [ ] FAIL

## Z12｜日志隐私测试【P0】

- [ ] PASS
- [ ] FAIL

---

# AA. PostgreSQL 17 Migration

## AA01｜0007 → 0008【P0】

真实隔离 PostgreSQL 17 临时库升级 PASS。

- [ ] PASS
- [ ] FAIL

## AA02｜空库 0001 → 0008【P0】

- [ ] PASS
- [ ] FAIL

## AA03｜历史 FileCleanup 升级兼容【P0】

Stage 05 旧：

```text
OBJECT
PREFIX
PENDING
DONE
```

记录保持可用。

- [ ] PASS
- [ ] FAIL

## AA04｜ORM / migration Stage 08 新字段一致【P0】

不得借此宣称或修改既有 Stage 03 drift。

- [ ] PASS
- [ ] FAIL

---

# AB. PostgreSQL 17 完整删除

## AB01｜构造多 ingestion profile【P0】

至少包含：

```text
正式报告
未完成 ingestion
Favorite
OCR
Confirmation
Asset
Authorization
```

- [ ] PASS
- [ ] FAIL

## AB02｜完整链删除后所有私有表计数正确【P0】

目标 profile 对应：

```text
HealthProfile = 0
MetricFavorite = 0
LabReport = 0
LabResult = 0
ConfirmationItem = 0
OcrTask = 0
OcrResultItem = 0
ReportAsset = 0
UploadAuthorization = 0
ReportIngestion = 0
```

- [ ] PASS
- [ ] FAIL

## AB03｜公共主数据计数不变【P0】

```text
StandardMetric
MetricAlias
```

- [ ] PASS
- [ ] FAIL

## AB04｜其它 profile 完整快照不变【P0】

- [ ] PASS
- [ ] FAIL

## AB05｜PREFIX cleanup 数量正确【P0】

- [ ] PASS
- [ ] FAIL

---

# AC. PostgreSQL 17 Transaction Rollback

## AC01｜cleanup insert failure rollback【P0】

- [ ] PASS
- [ ] FAIL

## AC02｜LabResult/LabReport delete failure rollback【P0】

- [ ] PASS
- [ ] FAIL

## AC03｜OCR chain failure rollback【P0】

- [ ] PASS
- [ ] FAIL

## AC04｜HealthProfile delete failure rollback【P0】

- [ ] PASS
- [ ] FAIL

## AC05｜所有 rollback 后原始数据完整【P0】

- [ ] PASS
- [ ] FAIL

---

# AD. PostgreSQL 17 并发专项

## AD01｜QUEUED claim vs profile delete【P0】

符合 K 节。

- [ ] PASS
- [ ] FAIL

## AD02｜commit vs profile delete【P0】

符合 T 节。

- [ ] PASS
- [ ] FAIL

## AD03｜migrate vs profile delete【P0】

符合 U 节。

- [ ] PASS
- [ ] FAIL

## AD04｜upload authorization vs profile delete【P0】

符合 S 节。

- [ ] PASS
- [ ] FAIL

## AD05｜Favorite PUT vs profile delete【P0】

符合 V 节。

- [ ] PASS
- [ ] FAIL

## AD06｜并发后无 FK orphan【P0】

对所有相关表执行明确查询验证。

- [ ] PASS
- [ ] FAIL

---

# AE. PostgreSQL 测试库清理

## AE01｜Stage 08 临时库全部 finally 删除【P0】

- [ ] PASS
- [ ] FAIL

## AE02｜独立 pg_database 查询无残留【P0】

不得只依赖脚本日志声称已删。

- [ ] PASS
- [ ] FAIL

---

# AF. Stage 03 回归

## AF01｜OCR queue 原专项 PASS【P0】

- [ ] PASS
- [ ] FAIL

## AF02｜lease / retry 行为未变化【P0】

- [ ] PASS
- [ ] FAIL

## AF03｜正常 OCR Worker 仍能完成任务【P0】

Stage 08 的 PROCESSING 删除阻断不能破坏正常 OCR。

- [ ] PASS
- [ ] FAIL

## AF04｜OCR runtime diff = 0【P0】

- [ ] PASS
- [ ] FAIL

---

# AG. Stage 04 回归

## AG01｜Confirmation 初始化仍通过【P0】

- [ ] PASS
- [ ] FAIL

## AG02｜REVIEW_PENDING 仍通过【P0】

- [ ] PASS
- [ ] FAIL

## AG03｜commit 幂等仍通过【P0】

- [ ] PASS
- [ ] FAIL

## AG04｜纯手工报告仍通过【P0】

- [ ] PASS
- [ ] FAIL

## AG05｜duplicate 仍通过【P0】

- [ ] PASS
- [ ] FAIL

---

# AH. Stage 05 回归

## AH01｜正式报告列表 / 详情 PASS【P0】

- [ ] PASS
- [ ] FAIL

## AH02｜报告迁移 PASS【P0】

- [ ] PASS
- [ ] FAIL

## AH03｜单份报告完整删除 PASS【P0】

- [ ] PASS
- [ ] FAIL

## AH04｜FileCleanup OBJECT PASS【P0】

- [ ] PASS
- [ ] FAIL

## AH05｜FileCleanup PREFIX PASS【P0】

- [ ] PASS
- [ ] FAIL

## AH06｜旧 report delete 不被 not_before 意外延迟【P0】

- [ ] PASS
- [ ] FAIL

---

# AI. Stage 06 回归

## AI01｜我的指标 PASS【P0】

- [ ] PASS
- [ ] FAIL

## AI02｜history / trend PASS【P0】

- [ ] PASS
- [ ] FAIL

## AI03｜Favorite PUT / DELETE PASS【P0】

- [ ] PASS
- [ ] FAIL

## AI04｜其它 profile Favorite 不受 Stage 08 删除影响【P0】

- [ ] PASS
- [ ] FAIL

---

# AJ. Stage 07 回归

## AJ01｜StandardMetric CRUD / status PASS【P0】

- [ ] PASS
- [ ] FAIL

## AJ02｜MetricAlias PASS【P0】

- [ ] PASS
- [ ] FAIL

## AJ03｜Exact Resolver PASS【P0】

- [ ] PASS
- [ ] FAIL

## AJ04｜OCR Issue PASS【P0】

- [ ] PASS
- [ ] FAIL

## AJ05｜Admin Auth 隔离 PASS【P0】

- [ ] PASS
- [ ] FAIL

## AJ06｜OCR Task readonly PASS【P0】

- [ ] PASS
- [ ] FAIL

---

# AK. OCR Frozen Boundary

## AK01｜backend/ocr_runtime 无变更【P0】

- [ ] PASS
- [ ] FAIL

## AK02｜Pipeline Version 不变【P0】

- [ ] PASS
- [ ] FAIL

## AK03｜matcher 不变【P0】

- [ ] PASS
- [ ] FAIL

## AK04｜threshold 不变【P0】

- [ ] PASS
- [ ] FAIL

## AK05｜fuzzy score 不变【P0】

- [ ] PASS
- [ ] FAIL

## AK06｜unit score / unit rules 不变【P0】

- [ ] PASS
- [ ] FAIL

## AK07｜retry / evidence 不变【P0】

- [ ] PASS
- [ ] FAIL

## AK08｜AUTO / REVIEW 判定不变【P0】

- [ ] PASS
- [ ] FAIL

---

# AL. Admin Web 回归

## AL01｜Admin tests【P0】

如当前 package 已存在正式测试命令则必须运行。

- [ ] PASS
- [ ] FAIL
- [ ] N/A（仅当当前仓库确无测试命令，并在 RESULT 说明）

## AL02｜Admin typecheck【P0】

- [ ] PASS
- [ ] FAIL

## AL03｜Admin build【P0】

- [ ] PASS
- [ ] FAIL

## AL04｜Stage 08 不新增用户医疗删除 Admin UI【P0】

- [ ] PASS
- [ ] FAIL

---

# AM. 日志与隐私

## AM01｜删除 API 日志不含 display_name【P0】

- [ ] PASS
- [ ] FAIL

## AM02｜日志不含生日 / 性别【P0】

- [ ] PASS
- [ ] FAIL

## AM03｜日志不含 LabResult 全文【P0】

- [ ] PASS
- [ ] FAIL

## AM04｜cleanup 日志不打印完整 prefix【P0】

- [ ] PASS
- [ ] FAIL

## AM05｜异常日志不打印 COS Secret / Token【P0】

- [ ] PASS
- [ ] FAIL

---

# AN. 负责人真实微信人工验收

本节不能由 Codex、API 自动测试或 PostgreSQL 脚本代替。

## AN01｜T01 空档案删除【P0】

负责人真实微信：

```text
新建测试空档案
→ 健康档案管理
→ 删除
→ 明确确认
```

确认：

- 档案消失；
- 页面正常。

- [ ] PASS
- [ ] FAIL

## AN02｜T02 已真实使用档案完整删除【P0】

准备一个至少包含：

```text
正式报告
指标历史 / 趋势
Favorite
```

的测试档案。

真实删除后确认：

- 健康档案消失；
- 正式报告消失；
- 我的指标无法再进入该档案；
- Favorite 不再存在；
- 原始报告旧入口不可再访问。

- [ ] PASS
- [ ] FAIL

## AN03｜T03 未完成任务随档案删除【P0】

准备至少一个：

```text
READY
OCR_FAILED
PENDING_CONFIRMATION
```

测试任务。

删除档案后：

- 任务记录不再出现；
- 不能重新打开任务；
- 无需先逐个删除任务。

- [ ] PASS
- [ ] FAIL

## AN04｜T04 删除当前默认档案【P0】

至少有两个 profile。

删除当前默认档案后：

- 自动切换到剩余档案；
- 首页当前档案正确；
- 报告 / 我的指标进入剩余档案上下文。

- [ ] PASS
- [ ] FAIL

## AN05｜T05 删除最后一个档案【P0】

删除最后一个 profile：

```text
首页显示无健康档案
→ 可以重新创建
```

- [ ] PASS
- [ ] FAIL

## AN06｜T06 PROCESSING OCR 阻断【P0】

真实让一份测试任务进入：

```text
PROCESSING
```

此时删除 profile：

- 明确提示正在识别；
- 删除未发生；
- profile 仍存在；
- OCR 任务仍可正常结束/失败。

任务离开 PROCESSING 后再次删除：

- 成功。

- [ ] PASS
- [ ] FAIL

---

# AO. Stage 09 边界

## AO01｜未进入统一 UI / UX 打磨【P0】

Stage 08 只做删除交互所需最小页面修改。

不得重构：

```text
首页
报告列表整体视觉
指标页整体视觉
底部 Tab
Admin 全局视觉
```

- [ ] PASS
- [ ] FAIL

## AO02｜未建设首页异常 / 待处理 Dashboard【P0】

- [ ] PASS
- [ ] FAIL

---

# AP. Stage 10 / 部署边界

## AP01｜未提前做生产部署【P0】

- [ ] PASS
- [ ] FAIL

## AP02｜未新增 Nginx / Supervisor / systemd 作为 Stage 08 主成果【P0】

- [ ] PASS
- [ ] FAIL

## AP03｜未提前做完整监控 / 备份体系【P0】

- [ ] PASS
- [ ] FAIL

---

# AQ. 文档

## AQ01｜README 同步【P0】

至少反映：

```text
Stage 08 完整 HealthProfile 删除能力
```

- [ ] PASS
- [ ] FAIL

## AQ02｜DATA_MODEL 同步【P0】

明确：

- HealthProfile 物理隐私删除；
- Favorite 随档案删除；
- FileCleanup.not_before；
- 公共主数据不属于用户删除范围。

- [ ] PASS
- [ ] FAIL

## AQ03｜RESULT.md 完整【P0】

最终必须记录：

```text
实际完成项
实际变更文件
migration
删除表范围
FileCleanup not_before 实现
安全余量
PROCESSING 阻断
事务实现
并发策略
自动测试
PostgreSQL 17
临时库清理
微信人工验收
设计偏差
已知问题
OCR frozen diff
Stage09 边界
```

- [ ] PASS
- [ ] FAIL

---

# AR. 最终 PASS 条件

Stage 08 只有以下全部满足才能：

```text
Stage 08 = PASS
```

必须同时满足：

```text
A～AQ 所有适用 P0 PASS

+

已使用 HealthProfile 可以完整删除
+
HealthProfile 物理删除
+
MetricFavorite 清除
+
正式报告/结果清除
+
Confirmation 清除
+
OCR 清除
+
Asset / Authorization / Ingestion 清除

+

每个 ingestion PREFIX cleanup 可靠登记
+
活跃上传凭据 not_before 覆盖
+
late object 最终可清理
+
COS 失败 PENDING 可重试
+
Stage05 cleanup 行为不回归

+

PROCESSING OCR 明确阻断
+
QUEUED Worker claim 并发安全
+
commit 并发安全
+
migrate 并发安全
+
UploadAuthorization 并发安全
+
Favorite 并发安全
+
无 FK orphan

+

default profile 正确
+
最后一个 profile 可删除
+
跨用户隔离
+
Admin Token 隔离

+

0007 → 0008 PG17 PASS
+
空库 0001 → 0008 PASS
+
rollback PASS
+
临时测试库 0 残留

+

Backend pytest PASS
+
Ruff PASS
+
Miniapp test/typecheck/build PASS
+
Admin test（适用时）/typecheck/build PASS

+

OCR runtime diff = 0
+
Pipeline Version 不变
+
matcher / threshold / fuzzy / unit / retry 不变
+
0001～0007 未修改
+
Stage03 drift 未夹带修复

+

负责人真实微信 T01～T06 全部 PASS

+

RESULT 完整
+
未进入 Stage09
+
未进入 Stage10
+
未进入部署发布
```

任意适用 P0 未满足：

```text
Stage 08 = FAIL
```

不得使用：

```text
SQLite 单测通过
API 返回 204
页面弹窗能打开
数据库只删了 HealthProfile
COS 正常情况下一次删除成功
```

替代完整数据生命周期验收。

---

# AS. 最终验收记录模板

最终 RESULT 中建议记录：

```text
Stage 08 = PASS / FAIL

Backend:
- pytest:
- Ruff:

Miniapp:
- tests:
- typecheck:
- build:

Admin:
- tests:
- typecheck:
- build:

PostgreSQL 17:
- 0007 → 0008:
- 0001 → 0008:
- full chain deletion:
- rollback:
- queued claim concurrency:
- commit concurrency:
- migrate concurrency:
- upload auth concurrency:
- favorite concurrency:
- temp DB residue:

OCR Frozen:
- runtime diff:
- pipeline version:
- threshold/matcher/retry diff:

负责人真实微信:
- T01:
- T02:
- T03:
- T04:
- T05:
- T06:

Stage 09:
- not started

Stage 10:
- not started

Deployment:
- not started
```
