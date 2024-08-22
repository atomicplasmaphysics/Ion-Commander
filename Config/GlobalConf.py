import logging

from PyQt6.QtCore import QSettings


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

    # power meter
    power_meter_display_parameter_name = 'power_meter_display_parameter'

    # timer parameters
    update_timer_time = 1000
    ramp_timer_time = 10000

    @staticmethod
    def updateWindowSize(width: int, height: int):
        """Updates and saves settings object with window parameters"""
        GlobalConf.settings.setValue(GlobalConf.window_width_name, width)
        GlobalConf.settings.setValue(GlobalConf.window_height_name, height)

        GlobalConf.settings.sync()

    @staticmethod
    def getWindowSize() -> tuple[int, int]:
        """Returns (width, height) of window"""
        return (GlobalConf.settings.value(GlobalConf.window_width_name, defaultValue=-1, type=int),
                GlobalConf.settings.value(GlobalConf.window_height_name, defaultValue=-1, type=int))

    @staticmethod
    def updateWindowCenter(x: int, y: int):
        """Updates and saves settings object with window center parameters"""
        GlobalConf.settings.setValue(GlobalConf.window_center_x_name, x)
        GlobalConf.settings.setValue(GlobalConf.window_center_y_name, y)

        GlobalConf.settings.sync()

    @staticmethod
    def getWindowCenter() -> tuple[int, int]:
        """Returns (x, y) of window center"""
        # TODO: check if coordinates even exist on screen, if not, than return center of the screen
        # TODO: should also be implemented in the BCA-GUIDE
        return (GlobalConf.settings.value(GlobalConf.window_center_x_name, defaultValue=0, type=int),
                GlobalConf.settings.value(GlobalConf.window_center_y_name, defaultValue=0, type=int))

    @staticmethod
    def updateConnections(
        psu: str = None,
        ebis: str = None,
        pressure: str = None,
        laser: tuple[int, int, int, int, int] = None,
        power_meter: str = None
    ):
        """
        Updates and saves settings object with connection parameters

        :param psu: port of PSU
        :param ebis: port of EBIS
        :param pressure: port of pressure ADC
        :param laser: tuple of (laser_ip1, laser_ip2, laser_ip3, laser_ip4, laser_port)
        :param power_meter: port of power meter
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
        if connection_type == 'power_meter':
            return GlobalConf.settings.value(GlobalConf.connection_power_meter_port_name, defaultValue='', type=str)

    @staticmethod
    def updatePowerMeterDisplayParameter(display_parameter: int):
        """Updates and saves settings object with power meter display parameter"""
        GlobalConf.settings.setValue(GlobalConf.power_meter_display_parameter_name, display_parameter)
        GlobalConf.settings.sync()

    @staticmethod
    def getPowerMeterDisplayParameter() -> int:
        """Returns power meter display parameter"""
        return GlobalConf.settings.value(GlobalConf.power_meter_display_parameter_name, defaultValue=0, type=int)
