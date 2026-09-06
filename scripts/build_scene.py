"""构建完整可编辑三维场景。由 Blender 的内置 Python 执行。"""
import sys,math,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
from geometry import *
from scenery import *
from people import populate

def main():
    began=time.time();bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    for c in list(bpy.data.collections):
        if c.name=='Collection':bpy.data.collections.remove(c)
    scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.render.fps=24;scene.frame_start=1;scene.frame_end=1440
    materials();make_ground();make_water();make_bridge();print('桥与河完成',flush=True)
    make_city();print('街市完成',flush=True)
    boats=[]
    for i,(x,y,l,w,a,s) in enumerate([(2,17,12,3.1,0,.2),(-6,-29,10,2.6,math.pi,.15),(7,-47,11,2.8,0,.12),(-8,47,13,3.2,math.pi,.16),(9,68,11,2.7,0,.08),(-11,-55,10,2.8,0,0),(11,34,9,2.6,math.pi,0),(-10,87,12,3,0,.12)]):
        boats.append(boat(f'汴河货船_{i+1}',x,y,l,w,a,s))
    populate(boats);print('舟船和人物完成',flush=True)
    make_environment();carts_and_street_detail();setup_lighting();print('环境细节完成',flush=True)
    shots=[
      ('01_入画',1,120,(-43,-58,32),(-39,-51,27),(0,1,2),(0,1,2),36,36),
      ('02_汴河行舟',121,360,(-7,-40,3.2),(-4,-24,4.6),(1,4,2),(1,7,2.6),29,31),
      ('03_虹桥烟火',361,660,(-24,-35,20),(-16,-28,25),(-1,0,5),(1,2,5),34,35),
      ('04_沿岸市井',661,960,(17.9,-24,3.3),(17.9,-10,3.9),(24,-10,3),(24,3,3.4),28,29),
      ('05_汴京繁华',961,1260,(-32,-34,13),(-44,-52,36),(1,8,2),(0,12,2),32,35),
      ('06_归于长卷',1261,1440,(-45,-55,37),(-62,-82,53),(0,15,2),(0,14,2),36,38)]
    records=[]
    for name,start,end,p0,p1,t0,t1,l0,l1 in shots:
        cd=bpy.data.cameras.new(name);cam=bpy.data.objects.new(name,cd);scene.collection.objects.link(cam)
        cd.sensor_width=36;cd.clip_end=600;cd.lens=l0;cd.dof.use_dof=True;cd.dof.aperture_fstop=8 if name.startswith(('02','04')) else 11
        target=empty(name+'_对焦',t0);target.location=t0;target.keyframe_insert('location',frame=start);target.location=t1;target.keyframe_insert('location',frame=end)
        cd.dof.focus_object=target
        camera_key(cam,start,p0,t0,l0);camera_key(cam,end,p1,t1,l1)
        marker=scene.timeline_markers.new(name,frame=start);marker.camera=cam
        records.append(dict(id=name,start=start,end=end,frames=end-start+1,duration=(end-start+1)/24,camera=cam.name))
        if start==1:scene.camera=cam
    (ROOT/'docs/镜头表.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
    scene.render.engine='CYCLES';scene.cycles.device='GPU';scene.cycles.samples=48
    scene.cycles.use_adaptive_sampling=True;scene.cycles.adaptive_threshold=.035;scene.cycles.use_denoising=True
    scene.cycles.denoiser='OPENIMAGEDENOISE'
    scene.cycles.max_bounces=4;scene.cycles.diffuse_bounces=2;scene.cycles.glossy_bounces=2;scene.cycles.transmission_bounces=2;scene.cycles.volume_bounces=0
    scene.cycles.sample_clamp_indirect=4;scene.render.use_persistent_data=True
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='METAL'
    scene.render.resolution_x=1080;scene.render.resolution_y=1920;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.image_settings.color_depth='8';scene.render.image_settings.compression=20
    scene.render.film_transparent=False;scene.render.use_motion_blur=True;scene.render.motion_blur_shutter=.25
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=-.10
    scene.world.color=(.4,.4,.4);scene.frame_set(480)
    # 自动打包引用，工程移动后仍可打开。
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'入画汴京.blend'))
    stats=dict(objects=len(scene.objects),meshes=len(bpy.data.meshes),polygons=sum(len(m.polygons) for m in bpy.data.meshes),build_seconds=round(time.time()-began,2),renderer='Cycles / Metal',seed=1145)
    (ROOT/'docs/场景统计.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2));print(stats,flush=True)

if __name__=='__main__':main()
