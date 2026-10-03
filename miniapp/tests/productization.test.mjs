import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import { tabPaths, navigate, newUploadPath, openReports } from '../src/navigation.ts'
import { pendingSummary, recentReports, favoriteSummary } from '../src/productization.ts'
import { fontScale, userError } from '../src/ui.ts'

test('three native tabs and navigation reset to stable report module', () => {
  const pages = JSON.parse(readFileSync(new URL('../src/pages.json', import.meta.url), 'utf8').replace(/^\uFEFF/, ''))
  assert.deepEqual(pages.tabBar.list.map(item => item.text), ['首页', '报告', '我的'])
  const calls = []
  globalThis.uni = { setStorageSync: (key, value) => calls.push([key, value]), switchTab: options => calls.push(['switchTab', options.url]), navigateTo: options => calls.push(['navigateTo', options.url]) }
  navigate(tabPaths.home); openReports('metrics'); navigate('/pages/profile-metrics/index'); navigate('/pages/report-detail/index?id=a')
  assert.deepEqual(calls, [['switchTab', tabPaths.home], ['uiReportView', 'metrics'], ['switchTab', tabPaths.reports], ['uiReportView', 'metrics'], ['switchTab', tabPaths.reports], ['navigateTo', '/pages/report-detail/index?id=a']])
})
test('new upload is explicit and cannot take a confirmed or unfinished identity', () => {
  assert.equal(newUploadPath(), '/pages/upload/index?new=1')
  const home = readFileSync(new URL('../src/pages/index/index.vue', import.meta.url), 'utf8')
  assert.match(home, /navigate\(newUploadPath\(\)\)/)
  assert.doesNotMatch(home, /ingestions\.find/)
})
test('multiple unfinished reports prioritize confirmation then failure while retaining count', () => {
  const tasks = ['PROCESSING', 'UPLOADING', 'CONFIRMED', 'READY', 'OCR_FAILED', 'PENDING_CONFIRMATION', 'QUEUED'].map((status, id) => ({ id: String(id), status }))
  assert.equal(pendingSummary(tasks).count, 6)
  assert.equal(pendingSummary(tasks).first.status, 'PENDING_CONFIRMATION')
  assert.equal(pendingSummary(tasks.filter(item => item.status !== 'PENDING_CONFIRMATION')).first.status, 'OCR_FAILED')
  assert.deepEqual(pendingSummary([{ status: 'CONFIRMED' }]), { count: 0, first: null })
  assert.equal(tasks[0].status, 'PROCESSING')
})
test('home summaries preserve formal server order and persisted values without recalculation', () => {
  const reports = [{ id: 'r1', abnormal_count: 2 }, { id: 'r2', abnormal_count: 0 }, { id: 'r3', abnormal_count: 3 }]
  assert.deepEqual(recentReports(reports), reports.slice(0, 2))
  const metrics = [false, true, true, true, true].map((is_favorite, i) => ({ is_favorite, latest: { result_text: `text${i}`, abnormal: null } }))
  assert.deepEqual(favoriteSummary(metrics), metrics.slice(1, 4))
  const home = readFileSync(new URL('../src/pages/index/index.vue', import.meta.url), 'utf8')
  assert.match(home, /reportsPath\(profileId\)/); assert.match(home, /metricsPath\(profileId\)/)
  assert.match(home, /report\.abnormal_count/); assert.match(home, /metric\.latest\.result_text/)
  assert.match(home, /if \(!guard\.current\(run\)\) return/)
})
test('font settings and safe error feedback cover large text and private transport errors', () => {
  assert.equal(fontScale({}), 1); assert.equal(fontScale({ fontSizeSetting: 24 }), 1.5)
  assert.equal(fontScale({ fontSizeScaleFactor: 1.4, fontSizeSetting: 24 }), 1.4)
  assert.equal(fontScale({ hostFontSizeSetting: '20' }), 1.25)
  assert.equal(fontScale({ fontSizeSetting: 100 }), 2)
  assert.doesNotMatch(userError(new Error('SECRET COS/key token')), /SECRET|COS|token/)
  assert.match(userError({ status: 401 }), /登录/)
})
test('upload without explicit identity starts fresh and only specified unfinished report is continued', () => {
  const upload = readFileSync(new URL('../src/pages/upload/index.vue', import.meta.url), 'utf8')
  assert.match(upload, /id\.value = params\?\.id \|\| ''/)
  assert.doesNotMatch(upload, /all\.find|forceNew/)
  assert.match(upload, /if \(id\.value\)/)
  assert.match(upload, /value\.health_profile_id !== me\.default_health_profile_id/)
})
test('pending and OCR summary never masquerade as live confirmation progress', () => {
  for (const page of ['ingestion-tasks', 'ocr']) {
    const source = readFileSync(new URL(`../src/pages/${page}/index.vue`, import.meta.url), 'utf8')
    assert.doesNotMatch(source, /result_summary\.(?:auto_count|review_count)|result_summary\?\.(?:auto_count|review_count)/)
    assert.match(source, /result_summary(?:\?\.)?\.?(?:total_count|total_count)/)
  }
})
test('late upload and manual completions do not navigate after their page is hidden', () => {
  const upload = readFileSync(new URL('../src/pages/upload/index.vue', import.meta.url), 'utf8')
  const ocr = readFileSync(new URL('../src/pages/ocr/index.vue', import.meta.url), 'utf8')
  assert.match(upload, /onHide\(\(\) => \{ visible = false/)
  assert.match(upload, /await request\(`\/ingestions\/\$\{id\.value\}\/manual`, 'POST'\)\s+if \(!visible\) return/)
  assert.match(ocr, /if \(visible\) confirmation\(\)/)
  const reports = readFileSync(new URL('../src/pages/reports/index.vue', import.meta.url), 'utf8')
  assert.match(reports, /if \(append && profile\.value\?\.id !== me\.default_health_profile_id\) \{ await load\(false\); return \}/)
})
