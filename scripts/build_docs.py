"""Build and verify the public site, including RTD metadata and agent exports."""

import gzip
import json
import os
import subprocess  # noqa: S404 -- invokes the local documentation builder, without a shell
import sys
import tempfile
import tomllib
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from xml.etree import ElementTree as ET  # noqa: S405 -- parses our own generated sitemap

from bs4 import BeautifulSoup
from markdownify import markdownify

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".build/docs"


def page_url(path: Path, base_url: str) -> str:
    relative = path.relative_to(OUTPUT).as_posix()
    return urljoin(base_url, relative.removesuffix("index.html"))


def build(base_url: str) -> None:
    source = (ROOT / "zensical.toml").read_text()
    original_url = tomllib.loads(source)["project"]["site_url"]
    source = source.replace(
        f"site_url = {json.dumps(original_url)}", f"site_url = {json.dumps(base_url)}", 1
    )
    # Keep the configuration next to the original: relative source paths stay valid.
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".toml", prefix=".zensical-", dir=ROOT
    ) as config:
        config.write(source)
        config.flush()
        subprocess.run(  # noqa: S603 -- arguments are fixed and configuration is local
            [
                sys.executable,
                "-m",
                "zensical",
                "build",
                "--clean",
                "--strict",
                "-f",
                config.name,
            ],
            cwd=ROOT,
            check=True,
        )


def finish_pages(base_url: str, version: str, noindex: bool) -> dict[Path, BeautifulSoup]:
    pages = {}
    index = [
        "# unihttp",
        "",
        "> Declarative, typed Python API clients. Choose an HTTP backend and serializer.",
        "",
        f"Documentation version: {version}. latest tracks development, not a release.",
        "",
        "## Documentation",
        "",
    ]
    for path in sorted(OUTPUT.rglob("*.html")):
        soup = BeautifulSoup(path.read_text(), "html.parser")
        article = soup.select_one("article.md-content__inner")
        if article is None or path.name == "404.html":
            if noindex or path.name == "404.html":
                tag = soup.new_tag("meta", attrs={"name": "robots", "content": "noindex"})
                soup.head.append(tag)
                path.write_text(str(soup))
            pages[path] = soup
            continue
        title = article.find("h1")
        description = soup.find("meta", attrs={"name": "description"})
        if title is None or description is None or not description.get("content"):
            raise ValueError(f"Missing heading or description: {path}")
        canonical = soup.find("link", rel="canonical")
        expected_url = page_url(path, base_url)
        if canonical is None or canonical.get("href") != expected_url:
            raise ValueError(f"Incorrect canonical URL: {path}")
        if noindex:
            soup.head.append(
                soup.new_tag("meta", attrs={"name": "robots", "content": "noindex"})
            )
        markdown_path = Path("markdown") / path.relative_to(OUTPUT).with_suffix(".md")
        alternate = soup.new_tag(
            "link",
            attrs={
                "rel": "alternate",
                "type": "text/markdown",
                "href": urljoin(base_url, markdown_path.as_posix()),
            },
        )
        soup.head.append(alternate)
        # Convert the article, not navigation. This expands snippets and API directives.
        content = BeautifulSoup(str(article), "html.parser")
        for element in content.select(".headerlink, .md-content__button"):
            element.decompose()
        label_exported_tabs(content)
        for link in content.find_all("a", href=True):
            link["href"] = urljoin(expected_url, link["href"])
        text = markdownify(str(content), heading_style="ATX")
        if "--8<--" in text or "::: unihttp" in text:
            raise ValueError(f"Unexpanded documentation directive: {path}")
        destination = OUTPUT / markdown_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(f"Source: {expected_url}\n\n{text.strip()}\n")
        label = title.get_text(" ", strip=True).replace("¶", "").strip()
        index.append(f"- [{label}]({alternate['href']}): {description['content']}")
        path.write_text(str(soup))
        pages[path] = soup
    (OUTPUT / "llms.txt").write_text("\n".join(index) + "\n")
    return pages


def label_exported_tabs(content: BeautifulSoup) -> None:
    """Keep each tab's label beside its content, including inactive and nested tabs."""
    for group in reversed(content.select(".tabbed-set")):
        labels = group.select(":scope > .tabbed-labels > label")
        panels = group.select(":scope > .tabbed-content > .tabbed-block")
        if not labels or len(labels) != len(panels):
            raise ValueError("Cannot associate exported tab labels with content")
        for label, panel in zip(labels, panels, strict=True):
            paragraph = content.new_tag("p")
            name = content.new_tag("strong")
            name.string = label.get_text(" ", strip=True)
            paragraph.append(name)
            panel.insert(0, paragraph)
        for control in group.select(":scope > input, :scope > .tabbed-labels"):
            control.decompose()


def verify_links(pages: dict[Path, BeautifulSoup], base_url: str) -> None:  # noqa: C901
    base = urlsplit(base_url)
    errors = []
    for path, soup in pages.items():
        # 404 URLs have no stable relative location when served for missing paths.
        if path.name == "404.html":
            continue
        for element in soup.select("a[href], link[href], script[src], img[src]"):
            href = element.get("href", element.get("src", ""))
            target = urlsplit(urljoin(page_url(path, base_url), href))
            if target.netloc != base.netloc or target.scheme not in {"http", "https"}:
                continue
            if not target.path.startswith(base.path):
                errors.append(f"{path}: link leaves this documentation version: {href}")
                continue
            relative = unquote(target.path[len(base.path) :])
            resolved = OUTPUT / relative
            if target.path.endswith("/"):
                resolved /= "index.html"
            if not resolved.is_file():
                errors.append(f"{path}: missing target: {href}")
            elif target.fragment and resolved in pages:
                anchor = unquote(target.fragment)
                if pages[resolved].find(id=anchor) is None:
                    errors.append(f"{path}: missing anchor: {href}")
    if errors:
        raise ValueError("\n".join(errors))


def verify_api_reference(pages: dict[Path, BeautifulSoup]) -> None:
    """Fail if the generator silently hides essential public signatures."""
    clients = pages[OUTPUT / "reference/clients/index.html"]
    for identifier in (
        "unihttp.clients.httpx.HTTPXSyncClient",
        "unihttp.clients.httpx.HTTPXAsyncClient",
    ):
        heading = clients.find(id=identifier)
        signature = heading.parent.select_one(".doc-signature") if heading else None
        if signature is None or not all(
            parameter in signature.get_text()
            for parameter in ("base_url", "request_dumper", "response_loader", "session")
        ):
            raise ValueError(f"Missing public constructor signature: {identifier}")

    serializers = pages[OUTPUT / "reference/serializers/index.html"]
    symbols = [
        "unihttp.serialize.RequestDumper.dump",
        "unihttp.serialize.ResponseLoader.load",
    ]
    for backend, prefix in (
        ("adaptix", "Adaptix"),
        ("pydantic", "Pydantic"),
        ("msgspec", "Msgspec"),
    ):
        symbols.extend((
            f"unihttp.serializers.{backend}.serialize.{prefix}Dumper.dump",
            f"unihttp.serializers.{backend}.serialize.{prefix}Loader.load",
        ))
    for identifier in symbols:
        if serializers.find(id=identifier) is None:
            raise ValueError(f"Missing public serializer method: {identifier}")


def verify_redirects(
    pages: dict[Path, BeautifulSoup], base_url: str, redirects: dict[str, str]
) -> None:
    """Verify that moved documentation still resolves to its consolidated page."""

    def html_path(source: str) -> Path:
        path = Path(source)
        if path.name == "index.md":
            return OUTPUT / path.with_suffix(".html")
        return OUTPUT / path.with_suffix("") / "index.html"

    for source, target in redirects.items():
        old_path = html_path(source)
        target_path = html_path(target)
        if old_path not in pages or target_path not in pages:
            raise ValueError(f"Missing redirect or destination: {source} -> {target}")
        soup = pages[old_path]
        canonical = soup.find("link", rel="canonical")
        refresh = soup.find("meta", attrs={"http-equiv": "refresh"})
        expected = page_url(target_path, base_url)
        old_url = page_url(old_path, base_url)
        if canonical is None or urljoin(old_url, canonical.get("href", "")) != expected:
            raise ValueError(f"Incorrect redirect canonical: {source}")
        destination = refresh.get("content", "").partition("url=")[2] if refresh else ""
        if not destination or urljoin(old_url, destination) != expected:
            raise ValueError(f"Incorrect redirect destination: {source}")


def verify_sitemap(base_url: str, noindex: bool) -> None:
    path = OUTPUT / "sitemap.xml"
    tree = ET.parse(path)  # noqa: S314 -- local output from Zensical, not untrusted XML
    root = tree.getroot()
    for location in root.findall(".//{*}loc"):
        if not location.text or not location.text.startswith(base_url):
            raise ValueError("Sitemap contains a URL outside the canonical version")
    if noindex:
        for child in list(root):
            root.remove(child)
        tree.write(path, encoding="utf-8", xml_declaration=True)
        # Zensical may emit a compressed copy; keep it consistent with the XML.
        compressed = OUTPUT / "sitemap.xml.gz"
        if compressed.exists():
            compressed.write_bytes(gzip.compress(path.read_bytes()))


def main() -> None:
    config = tomllib.loads((ROOT / "zensical.toml").read_text())["project"]
    base_url = (
        os.environ.get("READTHEDOCS_CANONICAL_URL", config["site_url"]).rstrip("/") + "/"
    )
    if urlsplit(base_url).scheme not in {"http", "https"}:
        raise ValueError("The documentation URL must be an absolute HTTP(S) URL")
    version = os.environ.get("READTHEDOCS_VERSION", "latest")
    version_type = os.environ.get("READTHEDOCS_VERSION_TYPE", "branch")
    noindex = (
        os.environ.get("DOCS_NOINDEX") == "1"
        or version_type == "external"
        or (version_type == "branch" and version not in {"latest", "stable"})
    )
    build(base_url)
    pages = finish_pages(base_url, version, noindex)
    verify_links(pages, base_url)
    verify_api_reference(pages)
    verify_redirects(pages, base_url, config["plugins"]["redirects"]["redirect_maps"])
    verify_sitemap(base_url, noindex)
    print(
        f"Verified {len(pages)} HTML pages; generated Markdown and llms.txt in {OUTPUT}"
    )


if __name__ == "__main__":
    main()
