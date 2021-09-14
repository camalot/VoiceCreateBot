from os.path import dirname, basename, isfile, join
import glob
import json
migration_files = glob.glob(join(dirname(__file__),"*.py"))


__all__ = [ basename(f)[:-3] for f in migration_files if isfile(f) and not f.endswith('__init__.py')]

print(json.dumps(__all__))