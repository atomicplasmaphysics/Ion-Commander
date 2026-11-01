#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>


// using the A4988 with 100R testing-resistors
// NEMA   (Model. Nr  )  Rated   Vref
// NEMA8  (8HS11-0204S)  0.2 A   0.16 V
// NEMA11 (11HS20-0674S) 0.67 A  0.54 V
// NEMA14 (14HS20-1504S) 1.5 A   0.8 V (1 A); 1.2 V (1.5 A)

// ---------- Pin assignment ----------
const uint8_t PIN_DIR    = 2;
const uint8_t PIN_STEP   = 3;
const uint8_t PIN_MS1    = 4;
const uint8_t PIN_MS2    = 5;
const uint8_t PIN_MS3    = 6;
const uint8_t PIN_ENABLE = 8;
const uint8_t PIN_LIMIT1 = 9;
const uint8_t PIN_LIMIT2 = 10;

// NC switches to GND (INPUT_PULLUP):
// LOW = normal, HIGH = limit activated / wire disconnected.
// Positive direction = upward, toward TOP.

const uint8_t STEP_PULSE_US = 3;
const long MAX_POSITION = 2147483647L;
const long MIN_POSITION = (-2147483647L - 1L);

char lineBuffer[100];
uint8_t lineLength = 0;

enum Mode { FULL, HALF, QUARTER, EIGHTH, SIXTEENTH };
Mode mode = SIXTEENTH;

// Position unit is always 1/16 of a full step.
long position = 0;
long targetPosition = 0;

bool enabled = false;
bool moving = false;
int8_t motionDirection = 0;
bool zeroSet = false;          // ZERO was called since the start of the Arduino (position is lost on a restart)

// Speed and acceleration are in 1/16 steps in every mode, so changing the mode does not change the speed.
uint32_t maxSpeed = 10000;     // 1/16 steps/s
uint32_t acceleration = 0;     // 1/16 steps/s^2 (0 means instant acceleration/deceleration)
float velocity = 0.0f;         // 1/16 steps/s

uint32_t lastUpdateUs = 0;
uint32_t lastStepUs = 0;

// ---------- Utility functions ----------

long stepSize() {
  switch (mode) {
    case FULL:      return 16;
    case HALF:      return 8;
    case QUARTER:   return 4;
    case EIGHTH:    return 2;
    case SIXTEENTH: return 1;
  }
  return 1;
}

const char* modeName() {
  switch (mode) {
    case FULL:      return "FULL";
    case HALF:      return "HALF";
    case QUARTER:   return "QUARTER";
    case EIGHTH:    return "EIGHTH";
    case SIXTEENTH: return "SIXTEENTH";
  }
  return "?";
}

bool limit1Hit() {
  return digitalRead(PIN_LIMIT1) == HIGH;
}
bool limit2Hit() {
  return digitalRead(PIN_LIMIT2) == HIGH;
}

void setModePins() {
  digitalWrite(PIN_MS1, mode == HALF    || mode == EIGHTH || mode == SIXTEENTH);
  digitalWrite(PIN_MS2, mode == QUARTER || mode == EIGHTH || mode == SIXTEENTH);
  digitalWrite(PIN_MS3, mode == SIXTEENTH);
}

void reportStatus(const char* arg) {
  if (!strcmp(arg, "MODE"))        Serial.println(modeName());
  else if (!strcmp(arg, "ENABLE")) Serial.println(enabled ? 1 : 0);
  else if (!strcmp(arg, "SPEED"))  Serial.println(maxSpeed);
  else if (!strcmp(arg, "ACCEL"))  Serial.println(acceleration);
  else if (!strcmp(arg, "POS"))    Serial.println(position);  // Integer 1/16-step units
  else if (!strcmp(arg, "TARGET")) Serial.println(targetPosition);
  else if (!strcmp(arg, "MOVING")) Serial.println(moving ? 1 : 0);
  else if (!strcmp(arg, "LIMIT"))  Serial.println((limit1Hit() ? 1 : 0) | (limit2Hit() ? 2 : 0)); // Bit 0 = LIMIT1; bit 1 = LIMIT2
  else if (!strcmp(arg, "ZEROED")) Serial.println(zeroSet ? 1 : 0);
  else                             Serial.println("ERR unknown_argument");
}

void stopImmediately() {
  moving = false;
  velocity = 0.0f;
  targetPosition = position;
  motionDirection = 0;
  digitalWrite(PIN_STEP, LOW);
}

bool parseLongArg(const char* text, long &value) {
  if (text == NULL || *text == '\0') return false;

  char* endPtr;
  value = strtol(text, &endPtr, 10);
  return *endPtr == '\0' && endPtr != text;
}

void startMove(long steps) {
  if (!enabled) {
    Serial.println("ERR motor_disabled");
    return;
  }

  if (moving) {
    Serial.println("ERR already_moving");
    return;
  }

  if (steps == 0) {
    Serial.println("OK");
    return;
  }

  // Check limits before starting.
  if (steps > 0 && limit1Hit()) {
    Serial.println("ERR limit1_active");
    return;
  }

  if (steps < 0 && limit2Hit()) {
    Serial.println("ERR limit2_active");
    return;
  }

  // Convert driver steps into fixed 1/16-step position units.
  const int64_t newTarget = (int64_t)position + (int64_t)steps;

  if (newTarget > MAX_POSITION || newTarget < MIN_POSITION) {
    Serial.println("ERR position_overflow");
    return;
  }

  targetPosition = (long)newTarget;
  motionDirection = steps > 0 ? 1 : -1;
  velocity = 0.0f;
  moving = true;

  digitalWrite(PIN_DIR, motionDirection > 0 ? HIGH : LOW);
  delayMicroseconds(5);

  lastUpdateUs = micros();
  lastStepUs = lastUpdateUs;

  Serial.println("OK");
}

// ---------- Serial command processing ----------

void printHelp() {
  Serial.println("Commands:");
  Serial.println("IDN?");
  Serial.println("STATUS MODE|ENABLE|SPEED|ACCEL|POS|TARGET|MOVING|LIMIT|ZEROED");
  Serial.println("MODE FULL|HALF|QUARTER|EIGHTH|SIXTEENTH");
  Serial.println("ENABLE 0|1");
  Serial.println("MOVE <signed_steps (in_current_mode)>|ZERO");
  Serial.println("SPEED <16th_steps_per_second (1_to_100000)>");
  Serial.println("ACCEL <16th_steps_per_second_squared (0_to_100000)>");
  Serial.println("HALT");
  Serial.println("ZERO");
  Serial.println("HELP");
}

void processCommand(char* line) {
  char original[100];
  strncpy(original, line, sizeof(original) - 1);
  original[sizeof(original) - 1] = '\0';

  char* cmd = strtok(line, " \t");
  char* arg = strtok(NULL, " \t");
  char* extra = strtok(NULL, " \t");

  Serial.println(original);

  if (cmd == NULL) return;

  if (extra != NULL) {
    Serial.println("ERR too_many_arguments");
    return;
  }

  if (!strcmp(cmd, "IDN?")) {
    if (arg != NULL) {
      Serial.println("ERR unexpected_argument");
      return;
    }
    Serial.println("AdjustableDelayStage by Alexander Redl");
    return;
  }

  if (!strcmp(cmd, "STATUS")) {
    if (arg == NULL) {
      Serial.println("ERR missing_status");
      return;
    }
    if (extra != NULL) {
      Serial.println("ERR unexpected_extra");
      return;
    }
    reportStatus(arg);
    return;
  }

  if (!strcmp(cmd, "HELP")) {
    printHelp();
    return;
  }

  if (!strcmp(cmd, "ENABLE")) {
    long value;
    if (!parseLongArg(arg, value) || (value != 0 && value != 1)) {
      Serial.println("ERR use_ENABLE_0_or_1");
      return;
    }

    if (!value && moving) stopImmediately();
    enabled = value;
    digitalWrite(PIN_ENABLE, enabled ? LOW : HIGH); // A4988 ENABLE is active LOW

    Serial.println("OK");
    return;
  }

  if (!strcmp(cmd, "MODE")) {
    if (moving) {
      Serial.println("ERR stop_before_changing_mode");
      return;
    }

    if (arg == NULL) {
      Serial.println("ERR missing_mode");
      return;
    }

    Mode newMode;
    if (!strcmp(arg, "FULL"))           newMode = FULL;
    else if (!strcmp(arg, "HALF"))      newMode = HALF;
    else if (!strcmp(arg, "QUARTER"))   newMode = QUARTER;
    else if (!strcmp(arg, "EIGHTH"))    newMode = EIGHTH;
    else if (!strcmp(arg, "SIXTEENTH")) newMode = SIXTEENTH;
    else {
      Serial.println("ERR invalid_mode");
      return;
    }

    mode = newMode;
    setModePins();

    Serial.println("OK");
    return;
  }

  if (!strcmp(cmd, "SPEED") || !strcmp(cmd, "ACCEL")) {
    if (moving) {
      Serial.println("ERR stop_before_changing_speed_or_accel");
      return;
    }

    long value;
    if (!parseLongArg(arg, value) || value < 0 || value > 100000) {
      Serial.println("ERR value_must_be_0_to_100000");
      return;
    }

    // No speed would divide by zero when calculating the step interval.
    if (!strcmp(cmd, "SPEED") && value == 0) {
      Serial.println("ERR speed_must_not_be_0");
      return;
    }

    if (!strcmp(cmd, "SPEED")) maxSpeed = value;
    else acceleration = value;

    Serial.println("OK");
    return;
  }

  if (!strcmp(cmd, "MOVE")) {
    if (arg == NULL) {
      Serial.println("ERR missing_step_count");
      return;
    }

    if (!strcmp(arg, "ZERO")) {
      startMove(-position);
      return;
    }

    long steps;
    if (!parseLongArg(arg, steps)) {
      Serial.println("ERR invalid_step_count");
      return;
    }
    startMove(steps * stepSize());
    return;
  }

  if (!strcmp(cmd, "ZERO")) {
    if (moving) {
      Serial.println("ERR stop_before_zero");
      return;
    }

    position = 0;
    targetPosition = 0;
    zeroSet = true;

    Serial.println("OK");
    return;
  }

  if (!strcmp(cmd, "HALT")) {
    stopImmediately();

    Serial.println("OK");
    return;
  }

  Serial.println("ERR unknown_command");
}

// ---------- Motion control ----------

void updateMotion() {
    if (!moving || !enabled) return;

    const uint32_t now = micros();

    // The target can be between two steps of the current mode (e.g. MOVE ZERO after changing the mode): the
    // position would jump around it forever, so closer than one step is reached.
    if (labs(targetPosition - position) < stepSize()) {
        stopImmediately();
        return;
    }

    // No acceleration/deceleration ramp: run at max speed and stop abruptly.
    if (acceleration == 0) {
        velocity = maxSpeed;
    } else {
        // Determine movement direction.
        const int direction = (targetPosition > position) ? 1 : (targetPosition < position) ? -1 : 0;

        if (direction == 0) {
            stopImmediately();
            return;
        }

        // Remaining distance in 1/16 steps, the unit of the speed.
        const int64_t remainingUnits = (int64_t)targetPosition - position;
        const float remainingSteps = (float)(remainingUnits >= 0 ? remainingUnits : -remainingUnits);

        // Calculate braking speed from remaining distance.
        const float brakingSpeed = sqrtf(2.0f * acceleration * remainingSteps);

        const float desiredSpeed = (brakingSpeed < maxSpeed) ? brakingSpeed : maxSpeed;

        // Update velocity based on elapsed time (lastUpdateUs is set at the start of a move).
        const float dt = (uint32_t)(now - lastUpdateUs) / 1000000.0f;
        lastUpdateUs = now;

        if (velocity < desiredSpeed) {
            velocity += acceleration * dt;
            if (velocity > desiredSpeed) velocity = desiredSpeed;
        } else if (velocity > desiredSpeed) {
            velocity -= acceleration * dt;
            if (velocity < desiredSpeed) velocity = desiredSpeed;
        }

        if (velocity < 1.0f) velocity = 1.0f;
    }

    // Enforce the relevant limit switch.
    const int direction = (targetPosition > position) ? 1 : -1;

    if ((direction > 0 && limit1Hit()) || (direction < 0 && limit2Hit())) {
        stopImmediately();
        return;
    }

    // Generate the next step when its interval has elapsed.
    const uint32_t intervalUs = (uint32_t)(1000000.0f / velocity * stepSize());

    if ((uint32_t)(now - lastStepUs) >= intervalUs) {
        lastStepUs = now;

        digitalWrite(PIN_DIR, direction > 0 ? HIGH : LOW);
        digitalWrite(PIN_STEP, HIGH);
        delayMicroseconds(3);
        digitalWrite(PIN_STEP, LOW);

        position += direction * stepSize();
    }
}

void setup() {
  pinMode(PIN_DIR,    OUTPUT);
  pinMode(PIN_STEP,   OUTPUT);
  pinMode(PIN_MS1,    OUTPUT);
  pinMode(PIN_MS2,    OUTPUT);
  pinMode(PIN_MS3,    OUTPUT);
  pinMode(PIN_ENABLE, OUTPUT);

  pinMode(PIN_LIMIT1, INPUT_PULLUP);
  pinMode(PIN_LIMIT2, INPUT_PULLUP);

  digitalWrite(PIN_STEP,   LOW);
  digitalWrite(PIN_ENABLE, HIGH);
  setModePins();

  Serial.begin(115200);
}

void loop() {
  // Read complete newline-terminated commands.
  while (Serial.available() > 0) {
    const char c = Serial.read();

    if (c == '\r') continue;

    if (c == '\n') {
      lineBuffer[lineLength] = '\0';
      processCommand(lineBuffer);
      lineLength = 0;
    } else if (lineLength < sizeof(lineBuffer) - 1) {
      lineBuffer[lineLength++] = c;
    } else {
      lineLength = 0;
      Serial.println("ERR command_too_long");
    }
  }

  updateMotion();
}
