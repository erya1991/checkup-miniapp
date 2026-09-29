# Stage 02｜微信登录、健康档案与报告图片上传

**状态：READY_FOR_IMPLEMENTATION**

## 1. 阶段目标

本阶段是 MVP 第一个真实业务阶段。

目标是完成：

> 微信用户能够进入小程序，创建和切换本人/家庭成员健康档案，并为指定健康档案创建一份报告导入任务，将单张或多张检验报告图片安全上传到腾讯云 COS，在小程序中完成预览、追加、排序和删除；退出小程序后再次进入，数据仍然正确存在。

本阶段结束时，系统必须形成以下真实链路：

```text
微信登录
→ 系统 User
→ 创建/选择 HealthProfile
→ 创建 ReportIngestion
→ 选择图片
→ 获取受限 COS 临时上传授权
→ 小程序直传 COS
→ 登记 ReportAsset
→ 图片预览 / 追加 / 排序 / 删除
→ ReportIngestion 达到 READY
```

本阶段**不执行 OCR**。

## 2. 上游基线

实施前必须读取：

- `AGENTS.md`
- `docs/00-baseline/PRODUCT_BASELINE.md`
- `docs/00-baseline/TECH_BASELINE.md`
- `docs/00-baseline/DEVELOPMENT_RULES.md`
- `docs/stages/01-foundation/RESULT.md`
- 本目录 `PLAN.md`
- 本目录 `ACCEPTANCE.md`

如与当前工程实际结构冲突，以：

1. 已冻结产品/技术基线；
2. Stage 01 已验收的真实工程结构；

为优先依据。

不得为了方便 Stage 02 而推翻 Stage 01 已验收骨架。

## 3. Stage 01 已知真实基础

Stage 01 已完成并通过验收，当前可直接复用：

- FastAPI 工程骨架；
- SQLAlchemy；
- Alembic；
- PostgreSQL 17 开发容器；
- `compose.yaml` 根目录启动方式；
- 后端健康检查；
- uni-app + Vue 3 + TypeScript 小程序骨架；
- Vue 3 + Vite + Element Plus 管理后台骨架；
- 环境变量规范；
- 基础测试、typecheck、build 能力。

本阶段不得重复初始化这些工程。

# 4. 本阶段范围

## 4.1 后端 P0

必须实现：

### 认证

- 微信小程序登录接口；
- 使用小程序 `wx.login` / `uni.login` 获得临时 code；
- 后端使用微信服务端接口交换微信身份；
- 创建或查找系统 `User`；
- 签发系统自己的访问令牌；
- 后续业务 API 不直接以微信 code 作为身份凭据；
- 微信 `AppSecret` 只能存在后端环境变量。

### User

实现最小 User 数据模型。

本阶段只保存完成业务所需的最少信息，不要求：手机号、身份证、实名认证、用户画像。

### HealthProfile

实现：创建、列表、详情、编辑、删除、当前/默认健康档案设置。

至少支持关系：本人、父亲、母亲、配偶、其他。

性别、出生日期允许为空。

### ReportIngestion

实现报告导入工作区。

本阶段只实际使用：

- `UPLOADING`
- `READY`
- `CANCELLED`（如当前设计需要）

不得实现 OCR 状态流转。

必须归属当前 User 和指定 HealthProfile。

### ReportAsset

实现：

- 多图片；
- 页码/顺序；
- COS object key；
- MIME type；
- 文件大小；
- 上传状态；
- 必要的文件完整性元数据。

### COS 文件服务

实现：

- 服务端生成随机对象路径；
- 服务端申请/签发受限临时凭证；
- 凭证只能用于当前授权对象或最小必要路径；
- 小程序客户端直接上传 COS；
- 永久 SecretKey 不得返回给前端；
- 上传成功后由业务 API 登记 `ReportAsset`；
- 删除未进入 OCR 的图片时，同步删除 COS 对象或通过可靠的文件清理流程完成删除。

### 数据权限

所有 HealthProfile、ReportIngestion、ReportAsset 必须验证当前登录用户所有权。

不能只知道资源 ID 就读取或修改他人数据。

## 4.2 小程序 P0

必须实现：

### 启动与登录

- 小程序启动；
- 获取微信登录 code；
- 调用后端登录；
- 保存系统 Token；
- Token 失效时能够重新进入登录流程；
- 登录失败有明确错误状态。

### 首次使用

没有健康档案时，引导用户创建第一个档案，推荐默认关系为“本人”。

不得强制用户填写非必要敏感信息。

### 首页基础业务版

至少具备：

- 当前健康档案；
- 健康档案切换入口；
- 上传报告主入口。

不要求最近正式报告、关注指标、异常统计，因为正式报告尚未进入本阶段。

### 健康档案管理

完成：档案列表、创建、编辑、删除、切换当前健康档案。

切换后必须影响后续上传归属。

### 上传报告

完成：

- 当前报告所属健康档案确认；
- 拍照；
- 相册选图；
- 支持多图；
- 上传进度；
- 上传失败重试；
- 上传完成后的图片确认页。

### 图片确认

完成：

- 多图预览；
- 放大查看；
- 追加图片；
- 删除图片；
- 调整图片顺序；
- 显示页序；
- 离开页面后重新进入仍可恢复导入任务及图片顺序。

### Stage 03 入口边界

可以展示“开始识别”作为流程占位，但 Stage 02 必须：

- 不创建 OcrTask；
- 不调用 OCR；
- 不生成 OcrResultItem；
- 不进入确认页。

建议按钮当前显示为“下一阶段接入 OCR”或开发环境明确标识未启用。

不得伪造 OCR 成功结果。

## 4.3 管理后台

Stage 02 **不开发正式后台业务功能**。

允许保持 Stage 01 占位页；禁止提前实现标准指标库、指标别名、报告分类、OCR 记录后台、用户健康数据管理。

# 5. 本阶段明确不做

本阶段不得实现：

- OCR Worker；
- OCR Pipeline 正式接入；
- OcrTask；
- OcrResultItem；
- AUTO / REVIEW；
- ConfirmationItem；
- 报告基本信息 OCR 识别；
- 人工确认页；
- 重复报告判断；
- LabReport；
- LabResult；
- 我的指标；
- 指标趋势；
- 关注指标；
- 管理后台业务页面；
- Redis / Celery / RabbitMQ / 微服务。

# 6. 数据模型

## 6.1 User

最小字段建议：

- `id`
- `wechat_openid`
- `status`
- `default_health_profile_id`（允许为空）
- `created_at`
- `updated_at`
- `last_login_at`

`wechat_openid` 应具备唯一约束。

如实际微信身份方案需要记录其它微信侧稳定标识，应保持最小化，并在 RESULT 中说明。

## 6.2 HealthProfile

至少：

- `id`
- `user_id`
- `display_name`
- `relation`
- `gender`（可空）
- `birth_date`（可空）
- `status`
- `created_at`
- `updated_at`

规则：必须属于一个 User；不同 User 的档案严格隔离。

## 6.3 ReportIngestion

至少：

- `id`
- `user_id`
- `health_profile_id`
- `mode`
- `status`
- `created_at`
- `updated_at`

Stage 02 中 `mode = OCR` 可作为默认上传模式；状态仅实际使用当前阶段需要的值。

至少存在一张有效已上传图片后，才可达到 `READY`。

## 6.4 ReportAsset

至少：

- `id`
- `ingestion_id`
- `cos_object_key`
- `page_no`
- `original_filename`（如保留）
- `mime_type`
- `file_size`
- `upload_status`
- `created_at`

可按需增加 checksum、width / height，但不得无业务需要扩展大量图片元数据。

# 7. 数据库迁移

Stage 02 必须通过 Alembic migration 创建正式业务表。

要求：

- 不直接手工修改数据库；
- migration 可从 Stage 01 基线数据库正常 `upgrade head`；
- 在干净数据库上也可完整升级；
- 如实现 downgrade，应保证至少本阶段 migration 可安全回退；若项目基线不要求 downgrade，必须在 RESULT 说明。

# 8. API 范围

接口具体响应结构遵循项目统一 API 规范。

## 8.1 Auth

### `POST /api/v1/auth/wechat`

输入微信临时 code。

行为：

```text
code
→ 微信服务端身份交换
→ User 查找/创建
→ 系统 Token
```

返回至少：access token、token 类型/有效期、当前用户基础信息。

如同时实现 refresh token，必须保持简单，并在 RESULT 说明。

自动测试不得依赖真实微信网络，应 mock 微信身份交换服务。

## 8.2 Current User

### `GET /api/v1/me`

返回当前 User、default health profile id、必要初始化状态。

## 8.3 HealthProfile

```text
GET    /api/v1/health-profiles
POST   /api/v1/health-profiles
GET    /api/v1/health-profiles/{id}
PATCH  /api/v1/health-profiles/{id}
DELETE /api/v1/health-profiles/{id}
```

设置默认档案：

```text
PUT /api/v1/me/default-health-profile
```

## 8.4 ReportIngestion

```text
POST /api/v1/ingestions
GET  /api/v1/ingestions/{id}
```

创建至少输入：`health_profile_id`、`mode`。

如首页真实需要恢复未完成任务，可增加按状态查询，但避免扩展通用查询系统。

## 8.5 COS 上传授权

```text
POST /api/v1/ingestions/{id}/upload-authorizations
```

后端负责：验证所有权、验证允许上传、生成随机 COS object key、获取最小权限临时凭证、返回必要上传信息。

前端不得自行决定任意对象路径，也不得获取永久 COS SecretKey。

## 8.6 Asset 登记

```text
POST /api/v1/ingestions/{id}/assets
```

只有 COS 上传成功后才能登记业务 Asset。

服务端应校验 ingestion 所有权、object key 是否属于本次授权范围、页序数据基本合法。

## 8.7 Asset 排序

```text
PUT /api/v1/ingestions/{id}/assets/order
```

要求一次提交完整排序；服务端验证所有 asset 均属于该 ingestion；页码/顺序不得重复；操作原子化。

## 8.8 删除 Asset

```text
DELETE /api/v1/ingestions/{id}/assets/{asset_id}
```

要求校验所有权；数据库删除与 COS 文件删除策略明确；删除后页序有效；最后一张有效图片删除后 ingestion 不得保持 `READY`。

# 9. COS 安全规则

必须遵守：

1. COS Bucket 使用私有读写；
2. 永久 SecretId / SecretKey 只存在服务端环境；
3. 客户端使用短时临时凭证；
4. 临时策略遵循最小权限；
5. object key 由服务端生成；
6. object key 不包含真实姓名、医院名称等敏感信息；
7. 推荐路径：

```text
users/{user_uuid}/ingestions/{ingestion_uuid}/original/{random_uuid}.{ext}
```

8. 前端不得获得列目录、读取其他用户对象等额外权限；
9. Stage 02 上传凭证只用于上传必要对象，不提前授予其它权限。

# 10. 小程序页面

本阶段至少实现或完善：

- P01 首页：当前健康档案、切换档案、上传报告；
- P02 健康档案切换：列表、当前标识、新建入口；
- P03 健康档案管理：新增、编辑、删除；
- P04 上传报告：当前归属档案、拍照、相册；
- P05 图片确认：多图、预览、追加、排序、删除、上传状态。

不实现 P06 OCR 处理中。

# 11. 前端状态规则

全局只维护必要状态：`authToken`、`user`、`currentHealthProfile`。

不得把所有上传页和档案列表数据永久塞入全局 store。

报告上传状态应以服务端 ReportIngestion / ReportAsset 为事实来源。

退出重进可以缓存 ingestion id，但最终必须重新从 API 获取真实状态。

# 12. 权限规则

必须自动测试：User A 不得查看、修改、删除 User B 的 HealthProfile；不得使用 B 的 profile 创建 ingestion；不得查看 B 的 ingestion；不得为 B 的 ingestion 获取 COS 授权；不得登记、排序、删除 B 的 Asset。

所有此类请求必须返回项目统一安全响应，不能泄露他人资源是否存在。

# 13. 删除规则

HealthProfile 若存在未完成 ingestion，推荐阻止直接删除并提示先处理/取消；或在完整事务和文件清理策略下级联取消。最终方案必须记录在 RESULT，不建设复杂回收站。

ReportAsset 删除后，COS 文件不能长期成为无业务引用孤儿；文件删除失败必须留下可排查记录。

# 14. 环境变量

在 `.env.example` 增加但不得填写真实值：

```text
WECHAT_APP_ID=
WECHAT_APP_SECRET=
COS_SECRET_ID=
COS_SECRET_KEY=
COS_BUCKET=
COS_REGION=
```

如 STS SDK 需要其它配置，再补充最少字段。

# 15. 测试要求

至少包括：

## Backend

- 微信登录 service mock；
- 新用户首次登录创建；
- 已存在用户再次登录；
- 未认证请求拒绝；
- HealthProfile CRUD；
- 默认档案；
- 跨用户权限隔离；
- ingestion 创建；
- 非本人 profile 创建 ingestion 拒绝；
- upload authorization 权限测试；
- object key 安全测试；
- asset 登记；
- asset 排序；
- asset 删除；
- ingestion READY 条件；
- Alembic migration。

## Frontend

- `pnpm typecheck`
- `pnpm build:mp-weixin`
- 关键业务状态无 TypeScript 错误。

Stage 02 不要求建设复杂 E2E 自动化框架。

# 16. 最终交付物

完成后至少存在：

- User / HealthProfile / ReportIngestion / ReportAsset 数据模型；
- 对应 migrations；
- 微信认证 API；
- HealthProfile API；
- ingestion / asset API；
- COS 上传授权服务；
- 小程序登录流程；
- 小程序档案页面；
- 小程序上传及图片确认流程；
- 后端测试；
- 小程序 typecheck/build；
- 更新后的 README；
- `RESULT.md`。

# 17. Definition of Done

只有同时满足：

```text
真实微信登录可用
+
健康档案真实入库
+
档案切换正确
+
真实图片可直传私有 COS
+
ReportIngestion / ReportAsset 正确入库
+
多图追加/排序/删除正确
+
退出重进可恢复
+
跨用户权限测试通过
+
没有真实 Secret 进入 Git
+
自动测试通过
+
ACCEPTANCE 全部 P0 PASS
```

Stage 02 才可以标记为 PASS。

否则 RESULT 必须保持 FAIL。

完成后停止，不进入 Stage 03。
