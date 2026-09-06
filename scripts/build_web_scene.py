"""网页版专用重建：错落街巷、真实开间、院落、桥头棚市与早春树木。"""
import bpy,sys,math,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from geometry import *
import scenery as sc
from scenery import M,roof,basket,pottery,stall,flag,sign,bridge_z
import people as pe

ROOT=Path(__file__).resolve().parents[1]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
RNG.seed(1145);sc.materials()
M['plaster_variants']=[mat('灰泥岁痕_'+str(i),c,.94,.22,32) for i,c in enumerate(['#b0a087','#bfb49b','#a89e87','#c4bba5'])]
M['thatch']=mat('旧苇草顶','#897b5a',.94,.4,50)
M['earthwall']=mat('院墙夯土','#a59879',.96,.4,30)
M['stain']=mat('墙脚风化','#746d55',.96,.4,40)

def river_center(y):return 2.8*math.sin(y*.025)+.016*max(0,-y-25)**1.3
def bankx(y,side):return river_center(y)+side*(15.35+.4*math.sin(y*.075))
sc.bankx=bankx
sc.make_ground();sc.make_water();sc.make_bridge()
SHOP_RECORDS=[]

def building(name,x,y,w,d,h,angle,shop=False,two=False,detail=True):
    g=Geo(name,(x,y,1.65),angle);plaster=RNG.choice(M['plaster_variants']);bays=max(2,round(w/2.3));bh=w/bays;ridge=RNG.uniform(1.2,1.8)
    g.box((0,0,.12),(w+.35,d+.35,.24),M['stone'])
    # 墙体由独立墙段构成，门扇后面留出空间与后墙。
    g.box((0,d/2-.1,h/2),(w,.2,h),plaster)
    for side in [-1,1]:
        g.box((side*w/2,0,h/2),(.18,d,h),plaster)
        g.mesh([(side*w/2,-d/2,h),(side*w/2,d/2,h),(side*w/2,0,h+ridge)],[(0,1,2)],plaster)
        for yy in [-d/2,0,d/2]:g.beam((side*w/2,yy,.2),(side*w/2,yy,h+.06),.15,M['dark'])
    g.box((0,0,.26),(w-.2,d-.2,.10),M['wood'])
    g.box((0,-d/2,h-.3),(w,.18,.6),plaster)
    for i in range(bays+1):
        xx=-w/2+i*bh;g.beam((xx,-d/2-.02,.2),(xx,-d/2-.02,h+.1),.18,M['dark'])
    for i in range(bays):
        xx=-w/2+(i+.5)*bh;bw=bh-.23
        if i!=bays//2:
            g.box((xx,-d/2, .53),(bw,.16,.65),M['wood'])
            if shop:
                # 半高柜台、深色内室与真实窗棂。
                g.box((xx,-d/2-.12,1.02),(bw,.5,.10),M['wood'])
                for zz in [1.45,1.85,2.25]:
                    if zz<h-.4:g.beam((xx-bw/2,-d/2,zz),(xx+bw/2,-d/2,zz),.04,M['lightwood'])
                for k in range(7):g.beam((xx-bw/2+k*bw/6,-d/2,1.05),(xx-bw/2+k*bw/6,-d/2,min(h-.55,2.6)),.033,M['wood'])
                for k in range(3):pottery(g,(xx-bw*.3+k*bw*.3,-d/2+.6,.35),RNG.uniform(.7,1.2))
            else:
                g.box((xx,-d/2+.02,1.65),(bw,.1,1.6),M['dark'])
                for k in range(9):g.beam((xx-bw*.46+k*bw*.115,-d/2-.07,.9),(xx-bw*.46+k*bw*.115,-d/2-.07,2.4),.04,M['wood'])
                for zz in [1.15,1.8,2.2]:g.beam((xx-bw*.5,-d/2-.08,zz),(xx+bw*.5,-d/2-.08,zz),.04,M['lightwood'])
        else:
            g.box((xx,-d/2,.33),(bw,.6,.15),M['stone'])
            for s in [-1,1]:
                # 打开的木门有厚度，近景可看到门轴、分板与内侧。
                xx0=xx+s*bw*.45
                g.box((xx0,-d/2+.23,1.47),(.16,.6,2.25),M['wood'])
                for zz in [.54,2.3]:g.cyl((xx0,-d/2+.06,zz),.035,.13,M['metal'],7)
    for zz in [.38,h-.58,h-.12]:g.beam((-w/2,-d/2-.08,zz),(w/2,-d/2-.08,zz),.14,M['wood'])
    if two:
        # 一楼外加披檐与栏杆，打破整齐一致的屋脊轮廓。
        roof(g,w+.7,d*.63,h*.54,.58,0)
        g.box((0,-d/2-.45,h*.5),(w+.3,1.15,.16),M['wood'])
        for j in range(int(w/.45)+1):
            xx=-w/2+j*w/int(w/.45);g.beam((xx,-d/2-.9,h*.5),(xx,-d/2-.9,h*.5+.85),.045,M['dark'])
        g.beam((-w/2,-d/2-.9,h*.5+.85),(w/2,-d/2-.9,h*.5+.85),.07,M['wood'])
    roof(g,w+1.0,d+1.2,h,ridge,1 if detail else 0)
    if shop:
        SHOP_RECORDS.append({'vendor':g.point((0,-d/2-.34,0)), 'customer':g.point((.6,-d/2-2.14,0)), 'angle':angle,'y':y})
        for xx in [-w*.4,w*.4]:g.beam((xx,-d/2-2.1,0),(xx,-d/2-2.1,2.63),.095,M['dark'])
        # 分条棚布有自然垂度，非一整张平板。
        for i in range(12):
            xa=-w*.47+i*w*.94/12;xb=xa+w*.94/12;verts=[]
            for j in range(7):
                t=j/6;zz=3.0-.35*t-.17*math.sin(t*math.pi)
                verts.extend([(xa,-d/2-t*2.25,zz),(xb,-d/2-t*2.25,zz+.018*math.sin(i))])
            g.mesh(verts,[(j*2,j*2+1,j*2+3,j*2+2) for j in range(6)],M['linen'] if i%5 else M['ochre'])
        if abs(y)<58:stall(g,0,-d/2-1.23,0,RNG.randrange(3))
        p=g.point((w*.42,-d/2-.3,3.6));flag(name+'_招幌',p,.6,1.5,M['linen'],angle)
        if abs(y)<60:sign(RNG.choice(['酒','茶','布','食','药']),g.point((w*.42+.1,-d/2-.42,3.33)),angle,.38)
    if detail:
        for s in [-1,1]:
            # 不规则低矮风化痕与墙边堆放的坛罐。
            g.box((s*w/2+.003,0,.34),(.19,d-.1,.21),M['stain'])
        for i in range(RNG.randrange(2,5)):
            pottery(g,(-w*.5-.5,RNG.uniform(-d*.3,d*.4),.03),RNG.uniform(.6,1.3))
    g.finish()

count=0
for side in [-1,1]:
    y=-84 if side<0 else -78
    while y<96:
        w=RNG.uniform(5.4,8.5);d=RNG.uniform(4.7,6.7)
        if -12<y<7:y=9+RNG.uniform(0,3)
        x=side*(23.5+d/2+RNG.uniform(-.5,.6))+river_center(y)
        building(f'临河重建_{side}_{count}',x,y,w,d,RNG.uniform(3.1,4.7),-side*math.pi/2+RNG.uniform(-.035,.035),True)
        y+=w+RNG.uniform(1.7,4.1);count+=1
    for row in range(2):
        y=-95+RNG.uniform(0,10)
        while y<102:
            w=RNG.uniform(5.2,9);d=RNG.uniform(5,8);two=RNG.random()<.22
            # 横向道路留空，院落与房屋错置排列。
            if -3<y<8 or 36<y<44:y+=13
            x=side*(39+row*14+RNG.uniform(-1,1))+river_center(y)*.5
            angle=-side*math.pi/2+RNG.choice([0,0,0,math.pi/2])+RNG.uniform(-.07,.07)
            building(f'坊巷重建_{side}_{count}',x,y,w,d,RNG.uniform(5.3,6.3) if two else RNG.uniform(2.9,4.2),angle,False,two,False)
            if RNG.random()<.55:
                court=Geo('院落短墙',(x,y,1.65),angle)
                for s in [-1,1]:court.box((s*(w/2+.7),-d/2-2.0,.85),(.25,3.9,1.7),M['earthwall'])
                court.box((0,-d/2-3.8,.85),(w+1.6,.27,1.7),M['earthwall'])
                court.finish()
            y+=max(w,d)+RNG.uniform(3,7);count+=1

# 虹桥西南桥头展开棚市，东南保留开敞通行处。
building('桥头重建酒楼',-29,-12,9.2,7.1,6.2,math.pi/2,True,True)
for x,y,angle in [(-21,4,.12),(-25,4,-.09),(22,4,-.1),(-34,-3,.0)]:
    g=Geo('桥头伞市',(x,y,1.65),angle);r=1.55
    g.cyl((0,0,1.35),.045,2.7,M['dark'],8)
    for i in range(20):
        a=i*math.tau/20;b=(i+1)*math.tau/20
        g.mesh([(0,0,3),(r*.6*math.cos(a),r*.6*math.sin(a),2.88),(r*math.cos(a),r*math.sin(a),2.58),(r*math.cos(b),r*math.sin(b),2.58),(r*.6*math.cos(b),r*.6*math.sin(b),2.88)],[(0,1,4),(1,2,3,4)],M['linen'] if i%5 else M['thatch'])
        g.beam((0,0,2.96),(r*math.cos(a),r*math.sin(a),2.57),.018,M['lightwood'])
    stall(g,0,0,0,RNG.randrange(3));g.finish()

# 城门置于西侧城区远端，不横截汴河。
g=Geo('西城门',(-72,45,1.6),math.pi/2)
for s in [-1,1]:g.box((s*27,0,4),(42,4.5,8),M['earthwall'])
for xx in range(-48,49,3):
    if abs(xx)>6:g.box((xx,0,8.5),(1.5,4.5,1.0),M['stone'])
for s in [-1,1]:g.box((s*6.0,0,4),(2.5,6,8),M['stone'])
g.box((0,0,7.7),(14.5,6,1.5),M['stone'])
g.box((0,0,9.8),(13,5,3),M['plaster'])
for xx in range(-6,7,2):g.beam((xx,-2.6,8.2),(xx,-2.6,11.4),.18,M['dark'])
roof(g,16,8,11,2,0);g.finish()

boats=[]
for i,(x,y,l,w,a,s) in enumerate([(2,17,12,3.1,0,.2),(-6,-29,10,2.6,math.pi,.15),(7,-47,11,2.8,0,.12),(-8,47,13,3.2,math.pi,.16),(9,68,11,2.7,0,.08),(-11,-55,10,2.8,0,0),(11,34,9,2.6,math.pi,0),(-10,87,12,3,0,.12)]):
    boats.append(sc.boat(f'汴河货船_{i+1}',x+river_center(y),y,l,w,a,s))
pe.populate(boats)
# 新街区的摊位位置变化较大，摊主与顾客按每个实际柜台布置，避免穿桌。
vendor_roots=[ob for ob in bpy.context.scene.objects if ob.type=='EMPTY' and ob.name.startswith('街市买卖_') and not any(c in ob.name for c in ['肩','腿'])]
for ob in vendor_roots:
    for child in list(ob.children_recursive):bpy.data.objects.remove(child,do_unlink=True)
    bpy.data.objects.remove(ob,do_unlink=True)
for ob in bpy.context.scene.objects:
    if ob.type=='EMPTY' and ob.name.startswith('街市行人_') and not any(c in ob.name for c in ['肩','腿']):
        ob.animation_data_clear()
        direction=1 if ob.location.x>0 else -1
        if int(ob.name.split('_')[-1])%10==0:ob.location.x=direction*19.1
        elif abs(ob.location.x)>20:ob.location.x=direction*20.45
        ob.location.x+=river_center(ob.location.y)
for i,shop in enumerate(SHOP_RECORDS):
    if abs(shop['y'])>58:continue
    pe.person(f'街市买卖_摊主_{i}',shop['vendor'],i%8,shop['angle'],role='vendor',scale=.94+RNG.random()*.07)
    if i%3!=0:
        pe.person(f'街市买卖_顾客_{i}',shop['customer'],(i+3)%8,shop['angle']+math.pi,role='vendor',scale=.94+RNG.random()*.08)

# 早春树冠保留枝干结构，补足细枝而非球形树冠。
sc.make_environment();sc.carts_and_street_detail()
for side in [-1,1]:
    for y in [-69,-41,27,54,84]:
        x=side*(35+RNG.uniform(-3,3));g=Geo('早春杂树',(x,y,1.6));h=RNG.uniform(6,10)
        g.tube([(0,0,0),(.12,0,h*.4),(.3,.05,h*.7),(.4,.1,h)],[.27,.2,.12,.03],M['bark'],8)
        for b in range(9):
            a=RNG.uniform(0,math.tau);z=RNG.uniform(h*.4,h*.8);end=(RNG.uniform(1.3,3.4)*math.cos(a),RNG.uniform(1.3,3.4)*math.sin(a),z+RNG.uniform(1,3))
            g.tube([(.1,0,z),tuple(c*.55 for c in end[:2])+(z+(end[2]-z)*.65,),end],[.08,.045,.015],M['bark'],6)
            for j in range(5):
                t=j/5;xx=end[0]*t;yy=end[1]*t;zz=z+(end[2]-z)*t
                g.tube([(xx,yy,zz),(xx+math.cos(a+.9)*.6,yy+math.sin(a+.9)*.6,zz+.7),(xx+math.cos(a+1)*1.0,yy+math.sin(a+1)*1.0,zz+1.3)],[.02,.013,.004],M['bark'],5)
        g.finish()

scene=bpy.context.scene;scene.frame_set(1);scene.render.fps=24;scene.frame_start=1;scene.frame_end=1440
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'汴京网页版.blend'))
people_count=sum(1 for ob in scene.objects if ob.type=='EMPTY' and ob.name.startswith(('桥上行人_','街市行人_','街市买卖_','船工_')) and not any(c in ob.name for c in ['肩','腿']))
(ROOT/'docs/网页重建.json').write_text(json.dumps({'建筑数量':count+1,'人物数量':people_count,'重建':'重新生成街区与建筑开间、院落、桥头伞市；西置城门、早春细枝。摊主与顾客按实际柜台重新安放。','来源':'scripts/build_web_scene.py'},ensure_ascii=False,indent=2))
print('网页专用重建完成',count+1,flush=True)
