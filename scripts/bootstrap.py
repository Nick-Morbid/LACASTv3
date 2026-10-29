"""Download the pinned ANTLR tool (Python runtime is installed through uv)."""
import hashlib
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'vendor/antlr-4.13.2-complete.jar'
SHA256 = 'eae2dfa119a64327444672aff63e9ec35a20180dc5b8090b7a6ab85125df4d76'
TARGET.parent.mkdir(parents=True, exist_ok=True)
if not TARGET.exists():
    urllib.request.urlretrieve('https://www.antlr.org/download/antlr-4.13.2-complete.jar', TARGET)
if hashlib.sha256(TARGET.read_bytes()).hexdigest() != SHA256:
    raise RuntimeError(f'ANTLR tool checksum mismatch: {TARGET}')
print('ANTLR 4.13.2 tool checksum verified')
