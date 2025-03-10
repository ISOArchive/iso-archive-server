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
import os


class DisketteSize(str, Enum):
    THREE_AND_A_HALF = "3.5"
    FIVE_AND_A_QUARTER = "5.25"


class FloppySize(str, Enum):
    THREE_AND_A_HALF_HD = "1.44MB"
    THREE_AND_A_HALF_DD = "720KB"
    FIVE_AND_A_QUARTER_HD = "1.2MB"
    FIVE_AND_A_QUARTER_DD = "360KB"


class Arch(str, Enum):
    ALPHA = "alpha"
    ARM64 = "arm64"
    ARM64E = "arm64e"
    ARM = "arm"
    ARMV7 = "armv7"
    MIPS = "mips"
    MIPS64 = "mips64"
    X86 = "x86"
    AMD64 = "amd64"
    PPC = "ppc"
    PPC64 = "ppc64"
    PPC64LE = "ppc64le"
    M68K = "m68k"
    SPARC = "sparc"
    IA64 = "ia64"
    HPPA = "hppa"
    S390 = "s390"
    S390X = "s390x"
    RISCV = "riscv"
    RISCV64 = "riscv64"
    LOONGARCH = "loongarch"
    LOONGARCH64 = "loongarch64"


class OS(TypedDict):
    name: str
    version: str
    disketteSize: DisketteSize | None
    floppySize: FloppySize | None
    arch: list[Arch | None]
    tags: list[str | None]
    extension: str


def generate_filename(os: OS) -> str:
    lists = []
    lists.append(os["name"])
    lists.append(os["version"].replace("_", "-"))
    if os["disketteSize"]:
        lists.append(os["disketteSize"])
    if os["floppySize"]:
        lists.append(os["floppySize"])
    lists.append(",".join([arch for arch in os["arch"] if arch]))
    lists.append(",".join([tag.replace("_", "-") for tag in os["tags"] if tag]))
    return "_".join([l for l in lists if l != ""]) + "." + os["extension"]


PATTERN = r"NAME-HERE-(?P<iso_type>\w+)-(?P<installation_type>\w+)-(?P<arch>[\w\d]+)-(?P<version>\d+(?:-\d+)*(?:\.\d+)*)"
DRY = os.getenv("DRY", False) == "True"

semaphore = asyncio.Semaphore(5)

ARCHS = {
    "i386": "x86",
    "i686": "x86",
    "aarch64": "arm64",
    "powerpc": "ppc",
    "ppc64el": "ppc64le",
    "armhfp": "arm",
    "armhf": "arm",
    "x86_64": "amd64",
}


async def download(url: str, dry: bool, chunk_size=1 << 15, tries=0):
    async with semaphore:
        urlpath = urlsplit(url).path
        filename = Path(unquote(urlpath)).name
        logging.debug("parsing %s", filename)
        search = re.search(PATTERN, filename)
        if search:
            version = search.group("version")
            arch = search.group("arch")
            if arch in ARCHS:
                arch = ARCHS[arch]
            installation_type = search.group("installation_type")
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
            if not dry:
                connector = aiohttp.TCPConnector(limit=5, force_close=True)
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.get(url, timeout=None) as response:
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
        pre = body.find("pre")
        if pre and isinstance(pre, bs4.element.Tag):
            return [
                urljoin(url, x.get("href"))
                for x in pre.find_all("a")
                if not (x.get("href").startswith("..") or x.get("href").startswith("?"))
            ]
        return []


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
    logging.basicConfig(level=os.getenv("LOGLEVEL", "INFO"))
    asyncio.run(main())
