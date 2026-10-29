import hashlib
from zipfile import ZipFile

from lacastv3.provenance import capture_runtime


def test_runtime_archive_is_allowlisted_and_hashes_exact_bytes(tmp_path):
    root = tmp_path / 'project'
    output = tmp_path / 'output'
    output.mkdir()
    (root / 'lacastv3').mkdir(parents=True)
    (root / 'configs/mysql').mkdir(parents=True)
    names = ['pyproject.toml', 'uv.lock', 'lacastv3/generator.py']
    names += ['configs/mysql/' + name for name in
              ('MySQLBase.g4', 'schema.json', 'schema.sql', 'semantics.json', 'web_corpus.json')]
    for name in names:
        (root / name).write_text('public input', encoding='utf-8')
    (root / '.env').write_text('SECRET=private')
    (root / 'configs/mysql/local.yaml').write_text('password: private')
    manifest = capture_runtime(root, output)
    with ZipFile(output / manifest['archive']) as archive:
        assert set(archive.namelist()) == set(names)
        for name in names:
            assert hashlib.sha256(archive.read(name)).hexdigest() == manifest['files'][name]
