import { describe, it, expect } from 'vitest'
describe('工具函数', () => {
  it('Date formatting',()=>{
    expect(new Date('2026-01-15').toLocaleString('zh-CN').length).toBeGreaterThan(5)
  })
  it('JSON roundtrip',()=>{
    expect(JSON.parse(JSON.stringify({a:1,b:'x'}))).toEqual({a:1,b:'x'})
  })
})