import re, os, glob

d = r'c:\Users\id654\Desktop\smart-campus-rag\chapters'
banned = ['首先', '其次', '最后', '此外', '另外', '总之', '值得注意的是',
          '需要指出的是', '重要的是', '显而易见', '我认为', '我觉得']
order = []
total = 0
print('%-30s %6s %s' % ('文件', '汉字', '禁用词/问题'))
for f in sorted(glob.glob(os.path.join(d, '*.md'))):
    t = open(f, encoding='utf-8').read()
    body = re.sub(r'<!--.*?-->', '', t, flags=re.S)
    lines = [l for l in body.split('\n') if not l.startswith('#') and not l.strip().startswith('|')]
    b = re.sub(r'```.*?```', '', '\n'.join(lines), flags=re.S)
    n = len(re.findall(r'[一-鿿]', b))
    hits = [w for w in banned if w in b]
    probs = hits[:]
    if re.search(r'^\s*[-*] ', b, re.M):
        probs.append('bullet')
    if '**' in b:
        probs.append('加粗')
    name = os.path.basename(f)
    if name.startswith(('01', '02')):
        for m in re.finditer(r'\[([1-8])\]', b):
            if m.group(1) not in order:
                order.append(m.group(1))
    if not name.startswith(('09', '00')):
        total += n
    print('%-30s %6d %s' % (name, n, probs or 'OK'))

print()
print('引用首现顺序(01+02):', ''.join(order))
print('正文六章+结论合计汉字:', total)

t = ''
for f in glob.glob(os.path.join(d, '*.md')):
    t += open(f, encoding='utf-8').read()
print('待补统计: 中文文献', t.count('[待补:中文文献]'), '| 图', t.count('[待补:图]'),
      '| 截图', t.count('[待补:截图]'), '| 实测', t.count('[待补:实测]'),
      '| 表内待实测', t.count('待实测'))
print('章间引用: 提到第7章处:', t.count('第7章'))
