import logging
import logging.config
import logging.handlers
import json
from pathlib import Path
from os import mkdir


from Config.GlobalConf import GlobalConf


class CustomFormatter(logging.Formatter):
    """
    Formats the logging output and also applies colors
    """

    blue = '\x1b[34;20m'
    yellow = '\x1b[33;20m'
    green = '\x1b[32;20m'
    red = '\x1b[31;20m'
    bold_red = '\x1b[31;1m'
    reset = '\x1b[0m'
    format = '%(asctime)s - %(levelname)-8s - %(message)s (%(filename)s:%(lineno)d)'

    FORMATS = {
        logging.DEBUG: blue + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        """Returns formatted record"""

        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def setupLogging(level: int = logging.WARNING):
    """
    Set up logging

    :param level: logging level
    """

    root_path = Path(__file__).parents[1]
    print(root_path)

    try:
        mkdir(root_path / 'logs')
    except FileExistsError:
        pass

    with open(root_path / 'Utility' / 'log_config.json', 'r') as log_file:
        config = json.load(log_file)
    config['handlers']['console']['level'] = logging.getLevelName(level)
    config['handlers']['file']['filename'] = str(root_path / 'logs' / f'{GlobalConf.title.replace(" ", "_")}.log')
    logging.config.dictConfig(config)


def main():
    """
    Simple routine to generate some generic log messages of different levels
    """

    setupLogging(logging.DEBUG)
    logger = logging.getLogger(GlobalConf.title)

    logger.debug('debug message')
    logger.info('info message')
    logger.warning('warning message')
    logger.error('error message')
    logger.critical('critical message')

    try:
        1/0
    except ZeroDivisionError:
        logger.exception('exception message')


if __name__ == '__main__':
    main()
