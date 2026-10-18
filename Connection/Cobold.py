"""
Remote control of CoboldPC (RoentDek) via CoboldPCCMD.exe, which sends a command to the command line of a running CoboldPC.

Measurement sequence (see CoboldPC help: "NewAcquisition", "StartAcquisition", "StopAcquisition"):
    new hardware,<file.lmf>,ANALYSIS    prepares an acquisition from the hardware that writes the list mode file
    start                               starts the acquisition
    stop                                stops it and closes the list mode file

CoboldPCCMD.exe -DAqState returns 1 = stopped, 2 = paused, 3 = running (-1 = unknown).
Note: CoboldPCCMD blocks if CoboldPC is not running, therefore it is only called if the CoboldPC process exists and always
with a timeout.
"""

import re
import subprocess
from datetime import datetime
from glob import glob
from pathlib import Path


from Config.GlobalConf import GlobalConf, DefaultParams


COBOLD_PATTERNS = [
    'C:/Program Files/RoentDek Handels GmbH/CoboldPC*/',
    'C:/Program Files (x86)/RoentDek Handels GmbH/CoboldPC*/',
]


class DAqState:
    """States returned by CoboldPCCMD -DAqState"""
    UNKNOWN = -1
    STOPPED = 1
    PAUSED = 2
    RUNNING = 3

    names = {UNKNOWN: 'Unknown', STOPPED: 'Stopped', PAUSED: 'Paused', RUNNING: 'Running'}


def findCoboldFolder() -> Path | None:
    """Returns the installation folder of CoboldPC (newest version) or None"""

    folders = []
    for pattern in COBOLD_PATTERNS:
        folders.extend(folder for folder in glob(pattern) if (Path(folder) / 'CoboldPCCMD.exe').exists())
    if not folders:
        return None
    return Path(sorted(folders)[-1])


def buildMeasurementPath(
    base_folder: str | Path,
    name: str,
    folder_pattern: str = DefaultParams.cobold_folder_pattern,
    file_pattern: str = DefaultParams.cobold_file_pattern,
    now: datetime | None = None
) -> Path:
    """
    Builds the path of the list mode file of a measurement from the naming patterns.
    Placeholders: {name}, {date} (2026-10-18), {time} (153000), {datetime} (20261018_153000), {counter} (1, 2, ...;
    the first number for which the file does not exist yet, format e.g. {counter:03d}).

    :param base_folder: folder of all measurements
    :param name: name of the measurement (characters that are not allowed in file names are replaced by "_")
    :param folder_pattern: pattern of the sub folder
    :param file_pattern: pattern of the file name (".lmf" is added if missing)
    :param now: time of the measurement (default: now)
    """

    if now is None:
        now = datetime.now()
    # "," is not allowed in CoboldPC file names, other characters are not allowed in Windows file names
    name = re.sub(r'[\\/:*?"<>|,]+', '_', name.strip()) or 'measurement'
    values = {
        'name': name,
        'date': now.strftime('%Y-%m-%d'),
        'time': now.strftime('%H%M%S'),
        'datetime': now.strftime('%Y%m%d_%H%M%S'),
    }

    for counter in range(1, 100000):
        folder = Path(base_folder) / folder_pattern.format(counter=counter, **values)
        file_name = file_pattern.format(counter=counter, **values)
        if not file_name.lower().endswith('.lmf'):
            file_name += '.lmf'
        path = folder / file_name
        if not path.exists():
            return path
        if '{counter' not in folder_pattern + file_pattern:
            # no counter in the patterns: never overwrite, append one
            stem = path.stem
            for extra in range(2, 100000):
                candidate = path.with_name(f'{stem}_{extra}.lmf')
                if not candidate.exists():
                    return candidate
    raise FileExistsError('No free file name found')


class CoboldConnection:
    """
    Connection to a running CoboldPC

    :param folder: installation folder of CoboldPC (default: found automatically)
    :param timeout: timeout of one command in s
    """

    def __init__(self, folder: str | Path | None = None, timeout: float = 30):
        self.folder = Path(folder) if folder else findCoboldFolder()
        self.timeout = timeout
        self.lmf_file: Path | None = None

    def __enter__(self):
        return self.open()

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.close()

    @property
    def cmd_exe(self) -> Path | None:
        """Path of CoboldPCCMD.exe"""
        return self.folder / 'CoboldPCCMD.exe' if self.folder is not None else None

    @property
    def cobold_exe(self) -> Path | None:
        """Path of CoboldPC (64 bit if available)"""

        if self.folder is None:
            return None
        for name in ('CoboldPC_x64.exe', 'CoboldPC_x86.exe', 'CoboldPC.exe'):
            if (self.folder / name).exists():
                return self.folder / name
        return None

    def open(self):
        """Checks the installation (raises ConnectionError if CoboldPC is not installed)"""

        if self.cmd_exe is None or not self.cmd_exe.exists():
            raise ConnectionError('CoboldPC (CoboldPCCMD.exe) not found, is CoboldPC installed?')
        return self

    def close(self):
        """Nothing to close (CoboldPC keeps running)"""

        pass

    def isRunning(self) -> bool:
        """Returns if a CoboldPC process is running"""

        try:
            output = subprocess.run(
                ['tasklist', '/FO', 'CSV', '/NH'],
                capture_output=True, text=True, timeout=10, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            ).stdout
        except (OSError, subprocess.SubprocessError) as error:
            raise ConnectionError(f'Could not list processes: {error}')
        return any(line.lower().startswith('"coboldpc') and not line.lower().startswith('"coboldpccmd') for line in output.splitlines())

    def startCobold(self) -> bool:
        """
        Starts CoboldPC if it is not running (it executes its Startup.ccf)

        :returns: True if it was started, False if it was already running
        """

        if self.isRunning():
            return False
        if self.cobold_exe is None:
            raise ConnectionError('CoboldPC executable not found')
        subprocess.Popen([str(self.cobold_exe)], cwd=str(self.folder))
        GlobalConf.logger.info(f'CoboldPC started: {self.cobold_exe}')
        return True

    def command(self, command: str) -> tuple[int, str]:
        """
        Sends a command to the command line of CoboldPC

        :param command: CoboldPC command (e.g. "start")
        :returns: (return code, output) of CoboldPCCMD
        """

        if not self.isRunning():
            raise ConnectionError('CoboldPC is not running')
        try:
            result = subprocess.run(
                [str(self.cmd_exe), command],
                capture_output=True, text=True, timeout=self.timeout, cwd=str(self.folder),
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            )
        except subprocess.TimeoutExpired:
            raise TimeoutError(f'CoboldPCCMD did not answer within {self.timeout} s (command "{command}")')
        except OSError as error:
            raise ConnectionError(f'CoboldPCCMD could not be executed: {error}')

        GlobalConf.logger.debug(f'CoboldPC command "{command}": return code {result.returncode}, output "{result.stdout.strip()}"')
        return result.returncode, result.stdout.strip()

    def daqState(self) -> int:
        """Returns the DAq state (see <DAqState>), DAqState.UNKNOWN if CoboldPC is not running"""

        if not self.isRunning():
            return DAqState.UNKNOWN
        return_code, output = self.command('-DAqState')
        match = re.search(r'-?\d+', output)
        state = int(match.group()) if match else return_code
        return state if state in DAqState.names else DAqState.UNKNOWN

    def startMeasurement(self, lmf_file: str | Path, comment: str = '') -> str:
        """
        Starts a measurement from the hardware that is written into the given list mode file

        :param lmf_file: list mode file (folder is created)
        :param comment: comment written into the header of the list mode file
        :returns: path of the list mode file
        """

        lmf_file = Path(lmf_file)
        if ',' in str(lmf_file):
            raise ValueError('The file name must not contain "," (CoboldPC uses it as separator)')
        lmf_file.parent.mkdir(parents=True, exist_ok=True)

        if self.daqState() in (DAqState.RUNNING, DAqState.PAUSED):
            self.command('stop')

        comment = comment.replace(',', ';').replace('\n', '\\n')
        new_command = DefaultParams.cobold_new_command.format(lmf=str(lmf_file), comment=comment)
        self.command(new_command)
        self.command('start')
        self.lmf_file = lmf_file
        GlobalConf.logger.info(f'CoboldPC measurement started: {lmf_file}')
        return str(lmf_file)

    def stopMeasurement(self) -> str:
        """
        Stops the measurement (closes the list mode file) and executes the optional save command

        :returns: path of the list mode file ('' if unknown)
        """

        self.command('stop')
        if DefaultParams.cobold_save_command and self.lmf_file is not None:
            self.command(DefaultParams.cobold_save_command.format(dcf=str(self.lmf_file.with_suffix('.dcf')), lmf=str(self.lmf_file)))
        GlobalConf.logger.info(f'CoboldPC measurement stopped: {self.lmf_file}')
        return str(self.lmf_file) if self.lmf_file is not None else ''

    def identification(self) -> str:
        """Returns the installation folder"""
        return f'CoboldPC in {self.folder}'


def test():
    """Tests the naming of measurements (CoboldPC is not called)"""

    import tempfile
    with tempfile.TemporaryDirectory() as folder:
        now = datetime(2026, 10, 18, 15, 30, 0)
        path = buildMeasurementPath(folder, 'Ar 8+, 1 keV', '{date}_{name}', '{name}_{datetime}_{counter:03d}', now)
        print(path.relative_to(folder))
        assert path.name == 'Ar 8+_ 1 keV_20261018_153000_001.lmf' and path.parent.name == '2026-10-18_Ar 8+_ 1 keV'
        path.parent.mkdir(parents=True)
        path.touch()
        second = buildMeasurementPath(folder, 'Ar 8+, 1 keV', '{date}_{name}', '{name}_{datetime}_{counter:03d}', now)
        assert second.name.endswith('_002.lmf'), second
        third = buildMeasurementPath(folder, 'Ar 8+, 1 keV', '{date}_{name}', '{name}_{datetime}_001', now)
        assert third.name.endswith('_001_2.lmf'), third
    print('Cobold folder:', findCoboldFolder())
    print('All Cobold naming tests passed')


if __name__ == '__main__':
    test()
