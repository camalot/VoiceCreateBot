import inspect
from os.path import dirname, basename, isfile, join
import glob
import typing
migration_files = glob.glob(join(dirname(__file__),"*.py"))
migration_files.sort(key=lambda x: str(filter(str.isdigit, x[:-3])), reverse=True)

__all__ = [basename(f)[:-3] for f in migration_files if isfile(f) and not f.endswith('__init__.py')]
class Migration():
    def __init__(self, connection):
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        self.connection = connection
        self._module = basename(__file__)[:-3]
        self.log(f"{self._module}.{self._class}.{_method}", f"INITIALIZE MIGRATION {self._module}")
        pass

    def log(self, method: str, message: str, stackTrace: typing.Optional[str] = None):
        print(f"[DEBUG] [{method}] [guild:0] {message}")
        if stackTrace:
            print(stackTrace)
