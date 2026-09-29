# Codex Prompt｜执行 Stage 02

现在正式开始：

# 研发阶段 02｜微信登录、健康档案与报告图片上传

当前工作目录必须是本项目 Git 仓库根目录。

## 1. 开始前必须读取

首先读取：

- `AGENTS.md`

然后读取：

- `docs/00-baseline/PRODUCT_BASELINE.md`
- `docs/00-baseline/TECH_BASELINE.md`
- `docs/00-baseline/DEVELOPMENT_RULES.md`
- `docs/stages/01-foundation/RESULT.md`
- `docs/stages/02-profile-upload/PLAN.md`
- `docs/stages/02-profile-upload/ACCEPTANCE.md`

如上游文档引用其它当前实现相关文件，再按需读取。

不要无目的读取整个仓库文档。

## 2. 先检查真实工程

编码前：

1. `git status`
2. 确认当前分支为 Stage 02 专用分支；
3. 查看 Stage 01 已实现的 backend / miniapp / compose / tests 结构；
4. 简要说明 Stage 02 实施顺序；
5. 然后直接开始执行。

不要重新初始化 Stage 01 已存在的工程。

## 3. 本阶段核心目标

必须完成真实链路：

```text
微信登录
→ User
→ 创建/选择 HealthProfile
→ 创建 ReportIngestion
→ 小程序获取受限 COS 临时上传授权
→ 小程序直传私有 COS
→ 登记 ReportAsset
→ 多图预览 / 追加 / 排序 / 删除
→ 退出重进恢复
→ ingestion READY
```

本阶段到 READY 为止。

## 4. 严格禁止提前实现 OCR

禁止实现或启用：

- OcrTask
- OCR Worker 正式任务
- OCR Pipeline 产品接入
- OcrResultItem
- AUTO / REVIEW
- ConfirmationItem
- LabReport
- LabResult
- 趋势
- 正式报告管理

即使页面上存在“开始识别”，也不得真正运行 OCR。

## 5. 微信登录

实现真实微信小程序登录业务，但自动测试必须 mock 微信服务端身份交换，不得让测试依赖外网。

要求：

- 微信 AppSecret 仅服务端使用；
- 不进入 miniapp；
- 不进入 Git；
- 同一微信身份不能重复创建 User；
- 业务 API 使用系统自己的 Token 鉴权。

不要自行增加手机号、身份证、实名认证等产品范围外信息。

## 6. COS 上传

采用：

> 服务端生成 object key + 服务端获取最小权限临时凭证 + 小程序直接上传私有 COS。

要求：

- 永久 COS Secret 不返回客户端；
- 临时授权最小权限；
- object key 不含姓名、医院等敏感信息；
- Bucket 私有；
- 上传成功后再登记 ReportAsset；
- 上传失败不得误登记成功；
- 跨用户不能获取授权或操作 Asset。

不要为了方便将 Bucket 改成公开读写。

## 7. 数据库

使用 Alembic migration。

本阶段核心数据实体：

- User
- HealthProfile
- ReportIngestion
- ReportAsset

不要手工改数据库作为正式方案。

不要提前创建 Stage 03 正式业务表。

## 8. 小程序

必须真实实现：

- 登录；
- 首次无档案引导；
- 健康档案创建/编辑/切换；
- 首页当前档案；
- 上传报告；
- 拍照/相册；
- 多图上传；
- 图片确认；
- 预览；
- 追加；
- 排序；
- 删除；
- 退出重进恢复。

优先保证流程和可靠性，不进行复杂视觉打磨。

## 9. 实施中遵循 ACCEPTANCE

边开发边运行自动测试。

禁止：

- 删除失败测试；
- 弱化断言；
- 屏蔽错误；
- 使用假成功页面代替真实 API；
- 用本地假图片列表代替真实 ReportAsset；
- 用公开 COS URL 绕过权限；
- 为通过测试关闭鉴权。

## 10. 完成后验收

代码完成后：

1. 重新读取 `ACCEPTANCE.md`；
2. 执行全部可自动执行的 P0；
3. 对必须人工完成的微信开发者工具 / COS 验收明确标记待人工验证；
4. 未完成的 P0 存在时，Stage 02 必须保持 FAIL；
5. 不得因为“代码看起来完成”就标 PASS。

如果需要用户手工完成：

- 微信合法域名；
- COS 白名单；
- 微信开发者工具真实登录；
- 真实图片上传；

请清晰给出操作步骤，停止等待人工结果，不要伪造 PASS。

## 11. RESULT.md

更新：

`docs/stages/02-profile-upload/RESULT.md`

必须包含：

- PASS / FAIL；
- 实际完成内容；
- 修改文件；
- migration；
- 实际依赖版本；
- 真实测试命令和数量；
- ACCEPTANCE 编号结果；
- 微信开发者工具结果；
- COS 配置与安全确认；
- 设计偏差；
- 已知问题；
- 下一阶段注意事项。

## 12. 阶段结束

最终汇报：

1. Stage 02 状态；
2. 自动测试结果；
3. 尚需人工验收项；
4. 与 PLAN 的差异；
5. 已知问题；
6. 是否具备进入 Stage 03 条件。

不要创建 Stage 03 PLAN。
不要开始 Stage 03。
