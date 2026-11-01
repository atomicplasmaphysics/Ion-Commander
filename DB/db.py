from __future__ import annotations
from sqlite3 import connect as connect_sqlite3, OperationalError, Connection, Cursor
from duckdb import connect as connect_duckdb, CatalogException, DuckDBPyConnection

from datetime import datetime, timedelta
from pathlib import Path

from enum import Enum, auto
from math import isfinite

import numpy as np


from Config.GlobalConf import GlobalConf, DefaultParams


class Tables:
    """
    Metadata for tables
    """

    name = ''
    structure = {
        'Time': '''BIGINT DEFAULT CAST(EXTRACT(EPOCH FROM now()) AS BIGINT)''',
    }
    index = ''
    # the History tab shows one entry per name (label) of the columns instead of one entry per column, it only shows the
    # readings of the time when a column had this name (e.g. a pressure gauge that moved to a different chamber)
    track_names = False

    def __init__(self):
        self.variables = []

        if not self.name:
            raise ValueError('No name defined')
        if not self.structure:
            raise ValueError(f'Table "{self.name}" has no structure')

        if ' ' in self.name:
            raise ValueError(f'Name {self.name} cannot have a space inside')

        for variable, variable_type in self.structure.items():
            if 'DEFAULT' not in variable_type:
                self.variables.append(variable)

    def column_names(self) -> list[str]:
        """Returns the column names"""
        return list(self.structure.keys())

    def create_table(self) -> str:
        """SQL query to create table"""
        table_string = ''
        for variable, variable_type in self.structure.items():
            table_string += f' {variable} {variable_type},\n'

        return f'''CREATE TABLE {self.name} (\n{table_string[:-2]}\n);'''

    def _index_name(self) -> str:
        """Returns name of index"""
        return f'idx_{self.name.lower()}_{self.index.lower()}'

    def create_index(self) -> str:
        """SQL query to create index"""
        if not self.index:
            return ''
        return f'''CREATE INDEX IF NOT EXISTS {self._index_name()} ON {self.name}({self.index})'''

    def exists_table(self) -> str:
        """SQL query if table exists"""
        return f'''SELECT * FROM {self.name} LIMIT 1;'''

    def exists_index(self) -> str:
        """SQL query if index exists"""
        if not self.index:
            return ''
        return f'''SELECT name FROM sqlite_master WHERE type='index' AND name='{self._index_name()}';'''

    def columns(self) -> str:
        """SQL query for column names"""
        return f'''PRAGMA table_info({self.name})'''

    def alter_add(self, columns: list[str]) -> str:
        """
        SQL query to alter the table and add given columns

        :param columns: list of columns
        """

        add_structure = dict()
        for column in columns:
            if column not in self.structure.keys():
                raise ValueError(f'Column "{column}" not in structure of table "{self.name}"')
            add_structure[column] = self.structure[column]

        table_string = ''
        for variable, variable_type in add_structure.items():
            table_string += f'ADD {variable} {variable_type},\n'

        return f'''ALTER TABLE {self.name}\n{table_string[:-2]};'''

    def alter_remove(self, columns: list[str]) -> str:
        """
        SQL query to alter the table and remove given columns

        :param columns: list of columns
        """

        table_string = ''
        for column in columns:
            table_string += f'DROP COLUMN {column},\n'

        return f'''ALTER TABLE {self.name}\n{table_string[:-2]};'''

    def insert(self, *args) -> str:
        """SQL query to insert"""

        if len(args) != len(self.variables):
            raise AttributeError(f'Table "{self.name}" expects {len(self.variables)} arguments, but {len(args)} arguments are provided')

        return f'''INSERT INTO {self.name} ({','.join(self.variables)}) VALUES ({','.join([self.sqlValue(arg) for arg in args])});'''

    @staticmethod
    def sqlValue(value) -> str:
        """Converts a value to SQL; None, nan and inf are stored as NULL (they would break the query)"""

        if value is None:
            return 'NULL'
        if isinstance(value, float) and not isfinite(value):
            return 'NULL'
        return str(value)

    def insert_parameterized(self) -> str:
        """SQL query to insert with placeholders (use for strings, values are passed separately)"""

        return f'''INSERT INTO {self.name} ({','.join(self.variables)}) VALUES ({','.join(['?'] * len(self.variables))});'''

    def get(self, column_ids: tuple[int], start_time: int | None, end_time: int | None, bucket_seconds: int | None = None, envelope: bool = False) -> tuple[list, str]:
        """
        SQL query to get columns of data within given timeframe

        :param column_ids: ids of columns
        :param start_time: start time as timestamp
        :param end_time: end time as timestamp
        :param bucket_seconds: if > 1 and the first column is "Time", the data is averaged in time buckets of this size (downsampling)
        :param envelope: with buckets: return avg, min and max of every column (columns: Time, c1_avg, c1_min, c1_max, c2_avg, ...)

        :returns: list of columns, sql query
        """

        if not column_ids:
            raise ValueError('No columns provided')
        column_names = []
        column_names_all = list(self.structure.keys())
        for column_id in column_ids:
            if column_id < 0 or column_id >= len(column_names_all):
                raise ValueError(f'Column id ({column_id}) is invalid, must be in range (0 .. {len(column_names_all)})')
            column_names.append(column_names_all[column_id])

        conditions = []
        if start_time is not None:
            conditions.append(f'Time >= {int(start_time)}')
        if end_time is not None:
            conditions.append(f'Time <= {int(end_time)}')
        condition = ' AND '.join(conditions)
        if condition:
            condition = f' WHERE {condition}'

        if bucket_seconds is not None and int(bucket_seconds) > 1 and column_names[0] == 'Time':
            bucket_seconds = int(bucket_seconds)
            # "Time - Time % x" works for sqlite3 and duckdb (integer division differs between them)
            selection = [f'Time - (Time % {bucket_seconds}) AS Time']
            for column_name in column_names[1:]:
                selection.append(f'avg({column_name}) AS {column_name}')
                if envelope:
                    selection.append(f'min({column_name}) AS {column_name}_min')
                    selection.append(f'max({column_name}) AS {column_name}_max')
            return column_names, f'''SELECT {', '.join(selection)} FROM {self.name}{condition} GROUP BY 1 ORDER BY 1;'''

        return column_names, f'''SELECT {', '.join(column_names)} FROM {self.name}{condition};'''


class PressureTable(Tables):
    name = 'Pressure'
    structure = {
        'Time': '''BIGINT DEFAULT CAST(EXTRACT(EPOCH FROM now()) AS BIGINT)''',
        'PITBUL': 'FLOAT default 0',
        'LSD': 'FLOAT default 0',
        'ESD': 'FLOAT default 0',
        'Prevac': 'FLOAT default 0',
    }
    track_names = True

    def __init__(self):
        super().__init__()


class PressureRS485Table(Tables):
    """
    Pressures of the gauges on the RS485 bus. There is one fixed column for every address of the bus, so adding gauges does
    not change the structure of the table. The names of the gauges are only labels (see <LabelsTable>), so renaming
    a gauge does not touch the data. A gauge without a reading is stored as NULL.
    """

    name = 'PressureRS485'
    addresses = range(1, 17)
    structure = {
        'Time': '''BIGINT DEFAULT CAST(EXTRACT(EPOCH FROM now()) AS BIGINT)''',
        **{f'Gauge{address:02d}': 'FLOAT' for address in addresses},
    }
    track_names = True

    def __init__(self):
        super().__init__()

    @staticmethod
    def column(address: int) -> str:
        """Returns name of the column of an address"""
        return f'Gauge{address:02d}'


class PSUTable(Tables):
    name = 'PSU'
    structure = {
        'Time': '''BIGINT DEFAULT CAST(EXTRACT(EPOCH FROM now()) AS BIGINT)''',
        'Channel0_Voltage': 'FLOAT default 0',
        'Channel0_Current': 'FLOAT default 0',
        'Channel1_Voltage': 'FLOAT default 0',
        'Channel1_Current': 'FLOAT default 0',
        'Channel2_Voltage': 'FLOAT default 0',
        'Channel2_Current': 'FLOAT default 0',
        'Channel3_Voltage': 'FLOAT default 0',
        'Channel3_Current': 'FLOAT default 0',
    }

    def __init__(self):
        super().__init__()


class LaserTable(Tables):
    name = 'Laser'
    structure = {
        'Time': '''BIGINT DEFAULT CAST(EXTRACT(EPOCH FROM now()) AS BIGINT)''',
        'Shutter': 'INTEGER default 0',
        'Pulsing': 'INTEGER default 0',
        'Status': 'INTEGER default 0',
        'Chiller_Temperature': 'FLOAT default 0',
        'Chiller_Set_Temperature': 'FLOAT default 0',
        'Baseplate_Temperature': 'FLOAT default 0',
        'Chiller_Flow': 'FLOAT default 0',
        'Chiller_Pressure': 'FLOAT default 0',
        'Amplifier_Repetition_Rate': 'FLOAT default 0',
        'Pulse_Width': 'INTEGER default 0',
        'Repetition_Rate_Divisor': 'INTEGER default 0',
        'Seeder_Bursts': 'INTEGER default 0',
        'RF_Level': 'FLOAT default 0',
    }

    def __init__(self):
        super().__init__()


class PowerMeterTable(Tables):
    name = 'PowerMeter'
    structure = {
        'Time': '''BIGINT DEFAULT CAST(EXTRACT(EPOCH FROM now()) AS BIGINT)''',
        'Power': 'FLOAT default 0',
        'Power_dBm': 'FLOAT default 0',
        'Current': 'FLOAT default 0',
        'Irradiance': 'FLOAT default 0',
        'Beam_Diameter': 'FLOAT default 0',
        'Attenuation': 'FLOAT default 0',
        'Averaging': 'INTEGER default 0',
        'Wavelength': 'INTEGER default 0',
    }

    def __init__(self):
        super().__init__()


class EBISTable(Tables):
    name = 'EBIS'
    structure = {
        'Time': '''BIGINT DEFAULT CAST(EXTRACT(EPOCH FROM now()) AS BIGINT)''',
        'Cathode_Voltage': 'FLOAT default 0',
        'Cathode_Current': 'FLOAT default 0',
        'DT1_Voltage': 'FLOAT default 0',
        'DT1_Current': 'FLOAT default 0',
        'DT2_Voltage': 'FLOAT default 0',
        'DT2_Current': 'FLOAT default 0',
        'DT3_Voltage': 'FLOAT default 0',
        'DT3_Current': 'FLOAT default 0',
        'Repeller_Voltage': 'FLOAT default 0',
        'Repeller_Current': 'FLOAT default 0',
        'Heating_Voltage': 'FLOAT default 0',
        'Heating_Current': 'FLOAT default 0',
    }

    def __init__(self):
        super().__init__()


class ElectrometerTable(Tables):
    name = 'Electrometer'
    structure = {
        'Time': '''BIGINT DEFAULT CAST(EXTRACT(EPOCH FROM now()) AS BIGINT)''',
        'Current': 'FLOAT default 0',
    }

    def __init__(self):
        super().__init__()


class EventsTable(Tables):
    """
    Events like interlock trips, (lost) connections or script starts.
    Not shown as plottable data, but marked in the History plots.
    """

    name = 'Events'
    structure = {
        'Time': '''BIGINT DEFAULT CAST(EXTRACT(EPOCH FROM now()) AS BIGINT)''',
        'Source': 'VARCHAR',
        'Type': 'VARCHAR',
        'Message': 'VARCHAR',
        'Value': 'DOUBLE',
    }

    def __init__(self):
        super().__init__()


class LabelsTable(Tables):
    """
    Human readable labels (and units) of the data columns.

    The column names of the data tables are stable ids that should never change. If something is renamed in the GUI
    (e.g. a pressure gauge), only a new row with the new label is added here (valid from <Time> on).
    This keeps the old data usable and the History tab shows the current label.
    """

    name = 'Labels'
    structure = {
        'Time': '''BIGINT DEFAULT CAST(EXTRACT(EPOCH FROM now()) AS BIGINT)''',
        'TableName': 'VARCHAR',
        'ColumnName': 'VARCHAR',
        'Label': 'VARCHAR',
        'Unit': 'VARCHAR',
    }

    def __init__(self):
        super().__init__()


class DB:
    """
    Database class for storing and accessing data in the database

    :param commit_time_interval: interval in seconds until database will be committed if a query is executed
    :param no_setup: no setup at startup
    :param debug: if debug is enabled
    :param db_file: use given database file (use empty for default one)
    :param db_type: use database query language <DBType>
    """

    class DBType(Enum):
        sqlite3 = auto()
        duckdb = auto()

    default_last_seconds = 300

    def __init__(
        self,
        commit_time_interval: int = 300,
        no_setup: bool = False,
        debug: bool = False,
        db_file: str = '',
        db_type: DBType = DBType.duckdb
    ):
        self.commit_time_interval = commit_time_interval
        self.debug = debug

        if not db_file:
            if db_type == DB.DBType.sqlite3:
                db_file = DefaultParams.db_file_sqlite3
            elif db_type == DB.DBType.duckdb:
                db_file = DefaultParams.db_file_duckdb
            else:
                GlobalConf.logger.error(f'Provided database type "{db_type}" is not supported!')
                raise ValueError(f'Provided database type "{db_type}" is not supported!')

        self.database_path = Path(__file__).parents[1] / DefaultParams.db_folder / db_file
        self.connection: Connection | DuckDBPyConnection | None = None
        self.cursor: Cursor | DuckDBPyConnection | None = None

        try:
            if db_type == DB.DBType.sqlite3:
                self.connection = connect_sqlite3(self.database_path)
            elif db_type == DB.DBType.duckdb:
                self.connection = connect_duckdb(self.database_path)
            else:
                GlobalConf.logger.error(f'Provided database type "{db_type}" is not supported!')
                raise ValueError(f'Provided database type "{db_type}" is not supported!')
            GlobalConf.logger.info(f'Using database system "{db_type}"')

            self.cursor = self.connection.cursor()

        except (OperationalError, CatalogException) as error:
            GlobalConf.logger.error(f'DB: Can not connect to database in file "{self.database_path}" because: {error}')

        self.new_commit_time = datetime.now()

        self.pressure_table = PressureTable()
        self.pressure_rs485_table = PressureRS485Table()
        self.psu_table = PSUTable()
        self.laser_table = LaserTable()
        self.power_meter_table = PowerMeterTable()
        self.ebis_table = EBISTable()
        self.electrometer_table = ElectrometerTable()
        self.tables = [
            self.pressure_table,
            self.pressure_rs485_table,
            self.psu_table,
            self.laser_table,
            self.power_meter_table,
            self.ebis_table,
            self.electrometer_table
        ]

        # tables with meta information (not plottable in the History tab)
        self.events_table = EventsTable()
        self.labels_table = LabelsTable()
        self.meta_tables = [
            self.events_table,
            self.labels_table
        ]

        # cache of the latest labels {table_name: {column_name: (label, unit)}}
        self.labels_cache: dict[str, dict[str, tuple[str, str]]] = {}

        if not no_setup:
            self.setUp()

    def _execute(self, query: str, force_commit: bool = False):
        """
        Executes the SQL query and writes to database if timer is reached

        :param query: SQL query to be executed
        :param force_commit: forces a commit
        """

        if self.connection is None or self.cursor is None:
            GlobalConf.logger.error(f'DB: connection or cursor is None')
            return

        if self.debug:
            GlobalConf.logger.debug(f'DB query: {query}')
        self.cursor.execute(query)

        now = datetime.now()
        if not force_commit:
            if now <= self.new_commit_time:
                return
        self.connection.commit()
        self.new_commit_time = now + timedelta(seconds=self.commit_time_interval)

    def _execute_parameterized(self, query: str, parameters: list | tuple, force_commit: bool = False):
        """
        Executes the SQL query with parameters (needed for strings) and writes to database if timer is reached

        :param query: SQL query with "?" placeholders
        :param parameters: values for the placeholders
        :param force_commit: forces a commit
        """

        if self.connection is None or self.cursor is None:
            GlobalConf.logger.error(f'DB: connection or cursor is None')
            return

        if self.debug:
            GlobalConf.logger.debug(f'DB query: {query} with {parameters}')
        self.cursor.execute(query, parameters)

        now = datetime.now()
        if not force_commit and now <= self.new_commit_time:
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

        if self.connection is None or self.cursor is None:
            GlobalConf.logger.error(f'DB: connection or cursor is None')
            return []

        self._execute(query, force_commit)
        return self.cursor.fetchall()

    def _commit(self):
        """Commits to database"""

        if self.connection is None or self.cursor is None:
            GlobalConf.logger.error(f'DB: connection or cursor is None')
            return

        self.connection.commit()
        self.new_commit_time = datetime.now() + timedelta(seconds=self.commit_time_interval)

    def deleteAllTables(self):
        """Deletes all tables on the database"""

        if self.connection is None or self.cursor is None:
            GlobalConf.logger.error(f'DB: connection or cursor is None')
            return

        self._execute('''SELECT name FROM sqlite_master WHERE type='table';''')
        tables = self.cursor.fetchall()

        for table in tables:
            self._execute(f'''DROP TABLE IF EXISTS {table[0]};''')

        self.connection.commit()

    def setUp(self):
        """Sets up all tables"""

        for table in self.tables + self.meta_tables:
            # check if table exists and if not create it
            try:
                self._execute(table.exists_table())
            except (OperationalError, CatalogException):
                GlobalConf.logger.info(f'DB: Table "{table.name}" did not exist, will create it...')
                self._execute(table.create_table())

            # check if table structure is correct
            result = [res[1] for res in self._execute_return(table.columns())]
            if set(result) != set(table.column_names()):
                raise RuntimeError(f'Columns of existing table "{table.name}" of ({result}) do not match required column names ({table.column_names()}).\nTry to call DB.updateColumns() for updating the columns. You should probably safe the DB beforehand.')

            # check if index exists and if not create it
            index_query = table.exists_index()
            if index_query:
                self._execute(index_query)
                if not self.cursor.fetchone():
                    GlobalConf.logger.info(f'DB: Index for table "{table.name}" on "{table.index}" did not exist, will create it...')
                    self._execute(table.create_index())

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

    def getData(
        self,
        table_idx: int,
        columns: int | tuple[int] | list[str] | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
        bucket_seconds: int | None = None,
        envelope: bool = False
    ) -> bool | tuple[list, np.ndarray]:
        """
        Get values from table with table_idx

        :param columns: column ids or column names
        :param table_idx: index of table
        :param start_time: start time as timestamp
        :param end_time: end time as timestamp
        :param bucket_seconds: average data in time buckets of this size (None or <= 1: raw data)
        :param envelope: with buckets, also return min and max of every bucket (3 value columns per column: avg, min, max)
        """

        columns_all = list(self.tables[table_idx].structure.keys())

        column_ids = columns
        if columns is None:
            column_ids = tuple(range(len(columns_all)))
        elif isinstance(columns, int):
            column_ids = (columns, )
        elif isinstance(columns, list):
            column_ids = []
            for column in columns:
                if column not in columns_all:
                    raise ValueError(f'Column "{column}" is not in table {self.tables[table_idx].name}')
                column_ids.append(columns_all.index(column))
            column_ids = tuple(column_ids)

        column_names, query = self.tables[table_idx].get(column_ids, start_time, end_time, bucket_seconds, envelope)
        results = self._execute_return(query)
        if not results:
            return False
        return column_names, np.array(results)

    def insertPressure(
        self,
        pitbul: float,
        lsd: float,
        esd: float,
        prevac: float
    ):
        """
        Inserts Pressure values

        :param pitbul: pressure for PITBUL in [mbar]
        :param lsd: pressure for LSD in [mbar]
        :param esd: pressure for ESD in [mbar]
        :param prevac: pressure for prevacuum in [mbar]
        """

        self._execute(self.pressure_table.insert(pitbul, lsd, esd, prevac))

    def getPressure(
        self,
        columns: int | tuple[int] | list[str] | None = None,
        start_time: int | None = None,
        end_time: int | None = None
    ) -> bool | tuple[list, np.ndarray]:
        """
        Get Pressure values

        :param columns: list of name of columns, tuple of ids of columns or None(=all columns)
        :param start_time: start time as timestamp
        :param end_time: end time as timestamp

        :returns: tuple of column names and column values
        """

        return self.getData(self.tables.index(self.pressure_table), columns, start_time, end_time)

    def insertPressureRS485(self, pressures: dict[int, float | None]):
        """
        Inserts pressure values of the gauges on the RS485 bus

        :param pressures: dictionary of {address: pressure in [mbar]}, missing gauges and None are stored as NULL
        """

        self._execute(self.pressure_rs485_table.insert(*[pressures.get(address) for address in self.pressure_rs485_table.addresses]))

    def getPressureRS485(
        self,
        columns: int | tuple[int] | list[str] | None = None,
        start_time: int | None = None,
        end_time: int | None = None
    ) -> bool | tuple[list, np.ndarray]:
        """
        Get pressure values of the gauges on the RS485 bus

        :param columns: list of name of columns, tuple of ids of columns or None(=all columns)
        :param start_time: start time as timestamp
        :param end_time: end time as timestamp

        :returns: tuple of column names and column values
        """

        return self.getData(self.tables.index(self.pressure_rs485_table), columns, start_time, end_time)

    def insertPSU(
        self,
        ch0v: float,
        ch0i: float,
        ch1v: float,
        ch1i: float,
        ch2v: float,
        ch2i: float,
        ch3v: float,
        ch3i: float,
    ):
        """
        Inserts PSU values

        :param ch0v: measured voltage of channel 0 in [V]
        :param ch0i: measured current of channel 0 in [A]
        :param ch1v: measured voltage of channel 1 in [V]
        :param ch1i: measured current of channel 1 in [A]
        :param ch2v: measured voltage of channel 2 in [V]
        :param ch2i: measured current of channel 2 in [A]
        :param ch3v: measured voltage of channel 3 in [V]
        :param ch3i: measured current of channel 3 in [A]
        """

        self._execute(self.psu_table.insert(ch0v, ch0i, ch1v, ch1i, ch2v, ch2i, ch3v, ch3i))

    def getPSU(
        self,
        columns: int | tuple[int] | list[str] | None = None,
        start_time: int | None = None,
        end_time: int | None = None
    ) -> bool | tuple[list, np.ndarray]:
        """
        Get PSU values

        :param columns: list of name of columns, tuple of ids of columns or None(=all columns)
        :param start_time: start time as timestamp
        :param end_time: end time as timestamp

        :returns: tuple of column names and column values
        """

        return self.getData(self.tables.index(self.psu_table), columns, start_time, end_time)

    def insertLaser(
        self,
        s: bool | int = -1,
        pc: bool | int = -1,
        l: int = -1,
        cht: float = -1,
        chst: float = -1,
        bt: float = -1,
        chf: float = -1,
        chp: float = -1,
        mrr: float = -1,
        pw: int = -1,
        rrd: int = -1,
        sb: int = -1,
        rl: float = -1
    ):
        """
        Inserts Laser values

        :param s: shutter on
        :param pc: pulsing on
        :param l: system status
        :param cht: chiller temperature in [°C]
        :param chst: chiller set temperature in [°C]
        :param bt: baseplate temperature in [°C]
        :param chf: chiller flowrate in [lpm]
        :param chp: chiller pressure in [bar]
        :param mrr: amplifier repetition rate in [kHz]
        :param pw: pulse width in [fs]
        :param rrd: repetition rate divisor
        :param sb: number of seeder bursts
        :param rl: RF level in [%]
        """

        self._execute(self.laser_table.insert(int(s), int(pc), l, cht, chst, bt, chf, chp, mrr, pw, rrd, sb, rl))

    def getLaser(
        self,
        columns: int | tuple[int] | list[str] | None = None,
        start_time: int | None = None,
        end_time: int | None = None
    ) -> bool | tuple[list, np.ndarray]:
        """
        Get Laser values

        :param columns: list of name of columns, tuple of ids of columns or None(=all columns)
        :param start_time: start time as timestamp
        :param end_time: end time as timestamp

        :returns: tuple of column names and column values
        """

        return self.getData(self.tables.index(self.laser_table), columns, start_time, end_time)

    def insertPowerMeter(
        self,
        power: float,
        power_dbm: float,
        current: float,
        irradiance: float,
        beam_diameter: float,
        attenuation: float,
        averaging: int,
        wavelength: int
    ):
        """
        Inserts Power Meter values

        :param power: power in [W]
        :param power_dbm: power in [dBm]
        :param current: current in [A]
        :param irradiance: irradiance in [W/cm²]
        :param beam_diameter: beam diameter in [mm]
        :param attenuation: attenuation in [dBm]
        :param averaging: count of averaging events
        :param wavelength: wavelength in [nm]
        """

        self._execute(self.power_meter_table.insert(power, power_dbm, current, irradiance, beam_diameter, attenuation, averaging, wavelength))

    def getPowerMeter(
        self,
        columns: int | tuple[int] | list[str] | None = None,
        start_time: int | None = None,
        end_time: int | None = None
    ) -> bool | tuple[list, np.ndarray]:
        """
        Get Power Meter values

        :param columns: list of name of columns, tuple of ids of columns or None(=all columns)
        :param start_time: start time as timestamp
        :param end_time: end time as timestamp

        :returns: tuple of column names and column values
        """

        return self.getData(self.tables.index(self.power_meter_table), columns, start_time, end_time)

    def insertEBIS(
        self,
        CatV: float,
        CatI: float,
        DT1V: float,
        DT1I: float,
        DT2V: float,
        DT2I: float,
        DT3V: float,
        DT3I: float,
        RepV: float,
        RepI: float,
        HeatV: float,
        HeatI: float
    ): 
        """
        Inserts EBIS values

        :param CatV: cathode voltage in [V]
        :param CatI: cathode current in [A]
        :param DT1V: drift tube 1 voltage in [V]
        :param DT1I: drift tube 1 current in [A]
        :param DT2V: drift tube 2 voltage in [V]
        :param DT2I: drift tube 2 current in [A]
        :param DT3V: drift tube 3 voltage in [V]
        :param DT3I: drift tube 3 current in [A]
        :param RepV: repeller voltage in [V]
        :param RepI: repeller current in [A]
        :param HeatV: heating voltage in [V]
        :param HeatI: heating current in [A]
        """

        self._execute(self.ebis_table.insert(CatV, CatI, DT1V, DT1I, DT2V, DT2I, DT3V, DT3I, RepV, RepI, HeatV, HeatI))

    def getEBIS(
        self,
        columns: int | tuple[int] | list[str] | None = None,
        start_time: int | None = None,
        end_time: int | None = None
    ) -> bool | tuple[list, np.ndarray]:
        """
        Get EBIS values

        :param columns: list of name of columns, tuple of ids of columns or None(=all columns)
        :param start_time: start time as timestamp
        :param end_time: end time as timestamp

        :returns: tuple of column names and column values
        """

        return self.getData(self.tables.index(self.ebis_table), columns, start_time, end_time)

    def insertElectrometer(self, current: float):
        """
        Inserts electrometer values

        :param current: current in [A]
        """

        self._execute(self.electrometer_table.insert(current))

    def getElectrometer(
        self,
        columns: int | tuple[int] | list[str] | None = None,
        start_time: int | None = None,
        end_time: int | None = None
    ) -> bool | tuple[list, np.ndarray]:
        """
        Get electrometer values

        :param columns: list of name of columns, tuple of ids of columns or None(=all columns)
        :param start_time: start time as timestamp
        :param end_time: end time as timestamp
        """

        return self.getData(self.tables.index(self.electrometer_table), columns, start_time, end_time)

    def insertEvent(self, source: str, event_type: str, message: str = '', value: float = 0., force_commit: bool = True):
        """
        Inserts an event (committed immediately by default, so it is not lost on a crash)

        :param source: source of event (e.g. "EBIS", "PSU", "Pressure")
        :param event_type: type of event (e.g. "interlock_hard", "connection_lost")
        :param message: human readable message
        :param value: optional value (e.g. pressure at the time of the trip)
        :param force_commit: commit immediately
        """

        try:
            self._execute_parameterized(
                self.events_table.insert_parameterized(),
                (str(source), str(event_type), str(message), float(value)),
                force_commit=force_commit
            )
        except Exception as error:
            # logging an event must never crash the caller (e.g. the interlock)
            GlobalConf.logger.error(f'DB: Could not insert event ({source}, {event_type}, {message}, {value}): {error}')

    def getEvents(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        source: str | None = None
    ) -> list[tuple[int, str, str, str, float]]:
        """
        Get events within given timeframe

        :param start_time: start time as timestamp
        :param end_time: end time as timestamp
        :param source: only events of this source (None = all)
        :returns: list of (time, source, type, message, value)
        """

        if self.connection is None or self.cursor is None:
            GlobalConf.logger.error(f'DB: connection or cursor is None')
            return []

        conditions = []
        parameters = []
        if start_time is not None:
            conditions.append('Time >= ?')
            parameters.append(int(start_time))
        if end_time is not None:
            conditions.append('Time <= ?')
            parameters.append(int(end_time))
        if source is not None:
            conditions.append('Source = ?')
            parameters.append(source)
        condition = f' WHERE {" AND ".join(conditions)}' if conditions else ''

        try:
            self.cursor.execute(f'''SELECT Time, Source, Type, Message, Value FROM {self.events_table.name}{condition} ORDER BY Time, rowid;''', parameters)
            return self.cursor.fetchall()
        except Exception as error:
            GlobalConf.logger.error(f'DB: Could not read events: {error}')
            return []

    def getLabels(self, table_name: str) -> dict[str, tuple[str, str]]:
        """
        Returns the latest labels of the columns of a table

        :param table_name: name of the data table
        :returns: dictionary of {column_name: (label, unit)}
        """

        if table_name in self.labels_cache:
            return dict(self.labels_cache[table_name])

        labels = {}
        if self.connection is None or self.cursor is None:
            return labels

        try:
            self.cursor.execute(
                f'''SELECT ColumnName, Label, Unit FROM {self.labels_table.name} WHERE TableName = ? ORDER BY Time, rowid;''',
                (table_name, )
            )
            for column_name, label, unit in self.cursor.fetchall():
                labels[column_name] = (label, unit)
        except Exception as error:
            GlobalConf.logger.error(f'DB: Could not read labels of table "{table_name}": {error}')

        self.labels_cache[table_name] = labels
        return dict(labels)

    def getLabelHistory(self, table_name: str, column_name: str) -> list[tuple[int, str, str]]:
        """
        Returns all labels a column ever had

        :param table_name: name of the data table
        :param column_name: name of the column
        :returns: list of (time, label, unit)
        """

        if self.connection is None or self.cursor is None:
            return []

        try:
            self.cursor.execute(
                f'''SELECT Time, Label, Unit FROM {self.labels_table.name} WHERE TableName = ? AND ColumnName = ? ORDER BY Time, rowid;''',
                (table_name, column_name)
            )
            return self.cursor.fetchall()
        except Exception as error:
            GlobalConf.logger.error(f'DB: Could not read label history of "{table_name}.{column_name}": {error}')
            return []

    def getNamePeriods(self, table_name: str) -> dict[str, list[tuple[str, str, int, int | None]]]:
        """
        Returns when which name was used: every label of a column is valid from its time until the time of the next label
        of this column. An empty label means that the readings of this time have no name, these are not returned.

        :param table_name: name of the data table
        :returns: dictionary of {name: [(column_name, unit, start_time, end_time or None if it is still valid), ...]}, latest name first
        """

        if self.connection is None or self.cursor is None:
            return {}

        try:
            self.cursor.execute(
                f'''SELECT ColumnName, Time, Label, Unit FROM {self.labels_table.name} WHERE TableName = ? ORDER BY ColumnName, Time, rowid;''',
                (table_name, )
            )
            rows = self.cursor.fetchall()
        except Exception as error:
            GlobalConf.logger.error(f'DB: Could not read names of table "{table_name}": {error}')
            return {}

        periods = []
        for row, next_row in zip(rows, rows[1:] + [None]):
            column_name, start_time, label, unit = row
            end_time = next_row[1] if next_row is not None and next_row[0] == column_name else None
            if label:
                periods.append((label, (column_name, unit, start_time, end_time)))

        # names that are still used first, then the most recently used ones
        periods.sort(key=lambda period: (period[1][3] is None, period[1][3] or 0, period[1][2]), reverse=True)
        names = {}
        for label, period in periods:
            names.setdefault(label, []).append(period)
        for name_periods in names.values():
            name_periods.sort(key=lambda period: period[2])
        return names

    def setLabelHistory(self, table_name: str, column_name: str, history: list[tuple[int, str, str]]) -> bool:
        """
        Replaces all labels of a column (e.g. to assign the readings of a time to a different name). The readings are not changed.

        :param table_name: name of the data table
        :param column_name: name of the column
        :param history: list of (time, label, unit), an empty label means that the readings of this time have no name
        :returns: True if the labels were stored
        """

        old_history = self.getLabelHistory(table_name, column_name)
        GlobalConf.logger.info(f'DB: Labels of "{table_name}.{column_name}" changed from {old_history} to {history}')
        insert = f'''INSERT INTO {self.labels_table.name} (Time, TableName, ColumnName, Label, Unit) VALUES (?, ?, ?, ?, ?);'''
        delete = f'''DELETE FROM {self.labels_table.name} WHERE TableName = ? AND ColumnName = ?;'''
        stored = True
        try:
            self._execute_parameterized(delete, (table_name, column_name))
            for time, label, unit in history:
                self._execute_parameterized(insert, (time, table_name, column_name, label, unit))
        except Exception as error:
            GlobalConf.logger.error(f'DB: Could not store labels of "{table_name}.{column_name}", restoring the old ones: {error}')
            stored = False
            self._execute_parameterized(delete, (table_name, column_name))
            for time, label, unit in old_history:
                self._execute_parameterized(insert, (time, table_name, column_name, label, unit))

        self.labels_cache.pop(table_name, None)
        self._commit()
        return stored

    def updateLabels(self, table_name: str, labels: dict[str, str | tuple[str, str]]):
        """
        Stores the labels of the columns of a table, but only if they changed (rename-proof logging)

        :param table_name: name of the data table
        :param labels: dictionary of {column_name: label} or {column_name: (label, unit)}
        """

        tables = {table.name: table for table in self.tables}
        if table_name not in tables:
            GlobalConf.logger.error(f'DB: Can not set labels, table "{table_name}" does not exist')
            return

        old_labels = self.getLabels(table_name)
        changed = False
        for column_name, label in labels.items():
            if column_name not in tables[table_name].structure:
                GlobalConf.logger.error(f'DB: Can not set label "{label}", column "{column_name}" does not exist in table "{table_name}"')
                continue

            unit = ''
            if isinstance(label, (tuple, list)):
                label, unit = label

            if old_labels.get(column_name) == (label, unit):
                continue

            if column_name in old_labels:
                GlobalConf.logger.info(f'DB: Label of "{table_name}.{column_name}" changed from "{old_labels[column_name][0]}" to "{label}"')
                # a renamed label is valid from now on
                query = self.labels_table.insert_parameterized()
                parameters = (table_name, column_name, str(label), str(unit))
            else:
                # the first label of a column is valid from the beginning (time 0), so it also describes all old data
                query = f'''INSERT INTO {self.labels_table.name} (Time, TableName, ColumnName, Label, Unit) VALUES (?, ?, ?, ?, ?);'''
                parameters = (0, table_name, column_name, str(label), str(unit))
            try:
                self._execute_parameterized(query, parameters)
                changed = True
            except Exception as error:
                GlobalConf.logger.error(f'DB: Could not store label "{label}" of "{table_name}.{column_name}": {error}')

        if changed:
            self.labels_cache.pop(table_name, None)
            self._commit()

    def getSize(self) -> int:
        """Returns the size of the database files (including the write-ahead log) in bytes"""

        size = 0
        for path in [self.database_path, self.database_path.with_name(self.database_path.name + '.wal')]:
            try:
                size += path.stat().st_size
            except OSError:
                pass
        return size

    def close(self):
        """Must be called on close"""
        if self.connection is None or self.cursor is None:
            GlobalConf.logger.error(f'DB: connection or cursor is None')
            return

        self.connection.commit()
        # close the connection (writes a checkpoint, DuckDB >= 2.0 reports objects alive at exit as leaks otherwise)
        self.cursor.close()
        self.connection.close()
        self.cursor = None
        self.connection = None


def main():
    import logging
    from time import time
    import matplotlib.pyplot as plt

    logging.basicConfig(level=logging.DEBUG)

    db = DB(debug=True)

    start_time = time()
    pressure = db.getPressure()
    print(f'getPressure(): took {time() - start_time:.2f} seconds')

    if pressure is not False:
        plt.plot(pressure[:, 0], pressure[:, 1], label='PITBUL')
        plt.plot(pressure[:, 0], pressure[:, 2], label='LSD')
        plt.plot(pressure[:, 0], pressure[:, 3], label='prevac')
        plt.legend(loc='upper right')
        plt.yscale('log')
        plt.show()

    db.close()


def test_data():
    from time import sleep
    from math import sqrt, log10, pi
    from random import random

    db = DB(debug=True)

    for i in range(1800):
        print(f'{i} seconds')

        power = (7.5 + random() * 0.5) * 1E-3
        power_dbm = 10 * log10(1000 * power)
        current = (2 + random() * 0.5) * 1E-7
        beam_diameter = 2.2
        attenuation = 0
        averaging = 10
        wavelength = 276
        beam_area = (beam_diameter / sqrt(2) / 10) ** 2 / 4 * pi
        irradiance = power / beam_area

        db.insertPowerMeter(power, power_dbm, current, irradiance, beam_diameter, attenuation, averaging, wavelength)

        sleep(1)

    db.close()


def rename_columns():
    db = DB(debug=True, no_setup=True)

    '''
    name = 'PSU'
    structure = {
        'CH0V': 'Channel0_Voltage',
        'CH0I': 'Channel0_Current',
        'CH1V': 'Channel1_Voltage',
        'CH1I': 'Channel1_Current',
        'CH2V': 'Channel2_Voltage',
        'CH2I': 'Channel2_Current',
        'CH3V': 'Channel3_Voltage',
        'CH3I': 'Channel3_Current',
    }
    '''

    '''
    name = 'Laser'
    structure = {
        'S': 'Shutter',
        'PC': 'Pulsing',
        'L': 'Status',
        'CHT': 'Chiller_Temperature',
        'CHST': 'Chiller_Set_Temperature',
        'BT': 'Baseplate_Temperature',
        'CHF': 'Chiller_Flow',
        'MRR': 'Amplifier_Repetition_Rate',
        'PW': 'Pulse_Width',
        'RRD': 'Repetition_Rate_Divisor',
        'SB': 'Seeder_Bursts',
        'RL': 'RF_Level',
    }
    '''

    name = 'PowerMeter'
    structure = {
        'Beam_diameter': 'Beam_Diameter',
    }

    for old, new in structure.items():
        db._execute(f'ALTER TABLE {name} RENAME COLUMN {old} to {new};')

    db.close()


def query_plan():
    db = DB(debug=True)

    print(db._execute_return('''
        EXPLAIN QUERY PLAN
        SELECT * FROM Laser WHERE Time >= 1700000000 AND Time <= 1700003600;
    '''))

    print(db._execute_return('PRAGMA table_info(Laser);'))

    print(db._execute_return('SELECT typeof(Time), Time FROM Laser LIMIT 20;'))

    print(db._execute_return('SELECT typeof(Time), COUNT(*) FROM Laser GROUP BY typeof(Time);'))

    db.close()


def time_db():
    from time import time
    from datetime import datetime

    db = DB()
    #db = DB(debug=True, db_type=DB.DBType.sqlite3, db_file='Laserlab_backup.db')

    start_time = time()
    db.getLaser(
        start_time=int(datetime.strptime('01.08.2025 00:00:00', '%d.%m.%Y %H:%M:%S').timestamp()),
        end_time=int(datetime.strptime('31.08.2025 00:00:00', '%d.%m.%Y %H:%M:%S').timestamp())
    )
    print(f'Took {time() - start_time}s to look up data from 01.08.2025 to 31.08.2025')


    start_time = time()
    db.getLaser(
        start_time=int(datetime.strptime('01.01.2025 00:00:00', '%d.%m.%Y %H:%M:%S').timestamp()),
        end_time=int(datetime.strptime('31.08.2025 00:00:00', '%d.%m.%Y %H:%M:%S').timestamp())
    )
    print(f'Took {time() - start_time}s to look up data from 01.01.2025 to 31.08.2025')

    db.close()

    """
    Results

    sqlite3(indexed):
    Took 4.675286531448364s to look up data from 01.08.2025 to 31.08.2025
    Took 63.097015380859375s to look up data from 01.01.2025 to 31.08.2025
    
    sqlite3(pragmas):
    Took 4.630336761474609s to look up data from 01.08.2025 to 31.08.2025
    Took 63.966304540634155s to look up data from 01.01.2025 to 31.08.2025
    
    duckdb:
    Took 3.174304723739624s to look up data from 01.08.2025 to 31.08.2025
    Took 45.66825556755066s to look up data from 01.01.2025 to 31.08.2025
    """


def setup_duckdb_naive():
    db_sqlite3 = DB(debug=True, no_setup=True, db_file='Laserlab.db', db_type=DB.DBType.sqlite3)
    db_duckdb = DB(debug=True, db_type=DB.DBType.duckdb)

    for device in ['Pressure', 'PSU', 'Laser', 'PowerMeter',  'EBIS']:
        print(f'Working on migrating "{device}"')
        print(' .reading data')
        data = db_sqlite3.__getattribute__(f'get{device}')(
            start_time=int(datetime.strptime('01.01.2000 00:00:00', '%d.%m.%Y %H:%M:%S').timestamp()),
            end_time=int(datetime.strptime('01.01.2030 00:00:00', '%d.%m.%Y %H:%M:%S').timestamp())
        )

        print(' .writing data')
        for d in data:
            db_duckdb.__getattribute__(f'insert{device}')(*d[1:])

        print(' .done')

    db_sqlite3.close()
    db_duckdb.close()


def setup_duckdb():
    db_duckdb = DB(debug=True, db_type=DB.DBType.duckdb)

    db_duckdb._execute('INSTALL sqlite;')
    db_duckdb._execute('LOAD sqlite;')

    db_duckdb._execute(f'''ATTACH '{Path(__file__).parents[1] / DefaultParams.db_folder / 'Laserlab_backup.db'}' AS sqlite_db (TYPE SQLITE);''')

    for table in ['Pressure', 'PSU', 'Laser', 'PowerMeter', 'EBIS']:
        print(f'Copying table {table} ...')
        db_duckdb._execute(f'''INSERT INTO {table} SELECT * FROM sqlite_db.{table}''')

    db_duckdb.close()


if __name__ == '__main__':
    db_duckdb = DB(debug=True, db_type=DB.DBType.duckdb, no_setup=True)
    db_duckdb.updateColumns()
    db_duckdb.close()
