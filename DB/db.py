from __future__ import annotations
from sqlite3 import connect, OperationalError, Connection, Cursor
from time import time
from datetime import datetime, timedelta
from pathlib import Path


import numpy as np


from Config.GlobalConf import GlobalConf, DefaultParams


class Tables:
    """
    Metadata for tables
    """

    name = ''
    structure = {
        'Time': '''INTEGER DEFAULT (strftime('%s', 'now'))''',
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
        'Prevac': 'FLOAT default 0',
    }

    def __init__(self):
        super().__init__()


class PSUTable(Tables):
    name = 'PSU'
    structure = {
        'Time': '''INTEGER DEFAULT (strftime('%s', 'now'))''',
        'CH0V': 'FLOAT default 0',
        'CH0I': 'FLOAT default 0',
        'CH1V': 'FLOAT default 0',
        'CH1I': 'FLOAT default 0',
        'CH2V': 'FLOAT default 0',
        'CH2I': 'FLOAT default 0',
        'CH3V': 'FLOAT default 0',
        'CH3I': 'FLOAT default 0',
    }

    def __init__(self):
        super().__init__()


class LaserTable(Tables):
    name = 'Laser'
    structure = {
        'Time': '''INTEGER DEFAULT (strftime('%s', 'now'))''',
        'S': 'INTEGER default 0',
        'PC': 'INTEGER default 0',
        'L': 'INTEGER default 0',
        'CHT': 'FLOAT default 0',
        'CHST': 'FLOAT default 0',
        'BT': 'FLOAT default 0',
        'CHF': 'FLOAT default 0',
        'MRR': 'FLOAT default 0',
        'PW': 'INTEGER default 0',
        'RRD': 'INTEGER default 0',
        'SB': 'INTEGER default 0',
        'RL': 'FLOAT default 0',
    }

    def __init__(self):
        super().__init__()


class PowerMeterTable(Tables):
    name = 'PowerMeter'
    structure = {
        'Time': '''INTEGER DEFAULT (strftime('%s', 'now'))''',
        'Power': 'FLOAT default 0',
        'Power_dBm': 'FLOAT default 0',
        'Current': 'FLOAT default 0',
        'Irradiance': 'FLOAT default 0',
        'Beam_diameter': 'FLOAT default 0',
        'Attenuation': 'FLOAT default 0',
        'Averaging': 'INTEGER default 0',
        'Wavelength': 'INTEGER default 0',
    }

    def __init__(self):
        super().__init__()


class DB:
    """
    Database class for storing and accessing data in the database

    :param commit_time_interval: interval in seconds until database will be committed if a query is executed
    :param no_setup: no setup at startup
    :param debug: if debug is enabled
    """

    default_last_seconds = 300

    def __init__(
        self,
        commit_time_interval: int = 300,
        no_setup: bool = False,
        debug: bool = True  # TODO: change this
    ):
        self.commit_time_interval = commit_time_interval
        self.debug = debug

        database_path = Path(__file__).parents[1] / DefaultParams.db_folder / DefaultParams.db_file
        self.connection: Connection | None = None
        self.cursor: Cursor | None = None

        try:
            self.connection = connect(database_path)
            self.cursor = self.connection.cursor()
        except OperationalError as error:
            GlobalConf.logger.error(f'DB: Can not connect to database in file "{database_path}" because: {error}')
        
        self.new_commit_time = datetime.now()

        self.pressure_table = PressureTable()
        self.psu_table = PSUTable()
        self.laser_table = LaserTable()
        self.power_meter_table = PowerMeterTable()
        self.tables = [
            self.pressure_table,
            self.psu_table,
            self.laser_table,
            self.power_meter_table
        ]

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

    def _execute_return(self, query: str, force_commit: bool = False) -> list:
        """
        Executes the SQL query, writes to database if timer is reached and returns result.

        :param query: SQL query to be executed
        :param force_commit: forces a commit
        :return: list of results
        """

        if self.connection is None or self.cursor is None:
            GlobalConf.logger.error(f'DB: connection or cursor is None')
            return

        self._execute(query, force_commit)
        return self.cursor.fetchall()

    def _commit(self):
        """Commits to database"""

        if self.connection is None or self.cursor is None:
            GlobalConf.logger.error(f'DB: connection or cursor is None')
            return

        self.connection.commit()
        self.new_commit_time = datetime.now() + timedelta(self.commit_time_interval)

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

        for table in self.tables:
            try:
                self._execute(table.exists())
            except OperationalError:
                GlobalConf.logger.info(f'DB: Table "{table.name}" did not exist, will create it...')
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

    def _getData(self, table_idx: int, last_seconds: int | None) -> bool | list[np.ndarray]:
        """Get values from table with table_idx"""

        results = self._execute_return(self.tables[table_idx].get(last_seconds))
        if not results:
            return False
        lists = []
        for _ in range(len(results[0])):
            lists.append([])
        for result in results:
            for i, res in enumerate(result):
                lists[i].append(res)
        for i in range(len(results[0])):
            lists[i] = np.array(lists[i])
        return lists

    def insertPressure(
        self,
        pitbul: float,
        lsd: float,
        prevac: float
    ):
        """
        Inserts pressure values

        :param pitbul: pressure for PITBUL in [mbar]
        :param lsd: pressure for LSD in [mbar]
        :param prevac: pressure for prevacuum in [mbar]
        """

        self._execute(self.pressure_table.insert(pitbul, lsd, prevac))

    def getPressure(self, last_seconds: int | None = default_last_seconds) -> bool | list[np.ndarray]:
        """
        Get pressure values

        :returns: list of np.ndarrays[
            times,
            PITBUL pressures in [mbar],
            LSD pressures in [mbar],
            prevacuum pressures in [mbar]
        ]
        """

        return self._getData(self.tables.index(self.pressure_table), last_seconds)

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

    def getPSU(self, last_seconds: int | None = default_last_seconds) -> bool | list[np.ndarray]:
        """
        Get PSU values

        :returns: list of np.ndarrays[
            times,
            channel 0 measured voltages in [V],
            channel 0 measured currents in [A],
            channel 1 measured voltages in [V],
            channel 1 measured currents in [A],
            channel 2 measured voltages in [V],
            channel 2 measured currents in [A],
            channel 3 measured voltages in [V],
            channel 3 measured currents in [A]
        ]
        """

        return self._getData(self.tables.index(self.psu_table), last_seconds)

    def insertLaser(
        self,
        s: bool | int,
        pc: bool | int,
        l: int,
        cht: float,
        chst: float,
        bt: float,
        chf: float,
        mrr: float,
        pw: int,
        rrd: int,
        sb: int,
        rl: float
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
        :param mrr: amplifier repetition rate in [kHz]
        :param pw: pulse width in [fs]
        :param rrd: repetition rate divisor
        :param sb: number of seeder bursts
        :param rl: RF level in [%]
        """

        self._execute(self.laser_table.insert(int(s), int(pc), l, cht, chst, bt, chf, mrr, pw, rrd, sb, rl))

    def getLaser(self, last_seconds: int | None = default_last_seconds) -> bool | list[np.ndarray]:
        """
        Get Laser values

        :returns: list of np.ndarrays[
            times,
            shutter ons,
            pulsing ons,
            system stati,
            chiller temperatures in [°C],
            chiller set temperatures in [°C],
            baseplate temperatures in [°C],
            chiller flowrates in [lpm],
            amplifier repetition rates in [kHz],
            pulse widths in [fs],
            repetition rate divisors,
            numbers of seeder bursts,
            RF levels in [%]
        ]
        """

        return self._getData(self.tables.index(self.laser_table), last_seconds)

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

    def getPowerMeter(self, last_seconds: int | None = default_last_seconds) -> bool | list[np.ndarray]:
        """
        Get Power Meter values

        :returns: list of np.ndarrays[
            times
            powers in [W]
            powers in [dBm]
            currents in [A]
            irradiances in [W/cm²]
            beam diameters in [mm]
            attenuations in [dBm]
            counts of averaging events
            wavelengths in [nm]
        ]
        """

        return self._getData(self.tables.index(self.power_meter_table), last_seconds)

    def close(self):
        """Must be called on close"""
        if self.connection is None or self.cursor is None:
            GlobalConf.logger.error(f'DB: connection or cursor is None')
            return

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
