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

    # PSU parameters
    psu_voltage_deviation = 5
    psu_voltage_maximum = 6000
    psu_current_maximum = 1E-4
    psu_time_ramp_default = 15

    # EBIS parameters
    ebis_voltage_deviation = 5
    ebis_voltage_maximum = 10000
    ebis_current_maximum = 1E-4
    ebis_current_deviation = 0.05

    # laser parameters
    laser_ip = (169, 254, 21, 151)
    laser_port = 23
    laser_chiller_temperature_low = 12
    laser_chiller_temperature_high = 33
    laser_chiller_flow_low = 4.7
    laser_chiller_flow_high = 5.3
    laser_baseplate_temperature_off = 27.5
    laser_baseplate_temperature_on = 28

    # power meter parameters
    TLPMx_encoding = 'utf-8'

    # database parameters
    db_folder = 'DB'
    db_file = 'Laserlab.db'

    # logging parameters
    logging_folder = 'log'
    logging_log_folder = 'logs'
    logging_json_file = 'log_config.json'

    # tip parameters
    tip_folder = 'Tips'
    tip_extension = 'html'
    tip_file_folder = 'entries'
    tip_encoding = 'utf-8'


class GlobalConf:
    """
    Class storing global configurations
    """

    # title
    title = 'Ion Commander'

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

    # power meter parameters
    power_meter_display_parameter_name = 'power_meter_display_parameter'

    # simulation parameters
    simulation_paths_parameter_name = 'simulation_paths_parameter'

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
        # TODO: should also be implemented in the BCA-GUIDE
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
        laser: tuple[int, int, int, int, int] = None
    ):
        """
        Updates and saves settings object with connection parameters

        :param psu: port of PSU
        :param ebis: port of EBIS
        :param pressure: port of pressure ADC
        :param laser: tuple of (laser_ip1, laser_ip2, laser_ip3, laser_ip4, laser_port)
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
        if connection_type == 'laser':
            return (GlobalConf.settings.value(GlobalConf.connection_laser_ip1_name, defaultValue=-1, type=int),
                    GlobalConf.settings.value(GlobalConf.connection_laser_ip2_name, defaultValue=-1, type=int),
                    GlobalConf.settings.value(GlobalConf.connection_laser_ip3_name, defaultValue=-1, type=int),
                    GlobalConf.settings.value(GlobalConf.connection_laser_ip4_name, defaultValue=-1, type=int),
                    GlobalConf.settings.value(GlobalConf.connection_laser_port_name, defaultValue=-1, type=int))

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
