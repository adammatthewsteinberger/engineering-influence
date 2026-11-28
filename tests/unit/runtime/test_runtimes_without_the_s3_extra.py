# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The API and the worker start without the s3 extra: botocore is imported only when the S3 store is chosen.

Checked in a child process that refuses botocore, as an image without the extra would be.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CHECK = """
import sys
class Refuse:
    def find_spec(self, name, path=None, target=None):
        if name == "botocore" or name.startswith("botocore."):
            raise ImportError("botocore is missing")
sys.meta_path.insert(0, Refuse())
import engineering_influence.runtime.api_runtime
import engineering_influence.runtime.worker_runtime
print("ok")
"""


def test_the_runtimes_import_without_botocore() -> None:
    result = subprocess.run(
        [sys.executable, "-c", CHECK], capture_output=True, text=True, cwd=ROOT, check=False
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"
