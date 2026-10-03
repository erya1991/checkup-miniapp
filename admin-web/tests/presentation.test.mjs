import test from 'node:test'
import assert from 'node:assert/strict'
import { activeAdminMenu, adminStatus } from '../src/presentation.ts'

test('standard metric details keep their parent navigation selected', () => {
  assert.equal(activeAdminMenu('/standard-metrics/metric-123'), '/standard-metrics')
  for (const path of ['/', '/standard-metrics', '/metric-aliases', '/ocr-metric-issues', '/ocr-tasks', '/login']) {
    assert.equal(activeAdminMenu(path), path)
  }
})

test('master data and task states retain their identities and distinct visual meanings', () => {
  const types = { ACTIVE: 'success', INACTIVE: 'info', QUEUED: 'info', PROCESSING: 'warning', SUCCEEDED: 'success', FAILED: 'danger' }
  for (const [status, type] of Object.entries(types)) {
    assert.equal(adminStatus(status).type, type)
    assert.ok(adminStatus(status).label.includes(status))
  }
  assert.notEqual(adminStatus('INACTIVE').label, adminStatus('ACTIVE').label)
})

test('unknown or empty task status is preserved conservatively', () => {
  assert.deepEqual(adminStatus('UNEXPECTED'), { label: 'UNEXPECTED', type: 'info' })
  assert.deepEqual(adminStatus(''), { label: '—', type: 'info' })
})
