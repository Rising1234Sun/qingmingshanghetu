"""离线原创编曲与环境音合成。旋律、节奏、混音均在本地计算。"""
from pathlib import Path
import json,re,math,subprocess
import numpy as np
from scipy import signal
import soundfile as sf
import imageio_ffmpeg
import mido

ROOT=Path(__file__).resolve().parents[1];SR=48000;DURATION=60;N=SR*DURATION
RNG=np.random.default_rng(1127);BEAT=60/96;BAR=4*BEAT
OUT=ROOT/'output/audio';OUT.mkdir(parents=True,exist_ok=True)
CACHE={};NOTES=[]

def db(v):return 10**(v/20)
def note_number(name):
    m=re.search(r'_([A-G])(#?)(-?\d)_',name)
    if not m:return None
    return (int(m.group(3))+1)*12+dict(C=0,D=2,E=4,F=5,G=7,A=9,B=11)[m.group(1)]+bool(m.group(2))

def load(path):
    path=str(path)
    if path not in CACHE:
        a,sr=sf.read(path,dtype='float32',always_2d=True)
        if a.shape[1]==1:a=np.repeat(a,2,axis=1)
        a=a[:,:2]
        if sr!=SR:
            d=math.gcd(sr,SR);a=signal.resample_poly(a,SR//d,sr//d,axis=0).astype('float32')
        env=np.max(abs(a),axis=1);nz=np.flatnonzero(env>max(.0005,float(env.max())*.012))
        if len(nz):a=a[max(0,nz[0]-240):]
        peak=np.max(abs(a));a/=max(peak,.1)
        CACHE[path]=a
    return CACHE[path]

def pitch_estimate(a,expected):
    x=a[int(.18*SR):int(.7*SR)].mean(axis=1)[::6]
    if len(x)<1000:return expected
    x=x-x.mean();ac=signal.fftconvolve(x,x[::-1],mode='full')[len(x)-1:]
    rate=SR/6
    # 先校验采样文件的八度约定，再在目标附近寻找基音峰。
    candidates=[]
    for mult in [.5,1,2]:
        fr=expected*mult;lo=max(3,int(rate/(fr*1.07)));hi=min(len(ac)-1,int(rate/(fr*.93)))
        if hi<=lo:continue
        k=lo+np.argmax(ac[lo:hi]);candidates.append((ac[k]/max(ac[0],1e-8),rate/k))
    best=max(candidates,key=lambda t:t[0]) if candidates else (0,expected)
    # 优先保留文件标注音高，只有可靠的另一八度峰明显更强时调整。
    return min(candidates,key=lambda t:abs(math.log2(t[1]/expected)))[1] if best[0]<.5 else best[1]

class Sampler:
    def __init__(self,prefix,percussion=False):
        self.files=sorted(p for p in (ROOT/'assets/audio/vsco'/prefix).rglob('*') if p.suffix.lower()=='.wav');self.percussion=percussion
        if percussion and 'Cymbals' in prefix:
            self.files=[p for p in self.files if 'hit_softmall' in p.name] or self.files
        self.map=[(note_number(p.name),p) for p in self.files]
        self.map=[(n,p) for n,p in self.map if n is not None]
        self.calibration={}
    def play(self,note,duration,vel=.6):
        if not self.files:raise RuntimeError('缺少本地乐器采样')
        if self.percussion:
            p=self.files[int(RNG.integers(len(self.files)))];a=load(p).copy()
        else:
            n,p=min(self.map,key=lambda x:abs(x[0]-note));a=load(p)
            if str(p) not in self.calibration:
                expected=440*2**((n-69)/12);self.calibration[str(p)]=pitch_estimate(a,expected)
            ratio=440*2**((note-69)/12)/self.calibration[str(p)]
            length=int(len(a)/ratio);t=np.arange(length)*ratio
            a=np.column_stack([np.interp(t,np.arange(len(a)),a[:,ch]) for ch in range(2)]).astype('float32')
        length=int((duration+.16)*SR)
        if len(a)<length and self.percussion:a=np.pad(a,((0,length-len(a)),(0,0)))
        if len(a)<length:
            tail=a[int(len(a)*.4):int(len(a)*.85)]
            if len(tail)>100:
                while len(a)<length:
                    ov=min(int(.06*SR),len(tail)//4);fade=np.linspace(0,1,ov)[:,None]
                    a[-ov:]=a[-ov:]*(1-fade)+tail[:ov]*fade;a=np.concatenate([a,tail[ov:]])
            else:a=np.pad(a,((0,length-len(a)),(0,0)))
        a=a[:length].copy();atk=min(int(.018*SR),len(a)//5);rel=min(int(.18*SR),len(a)//3)
        if atk:a[:atk]*=np.linspace(0,1,atk)[:,None]
        if rel:a[-rel:]*=np.linspace(1,0,rel)[:,None]
        a*=vel*.20
        return a

def place(track,a,t,amp=1,pan=0):
    i=max(0,int(t*SR));n=min(len(a),len(track)-i)
    if n<=0:return
    a=a[:n].copy()*amp
    if a.ndim==1:a=np.column_stack([a,a])
    a[:,0]*=math.cos((pan+1)*math.pi/4)*1.3;a[:,1]*=math.sin((pan+1)*math.pi/4)*1.3
    track[i:i+n]+=a

def pluck(note,duration):
    f=440*2**((note-69)/12);t=np.arange(int((duration+.55)*SR))/SR
    # 拨弦谐波衰减不同，带少量指触噪声；不是在线音乐生成。
    a=np.zeros(len(t))
    for k in range(1,13):
        a+=np.sin(math.tau*f*k*t+.035*k*k)*np.exp(-t*(1.8+k*.38))/(k**1.32)
    a+=RNG.normal(0,.016,len(t))*np.exp(-t*65)
    a*=np.minimum(t/.003,1)*.12
    return a.astype('float32')

def space(a,wet=.19):
    out=a.copy()
    for delay,gain in [(.043,.34),(.071,.28),(.109,.23),(.173,.17),(.271,.13),(.389,.09),(.571,.06)]:
        k=int(delay*SR);out[k:]+=wet*gain*a[:-k,::-1]
    return out

def main():
    flute=Sampler('Woodwinds/Flute');violin=Sampler('Strings/Violin Section/susVib');spic=Sampler('Strings/Violin Section/Spic')
    cello=Sampler('Strings/Cello Section/susvib');bass=Sampler('Strings/Solo Contrabass/SusVib');horn=Sampler('Brass/F Horn/sus');harp=Sampler('Strings/Harp')
    drum=Sampler('VSCO 1 Percussion/drums/bass',True);giant=Sampler('VSCO 1 Percussion/drums/other/ethnic/giant/mallet',True)
    gong=Sampler('VSCO 1 Percussion/varMetal/Gong',True);cymbal=Sampler('VSCO 1 Percussion/varMetal/Cymbals/susp',True)
    layers={name:np.zeros((N,2),np.float32) for name in ['丝竹旋律','管弦铺陈','鼓与转场']}
    chords=[[50,54,57,64],[47,50,54,62],[43,47,50,62],[45,52,57,59]]
    themes=[[(74,1),(78,.5),(81,.5),(78,1),(76,1)],[(74,1.5),(71,.5),(74,1),(76,1)],[(78,1),(81,1),(83,.5),(81,.5),(78,1)],[(76,1.5),(74,.5),(71,1),(74,1)]]
    def event(inst,n,t,d,v,track,pan=0):
        place(layers[track],inst.play(n,d,v),t,pan=pan);NOTES.append((t,d,n,v,track))
    for bar in range(24):
        t=bar*BAR;chord=chords[(bar//2)%4];energy=.28 if bar<2 else .45 if bar<6 else .58 if bar<11 else .64 if bar<16 else .85 if bar<21 else .43
        if bar==23:chord=chords[0];energy=.35
        for j,n in enumerate(chord[:3]):event(cello if j==0 else violin,n+(12 if j else 0),t,2.38,.45*energy,'管弦铺陈',-.3+j*.25)
        if bar>=4:event(bass,chord[0]-12,t,2.35,.65*energy,'管弦铺陈',0)
        if bar>=6:
            for beat in range(8):
                n=chord[beat%3]+12;event(spic,n,t+beat*BEAT/2,.20,.31*energy,'管弦铺陈',-.2)
        for beat in range(4 if bar<6 else 8):
            n=chord[(beat*2)%len(chord)]+12;tm=t+beat*BAR/(4 if bar<6 else 8)
            place(layers['丝竹旋律'],pluck(n,.45),tm,.55*energy,pan=.28)
        if bar<22 and bar%8 not in [6,7]:
            off=0
            for n,d in themes[bar%4]:
                event(flute,n,t+off*BEAT,d*BEAT*.86,.6*energy,'丝竹旋律',-.15);off+=d
        if 16<=bar<21:
            event(horn,chord[0]+12,t,1.10,.32,'管弦铺陈',.2)
            event(horn,chord[2]+12,t+2*BEAT,1.1,.30,'管弦铺陈',.1)
        if bar>=2 and bar<23:
            for beat in [0,2]:event(drum,36,t+beat*BEAT,1.5,.7*energy,'鼓与转场')
            if bar>=6:
                for beat in [1.5,3,3.5]:event(giant,45,t+beat*BEAT,.65,.46*energy,'鼓与转场',.13)
        if bar in [0,6,16,21]:event(gong,48,t,4,.25 if bar==0 else .36,'鼓与转场',-.1)
        if bar in [5,10,15]:
            a=cymbal.play(0,2.2,.25)[::-1].copy();place(layers['鼓与转场'],a,t+.25,1,pan=.1)
        print('已编配小节',bar+1,flush=True)
    event(harp,74,57.5,2.0,.35,'丝竹旋律',.1)
    # 房间感与尾部自然收束。
    music=sum(space(a) for a in layers.values());fade=np.linspace(1,0,int(SR*2.2))**1.3;music[-len(fade):]*=fade[:,None]
    for name,a in layers.items():sf.write(OUT/(name+'.wav'),a,SR,subtype='PCM_24')
    sf.write(OUT/'原创配乐_未母带.wav',music,SR,subtype='PCM_24')

    # 离线环境音：风、水、木响和有距离感的脚步，避免人声合成。
    env=np.zeros((N,2),np.float32);noise=RNG.normal(0,1,(N,2)).astype('float32')
    water=signal.sosfilt(signal.butter(2,[180,1500],btype='band',fs=SR,output='sos'),noise,axis=0)
    tt=np.arange(N)/SR;mod=.012*(1+.4*np.sin(tt*.8)+.2*np.sin(tt*1.73))
    env+=water*mod[:,None]
    wind=signal.sosfilt(signal.butter(2,270,fs=SR,output='sos'),noise,axis=0)
    env+=wind*(.018*(.7+.3*np.sin(tt*.23)))[:,None]
    for tm in np.arange(8,52,.71):
        dur=.12;tx=np.arange(int(dur*SR))/SR
        foot=(RNG.normal(0,.15,len(tx))+np.sin(math.tau*110*tx)*.1)*np.exp(-tx*48)
        place(env,foot.astype('float32'),float(tm),.045,pan=float(RNG.uniform(-.7,.7)))
    for tm in [6.3,10.6,15.4,20.8,24.7,33.4,40.2,47.5]:
        tx=np.arange(int(.36*SR))/SR;wood=np.sin(math.tau*(370+20*np.sin(tx*11))*tx)*np.exp(-tx*13)*.007
        place(env,wood,tm,pan=-.25)
    env[:SR]*=np.linspace(0,1,SR)[:,None];env[-2*SR:]*=np.linspace(1,0,2*SR)[:,None]
    sf.write(OUT/'环境音.wav',env,SR,subtype='PCM_24')
    sf.write(OUT/'混音_未母带.wav',music+space(env,.08),SR,subtype='PCM_24')

    ff=imageio_ffmpeg.get_ffmpeg_exe();reports={}
    for src,dst in [('原创配乐_未母带.wav','原创配乐.wav'),('混音_未母带.wav','配乐环境混音.wav')]:
        cmd=[ff,'-hide_banner','-i',str(OUT/src),'-af','loudnorm=I=-14:TP=-1:LRA=10:print_format=json','-f','null','-']
        p=subprocess.run(cmd,capture_output=True,text=True,check=True);data=json.loads(p.stderr[p.stderr.rfind('{'):p.stderr.rfind('}')+1]);reports[dst]=data
        fil=f'loudnorm=I=-14:TP=-1:LRA=10:measured_I={data["input_i"]}:measured_TP={data["input_tp"]}:measured_LRA={data["input_lra"]}:measured_thresh={data["input_thresh"]}:offset={data["target_offset"]}:linear=true'
        subprocess.run([ff,'-y','-v','error','-i',str(OUT/src),'-af',fil,'-ar','48000','-c:a','pcm_s24le',str(OUT/dst)],check=True)
    (ROOT/'docs/音频测量.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2))
    mid=mido.MidiFile();track=mido.MidiTrack();mid.tracks.append(track);track.append(mido.MetaMessage('set_tempo',tempo=mido.bpm2tempo(96)))
    ev=[]
    for t,d,n,v,name in NOTES:
        ev.extend([(int(t/BEAT*480),'note_on',n,max(1,min(127,int(v*120)))),(int((t+d)/BEAT*480),'note_off',n,0)])
    prev=0
    for ticks,typ,n,v in sorted(ev):track.append(mido.Message(typ,note=n,velocity=v,time=ticks-prev));prev=ticks
    mid.save(OUT/'原创配乐.mid')
    print('配乐、环境音、MIDI 与混音完成',flush=True)

if __name__=='__main__':main()
