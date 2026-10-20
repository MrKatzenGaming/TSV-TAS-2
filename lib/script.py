from sys import exit
from lib.classes import Joystick, Frame, Vector3f, Gyro, Button, STASButton
from lib.helpers import getStickPolar, to_f2, getGyroValues, getButtonBin
import lib.globals as g


def addToFrameRange(token: str, frameRange: range, rowIndex: int) -> None:
    # first find start and end frames involved, add any additional frames as needed
    minFrame = maxFrame = 0
    for j in frameRange:
        if j > maxFrame:
            maxFrame = j
        if j < minFrame:
            minFrame = j
    g.script.addFrames(maxFrame + 1)

    if frameRange.start < 0 or frameRange.stop < -1:
        exit("[addToFrameRange] Negative durations cannot go before frame 0")

    player_two = False
    token = token.strip()
    if len(token) > 0 and token[0] == "c":
        player_two = True
        token = token[1:]  # get rid of the c

    try:
        if "(" in token:  # stick/motion
            right = True  # True if right stick/gyro/etc.
            left = True  # True if left stick/gyro/etc.
            if "r" in token:
                left = False
            if "l" in token:
                right = False
            prefix = token[0 : token.index("(")]
            token = token[token.index("(") + 1 : token.rfind(")")]

            if "s" in prefix:  # stick
                previous_input_symbol = "!" in token
                current_symbol = "@" in token
                if "x" in prefix:
                    coords = Joystick.cartesian(
                        int(token.split(";")[0]), int(token.split(";")[1])
                    )
                    for j in frameRange:
                        if right:
                            g.script.getFrames(player_two)[j].right_stick = coords
                        if left:
                            g.script.getFrames(player_two)[j].left_stick = coords
                elif (
                    previous_input_symbol or current_symbol
                ):  # need to calculate each frame individually
                    for j in frameRange:
                        if previous_input_symbol:
                            if j - 1 < 0:
                                prev_frame = Frame.empty()
                            else:
                                prev_frame = g.script.getFrames(player_two)[j - 1]
                        else:
                            prev_frame = None
                        coords = Joystick.polar(
                            getStickPolar(token, right, prev_frame, j - rowIndex)
                        )
                        if right:
                            g.script.getFrames(player_two)[j].right_stick = coords
                        if left:
                            g.script.getFrames(player_two)[j].left_stick = coords
                else:
                    polar_coords = getStickPolar(token, right, None, None)
                    coords = Joystick.polar(polar_coords)
                    for j in frameRange:
                        if right:
                            g.script.getFrames(player_two)[j].right_stick = coords
                        if left:
                            g.script.getFrames(player_two)[j].left_stick = coords

            elif "a" in prefix:  # accelerometer
                accel = Vector3f(*map(to_f2, map(float, token.split(";"))))

                for j in frameRange:
                    if right:
                        g.script.getFrames(player_two)[j].accel_right = accel
                    if left:
                        g.script.getFrames(player_two)[j].accel_left = accel

            elif "g" in prefix:  # gyroscope
                gyro = getGyroValues(token)

                for j in frameRange:
                    if right:
                        g.script.getFrames(player_two)[j].gyro_right = gyro
                    if left:
                        g.script.getFrames(player_two)[j].gyro_left = gyro

        elif token == "m" or "m-" in token:  # motion macros
            if g.motionOffset != 0:  # shifting motion earlier or later
                newStart = frameRange.start + g.motionOffset
                while newStart < 0:
                    newStart += frameRange.step
                newStop = max(frameRange.stop + g.motionOffset, -1)
                frameRange = range(newStart, newStop, frameRange.step)

            if (
                g.motionOffset > 0
            ):  # ensure there are still enough frames if motion is shifted later
                minFrame = maxFrame = 0
                for j in frameRange:
                    if j > maxFrame:
                        maxFrame = j
                    if j < minFrame:
                        minFrame = j
                g.script.addFrames(maxFrame + 1)

            if not g.nxtas:
                accel_left = Vector3f.default_accel()
                accel_right = Vector3f.default_accel()
                gyro_left = Gyro.zero()
                gyro_right = Gyro.zero()
                if token == "m" or token == "m-u":
                    accel_left = Vector3f(0, 3, 0)
                    gyro_left.ang_vel = Vector3f(-3, 0, 0)
                elif token == "m-d":
                    accel_left = Vector3f(0, 3, 0)
                    gyro_left.ang_vel = Vector3f(3, 0, 0)
                elif token == "m-l":
                    accel_left = Vector3f(-3, 0, 0)
                    gyro_left.ang_vel = Vector3f(0, 2, 0)
                elif token == "m-r":
                    accel_left = Vector3f(3, 0, 0)
                    gyro_left.ang_vel = Vector3f(0, -2, 0)
                elif token == "m-uu":
                    accel_left = accel_right = Vector3f(0, 3, 0)
                    gyro_left.ang_vel = gyro_right.ang_vel = Vector3f(-2, 0, 0)
                elif token == "m-dd":
                    accel_left = accel_right = Vector3f(0, 3, 0)
                    gyro_left.ang_vel = gyro_right.ang_vel = Vector3f(2, 0, 0)
                elif token == "m-ll":
                    accel_left = accel_right = Vector3f(-3, 0, 0)
                    gyro_left.ang_vel = gyro_right.ang_vel = Vector3f(0, 2, 0)
                elif token == "m-rr":
                    accel_left = accel_right = Vector3f(3, 0, 0)
                    gyro_left.ang_vel = gyro_right.ang_vel = Vector3f(0, -2, 0)
                else:
                    return

                for j in frameRange:
                    (
                        g.script.getFrames(player_two)[j].accel_left,
                        g.script.getFrames(player_two)[j].accel_right,
                    ) = (accel_left, accel_right)
                    (
                        g.script.getFrames(player_two)[j].gyro_left,
                        g.script.getFrames(player_two)[j].gyro_right,
                    ) = (gyro_left, gyro_right)
                    g.script.getFrames(player_two)[j].macro = True

            else:  # nx-tas motion keybinds
                l_button = False
                if token == "m":
                    l_button = True
                elif token == "m-u":
                    l_button = True
                    token = "dp-u"
                elif token == "m-d":
                    l_button = True
                    token = "dp-d"
                elif token == "m-l":
                    l_button = True
                    token = "dp-l"
                elif token == "m-r":
                    l_button = True
                    token = "dp-r"
                elif token == "m-uu":
                    token = "dp-u"
                elif token == "m-dd":
                    token = "dp-d"
                elif token == "m-ll":
                    token = "dp-l"
                elif token == "m-rr":
                    token = "dp-r"
                else:
                    return

                if l_button:
                    for j in frameRange:
                        g.script.getFrames(player_two)[j].buttons |= (
                            2**Button.cPadIdx_L.value
                            if not g.stas
                            else 2**STASButton.cSTAS_L.value
                        )

                # include dpad button

                button_bin = getButtonBin(token, g.stas)
                for j in frameRange:
                    g.script.getFrames(player_two)[j].buttons |= button_bin

        else:  # button or comment/invalid
            button_bin = getButtonBin(token, g.stas)
            for j in frameRange:
                g.script.getFrames(player_two)[j].buttons |= button_bin

    except Exception as e:
        if g.debug:
            print(e)
        exit(
            "[addToFrameRange] Syntax error(s) on line "
            + str(g.lineInNumber)
            + " prevented gScript generation"
        )


# add a toggle for a button to be on indefinitely until its next input in the script ([*]) or a toggle to switch such a button off ([0]) – but the program will actually fill in the frames later
def addToggle(token: str, indexWrite: int, on: bool) -> None:
    try:
        player_two = "c" in token
        button_bin = getButtonBin(token, g.stas)

        g.script.addFrames(indexWrite + 1)
        if on:
            g.script.getFrames(player_two)[indexWrite].buttonsOn |= button_bin
        else:
            g.script.getFrames(player_two)[indexWrite].buttonsOff |= button_bin
    except Exception as e:
        if g.debug:
            print(e)
        exit(
            "[addToggle] Syntax error(s) on line "
            + str(g.lineInNumber)
            + " prevented gScript generation"
        )
