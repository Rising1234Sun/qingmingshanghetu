"""整理浏览器实际录制的文件：保留视频编码，校正混音响度并生成封面。"""
from pathlib import Path
import subprocess,json,re,hashlib
from PIL import Image,ImageDraw,ImageFont
import imageio_ffmpeg

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/web';ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
raw=max(OUT.glob('入画汴京_网页实录_20*.mp4'),key=lambda p:p.stat().st_mtime)
def run(args):return subprocess.run([ffmpeg,'-hide_banner','-y',*map(str,args)],capture_output=True,text=True,check=True)
raw_info=subprocess.run([ffmpeg,'-hide_banner','-i',str(raw)],capture_output=True,text=True).stderr
analysis=run(['-i',raw,'-vn','-af','loudnorm=I=-14:TP=-1:LRA=11:print_format=json','-f','null','-'])
numbers=json.loads(analysis.stderr[analysis.stderr.rfind('{'):analysis.stderr.rfind('}')+1])
af=(f"loudnorm=I=-14:TP=-1:LRA=11:measured_I={numbers['input_i']}:measured_TP={numbers['input_tp']}:"
    f"measured_LRA={numbers['input_lra']}:measured_thresh={numbers['input_thresh']}:offset={numbers['target_offset']}:linear=true")
movie=OUT/'入画汴京_网页版展示.mp4'
run(['-i',raw,'-map','0:v:0','-map','0:a:0','-c:v','copy','-af',af,'-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',movie])
run(['-i',raw,'-map','0:v:0','-c:v','copy','-an','-movflags','+faststart',OUT/'入画汴京_无配乐素材.mp4'])
verify=run(['-v','error','-i',movie,'-f','null','-'])
final_audio=run(['-i',movie,'-vn','-af','loudnorm=I=-14:TP=-1:print_format=json','-f','null','-'])
final_numbers=json.loads(final_audio.stderr[final_audio.stderr.rfind('{'):final_audio.stderr.rfind('}')+1])
for second in [3,15,26,38,48,57]:
    run(['-ss',second,'-i',movie,'-frames:v','1',OUT/f'实录选帧_{second:02}秒.jpg'])
cover=Image.open(OUT/'实录选帧_26秒.jpg').convert('RGBA')
shade=Image.new('RGBA',cover.size);pixels=shade.load();w,h=cover.size
for y in range(h):
    opacity=int(max(0,1-y/650)*125+max(0,(y-h+440)/440)*110)
    ImageDraw.Draw(shade).line((0,y,w,y),fill=(20,35,30,opacity))
cover=Image.alpha_composite(cover,shade);d=ImageDraw.Draw(cover)
font=ROOT/'assets/fonts/NotoSerifCJKsc-Regular.otf'
d.text((92,143),'清明上河图',font=ImageFont.truetype(str(font),81),fill='#f1e7ca')
d.line((95,275,417,275),fill='#b79b6c',width=2)
d.text((95,309),'入画 · 汴京',font=ImageFont.truetype(str(font),43),fill='#e1d9bd')
d.rectangle((91,h-196,145,h-141),fill='#a14b35');d.text((104,h-194),'宋',font=ImageFont.truetype(str(font),32),fill='#f0e7d3')
d.text((165,h-190),'浏览器实时三维重建',font=ImageFont.truetype(str(font),30),fill='#eee7d1')
cover.convert('RGB').save(OUT/'抖音竖屏封面.jpg',quality=95)
report={'raw':raw.name,'video':movie.name,'metadata':raw_info,'video_processing':'视频码流直接复制，无补帧、无 AI 增强；仅进行音频响度整理和 MP4 faststart 封装。',
        'decode_errors':verify.stderr,'audio_final':final_numbers,'sha256':hashlib.sha256(movie.read_bytes()).hexdigest()}
(ROOT/'docs/网页实录验收.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'file':movie.name,'bytes':movie.stat().st_size,'audio_lufs':final_numbers['input_i'],'true_peak':final_numbers['input_tp'],'decode_ok':not verify.stderr},ensure_ascii=False),flush=True)
