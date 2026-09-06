import * as THREE from 'three';
import {toWorld as v} from './world.js';

export const chapters = [
  {title:'虹桥胜景',subtitle:'飞架汴水，舟楫往来',number:'壹',map:'虹桥 · 汴水之上',pos:v(-34,-41,25),target:v(0,1,4)},
  {title:'汴河漕运',subtitle:'一河通南北，千帆载烟火',number:'贰',map:'汴河 · 漕运码头',pos:v(-8,-39,4.5),target:v(1,1,3)},
  {title:'沿岸市井',subtitle:'茶烟初起，市声渐浓',number:'叁',map:'东岸 · 临河街市',pos:v(16,-33,4.4),target:v(25,-27,3)},
  {title:'街巷营造',subtitle:'灰瓦连檐，深巷藏春',number:'肆',map:'西岸 · 坊巷之间',pos:v(-33,-12,18),target:v(-34,15,4)},
  {title:'城阙远眺',subtitle:'万家灯火前，一城春色中',number:'伍',map:'汴京 · 城郭远景',pos:v(-61,-76,51),target:v(-1,19,3)},
];

export const cinematicShots = [
  {start:0,end:10,chapter:0,p0:v(-45,-54,30),p1:v(-32,-41,23),t0:v(-2,1,3),t1:v(0,2,4)},
  {start:10,end:21,chapter:1,p0:v(-6,-38,3.4),p1:v(-4,-26,4.7),t0:v(2,3,2.5),t1:v(1,5,3.5)},
  {start:21,end:33,chapter:0,p0:v(-25,-27,13),p1:v(-13,-27,21),t0:v(-1,0,5),t1:v(0,0,5)},
  {start:33,end:43,chapter:2,p0:v(16,-39,4.4),p1:v(16,-24,4.3),t0:v(25,-33,3),t1:v(25,-18,2.9)},
  {start:43,end:53,chapter:3,p0:v(-30,-32,13),p1:v(-39,-42,28),t0:v(-5,7,4),t1:v(-1,8,3)},
  {start:53,end:60,chapter:4,p0:v(-43,-52,32),p1:v(-61,-79,48),t0:v(0,10,3),t1:v(0,16,3)},
];

export class Tour {
  constructor(camera,controls,onChapter,onFinish){this.camera=camera;this.controls=controls;this.onChapter=onChapter;this.onFinish=onFinish;this.active=false;this.transition=null;this.elapsed=0;this.lastShot=-1;}
  go(index,duration=2.8){this.stop();this.onChapter(index);const c=chapters[index];this.transition={from:this.camera.position.clone(),fromTarget:this.controls.target.clone(),to:c.pos.clone(),target:c.target.clone(),elapsed:0,duration};}
  start(){this.transition=null;this.active=true;this.elapsed=0;this.lastShot=-1;this.controls.enabled=false;}
  stop(){this.active=false;this.transition=null;this.controls.enabled=true;}
  tick(delta){
    if(this.transition){const t=this.transition;t.elapsed+=delta;const q=Math.min(1,t.elapsed/t.duration),s=q*q*(3-2*q);this.camera.position.lerpVectors(t.from,t.to,s);this.camera.position.y+=Math.sin(Math.PI*s)*Math.min(12,t.from.distanceTo(t.to)*.2);this.controls.target.lerpVectors(t.fromTarget,t.target,s);this.camera.lookAt(this.controls.target);if(q===1)this.transition=null;}
    if(!this.active)return;
    this.elapsed=Math.min(60,this.elapsed+delta);
    const idx=Math.max(0,cinematicShots.findIndex(s=>this.elapsed<s.end));
    const shot=cinematicShots[this.elapsed===60?cinematicShots.length-1:idx];
    if(this.lastShot!==idx){this.lastShot=idx;this.onChapter(shot.chapter);}
    const q=THREE.MathUtils.clamp((this.elapsed-shot.start)/(shot.end-shot.start),0,1),s=q*q*(3-2*q);
    this.camera.position.lerpVectors(shot.p0,shot.p1,s);this.controls.target.lerpVectors(shot.t0,shot.t1,s);this.camera.lookAt(this.controls.target);
    if(this.elapsed>=60){this.stop();this.onFinish();}
  }
}
