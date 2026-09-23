import re
from dataclasses import dataclass


@dataclass
class Caption:
    text: str
    start: float
    end: float


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s for s in sentences if s]


def _wrap_lines(sentence: str, max_chars: int) -> list[str]:
    words = sentence.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > max_chars and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def split_into_captions(text: str, total_duration: float, max_chars: int = 18) -> list[Caption]:
    sentences = _split_sentences(text)
    if not sentences:
        return []

    total_chars = sum(len(s) for s in sentences) or 1
    captions = []
    cursor = 0.0
    for sentence in sentences:
        sentence_duration = total_duration * (len(sentence) / total_chars)
        lines = _wrap_lines(sentence, max_chars)
        if not lines:
            cursor += sentence_duration
            continue
        per_line = sentence_duration / len(lines)
        for line in lines:
            captions.append(Caption(text=line, start=cursor, end=cursor + per_line))
            cursor += per_line
    return captions
