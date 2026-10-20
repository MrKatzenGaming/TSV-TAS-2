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
ftp = args.ftp
g.debug = args.debug
g.nxtas = args.nxtas
removeEmpty = (
    args.noempty
)  # won't work for lunakit/exlaunch format until mod treats y accel as -1

samePath = args.samepath
loop = args.loop
g.stas = args.stas


if outfile is None and not samePath:
    parser.error("outfile is required unless -p is specified")

if infile.endswith(".tsv") or infile.endswith(".txt"):
    separator = "\t"
elif infile.endswith(".csv"):
    separator = ","
else:
    sys.exit("Error: Invalid file type")

if samePath:
    outfile = infile[0 : infile.rindex(".")]
    if g.nxtas:
        outfile += ".txt"
    elif g.stas:
        outfile += ".stas"


do_once = True

if loop:
    print("Press enter to run command")
    print('Type "q" and press enter to quit')

while loop or do_once:
    do_once = False

    if loop:
        input_text = input()
        if input_text == "q" or input_text == "quit" or input_text == "exit":
            break

    g.script.title = infile.split("/")[-1]

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

    g.script.frames_P1 = [
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
    if g.script.is_two_player:
        g.script.frames_P2 = [
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
            if g.debug:
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
                        parseVariable(var, value)
                        # add variable values to dictionary
                        value = prepareToken(value, True, 0)
                        vars.update({var: value})
                        g.lineInNumber += 1
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
                            g.lineInNumber += 1
                            continue
                elif first[0] == "/" and first[1] != "/":  # commands
                    for _ in range(len(g.script.commands), indexStart + 1):
                        g.script.commands.append([])
                    g.script.commands[indexStart].append(first[1:])
                    g.lineInNumber += 1
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
                        g.lineInNumber += 1
                        continue

            for i in range(1, len(lineIn)):
                if lineIn[i] == "":
                    continue

                # perform all variable evaluation and as much math evaluation as possible
                token = prepareToken(lineIn[i], False, lineInDuration)

                if g.debug:
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
            g.lineInNumber += 1
            prevLineInDuration = lineInDuration

        # add empty frames to end of script as needed to reach the total number of frames
        if not removeEmpty:
            g.script.addFrames(indexStart)

        # now that all the inputs have been parsed, go through again to process toggled buttons
        buttonsOn = 0
        for frame in g.script.frames_P1:
            buttonsOn |= frame.buttonsOn
            buttonsOff = frame.buttons | frame.buttonsOff
            buttonsOn &= ~buttonsOff
            frame.buttons |= buttonsOn
        if g.script.is_two_player:
            for frame in g.script.frames_P2:
                buttonsOn |= frame.buttonsOn
                buttonsOff = frame.buttons | frame.buttonsOff
                buttonsOn &= ~buttonsOff
                frame.buttons |= buttonsOn

        # calculate angular velocity if gyroscope and angular velocity are not independent, or calculate proper gyroscope if a motion macro is used
        # angular velocity is change in gyroscope in degrees times -3/400
        if not g.independentGyro:
            calculateAngularVelocity(False)
            if g.script.is_two_player:
                calculateAngularVelocity(True)

        # remove empty frames (in 2P, only remove if both are empty)
        if removeEmpty:
            if g.script.is_two_player:
                modelFrame_1P = modelFrame_2P = Frame.empty()
                for i in range(len(g.script.frames_P1) - 1, -1, -1):
                    modelFrame_1P.step = modelFrame_2P.step = i
                    modelFrame_1P.buttonsOn = g.script.frames_P1[i].buttonsOn
                    modelFrame_1P.buttonsOff = g.script.frames_P1[i].buttonsOff
                    modelFrame_2P.buttonsOn = g.script.frames_P2[i].buttonsOn
                    modelFrame_2P.buttonsOff = g.script.frames_P2[i].buttonsOff
                    if (
                        modelFrame_1P == g.script.frames_P1[i]
                        and modelFrame_2P == g.script.frames_P2[i]
                    ):
                        del g.script.frames_P1[i]
                        del g.script.frames_P2[i]
            else:
                modelFrame = Frame.empty()
                for i in range(len(g.script.frames_P1) - 1, -1, -1):
                    modelFrame.step = i
                    modelFrame.buttonsOn = g.script.frames_P1[i].buttonsOn
                    modelFrame.buttonsOff = g.script.frames_P1[i].buttonsOff
                    if modelFrame == g.script.frames_P1[i]:
                        del g.script.frames_P1[i]

    # write all 1P and 2P frames to the same array
    g.script.combineFrames()

    if g.debug:
        debugFile = open(outfile + "-debug.csv", "w")

        debugFile.write(
            "Frame,2ndPlayer,Buttons,ButtonsOn,ButtonsOff,lx.r,ls.theta,ls.x,ls.y,rs.r,rs.theta,rs.x,rs.y,la.x,la.y,la.z,ra.x,ra.y,ra.z,lg.r.xx,lg.r.xy,lg.r.xz,lg.r.yx,lg.r.yy,lg.r.yz,lg.r.zx,lg.r.zy,lg.r.zz,lg.v.x,lg.v.y,lg.v.z,rg.r.xx,rg.r.xy,rg.r.xz,rg.r.yx,rg.r.yy,rg.r.yz,rg.r.zx,rg.r.zy,rg.r.zz,rg.v.x,rg.v.y,rg.v.z,Command\n"
        )
        for i in range(len(g.script.frames)):
            csv_writer = csv.writer(debugFile, delimiter=",")
            data = g.script.frames[i].toStrArray(g.script)
            csv_writer.writerow(data)
        debugFile.close()

    if g.nxtas:
        outf: FileIO = open(outfile, "w")  # type: ignore
        for frame in g.script.frames:
            outf.write(
                str(frame.step)  # type: ignore
                + " "
                + nxTAS_Buttons(frame.buttons, g.stas)
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

    elif g.stas:
        size: int = 0
        prevFrame: int = -1
        prevMotion = {
            0: {  # player 0
                "left": {"accel": Vector3f.zero(), "gyro": Vector3f.zero()},
                "right": {"accel": Vector3f.zero(), "gyro": Vector3f.zero()},
            },
            1: {  # player 1
                "left": {"accel": Vector3f.zero(), "gyro": Vector3f.zero()},
                "right": {"accel": Vector3f.zero(), "gyro": Vector3f.zero()},
            },
        }
        prevController = {
            0: {"buttons": 0, "lStick": Joystick.zero(), "rStick": Joystick.zero()},
            1: {"buttons": 0, "lStick": Joystick.zero(), "rStick": Joystick.zero()},
        }

        outf = open(outfile, "wb")  # type: ignore
        # File Header
        size += outf.write(b"STAS")
        size += outf.write(
            struct.pack("<3H2xQ", 0x0001, 0x0000, 0x0000, 0x0100000000010000)
        )  # Format Ver, Game Addon Ver, Editor Ver, Title Id

        # Script Header
        size += outf.write(struct.pack("<I", 0))  # TODO: Command Count
        size += outf.write(
            struct.pack("<I", g.script.frames[-1].step)
        )  # TODO: This is bad
        size += outf.write(struct.pack("<I", 0))  # Editing time in seconds
        size += outf.write(
            struct.pack("<8B", 2, 2 if g.script.is_two_player else 0, 0, 0, 0, 0, 0, 0)
        )  # Controller types per player

        size += writeAuthor(outf, g.script.author)

        size += writeTitle(outf, g.script.title)

        size += writeDesc(outf, g.script.description)

        if g.script.change_stage_name:
            writeCmdGo(
                outf,
                g.script.scenario_no,
                0,
                False,
                g.script.change_stage_name,
                g.script.change_stage_id,
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

        for frame in g.script.frames:
            if frame.step > prevFrame:  # do only for 1P frames
                prevFrame = frame.step
                writeCmdFrame(outf, frame.step)
                if frame.step == 0 and (
                    g.script.startPosition.x != 0
                    or g.script.startPosition.y != 0
                    or g.script.startPosition.z != 0
                ):
                    writeCmdTp(outf, g.script.startPosition, Quat4f.unit(), False)
                # parse commands, this relies on every step being included but that is okay
                for command_str in g.script.commands[frame.step]:
                    tokens = command_str.split(" ")
                    parseCommand(outf, tokens)

            # only write controller inputs if they differ
            if (prevController[frame.second_player]["buttons"] != frame.buttons) or (
                prevController[frame.second_player]["lStick"] != frame.left_stick
                or prevController[frame.second_player]["rStick"] != frame.right_stick
            ):
                writeCmdController(
                    outf,
                    frame.second_player,
                    frame.buttons.to_bytes(7, "little"),
                    frame.left_stick,
                    frame.right_stick,
                )
                if g.debug:
                    print(
                        "Wrote frame "
                        + str(frame.step)
                        + ", P2: "
                        + str(frame.second_player)
                    )

            prevController[frame.second_player] = {
                "buttons": frame.buttons,
                "lStick": frame.left_stick,
                "rStick": frame.right_stick,
            }

            if (frame.accel_left.NEQ0() or frame.gyro_left.ang_vel.NEQ0()) or (
                prevMotion[frame.second_player]["left"]["accel"].NEQ0()
                or prevMotion[frame.second_player]["left"]["gyro"].NEQ0()
            ):
                writeCmdMotion(
                    outf,
                    frame.second_player,
                    0,
                    frame.accel_left,
                    frame.gyro_left.ang_vel,
                )
                prevMotion[frame.second_player]["left"] = {
                    "accel": frame.accel_left,
                    "gyro": frame.gyro_left.ang_vel,
                }

            if (
                frame.accel_right.NEQ0()
                or frame.gyro_right.ang_vel.NEQ0()
                or (
                    prevMotion[frame.second_player]["right"]["accel"].NEQ0()
                    or prevMotion[frame.second_player]["right"]["gyro"].NEQ0()
                )
            ):
                writeCmdMotion(
                    outf,
                    frame.second_player,
                    1,
                    frame.accel_right,
                    frame.gyro_right.ang_vel,
                )
                prevMotion[frame.second_player]["right"] = {
                    "accel": frame.accel_left,
                    "gyro": frame.gyro_left.ang_vel,
                }

    else:  # TODO: maybe remove
        outf = open(outfile, "wb")  # type: ignore
        outf.write(b"BOOB")
        outf.write(
            struct.pack(
                "<I?3xi",
                len(g.script.frames),
                g.script.is_two_player,
                g.script.scenario_no,
            )
        )
        outf.write(
            bytes(g.script.change_stage_name, encoding="ascii")
            + b"\0" * (128 - len(g.script.change_stage_name))
        )
        outf.write(
            bytes(g.script.change_stage_id, encoding="ascii")
            + b"\0" * (128 - len(g.script.change_stage_id))
        )
        outf.write(
            struct.pack(
                "<3f",
                g.script.startPosition.x,
                g.script.startPosition.y,
                g.script.startPosition.z,
            )
        )

        for frame in g.script.frames:
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

    if ftp:
        ftp_config_file = open("ftp_config.json")
        ftp_config = json.load(ftp_config_file)
        ftp_config_file.close()

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
