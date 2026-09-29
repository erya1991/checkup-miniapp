# D-0003｜OCR/确认域与正式报告域分离

日期：2026-09-29  
状态：Accepted

## 决定

不使用一个 `report(status=draft/confirmed)` 万能实体承载所有数据。

采用：
`ReportIngestion → OcrResultItem → ConfirmationItem → commit → LabReport/LabResult`。

## 原因

医疗检验数据不能因 OCR 高置信度而静默写错。物理/逻辑隔离能确保未确认数据天然不会进入历史趋势。

## 影响

开发时需要维护导入域和正式域两套实体，但换来清晰的安全边界和审计能力。

## 重新评估条件

原则上作为核心安全架构长期保持。
