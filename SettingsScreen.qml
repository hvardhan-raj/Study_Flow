import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#F0F4F9"

    readonly property var scheduleSettings: backend.scheduleSettings || ({ daily_time_minutes: 120, preferred_time: "18:00" })
    readonly property var notificationRows: backend.settingsColumns.length > 1 ? backend.settingsColumns[1].rows : []
    readonly property var timeOptions: [
        "06:00", "06:30", "07:00", "07:30", "08:00", "08:30",
        "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
        "12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
        "15:00", "15:30", "16:00", "16:30", "17:00", "17:30",
        "18:00", "18:30", "19:00", "19:30", "20:00", "20:30",
        "21:00", "21:30"
    ]

    function preferredTimeIndex() {
        var preferred = String(root.scheduleSettings.preferred_time || "18:00")
        var idx = root.timeOptions.indexOf(preferred)
        return idx >= 0 ? idx : root.timeOptions.indexOf("18:00")
    }

    function saveAll() {
        backend.updateScheduleSetting("daily_time_minutes", dailyLimitField.text)
        backend.updateScheduleSetting("preferred_time", startTimeBox.currentText)
        backend.saveSettings()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        PageHeader {
            Layout.fillWidth: true
            pageTitle: "Settings"
            pageSubtitle: "STUDY LIMITS, START TIMES, AND LOCAL PREFERENCES"
            rightContent: [
                AppButton {
                    label: "Save"
                    iconName: "check"
                    variant: "primary"
                    small: true
                    onClicked: root.saveAll()
                }
            ]
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: 24
            Layout.rightMargin: 24
            Layout.topMargin: 22
            Layout.bottomMargin: 24
            spacing: 16

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 92
                radius: 18
                color: "#FFFFFF"
                border.color: "#E2E8F0"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 14

                    Rectangle {
                        width: 42
                        height: 42
                        radius: 14
                        color: "#EFF6FF"

                        AppIcon {
                            anchors.centerIn: parent
                            name: "calendar"
                            size: 18
                            tint: "#2563EB"
                        }
                    }

                    ColumnLayout {
                        spacing: 4
                        Text {
                            text: "Daily planning controls"
                            font.pixelSize: 15
                            font.bold: true
                            font.family: "Segoe UI"
                            color: "#0F172A"
                        }
                        Text {
                            text: "Set your daily study cap and preferred start time. Changes are applied locally and rebalance the revision schedule."
                            font.pixelSize: 11
                            font.family: "Segoe UI"
                            color: "#64748B"
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }

                    Item { Layout.fillWidth: true }

                    TagPill {
                        tagText: String(root.scheduleSettings.daily_time_minutes || 120) + " min / day"
                        tagColor: "#3B82F6"
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 16

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 18
                    color: "#FFFFFF"
                    border.color: "#E2E8F0"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 18

                        ColumnLayout {
                            spacing: 4
                            Text {
                                text: "Study Planning"
                                font.pixelSize: 16
                                font.bold: true
                                font.family: "Segoe UI"
                                color: "#0F172A"
                            }
                            Text {
                                text: "Control how much work the scheduler can place in a day."
                                font.pixelSize: 11
                                font.family: "Segoe UI"
                                color: "#94A3B8"
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            radius: 16
                            color: "#F8FAFC"
                            border.color: "#E2E8F0"
                            implicitHeight: dailyBlock.implicitHeight + 24

                            ColumnLayout {
                                id: dailyBlock
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 8

                                Text {
                                    text: "Daily Study Limit"
                                    font.pixelSize: 12
                                    font.bold: true
                                    font.family: "Segoe UI"
                                    color: "#0F172A"
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 10

                                    TextField {
                                        id: dailyLimitField
                                        Layout.preferredWidth: 120
                                        text: String(root.scheduleSettings.daily_time_minutes || 120)
                                        placeholderText: "120"
                                        selectByMouse: true
                                        validator: IntValidator { bottom: 15; top: 600 }
                                        onEditingFinished: backend.updateScheduleSetting("daily_time_minutes", text)
                                    }

                                    Text {
                                        text: "minutes per day"
                                        font.pixelSize: 11
                                        font.family: "Segoe UI"
                                        color: "#64748B"
                                    }

                                    Item { Layout.fillWidth: true }
                                }

                                Text {
                                    text: "When the daily cap is reached, remaining revisions are pushed forward automatically."
                                    wrapMode: Text.WordWrap
                                    font.pixelSize: 10
                                    font.family: "Segoe UI"
                                    color: "#64748B"
                                    Layout.fillWidth: true
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            radius: 16
                            color: "#F8FAFC"
                            border.color: "#E2E8F0"
                            implicitHeight: timeBlock.implicitHeight + 24

                            ColumnLayout {
                                id: timeBlock
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 8

                                Text {
                                    text: "Preferred Start Time"
                                    font.pixelSize: 12
                                    font.bold: true
                                    font.family: "Segoe UI"
                                    color: "#0F172A"
                                }

                                ComboBox {
                                    id: startTimeBox
                                    Layout.fillWidth: true
                                    model: root.timeOptions
                                    currentIndex: root.preferredTimeIndex()
                                    onActivated: backend.updateScheduleSetting("preferred_time", currentText)
                                }

                                Text {
                                    text: "Study sessions are allocated from this time with a 5-minute gap between revisions."
                                    wrapMode: Text.WordWrap
                                    font.pixelSize: 10
                                    font.family: "Segoe UI"
                                    color: "#64748B"
                                    Layout.fillWidth: true
                                }
                            }
                        }

                        Item { Layout.fillHeight: true }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 18
                    color: "#FFFFFF"
                    border.color: "#E2E8F0"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 18

                        ColumnLayout {
                            spacing: 4
                            Text {
                                text: "Notifications & Data"
                                font.pixelSize: 16
                                font.bold: true
                                font.family: "Segoe UI"
                                color: "#0F172A"
                            }
                            Text {
                                text: "Toggle reminder behavior and manage local history."
                                font.pixelSize: 11
                                font.family: "Segoe UI"
                                color: "#94A3B8"
                            }
                        }

                        Repeater {
                            model: root.notificationRows
                            delegate: Rectangle {
                                Layout.fillWidth: true
                                radius: 16
                                color: "#F8FAFC"
                                border.color: "#E2E8F0"
                                implicitHeight: 72

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 16
                                    spacing: 12

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 3

                                        Text {
                                            text: modelData.label
                                            font.pixelSize: 12
                                            font.bold: true
                                            font.family: "Segoe UI"
                                            color: "#0F172A"
                                        }

                                        Text {
                                            text: modelData.key === "notifications"
                                                ? "Enable or mute in-app alerts and toast updates."
                                                : (modelData.key === "reminders"
                                                    ? "Control scheduled reminder generation."
                                                    : "Automatically rebalance revision dates after changes.")
                                            font.pixelSize: 10
                                            font.family: "Segoe UI"
                                            color: "#64748B"
                                            wrapMode: Text.WordWrap
                                            Layout.fillWidth: true
                                        }
                                    }

                                    Rectangle {
                                        width: 44
                                        height: 24
                                        radius: 12
                                        color: modelData.toggleOn ? "#3B82F6" : "#CBD5E1"
                                        Behavior on color { ColorAnimation { duration: 160 } }

                                        Rectangle {
                                            width: 20
                                            height: 20
                                            radius: 10
                                            color: "#FFFFFF"
                                            anchors.verticalCenter: parent.verticalCenter
                                            x: modelData.toggleOn ? parent.width - width - 2 : 2
                                            Behavior on x { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: backend.toggleSetting(modelData.key || "")
                                        }
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            radius: 16
                            color: "#FEF2F2"
                            border.color: "#FECACA"
                            implicitHeight: dangerBlock.implicitHeight + 24

                            ColumnLayout {
                                id: dangerBlock
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 8

                                Text {
                                    text: "Clear Local History"
                                    font.pixelSize: 12
                                    font.bold: true
                                    font.family: "Segoe UI"
                                    color: "#991B1B"
                                }

                                Text {
                                    text: "Removes stored study minutes and recent notifications from local state."
                                    font.pixelSize: 10
                                    font.family: "Segoe UI"
                                    color: "#7F1D1D"
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }

                                AppButton {
                                    label: "Clear History"
                                    iconName: "close"
                                    variant: "danger"
                                    small: true
                                    onClicked: backend.clearHistory()
                                }
                            }
                        }

                        Item { Layout.fillHeight: true }
                    }
                }
            }
        }
    }
}
