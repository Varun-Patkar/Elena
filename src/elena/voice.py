import os
from pathlib import Path

from elena.runtime import default_data_dir


def warm_voice_models(data_dir: Path | None = None) -> None:
    model_dir = data_dir or default_data_dir() / "models"
    whisper_dir = model_dir / "whisper"
    kokoro_dir = model_dir / "kokoro"
    whisper_dir.mkdir(parents=True, exist_ok=True)
    kokoro_dir.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("HF_HOME", str(kokoro_dir))

    print("Downloading and validating faster-whisper small.en...")
    from faster_whisper import WhisperModel

    whisper = WhisperModel(
        "small.en",
        device="cpu",
        compute_type="int8",
        download_root=str(whisper_dir),
    )
    del whisper

    print("Downloading and validating Kokoro with the af_heart voice...")
    from kokoro import KPipeline

    pipeline = KPipeline(lang_code="a")
    next(pipeline("Elena voice setup complete.", voice="af_heart", speed=1))
    print(f"Voice models are ready under {model_dir}")


def main() -> None:
    warm_voice_models()


if __name__ == "__main__":
    main()