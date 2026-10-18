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

## Database
All values are logged once per second into a [DuckDB](https://duckdb.org/) file (`DB/Laserlab.duckdb`).
- **Data tables** (`Pressure`, `PSU`, `Laser`, `PowerMeter`, `EBIS`): one row per second, one column per value. The column names are
  *stable ids* - never rename them, otherwise the old data does not match anymore.
- **`Labels`**: the human readable name (and unit) of every column, with the time from which it is valid. If something is renamed in the
  GUI (e.g. a pressure gauge in `PressureVBoxLayout.pressure_gauges` - only the name, not the database column), a new label row is
  written at the next start. The History tab always shows the current name and lists the previous names in the tooltip.
- **`Events`**: things that happen once (interlock trips, lost connections, ...) with source, type, message and a value.

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
- [ ] Build a measure subtab (for TDC)
- [ ] Build a measure subtab (for NDIGO - if NDIGO is built)
- [x] Build a laser subtab
- [x] Make better logo and splash screen
- [ ] Start TDC software automatic with a button press and safe it automatically
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
- [ ] Ramp the heating current down/up slowly instead of jumping (cathode lifetime)

### Hardware / Devices
- [ ] Integrate the Adjustable Delay Stage (`Threaded` wrapper, `DeviceWrapper`, GUI panel, CommandServer entry, DB logging, position in mm/ps instead of steps)
- [ ] Implement Keithley PicoAmp meter in the Monitor tab (driver already exists)
- [ ] Keithley PicoAmp meter: set instrument back to local mode on close (`KeithleyPAmeter.py`)
- [ ] Keithley PicoAmp meter: check return values of `setCurrentRange`/`getLastData` (`KeithleyPAmeter.py`)
- [ ] Implement camera in the Monitor tab
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
- [ ] Restart button for the CommandServer if it could not be started (e.g. port in use)

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
- [x] Downsample data for long time ranges in the History tab (faster plots), but show the full density when zooming in (~2 points per pixel, averaged in the database, reloaded on zoom/pan)
- [ ] History: optionally show min/max envelopes instead of averages for downsampled data (spikes of e.g. the pressure can be averaged away)
- [x] Show the database size (menu `Database`)
- [x] Rename-proof logging: stable column ids plus a `Labels` table, so renaming e.g. a pressure gauge does not break the history
- [ ] Use the label valid at the time of the data for exports (currently the latest label is used)
- [x] `Events` table for one-time events (interlock trips, lost connections, ...)
- [x] Log lost connections and reconnects as events
- [x] Mark the events in the History plots (toggle "Events")
- [ ] Log more events (manual connect/disconnect, script start/end)
- [ ] Database maintenance: archive or thin out old data (e.g. keep 1 s data for 30 days, 1 min averages afterwards)
- [ ] Make the splitter of the History tab work as intended (stretch factors)

### GUI
- [ ] Add tooltips to everything
- [ ] Reduce code duplication of the channel rows in `PSU.py`/`EBIS.py` (one channel widget class)
- [x] Settings dialog for `DefaultParams` (update interval, limits, laser IP, server port) instead of editing the code (menu `Settings > Preferences...`)
- [ ] Apply changed preferences without restarting the application
- [x] Show CommandServer status (running, connected clients) in the status bar
- [ ] Start CoboldPC from the GUI
- [x] Remember popped out panels and their positions (move back to default if they would appear outside of the screen)
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
- [x] EBIS interlock: `hard_pmax_val`/`soft_pmax_val` start at `10` (= 10 mbar) and are only converted to `10 * 10^-8 mbar` after the spinbox was edited - the interlock is effectively off until then
- [x] `ConnectionWorker.execute` (`Threaded.py`): `work.append(work)` in the queue overflow branch should be `self.work.append(work)`
- [x] `ThreadedConnection.callback` (`Threaded.py`): after deleting a list of callback ids it raises `ValueError`, because the list is not an `int`
- [x] Devices forget their last port if the connection was lost before closing the app (`closeEvent` only stores the port if still connected)
- [x] Unplugged USB devices (`SerialException`) were not detected as lost connection - the panel stayed "connected" and logged an error every second
