"""在街市镜头尚未渲染时，修正相机与行人的近距离擦碰。"""
from pathlib import Path
import sys,json,hashlib,bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from geometry import camera_key

frames=list((ROOT/'renders/frames').glob('[0-9][0-9][0-9][0-9].png'))
assert all(int(p.stem)<661 for p in frames),'街市镜头已经开始渲染，不能执行兼容修订'
old=hashlib.sha256((ROOT/'入画汴京.blend').read_bytes()).hexdigest()
cam=bpy.data.objects['04_沿岸市井']
camera_key(cam,661,(17.9,-24,3.3),(24,-10,3),28)
camera_key(cam,960,(17.9,-10,3.9),(24,3,3.4),29)
bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'入画汴京.blend'))
new=hashlib.sha256((ROOT/'入画汴京.blend').read_bytes()).hexdigest()
manifest=ROOT/'renders/frames/render_manifest.json';data=json.loads(manifest.read_text());assert data['scene_sha256']==old
data['scene_sha256']=new;manifest.write_text(json.dumps(data,ensure_ascii=False,indent=2))
(ROOT/'docs/镜头修订.json').write_text(json.dumps({'previous_scene':old,'current_scene':new,'modified_camera':'04_沿岸市井','affected_frames':[661,960],'already_rendered_max':max(int(p.stem) for p in frames),'reason':'原路线与一位行人头部最近约 0.45 米；将相机横移到 x=17.9 并略抬高。已完成帧使用其他相机，不受本次修订影响。'},ensure_ascii=False,indent=2))
