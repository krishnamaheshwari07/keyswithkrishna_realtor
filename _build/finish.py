import pickle,sys,json,subprocess,pathlib,datetime
sys.path.insert(0,'_build')
from content import *
REELS,FEEDS,STORIES=pickle.load(open('_build/state.pkl','rb'))
OUT=pathlib.Path('posts')/DATE
def sh(c): subprocess.check_call(c)
items=[]
def mk(base,**kw):
    d=dict(id=base['_rid'],type=kw.pop('type'),theme=base['theme'],approved=True,status="pending",
      publish_at=f"{DATE}T{base['time']}:00-05:00",hook_rule="tension-v3");d.update(kw);return d
for r in REELS:
    rid=r['_rid']; lst=OUT/f"{rid}-list.txt"; fr=r['_frames']
    lines=[]
    for f in fr: lines.append(f"file '{pathlib.Path(f['img']).name}'\nduration {f['min']}")
    lines.append(f"file '{pathlib.Path(fr[-1]['img']).name}'")
    p=OUT/f"{rid}-frames"/"list.txt"; p.write_text("\n".join(lines))
    silent=f"/tmp/{rid}-silent.mp4"
    sh(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",str(p),"-vf","scale=1080:1920,format=yuv420p","-r","30","-c:v","libx264","-pix_fmt","yuv420p",silent])
    p.unlink()
    out=OUT/f"{rid}.mp4"
    sh(["python3","scripts/add_music.py","reel",silent,str(out),rid]+(["--mood=tense"] if r.get('mood') else []))
    cap=f"{r['cap']}\n\n{SIGN}\n\n{r['tags']}"
    m=dict(theme=r['theme'],tag=r['tag'],area=r['area'],scenes=r['_scenes'])
    it=mk(r,type="reel",caption=cap,media_url=RAW+f"{rid}.mp4",frames=fr,vo_pending=True,motion=m,brand_corner="logo",
      trigger=r['trigger'],share_reason=r['share'],format=r['fmt'],hook_pattern=r['pattern'],audience=r['aud'])
    if r.get('series'): it['series']=r['series']
    if r.get('math'): it['math_level']=r['math']
    if r.get('trial'): it['trial']=True
    if r.get('mood'): it['music_mood']=r['mood']
    if r.get('extra'): it.update(r['extra'])
    items.append(it)
for grp,typ in ((FEEDS,'feed'),(STORIES,'story')):
    for p in grp:
        rid=p['_rid']; media=f"{rid}.png"
        if typ=='story':
            sh(["python3","scripts/add_music.py","story",str(OUT/f"{rid}.png"),str(OUT/f"{rid}.mp4"),rid,"8"]); media=f"{rid}.mp4"
        items.append(mk(p,type=typ,caption=f"{p['cap']}\n\n{SIGN}\n\n{p['tags']}",media_url=RAW+media,brand_corner="photo",photo=p["photo"],
          format=p['fmt'],hook_pattern=p['pattern'],audience="buyer"))
items.sort(key=lambda i:i['publish_at'])
json.dump(items,open(OUT/'schedule.json','w'),indent=1,ensure_ascii=False)
u=json.load(open('data/photo-usage.json'))
json.dump(u,open('data/photo-usage.json','w'),indent=1)
print(len(items))
