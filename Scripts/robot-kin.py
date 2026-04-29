import math
from dataclasses import dataclass

# Link lengths in mm
L1 = 200.0  # shoulder to elbow
L2 = 200.0  # elbow to end effector

@dataclass
class ArmAngles:
    base: float = 0.0       # radians
    shoulder: float = 0.0   # radians
    elbow: float = 0.0      # radians
    valid: int = 0          # 1 = reachable, 0 = out of range


def solve_ik(x, y, z):
    result = ArmAngles()

    # 🔴 Removed incorrect hardcoding from original code:
    # x = 5; y = 10; z = 8

    # Joint 1: Base rotation
    result.base = math.atan2(y, x)

    # Radial distance in horizontal plane
    r = math.sqrt(x**2 + y**2)

    # Distance from shoulder joint to target
    dist = math.sqrt(r**2 + z**2)

    # Check reachability
    if dist > (L1 + L2) or dist < abs(L1 - L2):
        return result  # unreachable

    # Law of cosines → elbow angle
    cos_elbow = (dist**2 - L1**2 - L2**2) / (2 * L1 * L2)

    # Clamp for numerical safety
    cos_elbow = max(-1.0, min(1.0, cos_elbow))

    result.elbow = math.acos(cos_elbow)

    # Shoulder angle
    alpha = math.atan2(z, r)

    cos_alpha2 = (L1**2 + dist**2 - L2**2) / (2 * L1 * dist)
    cos_alpha2 = max(-1.0, min (1.0, cos_alpha2))

    alpha2 = math.acos(cos_alpha2)

    result.shoulder = alpha + alpha2

    result.valid = 1
    return result

angles = solve_ik(150, 100, 50)

if angles.valid:
    print("Base:", angles.base)
    print("Shoulder:", angles.shoulder)
    print("Elbow:", angles.elbow)
else:
    print("Target is unreachable")