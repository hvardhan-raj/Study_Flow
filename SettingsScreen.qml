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
            pageTitle: "Settings"
            pageSubtitle: "APP CONFIGURATION AND LOCAL DATA"
            rightContent: [
                AppButton { label: "Save Changes"; variant: "primary"; small: true; onClicked: backend.saveSettings() }
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

                // â”€â”€ Settings sections â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 24; Layout.rightMargin: 24; Layout.topMargin: 22
                    spacing: 16

                    Repeater {
                        model: backend.settingsColumns
                        delegate: SettingsSection {
                            Layout.fillWidth: true
                            sectionTitle: modelData.title

                            Repeater {
                                model: modelData.rows
                                delegate: SettingsRow {
                                    label:       modelData.label
                                    value:       modelData.value     || ""
                                    valueColor:  modelData.valueColor || "#374151"
                                    isToggle:    modelData.kind      === "toggle"
                                    toggleOn:    modelData.toggleOn  || false
                                    isDanger:    modelData.kind      === "danger"
                                    dangerLabel: modelData.dangerLabel || ""
                                    settingKey:  modelData.key       || ""
                                    onToggled:      backend.toggleSetting(settingKey)
                                    onDangerClicked: backend.clearHistory()
                                }
                            }
                        }
                    }
                }

            }
        }
    }
}
