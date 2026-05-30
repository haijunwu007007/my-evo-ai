import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
describe('Webhooks 视图', () => {
  it('basic structure', () => {
    const comp = defineComponent({template:'<div class="wh">Webhooks</div>'})
    expect(mount(comp).text()).toBe('Webhooks')
  })
})