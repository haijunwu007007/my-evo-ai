/**
 * AUTO-EVO-AI 国际化 (i18n) — 前端多语言引擎
 * 支持: 中文 / English / 日本語 / 한국어
 */

const I18N = {
  'zh-CN': {
    name: '中文',
    title: '⚡ AUTO-EVO-AI',
    subtitle: '生产力级 AI 自动化编排系统',
    auth_heading: '🔐 开始使用',
    auth_user: '用户名',
    auth_user_placeholder: '给你的名字',
    auth_pass: '密码（可选）',
    auth_pass_placeholder: '留空即可',
    auth_key: 'API Key（可选）',
    auth_key_placeholder: 'OpenAI / 其他 LLM Key',
    auth_btn: '🚀 进入系统',
    greeting: '你好，{name}！输入你想做的事',
    tab_chat: '💬 对话',
    tab_dashboard: '📊 仪表盘',
    tab_business: '🏢 企业管理',
    input_placeholder: '输入你想做的事...',
    mic_title: '语音输入',
    logout: '🔓 退出',
    bot_name: 'AUTO-EVO-AI',
    you: '你',
    loading: '思考中...',
    clear_confirm: '清除所有对话历史？',
    mic_unsupported: '请使用 Chrome/Edge 浏览器',
    mic_failed: '启动失败',
    send_failed: '处理失败: ',
    auth_required: '请先输入用户名',
    // chat responses
    what_can_do: [
      "我能干这些事：\n\n📊 **看看系统状态** — 说「系统怎么样」\n🤖 **叫几个AI讨论** — 说「团队讨论xxx」\n🖥️ **操作电脑** — 说「帮我截图」去 Agent-S\n⏰ **定时任务** — 说「每天下午5点备份」\n🏢 **企业管理** — 点右上角「企业管理」\n🔔 **通知推送** — 说「通知我服务器状态」\n🎤 **语音输入** — 点输入框边的 🎤 按钮\n\n你想先试哪个？",
      "我能做的事情很多：\n\n📊 **系统状态** — 「系统怎么样」\n🤖 **AI团队讨论** — 「团队讨论xxx」\n🖥️ **桌面操作** — 「帮我打开记事本」\n⏰ **定时任务** — 「每天下午5点」\n\n选一个试试？"
    ],
    status_ok: [
      "一切正常 ✅\n• 版本 {version}\n• 桌面自动化 {sdk}\n• API Key {key}\n\n放心用，有问题随时叫我。",
      "系统跑着呢 ✅\n版本 {version}，{sdk}，{key}\n有需要就说。"
    ],
    status_sdk_ready: '就绪',
    status_sdk_missing: '未安装',
    status_key_ready: '已配置',
    status_key_missing: '未配置，需要的话去系统后台配',
    team_discussion: '👥 团队讨论',
    system_team: '系统',
    team_lead: '我',
  },

  en: {
    name: 'English',
    title: '⚡ AUTO-EVO-AI',
    subtitle: 'Enterprise AI Automation Platform',
    auth_heading: '🔐 Get Started',
    auth_user: 'Username',
    auth_user_placeholder: 'Your name',
    auth_pass: 'Password (optional)',
    auth_pass_placeholder: 'Leave blank',
    auth_key: 'API Key (optional)',
    auth_key_placeholder: 'OpenAI / other LLM Key',
    auth_btn: '🚀 Enter',
    greeting: 'Hello {name}! What can I do for you?',
    tab_chat: '💬 Chat',
    tab_dashboard: '📊 Dashboard',
    tab_business: '🏢 Enterprise',
    input_placeholder: 'Type what you want...',
    mic_title: 'Voice input',
    logout: '🔓 Logout',
    bot_name: 'AUTO-EVO-AI',
    you: 'You',
    loading: 'Thinking...',
    clear_confirm: 'Clear all chat history?',
    mic_unsupported: 'Please use Chrome/Edge browser',
    mic_failed: 'Start failed',
    send_failed: 'Error: ',
    auth_required: 'Please enter a username',
    what_can_do: [
      "Here's what I can do:\n\n📊 **System Status** — Say \"check status\"\n🤖 **AI Team Discussion** — Say \"team discuss xxx\"\n🖥️ **Desktop Control** — Say \"screenshot\"\n⏰ **Scheduled Tasks** — Say \"backup at 5pm daily\"\n🏢 **Enterprise** — Click \"Enterprise\" top right\n🎤 **Voice Input** — Click 🎤 button\n\nWhat should we try first?",
    ],
    status_ok: [
      "All systems running ✅\n• Version {version}\n• Desktop automation: {sdk}\n• API Key: {key}\n\nAnything else?",
    ],
    status_sdk_ready: 'Ready',
    status_sdk_missing: 'Not installed',
    status_key_ready: 'Configured',
    status_key_missing: 'Not configured',
    team_discussion: '👥 Team Discussion',
    system_team: 'System',
    team_lead: 'Me',
  },

  ja: {
    name: '日本語',
    title: '⚡ AUTO-EVO-AI',
    subtitle: 'エンタープライズAI自動化プラットフォーム',
    auth_heading: '🔐 はじめる',
    auth_user: 'ユーザー名',
    auth_user_placeholder: 'あなたの名前',
    auth_pass: 'パスワード（任意）',
    auth_pass_placeholder: '空欄でOK',
    auth_key: 'API Key（任意）',
    auth_key_placeholder: 'OpenAI / その他LLM Key',
    auth_btn: '🚀 ログイン',
    greeting: 'こんにちは、{name}さん！どうしますか？',
    tab_chat: '💬 チャット',
    tab_dashboard: '📊 ダッシュボード',
    tab_business: '🏢 企業管理',
    input_placeholder: 'やりたいことを入力...',
    mic_title: '音声入力',
    logout: '🔓 ログアウト',
    bot_name: 'AUTO-EVO-AI',
    you: 'あなた',
    loading: '考え中...',
    clear_confirm: 'チャット履歴をクリアしますか？',
    mic_unsupported: 'Chrome/Edgeブラウザを使用してください',
    mic_failed: '起動失敗',
    send_failed: 'エラー: ',
    auth_required: 'ユーザー名を入力してください',
    what_can_do: [
      "できること：\n\n📊 **システム状態** — 「状態を確認」\n🤖 **AIチーム討論** — 「チーム討論xxx」\n🖥️ **デスクトップ操作** — 「スクリーンショット」\n⏰ **定期タスク** — 「毎日17時にバックアップ」\n🏢 **企業管理** — 右上の「企業管理」\n🎤 **音声入力** — 🎤 ボタンをクリック\n\n何を試しますか？",
    ],
    status_ok: ["正常稼働中 ✅\n• バージョン {version}\n• デスクトップ自動化: {sdk}\n• API Key: {key}\n\n何か他にありますか？"],
    status_sdk_ready: '利用可能',
    status_sdk_missing: '未インストール',
    status_key_ready: '設定済み',
    status_key_missing: '未設定',
    team_discussion: '👥 チーム討論',
    system_team: 'システム',
    team_lead: '私',
  },

  ko: {
    name: '한국어',
    title: '⚡ AUTO-EVO-AI',
    subtitle: '엔터프라이즈 AI 자동화 플랫폼',
    auth_heading: '🔐 시작하기',
    auth_user: '사용자명',
    auth_user_placeholder: '이름을 입력하세요',
    auth_pass: '비밀번호 (선택)',
    auth_pass_placeholder: '비워두기',
    auth_key: 'API Key (선택)',
    auth_key_placeholder: 'OpenAI / 기타 LLM Key',
    auth_btn: '🚀 입장',
    greeting: '{name}님! 무엇을 할까요?',
    tab_chat: '💬 채팅',
    tab_dashboard: '📊 대시보드',
    tab_business: '🏢 기업관리',
    input_placeholder: '원하는 것을 입력하세요...',
    mic_title: '음성 입력',
    logout: '🔓 로그아웃',
    bot_name: 'AUTO-EVO-AI',
    you: '나',
    loading: '생각 중...',
    clear_confirm: '채팅 기록을 지우시겠습니까?',
    mic_unsupported: 'Chrome/Edge 브라우저를 사용하세요',
    mic_failed: '시작 실패',
    send_failed: '오류: ',
    auth_required: '사용자명을 입력하세요',
    what_can_do: [
      "제가 할 수 있는 일:\n\n📊 **시스템 상태** — \"상태 확인\"\n🤖 **AI 팀 토론** — \"팀 토론 xxx\"\n🖥️ **데스크톱 작업** — \"스크린샷\"\n⏰ **예약 작업** — \"매일 오후5시 백업\"\n🏢 **기업 관리** — 우측 상단 «기업관리»\n🎤 **음성 입력** — 🎤 버튼 클릭\n\n무엇을 먼저 해볼까요?",
    ],
    status_ok: ["정상 작동 중 ✅\n• 버전 {version}\n• 데스크톱 자동화: {sdk}\n• API Key: {key}\n\n다른 도움이 필요하세요?"],
    status_sdk_ready: '준비됨',
    status_sdk_missing: '설치되지 않음',
    status_key_ready: '설정됨',
    status_key_missing: '설정되지 않음',
    team_discussion: '👥 팀 토론',
    system_team: '시스템',
    team_lead: '나',
  }
}

// 当前语言
let _locale = 'zh-CN'

function detectLocale() {
  const saved = localStorage.getItem('evo_locale')
  if (saved && I18N[saved]) return saved
  const browser = (navigator.language || navigator.userLanguage || 'zh-CN')
  if (browser.startsWith('zh')) return 'zh-CN'
  if (browser.startsWith('ja')) return 'ja'
  if (browser.startsWith('ko')) return 'ko'
  return 'en'
}

function setLocale(locale) {
  if (!I18N[locale]) return
  _locale = locale
  localStorage.setItem('evo_locale', locale)
  document.documentElement.lang = locale
  // 重绘界面
  translateUI()
}

function getLocale() { return _locale }

function __(key, ...args) {
  const dict = I18N[_locale] || I18N['zh-CN']
  let val = dict[key]
  if (Array.isArray(val)) val = val[Math.floor(Math.random() * val.length)]
  if (val === undefined) val = I18N['zh-CN'][key] || key
  if (args.length > 0) {
    for (const a of args) val = val.replace(/\{(\w+)\}/, a)
  }
  return val
}

function getLanguages() {
  return Object.entries(I18N).map(([code, data]) => ({ code, name: data.name }))
}

// 页面初始化
_locale = detectLocale()
document.documentElement.lang = _locale
