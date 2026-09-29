# Miniapp（Stage 01）

uni-app + Vue 3 + TypeScript 的微信小程序占位工程，尚无登录、档案、上传或 OCR 业务。

```powershell
pnpm install
pnpm typecheck
pnpm dev:mp-weixin
pnpm build:mp-weixin
```

在微信开发者工具导入 `miniapp/dist/build/mp-weixin`。当前 `manifest.json` 未设置真实微信 AppID，构建产物使用游客 AppID；正式预览所需的 AppID 由后续授权配置。基础 API 地址入口位于 `src/config.ts`，可用 `VITE_API_BASE_URL` 配置；当前占位页不发起网络请求。
