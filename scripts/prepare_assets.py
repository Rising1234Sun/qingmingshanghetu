"""整理免费素材，仅从本地下载包取用需要的文件。"""
from pathlib import Path
import zipfile, subprocess, json, re, shutil

ROOT = Path(__file__).resolve().parents[1]

def main():
    for name in ('Wood049', 'Ground037'):
        dest = ROOT/'assets/textures'/name
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(ROOT/'vendor'/f'{name}.zip') as z:
            for f in z.namelist():
                if f.endswith(('_Color.jpg', '_NormalGL.jpg', '_Roughness.jpg')):
                    z.extract(f, dest)
    with zipfile.ZipFile(ROOT/'vendor/makehuman_assets.zip') as z:
        for f in z.namelist():
            if any(s in f for s in ('skins/middleage_asian_male/', 'skins/middleage_asian_female/', 'skins/young_asian_male/')) and f.endswith('.png'):
                dest=ROOT/'assets/characters'/Path(f).name
                dest.write_bytes(z.read(f))

    repo = ROOT/'vendor/vsco'
    files = subprocess.check_output(['git','-C',str(repo),'ls-tree','-r','--name-only','HEAD'],text=True).splitlines()
    prefixes = ['Strings/Violin Section/susVib/', 'Strings/Violin Section/Spic/',
                'Strings/Cello Section/susvib/', 'Strings/Solo Contrabass/SusVib/',
                'Strings/Harp/', 'Woodwinds/Flute/susvib/', 'Woodwinds/Flute/susNV/',
                'Brass/F Horn/sus/', 'VSCO 1 Percussion/drums/bass/',
                'VSCO 1 Percussion/drums/other/ethnic/giant/mallet/',
                'VSCO 1 Percussion/varMetal/Gong/',
                'VSCO 1 Percussion/varMetal/Cymbals/susp/', 'Percussion/Timpani/']
    selected=[]
    for prefix in prefixes:
        matches=[f for f in files if f.startswith(prefix) and f.lower().endswith('.wav') and '/Rolls/' not in f]
        # 不重复下载多组力度、轮替采样，留足音域即可。
        grouped={}
        for f in matches:
            note=re.search(r'_([A-G]#?\d)_',Path(f).stem)
            key=note.group(1) if note else Path(f).stem
            if key not in grouped or ('_v2' in f and 'rr1' in f): grouped[key]=f
        chosen=list(grouped.values())[:24]
        selected.extend(chosen)
    selected=sorted(set(selected))
    print('下载管弦与打击乐采样:',len(selected),flush=True)
    # 一次批量 checkout，git 只取得选中的原始 WAV。
    subprocess.run(['git','-C',str(repo),'checkout','HEAD','--',*selected],check=True)
    for f in selected:
        out=ROOT/'assets/audio/vsco'/f
        out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(repo/f,out)
    (ROOT/'assets/audio/sample_manifest.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2))
    print('素材整理完成',flush=True)

if __name__=='__main__': main()
