import { describe, it, expect } from 'vitest'
describe('通知监控', () => {
  it('系统 API 存在', async () => {
    const mod = await import('@/api')
    const names = Object.keys(mod).filter(k => typeof (mod as Record<string, unknown>)[k] === 'function')
    expect(names.length).toBeGreaterThan(10)
  })
})
