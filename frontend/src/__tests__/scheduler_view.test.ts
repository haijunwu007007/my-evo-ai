import { describe, it, expect } from 'vitest'
describe('Scheduler 视图', () => {
  it('scheduler API exports', async () => {
    const mod = await import('@/api')
    expect(mod.getSchedulerStatus).toBeTypeOf('function')
    expect(mod.getSchedulerTasks).toBeTypeOf('function')
  })
})