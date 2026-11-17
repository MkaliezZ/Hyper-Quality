import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import package as publisher
import verify_public_source as boundary


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        subprocess.run(['git','init','-q'],cwd=self.root,check=True)
        subprocess.run(['git','config','user.name','Synthetic Test'],cwd=self.root,check=True)
        subprocess.run(['git','config','user.email','synthetic@example.invalid'],cwd=self.root,check=True)
        required=['README.md','README.zh-CN.md','CONTRIBUTING.md','CONTRIBUTING.zh-CN.md','LICENSE',
                  'LICENSE-NOTE.md','LICENSE-NOTE.zh-CN.md','THIRD_PARTY_NOTICES.md',
                  'vendor/hyper-protocol/LICENSE','vendor/hyper-protocol/LICENSES/CC-BY-4.0.txt']
        for name in required:
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('Synthetic publication fixture.\n',encoding='utf-8')
        (self.root/'PUBLICATION.json').write_text(json.dumps(dict(allowed_root_files=[p for p in required if '/' not in p]+['PUBLICATION.json'],allowed_roots=['vendor'])),encoding='utf-8')
        self.git('add','.')
        self.git('commit','-qm','Synthetic public tree')

    def tearDown(self):
        self.tmp.cleanup()

    def git(self,*args):
        subprocess.run(['git',*args],cwd=self.root,check=True,capture_output=True)

    def test_private_directory_cannot_be_force_added(self):
        path=self.root/'evidence/private.txt';path.parent.mkdir();path.write_text('SYNTHETIC_PRIVATE_SENTINEL',encoding='utf-8')
        self.git('add',str(path))
        self.assertFalse(boundary.check(self.root)['valid'])

    def test_credential_payload_is_rejected_without_echoing_value(self):
        value='gh'+'p_'+'a'*36
        (self.root/'README.md').write_text(value,encoding='utf-8')
        result=boundary.check(self.root)
        self.assertFalse(result['valid'])
        self.assertNotIn(value,json.dumps(result))

    def test_untracked_runtime_not_in_archive(self):
        path=self.root/'runtime/private.txt';path.parent.mkdir();path.write_text('SYNTHETIC_PRIVATE_SENTINEL',encoding='utf-8')
        target=self.root/'dist/public.zip'
        with patch.object(publisher,'ROOT',self.root),patch.object(publisher,'check',lambda:boundary.check(self.root)),patch.object(publisher,'tracked_files',lambda:boundary.tracked_files(self.root)),contextlib.redirect_stdout(io.StringIO()):
            publisher.package(target)
        with zipfile.ZipFile(target) as archive:
            self.assertFalse(any('runtime/' in n for n in archive.namelist()))
            self.assertTrue(all(b'SYNTHETIC_PRIVATE_SENTINEL' not in archive.read(n) for n in archive.namelist()))

    def test_dirty_tracked_content_cannot_be_packaged(self):
        (self.root/'README.md').write_text('Unreviewed changes',encoding='utf-8')
        with patch.object(publisher,'ROOT',self.root),patch.object(publisher,'check',lambda:boundary.check(self.root)):
            with self.assertRaises(subprocess.CalledProcessError):
                publisher.package(self.root/'dist/public.zip')


if __name__=='__main__':
    unittest.main()
