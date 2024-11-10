from __future__ import annotations
from sqlite3 import connect, OperationalError, Connection, Cursor
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

    def get(self, start_time: int | None, end_time: int | None):
        """SQL query to get last seconds of data"""

        conditions = []
        if start_time is not None:
            conditions.append(f'Time >= {int(start_time)}')
        if end_time is not None:
            conditions.append(f'Time <= {int(end_time)}')
        condition = ' AND '.join(conditions)
        if condition:
            condition = f' WHERE {condition}'

        return f'''SELECT * FROM {self.name}{condition};'''


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
        'Time': '''INTEGER DEFAULT (strftime('%s', 'now'))''',
        'Shutter': 'INTEGER default 0',
        'Pulsing': 'INTEGER default 0',
        'Status': 'INTEGER default 0',
        'Chiller_Temperature': 'FLOAT default 0',
        'Chiller_Set_Temperature': 'FLOAT default 0',
        'Baseplate_Temperature': 'FLOAT default 0',
        'Chiller_Flow': 'FLOAT default 0',
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
        'Time': '''INTEGER DEFAULT (strftime('%s', 'now'))''',
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
        debug: bool = False
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
            return []

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

    def getData(self, table_idx: int, start_time: int | None = None, end_time: int | None = None) -> bool | np.ndarray:
        """Get values from table with table_idx"""

        results = self._execute_return(self.tables[table_idx].get(start_time, end_time))
        if not results:
            return False
        return np.array(results)

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

    def getPressure(self, start_time: int | None = None, end_time: int | None = None) -> bool | np.ndarray:
        """
        Get pressure values

        :returns: list of np.ndarrays[
            times,
            PITBUL pressures in [mbar],
            LSD pressures in [mbar],
            prevacuum pressures in [mbar]
        ]
        """

        return self.getData(self.tables.index(self.pressure_table), start_time, end_time)

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

    def getPSU(self, start_time: int | None = None, end_time: int | None = None) -> bool | np.ndarray:
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

        return self.getData(self.tables.index(self.psu_table), start_time, end_time)

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

    def getLaser(self, start_time: int | None = None, end_time: int | None = None) -> bool | np.ndarray:
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

        return self.getData(self.tables.index(self.laser_table), start_time, end_time)

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

    def getPowerMeter(self, start_time: int | None = None, end_time: int | None = None) -> bool | np.ndarray:
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

        return self.getData(self.tables.index(self.power_meter_table), start_time, end_time)

    def close(self):
        """Must be called on close"""
        if self.connection is None or self.cursor is None:
            GlobalConf.logger.error(f'DB: connection or cursor is None')
            return

        self.connection.commit()


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


if __name__ == '__main__':
    rename_columns()
