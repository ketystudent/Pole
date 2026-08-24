import json, math, collections, re, unicodedata, os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML=os.path.join(ROOT,"BASE DE DADOS","Projeto_Digital_Ante.html")
with open(HTML,encoding="utf-8") as f:
    for line in f:
        if line.startswith("const D="):
            D=json.loads(line[len("const D="):].rstrip().rstrip(";")); break

todos=D["postes"]; util=[p for p in todos if p["poste_utilizado"]]
LAT0=sum(p["lat"] for p in util)/len(util)
MPD=111320.0
def xy(p):
    return (p["lon"]*MPD*math.cos(math.radians(LAT0)), p["lat"]*MPD)
for p in todos: p["_xy"]=xy(p)

# criterion computation --------------------------------------------------
real=[p for p in todos if p.get("poste_numero") is not None]
CELL=30.0
grid=collections.defaultdict(list)
for p in real: grid[(int(p["_xy"][0]//CELL),int(p["_xy"][1]//CELL))].append(p)
def prox_neighbors(p,R):
    cx,cy=int(p["_xy"][0]//CELL),int(p["_xy"][1]//CELL); out=[]
    for dy in(-1,0,1):
        for dx in(-1,0,1):
            for q in grid.get((cx+dx,cy+dy),[]):
                if q is p: continue
                d=math.hypot(p["_xy"][0]-q["_xy"][0],p["_xy"][1]-q["_xy"][1])
                if d<=R: out.append((d,q))
    return out

PREF=r"^(RUA|AVENIDA|AV|R|PRACA|ALAMEDA|TRAVESSA|ESTRADA|RODOVIA|VIA|LARGO|BECO|ACESSO)\b\.?\s*"
def base(p):
    e=(p.get("endereco_lote_mais_proximo") or "").split(",")[0]; e=re.sub(r"\s+\d+$","",e)
    s=unicodedata.normalize("NFKD",e).encode("ascii","ignore").decode().upper()
    s=re.sub(r"[^A-Z0-9 ]"," ",s); s=re.sub(PREF,"",s); return re.sub(r"\s+"," ",s).strip()
for p in todos: p["_rua"]=base(p)
rgrid=collections.defaultdict(list)
for p in todos:
    if p["_rua"]: rgrid[(int(p["_xy"][0]//CELL),int(p["_xy"][1]//CELL))].append(p)
def cruzamentos(R=40):
    best={}
    for (cx,cy),bucket in rgrid.items():
        cand=[]
        for dy in(-1,0,1):
            for dx in(-1,0,1): cand+=rgrid.get((cx+dx,cy+dy),[])
        for a in bucket:
            for b in cand:
                if a["_rua"]>=b["_rua"]: continue
                d=math.hypot(a["_xy"][0]-b["_xy"][0],a["_xy"][1]-b["_xy"][1])
                if d>R: continue
                k=(a["_rua"],b["_rua"])
                if k not in best or d<best[k][0]: best[k]=(d,a,b)
    return best
cpts=[((a["_xy"][0]+b["_xy"][0])/2,(a["_xy"][1]+b["_xy"][1])/2) for d,a,b in cruzamentos(40).values()]
cg=collections.defaultdict(list)
for q in cpts: cg[(int(q[0]//CELL),int(q[1]//CELL))].append(q)
def near_crossing(p,R):
    cx,cy=int(p["_xy"][0]//CELL),int(p["_xy"][1]//CELL)
    for dy in(-1,0,1):
        for dx in(-1,0,1):
            for q in cg.get((cx+dx,cy+dy),[]):
                if math.hypot(p["_xy"][0]-q[0],p["_xy"][1]-q[1])<=R: return True
    return False

COMBOS=[(8,20),(10,20),(12,25),(15,25)]
matches={}
clustersize={}
for RPROX,RCRUZ in COMBOS:
    key=f"{RPROX}_{RCRUZ}"
    ids=[]
    for p in util:
        vv=prox_neighbors(p,RPROX)
        if vv and near_crossing(p,RCRUZ):
            ids.append(p["cod_id"])
            clustersize[(key,p["cod_id"])]=len(vv)+1
    matches[key]=ids

# already processed --------------------------------------------------
d=os.path.join(ROOT,"POSTES UTILIZADOS")
proc=set(); rev=set()
for root,_,fs in os.walk(d):
    for f in fs:
        m=re.search(r"COD ID_(\d+)",f)
        if not m: continue
        (rev if " - REVISAO" in root else proc).add(m.group(1))

# output ---------------------------------------------------------------
util_by_id={p["cod_id"]:p for p in util}
out={
    "center": [round(LAT0,6)],
    "edges": [],
    "poles": [],
    "combos": [{"prox":a,"cruz":b,"key":f"{a}_{b}","ids":matches[f"{a}_{b}"]} for a,b in COMBOS],
    "processed": sorted(proc),
    "review": sorted(rev),
}
for c in ("sec","prim"):
    tipo = "sec" if c=="sec" else "prim"
    for e in D[c]:
        (lo1,la1),(lo2,la2) = e["coords"][0], e["coords"][-1]
        x1=lo1*MPD*math.cos(math.radians(LAT0)); y1=la1*MPD
        x2=lo2*MPD*math.cos(math.radians(LAT0)); y2=la2*MPD
        out["edges"].append([round(x1,1),round(y1,1),round(x2,1),round(y2,1),tipo])
for p in util:
    out["poles"].append([
        p["cod_id"], round(p["_xy"][0],1), round(p["_xy"][1],1),
        p.get("endereco_lote_mais_proximo","") or "",
        round(p["lat"],7), round(p["lon"],7)
    ])
print("edges:",len(out["edges"]),"poles:",len(out["poles"]))
for a,b in COMBOS: print(f"{a}/{b}:", len(matches[f'{a}_{b}']))
json.dump(out, open("mapdata.json","w",encoding="utf-8"), ensure_ascii=False, separators=(",",":"))
import os as _o
print("json bytes:", _o.path.getsize("mapdata.json"))
