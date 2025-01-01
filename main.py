from typing import Annotated
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from more_itertools import unique_justseen, ilen
from itertools import islice

from os_types import OS, OSParams

from utils import get_all_os_manifests, get_filtered_os_manifests, get_archive_path

app = FastAPI()

app.mount("/download", StaticFiles(directory=get_archive_path()), name="download")


@app.get("/os/params/")
def get_os_params(
    variants: Annotated[list[str] | None, Query()] = None,
    names: Annotated[list[str] | None, Query()] = None,
    versions: Annotated[list[str] | None, Query()] = None,
    disketteSizes: Annotated[list[str] | None, Query()] = None,
    floppySizes: Annotated[list[str] | None, Query()] = None,
    archs: Annotated[list[str] | None, Query()] = None,
    tags: Annotated[list[str] | None, Query()] = None,
) -> OSParams:
    os_manifests = get_all_os_manifests()
    filtered_manifests = get_filtered_os_manifests(
        variants, names, versions, disketteSizes, floppySizes, archs, tags
    )

    variants_result = unique_justseen(os["variant"] for os in os_manifests)
    names_result = unique_justseen(os["name"] for os in filtered_manifests)
    versions_result = unique_justseen(os["version"] for os in filtered_manifests)
    disketteSizes_result = unique_justseen(
        os["disketteSize"] for os in filtered_manifests
    )
    floppySizes_result = unique_justseen(os["floppySize"] for os in filtered_manifests)
    archs_result = unique_justseen(os["arch"] for os in filtered_manifests)
    tags_result = unique_justseen(
        tag
        for os in filtered_manifests
        for tag in os["tags"]
        if not tags or tag in tags
    )

    return OSParams(
        variants=list(variants_result),
        names=list(names_result),
        versions=list(versions_result),
        disketteSizes=[size for size in disketteSizes_result if size is not None],
        floppySizes=[size for size in floppySizes_result if size is not None],
        archs=list(archs_result),
        tags=list(tags_result),
    )


@app.get("/os/count/")
def get_os_count(
    variants: Annotated[list[str] | None, Query()] = None,
    names: Annotated[list[str] | None, Query()] = None,
    versions: Annotated[list[str] | None, Query()] = None,
    disketteSizes: Annotated[list[str] | None, Query()] = None,
    floppySizes: Annotated[list[str] | None, Query()] = None,
    archs: Annotated[list[str] | None, Query()] = None,
    tags: Annotated[list[str] | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
) -> int:
    filtered_manifests = get_filtered_os_manifests(
        variants, names, versions, disketteSizes, floppySizes, archs, tags, search
    )

    return ilen(filtered_manifests)


@app.get("/os/")
def get_os(
    variants: Annotated[list[str] | None, Query()] = None,
    names: Annotated[list[str] | None, Query()] = None,
    versions: Annotated[list[str] | None, Query()] = None,
    disketteSizes: Annotated[list[str] | None, Query()] = None,
    floppySizes: Annotated[list[str] | None, Query()] = None,
    archs: Annotated[list[str] | None, Query()] = None,
    tags: Annotated[list[str] | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    ascBy: Annotated[str | None, Query()] = None,
    descBy: Annotated[str | None, Query()] = None,
    size: Annotated[int, Query(ge=1, le=100)] = 10,
    page: Annotated[int, Query(ge=1)] = 1,
) -> list[OS]:
    filtered_manifests = get_filtered_os_manifests(
        variants, names, versions, disketteSizes, floppySizes, archs, tags, search
    )

    sort_key = ascBy or descBy
    if sort_key is not None:
        filtered_manifests = sorted(
            filtered_manifests,
            key=lambda os: os.get(sort_key, ""),
            reverse=bool(descBy),
        )
    return list(islice(filtered_manifests, size * (page - 1), size * page))
