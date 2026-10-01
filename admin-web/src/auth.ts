import { ref } from 'vue'

export const token = ref(sessionStorage.getItem('checkup-admin-token') || '')
export function setToken(value: string) {
  token.value = value
  if (value) sessionStorage.setItem('checkup-admin-token', value)
  else sessionStorage.removeItem('checkup-admin-token')
}
