import os,time,random,sqlite3,logging
from pathlib import Path
from datetime import datetime,timezone
import requests

VIDEO_DIR=Path("/app/videos"); DB_PATH=Path("/app/data/reels.db")
PAGE_ID=os.environ["FB_PAGE_ID"]; TOKEN=os.environ["FB_PAGE_ACCESS_TOKEN"]
GRAPH_VERSION=os.environ["GRAPH_API_VERSION"].strip()
INTERVAL=int(os.environ.get("POST_INTERVAL_MINUTES","360"))*60
REPEAT=os.environ.get("REPEAT","true").lower()=="true"
RANDOM_ORDER=os.environ.get("RANDOM_ORDER","false").lower()=="true"
TITLE=os.environ.get("DEFAULT_TITLE","").strip()
DESCRIPTION=os.environ.get("DEFAULT_DESCRIPTION","").strip()
SCAN=int(os.environ.get("SCAN_INTERVAL_SECONDS","30"))
EXT={".mp4",".mov",".m4v",".avi",".mkv",".mpeg",".mpg"}
GRAPH=f"https://graph.facebook.com/{GRAPH_VERSION}"
logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")

def db():
    DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS videos(
      id INTEGER PRIMARY KEY, filename TEXT UNIQUE, status TEXT DEFAULT 'queued',
      last_posted_at TEXT,last_video_id TEXT,attempts INTEGER DEFAULT 0,error TEXT)""")
    c.commit(); return c

def scan():
    c=db()
    for p in VIDEO_DIR.iterdir():
        if p.is_file() and p.suffix.lower() in EXT:
            c.execute("INSERT OR IGNORE INTO videos(filename) VALUES(?)",(p.name,))
    c.commit(); c.close()

def next_video():
    c=db(); rows=c.execute("SELECT filename FROM videos WHERE status='queued' ORDER BY id").fetchall(); c.close()
    if not rows:return None
    names=[x[0] for x in rows]
    if RANDOM_ORDER: random.shuffle(names)
    p=VIDEO_DIR/names[0]
    return p if p.exists() else None

def reset():
    c=db(); c.execute("UPDATE videos SET status='queued',error=NULL WHERE status='posted'"); c.commit(); c.close()

def status(name,s,err=None,vid=None):
    c=db()
    if s=="uploading":
        c.execute("UPDATE videos SET status='uploading',attempts=attempts+1,error=NULL WHERE filename=?",(name,))
    elif s=="posted":
        c.execute("UPDATE videos SET status='posted',last_posted_at=?,last_video_id=?,error=NULL WHERE filename=?",(datetime.now(timezone.utc).isoformat(),vid,name))
    else:
        c.execute("UPDATE videos SET status='queued',error=? WHERE filename=?",(str(err)[:4000],name))
    c.commit(); c.close()

def api_error(r):
    try: b=r.json()
    except: b=r.text
    return f"Meta API {r.status_code}: {b}"

def publish(path):
    r=requests.post(f"{GRAPH}/me/video_reels",params={"access_token":TOKEN,"upload_phase":"start"},timeout=120)
    if not r.ok: raise RuntimeError(api_error(r))
    x=r.json(); vid=x["video_id"]; url=x["upload_url"]
    with path.open("rb") as f:
        r=requests.post(url,headers={"Authorization":f"OAuth {TOKEN}","offset":"0","file_size":str(path.stat().st_size),"Content-Type":"application/octet-stream"},data=f,timeout=3600)
    if not r.ok: raise RuntimeError(api_error(r))
    params={"access_token":TOKEN,"video_id":vid,"upload_phase":"finish","video_state":"PUBLISHED"}
    if TITLE: params["title"]=TITLE
    if DESCRIPTION: params["description"]=DESCRIPTION
    r=requests.post(f"{GRAPH}/me/video_reels",params=params,timeout=180)
    if not r.ok: raise RuntimeError(api_error(r))
    return vid

def main():
    logging.info("Facebook Page Reels bot started; Page=%s interval=%s min",PAGE_ID,INTERVAL//60)
    last=0
    while True:
        try:
            scan()
            if time.time()-last>=INTERVAL:
                p=next_video()
                if p is None and REPEAT:
                    reset(); p=next_video()
                if p:
                    logging.info("Publishing %s",p.name); status(p.name,"uploading")
                    try:
                        vid=publish(p); status(p.name,"posted",vid=vid)
                        logging.info("Published %s as %s",p.name,vid)
                    except Exception as e:
                        status(p.name,"queued",err=e); logging.exception("Publish failed")
                    last=time.time()
        except Exception: logging.exception("Loop error")
        time.sleep(SCAN)

if __name__=="__main__": main()
