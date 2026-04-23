import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    id: root
    width: 1280
    height: 800
    visible: true
    title: "StudyFlow – Smart Study Schedule"
    color: "#F0F4F9"
    minimumWidth: 1080
    minimumHeight: 720

    Shortcut { sequence: "Ctrl+Tab";       onActivated: navigation.goToNextPage() }
    Shortcut { sequence: "Ctrl+Shift+Tab"; onActivated: navigation.goToPreviousPage() }
    Shortcut { sequence: "F1";             onActivated: navigation.navigateToRoute("assistant") }

    // Shell: sidebar (fixed left) + content area
    RowLayout {
        anchors.fill: parent
        spacing: 0

        Sidebar {
            id: sidebar
            Layout.fillHeight: true
            Layout.preferredWidth: 220
            pages: navigation.pages
            activePage: navigation.currentIndex
            onPageSelected: function(idx) { navigation.navigateToIndex(idx) }
        }

        StackLayout {
            id: contentStack
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: navigation.currentIndex

            DashboardScreen          {}   // 0
            TaskInboxScreen          {}   // 1
            CurriculumMapScreen      {}   // 2
            RevisionScheduleScreen   {}   // 3
            CalendarScreen           {}   // 4
            LearningIntelligenceScreen {}  // 5
            NotificationsScreen      {}   // 6
            AIAssistantScreen        {}   // 7
            SettingsScreen           {}   // 8
        }
    }
}
