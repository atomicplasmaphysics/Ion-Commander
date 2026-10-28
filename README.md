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

Optional (for the camera in the Monitor tab, the Spinnaker SDK/SpinView must be installed), one of:
- `spinnaker_python` (PySpin): wheel from the Teledyne website, must match the installed Spinnaker version and the Python version
- `harvesters` (`pip install harvesters`): uses the GenTL producer of the installed Spinnaker SDK (`Spinnaker_GenTL_*.cti`)

Without them only the virtual camera (simulated laser spot) is available.
With `harvesters` the Blackfly S (BFS-U3-16S2M, 1440x1080) delivers ~200 fps; the live view shows ~30 fps (`DefaultParams.camera_live_interval`).

To execute the GUI, download all files from this repository and execute the `main.py` file from the console.
```bash
>> python3 main.py
```

### Alternative Installation
If one wishes to execute the GUI without calling it from the console, [PyInstaller](https://pyinstaller.org/en/stable/) can be used to compile all needed python files into one executable.
After executing the `compile\pyinstaller.py` file (same packages and package PyInstaller are needed), a `Ion Commander.exe` will be created in the main folder.
For further information read the description of the `compile\pyinstaller.py` file.

## Scripts
Scripts (tab `Scripts`, files `Scripts/*.lsd`) send commands to the devices via the CommandServer (`DEVICE:function(arguments)`,
the functions are the ones of the classes in `Connection/`). Devices: `PSU`, `EBIS`, `LASER`, `PRESSURE`, `POWER`, `ELECTROMETER`,
`CAMERA`, `COBOLD`.
```
TIME 3                                         # first line: interval between the steps in seconds
WAIT                                           # one step without command
LASER:rfSet(%) 23, 24                          # "%" is replaced by every value -> one step per value
PSU:voltageSet(0,%);PSU:voltageSet(1,-%) 0:10:0.5  # ";" = several commands in ONE step, "start:stop:step" = range (stop included)
	WAIT                                       # tab = nested loop: executed for every value of the line above
	ELECTROMETER:readAverage(10)               # next step: mean, std and number of 10 electrometer readings
```
Basic math with `%` inside the function arguments is calculated: `-%`, `%+5`, `%-5`, `%*10`, `%/2`, `(%-1)*2`, `%**2`,
`abs(%)`, `round(%,1)`, `min(%,10)`, `max(%,0)` (e.g. with 2.5: `PSU:voltageSet(1,-%*2+1)` -> `PSU:voltageSet(1,-4)`).
No spaces inside the command (the space separates the command from the values). Arguments that are no math (e.g. `'run_%.lmf'`)
are only replaced. Wien filter scan: `PSU:voltageSet(0,%);PSU:voltageSet(1,-%) 0:50:0.5` plus an electrometer reading per step
(a negative voltage needs a channel with electronic polarity (EPU), otherwise set the polarity in the PSU panel and use `%`).

Every command and its answer is written to `Scripts/results/<script>_<date>_<time>.csv`
(columns `time_s, step, command, state, answer, value`; `value` is the first number of the answer, e.g. the current).
Example: `Scripts/PSU ramp electrometer.lsd` (symmetric ramp of two PSU channels, electrometer read after every step).

## Measurements with CoboldPC
**The tab `Measure` is disabled for now** (commented out in `Windows/Main.py`, also the CommandServer device `COBOLD`).

The tab `Measure` controls CoboldPC (RoentDek) with `CoboldPCCMD.exe`, which sends commands to the command line of the running CoboldPC:
1. Start CoboldPC (button `Start CoboldPC` - CoboldPC executes its `Startup.ccf`, which may already start an acquisition)
2. Select the measurement folder, enter name, duration (0 = until stopped) and comment
3. `Start measurement` sends `new hardware,<file>.lmf,ANALYSIS` and `start`; after the duration `stop` is sent

Folder and file names are built from patterns (Settings > Preferences > CoboldPC), default
`<folder>/{date}_{name}/{name}_{datetime}_{counter:03d}.lmf`, existing files are never overwritten.
Next to every list mode file a `.json` file with name, comment, start/stop time and the settings of all devices (PSU, EBIS,
pressures, laser, power meter) at start and stop is written. Start and stop are logged as events.
Scripts can use the device `COBOLD` of the CommandServer (e.g. `COBOLD:startMeasurement('D:/data/test.lmf')`, `COBOLD:stopMeasurement()`).

## Changelog
All changes are listed in [CHANGELOG.md](CHANGELOG.md), which is created from the commit messages with
```bash
>> python -m Utility.Changelog
```
Commit messages should start with the version (e.g. `v0.1.64 Short description`) followed by a detailed description.
The version itself is set in `GlobalConf.version`.

## Icons
Icons: [Lucide](https://lucide.dev) (ISC License, Copyright (c) Lucide Contributors 2022, portions Copyright (c) Cole Bemis 2013-2022
as part of Feather (MIT)), see `icons/LICENSE-Lucide.txt`. Logo and splash screens are our own.

## Manual
You are a big boy 🐶, there is no manual needed, you can figure it out yourself.
Maybe get some popcorn while figuring it out 🍿

## Database
All values are logged once per second into a [DuckDB](https://duckdb.org/) file (`DB/Laserlab.duckdb`).
- **Data tables** (`Pressure`, `PSU`, `Laser`, `PowerMeter`, `EBIS`): one row per second, one column per value. The column names are
  *stable ids* - never rename them, otherwise the old data does not match anymore.
- **`Labels`**: the human readable name (and unit) of every column, with the time from which it is valid. If something is renamed in the
  GUI (e.g. a pressure gauge in `PressureVBoxLayout.pressure_gauges` - only the name, not the database column), a new label row is
  written at the next start. The History tab always shows the current name and lists the previous names in the tooltip.
- **`Events`**: things that happen once (interlock trips, lost connections, ...) with source, type, message and a value.

Old data needs no migration: the data tables and their columns stay exactly the same, only the `Labels` and `Events` tables are
added. The first label of a column is stored as valid from the beginning (time 0), so it also describes all data logged before.

New tables are created automatically at startup, existing tables are never changed automatically.
Adding a new column to an existing table needs `DB.addNewColumns()` (make a copy of the database file first and close the GUI,
DuckDB allows only one process to open the file).

The size of the database is shown in the menu `Database`.

## TODOs
- [x] Make LogNorm stuff working
- [x] Better fitting routine and better starting parameters
- [x] Make the current Data-Analysis application as a subtab
- [x] Build a control subtab (Pressure, Voltage, Laser)
- [x] Logg everything in the control-tab
- [ ] Build a measure subtab (for TAC)
- [x] Build a measure subtab (for TDC) - tab `Measure` with CoboldPC
- [ ] Build a measure subtab (for NDIGO - if NDIGO is built)
- [x] Build a laser subtab
- [x] Make better logo and splash screen
- [x] Start TDC software automatic with a button press and safe it automatically (CoboldPC: start, timed measurement, naming format)
- [ ] Enable the `Measure` tab again (CoboldPC, currently commented out in `Windows/Main.py`)
- [ ] CoboldPC: test with the real TDC (only tested with a simulated CoboldPC) and check the return value of `CoboldPCCMD -DAqState`
- [ ] CoboldPC: save the Cobold document (.dcf) after a measurement (command not documented for the command line, configurable in the preferences)
- [x] No focus on any button (especially not the "connect"/"disconnect" button on popped out panels)

### Safety (EBIS interlock)
- [x] Make the pressure interlock fail-safe: if the pressure gauge is disconnected or not updating (pressure is reset to `0`), lower the heating current instead of silently passing (`Utility/Interlock.py`, tested with `python -m Utility.Interlock`)
- [x] Add a watchdog for stale readings (timestamp of last successful read per device), shown in the GUI; lower the heating current if there is no valid reading for too long ("No reading timeout")
- [x] Show interlock state (armed / tripped soft / tripped hard / tripped no reading) and log every trip to the database (`Events` table)
- [x] Persist interlock limits in `QSettings` and keep them in one unit (mbar, `ScientificDoubleSpinBox`)
- [x] Latch trips until "Re-arm" is pressed, refuse higher heating currents while tripped and also catch current changes from scripts (measured current is checked)
- [ ] Show the age of the last reading for Laser and Power Meter as well (PSU, EBIS and Pressure done)
- [ ] Optionally also check the other gauges (not only the selected one)
- [ ] Interlock self-test button (simulate a trip without hardware) and a "reset/re-arm" confirmation
- [x] Ramp the heating current up slowly instead of jumping (cathode lifetime) - "Ramp [A/min]"; lowering/switching off and the interlock are immediate

### Hardware / Devices
- [ ] Integrate the Adjustable Delay Stage (`Threaded` wrapper, `DeviceWrapper`, GUI panel, CommandServer entry, DB logging, position in mm/ps instead of steps)
- [x] Implement Keithley PicoAmp meter in the Monitor tab (panel "Electrometer", DB table `Electrometer`, CommandServer `ELECTROMETER`)
- [x] Keithley PicoAmp meter: set instrument back to local mode on close (`KeithleyPAmeter.py`)
- [x] Keithley PicoAmp meter: check return values of `setCurrentRange`/`getLastData` (`KeithleyPAmeter.py`, rewritten after the manual, test: `python -m Connection.KeithleyPAmeter [COMx]`)
- [x] Keithley 6514: run the device test routine with the real instrument (COM6, 9600 baud; READ? needs arm count 1, ^C recovers a blocked instrument, front panel defaults on close)
- [ ] Keithley 6514: measure with a real current source (only the open input, ~1E-13 A, was measured) and check the zero correct procedure
- [ ] Keithley 6514: offer the data elements/units in the CSV of the scripts (mean, std, n as separate columns)
- [x] Implement camera in the Monitor tab (FLIR/Teledyne via PySpin or harvesters, virtual camera, beam statistics, CommandServer `CAMERA`)
- [x] Camera: test with the real camera (Blackfly S via harvesters; live view lagged: old buffered images, slow beam statistics, 0.1 s worker polling)
- [ ] Camera: log beam position/width to the database, ROI selection (smaller images = higher frame rate), exposure/gain limits from the camera
- [ ] Camera: compute the beam statistics in the worker thread and optionally on a downsampled image
- [x] EBIS: use a `DeviceWrapper` like the PSU so it can be controlled via CommandServer/Scripts
- [x] Add EBIS to the CommandServer (device name `EBIS`, the pressure interlock still limits the heating current)
- [ ] EBIS via CommandServer: map logical channels (Cathode, DT1, ...) to the physical MICC channels, like the GUI does
- [x] Automatic reconnect on lost connection and remember/auto-connect last used ports on startup (all devices, also the power meter)
- [ ] Detect hanging devices (no answer for a long time, but no exception) and reconnect them as well
- [x] Monaco: cleaner return types for faults/IP/help (lists of codes/texts, `parseIP`, `MonacoCommand`, `MonacoSettings`, `MonacoReprate`)
- [ ] Monaco: verify the parsing of `?NEW`, `?SESSIONS`, `?TIMEZONES` and `?DAF` with real fault output (formats are not documented)
- [ ] Monaco: parse `?DATA` (datalogger) output
- [ ] ISEG: implement MICC user calibration commands
- [x] Include the device name in error messages of `ThreadedConnection.handleError`
- [ ] Get limits, units and decimals of PSU/EBIS spinboxes right, and move the input ranges to `DefaultParams`
- [ ] EBIS heating current: enable button directly at the current row (currently blocked by the warning message box on `editingFinished`)
- [ ] PSU: decide if all other channels must be switched on again after a polarity switch
- [ ] Laser: verify units of the chiller pressure and the RF level / output frequency calculation (see TODOs in `Laser.py`)
- [x] Laser: catch more socket errors on connect (`TELNET_ERRORS`)
- [x] Power meter: handle values outside of the valid range (shown as "Out of range", logged as NULL)

### Scripts / CommandServer
- [ ] Add message framing to the socket protocol (e.g. newline-terminated), so multiple commands sent quickly are not merged into one `recv`
- [ ] Add a timeout for answers in the ScriptServer, so a non-answering device does not block the script forever
- [x] Ranges for scans in scripts (`start:stop:step`) and results of every command saved as CSV
- [x] Basic math with the placeholder in scripts (`-%`, `%+5`, `%*10`, `abs(%)`, ...)
- [ ] Several placeholders per line (e.g. `%1`, `%2` for 2D scans) and named variables
- [ ] Conditions in scripts (wait-until e.g. `WAIT_UNTIL PRESSURE < 1E-8`) and variables
- [ ] Syntax check / dry-run of scripts before starting, with highlighting of the faulty line
- [ ] Progress bar with timer until the next command (see TODO in `Scripts.py`)
- [x] Allow multiple commands at each timestep (`A;B`)
- [x] Write a short documentation of the script language (README section "Scripts")
- [ ] Documentation of the CommandServer protocol with a small python client example
- [ ] Wien filter: live plot of the electrometer current vs. voltage while a script runs (from the results CSV)
- [ ] Wien filter: linked positive/negative PSU channels in the GUI (step both with one control, e.g. 0.5 V) - requirements to be clarified
- [ ] Optional access control for the CommandServer (it currently accepts every local client and can switch high voltages)
- [ ] Restart button for the CommandServer if it could not be started (e.g. port in use)

### Measurement / Analysis
- [ ] Combine Scripts + Delay Stage + TDC into automated pump-probe scans (move stage, acquire, save with metadata)
- [x] Save measurement metadata (laser, PSU/EBIS voltages, pressure) automatically next to measured files (JSON next to the .lmf)
- [x] Improve LogNorm fitting and finish `FitLogNormRange` (shifted log-normal, several start values, copy button)
- [x] Better limiting of fit parameters (`Fitting.py`: `estimateGauss`, `gaussBounds`, adaptive window for Gauss (center))
- [ ] LogNorm/Gauss fits with constant background (offset) as additional parameter
- [x] Check for sane numbers (no `inf`/`nan`) in `Functions.py` (`isSaneNumber`, `saneOrDefault`)
- [ ] LMF reader: read more header parameters and full event data (see TODOs in `LMFConvert.py`)
- [ ] Export of fit results (CSV) and plots (PNG/PDF) in the Analyse tab
- [ ] Mass axis calibration in the Analyse tab using the Simulation calculators

### History / Database
- [x] Downsample data for long time ranges in the History tab (faster plots), but show the full density when zooming in (~2 points per pixel, averaged in the database, reloaded on zoom/pan)
- [x] History: optionally show min/max envelopes instead of averages for downsampled data (toggle "Min/Max")
- [x] Show the database size (menu `Database`)
- [x] Rename-proof logging: stable column ids plus a `Labels` table, so renaming e.g. a pressure gauge does not break the history
- [ ] Use the label valid at the time of the data for exports (currently the latest label is used)
- [x] `Events` table for one-time events (interlock trips, lost connections, ...)
- [x] Log lost connections and reconnects as events
- [x] Mark the events in the History plots (toggle "Events")
- [ ] Log more events (manual connect/disconnect, script start/end)
- [ ] Database maintenance: archive or thin out old data (e.g. keep 1 s data for 30 days, 1 min averages afterwards)
- [x] Make the splitter of the History tab work as intended (stretch factors, sizes are remembered)
- [x] History: exponential fit of the pressure to predict the final pressure (also power law for outgassing, `Utility/PressureFit.py`)
- [ ] History: store prediction fits as events/notes and show the predicted curve after a restart

### GUI
- [x] Add tooltips to everything (all device panels, History, Analyse, tabs, menus, settings)
- [x] Tooltips for the Scripts/Tips/Simulation tabs and the fit parameter widgets
- [x] Reduce code duplication of the channel rows in `PSU.py`/`EBIS.py` (`Utility/ChannelRows.py`: `VoltageChannelRow`, `CurrentLimitRow`)
- [x] Settings dialog for `DefaultParams` (update interval, limits, laser IP, server port) instead of editing the code (menu `Settings > Preferences...`)
- [ ] Apply changed preferences without restarting the application
- [x] Scrollbars for panels that are larger than the screen (only shown if needed, also in popped out windows)
- [x] Pressure panel always fully visible (no scrollbar), short reading age ("1.2 s" instead of "Last reading 1.2 s ago")
- [x] Icons from Lucide (SVG, sharp at every size)
- [ ] Icons for a dark theme (the icons are black/colored, `currentColor` of the SVGs is replaced when creating them)
- [x] Show CommandServer status (running, connected clients) in the status bar
- [x] Start CoboldPC from the GUI
- [x] Remember popped out panels and their positions (move back to default if they would appear outside of the screen)

### Code quality / Project
- [x] Single source for the version number (`GlobalConf.version`)
- [x] Add `__pycache__/`, `.vs/` and `.mcp.json` to `.gitignore`
- [x] Threaded workers wake up immediately on new work (no 0.1 s polling, faster camera, scripts and GUI updates)
- [ ] Unit tests for things without hardware (`parseFunctionCall`, `CommandQueue.parseScript`, `convertInChannelString`, `getPrefix`, LMF reader, pressure conversions) using the virtual devices
- [x] Replace `print` statements with the logger (remaining `print`s are only in the demo/test functions of the drivers)
- [ ] Command-line arguments (log level, virtual devices, no CommandServer)
- [ ] Write a short manual (sorry big boy 🐶)
- [x] Automatic changelog from the commit messages (`python -m Utility.Changelog` writes `CHANGELOG.md`)


## BUGs
- [x] Laser: `TelnetConnection.readline()` looped forever when the laser closed the connection
- [x] Values `nan`/`inf` broke the SQL insert of the logging (now stored as `NULL`)
- [ ] Pack images in executable - otherwise not shown (icon paths are relative to the working directory - resolve them relative to the project folder)
- [x] EBIS interlock: `hard_pmax_val`/`soft_pmax_val` start at `10` (= 10 mbar) and are only converted to `10 * 10^-8 mbar` after the spinbox was edited - the interlock is effectively off until then
- [x] `ConnectionWorker.execute` (`Threaded.py`): `work.append(work)` in the queue overflow branch should be `self.work.append(work)`
- [x] `ThreadedConnection.callback` (`Threaded.py`): after deleting a list of callback ids it raises `ValueError`, because the list is not an `int`
- [x] EBIS: current limits were sent to the logical channel index instead of the physical MICC channel (e.g. the limit of Drift Tube 1 was set on the Repeller)
- [x] Devices forget their last port if the connection was lost before closing the app (`closeEvent` only stores the port if still connected)
- [x] Unplugged USB devices (`SerialException`) were not detected as lost connection - the panel stayed "connected" and logged an error every second
