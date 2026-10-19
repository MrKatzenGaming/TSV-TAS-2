from lib.classes import Script

global gFtp, gDebug, gNxtas, gRemoveEmpty, gSamePath, gLoop, gStas, gScript, gIndependentGyro, gMotionOffset, gLsOffset, gLineInNumber
gFtp: bool = False
gDebug: bool = False
gNxtas: bool = False
gRemoveEmpty: bool = (
    False  # won't work for lunakit/exlaunch format until mod treats y accel as -1
)

gSamePath: bool = False
gLoop: bool = False
gStas: bool = False
gScript: Script = Script()

# if True, can set angular velocity independently of rotation, if False angular velocity calculated from rotation
gIndependentGyro: bool = False
gMotionOffset: int = 0  # shifts motion macros by this amount
gLsOffset: float = 0  # shifts left stick inputs by this number of degrees
gLineInNumber: int = 1
