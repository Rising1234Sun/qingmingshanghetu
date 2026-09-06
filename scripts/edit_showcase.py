"""将真实网页操作实录剪成 120 秒，保留全页面，并生成带细节放大的竖屏版。"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json, subprocess, hashlib, argparse
import numpy as np
import soundfile as sf
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/showcase';OUT.mkdir(exist_ok=True)
WORK=OUT/'剪辑素材';WORK.mkdir(exist_ok=True)
FF=imageio_ffmpeg.get_ffmpeg_exe();FONT=ROOT/'assets/fonts/NotoSerifCJKsc-Regular.otf'
MAIN=json.loads((ROOT/'docs/完整功能录制_原始.json').read_text())
REF=json.loads((ROOT/'docs/原卷交互补录.json').read_text())
# 裁切只用于竖屏版下方的细节窗口；上方始终保留同一时刻完整页面。
rows=[
 ('main',2,5,'一幅可以走进去的长卷','完整页面与三维场景同时呈现','页面全貌',(680,145,1000,700)),
 ('main',8.5,6,'拖动鼠标，自由环视','换个角度，观察虹桥与沿岸建筑','鼠标环视',(420,140,1000,700)),
 ('main',16.5,5,'滚轮拉近，细看结构','舟船、桥板与人物都在三维空间中','滚轮缩放',(470,160,1000,700)),
 ('main',24.8,8,'点击标签，打开简介','「虹桥」的结构、原画依据与细节','标签与简介',(1285,430,620,434)),
 ('main',43.7,5,'汴河漕运，一键抵达','点击底部景点，镜头移动到河面','景点切换',(400,140,1000,700)),
 ('main',51.3,6,'漕船也有自己的介绍','查看船体、货物、水波与动画说明','舟船细节',(1285,315,620,434)),
 ('main',101.2,6,'茶肆、市井与人间烟火','点击「茶肆」，了解沿岸街市','市井简介',(1285,350,620,434)),
 ('main',126.9,6,'点一下「走近看看」','从简介直接进入对应的街市场景','近看市井',(420,155,1000,700)),
 ('main',133.8,5,'街巷营造，灰瓦连檐','第四景：木窗、屋瓦和院落层次','街巷与建筑',(350,100,1000,700)),
 ('main',139.4,5,'城阙远眺，一城展开','第五景：拉开尺度，查看街区全貌','城市全景',(400,100,1100,770)),
 ('main',149.9,5,'在舆图上选择目的地','点击右上角地图，移动观察位置','地图定位',(1050,100,840,588)),
 ('main',160.6,6,'把时辰切换到清晨','同一座虹桥，比较日光与阴影','清晨光照',(1000,180,840,588)),
 ('main',169.7,6,'再看一眼汴京暮色','光照切换后，回到完整场景观察','暮色光照',(700,160,1000,700)),
 ('main',190.4,4,'画质、动画、标记均可调','保留真实设置面板与运行读数','画面设置',(1285,355,620,434)),
 ('main',199.6,5,'打开线框，检查模型','从几何结构观察三维重建结果','线框结构',(420,140,1000,700)),
 ('main',220.4,2,'原卷对照，有据可查','在网页中打开张择端的原画长卷','原卷对照',(240,335,1300,910)),
 ('ref',20,6,'横向浏览，展开原卷','保留完整页面，同时放大画中细节','横向浏览',(370,340,1200,840)),
 ('main',290.1,5,'复原依据，也可以查看','作品说明写明建模方式与推定范围','关于复原',(205,365,1120,784)),
 ('main',307,6,'把成果带走，继续创作','实际点击按钮，保存当前高清画面','拍摄与导出',(1285,370,620,434)),
 ('main',331.1,6,'开启音乐，开始自动巡游','按钮、状态与移动镜头一起展示','自动巡游',(650,200,1000,700)),
 ('main',338.2,6,'隐藏界面，随镜入画','保留自由操作，也支持纯净画面','纯净画面',(520,120,1000,700)),
 ('main',354,6,'入画 · 汴京','打开网页，就能亲自检验作品','虹桥巡游',(490,115,1000,700)),
]
segments=[];elapsed=0
for key,ss,d,title,sub,label,crop in rows:
    x,y,w,h=crop
    # 焦点窗口永远不超出实际画面边界。
    y=min(y,1080-h);x=min(x,1920-w)
    segments.append(dict(source=key,in_seconds=ss,duration=d,start=elapsed,end=elapsed+d,title=title,subtitle=sub,label=label,crop=[x,y,w,h]))
    elapsed+=d
assert elapsed==120,elapsed

def run(args):
    p=subprocess.run([FF,'-hide_banner','-y',*map(str,args)],capture_output=True,text=True)
    if p.returncode:raise RuntimeError(p.stderr[-4500:])
    return p

def font(size):return ImageFont.truetype(str(FONT),size)
def text(draw,pos,s,size=30,fill='#ece6d0'):draw.text(pos,s,font=font(size),fill=fill)
def stamp(t):return f'{int(t)//60:02}:{int(t)%60:02}'

def card(seg,i,portrait=True):
    if portrait:
        im=Image.new('RGB',(1080,1920));d=ImageDraw.Draw(im)
        for y in range(1920):
            q=y/1920;d.line((0,y,1080,y),fill=(int(18+7*(1-q)),int(41+9*(1-q)),int(37+8*(1-q))))
        d.rectangle((52,56,119,123),fill='#9b4c37',outline='#b78c63',width=1);text(d,(67,58),'入',38);text(d,(151,62),'汴京 · 交互作品实录',26, '#bdbf9f')
        text(d,(49,132),'清明上河图',68);text(d,(55,227),'把一幅长卷，变成可探索的三维世界',28,'#b8c0ab')
        text(d,(42,297),'完整网页',23,'#ccc9af');text(d,(793,301),'实际操作录制',21,'#9eab98')
        d.rectangle((38,344,1042,910),outline='#829078',width=2)
        text(d,(42,938),'细节放大 · '+seg['label'],24,'#d4ba8a');text(d,(900,940),f'{i+1:02} / {len(segments):02}',21,'#9aa78f')
        d.rectangle((38,988,1042,1692),outline='#a58e63',width=2)
        size=min(40,int(990/max(len(seg['title']),1)));text(d,(45,1730),seg['title'],size)
        size=min(27,int(990/max(len(seg['subtitle']),1)));text(d,(48,1791),seg['subtitle'],size,'#b5bda7')
        d.line((44,1854,1035,1854),fill='#62735d',width=1)
        text(d,(45,1870),'入画 · 汴京  /  两分钟功能展示',21,'#899982');text(d,(875,1870),stamp(seg['start']),21,'#d0bd93')
        # 固定刻度说明当前演示进度，完整视频仍是连续的 120 秒。
        for j in range(len(segments)):
            xa=47+j*45;d.rectangle((xa,1835,xa+31,1838),fill='#ceb37a' if j<=i else '#365044')
    else:
        im=Image.new('RGBA',(1920,1080));d=ImageDraw.Draw(im)
        title=f'{i+1:02}  /  {seg["title"]}';width=min(1215,int(d.textlength(title,font=font(29)))+54)
        d.rounded_rectangle((63,797,63+width,856),radius=5,fill=(24,47,40,232),outline=(202,187,149,120),width=1)
        text(d,(86,806),title,29)
    path=WORK/f'版式_{"竖" if portrait else "横"}_{i:02}.png';im.save(path);return path

def render_clip(item):
    i,seg,kind=item;portrait=kind=='竖';src=MAIN if seg['source']=='main' else REF
    raw=src['video']['path'];base=card(seg,i,portrait);out=WORK/f'{kind}_{i:02}.mp4'
    if portrait:
        x,y,w,h=seg['crop'];fx=(f'[0:v]fps=24,split=2[full][zoom];[full]scale=1000:562:flags=lanczos[page];'
            f'[zoom]crop={w}:{h}:{x}:{y},scale=1000:700:flags=lanczos[detail];'
            '[1:v][page]overlay=40:346:shortest=1[a];[a][detail]overlay=40:990:shortest=1,setsar=1[v]')
    else:fx='[0:v]fps=24[page];[page][1:v]overlay=0:0:shortest=1,setsar=1[v]'
    run(['-v','warning','-ss',seg['in_seconds'],'-i',raw,'-loop','1','-framerate','24','-i',base,
         '-filter_complex_threads','2','-filter_complex',fx,'-map','[v]','-an','-frames:v',seg['duration']*24,
         '-c:v','libx264','-preset','fast','-crf','18','-threads','3','-pix_fmt','yuv420p','-movflags','+faststart',out])
    print(f'{kind}屏 {i+1:02}/{len(segments)} {seg["title"]}',flush=True)
    return out

def soundtrack():
    music,rate=sf.read(ROOT/'output/audio/两分钟功能演示/配乐环境混音.wav',dtype='float32',always_2d=True)
    assert rate==48000 and len(music)==120*rate
    clicks=np.zeros_like(music);rng=np.random.default_rng(956)
    for seg in segments:
        journal=MAIN if seg['source']=='main' else REF
        for e in journal['events']:
            if e['type']!='click' or e['label']=='页面' or not(seg['in_seconds']<=e['seconds']<seg['in_seconds']+seg['duration']):continue
            t=seg['start']+e['seconds']-seg['in_seconds'];n=int(t*rate);x=np.arange(int(.07*rate))/rate
            a=(np.sin(2*np.pi*640*x)*np.exp(-x*110)+rng.normal(0,.15,len(x))*np.exp(-x*90))*.055
            pan=(e.get('x',640)/1280-.5)*.45
            clicks[n:n+len(x),0]+=a[:len(clicks)-n]*(1-pan);clicks[n:n+len(x),1]+=a[:len(clicks)-n]*(1+pan)
    sf.write(OUT/'操作点击音.wav',clicks,rate,subtype='PCM_24')
    premix=OUT/'两分钟配乐_未母带.wav';sf.write(premix,music*.80+clicks,rate,subtype='PCM_24')
    p=run(['-i',premix,'-af','loudnorm=I=-14:TP=-1:LRA=11:print_format=json','-f','null','-'])
    data=json.loads(p.stderr[p.stderr.rfind('{'):p.stderr.rfind('}')+1]);
    af=(f'loudnorm=I=-14:TP=-1:LRA=11:measured_I={data["input_i"]}:measured_TP={data["input_tp"]}:'
        f'measured_LRA={data["input_lra"]}:measured_thresh={data["input_thresh"]}:offset={data["target_offset"]}:linear=true')
    sound=OUT/'两分钟配乐与点击音.wav';run(['-v','warning','-i',premix,'-af',af,'-ar',rate,'-c:a','pcm_s24le',sound]);return sound

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--preview',action='store_true');args=ap.parse_args()
    (ROOT/'docs/两分钟功能演示剪辑表.json').write_text(json.dumps({'duration':120,'fps':24,'segments':segments},ensure_ascii=False,indent=2))
    if args.preview:
        for i in [0,3,13,16]:
            seg=segments[i];base=card(seg,i,True);raw=(MAIN if seg['source']=='main' else REF)['video']['path'];frame=WORK/f'预览源_{i}.png'
            run(['-v','error','-ss',seg['in_seconds']+min(3,seg['duration']-.5),'-i',raw,'-frames:v','1',frame])
            im=Image.open(base);source=Image.open(frame);im.paste(source.resize((1000,562),Image.Resampling.LANCZOS),(40,346));x,y,w,h=seg['crop'];im.paste(source.crop((x,y,x+w,y+h)).resize((1000,700),Image.Resampling.LANCZOS),(40,990));im.save(OUT/f'竖屏排版预览_{i:02}.jpg',quality=94)
        print('版式预览完成');return
    sound=soundtrack()
    jobs=[(i,seg,kind) for i,seg in enumerate(segments) for kind in ['横','竖']]
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(render_clip,jobs))
    reports=[]
    for kind,name in [('横','入画汴京_两分钟完整网页演示_横屏'),('竖','入画汴京_两分钟功能展示_抖音竖屏')]:
        concat=WORK/f'拼接_{kind}.txt';concat.write_text(''.join(f"file '{kind}_{i:02}.mp4'\n" for i in range(len(segments))))
        mute=OUT/f'{name}_无配乐.mp4';movie=OUT/f'{name}.mp4'
        run(['-v','warning','-f','concat','-safe','0','-i',concat,'-c','copy','-movflags','+faststart',mute])
        run(['-v','warning','-i',mute,'-i',sound,'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-t','120','-movflags','+faststart',movie])
        check=run(['-v','error','-i',movie,'-f','null','-'])
        meta=subprocess.run([FF,'-hide_banner','-i',str(movie)],capture_output=True,text=True).stderr
        am=run(['-i',movie,'-vn','-af','loudnorm=I=-14:TP=-1:print_format=json','-f','null','-'])
        av=json.loads(am.stderr[am.stderr.rfind('{'):am.stderr.rfind('}')+1])
        reports.append(dict(file=movie.name,bytes=movie.stat().st_size,sha256=hashlib.sha256(movie.read_bytes()).hexdigest(),decode_errors=check.stderr,metadata=meta,lufs=av['input_i'],true_peak=av['input_tp']))
        for t in [3,20,39,65,76,87,99,117]:run(['-v','error','-ss',t,'-i',movie,'-frames:v','1',OUT/f'{kind}屏验收_{t:03}.jpg'])
        print(f'{movie.name} 完成，解码检查通过。',flush=True)
    (ROOT/'docs/两分钟功能视频验收.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2))
    lines=[]
    def srt(t):return f'{int(t)//3600:02}:{int(t)//60%60:02}:{int(t)%60:02},000'
    for i,s in enumerate(segments):lines.append(f'{i+1}\n{srt(s["start"])} --> {srt(s["end"])}\n{s["title"]}\n{s["subtitle"]}\n')
    (OUT/'两分钟功能展示字幕.srt').write_text('\n'.join(lines))
    print('两分钟横竖屏、无配乐版本、字幕和音轨均已完成。',flush=True)
if __name__=='__main__':main()
