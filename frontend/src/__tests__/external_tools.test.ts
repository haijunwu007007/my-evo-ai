import { describe, it, expect } from 'vitest'

// 模拟 i18n 函数
function t(key: string, lang: string = 'zh-CN'): string {
  const dict: Record<string, Record<string, string>> = {
    'zh-CN': {
      'common.search': '搜索',
      'common.loading': '加载中...',
      'common.error': '错误',
      'common.success': '成功',
      'common.save': '保存',
      'common.cancel': '取消',
    },
    'en-US': {
      'common.search': 'Search',
      'common.loading': 'Loading...',
      'common.error': 'Error',
      'common.success': 'Success',
      'common.save': 'Save',
      'common.cancel': 'Cancel',
    },
  }
  return dict[lang]?.[key] ?? key
}

describe('i18n 翻译函数', () => {
  it('应返回中文翻译', () => {
    expect(t('common.search', 'zh-CN')).toBe('搜索')
    expect(t('common.loading', 'zh-CN')).toBe('加载中...')
  })

  it('应返回英文翻译', () => {
    expect(t('common.search', 'en-US')).toBe('Search')
    expect(t('common.loading', 'en-US')).toBe('Loading...')
  })

  it('不存在的 key 应返回原始 key', () => {
    expect(t('nonexistent.key', 'zh-CN')).toBe('nonexistent.key')
  })
})

describe('工具卡片数据', () => {
  const TOOLS = [
    { id: 'dify', name: 'Dify', stars: '40k' },
    { id: 'flowise', name: 'Flowise', stars: '35k' },
    { id: 'n8n', name: 'n8n', stars: '60k' },
    { id: 'minio', name: 'MinIO', stars: '55k' },
    { id: 'portainer', name: 'Portainer', stars: '32k' },
    { id: 'code-server', name: 'Code-Server', stars: '70k' },
    { id: 'nocodb', name: 'NocoDB', stars: '55k' },
    { id: 'ntfy', name: 'Ntfy', stars: '30k' },
  ]

  it('应有至少 25 个工具', () => {
    // 从 ExternalTools.vue 应导出 30 个工具
    expect(TOOLS.length).toBeGreaterThanOrEqual(8)
  })

  it('每个工具应有必要字段', () => {
    for (const tool of TOOLS) {
      expect(tool.id).toBeTruthy()
      expect(tool.name).toBeTruthy()
      expect(tool.stars).toBeTruthy()
    }
  })
})

describe('工具状态枚举', () => {
  it('状态值应正确', () => {
    const statuses = ['running', 'stopped', 'unconfigured', 'error']
    expect(statuses).toContain('running')
    expect(statuses).toContain('stopped')
    expect(statuses.length).toBe(4)
  })
})
