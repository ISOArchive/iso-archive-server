from typing_extensions import TypedDict
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
    variant: str
    name: str
    version: str
    disketteSize: DisketteSize | None
    floppySize: FloppySize | None
    arch: list[Arch]
    tags: list[str]
    extension: str
    size: int
    url: str


class OSParams(TypedDict):
    variants: list[str]
    names: list[str]
    versions: list[str]
    disketteSizes: list[DisketteSize]
    floppySizes: list[FloppySize]
    archs: list[Arch]
    tags: list[str]
