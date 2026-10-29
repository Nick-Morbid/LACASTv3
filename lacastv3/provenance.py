"""Retain the runtime and public input files used by an evaluation."""
import hashlib
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


def capture_runtime(root: Path, output: Path):
    paths = [root / name for name in ('pyproject.toml', 'uv.lock')]
    paths += list((root / 'lacastv3').glob('*.py'))
    paths += [root / 'configs/mysql' / name for name in
              ('MySQLBase.g4', 'schema.json', 'schema.sql', 'semantics.json', 'web_corpus.json')]
    archive = output / 'runtime-source.zip'
    hashes = {}
    with ZipFile(archive, 'x', compression=ZIP_DEFLATED) as stream:
        for path in sorted(paths):
            content = path.read_bytes()
            relative = path.relative_to(root).as_posix()
            stream.writestr(relative, content)
            hashes[relative] = hashlib.sha256(content).hexdigest()
    return {'archive': archive.name, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
            'files': hashes}
