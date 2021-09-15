from inspect import stack
from os.path import dirname, basename, isfile, join
import glob
import json
import traceback
migration_files = glob.glob(join(dirname(__file__),"*.py"))

migration_files.sort(key=lambda x: str(filter(str.isdigit, x[:-3])), reverse=True)

__all__ = [ basename(f)[:-3] for f in migration_files if isfile(f) and not f.endswith('__init__.py')]
class Migration():
    def log(self, method: str, message: str, stackTrace: str = None):
        print(f"[DEBUG] [{method}] [guild:0] {message}")
        if stackTrace:
            print(stackTrace)
