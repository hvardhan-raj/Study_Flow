from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

DEFAULT_PAGES: list[dict[str, str]] = [
    {"route": "dashboard", "label": "Dashboard", "icon": "⊞"},
    {"route": "tasks", "label": "Task Inbox", "icon": "✓"},
    {"route": "curriculum", "label": "Curriculum Map", "icon": "◫"},
    {"route": "schedule", "label": "Revision Schedule", "icon": "⊟"},
    {"route": "calendar", "label": "Calendar", "icon": "▦"},
    {"route": "intelligence", "label": "Learning Intelligence", "icon": "↗"},
    {"route": "notifications", "label": "Notifications", "icon": "🔔"},
    {"route": "assistant", "label": "AI Assistant", "icon": "AI"},
    {"route": "settings", "label": "Settings", "icon": "⚙"},
]


class NavigationController(QObject):
    currentIndexChanged = Signal()
    currentRouteChanged = Signal()

    def __init__(self, pages: list[dict[str, str]] | None = None) -> None:
        super().__init__()
        self._pages = pages or DEFAULT_PAGES
        self._route_to_index = {page["route"]: index for index, page in enumerate(self._pages)}
        self._current_index = 0

    @Property("QVariantList", constant=True)
    def pages(self) -> list[dict[str, str]]:
        return self._pages

    @Property(int, notify=currentIndexChanged)
    def currentIndex(self) -> int:
        return self._current_index

    @Property(str, notify=currentRouteChanged)
    def currentRoute(self) -> str:
        return self._pages[self._current_index]["route"]

    @Slot(int)
    def navigateToIndex(self, index: int) -> None:
        if 0 <= index < len(self._pages) and index != self._current_index:
            self._current_index = index
            self.currentIndexChanged.emit()
            self.currentRouteChanged.emit()

    @Slot(str)
    def navigateToRoute(self, route: str) -> None:
        index = self._route_to_index.get(route)
        if index is not None:
            self.navigateToIndex(index)

    @Slot()
    def goToNextPage(self) -> None:
        self.navigateToIndex((self._current_index + 1) % len(self._pages))

    @Slot()
    def goToPreviousPage(self) -> None:
        self.navigateToIndex((self._current_index - 1) % len(self._pages))
