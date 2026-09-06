"""轻量批量几何工具：将静态细节合并，减少依赖图与内存开销。"""
import bpy, math, random
from collections import defaultdict
from mathutils import Vector
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RNG=random.Random(1145)

def rgb(h):
    h=h.lstrip('#'); vals=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in vals)+(1,)

def mat(name, color, rough=.7, noise=0, scale=12, metallic=0):
    m=bpy.data.materials.new(name); m.use_nodes=True
    n=m.node_tree.nodes; l=m.node_tree.links; p=n.get('Principled BSDF')
    p.inputs['Base Color'].default_value=rgb(color); p.inputs['Roughness'].default_value=rough
    p.inputs['Metallic'].default_value=metallic
    if noise:
        t=n.new('ShaderNodeTexNoise');t.inputs['Scale'].default_value=scale;t.inputs['Detail'].default_value=3
        c=n.new('ShaderNodeTexCoord');l.new(c.outputs['Generated'],t.inputs['Vector'])
        b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=noise;b.inputs['Distance'].default_value=.055
        l.new(t.outputs['Fac'],b.inputs['Height']);l.new(b.outputs['Normal'],p.inputs['Normal'])
    return m

def textured(name, folder, scale=.45, tint=None, rough=.8):
    m=mat(name,tint or '#8b8070',rough)
    n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
    tc=n.new('ShaderNodeTexCoord'); mp=n.new('ShaderNodeVectorMath');mp.operation='SCALE';mp.inputs[3].default_value=scale
    l.new(tc.outputs['Object'],mp.inputs[0])
    for channel,sock in [('Color','Base Color'),('Roughness','Roughness')]:
        path=next((ROOT/'assets/textures'/folder).glob('*_'+channel+'.jpg'))
        im=n.new('ShaderNodeTexImage');im.image=bpy.data.images.load(str(path),check_existing=True)
        im.projection='BOX'; im.projection_blend=.18
        if channel!='Color': im.image.colorspace_settings.name='Non-Color'
        l.new(mp.outputs['Vector'],im.inputs['Vector'])
        if tint and channel=='Color':
            sat=n.new('ShaderNodeHueSaturation');sat.inputs['Saturation'].default_value=.45
            l.new(im.outputs['Color'],sat.inputs['Color'])
            mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=.6;mix.inputs[2].default_value=rgb(tint)
            l.new(sat.outputs[0],mix.inputs[1]);l.new(mix.outputs[0],p.inputs[sock])
            bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.23;bump.inputs['Distance'].default_value=.045
            l.new(im.outputs['Color'],bump.inputs['Height']);l.new(bump.outputs[0],p.inputs['Normal'])
        else:l.new(im.outputs['Color'],p.inputs[sock])
    return m

class Geo:
    def __init__(self,name,origin=(0,0,0),angle=0):
        self.name=name;self.origin=Vector(origin);self.angle=angle
        self.parts=defaultdict(lambda:[[],[],[]])
    def point(self,p):
        x,y,z=p;c=math.cos(self.angle);s=math.sin(self.angle)
        return (self.origin.x+c*x-s*y,self.origin.y+s*x+c*y,self.origin.z+z)
    def mesh(self,verts,faces,material,smooth=False):
        v,f,sm=self.parts[material];k=len(v);v.extend(self.point(p) for p in verts)
        f.extend(tuple(k+i for i in face) for face in faces);sm.extend([smooth]*len(faces))
    def box(self,c,d,m,angle=0):
        x,y,z=c;dx,dy,dz=[a/2 for a in d];cs=math.cos(angle);sn=math.sin(angle)
        verts=[(x+u*cs-v*sn,y+u*sn+v*cs,z+w) for u,v,w in [(-dx,-dy,-dz),(dx,-dy,-dz),(dx,dy,-dz),(-dx,dy,-dz),(-dx,-dy,dz),(dx,-dy,dz),(dx,dy,dz),(-dx,dy,dz)]]
        self.mesh(verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],m)
    def beam(self,a,b,w,m,d=None):
        a=Vector(a);b=Vector(b);axis=(b-a).normalized();u=axis.cross(Vector((0,0,1)))
        if u.length<.01:u=axis.cross(Vector((0,1,0)))
        u.normalize();v=axis.cross(u).normalized();w/=2;d=(d/2 if d else w)
        # 八边倒角截面，保留木梁边缘的受光细节。
        corners=[(-w*.85,-d), (w*.85,-d),(w,-d*.85),(w,d*.85),(w*.85,d),(-w*.85,d),(-w,d*.85),(-w,-d*.85)]
        verts=[tuple(p+u*x+v*y) for p in (a,b) for x,y in corners]
        faces=[tuple(range(7,-1,-1)),tuple(range(8,16))]+[(i,(i+1)%8,(i+1)%8+8,i+8) for i in range(8)]
        self.mesh(verts,faces,m)
    def tube(self,points,r,m,sides=7):
        ps=[Vector(p) for p in points];verts=[]
        for i,p in enumerate(ps):
            tangent=(ps[min(i+1,len(ps)-1)]-ps[max(0,i-1)]).normalized()
            u=tangent.cross(Vector((0,0,1)))
            if u.length<.01:u=tangent.cross(Vector((0,1,0)))
            u.normalize();v=tangent.cross(u)
            ri=r[i] if isinstance(r,(list,tuple)) else r
            verts.extend(tuple(p+ri*(u*math.cos(2*math.pi*j/sides)+v*math.sin(2*math.pi*j/sides))) for j in range(sides))
        fs=[tuple(range(sides-1,-1,-1))]
        fs += [(i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j) for i in range(len(ps)-1) for j in range(sides)]
        fs += [tuple((len(ps)-1)*sides+j for j in range(sides))]
        self.mesh(verts,fs,m,True)
    def cyl(self,c,r,depth,m,sides=12,r2=None):
        x,y,z=c;self.tube([(x,y,z-depth/2),(x,y,z+depth/2)],[r,r if r2 is None else r2],m,sides)
    def ball(self,c,scale,m,seg=12,rings=7):
        verts=[];faces=[]
        for i in range(rings+1):
            ph=math.pi*i/rings
            for j in range(seg):
                th=2*math.pi*j/seg
                verts.append((c[0]+scale[0]*math.sin(ph)*math.cos(th),c[1]+scale[1]*math.sin(ph)*math.sin(th),c[2]+scale[2]*math.cos(ph)))
        for i in range(rings):
            for j in range(seg):faces.append(((i+1)*seg+j,(i+1)*seg+(j+1)%seg,i*seg+(j+1)%seg,i*seg+j))
        self.mesh(verts,faces,m,True)
    def lathe(self,c,profile,m,seg=16):
        verts=[(c[0]+r*math.cos(j*2*math.pi/seg),c[1]+r*math.sin(j*2*math.pi/seg),c[2]+z) for z,r in profile for j in range(seg)]
        fs=[(i*seg+j,i*seg+(j+1)%seg,(i+1)*seg+(j+1)%seg,(i+1)*seg+j) for i in range(len(profile)-1) for j in range(seg)]
        self.mesh(verts,fs,m,True)
    def finish(self,parent=None,collection=None):
        obs=[]; collection=collection or bpy.context.scene.collection
        for m,(vs,fs,sm) in self.parts.items():
            if not fs: continue
            mesh=bpy.data.meshes.new(self.name+'_'+m.name);mesh.from_pydata(vs,[],fs);mesh.materials.append(m);mesh.update()
            for p,s in zip(mesh.polygons,sm):p.use_smooth=s
            ob=bpy.data.objects.new(self.name+'_'+m.name,mesh);collection.objects.link(ob)
            if parent:ob.parent=parent
            obs.append(ob)
        return obs

def empty(name,loc=(0,0,0)):
    o=bpy.data.objects.new(name,None);bpy.context.scene.collection.objects.link(o);o.location=loc;return o

def linear(o):
    if o.animation_data and o.animation_data.action:
        for fc in o.animation_data.action.fcurves:
            for k in fc.keyframe_points:k.interpolation='LINEAR'

def camera_key(cam,frame,pos,target,lens):
    cam.location=pos;cam.rotation_euler=(Vector(target)-Vector(pos)).to_track_quat('-Z','Y').to_euler()
    cam.data.lens=lens;cam.keyframe_insert('location',frame=frame);cam.keyframe_insert('rotation_euler',frame=frame);cam.data.keyframe_insert('lens',frame=frame)
