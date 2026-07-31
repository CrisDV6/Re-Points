import json
from pathlib import Path


class PendingEventQueue:
    """Cola JSONL local; no guarda claves, tokens de dispositivo ni imágenes."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def enqueue(self, event: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")

    def read_all(self) -> list[dict]:
        if not self.path.exists():
            return []
        events = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
        return events

    def replace(self, events: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        content = "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events)
        self.path.write_text(content, encoding="utf-8")
