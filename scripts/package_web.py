"""仅打包本地网页运行所需文件，同时核对资产清单。"""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import json,hashlib,urllib.request,urllib.parse
root=Path(__file__).resolve().parents[1];files=[]
for p in sorted((root/'dist').rglob('*')):
    if not p.is_file():continue
    relative=p.relative_to(root/'dist').as_posix()
    with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:5186/'+urllib.parse.quote(relative),method='HEAD')) as response:
        assert int(response.headers['Content-Length'])==p.stat().st_size,relative
    files.append({'file':relative,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(root/'docs/网页资源验收.json').write_text(json.dumps({'files':len(files),'failures':[],'results':files},ensure_ascii=False,indent=2))
outfile=root/'入画汴京_网页版.zip'
with ZipFile(outfile,'w',compression=ZIP_DEFLATED,compresslevel=6) as z:
    for p in (root/'dist').rglob('*'):
        if p.is_file():z.write(p,'入画汴京/'+p.relative_to(root).as_posix())
    for rel in ['打开汴京.command','scripts/serve.mjs','docs/素材来源.md']:
        z.write(root/rel,'入画汴京/'+rel)
    z.writestr('入画汴京/先读我.txt','双击 打开汴京.command，打开 http://127.0.0.1:5186/。需要免费 Node.js，无需账号，可断网运行。本包为已构建的网页运行包，完整源代码、Blender 工程、音乐与视频保留在原项目目录。拍摄成果自动写入 output/web/。也可使用静态 HTTP 服务托管 dist/，此时导出会改为浏览器下载。')
with ZipFile(outfile) as z:assert z.testzip() is None
print(f'{len(files)} 个资源通过；运行包 {outfile.stat().st_size/1048576:.2f} MB。')
