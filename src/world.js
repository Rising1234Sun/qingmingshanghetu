import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { Water } from 'three/addons/objects/Water.js';
import { Sky } from 'three/addons/objects/Sky.js';
import { assetUrl } from './paths.js';

export const toWorld = (x, y, z) => new THREE.Vector3(x, z, -y);
const temp = new THREE.Object3D();
const clockUniform = { value: 0 };

// 固定种子使每次打开、录制时的附加细节保持一致。
function seeded(seed = 1145) {
  return () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
}

function surfaceMaterial(material, textures, kind = '') {
  const name = material.name;
  material.roughness = Math.max(.35, material.roughness);
  material.envMapIntensity = .10;
  material.side = THREE.DoubleSide;
  const isCloth=/衣料|麻布|布幌|粮袋/.test(name),isPlaster=name.includes('灰泥');
  let map = name.includes('旧木') ? textures.wood : name.includes('泥土') ? textures.ground : isCloth ? textures.cloth : isPlaster ? textures.plaster : null;
  const isGround = name.includes('泥土');
  const isTile = name.includes('筒瓦');
  if (isTile) { material.color.multiplyScalar(.78); material.roughness = .81; }
  if (name.includes('青瓷')) { material.roughness = .24; material.envMapIntensity = .8; }
  material.onBeforeCompile = shader => {
    shader.uniforms.uTime = clockUniform;
    if (map) shader.uniforms.uSurfaceMap = { value: map };
    shader.vertexShader = `varying vec3 vSurfaceWorld; varying vec3 vSurfaceNormal; uniform float uTime;\n` + shader.vertexShader;
    if (kind === 'flag') shader.vertexShader = shader.vertexShader.replace('#include <begin_vertex>', `#include <begin_vertex>
      float loose = max(-position.y, 0.0); transformed.z += sin(position.x*4.0 + position.y*3.0 + uTime*2.1)*loose*.095;
      transformed.x += sin(position.y*3.7+uTime*1.6)*loose*.027;`);
    shader.vertexShader = shader.vertexShader.replace('#include <worldpos_vertex>', `#include <worldpos_vertex>
      vec4 surfacePosition = vec4(transformed,1.0);
      #ifdef USE_INSTANCING
        surfacePosition = instanceMatrix * surfacePosition;
      #endif
      vSurfaceWorld = (modelMatrix * surfacePosition).xyz;
      vSurfaceNormal = normalize(mat3(modelMatrix) * objectNormal);`);
    shader.fragmentShader = `varying vec3 vSurfaceWorld; varying vec3 vSurfaceNormal; ${map ? 'uniform sampler2D uSurfaceMap;' : ''}
      float grain(vec3 p) { return fract(sin(dot(p,vec3(12.9898,78.233,54.53)))*43758.5453); }
    ` + shader.fragmentShader;
    shader.fragmentShader = shader.fragmentShader.replace('#include <color_fragment>', `#include <color_fragment>
      ${map ? `vec3 weights = pow(abs(normalize(vSurfaceNormal)),vec3(6.0)); weights /= max(dot(weights,vec3(1.0)),.0001);
        vec3 p = vSurfaceWorld * ${isGround ? '.30' : isCloth ? '5.0' : isPlaster ? '.7' : '.65'};
        vec3 pigment = texture2D(uSurfaceMap,p.yz).rgb*weights.x + texture2D(uSurfaceMap,p.xz).rgb*weights.y + texture2D(uSurfaceMap,p.xy).rgb*weights.z;
        ${isGround ? 'pigment = mix(pigment, texture2D(uSurfaceMap,mat2(.8,-.6,.6,.8)*p.xz*1.37+vec2(.27,.61)).rgb,.5);' : ''}
        float lum = dot(pigment,vec3(.299,.587,.114));
        diffuseColor.rgb *= mix(vec3(lum),pigment,${isGround ? '.23' : '.60'})*${isGround ? '1.45' : '1.45'} + .17;` : ''}
      float age = .98 + .02*sin(vSurfaceWorld.x*3.7 + sin(vSurfaceWorld.z*4.0))*sin(vSurfaceWorld.y*12.0);
      diffuseColor.rgb *= age;
      ${name.includes('灰泥') ? 'diffuseColor.rgb *= .78+.22*smoothstep(1.6,3.0,vSurfaceWorld.y);' : ''}
    `);
    if(map&&!isGround)shader.fragmentShader=shader.fragmentShader.replace('#include <normal_fragment_maps>',`#include <normal_fragment_maps>
      vec3 sx=dFdx(-vViewPosition),sy=dFdy(-vViewPosition);
      vec3 r1=cross(sy,normal),r2=cross(normal,sx);
      float determinant=dot(sx,r1);
      vec3 grad=sign(determinant)*(dFdx(lum)*r1+dFdy(lum)*r2);
      normal=normalize(abs(determinant)*normal-grad*${isGround?'.065':isCloth?'.018':'.025'});
    `);
  };
  material.customProgramCacheKey = () => name + kind;
  return material;
}

export async function createWorld(scene, renderer, progress) {
  const textureLoader = new THREE.TextureLoader();
  const [wood, ground, skin, waterNormal,cloth,plaster,eyes] = await Promise.all([
    '/textures/wood.jpg', '/textures/ground.jpg', '/textures/skin.jpg', '/textures/water-normal.png','/textures/cloth.jpg','/textures/plaster.jpg','/textures/eyes.png',
  ].map(path => textureLoader.loadAsync(assetUrl(path))));
  for (const t of [wood, ground, waterNormal,cloth,plaster]) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 8; }
  wood.colorSpace = ground.colorSpace = skin.colorSpace = THREE.SRGBColorSpace;
  skin.flipY = false;
  eyes.flipY=false;eyes.colorSpace=THREE.SRGBColorSpace;

  const draco = new DRACOLoader(); draco.setDecoderPath(assetUrl('draco/')); draco.setWorkerLimit(2);
  const loader = new GLTFLoader(); loader.setDRACOLoader(draco);
  const gltf = await loader.loadAsync(assetUrl('models/bianjing.glb'), e => progress(e.total ? e.loaded / e.total : 0, '载入三维街区与人物'));
  progress(.97, '布置光影，唤醒市井');
  const model = gltf.scene;
  scene.add(model);
  const materials = new Set(), people = [], boats = [], willows = [], flags = [], staticMeshes = [];
  model.traverse(o => {
    if (o.userData.web_kind === 'person') {
      o.userData.basePosition = o.position.clone();
      o.userData.baseQuaternion = o.quaternion.clone();
      o.userData.direction = new THREE.Vector3(0,0,1).applyQuaternion(o.quaternion).normalize();
      people.push(o);
    }
    if (o.userData.web_kind === 'boat') { o.userData.basePosition = o.position.clone(); o.userData.baseQuaternion = o.quaternion.clone(); boats.push(o); }
    if (o.userData.web_kind === 'willow') { o.userData.baseQuaternion = o.quaternion.clone(); willows.push(o); }
    if (!o.isMesh) return;
    if(o.geometry.attributes.color_1){o.geometry.setAttribute('color',o.geometry.attributes.color_1);o.material.vertexColors=true;}
    o.castShadow = true; o.receiveShadow = true;
    if (o.material.name.includes('皮肤') && o.geometry.attributes.uv) {
      o.material = o.material.clone(); o.material.map = skin; o.material.color.set('#e6d2c0');
    }
    if(o.material.name.includes('眼睛')){o.material.map=eyes;o.material.color.set('#ffffff');}
    if (o.userData.web_kind === 'flag') {
      o.material = o.material.clone(); surfaceMaterial(o.material, {wood,ground,cloth,plaster}, 'flag'); flags.push(o);
    } else if (!materials.has(o.material)) surfaceMaterial(o.material, {wood,ground,cloth,plaster});
    materials.add(o.material);
    if (o.userData.web_kind === 'architecture') { o.matrixAutoUpdate = false; o.updateMatrix(); staticMeshes.push(o); }
  });

  // 人物保留关节层级，在 GPU 端把相同几何合成一次绘制。
  const sourceGroups = new Map();
  model.traverse(o => {
    if (!o.isMesh || o.userData.web_kind === 'architecture' || o.userData.web_kind === 'flag') return;
    const key = o.geometry.uuid + o.material.uuid;
    if (!sourceGroups.has(key)) sourceGroups.set(key, []);
    sourceGroups.get(key).push(o);
  });
  const batches = [];
  for (const sources of sourceGroups.values()) {
    const first = sources[0];
    // 面部贴图材质在导出时共用；只出现一次的舟船几何也走同一更新通道。
    const mesh = new THREE.InstancedMesh(first.geometry, first.material, sources.length);
    mesh.name = `合批_${first.name}`; mesh.castShadow = true; mesh.receiveShadow = true;
    mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    mesh.frustumCulled = false;
    scene.add(mesh); batches.push({ mesh, sources });
    for (const source of sources) source.visible = false;
  }
  // 面部相同贴图仍可跨人物合批，清理上一步因独立材质产生的重复批次。
  const faceBatches = batches.filter(b => b.mesh.material.map === skin);
  if (faceBatches.length > 1) {
    const sources = faceBatches.flatMap(b => b.sources);
    const mesh = new THREE.InstancedMesh(sources[0].geometry, sources[0].material, sources.length);
    mesh.name='人物面部合批';mesh.castShadow=true;mesh.receiveShadow=true;mesh.frustumCulled=false;mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    for (const b of faceBatches) { scene.remove(b.mesh);b.mesh.dispose();batches.splice(batches.indexOf(b),1); }
    scene.add(mesh);batches.push({mesh,sources});
  }
  for (const person of people) {
    person.userData.joints = [];
    person.traverse(o => { if (['arm','leg'].includes(o.userData.web_kind)) { o.userData.baseQuaternion=o.quaternion.clone(); person.userData.joints.push(o); } });
  }

  const sky = new Sky(); sky.scale.setScalar(1800); scene.add(sky);
  const skyU = sky.material.uniforms;
  skyU.turbidity.value = 5.2; skyU.rayleigh.value = 1.3; skyU.mieCoefficient.value = .008; skyU.mieDirectionalG.value = .86;
  const sun = new THREE.DirectionalLight('#ffdbad', 3.3);
  sun.position.set(-45,75,65); sun.castShadow=true;
  sun.shadow.mapSize.set(4096,4096);sun.shadow.camera.left=-85;sun.shadow.camera.right=85;
  sun.shadow.camera.top=95;sun.shadow.camera.bottom=-95;sun.shadow.camera.near=1;sun.shadow.camera.far=300;
  sun.shadow.normalBias=.045;sun.shadow.bias=-.00009;sun.shadow.radius=2;
  sun.shadow.autoUpdate=false;sun.shadow.needsUpdate=true;
  scene.add(sun,sun.target);
  const hemi = new THREE.HemisphereLight('#d4e1e4','#625545',1.8);scene.add(hemi);
  const fill = new THREE.DirectionalLight('#c9dedc', .65);fill.position.set(45,35,-40);scene.add(fill);
  scene.fog = new THREE.FogExp2('#becabe',.0035);
  const pmrem = new THREE.PMREMGenerator(renderer);
  const envScene = new THREE.Scene();
  const envSky = sky.clone();envScene.add(envSky);

  const water = new Water(new THREE.PlaneGeometry(200,1200,1,1), {
    textureWidth:768, textureHeight:768, waterNormals:waterNormal,
    sunDirection:sun.position.clone().normalize(),sunColor:'#ffe7bb',waterColor:'#416f68',
    distortionScale:.8, fog:true, alpha:1,
  });
  water.rotation.x=-Math.PI/2;water.position.y=.08;
  water.material.uniforms.size.value=18;
  water.material.fragmentShader=water.material.fragmentShader.replace('noise.xzy * vec3( 1.5, 1.0, 1.5 )','noise.xzy * vec3( 0.6, 1.0, 0.6 )');
  scene.add(water);
  const originalWaterRender = water.onBeforeRender;
  let renderFrame=0;
  water.material.uniforms.uReflection={value:1};
  water.material.fragmentShader='uniform float uReflection;\n'+water.material.fragmentShader;
  water.material.fragmentShader=water.material.fragmentShader.replace('float theta = max(', 'reflectionSample=mix(waterColor+vec3(.12),reflectionSample,uReflection);\n float theta = max(');
  water.onBeforeRender=function(...args){if(args[1].overrideMaterial)return;if(quality==='low')water.material.uniforms.eye.value.copy(args[2].position);else if(renderFrame%3===0||renderFrame<3)originalWaterRender.apply(this,args);};

  // 广阔地景消除模型边缘，低对比远树形成真实的空气透视。
  const earthSource=staticMeshes.find(m=>m.material.name.includes('泥土'));
  for(const mesh of staticMeshes)if(mesh.material.name.includes('泥土'))mesh.visible=false;
  const landMaterial=surfaceMaterial(new THREE.MeshStandardMaterial({name:'泥土_连续地景',color:'#a39a7e',roughness:1}),{wood,ground,cloth,plaster});
  landMaterial.vertexColors=true;
  const riverCenter=y=>2.8*Math.sin(y*.025)+.016*Math.max(0,-y-25)**1.3;
  for(const side of [-1,1]){
    const pos=[],color=[],indices=[],rows=240,cols=45;
    for(let j=0;j<=rows;j++){
      const by=-360+j*3,bank=riverCenter(by)+side*(15.35+.4*Math.sin(by*.075));
      for(let i=0;i<=cols;i++){
        const distance=i<12?i*1.5:18+(i-12)**1.6*1.1,x=bank+side*distance;
        const ripple=(Math.sin(x*.12)*Math.cos(by*.08)*.026)*(1-Math.exp(-distance*.1));
        const hill=(Math.sin(x*.025+1)*2+Math.cos(by*.014)*1.8)*THREE.MathUtils.smoothstep(distance,57,120);
        pos.push(x,1.62+ripple+hill,-by);
        const street=Math.exp(-(((distance-5)/3)**2)),yard=distance<58?.07:Math.sin(x*.055)*Math.sin(by*.065)*.10;
        color.push(.92+street*.08-yard,.91+street*.06,.78+street*.11-yard);
      }
    }
    for(let j=0;j<rows;j++)for(let i=0;i<cols;i++){const a=j*(cols+1)+i;indices.push(a,a+1,a+cols+1,a+1,a+cols+2,a+cols+1);}
    const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));geo.setAttribute('color',new THREE.Float32BufferAttribute(color,3));geo.setIndex(indices);geo.computeVertexNormals();
    const land=new THREE.Mesh(geo,landMaterial);land.receiveShadow=true;scene.add(land);
  }
  const random=seeded(1729);
  // 远景坊巷用共享几何延续城市轮廓，近景仍由独立细节模型承担。
  const distantPlots=[];
  for(const side of [-1,1])for(let column=0;column<4;column++)for(let row=0;row<24;row++){
    const by=-135+row*12+random()*3;
    if(side<0&&by>33&&by<59)continue;
    distantPlots.push({x:side*(73+column*13+random()*2),z:-by,w:6+random()*3,d:5+random()*3,h:3+random()*2,a:(random()-.5)*.24+(random()<.18?Math.PI/2:0)});
  }
  const farWalls=new THREE.InstancedMesh(new THREE.BoxGeometry(1,1,1),new THREE.MeshStandardMaterial({color:'#a79e86',roughness:1,envMapIntensity:.04}),distantPlots.length);
  const farRoofGeometry=new THREE.BufferGeometry();
  farRoofGeometry.setAttribute('position',new THREE.Float32BufferAttribute([-.5,0,-.5,.5,0,-.5,.5,.24,0,-.5,.24,0,-.5,0,.5,.5,0,.5],3));
  farRoofGeometry.setIndex([0,3,2,0,2,1,3,4,5,3,5,2,0,4,3,1,2,5]);farRoofGeometry.computeVertexNormals();
  const farRoofs=new THREE.InstancedMesh(farRoofGeometry,new THREE.MeshStandardMaterial({color:'#40514e',roughness:.88,side:THREE.DoubleSide,envMapIntensity:.08}),distantPlots.length);
  const farBeams=new THREE.InstancedMesh(new THREE.BoxGeometry(1,1,1),new THREE.MeshStandardMaterial({color:'#625543',roughness:1,envMapIntensity:.03}),distantPlots.length);
  distantPlots.forEach((p,i)=>{
    const dist=Math.abs(p.x)-15.3,elev=1.62+(Math.sin(p.x*.025+1)*2+Math.cos(p.z*.014)*1.8)*THREE.MathUtils.smoothstep(dist,57,120);
    temp.position.set(p.x,elev+p.h/2,p.z);temp.rotation.set(0,p.a,0);temp.scale.set(p.w,p.h,p.d);temp.updateMatrix();farWalls.setMatrixAt(i,temp.matrix);
    temp.position.y=elev+p.h;temp.scale.set(p.w+1.1,5.7,p.d+1.2);temp.updateMatrix();farRoofs.setMatrixAt(i,temp.matrix);
    temp.position.y=elev+p.h-.23;temp.scale.set(p.w+.12,.24,p.d+.12);temp.updateMatrix();farBeams.setMatrixAt(i,temp.matrix);
  });
  farWalls.receiveShadow=true;farRoofs.castShadow=true;scene.add(farWalls,farRoofs,farBeams);
  const branches=[];
  function branch(a,b,r){branches.push({a:a.clone(),b:b.clone(),r});}
  for(let i=0;i<95;i++){
    const side=random()<.5?-1:1,x=side*(137+random()*95),z=-160+random()*410,h=6+random()*7;
    const base=new THREE.Vector3(x,1.7,z),top=base.clone().add(new THREE.Vector3((random()-.5)*1.2,h,0));branch(base,top,.25);
    for(let j=0;j<6;j++){
      const a=j*2.4+i,root=base.clone().lerp(top,.43+random()*.4),tip=root.clone().add(new THREE.Vector3(Math.cos(a)*(2+random()*2),2+random()*2,Math.sin(a)*(2+random()*2)));
      branch(root,tip,.095);
      for(let k=0;k<4;k++){
        const p=root.clone().lerp(tip,.35+k*.18),end=p.clone().add(new THREE.Vector3(Math.cos(a+k*.9)*(1+random()),1+random()*1.8,Math.sin(a+k*.9)*(1+random())));branch(p,end,.028);
        for(let q=0;q<2;q++){const twig=end.clone().add(new THREE.Vector3((random()-.5)*1.2,.6+random()*.7,(random()-.5)*1.2));branch(end,twig,.008);}
      }
    }
  }
  const distantWood=new THREE.InstancedMesh(new THREE.CylinderGeometry(.35,1,1,5),new THREE.MeshStandardMaterial({color:'#655e47',roughness:1,envMapIntensity:.01}),branches.length);
  const up=new THREE.Vector3(0,1,0),delta=new THREE.Vector3();
  branches.forEach((b,i)=>{delta.subVectors(b.b,b.a);temp.position.copy(b.a).add(b.b).multiplyScalar(.5);temp.quaternion.setFromUnitVectors(up,delta.clone().normalize());temp.scale.set(b.r,delta.length(),b.r);temp.updateMatrix();distantWood.setMatrixAt(i,temp.matrix);});scene.add(distantWood);
  // 轻烟使用软粒子。不会写入深度，避免出现不透明球体。
  const smokeCanvas=document.createElement('canvas');smokeCanvas.width=smokeCanvas.height=128;
  const sc=smokeCanvas.getContext('2d'),gradient=sc.createRadialGradient(64,64,0,64,64,64);
  gradient.addColorStop(0,'rgba(220,224,211,0.20)');gradient.addColorStop(.4,'rgba(220,224,211,0.10)');gradient.addColorStop(1,'rgba(220,224,211,0)');sc.fillStyle=gradient;sc.fillRect(0,0,128,128);
  const smokeMap=new THREE.CanvasTexture(smokeCanvas),smoke=[];
  for (const [x,y] of [[-26,-12],[28,28],[-28,39],[26,-41]]) for(let i=0;i<9;i++) {
    const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:smokeMap,transparent:true,depthWrite:false,color:'#efdfc2',opacity:.65}));
    sprite.userData={x,y,phase:i/9};sprite.scale.set(3,5,1);scene.add(sprite);smoke.push(sprite);
  }
  const birdGeo=new THREE.BufferGeometry();
  birdGeo.setAttribute('position',new THREE.Float32BufferAttribute([-1,0,0,0,.16,.15,1,0,0,-1,0,0,0,0,0,1,0,0],3));
  const birds=new THREE.InstancedMesh(birdGeo,new THREE.MeshBasicMaterial({color:'#414941',side:THREE.DoubleSide}),18);birds.frustumCulled=false;scene.add(birds);

  let envTexture, quality='high';
  function setLight(mode) {
    const options={day:{sun:'#fff1d5',power:3.2,hemi:1.25,elev:40,fog:'#bfcec8',density:.0032,exp:1.05},golden:{sun:'#ffdda6',power:3.4,hemi:.72,elev:25,fog:'#c3cabb',density:.0025,exp:.95},sunset:{sun:'#ffb472',power:3.4,hemi:.90,elev:11,fog:'#a6aaa2',density:.0041,exp:.97}}[mode];
    sun.color.set(options.sun);sun.intensity=options.power;hemi.intensity=options.hemi;
    const direction=new THREE.Vector3().setFromSphericalCoords(1,THREE.MathUtils.degToRad(90-options.elev),THREE.MathUtils.degToRad(-48));
    sun.position.copy(direction).multiplyScalar(140);
    sun.shadow.needsUpdate=true;
    skyU.sunPosition.value.copy(direction);water.material.uniforms.sunDirection.value.copy(direction);water.material.uniforms.sunColor.value.set(options.sun);
    scene.fog.color.set(options.fog);scene.fog.density=options.density;renderer.toneMappingExposure=options.exp;
    if(envTexture)envTexture.dispose();
    envTexture=pmrem.fromScene(envScene,.02,.1,2000);scene.environment=envTexture.texture;scene.environmentIntensity=.13;
  }
  setLight('golden');

  function update(time, motion=true) {
    renderFrame++;
    if(renderFrame%12===0)sun.shadow.needsUpdate=true;
    clockUniform.value=time;
    water.material.uniforms.time.value=time*.16;
    for(const [i,p] of people.entries()) {
      const d=p.userData,phase=time*5.2+d.web_phase;
      if(d.web_walk) {
        const speed=d.web_bridge?.33:.47;
        const travel=(time*speed)% (d.web_bridge?56:130);
        p.position.copy(d.basePosition).addScaledVector(d.direction,travel);
        if(d.web_bridge) {
          p.position.x=THREE.MathUtils.euclideanModulo(p.position.x+28,56)-28;
          p.position.y=1.805+4.95*Math.max(0,1-(p.position.x/15.3)**2);
        } else { p.position.z=THREE.MathUtils.euclideanModulo(p.position.z+68,136)-68;p.position.x=d.basePosition.x-riverCenter(-d.basePosition.z)+riverCenter(-p.position.z);p.position.y=1.635; }
      }
      for(const joint of d.joints) {
        const j=joint.userData;
        joint.quaternion.copy(j.baseQuaternion);
        const angle = d.web_walk ? Math.sin(phase)*j.web_side*(j.web_kind==='arm'?.23:-.25) : .06*Math.sin(time*1.6+d.web_phase+j.web_side);
        joint.rotateX(angle);
      }
    }
    for(const [i,b] of boats.entries()) {
      const d=b.userData,dir=new THREE.Vector3(0,0,1).applyQuaternion(d.baseQuaternion);
      b.position.copy(d.basePosition).addScaledVector(dir,Math.sin(time/90)*90*d.web_speed);
      b.position.x=d.basePosition.x-riverCenter(-d.basePosition.z)+riverCenter(-b.position.z);
      b.position.y=.018*Math.sin(time*1.5+i);
      b.quaternion.copy(d.baseQuaternion);b.rotateX(.006*Math.sin(time*1.2+i));b.rotateZ(.007*Math.sin(time*1.4+i));
    }
    for(const [i,w] of willows.entries()){w.quaternion.copy(w.userData.baseQuaternion);w.rotateZ(.011*Math.sin(time*.65+i));}
    for(const sprite of smoke){const d=sprite.userData,t=(time*.04+d.phase)%1;sprite.position.copy(toWorld(d.x+t*4,d.y+t,7+t*11));sprite.scale.set(1.6+t*4,3+t*5,1);sprite.material.opacity=Math.sin(t*Math.PI)*.44;}
    for(let i=0;i<18;i++){const a=time*.021+i*2.4;temp.position.set(Math.cos(a)*45,22+Math.sin(i*9)*4,Math.sin(a)*65-20);temp.rotation.set(0,-a,Math.sin(time*5+i)*.18);temp.scale.set( .6, .7+Math.sin(time*7+i)*.4,.65);temp.updateMatrix();birds.setMatrixAt(i,temp.matrix);}birds.instanceMatrix.needsUpdate=true;
    model.updateMatrixWorld(true);
    for(const {mesh,sources} of batches){sources.forEach((s,i)=>mesh.setMatrixAt(i,s.matrixWorld));mesh.instanceMatrix.needsUpdate=true;}
  }
  update(0);
  draco.dispose();
  return {
    model, water, sun, materials, people, boats, staticMeshes, batches,
    update, setLight,
    setWireframe(enabled){for(const m of materials){m.wireframe=enabled;m.needsUpdate=true;}water.visible=!enabled;},
    setQuality(value){quality=value;sun.castShadow=value!=='low';sun.shadow.needsUpdate=true;water.material.uniforms.uReflection.value=value==='low'?0:1;},
    getStats(){return {people:people.length,boats:boats.length,batches:batches.length,staticBatches:staticMeshes.length};},
  };
}
