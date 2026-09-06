"""从现有工程恢复制作；任一阶段失败时保留已完成的帧。"""
from pathlib import Path
import subprocess,json,sys,datetime
ROOT=Path(__file__).resolve().parents[1];BLENDER=ROOT/'tools/Blender.app/Contents/MacOS/Blender';PY=ROOT/'.venv/bin/python'

def step(name,cmd):
    print(name,flush=True)
    (ROOT/'logs/pipeline_status.json').write_text(json.dumps({'stage':name,'status':'running','updated_at':datetime.datetime.now().isoformat()},ensure_ascii=False))
    with (ROOT/'logs'/f'{name}.log').open('a') as log:subprocess.run(list(map(str,cmd)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)

def main():
    try:
        for start in range(1,1441,120):
            end=min(start+119,1440)
            step(f'正式渲染_{start:04d}_{end:04d}',[BLENDER,'-b',ROOT/'入画汴京.blend','--python-exit-code','1','--python',ROOT/'scripts/render.py','--','--start',start,'--end',end,'--samples','48'])
        step('合成成片',[PY,ROOT/'scripts/assemble.py'])
        for n in [80,230,520,810,1140,1360]:
            step(f'高清静帧_{n}',[BLENDER,'-b',ROOT/'入画汴京.blend','--python-exit-code','1','--python',ROOT/'scripts/render.py','--','--start',n,'--end',n,'--still','--samples','128','--folder','output/stills'])
        step('交付验收',[PY,ROOT/'scripts/verify.py'])
        (ROOT/'logs/pipeline_status.json').write_text(json.dumps({'stage':'全部完成','status':'complete','updated_at':datetime.datetime.now().isoformat()},ensure_ascii=False))
    except Exception as e:
        (ROOT/'logs/pipeline_status.json').write_text(json.dumps({'status':'failed','error':str(e),'updated_at':datetime.datetime.now().isoformat()},ensure_ascii=False));raise

if __name__=='__main__':main()
