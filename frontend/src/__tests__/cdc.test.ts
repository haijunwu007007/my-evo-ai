import { describe, it, expect } from 'vitest'
describe('CDC 同步', () => {
  it('系统 API 存在', async () => {
    const mod = await import('@/api')
    expect(typeof mod.getSystemStatus).toBe('function')
    expect(typeof mod.getSchedulerStatus).toBe('function')
  })
})
