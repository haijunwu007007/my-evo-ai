import { describe, it, expect } from 'vitest'
describe('API 导出', () => {
  it('所有 API 函数超过10个', async () => {
    const mod = await import('@/api')
    const names = Object.keys(mod).filter(k => typeof mod[k] === 'function')
    expect(names.length).toBeGreaterThan(10)
  })
  it('核心 API 函数存在', async () => {
    const mod = await import('@/api')
    expect(typeof mod.getSystemStatus).toBe('function')
    expect(typeof mod.getSchedulerStatus).toBe('function')
    expect(typeof mod.getModulesCategories).toBe('function')
  })
})
