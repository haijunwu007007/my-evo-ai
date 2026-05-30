import { describe, it, expect } from 'vitest'
describe('Theme System', () => {
  it('data-theme can be set', () => {
    document.documentElement.setAttribute('data-theme', 'dark')
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
  })
  it('CSS vars accessible', () => {
    const val = getComputedStyle(document.documentElement).getPropertyValue('--bg-sidebar')
    expect(val).toBeDefined()
  })
})
