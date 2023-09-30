import inspect
import os
import traceback

from bot.cogs.lib import logger, loglevel, settings
# from bot.cogs.lib.enums import loglevel


class MigrationRunner:
    def __init__(self) -> None:
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        self.settings = settings.Settings()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        self.log = logger.Log(minimumLogLevel=log_level)

        # get migrations from migrations folder
        self._migrations = []
        for file in os.listdir(os.path.join(os.getcwd(), "bot", "cogs", "lib", "migrations")):
            if file.endswith("_migration.py"):
                self.log.debug(0, f"{self._module}.{self._class}.__init__", f"Found migration {file[:-3]}")
                self._migrations.append({"id": int(file[:-3].split("_")[0]), "name": file[:-3]})

        # sort migrations by id
        self._migrations.sort(key=lambda x: x["id"])

    # load migrations and run them if they haven't been run yet
    def start_migrations(self) -> None:
        _method = inspect.stack()[0][3]
        for migration in self._migrations:
            try:
                module = __import__(f"bot.cogs.lib.migrations.{migration['name']}", fromlist=["Migration"])
                migration_class = getattr(module, "Migration")
                migration_instance = migration_class()
                if migration_instance.needs_run():
                    self.log.debug(
                        0, f"{self._module}.{self._class}.start_migrations", f"Running migration {migration}"
                    )
                    migration_instance.run()
                else:
                    self.log.debug(
                        0, f"{self._module}.{self._class}.start_migrations", f"Migration {migration} has already been run"
                    )
            except Exception as ex:
                self.log.error(
                    0,
                    f"{self._module}.{self._class}.{_method}",
                    f"Failed to run migration {migration}: {ex}",
                    stackTrace=traceback.format_exc(),
                )
                break
