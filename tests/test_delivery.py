import hashlib
import pytest
import subprocess
import sys

from lacastv3.delivery import check_evaluation, copy_runtime_assets


def evidence():
    rules = b'[{"id":"one"}]'
    digest = hashlib.sha256(rules).hexdigest()
    manifest = {'rules_sha256': digest, 'generation_profile': 'expanded',
                'database': 'lacastv3_test', 'server_version': '8.4.11', 'count': 10000}
    validation = {'full_snapshot_verified': True, 'status': 'completed',
                  'results': [{'rule_id': 'one', 'passed': True}]}
    fuzz = {'status': 'completed', 'requested': 10000, 'executed': 10000}
    return rules, manifest.copy(), validation, manifest.copy(), fuzz


def test_matching_complete_evidence_passes_gate():
    args = evidence()
    assert check_evaluation(*args) == hashlib.sha256(args[0]).hexdigest()


@pytest.mark.parametrize('index,field,value', [
    (1, 'rules_sha256', 'another snapshot'),
    (3, 'generation_profile', 'baseline'),
    (2, 'full_snapshot_verified', False),
    (2, 'results', []),
    (4, 'executed', 9999),
    (3, 'server_version', '5.7'),
])
def test_partial_or_mismatched_evidence_cannot_export(index, field, value):
    args = evidence()
    args[index][field] = value
    with pytest.raises(ValueError):
        check_evaluation(*args)


def test_deployment_assets_boot_without_original_worktree(tmp_path):
    copy_runtime_assets(tmp_path)
    for name in ('.env.example', 'DEPLOYMENT.md', 'prompts/rules.txt', 'scripts/bootstrap.py',
                 'scripts/preflight_mysql.py', 'configs/mysql/schema.sql', 'docs/architecture.md'):
        assert (tmp_path / name).is_file()
    assert not (tmp_path / '.env').exists()
    assert not (tmp_path / 'configs/mysql/local.yaml').exists()
    result = subprocess.run([sys.executable, '-m', 'lacastv3', '--help'],
                            cwd=tmp_path, check=True, capture_output=True, text=True)
    assert 'revalidate' in result.stdout
