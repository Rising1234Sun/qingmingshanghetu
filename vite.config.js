import {defineConfig} from 'vite';
export default defineConfig({
  base: process.env.VITE_BASE_PATH || './',
  server:{host:'127.0.0.1',port:5187,strictPort:true},
  build:{rollupOptions:{output:{manualChunks:{three:['three'],addons:['three/addons/loaders/GLTFLoader.js','three/addons/loaders/DRACOLoader.js','three/addons/controls/OrbitControls.js']}}}},
});
