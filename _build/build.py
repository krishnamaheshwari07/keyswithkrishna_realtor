import sys, re, json, subprocess, pathlib, html
sys.path.insert(0,'_build')
from content import *
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path('.').resolve(); OUT=ROOT/'posts'/DATE; OUT.mkdir(parents=True,exist_ok=True)
B=ROOT/'_build'/'html'; B.mkdir(parents=True,exist_ok=True)
FONTS="""@font-face{font-family:"Playfair Display";font-weight:700;src:url(../../posts/assets/fonts/playfair-display-latin-700-normal.woff2)}
@font-face{font-family:"Playfair Display";font-weight:800;src:url(../../posts/assets/fonts/playfair-display-latin-800-normal.woff2)}
@font-face{font-family:"Playfair Display";font-weight:900;src:url(../../posts/assets/fonts/playfair-display-latin-900-normal.woff2)}
""" + "".join('@font-face{font-family:Inter;font-weight:%d;src:url(../../posts/assets/fonts/inter-latin-%d-normal.woff2)}\n'%(w,w) for w in (400,500,600,700,800))
def hl(t,cls="g"):
    t=html.escape(t); return re.sub(r'\*(\S+(?:\s\S+)?)', lambda m:'<em class="%s">%s</em>'%(cls,m.group(1)) if False else '<em class="g">%s</em>'%m.group(1), t,count=0) if '*' in t else t
def hl1(t):  # *word highlights one word (or *two words via **? keep: word after *)
    t=html.escape(t); return re.sub(r'\*(\S+)', r'<em class="g">\1</em>', t)
def css(theme,H):
    dark=theme=="dark"
    bg="linear-gradient(135deg,#032b38 0%,#02495f 42%,#00784e 100%)" if dark else "#ffffff"
    return FONTS+f"""
:root{{--teal:#032b38;--teal2:#04566b;--gold:#fac951;--navy:#082035}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:1080px;height:{H}px;overflow:hidden}}
body{{background:{bg};font-family:Inter,sans-serif;color:{'#fff' if dark else '#032b38'};position:relative}}
{'' if dark else 'body::before{content:"";position:absolute;left:0;right:0;top:0;height:14px;background:linear-gradient(90deg,#02495f,#00784e,#6ebe28);z-index:5}'}
.header{{position:absolute;left:80px;right:80px;top:70px;display:flex;align-items:center;justify-content:space-between}}
.mark{{font-weight:800;letter-spacing:.2em;font-size:30px}}
.pill{{background:var(--gold);color:var(--teal);font-weight:800;letter-spacing:.16em;font-size:26px;padding:16px 30px;border-radius:40px}}
.loc{{position:absolute;left:80px;top:200px;font-weight:800;letter-spacing:.22em;font-size:26px;color:{'var(--gold)' if dark else '#8a6a00'}}}
.g{{font-style:normal;color:{'var(--gold)' if dark else '#b07a00'}}}
h1{{position:absolute;left:80px;width:920px;font-family:"Playfair Display";font-weight:900;line-height:1.08}}
.rule{{position:absolute;left:80px;right:80px;height:5px;background:var(--gold)}}
.f1{{position:absolute;left:80px;font-weight:700;font-size:30px;white-space:nowrap}}
.f1 em{{font-style:normal;margin-left:34px}}
.f2{{position:absolute;left:80px;font-weight:700;font-size:30px;white-space:nowrap}}
.fine{{position:absolute;left:80px;font-size:22px;line-height:1.35;color:{'#cfe3e6' if dark else '#3d5a63'}}}
.wedge{{position:absolute;right:0;background:linear-gradient(160deg,var(--gold) 0%,#d9a21b 100%);clip-path:polygon(34% 0,100% 0,100% 100%,0 100%)}}
.brand{{position:absolute;object-fit:cover;object-position:50% 25%;border-radius:24px;border:6px solid var(--gold);box-shadow:0 14px 30px rgba(3,43,56,.35)}}
.b{{position:absolute;left:80px;border-left:8px solid var(--gold);padding-left:26px;font-weight:700;line-height:1.18}}
.ring{{position:absolute;right:70px;width:400px;height:400px;border-radius:50%;background:var(--gold)}}
.logo{{position:absolute;right:82px;width:376px;height:376px;border-radius:50%;filter:drop-shadow(0 8px 18px rgba(3,43,56,.28))}}
.step{{position:absolute;left:80px;font-weight:800;letter-spacing:.14em;font-size:34px;color:{'var(--gold)' if dark else '#b07a00'}}}
.txt{{position:absolute;left:80px;width:920px;font-weight:800;line-height:1.14}}
.big{{position:absolute;left:80px;font-family:"Playfair Display";font-weight:900;color:{'var(--gold)' if dark else '#b07a00'}}}
.sub{{position:absolute;left:80px;width:920px;font-weight:600;font-size:36px;line-height:1.25}}
.kick{{position:absolute;left:80px;background:var(--gold);color:var(--teal);font-weight:800;letter-spacing:.12em;font-size:34px;padding:16px 30px;border-radius:14px;transform:rotate(-2deg)}}
.card{{position:absolute;left:80px;width:620px;border:2px solid {'#0f7d8a' if dark else '#cfe6e1'};background:{'#04566b' if dark else '#fff'};border-radius:26px;padding:24px 30px;font-weight:700;font-size:34px;line-height:1.2}}
"""
def footer(H,rule,f1,f2):
    return f'<div class="rule" style="top:{rule}px"></div><div class="f1" style="top:{f1}px">Krishna Rander · Realtor®<em>905-452-4298</em></div><div class="f2" style="top:{f2}px">PROPERTY.CA INC., Brokerage</div>'
def head(pill,area): return f'<div class="header"><div class="mark">KEYS WITH KRISHNA</div><div class="pill">{html.escape(pill)}</div></div><div class="loc">{html.escape(area)}</div>'
def static_page(piece,H):  # feed(1350) / story(1920) with photo card
    story=H==1920
    wt,wh,bt=(1000,700,1065) if story else (520,640,590)
    bh,bw=(620,475) if story else (570,440)
    rule,f1,f2=(1760,1784,1838) if story else (1190,1214,1268)
    h1top=290 if story else 244
    fs=100 if story else 84
    bfs=38 if story else 30; bwid=380 if story else 440
    items="".join(f'<div class="b" style="position:static;font-size:{bfs}px;width:{bwid+34}px">{html.escape(t)}</div>' for t in piece['bullets'])
    bul=f'<div style="position:absolute;left:80px;top:{880 if story else 580}px;display:flex;flex-direction:column;gap:{26 if story else 18}px">{items}</div>'
    finetop=(rule-110) if story else (rule-85)
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{css(piece['theme'],H)}
h1{{top:{h1top}px;font-size:{fs}px}}.wedge{{top:{wt}px;width:{ 600 if story else 500}px;height:{wh}px}}
.brand{{right:36px;top:{bt}px;height:{bh}px;width:{bw}px}}.fine{{top:{finetop}px;width:{430 if story else 440}px}}
</style></head><body><div class="wedge"></div><img class="brand" src="../../posts/assets/krishna/photos/{piece['photo']}">
{head(piece['pill'],piece['area'])}<h1>{hl1(piece['h1'])}</h1>{bul}<div class="fine">{html.escape(piece['fine'])}</div>{footer(H,rule,f1,f2)}</body></html>"""
def reel_page(r,sc):
    H=1920; k=sc['kind']; th=r['theme']; body=""
    ring='<div class="ring" style="top:1240px"></div><img class="logo" style="top:1252px" src="../../posts/assets/logo-640.png">'
    if k=='hook':
        body=f'<div class="kick" style="top:300px">{html.escape(sc["kick"])}</div><h1 style="top:420px;font-size:128px">{hl1(sc["text"])}</h1>'
    elif k=='point':
        body=f'<div class="step" style="top:300px">STEP {sc["n"]} OF {sc["of"]} · {html.escape(sc["short"].upper())}</div><div class="txt" style="top:380px;font-size:70px;width:760px">{html.escape(sc["text"])}</div>'+(f'<div class="fine" style="top:1080px;width:760px">{html.escape(sc["note"])}</div>' if sc.get("note") else '')
        if sc['of']==1: body=body.replace(f'STEP 1 OF 1 · ','')
    elif k=='news':
        body=f'<div class="kick" style="top:300px">{html.escape(sc["source"].upper())} · {html.escape(sc["date"].upper())}</div><div class="txt" style="top:440px;font-size:76px;width:900px">{html.escape(sc["text"])}</div>'
        ring=''
    elif k=='calc':
        body=f'<div class="step" style="top:300px">STEP {sc["n"]} OF {sc["of"]}</div><div class="txt" style="top:380px;font-size:62px">{html.escape(sc["text"])}</div><div class="big" style="top:640px;font-size:170px">{html.escape(sc["value"])}</div><div class="sub" style="top:930px">{html.escape(sc["formula"])}</div><div class="sub" style="top:1020px;font-weight:800">Running total: {html.escape(sc["running"])}</div>'
    elif k=='total':
        body=f'<div class="txt" style="top:330px;font-size:58px">{html.escape(sc["text"])}</div><div class="big" style="top:520px;font-size:190px">{html.escape(sc["value"])}</div><div class="sub" style="top:800px;font-size:38px">{html.escape(sc["sub"])}</div><div class="fine" style="top:1000px;width:920px;font-size:26px">{html.escape(sc["note"])}</div>'
        ring=''
    elif k=='cta':
        body=f'<div class="txt" style="top:330px;font-size:84px;font-family:Playfair Display;font-weight:900">{hl1(sc["text"])}</div><div class="card" style="top:760px">&#9825; Like &nbsp;&nbsp; &#128172; Comment &nbsp;&nbsp; &#10148; Share</div><div class="sub" style="top:930px;font-weight:800;font-size:44px">Call 905-452-4298</div><div class="fine" style="top:1090px;width:620px">{html.escape(sc["fine"])}</div>'
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{css(th,H)}</style></head><body>{head(r['tag'],r['area'])}{body}{ring}{footer(H,1760,1784,1838)}</body></html>"""
def precon_page(p):
    t=open('templates/precon-photo-headshot-dark.html').read().replace('../posts/','../../posts/')
    R=[('p004.jpg',p['photo']),('BOWMANVILLE (CLARINGTON)',p['area']),('<h1>Ravine Mills</h1>','<h1 style="font-size:76px">Poet &amp; Perth</h1>'),
       ('by Camcos Living · Freehold townhomes','by Reid\'s Heritage Homes · Urban bungalow towns'),
       ('posts/assets/precon/PROJECT-1.jpg','posts/assets/precon/illustration-bungalow.svg'),
       ("Artist's concept. Actual product may vary.","Illustration only. Not the actual home."),
       ('<b style="font-size:48px">$642,689</b><span>from price (HST included) · Occupancy: Summer 2027</span>','<b style="font-size:48px">$389,900</b><span>from price · Occupancy: Spring 2028 (confirm with builder)</span>'),
       ('From price per builder price list dated Jul 28, 2026. Occupancy is an estimate.','From price per builder price lists dated Aug 31 and Sep 8, 2026. Occupancy per price list: confirm with builder.')]
    for a_,b_ in R:
        assert a_ in t,a_; t=t.replace(a_,b_)
    return t
def words(s): return len(re.sub(r'\*','',s).split())
def hold(n): return max(3.5,min(6.0,2+0.25*n))
shots=[]  # (html,out,w,h)
sched=[]
for r in REELS:
    rid=f"d{DATE.replace('-','')}-{r['id']}"; fd=OUT/f"{rid}-frames"; fd.mkdir(exist_ok=True)
    scenes=[dict(kind='hook',text=r['hook'],kick=r['kick'],prop=r['hprop'])]; frames=[dict(say=r['hsay'],min=2.0)]
    if r.get('clip'): scenes[0]['clip']=r['clip']
    if r.get('news'):
        nw=r['news']; scenes.append(dict(kind='news',source=nw[0],date=nw[1],text=nw[2])); frames.append(dict(say=nw[3],min=4.5))
    if 'calc' in r:
        n=len(r['calc'])
        for i,(t,v,f,run,prop,say) in enumerate(r['calc'],1):
            scenes.append(dict(kind='calc',n=i,of=n,prop=prop,text=t,value=v,formula=f,running=run)); frames.append(dict(say=say,min=4.5))
        t=r['total']; scenes.append(dict(kind='total',text=t[0],value=t[1],sub=t[2],note=t[3])); frames.append(dict(say=t[4],min=4.5))
    else:
        n=len(r['pts'])
        for i,pt in enumerate(r['pts'],1):
            short,prop,text,say=pt[:4]
            scenes.append(dict(kind='point',n=i,of=n,prop=prop,text=text,short=short,**({'note':pt[4]} if len(pt)>4 else {}))); frames.append(dict(say=say,min=round(hold(words(text)),2)))
    scenes.append(dict(kind='cta',text=r['cta'],fine=r['fine'])); frames.append(dict(say=r['csay'],min=4.5))
    for i,sc in enumerate(scenes,1):
        pg=B/f"{rid}-f{i:02d}.html"; pg.write_text(reel_page(r,sc)); shots.append((pg,fd/f"f{i:02d}.png",1080,1920))
        frames[i-1]['img']=f"posts/{DATE}/{rid}-frames/f{i:02d}.png"
    r['_scenes']=scenes; r['_frames']=[dict(img=f['img'],say=f['say'],min=f['min']) for f in frames]; r['_rid']=rid
for grp,H in ((FEEDS,1350),(STORIES,1920)):
    for p in grp:
        rid=f"d{DATE.replace('-','')}-{p['id']}"; pg=B/f"{rid}.html"
        if p.get('precon'): pg.write_text(precon_page(p))
        else: pg.write_text(static_page(p,H))
        shots.append((pg,OUT/f"{rid}.png",1080,H)); p['_rid']=rid
bad=0
with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path="/opt/pw-browsers/chromium") if pathlib.Path("/opt/pw-browsers/chromium").exists() else pw.chromium.launch()
    for src,out,w,h in shots:
        pg=b.new_page(viewport={"width":w,"height":h}); pg.goto(src.as_uri()); pg.wait_for_load_state("networkidle"); pg.evaluate("document.fonts.ready")
        over=pg.evaluate("""()=>{const bad=[];document.querySelectorAll('body *').forEach(e=>{const r=e.getBoundingClientRect();if(['wedge','ring','brand','logo'].some(c=>e.classList.contains(c)))return;if(r.right>1081||r.bottom>%d+1||r.left<-1)bad.push((e.className||e.tagName)+':'+e.textContent.slice(0,20))});
        document.querySelectorAll('.b,.txt,.sub,.fine,h1,.big,.card').forEach(e=>{if(e.scrollWidth>e.clientWidth+2&&getComputedStyle(e).whiteSpace==='nowrap')bad.push('wide:'+e.className)});return bad}"""%h)
        pg.screenshot(path=str(out)); pg.close()
        if over: print("OVERFLOW",out.name,over); bad+=1
    b.close()
print("rendered",len(shots),"bad",bad)
import pickle; pickle.dump((REELS,FEEDS,STORIES),open('_build/state.pkl','wb'))
