"""
Convert your fine-tuned Whisper (HuggingFace) to CTranslate2 + int8_float16 quantization.
Output goes to a NEW folder so the original models/whisper-3-turbo-finetuned stays unchanged.

Run from project root:
  pip install ctranslate2 transformers
  python scripts/convert_whisper_to_ct2.py
"""

import os
import sys
from pathlib import Path

# Project root (parent of scripts/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)

INPUT_DIR = PROJECT_ROOT / "models" / "whisper-3-turbo-finetuned"
OUTPUT_DIR = PROJECT_ROOT / "models" / "whisper-3-turbo-finetuned-ct2"
QUANTIZATION = "int8_float16"
COPY_FILES = ["tokenizer.json", "preprocessor_config.json", "vocab.json", "merges.txt"]


def main():
    if not INPUT_DIR.is_dir():
        print(f"ERROR: Input model not found: {INPUT_DIR}")
        sys.exit(1)

    if OUTPUT_DIR.exists():
        print(f"ERROR: Output folder already exists: {OUTPUT_DIR}")
        print("Remove it or choose another output path if you want to re-convert.")
        sys.exit(1)

    try:
        from ctranslate2.converters import TransformersConverter
    except ImportError:
        print("ERROR: ctranslate2 not installed. Run:")
        print("  pip install ctranslate2 transformers")
        sys.exit(1)

    # Only copy files that exist in the source
    existing_copy = [f for f in COPY_FILES if (INPUT_DIR / f).is_file()]
    if not existing_copy:
        existing_copy = ["tokenizer.json", "preprocessor_config.json"]

    print(f"Input:  {INPUT_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Quantization: {QUANTIZATION}")
    print(f"Copy files: {existing_copy}")
    print("Converting (this may take a few minutes)...")

    converter = TransformersConverter(
        str(INPUT_DIR),
        copy_files=existing_copy,
        load_as_float16=True,
    )
    result = converter.convert(str(OUTPUT_DIR), quantization=QUANTIZATION, force=False)

    print(f"Done. CTranslate2 model saved to: {result}")
    print("You can use it with faster-whisper: WhisperModel(result, device='cuda', compute_type='int8_float16')")


if __name__ == "__main__":
    main()
