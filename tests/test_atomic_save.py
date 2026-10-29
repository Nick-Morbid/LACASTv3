import json
from pathlib import Path
from unittest.mock import patch

import pytest

from lacastv3.training import save


def test_save_retries_transient_permission_error(tmp_path):
    target = tmp_path / 'progress.json'
    target.write_text('{"checked": 1}')
    replace = Path.replace
    calls = []

    def transient(source, destination):
        calls.append(source)
        if len(calls) < 3:
            assert json.loads(target.read_text()) == {'checked': 1}
            raise PermissionError('reader holds destination')
        return replace(source, destination)

    with patch.object(Path, 'replace', transient), patch('lacastv3.training.time.sleep'):
        save(target, {'checked': 2})
    assert len(calls) == 3
    assert json.loads(target.read_text()) == {'checked': 2}


def test_save_preserves_checkpoint_when_access_remains_denied(tmp_path):
    target = tmp_path / 'progress.json'
    target.write_text('{"checked": 1}')
    with patch.object(Path, 'replace', side_effect=PermissionError('denied')), patch('lacastv3.training.time.sleep'):
        with pytest.raises(PermissionError):
            save(target, {'checked': 2})
    assert json.loads(target.read_text()) == {'checked': 1}
