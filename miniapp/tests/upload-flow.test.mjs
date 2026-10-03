import assert from 'node:assert/strict'
import { test } from 'node:test'
import { registerAndRefresh } from '../src/upload-flow.ts'
test('successful image registration followed by failed refresh does not become an upload retry', async () => {
  const calls = []
  assert.deepEqual(await registerAndRefresh(async () => { calls.push('register') }, async () => { calls.push('refresh'); throw Error('offline') }), { refreshRequired: true })
  assert.deepEqual(calls, ['register', 'refresh'])
})
test('failed image registration propagates for retry and cannot refresh an unregistered image', async () => {
  let refreshed = false
  await assert.rejects(registerAndRefresh(async () => { throw Error('register-failed') }, async () => { refreshed = true }), /register-failed/)
  assert.equal(refreshed, false)
})
test('successful registration and refresh finish without additional writes', async () => {
  let writes = 0
  assert.deepEqual(await registerAndRefresh(async () => { writes++ }, async () => {}), { refreshRequired: false })
  assert.equal(writes, 1)
})
