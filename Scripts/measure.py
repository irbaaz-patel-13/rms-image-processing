"""
RMS Image Processing – Group 9
Reference-board measurement script

Core idea (adapted from the contour measurement reference):
  1. Locate the board/base in the image → get its pixel width.
  2. pixelPerMetric = board_pixel_width / BOARD_WIDTH_MM
  3. Apply to every detected cup:
       diameter_mm   = 2 * r_px / pixelPerMetric
       cup_X_mm      = (cx_px - board_TL_x) / pixelPerMetric
       cup_Y_mm      = (cy_px - board_TL_y) / pixelPerMetric

Two board-location modes  (set MODE below):
──────────────────────────────────────────
  "auto"    Finds the largest quadrilateral contour in the edge map.
            Works well when the board has a clear rectangular outline.

  "manual"  Uses BOARD_CORNERS_PX that you measure once in an image viewer.
            Use this if "auto" picks the wrong rectangle.
──────────────────────────────────────────

Outputs → Outputs/measure/
  result.png     colour image: board outline + cup circles + mm labels
  debug.png      three-panel: grayscale | blurred | edges
  circles.txt    table of cup index, centre (mm), diameter (mm)
"""

import os
import sys
import cv2
import numpy as np

# Pull in the already-tuned HoughCircles parameters
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from params import TRIAL_1 as P

# =============================================================================
# A.  PATHS
# =============================================================================
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
IMAGE_PATH  = os.path.join(SCRIPT_DIR, "..", "Images", "test.png")
OUTPUT_DIR  = os.path.join(SCRIPT_DIR, "..", "Outputs", "measure")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# =============================================================================
# B.  BOARD / REFERENCE DIMENSIONS  ← edit these
# =============================================================================
BOARD_WIDTH_MM  = 600.0   # real-world width  of the board/platform (mm)
BOARD_HEIGHT_MM = 300.0   # real-world height of the board/platform (mm)

# "auto" tries to detect the board automatically.
# "manual" uses the four pixel corners you measure below.
MODE = "auto"

# For MODE = "manual":
# Measure the four corners of the board in your image viewer.
# Order: top-left, top-right, bottom-right, bottom-left  (clockwise)
BOARD_CORNERS_PX = np.array([
    [  60,  40],   # top-left     ← replace with real pixel measurements
    [1240,  40],   # top-right
    [1240, 590],   # bottom-right
    [  60, 590],   # bottom-left
], dtype=np.float32)

# =============================================================================
# C.  GEOMETRY HELPERS
# =============================================================================

def midpoint(ptA, ptB):
    return ((ptA[0] + ptB[0]) * 0.5, (ptA[1] + ptB[1]) * 0.5)


def order_points(pts):
    """
    Order four corner points as [top-left, top-right, bottom-right, bottom-left].
    Same logic as imutils.perspective.order_points — no extra library needed.
    """
    rect = np.zeros((4, 2), dtype="float32")
    s    = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    rect[0] = pts[np.argmin(s)]     # TL: smallest (x+y)
    rect[2] = pts[np.argmax(s)]     # BR: largest  (x+y)
    rect[1] = pts[np.argmin(diff)]  # TR: smallest (y-x)
    rect[3] = pts[np.argmax(diff)]  # BL: largest  (y-x)
    return rect


def euclidean(ptA, ptB):
    return np.linalg.norm(np.array(ptA) - np.array(ptB))

# =============================================================================
# D.  BOARD DETECTION
# =============================================================================

def detect_board_auto(gray):
    """
    Find the largest quadrilateral (4-vertex) contour in the edge map.
    Returns ordered corners as float32 (TL, TR, BR, BL), or None if not found.
    """
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    edges   = cv2.Canny(blurred, 30, 90)
    edges   = cv2.dilate(edges, None, iterations=2)
    edges   = cv2.erode(edges,  None, iterations=1)

    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts    = sorted(cnts, key=cv2.contourArea, reverse=True)

    for c in cnts[:10]:              # check only the 10 largest contours
        peri   = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:         # we need exactly 4 corners
            return order_points(approx.reshape(4, 2).astype("float32"))

    return None                      # no quad found


def board_corners(gray):
    """
    Return ordered (TL, TR, BR, BL) board corners based on MODE.
    Falls back to the full image boundary if auto detection fails.
    """
    if MODE == "manual":
        return order_points(BOARD_CORNERS_PX)

    corners = detect_board_auto(gray)
    if corners is None:
        h, w = gray.shape
        print("[WARN] Auto board detection failed – using full image boundary.")
        print("       Set MODE='manual' and fill BOARD_CORNERS_PX for accuracy.")
        corners = order_points(np.array(
            [[0, 0], [w, 0], [w, h], [0, h]], dtype="float32"
        ))
    return corners

# =============================================================================
# E.  MAIN
# =============================================================================

def main():
    # --- Load ----------------------------------------------------------------
    img = cv2.imread(IMAGE_PATH)
    if img is None:
        sys.exit(f"[ERROR] Cannot load: {IMAGE_PATH}")

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    print(f"[INFO] Image : {w} x {h} px")
    print(f"[INFO] Board : {BOARD_WIDTH_MM} x {BOARD_HEIGHT_MM} mm  (MODE={MODE})")
    print()

    # --- Board detection → pixelPerMetric -----------------------------------
    (tl, tr, br, bl) = board_corners(gray)

    # Use the top edge width as the reference span (most reliable horizontal ref)
    board_px_width = euclidean(tl, tr)
    pixelPerMetric = board_px_width / BOARD_WIDTH_MM

    print(f"[INFO] Board top-edge  : {board_px_width:.1f} px  "
          f"→  pixelPerMetric = {pixelPerMetric:.4f} px/mm")
    print(f"[INFO] 1 mm = {1/pixelPerMetric:.2f} px")
    print()

    # --- HoughCircles --------------------------------------------------------
    blurred = cv2.GaussianBlur(gray, (P["blur"], P["blur"]), 0)
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

    # --- Annotate: board outline ---------------------------------------------
    result = img.copy()
    board_box = np.array([tl, tr, br, bl], dtype=np.int32)
    cv2.drawContours(result, [board_box], -1, (0, 200, 255), 2)   # orange box

    # Label board dimensions on the top and left edges
    (tltrX, tltrY) = midpoint(tl, tr)
    (tlblX, tlblY) = midpoint(tl, bl)
    board_w_px = euclidean(tl, tr)
    board_h_px = euclidean(tl, bl)
    cv2.putText(result,
                f"board {BOARD_WIDTH_MM:.0f}mm ({board_w_px:.0f}px)",
                (int(tltrX) - 80, max(int(tltrY) - 10, 15)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 200, 255), 1, cv2.LINE_AA)
    cv2.putText(result,
                f"{BOARD_HEIGHT_MM:.0f}mm ({board_h_px:.0f}px)",
                (max(int(tlblX) - 10, 0), int(tlblY)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 200, 255), 1, cv2.LINE_AA)

    # --- Annotate: cups with real-world measurements -------------------------
    records = []
    for idx, (cx, cy, r) in enumerate(sorted(circles, key=lambda c: c[0])):
        diam_mm = (2 * r) / pixelPerMetric
        x_mm    = (cx - tl[0]) / pixelPerMetric
        y_mm    = (cy - tl[1]) / pixelPerMetric

        records.append((idx, cx, cy, r, diam_mm, x_mm, y_mm))

        cv2.circle(result, (cx, cy), r, (0, 255, 0), 2, cv2.LINE_AA)
        cv2.circle(result, (cx, cy), 4, (0, 255, 0), -1)

        # Label: diameter and position in mm
        lbl1 = f"d={diam_mm:.1f}mm"
        lbl2 = f"({x_mm:.0f},{y_mm:.0f})mm"
        cv2.putText(result, lbl1, (cx - r,     cy - r - 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 0), 1, cv2.LINE_AA)
        cv2.putText(result, lbl2, (cx - r,     cy - r - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (100, 255, 255), 1, cv2.LINE_AA)

        print(f"  Cup {idx:>2} | centre=({cx:>4},{cy:>4})px "
              f"→ ({x_mm:>6.1f},{y_mm:>6.1f})mm | d={diam_mm:.1f}mm")

    # Status bar
    bar = f"pixelPerMetric={pixelPerMetric:.3f}px/mm  board={BOARD_WIDTH_MM}x{BOARD_HEIGHT_MM}mm  cups={len(circles)}"
    cv2.rectangle(result, (0, 0), (len(bar) * 8, 20), (0, 0, 0), -1)
    cv2.putText(result, bar, (5, 14),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 255, 100), 1, cv2.LINE_AA)

    # --- Debug strip ---------------------------------------------------------
    edges = cv2.Canny(blurred, P["param1"] // 2, P["param1"])

    def to_bgr(g):
        return cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)

    debug = np.hstack([to_bgr(gray), to_bgr(blurred), to_bgr(edges)])
    for i, lbl in enumerate(["Grayscale",
                              f"Gaussian k={P['blur']}",
                              f"Canny p1={P['param1']}"]):
        cv2.putText(debug, lbl, (i * w + 8, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 255, 100), 1, cv2.LINE_AA)

    # --- Save outputs --------------------------------------------------------
    result_path  = os.path.join(OUTPUT_DIR, "result.png")
    debug_path   = os.path.join(OUTPUT_DIR, "debug.png")
    circles_path = os.path.join(OUTPUT_DIR, "circles.txt")

    cv2.imwrite(result_path, result)
    cv2.imwrite(debug_path,  debug)
    print()
    print(f"[SAVE] result.png  → {result_path}")
    print(f"[SAVE] debug.png   → {debug_path}")

    with open(circles_path, "w") as f:
        f.write(f"Board reference: {BOARD_WIDTH_MM} x {BOARD_HEIGHT_MM} mm\n")
        f.write(f"pixelPerMetric : {pixelPerMetric:.4f} px/mm\n")
        f.write(f"Image          : {os.path.basename(IMAGE_PATH)}\n\n")
        f.write(f"{'#':<4}  {'cx(px)':<8}  {'cy(px)':<8}  {'r(px)':<7}"
                f"  {'X(mm)':<8}  {'Y(mm)':<8}  {'diam(mm)'}\n")
        f.write("-" * 60 + "\n")
        for (idx, cx, cy, r, diam_mm, x_mm, y_mm) in records:
            f.write(f"{idx:<4}  {cx:<8}  {cy:<8}  {r:<7}"
                    f"  {x_mm:<8.1f}  {y_mm:<8.1f}  {diam_mm:.1f}\n")
    print(f"[SAVE] circles.txt → {circles_path}")


if __name__ == "__main__":
    main()
