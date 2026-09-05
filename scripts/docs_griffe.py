"""Adapt API extraction to unihttp's source layout without changing the package."""

from pathlib import Path
from typing import Any

from griffe import Extension, Function, GriffeLoader, Module, visit


class UnihttpDocsExtension(Extension):
    def on_module(self, *, mod: Module, loader: GriffeLoader, **kwargs: Any) -> None:
        if mod.path != "unihttp" or "serializers" in mod.members:
            return
        if not isinstance(mod.filepath, Path):
            return
        directory = mod.filepath.parent / "serializers"
        namespace = Module("serializers", filepath=[directory], parent=mod)
        mod.set_member("serializers", namespace)
        for package in sorted(directory.iterdir()):
            if not (package / "__init__.py").is_file():
                continue
            self._visit_module(package / "__init__.py", package.name, namespace, loader)
            child = namespace.members[package.name]
            for source in sorted(package.glob("*.py")):
                if source.name != "__init__.py":
                    self._visit_module(source, source.stem, child, loader)

    @staticmethod
    def _visit_module(
        source: Path, name: str, parent: Module, loader: GriffeLoader
    ) -> None:
        module = visit(
            name,
            source,
            source.read_text(encoding="utf-8"),
            parent=parent,
            docstring_parser=loader.docstring_parser,
            docstring_options=loader.docstring_options,
            lines_collection=loader.lines_collection,
            modules_collection=loader.modules_collection,
        )
        parent.set_member(name, module)

    def on_function(self, *, func: Function, loader: GriffeLoader, **kwargs: Any) -> None:
        if func.path == "unihttp.clients.base.BaseClient.handle_error" and func.docstring:
            # Normalize only the extracted text of this legacy docstring.
            func.docstring.value = func.docstring.value.replace(
                "\n     response:", "\n    response:"
            ).replace("\n     method:", "\n    method:")
