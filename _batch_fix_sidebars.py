"""Batch add hamburger + sidebar-overlay + toggle function to pages."""
import os

frontend = r'D:\AUTO-EVO-AI-V0.1\frontend'

# Pages that need fixing: they have sidebar but no hamburger/overlay
targets = [
    'ComposeCanvas.html',
    'billion-os.html',
    'claw.html',
    'enterprise_server.html',
    'hermes.html',
    'human.html',
    'monitor.html',
]

# The toggle JS function + sidebar-overlay div to inject
OVERLAY_HTML = '\n<div class="sidebar-overlay" id="sidebarOverlay" onclick="toggleSidebar()"></div>\n'

TOGGLE_JS = '''
function toggleSidebar(){
  var s=document.querySelector(".sidebar");
  var o=document.getElementById("sidebarOverlay");
  if(s)s.classList.toggle("open");
  if(o)o.classList.toggle("show");
}'''

# Hamburger button HTML to insert at the start of topbar-left
HAMBURGER = '<button class="hamburger" onclick="toggleSidebar()" aria-label="\\u83dc\\u5355">\\u2630</button>'

for fname in targets:
    path = os.path.join(frontend, fname)
    text = open(path, 'r', encoding='utf-8', errors='ignore').read()
    changes = []

    # 1. Add sidebar-overlay before </body>
    if 'sidebar-overlay' not in text and 'sidebarOverlay' not in text:
        if '</body>' in text:
            text = text.replace('</body>', OVERLAY_HTML + '</body>')
            changes.append('overlay')
        else:
            print(f"  {fname}: NO </body> tag!")
            continue

    # 2. Add toggleSidebar function before </script> or at end
    if 'toggleSidebar' not in text:
        # Find last script block
        last_close = text.rfind('</script>')
        if last_close >= 0:
            text = text[:last_close+9] + TOGGLE_JS + text[last_close+9:]
            changes.append('toggleFn')
        else:
            # Inject before </body>
            text = text.replace('</body>', f'<script>{TOGGLE_JS}</script>\n</body>')
            changes.append('toggleFn(inline)')

    # 3. Add hamburger button to topbar-left
    if 'hamburger' not in text.lower():
        # Find topbar-left div
        tlb = '<div class="topbar-left">'
        if tlb in text:
            idx = text.find(tlb) + len(tlb)
            # Don't add if there's already a hamburger
            if text[idx:idx+30].find('hamburger') == -1:
                text = text[:idx] + f'\n{HAMBURGER}\n' + text[idx:]
                changes.append('hamburger')
        else:
            # Try <h1> or grad-title as insertion point
            h1 = text.find('grad-title')
            if h1 >= 0:
                # Find the opening div
                before = text.rfind('<', 0, h1)
                div_start = text.rfind('<div', 0, h1)
                if div_start >= 0 and (before == div_start or before - div_start < 20):
                    idx = text.find('>', div_start) + 1
                    text = text[:idx] + f'\n{HAMBURGER}\n' + text[idx:]
                    changes.append('hamburger')

    if changes:
        open(path, 'w', encoding='utf-8').write(text)
        print(f"  {fname}: {', '.join(changes)} {'=> ' + fname.replace('.html','').replace('_',' ')}")
    else:
        print(f"  {fname}: no changes needed (already has all)")

print("\nDone.")
