import { describe, it, expect } from 'vitest'
describe('AI 聊天', () => {
  it('系统 API 模块可导入', async () => {
    const mod = await import('@/api')
    expect(mod).toBeDefined()
    expect(Object.keys(mod).length).toBeGreaterThan(20)
  })
})
