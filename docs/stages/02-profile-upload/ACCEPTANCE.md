# Stage 02｜验收标准

**阶段：微信登录、健康档案与报告图片上传**

> 本文档是 Stage 02 是否完成的唯一阶段验收基线。P0 项全部 PASS 才允许 Stage 02 = PASS。

# A. 工程与迁移

## A01｜Stage 01 基线未被破坏【P0】

验证：Backend 健康接口正常；admin-web 可 typecheck/build；miniapp 可 typecheck/build；PostgreSQL 开发容器可正常启动。

- [ ] PASS
- [ ] FAIL

## A02｜Stage 02 Migration 可执行【P0】

要求：Stage 01 数据库可 `upgrade head`；干净 PostgreSQL 数据库可完整迁移到 head；创建 User / HealthProfile / ReportIngestion / ReportAsset 所需结构；无手工 SQL 隐藏步骤。

- [ ] PASS
- [ ] FAIL

# B. 微信登录与认证

## B01｜真实微信小程序登录【P0】

Given：微信开发者工具配置真实小程序 AppID；后端本地 `.env` 配置真实但未提交 Git 的 `WECHAT_APP_SECRET`。

When：用户打开小程序。

Then：

```text
uni.login / wx.login
→ 临时 code
→ POST /api/v1/auth/wechat
→ 微信身份交换
→ 系统 User
→ 系统 Token
```

并成功进入应用。

- [ ] PASS
- [ ] FAIL

## B02｜首次登录创建 User【P0】

首次微信身份登录创建一个系统 User；`wechat_openid` 唯一；不重复创建。

- [ ] PASS
- [ ] FAIL

## B03｜重复登录不重复创建 User【P0】

同一微信用户再次登录返回同一系统 User，不产生重复账户。

- [ ] PASS
- [ ] FAIL

## B04｜未认证访问被拒绝【P0】

未携带有效系统 Token 时，`/me`、`/health-profiles`、`/ingestions` 等受保护 API 不得返回业务数据。

- [ ] PASS
- [ ] FAIL

## B05｜微信 AppSecret 不进入客户端和 Git【P0】

允许 `.env.example` 和文档保留字段名；禁止真实 secret、miniapp 源码中的 secret、被提交的 `.env`。

- [ ] PASS
- [ ] FAIL

# C. 健康档案

## C01｜首次无档案状态【P0】

新 User 首次进入：系统识别无 HealthProfile；前端引导创建第一个档案；不出现空白页或错误死路。

- [ ] PASS
- [ ] FAIL

## C02｜创建“本人”档案【P0】

能够创建 `relation = SELF` 的档案；性别、生日允许为空；数据库真实保存。

- [ ] PASS
- [ ] FAIL

## C03｜创建家庭成员档案【P0】

至少验证父亲，以及母亲或其他成员。

- [ ] PASS
- [ ] FAIL

## C04｜编辑档案【P0】

能够修改 display name、relation 和可选字段；保存后刷新保持。

- [ ] PASS
- [ ] FAIL

## C05｜切换当前档案【P0】

创建至少“本人”和“父亲”；切换为父亲后：首页显示父亲；新建上传任务默认归属父亲；重新进入应用后默认档案仍正确。

- [ ] PASS
- [ ] FAIL

## C06｜跨用户档案隔离【P0】

自动测试构造 User A / User B。User A 不得 GET/PATCH/DELETE User B profile。

- [ ] PASS
- [ ] FAIL

# D. ReportIngestion

## D01｜创建报告导入任务【P0】

在“父亲”档案下创建 ingestion；user/profile 归属正确；初始状态正确；数据真实持久化。

- [ ] PASS
- [ ] FAIL

## D02｜不能使用他人 HealthProfile 创建任务【P0】

User A 使用 User B 的 `health_profile_id` 创建 ingestion 必须拒绝且不产生数据。

- [ ] PASS
- [ ] FAIL

## D03｜重新进入可恢复 ingestion【P0】

创建上传任务后退出上传页，再进入时通过 API 恢复 ingestion 和已登记图片，不只依赖前端内存。

- [ ] PASS
- [ ] FAIL

# E. COS 安全上传

## E01｜COS Bucket 为私有访问【P0】

当前 MVP COS Bucket 不是公开读写。

- [ ] PASS
- [ ] FAIL

## E02｜临时上传授权【P0】

`POST /api/v1/ingestions/{id}/upload-authorizations` 返回短时临时凭证、服务端生成 object key、必要 bucket/region/expiration；不得返回永久 SecretKey。

- [ ] PASS
- [ ] FAIL

## E03｜最小权限【P0】

临时授权只能上传当前授权对象或最小必要路径；不能获得整个 Bucket 任意读写；不能读取其他用户文件。

- [ ] PASS
- [ ] FAIL

## E04｜object key 不包含敏感个人信息【P0】

禁止包含真实姓名、关系称谓、医院名称、报告编号等业务敏感文本；推荐 UUID/随机 key。

- [ ] PASS
- [ ] FAIL

## E05｜真实小程序上传单图【P0】

微信开发者工具：选择 1 张图片 → 获取临时授权 → 小程序直传 COS → 上传成功 → 登记 ReportAsset。数据库和 COS 均存在对应数据。

- [ ] PASS
- [ ] FAIL

## E06｜真实小程序上传多图【P0】

至少上传 2 张图片；每张独立 ReportAsset；均属于同一 ingestion；初始顺序正确。

- [ ] PASS
- [ ] FAIL

## E07｜上传失败可恢复【P0】

模拟至少一种失败。要求：页面明确提示；失败文件不登记成功；可重试；不误判 ingestion READY。

- [ ] PASS
- [ ] FAIL

## E08｜微信小程序上传域名/白名单配置完成【P0】

完成 COS 小程序上传所需合法域名/白名单配置。不得通过永久关闭安全校验来“通过验收”。配置步骤记录在 README 或 RESULT。

- [ ] PASS
- [ ] FAIL

# F. 图片确认

## F01｜图片预览【P0】

上传成功后可查看缩略图、大图预览、多页切换。

- [ ] PASS
- [ ] FAIL

## F02｜追加图片【P0】

已有图片后继续追加，新增图片属于同一 ingestion，页序正确。

- [ ] PASS
- [ ] FAIL

## F03｜调整顺序【P0】

例如 `1,2,3 → 3,1,2`，保存后前端刷新和后端顺序均保持；API 原子验证完整排序。

- [ ] PASS
- [ ] FAIL

## F04｜删除图片【P0】

删除其中一张后：前端立即移除；数据库 Asset 正确处理；COS 按设计清理；其余页序有效。

- [ ] PASS
- [ ] FAIL

## F05｜删除最后一张图片后状态正确【P0】

删除最后一张有效图片后，ingestion 不得维持 READY；页面提示至少需要一张图片。

- [ ] PASS
- [ ] FAIL

## F06｜达到 READY【P0】

至少 1 张图片且业务登记图片均上传成功时，ingestion 可达到 READY；本阶段到此结束，不得自动进入 OCR。

- [ ] PASS
- [ ] FAIL

# G. 权限与安全

## G01｜跨用户 Ingestion 隔离【P0】

User A 不得查看 User B ingestion。

- [ ] PASS
- [ ] FAIL

## G02｜跨用户上传授权隔离【P0】

User A 不得为 User B ingestion 获取 COS 上传授权。

- [ ] PASS
- [ ] FAIL

## G03｜跨用户 Asset 操作隔离【P0】

User A 不得登记、排序、删除 User B 的 Asset。

- [ ] PASS
- [ ] FAIL

## G04｜真实 Secret 未提交【P0】

Git tracked files 不得存在 `.env`、微信 AppSecret、COS SecretKey、JWT Secret、数据库真实密码。

- [ ] PASS
- [ ] FAIL

# H. 自动测试与构建

## H01｜Backend Tests【P0】

运行项目规定测试命令；全部通过；至少覆盖认证 mock、档案 CRUD、权限、ingestion、assets。

记录：

```text
Command:
Result:
Tests:
```

- [ ] PASS
- [ ] FAIL

## H02｜Backend Lint / Static Check【P0】

运行 Stage 01 已建立的后端质量检查。

- [ ] PASS
- [ ] FAIL

## H03｜Miniapp Typecheck【P0】

运行 `pnpm typecheck` 或项目等价命令。

- [ ] PASS
- [ ] FAIL

## H04｜Miniapp Build【P0】

运行 `pnpm build:mp-weixin`。

- [ ] PASS
- [ ] FAIL

## H05｜Admin Web 未被破坏【P0】

至少 typecheck、build。

- [ ] PASS
- [ ] FAIL

# I. 人工主流程验收

## I01｜完整 Stage 02 主流程【P0】

在微信开发者工具中实际完成：

```text
启动小程序
↓
微信登录
↓
首次创建“本人”
↓
新增“父亲”
↓
切换到父亲
↓
上传报告
↓
从相册选择2张真实/测试报告图片
↓
图片直传COS
↓
预览
↓
调整顺序
↓
删除其中1张
↓
再补充1张
↓
退出当前页面
↓
重新进入
↓
任务和图片正确恢复
↓
确认 ingestion = READY
```

并验证：当前任务属于父亲；未启动 OCR；未生成正式报告。

- [ ] PASS
- [ ] FAIL

# J. 阶段边界

## J01｜未提前实现 Stage 03【P0】

仓库不得出现已启用的 OcrTask、OCR Worker 正式任务、OCR Pipeline 产品接入、OcrResultItem、AUTO/REVIEW、ConfirmationItem、LabReport/LabResult。

如存在后续预留空目录/声明，必须不产生业务行为并在 RESULT 说明。

- [ ] PASS
- [ ] FAIL

# K. 最终判定

只有所有 P0 PASS、自动测试 PASS、微信开发者工具真实主流程 PASS、真实 COS 上传 PASS、RESULT.md 已更新时，Stage 02 才能写 `PASS`。

任意 P0 未完成则为 `FAIL`，不得以“代码已完成但未手工验证”为 PASS。
