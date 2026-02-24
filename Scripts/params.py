"""
Saved HoughCircles parameter sets – Group 9
============================================
Each entry is a dictionary of tuned values from one interactive tuning session.
Import whichever set you need in your trial scripts:

    from params import TRIAL_1
"""

# Trial 1 – tuned on Images/test.png
# Status bar reading: Circles=12  dp=0.8  minDist=211  p1=158  p2=32
#                     rMin=44  rMax=131  Gaussian (k=11)
TRIAL_1 = {
    "preprocess":  "gaussian",  # blur method: "gaussian" | "bilateral" | "median"
    "dp":          0.8,         # accumulator resolution ratio
    "minDist":     211,         # min px between circle centres
    "param1":      158,         # Canny high threshold
    "param2":      32,          # accumulator vote threshold
    "minRadius":   44,          # px – hard lower bound
    "maxRadius":   131,         # px – hard upper bound
    "blur":        11,          # Gaussian kernel size (must be odd)
}
