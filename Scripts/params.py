"""
Saved HoughCircles parameter sets – Group 9
============================================
Each entry is a dictionary of tuned values from one interactive tuning session.
Import whichever set you need in your trial scripts:

    from params import TRIAL_1
    from params import TRIAL_2
    from params import ALL_TRIALS   # list of all sets, used by webcam.py
"""

# Trial 1 – tuned on Images/test.png
# Status bar reading: Circles=12  dp=0.8  minDist=211  p1=158  p2=32
#                     rMin=44  rMax=131  Gaussian (k=11)
TRIAL_1 = {
    "label":       "Trial1",
    "preprocess":  "gaussian",  # blur method: "gaussian" | "bilateral" | "median"
    "dp":          0.8,         # accumulator resolution ratio
    "minDist":     211,         # min px between circle centres
    "param1":      158,         # Canny high threshold
    "param2":      32,          # accumulator vote threshold
    "minRadius":   44,          # px – hard lower bound
    "maxRadius":   131,         # px – hard upper bound
    "blur":        11,          # Gaussian kernel size (must be odd)
}

# Trial 2 – recalibrated on Images/IMG_2856.jpeg
# Controls reading: dp=1.2  minDist=182  p1=60  p2=86
#                   rMin=334  rMax=597  blur=3
TRIAL_2 = {
    "label":       "Trial2",
    "preprocess":  "gaussian",
    "dp":          1.2,
    "minDist":     182,
    "param1":      60,
    "param2":      86,
    "minRadius":   334,
    "maxRadius":   597,
    "blur":        3,           # must be odd – 3 is valid
}

# All trials in one list – webcam.py iterates this to test every set
ALL_TRIALS = [TRIAL_1, TRIAL_2]
