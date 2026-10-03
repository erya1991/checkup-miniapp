import assert from 'node:assert/strict'
import { test } from 'node:test'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import { computed, nextTick, reactive, ref, watch } from 'vue'
import * as confirmation from '../src/confirmation.ts'
import { userError } from '../src/ui.ts'

// Execute the real page script with synthetic API/native dependencies. These
// assertions cover save behavior; they do not substitute for device acceptance.
const page = readFileSync(new URL('../src/pages/confirmation/index.vue', import.meta.url), 'utf8')
const source = page.match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1]
  .replace(/^import[\s\S]*? from ['"][^'"]+['"]\s*\r?\n/gm, '')
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
const createPage = new Function('deps', `const { computed, nextTick, reactive, ref, watch, onLoad, onShow,
  ApiError, ensureLogin, request, confirmationErrorMessages, confirmationFormErrors, confirmationIdentityHint,
  confirmationItemLabel, groupedItems, itemForm, itemPayload, saveThenCommit, standardMetricLabel,
  openReports, userError, uni } = deps;
  ${compiled}
  return { workspace, report, form, error, reportErrors, itemErrors, editing, busy, success,
    load, edit, saveItem, resolve, submit, done };`)

class ApiError extends Error {
  constructor(code, details = {}) { super(code); this.code = code; this.details = details }
}
const profile = { id: 'profile-one', display_name: '测试档案', relation: 'SELF', gender: null, birth_date: null }
const item = { id: 'item-one', sequence_no: 1, metric_name: '测试指标', result_text: '3.5',
  unit_original: 'U/L', unit_normalized: 'U/L', reference_text: '1~4', standard_metric_id: 'metric-one',
  standard_metric: { id: 'metric-one', code: 'SYNTHETIC', name: '测试关联指标', status: 'ACTIVE' },
  source_type: 'OCR_AUTO', review_status: 'RESOLVED', resolution: 'ACCEPTED',
  source: { asset_id: 'asset-one', page_no: 1, final_decision: 'FINAL_AUTO', review_reasons: [] } }
function fixture(items = [item]) {
  return { id: 'ingestion-test', status: 'PENDING_CONFIRMATION', mode: 'OCR',
    health_profile_id: profile.id, health_profile: profile, hospital_name: null,
    examination_date: '2026-10-01', examination_time: null, report_no: null, report_category: null,
    assets: [{ id: 'asset-one', page_no: 1, mime_type: 'image/png', file_size: 100, upload_status: 'UPLOADED' }],
    items: structuredClone(items), pending_count: items.filter(i => i.review_status === 'PENDING').length }
}
function harness(initial = fixture(), custom) {
  const calls = [], modals = [], scrolls = []
  let server = structuredClone(initial), modalConfirm = false, destinations = 0
  const request = async (path, method = 'GET', data) => {
    calls.push({ path, method, data })
    if (custom) {
      const result = await custom({ path, method, data, calls, server })
      if (result !== undefined) return result
    }
    if (path === '/ingestions/ingestion-test') return { status: server.status }
    if (path === '/health-profiles') return [profile]
    if (path.endsWith('/confirmation') && method === 'GET') return structuredClone(server)
    if (path.endsWith('/confirmation') && method === 'PUT') {
      server = { ...server, ...data }; return structuredClone(server)
    }
    if (path.endsWith('/commit')) {
      server.status = 'CONFIRMED'
      return { report_id: 'saved-report', status: 'CONFIRMED', item_count: server.items.length }
    }
    if (path.includes('/confirmation/items/')) {
      const id = path.split('/').at(-1), current = server.items.find(i => i.id === id)
      Object.assign(current, data, { review_status: 'RESOLVED' })
      return structuredClone(server)
    }
    throw new Error('Unexpected synthetic request')
  }
  const state = createPage({ computed, nextTick, reactive, ref, watch,
    onLoad: callback => callback({ id: 'ingestion-test' }), onShow: () => {},
    ApiError, ensureLogin: async () => ({}), request, ...confirmation, userError,
    openReports: () => destinations++,
    uni: { showToast: () => {}, pageScrollTo: options => scrolls.push(options.selector),
      showModal: async options => { modals.push(options); return { confirm: modalConfirm } } } })
  return { state, calls, modals, scrolls, confirm: value => { modalConfirm = value },
    destinations: () => destinations }
}

test('real confirmation submit blocks unresolved AUTO-compatible review and absent report date', async () => {
  const h = harness(fixture([{ ...item, review_status: 'PENDING', resolution: null }]))
  await h.state.load()
  await h.state.submit()
  assert.equal(h.calls.some(c => c.path.endsWith('/commit')), false)
  assert.match(h.state.error.value, /需要核对/)
  assert.ok(h.scrolls.includes('#pending-items'))
  h.state.workspace.value.items[0].review_status = 'RESOLVED'
  h.state.report.examination_date = ''
  await h.state.submit()
  assert.equal(h.calls.some(c => c.method === 'PUT'), false)
  assert.equal(h.calls.some(c => c.path.endsWith('/commit')), false)
  assert.ok(h.state.reportErrors.examination_date)
  assert.ok(h.scrolls.includes('#report-information'))
})

test('real item edit preserves unsaved report input and keeps original identity explicit', async () => {
  const h = harness()
  await h.state.load()
  h.state.report.hospital_name = '合成未保存医院'
  await h.state.edit(h.state.workspace.value.items[0])
  h.state.form.result_text = '阴性'
  await h.state.saveItem(true)
  const edit = h.calls.find(c => c.path.includes('/confirmation/items/'))
  assert.deepEqual(edit.data, { result_text: '阴性', standard_metric_id: null, resolution: 'KEEP_ORIGINAL_NAME' })
  assert.equal(h.state.report.hospital_name, '合成未保存医院')
  assert.equal(h.state.editing.value, false)
  assert.deepEqual(h.state.workspace.value.items[0].source, item.source)
  assert.equal('abnormal' in edit.data, false)
  assert.equal('result_numeric' in edit.data, false)
})

test('real duplicate prompt requires explicit choice and sends the existing acknowledgement only after confirmation', async () => {
  const details = { candidates: [{ hospital_name: null, examination_date: '2026-10-01', report_no: null, item_count: 1 }],
    acknowledgement: 'synthetic-acknowledgement' }
  const h = harness(fixture(), async ({ path, data }) => {
    if (path.endsWith('/commit') && !data.duplicate_acknowledgement) throw new ApiError('DUPLICATE_CONFIRM_REQUIRED', details)
  })
  await h.state.load()
  await h.state.submit()
  assert.equal(h.state.success.value, null)
  assert.equal(h.calls.filter(c => c.path.endsWith('/commit')).length, 1)
  assert.equal(h.modals[0].cancelText, '返回修改')
  h.confirm(true)
  await h.state.submit()
  const commits = h.calls.filter(c => c.path.endsWith('/commit'))
  assert.deepEqual(commits.at(-1).data, { duplicate_acknowledgement: details.acknowledgement })
  assert.equal(h.state.success.value.report_id, 'saved-report')
  h.state.done()
  assert.equal(h.destinations(), 1)
})

test('real lost-response retry recovers the same report after confirmation becomes locked', async () => {
  let attempts = 0
  const saved = { report_id: 'same-synthetic-report', status: 'CONFIRMED', item_count: 1 }
  const h = harness(fixture(), async ({ path, method }) => {
    if (path.endsWith('/confirmation') && method === 'PUT' && attempts > 0) throw new ApiError('CONFIRMATION_LOCKED')
    if (path.endsWith('/commit')) {
      attempts++
      if (attempts === 1) throw new Error('private-network-stack-must-not-surface')
      return saved
    }
  })
  await h.state.load()
  await h.state.submit()
  assert.equal(h.state.success.value, null)
  assert.doesNotMatch(h.state.error.value, /private-network/)
  await h.state.submit()
  assert.deepEqual(h.state.success.value, saved)
  assert.equal(attempts, 2)
})

test('real save action guards double clicks while keeping text fields and source facts', async () => {
  let release
  const blocked = new Promise(resolve => { release = resolve })
  const h = harness(fixture(), async ({ path, method, server }) => {
    if (path.endsWith('/confirmation') && method === 'PUT') { await blocked; return structuredClone(server) }
  })
  await h.state.load()
  const first = h.state.submit()
  await h.state.submit()
  assert.equal(h.calls.filter(c => c.method === 'PUT').length, 1)
  assert.equal(h.state.busy.value, true)
  release()
  await first
  assert.equal(h.calls.filter(c => c.path.endsWith('/commit')).length, 1)
  assert.equal(h.state.busy.value, false)
})
