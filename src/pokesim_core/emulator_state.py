"""Backend provenance and explicitly supported checkpoint compatibility."""
from functools import lru_cache
import hashlib
from importlib.metadata import distribution
from pathlib import Path

STATE_FORMAT = "pyboy-format-15"
LEGACY_PYBOY_VERSION = "2.7.0"


@lru_cache(maxsize=1)
def _runtime_provenance():
    installed = distribution("pyboy-rs")
    native = sorted(installed.locate_file(p) for p in installed.files or ()
                    if str(p).startswith("pyboy_rs/") and str(p).endswith((".so", ".pyd")))
    if len(native) != 1:
        raise RuntimeError("Cannot identify the installed native emulator")
    wrapper = Path(native[0]).parent / "pyboy.py"
    return {"backend": "pyboy-rs", "version": installed.version, "state_format": STATE_FORMAT,
            "native_sha256": hashlib.sha256(Path(native[0]).read_bytes()).hexdigest(),
            "binding_sha256": hashlib.sha256(wrapper.read_bytes()).hexdigest()}


def runtime_provenance():
    return dict(_runtime_provenance())


def validate_runtime(metadata, *, exact=False):
    """Allow known legacy imports, require the original build for exact resume."""
    source = metadata.get("emulator")
    if source is None:
        if not exact and metadata.get("pyboy_version") == LEGACY_PYBOY_VERSION:
            return
        if "pyboy_version" in metadata and not exact:
            raise ValueError("Checkpoint requires a different or unsupported emulator version")
        raise ValueError("Checkpoint requires explicit emulator provenance")
    if not isinstance(source, dict):
        raise ValueError("Invalid emulator provenance")
    if source.get("backend") != "pyboy-rs" or source.get("state_format") != STATE_FORMAT:
        raise ValueError("Unsupported checkpoint emulator or state format")
    if exact and source != runtime_provenance():
        raise ValueError("Resume requires the original emulator build")


def checkpoint_metadata():
    return {"emulator": dict(runtime_provenance())}


def runtime_identity(metadata):
    if "emulator" in metadata:
        return metadata["emulator"]
    return {"backend": "pyboy", "version": metadata.get("pyboy_version")}


def retag_checkpoint(metadata):
    """Describe newly serialized Rust output while retaining its source lineage."""
    previous = dict(runtime_identity(metadata))
    current = runtime_provenance()
    result = dict(metadata)
    result.pop("pyboy_version", None)
    result["emulator"] = current
    if previous != current:
        result["emulator_migration"] = {"from": previous, "to": dict(current)}
    return result


def same_runtime_or_recorded_migration(source, output):
    before, after = runtime_identity(source), runtime_identity(output)
    if before == after:
        return True
    try:
        validate_runtime(source)
        validate_runtime(output)
    except ValueError:
        return False
    return output.get("emulator_migration") == {"from": before, "to": after}
