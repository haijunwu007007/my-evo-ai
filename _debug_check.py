lines = open('modules/agent_apollo.py', 'r', encoding='utf-8').readlines()
print('L396:', repr(lines[395]))
print('L397:', repr(lines[396]))
l = lines[395].rstrip()
print('ends with dq:', l.endswith('"'))
dq = l.count('"')
esc = l.count('\\"')
print('dq count:', dq, 'escaped:', esc, 'odd:', (dq - esc) % 2 == 1)
print('next starts with dq:', lines[396].strip().startswith('"'))

# 看行尾是否有 \\r
print('rline last 10 chars:', repr(l[-10:]))
print('\\r in line:', repr(l).count('\\r'))
