"""
This script is a template for downloading files

change the pattern and the filename variable to match the files

also change the url in the main function and the get_links function to match the website you want to download from

i highly recommend changing the main function logic to only download the files you want

by default, the logger is set to INFO level, you can change it to DEBUG to see more information
"""

import asyncio
import logging
from pathlib import Path
import aiohttp
import aiofiles
from urllib.parse import urlsplit, unquote, urljoin
import re
import bs4
from typing import TypedDict
from enum import Enum


class DisketteSize(str, Enum):
    THREE_AND_A_HALF = "3.5"
    FIVE_AND_A_QUARTER = "5.25"


class FloppySize(str, Enum):
    THREE_AND_A_HALF_HD = "1.44MB"
    THREE_AND_A_HALF_DD = "720KB"
    FIVE_AND_A_QUARTER_HD = "1.2MB"
    FIVE_AND_A_QUARTER_DD = "360KB"


class Arch(str, Enum):
    ARM64 = "arm64"
    ARM64E = "arm64e"
    ARM = "arm"
    MIPS = "mips"
    X86 = "x86"
    AMD64 = "amd64"
    PPC = "ppc"
    PPC64 = "ppc64"
    PPC64LE = "ppc64le"
    M68K = "m68k"
    SPARC = "sparc"
    IA64 = "ia64"
    HPPA = "hppa"
    S390X = "s390x"


class OS(TypedDict):
    name: str
    version: str
    disketteSize: DisketteSize | None
    floppySize: FloppySize | None
    arch: list[Arch]
    tags: list[str]
    extension: str


def generate_filename(os: OS) -> str:
    lists = []
    lists.append(os["name"])
    lists.append(os["version"])
    if os["disketteSize"]:
        lists.append(os["disketteSize"])
    if os["floppySize"]:
        lists.append(os["floppySize"])
    lists.append(",".join(filter(lambda x: x, os["arch"])))
    lists.append(",".join([tag.title().replace("_", "-") for tag in os["tags"] if tag]))
    return "_".join(lists) + "." + os["extension"]


PATTERN = r"NAME-HERE-(?P<iso_type>\w+)-(?P<installation_type>\w+)-(?P<arch>[\w\d]+)-(?P<version>\d+(?:-\d+)*(?:\.\d+)*)"
DRY = False

semaphore = asyncio.Semaphore(5)

ARCHS = {
    "i386": "x86",
    "i686": "x86",
    "aarch64": "arm64",
    "powerpc": "ppc",
    "armhfp": "arm",
    "x86_64": "amd64",
}


async def download(url: str, dry: bool, chunk_size=1 << 15, tries=0):
    async with semaphore:
        urlpath = urlsplit(url).path
        filename = Path(unquote(urlpath)).name
        search = re.search(PATTERN, filename)
        if search:
            version = search.group("version")
            arch = search.group("arch")
            if arch in ARCHS:
                arch = ARCHS[arch]
            installation_type = search.group("installation_type")
            installation_type = (
                installation_type.title() if installation_type != "DVD" else "DVD"
            )
            filename = generate_filename(
                OS(
                    name="NAME-HERE",
                    version=version,
                    disketteSize=None,
                    floppySize=None,
                    arch=[Arch(arch)],
                    tags=[installation_type],
                    extension="iso",
                )
            )
        else:
            logging.error(f"{filename} does not match pattern")
            return
        path = Path(filename)
        if path.with_suffix(path.suffix + ".part").exists() or (
            path.exists() and path.stat().st_size == 0
        ):
            path.unlink(missing_ok=True)
        elif path.exists() and path.stat().st_size > 0:
            logging.warning(f"{filename} already exists")
            return
        try:
            logging.info("downloading %s", filename)
            connector = aiohttp.TCPConnector(limit=5, force_close=True)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, timeout=None) as response:
                    if not dry:
                        async with aiofiles.open(
                            path.with_suffix(path.suffix + ".part"), "wb"
                        ) as file:
                            while True:
                                chunk = await response.content.read(chunk_size)
                                if not chunk:
                                    break
                                await file.write(chunk)
                        path.with_suffix(path.suffix + ".part").rename(
                            path.with_suffix(path.suffix)
                        )
                    logging.info("done %s", filename)
        except Exception as e:
            path.unlink(missing_ok=True)
            logging.exception(e)
            logging.error("error while downloading %s", filename)
            if tries < 5:
                tries += 1
                logging.info("trying again...")
                asyncio.create_task(download(url, dry, chunk_size, tries))
            else:
                logging.error("giving up downloading %s", filename)


async def get_links(session: aiohttp.ClientSession, url: str) -> list[str]:
    logging.debug(f"Listing {url}")
    async with session.get(url) as resp:
        body = await resp.text()
        body = bs4.BeautifulSoup(body, "lxml")
        return [urljoin(url, x.get("href")) for x in body.find_all("a")]


async def main():
    downloaders = []

    connector = aiohttp.TCPConnector(limit=5, force_close=True)
    async with aiohttp.ClientSession(connector=connector) as session:
        links = await get_links(
            session,
            "https://example.com",
        )
        while links:
            for link in links:
                if link.endswith(".iso"):
                    downloaders.append(download(link, DRY))
                else:
                    links = await get_links(session, link)

    await asyncio.gather(*downloaders)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
