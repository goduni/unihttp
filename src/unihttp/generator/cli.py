from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

from .configs import ClientType, GenerationConfig, SerializerType
from .generator import SDKGenerator


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a unihttp SDK from an OpenAPI 3.1 spec.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m unihttp.generator sample_openapi.yaml -o sdk.py
  python -m unihttp.generator openapi.json -o sdk.py --client httpx
  python -m unihttp.generator api.yaml -o sdk.py --serializer pydantic
        """,
    )

    parser.add_argument(
        "spec",
        help="Path to the OpenAPI YAML or JSON file",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file path (default: stdout)",
        default=None,
    )
    parser.add_argument(
        "--client",
        help="Client type (httpx, aiohttp, requests, niquests, zapros)",
        choices=[ct.value for ct in ClientType],
        default="httpx",
    )
    parser.add_argument(
        "--serializer",
        help="Serializer type (adaptix, pydantic, msgspec)",
        choices=[st.value for st in SerializerType],
        default="adaptix",
    )
    parser.add_argument(
        "--template",
        help="Custom Jinja2 template path",
        default=None,
    )
    parser.add_argument(
        "--package-name",
        help="Output package name",
        default=None,
    )
    parser.add_argument(
        "--base-url",
        help="Default base URL for the generated client",
        default=None,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show generated code without writing to file",
    )

    args = parser.parse_args()

    # Validate spec file exists
    spec_path = Path(args.spec)
    if not spec_path.exists():
        print(f"Error: Spec file not found: {args.spec}", file=sys.stderr)
        sys.exit(1)

    # Parse spec
    if args.verbose:
        print(f"Loading spec from: {args.spec}")

    # Create config
    client_type = ClientType(args.client)
    serializer_type = SerializerType(args.serializer)

    config = GenerationConfig(
        client_type=client_type,
        serializer_type=serializer_type,
        custom_template_path=args.template,
        output_package_name=args.package_name,
        base_url=args.base_url,
    )

    try:
        generator = SDKGenerator.from_file(args.spec, config)
    except Exception as e:
        print(f"Error parsing spec: {e}", file=sys.stderr)
        sys.exit(1)

    # Generate
    if args.verbose:
        print(
            f"Generating SDK with {args.client} client and {args.serializer} serializer"
        )

    try:
        code = generator.generate()
    except Exception as e:
        print(f"Error generating SDK: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

    # Output
    if args.dry_run:
        print("=== Generated Code (dry run) ===")
        print(code)
        sys.exit(0)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(code, encoding="utf-8")
        if args.verbose:
            print(f"SDK written to: {output_path}")
    else:
        sys.stdout.write(code + "\n")

    if args.verbose:
        print("Generation complete!")


if __name__ == "__main__":
    main()
