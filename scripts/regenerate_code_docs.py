#!/usr/bin/env python3
"""
Regenerate Architectures/Code_Documentation/*.md from current engine code.
Each doc contains exact code from all Python files in the given source dir.
"""

from pathlib import Path


def collect_py_files(src_root: Path, recursive: bool = False) -> list[Path]:
    """Return sorted list of .py files under src_root (optionally recursive)."""
    out = []
    if recursive:
        for p in sorted(src_root.rglob("*.py")):
            if "__pycache__" in p.parts:
                continue
            out.append(p)
    else:
        for p in sorted(src_root.glob("*.py")):
            out.append(p)
    return out


def anchor(name: str) -> str:
    """Section anchor from filename (e.g. plugins/llm.py -> plugins_llm)."""
    return name.replace("\\", "_").replace("/", "_").replace(".py", "").replace(".", "_")


def build_doc(
    title: str,
    src_root: Path,
    out_path: Path,
    recursive: bool = False,
) -> None:
    """Build one Code_Documentation markdown file from src_root."""
    files = collect_py_files(src_root, recursive=recursive)
    lines = [
        f"# {title}",
        "",
        "This document contains the complete, exact code from all Python files in the source tree.",
        "",
        "## Table of Contents",
        "",
    ]
    for i, f in enumerate(files, 1):
        rel = f.relative_to(src_root)
        link_name = str(rel).replace("\\", "/")
        anc = anchor(link_name)
        lines.append(f"{i}. [{link_name}](#{anc})")
    lines.append("")
    lines.append("---")
    lines.append("")

    out_parts = ["\n".join(lines)]
    for f in files:
        rel = f.relative_to(src_root)
        link_name = str(rel).replace("\\", "/")
        try:
            body = f.read_text(encoding="utf-8")
        except Exception as e:
            body = f"# Error reading file: {e}\n"
        # Code block content = exact file content (byte-for-byte)
        out_parts.append(f"## {link_name}\n\n```python\n{body}```\n\n---\n\n")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(out_parts), encoding="utf-8")
    print(f"Wrote {out_path} ({len(files)} files)")


def main():
    base = Path(__file__).resolve().parent.parent
    docs = base / "Architectures" / "Code_Documentation"
    engines = base / "framework" / "engines"
    security = base / "framework" / "security"

    # STT
    build_doc(
        "STT Engine - Complete Code Documentation",
        engines / "stt",
        docs / "STT_ENGINE.md",
    )
    # TTS
    build_doc(
        "TTS Engine - Complete Code Documentation",
        engines / "tts",
        docs / "TTS_ENGINE.md",
    )
    # LLM
    build_doc(
        "LLM Engine - Complete Code Documentation",
        engines / "llm",
        docs / "LLM_ENGINE.md",
    )
    # Security (only .py in security/, not database_migrations)
    build_doc(
        "Security Layers - Complete Code Documentation",
        security,
        docs / "SECURITY_LAYERS.md",
    )
    # Voice Mode (recursive for plugins/)
    build_doc(
        "Voice Mode Engine - Complete Code Documentation",
        engines / "voice_mode",
        docs / "VOICE_MODE_ENGINE.md",
        recursive=True,
    )
    print("Done.")


if __name__ == "__main__":
    main()
