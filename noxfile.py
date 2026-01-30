import nox
from nox_uv import session

nox.options.default_venv_backend = "uv"
nox.options.reuse_existing_virtualenvs = True


@session(
    python=["3.12", "3.13", "3.14"],
    uv_groups=["dev"]
)
def test(s: nox.Session) -> None:
    s.run("pytest", "--cov", "src")
