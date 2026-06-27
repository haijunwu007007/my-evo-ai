import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open(r'D:\AUTO-EVO-AI-V0.1\frontend\chat_engine.js', 'r', encoding='utf-8') as f:
    d = f.read()

# Check if voiceStop already exists
if 'function voiceStop' in d:
    print('voiceStop already in JS')
else:
    # Find the last }
    i = d.rfind('\n// Voice functions\n')
    if i < 0:
        # Append new code
        d += '''
// Voice functions
var _vStream=null,_vRec=null,_vChunks=[],_vFileInput=null;
function voiceStart(e){e.preventDefault();if(_vRec&&_vRec.state=='recording'){voiceStop(e);return}var b=document.getElementById('voiceBtn');b.textContent='...';b.style.background='#ff9800';_vChunks=[];navigator.mediaDevices.getUserMedia({audio:true}).then(function(s){_vStream=s;var mt=MediaRecorder.isTypeSupported('audio/webm;codecs=opus')?'audio/webm;codecs=opus':'audio/webm';_vRec=new MediaRecorder(s,{mimeType:mt});_vRec.ondataavailable=function(ev){if(ev.data.size>0)_vChunks.push(ev.data)};b.textContent='停止';b.style.background='#e53935';_vRec.start()}).catch(function(){if(!_vFileInput){_vFileInput=document.createElement('input');_vFileInput.type='file';_vFileInput.accept='audio/*';_vFileInput.style.display='none';_vFileInput.onchange=function(){var f=_vFileInput.files&&_vFileInput.files[0];_vFileInput.value='';if(!f){b.textContent='🎤';b.style.background='';return}b.textContent='...';var fd=new FormData();fd.append('file',f,f.name);fetch('/api/v1/speech/recognize',{method:'POST',body:fd}).then(function(r){return r.json()}).then(function(j){var i=document.getElementById('input');if(j.success&&j.text&&i){i.value=j.text;send()};b.textContent='🎤';b.style.background=''}).catch(function(){b.textContent='🎤';b.style.background=''})};document.body.appendChild(_vFileInput)}_vFileInput.click()})}
function voiceStop(e){if(!_vRec){return}_vRec.onstop=function(){if(_vStream){_vStream.getTracks().forEach(function(t){t.stop()});_vStream=null}if(_vChunks.length>0){var fb=new Blob(_vChunks,{type:'audio/webm'});var fd=new FormData();fd.append('file',fb,'v.webm');fetch('/api/v1/speech/recognize',{method:'POST',body:fd}).then(function(r){return r.json()}).then(function(j){var i=document.getElementById('input');if(j.success&&j.text&&i){i.value=j.text;send()}})}};try{_vRec.stop()}catch(ex){}_vRec=null}
'''
    else:
        # Replace everything after // Voice functions
        d = d[:i+23]  # keep the comment

    with open(r'D:\AUTO-EVO-AI-V0.1\frontend\chat_engine.js', 'w', encoding='utf-8') as f:
        f.write(d)

    print('Added voice functions')
    print('voiceStart:', d.count('voiceStart'))
    print('voiceStop:', d.count('voiceStop'))
    print('Size:', len(d))
