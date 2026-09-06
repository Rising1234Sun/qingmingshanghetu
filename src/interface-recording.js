import {toCanvas, toSvg, getFontEmbedCSS} from 'html-to-image';
import {saveMedia} from './recording.js';

// WebGL 每帧实时采集；按钮与弹窗按真实 DOM 状态更新，鼠标轨迹来自实际输入事件。
// 界面层单独缓存，避免对每一帧重复排版字体而拖慢三维场景。
export class InterfaceRecording {
  constructor(renderer,onStatus,onResolution=()=>{}){
    this.renderer=renderer;this.onStatus=onStatus;this.onResolution=onResolution;this.active=false;this.pending=true;this.lastSnapshot=0;
    this.cursor={x:640,y:360,down:false,pulse:0,seen:false};this.events=[];
    this.toolbar=document.createElement('div');this.toolbar.id='interface-recording-toolbar';this.toolbar.hidden=true;
    this.toolbar.innerHTML='<span id="interface-recording-time">准备录制</span><button id="stop-interface-recording">结束并保存</button>';
    document.body.append(this.toolbar);this.toolbar.querySelector('button').onclick=()=>this.stop();
    const update=e=>{if(!this.active)return;this.cursor.x=e.clientX;this.cursor.y=e.clientY;this.cursor.seen=true;};
    document.addEventListener('pointermove',update,true);
    document.addEventListener('pointerdown',e=>{update(e);this.cursor.down=true;this.cursor.pulse=performance.now();},true);
    document.addEventListener('pointerup',e=>{update(e);this.cursor.down=false;},true);
    document.addEventListener('click',e=>{if(!this.active||this.toolbar.contains(e.target))return;const el=e.target.closest('button,canvas,a,input');this.log('click',el?.getAttribute('aria-label')||el?.textContent?.trim()||el?.id||'页面',e);this.pending=true;setTimeout(()=>{this.pending=true;},400);},true);
    document.addEventListener('wheel',e=>{if(!this.active)return;update(e);this.cursor.pulse=performance.now();if(performance.now()-(this.lastWheel||0)>400){this.log('wheel',Math.abs(e.deltaX)>Math.abs(e.deltaY)?'横向滚动':e.deltaY<0?'滚轮拉近':'滚轮拉远',e);this.lastWheel=performance.now();}this.pending=true;},true);
    document.addEventListener('change',e=>{this.log('change',`${e.target.id}: ${e.target.type==='checkbox'?e.target.checked:e.target.value}`);this.pending=true;});
    document.addEventListener('keydown',e=>{if(this.active){this.log('key',e.key);this.pending=true;if(e.key==='Escape')this.stop();}});
    document.querySelectorAll('dialog').forEach(d=>d.addEventListener('close',()=>{this.pending=true;}));
    document.addEventListener('scroll',()=>{this.pending=true;},true);
    document.addEventListener('visibilitychange',()=>{if(document.hidden&&this.active)this.stop();});
  }
  log(type,label,e){if(this.active)this.events.push({seconds:+((performance.now()-this.started)/1000).toFixed(3),type,label,x:e?.clientX,y:e?.clientY});}
  async start(longEdge=1920){
    if(this.active||this.saving)return;
    this.onStatus('正在准备完整界面录制');
    await document.fonts.ready;
    this.longEdge=longEdge===3840?3840:1920;
    this.width=innerWidth;this.height=innerHeight;this.scale=this.longEdge/Math.max(this.width,this.height);
    // 同时提升实际 WebGL 缓冲区与 HTML 字体采样，保留源头细节。
    this.onResolution(this.longEdge);
    this.canvas=document.createElement('canvas');this.canvas.width=Math.round(this.width*this.scale/2)*2;this.canvas.height=Math.round(this.height*this.scale/2)*2;
    this.ctx=this.canvas.getContext('2d',{alpha:false});
    this.fontCSS=await getFontEmbedCSS(document.getElementById('interface'));
    this.options={fontEmbedCSS:this.fontCSS,pixelRatio:this.scale,skipAutoScale:true,cacheBust:false};
    this.hotImages=new Map();
    for(const el of document.querySelectorAll('.hotspot')){
      const image=await toCanvas(el,{...this.options,style:{opacity:'1',position:'static',transform:'none',filter:'none',margin:'0'}});
      this.hotImages.set(el,image);
    }
    await this.snapshot();
    const mime=['video/mp4;codecs=avc1.640033','video/mp4;codecs=avc1.42E033','video/mp4','video/webm;codecs=vp9','video/webm'].find(t=>MediaRecorder.isTypeSupported(t));
    if(!mime)throw new Error('此浏览器没有可用的网页录像编码器。');
    this.stream=this.canvas.captureStream(60);
    this.recorder=new MediaRecorder(this.stream,{mimeType:mime,videoBitsPerSecond:this.longEdge===3840?65000000:17000000});this.chunks=[];
    this.recorder.ondataavailable=e=>{if(e.data.size)this.chunks.push(e.data);};
    this.recorder.onstop=async()=>{
      this.active=false;this.saving=true;this.stopped=performance.now();this.toolbar.hidden=true;this.stream.getTracks().forEach(t=>t.stop());
      const renderSize={width:this.renderer.domElement.width,height:this.renderer.domElement.height};this.onResolution(0);
      this.onStatus('正在保存完整网页录制');
      const blob=new Blob(this.chunks,{type:this.recorder.mimeType});
      const ext=this.recorder.mimeType.includes('mp4')?'mp4':'webm';
      const result=await saveMedia(blob,`入画汴京_完整网页操作.${ext}`);
      const journal={video:result,seconds:(this.stopped-this.started)/1000,width:this.canvas.width,height:this.canvas.height,renderSize,viewport:{width:this.width,height:this.height},requestedCaptureFps:60,targetOutputFps:24,requestedVideoBitsPerSecond:this.recorder.videoBitsPerSecond,frames:this.frames,events:this.events,method:'真实 WebGL 连续画面 + 实际 DOM 界面状态；WebGL 与界面均按目标像素原生采集，鼠标与点击提示来自实际输入。'};
      await saveMedia(new Blob([JSON.stringify(journal,null,2)],{type:'application/json'}),'入画汴京_完整网页操作_日志.json');
      this.onStatus(`完整网页录制已保存 · ${(blob.size/1048576).toFixed(1)} MB`);this.canvas=null;this.chunks=[];this.saving=false;
    };
    this.toolbar.hidden=false;this.events=[];this.frames=0;this.started=performance.now();this.active=true;this.pending=true;
    this.recorder.start(1000);this.onStatus(`完整网页录制已开始 · ${this.canvas.width} × ${this.canvas.height}`);
  }
  stop(){if(this.recorder?.state==='recording')this.recorder.stop();}
  async snapshot(){
    if(this.busy)return;this.busy=true;this.pending=false;
    try{
      const main=document.getElementById('interface');
      this.uiImage=await toCanvas(main,{...this.options,width:this.width,height:this.height,filter:el=>el.id!=='hotspots'});
      this.dialogImages=[];
      for(const dialog of document.querySelectorAll('dialog[open]')){
        const r=dialog.getBoundingClientRect();
        const options={...this.options,width:r.width,height:r.height,style:{position:'relative',margin:'0',inset:'auto',maxHeight:'none',maxWidth:'none',overflow:'hidden'}};
        let img;
        if(dialog.id==='reference-dialog'){
          // SVG 克隆需要显式还原滚动偏移，原页面不做任何临时改动。
          const url=await toSvg(dialog,options),xml=new DOMParser().parseFromString(decodeURIComponent(url.slice(url.indexOf(',')+1)),'image/svg+xml');
          const original=dialog.querySelector('.scroll-window'),copy=xml.querySelector('.scroll-window');
          if(copy?.firstElementChild)copy.firstElementChild.style.transform=`translateX(${-original.scrollLeft}px)`;
          const picture=new Image();picture.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(new XMLSerializer().serializeToString(xml));await picture.decode();
          img=document.createElement('canvas');img.width=Math.round(r.width*this.scale);img.height=Math.round(r.height*this.scale);img.getContext('2d').drawImage(picture,0,0,img.width,img.height);
        }else img=await toCanvas(dialog,options);
        this.dialogImages.push({img,x:r.x,y:r.y,width:r.width,height:r.height,id:dialog.id});
      }
      this.lastSnapshot=performance.now();
    }catch(e){console.error('完整界面采集失败',e);this.onStatus('界面采集失败，请结束录制后重试');}
    finally{this.busy=false;}
  }
  frame(now){
    if(!this.active||!this.canvas)return;
    if(innerWidth!==this.width||innerHeight!==this.height){this.stop();return;}
    const elapsed=(now-this.started)/1000;
    this.toolbar.querySelector('span').textContent=`界面录制 ${Math.floor(elapsed/60).toString().padStart(2,'0')}:${Math.floor(elapsed%60).toString().padStart(2,'0')}`;
    if((this.pending&&now-this.lastSnapshot>240)||now-this.lastSnapshot>1500)this.snapshot();
    const ctx=this.ctx,w=this.canvas.width,h=this.canvas.height,s=this.scale;
    ctx.setTransform(1,0,0,1,0,0);ctx.fillStyle='#172e29';ctx.fillRect(0,0,w,h);
    const v=this.renderer.domElement.getBoundingClientRect();ctx.drawImage(this.renderer.domElement,v.x*s,v.y*s,v.width*s,v.height*s);
    const uiVisible=!document.body.classList.contains('ui-hidden');
    if(uiVisible){
      const shade=ctx.createLinearGradient(0,0,0,h);shade.addColorStop(0,'rgba(225,231,219,.62)');shade.addColorStop(.16,'rgba(225,231,219,0)');shade.addColorStop(.71,'rgba(15,34,30,0)');shade.addColorStop(1,'rgba(15,34,30,.65)');ctx.fillStyle=shade;ctx.fillRect(0,0,w,h);
      if(this.uiImage)ctx.drawImage(this.uiImage,0,0,w,h);
      const map=document.getElementById('minimap'),r=map.getBoundingClientRect();if(r.width)ctx.drawImage(map,r.x*s,r.y*s,r.width*s,r.height*s);
      for(const [el,img] of this.hotImages){if(!el.classList.contains('visible'))continue;const r=el.getBoundingClientRect();ctx.drawImage(img,r.x*s,r.y*s,r.width*s,r.height*s);}
    }
    // 弹窗后方保留清晰的三维场景，只做轻微压暗以突出正文。
    if(this.dialogImages.length){ctx.fillStyle='rgba(19,43,34,.20)';ctx.fillRect(0,0,w,h);for(const d of this.dialogImages){ctx.drawImage(d.img,d.x*s,d.y*s,d.width*s,d.height*s);}}
    if(this.cursor.seen){const p=this.cursor;ctx.save();ctx.scale(s,s);ctx.translate(p.x,p.y);const age=(now-p.pulse)/650;if(age>=0&&age<1){ctx.strokeStyle=`rgba(231,171,92,${1-age})`;ctx.lineWidth=2;ctx.beginPath();ctx.arc(0,0,10+age*17,0,Math.PI*2);ctx.stroke();}ctx.fillStyle=p.down?'#dfac6a':'#fff8e6';ctx.strokeStyle='#233e3a';ctx.lineWidth=1.2;ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(0,21);ctx.lineTo(5.5,16);ctx.lineTo(10,25);ctx.lineTo(14,23);ctx.lineTo(9.5,14.5);ctx.lineTo(17,14.5);ctx.closePath();ctx.fill();ctx.stroke();ctx.restore();}
    this.frames++;if(elapsed>900)this.stop();
  }
}
