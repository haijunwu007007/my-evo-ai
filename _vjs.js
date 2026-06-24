const fs = require('fs');
const d = fs.readFileSync('D:\\AUTO-EVO-AI-V0.1\\frontend\\chat.html', 'utf-8');
const m = d.match(/<script>([\s\S]*?)<\/script>/);
if (!m) { console.log('NO SCRIPT BLOCK'); process.exit(1); }
const js = m[1];
fs.writeFileSync('D:\\_chatjs.js', js);
try {
  require('child_process').execSync('node --check D:\\_chatjs.js 2>&1');
  console.log('JS OK');
} catch(e) {
  console.log('JS FAIL:', e.stderr.toString().slice(0, 300));
}
