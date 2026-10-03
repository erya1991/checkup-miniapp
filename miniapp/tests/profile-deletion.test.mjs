import assert from 'node:assert/strict'
import { test } from 'node:test'
import { busyMessage, deletionMessage, deleteWithConfirmation, profileContext } from '../src/profile-deletion.ts'

const impact = { profile: { id: 'p', display_name: '测试档案' }, report_count: 3,
  unfinished_ingestion_count: 2, total_ingestion_count: 5, favorite_count: 4, processing_ocr_count: 0 }
function setup(overrides = {}) {
  const events = []
  const actions = {
    impact: async () => { events.push('impact'); return impact },
    confirm: async message => { events.push(message); return true },
    remove: async () => { events.push('delete') },
    reload: async () => { events.push('reload'); return profileContext([{ id: 'replacement' }], 'replacement') },
    apply: context => events.push(context), notify: message => events.push(message), ...overrides,
  }
  return { actions, events }
}
test('impact confirmation identifies permanent scope and server counts', () => {
  const text = deletionMessage(impact)
  for (const word of ['测试档案', '永久删除', '无法恢复', '检验报告', '指标历史', '关注指标', '原始图片', '识别数据', '3 份', '2 个', '4 个']) assert.ok(text.includes(word))
})
test('cancel sends no destructive request', async () => {
  const { actions, events } = setup({ confirm: async () => false })
  assert.equal(await deleteWithConfirmation('p', actions), 'cancelled')
  assert.deepEqual(events, ['impact'])
})
test('processing preflight prevents confirmation and DELETE', async () => {
  const { actions, events } = setup({ impact: async () => ({ ...impact, processing_ocr_count: 1 }) })
  assert.equal(await deleteWithConfirmation('p', actions), 'busy')
  assert.deepEqual(events, [busyMessage])
})
test('concurrent claim refreshes impact, never retries delete or claims success', async () => {
  let calls = 0
  const { actions, events } = setup({ remove: async () => { calls++; throw { code: 'PROFILE_DELETE_BUSY' } } })
  assert.equal(await deleteWithConfirmation('p', actions), 'busy')
  assert.equal(calls, 1)
  assert.equal(events.filter(e => e === 'impact').length, 2)
  assert.ok(events.includes(busyMessage)); assert.ok(!events.includes('reload'))
})
test('successful deletion refreshes list/default and applies replacement', async () => {
  const { actions, events } = setup()
  assert.equal(await deleteWithConfirmation('p', actions), 'deleted')
  assert.equal(events[0], 'impact'); assert.equal(events[2], 'delete'); assert.equal(events[3], 'reload')
  assert.deepEqual(events[4], { profiles: [{ id: 'replacement' }], selected: 'replacement' })
})
test('last profile produces empty context with no stale selection', async () => {
  const { actions, events } = setup({ reload: async () => profileContext([], 'p') })
  assert.equal(await deleteWithConfirmation('p', actions), 'deleted')
  assert.deepEqual(events.at(-1), { profiles: [], selected: '' })
})
for (const failure of [new Error('lost 204'), { code: 'PROFILE_NOT_FOUND' }]) {
  test(`lost response / repeated request recovers via authoritative list: ${failure.code || failure.message}`, async () => {
    const { actions } = setup({ remove: async () => { throw failure } })
    assert.equal(await deleteWithConfirmation('p', actions), 'deleted')
  })
}
test('failed delete with existing profile is never reported successful', async () => {
  const failure = new Error('network')
  const { actions } = setup({ remove: async () => { throw failure }, reload: async () => profileContext([{ id: 'p' }], 'p') })
  await assert.rejects(deleteWithConfirmation('p', actions), failure)
})
test('failed refresh cannot confirm deletion', async () => {
  const { actions } = setup({ reload: async () => { throw new Error('offline') } })
  await assert.rejects(deleteWithConfirmation('p', actions), /offline/)
})
