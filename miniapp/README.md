# Miniapp（Stage 08 = PASS）

uni-app + Vue 3 + TypeScript 微信小程序：首页登录、档案创建/编辑/切换、相册/拍照多图直传私有 COS、图片预览/追加/排序/删除及 API 恢复。上传完成只到 READY，不执行 OCR。使用腾讯 `cos-wx-sdk-v5`；系统 Token 存在小程序本地存储，档案和图片列表从 API 加载。

上述为Stage02上传基础；后续已具备OCR、人工确认、正式报告、指标历史与趋势。Stage08在“健康档案管理”提供整档案永久删除：先从服务器读取影响，显示报告/未完成任务/关注数量及不可恢复说明；PROCESSING明确阻断；取消不发DELETE。成功后重新读取档案和/me，替换当前档案或显示空状态；删除响应丢失时依据服务器列表恢复，不自动重复危险删除。前端没有新增全局store或页面。首页、报告、指标页继续在onShow按服务端默认档案刷新。

最终 `pnpm test`（42项，0 failed、0 skipped）、`pnpm typecheck`、`pnpm build:mp-weixin` 全部通过。负责人2026-10-03真实微信T01～T06全部PASS，Stage08最终PASS；实机结果不以自动/API/PG验证替代，见 [Stage08 RESULT](../docs/stages/08-profile-data-deletion/RESULT.md)。其它目标环境需后端升级0008、重启API/cleanup worker，并导入构建产物。

```powershell
pnpm install
pnpm typecheck
pnpm dev:mp-weixin
pnpm build:mp-weixin
```

在微信开发者工具导入 `miniapp/dist/build/mp-weixin`，使用真实小程序 AppID。`manifest.json` 不保存真实 AppID；API 地址入口在 `src/config.ts`，通过 `VITE_API_BASE_URL=https://<API 域名>/api/v1` 配置。微信公众平台配置 HTTPS API request 合法域名、COS Bucket 域名 request/uploadFile/downloadFile 合法域名；保持合法域名检查开启。后端需配置真实微信和 COS 凭据，COS Bucket 私有。使用脱敏测试图片按 Stage 02 `ACCEPTANCE.md` 实测后才能验收。
