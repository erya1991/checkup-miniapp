import assert from 'node:assert/strict'
import { test } from 'node:test'
import { abnormalDescription, resultIdentityHint } from '../src/reports.ts'

test('original-name formal results explain why they do not aggregate without assigning an identity', () => {
  const stored = { metric_name: '报告上的名称', standard_metric: null }
  const before = structuredClone(stored)
  assert.equal(resultIdentityHint(stored), '按本报告名称保存 · 不参与同类指标趋势')
  assert.deepEqual(stored, before)
})
test('canonical identity stays auxiliary and does not replace the formal report name', () => {
  const stored = { metric_name: '历史报告名称', standard_metric: { id: 'm', code: 'STABLE', name: '现有统一名称' } }
  const before = structuredClone(stored)
  assert.equal(resultIdentityHint(stored), '关联指标：现有统一名称')
  assert.deepEqual(stored, before)
})
test('readable abnormal descriptions use only stored flags and leave unknown states unclassified', () => {
  assert.equal(abnormalDescription('HIGH'), '↑ 偏高')
  assert.equal(abnormalDescription('LOW'), '↓ 偏低')
  assert.equal(abnormalDescription('OTHER'), '异常标记')
  for (const flag of [null, '', 'NORMAL']) assert.equal(abnormalDescription(flag), '')
})
