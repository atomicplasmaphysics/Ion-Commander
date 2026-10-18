# Ion Commander
Quick and dirty python code for commanding our Ions in the LaserLab 💡⚔

## Installation
The GUI needs [Python ≥ 3.11](https://www.python.org/downloads/) with following packages installed:

```
Package     min. Version
----------- ------------
PyQt6       6.5.2
pyqtgraph   0.13.3
numpy       1.24.3
scipy       1.10.1
matplotlib  3.8.3
pyserial    3.5
duckdb      1.3.2
```

To execute the GUI, download all files from this repository and execute the `main.py` file from the console.
```bash
>> python3 main.py
```

### Alternative Installation
If one wishes to execute the GUI without calling it from the console, [PyInstaller](https://pyinstaller.org/en/stable/) can be used to compile all needed python files into one executable.
After executing the `compile\pyinstaller.py` file (same packages and package PyInstaller are needed), a `Ion Commander.exe` will be created in the main folder.
For further information read the description of the `compile\pyinstaller.py` file.

## Manual
You are a big boy 🐶, there is no manual needed, you can figure it out yourself.
Maybe get some popcorn while figuring it out 🍿

## TODOs
- [x] Make LogNorm stuff working
- [x] Better fitting routine and better starting parameters
- [x] Make the current Data-Analysis application as a subtab
- [x] Build a control subtab (Pressure, Voltage, Laser)
- [x] Logg everything in the control-tab
- [ ] Build a measure subtab (for TAC)
- [ ] Build a measure subtab (for TDC)
- [ ] Build a measure subtab (for NDIGO - if NDIGO is built)
- [x] Build a laser subtab
- [x] Make better logo and splash screen
- [ ] Start TDC software automatic with a button press and safe it automatically
- [x] No focus on any button (especially not the "connect"/"disconnect" button on popped out panels)

### Safety (EBIS interlock)
- [ ] Make the pressure interlock fail-safe: if the pressure gauge is disconnected or not updating (pressure is reset to `0`), lower the heating current instead of silently passing
- [ ] Add a watchdog for stale readings (timestamp of last successful read per device), shown in the GUI; shut down if there is no valid reading for too long
- [ ] Show interlock state (armed / tripped soft / tripped hard) and log every trip to the database
- [ ] Persist interlock limits in `QSettings` and keep them in one unit (no `10^-8 mbar` spinbox workaround - e.g. a scientific-notation spinbox)
- [ ] Optionally also check the other gauges (not only the selected one)
- [ ] Interlock self-test button (simulate a trip without hardware) and a "reset/re-arm" confirmation
- [ ] Ramp the heating current down/up slowly instead of jumping (cathode lifetime)

### Hardware / Devices
- [ ] Integrate the Adjustable Delay Stage (`Threaded` wrapper, `DeviceWrapper`, GUI panel, CommandServer entry, DB logging, position in mm/ps instead of steps)
- [ ] Implement Keithley PicoAmp meter in the Monitor tab (driver already exists)
- [ ] Keithley PicoAmp meter: set instrument back to local mode on close (`KeithleyPAmeter.py`)
- [ ] Keithley PicoAmp meter: check return values of `setCurrentRange`/`getLastData` (`KeithleyPAmeter.py`)
- [ ] Implement camera in the Monitor tab
- [ ] EBIS: use a `DeviceWrapper` like the PSU so it can be controlled via CommandServer/Scripts
- [ ] Add EBIS to the CommandServer
- [ ] Automatic reconnect on lost connection and remember/auto-connect last used ports on startup
- [ ] Monaco: cleaner return types for faults/IP/help (see TODOs in `Monaco.py`)
- [ ] Monaco: parse `?DATA` (datalogger) output
- [ ] ISEG: implement MICC user calibration commands
- [ ] Include the device name in error messages of `ThreadedConnection.handleError`
- [ ] Get limits, units and decimals of PSU/EBIS spinboxes right, and move the input ranges to `DefaultParams`
- [ ] EBIS heating current: enable button directly at the current row (currently blocked by the warning message box on `editingFinished`)
- [ ] PSU: decide if all other channels must be switched on again after a polarity switch
- [ ] Laser: verify units of the chiller pressure and the RF level / output frequency calculation (see TODOs in `Laser.py`)
- [ ] Laser: catch more socket errors on connect
- [ ] Power meter: handle values outside of the valid range

### Scripts / CommandServer
- [ ] Add message framing to the socket protocol (e.g. newline-terminated), so multiple commands sent quickly are not merged into one `recv`
- [ ] Add a timeout for answers in the ScriptServer, so a non-answering device does not block the script forever
- [ ] Support reading values in scripts (conditions, wait-until e.g. `WAIT_UNTIL PRESSURE < 1E-8`) and variables/ranges (`linspace`) for scans
- [ ] Syntax check / dry-run of scripts before starting, with highlighting of the faulty line
- [ ] Progress bar with timer until the next command (see TODO in `Scripts.py`)
- [ ] Allow multiple commands at each timestep (see TODO in `ScriptServer.py`)
- [ ] Write a short documentation of the script language and the CommandServer protocol (plus a small python client example)
- [ ] Optional access control for the CommandServer (it currently accepts every local client and can switch high voltages)

### Measurement / Analysis
- [ ] Combine Scripts + Delay Stage + TDC into automated pump-probe scans (move stage, acquire, save with metadata)
- [ ] Save measurement metadata (laser, PSU/EBIS voltages, pressure) automatically next to measured files
- [ ] Improve LogNorm fitting and finish `FitLogNormRange` (see TODOs in `Fitting.py`)
- [ ] Better limiting of fit parameters (`Fitting.py`)
- [ ] Check for sane numbers (no `inf`/`nan`) in `Functions.py`
- [ ] LMF reader: read more header parameters and full event data (see TODOs in `LMFConvert.py`)
- [ ] Export of fit results (CSV) and plots (PNG/PDF) in the Analyse tab
- [ ] Mass axis calibration in the Analyse tab using the Simulation calculators

### History / Database
- [ ] Downsample data for long time ranges in the History tab (faster plots), but show the full density when zooming in
- [ ] Show the database size
- [ ] Rename-proof logging: stable column ids plus a label table, so renaming e.g. a pressure gauge does not break the history
- [ ] Event log table (connect/disconnect, interlock trips, script start/end) and mark these events in the History plots
- [ ] Database maintenance: archive or thin out old data (e.g. keep 1 s data for 30 days, 1 min averages afterwards)
- [ ] Make the splitter of the History tab work as intended (stretch factors)

### GUI
- [ ] Add tooltips to everything
- [ ] Reduce code duplication of the channel rows in `PSU.py`/`EBIS.py` (one channel widget class)
- [ ] Settings dialog for `DefaultParams` (update interval, limits, laser IP, server port) instead of editing the code
- [ ] Show CommandServer status (running, connected clients) in the status bar
- [ ] Start CoboldPC from the GUI
- [ ] Remember popped out panels and their positions (move back to default if they would appear outside of the screen)
- [ ] Window geometry handling should also be implemented in the BCA-GUIDE (see `GlobalConf.py`)

### Code quality / Project
- [x] Single source for the version number (`GlobalConf.version`)
- [x] Add `__pycache__/`, `.vs/` and `.mcp.json` to `.gitignore`
- [ ] Unit tests for things without hardware (`parseFunctionCall`, `CommandQueue.parseScript`, `convertInChannelString`, `getPrefix`, LMF reader, pressure conversions) using the virtual devices
- [ ] Replace `print` statements with the logger
- [ ] Command-line arguments (log level, virtual devices, no CommandServer)
- [ ] Write a short manual (sorry big boy 🐶)
- [ ] Automatic changelog from the commit messages


## BUGs
- [ ] Pack images in executable - otherwise not shown (icon paths are relative to the working directory - resolve them relative to the project folder)
- [ ] EBIS interlock: `hard_pmax_val`/`soft_pmax_val` start at `10` (= 10 mbar) and are only converted to `10 * 10^-8 mbar` after the spinbox was edited - the interlock is effectively off until then
- [x] `ConnectionWorker.execute` (`Threaded.py`): `work.append(work)` in the queue overflow branch should be `self.work.append(work)`
- [x] `ThreadedConnection.callback` (`Threaded.py`): after deleting a list of callback ids it raises `ValueError`, because the list is not an `int`
- [ ] Devices forget their last port if the connection was lost before closing the app (`closeEvent` only stores the port if still connected)
