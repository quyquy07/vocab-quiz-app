"""Look up words: pronunciation audio + short meaning.

Primary source: the free, open dictionaryapi.dev API (Wiktionary-derived
audio + definitions). Cambridge Dictionary's website blocks automated
requests via Cloudflare, so it cannot be scraped directly.

Fallback: if no recorded audio is available for a word, synthesize one
with gTTS (Google Text-to-Speech). It produces an mp3 and runs anywhere
with internet access, including Linux cloud servers, so every word in a
quiz always has something to play.
"""
import re
import unicodedata
from pathlib import Path

import requests

API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{}"
AUDIO_DIR = Path(__file__).parent / "static" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def slugify(word: str) -> str:
    normalized = unicodedata.normalize("NFKD", word.strip().lower())
    ascii_only = normalized.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-") or "word"


def _download_audio(url: str, dest: Path) -> bool:
    if dest.exists():
        return True
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        return True
    except requests.RequestException:
        return False


def _region_of(url: str) -> str:
    lower = url.lower()
    if "uk" in lower or "gb" in lower or "-br." in lower:
        return "uk"
    if "us" in lower:
        return "us"
    return "other"


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def _synthesize_tts(word: str, dest: Path) -> bool:
    """Generate a pronunciation mp3 with gTTS (works on Linux cloud hosts)."""
    if dest.exists() and dest.stat().st_size > 0:
        return True
    try:
        from gtts import gTTS

        tts = gTTS(text=word, lang="en", tld="co.uk")
        tts.save(str(dest))
        if dest.exists() and dest.stat().st_size > 0:
            return True
        _safe_unlink(dest)
        return False
    except Exception:
        _safe_unlink(dest)
        return False


def lookup_word(word: str) -> dict:
    """Fetch pronunciation + meaning for a word.

    Returns a dict with keys: word, found, ipa_uk, ipa_us, audio_uk, audio_us,
    pos, meaning, source_url, synthesized. Audio fields are local static
    paths (relative to /static) or None.
    """
    slug = slugify(word)
    clean_word = word.strip().lower()
    url = API_URL.format(requests.utils.quote(clean_word))
    result = {
        "word": word.strip(),
        "found": False,
        "ipa_uk": None,
        "ipa_us": None,
        "audio_uk": None,
        "audio_us": None,
        "pos": None,
        "meaning": None,
        "source_url": f"https://dictionary.cambridge.org/dictionary/english/{clean_word}",
        "synthesized": False,
    }

    try:
        resp = requests.get(url, timeout=15)
    except requests.RequestException:
        resp = None

    if resp is not None and resp.status_code == 200:
        entries = resp.json()
        entry = entries[0] if entries else {}

        for phon in entry.get("phonetics", []):
            audio_url = phon.get("audio")
            text = phon.get("text")
            if not audio_url:
                continue
            region = _region_of(audio_url)
            dest_region = "uk" if region == "uk" else "us"
            if result[f"audio_{dest_region}"]:
                continue
            dest = AUDIO_DIR / f"{slug}_{dest_region}.mp3"
            if _download_audio(audio_url, dest):
                result[f"audio_{dest_region}"] = f"audio/{dest.name}"
                result[f"ipa_{dest_region}"] = text

        if not result["ipa_uk"] and not result["ipa_us"] and entry.get("phonetic"):
            result["ipa_us"] = entry["phonetic"]

        meanings = entry.get("meanings", [])
        if meanings:
            result["pos"] = meanings[0].get("partOfSpeech")
            defs = meanings[0].get("definitions", [])
            if defs:
                result["meaning"] = defs[0].get("definition")

    result["found"] = bool(result["meaning"] or result["audio_uk"] or result["audio_us"])

    if not result["audio_uk"] and not result["audio_us"]:
        dest = AUDIO_DIR / f"{slug}_tts.mp3"
        if _synthesize_tts(clean_word, dest):
            result["audio_us"] = f"audio/{dest.name}"
            result["synthesized"] = True

    return result
