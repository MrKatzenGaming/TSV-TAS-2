import struct
import sys
from ftplib import FTP
import json
import csv
from io import FileIO
import argparse

# Local libs
from lib.classes import *
from lib.helpers import *
from lib.evaluation import *
from lib.stas import *
from lib.parsing import *
from lib.script import *
import lib.globals as g

parser = argparse.ArgumentParser()
parser.add_argument("infile", help="Input File")
parser.add_argument("outfile", nargs="?", help="Output File")
parser.add_argument("-f", "--ftp", action="store_true", help="Enables FTP")
parser.add_argument("-d", "--debug", action="store_true", help="Enables Debug mode")
parser.add_argument(
    "-n", "--nxtas", action="store_true", help="Generates nxTAS scripts"
)
parser.add_argument("-e", "--noempty", action="store_true", help="Removes empty lines")
parser.add_argument(
    "-p",
    "--samepath",
    action="store_true",
    help="Input and output file name are the same",
)
parser.add_argument("-l", "--loop", action="store_true", help="Enables Loop mode")
parser.add_argument("-s", "--stas", action="store_true", help="Generates STAS files")

args = parser.parse_args()
infile: str = args.infile
outfile: str = args.outfile
g.gFtp = args.ftp
g.gDebug = args.debug
g.gNxtas = args.nxtas
g.gRemoveEmpty = args.noempty
g.gSamePath = args.samepath
g.gLoop = args.loop
g.gStas = args.stas


if outfile is None and not g.gSamePath:
    parser.error("outfile is required unless -p is specified")

if infile.endswith(".tsv") or infile.endswith(".txt"):
    separator = "\t"
elif infile.endswith(".csv"):
    separator = ","
else:
    sys.exit("Error: Invalid file type")

if g.gSamePath:
    outfile = infile[0 : infile.rindex(".")]
    if g.gNxtas:
        outfile += ".txt"
    elif g.gStas:
        outfile += ".stas"


do_once = True

if g.gLoop:
    print("Press enter to run command")
    print('Type "q" and press enter to quit')

while g.gLoop or do_once:
    do_once = False

    if g.gLoop:
        input_text = input()
        if input_text == "q" or input_text == "quit" or input_text == "exit":
            break

    g.gScript.title = infile.split("/")[-1]

    num_frames = 0

    # count frames roughly to initialize array
    with open(infile) as f:
        for lineIn in f:
            duration = 1
            first = lineIn.split(separator)[0]
            try:
                duration = int(first)
            except:
                if first == "":
                    pass
                else:
                    continue
            num_frames += duration
        f.close()

    g.gScript.frames_P1 = [
        Frame(
            i,
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
        for i in range(num_frames)
    ]
    if g.gScript.is_two_player:
        g.gScript.frames_P2 = [
            Frame(
                i,
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
            for i in range(num_frames)
        ]

    indexStart = 0
    indexStop = 0

    vars = dict()

    with open(infile) as f:
        prevLineInDuration = 1
        for lineIn in f:
            if g.gDebug:
                print(lineIn)
            lineIn = lineIn.split(separator)  # type: ignore
            lineIn[-1] = lineIn[-1].strip()  # type: ignore

            # handle first token (duration or variable assignment)
            lineInDuration = 1
            first = lineIn[0].strip()
            try:
                lineInDuration = int(float(first))
            except:
                if first == "*":  # toggle on the buttons
                    lineInDuration = "*"  # type: ignore
                elif first == "?":
                    sys.exit("Error: ? duration only allowed within sequences")
                elif first == "":
                    pass
                elif first[0] == "$":  # variables
                    if "=" in first:  # variable assignment
                        var = first[1 : first.index("=")].strip().lower()
                        value = first[first.index("=") + 1 :].strip()

                        # script start variables
                        if var == "stage":
                            g.gScript.change_stage_name = value
                        elif var == "entr" or var == "entrance":
                            g.gScript.change_stage_id = value
                        elif var == "scen" or var == "scenario":
                            try:
                                g.gScript.scenario_no = int(value)
                            except:
                                sys.exit("Error: Invalid scenario number")
                        elif var == "independent_gyro" or var == "ind_gyro":
                            if value.lower() == "true" or value.lower() == "t":
                                g.gIndependentGyro = True
                        elif var == "pos" or var == "position":
                            value = value[value.index("(") + 1 : value.index(")")]
                            coords = value.split(";")
                            g.gScript.startPosition.x = float(coords[0])
                            g.gScript.startPosition.y = float(coords[1])
                            g.gScript.startPosition.z = float(coords[2])
                        elif var == "title":
                            g.gScript.title = value
                        elif var == "author":
                            g.gScript.author = value
                        elif var == "desc" or var == "description":
                            g.gScript.description = value
                        elif var == "motion_offset":
                            g.gMotionOffset = int(value)
                        elif var == "ls_offset":
                            g.gLsOffset = float(value)
                        elif var == "is2p" or var == "is_two_player":
                            if value.lower() == "true" or value.lower() == "t":
                                g.gScript.is_two_player = True
                                is_two_player = True

                        # add variable values to dictionary
                        value = prepareToken(value, True, 0)
                        vars.update({var: value})
                        g.gLineInNumber += 1
                        continue
                    else:
                        try:
                            lineInDuration = int(
                                float(
                                    evaluateLast(
                                        prepareToken(first, True, 0), prevLineInDuration
                                    )
                                )
                            )
                        except:
                            g.gLineInNumber += 1
                            continue
                elif first[0] == "/" and first[1] != "/":  # commands
                    for _ in range(len(g.gScript.commands), indexStart + 1):
                        g.gScript.commands.append([])
                    g.gScript.commands[indexStart].append(first[1:])
                    g.gLineInNumber += 1
                    continue
                else:
                    try:
                        lineInDuration = int(
                            float(
                                evaluateLast(
                                    prepareToken(first, True, 0), prevLineInDuration
                                )
                            )
                        )
                    except:
                        g.gLineInNumber += 1
                        continue

            for i in range(1, len(lineIn)):
                if lineIn[i] == "":
                    continue

                # perform all variable evaluation and as much math evaluation as possible
                token = prepareToken(lineIn[i], False, lineInDuration)

                if g.gDebug:
                    print("Line Duration: " + str(lineInDuration))
                parseToken(
                    token,
                    indexStart,
                    lineInDuration,
                    indexStart,
                    lineInDuration,
                )

            if lineInDuration == "*":
                lineInDuration = 0
            indexStart += lineInDuration
            g.gLineInNumber += 1
            prevLineInDuration = lineInDuration

        # add empty frames to end of script as needed to reach the total number of frames
        if not g.gRemoveEmpty:
            g.gScript.addFrames(indexStart)

        # now that all the inputs have been parsed, go through again to process toggled buttons
        buttonsOn = 0
        for frame in g.gScript.frames_P1:
            buttonsOn |= frame.buttonsOn
            buttonsOff = frame.buttons | frame.buttonsOff
            buttonsOn &= ~buttonsOff
            frame.buttons |= buttonsOn
        if g.gScript.is_two_player:
            for frame in g.gScript.frames_P2:
                buttonsOn |= frame.buttonsOn
                buttonsOff = frame.buttons | frame.buttonsOff
                buttonsOn &= ~buttonsOff
                frame.buttons |= buttonsOn

        # calculate angular velocity if gyroscope and angular velocity are not independent, or calculate proper gyroscope if a motion macro is used
        # angular velocity is change in gyroscope in degrees times -3/400
        if not g.gIndependentGyro:
            calculateAngularVelocity(False)
            if g.gScript.is_two_player:
                calculateAngularVelocity(True)

        # remove empty frames (in 2P, only remove if both are empty)
        if g.gRemoveEmpty:
            if g.gScript.is_two_player:
                modelFrame_1P = modelFrame_2P = Frame.empty()
                for i in range(len(g.gScript.frames_P1) - 1, -1, -1):
                    modelFrame_1P.step = modelFrame_2P.step = i
                    modelFrame_1P.buttonsOn = g.gScript.frames_P1[i].buttonsOn
                    modelFrame_1P.buttonsOff = g.gScript.frames_P1[i].buttonsOff
                    modelFrame_2P.buttonsOn = g.gScript.frames_P2[i].buttonsOn
                    modelFrame_2P.buttonsOff = g.gScript.frames_P2[i].buttonsOff
                    if (
                        modelFrame_1P == g.gScript.frames_P1[i]
                        and modelFrame_2P == g.gScript.frames_P2[i]
                    ):
                        del g.gScript.frames_P1[i]
                        del g.gScript.frames_P2[i]
            else:
                modelFrame = Frame.empty()
                for i in range(len(g.gScript.frames_P1) - 1, -1, -1):
                    modelFrame.step = i
                    modelFrame.buttonsOn = g.gScript.frames_P1[i].buttonsOn
                    modelFrame.buttonsOff = g.gScript.frames_P1[i].buttonsOff
                    if modelFrame == g.gScript.frames_P1[i]:
                        del g.gScript.frames_P1[i]

    # write all 1P and 2P frames to the same array
    g.gScript.combineFrames()

    if g.gDebug:
        debugFile = open(outfile + "-debug.csv", "w")

        debugFile.write(
            "Frame,2ndPlayer,Buttons,ButtonsOn,ButtonsOff,lx.r,ls.theta,ls.x,ls.y,rs.r,rs.theta,rs.x,rs.y,la.x,la.y,la.z,ra.x,ra.y,ra.z,lg.r.xx,lg.r.xy,lg.r.xz,lg.r.yx,lg.r.yy,lg.r.yz,lg.r.zx,lg.r.zy,lg.r.zz,lg.v.x,lg.v.y,lg.v.z,rg.r.xx,rg.r.xy,rg.r.xz,rg.r.yx,rg.r.yy,rg.r.yz,rg.r.zx,rg.r.zy,rg.r.zz,rg.v.x,rg.v.y,rg.v.z,Command\n"
        )
        for i in range(len(g.gScript.frames)):
            csv_writer = csv.writer(debugFile, delimiter=",")
            data = g.gScript.frames[i].toStrArray(g.gScript)
            csv_writer.writerow(data)
        debugFile.close()

    if g.gNxtas:
        outf: FileIO = open(outfile, "w")  # type: ignore
        for frame in g.gScript.frames:
            outf.write(
                str(frame.step)  # type: ignore
                + " "
                + nxTAS_Buttons(frame.buttons, g.gStas)
                + " "
                + str(frame.left_stick.x)
                + ";"
                + str(frame.left_stick.y)
                + " "
                + str(frame.right_stick.x)
                + ";"
                + str(frame.right_stick.y)
                + "\n"
            )

    elif g.gStas:
        size: int = 0
        prevFrame: int = -1
        prevMotion: list[list[list[Vector3f]]] = [  # player, left/right, accel/gyro
            [[Vector3f.zero(), Vector3f.zero()], [Vector3f.zero(), Vector3f.zero()]],
            [[Vector3f.zero(), Vector3f.zero()], [Vector3f.zero(), Vector3f.zero()]],
        ]
        prevController: list[list[object]] = (
            [  # player, button/left joystick/right joystick
                [0, Joystick.zero(), Joystick.zero()],
                [0, Joystick.zero(), Joystick.zero()],
            ]
        )

        outf = open(outfile, "wb")  # type: ignore
        # File Header
        size += outf.write(b"STAS")
        size += outf.write(
            struct.pack("<3H2xQ", 0x0001, 0x0000, 0x0000, 0x0100000000010000)
        )  # Format Ver, Game Addon Ver, Editor Ver, Title Id

        # Script Header
        size += outf.write(struct.pack("<I", 0))  # TODO: Command Count
        size += outf.write(
            struct.pack("<I", g.gScript.frames[-1].step)
        )  # TODO: This is bad
        size += outf.write(struct.pack("<I", 0))  # Editing time in seconds
        size += outf.write(
            struct.pack("<8B", 2, 2 if g.gScript.is_two_player else 0, 0, 0, 0, 0, 0, 0)
        )  # Controller types per player

        size += writeAuthor(outf, g.gScript.author)

        size += writeTitle(outf, g.gScript.title)

        size += writeDesc(outf, g.gScript.description)

        if g.gScript.change_stage_name:
            writeCmdGo(
                outf,
                g.gScript.scenario_no,
                0,
                False,
                g.gScript.change_stage_name,
                g.gScript.change_stage_id,
            )

        # reset every controller state
        writeCmdController(
            outf, 0, int(0).to_bytes(7, "little"), Joystick.zero(), Joystick.zero()
        )
        writeCmdController(
            outf, 1, int(0).to_bytes(7, "little"), Joystick.zero(), Joystick.zero()
        )
        writeCmdMotion(outf, 0, 2, Vector3f.zero(), Vector3f.zero())
        writeCmdMotion(outf, 1, 2, Vector3f.zero(), Vector3f.zero())

        for frame in g.gScript.frames:
            # print(f"{frame.step}, {frame.buttons}")
            if frame.step > prevFrame:  # do only for 1P frames
                prevFrame = frame.step
                writeCmdFrame(outf, frame.step)
                if frame.step == 0 and (
                    g.gScript.startPosition.x != 0
                    or g.gScript.startPosition.y != 0
                    or g.gScript.startPosition.z != 0
                ):
                    writeCmdTp(outf, g.gScript.startPosition, Quat4f.unit(), False)
                # parse commands, this relies on every step being included but that is okay
                for command_str in g.gScript.commands[frame.step]:
                    tokens = command_str.split(" ")
                    command = tokens[0]
                    if g.gDebug:
                        print("Parsing command: " + str(command))
                    if command == "tp" or command == "ctp":
                        isCap = command == "ctp"
                        euler = Vector3f.zero()
                        quat = Quat4f.unit()
                        if len(tokens) in (4, 5, 7, 8):
                            try:
                                x, y, z = map(float, tokens[1:4])
                                if len(tokens) == 5 or len(tokens) == 7:
                                    if len(tokens) == 5:
                                        euler.y = float(tokens[4])
                                    elif len(tokens) == 7:
                                        euler.x, euler.y, euler.z = map(
                                            float, tokens[4:7]
                                        )
                                    quat = eulerToQuat(euler)
                                elif len(tokens) == 8:
                                    quat.x, quat.y, quat.z, quat.w = map(
                                        float, tokens[4:8]
                                    )
                                writeCmdTp(outf, Vector3f(x, y, z), quat, isCap)
                                if g.gDebug:
                                    print("Quat: " + str(quat))
                            except:
                                sys.exit(
                                    f"Error: /{command} coordinates must be numbers"
                                )
                        else:
                            sys.exit(f"Error: incorrect number of args for /{command}")
                    elif command == "absStick":
                        if len(tokens) == 2:
                            absStickEnable: bool = tokens[1] in [
                                "true",
                                "1",
                                "on",
                                "y",
                                "yes",
                            ]
                            writeCmdAbsStick(outf, absStickEnable)
                        else:
                            sys.exit(f"Error: incorrect number of args for /{command}")
                    elif command == "speed":
                        if len(tokens) == 2:
                            speed: int = int(tokens[1])
                            if speed > 10 or speed < 1:
                                sys.exit(
                                    f"Error: speed has to be between 1 and 10 inclusive"
                                )
                            writeCmdSpeedup(outf, speed)
                        else:
                            sys.exit(f"Error: incorrect number of args for /{command}")
                    elif command == "pause":
                        if len(tokens) == 1:
                            writeCommand(outf, 0xC006, b"")
                        else:
                            sys.exit(f"Error: incorrect number of args for /{command}")
                    elif command == "loadFile":
                        if len(tokens) == 2:
                            writeCmdSaveFile(outf, int(tokens[1]), False)
                        else:
                            sys.exit(f"Error: incorrect number of args for /{command}")
                    elif command == "reloadFile":
                        if len(tokens) == 1:
                            writeCmdSaveFile(outf, 0, True)
                        else:
                            sys.exit(f"Error: incorrect number of args for /{command}")
                    elif command == "demo":
                        if len(tokens) == 2:
                            demoEnable: bool = tokens[1] in [
                                "true",
                                "1",
                                "on",
                                "y",
                                "yes",
                            ]
                            writeCmdDemo(outf, demoEnable)
                        else:
                            sys.exit(f"Error: incorrect number of args for /{command}")
                    elif command in ["section", "msection", "csection"]:
                        if len(tokens) >= 2:
                            taser: str = ", ".join(tokens[1:])
                            if command in ["section", "msection"]:
                                writeCmdSection(outf, False, taser)
                            if command in ["section", "csection"]:
                                writeCmdSection(outf, True, taser)
                        else:
                            sys.exit(f"Error: incorrect number of args for /{command}")

            # only write controller inputs if they differ
            if (prevController[frame.second_player][0] != frame.buttons) or (
                prevController[frame.second_player][1] != frame.left_stick
                or prevController[frame.second_player][2] != frame.right_stick
            ):
                writeCmdController(
                    outf,
                    frame.second_player,
                    frame.buttons.to_bytes(7, "little"),
                    frame.left_stick,
                    frame.right_stick,
                )
                if g.gDebug:
                    print(
                        "Wrote frame "
                        + str(frame.step)
                        + ", P2: "
                        + str(frame.second_player)
                    )

            prevController[frame.second_player] = [
                frame.buttons,
                frame.left_stick,
                frame.right_stick,
            ]

            if (frame.accel_left.NEQ0() or frame.gyro_left.ang_vel.NEQ0()) or (
                prevMotion[frame.second_player][0][0].NEQ0()
                or prevMotion[frame.second_player][0][1].NEQ0()
            ):
                writeCmdMotion(
                    outf,
                    frame.second_player,
                    0,
                    frame.accel_left,
                    frame.gyro_left.ang_vel,
                )
                prevMotion[frame.second_player][0] = [
                    frame.accel_left,
                    frame.gyro_left.ang_vel,
                ]

            if (
                frame.accel_right.NEQ0()
                or frame.gyro_right.ang_vel.NEQ0()
                or (
                    prevMotion[frame.second_player][1][0].NEQ0()
                    or prevMotion[frame.second_player][1][1].NEQ0()
                )
            ):
                writeCmdMotion(
                    outf,
                    frame.second_player,
                    1,
                    frame.accel_right,
                    frame.gyro_right.ang_vel,
                )
                prevMotion[frame.second_player][1] = [
                    frame.accel_right,
                    frame.gyro_right.ang_vel,
                ]

    else:
        outf = open(outfile, "wb")  # type: ignore
        outf.write(b"BOOB")
        outf.write(
            struct.pack(
                "<I?3xi",
                len(g.gScript.frames),
                g.gScript.is_two_player,
                g.gScript.scenario_no,
            )
        )
        outf.write(
            bytes(g.gScript.change_stage_name, encoding="ascii")
            + b"\0" * (128 - len(g.gScript.change_stage_name))
        )
        outf.write(
            bytes(g.gScript.change_stage_id, encoding="ascii")
            + b"\0" * (128 - len(g.gScript.change_stage_id))
        )
        outf.write(
            struct.pack(
                "<3f",
                g.gScript.startPosition.x,
                g.gScript.startPosition.y,
                g.gScript.startPosition.z,
            )
        )

        for frame in g.gScript.frames:
            outf.write(
                struct.pack("<I?3xI", frame.step, frame.second_player, frame.buttons)
            )
            outf.write(
                struct.pack(
                    "<2f", frame.left_stick.x / 32767.0, frame.left_stick.y / 32767.0
                )
            )
            outf.write(
                struct.pack(
                    "<2f", frame.right_stick.x / 32767.0, frame.right_stick.y / 32767.0
                )
            )
            outf.write(
                struct.pack(
                    "<3f", frame.accel_left.x, frame.accel_left.y, frame.accel_left.z
                )
            )
            outf.write(
                struct.pack(
                    "<3f", frame.accel_right.x, frame.accel_right.y, frame.accel_right.z
                )
            )
            outf.write(
                struct.pack(
                    "<9f",
                    frame.gyro_left.direction.xx,
                    frame.gyro_left.direction.xy,
                    frame.gyro_left.direction.xz,
                    frame.gyro_left.direction.yx,
                    frame.gyro_left.direction.yy,
                    frame.gyro_left.direction.yz,
                    frame.gyro_left.direction.zx,
                    frame.gyro_left.direction.zy,
                    frame.gyro_left.direction.zz,
                )
            )
            outf.write(
                struct.pack(
                    "<3f",
                    frame.gyro_left.ang_vel.x,
                    frame.gyro_left.ang_vel.y,
                    frame.gyro_left.ang_vel.z,
                )
            )
            outf.write(
                struct.pack(
                    "<9f",
                    frame.gyro_right.direction.xx,
                    frame.gyro_right.direction.xy,
                    frame.gyro_right.direction.xz,
                    frame.gyro_right.direction.yx,
                    frame.gyro_right.direction.yy,
                    frame.gyro_right.direction.yz,
                    frame.gyro_right.direction.zx,
                    frame.gyro_right.direction.zy,
                    frame.gyro_right.direction.zz,
                )
            )
            outf.write(
                struct.pack(
                    "<3f",
                    frame.gyro_right.ang_vel.x,
                    frame.gyro_right.ang_vel.y,
                    frame.gyro_right.ang_vel.z,
                )
            )

    outf.close()

    print("Script successfully generated")

    if g.gFtp:
        ftp_config_file = open("ftp_config.json")
        ftp_config = json.load(ftp_config_file)
        ftp_config_file.close

        ftpC = FTP()
        ftpC.connect(host=ftp_config["ip"], port=int(ftp_config["port"]))
        ftpC.login(user=ftp_config["user"], passwd=ftp_config["passwd"])

        file = open(outfile, "rb")

        result = ftpC.storbinary("STOR SMO/tas/scripts/" + outfile, file)
        if result == "226 OK":
            print("Script successfully uploaded")
        else:
            print("FTP error")

        ftpC.quit()
