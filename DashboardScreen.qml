import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15

Rectangle {
    id: root
    color: "#F0F4F9"
    property var sessionInfo: backend.activeSession

    function sessionTimerText() {
        if (!sessionInfo.active || !sessionInfo.startedAt)
            return "00:00:00"
        var started = new Date(sessionInfo.startedAt)
        if (isNaN(started.getTime()))
            return sessionInfo.timerText || "00:00:00"
        var elapsed = Math.max(0, Math.floor((Date.now() - started.getTime()) / 1000))
        var hours = Math.floor(elapsed / 3600)
        var minutes = Math.floor((elapsed % 3600) / 60)
        var seconds = elapsed % 60
        return ("0" + hours).slice(-2) + ":" + ("0" + minutes).slice(-2) + ":" + ("0" + seconds).slice(-2)
    }

    Timer {
        interval: 1000
        running: root.sessionInfo.active
        repeat: true
        onTriggered: sessionTimer.text = root.sessionTimerText()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        PageHeader {
            Layout.fillWidth: true
            pageTitle: "Dashboard"
            pageSubtitle: "DAILY REVISION BOARD"
            rightContent: [
                Rectangle {
                    radius: 14
                    color: backend.activeSession.active ? "#ECFDF5" : "#EFF6FF"
                    border.color: backend.activeSession.active ? "#A7F3D0" : "#BFDBFE"
                    border.width: 1
                    implicitWidth: timerRow.implicitWidth + 18
                    implicitHeight: 30

                    Row {
                        id: timerRow
                        anchors.centerIn: parent
                        spacing: 6
                        AppIcon { anchors.verticalCenter: parent.verticalCenter; name: backend.activeSession.active ? "play" : "calendar"; tint: backend.activeSession.active ? "#059669" : "#2563EB"; size: 12 }
                        Text {
                            id: sessionTimer
                            anchors.verticalCenter: parent.verticalCenter
                            text: root.sessionTimerText()
                            font.pixelSize: 11
                            font.bold: true
                            font.family: "Segoe UI"
                            color: backend.activeSession.active ? "#047857" : "#1D4ED8"
                        }
                    }
                },
                AppButton {
                    label: backend.activeSession.label
                    iconName: backend.activeSession.active ? "stop" : "play"
                    variant: backend.activeSession.active ? "danger" : "primary"
                    small: true
                    onClicked: backend.startSession()
                }
            ]
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: 24
            Layout.rightMargin: 24
            Layout.topMargin: 20
            Layout.bottomMargin: 24
            spacing: 18

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 80
                radius: 20
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#0F3D6E" }
                    GradientStop { position: 1.0; color: "#1D66BE" }
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 24
                    anchors.rightMargin: 24
                    spacing: 14

                    Rectangle {
                        width: 40
                        height: 40
                        radius: 12
                        color: Qt.rgba(1, 1, 1, 0.14)
                        Text {
                            anchors.centerIn: parent
                            text: backend.dashboardBanner.emoji
                            font.pixelSize: 18
                            color: "white"
                        }
                    }

                    ColumnLayout {
                        spacing: 4
                        Text { text: backend.dashboardBanner.headline; font.pixelSize: 15; font.bold: true; font.family: "Segoe UI"; color: "white" }
                        Text { text: backend.dashboardBanner.detail; font.pixelSize: 11; font.family: "Segoe UI"; color: "#BFDBFE" }
                    }

                    Item { Layout.fillWidth: true }

                    Rectangle {
                        radius: 14
                        color: Qt.rgba(1, 1, 1, 0.10)
                        border.color: Qt.rgba(1, 1, 1, 0.18)
                        border.width: 1
                        implicitWidth: focusLabel.implicitWidth + 20
                        implicitHeight: 34

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

            RowLayout {
                Layout.fillWidth: true
                spacing: 14

                Repeater {
                    model: backend.dashboardStats
                    delegate: StatCard {
                        Layout.fillWidth: true
                        cardTitle: modelData.title
                        value: modelData.value
                        subtitle: modelData.subtitle
                        trend: modelData.trend
                        trendUp: modelData.trendUp
                        valueColor: modelData.valueColor
                        accentColor: modelData.accentColor
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 16

                Repeater {
                    model: backend.dashboardColumns
                    delegate: Rectangle {
                        property var col: modelData
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        Layout.fillHeight: true
                        radius: 18
                        color: "#FFFFFF"
                        border.width: 1
                        border.color: "#EEF2F8"

                        Rectangle {
                            anchors.top: parent.top
                            anchors.left: parent.left
                            anchors.right: parent.right
                            height: 3
                            radius: 18
                            color: col.accentColor
                        }

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            anchors.topMargin: 18
                            spacing: 12

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8

                                Rectangle { width: 10; height: 10; radius: 5; color: col.accentColor }

                                ColumnLayout {
                                    spacing: 2
                                    Text { text: col.title; font.pixelSize: 14; font.bold: true; font.family: "Segoe UI"; color: "#0F172A" }
                                    Text { text: col.subtitle; font.pixelSize: 10; font.family: "Segoe UI"; color: "#94A3B8" }
                                }

                                Item { Layout.fillWidth: true }
                                TagPill { tagText: col.count + " items"; tagColor: col.accentColor }
                            }

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
                                            taskData: modelData
                                            accentColor: col.accentColor
                                        }
                                    }

                                    Item {
                                        visible: col.items.length === 0
                                        Layout.fillWidth: true
                                        implicitHeight: 160

                                        ColumnLayout {
                                            anchors.centerIn: parent
                                            spacing: 6
                                            Text { text: col.key === "upcoming" ? "No upcoming tasks" : "All clear"; font.pixelSize: 13; font.bold: true; font.family: "Segoe UI"; color: "#64748B"; Layout.alignment: Qt.AlignHCenter }
                                            Text {
                                                text: col.key === "upcoming" ? "New revisions will appear as the schedule fills out." : "Nothing pending in this column right now."
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
