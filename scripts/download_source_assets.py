"""按需恢复完整中文字体和原卷参考图；网页运行不需要此步骤。"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def valid(file, entry):
    if not file.is_file() or file.stat().st_size != entry['bytes']:
        return False
    digest = hashlib.sha256()
    with file.open('rb') as handle:
        while block := handle.read(1024*1024):
            digest.update(block)
    return digest.hexdigest() == entry['sha256']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='只检查，不下载')
    parser.add_argument('--only', choices=['font', 'reference'], help='只处理字体或原卷')
    parser.add_argument('--output-root', type=Path, default=ROOT, help='保存到指定根目录')
    args = parser.parse_args()
    entries = json.loads((ROOT/'assets/source-downloads.json').read_text())['files']
    failures = []
    for entry in entries:
        if args.only and (entry['path'].endswith('.otf') != (args.only == 'font')):
            continue
        relative = PurePosixPath(entry['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('清单路径不合法')
        file = args.output_root.joinpath(*relative.parts)
        if valid(file, entry):
            print('校验通过：'+entry['path'])
            continue
        if args.check or file.exists():
            failures.append(entry['path'])
            continue
        file.parent.mkdir(parents=True, exist_ok=True)
        temporary = file.with_suffix(file.suffix+'.part')
        try:
            request = urllib.request.Request(entry['url'], headers={'User-Agent':'Bianjing-source-rebuild/1.0'})
            with urllib.request.urlopen(request, timeout=60) as response, temporary.open('wb') as handle:
                while block := response.read(1024*1024):
                    handle.write(block)
            if not valid(temporary, entry):
                raise RuntimeError('来源文件与原项目校验值不同：'+entry['path'])
            temporary.replace(file)
            print('已恢复：'+entry['path'], flush=True)
        finally:
            temporary.unlink(missing_ok=True)
    if failures:
        print('缺失或校验不一致：'+', '.join(failures))
        print('缺失文件可去掉 --check 下载；已有但不一致的文件保留，请先另存自己的修改。')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
