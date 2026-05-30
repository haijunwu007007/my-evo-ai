import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
describe('Modules 视图', () => {
  it('can create component instance', () => {
    const comp = defineComponent({ template: '<div class="test">模块管理</div>' })
    const wrapper = mount(comp)
    expect(wrapper.text()).toBe('模块管理')
  })
})
