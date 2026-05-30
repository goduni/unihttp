from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined


class TemplateRenderer:
    """Handle template rendering with Jinja2."""

    BASE_TEMPLATE_PATH = Path(__file__).parent / "template.j2"

    @classmethod
    def load_template(cls, template_path: str | Path = BASE_TEMPLATE_PATH) -> str:
        """Load a custom template from file."""
        return Path(template_path).read_text(encoding="utf-8")

    @classmethod
    def get_env(cls, template_dir: str | None = None) -> Environment:
        """Get Jinja2 environment with optional custom template directory."""
        env = Environment(  # noqa: S701
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )
        if template_dir:
            loader = FileSystemLoader(template_dir)
            env.loader = loader
        return env
