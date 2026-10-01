import assert from 'node:assert/strict'
import { test } from 'node:test'
import { readFileSync } from 'node:fs'
import { metricsPath, metricPath, favoritePath, metricDestination, mergePage,
  defaultSeries, selectedSeries, examinationLabel, requestGuard, changeFavorite,
  chartGeometry, emptyTrendMessage, appFontSize } from '../src/profile-metrics.ts'
import { reportDestination } from '../src/reports.ts'

const point = (id, value = 1, date = '2026-10-01') => ({
  lab_result_id: id, report_id: 'report-' + id, value, result_text: '正式文本-' + id,
  examination_date: date, examination_time: null, unit: 'U', reference_text: '本次范围', abnormal: null,
})
test('metric routes always carry encoded profile context and server pagination', () => {
  assert.equal(metricsPath('a/b', 2), '/profile-metrics?health_profile_id=a%2Fb&page=2&page_size=20')
  assert.equal(metricPath('a/b', 'm/n'), '/profile-metrics/m%2Fn?health_profile_id=a%2Fb')
  assert.equal(metricPath('p', 'm', 'history', 3), '/profile-metrics/m/history?health_profile_id=p&page=3&page_size=50')
  assert.equal(metricPath('p', 'm', 'trend'), '/profile-metrics/m/trend?health_profile_id=p')
  assert.equal(favoritePath('a/b', 'm/n'), '/favorites/m%2Fn?health_profile_id=a%2Fb')
  assert.equal(metricDestination('a/b'), '/pages/metric-detail/index?id=a%2Fb')
  assert.equal(reportDestination('r/s'), '/pages/report-detail/index?id=r%2Fs')
})
test('metric/history pagination preserves separate same-day result identities', () => {
  const a = point('a'), b = point('b')
  assert.deepEqual(mergePage([a], [b], true), [a, b])
  assert.deepEqual(mergePage([a], [b], false), [b])
  assert.deepEqual(mergePage([a], [], true), [a])
})
test('use server series recency order and empty trend is normal', () => {
  const series = [{ series_key: 'V', unit: 'V', points: [point('a')] },
    { series_key: 'U', unit: 'U', points: [point('b')] }]
  assert.equal(defaultSeries(series), 'V')
  assert.equal(selectedSeries(series, 'U'), series[1])
  assert.equal(defaultSeries([]), '')
  assert.equal(selectedSeries([], ''), null)
  assert.match(emptyTrendMessage, /历史结果仍可查看/)
})
test('favorite state changes only after successful server response; failures preserve prior state', async () => {
  const calls = []
  assert.equal(await changeFavorite(async method => { calls.push(method); return { is_favorite: true } }, false), true)
  assert.equal(await changeFavorite(async method => { calls.push(method); return { is_favorite: false } }, true), false)
  assert.deepEqual(calls, ['PUT', 'DELETE'])
  await assert.rejects(changeFavorite(async () => { throw Error('offline') }, false), /offline/)
})
test('slow old profile responses and hidden page writes are rejected', async () => {
  const guard = requestGuard(), writes = []
  let resolveOld
  const oldRun = guard.next()
  const oldResponse = new Promise(resolve => { resolveOld = resolve })
    .then(value => { if (guard.current(oldRun)) writes.push(value) })
  const newRun = guard.next()
  if (guard.current(newRun)) writes.push('mother')
  resolveOld('father')
  await oldResponse
  assert.deepEqual(writes, ['mother'])
  guard.invalidate()
  assert.equal(guard.current(newRun), false)
  assert.equal(guard.current(guard.next()), true)
})
test('chart keeps same-date and same-value points; long series and single points have finite geometry', () => {
  const points = [point('a', 5), point('b', 5), point('c', -2)]
  const geometry = chartGeometry(points)
  assert.equal(geometry.dots.length, 3)
  assert.equal(geometry.lines.length, 2)
  assert.deepEqual(geometry.dots.map(d => d.point.lab_result_id), ['a', 'b', 'c'])
  assert.ok(geometry.dots[0].x < geometry.dots[1].x)
  assert.equal(geometry.dots[0].point.result_text, '正式文本-a')
  for (const input of [[], [point('single', 0)], [point('a', 1), point('b', 1)]]) {
    const result = chartGeometry(input)
    assert.ok(result.dots.every(dot => Number.isFinite(dot.x) && Number.isFinite(dot.y)))
  }
  assert.ok(chartGeometry(Array.from({ length: 20 }, (_, i) => point(String(i), i))).width > 320)
})
test('unknown examination time remains unknown; frontend consumes server text and units', () => {
  assert.equal(examinationLabel(point('a')), '2026-10-01（时间未记录）')
  assert.equal(examinationLabel({ examination_date: '2026-10-01', examination_time: '08:00:00' }), '2026-10-01 08:00:00')
  const page = readFileSync(new URL('../src/pages/metric-detail/index.vue', import.meta.url), 'utf8')
  assert.match(page, /row\.result_text/)
  assert.match(page, /selectedPoint\.result_text/)
  assert.match(page, /report\(selectedPoint\.report_id\)/)
  assert.match(page, /onHide\(\(\) => guard\.invalidate\(\)\)/)
  assert.match(page, /if \(!guard\.current\(run\)\) return/)
})

test('font sizing accepts WeChat and uni-app host settings with readable fallback', () => {
  assert.equal(appFontSize({ fontSizeSetting: 24, hostFontSizeSetting: 18 }), 24)
  assert.equal(appFontSize({ hostFontSizeSetting: 20 }), 20)
  assert.equal(appFontSize({}), 16)
})
