import logging

from PyQt6.QtCore import QSettings, QRect
from PyQt6.QtWidgets import QApplication


class LoggerSettings(QSettings):
    """
    Class that extends the QSettings with logging messages
    """

    def __init__(self, *args, logger: logging.Logger = None, **kwargs):
        super().__init__(*args, **kwargs)
        if logger is None:
            logger = logging
        self.logger = logger

    def value(self, key, **kwargs):
        """Get value of key"""
        if key not in self.allKeys():
            default = kwargs.get('defaultValue')
            default_text = '' if default is None else f', using "{default}" as default value'
            self.logger.info(f'"{key}" not found in Settings{default_text}')
        return super().value(key, **kwargs)


class DefaultParams:
    """
    Class storing default parameters
    """

    # timer parameters
    update_timer_time = 1000
    ramp_timer_time = 10000

    # reconnect parameters (time between attempts in ms after a lost connection)
    reconnect_interval_time = 5000
    reconnect_interval_time_laser = 15000

    # PSU parameters (input ranges of the fields: voltages in V, current limits in mA, ramp speed in %/s of the nominal voltage)
    psu_voltage_deviation = 5
    psu_voltage_maximum = 6000
    psu_voltage_decimals = 1
    psu_current_maximum = 1E-4
    psu_current_limit_minimum = 0.002
    psu_current_limit_maximum = 2.
    psu_ramp_speed_maximum = 20.
    psu_time_ramp_default = 15
    psu_time_ramp_maximum = 600

    # EBIS parameters (input ranges of the fields: voltages in V, current limits in mA, heating in A, ramp speed in %/s)
    ebis_voltage_deviation = 5
    ebis_voltage_maximum = 10000
    ebis_voltage_decimals = 1
    ebis_current_maximum = 1E-4
    ebis_current_deviation = 0.05
    ebis_current_limit_minimum = 0.002
    ebis_current_limit_maximum = 1.
    ebis_cathode_current_limit_maximum = 10.
    ebis_heating_voltage_maximum = 5.
    ebis_heating_current_maximum = 5.
    ebis_heating_ramp_maximum = 10.
    ebis_interlock_current_maximum = 3.
    ebis_ramp_speed_maximum = 20.

    # laser parameters
    laser_ip = (169, 254, 21, 151)
    laser_port = 23
    laser_chiller_temperature_low = 12
    laser_chiller_temperature_high = 33
    laser_chiller_flow_low = 4.7
    laser_chiller_flow_high = 5.3
    laser_chiller_pressure_low = 3
    laser_chiller_pressure_high = 35
    laser_baseplate_temperature_off = 27.5
    laser_baseplate_temperature_on = 28

    laser_ir_wavelength = 1035
    laser_uv_wavelength = 259

    # power meter parameters
    TLPMx_encoding = 'utf-8'

    # database parameters
    db_folder = 'DB'
    db_file_sqlite3 = 'Laserlab.db'
    db_file_duckdb = 'Laserlab.duckdb'

    # logging parameters
    logging_folder = 'log'
    logging_log_folder = 'logs'
    logging_json_file = 'log_config.json'

    # tip parameters
    tip_folder = 'Tips'
    tip_extension = 'html'
    tip_file_folder = 'entries'
    tip_encoding = 'utf-8'

    # CommandServer parameters
    cs_host = 'localhost'
    cs_port = 6969
    cs_encoding = 'utf-8'
    cs_max_connections = 10

    # CoboldPC parameters (measurement naming: {name}, {date}, {time}, {datetime}, {counter} / {counter:03d})
    cobold_folder_pattern = '{date}_{name}'
    cobold_file_pattern = '{name}_{datetime}_{counter:03d}'
    cobold_new_command = 'new hardware,{lmf},ANALYSIS'
    cobold_save_command = ''
    cobold_state_interval = 2000

    # Camera parameters
    camera_folder = 'Images'
    # interval of the live view in ms (only one image is requested at a time, so this is the maximum rate)
    camera_live_interval = 30

    # Script parameters
    script_folder = 'Scripts'
    script_extension = 'lsd'
    script_encoding = 'utf-8'

    # parameters that can be changed in the settings dialog (stored in QSettings, applied at startup)
    # name: (group, description, unit, minimum, maximum)
    editable = {
        'update_timer_time': ('General', 'Update interval of the devices and of the logging', 'ms', 100, 60000),
        'ramp_timer_time': ('General', 'Update interval of the PSU voltage ramp', 'ms', 100, 600000),
        'reconnect_interval_time': ('General', 'Time between reconnect attempts after a lost connection', 'ms', 1000, 600000),
        'reconnect_interval_time_laser': ('General', 'Time between reconnect attempts of the laser', 'ms', 1000, 600000),
        'psu_voltage_deviation': ('PSU', 'Allowed deviation of the measured voltage', 'V', 0, 1000),
        'psu_voltage_maximum': ('PSU', 'Maximum voltage of the input fields', 'V', 0, 100000),
        'psu_voltage_decimals': ('PSU', 'Decimals of the voltage input fields', '', 0, 3),
        'psu_current_maximum': ('PSU', 'Allowed current (shown in red above)', 'A', 0, 1),
        'psu_current_limit_minimum': ('PSU', 'Minimum of the current limit fields', 'mA', 0, 1000),
        'psu_current_limit_maximum': ('PSU', 'Maximum of the current limit fields', 'mA', 0, 1000),
        'psu_ramp_speed_maximum': ('PSU', 'Maximum ramp speed of the ISEG crate (% of the nominal voltage per second)', '%/s', 0, 100),
        'psu_time_ramp_default': ('PSU', 'Default duration of the voltage ramp', 'min', 0, 600),
        'psu_time_ramp_maximum': ('PSU', 'Maximum duration of the voltage ramp', 'min', 1, 10000),
        'ebis_voltage_deviation': ('EBIS', 'Allowed deviation of the measured voltage', 'V', 0, 1000),
        'ebis_voltage_maximum': ('EBIS', 'Maximum voltage of the input fields', 'V', 0, 100000),
        'ebis_voltage_decimals': ('EBIS', 'Decimals of the voltage input fields', '', 0, 3),
        'ebis_current_maximum': ('EBIS', 'Allowed current (shown in red above)', 'A', 0, 1),
        'ebis_current_deviation': ('EBIS', 'Allowed deviation of the heating current', 'A', 0, 10),
        'ebis_current_limit_minimum': ('EBIS', 'Minimum of the current limit fields', 'mA', 0, 1000),
        'ebis_current_limit_maximum': ('EBIS', 'Maximum of the current limit fields (drift tubes, repeller)', 'mA', 0, 1000),
        'ebis_cathode_current_limit_maximum': ('EBIS', 'Maximum of the current limit field of the cathode', 'mA', 0, 1000),
        'ebis_heating_voltage_maximum': ('EBIS', 'Maximum of the cathode heating voltage field', 'V', 0, 100),
        'ebis_heating_current_maximum': ('EBIS', 'Maximum of the cathode heating current field', 'A', 0, 100),
        'ebis_heating_ramp_maximum': ('EBIS', 'Maximum speed of the heating current ramp', 'A/min', 0, 100),
        'ebis_interlock_current_maximum': ('EBIS', 'Maximum of the heating current fields of the pressure interlock', 'A', 0, 100),
        'ebis_ramp_speed_maximum': ('EBIS', 'Maximum ramp speed of the MICC (% of the nominal voltage per second)', '%/s', 0, 100),
        'laser_ip': ('Laser', 'Default IP address of the laser', '', None, None),
        'laser_port': ('Laser', 'Default port of the laser', '', 1, 65535),
        'laser_chiller_temperature_low': ('Laser', 'Lower limit of the chiller temperature', '°C', -50, 100),
        'laser_chiller_temperature_high': ('Laser', 'Upper limit of the chiller temperature', '°C', -50, 100),
        'laser_chiller_flow_low': ('Laser', 'Lower limit of the chiller flow', 'lpm', 0, 100),
        'laser_chiller_flow_high': ('Laser', 'Upper limit of the chiller flow', 'lpm', 0, 100),
        'laser_chiller_pressure_low': ('Laser', 'Lower limit of the chiller pressure', '', 0, 1000),
        'laser_chiller_pressure_high': ('Laser', 'Upper limit of the chiller pressure', '', 0, 1000),
        'laser_baseplate_temperature_off': ('Laser', 'Baseplate temperature limit (off)', '°C', -50, 100),
        'laser_baseplate_temperature_on': ('Laser', 'Baseplate temperature limit (on)', '°C', -50, 100),
        'laser_ir_wavelength': ('Laser', 'IR wavelength', 'nm', 1, 100000),
        'laser_uv_wavelength': ('Laser', 'UV wavelength', 'nm', 1, 100000),
        'cs_host': ('CommandServer', 'Host of the CommandServer', '', None, None),
        'cs_port': ('CommandServer', 'Port of the CommandServer', '', 1, 65535),
        'cs_max_connections': ('CommandServer', 'Maximum number of simultaneous clients', '', 1, 1000),
        'cobold_folder_pattern': ('CoboldPC', 'Folder of a measurement ({name}, {date}, {time}, {datetime}, {counter:03d})', '', None, None),
        'cobold_file_pattern': ('CoboldPC', 'File name of a measurement (.lmf is added)', '', None, None),
        'cobold_new_command': ('CoboldPC', 'CoboldPC command to prepare a measurement ({lmf}, {comment})', '', None, None),
        'cobold_save_command': ('CoboldPC', 'Optional CoboldPC command after stopping ({dcf}, {lmf}), empty: none', '', None, None),
    }

    # string parameters that may be empty
    allow_empty = {'cobold_save_command'}

    # original values of the editable parameters (filled by <loadOverrides>)
    original = {}

    @classmethod
    def convert(cls, name: str, value):
        """
        Converts a value (e.g. a string from QSettings) to the type of the default value and checks the range.
        Raises ValueError if it is not valid.

        :param name: name of parameter
        :param value: new value
        """

        default = cls.original.get(name, getattr(cls, name))
        _, _, _, minimum, maximum = cls.editable[name]

        if isinstance(default, tuple):
            parts = value if isinstance(value, (tuple, list)) else str(value).replace(',', '.').split('.')
            converted = tuple(int(part) for part in parts)
            if len(converted) != len(default) or not all(0 <= part <= 255 for part in converted):
                raise ValueError(f'{name}: "{value}" is not a valid IP address')
            return converted

        if isinstance(default, bool):
            return str(value).lower() in ['1', 'true', 'yes']

        if isinstance(default, (int, float)):
            converted = type(default)(float(value)) if isinstance(default, int) else float(value)
            if (minimum is not None and converted < minimum) or (maximum is not None and converted > maximum):
                raise ValueError(f'{name}: {converted} is not in the range [{minimum}, {maximum}]')
            return converted

        converted = str(value).strip()
        if not converted and name not in cls.allow_empty:
            raise ValueError(f'{name}: empty value is not allowed')
        return converted

    @classmethod
    def toString(cls, value) -> str:
        """Converts a value to a string for the settings/dialog"""

        if isinstance(value, tuple):
            return '.'.join(str(part) for part in value)
        return str(value)

    @classmethod
    def loadOverrides(cls, settings: QSettings, group: str = 'default_params'):
        """
        Applies the values stored in the settings (invalid values are ignored and logged)

        :param settings: settings object
        :param group: group in the settings
        """

        for name in cls.editable:
            cls.original.setdefault(name, getattr(cls, name))

        settings.beginGroup(group)
        keys = settings.childKeys()
        settings.endGroup()

        for name in keys:
            if name not in cls.editable:
                continue
            try:
                setattr(cls, name, cls.convert(name, settings.value(f'{group}/{name}', type=str)))
            except (TypeError, ValueError) as error:
                logging.getLogger('Ion Commander').error(f'Stored parameter is invalid and ignored: {error}')

    @classmethod
    def saveOverrides(cls, settings: QSettings, values: dict[str, str], group: str = 'default_params'):
        """
        Stores the values that differ from the original values (takes effect after restarting the application)

        :param settings: settings object
        :param values: dictionary of {name: value}, values are converted and checked (ValueError if invalid)
        :param group: group in the settings
        """

        converted = {name: cls.convert(name, value) for name, value in values.items() if name in cls.editable}

        settings.remove(group)
        for name, value in converted.items():
            if value != cls.original.get(name, getattr(cls, name)):
                settings.setValue(f'{group}/{name}', cls.toString(value))
        settings.sync()


class GlobalConf:
    """
    Class storing global configurations
    """

    # title
    title = 'Ion Commander'

    # version (single source of truth - update only here)
    version = '0.1.79'

    # logger
    logger = logging.getLogger(title)

    # settings object
    settings = LoggerSettings(f'TU Wien {title}', title, logger=logger)

    # window parameters
    window_width_name = 'window_width'
    window_height_name = 'window_height'
    window_center_x_name = 'window_center_x'
    window_center_y_name = 'window_center_y'
    window_maximized_value = int(1E9)

    # connection parameters
    connection_psu_port_name = 'connection_psu_port'
    connection_ebis_port_name = 'connection_ebis_port'
    connection_pressure_port_name = 'connection_pressure_port'
    connection_laser_ip1_name = 'connection_laser_ip1'
    connection_laser_ip2_name = 'connection_laser_ip2'
    connection_laser_ip3_name = 'connection_laser_ip3'
    connection_laser_ip4_name = 'connection_laser_ip4'
    connection_laser_port_name = 'connection_laser_port'
    connection_power_meter_port_name = 'connection_power_meter_port'
    connection_camera_name = 'connection_camera'
    connection_electrometer_name = 'connection_electrometer'
    cobold_measurement_folder_name = 'cobold_measurement_folder'

    # popped out panels
    popout_group_name = 'popouts'

    # EBIS interlock parameters
    ebis_interlock_group_name = 'ebis_interlock'
    ebis_heating_ramp_name = 'ebis_heating_ramp'
    ebis_interlock_gauge_name = 'ebis_interlock_gauge'

    # power meter parameters
    power_meter_display_parameter_name = 'power_meter_display_parameter'

    # simulation parameters
    simulation_paths_parameter_name = 'simulation_paths_parameter'

    # parameters changed in the settings dialog
    default_params_group_name = 'default_params'

    @staticmethod
    def updateWindowSizeCenter(width: int, height: int, center_x: int, center_y: int):
        """Updates and saves settings object with window parameters"""
        GlobalConf.settings.setValue(GlobalConf.window_width_name, width)
        GlobalConf.settings.setValue(GlobalConf.window_height_name, height)
        GlobalConf.settings.setValue(GlobalConf.window_center_x_name, center_x)
        GlobalConf.settings.setValue(GlobalConf.window_center_y_name, center_y)

        GlobalConf.settings.sync()

    @staticmethod
    def getWindowSizeCenter() -> tuple[int, int, int, int]:
        """
        Returns (width, height, center_x, center_y) of window.
        Returns (GlobalConf.window_maximized_value, GlobalConf.window_maximized_value) for width and height if should be maximized.
        """
        width = GlobalConf.settings.value(GlobalConf.window_width_name, defaultValue=GlobalConf.window_maximized_value, type=int)
        height = GlobalConf.settings.value(GlobalConf.window_height_name, defaultValue=GlobalConf.window_maximized_value, type=int)
        center_x = GlobalConf.settings.value(GlobalConf.window_center_x_name, defaultValue=0, type=int)
        center_y = GlobalConf.settings.value(GlobalConf.window_center_y_name, defaultValue=0, type=int)

        test_width = width if width != GlobalConf.window_maximized_value else 100
        test_height = height if height != GlobalConf.window_maximized_value else 100
        window_geometry = QRect(int(center_x - test_width / 2), int(center_y - test_height / 2), test_width, test_height)
        for screen in QApplication.screens():
            geometry = screen.geometry()
            if geometry.intersects(window_geometry):
                if geometry.width() < width:
                    width = geometry.width()
                    if geometry.height() < height:
                        width = GlobalConf.window_maximized_value
                        height = GlobalConf.window_maximized_value
                elif geometry.height() < height:
                    height = geometry.height()
                return width, height, center_x, center_y

        geometry = QApplication.primaryScreen().availableVirtualGeometry()
        return (GlobalConf.window_maximized_value, GlobalConf.window_maximized_value,
                int(geometry.x() + geometry.width() / 2), int(geometry.y() + geometry.height() / 2))

    @staticmethod
    def updateConnections(
        psu: str = None,
        ebis: str = None,
        pressure: str = None,
        laser: tuple[int, int, int, int, int] | list[int] = None,
        power_meter: str = None,
        camera: str = None,
        electrometer: str = None
    ):
        """
        Updates and saves settings object with connection parameters

        :param psu: port of PSU
        :param ebis: port of EBIS
        :param pressure: port of pressure ADC
        :param laser: tuple of (laser_ip1, laser_ip2, laser_ip3, laser_ip4, laser_port)
        :param power_meter: resource name of power meter
        """

        if psu is not None:
            GlobalConf.settings.setValue(GlobalConf.connection_psu_port_name, psu)
        if ebis is not None:
            GlobalConf.settings.setValue(GlobalConf.connection_ebis_port_name, ebis)
        if pressure is not None:
            GlobalConf.settings.setValue(GlobalConf.connection_pressure_port_name, pressure)
        if laser is not None:
            GlobalConf.settings.setValue(GlobalConf.connection_laser_ip1_name, laser[0])
            GlobalConf.settings.setValue(GlobalConf.connection_laser_ip2_name, laser[1])
            GlobalConf.settings.setValue(GlobalConf.connection_laser_ip3_name, laser[2])
            GlobalConf.settings.setValue(GlobalConf.connection_laser_ip4_name, laser[3])
            GlobalConf.settings.setValue(GlobalConf.connection_laser_port_name, laser[4])
        if power_meter is not None:
            GlobalConf.settings.setValue(GlobalConf.connection_power_meter_port_name, power_meter)
        if camera is not None:
            GlobalConf.settings.setValue(GlobalConf.connection_camera_name, camera)
        if electrometer is not None:
            GlobalConf.settings.setValue(GlobalConf.connection_electrometer_name, electrometer)

        GlobalConf.settings.sync()

    @staticmethod
    def getConnection(connection_type: str) -> str | tuple[int, int, int, int, int]:
        """Returns connection for connection_type"""
        connection_type = connection_type.lower()
        if connection_type == 'psu':
            return GlobalConf.settings.value(GlobalConf.connection_psu_port_name, defaultValue='', type=str)
        if connection_type == 'ebis':
            return GlobalConf.settings.value(GlobalConf.connection_ebis_port_name, defaultValue='', type=str)
        if connection_type == 'pressure':
            return GlobalConf.settings.value(GlobalConf.connection_pressure_port_name, defaultValue='', type=str)
        if connection_type == 'power_meter':
            return GlobalConf.settings.value(GlobalConf.connection_power_meter_port_name, defaultValue='', type=str)
        if connection_type == 'camera':
            return GlobalConf.settings.value(GlobalConf.connection_camera_name, defaultValue='', type=str)
        if connection_type == 'electrometer':
            return GlobalConf.settings.value(GlobalConf.connection_electrometer_name, defaultValue='', type=str)
        if connection_type == 'laser':
            return (GlobalConf.settings.value(GlobalConf.connection_laser_ip1_name, defaultValue=-1, type=int),
                    GlobalConf.settings.value(GlobalConf.connection_laser_ip2_name, defaultValue=-1, type=int),
                    GlobalConf.settings.value(GlobalConf.connection_laser_ip3_name, defaultValue=-1, type=int),
                    GlobalConf.settings.value(GlobalConf.connection_laser_ip4_name, defaultValue=-1, type=int),
                    GlobalConf.settings.value(GlobalConf.connection_laser_port_name, defaultValue=-1, type=int))
        raise NotImplementedError(f'Connection type {connection_type} not implemented')

    @staticmethod
    def updatePopouts(popouts: dict[str, tuple[int, int, int, int] | None]):
        """
        Updates and saves settings object with the popped out panels

        :param popouts: dictionary of {panel title: geometry (x, y, width, height) or None if not popped out}
        """

        GlobalConf.settings.remove(GlobalConf.popout_group_name)
        for title, geometry in popouts.items():
            if geometry is not None:
                GlobalConf.settings.setValue(f'{GlobalConf.popout_group_name}/{title}', ','.join(str(value) for value in geometry))
        GlobalConf.settings.sync()

    @staticmethod
    def getPopouts() -> dict[str, tuple[int, int, int, int] | None]:
        """Returns the popped out panels as {panel title: geometry (x, y, width, height) or None if invalid}"""

        GlobalConf.settings.beginGroup(GlobalConf.popout_group_name)
        keys = GlobalConf.settings.childKeys()
        GlobalConf.settings.endGroup()

        popouts = {}
        for key in keys:
            value = GlobalConf.settings.value(f'{GlobalConf.popout_group_name}/{key}', defaultValue='', type=str)
            try:
                geometry = tuple(int(part) for part in value.split(','))
            except ValueError:
                geometry = None
            popouts[key] = geometry if geometry is not None and len(geometry) == 4 else None
        return popouts

    @staticmethod
    def updateEBISInterlock(limits: dict[str, float] = None, gauge: str = None):
        """
        Updates and saves settings object with the EBIS pressure interlock parameters

        :param limits: dictionary of interlock limits (see <InterlockLimits>), all pressures in mbar
        :param gauge: name of the selected pressure gauge
        """

        if limits is not None:
            for key, value in limits.items():
                GlobalConf.settings.setValue(f'{GlobalConf.ebis_interlock_group_name}/{key}', float(value))
        if gauge is not None:
            GlobalConf.settings.setValue(GlobalConf.ebis_interlock_gauge_name, gauge)

        GlobalConf.settings.sync()

    @staticmethod
    def getEBISInterlock() -> tuple[dict[str, float], str]:
        """Returns (dictionary of stored interlock limits, name of pressure gauge); missing limits are not in the dictionary"""

        limits = {}
        GlobalConf.settings.beginGroup(GlobalConf.ebis_interlock_group_name)
        keys = GlobalConf.settings.childKeys()
        GlobalConf.settings.endGroup()
        for key in keys:
            limits[key] = GlobalConf.settings.value(f'{GlobalConf.ebis_interlock_group_name}/{key}', defaultValue=-1, type=float)

        gauge = GlobalConf.settings.value(GlobalConf.ebis_interlock_gauge_name, defaultValue='', type=str)
        return limits, gauge

    @staticmethod
    def updatePowerMeterDisplayParameter(display_parameter: int):
        """Updates and saves settings object with power meter display parameter"""
        GlobalConf.settings.setValue(GlobalConf.power_meter_display_parameter_name, display_parameter)
        GlobalConf.settings.sync()

    @staticmethod
    def getPowerMeterDisplayParameter() -> int:
        """Returns power meter display parameter"""
        return GlobalConf.settings.value(GlobalConf.power_meter_display_parameter_name, defaultValue=0, type=int)

    @staticmethod
    def updateSimulationPathsParameter(simulation_paths: list[str]):
        """Updates and saves settings object with simulation paths parameter"""
        GlobalConf.settings.setValue(GlobalConf.simulation_paths_parameter_name, simulation_paths)
        GlobalConf.settings.sync()

    @staticmethod
    def getSimulationPathsParameter() -> list[str]:
        """Returns simulation paths parameter"""
        return GlobalConf.settings.value(GlobalConf.simulation_paths_parameter_name, defaultValue=[], type=list)


# apply the values of the settings dialog before any other module uses DefaultParams (e.g. as default arguments)
DefaultParams.loadOverrides(GlobalConf.settings, GlobalConf.default_params_group_name)
