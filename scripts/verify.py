"""对交付文件进行实际解码与音频响度测量。"""
from pathlib import Path
import subprocess,json,re,hashlib
import imageio_ffmpeg
from PIL import Image
import soundfile as sf

ROOT=Path(__file__).resolve().parents[1]
def main():
    ff=imageio_ffmpeg.get_ffmpeg_exe();results={}
    for name in ['清明上河图_60秒_无声版.mp4','清明上河图_60秒_配乐版.mp4']:
        path=ROOT/'output'/name
        p=subprocess.run([ff,'-v','error','-i',str(path),'-map','0:v:0','-f','null','-','-progress','pipe:1'],capture_output=True,text=True,check=True)
        count=int(re.findall(r'^frame=(\d+)$',p.stdout,re.M)[-1]);assert count==1440,(name,count)
        r=imageio_ffmpeg.read_frames(str(path));meta=next(r);r.close()
        assert tuple(meta['size'])==(1080,1920),meta
        assert abs(meta['fps']-24)<1e-5,meta
        results[name]={'decoded_frames':count,'size':meta['size'],'fps':meta['fps'],'duration':meta['duration'],'bytes':path.stat().st_size}
    for folder in ['renders/frames','output/frames']:
        paths=sorted((ROOT/folder).glob('[0-9][0-9][0-9][0-9].png'));assert len(paths)==1440,(folder,len(paths))
        for p in paths:
            with Image.open(p) as im:assert im.size==(1080,1920);im.verify()
        results[folder]={'frames':len(paths),'valid_png':True}
    for name in ['原创配乐.wav','环境音.wav','配乐环境混音.wav']:
        path=ROOT/'output/audio'/name;info=sf.info(path);assert info.samplerate==48000 and info.frames==2880000
        p=subprocess.run([ff,'-hide_banner','-i',str(path),'-af','loudnorm=I=-14:TP=-1:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
        data=json.loads(p.stderr[p.stderr.rfind('{'):p.stderr.rfind('}')+1]);results[name]={'sample_rate':info.samplerate,'duration':info.duration,'integrated_lufs':float(data['input_i']),'true_peak_dbtp':float(data['input_tp'])}
        if name!='环境音.wav':
            assert abs(float(data['input_i'])+14)<1.0,data
            assert float(data['input_tp'])<=-.85,data
    (ROOT/'docs/交付验收.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print(json.dumps(results,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
