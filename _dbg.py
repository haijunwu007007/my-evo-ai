f = 'modules/experience_base.py'
lines = open(f, 'r', encoding='utf-8').readlines()
for i in range(745, 760):
    r = lines[i].rstrip().replace('\u2705','[OK]').replace('\u274c','[NO]')
    print(f'{i+1}: {r}')
