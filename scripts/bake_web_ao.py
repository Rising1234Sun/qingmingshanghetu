"""为静态建筑烘焙顶点环境遮蔽，增强榫卯与檐下深度，浏览器无需逐帧重算。"""
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import math,time

def bake(objects):
    start=time.time();verts=[];faces=[]
    for ob in objects:
        k=len(verts);verts.extend(tuple(ob.matrix_world@v.co) for v in ob.data.vertices)
        faces.extend(tuple(k+i for i in p.vertices) for p in ob.data.polygons)
    tree=BVHTree.FromPolygons(verts,faces,all_triangles=False,epsilon=.001)
    del verts,faces
    # 同一空间位置共享光照采样，屋瓦重复边界不产生明暗接缝。
    cache={};rays=[Vector((math.cos(i*2.39996)*.74,math.sin(i*2.39996)*.74,.68)) for i in range(6)]
    for oi,ob in enumerate(objects):
        mesh=ob.data;colors=mesh.color_attributes.new(name='环境遮蔽',type='FLOAT_COLOR',domain='POINT');normal_matrix=ob.matrix_world.to_3x3().inverted().transposed()
        for vertex in mesh.vertices:
            p=ob.matrix_world@vertex.co;n=(normal_matrix@vertex.normal).normalized()
            key=(round(p.x,2),round(p.y,2),round(p.z,2),round(n.x,1),round(n.y,1),round(n.z,1))
            factor=cache.get(key)
            if factor is None:
                tangent=n.cross(Vector((0,0,1)))
                if tangent.length<.01:tangent=n.cross(Vector((0,1,0)))
                tangent.normalize();bitangent=n.cross(tangent);origin=p+n*.025;occ=0
                for ray in rays:
                    direction=tangent*ray.x+bitangent*ray.y+n*ray.z
                    hit,_,_,distance=tree.ray_cast(origin,direction,2.8)
                    if hit is not None:occ+=(1-distance/2.8)**.7
                factor=max(.36,1-occ/6*.76);cache[key]=factor
            colors.data[vertex.index].color=(factor,factor,factor,1)
        if oi%10==0:print(f'顶点遮蔽 {oi+1}/{len(objects)}, {time.time()-start:.1f} 秒',flush=True)
    print(f'静态顶点遮蔽完成 {len(cache)} 采样点，{time.time()-start:.1f} 秒',flush=True)
