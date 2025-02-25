from typing import Generator
from pathlib import Path
from os_types import OS, Arch, DisketteSize, FloppySize
import re
from dotenv import load_dotenv
from os import getenv
from watchdog.events import (
    FileCreatedEvent,
    FileDeletedEvent,
    FileMovedEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer, ObserverType

load_dotenv()

pattern = r"""
    (?P<os_name>[^_]+)                 # OS Name
    _(?P<version>[^_]+)                # Version or Build Number
    (?:_(?P<disk_size>[^_]+)           # Disk Size (optional)
    _(?P<floppy_size>[^_]+))?          # Floppy Size (optional)
    _(?P<arch>[^_]+(?:,[^_.]+)*)       # Architecture
    (?:_(?P<tags>[^_.]+(?:,[^_.]+)*))? # Tags (optional)
    \.(?P<extension>.+)                # File Extension
"""

filename_regex = re.compile(pattern, re.VERBOSE)


def get_archive_path() -> Path:
    return Path(getenv("ARCHIVE_PATH", "./"))


def get_os_file_list() -> Generator[str, None, None]:
    return (
        file.name
        for file in get_archive_path().rglob("*")
        if file.is_file() and not file.name.startswith("download")
    )


def get_os_manifest_from_path(path: Path) -> OS | None:
    try:
        varient = path.parts[3]
        match = filename_regex.match(path.name)
        if match is None:
            return None

        groups = match.groupdict()
        return OS(
            variant=varient,
            name=groups["os_name"],
            version=groups["version"],
            disketteSize=(
                DisketteSize(groups.get("disk_size"))
                if groups.get("disk_size")
                else None
            ),
            floppySize=(
                FloppySize(groups.get("floppy_size"))
                if groups.get("floppy_size")
                else None
            ),
            arch=[Arch(arch) for arch in groups["arch"].split(",")],
            tags=groups.get("tags") and groups["tags"].split(",") or [],
            extension=groups["extension"],
            size=path.stat().st_size,
            url=f"{getenv('DOWNLOAD_URL', '')}/{path.relative_to(get_archive_path())}",
        )
    except ValueError as e:
        print(f"Error parsing {path}: {e}")
        return None


CACHED_MANIFEST: list[OS] = []
IS_INITIALIZED = False
OBSERVER = Observer()


class FileHandler(FileSystemEventHandler):
    def on_created(self, event: FileCreatedEvent) -> None:
        super().on_created(event)
        path = event.src_path
        if type(path) == bytes:
            path = path.decode()
        result = get_os_manifest_from_path(Path(path))  # type: ignore
        if result:
            CACHED_MANIFEST.append(result)

    def on_deleted(self, event: FileDeletedEvent) -> None:
        super().on_deleted(event)
        path = event.src_path
        if type(path) == bytes:
            path = path.decode()
        result = get_os_manifest_from_path(Path(path))  # type: ignore
        if result:
            for i, os in enumerate(CACHED_MANIFEST):
                if os == result:
                    del CACHED_MANIFEST[i]

    def on_moved(self, event: FileMovedEvent) -> None:
        super().on_moved(event)
        if not event.is_directory:
            path = event.dest_path
            if type(path) == bytes:
                path = path.decode()
            result = get_os_manifest_from_path(Path(path))  # type: ignore
            if result:
                CACHED_MANIFEST.append(result)
            path = event.src_path
            if type(path) == bytes:
                path = path.decode()
            result = get_os_manifest_from_path(Path(path))  # type: ignore
            if result:
                for i, os in enumerate(CACHED_MANIFEST):
                    if os == result:
                        del CACHED_MANIFEST[i]


def generate_os_manifests():
    """
    Should be called once to generate all OS manifests
    """
    global CACHED_MANIFEST, IS_INITIALIZED
    if not IS_INITIALIZED:
        archive_path = get_archive_path()
        for path in archive_path.rglob("*"):
            if path.is_file():
                result = get_os_manifest_from_path(path)
                if result:
                    CACHED_MANIFEST.append(result)
        OBSERVER.schedule(FileHandler(), str(archive_path), recursive=True)
        OBSERVER.start()
        IS_INITIALIZED = True


def get_all_os_manifests() -> Generator[OS, None, None]:
    if not IS_INITIALIZED:
        generate_os_manifests()
    for m in CACHED_MANIFEST:
        yield m


def get_filtered_os_manifests(
    variants: list[str] | None = None,
    names: list[str] | None = None,
    versions: list[str] | None = None,
    disketteSizes: list[str] | None = None,
    floppySizes: list[str] | None = None,
    archs: list[str] | None = None,
    tags: list[str] | None = None,
    search: str | None = None,
) -> Generator[OS, None, None]:
    for os in get_all_os_manifests():
        if (
            (not variants or os["variant"] in variants)
            and (not names or os["name"] in names)
            and (not versions or os["version"] in versions)
            and (
                not disketteSizes
                or (os["disketteSize"] and os["disketteSize"].value in disketteSizes)
            )
            and (
                not floppySizes
                or (os["floppySize"] and os["floppySize"].value in floppySizes)
            )
            and (not archs or any(arch.value in archs for arch in os["arch"]))
            and (not tags or any(tag in os["tags"] for tag in tags))
            and (
                not search
                or search.lower() in os["variant"].lower()
                or search.lower() in os["name"].lower()
                or search.lower() in os["version"].lower()
                or (
                    os["disketteSize"]
                    and search.lower() in os["disketteSize"].value.lower()
                )
                or (
                    os["floppySize"]
                    and search.lower() in os["floppySize"].value.lower()
                )
                or any(search.lower() in arch.value.lower() for arch in os["arch"])
                or any(search.lower() in tag.lower() for tag in os["tags"])
            )
        ):
            yield os
