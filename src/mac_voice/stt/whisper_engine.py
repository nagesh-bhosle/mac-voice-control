"""Local Whisper STT wrapper. Stub-friendly on Linux and without whisper deps."""

from __future__ import annotations

import platform


class WhisperNotAvailableError(RuntimeError):
    pass


class WhisperEngine:
    def __init__(self, model: str = "base") -> None:
        self.model = model
        self._model = None
        self._backend = ""

    def is_available(self) -> bool:
        if platform.system() != "Darwin":
            return False
        try:
            import whisper  # type: ignore  # noqa: F401
            return True
        except ImportError:
            return False
        except Exception:
            return False

    def load(self) -> str:
        if platform.system() != "Darwin":
            raise WhisperNotAvailableError("Whisper STT requires macOS; running on " + platform.system())
        try:
            import whisper  # type: ignore
        except ImportError as exc:
            raise WhisperNotAvailableError(
                "openai-whisper is not installed. Run scripts/setup.sh for install hints."
            ) from exc
        self._model = whisper.load_model(self.model)
        self._backend = "openai-whisper"
        return self._backend

    def transcribe(self, audio_path: str) -> str:
        if self._model is None:
            self.load()
        assert self._model is not None
        result = self._model.transcribe(audio_path)
        text = result.get("text", "") if isinstance(result, dict) else str(result)
        return text.strip()

    def transcribe_stub(self, placeholder: str = "") -> str:
        return placeholder
