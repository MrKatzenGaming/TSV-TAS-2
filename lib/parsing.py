from sys import exit
from re import search
from lib.classes import Joystick, Frame, Vector3f, Quat4f
from lib.helpers import getStickPolar, eulerToQuat
from lib.script import addToggle, addToFrameRange
from collections.abc import Collection
from lib.stas import *
import lib.globals as g


# parses the duration of a token
def parseDuration(token, default):
    try:
        duration_str = token[token.index("[") + 1 : token.index("]")].strip()
        if duration_str == "?" or duration_str == "*":  # special duration characters
            duration = duration_str
        else:
            try:
                duration = int(float(duration_str))  # rounds down floats
            except:
                exit("[parseDuration] Invalid local duration in row " + g.lineInNumber)
        token = token.replace(token[token.index("[") : token.index("]") + 1], "")
        return token.strip(), duration
    except:
        return token, default


# parses token into subtokens
def parseToken(token, indexWrite, duration, rowIndex, rowDuration):
    if g.debug:
        print("Parsing Token: " + token)
        print("Write Index: " + str(indexWrite))

    token = token.strip()
    if search("^\\[[0-9]*\\] *\\(", token) or (not "|" in token and not "/" in token):
        token, duration = parseDuration(
            token, duration
        )  # see if there is a duration associated with the token

    if g.debug:
        print("Duration: " + str(duration))

    if len(token) > 0 and token[0] == "(" and token[-1] == ")":
        token = token[1:-1]  # remove enclosing parentheses

    if "|" in token:
        parseSequence(token, indexWrite, rowIndex, rowDuration)
    elif "/" in token:
        parseLoop(token, indexWrite, duration, rowIndex, rowDuration)
    elif "&" in token:
        for subtoken in token.split("&"):
            parseToken(subtoken, indexWrite, duration, rowIndex, rowDuration)
    elif "->" in token:
        parseInterpolatedStick(token, indexWrite, duration)
    else:
        if duration == "?":
            exit("[parseToken] ? duration only allowed within sequences")
        elif duration == "*":
            addToggle(token, indexWrite, True)
        elif duration == 0:
            addToggle(token, indexWrite, False)
        elif duration > 0:
            addToFrameRange(token, range(indexWrite, indexWrite + duration), rowIndex)
        else:
            addToFrameRange(
                token, range(indexWrite - 1, indexWrite + duration - 1, -1), rowIndex
            )


def parseInterpolatedStick(token, indexStart, duration):
    if "@" in token:

        exit(f"[parseInterpolation] Cannot use @ Symbol (line {g.lineInNumber})")
    if duration < 0:
        exit(
            f"[parseInterpolation] Cannot have negative duration (line {g.lineInNumber})"
        )
    if duration < 2:
        exit(
            f"[parseInterpolation] Must have duration of at least 2 (line {g.lineInNumber})"
        )

    player_two = "c" in token

    # add frames as necessary
    g.script.addFrames(indexStart + duration)
    indexStop = indexStart + duration

    if indexStart - 1 < 0:
        prev_frame = Frame.empty()
    else:
        prev_frame = g.script.getFrames(player_two)[indexStart - 1]

    try:
        token1, token2 = token.split("->")

        right = False  # True if right stick/gyro/etc., False if left
        if "r" in token1:
            right = True

        token1 = token1[token1.index("(") + 1 : token1.index(")")]
        token2 = token2[token2.index("(") + 1 : token2.index(")")]

        r1, theta1 = getStickPolar(token1, right, prev_frame, None)
        r2, theta2 = getStickPolar(token2, right, prev_frame, None)

        dr = (r2 - r1) / (duration - 1)
        dtheta = (theta2 - theta1) / (duration - 1)

        r, theta = r1, theta1

        for i in range(indexStart, indexStop):
            if right:
                g.script.getFrames(player_two)[i].right_stick = Joystick.polar(
                    (r, theta)
                )
            else:
                g.script.getFrames(player_two)[i].left_stick = Joystick.polar(
                    (r, theta)
                )
            r += dr
            theta += dtheta
        if right:
            g.script.getFrames(player_two)[indexStop - 1].right_stick = Joystick.polar(
                (r2, theta2)
            )
        else:
            g.script.getFrames(player_two)[indexStop - 1].left_stick = Joystick.polar(
                (r2, theta2)
            )
    except Exception as e:
        if g.debug:
            print(e)
        exit(
            "[parseInterpolation] Syntax error(s) on line "
            + str(g.lineInNumber)
            + " prevented script generation"
        )


def parseSequence(token, indexWrite, rowIndex, rowDuration):
    steps = token.split("|")
    for i in range(len(steps)):
        subtoken, duration = parseDuration(steps[i], 1)  # parse out duration
        if duration == "*":
            exit(
                "[parseSequence] * not supported for durations within sequences (line "
                + str(g.lineInNumber)
                + ")"
            )
        elif duration == "?":
            duration = rowDuration + rowIndex - indexWrite
            if duration < 0:
                duration = 0
        parseToken(subtoken, indexWrite, duration, rowIndex, rowDuration)
        indexWrite += duration


def parseLoop(token, indexWrite, duration, rowIndex, rowDuration):
    if duration == "*" or duration == "?":
        exit(
            f"[parseLoop] {duration} not supported for durations within sequences (line {g.lineInNumber})"
        )
    elif duration == 0:
        return
    elif duration < 0:
        exit(f"[parseLoop] cannot have negative total duration (line {g.lineInNumber})")

    remainingDuration = duration
    steps = token.split("/")
    subtokens = []
    durations = []
    for i in range(len(steps)):
        subtoken, duration = parseDuration(steps[i], 1)  # parse out duration
        subtokens.append(subtoken)
        durations.append(duration)
    while remainingDuration > 0:
        for i in range(len(steps)):
            if remainingDuration <= 0:
                return
            if durations[i] >= 0:
                parseToken(
                    subtokens[i],
                    indexWrite,
                    min(durations[i], remainingDuration),
                    rowIndex,
                    rowDuration,
                )
                remainingDuration -= durations[i]
            else:
                exit("[parseLoop] Negative durations are not permitted within loops")
            indexWrite += durations[i]


COMMAND_ARG_COUNT: dict[str, Collection[int]] = {
    "tp": (3, 4, 6, 7),
    "ctp": (3, 4, 6, 7),
    "absStick": (1,),
    "demo": (1,),
    "speed": (1,),
    "pause": (0,),
    "loadFile": (1,),
    "reloadFile": (0,),
    "section": (1,),
    "msection": (1,),
    "csection": (1,),
}


def parseCommand(file: FileIO, tokens: list[str]):
    command: str = tokens[0]
    args = tokens[1:]
    if g.debug:
        print("Parsing command: " + str(command))

    if len(args) not in COMMAND_ARG_COUNT[command]:
        exit(f"[parseCommands] Incorrect number of args for /{command}")

    if command in ("tp", "ctp"):
        euler = Vector3f.zero()
        quat = Quat4f.unit()
        try:
            x, y, z = map(float, args[0:3])
            if len(args) == 4:
                euler.y = float(args[4])
                quat = eulerToQuat(euler)
            elif len(args) == 6:
                euler.x, euler.y, euler.z = map(float, args[3:6])
                quat = eulerToQuat(euler)
            elif len(args) == 7:
                quat.x, quat.y, quat.z, quat.w = map(float, args[3:7])
            writeCmdTp(file, Vector3f(x, y, z), quat, command == "ctp")
            if g.debug:
                print("Quat: " + str(quat))
        except:
            exit(f"[parseCommands] {command}: coordinates must be numbers")
        return

    if command in ("absStick", "demo"):
        enabled = args[0] in ("true", "1", "on", "y", "yes")
        if command == "absStick":
            writeCmdAbsStick(file, enabled)
        else:
            writeCmdDemo(file, enabled)
        return

    if command == "speed":
        try:
            speed: int = int(args[0])
            if speed > 10 or speed < 1:
                exit(
                    "[parseCommands] speed: Speed has to be between 1 and 10 inclusive"
                )
            writeCmdSpeedup(file, speed)
        except:
            exit("[parseCommands] speed: Supplied argument must be an integer")

        return

    if command == "pause":
        writeCommand(file, 0xC006, b"")
        return

    if command == "loadFile":
        try:
            fileNum = int(args[0])
            if fileNum < 0 or fileNum > 4:
                exit("[parseCommands] loadFile: Can only load files between 0 and 4")
            writeCmdSaveFile(file, fileNum, False)
        except:
            exit("[parseCommands] loadFile: Supplied argument must be an integer")
        return

    if command == "reloadFile":
        writeCmdSaveFile(file, 0, True)
        return

    if command in ("section", "msection", "csection"):
        taser: str = ", ".join(args[0:])
        if command in ("section", "msection"):
            writeCmdSection(file, False, taser)
        if command in ("section", "csection"):
            writeCmdSection(file, True, taser)
