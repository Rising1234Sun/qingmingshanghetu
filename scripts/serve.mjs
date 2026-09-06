// 仅在本机提供成品网页，并将网页拍摄成果保存到当前项目。
import http from 'node:http';
import {createReadStream,createWriteStream,existsSync,mkdirSync,statSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {pipeline} from 'node:stream/promises';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const publicRoot=path.join(root,'dist');
const output=path.join(root,'output','web');mkdirSync(output,{recursive:true});
const port=Number(process.env.BIANJING_PORT||5186);
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json','.wasm':'application/wasm','.glb':'model/gltf-binary','.jpg':'image/jpeg','.png':'image/png','.svg':'image/svg+xml','.woff2':'font/woff2','.mp3':'audio/mpeg','.mp4':'video/mp4','.webm':'video/webm'};
http.createServer(async(req,res)=>{
  try{
    const url=new URL(req.url,`http://127.0.0.1:${port}`);
    if(req.method==='POST'&&url.pathname==='/__export'){
      if(req.headers.origin!==`http://127.0.0.1:${port}`){res.writeHead(403);res.end('仅接受本机作品页面');return;}
      const type=(req.headers['content-type']||'').split(';')[0];
      const ext={'video/mp4':'.mp4','video/webm':'.webm','image/png':'.png','application/json':'.json'}[type];
      if(!ext){res.writeHead(415);res.end('不支持的媒体格式');return;}
      const filename=`入画汴京_网页实录_${new Date().toISOString().replaceAll(':','-').replaceAll('.','-')}${ext}`;
      await pipeline(req,createWriteStream(path.join(output,filename)));
      res.writeHead(200,{'Content-Type':'application/json; charset=utf-8'});res.end(JSON.stringify({path:path.join(output,filename),filename}));return;
    }
    if(req.method!=='GET'&&req.method!=='HEAD'){res.writeHead(405);res.end();return;}
    const relative=decodeURIComponent(url.pathname==='/'?'/index.html':url.pathname);
    const file=path.resolve(publicRoot,'.'+relative);
    if(!file.startsWith(publicRoot+path.sep)||!existsSync(file)||!statSync(file).isFile()){res.writeHead(404);res.end('文件不存在');return;}
    const size=statSync(file).size;res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream','Content-Length':size,'Cache-Control':'no-cache'});
    if(req.method==='HEAD')res.end();else createReadStream(file).pipe(res);
  }catch(error){if(!res.headersSent)res.writeHead(500);res.end('本地服务错误');console.error(error);}
}).listen(port,'127.0.0.1',()=>console.log(`入画·汴京 已打开本地服务：http://127.0.0.1:${port}/\n拍摄成果保存在 ${output}`));
