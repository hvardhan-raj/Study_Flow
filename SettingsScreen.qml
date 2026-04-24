import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#F0F4F9"

    readonly property var scheduleSettings: backend.scheduleSettings || ({ daily_time_minutes: 120, preferred_time: "18:00" })
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
                    variant: "primary"
                    small: true
                    onClicked: {
                        backend.updateScheduleSetting("daily_time_minutes", dailyLimitField.text)
                        backend.updateScheduleSetting("preferred_time", startTimeBox.currentText)
                        backend.saveSettings()
                    }
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
                spacing: 18

                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 24
                    Layout.rightMargin: 24
                    Layout.topMargin: 22
                    spacing: 16

                    Rectangle {
                        Layout.fillWidth: true
                        radius: 16
                        color: "#FFFFFF"
                        border.color: "#E2E8F0"
                        implicitHeight: planningColumn.implicitHeight + 36

                        ColumnLayout {
                            id: planningColumn
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 14

                            Text {
                                text: "Study Planning"
                                font.pixelSize: 10
                                font.letterSpacing: 1.4
                                font.bold: true
                                color: "#94A3B8"
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 6

                                Text {
                                    text: "Daily Study Limit (minutes)"
                                    font.pixelSize: 12
                                    font.bold: true
                                    color: "#0F172A"
                                }

                                TextField {
                                    id: dailyLimitField
                                    Layout.fillWidth: true
                                    text: String(root.scheduleSettings.daily_time_minutes || 120)
                                    placeholderText: "120"
                                    selectByMouse: true
                                    validator: IntValidator { bottom: 15; top: 600 }
                                    onEditingFinished: backend.updateScheduleSetting("daily_time_minutes", text)
                                }

                                Text {
                                    text: "Controls how many study minutes can be planned each day before overflow is pushed forward."
                                    wrapMode: Text.WordWrap
                                    font.pixelSize: 10
                                    color: "#64748B"
                                    Layout.fillWidth: true
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 6

                                Text {
                                    text: "Preferred Study Start Time"
                                    font.pixelSize: 12
                                    font.bold: true
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
                                    text: "Daily task slots are allocated sequentially from this time with a 5-minute buffer between revisions."
                                    wrapMode: Text.WordWrap
                                    font.pixelSize: 10
                                    color: "#64748B"
                                    Layout.fillWidth: true
                                }
                            }
                        }
                    }

                    SettingsSection {
                        Layout.fillWidth: true
                        sectionTitle: "Notifications"

                        Repeater {
                            model: backend.settingsColumns.length > 1 ? backend.settingsColumns[1].rows : []
                            delegate: SettingsRow {
                                label: modelData.label
                                value: modelData.value || ""
                                valueColor: modelData.valueColor || "#374151"
                                isToggle: modelData.kind === "toggle"
                                toggleOn: modelData.toggleOn || false
                                isDanger: modelData.kind === "danger"
                                dangerLabel: modelData.dangerLabel || ""
                                settingKey: modelData.key || ""
                                onToggled: backend.toggleSetting(settingKey)
                                onDangerClicked: backend.clearHistory()
                            }
                        }
                    }
                }
            }
        }
    }
}
