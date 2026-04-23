from ui import NavigationController


def test_navigation_controller_tracks_routes_and_indexes() -> None:
    controller = NavigationController()

    assert controller.currentIndex == 0
    assert controller.currentRoute == "dashboard"

    controller.navigateToRoute("calendar")

    assert controller.currentIndex == 4
    assert controller.currentRoute == "calendar"


def test_navigation_controller_wraps_previous_and_next() -> None:
    controller = NavigationController()

    controller.goToPreviousPage()
    assert controller.currentRoute == "settings"

    controller.goToNextPage()
    assert controller.currentRoute == "dashboard"
