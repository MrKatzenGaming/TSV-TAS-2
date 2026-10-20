from lib.classes import Script

ftp: bool = False
debug: bool = False
nxtas: bool = False
removeEmpty: bool = (
    False  # won't work for lunakit/exlaunch format until mod treats y accel as -1
)

samePath: bool = False
loop: bool = False
stas: bool = False
script: Script = Script()

# if True, can set angular velocity independently of rotation, if False angular velocity calculated from rotation
independentGyro: bool = False
motionOffset: int = 0  # shifts motion macros by this amount
lsOffset: float = 0  # shifts left stick inputs by this number of degrees
lineInNumber: int = 1
