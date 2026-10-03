# Miniapp（Stage 09：等待人工验收）

uni-app + Vue 3 + TypeScript 微信小程序。一级入口为首页 / 报告 / 我的；报告内切换检验报告 / 我的指标。首页提供新上传、多个待处理报告摘要、最近正式报告及关注指标。上传入口始终开始新流程，指定未完成报告从待处理列表继续；识别完成后仍需人工核对并最终保存。使用腾讯 `cos-wx-sdk-v5` 直传私有 COS；Token 本地存储，业务列表按页面从 API 获取。

Stage09 统一公共 tokens、PageContainer、UiState、StatusTag、ProfileContext 与 MetricList；使用原生 TabBar、导航、picker、图片预览、Modal 和 ActionSheet。通过 getAppBaseInfo 适配微信字体倍率；大字体、真机点击热区与返回栈仍需负责人实测。67 项 tests、typecheck、微信构建通过；Stage09 状态为 AUTOMATED PASS / WAITING MANUAL ACCEPTANCE，T01～T11 待验，见 [RESULT](../docs/stages/09-productization-ui-ux/RESULT.md)。

上述为Stage02上传基础；后续已具备OCR、人工确认、正式报告、指标历史与趋势。Stage08在“健康档案管理”提供整档案永久删除：先从服务器读取影响，显示报告/未完成任务/关注数量及不可恢复说明；PROCESSING明确阻断；取消不发DELETE。成功后重新读取档案和/me，替换当前档案或显示空状态；删除响应丢失时依据服务器列表恢复，不自动重复危险删除。前端没有新增全局store或页面。首页、报告、指标页继续在onShow按服务端默认档案刷新。

最终 `pnpm test`（42项，0 failed、0 skipped）、`pnpm typecheck`、`pnpm build:mp-weixin` 全部通过。负责人2026-10-03真实微信T01～T06全部PASS，Stage08最终PASS；实机结果不以自动/API/PG验证替代，见 [Stage08 RESULT](../docs/stages/08-profile-data-deletion/RESULT.md)。其它目标环境需后端升级0008、重启API/cleanup worker，并导入构建产物。

```powershell
pnpm install
pnpm typecheck
pnpm dev:mp-weixin
pnpm build:mp-weixin
```

在微信开发者工具导入 `miniapp/dist/build/mp-weixin`，使用真实小程序 AppID。`manifest.json` 不保存真实 AppID；API 地址入口在 `src/config.ts`，通过 `VITE_API_BASE_URL=https://<API 域名>/api/v1` 配置。微信公众平台配置 HTTPS API request 合法域名、COS Bucket 域名 request/uploadFile/downloadFile 合法域名；保持合法域名检查开启。后端需配置真实微信和 COS 凭据，COS Bucket 私有。使用脱敏测试图片按 Stage 02 `ACCEPTANCE.md` 实测后才能验收。
