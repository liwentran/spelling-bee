"""Text-to-speech as an MP3 clip, so the TV can play speech through an <audio> element.

Native speechSynthesis on Safari speaks through the system voice, which AirPlay mirroring
doesn't carry to the TV; page audio (like the sound effects) does.
"""
import urllib.parse
import urllib.request
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

router = APIRouter(prefix="/api/tts", tags=["tts"])

GOOGLE_TTS = "https://translate.google.com/translate_tts"
CHUNK_LIMIT = 190  # Google rejects requests over ~200 characters


def _chunks(text: str) -> list[str]:
    """Split on word boundaries into pieces short enough for one request each."""
    chunks, current = [], ""
    for word in text.split():
        word = word[:CHUNK_LIMIT]
        if current and len(current) + 1 + len(word) > CHUNK_LIMIT:
            chunks.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        chunks.append(current)
    return chunks


@lru_cache(maxsize=256)
def _synthesize(text: str) -> bytes:
    audio = b""
    for i, chunk in enumerate(chunks := _chunks(text)):
        query = urllib.parse.urlencode({
            "ie": "UTF-8", "client": "tw-ob", "tl": "en-US", "q": chunk,
            "total": len(chunks), "idx": i, "textlen": len(chunk),
        })
        req = urllib.request.Request(f"{GOOGLE_TTS}?{query}", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            audio += resp.read()  # MP3 frames concatenate into one playable stream
    return audio


@router.get("/")
@router.get("")
def tts(text: str = Query(..., min_length=1, max_length=2000)):
    try:
        audio = _synthesize(" ".join(text.split()))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Speech service failed: {e}")
    return Response(audio, media_type="audio/mpeg", headers={"Cache-Control": "public, max-age=86400"})
