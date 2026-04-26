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
                AppButton { label: "Refresh"; iconName: "refresh"; variant: "secondary"; small: true; onClicked: backend.refreshReminders() },
                AppButton { label: "Mark All Read"; iconName: "check"; variant: "primary"; small: true; onClicked: backend.markAllNotificationsRead() }
            ]
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: 24
            Layout.rightMargin: 24
            Layout.topMargin: 20
            Layout.bottomMargin: 24
            spacing: 18

            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: 2
                Layout.fillHeight: true
                spacing: 16

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 18
                    color: "#FFFFFF"
                    border.color: "#EEF2F8"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 12

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
                            AppButton { label: "Clear All"; iconName: "close"; variant: "ghost"; small: true; onClicked: backend.clearNotifications() }
                        }

                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            contentWidth: availableWidth

                            ColumnLayout {
                                width: parent.width
                                spacing: 10

                                Repeater {
                                    model: backend.notifications
                                    delegate: Rectangle {
                                        Layout.fillWidth: true
                                        implicitHeight: notifRow.implicitHeight + 22
                                        radius: 14
                                        color: modelData.read ? "#FAFBFC" : "#F0F7FF"
                                        border.color: modelData.read ? "#EEF2F8" : "#BFDBFE"
                                        border.width: 1

                                        RowLayout {
                                            id: notifRow
                                            anchors.fill: parent
                                            anchors.margins: 12
                                            spacing: 12

                                            Rectangle {
                                                width: 4
                                                Layout.fillHeight: true
                                                radius: 2
                                                color: modelData.color || "#3B82F6"
                                            }

                                            Rectangle {
                                                width: 36
                                                height: 36
                                                radius: 12
                                                color: modelData.read ? "#F1F5F9" : Qt.rgba(modelData.color.r, modelData.color.g, modelData.color.b, 0.12)

                                                AppIcon {
                                                    anchors.centerIn: parent
                                                    name: modelData.icon || "info"
                                                    size: 16
                                                    tint: modelData.color || "#3B82F6"
                                                }
                                            }

                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 4

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
                                                }
                                            }

                                            AppButton {
                                                visible: !modelData.read
                                                label: "Read"
                                                iconName: "check"
                                                variant: "secondary"
                                                small: true
                                                onClicked: backend.markNotificationRead(modelData.id)
                                            }
                                        }
                                    }
                                }

                                Item {
                                    visible: backend.notifications.length === 0
                                    Layout.fillWidth: true
                                    implicitHeight: 180

                                    ColumnLayout {
                                        anchors.centerIn: parent
                                        spacing: 8
                                        AppIcon { Layout.alignment: Qt.AlignHCenter; name: "check"; size: 20; tint: "#10B981" }
                                        Text { text: "Inbox clear"; font.pixelSize: 15; font.bold: true; font.family: "Segoe UI"; color: "#0F172A"; Layout.alignment: Qt.AlignHCenter }
                                        Text { text: "Refresh reminders to rebuild smart alerts."; font.pixelSize: 11; font.family: "Segoe UI"; color: "#94A3B8"; Layout.alignment: Qt.AlignHCenter }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                spacing: 16

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: digestCol.implicitHeight + 32
                    radius: 18
                    color: "#FFFFFF"
                    border.color: "#E2E8F0"
                    border.width: 1

                    ColumnLayout {
                        id: digestCol
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 10

                        RowLayout {
                            spacing: 8
                            AppIcon { name: backend.todayDigest.overdueCount > 0 ? "alert" : "calendar"; tint: backend.todayDigest.tone || "#1D4ED8"; size: 16 }
                            Text { text: "Today's Digest"; font.pixelSize: 14; font.bold: true; font.family: "Segoe UI"; color: "#0F172A" }
                            Item { Layout.fillWidth: true }
                            TagPill {
                                tagText: backend.todayDigest.overdueCount > 0 ? "Overdue focus" : (backend.todayDigest.dueTodayCount > 0 ? "Due today" : "Clear")
                                tagColor: backend.todayDigest.tone || "#3B82F6"
                            }
                        }

                        Text {
                            text: backend.todayDigest.summary
                            font.pixelSize: 13
                            font.bold: true
                            font.family: "Segoe UI"
                            color: "#0F172A"
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Text {
                            text: backend.todayDigest.nextSession
                            font.pixelSize: 11
                            font.family: "Segoe UI"
                            color: "#475569"
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Text {
                            visible: backend.todayDigest.nextSubject && backend.todayDigest.nextSubject.length > 0
                            text: backend.todayDigest.nextSubject
                            font.pixelSize: 10
                            font.bold: true
                            font.family: "Segoe UI"
                            color: backend.todayDigest.tone || "#3B82F6"
                        }

                        AppButton { label: "View Schedule"; iconName: "calendar"; variant: "primary"; small: true; onClicked: navigation.navigateToRoute("schedule") }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: remCol.implicitHeight + 32
                    radius: 18
                    color: "#FFFFFF"
                    border.color: "#EEF2F8"
                    border.width: 1

                    ColumnLayout {
                        id: remCol
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 10

                        Text { text: "Upcoming Reminders"; font.pixelSize: 14; font.bold: true; font.family: "Segoe UI"; color: "#0F172A" }

                        Repeater {
                            model: backend.upcomingReminders
                            delegate: RowLayout {
                                Layout.fillWidth: true
                                spacing: 10

                                Rectangle {
                                    width: 10
                                    height: 10
                                    radius: 5
                                    color: modelData.color
                                    Layout.alignment: Qt.AlignVCenter
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    Text { text: modelData.title; font.pixelSize: 11; font.bold: true; font.family: "Segoe UI"; color: "#0F172A"; elide: Text.ElideRight; Layout.fillWidth: true }
                                    Text { text: modelData.subject; font.pixelSize: 10; font.family: "Segoe UI"; color: "#94A3B8" }
                                }

                                Text { text: modelData.when; font.pixelSize: 10; font.family: "Segoe UI"; color: "#64748B" }
                            }
                        }

                        Text { visible: backend.upcomingReminders.length === 0; text: "No upcoming reminders."; font.pixelSize: 11; font.family: "Segoe UI"; color: "#94A3B8" }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: deliveryCol.implicitHeight + 32
                    radius: 18
                    color: "#FFFFFF"
                    border.color: "#EEF2F8"
                    border.width: 1

                    ColumnLayout {
                        id: deliveryCol
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 12

                        Text { text: "Reminder Delivery"; font.pixelSize: 14; font.bold: true; font.family: "Segoe UI"; color: "#0F172A" }

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: deliveryEnabledRow.implicitHeight + 22
                            radius: 14
                            color: "#F8FAFC"
                            border.color: "#E2E8F0"

                            RowLayout {
                                id: deliveryEnabledRow
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 10

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 3
                                    Text { text: "Reminder checks"; font.pixelSize: 11; font.bold: true; font.family: "Segoe UI"; color: "#334155" }
                                    Text { text: "Keeps the notification worker active for daily digests and scheduled study alerts."; font.pixelSize: 10; font.family: "Segoe UI"; color: "#64748B"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                }

                                Rectangle {
                                    width: 40
                                    height: 22
                                    radius: 11
                                    color: backend.reminderPreferences.enabled ? "#10B981" : "#D1D9E6"
                                    Behavior on color { ColorAnimation { duration: 160 } }

                                    Rectangle {
                                        width: 18
                                        height: 18
                                        radius: 9
                                        color: "#FFFFFF"
                                        anchors.verticalCenter: parent.verticalCenter
                                        x: backend.reminderPreferences.enabled ? parent.width - width - 2 : 2
                                        Behavior on x { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: backend.updateReminderPreference("enabled", backend.reminderPreferences.enabled ? "false" : "true")
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: desktopRow.implicitHeight + 22
                            radius: 14
                            color: "#F8FAFC"
                            border.color: "#E2E8F0"

                            RowLayout {
                                id: desktopRow
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 10

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 3
                                    Text { text: "System study notifications"; font.pixelSize: 11; font.bold: true; font.family: "Segoe UI"; color: "#334155" }
                                    Text { text: "Show a desktop notification when a scheduled study block reaches its start time."; font.pixelSize: 10; font.family: "Segoe UI"; color: "#64748B"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                }

                                Rectangle {
                                    width: 40
                                    height: 22
                                    radius: 11
                                    color: backend.reminderPreferences.desktop_notifications ? "#3B82F6" : "#D1D9E6"
                                    Behavior on color { ColorAnimation { duration: 160 } }

                                    Rectangle {
                                        width: 18
                                        height: 18
                                        radius: 9
                                        color: "#FFFFFF"
                                        anchors.verticalCenter: parent.verticalCenter
                                        x: backend.reminderPreferences.desktop_notifications ? parent.width - width - 2 : 2
                                        Behavior on x { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: backend.updateReminderPreference("desktop_notifications", backend.reminderPreferences.desktop_notifications ? "false" : "true")
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
