import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15

Rectangle {
    id: root
    color: "#F0F4F9"

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        PageHeader {
            Layout.fillWidth: true
            pageTitle: "Dashboard"
            pageSubtitle: "DAILY REVISION BOARD"
            rightContent: [
                AppButton {
                    label: "+ Start Session"
                    variant: "primary"
                    small: true
                    onClicked: backend.startSession()
                }
            ]
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            clip: true

            ColumnLayout {
                width: parent.width
                spacing: 20

                // ── Banner ─────────────────────────────────────────────
                Rectangle {
                    Layout.fillWidth: true
                    Layout.leftMargin: 24
                    Layout.rightMargin: 24
                    Layout.topMargin: 20
                    implicitHeight: 68
                    radius: 16
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "#0F3D6E" }
                        GradientStop { position: 1.0; color: "#1D66BE" }
                    }

                    RowLayout {
                        anchors { fill: parent; leftMargin: 24; rightMargin: 24 }
                        spacing: 14

                        Rectangle {
                            width: 36; height: 36
                            radius: 10
                            color: Qt.rgba(1, 1, 1, 0.14)
                            Text {
                                anchors.centerIn: parent
                                text: backend.dashboardBanner.emoji
                                font.pixelSize: 18
                                color: "white"
                            }
                        }

                        ColumnLayout {
                            spacing: 3
                            Text {
                                text: backend.dashboardBanner.headline
                                font.pixelSize: 14
                                font.bold: true
                                font.family: "Segoe UI"
                                color: "white"
                            }
                            Text {
                                text: backend.dashboardBanner.detail
                                font.pixelSize: 11
                                font.family: "Segoe UI"
                                color: "#93C5FD"
                            }
                        }

                        Item { Layout.fillWidth: true }

                        Rectangle {
                            radius: 12
                            color: Qt.rgba(1, 1, 1, 0.10)
                            border.color: Qt.rgba(1, 1, 1, 0.18)
                            border.width: 1
                            implicitWidth: focusLabel.implicitWidth + 20
                            implicitHeight: 30

                            Text {
                                id: focusLabel
                                anchors.centerIn: parent
                                text: "Focus score " + backend.dashboardFocus.score + "%"
                                font.pixelSize: 11
                                font.bold: true
                                font.family: "Segoe UI"
                                color: "white"
                            }
                        }
                    }
                }

                // ── Stat cards ────────────────────────────────────────
                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 24
                    Layout.rightMargin: 24
                    spacing: 14

                    Repeater {
                        model: backend.dashboardStats
                        delegate: StatCard {
                            Layout.fillWidth: true
                            cardTitle:   modelData.title
                            value:       modelData.value
                            subtitle:    modelData.subtitle
                            trend:       modelData.trend
                            trendUp:     modelData.trendUp
                            valueColor:  modelData.valueColor
                            accentColor: modelData.accentColor
                        }
                    }
                }

                // ── Kanban columns ────────────────────────────────────
                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 24
                    Layout.rightMargin: 24
                    Layout.bottomMargin: 24
                    spacing: 16

                    Repeater {
                        model: backend.dashboardColumns
                        delegate: Rectangle {
                            property var col: modelData

                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            radius: 16
                            color: "#FFFFFF"
                            border.width: 1
                            border.color: "#EEF2F8"
                            implicitHeight: 540

                            // Accent top strip
                            Rectangle {
                                anchors { top: parent.top; left: parent.left; right: parent.right }
                                height: 3
                                radius: 16
                                color: col.accentColor
                            }

                            ColumnLayout {
                                anchors { fill: parent; margins: 16; topMargin: 18 }
                                spacing: 12

                                // Column header
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    Rectangle {
                                        width: 10; height: 10; radius: 5
                                        color: col.accentColor
                                    }

                                    ColumnLayout {
                                        spacing: 2
                                        Text {
                                            text: col.title
                                            font.pixelSize: 14
                                            font.bold: true
                                            font.family: "Segoe UI"
                                            color: "#0F172A"
                                        }
                                        Text {
                                            text: col.subtitle
                                            font.pixelSize: 10
                                            font.family: "Segoe UI"
                                            color: "#94A3B8"
                                        }
                                    }

                                    Item { Layout.fillWidth: true }

                                    TagPill {
                                        tagText:  col.count + " items"
                                        tagColor: col.accentColor
                                    }
                                }

                                // Task list
                                ScrollView {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    contentWidth: availableWidth
                                    clip: true

                                    ColumnLayout {
                                        width: parent.width
                                        spacing: 10

                                        Repeater {
                                            model: col.items
                                            delegate: DashboardTaskCard {
                                                Layout.fillWidth: true
                                                taskData:    modelData
                                                accentColor: col.accentColor
                                            }
                                        }

                                        // Empty state
                                        Item {
                                            visible: col.items.length === 0
                                            Layout.fillWidth: true
                                            implicitHeight: 160

                                            ColumnLayout {
                                                anchors.centerIn: parent
                                                spacing: 6

                                                Text {
                                                    text: col.key === "upcoming" ? "No upcoming tasks" : "All clear ✓"
                                                    font.pixelSize: 13
                                                    font.bold: true
                                                    font.family: "Segoe UI"
                                                    color: "#64748B"
                                                    Layout.alignment: Qt.AlignHCenter
                                                }

                                                Text {
                                                    text: col.key === "upcoming"
                                                        ? "New revisions will appear as the schedule fills out."
                                                        : "Nothing pending in this column right now."
                                                    font.pixelSize: 10
                                                    font.family: "Segoe UI"
                                                    color: "#94A3B8"
                                                    horizontalAlignment: Text.AlignHCenter
                                                    wrapMode: Text.WordWrap
                                                    Layout.alignment: Qt.AlignHCenter
                                                    Layout.maximumWidth: 180
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
