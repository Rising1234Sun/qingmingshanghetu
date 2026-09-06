"""完整序列校验、原画转场、中文字幕、剪辑与编码。"""
from pathlib import Path
import argparse,json,subprocess,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter,ImageEnhance
import imageio_ffmpeg

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output';W,H=1080,1920;FPS=24
FONT=ROOT/'assets/fonts/NotoSerifCJKsc-Regular.otf'

def font(size):return ImageFont.truetype(str(FONT),size)
def smooth(v):v=max(0,min(1,v));return v*v*(3-2*v)

def paper_frame():
    rng=np.random.default_rng(1103)
    noise=rng.normal(0,1.4,(H,W,1))+np.sin(np.arange(H)[:,None,None]*1.7)*.55
    tone=np.array([222,207,175])[None,None,:]+noise
    p=Image.fromarray(np.clip(tone,0,255).astype('uint8'),'RGB')
    original=Image.open(ROOT/'references/张择端清明上河图原卷.jpg')
    # 两段原画居于画面中心，完整保留虹桥的辨识特征。
    for rect,yy in [((17500,0,23100,1800),590),((8400,0,14000,1800),1030)]:
        strip=original.crop(rect).resize((W,347),Image.Resampling.LANCZOS)
        strip=ImageEnhance.Contrast(strip).enhance(1.10)
        mask=np.ones((347,W),np.float32)
        for k in range(48):mask[k]*=k/48;mask[-k-1]*=k/48
        p.paste(strip,(0,yy),Image.fromarray((mask*235).astype('uint8')))
    d=ImageDraw.Draw(p)
    d.text((92,190),'清明上河图',font=font(104),fill='#3e3c30')
    d.line((96,342,300,342),fill='#9b503d',width=3)
    d.text((96,388),'入画 · 汴京',font=font(52),fill='#665b45')
    d.text((100,1525),'北宋 · 张择端本',font=font(34),fill='#756b53')
    d.text((100,1585),'三维艺术复原',font=font(28),fill='#82765d')
    d.rectangle((874,1497,952,1604),outline='#a05242',width=3)
    d.text((894,1510),'入',font=font(42),fill='#a05242');d.text((894,1550),'画',font=font(42),fill='#a05242')
    return p

def title_layer():
    im=Image.new('RGBA',(W,H),(0,0,0,0));a=np.zeros((H,W,4),np.uint8)
    a[:,:,:3]=[17,26,24]
    a[:,:,3]=(np.clip((np.arange(H)[:,None]-1000)/650,0,.86)*255).astype('uint8')
    im=Image.fromarray(a);d=ImageDraw.Draw(im)
    d.text((85,1270),'清明上河图',font=font(108),fill='#f1e7cb',stroke_width=1)
    d.line((90,1430,307,1430),fill='#cdb887',width=3)
    d.text((90,1480),'入画 · 汴京',font=font(48),fill='#eee4c9')
    d.text((92,1575),'三维艺术复原',font=font(28),fill='#d3c9ad')
    return im

def prepare_frame(im,index,paper,title):
    t=index/FPS
    # 双向纸本溶解结合真实三维画面的连续运动。
    if t<4.5:
        amount=1-smooth((t-1.3)/3.2)
        zoom=1+.035*t/4.5;ww=round(W/zoom);hh=round(H/zoom)
        moving=paper.crop(((W-ww)//2,(H-hh)//2,(W+ww)//2,(H+hh)//2)).resize((W,H),Image.Resampling.BICUBIC)
        if amount>0:im=Image.blend(im,moving,amount)
    if t>=53.5:
        amount=smooth((t-53.5)/5.8)*.92
        if amount>0:im=Image.blend(im,paper,amount)
    if 48.5<t<53.5:
        a=smooth((t-48.5)/1.2)*(1-smooth((t-52.3)/1.2));lay=title.copy();lay.putalpha(lay.getchannel('A').point(lambda v:round(v*a)))
        im=Image.alpha_composite(im.convert('RGBA'),lay).convert('RGB')
    return im

def run(cmd):subprocess.run(cmd,check=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--preview',action='store_true');args=ap.parse_args()
    ff=imageio_ffmpeg.get_ffmpeg_exe();OUT.mkdir(exist_ok=True)
    if args.preview:
        paths=[ROOT/'renders/motion_test'/f'{n:04d}.png' for n in range(480,552)]
        if not all(p.exists() for p in paths):raise RuntimeError('3 秒样片尚未渲染完整')
        run([ff,'-y','-v','error','-framerate','24','-start_number','480','-i',str(ROOT/'renders/motion_test/%04d.png'),'-ss','19.958333','-i',str(OUT/'audio/配乐环境混音.wav'),'-frames:v','72','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-t','3','-movflags','+faststart',str(OUT/'虹桥_3秒动作样片.mp4')])
        return
    paths=[ROOT/'renders/frames'/f'{n:04d}.png' for n in range(1,1441)]
    missing=[p.name for p in paths if not p.exists()]
    if missing:raise RuntimeError(f'尚缺少 {len(missing)} 帧：'+', '.join(missing[:8]))
    paper=paper_frame();title=title_layer();paper.save(OUT/'画卷片头.png')
    frames=OUT/'frames';frames.mkdir(exist_ok=True)
    movie=OUT/'清明上河图_60秒_无声版.mp4'
    cmd=[ff,'-y','-v','error','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}','-framerate','24','-i','-',
         '-vf','scale=out_color_matrix=bt709:out_range=tv,format=yuv420p','-c:v','libx264','-preset','medium','-crf','17',
         '-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-color_range','tv','-an','-movflags','+faststart',str(movie)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for i,p in enumerate(paths):
            with Image.open(p) as src:
                if src.size!=(W,H):raise RuntimeError(f'{p.name} 分辨率错误：{src.size}')
                im=prepare_frame(src.convert('RGB'),i,paper,title)
            im.save(frames/f'{i+1:04d}.png',compress_level=3)
            proc.stdin.write(im.tobytes())
            if i%120==0:print('合成帧',i+1,flush=True)
    finally:proc.stdin.close()
    if proc.wait()!=0:raise RuntimeError('视频编码失败')
    run([ff,'-y','-v','error','-i',str(movie),'-i',str(OUT/'audio/配乐环境混音.wav'),'-c:v','copy','-c:a','aac','-b:a','320k','-ar','48000','-t','60','-movflags','+faststart',str(OUT/'清明上河图_60秒_配乐版.mp4')])
    shots=json.loads((ROOT/'docs/镜头表.json').read_text())
    for s in shots:
        run([ff,'-y','-v','error','-ss',str((s['start']-1)/24),'-i',str(movie),'-frames:v',str(s['frames']),'-c:v','libx264','-preset','medium','-crf','17','-an','-movflags','+faststart',str(OUT/'shots'/f'{s["id"]}.mp4')])
    best=Image.open(ROOT/'renders/frames/1140.png').convert('RGBA');cover=Image.alpha_composite(best,title);cover.convert('RGB').save(OUT/'抖音竖屏封面.jpg',quality=96)
    (OUT/'抖音发布文案.txt').write_text('清明上河图里的汴京，流动起来了。\n基于张择端本的三维艺术复原。\n\n#清明上河图 #国风 #3D动画 #传统文化\n')
    thumbs=Image.new('RGB',(1200,1440),'#192622');d=ImageDraw.Draw(thumbs)
    for i,n in enumerate([80,230,520,810,1140,1360]):
        im=Image.open(frames/f'{n:04d}.png').resize((400,711));thumbs.paste(im,((i%3)*400,(i//3)*720))
    thumbs.save(OUT/'全片分镜预览.jpg',quality=92)
    print('配乐成片、无声版、分镜视频、序列与封面完成',flush=True)

if __name__=='__main__':main()
