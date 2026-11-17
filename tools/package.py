"""Package only a clean, reviewed Git tracked tree; never collect runtime outputs."""
import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path
from verify_public_source import ROOT, check, tracked_files


def package(out):
    out=Path(out).resolve()
    if out.exists():
        raise ValueError('Output exists; use a new archive path.')
    validation=check()
    if not validation['valid']:
        raise ValueError(json.dumps(validation,ensure_ascii=False))
    for args in [['git','diff','--quiet'],['git','diff','--cached','--quiet']]:
        subprocess.run(args,cwd=ROOT,check=True)
    commit=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    files=tracked_files()
    blobs={name:(ROOT/name).read_bytes() for name in files}
    manifest={name:hashlib.sha256(content).hexdigest() for name,content in sorted(blobs.items())}
    out.parent.mkdir(parents=True,exist_ok=True)
    prefix='Hyper-Quality/'
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,content in sorted(blobs.items()):
            archive.writestr(prefix+name,content)
        archive.writestr(prefix+'PACKAGE-MANIFEST.json',json.dumps(dict(commit=commit,files=manifest),ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(out) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist())=={prefix+n for n in manifest}|{prefix+'PACKAGE-MANIFEST.json'}
        for name,expected in manifest.items():
            assert hashlib.sha256(archive.read(prefix+name)).hexdigest()==expected,name
    result=dict(archive=out.name,commit=commit,files=len(files),bytes=out.stat().st_size,
                sha256=hashlib.sha256(out.read_bytes()).hexdigest(),crc_and_file_hashes_verified=True,
                scope='Public tracked source only; excludes runtime/private evidence.')
    out.with_suffix('.receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    package(parser.parse_args().out)
