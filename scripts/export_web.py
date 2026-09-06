"""从可编辑工程导出网页 GLB：静态合批、共享人物网格、动画由浏览器驱动。"""
import bpy, math, json, time
import sys
from pathlib import Path
from collections import defaultdict
from mathutils import Matrix

ROOT=Path(__file__).resolve().parents[1]
scene=bpy.context.scene
scene.frame_set(1)
start=time.time()

# 保留动态对象关系，记录可在网页端无限循环的运动参数。
for ob in list(scene.objects):
    if ob.type=='EMPTY':
        n=ob.name
        if n.startswith('汴河货船_'):
            ob['web_kind']='boat'
            ob['web_speed']=[.2,.15,.12,.16,.08,0,0,.12][int(n.split('_')[-1])-1]
        elif n.startswith(('桥上行人_','街市行人_','街市买卖_','船工_')) and not any(a in n for a in ['肩','腿']):
            ob['web_kind']='person'
            ob['web_walk']=n.startswith(('桥上行人_','街市行人_'))
            ob['web_bridge']=n.startswith('桥上行人_')
            ob['web_phase']=(sum(map(ord,n))*1.618)%math.tau
        elif '肩' in n or '腿' in n:
            ob['web_kind']='arm' if '肩' in n else 'leg'
            ob['web_side']=1 if ob.location.x>0 else -1
        elif n.startswith('风中柳梢'):
            ob['web_kind']='willow'
    if ob.type=='MESH' and ('招幌' in ob.name or '桥头长幡' in ob.name):
        ob['web_kind']='flag'

# 移除离线相机、原水面及体积；这些效果在 WebGL 中重新实现。
for ob in list(scene.objects):
    if ob.hide_render or ob.type in {'CAMERA','LIGHT'} or ob.name.startswith(('汴河水面','炊烟体积')) or '对焦' in ob.name:
        bpy.data.objects.remove(ob,do_unlink=True)

for ob in scene.objects:
    ob.animation_data_clear()
    if ob.data and hasattr(ob.data,'animation_data_clear'):ob.data.animation_data_clear()
    if ob.type=='MESH' and ob.data.shape_keys:
        ob.shape_key_clear()

# glTF 只保存标准 PBR；网页再补充木纹、地表与织物的实时材质。
for m in bpy.data.materials:
    if not m.use_nodes:continue
    nodes=m.node_tree.nodes;p=nodes.get('Principled BSDF')
    if not p:continue
    color=tuple(p.inputs['Base Color'].default_value)
    rough=p.inputs['Roughness'].default_value
    for node in list(nodes):
        if node.type not in {'BSDF_PRINCIPLED','OUTPUT_MATERIAL'}:nodes.remove(node)
    p.inputs['Base Color'].default_value=color
    p.inputs['Roughness'].default_value=rough
    p.inputs['Subsurface Weight'].default_value=0

# 按材质与街区合并静态对象，保留 3 个空间块以便浏览器视锥剔除。
groups=defaultdict(list)
for ob in list(scene.objects):
    if ob.type in {'MESH','FONT','CURVE'} and not ob.parent and not ob.get('web_kind'):
        if ob.type!='MESH':
            bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
            bpy.ops.object.convert(target='MESH')
        center=sum((ob.matrix_world @ __import__('mathutils').Vector(c) for c in ob.bound_box),__import__('mathutils').Vector())/8
        bucket=-1 if center.y<-35 else 1 if center.y>40 else 0
        material=ob.data.materials[0].name if ob.data.materials else 'none'
        groups[(bucket,material)].append(ob)

for (bucket,material),obs in groups.items():
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:o.select_set(True)
    bpy.context.view_layer.objects.active=obs[0]
    if len(obs)>1:bpy.ops.object.join()
    o=bpy.context.view_layer.objects.active;o.name=f'街区{bucket}_{material}'
    o['web_kind']='architecture'

sys.path.insert(0,str(Path(__file__).resolve().parent))
from bake_web_ao import bake
bake([ob for ob in scene.objects if ob.type=='MESH' and ob.get('web_kind')=='architecture'])

bpy.ops.object.select_all(action='SELECT')
path=ROOT/'public/models/bianjing.glb'
bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
    export_extras=True,export_animations=False,export_cameras=False,export_lights=False,
    export_apply=True,export_draco_mesh_compression_enable=True,
    export_draco_mesh_compression_level=6,export_draco_position_quantization=16,
    export_draco_normal_quantization=10,export_draco_texcoord_quantization=12,
    export_yup=True,export_vertex_color='ACTIVE')
stats={'objects':len(scene.objects),'static_batches':len(groups),'glb_bytes':path.stat().st_size,
       'export_seconds':round(time.time()-start,2),'source':'汴京网页版.blend',
       'geometry':'真实三维网格，非照片投影','historical_note':'依据张择端原卷重点重建虹桥与沿河市井；背面、尺度及部分街巷作空间推定。'}
(ROOT/'public/models/manifest.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2))
print(json.dumps(stats,ensure_ascii=False),flush=True)
