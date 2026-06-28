/* AUTO-EVO-AI 浏览器本地代理 — 打开这个页面，你的浏览器就变成系统的手脚 */
/* 将这个文件注入到 local-agent.html */

var AGENT_WS = null
var AGENT_RECONNECT = null

function connectAgent(){
  var protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  var host = location.host
  AGENT_WS = new WebSocket(protocol + '//' + host + '/ws/agent')
  AGENT_WS.onopen = function(){
    document.getElementById('agtStatus').textContent = '✅ 已连接'
    document.getElementById('agtStatus').className = 'connected'
    document.getElementById('agtInfo').textContent = '等待命令...'
  }
  AGENT_WS.onmessage = function(ev){
    try{
      var msg = JSON.parse(ev.data)
      var action = msg.action || ''
      var params = msg.params || {}
      document.getElementById('agtInfo').textContent = '执行: ' + action
      executeLocal(action, params, function(result){
        AGENT_WS.send(JSON.stringify({type:'result', id:msg.id, data:result}))
        document.getElementById('agtInfo').textContent = '✅ ' + action + ' 完成'
      })
    }catch(e){
      document.getElementById('agtInfo').textContent = '❌ 解析错误: ' + e.message
    }
  }
  AGENT_WS.onclose = function(){
    document.getElementById('agtStatus').textContent = '⚠️ 已断开'
    document.getElementById('agtStatus').className = 'disconnected'
    AGENT_RECONNECT = setTimeout(connectAgent, 3000)
  }
  AGENT_WS.onerror = function(){
    document.getElementById('agtStatus').textContent = '❌ 连接失败'
    document.getElementById('agtStatus').className = 'disconnected'
  }
}

function executeLocal(action, params, callback){
  switch(action){
    case 'ping':
      callback({ok:true, pong:true, browser:navigator.userAgent.slice(0,60)})
      break
    case 'open_url':
      window.open(params.url, '_blank')
      callback({ok:true, info:'已打开: ' + params.url})
      break
    case 'open_browser':
      window.open(params.url || 'https://www.baidu.com', '_blank')
      callback({ok:true, info:'浏览器已打开'})
      break
    case 'new_tab':
      window.open(params.url || 'about:blank', '_blank')
      callback({ok:true, info:'已打开新标签页'})
      break
    case 'alert':
      alert(params.message || '来自AUTO-EVO-AI的消息')
      callback({ok:true})
      break
    case 'notify':
      if(Notification.permission === 'granted'){
        new Notification('AUTO-EVO-AI', {body: params.message || ''})
      }
      callback({ok:true})
      break
    case 'clipboard_copy':
      navigator.clipboard.writeText(params.text || '')
        .then(function(){callback({ok:true})})
        .catch(function(e){callback({ok:false, error:e.message})})
      break
    case 'file_select':
      var inp = document.createElement('input'); inp.type = 'file'; inp.multiple = true
      inp.onchange = function(){
        var files = []
        for(var i=0;i<inp.files.length;i++) files.push(inp.files[i].name)
        callback({ok:true, files:files})
      }
      inp.oncancel = function(){callback({ok:false, error:'已取消'})}
      inp.click()
      break
    case 'screenshot':
      if(!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia){
        callback({ok:false, error:'浏览器不支持屏幕截图'})
        return
      }
      navigator.mediaDevices.getDisplayMedia({video:{mediaSource:'screen'}})
        .then(function(stream){
          var v = document.createElement('video')
          v.srcObject = stream; v.play()
          setTimeout(function(){
            stream.getTracks().forEach(function(t){t.stop()})
            callback({ok:true, info:'截图成功'})
          }, 1000)
        })
        .catch(function(){callback({ok:false, error:'截图被取消'})})
      break
    case 'get_info':
      callback({ok:true, info:{
        url: location.href,
        platform: navigator.platform,
        language: navigator.language,
        userAgent: navigator.userAgent.slice(0,80)
      }})
      break
    default:
      callback({ok:false, error:'未知命令: ' + action})
  }
}

function initAgent(){
  // 请求通知权限
  if('Notification' in window && Notification.permission === 'default'){
    Notification.requestPermission()
  }
  connectAgent()
  document.getElementById('agtStart').textContent = '正在连接...'
}
