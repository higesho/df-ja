# 使い方（dfint-ja で）: ゲームで伝説のページを開いた後に python -I -X utf8 tools/sentences/log_check.py
# 結果: work/frag/legend_sents2.txt（ログの文）と、訳せない・英語が残る文の一覧
"""ログの段落（paragraph piece）を文に分け、試験スクリプトで訳せない文を出す。リンクは残す"""
import re,subprocess,sys
t=open('../dfint-data/dfint-log.log',encoding='utf-8',errors='replace').read()
pieces=re.findall(r'paragraph piece box=\w+ old_len=\d+: "(.*)"\n',t)
sents=[]
for p in pieces:
    p=p.replace('\\"','"')
    for part in re.split(r'\[(?:B|P|R)\]',p):
        part=re.sub(r'\[C:\d+:\d+:\d+\]','',part).strip()
        for s in re.findall(r'(?:[^.!?\[]|\[[^\]]*\])+(?:[.!?]+|$)\s*',part):
            s=s.strip()
            if s and re.search('[a-z]{3}',re.sub(r'\[[^\]]*\]','',s)): sents.append(s)
sents=list(dict.fromkeys(sents))
__import__('os').makedirs('work/frag',exist_ok=True) or open('work/frag/legend_sents2.txt','w',encoding='utf-8').write('\n'.join(sents))
r=subprocess.run(['python','-I','-X','utf8','tools/sentences/test.py','-f','work/frag/legend_sents2.txt'],capture_output=True,text=True,encoding='utf-8').stdout.splitlines()
out=[]
for i,l in enumerate(r):
    if l.startswith('  → '):
        en,ja=r[i-1],l[4:]
        plain=re.sub(r'\[[^\]]*\]','',ja)
        if ja=='（訳せない）' or re.search(r'\b[a-z]{3,}\b',re.sub(r'\b[A-Z][\w\'-]*( (of|the|and) [A-Z][\w\'-]*)*','',plain)):
            out.append((en,ja))
print(len(sents),'bad',len(out))
for en,ja in out: print('EN',re.sub(r'\[/?LPAGE[^\]]*\]','',en)[:260]); print('JA',re.sub(r'\[/?LPAGE[^\]]*\]','',ja)[:200])
