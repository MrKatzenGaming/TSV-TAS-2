from dataclasses import dataclass, field
from math import cos, sin, radians, atan2, sqrt, degrees, isclose
from enum import IntEnum

ANG_VEL_FACTOR: float = -3 / 200.0


@dataclass
class Vector2f:
    x: float
    y: float

    @staticmethod
    def zero() -> Vector2f:
        return Vector2f(0, 0)


@dataclass
class Vector2i:
    x: int
    y: int

    @staticmethod
    def zero() -> Vector2i:
        return Vector2i(0, 0)


@dataclass
class Vector3f:
    x: float
    y: float
    z: float

    @staticmethod
    def zero() -> Vector3f:
        return Vector3f(0, 0, 0)

    @staticmethod
    def default_accel() -> Vector3f:
        # return Vector3f(0, -1, 0)
        return Vector3f(0, 0, 0)

    def __eq__(self: Vector3f, other: object) -> bool:
        if not isinstance(other, Vector3f):
            raise NotImplementedError()
        if self is None and other is None:
            return True
        if self is None or other is None:
            return False
        return (
            isclose(self.x, other.x)
            and isclose(self.y, other.y)
            and isclose(self.z, other.z)
        )

    def NEQ0(self: Vector3f) -> bool:
        if self is None:
            return True
        return not (isclose(self.x, 0) and isclose(self.y, 0) and isclose(self.z, 0))


@dataclass
class Quat4f:
    x: float
    y: float
    z: float
    w: float

    @staticmethod
    def unit() -> Quat4f:
        return Quat4f(0, 0, 0, 0)


@dataclass
class Joystick:
    r: float
    theta: float
    x: int
    y: int

    @staticmethod
    def zero() -> Joystick:
        return Joystick(0, 0, 0, 0)

    @staticmethod
    def polar(
        r_theta: tuple[float, float],
    ) -> (
        Joystick
    ):  # accepts pair with r and theta, snaps to nearest 2^16-representable float
        r: float = r_theta[0]
        theta: float = r_theta[1]
        return Joystick(
            r,
            theta,
            int(32767 * r * cos(radians(theta))),
            int(32767 * r * sin(radians(theta))),
        )

    @staticmethod
    def cartesian(x: int, y: int) -> Joystick:
        # note that with how polar rounds the r and theta may not generate the x and y
        return Joystick(sqrt(x**2 + y**2) / 32767, degrees(atan2(y, x)), x, y)

    def __eq__(self: Joystick, other: object) -> bool:
        if not isinstance(other, Joystick):
            raise NotImplementedError()
        return self.x == other.x and self.y == other.y


@dataclass
class Matrix33f:
    xx: float
    xy: float
    xz: float
    yx: float
    yy: float
    yz: float
    zx: float
    zy: float
    zz: float

    @staticmethod
    def ident() -> Matrix33f:
        return Matrix33f(1, 0, 0, 0, 1, 0, 0, 0, 1)


@dataclass
class Gyro:  # default gyroscope rotation is 3x3 identity matrix
    euler: Vector3f
    direction: Matrix33f
    ang_vel: Vector3f

    @staticmethod
    def zero() -> Gyro:
        return Gyro(Vector3f.zero(), Matrix33f.ident(), Vector3f.zero())


@dataclass
class Script:
    change_stage_name: str = ""
    change_stage_id: str = ""
    scenario_no: int = 1
    is_two_player: bool = False
    startPosition: Vector3f = field(default_factory=Vector3f.zero)
    title: str = ""
    author: str = "TSV-TAS-2"
    description: str = "Description from TSV-TAS-2"
    frames: list[Frame] = field(default_factory=list)
    frames_P1: list[Frame] = field(default_factory=list)
    frames_P2: list[Frame] = field(default_factory=list)
    commands: list[list[str]] = field(default_factory=list)

    def getFrames(self: Script, player_two: bool) -> list[Frame]:
        if player_two:
            return self.frames_P2
        else:
            return self.frames_P1

    def addFrames(self: Script, end: int) -> None:  # add frames through frame end - 1
        for j in range(len(self.frames_P1), end):
            self.frames_P1.append(
                Frame(
                    j,
                    False,
                    0,
                    0,
                    0,
                    Joystick.zero(),
                    Joystick.zero(),
                    Vector3f.default_accel(),
                    Vector3f.default_accel(),
                    Gyro.zero(),
                    Gyro.zero(),
                    False,
                )
            )
        for j in range(len(self.commands), end):
            self.commands.append([])
        if self.is_two_player:
            for j in range(len(self.frames_P2), end):
                self.frames_P2.append(
                    Frame(
                        j,
                        True,
                        0,
                        0,
                        0,
                        Joystick.zero(),
                        Joystick.zero(),
                        Vector3f.default_accel(),
                        Vector3f.default_accel(),
                        Gyro.zero(),
                        Gyro.zero(),
                        False,
                    )
                )

    # merge player 1 and player 2 frames into one array called frames
    def combineFrames(self: Script) -> None:
        if self.is_two_player:
            self.frames = []
            for j in range(0, len(self.frames_P1)):
                self.frames.append(self.frames_P1[j])
                self.frames.append(self.frames_P2[j])
        else:
            self.frames = self.frames_P1


@dataclass
class Frame:
    step: int
    second_player: bool
    buttons: int
    buttonsOn: int
    buttonsOff: int
    left_stick: Joystick
    right_stick: Joystick
    accel_left: Vector3f
    accel_right: Vector3f
    gyro_left: Gyro
    gyro_right: Gyro
    macro: bool

    def toStrArray(self: Frame, script: Script) -> map:

        dl = self.gyro_left.direction
        dr = self.gyro_right.direction
        avl = self.gyro_left.ang_vel
        avr = self.gyro_right.ang_vel
        values = [
            self.step,
            self.second_player,
            self.buttons,
            self.buttonsOn,
            self.buttonsOff,
            self.left_stick.r,
            self.left_stick.theta,
            self.left_stick.x,
            self.left_stick.y,
            self.right_stick.r,
            self.right_stick.theta,
            self.right_stick.x,
            self.right_stick.y,
            self.accel_left.x,
            self.accel_left.y,
            self.accel_left.z,
            self.accel_right.x,
            self.accel_right.y,
            self.accel_right.z,
            dl.xx,
            dl.xy,
            dl.xz,
            dl.yx,
            dl.yy,
            dl.yz,
            dl.zx,
            dl.zy,
            dl.zz,
            avl.x,
            avl.y,
            avl.z,
            dr.xx,
            dr.xy,
            dr.xz,
            dr.yx,
            dr.yy,
            dr.yz,
            dr.zx,
            dr.zy,
            dr.zz,
            avr.x,
            avr.y,
            avr.z,
            script.commands[self.step],
        ]
        return map(str, values)

    @staticmethod
    def empty() -> Frame:
        return Frame(
            0,
            False,
            0,
            0,
            0,
            Joystick.zero(),
            Joystick.zero(),
            Vector3f.default_accel(),
            Vector3f.default_accel(),
            Gyro.zero(),
            Gyro.zero(),
            False,
        )


class Button(IntEnum):
    cPadIdx_A = 0
    cPadIdx_B = 1
    cPadIdx_C = 2
    cPadIdx_X = 3
    cPadIdx_Y = 4
    cPadIdx_Z = 5
    cPadIdx_2 = 6  # R Stick Click
    cPadIdx_1 = 7  # L Stick Click
    cPadIdx_Home = 8
    cPadIdx_Minus = 9
    cPadIdx_Plus = 10
    cPadIdx_Start = 11
    cPadIdx_Select = 12
    cPadIdx_ZL = 2
    cPadIdx_ZR = 5
    cPadIdx_L = 13
    cPadIdx_R = 14
    cPadIdx_Touch = 15
    cPadIdx_Up = 16
    cPadIdx_Down = 17
    cPadIdx_Left = 18
    cPadIdx_Right = 19
    cPadIdx_LeftStickUp = 20
    cPadIdx_LeftStickDown = 21
    cPadIdx_LeftStickLeft = 22
    cPadIdx_LeftStickRight = 23
    cPadIdx_rightUp = 24
    cPadIdx_rightDown = 25
    cPadIdx_rightLeft = 26
    cPadIdx_rightRight = 27
    cPadIdx_Max = 28


class STASButton(IntEnum):
    cSTAS_A = 0
    cSTAS_B = 1
    cSTAS_X = 2
    cSTAS_Y = 3
    cSTAS_LeftStick = 4
    cSTAS_RightStick = 5
    cSTAS_L = 6
    cSTAS_R = 7
    cSTAS_ZL = 8
    cSTAS_ZR = 9
    cSTAS_Plus = 10
    cSTAS_Minus = 11
    cSTAS_DLeft = 12
    cSTAS_DUp = 13
    cSTAS_DRight = 14
    cSTAS_DDown = 15
