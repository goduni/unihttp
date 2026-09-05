"""Verify deployment metadata and that exported docs contain usable content."""

import pytest

pytest.importorskip("markdownify")
BeautifulSoup = pytest.importorskip("bs4").BeautifulSoup

from scripts import build_docs


@pytest.fixture
def rendered_site(tmp_path, monkeypatch):
    monkeypatch.setattr(build_docs, "OUTPUT", tmp_path)
    return tmp_path


def write_page(root, relative="index.html", content="<p>Documentation</p>"):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    url = "https://docs.example.com/en/v1/" + relative.removesuffix("index.html")
    path.write_text(f'''<!doctype html><html><head><title>Test</title>
<meta name="description" content="Example description">
<link rel="canonical" href="{url}"></head><body>
<nav>Not part of the article</nav>
<article class="md-content__inner"><h1>Example</h1>{content}</article>
</body></html>''')
    return path


def test_preview_exports_and_metadata(rendered_site):
    path = write_page(
        rendered_site,
        content='<h2 id="api">API</h2><pre><code>class User: pass</code></pre>',
    )
    pages = build_docs.finish_pages("https://docs.example.com/en/v1/", "123", True)
    build_docs.verify_links(pages, "https://docs.example.com/en/v1/")
    soup = BeautifulSoup(path.read_text(), "html.parser")
    assert soup.find("meta", attrs={"name": "robots"})["content"] == "noindex"
    exported = (rendered_site / "markdown/index.md").read_text()
    assert "class User: pass" in exported
    assert "Not part of the article" not in exported
    assert "Development documentation" not in exported
    assert (
        "https://docs.example.com/en/v1/markdown/index.md"
        in (rendered_site / "llms.txt").read_text()
    )


def test_release_is_indexable(rendered_site):
    write_page(rendered_site)
    pages = build_docs.finish_pages("https://docs.example.com/en/v1/", "v1", False)
    soup = pages[rendered_site / "index.html"]
    assert soup.find("meta", attrs={"name": "robots"}) is None
    assert "Documentation version:" not in soup.get_text()
    assert "Documentation version: v1." in (rendered_site / "llms.txt").read_text()


def test_latest_has_no_development_banner(rendered_site):
    write_page(rendered_site)
    pages = build_docs.finish_pages("https://docs.example.com/en/v1/", "latest", False)
    soup = pages[rendered_site / "index.html"]
    assert "Development documentation" not in soup.get_text()
    assert "may include unreleased changes" not in soup.get_text()
    assert (
        "Development documentation"
        not in (rendered_site / "markdown/index.md").read_text()
    )
    assert "Documentation version: latest." in (rendered_site / "llms.txt").read_text()


@pytest.mark.parametrize("href", ["missing/", "#missing", "/en/latest/"])
def test_broken_links_fail(rendered_site, href):
    write_page(rendered_site, content=f'<a href="{href}">Broken</a>')
    pages = build_docs.finish_pages("https://docs.example.com/en/v1/", "v1", False)
    with pytest.raises(ValueError):
        build_docs.verify_links(pages, "https://docs.example.com/en/v1/")


def test_preview_sitemap_has_no_indexable_urls(rendered_site):
    path = rendered_site / "sitemap.xml"
    path.write_text(
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://docs.example.com/en/v1/</loc></url></urlset>'
    )
    build_docs.verify_sitemap("https://docs.example.com/en/v1/", True)
    assert "<loc>" not in path.read_text()


def test_wrong_canonical_fails(rendered_site):
    write_page(rendered_site)
    with pytest.raises(ValueError, match="canonical"):
        build_docs.finish_pages("https://wrong.example.com/", "v1", False)


@pytest.mark.parametrize(
    "prefix", ["https://docs.example.com/en/latest/", "https://custom.example/v1/"]
)
def test_redirects_keep_canonical_and_skip_article_exports(rendered_site, prefix):
    write_page(rendered_site)
    old = rendered_site / "old" / "index.html"
    old.parent.mkdir()
    old.write_text(
        '<html><head><link rel="canonical" href="../"><meta http-equiv="refresh" content="0; url=../"></head><body><a href="../">Moved</a></body></html>'
    )
    pages = build_docs.finish_pages("https://docs.example.com/en/v1/", "v1", False)
    build_docs.verify_redirects(pages, prefix, {"old.md": "index.md"})
    assert not (rendered_site / "markdown/old/index.md").exists()
    assert "old/index.md" not in (rendered_site / "llms.txt").read_text()
    pages[old].find("meta")["content"] = "0; url=missing/"
    with pytest.raises(ValueError, match="redirect destination"):
        build_docs.verify_redirects(pages, prefix, {"old.md": "index.md"})


def test_tab_exports_keep_labels_and_inactive_code(rendered_site):
    import markdown

    content = markdown.markdown(
        '=== "HTTPX"\n\n    ```python\n    from unihttp.clients.httpx import HTTPXSyncClient\n    ```\n\n'
        '=== "aiohttp"\n\n    ```python\n    from unihttp.clients.aiohttp import AiohttpAsyncClient\n    ```',
        extensions=["pymdownx.superfences", "pymdownx.tabbed"],
        extension_configs={"pymdownx.tabbed": {"alternate_style": True}},
    )
    path = write_page(rendered_site, content=content)
    build_docs.finish_pages("https://docs.example.com/en/v1/", "v1", False)
    exported = (rendered_site / "markdown/index.md").read_text()
    assert exported.index("**HTTPX**") < exported.index("HTTPXSyncClient")
    assert exported.index("HTTPXSyncClient") < exported.index("**aiohttp**")
    assert exported.index("**aiohttp**") < exported.index("AiohttpAsyncClient")
    html = BeautifulSoup(path.read_text(), "html.parser")
    assert len(html.select(".tabbed-set > input")) == 2
    assert len(html.select(".tabbed-labels > label")) == 2


@pytest.fixture
def installation_html():
    import markdown

    source = (build_docs.ROOT / "site/getting-started/installation.md").read_text()
    return markdown.markdown(
        source.split("---", 2)[2],
        extensions=["attr_list", "md_in_html", "pymdownx.superfences", "pymdownx.tabbed"],
        extension_configs={"pymdownx.tabbed": {"alternate_style": True}},
    )


def test_installation_covers_all_backend_serializer_combinations(installation_html):
    import shlex
    import tomllib

    project = tomllib.loads((build_docs.ROOT / "pyproject.toml").read_text())["project"]
    extras = project["optional-dependencies"]
    soup = BeautifulSoup(installation_html, "html.parser")
    picker = soup.select_one(".uh-install-picker > .tabbed-set")
    labels = picker.select(":scope > .tabbed-labels > label")
    panels = picker.select(":scope > .tabbed-content > .tabbed-block")
    assert {label.get_text().lower() for label in labels} == {
        "httpx",
        "requests",
        "aiohttp",
        "httpx2",
        "niquests",
        "zapros",
        "urllib",
    }
    for label, panel in zip(labels, panels, strict=True):
        backend = label.get_text().lower()
        serializers = panel.select_one(".tabbed-set")
        names = serializers.select(":scope > .tabbed-labels > label")
        commands = serializers.select(":scope > .tabbed-content > .tabbed-block")
        assert {name.get_text().lower() for name in names} == {
            "adaptix",
            "pydantic",
            "msgspec",
        }
        for name, command in zip(names, commands, strict=True):
            selected = ([backend] if backend != "urllib" else []) + [
                name.get_text().lower()
            ]
            assert set(selected) <= extras.keys()
            package = "unihttp[" + ",".join(selected) + "]"
            blocks = command.select("pre > code")
            assert len(blocks) == 2
            assert shlex.split(blocks[0].get_text()) == [
                "python",
                "-m",
                "pip",
                "install",
                package,
            ]
            assert shlex.split(blocks[1].get_text()) == ["uv", "add", package]


def test_installation_exports_nested_tabs(rendered_site, installation_html):
    write_page(rendered_site, content=installation_html)
    build_docs.finish_pages("https://docs.example.com/en/v1/", "v1", False)
    exported = (rendered_site / "markdown/index.md").read_text()
    first_backend = exported.split("**HTTPX**", 1)[1].split("**requests**", 1)[0]
    for name, extra in [
        ("Adaptix", "adaptix"),
        ("Pydantic", "pydantic"),
        ("msgspec", "msgspec"),
    ]:
        assert first_backend.index(f"**{name}**") < first_backend.index(
            f"unihttp[httpx,{extra}]"
        )
    assert "unihttp[pydantic]" in exported  # Inactive urllib + Pydantic tab.


def navigation_paths(items):
    for item in items:
        if isinstance(item, str):
            yield item
        else:
            for value in item.values():
                if isinstance(value, list):
                    yield from navigation_paths(value)
                else:
                    yield value


@pytest.mark.parametrize(
    "page",
    sorted((build_docs.ROOT / "site").rglob("*.md")),
    ids=lambda page: page.relative_to(build_docs.ROOT / "site").as_posix(),
)
def test_rendered_examples_are_clean(page):
    import re
    import markdown

    html = markdown.markdown(
        page.read_text().split("---", 2)[2],
        extensions=[
            "attr_list",
            "md_in_html",
            "pymdownx.superfences",
            "pymdownx.tabbed",
            "pymdownx.snippets",
        ],
        extension_configs={
            "pymdownx.tabbed": {"alternate_style": True},
            "pymdownx.snippets": {
                "base_path": [str(build_docs.ROOT)],
                "check_paths": True,
                "dedent_subsections": True,
            },
        },
    )
    soup = BeautifulSoup(html, "html.parser")
    for code in soup.select(".highlight pre > code"):
        text = code.get_text()
        assert not re.search(r"\n(?:[ \t]*\n){3,}", text), page
        assert not re.search(r"#\s*(?:noqa\b|type:\s*ignore\b|pyright:|ruff:)", text), (
            page
        )
        if page == build_docs.ROOT / "site/index.md":
            assert "user_id: Path[int]\n\n\nclass UserClient" in text
        if page.relative_to(build_docs.ROOT / "site").as_posix() in {
            "guides/middleware.md",
            "guides/responses.md",
            "guides/errors.md",
            "guides/streaming.md",
            "recipes/retries.md",
        }:
            assert not text.startswith(" "), (
                "Guide snippets must not inherit function indentation"
            )
            assert "MockTransport" not in text
            assert "events.append" not in text


def test_middleware_snippet_ranges_match_complete_definitions():
    import ast
    import re

    root = build_docs.ROOT
    page = (root / "site/guides/middleware.md").read_text()
    snippets = re.findall(r'--8<-- "(examples/middleware_\w+\.py):(\d+):(\d+)"', page)
    assert len(snippets) == 4
    for name, start, end in snippets:
        source = (root / name).read_text()
        tree = ast.parse(source)
        definition = next(node for node in tree.body if node.lineno == int(start))
        assert isinstance(definition, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        assert definition.end_lineno == int(end), "Update the snippet range with the example"
        snippet = "\n".join(source.splitlines()[int(start) - 1:int(end)])
        assert ast.dump(ast.parse(snippet).body[0]) == ast.dump(definition)


def test_navigation_covers_each_listed_page_once():
    import tomllib
    from collections import Counter

    config = tomllib.loads((build_docs.ROOT / "zensical.toml").read_text())["project"]
    assert [next(iter(section)) for section in config["nav"]] == [
        "Getting started",
        "User guide",
        "API reference",
        "Coding agent skills",
        "Contributing",
    ]
    paths = list(navigation_paths(config["nav"]))
    assert all(count == 1 for count in Counter(paths).values())
    root = build_docs.ROOT / config["docs_dir"]
    # Keep the old release URL available without a navigation entry.
    unlisted = {"project/releases.md"}
    assert set(paths).isdisjoint(unlisted)
    assert set(paths) | unlisted == {
        path.relative_to(root).as_posix() for path in root.rglob("*.md")
    }
    assert config["nav"][-2:] == [
        {"Coding agent skills": "project/agent-skills.md"},
        {"Contributing": "project/documentation.md"},
    ]
    assert "navigation.indexes" in config["theme"]["features"]
    assert "navigation.expand" not in config["theme"]["features"]
    guide = next(item["User guide"] for item in config["nav"] if "User guide" in item)
    assert {"Serialization": "guides/serialization.md"} in guide
    redirects = config["plugins"]["redirects"]["redirect_maps"]
    assert redirects == {
        f"integrations/{backend}.md": "guides/serialization.md"
        for backend in ("adaptix", "pydantic", "msgspec")
    }
    assert all(not (root / source).exists() for source in redirects)


def test_api_extraction_supports_original_namespace_package(caplog):
    from griffe import GriffeLoader, load_extensions

    root = build_docs.ROOT
    assert not (root / "src/unihttp/serializers/__init__.py").exists()
    source = root / "src/unihttp/clients/base.py"
    original = source.read_bytes()
    loader = GriffeLoader(
        search_paths=[root / "src"],
        extensions=load_extensions(str(root / "scripts/docs_griffe.py") + ":UnihttpDocsExtension"),
        docstring_parser="google",
    )
    package = loader.load("unihttp")
    loader.resolve_aliases()
    for backend, prefix in [("adaptix", "Adaptix"), ("pydantic", "Pydantic"), ("msgspec", "Msgspec")]:
        for suffix, method in [("Dumper", "dump"), ("Loader", "load")]:
            obj = package[f"serializers.{backend}.serialize.{prefix}{suffix}"]
            assert method in obj.members
    hook = package["clients.base.BaseClient.handle_error"]
    assert hook.docstring.parsed
    assert "Confusing indentation" not in caplog.text
    assert source.read_bytes() == original
    assert not (root / "src/unihttp/serializers/__init__.py").exists()


@pytest.mark.parametrize(
    "section,index",
    [("User guide", "guides/index.md"), ("API reference", "reference/index.md")],
)
def test_section_indexes_link_to_every_child(section, index):
    import re
    import tomllib

    config = tomllib.loads((build_docs.ROOT / "zensical.toml").read_text())["project"]
    children = next(item[section] for item in config["nav"] if section in item)
    root = build_docs.ROOT / config["docs_dir"]
    page = root / index
    targets = {
        (page.parent / link.split("#")[0]).resolve()
        for link in re.findall(r"\]\(([^)]+)\)", page.read_text())
    }
    assert {
        (root / path).resolve() for path in navigation_paths(children) if path != index
    } <= targets
