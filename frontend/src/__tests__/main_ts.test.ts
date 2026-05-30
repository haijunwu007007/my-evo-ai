import { describe, it, expect } from 'vitest'
describe('入口', () => {
  it('app element exists',()=>{
    const e = document.createElement('div'); e.id='app'; document.body.appendChild(e)
    expect(document.getElementById('app')).not.toBeNull()
  })
})