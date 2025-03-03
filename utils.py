from typing import Generator
from pathlib import Path
from os_types import OS, Arch, DisketteSize, FloppySize
import re
from dotenv import load_dotenv
from os import getenv
import watchfiles, threading

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


def get_os_manifest_from_path(path: Path, without_size=False) -> OS | None:
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
            size=path.stat().st_size if not without_size else 0,
            url=f"{getenv('DOWNLOAD_URL', '')}/{path.relative_to(get_archive_path())}",
        )
    except ValueError as e:
        print(f"Error parsing {path}: {e}")
        return None


CACHED_MANIFEST: list[OS] = []
IS_INITIALIZED = False


def watch_file_changes():
    for changes in watchfiles.watch(get_archive_path()):
        for change_type, path in changes:
            if change_type == 1:
                result = get_os_manifest_from_path(Path(path))
                if result:
                    CACHED_MANIFEST.append(result)
            elif change_type == 3:
                result = get_os_manifest_from_path(Path(path), without_size=True)
                if result:
                    for i, os in enumerate(CACHED_MANIFEST):
                        if os["url"] == result["url"]:
                            del CACHED_MANIFEST[i]


def generate_os_manifests():
    """
    Should be called once to generate all OS manifests
    """
    global CACHED_MANIFEST, IS_INITIALIZED
    if not IS_INITIALIZED:
        IS_INITIALIZED = True
        archive_path = get_archive_path()
        for path in archive_path.rglob("*"):
            if path.is_file():
                result = get_os_manifest_from_path(path)
                if result:
                    CACHED_MANIFEST.append(result)
        threading.Thread(target=watch_file_changes, daemon=True).start()


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


def get_filtered_os_params(
    variants: list[str] | None = None,
    names: list[str] | None = None,
    versions: list[str] | None = None,
    disketteSizes: list[str] | None = None,
    floppySizes: list[str] | None = None,
    archs: list[str] | None = None,
    tags: list[str] | None = None,
    search: str | None = None,
) -> tuple[set, set, set, set, set, set, set]:
    variants_result = set()
    names_result = set()
    versions_result = set()
    disketteSizes_result = set()
    floppySizes_result = set()
    archs_result = set()
    tags_result = set()

    option_list = {
        "variant",
        "name",
        "version",
        "disketteSize",
        "floppySize",
        "arch",
        "tags",
    }

    for os in get_all_os_manifests():
        unused_options = set()

        if variants is not None and os["variant"] not in variants:
            unused_options.update(option_list.difference(("variant",)))

        if names is not None and os["name"] not in names:
            unused_options.update(option_list.difference(("name",)))

        if versions is not None and os["version"] not in versions:
            unused_options.update(option_list.difference(("version",)))

        if disketteSizes is not None and (
            os["disketteSize"] is None or os["disketteSize"].value not in disketteSizes
        ):
            unused_options.update(option_list.difference(("disketteSize",)))

        if floppySizes is not None and (
            os["floppySize"] is None or os["floppySize"].value not in floppySizes
        ):
            unused_options.update(option_list.difference(("floppySize",)))

        if archs is not None and not any(arch.value in archs for arch in os["arch"]):
            unused_options.update(option_list.difference(("arch",)))

        if tags is not None and not any(tag in os["tags"] for tag in tags):
            unused_options.update(option_list.difference(("tags",)))

        if search is not None and (
            True
            and search.lower() not in os["variant"].lower()
            and search.lower() not in os["name"].lower()
            and search.lower() not in os["version"].lower()
            and not any(search.lower() in arch.value.lower() for arch in os["arch"])
            and not any(search.lower() in tag.lower() for tag in os["tags"])
            and not (
                os["disketteSize"]
                and search.lower() in os["disketteSize"].value.lower()
            )
            and not (
                os["floppySize"] and search.lower() in os["floppySize"].value.lower()
            )
        ):
            unused_options.update(option_list)

        if "variant" not in unused_options:
            variants_result.add(os["variant"])
        if "name" not in unused_options:
            names_result.add(os["name"])
        if "version" not in unused_options:
            versions_result.add(os["version"])
        if "disketteSize" not in unused_options:
            disketteSizes_result.add(os["disketteSize"])
        if "floppySize" not in unused_options:
            floppySizes_result.add(os["floppySize"])
        if "arch" not in unused_options:
            archs_result.update(os["arch"])
        if "tags" not in unused_options:
            tags_result.update(os["tags"])

    return (
        variants_result,
        names_result,
        versions_result,
        disketteSizes_result,
        floppySizes_result,
        archs_result,
        tags_result,
    )
