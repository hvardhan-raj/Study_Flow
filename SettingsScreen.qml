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
            pageSubtitle: "APP CONFIGURATION, CLOUD SYNC, AND LOCAL DATA"
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

                // â”€â”€ Cloud Sync + History â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 24; Layout.rightMargin: 24; Layout.bottomMargin: 24
                    spacing: 18

                    // Cloud sync config
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredWidth: 2
                        implicitHeight: syncInner.implicitHeight + 40
                        radius: 16; color: "#FFFFFF"; border.color: "#EEF2F8"; border.width: 1

                        ColumnLayout {
                            id: syncInner
                            anchors { fill: parent; margins: 20 }
                            spacing: 14

                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "Cloud Sync"; font.pixelSize: 15; font.bold: true; font.family: "Segoe UI"; color: "#0F172A"; Layout.fillWidth: true }
                                TagPill { tagText: backend.syncStatus.label; tagColor: backend.syncStatus.color }
                            }

                            Text {
                                text: "Offline-first is always on. Add Supabase details to enable optional cloud backup."
                                font.pixelSize: 11; font.family: "Segoe UI"; color: "#64748B"
                                wrapMode: Text.WordWrap; Layout.fillWidth: true
                            }

                            Rectangle {
                                Layout.fillWidth: true; implicitHeight: 38; radius: 10
                                color: "#F8FAFC"; border.color: syncUrlField.activeFocus ? "#93C5FD" : "#DDE4EF"; border.width: 1
                                Behavior on border.color { ColorAnimation { duration: 150 } }
                                TextField {
                                    id: syncUrlField
                                    anchors { fill: parent; leftMargin: 12; rightMargin: 12 }
                                    placeholderText: "Supabase project URL"
                                    text: backend.syncSettings.supabaseUrl
                                    font.pixelSize: 12; font.family: "Segoe UI"
                                    background: Item {}
                                    onEditingFinished: backend.updateSyncSetting("supabase_url", text)
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true; implicitHeight: 38; radius: 10
                                color: "#F8FAFC"; border.color: syncKeyField.activeFocus ? "#93C5FD" : "#DDE4EF"; border.width: 1
                                Behavior on border.color { ColorAnimation { duration: 150 } }
                                TextField {
                                    id: syncKeyField
                                    anchors { fill: parent; leftMargin: 12; rightMargin: 12 }
                                    placeholderText: backend.syncSettings.anonKeyConfigured ? "Anon key configured" : "Supabase anon key"
                                    echoMode: TextInput.Password
                                    font.pixelSize: 12; font.family: "Segoe UI"
                                    background: Item {}
                                    onEditingFinished: {
                                        if (text.length > 0) {
                                            backend.updateSyncSetting("supabase_anon_key", text)
                                            text = ""
                                        }
                                    }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "Device: " + backend.syncSettings.deviceId
                                    font.pixelSize: 10; font.family: "Segoe UI"; color: "#94A3B8"
                                    Layout.fillWidth: true; elide: Text.ElideRight
                                }
                                AppButton { label: "Force Full Sync"; variant: "primary"; small: true; onClicked: backend.forceFullSync() }
                            }
                        }
                    }

                    // Sync history
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredWidth: 1
                        implicitHeight: historyInner.implicitHeight + 40
                        radius: 16; color: "#FFFFFF"; border.color: "#EEF2F8"; border.width: 1

                        ColumnLayout {
                            id: historyInner
                            anchors { fill: parent; margins: 20 }
                            spacing: 10

                            Text { text: "Sync History"; font.pixelSize: 15; font.bold: true; font.family: "Segoe UI"; color: "#0F172A" }

                            Repeater {
                                model: backend.syncHistory
                                delegate: Rectangle {
                                    Layout.fillWidth: true
                                    implicitHeight: 62; radius: 12
                                    color: "#F8FAFC"; border.color: "#EEF2F8"; border.width: 1

                                    ColumnLayout {
                                        anchors { fill: parent; margins: 10 }
                                        spacing: 3
                                        Text {
                                            text: modelData.status + "  â†‘" + modelData.pushed + "  â†“" + modelData.pulled
                                            font.pixelSize: 11; font.bold: true; font.family: "Segoe UI"; color: "#0F172A"
                                            Layout.fillWidth: true; elide: Text.ElideRight
                                        }
                                        Text {
                                            text: modelData.message
                                            font.pixelSize: 10; font.family: "Segoe UI"; color: "#64748B"
                                            Layout.fillWidth: true; elide: Text.ElideRight
                                        }
                                    }
                                }
                            }

                            Text {
                                visible: backend.syncHistory.length === 0
                                text: "No sync attempts yet."
                                font.pixelSize: 11; font.family: "Segoe UI"; color: "#94A3B8"
                            }
                        }
                    }
                }
            }
        }
    }
}

