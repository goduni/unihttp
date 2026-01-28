# Cross-platform shell configuration
# Use PowerShell on Windows (higher precedence than shell setting)

set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

# Use sh on Unix-like systems

set shell := ["sh", "-c"]

lint:
    ruff check

static-analysis:
    mypy

test:
    pytest --cov

test-all:
    nox

check-all:
    just lint
    just static-analysis
    just test-all
