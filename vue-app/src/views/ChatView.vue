<template>
  <div class="chat-view">
    <div class="tools-area">
      <div v-for="cat in categories" :key="cat.name" class="cat-block">
        <div class="cat-head" @click="cat.open = !cat.open">
          {{ cat.name }} <span class="cat-arrow">{{ cat.open ? '\u25bc' : '\u25b6' }}</span>
        </div>
        <div v-show="cat.open" class="cat-body">
          <span v-for="t in cat.tools" :key="t.name" class="qa" @click="pickTool(t)">{{ t.label }}</span>
        </div>
      </div>
    </div>
    <div class="input-area">
      <input v-model="input" @keyup.enter="send" placeholder="输入你想做的事..." class="chat-input">
      <button @click="send" class="send-btn">\u279e</button>
    </div>
  </div>
</template>
<script>
export default {
  data() {
    return {
      user: localStorage.getItem('evo_user') || 'admin',
      input: '',
      categories: [
        {name:'\U0001f4cb 文档/办公',open:false,tools:[
          {name:'docx_processor',label:'\U0001f4c4 文档生成'},{name:'excel_pro',label:'\U0001f4ca 电子表格'},
          {name:'ppt_generator',label:'\U0001f4fd 演示文稿'},{name:'pdf_toolkit',label:'\U0001f4c3 PDF处理'},
        ]},
        {name:'\U0001f527 开发/代码',open:false,tools:[
          {name:'interpreter_execute',label:'\U0001f4bb 代码执行'},{name:'autogpt_run',label:'\U0001f9e0 自主任务'},
          {name:'openhands_generate',label:'\U0001f3d7 生成项目'},{name:'code_review',label:'\U0001f50d PR审查'},
        ]},
      ]
    }
  },
  methods: {
    pickTool(t) { this.input = t.label + '\uff1a' },
    async send() {
      if (!this.input.trim()) return
      await fetch('/api/v1/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({msg:this.input})})
      this.input = ''
    }
  }
}
</script>
<style scoped>
.chat-view{padding:8px}.tools-area{max-height:300px;overflow-y:auto;padding:8px 0}
.cat-block{margin-bottom:2px}.cat-head{padding:4px 8px;font-size:12px;font-weight:600;color:var(--accent);cursor:pointer;border-radius:6px}
.cat-head:hover{background:var(--glass)}.cat-body{display:flex;flex-wrap:wrap;gap:4px;padding:4px 8px}
.qa{padding:3px 10px;border-radius:12px;font-size:11px;color:var(--text2);border:1px solid var(--border);cursor:pointer;background:var(--card)}
.qa:hover{border-color:var(--accent);color:var(--accent)}
.input-area{display:flex;gap:8px;padding:8px 0;border-top:1px solid var(--border)}
.chat-input{flex:1;padding:10px 14px;border:1px solid var(--border);border-radius:20px;font-size:13px;background:var(--input-bg);color:var(--text);outline:none}
.chat-input:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--glow)}
.send-btn{width:40px;height:40px;border-radius:50%;border:none;background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;font-size:16px;cursor:pointer}
</style>
