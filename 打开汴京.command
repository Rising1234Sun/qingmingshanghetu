#!/bin/zsh
# 双击启动本机网页；所有资源都保存在项目内。
cd -- "${0:A:h}"
if /usr/bin/curl -fsS http://127.0.0.1:5186/ >/dev/null 2>&1; then
  /usr/bin/open http://127.0.0.1:5186/
  exit 0
fi
BIANJING_NODE="$(command -v node 2>/dev/null)"
if [[ -z "$BIANJING_NODE" ]]; then
  BIANJING_NODES=("$HOME"/.nvm/versions/node/*/bin/node(N))
  BIANJING_NODE="${BIANJING_NODES[-1]}"
fi
if [[ ! -x "$BIANJING_NODE" ]]; then
  print '未找到 Node.js。可安装免费的 Node.js 后重新打开。'
  read 'REPLY?按回车退出'
  exit 1
fi
if [[ ! -f dist/index.html ]]; then
  print '首次使用请在项目目录执行 npm ci 和 npm run build，再双击此文件。'
  read 'REPLY?按回车退出'
  exit 1
fi
"$BIANJING_NODE" scripts/serve.mjs &
BIANJING_PID=$!
trap 'kill "$BIANJING_PID" 2>/dev/null' EXIT
for BIANJING_ATTEMPT in {1..30}; do
  if /usr/bin/curl -fsS http://127.0.0.1:5186/ >/dev/null 2>&1; then break; fi
  sleep 0.1
done
/usr/bin/open http://127.0.0.1:5186/
wait "$BIANJING_PID"
