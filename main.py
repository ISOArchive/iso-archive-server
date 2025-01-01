from typing import Annotated
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from more_itertools import unique_everseen, ilen
from itertools import islice

from os_types import OS, OSParams

from utils import get_all_os_manifests, get_filtered_os_manifests, get_archive_path

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://api.isoarchives.org",
        "https://isoarchives.org",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

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
    filtered_manifests = get_filtered_os_manifests(
        variants, names, versions, disketteSizes, floppySizes, archs, tags
    )

    variants_result = set()
    names_result = set()
    versions_result = set()
    disketteSizes_result = set()
    floppySizes_result = set()
    archs_result = set()
    tags_result = set()

    for os in filtered_manifests:
        variants_result.add(os["variant"])
        names_result.add(os["name"])
        versions_result.add(os["version"])
        disketteSizes_result.add(os["disketteSize"])
        floppySizes_result.add(os["floppySize"])
        archs_result.add(os["arch"])
        tags_result.update(os["tags"])

    return OSParams(
        variants=list(sorted(variants_result)),
        names=list(sorted(names_result)),
        versions=list(sorted(versions_result)),
        disketteSizes=list(sorted(disketteSizes_result)),
        floppySizes=list(sorted(floppySizes_result)),
        archs=list(sorted(archs_result)),
        tags=list(sorted(tags_result)),
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
    page: Annotated[int, Query(ge=0)] = 0,
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
    return list(islice(filtered_manifests, size * page, size * (page + 1)))
