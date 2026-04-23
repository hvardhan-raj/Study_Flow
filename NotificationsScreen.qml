import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#F0F4F9"

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        PageHeader {
            Layout.fillWidth: true
            pageTitle: "Notifications & Alerts"
            pageSubtitle: "REMINDERS & DIGESTS"
            rightContent: [
                AppButton { label: "Export Calendar";   variant: "secondary"; small: true; onClicked: backend.exportCalendar() },
                AppButton { label: "Refresh";           variant: "secondary"; small: true; onClicked: backend.refreshReminders() },
                AppButton { label: "Mark All Read";     variant: "primary";   small: true; onClicked: backend.markAllNotificationsRead() }
            ]
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            clip: true

            RowLayout {
                width: parent.width
                spacing: 18

                // ── Left column: stats + notification list ──────────────
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 2
                    Layout.margins: 24
                    spacing: 16

                    // Stat chips
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        Repeater {
                            model: backend.notificationStats
                            delegate: Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: 84
                                radius: 14
                                color: "#FFFFFF"
                                border.color: "#EEF2F8"
                                border.width: 1

                                ColumnLayout {
                                    anchors { fill: parent; margins: 16 }
                                    spacing: 5

                                    Rectangle {
                                        width: 24; height: 3; radius: 2
                                        color: modelData.color
                                    }

                                    Text {
                                        text: modelData.value
                                        font.pixelSize: 24
                                        font.bold: true
                                        font.family: "Segoe UI"
                                        color: "#0F172A"
                                    }

                                    Text {
                                        text: modelData.label
                                        font.pixelSize: 10
                                        font.letterSpacing: 1.2
                                        font.family: "Segoe UI"
                                        color: "#94A3B8"
                                    }
                                }
                            }
                        }
                    }

                    // Notification list
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: notifCol.implicitHeight + 36
                        radius: 16
                        color: "#FFFFFF"
                        border.color: "#EEF2F8"
                        border.width: 1

                        ColumnLayout {
                            id: notifCol
                            anchors { fill: parent; margins: 18 }
                            spacing: 10

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "Recent Notifications"
                                    font.pixelSize: 15
                                    font.bold: true
                                    font.family: "Segoe UI"
                                    color: "#0F172A"
                                    Layout.fillWidth: true
                                }
                                AppButton { label: "Clear All"; variant: "ghost"; small: true; onClicked: backend.clearNotifications() }
                            }

                            Repeater {
                                model: backend.notifications
                                delegate: Rectangle {
                                    Layout.fillWidth: true
                                    implicitHeight: notifRow.implicitHeight + 22
                                    radius: 12
                                    color: modelData.read ? "#FAFBFC" : "#F0F7FF"
                                    border.color: modelData.read ? "#EEF2F8" : "#BFDBFE"
                                    border.width: 1

                                    RowLayout {
                                        id: notifRow
                                        anchors { fill: parent; margins: 12 }
                                        spacing: 12

                                        // Color accent bar
                                        Rectangle {
                                            width: 3
                                            Layout.fillHeight: true
                                            radius: 2
                                            color: modelData.color || "#3B82F6"
                                        }

                                        // Icon circle
                                        Rectangle {
                                            width: 34; height: 34; radius: 12
                                            color: modelData.read ? "#F1F5F9" : Qt.rgba(
                                                (modelData.color || "#3B82F6").r,
                                                (modelData.color || "#3B82F6").g,
                                                (modelData.color || "#3B82F6").b, 0.12)
                                            Text {
                                                anchors.centerIn: parent
                                                text: modelData.icon || "!"
                                                font.pixelSize: 13
                                                font.bold: true
                                                color: modelData.color || "#3B82F6"
                                            }
                                        }

                                        // Content
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 3

                                            RowLayout {
                                                Layout.fillWidth: true
                                                Text {
                                                    text: modelData.title || "StudyFlow Alert"
                                                    font.pixelSize: 12
                                                    font.bold: !modelData.read
                                                    font.family: "Segoe UI"
                                                    color: "#0F172A"
                                                    Layout.fillWidth: true
                                                    elide: Text.ElideRight
                                                }
                                                Text {
                                                    text: modelData.time || ""
                                                    font.pixelSize: 10
                                                    font.family: "Segoe UI"
                                                    color: "#94A3B8"
                                                }
                                            }

                                            Text {
                                                text: modelData.body || ""
                                                font.pixelSize: 11
                                                font.family: "Segoe UI"
                                                color: "#64748B"
                                                wrapMode: Text.WordWrap
                                                Layout.fillWidth: true
                                                maximumLineCount: 2
                                                elide: Text.ElideRight
                                            }
                                        }

                                        AppButton {
                                            visible: !modelData.read
                                            label: "Read"
                                            variant: "secondary"
                                            small: true
                                            onClicked: backend.markNotificationRead(modelData.id)
                                        }
                                    }
                                }
                            }

                            // Empty state
                            Item {
                                visible: backend.notifications.length === 0
                                Layout.fillWidth: true
                                implicitHeight: 140
                                ColumnLayout {
                                    anchors.centerIn: parent
                                    spacing: 8
                                    Text { text: "Inbox clear ✓"; font.pixelSize: 15; font.bold: true; font.family: "Segoe UI"; color: "#0F172A"; Layout.alignment: Qt.AlignHCenter }
                                    Text { text: "Refresh reminders to rebuild smart alerts."; font.pixelSize: 11; font.family: "Segoe UI"; color: "#94A3B8"; Layout.alignment: Qt.AlignHCenter }
                                }
                            }
                        }
                    }
                }

                // ── Right column: digest + preferences + alerts ─────────
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    Layout.topMargin: 24
                    Layout.rightMargin: 24
                    Layout.bottomMargin: 24
                    spacing: 16

                    // Today's Digest
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: digestCol.implicitHeight + 32
                        radius: 16
                        color: "#EFF6FF"
                        border.color: "#BFDBFE"
                        border.width: 1

                        ColumnLayout {
                            id: digestCol
                            anchors { fill: parent; margins: 16 }
                            spacing: 10

                            Text { text: "Today's Digest"; font.pixelSize: 14; font.bold: true; font.family: "Segoe UI"; color: "#1D4ED8" }

                            Text {
                                text: backend.todayDigest.summary
                                font.pixelSize: 12; font.family: "Segoe UI"; color: "#1E40AF"
                                wrapMode: Text.WordWrap; Layout.fillWidth: true
                            }

                            Rectangle { Layout.fillWidth: true; height: 1; color: "#BFDBFE" }

                            Text {
                                text: backend.todayDigest.nextSession
                                font.pixelSize: 11; font.family: "Segoe UI"; color: "#334155"
                                wrapMode: Text.WordWrap; Layout.fillWidth: true
                            }

                            AppButton { label: "View Schedule"; variant: "primary"; small: true; onClicked: navigation.navigateToRoute("schedule") }
                        }
                    }

                    // Reminder Preferences
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: prefCol.implicitHeight + 32
                        radius: 16
                        color: "#FFFFFF"
                        border.color: "#EEF2F8"
                        border.width: 1

                        ColumnLayout {
                            id: prefCol
                            anchors { fill: parent; margins: 16 }
                            spacing: 10

                            Text { text: "Reminder Preferences"; font.pixelSize: 14; font.bold: true; font.family: "Segoe UI"; color: "#0F172A" }

                            Text {
                                text: backend.reminderPreferences.summary
                                font.pixelSize: 11; font.family: "Segoe UI"; color: "#64748B"
                                wrapMode: Text.WordWrap; Layout.fillWidth: true
                            }

                            RowLayout {
                                spacing: 8
                                TagPill { tagText: backend.reminderPreferences.enabled ? "Daily check on" : "Daily check off"; tagColor: backend.reminderPreferences.enabled ? "#10B981" : "#94A3B8" }
                                TagPill { tagText: "Next " + backend.reminderPreferences.next_run; tagColor: "#3B82F6" }
                            }
                        }
                    }

                    // Upcoming Reminders
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: remCol.implicitHeight + 32
                        radius: 16
                        color: "#FFFFFF"
                        border.color: "#EEF2F8"
                        border.width: 1

                        ColumnLayout {
                            id: remCol
                            anchors { fill: parent; margins: 16 }
                            spacing: 10

                            Text { text: "Upcoming Reminders"; font.pixelSize: 14; font.bold: true; font.family: "Segoe UI"; color: "#0F172A" }

                            Repeater {
                                model: backend.upcomingReminders
                                delegate: RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 10

                                    Rectangle {
                                        width: 8
                                        height: 8
                                        radius: 4
                                        color: modelData.color
                                        Layout.alignment: Qt.AlignVCenter
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 1
                                        Text { text: modelData.title; font.pixelSize: 11; font.bold: true; font.family: "Segoe UI"; color: "#0F172A"; elide: Text.ElideRight; Layout.fillWidth: true }
                                        Text { text: modelData.subject; font.pixelSize: 10; font.family: "Segoe UI"; color: "#94A3B8" }
                                    }

                                    Text { text: modelData.when; font.pixelSize: 10; font.family: "Segoe UI"; color: "#64748B" }
                                }
                            }

                            Text { visible: backend.upcomingReminders.length === 0; text: "No upcoming reminders."; font.pixelSize: 11; font.family: "Segoe UI"; color: "#94A3B8" }
                        }
                    }

                    // Alert Settings
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: alertCol.implicitHeight + 32
                        radius: 16
                        color: "#FFFFFF"
                        border.color: "#EEF2F8"
                        border.width: 1

                        ColumnLayout {
                            id: alertCol
                            anchors { fill: parent; margins: 16 }
                            spacing: 12

                            Text { text: "Alert Settings"; font.pixelSize: 14; font.bold: true; font.family: "Segoe UI"; color: "#0F172A" }

                            Repeater {
                                model: backend.alertSettings
                                delegate: RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 10

                                    Rectangle { width: 4; height: 22; radius: 2; color: modelData.color }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 1
                                        Text { text: modelData.label; font.pixelSize: 11; font.bold: true; font.family: "Segoe UI"; color: "#334155" }
                                        Text { text: modelData.description; font.pixelSize: 9; font.family: "Segoe UI"; color: "#94A3B8"; Layout.fillWidth: true; elide: Text.ElideRight }
                                    }

                                    Rectangle {
                                        width: 40; height: 22; radius: 11
                                        color: modelData.on ? modelData.color : "#D1D9E6"
                                        Behavior on color { ColorAnimation { duration: 160 } }

                                        Rectangle {
                                            width: 18; height: 18; radius: 9; color: "#FFFFFF"
                                            anchors.verticalCenter: parent.verticalCenter
                                            x: modelData.on ? parent.width - width - 2 : 2
                                            Behavior on x { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
                                        }

                                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: backend.toggleAlertSetting(modelData.key) }
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
