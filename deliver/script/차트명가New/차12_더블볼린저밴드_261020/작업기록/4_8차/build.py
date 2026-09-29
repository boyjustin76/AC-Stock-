# -*- coding: utf-8 -*-
"""수정_1.docx 를 틀로 8차를 조립한다 (docx 스킬의 편집 절차: 풀기 → document.xml 수정 → 묶기)."""
import re, sys, zipfile, shutil, importlib
sys.path.insert(0, r"C:\Users\user\AppData\Local\Temp\claude\C--Users-user-Desktop-----------------01-----E-Script\e1fa110c-f82d-4e3c-a7f3-2b7d8284ef16\scratchpad\v8")
import spec
importlib.reload(spec)

BASE, OUT = sys.argv[1], sys.argv[2]
src = zipfile.ZipFile(BASE)
xml = src.read("word/document.xml").decode("utf-8")
앞, 몸 = xml.split("<w:body>", 1)
몸, 끝 = 몸.rsplit("</w:body>", 1)
sect = re.search(r"<w:sectPr\b.*?</w:sectPr>\s*$", 몸, re.S)
sectpr = sect.group(0) if sect else ""
몸 = 몸[:sect.start()] if sect else 몸
blocks = re.findall(r"<w:tbl>.*?</w:tbl>|<w:p\b(?:(?!</w:p>).)*</w:p>|<w:p\b[^>]*/>", 몸, re.S)
assert len(blocks) == 129, len(blocks)   # 0~128. 끝의 sectPr 은 문단이 아니다


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def 아이디떼기(p):
    # 문단을 여러 번 찍어 내므로 w14:paraId / textId 가 겹치지 않게 뗀다
    return re.sub(r'\s+w14:(paraId|textId)="[^"]*"', "", p)


def 틀(p):
    open_tag = 아이디떼기(re.match(r"<w:p\b[^>]*>", p).group(0))
    ppr = re.search(r"<w:pPr>.*?</w:pPr>", p, re.S)
    run = re.search(r"<w:r\b[^>]*>(.*?)</w:r>", p, re.S)
    rpr = re.search(r"<w:rPr>.*?</w:rPr>", run.group(1), re.S) if run else None
    return open_tag, (ppr.group(0) if ppr else ""), (rpr.group(0) if rpr else "")


def 찍기(틀값, 글):
    o, ppr, rpr = 틀값
    return '%s%s<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r></w:p>' % (o, ppr, rpr, esc(글))


본문틀 = 틀(blocks[4])
빈줄 = 아이디떼기(blocks[6])
새 = []
for item in spec.S:
    k = item[0]
    if k == "K":
        새.append(blocks[item[1]])
    elif k == "H":
        새.append(찍기(틀(blocks[item[1]]), item[2]))
    elif k == "B":
        새.append(찍기(본문틀, item[1]))
    elif k == "E":
        새.append(빈줄)
xml2 = 앞 + "<w:body>" + "".join(새) + sectpr + "</w:body>" + 끝

tmp = OUT + ".tmp"
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
    for it in src.infolist():
        out.writestr(it, xml2.encode("utf-8") if it.filename == "word/document.xml" else src.read(it.filename))
src.close()
shutil.move(tmp, OUT)
print("냈다: 문단 %d개 (본문 %d · 그대로 %d)" % (len(새), sum(1 for i in spec.S if i[0] == "B"), sum(1 for i in spec.S if i[0] == "K")))
