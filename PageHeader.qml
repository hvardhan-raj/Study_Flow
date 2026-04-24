import QtQuick 2.15
import QtQuick.Layouts 1.15

// Top header bar — consistent across all screens
Item {
    id: root
    height: 62

    property string pageTitle:    "Page Title"
    property string pageSubtitle: "Subtitle"
    property alias  rightContent: rightSlot.data

    Rectangle {
        anchors.fill: parent
        color: "#FFFFFF"

        // Bottom border
        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: "#EEF2F8"
        }

        RowLayout {
            anchors { fill: parent; leftMargin: 28; rightMargin: 20 }
            spacing: 0

            // Title block
            ColumnLayout {
                spacing: 2
                Text {
                    text: root.pageTitle
                    font.pixelSize: 16
                    font.bold: true
                    font.family: "Segoe UI"
                    color: "#0F172A"
                }
                Text {
                    text: root.pageSubtitle
                    font.pixelSize: 9
                    font.letterSpacing: 1.4
                    font.family: "Segoe UI"
                    color: "#94A3B8"
                }
            }

            Item { Layout.fillWidth: true }

            // Injected right-side controls
            Row {
                id: rightSlot
                spacing: 8
            }

            Item { width: 14 }

            // Notification bell
            Rectangle {
                width: 32; height: 32; radius: 16
                color: "#F8FAFC"
                border.color: "#EEF2F8"
                border.width: 1

                AppIcon { anchors.centerIn: parent; name: "bell"; size: 14; tint: "#475569" }

                Rectangle {
                    width: 8; height: 8; radius: 4
                    color: "#EF4444"
                    border.color: "#FFFFFF"
                    border.width: 1.5
                    anchors { top: parent.top; right: parent.right; topMargin: 2; rightMargin: 2 }
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: if (typeof navigation !== "undefined") navigation.navigateToRoute("notifications")
                }
            }

            Item { width: 8 }

            Rectangle {
                width: 10
                height: 10
                radius: 5
                color: "#3B82F6"
            }
        }
    }
}
