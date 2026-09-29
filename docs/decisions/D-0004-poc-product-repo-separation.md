# D-0004｜OCR PoC/Regression 与正式产品仓库职责分离

日期：2026-09-29  
状态：Accepted

## 决定

`checkup-ocr-poc` 继续负责 OCR 算法实验、真实样本泛化和 Regression；正式 `checkup-miniapp` 负责产品业务和稳定 Pipeline 接入。

## 原因

避免业务开发破坏已经冻结的 OCR 回归能力，也避免正式产品仓库被大量实验脚本/样本/中间产物污染。

## 影响

算法变更先在 PoC 验证，再以明确版本迁入正式产品。
