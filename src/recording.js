export function saveBlob(blob,name){const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download=name;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),15000);}

export async function saveMedia(blob,name){
  // 只有回环地址尝试本地保存；公开静态站点直接下载，不上传录像。
  if(location.hostname==='127.0.0.1'){
    try{const response=await fetch('/__export',{method:'POST',headers:{'Content-Type':blob.type},body:blob});if(response.ok)return await response.json();}catch{}
  }
  saveBlob(blob,name);return null;
}

export class Capture {
  constructor(renderer,audio,onStop){this.renderer=renderer;this.audio=audio;this.onStop=onStop;this.active=false;this.context=null;this.source=null;this.destination=null;}
  async prepareAudio(){
    if(!this.context){const AudioContext=window.AudioContext||window.webkitAudioContext;this.context=new AudioContext();this.source=this.context.createMediaElementSource(this.audio);this.destination=this.context.createMediaStreamDestination();this.source.connect(this.context.destination);this.source.connect(this.destination);}
    await this.context.resume();
  }
  async start(){
    if(!window.MediaRecorder||!this.renderer.domElement.captureStream)throw new Error('此浏览器不支持直接录制，请使用 Chrome、Edge 或系统录屏。');
    await this.prepareAudio();
    this.audio.currentTime=0;this.audio.muted=false;await this.audio.play();
    const canvasStream=this.renderer.domElement.captureStream(30);
    this.stream=new MediaStream([...canvasStream.getVideoTracks(),...this.destination.stream.getAudioTracks()]);
    const mime=['video/mp4;codecs=avc1.42E01E,mp4a.40.2','video/mp4','video/webm;codecs=vp9,opus','video/webm;codecs=vp8,opus','video/webm'].find(t=>MediaRecorder.isTypeSupported(t));
    if(!mime)throw new Error('浏览器没有可用的视频编码器，请使用系统录屏。');
    this.recorder=new MediaRecorder(this.stream,{mimeType:mime,videoBitsPerSecond:14000000,audioBitsPerSecond:192000});
    this.chunks=[];this.recorder.ondataavailable=e=>{if(e.data.size)this.chunks.push(e.data);};
    this.recorder.onerror=e=>this.onStop(e.error?.message||'录制失败');
    this.recorder.onstop=async()=>{const blob=new Blob(this.chunks,{type:this.recorder.mimeType});const ext=this.recorder.mimeType.includes('mp4')?'mp4':'webm';await saveMedia(blob,`入画汴京_网页实录_${new Date().toISOString().slice(0,10)}.${ext}`);this.stream.getVideoTracks().forEach(t=>t.stop());this.active=false;this.onStop(null,blob.size);};
    this.recorder.start(1000);this.active=true;
  }
  stop(){if(this.active&&this.recorder.state!=='inactive')this.recorder.stop();}
}
