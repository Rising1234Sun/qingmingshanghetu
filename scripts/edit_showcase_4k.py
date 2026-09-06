"""使用新录制的原生 4K 网页素材，重剪两分钟高清功能演示。"""
from pathlib import Path
import argparse, hashlib, json, re, subprocess
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/showcase/4K重制'
WORK = OUT / '剪辑素材'
WORK.mkdir(parents=True, exist_ok=True)
FF = imageio_ffmpeg.get_ffmpeg_exe()
COLOR_TAGS = 'h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0'
FONT = ROOT / 'assets/fonts/NotoSerifCJKsc-Regular.otf'
JOURNAL = json.loads((ROOT / 'docs/4K完整网页录制_原始.json').read_text())
SOURCE = Path(JOURNAL['video']['path'])
if not SOURCE.is_absolute():
    SOURCE = ROOT / SOURCE
if not SOURCE.exists():
    SOURCE = ROOT / 'output/web' / Path(JOURNAL['video']['path']).name
assert JOURNAL['renderSize'] == {'width': 3840, 'height': 2160}

# 下方窗口与上方完整网页取自相同时间；坐标均为新源视频的真实像素。
# 画面切换的等待被剪除，保留实际鼠标输入及其结果。
ROWS = [
    (3, 5, '打开网页，先看整体', '完整界面与三维场景同时呈现', '页面全貌', (1300, 40, 1840, 1728)),
    (22.5, 6, '拖动鼠标，自由环视', '换个角度，观察虹桥与两岸建筑', '鼠标环视', (1130, 40, 1840, 1728)),
    (30.7, 5, '滚轮拉近，细看结构', '桥板、栏杆与屋瓦的真实几何细节', '滚轮缩放', (1360, 40, 1840, 1728)),
    (42.9, 8, '点击标签，打开简介', '虹桥形制、原画依据与木构细节', '虹桥简介', (2176, 276, 1640, 1540)),
    (102.8, 5, '汴河漕运，一键抵达', '点击底部景点，镜头移动到河面', '场景切换', (980, 20, 1840, 1728)),
    (108.0, 6, '漕船也有自己的介绍', '船体、货物、水波与关节动画', '漕船简介', (2516, 488, 1280, 1202)),
    (141.2, 6, '茶肆、市井与人间烟火', '点击标签，了解沿岸街市', '茶肆简介', (2516, 506, 1280, 1202)),
    (155.1, 6, '点一下「走近看看」', '从简介进入对应的三维街市场景', '近看市井', (1470, 30, 1840, 1728)),
    (168.6, 5, '街巷营造，灰瓦连檐', '木窗、屋瓦和院落的空间层次', '街巷细节', (870, 25, 1840, 1728)),
    (182.5, 5, '城阙远眺，一城展开', '拉开尺度，查看建筑与街区关系', '城市全景', (1130, 20, 1840, 1728)),
    (198.7, 5, '在舆图上选择目的地', '点击右上角地图，移动观察位置', '地图定位', (2360, 380, 1450, 1362)),
    (220.4, 6, '把时辰切换到清晨', '比较同一场景的日光与阴影', '清晨光照', (1790, 80, 2048, 1924)),
    (243.0, 6, '再看一眼汴京暮色', '保留设置按钮与光照变化过程', '暮色光照', (1790, 80, 2048, 1924)),
    (279.8, 4, '画质、动画、标记均可调', '画面设置与当前实际运行读数', '画面设置', (1790, 80, 2048, 1924)),
    (300.9, 5, '打开线框，检查模型', '从几何结构观察三维重建结果', '线框结构', (1130, 40, 1840, 1728)),
    (325.3, 2, '原卷对照，有据可查', '在网页中打开张择端的原画长卷', '原卷对照', (1000, 160, 1840, 1728)),
    (334.0, 6, '横向浏览，展开原卷', '真实滚动，查看长卷中的更多细节', '横向浏览', (1000, 160, 1840, 1728)),
    (356.5, 5, '复原依据，也可以查看', '明确区分原画依据与空间推定', '复原说明', (400, 466, 1560, 1466)),
    (388.0, 6, '把成果带走，继续创作', '实际点击按钮，保存当前高清画面', '拍摄与导出', (1790, 74, 2048, 1924)),
    (406.4, 6, '开启音乐，开始自动巡游', '保留音乐开关、状态与移动镜头', '自动巡游', (1260, 40, 1840, 1728)),
    (420.5, 6, '隐藏界面，随镜入画', '切换纯净画面，继续观察船与水面', '纯净画面', (1050, 110, 2048, 1924)),
    (432.0, 6, '入画 · 汴京', '打开网页，就能亲自检验运行效果', '虹桥巡游', (900, 60, 2048, 1924)),
]
SEGMENTS = []
elapsed = 0
for ss, duration, title, subtitle, label, crop in ROWS:
    x, y, w, h = crop
    assert x + w <= 3840 and y + h <= 2160
    SEGMENTS.append(dict(in_seconds=ss, duration=duration, start=elapsed, end=elapsed+duration,
                         title=title, subtitle=subtitle, label=label, crop=list(crop)))
    elapsed += duration
assert elapsed == 120


def run(args):
    result = subprocess.run([FF, '-hide_banner', '-y', *map(str, args)], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-5000:])
    return result


def card(seg, index):
    # 按最终 2160×3840 像素直接绘制字体与装饰，避免放大旧版 PNG。
    im = Image.new('RGB', (2160, 3840), '#18372e')
    draw = ImageDraw.Draw(im)
    def rect(box, **kwargs):
        draw.rectangle(tuple(round(n*2) for n in box), **kwargs)
    def text(pos, value, size=24, fill='#e8e7d5'):
        draw.text(tuple(round(n*2) for n in pos), value,
                  font=ImageFont.truetype(str(FONT), round(size*2)), fill=fill)
    rect((0, 0, 1080, 150), fill='#173329')
    rect((30, 31, 83, 85), fill='#934b36', outline='#b79a70', width=2)
    text((43, 30), '入', 33)
    text((105, 28), '汴京 · 交互网页实录', 23, '#b5bea5')
    text((106, 67), '清明上河图', 43)
    text((851, 43), '4K 采集', 24, '#d5bd88')
    text((30, 147), '完整网页 · 保留全部界面', 20, '#c1c8ae')
    rect((26, 182, 1054, 762), outline='#81927b', width=3)
    text((30, 778), '细节放大 · '+seg['label'], 22, '#d3bc8a')
    text((936, 779), f'{index+1:02} / 22', 19, '#b2bca1')
    rect((26, 816, 1054, 1782), outline='#a48f65', width=3)
    text((30, 1801), seg['title'], min(34, 1010/max(len(seg['title']), 1)))
    text((32, 1854), seg['subtitle'], min(24, 1010/max(len(seg['subtitle']), 1)), '#b8c3a7')
    for j in range(22):
        rect((30+j*47, 1903, 63+j*47, 1905), fill='#d0b47c' if j <= index else '#3e5944')
    out = WORK/f'原生4K版式_{index:02}.png'
    im.save(out)
    return out


def filter_graph(seg):
    x, y, w, h = seg['crop']
    return (f'[0:v]fps=24,split=2[whole][focus];'
            '[whole]scale=2048:1152:flags=lanczos[page];'
            f'[focus]crop={w}:{h}:{x}:{y},scale=2048:1924:flags=lanczos[detail];'
            '[1:v][page]overlay=56:368:shortest=1[a];'
            '[a][detail]overlay=56:1636:shortest=1,'
            'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,setsar=1[v]')


def render_clip(index):
    seg = SEGMENTS[index]
    output = WORK/f'竖屏4K_{index:02}.mp4'
    run(['-v','warning','-ss',seg['in_seconds'],'-i',SOURCE,
         '-loop','1','-framerate','24','-i',card(seg,index),
         '-filter_complex_threads','2','-filter_complex',filter_graph(seg),'-map','[v]',
         '-an','-frames:v',seg['duration']*24,'-c:v','libx264','-preset','medium',
         '-crf','13','-threads','4','-profile:v','high','-level:v','5.1',
         '-g','48','-keyint_min','24','-pix_fmt','yuv420p',
         '-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709',
         '-movflags','+faststart',output])
    print(f'4K {index+1:02}/22  {seg["title"]}', flush=True)
    return output


def preview():
    for i in [0,3,5,13,16,18,21]:
        seg = SEGMENTS[i]
        base = card(seg,i)
        source = WORK/f'4K源画面_{i:02}.png'
        run(['-v','error','-ss',seg['in_seconds']+min(3,seg['duration']-.3),'-i',SOURCE,'-frames:v','1',source])
        im = Image.open(base)
        frame = Image.open(source)
        im.paste(frame.resize((2048,1152),Image.Resampling.LANCZOS),(56,368))
        x,y,w,h = seg['crop']
        im.paste(frame.crop((x,y,x+w,y+h)).resize((2048,1924),Image.Resampling.LANCZOS),(56,1636))
        im.save(OUT/f'4K排版预览_{i:02}.png')
        im.resize((1080,1920),Image.Resampling.LANCZOS).save(OUT/f'手机预览_{i:02}.jpg',quality=96)
    print('原生 4K 版式预览完成',flush=True)


def metadata(path):
    return subprocess.run([FF,'-hide_banner','-i',str(path)],capture_output=True,text=True).stderr


def main():
    global SOURCE
    ap=argparse.ArgumentParser()
    ap.add_argument('--preview',action='store_true')
    ap.add_argument('--source',type=Path,help='指定本次 3840×2160 网页原始录像；新录像需同步调整 ROWS 时间线')
    ap.add_argument('--include-1080p',action='store_true',help='另外输出 1080P 缩小副本；默认只输出 4K')
    args=ap.parse_args()
    if args.source:
        SOURCE=args.source.expanduser().resolve()
    if not SOURCE.is_file():
        ap.error('没有找到原始录像。请用 --source 指定本地文件，并按新录像调整 ROWS 时间线。')
    source_meta=metadata(SOURCE)
    if not re.search(r'Video:.*\b3840x2160\b',source_meta):
        ap.error('此版式需要 3840×2160 的原始网页录像，请先确认源文件像素。')
    assert sum(s['duration'] for s in SEGMENTS)==120,'片段时长之和必须为 120 秒'
    for seg in SEGMENTS:
        x,y,w,h=seg['crop']
        assert x>=0 and y>=0 and x+w<=3840 and y+h<=2160,'裁切区域超出源画面'
    duration_match=re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)',source_meta)
    if not duration_match:
        ap.error('无法确认源录像时长')
    hours,minutes,seconds=map(float,duration_match.groups())
    duration=hours*3600+minutes*60+seconds
    if any(s['in_seconds']+s['duration']>duration+.05 for s in SEGMENTS):
        ap.error('剪辑时间超出源录像，请按新录像调整 ROWS 时间线')
    if args.preview:
        preview()
        return
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(render_clip,range(len(SEGMENTS))))
    concat=WORK/'4K竖屏拼接.txt'
    concat.write_text(''.join(f"file '竖屏4K_{i:02}.mp4'\n" for i in range(len(SEGMENTS))))
    master=OUT/'入画汴京_两分钟网页实测_4K竖屏_无配乐.mp4'
    upload=OUT/'入画汴京_两分钟网页实测_1080P高清上传版_无配乐.mp4'
    run(['-v','warning','-f','concat','-safe','0','-i',concat,'-c','copy','-bsf:v',COLOR_TAGS,'-movflags','+faststart',master])
    print('4K 竖屏主文件已导出。',flush=True)
    outputs=[master]
    if args.include_1080p:
        run(['-v','warning','-i',master,'-vf','scale=1080:1920:flags=lanczos,setsar=1',
             '-an','-c:v','libx264','-preset','slow','-crf','14','-maxrate','24M','-bufsize','48M',
             '-threads','6','-g','48','-pix_fmt','yuv420p','-color_primaries','bt709',
             '-color_trc','bt709','-colorspace','bt709','-bsf:v',COLOR_TAGS,'-movflags','+faststart',upload])
        outputs.append(upload)
    reports=[]
    for path in outputs:
        check=run(['-v','error','-i',path,'-f','null','-'])
        measurement=run(['-i',path,'-map','0:v:0','-c','copy','-f','null','-'])
        frames=re.findall(r'frame=\s*(\d+)',measurement.stderr)
        assert frames and int(frames[-1])==2880,measurement.stderr[-1200:]
        meta=metadata(path)
        reports.append(dict(file=str(path.relative_to(ROOT)),bytes=path.stat().st_size,
                            sha256=hashlib.file_digest(path.open('rb'),'sha256').hexdigest(),
                            frames=int(frames[-1]),decode_errors=check.stderr,metadata=meta))
        print(path.name+'：2880 帧，完整解码通过。',flush=True)
    for t in [3,19,32,39,65,76,87,99,117]:
        run(['-v','error','-ss',t,'-i',master,'-frames:v','1',OUT/f'4K成片验收_{t:03}.png'])
    (ROOT/'docs/4K视频清晰度验收.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2))
    (ROOT/'docs/4K功能演示剪辑表.json').write_text(json.dumps(dict(duration=120,fps=24,
        source=str(SOURCE.relative_to(ROOT)) if SOURCE.is_relative_to(ROOT) else SOURCE.name,
        source_render_size=JOURNAL['renderSize'],segments=SEGMENTS),ensure_ascii=False,indent=2))
    print('4K 重制与验收完成。',flush=True)


if __name__=='__main__':
    main()
