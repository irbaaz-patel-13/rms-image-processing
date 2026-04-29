"""
RMS Image Processing – Group 9
Trial 1: Run Stage 2 (HoughCircles) with saved tuned parameters.

Reads parameters from params.TRIAL_1.
Saves all outputs to:  ../Outputs/Trial-1/

Output files
------------
  result.png   – colour image annotated with detected circles and pixel radii
  debug.png    – three-panel debug strip: [Grayscale | Blurred | Canny edges]
  circles.txt  – detected circle list: index, centre (px), radius (px)
"""

import os
import sys
import cv2
import numpy as np

# Import the saved parameter set
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from params import TRIAL_1 as P

# =============================================================================
# PATHS
# =============================================================================
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
IMAGE_PATH  = os.path.join(SCRIPT_DIR, "..", "Images", "IMG_2857.JPG")
OUTPUT_DIR  = os.path.join(SCRIPT_DIR, "..", "Outputs", "Trial-2")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# =============================================================================
# PREPROCESSING
# =============================================================================

def apply_blur(gray, method, k):
    if method == "bilateral":
        return cv2.bilateralFilter(gray, d=k, sigmaColor=75, sigmaSpace=75)
    elif method == "median":
        return cv2.medianBlur(gray, k)
    else:                               # gaussian
        return cv2.GaussianBlur(gray, (k, k), 0)


# =============================================================================
# MAIN
# =============================================================================

def main():
    # --- Load image ----------------------------------------------------------
    img = cv2.imread(IMAGE_PATH)
    if img is None:
        sys.exit(f"[ERROR] Cannot load image: {IMAGE_PATH}")

    h, w = img.shape[:2]
    print(f"[INFO] Image loaded : {w} x {h} px")
    print(f"[INFO] Output dir   : {OUTPUT_DIR}")
    print()
    print("[INFO] Parameters (TRIAL_1):")
    for k, v in P.items():
        print(f"         {k:<12} = {v}")
    print()

    # --- Preprocessing -------------------------------------------------------
    gray    = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = apply_blur(gray, P["preprocess"], P["blur"])
    edges   = cv2.Canny(blurred, P["param1"] // 2, P["param1"])

    # --- HoughCircles --------------------------------------------------------
    raw = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=P["dp"],
        minDist=P["minDist"],
        param1=P["param1"],
        param2=P["param2"],
        minRadius=P["minRadius"],
        maxRadius=P["maxRadius"],
    )

    circles = np.round(raw[0]).astype(int) if raw is not None else []
    print(f"[INFO] Circles detected: {len(circles)}")

    # --- Annotate result image -----------------------------------------------
    result = img.copy()
    for (cx, cy, r) in circles:
        cv2.circle(result, (cx, cy), r, (0, 255, 0), 2, cv2.LINE_AA)
        cv2.circle(result, (cx, cy), 4, (0, 255, 0), -1)
        cv2.putText(result, f"r={r}px", (cx - r, cy - r - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA)

    # Status bar
    bar = (f"Trial-1  Circles={len(circles)}  dp={P['dp']}  "
           f"minDist={P['minDist']}  p1={P['param1']}  p2={P['param2']}  "
           f"rMin={P['minRadius']}  rMax={P['maxRadius']}  "
           f"{P['preprocess']} k={P['blur']}")
    cv2.rectangle(result, (0, 0), (len(bar) * 8, 20), (0, 0, 0), -1)
    cv2.putText(result, bar, (5, 14),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 255, 100), 1, cv2.LINE_AA)

    # --- Build debug strip ---------------------------------------------------
    def to_bgr(img_gray):
        return cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)

    debug = np.hstack([to_bgr(gray), to_bgr(blurred), to_bgr(edges)])
    for i, lbl in enumerate(["Grayscale", f"{P['preprocess'].title()} k={P['blur']}", "Canny edges"]):
        cv2.putText(debug, lbl, (i * w + 8, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 255, 100), 1, cv2.LINE_AA)

    # --- Save outputs --------------------------------------------------------
    result_path  = os.path.join(OUTPUT_DIR, "result.png")
    debug_path   = os.path.join(OUTPUT_DIR, "debug.png")
    circles_path = os.path.join(OUTPUT_DIR, "circles.txt")

    cv2.imwrite(result_path, result)
    cv2.imwrite(debug_path,  debug)
    print(f"[SAVE] result.png → {result_path}")
    print(f"[SAVE] debug.png  → {debug_path}")

    with open(circles_path, "w") as f:
        f.write(f"Trial-1 – HoughCircles detections on {os.path.basename(IMAGE_PATH)}\n")
        f.write(f"Total detected: {len(circles)}\n\n")
        f.write(f"{'#':<4}  {'cx (px)':<10}  {'cy (px)':<10}  {'r (px)':<8}\n")
        f.write("-" * 36 + "\n")
        for i, (cx, cy, r) in enumerate(sorted(circles, key=lambda c: c[0])):
            f.write(f"{i:<4}  {cx:<10}  {cy:<10}  {r:<8}\n")
            print(f"  [{i}]  centre=({cx:>4}, {cy:>4})  radius={r}px")
    print(f"[SAVE] circles.txt → {circles_path}")


if __name__ == "__main__":
    main()
