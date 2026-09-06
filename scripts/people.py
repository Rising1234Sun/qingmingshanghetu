"""MakeHuman 核心面部网格、宋式衣帽与可编辑的骨节动画。"""
import bpy,math,random
from geometry import *
from scenery import M,bridge_z,basket

HEAD=None
EYES=None
GARMENTS=[]

def prepare_people():
    global HEAD,EYES
    vs=[];uvs=[];faces=[];group=''
    for line in (ROOT/'assets/characters/base.obj').read_text().splitlines():
        tok=line.split()
        if not tok:continue
        if tok[0]=='v':vs.append(tuple(map(float,tok[1:4])))
        elif tok[0]=='vt':uvs.append(tuple(map(float,tok[1:3])))
        elif tok[0]=='g':group=tok[1]
        elif tok[0]=='f' and group=='body':
            f=[(int(t.split('/')[0])-1,int(t.split('/')[1])-1) for t in tok[1:]]
            if all(vs[a][1]>5.35 for a,b in f):faces.append(f)
    target=ROOT/'assets/characters/asian-male-young.target'
    if target.exists():
        for line in target.read_text().splitlines():
            tok=line.split()
            if len(tok)==4 and tok[0].isdigit():
                i=int(tok[0]);vs[i]=tuple(vs[i][k]+.6*float(tok[k+1]) for k in range(3))
    used=sorted(set(i for f in faces for i,j in f));index={v:i for i,v in enumerate(used)}
    scale=1.74/16.91
    verts=[(vs[i][0]*scale,-vs[i][2]*scale,(vs[i][1]+8.42)*scale) for i in used]
    mesh=bpy.data.meshes.new('MakeHuman_CC0_面部');mesh.from_pydata(verts,[],[[index[i] for i,j in f] for f in faces]);mesh.update()
    uv=mesh.uv_layers.new(name='MakeHuman原始UV')
    for poly,face in zip(mesh.polygons,faces):
        poly.use_smooth=True
        for loop,(i,j) in zip(poly.loop_indices,face):uv.data[loop].uv=uvs[j]
    skin=mat('人物皮肤_开放采样','#b58a69',.67,.07,60)
    n=skin.node_tree.nodes;l=skin.node_tree.links;p=n.get('Principled BSDF');p.inputs['Subsurface Weight'].default_value=.08
    choices=list((ROOT/'assets/characters').glob('middleage_lightskinned_male_diffuse2.png'))
    if choices:
        tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(choices[0]));l.new(tex.outputs['Color'],p.inputs['Base Color'])
    mesh.materials.append(skin);HEAD=mesh;M['skin']=skin
    # 使用同一开放基础模型的眼球与虹膜 UV，补足原先的空眼眶。
    eye_path=ROOT/'assets/characters/eyes.obj'
    if eye_path.exists():
        ev=[];et=[];ef=[]
        for line in eye_path.read_text().splitlines():
            t=line.split()
            if not t:continue
            if t[0]=='v':
                x,y,z=map(float,t[1:4]);ev.append((x*scale,-z*scale,(y+8.42)*scale))
            elif t[0]=='vt':et.append(tuple(map(float,t[1:3])))
            elif t[0]=='f':ef.append([(int(s.split('/')[0])-1,int(s.split('/')[1])-1) for s in t[1:]])
        EYES=bpy.data.meshes.new('MakeHuman_CC0_眼球');EYES.from_pydata(ev,[],[[i for i,j in f] for f in ef]);EYES.update()
        eu=EYES.uv_layers.new(name='眼球UV')
        for poly,face in zip(EYES.polygons,ef):
            poly.use_smooth=True
            for loop,(i,j) in zip(poly.loop_indices,face):eu.data[loop].uv=et[j]
        EYES.materials.append(mat('人物眼睛','#b7a998',.26))
    M['hair']=mat('人物发髻','#242420',.76,.16,45)
    M['shoe']=mat('布鞋','#313635',.94)
    for i,c in enumerate(['#657471','#9a8b71','#667988','#8c6250','#aaa58c','#545d63','#a69781','#76694f']):
        GARMENTS.append(mat(f'衣料_{i}',c,.91,.16,110))

def robe(g,m,short=False):
    rings=[(.57 if short else .20,.245,.162),(.69,.213,.153),(.82,.171,.137),(.94,.179,.138),(1.07,.192,.142),(1.21,.221,.15),(1.31,.242,.137),(1.36,.214,.112),(1.40,.145,.090),(1.44,.078,.074)]
    verts=[];segments=32
    for z,rx,ry in rings:
        for i in range(segments):
            a=i*math.tau/segments;fold=1+(.026+max(0,.92-z)*.15)*math.cos(a*9+z*1.7)+.012*math.sin(a*17-z*8)
            verts.append((rx*math.cos(a)*fold,ry*math.sin(a)*fold,z))
    faces=[(r*segments+i,r*segments+(i+1)%segments,(r+1)*segments+(i+1)%segments,(r+1)*segments+i) for r in range(len(rings)-1) for i in range(segments)]
    g.mesh(verts,faces,m,True)
    # 交领、腰带、衣襟具有独立厚度。
    g.beam((-.071,-.073,1.43),(.11,-.145,1.18),.032,M['linen'],.012)
    g.beam((.071,-.073,1.43),(-.055,-.143,1.12),.032,M['linen'],.012)
    g.tube([(.182*math.cos(i*math.tau/24),.138*math.sin(i*math.tau/24),.94) for i in range(25)],.026,M['dark'],5)
    g.beam((.10,-.151,.92),(.08,-.168,.56),.025,M['dark'])

def limb_mesh(m,kind):
    g=Geo('衣袖' if kind=='arm' else '裤脚')
    if kind=='arm':
        g.tube([(0,0,.04),(0,0,-.045),(.013,-.006,-.13),(.017,-.01,-.23),(.012,-.014,-.32),(0,-.025,-.42),(0,-.025,-.45)],[.068,.096,.112,.125,.122,.105,.09],m,20)
        g.ball((0,-.025,-.48),(.055,.04,.072),M['skin'],10,6)
        for i in range(4):g.tube([(-.03+i*.02,-.03,-.50),(-.03+i*.02,-.035,-.56)],.009,M['skin'],5)
    else:
        g.tube([(0,0,0),(0,0,-.29),(0,0,-.55)],[.084,.067,.055],m,10)
        g.ball((0,-.075,-.57),(.076,.15,.065),M['shoe'],12,6)
    return g

PROTOTYPES={}
def prototype(style):
    if style in PROTOTYPES:return PROTOTYPES[style]
    col=bpy.data.collections.new(f'衣饰模板_{style}');bpy.context.scene.collection.children.link(col)
    # 模板隐藏仅限对象本身，实例使用相同网格数据。
    m=GARMENTS[style%len(GARMENTS)];g=Geo('衣身模板');robe(g,m,style%3==0)
    g.ball((0,.036,1.65),(.094,.087,.105),M['hair'],14,8)
    g.ball((0,.005,1.714),(.086,.085,.045),M['hair'],16,9)
    if style%4==0:
        g.ball((0,.025,1.762),(.16,.13,.075),M['hair'],12,6)
        for side in [-1,1]:g.box((side*.15,.03,1.76),(.13,.065,.025),M['hair'])
    elif style%4==1:
        g.cyl((0,.025,1.765),.052,.10,M['hair'],10,.035)
        g.beam((-.087,.025,1.76),(.083,.025,1.76),.012,M['lightwood'])
    elif style%4==2:
        g.lathe((0,0,1.72),[(0,.21),(.05,.13),(.14,.025)],M['basket'],20)
    else:g.ball((0,.025,1.747),(.102,.092,.066),M['linen'],12,6)
    body=g.finish(collection=col)
    # 网格原型不进入渲染，复制时只共享 data。
    arm=limb_mesh(m,'arm').finish(collection=col);leg=limb_mesh(M['dark'],'leg').finish(collection=col)
    for ob in body+arm+leg:ob.hide_render=True;ob.hide_set(True)
    PROTOTYPES[style]=(body,arm,leg)
    return PROTOTYPES[style]

def copies(objs,parent,name):
    for proto in objs:
        ob=bpy.data.objects.new(name,proto.data);bpy.context.scene.collection.objects.link(ob);ob.parent=parent

def person(name,pos,style=0,angle=0,walk=None,parent=None,scale=1,role='walk'):
    body,arm,leg=prototype(style);root=empty(name,pos);root.rotation_euler.z=angle;root.scale=(scale,)*3
    if parent:root.parent=parent
    copies(body,root,name+'_衣身')
    head=bpy.data.objects.new(name+'_面部',HEAD);bpy.context.scene.collection.objects.link(head);head.parent=root
    if EYES:
        eyes=bpy.data.objects.new(name+'_眼球',EYES);bpy.context.scene.collection.objects.link(eyes);eyes.parent=root
    phase=RNG.uniform(0,math.tau);period=28.8
    gait=.2
    if walk:
        pa,pb,_=walk;speed=math.hypot(pb[0]-pa[0],pb[1]-pa[1])/60
        gait=min(.42,max(.10,math.asin(min(.9,speed*(period/24)/(2*.57)))))
    for side in [-1,1]:
        shoulder=empty(name+'_肩',(.235*side,0,1.33));shoulder.parent=root;copies(arm,shoulder,name+'_衣袖')
        hip=empty(name+'_腿',(.1*side,0,.62));hip.parent=root;copies(leg,hip,name+'_裤脚')
        if walk:
            for f in range(1,1442,6):
                th=(f-1)*math.tau/period+phase
                shoulder.rotation_euler.x=side*gait*.8*math.sin(th);shoulder.rotation_euler.y=side*.13
                shoulder.keyframe_insert('rotation_euler',frame=f)
                hip.rotation_euler.x=-side*gait*math.sin(th);hip.keyframe_insert('rotation_euler',frame=f)
        else:
            shoulder.rotation_euler.y=side*.10
            base=-.65 if role in ['vendor','crew'] else -.12
            shoulder.driver_add('rotation_euler',0).driver.expression=f'{base}+0.10*sin(frame*.035+{phase+side:.4f})'
        linear(shoulder);linear(hip)
    if walk:
        start,end,kind=walk
        for f in range(1,1442,12):
            t=(f-1)/1439
            x=start[0]+t*(end[0]-start[0]);y=start[1]+t*(end[1]-start[1]);z=bridge_z(x)+.085 if kind=='bridge' and abs(x)<15.3 else 1.635
            root.location=(x,y,z+.011*math.sin((f-1)*math.tau/period*2+phase));root.keyframe_insert('location',frame=f)
        linear(root)
    if role=='porter':
        g=Geo(name+'_扁担');g.beam((-.77,0,1.37),(.77,0,1.37),.052,M['lightwood'])
        for side in [-1,1]:
            g.tube([(side*.66,0,1.37),(side*.66,0,.46)],.018,M['rope']);basket(g,(side*.66,0,.18),.2,.3)
        g.finish(root)
    return root

def populate(boats):
    prepare_people()
    # 桥面双向通行，摊贩聚于两侧，不占据通船空间。
    for i in range(44):
        x=-14.5+(i//2)*29/21;direction=1 if i%2 else -1;yy=(.72 if i%11==0 else 1.10)*(-direction)
        distance=12;end=max(-21,min(21,x+direction*distance))
        person(f'桥上行人_{i}',(x,yy,bridge_z(x)),i%8,direction*math.pi/2,((x,yy),(end,yy),'bridge'),scale=RNG.uniform(.91,1.04),role='porter' if i%11==0 else 'walk')
    for side in [-1,1]:
        for i in range(58):
            y=-57+i*2.05;x=side*(22.6+RNG.uniform(-.3,.3))
            if i%3==0:
                x=side*(19.1 if i%2 else 20.8)
                person(f'街市行人_{side}_{i}',(x,y,1.635),i%8,0 if i%2 else math.pi,((x,y),(x,y+(-1 if i%2 else 1)*28),'street'),scale=RNG.uniform(.90,1.07),role='porter' if i%10==0 else 'walk')
            else:person(f'街市买卖_{side}_{i}',(x,y,1.635),i%8,side*math.pi/2,scale=RNG.uniform(.91,1.04),role='vendor')
    for i,b in enumerate(boats):
        person(f'船工_{i}',(.6,3.1,.99),i%8,.3,parent=b,role='crew',scale=.97)
        g=Geo(f'船工篙_{i}');g.beam((.85,2.9,1.6),(1.7,5.2,-.05),.04,M['lightwood']);g.finish(b)
