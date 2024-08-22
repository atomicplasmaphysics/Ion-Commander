from sqlite3 import connect, OperationalError
from time import time
from datetime import datetime, timedelta
from pathlib import Path


from Config.GlobalConf import GlobalConf


class Tables:
    """
    Metadata for tables
    """

    name = ''
    structure = {
        'Time': 'DATETIME default CURRENT_TIMESTAMP',
    }

    def __init__(self):
        self.variables = []

        if not self.name:
            raise ValueError(f'No name defined')
        if not self.structure:
            raise ValueError(f'Table "{self.name}" has no structure')

        for variable, variable_type in self.structure.items():
            if 'DEFAULT' not in variable_type:
                self.variables.append(variable)

    def column_names(self) -> list[str]:
        """Returns the column names"""
        return list(self.structure.keys())

    def create(self) -> str:
        table_string = ''
        for variable, variable_type in self.structure.items():
            table_string += f' {variable} {variable_type},\n'

        return f'''CREATE TABLE {self.name} (\n{table_string[:-2]}\n);'''

    def exists(self) -> str:
        """SQL query if table exists"""
        return f'''SELECT * FROM {self.name} LIMIT 1;'''

    def columns(self) -> str:
        """SQL query for column names"""
        return f'''PRAGMA table_info({self.name})'''

    def alter_add(self, columns: list[str]) -> str:
        """SQL query to alter the table and add given columns"""

        add_structure = dict()
        for column in columns:
            if column not in self.structure.keys():
                raise ValueError(f'Column "{column}" not in structure of table "{self.name}"')
            add_structure[column] = self.structure[column]

        table_string = ''
        for variable, variable_type in add_structure.items():
            table_string += f'ADD {variable} {variable_type},\n'

        return f'''ALTER TABLE {self.name}\n{table_string[:-2]};'''

    def alter_remove(self, columns: list[str]):
        """SQL query to alter the table and remove given columns"""

        table_string = ''
        for column in columns:
            table_string += f'DROP COLUMN {column},\n'

        return f'''ALTER TABLE {self.name}\n{table_string[:-2]};'''

    def insert(self, *args) -> str:
        """SQL query to insert"""

        if len(args) != len(self.variables):
            raise AttributeError(f'Table "{self.name}" expects {len(self.variables)} arguments, but {len(args)} arguments are provided')

        return f'''INSERT INTO {self.name} ({','.join(self.variables)}) VALUES ({','.join([str(arg) for arg in args])});'''

    def get(self, last_seconds: int | None = None):
        """SQL query to get last seconds of data"""

        if last_seconds is None:
            return f'''SELECT * FROM {self.name};'''
        return f'''SELECT * FROM {self.name} WHERE Time >= {int(time() - last_seconds)};'''


class PressureTable(Tables):
    name = 'Pressure'
    structure = {
        'Time': '''INTEGER DEFAULT (strftime('%s', 'now'))''',
        'PITBUL': 'FLOAT default 0',
        'LSD': 'FLOAT default 0',
        'Prevac': 'FLOAT default 0'
    }

    def __init__(self):
        super().__init__()


class DB:
    """
    Database class for storing and accessing data in the database

    :param commit_time_interval: interval in seconds until database will be committed if a query is executed
    :param no_setup: no setup at startup
    """

    def __init__(
        self,
        commit_time_interval: int = 300,
        no_setup: bool = False
    ):
        self.commit_time_interval = commit_time_interval
        
        # TODO: there might occur errors?!
        root_path = Path(__file__).parents[1]
        self.connection = connect(root_path / 'DB' / 'Laserlab.db')
        self.cursor = self.connection.cursor()
        
        self.new_commit_time = datetime.now()

        self.pressure_table = PressureTable()
        self.tables = [self.pressure_table]

        if not no_setup:
            self.setUp()

    def _execute(self, query: str, force_commit: bool = False):
        """
        Executes the SQL query and writes to database if timer is reached

        :param query: SQL query to be executed
        :param force_commit: forces a commit
        """

        GlobalConf.logger.debug(f'DB query: {query}')
        self.cursor.execute(query)

        now = datetime.now()
        if not force_commit:
            if now <= self.new_commit_time:
                return
        self.connection.commit()
        self.new_commit_time = now + timedelta(seconds=self.commit_time_interval)

    def _execute_return(self, query: str, force_commit: bool = False) -> list:
        """
        Executes the SQL query, writes to database if timer is reached and returns result.

        :param query: SQL query to be executed
        :param force_commit: forces a commit
        :return: list of results
        """

        self._execute(query, force_commit)
        return self.cursor.fetchall()

    def _commit(self):
        """Commits to database"""
        self.connection.commit()
        self.new_commit_time = datetime.now() + timedelta(self.commit_time_interval)

    def deleteAllTables(self):
        """Deletes all tables on the database"""

        self._execute('''SELECT name FROM sqlite_master WHERE type='table';''')
        tables = self.cursor.fetchall()

        for table in tables:
            self._execute(f'''DROP TABLE IF EXISTS {table[0]};''')

        self.connection.commit()

    def setUp(self):
        """Sets up all tables"""

        for table in self.tables:
            try:
                self._execute(table.exists())
            except OperationalError:
                GlobalConf.logger.info(f'INFO: Table "{table.name}" did not exist, will create it...')
                self._execute(table.create())

            result = [res[1] for res in self._execute_return(table.columns())]
            if set(result) != set(table.column_names()):
                raise RuntimeError(f'Columns of existing table "{table.name}" of ({result}) do not match required column names ({table.column_names()}).')

    def updateColumns(self):
        """Updates all columns of all tables. WARNING: will delete old columns that are not used"""
        self.removeOldColumns()
        self.addNewColumns()

    def addNewColumns(self, table: Tables = None, columns: list[str] = None):
        """
        Add new columns to table (from structure-definition to database.db file)

        :param table: table where new columns should be added
        :param columns: list of columns to be added (when non are provided all new ones will be added)
        """

        tables = self.tables
        if table:
            tables = [table]

        for table in tables:
            old_columns = [res[1] for res in self._execute_return(table.columns())]
            new_columns = table.column_names()
            if columns:
                new_columns = [c for c in new_columns if c in columns]
            diff_columns = list(set(new_columns) - set(old_columns))
            if diff_columns:
                self._execute(table.alter_add(diff_columns))

    def removeOldColumns(self, table: Tables = None, columns: list[str] = None):
        """
        Remove columns from table (from structure-definition to database.db file)

        :param table: table where columns should be removed
        :param columns: list of columns that are not removed (when non are provided all columns that are not in the structure-definition will be removed)
        """

        tables = self.tables
        if table:
            tables = [table]

        for table in tables:
            old_columns = [res[1] for res in self._execute_return(table.columns())]
            new_columns = table.column_names()
            if columns:
                new_columns = [c for c in new_columns if c not in columns]
            diff_columns = list(set(old_columns) - set(new_columns))
            if diff_columns:
                self._execute(table.alter_remove(diff_columns))

    def insertPressure(self, pressure_pitbul: float, pressure_lsd: float, pressure_prevac: float):
        """Inserts pressure values"""
        self._execute(self.pressure_table.insert(pressure_pitbul, pressure_lsd, pressure_prevac))

    def getPressure(self, last_seconds: int | None = 300):
        """Get pressure values"""

        results = self._execute_return(self.pressure_table.get(last_seconds))
        if not results:
            return False
        lists = []
        for _ in range(len(results[0])):
            lists.append([])
        for result in results:
            for i, res in enumerate(result):
                lists[i].append(res)
        return lists

    def close(self):
        """Must be called on close"""

        self.connection.commit()


def main():
    from random import random
    import matplotlib.pyplot as plt
    from time import sleep

    db = DB()

    d1, d2, d3 = 0, 0, 0
    for _ in range(100):
        d1, d2, d3 = d1 + random(), d2 + random(), d3 + random()
        db.insertPressure(d1, d2, d3)
        sleep(1)

    pressure = db.getPressure(300)
    print(pressure)
    if pressure:
        print(len(pressure[0]))
        plt.plot(pressure[0], pressure[1])
        plt.plot(pressure[0], pressure[2])
        plt.plot(pressure[0], pressure[3])
        plt.show()

    db.close()


def main2():
    pt = PressureTable()
    print(pt.create())
    print(pt.insert(1, 2))


if __name__ == '__main__':
    main()
