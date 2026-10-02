import assert from 'node:assert/strict'
import { test } from 'node:test'
import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { formatAdminTime, formatAdminTimeCell } from '../src/time.ts'

test('UTC ISO times display Shanghai date and seconds, including fractional seconds', () => {
  for (const value of ['2026-10-02T23:05:09Z', '2026-10-02T23:05:09.123456+00:00']) {
    assert.equal(formatAdminTime(value), '2026-10-03 07:05:09')
  }
})

test('Shanghai midnight and year rollover use 00 hours and the correct date', () => {
  assert.equal(formatAdminTime('2026-10-02T16:00:00Z'), '2026-10-03 00:00:00')
  assert.equal(formatAdminTime('2026-12-31T18:02:03Z'), '2027-01-01 02:02:03')
})

test('an explicit +08:00 input is not shifted twice', () => {
  assert.equal(formatAdminTime('2026-10-03T07:05:09+08:00'), '2026-10-03 07:05:09')
})

test('null, missing, empty and invalid times display an em dash', () => {
  for (const value of [null, undefined, '', 'invalid-date']) assert.equal(formatAdminTime(value), '—')
})

test('display timezone stays Shanghai when the host timezone differs', () => {
  const moduleUrl = new URL('../src/time.ts', import.meta.url).href
  const script = `import { formatAdminTime } from ${JSON.stringify(moduleUrl)}; process.stdout.write(formatAdminTime('2026-10-02T23:05:09Z'))`
  for (const TZ of ['UTC', 'America/New_York']) {
    assert.equal(execFileSync(process.execPath, ['--input-type=module', '-e', script], {
      env: { ...process.env, TZ }, encoding: 'utf8',
    }), '2026-10-03 07:05:09')
  }
})

test('table formatter reads the cell value and preserves null display', () => {
  assert.equal(formatAdminTimeCell({}, {}, '2026-10-02T23:05:09Z'), '2026-10-03 07:05:09')
  assert.equal(formatAdminTimeCell({}, {}, null), '—')
})

test('all five displayed timestamp fields use the shared formatter', () => {
  const fields = new Set()
  for (const name of ['MetricsPage', 'IssuesPage', 'TasksPage']) {
    const page = readFileSync(new URL(`../src/views/${name}.vue`, import.meta.url), 'utf8')
    for (const column of page.matchAll(/<el-table-column\b[^>]*\bprop="([^"]+_at)"[^>]*>/g)) {
      fields.add(column[1])
      assert.match(column[0], /:formatter="formatAdminTimeCell"/)
    }
  }
  assert.deepEqual([...fields].sort(), ['created_at', 'finished_at', 'latest_seen_at', 'started_at', 'updated_at'])
})
