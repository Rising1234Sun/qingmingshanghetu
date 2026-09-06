import './style.css';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { SSAOPass } from 'three/addons/postprocessing/SSAOPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { FXAAShader } from 'three/addons/shaders/FXAAShader.js';
import { createWorld,toWorld } from './world.js';
import { Tour,chapters } from './tour.js';
import { Capture,saveMedia } from './recording.js';
import {InterfaceRecording} from './interface-recording.js';
import {assetUrl} from './paths.js';

const $=id=>document.getElementById(id);
const icons={play:'<path d="m7 4 13 8-13 8z"/>',pause:'<path d="M8 5v14M16 5v14"/>',scroll:'<path d="M5 4h13v15H5zM5 4C1 4 1 9 5 9M18 15c4 0 4 5 0 5M9 8h5M9 12h5M9 16h4"/>','volume-off':'<path d="M11 5 6 9H3v6h3l5 4zM16 9l5 6m0-6-5 6"/>',volume:'<path d="M11 5 6 9H3v6h3l5 4zM15 8a6 6 0 0 1 0 8M18 4a11 11 0 0 1 0 16"/>',sliders:'<path d="M4 7h7m4 0h5M4 17h3m4 0h9"/><circle cx="13" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',expand:'<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/>',eye:'<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>'};
const icon=name=>`<svg viewBox="0 0 24 24" aria-hidden="true">${icons[name]||icons.play}</svg>`;
document.querySelectorAll('[data-icon]').forEach(el=>el.innerHTML=icon(el.dataset.icon));
let toastTimer;
function toast(message){$('toast').textContent=message;$('toast').classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.remove('show'),4200);}

const viewport=$('viewport');
let renderer;
try{renderer=new THREE.WebGLRenderer({antialias:false,alpha:false,powerPreference:'high-performance',preserveDrawingBuffer:true});}
catch(error){$('load-error').hidden=false;$('load-error').textContent='无法初始化三维画面。请开启浏览器硬件加速，并使用支持 WebGL 2 的浏览器。';throw error;}
renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;
renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFShadowMap;renderer.info.autoReset=false;
viewport.append(renderer.domElement);
let interfaceLongEdge=0;
const interfaceRecording=new InterfaceRecording(renderer,message=>toast(message),longEdge=>{interfaceLongEdge=longEdge;resize();});
$('record-interface').onclick=async()=>{try{const longEdge=Number($('interface-resolution').value);$('capture-dialog').close();await interfaceRecording.start(longEdge);}catch(error){interfaceLongEdge=0;resize();toast(error.message);console.error(error);}};
const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(43,1,.3,1400);
camera.position.copy(toWorld(-40,-48,28));
const controls=new OrbitControls(camera,renderer.domElement);controls.target.copy(toWorld(-6,1,3));controls.enableDamping=true;controls.dampingFactor=.065;
controls.minDistance=3;controls.maxDistance=200;controls.maxPolarAngle=Math.PI*.489;controls.minPolarAngle=.13;controls.panSpeed=.65;controls.rotateSpeed=.5;controls.zoomSpeed=.7;controls.update();
const composer=new EffectComposer(renderer),renderPass=new RenderPass(scene,camera);composer.addPass(renderPass);
const ao=new SSAOPass(scene,camera,window.innerWidth,window.innerHeight);ao.kernelRadius=.6;ao.minDistance=.0005;ao.maxDistance=.025;ao.enabled=false;composer.addPass(ao);
composer.addPass(new OutputPass());const fxaa=new ShaderPass(FXAAShader);composer.addPass(fxaa);
let quality=window.innerWidth<700&&matchMedia('(pointer: coarse)').matches?'low':'high',world,animTime=0,motion=true,pins=true,loaded=false,currentChapter=0;
let pausedByVisibility=false,lastNow=performance.now(),statStart=lastNow,statFrames=0,currentFps=0,recordingSize=false;
const audio=new Audio(assetUrl('audio/bianjing.mp3'));audio.loop=true;audio.volume=.72;audio.preload='none';
function resize(){const r=viewport.getBoundingClientRect();const dpr=interfaceLongEdge?interfaceLongEdge/Math.max(r.width,r.height):quality==='ultra'?Math.min(devicePixelRatio,2):quality==='low'?1:Math.min(devicePixelRatio,1.5);renderer.setPixelRatio(recordingSize?1:dpr);renderer.setSize(recordingSize?(viewport.classList.contains('portrait')?1080:1920):r.width,recordingSize?(viewport.classList.contains('portrait')?1920:1080):r.height,false);camera.aspect=recordingSize?(viewport.classList.contains('portrait')?9/16:16/9):r.width/r.height;camera.updateProjectionMatrix();composer.setPixelRatio(recordingSize?1:dpr);composer.setSize(renderer.domElement.width/(recordingSize?1:dpr),renderer.domElement.height/(recordingSize?1:dpr));fxaa.uniforms.resolution.value.set(1/renderer.domElement.width,1/renderer.domElement.height);}
resize();window.addEventListener('resize',resize);
const capture=new Capture(renderer,audio,(error,size)=>{recordingSize=false;resize();document.body.classList.remove('recording');setUI(true);tour.stop();refreshTour();if(error)toast(error);else toast(`录制已保存 · ${(size/1048576).toFixed(1)} MB`);});
function selectChapter(index){currentChapter=index;const c=chapters[index];$('scene-number').textContent=c.number;$('scene-title').textContent=c.title;$('scene-subtitle').textContent=c.subtitle;$('location-name').textContent=c.map;document.querySelectorAll('.chapter').forEach((b,i)=>b.classList.toggle('active',i===index));}
const tour=new Tour(camera,controls,selectChapter,()=>{if(capture.active)capture.stop();refreshTour();toast('巡游结束，可以继续自由观察');});
function refreshTour(){$('tour').classList.toggle('playing',tour.active);$('tour-label').textContent=tour.active?'结束巡游':'自动巡游';$('tour').querySelector('.icon').innerHTML=icon(tour.active?'pause':'play');$('tour-time').textContent=tour.active?'00:00':'60 秒';$('tour-progress').hidden=!tour.active;}
function startTour(){if(!loaded)return;document.body.classList.add('exploring');tour.start();refreshTour();}
function toggleTour(){if(tour.active){tour.stop();refreshTour();if(capture.active)capture.stop();}else startTour();}
$('tour').onclick=toggleTour;$('intro-tour').onclick=startTour;
document.querySelectorAll('.chapter').forEach(b=>b.onclick=()=>{document.body.classList.add('exploring');tour.go(Number(b.dataset.chapter));refreshTour();});
controls.addEventListener('start',()=>{if(capture.active)return;document.body.classList.add('exploring');tour.stop();refreshTour();});
$('home').onclick=()=>{tour.go(0);refreshTour();};
for(const [id,factor] of [['zoom-in',.8],['zoom-out',1.25]])$(id).onclick=()=>{tour.stop();refreshTour();const diff=camera.position.clone().sub(controls.target);const distance=THREE.MathUtils.clamp(diff.length()*factor,controls.minDistance,controls.maxDistance);camera.position.copy(controls.target).add(diff.setLength(distance));controls.update();document.body.classList.add('exploring');};
function setUI(visible){document.body.classList.toggle('ui-hidden',!visible);$('restore-ui').hidden=visible;}
$('hide-ui').onclick=()=>setUI(false);$('restore-ui').onclick=()=>setUI(true);
$('fullscreen').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch{toast('此浏览器未开放全屏，请使用浏览器全屏快捷键。');}};
async function toggleAudio(){try{await capture.prepareAudio();if(audio.paused){await audio.play();}else audio.pause();updateAudioButton();}catch{toast('音频未能播放，请再次点击声音按钮。');}}
function updateAudioButton(){const playing=!audio.paused;$('sound').setAttribute('aria-pressed',String(playing));$('sound').setAttribute('aria-label',playing?'关闭原创配乐':'开启原创配乐');$('sound').title=playing?'关闭原创配乐':'开启原创配乐';$('sound').querySelector('.icon').innerHTML=icon(playing?'volume':'volume-off');}
$('sound').onclick=toggleAudio;
for(const name of ['settings','reference','about','capture'])$(`${name}-open`).onclick=()=>$(name+'-dialog').showModal();
document.querySelectorAll('dialog').forEach(d=>d.addEventListener('click',e=>{const r=d.getBoundingClientRect();if(e.target===d&&(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom))d.close();}));
$('quality').value=quality;
$('quality').onchange=e=>{quality=e.target.value;world?.setQuality(quality);ao.enabled=quality==='ultra';resize();toast('画面精度已调整');};
$('motion-toggle').onchange=e=>{motion=e.target.checked;};
$('pins-toggle').onchange=e=>{pins=e.target.checked;};
$('wire-toggle').onchange=e=>{world?.setWireframe(e.target.checked);};
document.querySelectorAll('[data-light]').forEach(b=>b.onclick=()=>{world?.setLight(b.dataset.light);document.querySelectorAll('[data-light]').forEach(o=>o.classList.toggle('active',o===b));$('time-label').textContent={day:'清晨 · 晴空',golden:'午后 · 暖日',sunset:'日暮 · 余晖'}[b.dataset.light];});
$('aspect').onchange=e=>{viewport.classList.toggle('portrait',e.target.value==='portrait');resize();toast(e.target.value==='portrait'?'已切换 9:16 竖屏取景':'已恢复横屏取景');};
$('screenshot').onclick=()=>{if(!loaded)return;$('capture-dialog').close();renderer.setPixelRatio(1);const r=viewport.getBoundingClientRect();const scale=3840/Math.max(r.width,r.height);renderer.setSize(Math.round(r.width*scale),Math.round(r.height*scale),false);renderer.render(scene,camera);renderer.domElement.toBlob(async blob=>{if(blob)await saveMedia(blob,'入画汴京_三维实景.png');resize();toast('当前三维画面已保存');},'image/png');};
$('record').onclick=async()=>{if(!loaded||capture.active)return;$('record').disabled=true;try{$('capture-dialog').close();setUI(false);document.body.classList.add('recording');recordingSize=true;resize();await capture.start();updateAudioButton();animTime=0;startTour();toast('正在记录三维巡游，按 Esc 可停止并保存');}catch(error){recordingSize=false;resize();document.body.classList.remove('recording');setUI(true);toast(error.message);}finally{$('record').disabled=false;}};

const details=[
  {title:'编木虹桥',label:'虹桥',pos:toWorld(2,0,8),chapter:0,html:`<img src="${assetUrl('reference/bridge.jpg')}" alt="原卷中的虹桥"><p>木梁交叠，拱架横跨汴河。原卷中桥上人流与桥下船工构成整个画面的焦点。</p><ul><li>开放木构，无河中桥墩</li><li>逐块桥板、栏杆与交叠木梁</li><li>桥上行人、挑担人与临桥摊贩</li></ul>`},
  {title:'汴河漕运',label:'漕船',pos:toWorld(-6,-26,3),chapter:1,html:'<p>汴河连接南北交通，货船满载粮袋与日用物资。竹篷、缆绳、舷板和撑篙在三维空间中分别建模。</p><ul><li>船体轻摇，缓慢随河前行</li><li>实时水面倒影与细波</li><li>船工关节动画与货物细节</li></ul>'},
  {title:'沿岸茶肆',label:'茶肆',pos:toWorld(24,-14,6),chapter:2,html:'<p>檐下设摊，窗前置器。茶肆、酒坊与布铺组成临河商业街，器皿与竹篮保留可近看的几何细节。</p><ul><li>木窗、曲瓦、梁柱与布幌</li><li>青瓷、陶器、竹篮和木车</li><li>日光与阴影随时辰切换</li></ul>'},
];
const hotElements=details.map((d,i)=>{const button=document.createElement('button');button.className='hotspot';button.setAttribute('aria-label','查看'+d.title);button.innerHTML=`<i></i><span>${d.label}</span>`;$('hotspots').append(button);button.onclick=()=>{$('detail-title').textContent=d.title;$('detail-content').innerHTML=d.html;$('detail-dialog').showModal();$('detail-visit').onclick=()=>{$('detail-dialog').close();tour.go(d.chapter);refreshTour();document.body.classList.add('exploring');};};return button;});

const map=$('minimap'),ctx=map.getContext('2d');
function drawMap(){const w=map.width,h=map.height;ctx.clearRect(0,0,w,h);const project=(x,z)=>[w/2+x*2.05,h/2+z*1.36];
  ctx.fillStyle='#617f741f';ctx.beginPath();ctx.moveTo(145,0);ctx.bezierCurveTo(126,100,162,240,143,400);ctx.lineTo(210,400);ctx.bezierCurveTo(230,270,191,100,215,0);ctx.closePath();ctx.fill();
  ctx.strokeStyle='#63725d42';ctx.lineWidth=1;for(let side of [-1,1])for(let row=0;row<3;row++)for(let i=0;i<15;i++){const [x,y]=project(side*(28+row*12),-108+i*15);ctx.strokeRect(x-8,y-6,15+(i%2)*4,13);}
  ctx.strokeStyle='#a1684e';ctx.lineWidth=5;ctx.beginPath();const p0=project(-17,0),p1=project(17,0);ctx.moveTo(...p0);ctx.lineTo(...p1);ctx.stroke();
  const [tx,tz]=project(controls.target.x,controls.target.z),[cx,cz]=project(camera.position.x,camera.position.z),a=Math.atan2(tz-cz,tx-cx);ctx.fillStyle='#4e7a6740';ctx.beginPath();ctx.moveTo(cx,cz);ctx.arc(cx,cz,33,a-.4,a+.4);ctx.closePath();ctx.fill();ctx.fillStyle='#a14e35';ctx.beginPath();ctx.arc(cx,cz,4.8,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#66867370';ctx.setLineDash([4,5]);ctx.beginPath();ctx.moveTo(cx,cz);ctx.lineTo(tx,tz);ctx.stroke();ctx.setLineDash([]);
}
map.onclick=e=>{const r=map.getBoundingClientRect(),x=((e.clientX-r.left)/r.width*map.width-map.width/2)/2.05,z=((e.clientY-r.top)/r.height*map.height-map.height/2)/1.36;tour.stop();refreshTour();const delta=new THREE.Vector3(x,2,z).sub(controls.target);camera.position.add(delta);controls.target.add(delta);controls.update();document.body.classList.add('exploring');};
const keys=new Set();window.addEventListener('keydown',e=>{if(['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName)||document.querySelector('dialog[open]'))return;if(e.key==='Escape'){if(interfaceRecording.active)interfaceRecording.stop();if(capture.active)capture.stop();else{setUI(true);tour.stop();refreshTour();}}if(e.key.toLowerCase()==='h'){setUI(document.body.classList.contains('ui-hidden'));}if(e.code==='Space'&&document.activeElement.tagName!=='BUTTON'){e.preventDefault();toggleTour();}keys.add(e.code);});window.addEventListener('keyup',e=>keys.delete(e.code));window.addEventListener('blur',()=>keys.clear());
document.addEventListener('visibilitychange',()=>{pausedByVisibility=document.hidden;lastNow=performance.now();if(document.hidden&&capture.active){capture.stop();toast('页面离开前台，已停止并保存当前录制。');}});
renderer.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();toast('图形上下文已中断，请刷新网页重新载入。');if(capture.active)capture.stop();});
const projected=new THREE.Vector3();
function animate(now){requestAnimationFrame(animate);if(pausedByVisibility)return;const dt=Math.min((now-lastNow)/1000,.12);lastNow=now;if(!loaded)return;
  if(motion)animTime+=dt;world.update(animTime,motion);tour.tick(dt);
  if(!tour.active&&!tour.transition){const speed=dt*(keys.has('ShiftLeft')?18:7),forward=camera.getWorldDirection(new THREE.Vector3());forward.y=0;forward.normalize();const right=new THREE.Vector3().crossVectors(forward,camera.up);const move=new THREE.Vector3();if(keys.has('KeyW')||keys.has('ArrowUp'))move.addScaledVector(forward,speed);if(keys.has('KeyS')||keys.has('ArrowDown'))move.addScaledVector(forward,-speed);if(keys.has('KeyD')||keys.has('ArrowRight'))move.addScaledVector(right,speed);if(keys.has('KeyA')||keys.has('ArrowLeft'))move.addScaledVector(right,-speed);if(move.lengthSq()){camera.position.add(move);controls.target.add(move);document.body.classList.add('exploring');}}
  controls.update();camera.position.y=Math.max(1.92,camera.position.y);
  const rect=viewport.getBoundingClientRect();
  hotElements.forEach((el,i)=>{projected.copy(details[i].pos).project(camera);const visible=pins&&!tour.active&&projected.z<1&&projected.z>-1&&Math.abs(projected.x)<.89&&Math.abs(projected.y)<.70&&camera.position.distanceTo(details[i].pos)<110;el.classList.toggle('visible',visible);el.style.left=`${rect.left+(projected.x*.5+.5)*rect.width}px`;el.style.top=`${rect.top+(-projected.y*.5+.5)*rect.height}px`;});
  renderer.info.reset();composer.render();interfaceRecording.frame(now);
  statFrames++;
  if(now-statStart>700){currentFps=Math.round(statFrames*1000/(now-statStart));$('performance').textContent=`${currentFps} FPS · ${(renderer.info.render.triangles/1000000).toFixed(2)}M 三角形\n${renderer.info.render.calls} 次绘制 · ${world.people.length} 人 · ${world.boats.length} 船`;statStart=now;statFrames=0;drawMap();}
  if(tour.active){$('tour-time').textContent=`00:${Math.floor(tour.elapsed).toString().padStart(2,'0')}`;$('tour-progress').firstElementChild.style.width=`${tour.elapsed/60*100}%`;}
}
requestAnimationFrame(animate);
try{
  world=await createWorld(scene,renderer,(p,label)=>{$('loading-bar').style.width=`${Math.round(p*93)}%`;$('loading-percent').textContent=`${Math.round(p*93)}%`;$('loading-label').textContent=label;});
  world.setQuality(quality);$('loading-label').textContent='初春日光，落在汴河';$('loading-percent').textContent='98%';$('loading-bar').style.width='98%';
  await renderer.compileAsync(scene,camera);loaded=true;lastNow=performance.now();document.body.classList.add('ready');$('loading-percent').textContent='100%';$('loading-bar').style.width='100%';
  // 仅暴露读数与可检验状态，便于本地验收；界面操作全部通过真实控件完成。
  window.bianjing={getStats:()=>({...world.getStats(),fps:currentFps,triangles:renderer.info.render.triangles,drawCalls:renderer.info.render.calls,quality,loaded,tour:tour.active,recording:capture.active,seconds:animTime}),getView:()=>({position:camera.position.toArray(),target:controls.target.toArray()})};
}catch(error){console.error(error);$('load-error').hidden=false;$('load-error').innerHTML='场景加载未完成。请确认已通过项目的本地启动器打开，然后刷新重试。<br><small></small>';$('load-error').querySelector('small').textContent=error.message;$('loading-label').textContent='载入中断';}
