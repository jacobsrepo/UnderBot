// Exercise the actual delivered HTML script with DOM/WebGL stubs, then compare
// its kinematics against an independent floating-root PyBullet import.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const pkg = root;
const html = fs.readFileSync(path.join(pkg, 'viewer.html'), 'utf8');
const dataString = html.match(/<script id="model-data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const script = html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
const model = JSON.parse(dataString);
if (model.revision !== 'R09') throw Error('Expected R09 viewer');
if (!html.includes('Frame and floors: 200 × 200 mm') || !html.includes('204 × 204 mm covered body') || !html.includes('uncalibrated reservations')) throw Error('R09 packaging note missing');
const expected = JSON.parse(fs.readFileSync(path.join(pkg, 'validation', 'pybullet_import_R09.json'), 'utf8'));
const urdfHash = crypto.createHash('sha256').update(fs.readFileSync(path.join(pkg, 'urdf', 'underbot.portable.urdf'))).digest('hex');
if (model.urdf_sha256 !== urdfHash || expected.urdf_sha256 !== urdfHash) throw Error('Source hashes differ');
for(const [filename,encoded] of Object.entries(model.meshes)) {
  const hash=crypto.createHash('sha256').update(Buffer.from(encoded,'base64')).digest('hex');
  if(hash!==expected.mesh_sha256[filename])throw Error('Embedded STL differs from preview source: '+filename);
  const sourceHash=crypto.createHash('sha256').update(fs.readFileSync(path.join(pkg,filename))).digest('hex');
  if(hash!==sourceHash)throw Error('Embedded STL differs from current source asset: '+filename);
}
const elements = [];
class Element {
  constructor(tag) { this.tagName=tag; this.children=[]; this.dataset={}; this.style={}; this.value=''; this.textContent=''; this.checked=true; this.classList={toggle(){}}; elements.push(this); }
  append(...children) { this.children.push(...children); }
  setAttribute(name,value) { this[name]=value; }
  addEventListener() {}
  setPointerCapture() {}
  click() { if (this.onclick) this.onclick(); }
}
const gl = new Proxy({}, { get(target, prop) {
  if (prop==='getShaderParameter'||prop==='getProgramParameter') return ()=>true;
  if (prop==='createShader'||prop==='createProgram'||prop==='createBuffer'||prop==='getUniformLocation') return ()=>({});
  if (prop==='getAttribLocation') return ()=>0;
  if (prop==='bufferData') return (_,array)=>{ if (!Array.from(array).every(Number.isFinite)) throw Error('Nonfinite WebGL geometry'); };
  if (/^[A-Z_]+$/.test(prop)) return 1;
  return ()=>{};
}});
const nodes = {};
const document = {
  getElementById(id) {
    if (!nodes[id]) nodes[id]=new Element(id);
    if (id==='model-data') nodes[id].textContent=dataString;
    if (id==='canvas') Object.assign(nodes[id],{clientWidth:1200,clientHeight:900,getContext:()=>gl});
    if (id==='mode') nodes[id].value='visual';
    return nodes[id];
  },
  createElement(tag) { return new Element(tag); },
  querySelectorAll(selector) { return elements.filter(el=>selector==='.joint' && el.className==='joint'); }
};
const context = {document,window:{},devicePixelRatio:1,requestAnimationFrame(){},atob:s=>Buffer.from(s,'base64').toString('binary'),Float32Array,Uint8Array,DataView,Math,Number,Array,Object,JSON,Error};
vm.createContext(context);
vm.runInContext(script,context,{timeout:20000});
const viewer=context.window.underbotViewer;
for (const [name,value] of Object.entries(expected.nonzero_independent_pose_radians)) viewer.setJoint(name,value);
const actual=viewer.getTransforms();
let error=0;
for (const [link,matrix] of Object.entries(expected.nonzero_pose_world_link_frames)) {
  for(let row=0;row<4;row++)for(let col=0;col<4;col++)error=Math.max(error,Math.abs(actual[link][col*4+row]-matrix[row][col]));
}
if (error>2e-6) throw Error('Viewer/PyBullet FK disagreement: '+error);
const controls=elements.filter(el=>el.className==='joint');
if(controls.length!==16)throw Error('Expected 16 independent joint controls, got '+controls.length);
const groupNames=elements.filter(el=>el.tagName==='summary').map(el=>el.textContent);
if(!groupNames.includes('Passive caster · inspection only'))throw Error('Passive caster section missing');
for(const follower of expected.mimic_followers){
 const joint=model.joints.find(j=>j.name===follower);
 const expectedValue=viewer.values[joint.mimic.joint]*joint.mimic.multiplier+joint.mimic.offset;
 if(Math.abs(viewer.getMimicValue(follower)-expectedValue)>1e-12)throw Error('Mimic mismatch');
}
viewer.reset();
if(!Object.values(viewer.values).every(value=>value===0))throw Error('Reset missed a joint');
const report={status:'PASS',urdf_sha256:urdfHash,links:model.links.length,joints:model.joints.length,independent_controls:controls.length,groups:groupNames,maximum_viewer_vs_pybullet_matrix_error:error,mimic_followers_checked:expected.mimic_followers,reset_all_independent_coordinates:true,embedded_stl_assets:Object.keys(model.meshes).length,all_embedded_meshes_match_current_source:true,external_dependencies:false,scope:'The delivered JavaScript ran with DOM/WebGL stubs, decoded all embedded STL meshes, built every slider, drew one frame, matched actual PyBullet FK, applied mimic equations, and reset all controls. Native browser rasterization and GPU appearance were not tested by this check.'};
fs.writeFileSync(path.join(pkg,'validation','viewer_checks_R09.json'),JSON.stringify(report,null,2)+'\n');
process.stdout.write(JSON.stringify(report,null,2)+'\n');
