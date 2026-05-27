/**
 * AUTO-EVO-AI V0.1 — SSO Auth 用户管理 Store
 */
import { defineStore } from 'pinia'
import { sso } from '../api/modules'

export const useSsoAuthStore = defineStore('ssoAuth', {
  state: () => ({
    sessions: [],
    jwtToken: null,
    currentUser: null,
    loading: false,
    error: null,
  }),

  actions: {
    async login(userId, username) {
      this.loading = true; this.error = null
      try {
        const r = await sso.login(userId, username)
        if (r?.success) {
          this.currentUser = { userId: r.user_id, token: r.session_token }
          return r
        }
        this.error = r?.error || '登录失败'
        return r
      } catch (e) { this.error = e.message }
      finally { this.loading = false }
    },

    async logout(token) {
      const r = await sso.logout(token)
      if (r?.success) { this.currentUser = null; this.jwtToken = null }
      return r
    },

    async registerUser(username, password, roles) {
      this.loading = true; this.error = null
      try {
        const r = await sso.registerUser(username, password, roles)
        if (!r?.success) this.error = r?.error || '注册失败'
        return r
      } catch (e) { this.error = e.message }
      finally { this.loading = false }
    },

    async authenticate(username, password) {
      this.loading = true; this.error = null
      try {
        const r = await sso.authenticate(username, password)
        if (r?.success) this.currentUser = { userId: r.user_id, username: r.username, roles: r.roles }
        else this.error = r?.error || '认证失败'
        return r
      } catch (e) { this.error = e.message }
      finally { this.loading = false }
    },

    async generateJwt(userId, role) {
      const r = await sso.generateJwt(userId, role)
      if (r?.success) this.jwtToken = r.jwt
      return r
    },

    async verifyJwt(token) {
      return await sso.verifyJwt(token)
    },

    async listSessions() {
      try {
        const r = await sso.listSessions()
        if (r?.success) this.sessions = r.sessions || []
        return r
      } catch (e) { /* ignore */ }
    },
  },
})
