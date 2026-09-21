from dataclasses import dataclass


@dataclass
class Caption:
    text: str
    start: float
    end: float


def split_into_captions(text: str, total_duration: float, max_chars: int = 18) -> list[Caption]:
    words = text.split()
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

    if not lines:
        return []

    per_line = total_duration / len(lines)
    captions = []
    for i, line in enumerate(lines):
        start = i * per_line
        end = start + per_line
        captions.append(Caption(text=line, start=start, end=end))
    return captions
