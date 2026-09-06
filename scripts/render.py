"""分段渲染、跳过已完成的帧，并保存可读进度。"""
import bpy,sys,argparse,json,time,os,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--start',type=int,default=1);ap.add_argument('--end',type=int,default=1440);ap.add_argument('--step',type=int,default=1)
    ap.add_argument('--scale',type=int,default=100);ap.add_argument('--samples',type=int,default=48);ap.add_argument('--engine',choices=['CYCLES','BLENDER_EEVEE_NEXT'],default='CYCLES')
    ap.add_argument('--folder',default='renders/frames');ap.add_argument('--still',action='store_true');ap.add_argument('--force',action='store_true')
    args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    sc=bpy.context.scene;sc.render.engine=args.engine;sc.render.resolution_percentage=args.scale;sc.cycles.samples=args.samples
    if args.still:sc.render.resolution_x=2160;sc.render.resolution_y=3840
    p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='METAL';p.get_devices()
    for d in p.devices:d.use=d.type=='METAL'
    sc.cycles.device='GPU';sc.render.use_persistent_data=True
    if args.engine=='BLENDER_EEVEE_NEXT':sc.render.use_motion_blur=False
    out=ROOT/args.folder;out.mkdir(parents=True,exist_ok=True);times=[]
    identity=dict(scene_sha256=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),engine=args.engine,
                  width=sc.render.resolution_x*args.scale//100,height=sc.render.resolution_y*args.scale//100,samples=args.samples)
    manifest=out/'render_manifest.json'
    if manifest.exists() and json.loads(manifest.read_text())!=identity and not args.force:
        raise RuntimeError('此输出目录包含不同工程或画质设置的帧，请改用新目录，或用 --force 重渲染。')
    manifest.write_text(json.dumps(identity,ensure_ascii=False,indent=2))
    for frame in range(args.start,args.end+1,args.step):
        dest=out/f'{frame:04d}.png'
        if dest.exists() and dest.stat().st_size>1024 and not args.force:
            with dest.open('rb') as f:
                f.seek(-12,2);tail=f.read()
            if b'IEND' in tail:continue
        sc.frame_set(frame);sc.camera=next(m.camera for m in reversed(sorted(sc.timeline_markers,key=lambda m:m.frame)) if m.frame<=frame and m.camera)
        temporary=dest.with_name('.pending-'+dest.name)
        sc.render.filepath=str(temporary);t=time.time();bpy.ops.render.render(write_still=True);temporary.replace(dest);dt=time.time()-t;times.append(dt)
        progress=dict(frame=frame,through=args.end,seconds=round(dt,2),average_seconds=round(sum(times)/len(times),2),file=str(dest),engine=args.engine,samples=args.samples)
        (out/'progress.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2));print('PROGRESS',json.dumps(progress,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
