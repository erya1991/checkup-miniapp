# Stage 08｜健康档案隐私删除与数据生命周期闭环

**状态：READY_FOR_ACCEPTANCE_FREEZE**

> Stage 08 承接已经正式 PASS 的 Stage 00～07。
>
> 本阶段只有一个主题：
>
> **让已经真实使用过的 HealthProfile 也能够安全、完整、可验证地删除其全部健康数据及相关私有文件。**
>
> 本阶段不是 UI 总打磨阶段，不进入 Stage 09；不进入生产部署与发布；不修改冻结 OCR 算法。

---

# 1. 阶段目标

截至 Stage 07，普通用户已经形成完整的报告使用主链：

```text
微信登录
→ 健康档案
→ 多图上传
→ OCR
→ AUTO / REVIEW
→ 人工确认
→ 正式 LabReport / LabResult
→ 报告管理
→ 我的指标 / 历史 / 趋势 / Favorite
```

Stage 05 已经完成**单份正式报告**的完整隐私删除：

```text
LabReport / LabResult
→ Confirmation
→ OCR Task / Result
→ ReportAsset / UploadAuthorization / ReportIngestion
→ COS ingestion prefix
```

但当前真实 HealthProfile 删除仍是：

```text
DELETE /health-profiles/{id}

如果存在任意 ReportIngestion
→ 409 PROFILE_HAS_INGESTIONS
```

小程序也明确提示：

```text
有导入任务的档案不能直接删除
```

因此当前实际行为是：

```text
从未使用过的健康档案
→ 可以删除

一旦上传过报告的健康档案
→ 无法从产品中完整删除
```

这与冻结 `TECH_BASELINE.md` 的要求不一致：

> 删除健康档案需受控清理其报告、结果、关注、导入、OCR 与文件，不能只依赖数据库级联。

Stage 08 的目标是补齐这一最后的 P0 数据生命周期闭环：

```text
HealthProfile
→ 用户明确查看删除影响
→ 用户确认永久删除
→ 删除全部正式报告与结果
→ 删除全部 Confirmation
→ 删除全部 OCR Task / Result
→ 删除全部 ReportAsset / UploadAuthorization / ReportIngestion
→ 删除 MetricFavorite
→ 清理 default_health_profile_id
→ 物理删除 HealthProfile
→ 原图 / OCR artifact 进入可靠 COS prefix 清理
```

最终用户应能够真正完成：

> “我不再管理这个家庭成员，请永久删除这个健康档案和该档案下的健康数据。”

---

# 2. 必读基线

实施前必须重新读取仓库最新 `main`，不得仅依赖本 PLAN 中的代码事实。

按 `AGENTS.md` 的要求至少读取：

1. `AGENTS.md`
2. `docs/00-baseline/PRODUCT_BASELINE.md`
3. `docs/00-baseline/TECH_BASELINE.md`
4. `docs/00-baseline/DEVELOPMENT_RULES.md`
5. 本目录 `PLAN.md`
6. 本目录 `ACCEPTANCE.md`
7. `docs/stages/07-admin/RESULT.md`

随后按主题继续读取：

```text
README.md
backend/README.md
miniapp/README.md
admin-web/README.md

docs/01-architecture/DATA_MODEL.md
docs/01-architecture/API_CONVENTIONS.md
docs/01-architecture/SYSTEM_ARCHITECTURE.md

docs/stages/02-profile-upload/RESULT.md
docs/stages/03-ocr-integration/RESULT.md
docs/stages/04-confirmation-report/RESULT.md
docs/stages/05-report-management/RESULT.md
docs/stages/06-metric-trend/RESULT.md
docs/stages/07-admin/RESULT.md
```

如果 `PROJECT_CONTEXT.md` 在实施时存在，也应读取；当前 Stage 08 设计时远程 `main` 未发现该文件，因此不得把旧对话中的 PROJECT_CONTEXT 内容当作代码事实。

必须检查真实代码，至少包括：

```text
backend/app/api/v1/business.py
backend/app/reports.py
backend/app/cleanup_worker.py
backend/app/ocr_worker.py
backend/app/ocr_queue.py
backend/app/ocr_pipeline.py
backend/app/confirmation.py
backend/app/profile_metrics.py
backend/app/models/entities.py
backend/migrations/versions/*
backend/tests/*

miniapp/src/pages/profiles/index.vue
miniapp/src/pages/profile-edit/index.vue
miniapp/src/pages/index/index.vue
miniapp/src/api.ts
```

实施前必须再次核对：

```text
git status
git log -1
origin/main
alembic heads
```

不得因为本 PLAN 已写明当前事实而跳过真实代码核验。

---

# 3. 当前真实基线

Stage 07 最终已经 PASS。

当前正式产品域已经存在：

```text
User
HealthProfile

ReportIngestion
UploadAuthorization
ReportAsset
OcrTask
OcrResultItem
ConfirmationItem

LabReport
LabResult

StandardMetric
MetricAlias
MetricFavorite

FileCleanup
```

当前 migration head：

```text
0007_standard_metric_admin
```

Stage 08 不得修改：

```text
0001～0007
```

当前 HealthProfile 删除逻辑为：

```text
有 ReportIngestion
→ PROFILE_HAS_INGESTIONS

没有 ReportIngestion
→ status = DELETED
```

当前 Stage 05 正式报告删除已经具备：

```text
FileCleanup(PREFIX, PENDING)
+
完整 ingestion 数据链硬删除
+
数据库 commit 后即时 COS cleanup
+
失败后 cleanup_worker 重试
```

当前 Stage 06 已经新增：

```text
MetricFavorite(
    health_profile_id,
    standard_metric_id
)
```

因此 HealthProfile 删除不能只复制 Stage 02 的 `status = DELETED`，也不能只循环调用“删除正式报告”。

---

# 4. Stage 08 一句话职责

> Stage 08 负责 HealthProfile 的完整隐私删除：在不修改 OCR 判定、不重写历史数据的前提下，安全清除该档案当前仍存在的全部用户健康数据，并可靠回收该档案所有 ingestion 的私有 COS 文件。

---

# 5. 核心删除语义

Stage 08 将：

```text
DELETE /api/v1/health-profiles/{profile_id}
```

从当前“空档案删除接口”升级为：

> **完整 HealthProfile 隐私删除接口。**

成功后必须满足：

```text
HealthProfile 不存在
+
该 HealthProfile 的 MetricFavorite 不存在
+
该 HealthProfile 当前仍归属的 ReportIngestion 不存在
+
对应 LabReport / LabResult 不存在
+
对应 ConfirmationItem 不存在
+
对应 OcrTask / OcrResultItem 不存在
+
对应 ReportAsset / UploadAuthorization 不存在
+
产品查询立即无法再读取上述健康数据
+
每个 ingestion 的 COS prefix 已进入可靠 FileCleanup
```

删除不是：

```text
隐藏
软删除
仅 status=DELETED
回收站
```

本阶段对用户明确执行的完整 HealthProfile 删除采用**物理删除 HealthProfile 行**。

原因：

- HealthProfile 本身包含展示名称、关系、可选性别和生日；
- 用户请求删除档案时，没有业务理由继续永久保存这些个人信息；
- 当前产品没有回收站或恢复需求；
- 冻结 baseline 强调的是隐私与完整数据删除。

已有历史 `status=DELETED` 的旧空档案不在 Stage 08 自动批量清理范围内；不得通过 migration 静默删除过去数据。Stage 08 只改变用户今后明确执行删除时的正式行为。

---

# 6. 删除范围

一个 HealthProfile 删除时，数据库目标范围至少包括：

```text
MetricFavorite

该 profile 当前归属的全部 ReportIngestion
    ├── UploadAuthorization
    ├── ReportAsset
    ├── OcrTask
    │     └── OcrResultItem
    ├── ConfirmationItem
    └── LabReport
          └── LabResult

HealthProfile
```

## 6.1 正式报告

所有当前仍属于该 HealthProfile 的：

```text
LabReport
LabResult
```

全部硬删除。

不得：

- 保留正式结果用于趋势；
- 保留“已删除报告”软状态；
- 把结果迁到其它档案；
- 自动合并到本人档案。

## 6.2 未完成 ingestion

必须同时清理以下状态的 ingestion：

```text
UPLOADING
READY
QUEUED
OCR_FAILED
PENDING_CONFIRMATION
CONFIRMED
```

`PROCESSING` 单独按第 10 节安全处理。

删除 HealthProfile 不要求用户先逐份：

```text
取消上传
删除任务
删除报告
取消 Favorite
```

产品必须提供真正的“一次删除整个档案”能力。

## 6.3 Confirmation

包括：

- OCR 初始化项；
- 人工修改项；
- MANUAL 项；
- REMOVED 项；

全部删除。

## 6.4 OCR

包括该 ingestion 所有：

```text
成功 run
失败 run
retry run
OcrResultItem
```

全部删除。

这里不违反 OcrResultItem “不可变机器快照”原则。

不可变原则指：

> 不得因为主数据变化或人工确认去重写历史机器事实。

而用户明确执行隐私删除时：

> 可以、且应该删除该用户请求删除的数据。

Stage 08 不 UPDATE 机器快照；只执行用户明确授权的整档案删除。

## 6.5 Favorite

当前 HealthProfile 的全部：

```text
MetricFavorite
```

删除。

不得迁移到其它 HealthProfile。

Favorite 是档案级偏好，档案被删除后不应继续存在 dormant Favorite。

## 6.6 公共主数据

绝对不得删除：

```text
StandardMetric
MetricAlias
```

它们是公共产品主数据，不属于用户 HealthProfile 私有数据。

---

# 7. COS 文件清理范围

每个待删除 ingestion 必须登记：

```text
users/{user_id}/ingestions/{ingestion_id}/
```

完整 prefix cleanup。

必须覆盖：

```text
original/
ocr/
manifest
retry
evidence
以及 ingestion prefix 下其它可能残留对象
```

不能只删除当前数据库仍存在的 ReportAsset object key。

原因：

- Stage 03 OCR artifact 不只包含原图；
- Stage 02 已知可能出现“上传成功但登记失败”的 ingestion 范围孤儿文件；
- prefix 是当前产品已经验证的正式删除边界。

---

# 8. FileCleanup Stage 08 扩展

Stage 05 的 `FileCleanup` 已经支持：

```text
target_type = OBJECT | PREFIX
status = PENDING | DONE
```

但 HealthProfile 删除存在一个 Stage 05 单份正式报告删除不一定遇到的窗口：

```text
用户已经取得临时上传凭据
→ 请求删除 HealthProfile
→ 数据库立即删除
→ 临时 COS 凭据仍可能短时间有效
```

当前上传授权约 15 分钟有效。

如果：

```text
prefix 先删空
→ cleanup 被标记 DONE
→ 客户端随后使用仍有效的凭据上传
```

则可能产生删除后的孤儿文件。

因此 Stage 08 增加一个最小文件清理调度字段，建议：

```text
FileCleanup.not_before
```

允许为空。

语义：

```text
NULL
→ 与 Stage 05 现有行为一致，可立即处理

非 NULL
→ cleanup worker 在 not_before 到达前不得将该 cleanup 处理为 DONE
```

Stage 08 profile 删除为每个 ingestion 计算：

```text
not_before
=
max(
    当前时间,
    该 ingestion 所有尚未自然过期 UploadAuthorization.expires_at
)
+
小型安全余量
```

建议安全余量固定为：

```text
60 seconds
```

除非实施时真实 COS STS 行为证明需要等价但不同的最小值。

Stage 08 不为此建设复杂文件任务调度系统。

## 8.1 为什么允许文件短时延迟删除

HealthProfile 删除成功后：

```text
数据库正式健康数据已经删除
产品不再能读取报告
产品不再签发新的原图 preview
```

COS 文件进入持久、可重试的后台删除队列。

这与 Stage 05 已冻结的原则一致：

> COS 临时故障不能恢复已经完成的数据库隐私删除。

在存在尚未过期上传凭据时，等待凭据失效后再执行最终 prefix 删除，比“立即删一次然后留下晚到孤儿文件”更安全。

## 8.2 现有 Stage 05 行为不得改变

已有：

```text
FileCleanup.not_before = NULL
```

必须继续立即可执行。

Stage 05 正式报告删除不能因为 Stage 08 migration 被统一延迟 15 分钟。

## 8.3 cleanup worker 查询

worker 只领取：

```text
status = PENDING
AND
(
    not_before IS NULL
    OR not_before <= now
)
```

排序至少保持稳定：

```text
not_before / created_at / id
```

具体 SQL 可结合现有实现。

---

# 9. 为什么 Stage 08 需要 migration

新增独立 migration：

```text
0008_profile_data_deletion
```

至少：

```text
file_cleanups.not_before TIMESTAMPTZ NULL
```

并根据真实 PostgreSQL 查询需要增加合理索引，例如：

```text
(status, not_before, created_at)
```

是否最终需要组合索引，以实际 worker 查询和 PostgreSQL 验证为准。

不得修改：

```text
0001～0007
```

不得顺手修复 Stage 03 已知 ORM / migration index drift。

不得新增：

```text
profile_delete_jobs
deletion_history
recycle_bin
soft_delete table
复杂任务系统
```

除非实施时证明仅靠现有事务 + FileCleanup 无法满足冻结 ACCEPTANCE；此时必须先记录设计冲突，不得自行扩范围。

---

# 10. PROCESSING OCR 的安全边界

当前 OCR Worker：

```text
OcrTask.PROCESSING
→ 后台长时间执行 OCR
→ run_pipeline 内部写 COS artifact
→ 返回后再检查 lease 并写数据库
```

因此如果直接在 OCR 正在运行时删除档案：

```text
数据库可能已经删完
但旧 Worker 仍可能继续往 ingestion prefix 写 artifact
```

Stage 08 不为了档案删除去修改冻结 OCR runtime，也不建设复杂 Worker cancel protocol。

因此本阶段冻结：

```text
只要目标 HealthProfile 存在 OcrTask.status = PROCESSING
→ HealthProfile 删除不得执行
→ 返回稳定 409 PROFILE_DELETE_BUSY
```

响应 details 至少可以包含：

```text
processing_count
```

不得返回 OCR 医疗内容。

用户稍后在任务结束、失败或进入其它非 PROCESSING 状态后可再次删除。

这是一项安全阻断，不是功能缺失。

Stage 08 不要求“强制终止 OCR”。

---

# 11. QUEUED OCR

`QUEUED` 不应永久阻止删除。

删除事务必须对目标 profile 下的：

```text
ReportIngestion
OcrTask
```

采用数据库锁或等价 PostgreSQL 串行语义。

必须保证与 OCR Worker claim 竞争时只有以下两类合法结果：

### 情形 A

```text
Profile deletion 先锁到 QUEUED task
→ Worker claim 跳过 / 无法取得该 task
→ task 随档案删除
```

### 情形 B

```text
Worker 先成功 claim
→ task = PROCESSING
→ Profile deletion 看到 PROCESSING
→ 整个档案删除 rollback
→ PROFILE_DELETE_BUSY
```

绝不能出现：

```text
Profile 删除成功
+
同一 task 后续又成功写回 OcrResultItem / ingestion 状态
```

这一点必须在真实 PostgreSQL 17 做双 session / Worker 语义验证。

---

# 12. 数据库删除事务

HealthProfile 的数据库健康数据删除必须使用单一 PostgreSQL 事务。

推荐逻辑：

```text
BEGIN

锁定当前 User 的目标 HealthProfile

再次验证：
    user_id
    当前 profile 可删除

锁定该 profile 当前全部 ReportIngestion
锁定对应 OcrTask

如果任意 OcrTask = PROCESSING：
    ROLLBACK
    PROFILE_DELETE_BUSY

重新取得本事务内权威 ingestion 集合

为每个 ingestion：
    计算 cleanup prefix
    计算 not_before
    创建 FileCleanup(PREFIX, PENDING, not_before)
    flush，确保 cleanup 可持久化

删除：
    LabResult
    LabReport
    ConfirmationItem
    OcrResultItem
    OcrTask
    ReportAsset
    UploadAuthorization
    ReportIngestion

删除：
    MetricFavorite

如果 User.default_health_profile_id == 当前 profile：
    选择其它 ACTIVE profile 作为 replacement
    如果不存在 → NULL

物理删除 HealthProfile

COMMIT
```

具体 SQL 删除顺序必须以真实 FK 为准。

任何数据库步骤失败：

```text
全部 rollback
```

不得出现：

```text
HealthProfile 已删
但 LabResult 还存在

或

数据已删
但没有 FileCleanup

或

Favorite 遗留引用已删除 profile
```

---

# 13. 删除影响预览

整个 HealthProfile 删除属于高风险不可恢复操作。

Stage 08 P0 增加一个轻量只读预览能力。

建议：

```text
GET /api/v1/health-profiles/{profile_id}/deletion-impact
```

返回当前用户可见的最小摘要：

```json
{
  "profile": {
    "id": "...",
    "display_name": "父亲"
  },
  "report_count": 3,
  "unfinished_ingestion_count": 1,
  "total_ingestion_count": 4,
  "favorite_count": 2,
  "processing_ocr_count": 0
}
```

不需要返回：

- LabResult 明细；
- 指标名称；
- 结果值；
- 医院；
- 报告号；
- OCR 全文；
- COS key。

该接口只用于危险删除确认。

如果 implementation 选择将同等摘要直接返回在其它安全预检接口，也必须保持相同产品能力；但不得仅靠前端本地计数猜测。

---

# 14. HealthProfile 删除 API

继续使用：

```text
DELETE /api/v1/health-profiles/{profile_id}
```

成功数据库删除后：

```text
204 No Content
```

即使：

```text
COS cleanup 尚未到 not_before
或到期后第一次 COS 删除暂时失败
```

仍视为用户数据库隐私删除成功。

原因：

- Profile 和正式健康数据已经不存在；
- FileCleanup 已在同一事务前置持久化；
- cleanup worker 可以继续可靠重试。

不得因为 COS 临时错误恢复数据库健康数据。

---

# 15. 删除重复请求

Stage 08 不为了重复 DELETE 建立包含个人信息的 deletion tombstone。

因此删除成功后再次对同一 ID 调用：

```text
DELETE
```

允许统一返回：

```text
404 PROFILE_NOT_FOUND
```

重点要求：

```text
不会重新生成 cleanup
不会影响其它 HealthProfile
不会产生 500
```

小程序如果发生：

```text
服务端删除已成功
但客户端没有收到 204
```

刷新 HealthProfile 列表后，如果目标 profile 已不存在，应按“删除已完成”恢复，而不是提示用户数据仍存在。

---

# 16. 默认 HealthProfile

如果删除的是：

```text
User.default_health_profile_id
```

则同一事务内：

1. 从该 User 剩余 `ACTIVE` profile 中选择一个稳定 replacement；
2. 推荐保持当前逻辑：

```text
created_at ASC
→ id ASC
```

3. 如果没有剩余 ACTIVE profile：

```text
default_health_profile_id = NULL
```

不得：

- 自动新建本人档案；
- 把其它用户档案设为默认；
- 保留指向已删除 profile 的 ID。

删除最后一个 HealthProfile 是合法行为。

再次进入首页时应自然进入：

```text
还没有健康档案
→ 创建本人档案
```

---

# 17. 跨用户安全

用户只能删除：

```text
HealthProfile.user_id == current_user.id
```

User A 使用 User B 的 profile ID：

```text
deletion-impact → 404 PROFILE_NOT_FOUND
DELETE → 404 PROFILE_NOT_FOUND
```

不得泄露：

- 对方 profile 是否存在；
- 对方报告数；
- 对方任务状态；
- 对方 Favorite；
- 对方文件状态。

Admin Token 不得调用普通用户 HealthProfile 删除接口冒充用户。

Stage 07 Admin 只管理主数据与 OCR 技术排查，不获得用户正式医疗数据删除能力。

---

# 18. 与报告迁移 / commit / Favorite / 上传的并发

Stage 08 不要求新增大型分布式锁系统。

但 PostgreSQL 17 上必须证明：

## 18.1 删除 vs 新 ingestion / upload authorization

不能出现：

```text
HealthProfile 已删除
→ 新 ReportIngestion 或新 UploadAuthorization 成功留下
```

如果上传授权在删除前已经成功签发：

- 删除事务必须读取其 `expires_at`；
- cleanup.not_before 必须覆盖该凭据剩余有效期和安全余量。

## 18.2 删除 vs commit

合法结果只允许：

### commit 先完成

```text
正式报告进入该 profile
→ profile delete 随后将它一起删除
```

或：

### delete 先完成

```text
commit 失败
→ 不重新生成指向已删除 profile 的 LabReport / LabResult
```

不得存在 orphan 正式数据。

## 18.3 删除 vs report migrate

目标是：

```text
最终数据库状态唯一且一致
```

允许：

- 迁移先完成，则报告最终属于目标 profile，不应被后续源 profile 删除误删；
- profile 删除先完成，则迁移应失败/资源不存在。

不得出现：

```text
LabReport 在目标 profile
LabResult 还在已删除 profile
ReportIngestion 又是另一 profile
```

如果现有行锁顺序无法证明这一点，允许增加**最小共享 profile lifecycle locking helper**，但不得引入 Redis、分布式锁或新服务。

## 18.4 删除 vs Favorite PUT

最终不得存在：

```text
MetricFavorite.health_profile_id
→ 已删除 HealthProfile
```

依赖数据库 FK 与事务/锁证明，不允许仅依赖前端隐藏按钮。

---

# 19. 小程序删除交互

修改现有：

```text
pages/profiles/index.vue
```

不新建复杂隐私中心。

点击：

```text
删除
```

后：

1. 请求 `deletion-impact`；
2. 如果 `processing_ocr_count > 0`：
   - 明确提示“该档案有正在识别的报告，识别结束后才能删除”；
   - 不发 DELETE；
3. 否则展示危险确认。

确认文案必须明确至少表达：

```text
将永久删除「父亲」健康档案，
以及该档案下的全部检验报告、指标历史、关注指标、原始图片和识别数据。
删除后无法恢复。
```

如存在统计，建议同时展示：

```text
正式报告 X 份
未完成任务 X 个
关注指标 X 个
```

用户明确确认后才调用 DELETE。

不要求：

- 输入档案名称二次验证；
- 短信验证码；
- 微信支付式确认；
- 单独删除页面。

Stage 09 才统一做 UI / UX 视觉打磨。

---

# 20. 删除成功后的前端行为

成功后：

```text
重新请求 /health-profiles
重新请求 /me
更新 selected/default
```

如果仍有其它档案：

```text
显示 replacement 当前档案
```

如果没有：

```text
显示空档案状态
提供新增档案入口
```

不得保留：

- 已删除 profile 的本地 selected；
- 已删除 profile 的 reports / metrics 页面上下文；
- 已删除 profile 的 pending frontend cache。

当前页面体系没有复杂全局 store，Stage 08 不因此引入新的状态管理框架。

---

# 21. PROCESSING 阻断前端恢复

如果 DELETE 在 impact 之后、实际提交时因为并发 OCR claim 返回：

```text
409 PROFILE_DELETE_BUSY
```

前端必须：

- 显示稳定中文提示；
- 不显示“删除成功”；
- 刷新 impact；
- 不自行循环重试危险删除。

这是正常并发保护。

---

# 22. FileCleanup worker

现有独立进程继续：

```text
python -m app.cleanup_worker
```

Stage 08 只扩展 due-time 过滤。

不得引入：

- Celery；
- Redis；
- RabbitMQ；
- Kafka；
- cron 依赖作为唯一正确性来源；
- 新微服务。

worker 必须继续支持：

```text
OBJECT
PREFIX
```

已有 OBJECT 引用保护不能被破坏。

PREFIX：

```text
对象不存在
→ 成功

重复执行
→ 幂等

COS 临时失败
→ PENDING
→ 后续重试
```

---

# 23. 日志与隐私

允许记录：

```text
request_id
user_id 内部 ID
profile_id
ingestion_count
cleanup_id
status
error_code
duration
```

不得记录：

- HealthProfile display_name；
- 性别 / 生日；
- 医院；
- 报告编号；
- LabResult 全文；
- OCR 全文；
- COS Secret；
- 临时 Token；
- 永久 COS URL；
- 完整医疗 payload。

cleanup worker 不在普通日志输出完整 prefix。

---

# 24. 主要 API

Stage 08 预期用户 API：

```text
GET    /api/v1/health-profiles/{profile_id}/deletion-impact
DELETE /api/v1/health-profiles/{profile_id}
```

已有 profile CRUD 其它接口保持兼容。

建议稳定业务错误码：

```text
PROFILE_NOT_FOUND
PROFILE_DELETE_BUSY
PROFILE_DELETE_FAILED
```

`PROFILE_DELETE_FAILED` 只用于数据库隐私删除未提交成功的场景。

数据库已经删除成功但 COS cleanup PENDING 时：

```text
不得返回 PROFILE_DELETE_FAILED
```

---

# 25. 数据模型文档同步

Stage 08 完成后应更新：

```text
docs/01-architecture/DATA_MODEL.md
```

至少补充：

- HealthProfile 删除为整档案隐私删除；
- MetricFavorite 随 profile 删除；
- user data domain 与 StandardMetric / MetricAlias 公共主数据的边界；
- FileCleanup.not_before。

如 API_CONVENTIONS 对 Health Profile 仍描述旧删除语义，也应同步。

不为了文档完整性重写所有历史 Stage 文档。

---

# 26. 自动测试重点

新增 Stage 08 后端测试至少覆盖：

## HealthProfile 删除

- 空档案；
- 只有 Favorite；
- 只有未完成 ingestion；
- 有正式报告；
- 多个 ingestion；
- OCR + MANUAL 混合；
- failed/retry OCR 历史；
- Confirmation REMOVED / MANUAL；
- 删除默认档案；
- 删除最后一个档案；
- 删除非默认档案；
- 跨用户；
- 重复 DELETE 安全。

## 正式数据

删除后：

```text
LabReport = 0
LabResult = 0
```

目标 profile 对应：

```text
我的指标 = 不可查询
Favorite = 0
```

其它 HealthProfile 的报告、趋势、Favorite 完全不受影响。

## 临时数据

删除后：

```text
ReportIngestion = 0
UploadAuthorization = 0
ReportAsset = 0
OcrTask = 0
OcrResultItem = 0
ConfirmationItem = 0
```

## FileCleanup

- 每个 ingestion 有 PREFIX cleanup；
- prefix 正确；
- active upload authorization 产生未来 not_before；
- 没有活跃 authorization 时可立即 due；
- not_before 前 worker 不处理；
- not_before 后处理；
- COS 失败保持 PENDING；
- retry 后 DONE；
- OBJECT 既有行为不变；
- Stage 05 report delete 的 NULL not_before 仍立即处理。

## PROCESSING

- PROCESSING OCR 阻断；
- 阻断时 0 DB 数据被删除；
- 0 新 profile cleanup 被提交；
- task/ingestion 保持原状。

---

# 27. PostgreSQL 17 专项

新增：

```text
backend/tests/verify_postgres_profile_deletion.py
```

或等价独立验证脚本。

至少验证：

## Migration

```text
0007 → 0008
```

以及：

```text
空库 0001 → ... → 0008
```

并验证历史：

```text
FileCleanup.not_before = NULL
```

保持原语义。

## 完整数据链

构造一个 profile：

```text
多个 ingestion
+
至少一份正式报告
+
至少一个 Favorite
+
OCR / Confirmation / Asset
```

执行删除后核对所有目标表。

## Rollback

人为注入数据库异常：

```text
FileCleanup 创建失败
或
中间删除失败
```

必须整事务 rollback。

## OCR claim 竞争

双 session：

```text
Profile DELETE
vs
Worker claim QUEUED task
```

验证只允许第 11 节两类安全结果。

## commit 竞争

```text
Profile DELETE
vs
Stage 04 commit
```

不得产生 orphan 正式数据。

## migrate 竞争

```text
Profile DELETE
vs
Stage 05 report migrate
```

最终三处 profile 归属必须一致，或被删除，不得半迁移。

## UploadAuthorization 竞争

验证：

```text
已签发凭据的 expires_at
```

被纳入 not_before。

并模拟：

```text
DB 删除后 / not_before 前出现晚到 object
→ due 后 PREFIX cleanup 可删除
```

不要求真实 COS；可使用合成 COS adapter，但数据库并发必须是真实 PostgreSQL 17。

## 临时库

所有 Stage 08 PG 测试库必须：

```text
唯一命名
finally 删除
独立查询 pg_database 确认不存在
```

---

# 28. Miniapp 自动测试

至少新增/调整纯逻辑测试覆盖：

- deletion impact 文案数据；
- PROCESSING 阻断状态；
- 删除成功刷新；
- 删除默认 profile 后 replacement；
- 删除最后 profile 的空状态；
- DELETE 响应丢失后刷新列表可恢复；
- API 409 不误显示成功。

然后执行：

```text
pnpm test
pnpm typecheck
pnpm build:mp-weixin
```

不引入新的 UI 框架或状态管理库。

---

# 29. Admin 回归

Stage 08 不增加 Admin 用户健康数据管理。

必须继续：

```text
admin-web pnpm test（如当前已有）
admin-web pnpm typecheck
admin-web pnpm build
```

并确认：

- Admin Token 不能调用普通用户 HealthProfile 删除；
- StandardMetric / MetricAlias / OCR issue / OCR task 现有能力不受影响。

---

# 30. OCR 冻结边界

Stage 08 不修改：

```text
backend/ocr_runtime/**
OCR matcher
threshold
fuzzy score
unit scoring
retry
evidence
FINAL_AUTO / FINAL_REVIEW
Pipeline Version
```

允许为了 Stage 08 检查并发边界读取：

```text
ocr_worker.py
ocr_queue.py
ocr_pipeline.py
```

但本阶段推荐方案已经通过：

```text
PROCESSING 阻断
```

避免为了删除档案引入 OCR cancel 或修改运行时。

如果实现确需修改产品侧 queue/worker 协作：

- 必须证明不改变 OCR 识别结果；
- 不得修改 runtime；
- Frozen Regression 仍按 Stage 07 规则核对；
- 变更必须仅服务于生命周期安全。

默认不需要。

---

# 31. 既有回归

必须完整保持：

## Stage 03

- queue；
- lease；
- retry；
- OcrResultItem 不可变；
- Worker 正常处理。

## Stage 04

- Confirmation；
- REVIEW；
- commit；
- pure manual；
- duplicate；
- StandardMetric 选择。

## Stage 05

- 正式报告列表/详情；
- 报告迁移；
- 单份报告删除；
- FileCleanup OBJECT / PREFIX；
- cleanup retry。

## Stage 06

- 我的指标；
- history；
- trend；
- Favorite；
- report migrate/delete 后自然变化。

## Stage 07

- StandardMetric；
- MetricAlias；
- exact resolver；
- OCR issue；
- Admin Auth；
- OCR Task readonly。

Stage 08 不能通过删除/skip/弱化旧测试制造 PASS。

---

# 32. 负责人真实微信人工验收

Stage 08 最终 PASS 前必须由负责人实际在微信小程序完成。

至少：

## T01｜空档案删除

```text
新建空 HealthProfile
→ 删除
→ 列表消失
```

## T02｜真实使用档案删除

准备一个包含：

```text
正式报告
我的指标历史
Favorite
```

的测试 HealthProfile。

执行：

```text
健康档案管理
→ 删除
→ 查看影响摘要
→ 明确确认永久删除
→ 删除成功
```

确认：

- profile 消失；
- 报告不再可见；
- 我的指标不再可见；
- Favorite 不再可见；
- 原报告入口不可再访问。

## T03｜未完成任务

准备：

```text
READY / OCR_FAILED / PENDING_CONFIRMATION
```

中的至少一个真实未完成测试任务。

删除 profile 后：

- 任务记录消失；
- 不能再次打开；
- 不要求逐个先删除任务。

## T04｜默认档案删除

删除当前默认 profile。

确认：

- 其它 profile 成为当前档案；
- 首页 / 报告 / 我的指标使用 replacement；
- 不出现已删除 profile。

## T05｜最后一个档案删除

删除用户最后一个 HealthProfile。

确认：

```text
首页进入“还没有健康档案”
→ 可以重新创建档案
```

## T06｜PROCESSING 阻断

真实触发 OCR PROCESSING 后尝试删除。

必须：

- 明确提示正在识别，暂不能删除；
- profile 和任务均还存在；
- OCR 结束后再次删除可以成功。

不要求负责人真实制造 COS 删除故障；COS not_before、失败重试和晚到文件由自动/PG 集成验证承担。

---

# 33. 本阶段明确不做

Stage 08 不实现：

```text
账号注销 / 删除 User
微信账号解绑
家庭成员邀请
多人协同
共享报告
导出全部数据
隐私中心
回收站
恢复删除档案

报告编辑
LabResult 编辑
历史重新标准化
历史 standard_metric_id 回填

OCR 算法优化
OCR cancel / 强制终止
OCR matcher 修改
threshold 修改
Pipeline Version 修改

AI 解读
医学建议
异常提醒推送
订阅消息
阈值提醒

首页 Dashboard 产品化
全项目 UI / UX 重构
底部 Tab 总体改版
Admin 视觉重构

生产部署
Nginx
进程守护
监控
备份恢复
发布
```

其中：

```text
首页产品化 + 统一 UI / UX
```

统一进入 Stage 09。

```text
上线前可靠性 / 安全 / 运行体系
```

进入 Stage 10。

之后才进入部署与发布。

---

# 34. 预期主要实现范围

预计主要涉及：

## Backend

```text
app/api/v1/business.py
app/reports.py 或新 profile_deletion.py
app/cleanup_worker.py
app/models/entities.py

migrations/versions/0008_profile_data_deletion.py

tests/test_stage08.py
tests/verify_postgres_profile_deletion.py
```

建议：

> 不要把复杂 profile 删除继续堆进 `business.py`。

可以抽取：

```text
profile_deletion.py
```

或等价 service，复用 Stage 05 已验证的 ingestion 链删除逻辑。

如果抽取通用：

```text
delete_ingestion_chain(...)
```

必须保证 Stage 05 report deletion 既有行为和测试全部保持。

## Miniapp

```text
src/pages/profiles/index.vue
src/api.ts（如需类型）
tests/*
```

原则上不新增页面。

## Admin

无业务页面新增。

---

# 35. 文档更新

Stage 08 完成时至少更新：

```text
README.md
backend/README.md
miniapp/README.md（如现有结构需要）
docs/01-architecture/DATA_MODEL.md
本目录 RESULT.md
```

如 `deploy/README.md` 已记录 cleanup worker 运行方式，而 not_before 不改变启动命令，只需在确有必要时同步，不做无关部署设计。

---

# 36. Definition of Done

Stage 08 只有同时满足以下条件才能 PASS：

```text
Stage 07 基线未破坏

+

HealthProfile 删除不再被 PROFILE_HAS_INGESTIONS 永久阻断
+
用户可查看删除影响摘要
+
危险删除有明确不可恢复确认

+

目标 HealthProfile 物理删除
+
全部 MetricFavorite 删除
+
全部正式 LabReport / LabResult 删除
+
全部 Confirmation 删除
+
全部 OCR Task / Result 删除
+
全部 ReportAsset / UploadAuthorization / ReportIngestion 删除

+

每个 ingestion 都有可靠 PREFIX cleanup
+
活跃上传凭据通过 not_before 安全覆盖
+
cleanup 到期可删除晚到文件
+
COS 临时失败可继续 PENDING 重试
+
Stage 05 原 FileCleanup 行为不回归

+

PROCESSING OCR 安全阻断
+
QUEUED claim 与 profile delete 竞争安全
+
commit / migrate / upload auth / Favorite 并发无 orphan

+

默认 HealthProfile 正确替换
+
最后一个 HealthProfile 可删除
+
跨用户隔离通过

+

0007 → 0008 PostgreSQL 17 migration PASS
+
空库 0001 → 0008 PASS
+
事务 rollback PASS
+
并发专项 PASS
+
临时测试库全部删除

+

Backend 全量 pytest PASS
+
Ruff PASS
+
Miniapp test/typecheck/build PASS
+
Admin test/typecheck/build PASS

+

OCR runtime diff = 0
+
Pipeline Version / threshold / retry / matcher 不变
+
0001～0007 未修改
+
Stage 03 migration drift 未顺手修复

+

负责人真实微信 T01～T06 全部 PASS
+
RESULT.md 完整

+

未进入 Stage 09 UI / UX
+
未进入 Stage 10 上线前收口
+
未进入部署发布
```

任意 P0 未满足：

```text
Stage 08 = FAIL
```

---

# 37. Stage 09 交接边界

Stage 08 PASS 后，核心 MVP 业务与数据生命周期视为完整。

Stage 09 统一进入：

```text
小程序整体产品化
+
首页 / 异常标记 / 待处理事项
+
信息架构
+
统一 UI / UX 打磨
+
Admin 基础视觉与交互一致性
```

Stage 09 不应重新打开 Stage 08 隐私删除语义。

---

# 38. Stage 10 与发布边界

Stage 10 再处理：

```text
上线前可靠性
安全强化
长期进程运行
配置校验
日志 / 监控
备份恢复
依赖与构建风险
```

之后单独进入：

```text
部署
真实环境 migration
Worker / Cleanup Worker 运行
Nginx / HTTPS
COS / 域名
微信小程序发布准备
上线验证
```

Stage 08 不提前完成这些内容。

---

# 39. Stage 08 冻结结论

Stage 08 最终设计主题：

```text
健康档案完整隐私删除
+
整档案数据生命周期闭环
+
上传临时凭据安全窗口处理
+
可靠 COS prefix cleanup
+
OCR PROCESSING 安全阻断
+
PostgreSQL 事务 / 并发证明
```

不扩大为：

```text
账号注销
全局隐私中心
UI 重构
OCR 算法
生产部署
```

本 PLAN 确认后，以 `ACCEPTANCE.md` 作为最终 PASS 的唯一阶段验收基线。
