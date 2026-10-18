# Changelog

*Automatically created from the commit messages with `python -m Utility.Changelog` - do not edit by hand.*

## v0.1.67 (2026-10-18)

**Fitting: finished LogNorm fit, better start values and limits**

Gauss fits (range, center, gauss + counts):
- Bug fix: the start value of sigma was never estimated from the data
  ("y > max" is never true), always a quarter of the range was used.
  New estimateGauss(): sigma from the width at half maximum around the
  maximum.
- New gaussBounds(): sigma between a tenth of the bin width and the range
  width (no division by zero for sigma = 0 anymore), mu inside the range,
  c between 0 and 10 x maximum; clipToBounds() keeps start values inside
  the bounds (curve_fit raised ValueError otherwise).
- At least 4 data points are needed.
- Gauss (center), "better limiting" TODO: the window is now +-3 FWHM of
  the estimated peak around the bar (min. 1/4 of the old 10 % window,
  max. half of the view), so wide peaks are not cut and neighbouring
  peaks do not disturb narrow ones. Removed the wrong
  "self.parameters = [0, 0, 0]" assignment.

LogNorm (range), "unfinished/improve" TODOs:
- Shifted log-normal with area A:
  y = A/(sigma (x-x0) sqrt(2pi)) exp(-(ln(x-x0)-mu)^2/(2 sigma^2)), 0 for x<=x0
  (computed without nan/warnings for x <= x0).
- Start values from the peak (mode, FWHM, area) for several skewness
  values sigma (0.05 ... 1.0); the result with the smallest squared
  residuals is used. Before, the start values assumed x0 = 0 and the
  bounds of mu were invalid for negative mu.
- Bounds: 0.001 < sigma < 5, mu +-10 around the start, x0 before the
  peak maximum, 0 < A < 20 x estimated area.
- Mode and FWHM as separate functions; copy button returns (mode, A, fwhm)
  (was missing).

Tested with synthetic Poisson data: Gauss mu/sigma within 0.1 of the true
values (also next to a second peak), LogNorm recovers mode 34.24 (true
34.26) for a tight range and a range with empty bins before the peak.

## v0.1.66 (2026-10-18)

**EBIS: slow ramp of the cathode heating current** (9b0b1f0)

- New row in the EBIS "Heating" group: "Ramp [A/min]" (default 0.1 A/min,
  stored in QSettings, 0 = set immediately like before), a status label
  "Ramping: 1.000 A -> 1.05 A" and a "Stop" button that holds the current
  value.
- Entering a new heating current starts a software ramp: every 0.5 s the
  current set in the MICC moves towards the target by speed * elapsed
  time. Entering another value while ramping retargets the ramp. The ramp
  starts from the current read from the device on connect (if unknown,
  the value is set directly).
- Safety first: the pressure interlock stops a running ramp and lowers the
  heating current immediately; the trip limit also caps the ramp target.
- The ramp is stopped on disconnect/reset.
- A software ramp is used instead of the MICC current ramp, because the
  hardware ramp is defined in % of the nominal value per second and it is
  not clear if it applies to the current-controlled heating channel.

Tested offscreen with a fake connection and simulated clock: ramp up
(0.01 A/s steps), finish at target, ramp down, interlock lowers to 0 A
immediately and stops the ramp, ramp speed 0 sets immediately.

## v0.1.65 (2026-10-18)

**Sane numbers, power meter out of range, robust laser telnet connection** (d30c871)

Sane numbers (Utility/Functions.py):
- New isSaneNumber() (int/float/numpy number, finite, not bool) and
  saneOrDefault().
- getPrefix() returns (value, '') for nan/inf instead of crashing
  (formatting nan with an exponent raised an IndexError), and accepts numpy
  numbers.

Database: Tables.insert() writes None, nan and inf as NULL. Before, such a
value was written as the text "nan"/"inf" into the SQL query, which made
the insert fail (e.g. for an overranged power meter).

Power meter (Windows/PowerMeter.py):
- Powers above 100 W / currents above 0.1 A (e.g. the overrange value
  9.9E37), nan and inf are treated as out of range: the display shows
  "Out of range" (with tooltip), min/max are not updated and the value is
  logged as NULL.
- Power in dBm is only calculated for positive powers (log10 of 0 or a
  negative value crashed the update callback before).
- Invalid measurement results are logged instead of raising.

Laser / telnet (Connection/Telnet.py, Windows/Laser.py):
- TELNET_ERRORS = (OSError, EOFError, ValueError, UnicodeDecodeError)
  covers refused connections, timeouts, unknown hosts (gaierror), closed
  connections and invalid answers; used for connect and disconnect.
- Bug fix: readline() looped forever (100 % CPU in the worker thread) if
  the laser closed the connection, because recv() returns b'' then. Now a
  ConnectionResetError is raised, which also triggers the automatic
  reconnect. read() does the same.
- Bug fix: a failed connect kept the unconnected socket, so a later
  open() never connected again.

Tested: sane numbers/prefixes, NULL logging in a scratch DB, power meter
display parameters for normal/negative/overrange/nan values, refused
connection and server-side close with local test sockets.

## v0.1.64 (2026-10-18)

**Automatic changelog, labels valid for old data, remove BCA-GUIDE TODO** (59aadda)

Changelog:
- New Utility/Changelog.py: "python -m Utility.Changelog" creates
  CHANGELOG.md from the git history. Subjects starting with a version
  (v0.1.52, v0.1.40b, ...) start a version entry with the commit body as
  details; commits without version are listed under the next newer
  version; merge commits and trailers (Co-Authored-By, ...) are skipped.
- "--next-message FILE" includes the commit that is about to be created,
  so CHANGELOG.md can be updated in the same commit.
- CHANGELOG.md added (93 versions), README section "Changelog".

Database (old data):
- The first label of a column is now stored with Time 0 (valid from the
  beginning), so it also describes all data that was logged before the
  Labels table existed. Renames are still stored with the current time.
- README: no migration of the old data is needed, the data tables are
  unchanged.

Other:
- Removed the "should also be implemented in the BCA-GUIDE" TODO
  (GlobalConf.py) and its README entry.

## v0.1.63 (2026-10-18)

**Logger instead of print in the virtual devices** (4480d05)

- Connection/VirtualDevice.py: VirtualSerial/VirtualSocket log their
  write/read/close calls with GlobalConf.logger.debug instead of print.
- Checked all modules (AST scan): the remaining print() calls are only in
  the demo/test functions of the drivers (main(), readErrorStatus(),
  toggleLaserAndReadStatus(), simulation_calculator_test(), ...) that are
  run from the console, which is intended.
- README TODO ticked off.

## v0.1.62 (2026-10-18)

**Tooltips for all controls of the device panels, History, Analyse and tabs** (d224caf)

- 77 new tooltips: PSU (connection, ramp), EBIS (connection, general HV,
  heating current, ramp speed), Pressure (connection), Power Meter
  (connection, display parameter, wavelength/IR/UV presets, attenuation,
  averaging, beam diameter, min/max), Laser (connection/IP settings, key
  switch, shutter, pulsing, system start/stop, chiller temperature/flow/
  pressure/service, faults, amplifier, repetition rate/divisor, RF level,
  pulse width), History (start/end time, export file), Analyse (fit
  function, reset sliders, log-y, fill histogram).
- Tooltips for the main tabs (MainWindow.addTab got a tooltip argument).
- DisplayLabel: setToolTip() now stores a description that is kept when
  the label updates its "Target value: ..." tooltip (before, every update
  replaced it). Used e.g. for the measured values of the channel rows.
- Removed the "TODO: Add tooltips to everything" in Main.py.

Checked offscreen: every button/spinbox/combobox of the PSU, EBIS,
Pressure, Laser and Power Meter panels has a tooltip (the inner +/-
buttons of the polarity widgets use the tooltip of their parent).

## v0.1.61 (2026-10-18)

**One channel row class for PSU/EBIS, fix EBIS current limit channels** (772ab89)

Refactoring (new Utility/ChannelRows.py):
- VoltageChannelRow: name | (polarity) | set voltage | measured voltage |
  (measured current) | output LED | enable button, inserted into an
  InsertingGridLayout; setOutputState()/reset(); tooltips for every widget.
- CurrentLimitRow: name | limit [mA] | limit reached LED;
  updateCurrent()/reset().
- PSU.py and EBIS.py build their rows from a list of channel names
  (PSU: MCP Front/Back, Anode, Cathode LSD, Focus LSD; EBIS: Cathode,
  Drift Tube 1-3, Repeller + heating voltage row without current column).
  The grouped lists used by the device callbacks (status_voltages,
  indicators, ...) are derived from the rows, so the device logic is
  unchanged. reset(), log() and databaseLabels() use the rows.
  -174 lines in PSU.py, -193 lines in EBIS.py.
- EBIS.channel_dict (logical -> physical MICC channel) moved to the top
  of __init__ and commented.

Bug fix (EBIS):
- setCurrentLimit() sent the limit to the logical channel index instead of
  the physical MICC channel, e.g. the limit entered for "Drift Tube 1"
  (logical 1) was set on physical channel 1 = Repeller. Reading the limits
  back used the physical order, so the GUI looked consistent. Now mapped
  via channel_dict like voltages and outputs.

Tested offscreen: grid sizes, grouped lists (incl. heating current at
index 5 and None limit), ramp channel names, DB labels, the limit of
Drift Tube 1 goes to physical channel 2 and the repeller voltage to
physical channel 1, interlock and reconnect tests still pass.

## v0.1.60 (2026-10-18)

**Settings dialog for DefaultParams** (1798673)

- New menu "Settings > Preferences..." (Windows/Settings.py) with the
  editable parameters grouped by General (update/ramp/reconnect
  intervals), PSU, EBIS (deviations, maxima), Laser (default IP/port,
  chiller/baseplate limits, wavelengths) and CommandServer (host, port,
  max. clients). Tooltips show description, default value and range.
- Values are checked (type, range, IP format); invalid fields are marked
  red and nothing is saved. "Restore defaults" fills in the original values.
- Only values that differ from the defaults are stored (QSettings group
  "default_params").
- DefaultParams.editable describes the parameters (group, description,
  unit, min, max); convert()/toString()/loadOverrides()/saveOverrides().
- The stored values are applied at the end of Config/GlobalConf.py, i.e.
  before any other module is imported - this is needed because several
  modules use DefaultParams as default arguments (evaluated at import).
  Therefore changes take effect after a restart (the dialog says so).
  Invalid stored values are ignored and logged.

Tested offscreen with an isolated settings file: conversion/validation,
invalid save rejected, save + load round trip, restore defaults.

## v0.1.59 (2026-10-18)

**Remember popped out panels and their positions** (bbce1a1)

- VBoxTitleLayout keeps a list of all panels that can be popped out
  (popout_instances) and got popoutGeometry()/restorePopout().
- On close, the main window stores which panels are popped out and their
  window geometry in QSettings (group "popouts", key = panel title, e.g.
  "EBIS"). This happens before the tabs are closed, because closing them
  also closes the popped out windows.
- On startup (after the main window is shown) these panels are popped out
  again at their old position. If the title bar of the window would not be
  on any screen (e.g. second monitor removed) or the size is invalid, the
  default position is used instead.
- GlobalConf.updatePopouts()/getPopouts().
- Clearer tooltip of the popout button.

Tested offscreen: restore at a stored position, store/load round trip,
position outside of all screens falls back to the default.

## v0.1.58 (2026-10-18)

**History: zoom-dependent downsampling and event markers** (f4e54fb)

Downsampling (Windows/History.py):
- The preview loads the data averaged in time buckets inside the database
  (DB.getData(bucket_seconds=...)), so about 2 points per pixel of the
  plot are transferred and drawn - independent of the selected time range.
- Zooming/panning (debounced 300 ms) loads the visible range again if a
  finer resolution is available (down to the raw 1 s data) or if the view
  was zoomed out a lot; 50 % margin on both sides so small pans do not
  reload. The current resolution is shown next to the plot ("Resolution:
  82 s" / "all data").
- Curves use pyqtgraph clip-to-view and peak downsampling for rendering.
- Each selected column is plotted as its own series, no more merging into
  a dense 1-row-per-second array with nan gaps for the preview.
- Export still uses the full resolution (unchanged).
- Example (test DB, 3 days of 1 Hz data): full range loads in 0.03 s with
  82 s buckets (3162 points instead of 259200), 1 h zoom -> 2 s buckets.

Events: new "Events" toggle marks the entries of the Events table
(interlock trips red, lost connections/reconnects orange) as dashed
vertical lines with label and tooltip.

Utility/Functions.py: mergeArraysFirstColumn() got a step parameter for
bucketed data (default 1 = old behaviour).

## v0.1.57 (2026-10-18)

**Monaco: structured return types instead of raw strings** (22d0f55)

Connection/Monaco.py - resolves the "better faults/errors/help/output" TODOs:
- New parser functions (usable without a laser): parseCodes, parseTexts,
  parseIP, parseHelp, parseReprates, parseKeyValues.
- New NamedTuples: MonacoCommand (?HELP entries), MonacoSettings (?SET,
  still indexable like the old tuple, so Laser.py keeps working),
  MonacoReprate (?LOOKUP REPRATES NAMES).
- faultsGet, fhGet, whGet -> list[int] (empty for "SYSTEM OK"); fGet/wGet
  use the shared parser.
- dafGet, chfaultGet -> list[str] of active faults (empty for "SYSTEM OK-"
  / "There are no active chiller faults").
- lipGet -> tuple of 4 ints or None (e.g. for "Error, bad command").
- helpGet -> list[MonacoCommand] (command, access, type, min, max,
  description); checked against the full help text in the module
  docstring (192 commands parsed).
- lookupRepratesNamesGet -> list[MonacoReprate], e.g. (200.0, 5, 'PulseEQ').
- newGet -> dict, sessionsGet/timezonesGet -> list[str] (best effort, the
  formats are not documented - listed as TODO to verify).
- dataGet stays raw (TODO: datalogger format unknown).

Only setGet() is used by the GUI and its NamedTuple is backwards
compatible. CommandServer clients get the str() of the new types.

## v0.1.56 (2026-10-18)

**Automatic reconnect after lost connections, remember ports reliably** (fcf8f53)

Lost connection detection (Connection/Threaded.py):
- SerialException (unplugged USB device) and BrokenPipeError now count as
  lost connection, not only ConnectionAborted/ResetError. Before, an
  unplugged device left the panel "connected" and logged an error every
  second.
- The lost-connection function is called only once per connection and
  not for (queued) errors of an already closed connection, so a late error
  can not disconnect a freshly reconnected device.
- Error messages include the device name (e.g. "ISEG: SerialException: ...").

Automatic reconnect (new Utility/AutoReconnect.py):
- AutoReconnect: after a lost connection, tries to connect silently every
  5 s (laser: 15 s, because a failing telnet attempt blocks up to its
  timeout). Stops on success or when the user presses Connect/Disconnect.
  Logs only the 1st and every 10th failed attempt.
- EventLog: global sink for events; the main window points it to
  DB.insertEvent, so "connection_lost" and "reconnected" end up in the
  Events table.
- Used by PSU, EBIS, Pressure, Laser and Power Meter
  (manualConnect/connectionLost/reconnect).
- Laser: automatic reconnects do NOT acknowledge laser faults (fackSet is
  only sent on a manual/startup connect), so a fault can not be cleared
  without the user noticing.

Remember ports:
- closeEvent stores the last port also if the connection was lost
  (reconnect pending); only a manual disconnect forgets it. Before, a
  device that lost its connection was not auto-connected on the next start.
- Power meter port is now stored/restored and auto-connected on startup
  (GlobalConf.updateConnections(power_meter=...), getConnection('power_meter')).
- New DefaultParams.reconnect_interval_time / reconnect_interval_time_laser.

Tested offscreen: SerialException triggers exactly one lost-connection
call, reconnect attempts, port remembered after loss, manual connect stops
reconnecting, manual disconnect forgets the port, events are logged.

## v0.1.55 (2026-10-18)

**EBIS DeviceWrapper + CommandServer entry, server status in status bar** (589e999)

EBIS (Windows/EBIS.py):
- Uses a DeviceISEGWrapper like the PSU. self.threaded_connection is now a
  property that reads/writes device_wrapper.threaded_connection, so all
  existing code keeps working and the CommandServer always sees the
  current connection.
- The threaded connection now gets self.unconnect as
  connection_aborted_function (as the PSU), so a lost connection resets
  the panel instead of leaving it in "connected" state.

CommandServer (Socket/CommandServer.py, Windows/Main.py):
- New device "EBIS" (only if the EBIS panel is enabled). Example:
  "EBIS:measureCurrent(10)". Note: the channels are the physical MICC
  channels; the pressure interlock still lowers the heating current if a
  command raises it while tripped (it checks the measured current).
- The socket is bound in startServer() instead of __init__ and errors
  (e.g. port already used by a second instance) are caught and logged:
  the GUI starts without the server instead of crashing.
- Tracks connected clients (thread-safe) and has status()/clientCount().
- Also catches ConnectionAbortedError of clients.

Main window: permanent status bar label "CommandServer on localhost:6969,
N clients" (or "not running (reason)"), updated every second; tooltip
lists the available devices.

Tested on a spare port: start, second instance on the same port (not
running, no crash), client count up/down, EBIS answer "not connected".

## v0.1.54 (2026-10-18)

**Fail-safe EBIS pressure interlock with watchdog, states and trip logging** (e313091)

Interlock logic (new Utility/Interlock.py, no GUI/hardware dependency):
- PressureInterlock with InterlockLimits (all pressures in mbar) and
  InterlockState: DISABLED, ARMED, TRIPPED_SOFT, TRIPPED_NO_READING,
  TRIPPED_HARD.
- Hard limit: pressure above limit -> heating current lowered immediately.
- Soft limit: median over the soft duration above limit -> lowered to the
  soft current. Now needs a full window of valid readings (before, a single
  value right after startup could trip it, and zeros from a disconnected
  gauge were part of the median).
- Fail-safe watchdog: if there is no valid pressure (ADC not connected,
  gauge disconnected -> pressure 0, nan, or the readings are older than the
  "No reading timeout") for longer than the timeout, the heating current is
  lowered to the hard-limit current. Before, a missing gauge silently
  passed the check.
- Trips are latched (only escalate) until the user presses "Re-arm".
- Self tests: python -m Utility.Interlock

EBIS panel (Windows/EBIS.py):
- New "Pressure Interlock" group: state LED + text (with max. current and
  trip reason as tooltip), Re-arm button, selected gauge with its last
  pressure and reading age, hard/soft limits in mbar with the new
  ScientificDoubleSpinBox (no more "10^-8 mbar" workaround), currents,
  soft duration and watchdog timeout.
- Fixes the bug that hard/soft limits started at 10 mbar until the
  spinbox was edited (interlock effectively off after every start).
- Limits and the selected gauge are stored in QSettings and restored.
- While tripped, higher heating currents are refused (message box). The
  interlock also compares the measured heating current, so changes from
  scripts/CommandServer are lowered again.

Control tab: pressureCheck() only feeds the interlock now and writes every
new trip to the Events table of the database and to the status bar.

Watchdog display: ThreadedConnection stores the time of the last answer of
the device (secondsSinceLastResult()); new ReadingAgeLabel shows
"Last reading x s ago" (orange > 3 s, red > 10 s) in the connection rows of
PSU, EBIS and Pressure.

Other: ScientificDoubleSpinBox (Layouts.py), GlobalConf.update/getEBISInterlock().

Tested offscreen without hardware (isolated QSettings, no auto connect):
armed/hard trip/refused current/watchdog trip/persistence round trip.

## v0.1.53 (2026-10-18)

**Database: Events and Labels tables, rename-proof history, DB size** (d7174b5)

Database (DB/db.py) - only additive changes, existing tables are untouched;
the new tables are created automatically on the next start:
- New table "Events" (Time, Source, Type, Message, Value) for one-time
  events like interlock trips or lost connections. DB.insertEvent() commits
  immediately and never raises (must not crash e.g. the interlock),
  DB.getEvents() reads them back.
- New table "Labels" (Time, TableName, ColumnName, Label, Unit): the column
  names of the data tables are now treated as stable ids, the human readable
  name lives here with the time it is valid from. DB.updateLabels() only
  writes changed labels, DB.getLabels()/getLabelHistory() read them (cached).
- Parameterized queries (_execute_parameterized, Tables.insert_parameterized)
  for string values.
- getData()/Tables.get() take an optional bucket_seconds argument that
  averages the data in time buckets inside the database (downsampling for
  long time ranges, used by the History tab later).
- DB.getSize() returns the size of the database file + write-ahead log.
- Fixed DB._commit(): next commit time used timedelta(days) instead of
  seconds.

Pressure (Windows/Pressure.py):
- pressure_gauges entries now carry their stable database column, so a
  gauge can be renamed without breaking the history; logging inserts by
  column instead of by position.
- Timestamp of the last successful reading (secondsSinceLastUpdate()) and
  getPressure(name) - groundwork for the interlock watchdog.

GUI:
- Main window registers the current labels of the pressure gauges and the
  PSU channels at startup, shows the version in the window title and has a
  new "Database" menu with the database size and "Open database folder".
- History tab lists the current labels (with unit) instead of the raw
  column names; the tooltip shows the database column and previous names.
  Plot legends/exports use the labels as well.
- (Also contains the already present "Shutting down" log line in Main.py.)

README: new "Database" section explaining data/Labels/Events tables and how
to rename things safely; TODOs updated.

Tested with a scratch DuckDB file (never the live database): table
creation, re-opening, events, label changes/history, bucketed queries and
the History tab offscreen.

## v0.1.52 (2026-10-18)

- Ion Commander v0.1.51 (48ef15f)
**Housekeeping: single version source, gitignore, callback bug fix** (bf8d557)

- Version number now lives only in GlobalConf.version; the splash screen
  reads it from there (no more hard-coded 'v0.1.51' in main.py)
- .gitignore: ignore __pycache__/, *.pyc, .vs/, .vscode/, .mcp.json, .claude/
- Threaded.py: ThreadedConnection.callback() no longer raises ValueError
  when the worker returns a list of deleted callback ids (queue overflow).
  The callbacks of the dropped tasks are removed (pop with default, so
  unknown ids do not raise KeyError) and the call returns early.
- README: TODO section reorganised; all TODOs found in the code are now
  listed (Keithley, Monaco, Laser, PowerMeter, Fitting, LMFConvert, ...),
  new items added (interlock self-test, heating ramp, CommandServer access
  control, DB thinning, changelog), the already fixed
  ConnectionWorker.execute work.append bug is ticked off and a new bug
  (devices forget their port after a lost connection) is listed.

## v0.1.51 (2026-09-11)

- Create LICENSE (949b8de)
**Selectable pressure gauge for EBIS PSU shutdown criteria** (da68aaf)

## v0.1.50 (2026-04-29)

**Added EBIS ramp** (a7784ee)

## v0.1.49 (2026-04-29)

**Added TODOs, corrected EBIS current limits** (199d077)

## v0.1.48 (2026-04-29)

**EBIS current limit implementation** (c270bf3)

## v0.1.47 (2025-11-30)

**Better Error handling for missing TLPMx .dll path** (8fcc41f)

## v0.1.47 (2025-11-27)

**Added ESD pressure view and logging, updated requirements.txt, README.md and .gitignore file, amd provided better example for the scripts** (ade5600)

## v0.1.46 (2025-11-04)

**Added chiller pressure (log, laser/chiller view, history) Autoupdate on history** (9e34ec5)

## v0.1.45 (2025-08-25)

**Updated database - now it magically works** (7de3d32)

## v0.1.44 (2025-08-25)

**Updated db.py for temporary working again** (d345d5b)

## v0.1.43 (2025-08-25)

**Change over from sqlite3 to duckdb** (aa32c96)

## v0.1.42 (2025-08-12)

**Pressure control only triggers if set pressure is above target** (3e3be8a)

## v0.1.42 (2025-07-07)

**Pressure Widgets showing "No pressure available" if unconnected** (4143271)

## v0.1.41 (2025-07-03)

**Different target pressure for hard and soft limits** (d2d44aa)

## v0.1.40c (2025-07-02)

**Using median instead of average for soft limit Also resets the heating current SpinBox value** (0adf90e)

## v0.1.40b (2025-07-02)

**missing line for safe current set + current input range** (ad7648f)

## v0.1.40 (2025-07-02)

**Added controls for the EBIS pressure safety hard limit : instant off if value reached soft limit : off if average pressure over time is above limit this is to survive short pressure spikes** (1daf4f6)

## v0.1.39 (2025-07-02)

- Started to add logging to EBIS (ca3386c)
- better voltage steps (6f8b19f)
- EBIS logging (e84cd98)
- absolute values cathode and repeller values are negative, so not visible when history uses a log graph (1d547d0)
**EBIS logging, pressure regulates EBIS cathode heating current** (dcf5f1c)

## v0.1.38 (2025-05-06)

**(no description)** (8b8e11b)

WAIT command for ScriptServer; also adjusted example script

More Error handling in Threaded classes, especially if the Laser unconnects

## v0.1.37 (2025-04-22)

**View .lmftxt files PowerMeter Server Script support** (eaf76b7)

## v0.1.36 (2025-02-16)

**Better closing - no errors (maybe not the best choices..)** (32afa4c)

ScriptServer now runs in own thread -> works propperly even on errors

## v0.1.35b (2025-02-15)

**Added icons to git** (ecc7e52)

## v0.1.35 (2025-02-15)

**Added Script section to run on socket server** (0c05ac6)

Added repetition rate functionality for Laser

## v0.1.34 (2025-02-13)

**better implementation of Threaded Workers (clean queue if too many)** (d6b1a5d)

Update lmf2txt.exe

Reimplement Laser Frequency better

## v0.1.33 (2025-02-07)

**Updated lmf2txt with more features** (f4668e9)

## v0.1.32b (2025-02-07)

**Re-added lmf2txt converter, but only sourcecodes and latest executable** (06a6df7)

## v0.1.32a (2025-02-07)

**Removed lmf2txt temporary** (c7181e7)

## v0.1.31b (2025-02-07)

**Included combination tool for STL files (only for Windows): STLCombine/STLCombine.exe** (c452878)

## v0.1.31a (2025-02-07)

**Included combination tool for STL files (only for Windows): STLCombine/STLCombine.exe** (3835508)

## v0.1.30 (2025-02-04)

**Laser displayed as disconnected if it is switched off while GUI is running. Same implementation for PSU.** (a486cf2)

## v0.1.29 (2025-01-05)

**Faults table for laser now working properly Better labels in Fitting routines Adjusted Pressure limits Better history plotting** (d47a770)

## v0.1.28 (2025-01-05)

**Create Tip related folders on startup to prevent crashes** (127caad)

## v0.1.27 (2025-01-05)

**Better error handling in Threaded.py** (3b24cfe)

## v0.1.26 (2024-11-13)

**Socket server extended for Laser and PSU classes.** (6031d94)

## v0.1.25 (2024-11-13)

**Socket server fully implemented (not tested yet). Call routines should correspond 1:1 to actual function calls because of ast analysis Removed str arguments in Connection classes again** (2335cc9)

## v0.1.24 (2024-11-12)

**Made socket server working (without arguments) -> will change calls to normal call routines, therefore also "str" annotations will be removed again in Connection Classes** (6e0fa7e)

## v0.1.23 (2024-11-12)

**Implemented Socket Server first draft** (3c8384c)

## v0.1.22 (2024-11-10)

**Fixed Laser Table** (b5db734)

## v0.1.21 (2024-11-10)

**Make FitRoutines accessable by non-QT calls Easier history viewing (time-now button) Added support for Keithley Ampmeter Changed Errortable for Laser (more visually work needed) Pressure in ur(under range) do now have the minimum pressure value Updated threaded connections: do not crash anymore when threads are shut down. Added more control over USB communication** (d5d75d1)

## v0.1.20 (2024-09-17)

**Updated .gitignore file to exclude logs, databases and tips Updated splash screens and logo Added splash screen at shutdown Added description of copy Fitting Parameters button Updated Tip editor functionality Updated Fitting routines for better initial guess therefore faster fitting Updated laser error table (more work probably needed) Updated file operations to encode/decode in 'utf-8'. Changed default debug in DB to False** (08152e1)

## v0.1.19 (2024-09-17)

**Included History viewing of database and exporting from history to csv files Added time selection Added datetime selection** (c478dc2)

## v0.1.18 (2024-09-16)

**Included requirements.txt file Updated colors and moved color functions in separate function class Moved everything into GlobalConf/StylesConf** (b7cdabc)

## v0.1.17b (2024-09-16)

**Deleted solved TODO comments Added some ToolTips** (37cd921)

## v0.1.17 (2024-09-14)

**GlobalConf update screen position Update debug log messages from matplotlib** (0593abd)

## v0.1.16 (2024-09-14)

**Updated ReadMe including matplotlib Minor improvements/bugfixes on layouts (VBoxTitleLayout generation) Added DB support for Laser, PSU and PowerMeter** (2019965)

## v0.1.15 (2024-09-11)

**Implemented Simulation evaluation Tab** (958246c)

## v0.1.14 (2024-09-11)

**Fully implemented PowerMeter Added Latex Label Layout Added fitting option (Gauss & Counts simultaneously) Added copy fitting parameters button** (c17d25f)

## v0.1.13 (2024-09-11)

**Implemented Popout windows for VBoxTitleLayouts** (305afd7)

## v0.1.12 (2024-08-22)

**First implementation of DB to store values permanently. For now only Pressure is supported. Improvements for PowerMeter** (7da6bef)

## v0.1.11 (2024-08-20)

**Update lmf2txt executable Support of different Presure Gauges (added TPF300 with calibration voltages to the mix)** (bddd8b6)

## v0.1.10 (2024-06-30)

**Reading LMFs now possible** (cb30f12)

## v0.1.09b (2024-06-30)

**Updated lmf2txt** (4653ca3)

## v0.1.09 (2024-06-29)

**Included lmf2txt.exe converter program** (7590ff5)

## v0.1.08 (2024-06-16)

**Improved analysis and PowerMeter** (fb72996)

## v0.1.07 (2024-06-13)

**More Power Meter stuff** (521ca90)

## v0.1.06 (2024-06-11)

**Added an editor for Tips** (2a3b077)

## v0.1.05a (2024-06-07)

**Updated plotting for multiple plots: clearing all when clear button is pressed** (29dafd0)

## v0.1.05 (2024-06-07)

**Plotting for multiple plots** (7846bbf)

## v0.1.04 (2024-06-03)

**Better timing display while ramping up PSU** (3594fcf)

## v0.1.03 (2024-06-03)

**Added counting to fit parameters in Analyse-Tab** (6bba5f5)

## v0.1.02b (2024-05-22)

**Updated .gitignore file** (5038ad9)

## v0.1.02 (2024-05-22)

**First powermeter implementation** (cae2511)

## v0.1.01 (2024-04-22)

**Relocated Log Folder** (e79f916)

## v0.1.01 (2024-04-22)

**Save and restore connection settings** (17e28da)

## v0.1.00 (2024-03-04)

**All major functionality concerning operation of connected devices is working stable (over one weekend at least)** (5ce42db)

## v0.0.13 (2024-02-22)

**Mayor update on PSU, EBIS and Pressure communication** (eee64f4)

## v0.0.12b (2024-02-12)

**Improved LogNorm Fitting** (4ce0391)

## v0.0.12 (2024-02-12)

**Improved LogNorm Fitting** (cbedccc)

## v0.0.11 (2024-01-30)

**Updated EBIS and Pressure Improved logging methods applied for all logging-instances** (264d4c4)

## v0.0.10 (2024-01-29)

**Better logging** (eaaac38)

## v0.0.9 (2024-01-17)

**Basic connection of PSU, EBIS and Pressure are done** (c3ce72a)

## v0.0.8 (2024-01-16)

**First test of pressure connection** (df65b34)

## v0.0.7 (2024-01-16)

**Threaded support for Connection Classes** (ffede86)

## v0.0.6 (2024-01-07)

**First draft of complete Control window** (a944f16)

## v0.0.5 (2024-01-05)

**Added First EBIS Control panel** (f512f9c)

## v0.0.4 (2024-01-04)

**Added pressure displays** (fb6212b)

## v0.0.3c (2024-01-04)

**Update .gitignore file** (e91b984)

## v0.0.3b (2024-01-04)

**Add .idea folder to .gitignore** (db9d908)

## v0.0.3a (2024-01-04)

**Delete .idea folder** (7d31550)

## v0.0.3 (2024-01-04)

**Updated all function names to follow CamelCase convention Better Indicator Light** (4a860ed)

## v0.0.2 (2024-01-03)

**Minor improved Splash screen class** (16ebd1a)

## v0.0.1 (2024-01-02)

- first commit (2c049f8)
- test123 (b34163d)
- Get project up to date (f25d8a9)
- Better Readme Better Colors Better Layout Comments to self-compilation file .gitignore file added (5b951f9)
- Update readme (0f473fd)
- Update readme Update styles Redo complete layout, make expendable (b6db21a)
- Forgot MainWindow lol (a844464)
- Allow drag and drop on Analyse.py window (fd4bc67)
- Update README.md (16d4a2f)
- Update readme (bc695cd)
- Update readme (07f18a2)
- blabla (e5edc7e)
- Update readme Restructure everything Add RNDIS communicaion with Monaco laser (b3537a5)
- Update and implement more functionality for Monaco Laser (6e87615)
- Introduce communication to LucidControl and therefore to Thyracont pressure gauge Update layout Small improvements (4443343)
**Improved Splash screen and logo** (175a0ae)

