"""ROM identity without importing the emulator or modifying user files."""
from dataclasses import dataclass
import hashlib
from pathlib import Path

RED_SHA1 = "ea9bcae617fdf159b045185467ae58b2e4a48b9a"
BLUE_SHA1 = "d7037c83e1ae5b39bde3c30787637ba1d4c48ce2"
KNOWN_ROM_SHA1 = {
    RED_SHA1: "Pokemon Red (USA, Europe)",
    BLUE_SHA1: "Pokemon Blue (USA, Europe)",
}
_GAMES = {RED_SHA1: "red", BLUE_SHA1: "blue"}


@dataclass(frozen=True)
class RomInfo:
    sha1: str
    sha256: str
    game: str | None
    name: str
    verified: bool


def inspect_rom(path: str | Path) -> RomInfo:
    """Hash a ROM in read-only mode. Unknown ROMs are described without acceptance."""
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            sha1.update(chunk)
            sha256.update(chunk)
    identity = sha1.hexdigest()
    return RomInfo(identity, sha256.hexdigest(), _GAMES.get(identity),
                   KNOWN_ROM_SHA1.get(identity, "Unknown ROM"), identity in KNOWN_ROM_SHA1)


def require_rom(path: str | Path, *, allowed_games=("red", "blue")) -> RomInfo:
    """Require a verified supported ROM before starting an emulator."""
    info = inspect_rom(path)
    if not info.verified or info.game not in allowed_games:
        raise ValueError("Unsupported ROM hash. A clean supported Pokemon Red or Blue ROM is required.")
    return info
