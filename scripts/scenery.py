"""依据原卷搭建虹桥、汴河、民居、货船与环境动画。"""
import bpy, math, random
from mathutils import Vector
from geometry import *

M={}
def materials():
    M.update(wood=textured('旧木_实拍纹理','Wood049',.5,'#c3ab88'),
             dark=mat('深色榫木','#44342a',.8,.12,16),
             lightwood=mat('新旧竹木','#9b8156',.82,.17,22),
             plaster=mat('米白灰泥','#c1b499',.93,.25,52),
             earth=textured('泥土_实拍纹理','Ground037',.32,'#bcb099'),
             bank=mat('河岸夯土','#74644c',.95,.45,38),
             stone=mat('磨损青石','#797e74',.86,.2,24),
             mortar=mat('土石缝隙','#5a584a',.95),
             rope=mat('麻绳','#a59168',.86,.25,90),
             linen=mat('米色麻布','#c5b99b',.93,.2,100),
             ochre=mat('赭红布幌','#975c42',.9,.18,90),
             blue=mat('靛青布幌','#4d6266',.93,.18,90),
             basket=mat('竹篾','#ad9360',.8,.25,90),
             clay=mat('陶土','#865b44',.7,.2,22),
             celadon=mat('青瓷','#97ae9c',.2,.08,80),
             black=mat('墨色','#1f221f',.85),
             leaf=mat('初春柳叶','#748255',.75),
             leaf2=mat('嫩叶','#a3a86a',.75),
             bark=mat('老柳树皮','#655948',.92,.45,15),
             reed=mat('芦苇','#a69b73',.9),
             metal=mat('旧铁','#494b48',.6,.2,25,.7),
             sack=mat('粮袋','#bda988',.95,.3,70))
    M['tiles']=[mat(f'青灰筒瓦_{i}',c,.86,.22,65) for i,c in enumerate(['#41494a','#475051','#4b5453','#454b4d','#4a504e'])]
    return M

def bridge_z(x):return 1.72+4.95*max(0,1-(x/15.3)**2)

def make_bridge():
    g=Geo('虹桥_编木拱'); span=15.3; width=6.0
    # 多道交叠直木形成拱架，桥中没有落水桥墩。
    xs=[-15.7,-12,-8,-4,0,4,8,12,15.7]
    for y in [-2.65,-1.7,-.8,.8,1.7,2.65]:
        for i,(a,b) in enumerate(zip(xs[:-1],xs[1:])):
            g.beam((a,y,bridge_z(a)-.68),(b,y,bridge_z(b)-.68),.36,M['wood'],.45)
        for i in range(1,len(xs)-1):
            x=xs[i]
            g.beam((x-3,y,bridge_z(x-3)-1.3),(x+3,y,bridge_z(x+3)-.52),.27,M['dark'])
    for i in range(23):
        x=-15+i*30/22;z=bridge_z(x)
        g.beam((x,-3.32,z-.45),(x,3.32,z-.45),.23,M['dark'])
        if abs(x)<13:
            g.beam((x-.9,-2.7,z-.8),(x+.9,2.7,z-.8),.16,M['wood'])
    for i in range(153):
        x=-15.3+i*.2
        g.beam((x,-3.08,bridge_z(x)),(x,3.08,bridge_z(x)),.188,M['wood'],.14)
    for side in [-1,1]:
        y=side*3.06
        for i in range(32):
            x=-15.2+i*30.4/31;z=bridge_z(x)
            g.beam((x,y,z),(x,y,z+1.07),.13,M['dark'])
            g.ball((x,y,z+1.12),(.115,.115,.09),M['wood'],8,4)
        for h in [.38,.76,1.04]:
            for a,b in zip(xs[:-1],xs[1:]):
                g.beam((a,y,bridge_z(a)+h),(b,y,bridge_z(b)+h),.11,M['wood'])
    for s in [-1,1]:
        for y in [-3.2,3.2]:
            g.box((s*15.65,y,.9),(1.5,1.25,1.9),M['stone'])
            g.beam((s*16,y,1.8),(s*16,y,8.7),.22,M['wood'])
            g.beam((s*16,y,8.6),(s*16+1.8,y,8.6),.14,M['wood'])
            flag('桥头长幡',(s*16+.7,y,8.5),1.0,2.2,M['linen'],.0)
    for x in [-9,-4,4,9]:
        z=bridge_z(x)+.12
        g.box((x,2.05,z+.65),(1.7,.78,.09),M['wood'])
        for dx in [-.67,.67]:
            for yy in [1.76,2.33]:g.beam((x+dx,yy,bridge_z(x+dx)+.1),(x+dx,yy,z+.64),.065,M['dark'])
        for dx in [-.5,0,.5]:pottery(g,(x+dx,2.05,z+.71),.36,True)
    g.finish()

def flag(name,loc,w,h,material,angle=0):
    g=Geo(name);nx=8;nz=14;vs=[]
    for j in range(nz+1):
        for i in range(nx+1):
            u=i/nx;v=j/nz
            vs.append((w*u,.12*v*math.sin(u*4+v*3),-h*v))
    fs=[(j*(nx+1)+i,j*(nx+1)+i+1,(j+1)*(nx+1)+i+1,(j+1)*(nx+1)+i) for j in range(nz) for i in range(nx)]
    g.mesh(vs,fs,material,True);o=g.finish()[0];o.location=loc;o.rotation_euler.z=angle
    o.shape_key_add(name='悬垂'); key=o.shape_key_add(name='风吹');ph=RNG.uniform(0,6)
    for i,v in enumerate(key.data):
        x,y,z=vs[i];d=-z/h
        v.co.y=y+.28*d*math.sin(d*5+x*4+ph);v.co.x=x+.075*d*math.sin(d*6+ph)
    d=key.driver_add('value').driver;d.expression=f'0.5+0.5*sin(frame*0.065+{ph:.4f})'
    sol=o.modifiers.new('布料厚度','SOLIDIFY');sol.thickness=.007
    return o

def roof(g,w,d,z,h,detail=1):
    def rz(x,s): return z+h*(1-s)+.28*s**5+.11*(abs(x)/(w/2))**6
    cols=max(10,int(w/(.23 if detail else .42)));rows=max(7,int(d/.46))
    # 铺瓦的每条瓦沟均是几何曲面，避免屋顶成为平板。
    for side in [-1,1]:
        for col in range(cols):
            xa=-w/2+w*col/cols;xb=-w/2+w*(col+1)/cols
            for row in range(rows):
                s0=row/rows;s1=min(1,(row+1.08)/rows);vs=[]
                for s in [s0,s1]:
                    for k in range(5):
                        t=k/4;x=xa+(xb-xa)*t
                        vs.append((x,side*s*d/2,rz(x,s)+.032*math.cos(t*math.pi*2)+.025))
                g.mesh(vs,[(i,i+1,i+6,i+5) for i in range(4)],RNG.choice(M['tiles']),True)
        for x in [-w/2,w/2]:
            pts=[(x,side*(i/12)*d/2,rz(x,i/12)-.05) for i in range(13)]
            g.tube(pts,.085,M['dark'],7)
        g.beam((-w/2,side*d/2,z+.23),(w/2,side*d/2,z+.23),.12,M['dark'])
        for i in range(max(9,int(w/.42))):
            x=-w/2+w*i/max(9,int(w/.42))
            g.beam((x,side*(d/2-.5),z+.17),(x,side*(d/2+.07),z+.17),.07,M['wood'])
    g.tube([(-w/2,0,z+h+.13),(0,0,z+h+.1),(w/2,0,z+h+.13)],.125,M['tiles'][3],9)
    for x in [-w/2,w/2]:
        g.beam((x,-d*.46,z+.2),(x,0,z+h-.07),.15,M['wood'])
        g.beam((x,0,z+h-.07),(x,d*.46,z+.2),.15,M['wood'])

def pottery(g,c,scale=1,ceramic=False):
    x,y,z=c;prof=[(0,.19),(.08,.23),(.25,.32),(.45,.3),(.6,.18),(.66,.16),(.69,.18),(.71,.18),(.71,.13),(.66,.13)]
    g.lathe((x,y,z),[(a*scale,b*scale) for a,b in prof],M['celadon' if ceramic else 'clay'],16)

def basket(g,c,r=.34,h=.43):
    x,y,z=c;g.cyl((x,y,z+h/2),r*.8,h,M['basket'],14,r)
    for i in range(6):
        zz=z+h*i/5;rr=r*(.8+.2*i/5)
        g.tube([(x+rr*math.cos(a*math.pi/12),y+rr*math.sin(a*math.pi/12),zz) for a in range(25)],.016,M['rope'],5)
    g.tube([(x+r*math.cos(a*math.pi/12),y+r*math.sin(a*math.pi/12),z+h+.012) for a in range(25)],.025,M['lightwood'],6)

def stall(g,x,y,z,goods=0):
    g.box((x,y,z+.72),(2.6,1.15,.12),M['wood'])
    for dx in [-1.05,1.05]:
        for dy in [-.42,.42]:g.beam((x+dx,y+dy,z),(x+dx,y+dy,z+.7),.1,M['dark'])
    for i in range(7):
        xx=x+RNG.uniform(-1.06,1.06);yy=y+RNG.uniform(-.35,.35)
        if goods%3==0:pottery(g,(xx,yy,z+.8),RNG.uniform(.28,.55),True)
        elif goods%3==1:basket(g,(xx,yy,z+.8),.16,.12)
        else:g.ball((xx,yy,z+.86),(.17,.13,.07),M['linen'],10,5)
    for i in range(2):basket(g,(x-1.55+i*3.1,y,z),.38,.52)

def house(name,x,y,w,d,h=3.8,angle=0,shop=True,detail=1):
    g=Geo(name,(x,y,1.65),angle)
    g.box((0,0,.12),(w+.35,d+.35,.25),M['stone'])
    g.box((0,0,h/2),(w,d,h),M['plaster'])
    # 真实柱网、檐下梁、木窗与可见室内暗部。
    n=max(2,round(w/2.1))
    for side in [-1,1]:
        for i in range(n+1):
            xx=-w/2+w*i/n
            g.beam((xx,side*(d/2+.035),.13),(xx,side*(d/2+.035),h+.15),.16,M['dark'])
        for z in [.35,h*.68,h-.14]:g.beam((-w/2,side*(d/2+.03),z),(w/2,side*(d/2+.03),z),.13,M['wood'])
    for side in [-1,1]:
        for yy in [-d*.48,0,d*.48]:g.beam((side*w/2,yy,0),(side*w/2,yy,h+.08),.13,M['wood'])
    for i in range(n):
        xx=-w/2+w*(i+.5)/n;bw=w/n-.32
        if i==n//2:
            g.box((xx,-d/2-.04,1.2),(bw,.12,2.35),M['dark'])
            for side in [-1,1]:g.box((xx+side*bw*.48,-d/2-.14,1.2),(.14,.25,2.4),M['wood'])
            if shop:
                for k in range(3):pottery(g,(xx-.38+k*.38,-d/2+.02,.2),.8)
        else:
            g.box((xx,-d/2-.04,h*.46),(bw,.09,h*.5),M['dark'])
            for k in range(7):g.beam((xx-bw/2+k*bw/6,-d/2-.11,h*.23),(xx-bw/2+k*bw/6,-d/2-.11,h*.68),.035,M['lightwood'])
            for zz in [h*.28,h*.41,h*.55,h*.65]:g.beam((xx-bw/2,-d/2-.13,zz),(xx+bw/2,-d/2-.13,zz),.035,M['wood'])
    if h>5:
        for z in [h*.5,h*.53]:g.beam((-w/2,-d/2-.2,z),(w/2,-d/2-.2,z),.2,M['wood'])
        for i in range(14):
            xx=-w/2+w*i/13;g.beam((xx,-d/2-.3,h*.5),(xx,-d/2-.3,h*.5+.78),.06,M['wood'])
        g.beam((-w/2,-d/2-.3,h*.5+.78),(w/2,-d/2-.3,h*.5+.78),.075,M['dark'])
    roof(g,w+1.05,d+1.25,h,RNG.uniform(1.1,1.75),detail)
    if shop:
        # 檐外棚架和垂挂布幌，与店铺的局部朝向一致。
        for xx in [-w*.4,w*.4]:g.beam((xx,-d/2-1.9,0),(xx,-d/2-1.9,2.55),.09,M['dark'])
        for xx in [-w*.4,w*.4]:g.beam((xx,-d/2,3.0),(xx,-d/2-2.15,2.55),.075,M['lightwood'])
        verts=[(-w*.46,-d/2,3.0),(w*.46,-d/2,3.0),(w*.46,-d/2-2.15,2.58),(-w*.46,-d/2-2.15,2.58)]
        g.mesh(verts,[(0,1,2,3)],M['linen'])
        if abs(y)<45:stall(g,0,-d/2-1.2,0,RNG.randint(0,3))
        p=g.point((w*.45,-d/2-.4,3.2))
        flag(name+'_招幌',p,.7,1.7,M['ochre'] if RNG.random()<.38 else M['linen'],angle)
    g.finish()
    if shop and abs(y)<50:
        p=g.point((w*.45+.08,-d/2-.47,2.9));sign('酒' if RNG.random()<.4 else RNG.choice(['茶','布','食','药']),p,angle,.4)

FONT=None
def sign(text,pos,angle,size):
    global FONT
    if FONT is None:
        for path in [str(ROOT/'assets/fonts/NotoSerifCJKsc-Regular.otf'),'/System/Library/Fonts/Supplemental/Songti.ttc']:
            if Path(path).exists():FONT=bpy.data.fonts.load(path);break
    cu=bpy.data.curves.new('商铺文字','FONT');cu.body=text;cu.size=size;cu.extrude=.001
    if FONT:cu.font=FONT
    cu.materials.append(M['black']);o=bpy.data.objects.new('招牌_'+text,cu);bpy.context.scene.collection.objects.link(o)
    o.location=pos;o.rotation_euler=(math.pi/2,0,angle)

def make_city():
    for side in [-1,1]:
        # 临河通道为步行街，桥头留出开敞集市。
        y=-83;index=0
        while y<89:
            w=RNG.uniform(5,8);d=RNG.uniform(4.7,6.4)
            if abs(y)<6:y=9
            house(f'临河民居_{side}_{index}',side*(23+d/2),y,w,d,RNG.uniform(3.2,4.4),-side*math.pi/2,True)
            y+=w+RNG.uniform(.9,2.6);index+=1
        for row in range(2):
            y=-98+RNG.uniform(0,7);index=0
            while y<110:
                w=RNG.uniform(5.3,9);d=RNG.uniform(5,8)
                h=RNG.uniform(3,4.7) if RNG.random()<.86 else RNG.uniform(5.2,6.6)
                if abs(y)<4:y=7
                house(f'后街民居_{side}_{row}_{index}',side*(39+row*13),y,w,d,h,-side*math.pi/2,False,0)
                y+=w+RNG.uniform(1,3);index+=1
    # 桥头一座较大的临街酒楼，保持民居式灰瓦木楼。
    house('桥头酒楼',-27,-12,9,7,6.2,math.pi/2,True)
    # 远处城门与夯土城墙只用于建立城市层次。
    g=Geo('远景城廓')
    for side in [-1,1]:g.box((side*43,111,4.6),(69,3.8,8.8),M['bank'])
    for x in range(-77,78,3):
        if abs(x)>8:g.box((x,111,9.5),(1.65,3.8,1.1),M['stone'])
    for x in [-8,8]:g.box((x,111,5.6),(3.5,7,11.2),M['stone'])
    g.box((0,111,10),(18,7,2.2),M['stone']);g.finish()
    gate=Geo('城楼上层',(0,111,11));gate.box((0,0,1),(17,7,2),M['plaster'])
    for xx in range(-8,9,2):gate.beam((xx,-3.55,0),(xx,-3.55,2.8),.2,M['dark'])
    roof(gate,20,10,2.6,2.1,0);gate.finish()

def bankx(y,side): return side*(15.35+.35*math.sin(y*.09))+1.6*math.sin(y*.022)

def make_ground():
    g=Geo('土岸与街道')
    for side in [-1,1]:
        verts=[];faces=[]
        for i in range(121):
            y=-180+i*3;x=bankx(y,side)
            verts.extend([(x,y,1.62),(side*130,y,1.62),(x-side*.8,y,-.4)])
        for i in range(120):
            q=i*3;faces.extend([(q,q+3,q+4,q+1),(q,q+2,q+5,q+3)])
        g.mesh(verts,faces[::2],M['earth'])
        g.mesh(verts,faces[1::2],M['bank'])
        for i in range(100):
            y=RNG.uniform(-125,125);x=bankx(y,side)
            g.ball((x+side*.2,y,.75),(RNG.uniform(.3,.8),RNG.uniform(.35,.8),RNG.uniform(.3,.65)),M['stone'],7,4)
        # 码头木栈道、系缆桩、木梯。
        for y in [-43,-21,27,52,79]:
            for x in [side*14.2,side*16.8]:
                for yy in [y-2.1,y+2.1]:g.cyl((x,yy,.3),.15,3,M['dark'],9)
            for i in range(18):g.box((side*15.6,y-2.15+i*.25,1.05),(3.4,.23,.13),M['wood'])
            for yy in [y-1.7,y+1.7]:g.cyl((side*15.1,yy,1.5),.12,1,M['wood'],9)
    # 拱桥两端铺石，向街市过渡为车辙土路。
    for side in [-1,1]:
        for i in range(15):
            for j in range(9):
                g.box((side*(16+i*.49),-2.4+j*.57,1.66),(.47,.55,.08),M['stone'])
    g.finish()

def carts_and_street_detail():
    for x,y,a in [(-20,-14,.3),(20,10,-.1),(-20,34,.15),(21,-35,.2)]:
        g=Geo('市井木车',(x,y,1.64),a)
        for i in range(10):g.box((0,-1.1+i*.24,.65),(1.2,.22,.12),M['wood'])
        for side in [-1,1]:
            g.beam((side*.52,-1.4,.56),(side*.52,2.0,.72),.085,M['dark'])
            pts=[(side*.75,.6*math.sin(j*math.tau/24),.61+.6*math.cos(j*math.tau/24)) for j in range(25)]
            g.tube(pts,.07,M['dark'],6)
            for j in range(10):
                aa=j*math.tau/10;g.beam((side*.75,0,.61),(side*.75,.55*math.sin(aa),.61+.55*math.cos(aa)),.04,M['wood'])
            for yy in [-1.05,1.0]:g.beam((side*.57,yy,.65),(side*.57,yy,1.25),.06,M['wood'])
            g.beam((side*.57,-1.05,1.20),(side*.57,1,1.2),.07,M['wood'])
        g.beam((-.8,0,.61),(.8,0,.61),.15,M['dark'])
        for yy in [-.6,0,.6]:
            g.ball((0,yy,.97),(.48,.38,.25),M['sack'],14,8)
            g.tube([(-.4,yy,1.1),(0,yy+.06,1.22),(.4,yy,1.1)],.016,M['rope'])
        g.finish()
    g=Geo('碎石与落叶')
    for side in [-1,1]:
        for i in range(1100):
            y=RNG.uniform(-76,90);x=side*RNG.uniform(16.5,23.4)
            if RNG.random()<.65:g.ball((x,y,1.63),(RNG.uniform(.018,.09),RNG.uniform(.015,.07),.014),M['stone'],5,3)
            else:
                r=RNG.uniform(.03,.08);g.mesh([(x-r,y,1.637),(x,y-r*2,1.64),(x+r,y,1.639),(x,y+r*2,1.64)],[(0,1,2,3)],M['reed'])
    g.finish()

def make_water():
    m=mat('汴河_流动水面','#617e74',.17)
    n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
    p.inputs['Metallic'].default_value=.1;p.inputs['IOR'].default_value=1.333
    p.inputs['Transmission Weight'].default_value=0.0
    tc=n.new('ShaderNodeTexCoord');add=n.new('ShaderNodeVectorMath');add.operation='ADD'
    l.new(tc.outputs['Object'],add.inputs[0]);add.inputs[1].default_value=(0,0,0)
    add.inputs[1].driver_add('default_value',1).driver.expression='frame*0.006'
    waves=n.new('ShaderNodeTexNoise');waves.inputs['Scale'].default_value=1.9;waves.inputs['Detail'].default_value=3
    stretch=n.new('ShaderNodeVectorMath');stretch.operation='MULTIPLY';stretch.inputs[1].default_value=(.35,3.2,1)
    l.new(add.outputs[0],stretch.inputs[0]);l.new(stretch.outputs[0],waves.inputs['Vector'])
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.32;bump.inputs['Distance'].default_value=.09
    l.new(waves.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],p.inputs['Normal'])
    g=Geo('汴河水面');vs=[];fs=[];nx=28;ny=160
    for j in range(ny+1):
        y=-195+j*390/ny
        for i in range(nx+1):
            x=-18+i*36/nx+1.6*math.sin(y*.022);vs.append((x,y,.04+.018*math.sin(x*1.9+y*.38)))
    for j in range(ny):
        for i in range(nx):
            k=j*(nx+1)+i;fs.append((k,k+1,k+nx+2,k+nx+1))
    g.mesh(vs,fs,m,True);g.finish()
    M['water']=m
    M['foam']=mat('细微船迹','#b5c3b2',.35)

def boat(name,x,y,length=11,width=2.8,heading=0,speed=.18):
    root=empty(name,(x,y,0));root.rotation_euler.z=heading
    g=Geo(name+'_船身');sections=20;levels=6;vs=[];fs=[]
    for k in range(levels):
        t=k/(levels-1);z=-.36+t*1.37
        for i in range(sections+1):
            f=i/sections;yy=(f-.5)*length
            spread=(.2+.8*math.sin(math.pi*f)**.45)*width/2*(.72+.28*t)
            rise=(abs(f-.5)*2)**5*.72
            vs.extend([(-spread,yy,z+rise),(spread,yy,z+rise)])
    for k in range(levels-1):
        for i in range(sections):
            for s in range(2):
                a=k*(sections+1)*2+i*2+s;b=a+(sections+1)*2
                fs.append((a,a+2,b+2,b))
    g.mesh(vs,fs,M['wood'],True)
    for k in range(levels):
        t=k/(levels-1)
        for side in [-1,1]:
            pts=[]
            for i in range(sections+1):
                f=i/sections;ww=(.2+.8*math.sin(math.pi*f)**.45)*width/2*(.72+.28*t)
                pts.append((side*ww,(f-.5)*length,-.36+t*1.37+(abs(f-.5)*2)**5*.72))
            g.tube(pts,.035 if k<levels-1 else .085,M['dark'],7)
    for i in range(int(length/.23)):
        yy=-length*.46+i*.23;f=yy/length+.5;ww=(.2+.8*max(0,math.sin(math.pi*f))**.45)*width
        g.box((0,yy,.89),(ww*.95,.21,.1),M['wood'])
    # 弯竹篷顶与密排竹篾。
    cabin_length=length*.36;cy=-length*.13
    for j in range(32):
        yy=cy-cabin_length/2+cabin_length*j/31
        pts=[(width*.43*math.cos(i*math.pi/14),yy,1.25+width*.4*math.sin(i*math.pi/14)) for i in range(15)]
        g.tube(pts,.065,M['basket'],6)
    for i in range(9):
        a=i*math.pi/8;x0=width*.44*math.cos(a);z=1.26+width*.41*math.sin(a)
        g.beam((x0,cy-cabin_length*.53,z),(x0,cy+cabin_length*.53,z),.05,M['dark'])
    for i in range(7):
        xx=RNG.uniform(-width*.31,width*.31);yy=length*.18+RNG.random()*length*.17
        g.ball((xx,yy,1.1),(width*.2,.39,.23),M['sack'],12,6)
        g.tube([(xx-.2,yy,1.28),(xx,yy+.06,1.32),(xx+.2,yy,1.28)],.018,M['rope'])
    g.beam((0,length*.19,1),(0,length*.11,3.7),.14,M['wood'])
    # 桅杆保持低位以留出过桥净空。
    g.beam((0,-length*.33,1.35),(0,length*.4,3.5),.13,M['lightwood'])
    for side in [-1,1]:
        g.tube([(side*width*.44,-length*.33,1.1),(0,length*.11,3.7),(side*width*.4,length*.37,1.18)],.022,M['rope'],5)
        g.beam((side*width*.31,-length*.36,1.1),(side*width*.8,-length*.61,-.04),.055,M['wood'])
        g.box((side*width*.8,-length*.62,.01),(.26,.65,.08),M['wood'])
    g.finish(root)
    root.location=(x,y,0);root.keyframe_insert('location',frame=1)
    root.location=(x+speed*60*math.sin(heading),y-speed*60*math.cos(heading),0);root.keyframe_insert('location',frame=1440);linear(root)
    for idx in [0,1]:
        root.rotation_euler[idx]=0
        d=root.driver_add('rotation_euler',idx).driver;d.expression=f'{.006 if idx==0 else .008}*sin(frame*0.05+{RNG.random()*6:.4f})'
    # 与船体同速移动的 V 形低对比波纹。
    wake=Geo(name+'_船尾纹')
    for side in [-1,1]:
        for j in range(3):
            pts=[(side*(width*.43+t*.35),length*.43+t,.06+.005*j) for t in [0,.5,1,1.5,2,2.5,3,3.5]]
            wake.tube(pts,.012+j*.003,M['foam'],5)
    wake.finish(root)
    return root

def tree(x,y,h=9,willow=True):
    g=Geo('岸柳',(x,y,1.6));lean=RNG.uniform(-.6,.6)
    trunk=[(0,0,0),(.1,.1,h*.28),(lean,.15,h*.58),(lean+.35,0,h*.82)]
    g.tube(trunk,[.36,.28,.2,.08],M['bark'],9)
    crown=Geo('柳枝与嫩叶');ph=RNG.random()*6
    for b in range(10):
        a=b*math.tau/10+RNG.uniform(-.2,.2);r=RNG.uniform(1.7,3.3)
        origin=(lean,0,h*RNG.uniform(.5,.73));end=(r*math.cos(a),r*math.sin(a),h*RNG.uniform(.82,1.08))
        mid=tuple((origin[i]+end[i])/2 for i in range(3));g.tube([origin,mid,end],[.12,.08,.025],M['bark'],7)
        for k in range(4):
            aa=a+RNG.uniform(-.7,.7);dd=RNG.uniform(1.5,3.8)
            pts=[]
            for q in range(8):
                t=q/7;px=end[0]+t*.85*math.cos(aa);py=end[1]+t*.85*math.sin(aa);pz=end[2]-dd*t*t
                pts.append((px,py,pz))
                if q>1:
                    for sign in [-1,1]:
                        le=(px+sign*.08,py,pz)
                        crown.mesh([le,(px+sign*.2,py+.035,pz+.08),(px+sign*.1,py+.03,pz+.19),(px+sign*.06,py-.02,pz+.11)],[(0,1,2,3)],M['leaf'] if k%3 else M['leaf2'],True)
            crown.tube(pts,[.019*(1-i/9) for i in range(8)],M['bark'],5)
    g.finish();root=empty('风中柳梢',(x,y,1.6));crown.finish(root)
    dr=root.driver_add('rotation_euler',1).driver;dr.expression=f'.014*sin(frame*.022+{ph:.4f})'

def make_environment():
    for side in [-1,1]:
        for y in [-85,-60,-34,19,42,71,91]:tree(side*(17.9+RNG.uniform(0,1.5)),y,RNG.uniform(7,10))
    # 炊烟为低密度分层体积，中心密、边缘透明，轻微上升。
    smoke=bpy.data.materials.new('淡炊烟');smoke.use_nodes=True;n=smoke.node_tree.nodes;n.clear();l=smoke.node_tree.links
    out=n.new('ShaderNodeOutputMaterial');v=n.new('ShaderNodeVolumePrincipled');v.inputs['Color'].default_value=(.7,.74,.69,1)
    tc=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=3;noise.inputs['Detail'].default_value=2
    noise.noise_dimensions='4D';noise.inputs['W'].driver_add('default_value').driver.expression='frame*.003'
    l.new(tc.outputs['Generated'],noise.inputs['Vector']);mathn=n.new('ShaderNodeMath');mathn.operation='MULTIPLY';mathn.inputs[1].default_value=.07;l.new(noise.outputs['Fac'],mathn.inputs[0]);l.new(mathn.outputs[0],v.inputs['Density']);l.new(v.outputs[0],out.inputs['Volume'])
    for x,y in [(-26,-12),(28,28),(-28,39),(26,-41)]:
        g=Geo('炊烟体积')
        for i in range(3):g.ball((x+i*.5,y+i*.18,7+i*1.8),(.45+i*.37,.45+i*.3,1.2),smoke,10,6)
        g.finish()
    g=Geo('河边芦苇')
    for side in [-1,1]:
        for i in range(130):
            y=RNG.uniform(-100,105)
            if abs(y)<6:continue
            x=bankx(y,side)-side*.3;z=RNG.uniform(.8,1.3)
            g.tube([(x,y,.5),(x+.12,y+.06,z),(x+.32,y+.13,z+.55)],.012,M['reed'],5)
    g.finish()

def setup_lighting():
    world=bpy.data.worlds.new('初春晴日');bpy.context.scene.world=world;world.use_nodes=True
    n=world.node_tree.nodes;l=world.node_tree.links;bg=n.get('Background');bg.inputs['Strength'].default_value=.42
    sky=n.new('ShaderNodeTexSky');sky.sky_type='NISHITA';sky.sun_elevation=math.radians(25);sky.sun_rotation=math.radians(132)
    sky.sun_disc=False;sky.air_density=1.1;sky.dust_density=1.25;l.new(sky.outputs[0],bg.inputs[0])
    bg.inputs['Strength'].default_value=.28
    ld=bpy.data.lights.new('暖日光','SUN');ld.energy=3.4;ld.angle=math.radians(3.5);ld.color=(1,.80,.56)
    o=bpy.data.objects.new('暖日光',ld);bpy.context.scene.collection.objects.link(o);o.rotation_euler=(math.radians(62),0,math.radians(-38))
    # 低密度空气透视，全景仍保留细节。
    fog=bpy.data.materials.new('空气薄雾');fog.use_nodes=True;n=fog.node_tree.nodes;n.clear();out=n.new('ShaderNodeOutputMaterial');v=n.new('ShaderNodeVolumePrincipled')
    v.inputs['Density'].default_value=.0009;v.inputs['Color'].default_value=(.77,.8,.75,1);v.inputs['Anisotropy'].default_value=.3
    fog.node_tree.links.new(v.outputs['Volume'],out.inputs['Volume'])
    # 远景空气透视改由三维深度通道合成，炊烟仍使用实际体积。
    scene=bpy.context.scene;scene.view_layers[0].use_pass_mist=True
    world.mist_settings.start=22;world.mist_settings.depth=205;world.mist_settings.falloff='QUADRATIC'
    scene.use_nodes=True;nd=scene.node_tree.nodes;nd.clear();lk=scene.node_tree.links
    rl=nd.new('CompositorNodeRLayers');strength=nd.new('CompositorNodeMath');strength.operation='MULTIPLY';strength.inputs[1].default_value=.63
    lk.new(rl.outputs['Mist'],strength.inputs[0]);mix=nd.new('CompositorNodeMixRGB');mix.blend_type='MIX';mix.inputs[2].default_value=(.40,.46,.44,1)
    lk.new(strength.outputs[0],mix.inputs[0]);lk.new(rl.outputs['Image'],mix.inputs[1]);glow=nd.new('CompositorNodeGlare');glow.glare_type='FOG_GLOW';glow.threshold=2;glow.quality='MEDIUM';glow.size=6
    lk.new(mix.outputs[0],glow.inputs[0]);out=nd.new('CompositorNodeComposite');lk.new(glow.outputs[0],out.inputs[0])
