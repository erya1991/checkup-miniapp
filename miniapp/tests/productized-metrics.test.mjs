import assert from 'node:assert/strict'
import { test } from 'node:test'
import { chartDateLabel, examinationLabel } from '../src/profile-metrics.ts'

test('compact chart dates retain the year, while selected-point details retain the complete time', () => {
  const result = { examination_date: '2026-10-04', examination_time: '08:17:30' }
  const before = structuredClone(result)
  assert.deepEqual(chartDateLabel(result), { year: '2026', date: '10-04', time: '08:17' })
  assert.equal(examinationLabel(result), '2026-10-04 08:17:30')
  assert.deepEqual(result, before)
})
test('unknown time never gains a fabricated midnight in chart or point details', () => {
  const result = { examination_date: '2025-01-01', examination_time: null }
  assert.deepEqual(chartDateLabel(result), { year: '2025', date: '01-01', time: '' })
  assert.equal(examinationLabel(result), '2025-01-01（时间未记录）')
})
