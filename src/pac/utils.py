from __future__ import annotations

import hashlib
import re
import shutil
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

from pac.models import SourceKind
from pac.paths import ProjectPaths

ARXIV_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/([^/?#]+)", re.IGNORECASE)
LINK_RE = re.compile(r"https?://[^\s<>)\]]+")
SAFE_ID_RE = re.compile(r"[^a-z0-9]+")


def is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def short_hash(value: str, length: int = 12) -> str:
    return sha256_text(value)[:length]


def slugify(value: str, *, fallback: str = "untitled") -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = SAFE_ID_RE.sub("-", ascii_value.lower()).strip("-")
    return slug or fallback


def title_from_id(object_id: str) -> str:
    return object_id.replace("-", " ").title()


def detect_source_kind(source: str, explicit: str = "auto") -> SourceKind:
    if explicit != "auto":
        return SourceKind(explicit)
    if is_url(source):
        parsed = urlparse(source)
        if "arxiv.org" in parsed.netloc.lower():
            return SourceKind.ARXIV
        if parsed.netloc.lower() == "github.com" or parsed.netloc.lower().endswith(".github.com"):
            return SourceKind.GITHUB_REPO
        return SourceKind.URL
    if Path(source).suffix.lower() == ".pdf":
        return SourceKind.PDF
    return SourceKind.URL


def resolve_local_path(paths: ProjectPaths, source: str) -> Path:
    candidate = Path(source).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (paths.root / candidate).resolve()


def source_stem(source: str, kind: SourceKind) -> str:
    if kind in {SourceKind.PDF, SourceKind.ANNOTATED_PDF, SourceKind.IMPLEMENTATION_REPO}:
        return Path(source).stem or Path(source).name
    parsed = urlparse(source)
    if kind == SourceKind.ARXIV:
        match = ARXIV_RE.search(source)
        if match:
            return f"arxiv-{match.group(1)}"
    if kind == SourceKind.GITHUB_REPO:
        parts = [part for part in parsed.path.strip("/").split("/") if part]
        if len(parts) >= 2:
            return f"{parts[0]}-{parts[1]}"
    path_name = Path(parsed.path).stem or parsed.netloc
    return f"{parsed.netloc}-{path_name}"


def stable_intake_id(source: str) -> str:
    return f"intake-{short_hash(source)}"


def stable_source_id(source: str, kind: SourceKind) -> str:
    return f"{kind.value}-{slugify(source_stem(source, kind))}-{short_hash(source, 8)}"


def stable_object_id(source: str, kind: SourceKind) -> str:
    return slugify(source_stem(source, kind))


def copy_without_overwrite(source: Path, destination: Path) -> tuple[Path, bool]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_hash = sha256_file(source)
    if destination.exists():
        if sha256_file(destination) == source_hash:
            return destination, False
        destination = destination.with_name(
            f"{destination.stem}-{source_hash[:8]}{destination.suffix}"
        )
    if destination.exists():
        return destination, False
    shutil.copy2(source, destination)
    return destination, True
