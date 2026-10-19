from struct import pack
from io import FileIO
from lib.classes import Joystick, Vector3f, Quat4f


def align_up(value, alignment):
    return ((value + alignment - 1) // alignment) * alignment


def writeAuthor(file: FileIO, name: str) -> int:
    author = bytes(name, "utf-8") + b"\x00"
    size = file.write(pack("<H", len(author)))  # Author Length
    size += file.write(author)  # Author
    align = align_up(size, 4)
    size += file.write(pack(f"<{align-size}x"))
    return size


def writeTitle(file: FileIO, title: str) -> int:
    _title = bytes(title, "utf-8") + b"\x00"
    size = file.write(pack("<I", len(_title)))  # Title Length
    size += file.write(_title)
    align = align_up(size, 4)
    size += file.write(pack(f"<{align-size}x"))
    return size


def writeDesc(file: FileIO, desc: str) -> int:
    _desc = bytes(desc, "utf-8") + b"\x00"
    size = file.write(pack("<I", len(_desc)))  # Description Length
    size += file.write(_desc)
    align = align_up(size, 4)
    size += file.write(pack(f"<{align-size}x"))
    return size


def writeCommand(file: FileIO, type: int, data: bytes) -> None:
    file.write(pack("<H", type))
    file.write(len(data).to_bytes(6, "little"))
    file.write(data)


def writeCmdFrame(file: FileIO, frame: int) -> None:
    data: bytes = frame.to_bytes(4, "little")
    # print(f"CmdFrame: {frame}")

    writeCommand(file, 0, data)


def writeCmdController(
    file: FileIO, player: int, buttons: bytes, left: Joystick, right: Joystick
) -> None:
    data: bytes = player.to_bytes(1, "little")
    data += buttons
    data += left.x.to_bytes(4, "little", signed=True)
    data += left.y.to_bytes(4, "little", signed=True)
    data += right.x.to_bytes(4, "little", signed=True)
    data += right.y.to_bytes(4, "little", signed=True)
    # print(f"CmdController: {player}, {bin(int.from_bytes(buttons,"little"))}, {left.x}, {left.y}, {right.x}, {right.y}")

    writeCommand(file, 1, data)


def writeCmdMotion(
    file: FileIO, player: int, controllerID: int, accel: Vector3f, gyro: Vector3f
) -> None:
    data: bytes = player.to_bytes(1, "little")
    data += controllerID.to_bytes(1, "little")
    data += pack("<2x")
    data += pack("<3f", accel.x, accel.y, accel.z)
    data += pack("<3f", gyro.x, gyro.y, gyro.z)
    # print(f"CmdMotion: {player}, {controllerID}, {accel.x}, {accel.y}, {accel.z}, {gyro.x}, {gyro.y}, {gyro.z}")

    writeCommand(file, 2, data)


def writeCmdSaveFile(file: FileIO, id: int, reload: bool) -> None:
    data: bytes = pack("<b?", id, reload)
    writeCommand(file, 0xC000, data)


def writeCmdGo(
    file: FileIO,
    scenario: int,
    subScenario: int,
    returnPrev: bool,
    stageName: str,
    entr: str,
) -> None:
    data: bytes = pack("<BB?x", scenario, subScenario, returnPrev)
    data += (len(stageName) + 1).to_bytes(2, "little")
    data += bytes(stageName, "utf-8") + b"\x00"
    size = len(data)
    data += pack(f"{align_up(size,4)-size}x")
    data += (len(entr) + 1).to_bytes(2, "little")
    data += bytes(entr, "utf-8") + b"\x00"

    writeCommand(file, 0xC001, data)


def writeCmdTp(file: FileIO, pos: Vector3f, rot: Quat4f, isCap: bool) -> None:
    data: bytes = pack("<3f", pos.x, pos.y, pos.z)
    data += pack("<4f", rot.x, rot.y, rot.z, rot.w)
    writeCommand(file, 0xC003 if isCap else 0xC002, data)


def writeCmdAbsStick(file: FileIO, enable: bool) -> None:
    data: bytes = pack("<?", enable)
    data += pack("<3x")
    writeCommand(file, 0xC004, data)


def writeCmdSpeedup(file: FileIO, speed: int) -> None:
    data: bytes = pack("<b", speed)
    data += pack("<3x")
    writeCommand(file, 0xC005, data)


def writeCmdDemo(file: FileIO, enable: bool) -> None:
    data: bytes = pack("<?", enable)
    data += pack("<3x")
    writeCommand(file, 0xC007, data)


def writeCmdSection(file: FileIO, player: bool, taser: str) -> None:
    data: bytes = pack("<b", player)
    data += int(len(taser) + 1).to_bytes(2, "little")
    data += bytes(taser, "utf-8") + b"\x00"
    size = len(data)
    data += pack(f"{align_up(size,4)-size}x")
    writeCommand(file, 0xC008, data)
