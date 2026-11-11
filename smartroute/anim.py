"""Tampilan 'control room' 3D pergerakan truk tangki (MapLibre GL + deck.gl).

* Peta gelap penuh, dapat dimiringkan (pitch) dan diputar (bearing), rotasi otomatis opsional.
* Jejak bercahaya (TripsLayer), kolom 3D SPBU (tinggi = volume permintaan, warna = status layanan),
  ikon truk tangki SVG buatan sendiri (tanpa logo/merek dagang) yang ukurannya mengikuti kapasitas KL.
* Panel HUD: jam & kendali waktu, KPI langsung, kartu status setiap truk (spidometer, muatan), dan log kejadian.
"""
from __future__ import annotations

import base64
import json
from typing import Dict, List

UNIT_COLORS = ["#ff4d4f", "#36cfc9", "#ffc53d", "#9254de", "#73d13d", "#40a9ff", "#ff85c0", "#ffa940", "#bae637", "#d3adf7"]


def truck_svg(kl: float, cab: str, flip: bool = False) -> str:
    """SVG truk tangki menghadap kanan (flip=True: menghadap kiri). Ukuran mengikuti kapasitas KL."""
    if kl <= 6:
        L, axles, semi = 34, [10, 36], False
    elif kl <= 8:
        L, axles, semi = 42, [10, 44], False
    elif kl <= 16:
        L, axles, semi = 58, [10, 50, 60], False
    else:
        L, axles, semi = 78, [12, 22, 66, 76, 86], True
    W = L + 26
    cab_x = L + 6 if semi else L + 4
    g = [f'<rect x="1" y="21" width="{W - 3}" height="3" fill="#333"/>']
    if semi:
        g.append(f'<rect x="{L - 2}" y="19" width="10" height="3" fill="#555"/>')
    g.append(f'<rect x="2" y="4" width="{L}" height="16" rx="7" fill="#fdfdfd" stroke="#444" stroke-width="0.8"/>')
    g.append(f'<rect x="5" y="6.5" width="{L - 6}" height="2.6" fill="#e31e24"/>')
    g.append(f'<rect x="5" y="15" width="{L - 6}" height="2.6" fill="#0a5ea8"/>')
    g.append(f'<rect x="{2 + L * 0.45}" y="9.6" width="5" height="4.8" fill="#64b33b"/>')
    if not flip:
        g.append(f'<text x="{2 + L * 0.2}" y="14" font-size="5.5" font-family="Arial" font-weight="700" fill="#0a5ea8">BBM</text>')
    g.append(f'<rect x="{2 + L * 0.3}" y="2.5" width="4" height="2" fill="#777"/><rect x="{2 + L * 0.65}" y="2.5" width="4" height="2" fill="#777"/>')
    g.append(f'<path d="M{cab_x} 21 L{cab_x} 8 Q{cab_x} 6 {cab_x + 2} 6 L{cab_x + 12} 6 L{cab_x + 18} 13 L{cab_x + 18} 21 Z" '
             f'fill="{cab}" stroke="#111" stroke-width="0.8"/>')
    g.append(f'<path d="M{cab_x + 11} 8 L{cab_x + 16} 13 L{cab_x + 11} 13 Z" fill="#cfe8ff"/>')
    for ax in axles + [cab_x + 12]:
        if ax < W - 2:
            g.append(f'<circle cx="{ax}" cy="24" r="3.6" fill="#111"/><circle cx="{ax}" cy="24" r="1.4" fill="#aaa"/>')
    body = "".join(g)
    if flip:
        body = f'<g transform="translate({W},0) scale(-1,1)">{body}</g>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="30" viewBox="0 0 {W} 30">{body}</svg>'


def _data_url(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def build_html(sim: Dict, stations: List[Dict], depot: Dict, height: int = 860, title: str = "SMARTROUTE-BBM") -> str:
    units = []
    for k, u in enumerate(sim["units"]):
        col = UNIT_COLORS[k % len(UNIT_COLORS)]
        units.append(dict(u, color=col, svg=truck_svg(u["kapasitas"], col),
                          icon_r=_data_url(truck_svg(u["kapasitas"], col)),
                          icon_l=_data_url(truck_svg(u["kapasitas"], col, flip=True))))
    data = dict(units=units, stations=stations, depot=depot, t_end=sim["t_end"], start_h=sim["shift_start_h"],
                shift_len=sim["shift_len"], events=sim["events"], stops=sim["stops"], title=title)
    return _TEMPLATE.replace("__DATA__", json.dumps(data, separators=(",", ":"))).replace("__H__", str(height))


_TEMPLATE = r"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css">
<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<script src="https://unpkg.com/deck.gl@9.0.38/dist.min.js"></script>
<style>
html,body{margin:0;height:100%;background:#05080d;color:#dfe7f1;font:13px/1.35 "Inter",system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}
#root{position:relative;height:__H__px;border-radius:14px;overflow:hidden;background:#05080d;border:1px solid #13202e}
#map{position:absolute;inset:0}
.glass{position:absolute;background:rgba(8,16,26,.72);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
  border:1px solid rgba(64,169,255,.25);border-radius:12px;box-shadow:0 0 24px rgba(0,140,255,.12)}
.h{font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:#6fa8dc}
#top{left:12px;top:12px;padding:10px 14px;width:310px}
#clock{font:700 38px/1 "JetBrains Mono",ui-monospace,Menlo,Consolas,monospace;color:#e6f4ff;text-shadow:0 0 12px rgba(64,169,255,.6)}
#prog{height:4px;background:#13202e;border-radius:2px;margin:8px 0 6px;overflow:hidden}#prog i{display:block;height:100%;background:linear-gradient(90deg,#36cfc9,#40a9ff)}
#ctrl{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-top:6px}
button,select{font:inherit;font-size:12px;padding:4px 9px;border-radius:7px;border:1px solid #24405c;background:#0b1622;color:#dfe7f1;cursor:pointer}
button.on{background:#0f3a5f;border-color:#40a9ff;color:#fff}
button.go{background:#d4380d;border-color:#ff7a45;color:#fff}
input[type=range]{width:100%;accent-color:#40a9ff}
#kpi{left:12px;bottom:12px;display:flex;gap:8px;padding:8px}
.k{min-width:96px;padding:6px 10px;border-right:1px solid #13202e}.k:last-child{border-right:0}
.k b{display:block;font:700 20px/1.1 ui-monospace,Menlo,Consolas,monospace;color:#e6f4ff}
.k span{font-size:10px;color:#7c93ab;text-transform:uppercase;letter-spacing:.08em}
#fleet{right:12px;top:12px;width:300px;max-height:calc(100% - 200px);overflow:auto;padding:10px 12px}
.card{display:grid;grid-template-columns:62px 1fr;gap:4px 10px;padding:9px 0;border-bottom:1px solid #13202e;align-items:center}
.card:last-child{border-bottom:0}
.nm{font-weight:700;color:#fff}.sub{font-size:11px;color:#7c93ab}
.chip{display:inline-block;font-size:10px;padding:1px 7px;border-radius:9px;margin-top:2px}
.lbar{height:6px;background:#13202e;border-radius:3px;overflow:hidden;margin-top:4px}.lbar i{display:block;height:100%}
#log{right:56px;bottom:12px;width:300px;height:150px;overflow:hidden;padding:8px 12px}
#log .ln{font-size:11.5px;color:#a9bcd0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;padding:2px 0;border-bottom:1px dashed #102030}
#log .ln b{color:#fff}
#legend{left:334px;top:12px;padding:8px 12px;font-size:11px;color:#a9bcd0}
#legend .sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin:0 4px -1px 8px}
#err{position:absolute;inset:0;display:none;align-items:center;justify-content:center;color:#ffa39e;font-size:14px}
@media (max-width:900px){#fleet{width:220px}#log{display:none}#legend{display:none}#top{width:240px}#clock{font-size:28px}}
@media (max-width:620px){#fleet{display:none}#kpi{flex-wrap:wrap;right:12px}.k{min-width:70px}}
</style></head><body>
<div id="root"><div id="map"></div><div id="err">Peta 3D memerlukan WebGL dan koneksi ke unpkg.com / server.arcgisonline.com.</div>
 <div id="top" class="glass"><div class="h" id="ttl"></div><div id="clock">06:00</div>
  <div class="sub" id="tinfo"></div><div id="prog"><i></i></div>
  <input id="slider" type="range" min="0" step="0.5" value="0">
  <div id="ctrl"><button id="play" class="go">▶ Putar</button><button id="reset" title="Ulang">⟲</button>
   <select id="spd"><option value="2">×2 mnt/dtk</option><option value="5" selected>×5 mnt/dtk</option><option value="10">×10 mnt/dtk</option><option value="20">×20 mnt/dtk</option></select>
   <button id="v3d" class="on">3D</button><button id="rot">⟳ Rotasi</button><button id="fitb" title="Tampilkan seluruh wilayah">⤢</button><select id="follow"><option value="">Kamera bebas</option></select><select id="base"><option value="dark">Peta gelap</option><option value="sat">Satelit</option><option value="osm">OpenStreetMap</option></select></div>
 </div>
 <div id="legend" class="glass"><span class="h">SPBU</span><span class="sw" style="background:#5b6b7c"></span>menunggu
  <span class="sw" style="background:#ffa940"></span>bongkar<span class="sw" style="background:#52c41a"></span>terlayani
  <span class="h" style="margin-left:12px">Tinggi kolom</span> = volume KL</div>
 <div id="fleet" class="glass"><div class="h">Status armada</div><div id="cards"></div></div>
 <div id="kpi" class="glass"></div>
 <div id="log" class="glass"><div class="h">Log kejadian</div><div id="lines"></div></div>
</div>
<script>
const D=__DATA__;
document.getElementById('ttl').textContent=D.title+' · control room';
const startMin=D.start_h*60;
function hhmm(t){const m=Math.round(startMin+t);return String(Math.floor(m/60)%24).padStart(2,'0')+':'+String(m%60).padStart(2,'0')}
function hex(c,a){const n=parseInt(c.slice(1),16);return [n>>16&255,n>>8&255,n&255,a===undefined?255:a]}
const ST={0:['DI FT','#40a9ff'],1:['MENUJU SPBU','#36cfc9'],2:['BONGKAR','#ffa940'],3:['KEMBALI','#9254de'],9:['SELESAI','#52c41a'],8:['SIAGA','#5b6b7c']};
const T1=Math.ceil(D.t_end+10);const slider=document.getElementById('slider');slider.max=T1;
document.getElementById('tinfo').textContent='Shift '+hhmm(0)+'–'+hhmm(D.shift_len)+' · simulasi selesai '+hhmm(D.t_end);
const stopsBy={};D.stops.forEach(s=>{(stopsBy[s.spbu]=stopsBy[s.spbu]||[]).push(s)});
const totVol=D.stops.reduce((a,s)=>a+s.volume_kl,0);
const U=D.units.map(u=>Object.assign({},u,{path:u.frames.map(f=>[f[2],f[1]]),ts:u.frames.map(f=>f[0])}));
U.forEach(u=>{const o=document.createElement('option');o.value=u.unit;o.textContent='Ikuti '+u.unit;document.getElementById('follow').appendChild(o)});
function find(fr,t){let lo=0,hi=fr.length-1;if(t<=fr[0][0])return 0;if(t>=fr[hi][0])return hi;
 while(hi-lo>1){const m=(lo+hi)>>1;if(fr[m][0]<=t)lo=m;else hi=m}return lo}
function state(u,t){const fr=u.frames,i=find(fr,t),a=fr[i],b=fr[Math.min(i+1,fr.length-1)];
 const r=b[0]>a[0]?Math.min(1,Math.max(0,(t-a[0])/(b[0]-a[0]))):0;
 const lon=a[2]+(b[2]-a[2])*r,lat=a[1]+(b[1]-a[1])*r,load=a[5]+(b[5]-a[5])*r,km=a[6]+(b[6]-a[6])*r;
 const moving=t>=a[0]&&t<b[0]&&(b[1]!==a[1]||b[2]!==a[2]);
 let code=moving?b[3]:a[3];let txt='Siaga di FT';for(const s of u.spans){if(t>=s[0]&&t<s[1]){txt=s[2];break}}
 if(!moving&&code!==2&&txt.startsWith('Siaga'))code=8;
 if(t<fr[0][0]){code=8;txt='Belum berangkat'}if(t>=fr[fr.length-1][0]){code=9;txt='Semua ritase selesai'}
 if(txt.startsWith('Muat'))code=0;
 return {lon,lat,load,km,v:moving?b[4]:0,code,txt,west:moving&&b[2]<a[2]-1e-9}}
let map,is3d=true;try{
 map=new maplibregl.Map({container:'map',attributionControl:{compact:true},
  style:{version:8,sources:{
    dark:{type:'raster',tiles:['https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}'],tileSize:256,maxzoom:16,attribution:'Tiles © Esri — Esri, HERE, Garmin, © OpenStreetMap contributors'},
    darkref:{type:'raster',tiles:['https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}'],tileSize:256,maxzoom:16},
    sat:{type:'raster',tiles:['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],tileSize:256,maxzoom:18,attribution:'Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics'},
    osm:{type:'raster',tiles:['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],tileSize:256,maxzoom:19,attribution:'© OpenStreetMap contributors'}},
   layers:[{id:'bg',type:'background',paint:{'background-color':'#05080d'}},
    {id:'dark',type:'raster',source:'dark'},{id:'darkref',type:'raster',source:'darkref'},
    {id:'sat',type:'raster',source:'sat',layout:{visibility:'none'},paint:{'raster-brightness-max':0.75,'raster-saturation':-0.2}},
    {id:'osm',type:'raster',source:'osm',layout:{visibility:'none'},paint:{'raster-brightness-max':0.85}}]},
  center:[D.depot.lon,D.depot.lat],zoom:10,pitch:55,bearing:-18,maxPitch:75});
 map.addControl(new maplibregl.NavigationControl({visualizePitch:true}),'bottom-right');
 map.addControl(new maplibregl.FullscreenControl({container:document.getElementById('root')}),'bottom-right');
}catch(e){document.getElementById('err').style.display='flex';throw e}
const pts=[[D.depot.lon,D.depot.lat]].concat(D.stations.map(s=>[s.lon,s.lat]));
const bb=pts.reduce((b,p)=>[[Math.min(b[0][0],p[0]),Math.min(b[0][1],p[1])],[Math.max(b[1][0],p[0]),Math.max(b[1][1],p[1])]],[[999,999],[-999,-999]]);
let fitted=false;
function fit(){const r=document.getElementById('root');if(r.clientWidth<50||r.clientHeight<50)return;map.resize();
 if(map.getCanvas().clientWidth<50||document.visibilityState==='hidden')return;
 const w=r.clientWidth;map.fitBounds(bb,{padding:{top:90,bottom:110,left:Math.min(60,w*.05),right:w>900?330:40},pitch:is3d?55:0,bearing:is3d?-18:0,duration:0});fitted=true}
let moved=false;
new ResizeObserver(()=>{map.resize();if(!moved)fit()}).observe(document.getElementById('root'));
new IntersectionObserver(es=>{if(es.some(e=>e.isIntersecting)&&!moved)setTimeout(fit,60)}).observe(document.getElementById('root'));
['dragstart','rotatestart','pitchstart','wheel'].forEach(ev=>map.on(ev,e=>{if(e.originalEvent)moved=true}));
setInterval(()=>{if(!moved){const c=map.getCanvas();if(c.clientWidth>50&&map.getZoom()<7)fit()}},800);
const overlay=new deck.MapboxOverlay({interleaved:false,layers:[]});map.addControl(overlay);
const stInfo=D.stations.map(s=>{const st=stopsBy[s.id]||[];return Object.assign({},s,{vol:st.reduce((a,x)=>a+x.volume_kl,0),win:st.map(x=>[x.tiba_simulasi,x.tiba_simulasi+x.bongkar_menit])})});
function stColor(s,t){if(s.win.some(w=>t>=w[0]&&t<w[1]))return [255,169,64,235];if(s.win.length&&s.win.every(w=>t>=w[1]))return [82,196,26,230];return [91,107,124,200]}
let T=0,play=false,last=null,rot=false;
function layers(t,S){const pulse=0.5+0.5*Math.sin(performance.now()/300);
 return [
  new deck.PathLayer({id:'routes',data:U,getPath:d=>d.path,getColor:d=>hex(d.color,70),getWidth:3,widthUnits:'pixels',jointRounded:true,capRounded:true}),
  new deck.TripsLayer({id:'trails',data:U,getPath:d=>d.path,getTimestamps:d=>d.ts,getColor:d=>hex(d.color),widthMinPixels:5,
    fadeTrail:true,trailLength:35,currentTime:t,capRounded:true,jointRounded:true}),
  new deck.ColumnLayer({id:'spbu',data:stInfo,diskResolution:24,radius:260,extruded:true,pickable:true,
    getPosition:d=>[d.lon,d.lat],getElevation:d=>400+d.vol*450,getFillColor:d=>stColor(d,t),getLineColor:[255,255,255,80],
    updateTriggers:{getFillColor:[Math.floor(t)]},material:{ambient:0.6,diffuse:0.6}}),
  new deck.ColumnLayer({id:'depot',data:[D.depot],diskResolution:6,radius:520,extruded:true,getPosition:d=>[d.lon,d.lat],
    getElevation:5200,getFillColor:[64,169,255,200]}),
  new deck.TextLayer({id:'lbl',data:stInfo.concat([{id:'FT GELUMBANG',lon:D.depot.lon,lat:D.depot.lat,vol:11}]),getPosition:d=>[d.lon,d.lat,700+d.vol*450],
    getText:d=>d.id,getSize:d=>d.id.length>4?14:12,getColor:[230,244,255],fontWeight:700,getPixelOffset:[0,-14],
    billboard:true,outlineWidth:3,outlineColor:[5,8,13,255],fontSettings:{sdf:true}}),
  new deck.ScatterplotLayer({id:'halo',data:S,getPosition:d=>[d.s.lon,d.s.lat],radiusUnits:'pixels',
    getRadius:d=>d.s.code===2?16+8*pulse:12,getFillColor:d=>hex(ST[d.s.code][1],70),getLineColor:d=>hex(ST[d.s.code][1],220),
    stroked:true,lineWidthMinPixels:1.5,updateTriggers:{getRadius:[pulse],getFillColor:[t]}}),
  new deck.IconLayer({id:'trucks',data:S,pickable:true,getPosition:d=>[d.s.lon,d.s.lat],sizeUnits:'pixels',
    getIcon:d=>({url:d.s.west?d.u.icon_l:d.u.icon_r,id:d.u.unit+(d.s.west?'L':'R'),width:(d.u.kapasitas>16?104:d.u.kapasitas>8?84:d.u.kapasitas>6?68:60)*2,height:60,anchorY:52}),
    getSize:d=>d.u.kapasitas>16?34:d.u.kapasitas>8?30:d.u.kapasitas>6?26:23,billboard:true,
    updateTriggers:{getIcon:[t]}})
 ]}
function gauge(v,max,col){const a=Math.min(1,v/max)*Math.PI;const x=30-24*Math.cos(a),y=30-24*Math.sin(a);
 return `<svg width="60" height="36" viewBox="0 0 60 36"><path d="M6 30 A24 24 0 0 1 54 30" stroke="#13202e" stroke-width="6" fill="none"/>
 <path d="M6 30 A24 24 0 0 1 ${x.toFixed(1)} ${y.toFixed(1)}" stroke="${col}" stroke-width="6" fill="none" stroke-linecap="round"/>
 <text x="30" y="29" text-anchor="middle" font-size="12" font-weight="700" fill="#e6f4ff" font-family="monospace">${Math.round(v)}</text>
 <text x="30" y="36" text-anchor="middle" font-size="6" fill="#7c93ab">km/jam</text></svg>`}
function render(){
 const S=U.map(u=>({u,s:state(u,T)}));
 overlay.setProps({layers:layers(T,S),getTooltip:({object})=>object&&(object.u?`${object.u.unit} · ${object.u.kapasitas} KL\n${object.s.txt}`:
   object.vol!==undefined&&object.win?`${object.id} · ${object.vol.toFixed(2)} KL`:null)});
 document.getElementById('clock').textContent=hhmm(T);slider.value=T;
 document.querySelector('#prog i').style.width=Math.min(100,T/D.shift_len*100)+'%';
 document.getElementById('cards').innerHTML=S.map(({u,s})=>{const c=ST[s.code];const pct=Math.max(0,Math.min(100,s.load/u.kapasitas*100));
  return `<div class="card"><div>${gauge(s.v,80,u.color)}</div><div><span class="nm" style="color:${u.color}">${u.unit}</span>
   <span class="sub"> · tipe ${u.tipe} · ${u.kapasitas} KL${u.assigned?'':' · ⚠ tanpa unit'}</span><br>
   <span class="chip" style="background:${c[1]}22;color:${c[1]};border:1px solid ${c[1]}66">${c[0]}</span>
   <div class="sub" style="margin-top:3px">${s.txt}</div>
   <div class="lbar"><i style="width:${pct}%;background:linear-gradient(90deg,#0a5ea8,#36cfc9)"></i></div>
   <div class="sub">muatan ${s.load.toFixed(1)} KL · ${s.km.toFixed(1)} km</div></div></div>`}).join('');
 const served=stInfo.filter(s=>s.win.length&&s.win.every(w=>T>=w[1])).length;
 let deliv=0;D.stops.forEach(x=>{const e=x.tiba_simulasi+x.bongkar_menit;if(T>=e)deliv+=x.volume_kl;else if(T>x.tiba_simulasi)deliv+=x.volume_kl*(T-x.tiba_simulasi)/x.bongkar_menit});
 const km=S.reduce((a,x)=>a+x.s.km,0),act=S.filter(x=>[0,1,2,3].includes(x.s.code)).length,mv=S.filter(x=>x.s.v>0);
 const k=[[served+'/'+D.stations.length,'SPBU terlayani'],[deliv.toFixed(1)+' KL','terkirim / '+totVol.toFixed(1)],[km.toFixed(0)+' km','jarak tempuh'],
  [act+'/'+U.length,'truk aktif'],[mv.length?(mv.reduce((a,x)=>a+x.s.v,0)/mv.length).toFixed(0)+' km/j':'–','rerata kecepatan'],[hhmm(D.t_end),'estimasi selesai']];
 document.getElementById('kpi').innerHTML=k.map(x=>`<div class="k"><b>${x[0]}</b><span>${x[1]}</span></div>`).join('');
 document.getElementById('lines').innerHTML=D.events.filter(e=>e.t<=T).slice(-7).reverse()
   .map(e=>`<div class="ln">${hhmm(e.t)} · <b>${e.unit}</b> ${e.ev} @ ${e.tempat}</div>`).join('');
 const f=document.getElementById('follow').value;if(f){const x=S.find(q=>q.u.unit===f);if(x)map.jumpTo({center:[x.s.lon,x.s.lat]})}
}
function loop(ts){if(play){if(last!==null){T+=(ts-last)/1000*parseFloat(document.getElementById('spd').value);if(T>=T1){T=T1;play=false;
  document.getElementById('play').textContent='▶ Putar'}}last=ts}else last=null;
 if(rot)map.setBearing(map.getBearing()+0.08);render();requestAnimationFrame(loop)}
document.getElementById('play').onclick=()=>{play=!play;if(play&&T>=T1)T=0;document.getElementById('play').textContent=play?'⏸ Jeda':'▶ Putar'};
document.getElementById('reset').onclick=()=>{T=0};
slider.oninput=()=>{T=parseFloat(slider.value)};
document.getElementById('rot').onclick=e=>{rot=!rot;e.target.classList.toggle('on',rot)};
document.getElementById('v3d').onclick=e=>{is3d=!is3d;e.target.classList.toggle('on',is3d);map.easeTo({pitch:is3d?55:0,bearing:is3d?-18:0,duration:900})};
document.getElementById('base').onchange=e=>{const v=e.target.value;
 [['dark',v==='dark'],['darkref',v==='dark'||v==='sat'],['sat',v==='sat'],['osm',v==='osm']].forEach(([id,on])=>map.setLayoutProperty(id,'visibility',on?'visible':'none'))};
document.getElementById('fitb').onclick=()=>{document.getElementById('follow').value='';fit()};
document.getElementById('follow').onchange=e=>{if(e.target.value)map.easeTo({zoom:13,pitch:60,duration:800})};
map.on('load',()=>{fit();render();requestAnimationFrame(loop)});
</script></body></html>"""
