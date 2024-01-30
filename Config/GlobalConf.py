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

    @staticmethod
    def updateWindowSize(width, height):
        """Updates and saves settings object with window parameters"""
        GlobalConf.settings.setValue(GlobalConf.window_width_name, width)
        GlobalConf.settings.setValue(GlobalConf.window_height_name, height)

        GlobalConf.settings.sync()

    @staticmethod
    def updateWindowCenter(x, y):
        """Updates and saves settings object with window center parameters"""
        GlobalConf.settings.setValue(GlobalConf.window_center_x_name, x)
        GlobalConf.settings.setValue(GlobalConf.window_center_y_name, y)

        GlobalConf.settings.sync()

    @staticmethod
    def getWindowSize():
        """Returns (width, height) of window"""
        return (GlobalConf.settings.value(GlobalConf.window_width_name, defaultValue=-1, type=int),
                GlobalConf.settings.value(GlobalConf.window_height_name, defaultValue=-1, type=int))

    @staticmethod
    def getWindowCenter():
        """Returns (x, y) of window center"""
        # TODO: check if coordinates even exist on screen, if not, than return center of the screen
        # TODO: should also be implemented in the BCA-GUIDE
        return (GlobalConf.settings.value(GlobalConf.window_center_x_name, defaultValue=0, type=int),
                GlobalConf.settings.value(GlobalConf.window_center_y_name, defaultValue=0, type=int))
