// 检查新克隆能否取得完整资产，以及静态构建后的引用是否仍能解析。
import assert from 'node:assert/strict';
import {readFileSync, readdirSync, existsSync, statSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
const option = name => args.includes(name) ? args[args.indexOf(name) + 1] : null;
const filesIn = dir => readdirSync(dir, {withFileTypes:true}).flatMap(entry =>
  entry.isDirectory() ? filesIn(path.join(dir, entry.name)) : [path.join(dir, entry.name)]);
const hash = file => createHash('sha256').update(readFileSync(file)).digest('hex');
const publicDir = path.join(root, 'public');
const required = ['models/bianjing.glb', 'models/manifest.json', 'draco/draco_decoder.wasm',
  'draco/draco_wasm_wrapper.js', 'draco/LICENSE', 'fonts/song.woff2', 'fonts/OFL.txt',
  'audio/bianjing.mp3', 'reference/scroll.jpg', 'reference/bridge.jpg',
  ...['wood.jpg','ground.jpg','skin.jpg','eyes.png','cloth.jpg','plaster.jpg','water-normal.png'].map(s=>'textures/'+s)];
for (const relative of required) {
  const file = path.join(publicDir, relative);
  assert(existsSync(file) && statSync(file).size > 0, `缺少运行资产：${relative}`);
}

const glb = readFileSync(path.join(publicDir, 'models/bianjing.glb'));
assert.equal(glb.toString('ascii', 0, 4), 'glTF', '模型不是有效 GLB，可能下载成了指针文件');
assert.equal(glb.readUInt32LE(4), 2, '需要 glTF 2');
assert.equal(glb.readUInt32LE(8), glb.length, '模型可能被截断');
assert.equal(glb.toString('ascii', 16, 20), 'JSON');
const model = JSON.parse(glb.toString('utf8', 20, 20 + glb.readUInt32LE(12)));
assert(model.meshes?.length > 0, '模型缺少三维网格');
const people = model.nodes.filter(n => n.extras?.web_kind === 'person').length;
const boats = model.nodes.filter(n => n.extras?.web_kind === 'boat').length;
assert(people > 0 && boats > 0, '模型缺少网页人物或船只动画标签');
const manifest = JSON.parse(readFileSync(path.join(publicDir, 'models/manifest.json')));
assert.equal(manifest.glb_bytes, glb.length, '模型清单大小与实际文件不一致');
console.log(`运行资产通过：GLB ${(glb.length/1048576).toFixed(2)} MiB，${people} 人，${boats} 船。`);

const docs = [path.join(root, 'README.md'), ...filesIn(path.join(root, 'docs')).filter(f=>f.endsWith('.md'))];
for (const file of docs) {
  for (const [, link] of readFileSync(file, 'utf8').matchAll(/\]\(([^\s)]+)\)/g)) {
    if (/^(?:[a-z]+:|#|\/\/)/i.test(link)) continue;
    const relative = decodeURIComponent(link.split('#')[0]);
    assert(existsSync(path.resolve(path.dirname(file), relative)), `文档链接不存在：${path.relative(root,file)} → ${link}`);
  }
}
console.log(`文档链接通过：${docs.length} 个文档。`);

if (args.includes('--dist')) {
  assert(option('--dist'), '--dist 后需要构建目录');
  const dist = path.resolve(root, option('--dist'));
  assert(existsSync(path.join(dist, 'index.html')), '构建目录缺少 index.html');
  for (const file of filesIn(publicDir)) {
    const relative = path.relative(publicDir, file), target = path.join(dist, relative);
    assert(existsSync(target), `构建缺少资产：${relative}`);
    assert.equal(hash(file), hash(target), `构建资产与源文件不同：${relative}`);
  }
  const base = option('--base') || '/';
  assert(base.startsWith('/') && base.endsWith('/'), '--base 需要以 / 开头和结束');
  for (const file of filesIn(dist).filter(f=>/\.(html|css)$/.test(f))) {
    const relative = path.relative(dist,file).split(path.sep).join('/');
    const documentUrl = new URL(base + relative, 'https://static-check.invalid');
    const source = readFileSync(file, 'utf8');
    const references = file.endsWith('.html') ? [...source.matchAll(/(?:src|href)="([^"]+)"/g)].map(m=>m[1])
      : [...source.matchAll(/url\((?:["']?)([^)'"\s]+)(?:["']?)\)/g)].map(m=>m[1]);
    for (const ref of references) {
      if (/^(?:[a-z]+:|#|\/\/)/i.test(ref)) continue;
      const url = new URL(ref, documentUrl);
      assert(url.pathname.startsWith(base), `资源逃出了部署子目录：${ref}`);
      const target = path.join(dist, decodeURIComponent(url.pathname.slice(base.length)));
      assert(existsSync(target), `构建引用不存在：${relative} → ${ref}`);
    }
  }
  console.log(`构建资产与引用通过：${path.relative(root,dist)}，部署前缀 ${base}。`);
}
