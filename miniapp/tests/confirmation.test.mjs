import assert from 'node:assert/strict'
import { test } from 'node:test'
import { readFileSync } from 'node:fs'
import { confirmationFormErrors, confirmationIdentityHint, confirmationItemLabel,
  groupedItems, itemForm, itemPayload, saveThenCommit, standardMetricLabel } from '../src/confirmation.ts'

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

test('prelinked REVIEW shows canonical name without search or resolving the item and retains its code', () => {
  const review = { ...auto, id: 'review', review_status: 'PENDING', resolution: null,
    standard_metric: { id: 'ALT', code: 'ALT', name: '丙氨酸氨基转移酶', status: 'ACTIVE' } }
  const before = structuredClone(review)
  assert.equal(standardMetricLabel(review.standard_metric_id, review.standard_metric), '丙氨酸氨基转移酶')
  assert.equal(review.standard_metric.code, 'ALT')
  assert.deepEqual(groupedItems([review]).pending, [review])
  assert.deepEqual(review, before)
  assert.deepEqual(itemPayload(itemForm(review), review), { resolution: 'ACCEPTED' })
})

test('manual selection uses its canonical search label and clearing identity hides the old label', () => {
  const old = { id: 'ALT', code: 'ALT', name: '丙氨酸氨基转移酶', status: 'ACTIVE' }
  assert.equal(standardMetricLabel('AST', old, { AST: '天门冬氨酸氨基转移酶' }), '天门冬氨酸氨基转移酶')
  assert.equal(standardMetricLabel(null, old), '未关联')
  assert.equal(standardMetricLabel('ALT'), '已关联，可重新选择')
})

test('confirmation list and editor consume canonical metadata from the workspace', () => {
  const page = readFileSync(new URL('../src/pages/confirmation/index.vue', import.meta.url), 'utf8')
  assert.equal((page.match(/关联指标：\{\{ standardMetricLabel\(item\.standard_metric_id, item\.standard_metric\)/g) || []).length, 2)
  assert.match(page, /standardMetricLabel\(form\.standard_metric_id, selected\?\.standard_metric, metricNames\)/)
  assert.match(page, /metric\.name/)
  assert.match(page, /metric\.code/)
})

test('product labels prioritize unresolved state even for an OCR_AUTO source without altering facts', () => {
  const pendingAuto = { ...auto, review_status: 'PENDING', resolution: null }
  const before = structuredClone(pendingAuto)
  assert.equal(confirmationItemLabel(pendingAuto), '需要核对')
  assert.equal(confirmationItemLabel(auto), '已自动采用')
  assert.equal(confirmationItemLabel({ ...auto, source_type: 'OCR_CORRECTED' }), '已核对')
  assert.equal(confirmationItemLabel({ ...auto, source_type: 'MANUAL' }), '手工添加')
  assert.equal(confirmationItemLabel({ ...pendingAuto, resolution: 'REMOVED' }), '已移除')
  assert.deepEqual(groupedItems([pendingAuto]).pending, [pendingAuto])
  assert.deepEqual(pendingAuto, before)
})

test('keep-original and resolved NULL identities explain trend exclusion without linking the item', () => {
  const kept = { ...auto, metric_name: '报告原名称', standard_metric_id: null, resolution: 'KEEP_ORIGINAL_NAME' }
  const before = structuredClone(kept)
  assert.equal(confirmationIdentityHint(kept), '按报告原名称保存 · 不参与“我的指标”趋势')
  assert.equal(confirmationIdentityHint({ ...kept, resolution: 'MANUAL_ADDED' }), confirmationIdentityHint(kept))
  assert.match(confirmationIdentityHint({ ...kept, review_status: 'PENDING', resolution: null }), /请选择关联指标/)
  assert.equal(confirmationIdentityHint({ ...kept, resolution: 'REMOVED' }), '')
  assert.equal(confirmationIdentityHint(auto), '')
  assert.deepEqual(kept, before)
})

test('field feedback requires names and results while permitting text results and optional units', () => {
  const empty = confirmationFormErrors({ ...itemForm(null), metric_name: '  ', result_text: '\t' })
  assert.ok(empty.metric_name)
  assert.ok(empty.result_text)
  const textForm = { ...itemForm(null), metric_name: ' 尿蛋白 ', result_text: ' 阴性 ' }
  const before = structuredClone(textForm)
  assert.deepEqual(confirmationFormErrors(textForm), { metric_name: '', result_text: '' })
  assert.deepEqual(textForm, before)
})

test('confirmation UI keeps review priority, recovery controls and a stable report destination', () => {
  const page = readFileSync(new URL('../src/pages/confirmation/index.vue', import.meta.url), 'utf8')
  const template = page.slice(page.indexOf('<template>'), page.indexOf('<style'))
  assert.ok(template.indexOf('需要核对 ·') < template.indexOf('已采用 ·'))
  assert.match(template, /adoptedExpanded/)
  assert.match(template, /removedExpanded/)
  assert.match(template, /重新核对/)
  assert.match(template, /确认并保存报告/)
  assert.match(template, /不参与“我的指标”趋势/)
  assert.doesNotMatch(template, />[^<]*(?:AUTO|REVIEW|KEEP_ORIGINAL_NAME|StandardMetric)/)
  assert.match(page, /function done\(\) \{ openReports\(\) \}/)
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
