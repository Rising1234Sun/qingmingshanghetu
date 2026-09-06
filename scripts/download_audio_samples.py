"""从固定版本的 VSCO 2 CE 仓库恢复选定采样；校验成功后才写入最终文件。"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import sys
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def matches(file, entry):
    if not file.is_file() or file.stat().st_size != entry['bytes']:
        return False
    with file.open('rb') as handle:
        digest = hashlib.sha256()
        while block := handle.read(1024*1024):
            digest.update(block)
        return digest.hexdigest() == entry['sha256']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='只检查本地文件，不联网')
    parser.add_argument('--limit', type=int, help='只处理清单前 N 个文件')
    parser.add_argument('--output', type=Path, default=ROOT/'assets/audio/vsco', help='采样存放目录')
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error('--limit 必须大于零')
    manifest = json.loads((ROOT/'assets/audio/vsco-downloads.json').read_text())
    entries = manifest['files'][:args.limit]
    base = f"https://raw.githubusercontent.com/sgossner/VSCO-2-CE/{manifest['revision']}/"
    missing = []
    for index, entry in enumerate(entries, 1):
        relative = PurePosixPath(entry['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('清单包含非法路径')
        target = args.output.joinpath(*relative.parts)
        if matches(target, entry):
            continue
        if args.check:
            missing.append(entry['path'])
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + '.part')
        url = base + urllib.parse.quote(entry['path'], safe='/')
        try:
            request = urllib.request.Request(url, headers={'User-Agent':'Bianjing-asset-rebuild/1.0'})
            with urllib.request.urlopen(request, timeout=30) as response, temporary.open('wb') as handle:
                while block := response.read(1024*1024):
                    handle.write(block)
            if not matches(temporary, entry):
                raise RuntimeError(f"下载校验失败：{entry['path']}")
            temporary.replace(target)
            print(f"[{index}/{len(entries)}] 已恢复 {entry['path']}", flush=True)
        finally:
            temporary.unlink(missing_ok=True)
    if missing:
        print(f'缺失或校验不一致：{len(missing)}/{len(entries)} 个采样。')
        for name in missing[:8]:
            print('  ' + name)
        print('去掉 --check 运行以恢复文件。')
        return 1
    print(f'采样校验通过：{len(entries)} 个文件。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
