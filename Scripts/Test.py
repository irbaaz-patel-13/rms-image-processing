"""
RMS Image Processing – Group 9
Stage 2: Preprocessing + HoughCircles  (tuning only)

Three debug panels update live as you drag the trackbars:
  [Grayscale]  [Blurred]  [Canny edges]   ← what HoughCircles actually sees
  [Result]                                ← detected circles on the colour image

Each detected circle is labelled with its pixel radius.
Detected radii are printed to the console so you can measure the px→mm scale.

Keyboard shortcuts (click any window first):
  s   – save Result image to Images/result.png
  p   – print current parameters + detected radii to console
  q / ESC – quit

──────────────────────────────────────────────────────────────────────────────
PREPROCESSING CHOICE  (see PREPROCESS constant below)
──────────────────────────────────────────────────────────────────────────────
Three options are available:

  "gaussian"   GaussianBlur  → standard choice; fast; blurs edges slightly.
  "bilateral"  BilateralFilter → preserves sharp edges while smoothing flat
                regions; best if cup rims are losing detail under Gaussian.
                Slower, but usually better for structured objects.
  "median"     MedianBlur    → good at removing salt-and-pepper noise;
                less common for this task.

Start with "gaussian".  Switch to "bilateral" if circles are missed or the
Canny panel shows fuzzy / broken rim arcs.
──────────────────────────────────────────────────────────────────────────────
HOUGHCIRCLES METHOD CHOICE  (see HOUGH_METHOD constant below)
──────────────────────────────────────────────────────────────────────────────
  HOUGH_GRADIENT      Classic 2-stage: Canny edges → Hough vote.
                      param2 is an integer accumulator threshold.
                      Good default; well-documented.

  HOUGH_GRADIENT_ALT  Improved version (OpenCV ≥ 4.3).
                      Uses a phase-coded approach; more robust to partial
                      arcs (e.g. when part of a rim is occluded).
                      param2 changes meaning: float in [0, 1] — higher = stricter.
                      If you switch, set param2 trackbar to ~80 (= 0.80).

Start with HOUGH_GRADIENT.
"""

import os
import sys
import cv2
import numpy as np

# =============================================================================
# A. PATHS
# =============================================================================
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
IMAGE_PATH  = os.path.join(SCRIPT_DIR, "..", "Images", "test.png")
RESULT_PATH = os.path.join(SCRIPT_DIR, "..", "Images", "result.png")

# =============================================================================
# B. CHOICES  –  edit these two constants to switch approach
# =============================================================================
PREPROCESS  = "gaussian"          # "gaussian" | "bilateral" | "median"
HOUGH_METHOD = cv2.HOUGH_GRADIENT  # cv2.HOUGH_GRADIENT | cv2.HOUGH_GRADIENT_ALT

# =============================================================================
# C. DEFAULT TRACKBAR STARTING VALUES
# =============================================================================
# dp_x10: dp = value / 10  (trackbars must be integers, so we scale)
# All radii and distances are in pixels.
DEFAULT = {
    "dp_x10":    10,   # dp = 1.0
    "minDist":   80,   # minimum px between two detected centres
    "param1":   100,   # Canny high threshold (low = param1/2 automatically)
    "param2":    30,   # accumulator vote threshold; LOWER → more circles found
    "minRadius": 40,   # discard circles smaller than this (filters noise/balls)
    "maxRadius": 200,  # discard circles larger than this  (0 = no limit)
    "blur":       7,   # blur strength; forced odd by the code
}

# =============================================================================
# D. HELPERS
# =============================================================================

def get_tb(name):
    return cv2.getTrackbarPos(name, "Controls")


def preprocess(gray):
    """Apply the chosen blur and return (blurred, label_string)."""
    k = get_tb("blur") | 1          # force odd

    if PREPROCESS == "bilateral":
        # d=-1 → derived from sigmaSpace; sigmaColor=sigmaSpace for simplicity
        blurred = cv2.bilateralFilter(gray, d=k, sigmaColor=75, sigmaSpace=75)
        label = f"Bilateral (d={k})"
    elif PREPROCESS == "median":
        blurred = cv2.medianBlur(gray, k)
        label = f"Median (k={k})"
    else:                            # "gaussian"  (default)
        blurred = cv2.GaussianBlur(gray, (k, k), 0)
        label = f"Gaussian (k={k})"

    return blurred, label


def build_debug_row(gray, blurred, edges, blur_label):
    """
    Return a single wide image: [Grayscale | Blurred | Canny edges].
    All three are shown at the same height so they line up.
    """
    def to_bgr(img):
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    h, w = gray.shape
    panel = np.hstack([to_bgr(gray), to_bgr(blurred), to_bgr(edges)])

    labels = ["Grayscale", blur_label, "Canny edges"]
    for i, lbl in enumerate(labels):
        cv2.putText(panel, lbl, (i * w + 8, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 255, 100), 1, cv2.LINE_AA)
    return panel


# =============================================================================
# E. PROCESSING
# =============================================================================

def process(img_bgr):
    """Run Stage 2 with current trackbar values. Returns (result, debug, circles)."""

    dp       = max(1, get_tb("dp_x10")) / 10.0
    min_dist = max(1, get_tb("minDist"))
    param1   = max(1, get_tb("param1"))
    param2   = get_tb("param2")
    min_r    = get_tb("minRadius")
    max_r    = get_tb("maxRadius")

    # --- Preprocessing -------------------------------------------------------
    gray            = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    blurred, b_lbl  = preprocess(gray)

    # Visualise the edges HoughCircles will use (param1 drives Canny internally)
    edges = cv2.Canny(blurred, param1 // 2, param1)

    # --- HoughCircles --------------------------------------------------------
    raw = cv2.HoughCircles(
        blurred,
        HOUGH_METHOD,
        dp=dp,
        minDist=min_dist,
        param1=param1,
        param2=param2 if HOUGH_METHOD == cv2.HOUGH_GRADIENT else param2 / 100.0,
        minRadius=min_r,
        maxRadius=max_r,
    )

    circles = np.round(raw[0]).astype(int) if raw is not None else []

    # --- Annotate result image -----------------------------------------------
    result = img_bgr.copy()
    for (cx, cy, r) in circles:
        cv2.circle(result, (cx, cy), r,  (0, 255, 0), 2, cv2.LINE_AA)
        cv2.circle(result, (cx, cy), 4,  (0, 255, 0), -1)
        cv2.putText(result, f"r={r}px", (cx - r, cy - r - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA)

    # Status bar at the top of result
    n   = len(circles)
    bar = (f"Circles={n}  dp={dp:.1f}  minDist={min_dist}  "
           f"p1={param1}  p2={param2}  rMin={min_r}  rMax={max_r}  {b_lbl}")
    cv2.rectangle(result, (0, 0), (len(bar) * 8, 20), (0, 0, 0), -1)
    cv2.putText(result, bar, (5, 14),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 255, 100), 1, cv2.LINE_AA)

    debug = build_debug_row(gray, blurred, edges, b_lbl)
    return result, debug, list(circles)


# =============================================================================
# F. MAIN
# =============================================================================

def main():
    img = cv2.imread(IMAGE_PATH)
    if img is None:
        sys.exit(f"[ERROR] Cannot load: {IMAGE_PATH}")

    h, w = img.shape[:2]
    print(f"[INFO] Image: {w} x {h} px")
    print(f"[INFO] Preprocessing : {PREPROCESS}")
    print(f"[INFO] HoughCircles  : {'HOUGH_GRADIENT_ALT' if HOUGH_METHOD == cv2.HOUGH_GRADIENT_ALT else 'HOUGH_GRADIENT'}")
    print()

    # Window setup
    cv2.namedWindow("Result",   cv2.WINDOW_NORMAL)
    cv2.namedWindow("Debug",    cv2.WINDOW_NORMAL)
    cv2.namedWindow("Controls", cv2.WINDOW_NORMAL)

    disp_w = min(w, 1100)
    disp_h = int(h * disp_w / w)
    cv2.resizeWindow("Result",   disp_w,      disp_h)
    cv2.resizeWindow("Debug",    disp_w,      disp_h // 2)
    cv2.resizeWindow("Controls", 520,         310)

    # Trackbars
    def _nop(_): pass
    cv2.createTrackbar("dp_x10",    "Controls", DEFAULT["dp_x10"],    30,  _nop)
    cv2.createTrackbar("minDist",   "Controls", DEFAULT["minDist"],   500, _nop)
    cv2.createTrackbar("param1",    "Controls", DEFAULT["param1"],    300, _nop)
    cv2.createTrackbar("param2",    "Controls", DEFAULT["param2"],    150, _nop)
    cv2.createTrackbar("minRadius", "Controls", DEFAULT["minRadius"], 400, _nop)
    cv2.createTrackbar("maxRadius", "Controls", DEFAULT["maxRadius"], 600, _nop)
    cv2.createTrackbar("blur",      "Controls", DEFAULT["blur"],       31, _nop)

    print("Keyboard: s=save  p=print params  q/ESC=quit")
    print()

    last_n = -1   # track circle count changes to avoid console spam

    while True:
        result, debug, circles = process(img)

        disp_result = cv2.resize(result, (disp_w, disp_h))
        disp_debug  = cv2.resize(debug,  (disp_w, disp_h // 2))
        cv2.imshow("Result", disp_result)
        cv2.imshow("Debug",  disp_debug)

        # Print to console whenever circle count changes (handy for tuning)
        if len(circles) != last_n:
            last_n = len(circles)
            radii = sorted([r for (_, _, r) in circles])
            print(f"  Circles detected: {last_n}   radii(px): {radii}")

        key = cv2.waitKey(40) & 0xFF

        if key in (ord('q'), 27):
            break

        elif key == ord('s'):
            cv2.imwrite(RESULT_PATH, result)
            print(f"[SAVE] → {RESULT_PATH}")

        elif key == ord('p'):
            dp_x10 = get_tb("dp_x10")
            radii  = sorted([r for (_, _, r) in circles])
            print(
                f"\n--- Parameters ---\n"
                f"  PREPROCESS   = {PREPROCESS!r}\n"
                f"  dp           = {dp_x10/10:.1f}\n"
                f"  minDist      = {get_tb('minDist')}\n"
                f"  param1       = {get_tb('param1')}\n"
                f"  param2       = {get_tb('param2')}\n"
                f"  minRadius    = {get_tb('minRadius')}\n"
                f"  maxRadius    = {get_tb('maxRadius')}\n"
                f"  blur         = {get_tb('blur') | 1}\n"
                f"  circles      = {len(circles)}\n"
                f"  radii (px)   = {radii}\n"
            )

    cv2.destroyAllWindows()
    print("[INFO] Done.")


if __name__ == "__main__":
    main()
