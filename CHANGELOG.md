# Changelog

*Automatically created from the commit messages with `python -m Utility.Changelog` - do not edit by hand.*

## v0.1.81 (2026-10-29)

**Icons for the dark theme, icons relative to the project folder, Scripts toolbar label fixed**

Icons (Utility/Icons.py, new):
- getIcon('<file>') loads icons from the icons folder of the project (before: QIcon('icons/...') relative to the
  working directory). In a dark theme (palette: window darker than the text, e.g. dark mode of Windows with the
  windows11 style, checked when the icon is created = at startup) the black (#000000) of the monochrome Lucide icons
  is replaced by the button text color and the SVG is rendered at 16 ... 128 px (cached per icon and color); colored
  icons (play, abort, delete) and PNGs are unchanged.
- All 18 QIcon('icons/...') calls replaced (Layouts, Analyse, Camera, EBIS, Electrometer, Laser, PowerMeter, Pressure,
  PSU, Scripts, main.py); unused QIcon imports removed.
- Tested: offscreen with a light and a dark palette (pixel colors of the rendered icons), from another working
  directory, and on the real Windows platform (windows11 style reports the dark mode: window #1e1e1e, text #ffffff,
  screenshot of the buttons and the Scripts tab).

Scripts tab (Windows/Scripts.py): the info label of v0.1.80 ("7 steps, about 4.5 s" / error) had width 0 in the
toolbar (size policy Ignored), now Expanding with a minimum width (a long error still does not widen the window);
progress bar at least 150 px (the windows11 style draws the text next to a thin bar).

README: icons, TODOs updated and extended.

## v0.1.80 (2026-10-29)

**Scripts: %1/%2 placeholders, VAR variables, WAIT %, syntax check with duration estimate, progress bar with timer** (7830de9)

Script parser (Socket/ScriptServer.py):
- Placeholders are now replaced when the steps are built (the values of the enclosing loops are known there), the lines
  are parsed into ScriptLine(number, indent, kind, text, values, source) first.
- %1, %2, ...: value of the enclosing loop line with 0, 1, ... tabs (2D scans, e.g. "PSU:voltageSet(1,-%1/2+%) -2:2:1"
  below a loop over channel 0); % stays the value of the line itself.
- VAR <name> <values> with an indented block: loop over the values without a step of its own ($name in the block);
  VAR <name> <value> without block: variable for the following lines of the same level and their blocks (a variable
  set inside a block is only valid there); several values without block are an error.
- Variables and placeholders with math work in commands, values and ranges ("0:$umax:0.5", "0:%1*2:1", "$u*2").
- WAIT % <values> (wait times as loop values), WAIT $t, WAIT %1*2; the seconds are checked when the step is built.
- PRINT texts: placeholders/variables with a value are replaced, everything else is kept (e.g. "50%").
- Errors carry the line number (ScriptError, CommandQueue.error_line), clear messages for undefined %n/$name, invalid
  names, VAR without values, values without "%", WAIT % without values; scripts with more than 1,000,000 steps are
  rejected.
- CommandQueue.stepDurations()/duration(): planned duration (stepDuration() and stepCommands() are module functions now,
  also used by the worker); ScriptServer.duration(), progressInfo() (executed steps, steps, seconds until the next step,
  remaining seconds), progress() is based on the planned time.
- All 9 scripts in Scripts/ give exactly the same steps as before (compared with the parser of v0.1.79).

Scripts tab (Windows/Scripts.py):
- Syntax check while editing (debounced 300 ms): "<n> steps, about <duration>" or the first error in red (the label
  does not widen the window, full text in the tooltip).
- Progress bar with a timer (200 ms): "Step 3/7, next in 0.8 s, 3.8 s left", "Finished" at the end; the planned
  duration is written into the output at the start. TODO comment removed.

Tests: parser tests (2D, VAR scopes, WAIT %, durations, 21 error cases), end-to-end run with a fake PSU and
electrometer via the CommandServer, Scripts tab offscreen (check while editing, progress text during a run).

README: script syntax (VAR, %1/%2, WAIT %), check and progress; TODOs updated and extended.

## v0.1.79 (2026-10-29)

**Reading age for Laser/Power Meter, Monaco datalogger and long answers, PSU/EBIS input ranges in DefaultParams** (79e3748)

Reading age (Windows/Laser.py, Windows/PowerMeter.py):
- Laser and Power Meter show the age of the last successful reading (ReadingAgeLabel, orange/red if too old) like
  PSU, EBIS, Pressure, Electrometer and Camera.

Monaco (Connection/Monaco.py, Connection/Telnet.py):
- parseRead read only one recv(1024): long answers (?HELP, ?TIMEZONES, ?NEW after startup, ?DATA with many rows)
  come in several packets or are longer than 1024 bytes and failed with "Expected terminating cursor" (that is why
  newGet/sessionsGet/timezonesGet/helpGet were excluded in readOutValues). Now it reads until the "Monaco> " prompt
  (at most <timeout> s and 16 MB) and decodes the bytes at the end (a "°" split into two packets does not fail).
  TelnetConnection.readBytes() added, read() uses it.
- readInit: reads the welcome message up to the first prompt and everything that arrives within 0.3 s (before it
  needed the welcome message and the prompt in two separate packets, a second prompt would shift all answers).
- ?DATA (datalogger): dataGet(param, rows=, old_rows=, days=, hours=, minutes=, seconds=, time_from=, time_to=,
  no_duplicates=) builds the options of the manual (ROWS=n, DAYS=n, FROM="...", NODUP=1, ...) and returns a list of
  MonacoDatalogEntry(time, text, value); parseDatalog() reads the format of the manual ("2019-11-06 15:53.06 310",
  "... SYSTEM OK"), also hh:mm:ss(.fff), and skips other lines. The raw text: dataRawGet(cmd).
- The manual (Monaco 1035-40-40.pdf, Table 7-2) only describes ?NEW ("every parameter that has changed"), ?SESSIONS
  ("lists the active connections"), ?TIMEZONES and ?DAF without format, so the parsers accept the likely variants:
  parseTexts drops only the "no entries" entries (e.g. "SYSTEM OK-" of ?DAF) and keeps real entries of a mixed answer;
  parseTimezones splits lines, "&" and several zones in one line (only in front of "(UTC", the names contain commas);
  parseKeyValues splits at "," only if "KEY=" follows (values like "(UTC+01:00) Amsterdam, Berlin" are kept).
- python -m Connection.Monaco --test: parser tests (example of the manual, recorded answers);
  python -m Connection.Monaco --raw: sends only queries and writes the raw answers to monaco_raw_output.txt, to check
  the undocumented formats with the real laser (not run: the laser is used by the running GUI).
- Tested with a local fake Monaco server: answers in 7-byte packets, "°" split, 56 kB ?DATA answer (2000 rows),
  missing prompt (error after the timeout), welcome message with the prompt in one packet, delayed and doubled.

PSU/EBIS input ranges (Config/GlobalConf.py, Windows/PSU.py, Windows/EBIS.py):
- New DefaultParams (editable in the preferences): psu/ebis_voltage_decimals, psu/ebis_current_limit_minimum/maximum
  (mA), ebis_cathode_current_limit_maximum, psu_ramp_speed_maximum, psu_time_ramp_maximum,
  ebis_heating_voltage_maximum, ebis_heating_current_maximum, ebis_heating_ramp_maximum,
  ebis_interlock_current_maximum, ebis_ramp_speed_maximum (defaults = the old hard-coded values).
- Ramp speed of the ISEG crate/MICC: unit %/s of the nominal voltage (SCPI guide: :CONF:RAMP:VOLT), 3 decimals
  instead of 2, tooltip with an example and the range; docstrings of setRampSpeed said %/min.
- Heating voltage with 2 decimals (0 ... 5 V), voltage step = 10^-decimals.

README: TODOs updated and extended.

## v0.1.78 (2026-10-28)

**Fix broken package update (matplotlib), DuckDB pinned to < 2, DB.close() closes the connection** (b659196)

Startup failed after updating all packages with "No module named 'matplotlib.backends.registry'":
- Cause: Ion Commander was running during the update. Windows cannot replace files of loaded packages, so pip left
  half-installed packages behind (matplotlib 3.11.2 without RECORD and with missing files, plus "~..." backup folders
  of matplotlib, pillow, numpy, scipy, kiwisolver and PyQt6-Qt6).
- venv repaired (not part of the repository): matplotlib deleted and installed again, the "~..." folders removed, all
  installed packages checked against their RECORD files (all complete), pip check ok.
- Tested with the new versions (PyQt6 6.12, numpy 2.5, scipy 1.18, matplotlib 3.11, pyqtgraph 0.14): main window,
  scripts (fake devices), History (fits, electrometer data), pressure panel - all ok.

DuckDB:
- duckdb 2.0 (now built with nanobind) prints ~20 lines "nanobind: leaked 27 instances/6 types/85 functions" when the
  GUI is closed: objects of the PyQt widgets that are not freed at interpreter exit still reference DuckDB's module
  objects (not a real leak, also with a fake database). Downgraded to 1.5.6 (latest 1.x), requirements.txt: duckdb<2.
- Compatibility checked with scratch files only (the live database was not touched, it is locked by the running
  instance): duckdb 2.0 keeps the storage version of files written by 1.2/1.5, they stay readable by 1.x afterwards,
  and 2.0 replays a WAL written by 1.5.
- DB.close() now also closes the cursor and the connection (before it only committed); all DB methods already check
  for a closed connection.

README: package update note (close the GUI first, how to repair), requirements, TODOs.
Also contains the README TODO "Test the CoboldPC interface and make it functional with CCF-files" (added by hand).

## v0.1.77 (2026-10-28)

**Script WAIT <s>/PRINT/output folder, History fit toggle, pressure digit, label colors, electrometer cleanup** (5a934a2)

Scripts (Socket/ScriptServer.py, Windows/Scripts.py):
- WAIT <seconds>: the step takes the given time instead of the interval (plain WAIT = one interval as before).
  Steps are now scheduled one after another (next step = planned time of this step + its duration, no drift).
- PRINT <text>: writes the text into the output (with the elapsed time) and as a row with the command PRINT into
  the results CSV; spaces and ";" in the text are kept; a step that only prints takes no time.
- Output folder selectable in the Scripts tab (FilePath with folder dialog, remembered in the settings, default
  Scripts/results). Every run writes <script>_<date>_<time>.csv and <script>_<date>_<time>.log (the output).
- Loops: an indented block only belongs to the line directly above it. Before, all consecutive lines of the same
  level got the block (e.g. a PRINT or WAIT line above a scan also ran the whole inner block), which also
  contradicted the documented example. New recursive builder, error for lines indented less than the first line.
- Clear errors for "WAIT x", "WAIT -1" and unknown statements like "WAITS".
- Editor: the current line is highlighted with 20 % of the highlight color mixed into the background (read from
  the palette every time) instead of a full complementary color - readable in light and dark mode.

History (Windows/History.py, Utility/PressureFit.py):
- "Fit" on/off button (LED). Only if it is on, the model and the curve can be selected; the fit stays on and is
  recalculated after every update, auto update, zoom/pan and selection change (before, every auto update cleared it).
  "Fit visible range"/"Clear fit" buttons removed.
- New fit models for any curve (also negative values): Linear (slope per hour), Gaussian (peak/dip: peak value,
  time, FWHM, background) and Log-normal (asymmetric peak); exponential/power law/linear are extrapolated, the peaks
  only drawn over the fitted range; the unit is taken from the curve label; tests in python -m Utility.PressureFit.
- Auto update button moved behind the end time ("Now" button).
- Electrometer data in the History: loading, downsampling and plotting of the Electrometer table were tested with a
  scratch database (2 days of 1E-13 A values) and work; values are only logged while zero check is off (after
  connecting, zero check is on) - see README TODO.

Pressure:
- No horizontal scrolling of the Pressure panel (minimum width = content), vertical scrolling is possible again
  (VBoxTitleLayout(scroll_horizontal=False) replaces scrollable=False of v0.1.76).
- The big digit is always the magnitude of the exponent; positive exponents (>= 10 mbar) are shown in red,
  negative ones in the default color (StackWidget.setDigitColor).

Colored value fields (DisplayLabel): QLabel.setText only repaints the contents rect (and nothing if the text did
not change), but the colored background also covers the 5 px margins, so the margins kept an old color (e.g. green
frame around a yellow text area). The whole label is repainted now.

Electrometer:
- No baud rate setting anymore, always 9600 (KeithleyPAmeter.BAUDRATE), baud rate setting removed from QSettings.
- python -m Connection.KeithleyPAmeter takes no arguments, uses TEST_COMPORT = 'COM6' from the source code.
- Live plot shows the last minute only.

Icons: old icon sources (icons/src, .ai/.svg of the replaced icons) removed; the remaining logo/splash images are our
own artwork and stay.

README: script statements (PRINT, WAIT <s>, loop rule, output folder), TODOs updated and extended.

## v0.1.76 (2026-10-28)

**Script math with %, Keithley on real hardware, faster camera, Lucide icons, pressure always visible** (0801865)

Scripts:
- Basic math with the placeholder inside the function arguments is calculated (Socket/ScriptServer.py:
  substitutePlaceholder, evaluateMath with a safe AST evaluator, splitArguments, formatNumber):
  -%, %+5, %-5, %*10, %/2, (%-1)*2, %**2, abs(%), round(%,1), min(%,10), max(%,0).
  Example: PSU:voltageSet(0,%);PSU:voltageSet(1,-%) 0:10:0.5 -> symmetric Wien filter ramp.
  Arguments that are no math (e.g. 'run_%.lmf') or non-numeric values are only replaced.
- Numbers are formatted without float noise and without losing small values (ranges like 0:3e-13:1e-13
  were rounded to 0 before, :g also cut to 6 digits).

Keithley 6514 electrometer (tested on the real instrument, COM6, 9600 baud, open input ~1E-13 A):
- Simulator (Keithley6514Simulator, port "simulation") and its tests removed, also from the GUI panel.
- READ? failed with error 830 "Invalid with INFinite ARM:COUNT" (front panel/power-on mode). open() now sets
  ABOR, ARM:SOUR IMM, ARM:COUN 1, TRIG:SOUR IMM, TRIG:COUN 1 and clears old errors (setupTrigger).
- A bus INIT with an infinite arm count blocks the RS-232 parser (no answers anymore); open() sends ^C first
  (breakOperation, the instrument answers "DCL") so a blocked instrument is recovered.
- close() restores the front panel defaults with SYST:PRES (continuous readings) if the instrument was in
  continuous mode before, then local mode.
- Reading timeout at least 10 s: the first reading after switching to current with auto range took 5.4 s.
- Device routine python -m Connection.KeithleyPAmeter [COMx] [baud] passes; the Electrometer panel, zero correct,
  DB logging (scratch DB) and the CommandServer were tested with the real instrument.

Camera (Blackfly S BFS-U3-16S2M via harvesters, measured on the real camera):
- The lag came from old buffered images (stream mode OldestFirst): now NewestOnly (harvesters and PySpin).
- beamStatistics used full coordinate grids in float64 (65-80 ms per 1440x1080 image); now float32 and
  projections, same results, ~8 ms.
- Threaded workers polled their queue every 0.1 s, which limited the live view to <10 fps. They now wake up
  immediately via a threading.Event (Connection/Threaded.py) - also faster for all devices and scripts
  (commands of one script step are now ~10 ms apart instead of ~100 ms).
- Live interval 30 ms: the GUI shows ~32 fps (was ~6-10 fps), grabbing alone reaches ~200 fps.

GUI:
- Measure tab (CoboldPC) commented out in Windows/Main.py, also the CommandServer device COBOLD.
- Icons replaced by Lucide icons (SVG, ISC License, icons/LICENSE-Lucide.txt, credit in the README); old PNG
  icons removed, logo and splash screens unchanged.
- Reading age is short now ("1.2 s" / "no data" instead of "Last reading 1.2 s ago").
- Pressure panel is never scrollable (VBoxTitleLayout(scrollable=False)), the pressures are always visible.

README: script math, Lucide credit, Measure tab disabled, camera frame rates; TODOs updated and extended
(Keithley/camera follow-ups, several placeholders, Wien filter live plot, dark theme icons); literal "\n" in
several TODO lines fixed.

## v0.1.75 (2026-10-28)

**Scripts: several commands per step, ranges, results as CSV, PSU ramp + electrometer example** (ddc41c7)

Script language (Socket/ScriptServer.py):
- "A;B" executes several commands in one step (";" inside brackets or
  quotes is kept), e.g. "PSU:voltageSet(0,%);PSU:voltageSet(1,%) 0, 10"
  sets two PSU channels to the same value in each step (symmetric ramp of
  a positive and a negative channel). Resolves the "multiple commands at
  each timestep" TODO.
- Ranges "start:stop:step" (stop included, also negative steps) in the
  argument list, e.g. "0:100:0.5" instead of 201 values.
- Errors in ranges are reported with line number before the start.

Results:
- Every sent command and its answer is written to
  Scripts/results/<script>_<date>_<time>.csv with the columns time_s,
  step, command, state, answer, value (value = first number of the answer,
  e.g. the current of ELECTROMETER:readCurrent() or the mean of
  ELECTROMETER:readAverage(10)). The Scripts tab shows the file name.

Example (local file, the Scripts folder is not versioned):
Scripts/PSU ramp electrometer.lsd - channel 0 and 1 of the PSU are ramped
0 ... 10 V in 0.5 V steps, after every step one interval is waited and the
electrometer is read (mean of 10 readings), finally both are set to 0.

README: new section "Scripts" describing the script language; TODOs
updated (Wien filter GUI linking added as open point).

Tested: parser (";", quotes, ranges), end-to-end run through a
CommandServer on a spare port with a fake PSU and the simulated
electrometer (current follows the voltage), CSV content checked.

## v0.1.74 (2026-10-28)

**Electrometer (Keithley 6514) panel in the Monitor tab, logging, CommandServer** (2c5e9a4)

GUI (new Windows/Electrometer.py, Monitor tab between power meter and
camera):
- Connection: COM port (+ "simulation" for the simulated instrument),
  baud rate (must match the RS-232 menu of the instrument), reading age;
  port and baud rate are remembered, automatic reconnect.
- Settings: current range (AUTO, 20 pA ... 20 mA), NPLC, damping, zero
  check (shows the state of the instrument), "Zero correct" (procedure
  from the manual), "Live" (continuous readings, one request at a time).
- Display: last reading with SI prefix, warnings for overflow, zero check
  on and wrong function (red), plot of the last 5 minutes.
- On connect the instrument is configured for current measurement with
  the selected range/NPLC/damping; zero check stays on (safe state) until
  the user switches it off or runs a zero correction.

Database: new table "Electrometer" (Current in A, created automatically
on the next start, existing tables unchanged); only valid readings are
logged (no overflow, no zero check). Label "Electrometer Current [A]".

CommandServer/Scripts: device "ELECTROMETER" (ThreadedKeithleyConnection,
DeviceKeithleyWrapper), e.g. "ELECTROMETER:readCurrent()" or
"ELECTROMETER:readAverage(10)" -> (mean, std, n).
Measurement metadata (CoboldPC JSON) includes the electrometer.

Tested offscreen with the simulated instrument: connect, live readings,
zero check warning, zero correction, DB logging (scratch DB), readCurrent
and readAverage through a CommandServer on a spare port.

## v0.1.73 (2026-10-28)

**Keithley 6514 electrometer driver rewritten after the manual, simulator and tests** (d192651)

Connection/KeithleyPAmeter.py (Keithley 6514, RS-232/SCPI, manual
"D:/Datasheets/Keithley 6514.pdf"):
- Set commands are only written; before, every command waited for an
  answer that never came (1 s timeout per command).
- Responses are read until CR or LF, so every terminator setting of the
  instrument (LF, CR, CRLF, LFCR) works (pyserial readline only knows LF).
  Longer timeouts for READ? depending on NPLC and number of readings.
- Data format is set on connect: FORM:ELEM READ,TIME,STAT. New
  KeithleyReading (value, timestamp, status word) with overflow,
  zero_check, zero_correct and function from the status bits; overflow
  (+9.9E37) is returned as nan.
- New: read(), readAll(), readValue(), readCurrent() (switches to the
  current function if needed, warns if zero check is on), readAverage(n)
  (one READ? with trigger count n -> mean, std, number of valid readings),
  configureCurrent(range, nplc, damping), zeroCorrect() (procedure from
  the manual), set/getNPLC, median and average filter, trigger count,
  getFunction, getCurrentRange/AutoRange, get/setZeroCheck/Correct,
  getError()/getErrors() (SYST:ERR?), *OPC?, display on/off, setRemote.
- Ranges accept the enums, a value in base units or 'AUTO'.
- close() puts the instrument back into local mode (SYST:LOC), so the
  front panel can be used again (TODO resolved).
- Baud rate is a parameter (default 9600).
- Keithley6514Simulator: simulated instrument (comport "simulation") with
  settable input current and noise, zero check, ranges with overflow,
  error queue, all terminators.
- Tests: "python -m Connection.KeithleyPAmeter" runs automatic tests with
  the simulator, "python -m Connection.KeithleyPAmeter COM6 [baud]" runs a
  test routine with the real instrument (identification, error queue,
  single reading with status, average, timing for NPLC 0.1/1/10, local).
  The previous main()/average() test functions (COM6) are replaced by it.

Tested with the simulator (all tests pass). The real instrument was not
connected (no COM6), so testDevice() has not been run yet.

## v0.1.72 (2026-10-28)

**EBIS heating off is immediate, scrollbars for large panels** (33841f7)

EBIS heating current:
- Only increasing the heating current is ramped. Lowering it (e.g.
  switching the cathode heating off) is set immediately, also while a
  ramp up is running (the ramp is stopped). The pressure interlock was
  already immediate. Tooltip of "Ramp [A/min]" updated.
- Cathode current limit input range up to 10 mA (change by Alexander).

Scrollbars (Utility/Layouts.py, VBoxTitleLayout):
- The body of every panel (PSU, EBIS, Laser, Pressure, Power Meter,
  Camera, CoboldPC) is placed in a QScrollArea without frame. Scrollbars
  only appear if the panel does not fit (e.g. the EBIS panel on a small
  screen); otherwise nothing changes.
- Popping out moves the scroll area into the popout window; the popout
  window is as large as the content but at most 90 % of the screen.

Tested offscreen with the EBIS panel: 700x400 window -> scrollbars,
1400x1600 window -> none, pop out/restore.

## v0.1.71 (2026-10-18)

**Measure tab: timed CoboldPC measurements with naming format and metadata** (591f267)

CoboldPC remote control (new Connection/Cobold.py):
- Uses CoboldPCCMD.exe of the installed CoboldPC (found automatically in
  "C:/Program Files*/RoentDek Handels GmbH/CoboldPC*"), which sends a
  command to the command line of the running CoboldPC (see CoboldPC help).
- isRunning() checks the process list first, because CoboldPCCMD blocks if
  CoboldPC is not running (tested: it did not return within 15 s); every
  command has a timeout (30 s).
- startCobold(), command(), daqState() (-DAqState: 1 stopped, 2 paused,
  3 running), startMeasurement(lmf, comment) = stop if running +
  "new hardware,<lmf>,ANALYSIS" + "start", stopMeasurement() = "stop" (+
  optional configurable save command).
- buildMeasurementPath(): folder/file patterns with {name}, {date}, {time},
  {datetime}, {counter:03d}; "," and characters not allowed in file names
  are replaced; existing files are never overwritten (counter or suffix).
- ThreadedCoboldConnection, DeviceCoboldWrapper: CommandServer device
  "COBOLD", so scripts can start/stop measurements (e.g. for scans).

Measure tab (new Windows/Measure.py):
- CoboldPC state (polled every 2 s, one request at a time), "Start CoboldPC".
- Measurement: name, duration in min (0 = until stopped), measurement
  folder (remembered), comment, preview of the next file, start/stop,
  progress bar with remaining time, open folder. The measurement is
  stopped automatically after the duration (and when the GUI is closed).
- A JSON file next to the .lmf contains name, comment, file, start/stop,
  planned/real duration, stop reason, software version and the settings of
  all devices at start and stop (MainWindow.deviceSettings(): PSU and EBIS
  channels, heating, interlock state, pressures, laser, power meter).
- Start/stop are logged as events (shown in the History plots).

Settings: naming patterns and the CoboldPC commands are editable in
Settings > Preferences > CoboldPC (save command may be empty).
README: section "Measurements with CoboldPC"; TODOs updated (measure tab
TDC, start CoboldPC, measurement metadata).

Tested: naming patterns (python -m Connection.Cobold); offscreen with the
real installation (CoboldPC not running -> "Not running", start disabled,
CoboldPCCMD not called) and with a simulated CoboldPC (command sequence
new/start/stop, automatic stop after 6 s, JSON content); full main window.
CoboldPC itself was not started (its Startup.ccf starts an acquisition).

## v0.1.70 (2026-10-18)

**Camera (SpinView/FLIR) in the Monitor tab** (68e6f56)

Connection (new Connection/Camera.py):
- CameraConnection for FLIR/Teledyne cameras with the first available
  backend: PySpin (Spinnaker Python wrapper) or harvesters with the GenTL
  producer of the installed Spinnaker SDK (found automatically, e.g.
  C:/Program Files/Teledyne/Spinnaker/cti64/vs2015/Spinnaker_GenTL_v140.cti).
  Neither is installed at the moment, the panel explains what to install.
- Virtual camera (id "virtual") with a moving, noisy Gaussian laser spot
  whose brightness follows exposure and gain - for testing without
  hardware.
- Functions: listCameras(), open/close, identification, set/get exposure
  (us) and gain (dB) incl. ranges (values are clipped), continuous
  acquisition, grabImage() -> 2D numpy array, saturation value.
- beamStatistics(): maximum, saturated fraction, centroid and rms width;
  background and noise from the image border, only pixels above 3x noise
  are used (FWHM within 0.3 % on a synthetic spot).
- ThreadedCameraConnection and DeviceCameraWrapper; the camera is
  available in the CommandServer as "CAMERA".

GUI (new Windows/Camera.py, Monitor tab):
- Camera selection (+ refresh), connect/disconnect, reading age, backend
  info; exposure and gain with the values set in the camera; live image
  (one request at a time, so a slow camera does not fill the queue),
  single image, save as PNG (8 bit) + NPY (raw) into "Images/", auto
  levels, crosshair at the centroid.
- Beam: maximum/saturation (red if saturated), centroid, FWHM, frame rate.
- Last camera is remembered (not the virtual one), automatic reconnect.
- Images/ added to .gitignore, README: optional camera packages.

Tested offscreen with the virtual camera: connect, exposure, 2 s live
(6.5 fps offscreen), statistics, saving, disconnect, Monitor tab. The real
camera could not be tested (not connected and no backend installed).

## v0.1.69 (2026-10-18)

**Tooltips for Scripts, Tips, Simulation, Analyse and fit parameters** (38ffcfe)

- Fit parameter fields (StackedVBoxLayout/FittingWidget): label and value
  explain the symbol (σ, μ, c, FWHM, x0, A, mode, Counts, x₁, x₂, ∆x),
  e.g. "x0: onset of the peak (LogNorm is 0 before) - click to copy".
- Tips editor (TextEdit): all File/Format menu actions describe what they
  do incl. shortcut, tooltips are shown in the menus.
- Scripts: script list (with folder) and output.
- Simulation: list of selected simulation folders.
- Analyse: list of selected files and the histogram plot.

Checked offscreen: every button, spinbox, combobox and list of the
Scripts, Tips, Simulation and Analyse tabs has a (possibly inherited)
tooltip; only the Qt-internal toolbar overflow button and the menu titles
have none.

## v0.1.68 (2026-10-18)

**History: pressure prediction fit, min/max envelope, working splitter** (77b83ac)

Prediction fit (new Utility/PressureFit.py, new row in the History tab):
- Fits the visible part of a selected curve (pressures are preselected)
  and draws the prediction as dashed red line until 3x the fitted time
  span into the future. Result: final value p_inf, time constant/exponent,
  relative rms and when 1.1 x p_inf is reached.
- Models (all with offset p_inf = predicted final pressure):
  Exponential p(t) = p_inf + A exp(-t/tau)  - pumping of the gas volume
  Power law   p(t) = p_inf + A (t + t1)^-n  - outgassing of the walls,
              usually the better model for long times (n ~ 1 for metals)
- Relative weights (sigma = p), because pressures span several decades;
  several start values, the best result is used; a warning is shown if a
  parameter ends at its limit (model probably not suitable).
- Self tests: python -m Utility.PressureFit

Min/Max envelope:
- New toggle "Min/Max": for downsampled data the minimum and maximum of
  every time bucket are shown as shaded band around the averaged curve,
  so short pressure spikes are not averaged away.
- DB.getData(..., envelope=True) returns avg, min and max per bucket in
  one query.

Splitter:
- Bug fix: setStretchFactor(0, ...) was called twice instead of for both
  widgets. Now selection : plot = 1 : 4, and the splitter sizes are stored
  on close and restored on startup (QSettings "history_splitter_state").

Tested offscreen with a scratch DB (6 h synthetic pump down with a 5 s
spike): envelope keeps the spike (1.03E-6 vs. 8.8E-7 average), the
exponential fit gives p_inf = 2.00E-9 mbar and tau = 60 min (true
values), the power law fit warns, splitter state is stored.

## v0.1.67 (2026-10-18)

**Fitting: finished LogNorm fit, better start values and limits** (676bc37)

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

