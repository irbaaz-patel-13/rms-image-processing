/*
 * RMS Group 9 - 4-DOF Robot Arm Controller
 *
 * Hardware:
 *   DOF 1 - Stepper motor  : base rotation about vertical axis  (pins 18/19)
 *   DOF 2 - Servo (shoulder): rotates link 1 in the vertical plane  (pin 25)
 *   DOF 3 - Servo (elbow)  : rotates link 2 relative to link 1    (pin 26)
 *   DOF 4 - Servo (gripper): opens/closes parallel gripper         (pin 27)
 *
 * Kinematic model:
 *   The arm is a 2-link planar manipulator working in a vertical plane.
 *   The stepper first rotates the base so that the arm plane faces the target.
 *   The two servos then position the wrist (end of link 2) in that plane.
 *   Inverse kinematics is solved analytically using the law of cosines.
 *
 * Coordinate system (from webcam.py):
 *   Origin = directly below the camera = directly above the robot base
 *   X_mm, Y_mm = horizontal cup position relative to origin
 *   z  = vertical, positive upward, measured from the shoulder pivot joint
 */

#include <ESP32Servo.h>
#include <math.h>

// ---- hardware pins ----
#define STEP_PIN      18
#define DIR_PIN       19
#define SHOULDER_PIN  25
#define ELBOW_PIN     26
#define GRIPPER_PIN   27

// ---- stepper: 200 steps/rev (1.8 deg per step, no microstepping) ----
#define STEPS_PER_REV  200
#define STEP_DELAY_US  1500   // microseconds between pulses - reduce carefully or it stalls

// ---- link lengths in mm - keep in sync with robot-kin.py ----
#define L1  200.0f   // shoulder to elbow
#define L2  200.0f   // elbow to end effector (wrist)

/*
 * Arm geometry (measure on the physical robot):
 *
 *              shoulder pivot
 *                   |
 *                   |  <- SHOULDER_HEIGHT_MM above table
 *   ________________|________________  <- table surface
 *
 *   GRIPPER_OFFSET_MM = distance from wrist (end of L2) down to gripper tip.
 *   The IK targets the wrist, so we subtract this offset from the z target
 *   to make the gripper tip actually reach the cup.
 *
 *   LIFT_HEIGHT_MM = how far to raise the cup vertically after gripping.
 */
#define SHOULDER_HEIGHT_MM  150.0f
#define GRIPPER_OFFSET_MM    30.0f
#define LIFT_HEIGHT_MM       60.0f

// ---- servo limits (degrees) - prevent mechanical damage ----
#define SHOULDER_MIN  10
#define SHOULDER_MAX 160
#define ELBOW_MIN     10
#define ELBOW_MAX    160
#define GRIPPER_OPEN   50
#define GRIPPER_CLOSE 120

// ---- home position (arm folded upright, base at 0) ----
#define HOME_SHOULDER  90   // link 1 pointing straight up
#define HOME_ELBOW     10   // link 2 nearly parallel to link 1, compact

// ---- serial ----
#define BAUD_RATE  115200
#define LINE_BUF   128
#define MAX_CUPS    20


// =============================================================================
// KINEMATICS
// =============================================================================

/*
 * ArmAngles holds the solution for all three revolute joints.
 * All angles are in radians - they are only converted to degrees
 * at the point of writing to the servo.
 *
 *   base     - rotation of the stepper around the vertical axis
 *              (0 = startup orientation, positive = anticlockwise when viewed from above)
 *   shoulder - angle of link 1 above horizontal in the vertical arm plane
 *              (0 = horizontal forward,  pi/2 = straight up)
 *   elbow    - angle between link 1 and link 2
 *              (0 = fully extended,  pi = fully folded back)
 *   valid    - 1 if the target is reachable, 0 if not
 */
typedef struct {
    float base;       // radians
    float shoulder;   // radians
    float elbow;      // radians
    int   valid;      // 1 = reachable, 0 = out of range
} ArmAngles;


/*
 * solveIK  -  analytical inverse kinematics for the 2-link planar arm
 *
 * Arguments:
 *   x, y  - horizontal position of the target (mm), relative to robot base
 *   z     - vertical position of the target (mm), relative to shoulder pivot
 *             positive = above shoulder,  negative = below shoulder
 *
 * Method:
 *   Step 1. Base rotation
 *     The stepper rotates the arm plane to face the target.
 *     theta_base = atan2(y, x)
 *     This is the standard horizontal bearing to the point (x, y).
 *
 *   Step 2. Reduce to a 2D problem
 *     Once the base has rotated, the arm only needs to move in the vertical
 *     plane that contains the target.  The horizontal reach in that plane is:
 *       r = sqrt(x^2 + y^2)
 *     The arm now needs to place the wrist at point (r, z) in this 2D plane.
 *
 *   Step 3. Reachability
 *     The straight-line distance from shoulder to target:
 *       d = sqrt(r^2 + z^2)
 *     The target is reachable only if:
 *       |L1 - L2| <= d <= L1 + L2
 *
 *   Step 4. Elbow angle  (law of cosines on the shoulder-elbow-wrist triangle)
 *     In the triangle formed by L1, L2, and d:
 *       cos(theta_elbow) = (d^2 - L1^2 - L2^2) / (2 * L1 * L2)
 *     This gives the "elbow-up" configuration (elbow above the line shoulder->wrist).
 *
 *   Step 5. Shoulder angle  (two-step decomposition)
 *     alpha  = atan2(z, r)
 *       This is the angle from horizontal to the straight line shoulder->wrist.
 *     alpha2 = acos((L1^2 + d^2 - L2^2) / (2 * L1 * d))
 *       This is the angle between the shoulder->wrist line and link 1,
 *       again from the law of cosines on the same triangle.
 *     theta_shoulder = alpha + alpha2
 */
ArmAngles solveIK(float x, float y, float z) {
    ArmAngles result;
    result.valid = 0;

    // Step 1: base rotation - horizontal bearing to (x, y)
    result.base = atan2f(y, x);

    // Step 2: reduce to 2D - horizontal reach r in the arm plane
    float r = sqrtf(x*x + y*y);

    // Step 3: straight-line distance from shoulder joint to target wrist point
    float d = sqrtf(r*r + z*z);

    // reachability check - target must lie within the annular workspace
    if (d > (L1 + L2) || d < fabsf(L1 - L2)) {
        // target is outside the arm's workspace - return invalid
        return result;
    }

    // Step 4: elbow angle via law of cosines
    //   cosElbow can drift slightly outside [-1, 1] due to floating-point error
    //   at the workspace boundary, so clamp it before calling acosf
    float cosElbow = (d*d - L1*L1 - L2*L2) / (2.0f * L1 * L2);
    cosElbow = fmaxf(-1.0f, fminf(1.0f, cosElbow));
    result.elbow = acosf(cosElbow);   // elbow-up solution

    // Step 5: shoulder angle
    //   alpha  = angle from horizontal to the shoulder->wrist straight line
    //   alpha2 = angle between that line and link 1 (law of cosines)
    float alpha    = atan2f(z, r);
    float cosAlpha2 = (L1*L1 + d*d - L2*L2) / (2.0f * L1 * d);
    cosAlpha2 = fmaxf(-1.0f, fminf(1.0f, cosAlpha2));
    float alpha2   = acosf(cosAlpha2);
    result.shoulder = alpha + alpha2;

    result.valid = 1;
    return result;
}


// Print the IK solution to Serial (angles converted to degrees for readability)
void printAngles(const char* label, ArmAngles a) {
    Serial.print(label);
    if (!a.valid) {
        Serial.println(" -> UNREACHABLE");
        return;
    }
    Serial.print("  base=");     Serial.print(a.base     * (180.0f / M_PI), 1); Serial.print("deg");
    Serial.print("  shoulder="); Serial.print(a.shoulder * (180.0f / M_PI), 1); Serial.print("deg");
    Serial.print("  elbow=");    Serial.print(a.elbow    * (180.0f / M_PI), 1); Serial.println("deg");
}


// =============================================================================
// HARDWARE DRIVERS
// =============================================================================

Servo shoulderSrv, elbowSrv, gripperSrv;
long  stepPos = 0;   // current stepper position in steps (0 = startup = 0 deg)


// Move stepper to an absolute step count
void stepperMoveTo(long target) {
    if (target == stepPos) return;
    digitalWrite(DIR_PIN, (target > stepPos) ? HIGH : LOW);
    long n = abs(target - stepPos);
    for (long i = 0; i < n; i++) {
        digitalWrite(STEP_PIN, HIGH);  delayMicroseconds(STEP_DELAY_US);
        digitalWrite(STEP_PIN, LOW);   delayMicroseconds(STEP_DELAY_US);
    }
    stepPos = target;
}

// Rotate base to an absolute angle in degrees
void baseRotateDeg(float deg) {
    long target = (long)((deg / 360.0f) * STEPS_PER_REV);
    stepperMoveTo(target);
}

// Write a servo angle clamped to safe limits
void writeServo(Servo& s, float rad, int limitLo, int limitHi) {
    int deg = (int)(rad * (180.0f / M_PI));
    s.write(constrain(deg, limitLo, limitHi));
}

void goHome() {
    // fold elbow first to avoid the arm swinging wide
    elbowSrv.write(HOME_ELBOW);       delay(400);
    shoulderSrv.write(HOME_SHOULDER); delay(500);
    baseRotateDeg(0.0f);
    Serial.println("[ARM] home position reached");
}


// =============================================================================
// PICK SEQUENCE
// =============================================================================

/*
 * pickCup  -  full pick-and-lift sequence for one cup
 *
 * x_mm, y_mm : cup position from webcam (relative to camera nadir = robot base)
 *
 * The wrist target z coordinates are derived from the physical geometry:
 *
 *   z_reach = -(SHOULDER_HEIGHT_MM - GRIPPER_OFFSET_MM)
 *
 *     The shoulder is SHOULDER_HEIGHT_MM above the table.
 *     The gripper tip extends GRIPPER_OFFSET_MM below the wrist.
 *     So to place the gripper tip at table level the wrist must be at:
 *       z_wrist = -SHOULDER_HEIGHT_MM + GRIPPER_OFFSET_MM
 *     (negative because the table is below the shoulder pivot)
 *
 *   z_lift  = z_reach + LIFT_HEIGHT_MM
 *     After gripping, raise the wrist by LIFT_HEIGHT_MM.
 */
void pickCup(float x_mm, float y_mm) {

    // ------------------------------------------------------------------
    // 1. Solve IK for the reach position (gripper at table level)
    // ------------------------------------------------------------------
    float z_reach = -(SHOULDER_HEIGHT_MM - GRIPPER_OFFSET_MM);   // e.g. -120 mm
    ArmAngles ikReach = solveIK(x_mm, y_mm, z_reach);
    printAngles("[IK] reach", ikReach);

    if (!ikReach.valid) {
        Serial.println("[ARM] reach position unreachable - skipping cup");
        return;
    }

    // ------------------------------------------------------------------
    // 2. Solve IK for the lift position (cup raised off table)
    // ------------------------------------------------------------------
    float z_lift = z_reach + LIFT_HEIGHT_MM;
    ArmAngles ikLift = solveIK(x_mm, y_mm, z_lift);
    printAngles("[IK] lift ", ikLift);

    if (!ikLift.valid) {
        Serial.println("[ARM] lift position unreachable - attempting half lift");
        ikLift = solveIK(x_mm, y_mm, z_reach + LIFT_HEIGHT_MM * 0.5f);
        if (!ikLift.valid) {
            Serial.println("[ARM] half lift also unreachable - aborting");
            return;
        }
    }

    // ------------------------------------------------------------------
    // 3. Execute motion
    // ------------------------------------------------------------------

    // --- rotate base ---
    // base angle is in radians from solveIK; convert to degrees for stepper
    float baseDeg = ikReach.base * (180.0f / M_PI);
    Serial.print("[ARM] rotating base to "); Serial.print(baseDeg, 1); Serial.println(" deg");
    baseRotateDeg(baseDeg);
    delay(300);

    // --- extend arm to reach position ---
    // move shoulder before elbow to reduce risk of the arm tip hitting the table
    Serial.println("[ARM] extending to reach position");
    writeServo(shoulderSrv, ikReach.shoulder, SHOULDER_MIN, SHOULDER_MAX); delay(400);
    writeServo(elbowSrv,    ikReach.elbow,    ELBOW_MIN,    ELBOW_MAX);    delay(700);

    // --- close gripper ---
    gripperSrv.write(GRIPPER_CLOSE);
    Serial.println("[ARM] gripper closed");
    delay(600);

    // --- lift ---
    Serial.println("[ARM] lifting cup");
    writeServo(shoulderSrv, ikLift.shoulder, SHOULDER_MIN, SHOULDER_MAX); delay(400);
    writeServo(elbowSrv,    ikLift.elbow,    ELBOW_MIN,    ELBOW_MAX);    delay(600);

    // --- return home and release ---
    delay(300);
    goHome();
    delay(400);
    gripperSrv.write(GRIPPER_OPEN);
    Serial.println("[ARM] gripper open - cup released");
}


// =============================================================================
// SERIAL PROTOCOL  (matches webcam.py: CAPTURE,n / CUP,... / END)
// =============================================================================

struct CupData {
    int   idx;
    float x_mm, y_mm, diam_mm;
    char  type[16];
};

CupData cups[MAX_CUPS];
int  cupCnt   = 0;
int  n_exp    = 0;
bool doPickSeq = false;

char lineBuf[LINE_BUF];
int  bufPos = 0;

void parseLine(const char* line) {

    // CAPTURE,n  - start of a new batch
    if (strncmp(line, "CAPTURE,", 8) == 0) {
        n_exp     = atoi(line + 8);
        cupCnt    = 0;
        doPickSeq = false;
        Serial.print("[RX] expecting "); Serial.print(n_exp); Serial.println(" cup(s)");
        return;
    }

    // CUP,i,cx_px,cy_px,diam_mm,X_mm,Y_mm,type
    if (strncmp(line, "CUP,", 4) == 0 && cupCnt < MAX_CUPS) {
        CupData& c = cups[cupCnt];
        char buf[LINE_BUF];
        strncpy(buf, line + 4, LINE_BUF - 1);
        buf[LINE_BUF - 1] = '\0';

        char* tok = strtok(buf, ",");
        if (tok) c.idx    = atoi(tok);
        tok = strtok(NULL, ",");             // cx_px - skip, not needed for kinematics
        tok = strtok(NULL, ",");             // cy_px - skip
        tok = strtok(NULL, ",");
        if (tok) c.diam_mm = atof(tok);
        tok = strtok(NULL, ",");
        if (tok) c.x_mm   = atof(tok);      // world X in mm from webcam
        tok = strtok(NULL, ",");
        if (tok) c.y_mm   = atof(tok);      // world Y in mm from webcam
        tok = strtok(NULL, ",");
        if (tok) { strncpy(c.type, tok, 15); c.type[15] = '\0'; }

        Serial.print("[RX] cup "); Serial.print(c.idx);
        Serial.print("  ("); Serial.print(c.x_mm, 1);
        Serial.print(", "); Serial.print(c.y_mm, 1);
        Serial.print(") mm  d="); Serial.print(c.diam_mm, 1);
        Serial.print(" mm  "); Serial.println(c.type);

        cupCnt++;
        return;
    }

    // END  - all cups sent, send ACK then trigger pick sequence
    if (strcmp(line, "END") == 0) {
        Serial.print("ACK,"); Serial.println(cupCnt);
        if (cupCnt == n_exp) {
            Serial.println("[RX] all cups received - starting pick sequence");
            doPickSeq = true;
        } else {
            Serial.print("[RX] MISMATCH expected="); Serial.print(n_exp);
            Serial.print(" received="); Serial.println(cupCnt);
        }
    }
}


// =============================================================================
// SETUP / LOOP
// =============================================================================

void setup() {
    Serial.begin(BAUD_RATE);
    while (!Serial) { delay(10); }

    pinMode(STEP_PIN, OUTPUT);
    pinMode(DIR_PIN,  OUTPUT);

    delay(200);  // let power rails settle before attaching servos
    shoulderSrv.attach(SHOULDER_PIN);
    elbowSrv.attach(ELBOW_PIN);
    gripperSrv.attach(GRIPPER_PIN);
    delay(200);

    gripperSrv.write(GRIPPER_OPEN);
    delay(300);
    goHome();

    Serial.println("[ARM] ready - send cup data from webcam.py");
}

void loop() {
    // read incoming serial one character at a time, parse on newline
    while (Serial.available()) {
        char ch = (char)Serial.read();
        if (ch == '\n' || ch == '\r') {
            if (bufPos > 0) {
                lineBuf[bufPos] = '\0';
                parseLine(lineBuf);
                bufPos = 0;
            }
        } else if (bufPos < LINE_BUF - 1) {
            lineBuf[bufPos++] = ch;
        }
    }

    // execute pick sequence once all cup data has arrived
    if (doPickSeq) {
        doPickSeq = false;
        for (int i = 0; i < cupCnt; i++) {
            Serial.print("\n[ARM] ---- cup "); Serial.print(i);
            Serial.print("  ("); Serial.print(cups[i].x_mm, 1);
            Serial.print(", "); Serial.print(cups[i].y_mm, 1); Serial.println(") mm ----");
            pickCup(cups[i].x_mm, cups[i].y_mm);
            delay(500);
        }
        Serial.println("[ARM] sequence complete");
    }
}
