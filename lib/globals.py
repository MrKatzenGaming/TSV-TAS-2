from lib.classes import Script

debug: bool = False
nxtas: bool = False
stas: bool = False
script: Script = Script()
# if True, can set angular velocity independently of rotation, if False angular velocity calculated from rotation
independentGyro: bool = False
motionOffset: int = 0  # shifts motion macros by this amount
lsOffset: float = 0  # shifts left stick inputs by this number of degrees
lineInNumber: int = 1
vars: dict[str, str] = dict()
cmdCount: int = 0
