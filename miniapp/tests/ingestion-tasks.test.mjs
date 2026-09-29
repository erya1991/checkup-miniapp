import assert from 'node:assert/strict'
import { test } from 'node:test'
import { ingestionTasksPath, taskDestination, taskStatusLabels } from '../src/ingestion-tasks.ts'

test('task records request only the selected health profile', () => {
  assert.equal(ingestionTasksPath('profile/a'), '/ingestions?health_profile_id=profile%2Fa')
})

test('upload states reopen the image confirmation page', () => {
  for (const status of ['UPLOADING', 'READY']) {
    assert.equal(taskDestination({ id: 'old-task', status }), '/pages/upload/index?id=old-task')
  }
})

test('OCR states, including an older completed task, reopen the Stage 03 status page', () => {
  for (const status of ['QUEUED', 'PROCESSING', 'OCR_FAILED', 'PENDING_CONFIRMATION']) {
    assert.equal(taskDestination({ id: 'old-task', status }), '/pages/ocr/index?id=old-task')
  }
  assert.equal(taskStatusLabels.PENDING_CONFIRMATION, '识别完成，待确认')
})

test('unknown states do not navigate to an unrelated page', () => {
  assert.equal(taskDestination({ id: 'old-task', status: 'UNKNOWN' }), null)
})
