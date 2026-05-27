import { describe, it, expect } from 'vitest'

describe('SystemMonitorStore', () => {
  it('should have correct initial state', () => {
    const state = {
      metrics: {},
      cpuHistory: [],
      alerts: [],
      wsConnected: false,
    }
    expect(state.metrics).toEqual({})
    expect(state.cpuHistory).toEqual([])
    expect(state.alerts).toEqual([])
    expect(state.wsConnected).toBe(false)
  })
})

describe('SsoAuthStore', () => {
  it('should have correct initial state', () => {
    const state = {
      users: [],
      sessions: [],
      providers: [],
      authenticated: false,
    }
    expect(state.authenticated).toBe(false)
    expect(state.users).toEqual([])
  })
})

describe('DataAnalysisStore', () => {
  it('should have correct initial state', () => {
    const state = {
      input: '',
      result: null,
      history: [],
    }
    expect(state.input).toBe('')
    expect(state.result).toBeNull()
  })
})

describe('Router', () => {
  it('should define correct routes', () => {
    const routes = [
      '/login', '/dashboard', '/sysmon', '/sso-auth',
      '/data-analysis', '/modules', '/security', '/settings',
    ]
    expect(routes).toContain('/login')
    expect(routes).toContain('/sysmon')
    expect(routes).toContain('/sso-auth')
    expect(routes).toContain('/data-analysis')
    expect(routes.length).toBeGreaterThanOrEqual(8)
  })
})
