# Narrative AI SDK (v0.4.0)

**What's new in 0.4.0:** lazy engine imports (PEP 562); `configure` / `reset` for bring-your-own models; `[test]` extra for the SDK suite; `httpx` in core deps; README install and BYO docs refresh.

A unified Python SDK for AI engines — **LLM, STT, TTS, RAG, OCR, VLM, Web Intelligence,
Input Processing, and Voice Mode** — behind one tiny, consistent surface:

```python
import narrative_ai as nai
```

Engines are resolved **lazily** (PEP 562). Simply doing `import narrative_ai` is cheap
and does **not** require every heavy optional dependency (torch, openai, sentence-transformers,
livekit, …) to be installed. Each engine's extra dependencies are imported only the first time
you touch that engine, and a missing optional dependency raises a clear, actionable error
telling you exactly which extra to install.

---

## Installation

```bash
# Core only — import works, install engine extras as needed
pip install narrative-ai-framework

# Install just the engine(s) you need
pip install "narrative-ai-framework[llm]"     # OpenAI / Gemini / Anthropic / xAI / DeepSeek
pip install "narrative-ai-framework[rag]"     # embeddings + vector store
pip install "narrative-ai-framework[stt]"     # speech-to-text (Whisper, ElevenLabs, …)
pip install "narrative-ai-framework[tts]"     # text-to-speech
pip install "narrative-ai-framework[ocr]"     # document OCR / restoration
pip install "narrative-ai-framework[vlm]"     # vision-language (image captioning / Q&A)
pip install "narrative-ai-framework[web]"     # web search
pip install "narrative-ai-framework[voice]"   # LiveKit real-time voice agent

# Everything
pip install "narrative-ai-framework[all]"
```

Available extras: `llm`, `stt`, `tts`, `rag`, `ocr`, `vlm`, `web`, `voice`, `db`, `security`,
`api`, `test`, `dev`, `all`. Requires **Python 3.10+**.

There are three distinct install levels:

| Goal | Command | What you get |
| ---- | ------- | ------------ |
| Just `import narrative_ai` | `pip install narrative-ai-framework` | Lazy SDK surface; accessing an engine without its extra raises a friendly `pip install narrative-ai-framework[...]` error |
| Run the SDK test suite | `pip install -e ".[test]"` | pytest + light scientific/security deps the suite needs to collect & pass (no torch/qdrant/openai) |
| Make real (live) engine calls | `pip install "narrative-ai-framework[<engine>]"` or `[all]` + API keys | Heavy provider deps + credentials via `configure(...)` / `set_api_key(...)` |

---

## Quickstart

```python
import asyncio
import narrative_ai as nai

async def main():
    # Bring your own model + key (no config files to edit)
    nai.llm.configure(provider="openai", model="gpt-4o", api_key="sk-...")

    result = await nai.llm.generate("Write a one-line haiku about the sea.")
    print(result.text)

asyncio.run(main())
```

> **Sync vs async:** the engine *call* functions (`generate`, `speech_to_text`,
> `text_to_speech`, `remember`, `recall`, `caption`, …) are **coroutines** — `await` them
> inside an `async` function and drive them with `asyncio.run(...)`.
> Configuration helpers (`configure`, `reset`, `set_api_key`, `chunk`, …) are plain
> synchronous functions.

---

## Bring your own model (BYO)

`nai.llm.configure(provider, model, api_key, base_url)` is the first-class entry point.
It rebuilds the default engine so the **next** `generate()` call uses your choices —
no YAML, no env files required.

```python
import narrative_ai as nai

# (a) OpenAI
nai.llm.configure(provider="openai", model="gpt-4o", api_key="sk-...")

# (b) Any OpenAI-compatible / local endpoint (vLLM, LiteLLM, OpenRouter, LM Studio …)
nai.llm.configure(
    provider="openai",
    model="llama-3.1-70b",
    api_key="local-or-proxy-key",
    base_url="http://localhost:8000/v1",
)

# (c) Local Ollama (no key required)
nai.llm.configure(provider="ollama", model="llama3.1",
                  base_url="http://localhost:11434")
```

**Verify which provider/model is active:**

```python
engine = nai.llm.configure(provider="openai", model="gpt-4o", api_key="sk-...")
print("primary provider:", engine.config.primary_provider)
sub = engine.config.get_provider_config(engine.config.primary_provider)
print("active model:", sub.default_model)
print("base_url:", sub.base_url)
```

Valid LLM providers: `openai`, `gemini`, `anthropic`, `xai`, `deepseek`, `ollama`.
An unknown provider raises `ValueError`. `nai.llm.reset()` drops the cached engine so the
next call rebuilds from the current config/env.

The same `configure(...)` / `reset()` pattern is available on the other key engines:

| Engine | `configure(...)` signature |
| :--- | :--- |
| `nai.llm` | `configure(provider, model, api_key, base_url, *, temperature, max_tokens, make_primary=True)` |
| `nai.rag` | `configure(provider, api_key, embedding_model)` |
| `nai.stt` | `configure(provider, api_key)` |
| `nai.tts` | `configure(provider, api_key)` |
| `nai.vlm` | `configure(provider, api_key)` |
| `nai.web_intel` | `configure(provider, api_key)` |

---

## Engine reference

All examples assume `import narrative_ai as nai` inside an `async` function.

### `nai.llm` — Large Language Models

| Function | Signature (key args) | Returns |
| :--- | :--- | :--- |
| `generate` | `await generate(prompt, *, system_prompt, messages, temperature=0.7, max_tokens, provider)` | `LLMResult` (`.text`, `.usage`, …) |
| `generate_stream` | `async for token in generate_stream(prompt, ...)` | `AsyncIterator[str]` |
| `chat` | `chat(session_id=None)` | `ConversationManager` |
| `estimate_tokens` | `estimate_tokens(text, provider_hint="openai")` | `int` |
| `calculate_cost` | `calculate_cost(result)` | `float` (USD) |
| `check_security` | `check_security(text)` | `str` (sanitized) |
| `configure` / `reset` | BYO model (see above) | `LLMEngine` / `None` |
| `LLMClient` | `LLMClient(user_id, tenant_id, provider, api_key, ...)` | session client |

```python
res = await nai.llm.generate("Hello", temperature=0.2)
print(res.text)

async for token in nai.llm.generate_stream("Tell me a joke"):
    print(token, end="", flush=True)
```

### `nai.rag` — Retrieval-Augmented Memory

| Function | Signature (key args) | Returns |
| :--- | :--- | :--- |
| `remember` | `await remember(document, doc_id=None, user_id=None, ...)` | `IndexingResult` (`.doc_id`, `.chunks_indexed`, `.success`) |
| `recall` | `await recall(query, top_k=None, return_context=True, ...)` | `RichContext` (`.formatted_text`) |
| `search` | `await search(query, ...)` | `List[RetrievalResult]` |
| `forget` | `await forget(doc_id, user_id=None)` | `bool` |
| `get_stats` | `await get_stats()` | `dict` |
| `chunk` | `chunk(text, chunk_size=200, overlap=30, ...)` | `List[TextChunk]` (offline, no deps) |
| `detect_lang` / `normalize` | `detect_lang(text)` / `normalize(text)` | `str` (offline) |
| `configure` / `reset` | embedding BYO | `None` |
| `RAGClient` | `RAGClient(user_id, top_k=5, ...)` | session client |

```python
doc = await nai.input_processor.process("notes.pdf")   # -> StructuredDocument
result = await nai.rag.remember(document=doc, doc_id="notes-1")
print(result.success, result.chunks_indexed)

ctx = await nai.rag.recall("What did I write about the sea?")
print(ctx.formatted_text)
```

### `nai.stt` — Speech-to-Text

| Function | Signature (key args) | Returns |
| :--- | :--- | :--- |
| `speech_to_text` | `await speech_to_text(audio, sample_rate=16000, language=None, extract_emotion=True, use_vad=True)` | `TranscriptionResult` (`.text`) |
| `stt_streaming` | `async for r in stt_streaming(audio_stream, ...)` | `AsyncIterator[TranscriptionResult]` |
| `detect_emotion` | `await detect_emotion(audio, sample_rate=16000)` | `EmotionResult` |
| `configure` / `reset` | provider/key BYO | `None` |
| `STTClient` | `STTClient(user_id, language, provider, api_key, ...)` | session client |

```python
res = await nai.stt.speech_to_text(audio_bytes, language="en")
print(res.text)
```

### `nai.tts` — Text-to-Speech

| Function | Signature (key args) | Returns |
| :--- | :--- | :--- |
| `text_to_speech` | `await text_to_speech(text, voice_id=None, emotion=None, language=None, output_format="mp3_44100_128")` | `TTSResult` |
| `tts_streaming` | `async for chunk in tts_streaming(text, ...)` | `AsyncIterator[StreamingChunk]` |
| `get_voices` | `await get_voices()` | `List[VoiceInfo]` |
| `configure` / `reset` | provider/key BYO | `None` |
| `TTSClient` | `TTSClient(user_id, voice_id, provider, api_key, ...)` | session client |

```python
audio = await nai.tts.text_to_speech("Hello there", language="en")
```

### `nai.vlm` — Vision-Language

| Function | Signature (key args) | Returns |
| :--- | :--- | :--- |
| `caption` | `await caption(image, prompt="Describe this image in detail.")` | `CaptionResult` (`.caption`) |
| `ask` | `await ask(image, question)` | `str` |
| `configure` / `reset` | provider/key BYO | `None` |
| `VLMClient` | `VLMClient(user_id, provider="openai", api_key=None)` | session client |

```python
res = await nai.vlm.caption("photo.jpg")
print(res.caption)
answer = await nai.vlm.ask("photo.jpg", "How many people are in this image?")
```

### `nai.ocr` — Document OCR & Restoration

| Function | Signature (key args) | Returns |
| :--- | :--- | :--- |
| `extract_text` | `await extract_text(image, shadow_removal=False, dewarping=False, ...)` | `str` |
| `ocr` | `await ocr(image, ocr=True, ...)` | `dict` (`text`, `processed_image`, `timings`) |
| `enhance` / `dewarp` / `deshadow` / `binarize` / `restoration` | `await <fn>(image, ...)` | `bytes` |
| `set_service_url` / `set_ocr_provider` | remote endpoint config | `None` |
| `OCRClient` | `OCRClient(user_id, shadow_removal, dewarping, ...)` | session client |

```python
text = await nai.ocr.extract_text("scan.png", dewarping=True)
```

### `nai.input_processor` — Multimodal Ingestion

| Function | Signature (key args) | Returns |
| :--- | :--- | :--- |
| `process` | `await process(source, enable_image_processing=None, enable_audio_processing=None)` | `StructuredDocument` |
| `process_batch` | `await process_batch(sources, batch_concurrency=None)` | `List[StructuredDocument]` |
| `process_audio` | `await process_audio(source, language=None)` | `StructuredDocument` |
| `process_document` | `await process_document(file_path, enable_image_processing=False)` | `StructuredDocument` |
| `InputClient` | `InputClient(user_id, enable_image_processing, ...)` | session client |

```python
doc = await nai.input_processor.process("file.pdf")
print(doc.text)
```

### `nai.web_intel` — Web Search

| Function | Signature (key args) | Returns |
| :--- | :--- | :--- |
| `search` | `await search(query, max_results=None, freshness=None, timeout_ms=None)` | `WebSearchResponse` (`.query`, `.sources`) |
| `configure` / `reset` | provider/key BYO | `None` |
| `WebIntelClient` | `WebIntelClient(max_results, freshness, api_key, ...)` | session client |

```python
nai.web_intel.configure(provider="tavily", api_key="tvly-...")
resp = await nai.web_intel.search("latest AI news", max_results=5)
for s in resp.sources:
    print(s)
```

### `nai.voice_mode` — Real-time Voice Agent (LiveKit)

| Function | Signature | Returns |
| :--- | :--- | :--- |
| `set_livekit_config` | `set_livekit_config(url, api_key, api_secret)` | `None` |
| `set_agent_name` | `set_agent_name(name)` | `None` |
| `start_agent` | `start_agent()` (blocking worker loop) | `None` |
| `VoiceClient` | `VoiceClient().start()` | — |

```python
nai.voice_mode.set_livekit_config(url="wss://...", api_key="...", api_secret="...")
nai.voice_mode.set_agent_name("Narrator")
nai.voice_mode.start_agent()   # blocks, registers worker with LiveKit
```

---

## Offline / no-key demo

Some helpers run with **no API keys and no heavy ML deps** — handy for a quick smoke test:

```python
import narrative_ai as nai

print(nai.__version__)                       # 0.4.0
print(nai.rag.detect_lang("Hello world"))    # 'en'
print(nai.rag.detect_lang("مرحبا بالعالم"))  # 'ar'
chunks = nai.rag.chunk("Sentence one. Sentence two. Sentence three.", chunk_size=20)
print(len(chunks), "chunks")
```

Anything that calls a provider (LLM/STT/TTS/VLM/Web) needs the matching extra installed
**and** credentials configured via `configure(...)` or `set_api_key(...)`.

### Run the full demo script

A single, self-contained, **auto-detecting** demo lives at
[`examples/sdk_demo.py`](examples/sdk_demo.py). It prints clear section headers and
`✓ / ✗` results and is safe to run anywhere — it **always exits 0**, even with no API
keys, no live backend, and no heavy ML deps installed.

```powershell
# Windows / PowerShell — use the project venv interpreter by full path
.\.venv\Scripts\python.exe examples\sdk_demo.py
```

```bash
# macOS / Linux
.venv/bin/python examples/sdk_demo.py
```

What it proves, in order:

1. **Cheap import** — `import narrative_ai` + `__version__`, no heavy deps needed.
2. **Graceful degradation** — every engine facade imports via lazy loading; heavy deps
   (torch / qdrant / sentence-transformers / livekit) are reported absent; and a real
   generation with no usable provider is **caught cleanly** instead of crashing.
3. **Offline helpers** (no network, no keys) — language detection (EN + AR),
   Arabic-aware chunking, query normalization, keyword extraction, token estimation.
4. **Bring-your-own-model** — `configure(...)` switches provider/model/`base_url` for both
   local Ollama and any OpenAI-compatible endpoint, printing the active config.
5. **Auto-detected LIVE generation** — it picks the richest available backend in this
   order: a real `OPENAI_API_KEY` → a local Ollama server on `http://localhost:11434` →
   an `OLLAMA_CLOUD_API_KEY`. If one is found it makes a **real** model call and prints the
   response; otherwise it prints the exact one-liners to enable each and continues.

To light up the live LLM section, set **one** of:

```powershell
$env:OPENAI_API_KEY = "sk-..."                      # then: pip install openai
# or run a local model:  ollama pull llama3.1; ollama serve   # http://localhost:11434
# or set OLLAMA_CLOUD_API_KEY (in your environment or .env) for managed Ollama Cloud
```

---

## Development & testing

The SDK test suite mocks every heavy provider/network layer, but the engine `api`
modules it imports directly still eagerly pull a handful of **lightweight** deps
(`numpy`, `psutil`, `Pillow`) plus the shared security stack (`SQLAlchemy`,
`cryptography`, `PyJWT`, `bcrypt`). The `test` extra carries exactly these — no
`torch`/`qdrant-client`/`openai`/`livekit` required.

From a fresh virtual environment:

```bash
python -m venv .venv
# Windows (PowerShell):  .\.venv\Scripts\Activate.ps1
# macOS/Linux:           source .venv/bin/activate

pip install -U pip
pip install -e ".[test]"     # (or ".[dev]" to also get mypy + ruff)

# Run the SDK test suite (must be green on a clean install):
python -m pytest tests/unit/test_engines_sdk/ tests/integration/test_sdk_root.py test_sdk_functional_integration.py -q
```

> Tip: verify in an *isolated* venv. If you have a conda `base` env active it can
> leak `numpy`/`psutil`/`Pillow` and hide packaging gaps — confirm isolation with
> `python -c "import numpy"` failing right after `python -m venv`, or call the
> venv interpreter by full path (e.g. `.\.venv\Scripts\python.exe -m pytest ...`).

---

## License

MIT License.
