import assert from 'node:assert/strict'
import { test } from 'node:test'
import { groupedItems, itemForm, itemPayload, saveThenCommit } from '../src/confirmation.ts'

const auto = { id: 'auto', metric_name: '原始名', result_text: '3.5', unit_original: 'U/L',
  reference_text: '1~4', standard_metric_id: 'ALT', source_type: 'OCR_AUTO',
  review_status: 'RESOLVED', resolution: 'ACCEPTED' }

test('REVIEW pending, AUTO adopted, and removed remain separate', () => {
  const review = { ...auto, id: 'review', review_status: 'PENDING', resolution: null }
  const removed = { ...auto, id: 'removed', resolution: 'REMOVED' }
  const groups = groupedItems([auto, review, removed])
  assert.deepEqual(groups.pending.map(i => i.id), ['review'])
  assert.deepEqual(groups.adopted.map(i => i.id), ['auto'])
  assert.deepEqual(groups.removed.map(i => i.id), ['removed'])
})

test('an unmodified AUTO is accepted without requiring value writes', () => {
  assert.deepEqual(itemPayload(itemForm(auto), auto), { resolution: 'ACCEPTED' })
})

test('AUTO text edits send final text and correction, without stale numeric or abnormal', () => {
  const payload = itemPayload({ ...itemForm(auto), result_text: '阴性' }, auto)
  assert.deepEqual(payload, { result_text: '阴性', resolution: 'CORRECTED' })
  assert.equal('result_numeric' in payload, false)
  assert.equal('abnormal' in payload, false)
})

test('identity-only selection uses standard selection, combined edits use correction', () => {
  const form = { ...itemForm(auto), standard_metric_id: 'AST' }
  assert.equal(itemPayload(form, auto).resolution, 'STANDARD_METRIC_SELECTED')
  assert.equal(itemPayload({ ...form, result_text: '2' }, auto).resolution, 'CORRECTED')
})

test('keep original explicitly clears standard identity and can retain edits', () => {
  assert.deepEqual(itemPayload({ ...itemForm(auto), result_text: '阳性' }, auto, true),
    { result_text: '阳性', standard_metric_id: null, resolution: 'KEEP_ORIGINAL_NAME' })
})

test('manual adds text results with nullable units/ranges/identity', () => {
  assert.deepEqual(itemPayload({ ...itemForm(null), metric_name: ' 新项 ', result_text: ' 未见异常 ' }, null),
    { metric_name: '新项', result_text: '未见异常', unit_original: null, reference_text: null, standard_metric_id: null })
})

test('a lost successful commit response recovers even when report fields are now frozen', async () => {
  let attempts = 0
  const saved = { report_id: 'same-report', item_count: 2 }
  const result = await saveThenCommit(async () => { throw { code: 'CONFIRMATION_LOCKED' } }, async () => {
    attempts++; return saved
  })
  assert.deepEqual(result, saved)
  assert.equal(attempts, 1)
})

test('failed report validation must not attempt commit', async () => {
  let committed = false
  await assert.rejects(saveThenCommit(async () => { throw new Error('INVALID_REPORT_DATE') }, async () => {
    committed = true
  }), /INVALID_REPORT_DATE/)
  assert.equal(committed, false)
})
