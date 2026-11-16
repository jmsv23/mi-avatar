// Regression: facial state must depend only on time, including backward seeks.
const {readFileSync} = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
class Element {
  constructor(tag) { this.tag = tag; this.attrs = {}; this.style = {}; this.children = []; }
  setAttribute(key, value) { this.attrs[key] = String(value); }
  removeAttribute(key) { delete this.attrs[key]; }
  appendChild(child) { this.children.push(child); return child; }
}
const ctx = {window:{}, document:{createElementNS:(_,tag)=>new Element(tag)}};
vm.createContext(ctx);
for (const file of ['avatar.js','avatar-player.js']) vm.runInContext(readFileSync(`motion/shared/${file}`,'utf8'),ctx);
ctx.AVATAR = ctx.window.AVATAR;
const AVATAR = ctx.window.AVATAR, PLAYER = ctx.window.AVPLAYER;
const eyes = {izq:{x:40,y:30,piel:'#fda769'},der:{x:80,y:30,piel:'#fda769'}};
const reference = {boca:{x:60,y:65,escala:1},ojos:eyes};
const frame = name => ({archivo:name+'.png',x:30,y:20,ancho:60,alto:50});
const manifest = {lienzo:{ancho:120,alto:180},poses:{
  neutral:{archivo:'neutral.png',boca:reference.boca,ojos:eyes},
  pensar:{archivo:'pensar.png',boca:{x:64,y:70,escala:0.9,rotacion:10},ojos:eyes,habla:false,parpadeo:false},
},recortes:{referencia:reference,bocas:{A:frame('A'),E_I:frame('E_I'),O_U:frame('O_U'),FV:frame('FV'),CONS:frame('CONS')},
ojos:{izq:{medio:frame('izq-medio'),cerrado:frame('izq-cerrado')},der:{medio:frame('der-medio'),cerrado:frame('der-cerrado')}}}};
function visibleImages(root) {
  return [root,...root.children.flatMap(child=>flatten(child))].filter(node=>node.tag==='image' && node.attrs.opacity==='1').map(node=>node.attrs.href).sort();
}
function flatten(root) { return [root,...root.children.flatMap(flatten)]; }
const stage = new Element('div');
const avatar = AVATAR.create(stage,manifest);
avatar.set({pose:'neutral',viseme:'A',lids:1});
assert.deepEqual(visibleImages(stage),['A.png','der-cerrado.png','izq-cerrado.png']);
avatar.set({viseme:'REST',lids:0});
assert.deepEqual(visibleImages(stage),[]);
avatar.set({viseme:'MBP',lids:0.5});
assert.deepEqual(visibleImages(stage),['der-medio.png','izq-medio.png']);
avatar.set({pose:'pensar',viseme:'A',lids:1});
assert.deepEqual(visibleImages(stage),[]);
avatar.set({pose:'neutral',mouth:AVATAR.mixViseme('A','O_U',0.8),lids:0});
assert.deepEqual(visibleImages(stage),['O_U.png']);
const body = new Element('div'), mount = new Element('div');
const player = PLAYER.mount(body,mount,manifest,{poses:[{t:0,pose:'neutral'},{t:2,pose:'pensar'}],
visemas:[{t:0.2,d:0.5,v:'A'},{t:0.7,d:0.5,v:'O_U'}],parpadeos:[0.4],gestos:[]});
const snapshot = t => { player.render(t); return JSON.stringify({body, mount}); };
for (const time of [0,0.3,0.43,0.48,0.54,0.8,1.5,2.2]) {
  const expected = snapshot(time);
  snapshot(2.5); snapshot(0);
  assert.equal(snapshot(time),expected,`seek at ${time}`);
}
// Cambio de pose: fundido corto entre dos capas, y luego solo la capa nueva visible.
const [under, over] = mount.children;
player.render(2.05);
assert.equal(under.style.opacity,'1'); assert.ok(Number(over.style.opacity)>0 && Number(over.style.opacity)<1);
player.render(2.5);
assert.equal(under.style.opacity,'0'); assert.equal(over.style.opacity,'1');
const legacy = structuredClone(manifest); delete legacy.recortes;
const fallbackRoot = new Element('div');
const fallback = AVATAR.create(fallbackRoot,legacy);
fallback.set({pose:'neutral',viseme:'A',lids:1});
assert.equal(fallback.svg.children.find(node=>node.tag==='g').style.display,'');
// Al cerrar, ningún tramo vertical del ojo puede seguir dejando ver el blanco.
const lidRects = flatten(fallbackRoot).filter(node=>node.tag==='rect' && (node.attrs['clip-path']||'').includes('-eye-'));
const clips = [...new Set(lidRects.map(node=>node.attrs['clip-path']))];
assert.equal(clips.length,2);
for (const clip of clips) {
  const masks = lidRects.filter(node=>node.attrs['clip-path']===clip);
  for (let y=-20; y<=23; y+=0.5) {
    assert.ok(masks.some(node=>y>=Number(node.attrs.y) && y<=Number(node.attrs.y)+Number(node.attrs.height)),`uncovered eye at ${y}`);
  }
}
fallback.set({lids:0});
assert.ok(lidRects.every(node=>Number(node.attrs.height)===0));
console.log('OK: facial states, disabled gestures, backward seeking, and original renderer.');
