import assert from 'node:assert/strict'
import { test } from 'node:test'
import { abnormalLabel, reportDestination, reportsPath, unfinished } from '../src/reports.ts'

test('formal report pagination and detail use independent routes', () => {
  assert.equal(reportsPath('a/b', 2), '/reports?health_profile_id=a%2Fb&page=2&page_size=20')
  assert.equal(reportDestination('a/b'), '/pages/report-detail/index?id=a%2Fb')
})
test('missing abnormal never implies normal, stored flags only', () => {
  assert.equal(abnormalLabel(null), '')
  assert.equal(abnormalLabel(''), '')
  assert.equal(abnormalLabel('NORMAL'), '')
  assert.equal(abnormalLabel('HIGH'), '↑')
  assert.equal(abnormalLabel('LOW'), '↓')
  assert.equal(abnormalLabel('OTHER'), '异常标记')
})
test('committed and cancelled tasks cannot become home drafts', () => {
  assert.equal(unfinished('CONFIRMED'), false)
  assert.equal(unfinished('CANCELLED'), false)
  for (const status of ['UPLOADING', 'READY', 'QUEUED', 'PROCESSING', 'OCR_FAILED', 'PENDING_CONFIRMATION']) assert.equal(unfinished(status), true)
})

test('pagination replaces old profile data and appends next page', async () => {
  const { mergeReportPage } = await import('../src/reports.ts')
  assert.deepEqual(mergeReportPage([{ id: 'old' }], [{ id: 'new' }], false), [{ id: 'new' }])
  assert.deepEqual(mergeReportPage([{ id: 'a' }], [{ id: 'b' }], true), [{ id: 'a' }, { id: 'b' }])
})
test('duplicate migration cancellation sends no acknowledged write', async () => {
  const { migrateWithConfirmation } = await import('../src/reports.ts')
  const bodies = []
  const result = await migrateWithConfirmation(async body => {
    bodies.push(body)
    throw { code: 'DUPLICATE_CONFIRM_REQUIRED', details: { candidates: [], acknowledgement: 'bound' } }
  }, 'target', async () => false)
  assert.equal(result, null)
  assert.deepEqual(bodies, [{ health_profile_id: 'target', duplicate_acknowledgement: null }])
})
test('explicit duplicate continuation retries same target with fresh credential', async () => {
  const { migrateWithConfirmation } = await import('../src/reports.ts')
  const bodies = []
  const result = await migrateWithConfirmation(async body => {
    bodies.push(body)
    if (bodies.length === 1) throw { code: 'DUPLICATE_CONFIRM_REQUIRED', details: { candidates: [], acknowledgement: 'bound' } }
    return { id: 'report', health_profile_id: 'target' }
  }, 'target', async prompt => prompt.acknowledgement === 'bound')
  assert.equal(result.health_profile_id, 'target')
  assert.deepEqual(bodies[1], { health_profile_id: 'target', duplicate_acknowledgement: 'bound' })
})
test('failed migration propagates; deletion returns to formal list', async () => {
  const { migrateWithConfirmation, deletedReportDestination } = await import('../src/reports.ts')
  await assert.rejects(migrateWithConfirmation(async () => { throw Error('offline') }, 'target', async () => true), /offline/)
  assert.equal(deletedReportDestination, '/pages/reports/index')
})

test('formal details prefer normalized unit, fall back to original, and preserve stored values', async () => {
  const { displayUnit } = await import('../src/reports.ts')
  const cases = [
    [{ unit_normalized: 'μg/mL', unit_original: 'ug/ml' }, 'μg/mL'],
    [{ unit_normalized: 'U/L', unit_original: null }, 'U/L'],
    [{ unit_normalized: null, unit_original: '原始单位' }, '原始单位'],
    [{ unit_normalized: '', unit_original: '原始单位' }, '原始单位'],
    [{ unit_normalized: null, unit_original: null }, ''],
    [{ unit_normalized: '', unit_original: '' }, ''],
  ]
  for (const [values, expected] of cases) {
    const stored = { ...values }
    assert.equal(displayUnit(values), expected)
    assert.deepEqual(values, stored)
  }
})
