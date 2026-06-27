import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open(r'D:\AUTO-EVO-AI-V0.1\frontend\chat_engine.js', 'r', encoding='utf-8') as f:
    d = f.read()

# Find existing voice functions section and remove it
i = d.find('\n// Voice functions\n')
if i >= 0:
    d = d[:i]

# Append clean voice functions
voice_code = (
    '\n// Voice functions\n'
    'var _vStream=null,_vRec=null,_vChunks=[],_vFileInput=null;\n'
    'function voiceStart(e){'
    'e.preventDefault();'
    'if(_vRec&&_vRec.state==\'recording\'){voiceStop(e);return}'
    'var b=document.getElementById(\'voiceBtn\');'
    'b.textContent=\'...\';b.style.background=\'#ff9800\';'
    '_vChunks=[];'
    'navigator.mediaDevices.getUserMedia({audio:true}).then(function(s){'
    '_vStream=s;'
    'var mt=MediaRecorder.isTypeSupported(\'audio/webm;codecs=opus\')?\'audio/webm;codecs=opus\':\'audio/webm\';'
    '_vRec=new MediaRecorder(s,{mimeType:mt});'
    '_vRec.ondataavailable=function(ev){if(ev.data.size>0)_vChunks.push(ev.data)};'
    'b.textContent=\'\u505c\u6b62\';b.style.background=\'#e53935\';'
    '_vRec.start()'
    '}).catch(function(){'
    'if(!_vFileInput){'
    '_vFileInput=document.createElement(\'input\');'
    '_vFileInput.type=\'file\';_vFileInput.accept=\'audio/*\';'
    '_vFileInput.style.display=\'none\';'
    '_vFileInput.onchange=function(){'
    'var f=_vFileInput.files&&_vFileInput.files[0];_vFileInput.value=\'\';'
    'if(!f){b.textContent=\'\U0001f3a4\';b.style.background=\'\';return}'
    'b.textContent=\'...\';'
    'var fd=new FormData();fd.append(\'file\',f,f.name);'
    'fetch(\'/api/v1/speech/recognize\',{method:\'POST\',body:fd}).then(function(r){return r.json()}).then(function(j){'
    'var i=document.getElementById(\'input\');'
    'if(j.success&&j.text&&i){i.value=j.text;send()};'
    'b.textContent=\'\U0001f3a4\';b.style.background=\'\''
    '}).catch(function(){b.textContent=\'\U0001f3a4\';b.style.background=\'\'})'
    '};'
    'document.body.appendChild(_vFileInput)'
    '}'
    '_vFileInput.click()'
    '});'
    '}\n'
    'function voiceStop(e){'
    'if(!_vRec){return}'
    '_vRec.onstop=function(){'
    'if(_vStream){_vStream.getTracks().forEach(function(t){t.stop()});_vStream=null}'
    'if(_vChunks.length>0){'
    'var fb=new Blob(_vChunks,{type:\'audio/webm\'});'
    'var fd=new FormData();fd.append(\'file\',fb,\'v.webm\');'
    'fetch(\'/api/v1/speech/recognize\',{method:\'POST\',body:fd}).then(function(r){return r.json()}).then(function(j){'
    'var i=document.getElementById(\'input\');'
    'if(j.success&&j.text&&i){i.value=j.text;send()}'
    '})'
    '}'
    '};'
    'try{_vRec.stop()}catch(ex){}'
    '_vRec=null'
    '}\n'
)

d += voice_code

with open(r'D:\AUTO-EVO-AI-V0.1\frontend\chat_engine.js', 'w', encoding='utf-8') as f:
    f.write(d)

print('voiceStart:', d.count('function voiceStart'))
print('voiceStop:', d.count('function voiceStop'))
print('Size:', len(d))
