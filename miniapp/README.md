# Miniapp（Stage 02）

uni-app + Vue 3 + TypeScript 微信小程序：首页登录、档案创建/编辑/切换、相册/拍照多图直传私有 COS、图片预览/追加/排序/删除及 API 恢复。上传完成只到 READY，不执行 OCR。使用腾讯 `cos-wx-sdk-v5`；系统 Token 存在小程序本地存储，档案和图片列表从 API 加载。

```powershell
pnpm install
pnpm typecheck
pnpm dev:mp-weixin
pnpm build:mp-weixin
```

在微信开发者工具导入 `miniapp/dist/build/mp-weixin`，使用真实小程序 AppID。`manifest.json` 不保存真实 AppID；API 地址入口在 `src/config.ts`，通过 `VITE_API_BASE_URL=https://<API 域名>/api/v1` 配置。微信公众平台配置 HTTPS API request 合法域名、COS Bucket 域名 request/uploadFile/downloadFile 合法域名；保持合法域名检查开启。后端需配置真实微信和 COS 凭据，COS Bucket 私有。使用脱敏测试图片按 Stage 02 `ACCEPTANCE.md` 实测后才能验收。
