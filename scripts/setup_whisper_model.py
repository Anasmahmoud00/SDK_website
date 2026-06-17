#!/usr/bin/env python3
"""
Whisper Model Setup Helper Script

This script helps you:
1. Verify your model directory structure
2. Download missing config files from base model
3. Set up the model path in .env
"""

import sys
from pathlib import Path
from typing import List

# Project root (parent of scripts/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def check_model_directory(model_path: Path) -> tuple[bool, List[str]]:
    """Check if model directory has all required files."""
    required_files = [
        "model.safetensors",
        "config.json",
        "preprocessor_config.json",
        "vocab.json",
        "merges.txt",
    ]

    # Tokenizer can be either tokenizer.json OR tokenizer_config.json
    optional_tokenizer_files = ["tokenizer.json", "tokenizer_config.json"]

    missing_files = []
    for file in required_files:
        file_path = model_path / file
        if not file_path.exists():
            missing_files.append(file)

    # Check for tokenizer files (need at least one)
    has_tokenizer = any((model_path / f).exists() for f in optional_tokenizer_files)
    if not has_tokenizer:
        missing_files.append("tokenizer.json OR tokenizer_config.json")

    return len(missing_files) == 0, missing_files


def download_config_files(model_path: Path, base_model: str = "openai/whisper-large-v3-turbo"):
    """Download missing config files from base HuggingFace model."""
    try:
        from transformers import AutoProcessor, AutoConfig, WhisperTokenizer
    except ImportError:
        print("❌ Error: transformers library not installed.")
        print("   Install with: pip install transformers")
        return False

    print(f"\n📥 Downloading config files from {base_model}...")

    try:
        # Download processor (includes preprocessor_config.json)
        print("  - Downloading processor...")
        processor = AutoProcessor.from_pretrained(base_model)
        processor.save_pretrained(str(model_path))
        print("    ✅ Processor saved")

        # Download tokenizer files
        print("  - Downloading tokenizer...")
        tokenizer = WhisperTokenizer.from_pretrained(base_model)
        tokenizer.save_pretrained(str(model_path))
        print("    ✅ Tokenizer saved")

        # Download model config
        print("  - Downloading model config...")
        config = AutoConfig.from_pretrained(base_model)
        config.save_pretrained(str(model_path))
        print("    ✅ Model config saved")

        print("\n✅ All config files downloaded successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Error downloading config files: {e}")
        return False


def update_env_file(model_path: Path, env_file: Path, project_root: Path) -> bool:
    """Update .env file with WHISPER_MODEL_PATH."""
    # Convert to relative path if possible
    try:
        rel_path = model_path.relative_to(project_root)
        path_str = f"./{rel_path.as_posix()}"
    except ValueError:
        # Use absolute path if not under project root
        path_str = str(model_path)

    env_line = f"WHISPER_MODEL_PATH={path_str}\n"

    # Read existing .env
    env_content = ""
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            env_content = f.read()

    # Check if WHISPER_MODEL_PATH already exists
    lines = env_content.split("\n")
    updated = False
    new_lines = []

    for line in lines:
        if line.startswith("WHISPER_MODEL_PATH="):
            new_lines.append(env_line.strip())
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        # Add new line
        if new_lines and new_lines[-1]:
            new_lines.append("")
        new_lines.append(env_line.strip())

    # Write back
    try:
        with open(env_file, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines))
        print(f"\n✅ Updated {env_file} with WHISPER_MODEL_PATH={path_str}")
        return True
    except Exception as e:
        print(f"\n❌ Error updating .env file: {e}")
        return False


def main():
    """Main setup function."""
    print("=" * 70)
    print("Whisper Fine-Tuned Model Setup Helper")
    print("=" * 70)

    # Get model path from user
    if len(sys.argv) > 1:
        model_path_str = sys.argv[1]
    else:
        print("\n📁 Enter the path to your Whisper model directory:")
        print("   (Should contain model.safetensors and config files)")
        model_path_str = input("   Path: ").strip().strip('"').strip("'")

    if not model_path_str:
        print("\n❌ Error: Model path is required")
        print("\nUsage: python scripts/setup_whisper_model.py <model_path>")
        print("   Example: python scripts/setup_whisper_model.py ./models/whisper-3-turbo-finetuned")
        sys.exit(1)

    model_path = Path(model_path_str).expanduser().resolve()

    # Check if directory exists
    if not model_path.exists():
        print(f"\n❌ Error: Directory does not exist: {model_path}")
        create = input("   Create directory? (y/n): ").strip().lower()
        if create == "y":
            model_path.mkdir(parents=True, exist_ok=True)
            print(f"   ✅ Created directory: {model_path}")
        else:
            sys.exit(1)

    if not model_path.is_dir():
        print(f"\n❌ Error: Path is not a directory: {model_path}")
        sys.exit(1)

    print(f"\n📂 Checking model directory: {model_path}")
    print("-" * 70)

    # Check required files
    is_complete, missing_files = check_model_directory(model_path)

    # List all files
    all_files = list(model_path.glob("*"))
    if all_files:
        print("\n📋 Files found in directory:")
        for file in sorted(all_files):
            if file.is_file():
                size = file.stat().st_size / (1024 * 1024)  # MB
                status = (
                    "✅"
                    if file.name
                    in [
                        "model.safetensors",
                        "config.json",
                        "preprocessor_config.json",
                        "tokenizer.json",
                        "tokenizer_config.json",
                        "vocab.json",
                        "merges.txt",
                    ]
                    else "📄"
                )
                print(f"  {status} {file.name:30s} ({size:.2f} MB)")
    else:
        print("  ⚠️  Directory is empty")

    # Check for model.safetensors specifically
    safetensors_file = model_path / "model.safetensors"
    if not safetensors_file.exists():
        print("\n⚠️  WARNING: model.safetensors not found!")
        print("   Make sure you copy your fine-tuned model.safetensors file here.")

    # Report missing files
    if missing_files:
        print(f"\n⚠️  Missing {len(missing_files)} required file(s):")
        for file in missing_files:
            print(f"   - {file}")

        print("\n💡 You can download these from the base Whisper model.")
        download = input("   Download missing config files? (y/n): ").strip().lower()

        if download == "y":
            success = download_config_files(model_path)
            if success:
                # Re-check
                is_complete, missing_files = check_model_directory(model_path)

    # Final status
    print("\n" + "-" * 70)
    if is_complete:
        print("✅ Model directory is complete! All required files present.")
    else:
        print(f"⚠️  Model directory incomplete. Missing {len(missing_files)} file(s).")
        print("   You can download them later or copy from the base model.")

    # Update .env file
    print("\n📝 Updating .env file...")
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        update_env_file(model_path, env_file, PROJECT_ROOT)
    else:
        print(f"   ⚠️  .env file not found at {env_file}")
        print("   You can manually add: WHISPER_MODEL_PATH=<path>")

    # Final instructions
    print("\n" + "=" * 70)
    print("✅ Setup Complete!")
    print("=" * 70)
    print("\n📚 Next Steps:")
    print("   1. Verify your model.safetensors file is in the directory")
    print("   2. If missing config files, download them (see guide)")
    print("   3. Test your model:")
    print("\n      from narrative_ai.engines.stt import STTEngine")
    print("      engine = STTEngine()")
    print("      await engine.initialize()")
    print("      result = await engine.transcribe(audio_bytes, sample_rate=16000)")
    print("\n📖 See WHISPER_MODEL_SETUP_GUIDE.md for detailed instructions")


if __name__ == "__main__":
    main()
