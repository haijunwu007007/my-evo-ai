import { describe, it, expect } from 'vitest'
describe('Router', () => {
  it('routes are defined', async () => {
    const mod = await import('@/router')
    const defaultExport = mod.default
    expect(defaultExport).toBeDefined()
  })
})
