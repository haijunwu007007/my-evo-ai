<template>
  <span class="voice-input-wrapper" :style="{ display: 'inline-flex', alignItems: 'center' }">
    <button
      class="mic-btn"
      :class="{ listening: isListening }"
      @click="toggle"
      :title="isListening ? '点击停止录音' : '点击语音输入'"
      :disabled="!supported"
    >
      <span v-if="!supported">🎤</span>
      <span v-else-if="isListening">🔴</span>
      <span v-else>🎤</span>
    </button>
    <span v-if="isListening" class="listening-indicator">正在聆听…</span>
    <span v-if="errMsg" class="err-tip">{{ errMsg }}</span>
  </span>
</template>

<script setup lang="ts">
import { ref, onUnmounted } from 'vue'

const emit = defineEmits<{
  (e: 'result', text: string): void
}>()

const supported = ref(false)
const isListening = ref(false)
const errMsg = ref('')

let recognition: any = null

// 检测浏览器是否支持语音识别
const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
supported.value = !!SpeechRecognition

function toggle() {
  if (isListening.value) {
    stop()
  } else {
    start()
  }
}

function start() {
  errMsg.value = ''
  if (!SpeechRecognition) {
    errMsg.value = '浏览器不支持语音输入'
    return
  }
  recognition = new SpeechRecognition()
  recognition.lang = 'zh-CN'
  recognition.continuous = false
  recognition.interimResults = false
  recognition.maxAlternatives = 1

  recognition.onresult = (event: any) => {
    const text = event.results[0][0].transcript
    emit('result', text)
    isListening.value = false
  }

  recognition.onerror = (event: any) => {
    errMsg.value = event.error === 'no-speech' ? '未检测到语音' : `错误: ${event.error}`
    isListening.value = false
  }

  recognition.onend = () => {
    isListening.value = false
  }

  try {
    recognition.start()
    isListening.value = true
  } catch (e: any) {
    errMsg.value = '启动失败: ' + e.message
  }
}

function stop() {
  if (recognition) {
    recognition.stop()
    recognition = null
  }
  isListening.value = false
}

onUnmounted(() => {
  if (recognition) recognition.abort()
})
</script>

<style scoped>
.mic-btn {
  width: 32px;
  height: 32px;
  border: 1px solid var(--border-subtle, #2d2d44);
  border-radius: 8px;
  background: var(--bg-sidebar, #111127);
  cursor: pointer;
  font-size: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.mic-btn:hover { background: rgba(99,102,241,0.12); border-color: #6366f1; }
.mic-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.mic-btn.listening {
  background: rgba(239,68,68,0.15);
  border-color: #ef4444;
  animation: pulse-mic 1.2s infinite;
}
@keyframes pulse-mic {
  0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.3); }
  50% { box-shadow: 0 0 0 6px rgba(239,68,68,0); }
}
.listening-indicator {
  font-size: 12px;
  color: #ef4444;
  margin-left: 6px;
  animation: blink 1s infinite;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.err-tip {
  font-size: 11px;
  color: #f59e0b;
  margin-left: 6px;
}
</style>
