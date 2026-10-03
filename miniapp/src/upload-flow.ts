// Once registration succeeds, a failed read refresh must not upload the same
// image again. Only a failed write belongs in the image retry list.
export async function registerAndRefresh(register: () => Promise<unknown>, refresh: () => Promise<void>) {
  await register()
  try { await refresh(); return { refreshRequired: false } }
  catch { return { refreshRequired: true } }
}
