from lib.classes import (
    STASButton,
    Button,
    Vector3f,
    Matrix33f,
    Gyro,
    Quat4f,
    ANG_VEL_FACTOR,
)
from math import sin, cos, radians
from lib.evaluation import evaluateLast, evaluateCurrentFrame
import lib.globals as g


def to_f2(f4):  # stores float with 2 byte precision if uncommented
    # return int(f4 * 32767) / 32767.0
    return f4


def getButtonBin(button: str, stas: bool):
    button = button.lower().strip()
    if len(button) > 1 and button[0] == "c":
        button = button[1:]  # 2P button
    if button == "a":
        return 2 ** (STASButton.cSTAS_A.value if stas else Button.cPadIdx_A.value)

    elif button == "b":
        return 2 ** (STASButton.cSTAS_B.value if stas else Button.cPadIdx_B.value)

    elif button == "x":
        return 2 ** (STASButton.cSTAS_X.value if stas else Button.cPadIdx_X.value)

    elif button == "y":
        return 2 ** (STASButton.cSTAS_Y.value if stas else Button.cPadIdx_Y.value)

    elif button == "l":
        return 2 ** (STASButton.cSTAS_L.value if stas else Button.cPadIdx_L.value)

    elif button == "r":
        return 2 ** (STASButton.cSTAS_R.value if stas else Button.cPadIdx_R.value)

    elif button == "zl":
        return 2 ** (STASButton.cSTAS_ZL.value if stas else Button.cPadIdx_ZL.value)

    elif button == "zr":
        return 2 ** (STASButton.cSTAS_ZR.value if stas else Button.cPadIdx_ZR.value)

    elif button == "plus" or button == "+":
        return 2 ** (STASButton.cSTAS_Plus.value if stas else Button.cPadIdx_Plus.value)

    elif button == "minus" or button == "-":
        return 2 ** (
            STASButton.cSTAS_Minus.value if stas else Button.cPadIdx_Minus.value
        )

    elif button == "dp-l":
        return 2 ** (
            STASButton.cSTAS_DLeft.value if stas else Button.cPadIdx_Left.value
        )

    elif button == "dp-u":
        return 2 ** (STASButton.cSTAS_DUp.value if stas else Button.cPadIdx_Up.value)

    elif button == "dp-r":
        return 2 ** (
            STASButton.cSTAS_DRight.value if stas else Button.cPadIdx_Right.value
        )

    elif button == "dp-d":
        return 2 ** (
            STASButton.cSTAS_DDown.value if stas else Button.cPadIdx_Down.value
        )

    elif button == "ls":
        return 2 ** (
            STASButton.cSTAS_LeftStick.value if stas else Button.cPadIdx_1.value
        )

    elif button == "rs":
        return 2 ** (
            STASButton.cSTAS_RightStick.value if stas else Button.cPadIdx_2.value
        )
    else:
        return 0  # no button found


def nxTAS_Buttons(
    buttons: int, stas: bool
):  # converts button int into string list of buttons for nx-TAS format
    button_list = []
    if buttons == 0:
        return "NONE"
    if buttons & 2 ** (STASButton.cSTAS_A.value if stas else Button.cPadIdx_A.value):
        button_list.append("KEY_A")

    if buttons & 2 ** (STASButton.cSTAS_B.value if stas else Button.cPadIdx_B.value):
        button_list.append("KEY_B")

    if buttons & 2 ** (STASButton.cSTAS_X.value if stas else Button.cPadIdx_X.value):
        button_list.append("KEY_X")

    if buttons & 2 ** (STASButton.cSTAS_Y.value if stas else Button.cPadIdx_Y.value):
        button_list.append("KEY_Y")

    if buttons & 2 ** (STASButton.cSTAS_L.value if stas else Button.cPadIdx_L.value):
        button_list.append("KEY_L")

    if buttons & 2 ** (STASButton.cSTAS_R.value if stas else Button.cPadIdx_R.value):
        button_list.append("KEY_R")

    if buttons & 2 ** (STASButton.cSTAS_ZL.value if stas else Button.cPadIdx_ZL.value):
        button_list.append("KEY_ZL")

    if buttons & 2 ** (STASButton.cSTAS_ZR.value if stas else Button.cPadIdx_ZR.value):
        button_list.append("KEY_ZR")

    if buttons & 2 ** (
        STASButton.cSTAS_Plus.value if stas else Button.cPadIdx_Plus.value
    ):
        button_list.append("KEY_PLUS")

    if buttons & 2 ** (
        STASButton.cSTAS_Minus.value if stas else Button.cPadIdx_Minus.value
    ):
        button_list.append("KEY_MINUS")

    if buttons & 2 ** (
        STASButton.cSTAS_DLeft.value if stas else Button.cPadIdx_Left.value
    ):
        button_list.append("KEY_DLEFT")

    if buttons & 2 ** (
        STASButton.cSTAS_DRight.value if stas else Button.cPadIdx_Right.value
    ):
        button_list.append("KEY_DRIGHT")

    if buttons & 2 ** (STASButton.cSTAS_DUp.value if stas else Button.cPadIdx_Up.value):
        button_list.append("KEY_DUP")

    if buttons & 2 ** (
        STASButton.cSTAS_DDown.value if stas else Button.cPadIdx_Down.value
    ):
        button_list.append("KEY_DDOWN")

    if buttons & 2 ** (
        STASButton.cSTAS_LeftStick.value if stas else Button.cPadIdx_1.value
    ):
        button_list.append("KEY_LSTICK")

    if buttons & 2 ** (
        STASButton.cSTAS_RightStick.value if stas else Button.cPadIdx_2.value
    ):
        button_list.append("KEY_RSTICK")

    return ";".join(button_list)


# prev_frame is used to evaluate ! characters if it is not None
# offset_from_row_index is used to evaluate @ characters if it is not None
def getStickPolar(token, right_stick, prev_frame, offset_from_row_index):
    r = 1.0
    theta = 0.0
    if prev_frame is not None:  # contains !
        if right_stick:
            prev_stick = prev_frame.right_stick
        else:
            prev_stick = prev_frame.left_stick
    if ";" in token:  # (r; theta)
        r_token = token[0 : token.index(";")]
        theta_token = token[token.index(";") + 1 :]
        if prev_frame is not None:
            r_token, theta_token = evaluateLast(r_token, prev_stick.r), evaluateLast(
                theta_token, prev_stick.theta - g.gLsOffset
            )
        if offset_from_row_index is not None:
            r_token, theta_token = evaluateCurrentFrame(
                r_token, offset_from_row_index
            ), evaluateCurrentFrame(theta_token, offset_from_row_index)
        r, theta = float(r_token), float(theta_token)
    else:  # (r)
        if prev_frame is not None:
            token = evaluateLast(token, prev_stick.theta - g.gLsOffset)
        if offset_from_row_index is not None:
            token = evaluateCurrentFrame(token, offset_from_row_index)
        theta = float(token)
    theta += g.gLsOffset
    return r, theta


# euler in degrees to rotation matrix
def toRotationMatrix(euler: Vector3f):
    euler_radians = Vector3f.zero()
    euler_radians.x, euler_radians.y, euler_radians.z = (
        radians(euler.x),
        radians(euler.y),
        radians(euler.z),
    )

    cx = cos(euler_radians.x)
    cy = cos(euler_radians.y)
    cz = cos(euler_radians.z)
    sx = sin(euler_radians.x)
    sy = sin(euler_radians.y)
    sz = sin(euler_radians.z)

    return Matrix33f(
        to_f2(cy * cz),
        to_f2(-cy * sz),
        to_f2(sy),
        to_f2(cz * sx * sy + cx * sz),
        to_f2(cx * cz - sx * sy * sz),
        to_f2(-cy * sx),
        to_f2(-cx * cz * sy + sx * sz),
        to_f2(cz * sx + cx * sy * sz),
        to_f2(cx * cy),
    )


def getGyroValues(token):
    all = token.split(
        ";"
    )  # (pitch; yaw; roll) or #(pitch; yaw; roll; ang-x; ang-y; ang-z)
    ang_vel = Vector3f.zero()
    euler = Vector3f.zero()
    if len(all) == 6:
        ang_vel.x, ang_vel.y, ang_vel.z = (
            to_f2(float(all[3])),
            to_f2(float(all[4])),
            to_f2(float(all[5])),
        )
    euler.x, euler.y, euler.z = float(all[0]), float(all[1]), float(all[2])

    return Gyro(euler, toRotationMatrix(euler), ang_vel)


# calculates needed angular velocities for all frames based on the gyroscope
def calculateAngularVelocity(player_two):
    euler_left_old, euler_right_old = (
        g.gScript.getFrames(player_two)[0].gyro_left.euler,
        g.gScript.getFrames(player_two)[0].gyro_right.euler,
    )
    for i in range(1, len(g.gScript.getFrames(player_two))):
        euler_left, euler_right = (
            g.gScript.getFrames(player_two)[i].gyro_left.euler,
            g.gScript.getFrames(player_two)[i].gyro_right.euler,
        )
        if not g.gScript.getFrames(player_two)[i].macro:
            g.gScript.getFrames(player_two)[i].gyro_left.ang_vel = Vector3f(
                ANG_VEL_FACTOR * (euler_left.x - euler_left_old.x),
                ANG_VEL_FACTOR * (euler_left.y - euler_left_old.y),
                ANG_VEL_FACTOR * (euler_left.z - euler_left_old.z),
            )
            g.gScript.getFrames(player_two)[i].gyro_right.ang_vel = Vector3f(
                ANG_VEL_FACTOR * (euler_right.x - euler_right_old.x),
                ANG_VEL_FACTOR * (euler_right.y - euler_right_old.y),
                ANG_VEL_FACTOR * (euler_right.z - euler_right_old.z),
            )
        """
        else:
            ang_vel_left, ang_vel_right = script.frames[i].gyro_left.ang_vel, script.frames[i].gyro_right.ang_vel
            script.frames[i].gyro_left.euler = Vector3f(euler_left_old.x + ang_vel_left.x / ANG_VEL_FACTOR, euler_left_old.y + ang_vel_left.y / ANG_VEL_FACTOR, euler_left_old.z + ang_vel_left.z / ANG_VEL_FACTOR)
            script.frames[i].gyro_right.euler = Vector3f(euler_right_old.x + ang_vel_right.x / ANG_VEL_FACTOR, euler_right_old.y + ang_vel_right.y / ANG_VEL_FACTOR, euler_right_old.z + ang_vel_right.z / ANG_VEL_FACTOR)
            script.frames[i].gyro_left.direction = toRotationMatrix(script.frames[i].gyro_left.euler)
            script.frames[i].gyro_right.direction = toRotationMatrix(script.frames[i].gyro_right.euler)
        """
        euler_left_old, euler_right_old = euler_left, euler_right


def eulerToQuat(euler_deg: Vector3f) -> Quat4f:
    quat = Quat4f.unit()
    euler = Vector3f.zero()
    euler.x = radians(euler_deg.x)
    euler.y = radians(euler_deg.y)
    euler.z = radians(euler_deg.z)
    cy = cos(euler.y / 2)
    sy = sin(euler.y / 2)
    cp = cos(euler.z / 2)
    sp = sin(euler.z / 2)
    cr = cos(euler.x / 2)
    sr = sin(euler.x / 2)

    quat.w = cr * cp * cy + sr * sp * sy
    quat.x = sr * cp * cy - cr * sp * sy
    quat.z = cr * sp * cy + sr * cp * sy
    quat.y = cr * cp * sy - sr * sp * cy

    return quat
