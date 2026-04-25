from __future__ import annotations

from server.publishers.exporters import DouyinExporter, MarkdownExporter, XHSExporter


class PublisherRegistry:
    def __init__(self) -> None:
        self._items = {
            "markdown": MarkdownExporter(),
            "xhs": XHSExporter(),
            "douyin": DouyinExporter(),
        }

    def get(self, name: str):
        if name not in self._items:
            raise KeyError(f"unknown publisher: {name}")
        return self._items[name]

    def list(self) -> list[str]:
        return sorted(self._items.keys())


publisher_registry = PublisherRegistry()

