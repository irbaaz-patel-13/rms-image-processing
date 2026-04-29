# RMS Group 9 - webcam capture + cup detection
# camera must be mounted overhead at CAMERA_HEIGHT_MM above the table
# press C to capture and run detection, Q to quit

import os
import sys
import math
import time
import cv2
import numpy as np
import serial
import serial.tools.list_ports

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# --- edit these before running ---
CAMERA_INDEX     = 1        # 0 = laptop cam, 1 = USB webcam
CAMERA_HEIGHT_MM = 460.0    # height of camera above table in mm
CAMERA_HFOV_DEG  = 60.0     # horizontal FOV in degrees (check webcam spec sheet)

# cup diameter ranges in mm
PINT_DIAM_MM      = (70, 90)
HALF_PINT_DIAM_MM = (50, 60)
SHOT_DIAM_MM      = (40, 50)

MIN_CUP_DIAM_MM = min(SHOT_DIAM_MM[0], HALF_PINT_DIAM_MM[0], PINT_DIAM_MM[0])
MAX_CUP_DIAM_MM = max(SHOT_DIAM_MM[1], HALF_PINT_DIAM_MM[1], PINT_DIAM_MM[1])

# cups have bright white interiors - circles with mean inner brightness below this are noise
# FIXME: may need lowering to ~100 in dim lighting conditions
CUP_INTERIOR_MIN_BRIGHTNESS = 150

# ESP32 serial - change COM port to match device manager
SERIAL_PORT    = "COM3"
SERIAL_BAUD    = 115200
SERIAL_TIMEOUT = 3

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Outputs", "webcam")
os.makedirs(OUTPUT_DIR, exist_ok=True)

COLORS = {
    "Pint":      (0,   255,   0),
    "Half-Pint": (0,   200, 255),
    "Shot":      (255, 120,   0),
    "Unknown":   (150, 150, 150),
}

def calc_ppm(img_w):
    # pixels per mm derived from camera geometry
    return img_w / (2.0 * CAMERA_HEIGHT_MM * math.tan(math.radians(CAMERA_HFOV_DEG) / 2.0))


def get_r_range(ppm, slack=0.25):
    r_min = max(8, int((MIN_CUP_DIAM_MM / 2.0) * ppm * (1.0 - slack)))
    r_max = int((MAX_CUP_DIAM_MM / 2.0) * ppm * (1.0 + slack))
    return r_min, r_max


def classify(diam_mm):
    if PINT_DIAM_MM[0]      <= diam_mm <= PINT_DIAM_MM[1]:      return "Pint"
    if HALF_PINT_DIAM_MM[0] <= diam_mm <= HALF_PINT_DIAM_MM[1]: return "Half-Pint"
    if SHOT_DIAM_MM[0]      <= diam_mm <= SHOT_DIAM_MM[1]:       return "Shot"
    return "Unknown"


def inner_brightness(gray, cx, cy, r):
    # mean brightness of pixels inside the inner 60% of the circle
    inner_r = max(1, int(r * 0.6))
    mask = np.zeros_like(gray)
    cv2.circle(mask, (cx, cy), inner_r, 255, -1)
    px = gray[mask > 0]
    return float(px.mean()) if px.size else 0.0


def nms(circles, thresh=0.7):
    # remove overlapping circles, keep the larger one
    circles = sorted(circles, key=lambda c: -c[2])
    kept = []
    for cx, cy, r in circles:
        if all(math.hypot(cx - kx, cy - ky) > thresh * max(r, kr) for kx, ky, kr in kept):
            kept.append((cx, cy, r))
    return kept


def detect_cups(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    ppm = calc_ppm(w)
    r_min, r_max = get_r_range(ppm)
    min_dist = int(r_min * 1.5)

    # tried gaussian but bilateral keeps the rim edges sharper
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    processed = cv2.bilateralFilter(clahe.apply(gray), d=9, sigmaColor=50, sigmaSpace=50)

    raw_circ = []
    # sweep param2 strict to lenient, stop as soon as we get candidates
    for p2 in (50, 40, 30, 22):
        raw = cv2.HoughCircles(processed, cv2.HOUGH_GRADIENT,
                               dp=1.2, minDist=min_dist, param1=60, param2=p2,
                               minRadius=r_min, maxRadius=r_max)
        if raw is not None:
            raw_circ = np.round(raw[0]).astype(int).tolist()
            if len(raw_circ) >= 1:
                break

    # print(f"debug: hough raw count before filtering = {len(raw_circ)}")

    # drop detections whose centre is too close to the frame edge
    raw_circ = [(cx, cy, r) for cx, cy, r in raw_circ
                if r * 0.35 < cx < w - r * 0.35 and r * 0.35 < cy < h - r * 0.35]

    # cups are white inside so dark-interior circles are false positives
    raw_circ = [(cx, cy, r) for cx, cy, r in raw_circ
                if inner_brightness(gray, cx, cy, r) >= CUP_INTERIOR_MIN_BRIGHTNESS]

    return nms(raw_circ), ppm


def draw_results(frame, circles, ppm):
    result = frame.copy()
    h, w = frame.shape[:2]
    cx_img = w / 2.0
    cy_img = h / 2.0

    for cx, cy, r in sorted(circles, key=lambda c: c[0]):
        diam_mm = (2 * r) / ppm
        cup_type = classify(diam_mm)
        col = COLORS[cup_type]
        x_mm = (cx - cx_img) / ppm
        y_mm = (cy - cy_img) / ppm

        cv2.circle(result, (cx, cy), r, col, 2, cv2.LINE_AA)
        cv2.circle(result, (cx, cy), 4, col, -1)
        cv2.putText(result, f"{cup_type} {diam_mm:.0f}mm", (cx - r, cy - r - 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1, cv2.LINE_AA)
        cv2.putText(result, f"({x_mm:+.0f},{y_mm:+.0f})mm", (cx - r, cy - r - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, col, 1, cv2.LINE_AA)

    bar = f"cups={len(circles)}  ppm={ppm:.3f}px/mm  H={CAMERA_HEIGHT_MM}mm  HFOV={CAMERA_HFOV_DEG}deg  brightThresh={CUP_INTERIOR_MIN_BRIGHTNESS}"
    cv2.rectangle(result, (0, 0), (len(bar) * 8, 20), (0, 0, 0), -1)
    cv2.putText(result, bar, (5, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 255, 100), 1, cv2.LINE_AA)
    return result


def save_result(frame, circles, ppm, cap_n):
    h, w = frame.shape[:2]
    cx_img = w / 2.0
    cy_img = h / 2.0
    result = draw_results(frame, circles, ppm)

    tag = f"capture_{cap_n:04d}"
    raw_path    = os.path.join(OUTPUT_DIR, f"{tag}.png")
    result_path = os.path.join(OUTPUT_DIR, f"{tag}_result.png")
    txt_path    = os.path.join(OUTPUT_DIR, f"{tag}.txt")

    cv2.imwrite(raw_path, frame)
    cv2.imwrite(result_path, result)

    with open(txt_path, "w") as f:
        f.write(f"Capture #{cap_n}\n")
        f.write(f"Image          : {w}x{h} px\n")
        f.write(f"Camera height  : {CAMERA_HEIGHT_MM} mm\n")
        f.write(f"HFOV           : {CAMERA_HFOV_DEG} deg\n")
        f.write(f"ppm            : {ppm:.4f} px/mm\n")
        f.write(f"Brightness thr : {CUP_INTERIOR_MIN_BRIGHTNESS}\n")
        f.write(f"Cups detected  : {len(circles)}\n\n")
        f.write(f"{'#':<4}  {'cx_px':>6}  {'cy_px':>6}  {'r_px':>5}  {'diam_mm':>8}  {'X_mm':>7}  {'Y_mm':>7}  type\n")
        f.write("-" * 62 + "\n")
        for i, (cx, cy, r) in enumerate(sorted(circles, key=lambda c: c[0])):
            diam_mm  = (2 * r) / ppm
            x_mm     = (cx - cx_img) / ppm
            y_mm     = (cy - cy_img) / ppm
            cup_type = classify(diam_mm)
            f.write(f"{i:<4}  {cx:>6}  {cy:>6}  {r:>5}  {diam_mm:>8.1f}  {x_mm:>+7.1f}  {y_mm:>+7.1f}  {cup_type}\n")
            print(f"  Cup {i}: ({cx},{cy})px  r={r}px  d={diam_mm:.1f}mm  pos=({x_mm:+.0f},{y_mm:+.0f})mm  -> {cup_type}")

    print(f"  saved: {raw_path}")
    print(f"  saved: {result_path}")
    print(f"  saved: {txt_path}")
    return result


def send_to_esp32(circles, ppm, img_w, img_h):
    cx_img = img_w / 2.0
    cy_img = img_h / 2.0

    cup_list = sorted(circles, key=lambda c: c[0])

    lines = [f"CAPTURE,{len(cup_list)}"]
    for i, (cx, cy, r) in enumerate(cup_list):
        diam_mm  = round((2 * r) / ppm, 1)
        x_mm     = round((cx - cx_img) / ppm, 1)
        y_mm     = round((cy - cy_img) / ppm, 1)
        cup_type = classify(diam_mm)
        lines.append(f"CUP,{i},{cx},{cy},{diam_mm},{x_mm},{y_mm},{cup_type}")
    lines.append("END")

    print(f"\n[ESP32] connecting to {SERIAL_PORT} @ {SERIAL_BAUD} baud...")

    try:
        with serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=SERIAL_TIMEOUT) as ser:
            time.sleep(1.5)  # this delay is needed or the ESP32 hasn't finished resetting
            ser.reset_input_buffer()

            print(f"[ESP32] sending {len(cup_list)} cup(s):")
            for line in lines:
                ser.write((line + "\n").encode("ascii"))
                print(f"  TX: {line}")
                time.sleep(0.02)

            # ESP32 sends debug prints before ACK so keep reading until we see ACK
            print("[ESP32] waiting for ACK...")
            deadline = time.time() + SERIAL_TIMEOUT
            ack_line = None

            while time.time() < deadline:
                rx = ser.readline().decode("ascii", errors="replace").strip()
                if not rx:
                    continue
                print(f"[ESP32] RX: {rx}")
                if rx.startswith("ACK,"):
                    ack_line = rx
                    break

            if ack_line is None:
                print(f"[ESP32] timeout - no ACK received within {SERIAL_TIMEOUT}s")
                return

            try:
                n_ack = int(ack_line.split(",")[1])
            except Exception:
                n_ack = -1

            if n_ack == len(cup_list):
                print(f"[ESP32] PASS - confirmed {n_ack} cup(s) received ok")
            else:
                print(f"[ESP32] MISMATCH - sent {len(cup_list)}, ESP32 got {n_ack}")

    except serial.SerialException as e:
        print(f"[ESP32] error - couldn't open {SERIAL_PORT}: {e}")
        print("[ESP32] available ports:")
        for p in serial.tools.list_ports.comports():
            print(f"  {p.device} - {p.description}")


def init_camera():
    # DirectShow avoids the MSMF grab errors that crash the feed on Windows
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if cap.isOpened():
        time.sleep(0.5)
        ok, _ = cap.read()
        if ok:
            print(f"[CAM] opened index {CAMERA_INDEX} via DirectShow")
            return cap
        cap.release()

    for idx in range(4):
        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            time.sleep(0.5)
            ok, _ = cap.read()
            if ok:
                print(f"[CAM] opened index {idx} (fallback)")
                return cap
        cap.release()

    sys.exit("ERROR: no webcam found - check USB connection or change CAMERA_INDEX")


def main():
    cap = init_camera()

    w_cam = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h_cam = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps   = cap.get(cv2.CAP_PROP_FPS)
    ppm_est = calc_ppm(w_cam)
    r_min, r_max = get_r_range(ppm_est)

    print(f"[CAM] {w_cam}x{h_cam}  FPS={fps:.1f}  backend={cap.getBackendName()}")
    print(f"[CAM] H={CAMERA_HEIGHT_MM}mm  HFOV={CAMERA_HFOV_DEG}deg  ppm~{ppm_est:.3f}  r=[{r_min},{r_max}]px")
    print("\n  C - capture + detect cups\n  Q / ESC - quit\n")

    win_w = min(w_cam, 1280)
    win_h = min(h_cam, 720)
    cv2.namedWindow("Live", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Live", win_w, win_h)

    # TODO: could persist cap_n between runs by reading last capture index from output folder
    cap_n = 0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.1)
                ok, frame = cap.read()
            if not ok:
                print("ERROR: camera stopped sending frames")
                break

            view = frame.copy()
            cv2.putText(view, "C=capture  Q=quit", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.imshow("Live", view)

            key = cv2.waitKey(30) & 0xFF

            if key in (ord('q'), ord('Q'), 27):
                break
            elif key in (ord('c'), ord('C')):
                print(f"\n[CAPTURE #{cap_n}] detecting...")
                circles, ppm = detect_cups(frame)
                fH, fW = frame.shape[:2]
                print(f"  found {len(circles)} cup(s)  ppm={ppm:.3f}")
                result = save_result(frame, circles, ppm, cap_n)
                send_to_esp32(circles, ppm, fW, fH)

                wname = f"Result #{cap_n}"
                cv2.namedWindow(wname, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(wname, win_w, win_h)
                cv2.imshow(wname, result)
                cap_n += 1

    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("\ncamera released, done.")


if __name__ == "__main__":
    main()
