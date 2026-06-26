import paramiko, urllib.request, re

js = urllib.request.urlopen("http://122.51.144.227:8765/frontend/chat_engine.js", timeout=15).read().decode()

old_block = re.search(r'function startVoiceRecord\(e\)\{.+?function toggleRightPanel', js, re.DOTALL).group()

new_block = """function startVoiceRecord(e){
  if(_voicing){stopVoiceRecord();return}
  _voicing=true;_voiceReady=false
  var b=document.getElementById('voiceMic'),l=document.getElementById('voiceLabel')
  b.classList.add('recording');l.textContent='请说话';_voiceChunks=[]
  try{
    navigator.mediaDevices.getUserMedia({audio:true}).then(function(s){
      _voiceStream=s;_voiceReady=true
      var mt=MediaRecorder.isTypeSupported('audio/webm;codecs=opus')?'audio/webm;codecs=opus':'audio/webm'
      _voiceRec=new MediaRecorder(s,{mimeType:mt})
      _voiceRec.ondataavailable=function(ev){if(ev.data.size>0)_voiceChunks.push(ev.data)}
      _voiceRec.start();l.textContent='松开发送'
    }).catch(function(){b.classList.remove('recording');l.textContent='无权限';_voicing=false;setTimeout(function(){l.textContent='🎤语音'},2000)})
  }catch(err){b.classList.remove('recording');l.textContent='不支持';_voicing=false;setTimeout(function(){l.textContent='🎤语音'},2000)}
}
function stopVoiceRecord(e){
  if(!_voicing)return;_voicing=false
  var b=document.getElementById('voiceMic'),l=document.getElementById('voiceLabel'),i=document.getElementById('input')
  b.classList.remove('recording')
  if(!_voiceReady)return setTimeout(function(){stopVoiceRecord()},300)
  if(!_voiceRec||_voiceRec.state==='inactive'){l.textContent='🎤语音';return}
  _voiceRec.onstop=function(){
    if(_voiceStream){_voiceStream.getTracks().forEach(function(t){t.stop()});_voiceStream=null}
    if(_voiceChunks.length===0){l.textContent='🎤语音';return}
    l.textContent='识别中'
    var fd=new FormData();fd.append('file',new Blob(_voiceChunks,{type:'audio/webm'}),'v.webm');_voiceChunks=[]
    fetch('/api/v1/speech/recognize',{method:'POST',body:fd}).then(function(r){return r.json()}).then(function(j){
      if(j.success&&j.text){i.value=j.text;l.textContent='🎤语音';send()}
      else{l.textContent='🎤语音'}
    }).catch(function(){l.textContent='🎤语音'})
  }
  _voiceRec.stop()
}
function cancelVoiceRecord(e){
  if(!_voicing||!_voiceRec)return;_voicing=false
  var b=document.getElementById('voiceMic'),l=document.getElementById('voiceLabel')
  b.classList.remove('recording');l.textContent='🎤语音';document.getElementById('input').value=''
  if(_voiceRec.state!=='inactive'){try{_voiceRec.stop()}catch(ex){}}
  if(_voiceStream){_voiceStream.getTracks().forEach(function(t){t.stop()});_voiceStream=null}
  _voiceChunks=[]
}
function toggleRightPanel"""

js = js.replace(old_block, new_block)

# Update event binding to use click only for voice
old_bind = re.search(r'// 语音按钮事件绑定.*?function startVoiceRecord', js, re.DOTALL)
if old_bind:
    old = old_bind.group()
    new = "// 语音按钮事件绑定(点击切换)\n(function(){var mic=document.getElementById('voiceMic');if(mic)mic.addEventListener('click',function(e){startVoiceRecord(e)})})()\nfunction startVoiceRecord"
    js = js.replace(old, new)

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect("122.51.144.227", username="ubuntu", password="Hj711201", timeout=10)
sftp = s.open_sftp()
with sftp.open("/home/ubuntu/my-evo-ai/frontend/chat_engine.js", "w") as f:
    f.write(js)
sftp.close()
s.exec_command("sudo systemctl restart evo.service")
s.close()
print(f"Deployed {len(js)} bytes, click mode")
