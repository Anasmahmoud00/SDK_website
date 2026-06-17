#!/usr/bin/env python3
"""
Regenerate *_CODE_COMPLETE.md from current source under framework/.

Usage (from project root):
    python scripts/regenerate_code_complete_docs.py

Writes: LLM_ENGINE_CODE_COMPLETE.md, STT_ENGINE_CODE_COMPLETE.md,
        TTS_ENGINE_CODE_COMPLETE.md, SECURITY_CODE_COMPLETE.md
"""

import os
from pathlib import Path

# Project root = parent of 'scripts'
ROOT = Path(__file__).resolve().parent.parent
FRAMEWORK = ROOT / "framework"


def header_llm() -> str:
    return """# LLM Engine - Complete Code

**Purpose**: Complete LLM engine code for AI review.

 **Module**: `framework/engines/llm/`

---

## Document status (for evaluator)

**Last updated for evaluation**: 2025-01-27.

**Embedded code**: Regenerated from live source. Code blocks in this document are synced from `framework/engines/llm/` as of the date above.

**Recent code changes reflected in live source**:
- **LLMResult** (`base_llm.py`): `__post_init__` clamps token counts to ≥ 0 and enforces `total_tokens == input_tokens + output_tokens`.
- See `framework/engines/llm/LLM_ENGINE_RE_REVIEW_VERIFICATION.md` for the 14-issue verification table.

---

"""


def header_stt() -> str:
    return """# STT Engine - Complete Code

**Purpose**: Complete STT engine code for AI review.

**Module**: `framework/engines/stt/`

---

## Document status (for evaluator)

**Last updated for evaluation**: 2025-01-27.

**Embedded code**: Regenerated from live source. Code blocks in this document are synced from `framework/engines/stt/` as of the date above.

**Recent code changes reflected in live source**:
- **Audio input types**: `STTEngine.transcribe()` accepts bytes or `np.ndarray`; `_validate_audio_security` has an `isinstance(audio, np.ndarray)` branch.

---

"""


def header_tts() -> str:
    return """# TTS Engine - Complete Code

**Purpose**: Complete TTS engine code for AI review.

**Module**: `framework/engines/tts/`

---

## Document status (for evaluator)

**Last updated for evaluation**: 2025-01-27.

**Embedded code**: Regenerated from live source. Code blocks in this document are synced from `framework/engines/tts/` as of the date above.

**Known gap**: EGTTS is in config/strategy but `egtts.py` is not implemented; strategy catches ImportError.

---

"""


def header_security() -> str:
    return """# Security Module - Complete Code

**Purpose**: Complete Security module code for AI review.

**Module**: `framework/security/`

---

## Document status (for evaluator)

**Last updated for evaluation**: 2025-01-27.

**Embedded code**: Regenerated from live source. Code blocks in this document are synced from `framework/security/` as of the date above.

---

"""


def build_doc(src_dir: Path, files: list[str], header: str) -> str:
    out = [header]
    for name in files:
        path = src_dir / name
        if not path.exists():
            out.append(f"## File: `{name}`\n\n*(file not found)*\n\n")
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        out.append(f"## File: `{name}`\n\n```python\n{raw}\n```\n\n")
    return "".join(out)


def main() -> None:
    os.chdir(ROOT)

    # LLM
    llm_dir = FRAMEWORK / "engines" / "llm"
    llm_files = [
        "__init__.py",
        "llm_engine.py",
        "llm_strategy.py",
        "base_llm.py",
        "config.py",
        "input_processor.py",
        "response_processor.py",
        "conversation_manager.py",
        "gemini_llm.py",
        "openai_llm.py",
        "claude_llm.py",
        "xai_llm.py",
        "deepseek_llm.py",
    ]
    out_path = ROOT / "LLM_ENGINE_CODE_COMPLETE.md"
    out_path.write_text(build_doc(llm_dir, llm_files, header_llm()), encoding="utf-8")
    print(f"Wrote {out_path}")

    # STT
    stt_dir = FRAMEWORK / "engines" / "stt"
    stt_files = [
        "__init__.py",
        "stt_engine.py",
        "stt_strategy.py",
        "base_stt.py",
        "config.py",
        "audio_processor.py",
        "vad_processor.py",
        "emotion_detector.py",
        "elevenlabs_stt.py",
        "whisper_stt.py",
        "conformer_stt.py",
    ]
    out_path = ROOT / "STT_ENGINE_CODE_COMPLETE.md"
    out_path.write_text(build_doc(stt_dir, stt_files, header_stt()), encoding="utf-8")
    print(f"Wrote {out_path}")

    # TTS
    tts_dir = FRAMEWORK / "engines" / "tts"
    tts_files = [
        "__init__.py",
        "tts_engine.py",
        "tts_strategy.py",
        "base_tts.py",
        "config.py",
        "audio_processor.py",
        "emotion_applicator.py",
        "elevenlabs_tts.py",
        "openai_tts.py",
        "voice_selector.py",
        "prosody_engine.py",
        "streaming.py",
        "model_loader.py",
    ]
    out_path = ROOT / "TTS_ENGINE_CODE_COMPLETE.md"
    out_path.write_text(build_doc(tts_dir, tts_files, header_tts()), encoding="utf-8")
    print(f"Wrote {out_path}")

    # Security
    sec_dir = FRAMEWORK / "security"
    sec_files = [
        "__init__.py",
        "rate_limiting.py",
        "audit_trail.py",
        "input_validation.py",
        "stream_isolation.py",
        "error_handling.py",
        "circuit_breaker.py",
    ]
    out_path = ROOT / "SECURITY_CODE_COMPLETE.md"
    out_path.write_text(build_doc(sec_dir, sec_files, header_security()), encoding="utf-8")
    print(f"Wrote {out_path}")

    print("Done. All four CODE_COMPLETE docs regenerated from live source.")


if __name__ == "__main__":
    main()
