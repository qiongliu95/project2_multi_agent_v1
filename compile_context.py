from __future__ import annotations

import argparse
from pathlib import Path

from core.context_compiler import compile_human_context_file, save_compiled_context


PROJECT_ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile a human-maintained context Markdown file to Context Package V2."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Human-maintained context Markdown file.",
    )
    parser.add_argument(
        "--output",
        help="Output Context Package V2 JSON path. Defaults to outputs/compiled_context/{context_id}.json.",
    )
    args = parser.parse_args()

    package = compile_human_context_file(args.input)
    output_path = args.output
    if not output_path:
        output_path = str(
            PROJECT_ROOT
            / "outputs"
            / "compiled_context"
            / f"{package['context_id']}.json"
        )

    saved_path = save_compiled_context(package, output_path)
    structured_content = package.get("structured_content", {})

    print(f"compiled_context: {saved_path}")
    print(f"context_id: {package.get('context_id')}")
    print("section_counts:")
    for section, entries in structured_content.items():
        print(f"  - {section}: {len(entries) if isinstance(entries, list) else 0}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
