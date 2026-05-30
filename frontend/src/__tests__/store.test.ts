import { describe, it, expect } from 'vitest'
describe('Store', () => {
  it('systemMonitor store exports', async () => {
    const mod = await import('@/stores/systemMonitor')
    expect(mod.useSystemMonitorStore).toBeDefined()
  })
})