import { describe, it, expect } from 'vitest'
import { shallowMount } from '@vue/test-utils'
import { defineComponent } from 'vue'
describe('Login.vue', () => {
  it('renders', () => {
    const comp = defineComponent({ template: '<div class="login">登录页面</div>' })
    const wrapper = shallowMount(comp)
    expect(wrapper.text()).toContain('登录')
  })
})
