import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#F0F4F9"

    function sendPrompt(text) {
        var clean = (text || messageInput.text).trim()
        if (clean.length === 0) return
        backend.sendAssistantMessage(clean)
        messageInput.text = ""
        chatView.positionViewAtEnd()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        PageHeader {
            Layout.fillWidth: true
            pageTitle: "AI Assistant"
            pageSubtitle: "LOCAL STUDY COACH WITH SCHEDULE CONTEXT"
            rightContent: [
                AppButton { label: "Clear Chat"; variant: "secondary"; small: true; onClicked: backend.clearAssistantChat() }
            ]
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 24
            spacing: 18

            // ── Chat panel ──────────────────────────────────────────────
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: 2
                spacing: 14

                // Status bar
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: statusRow.implicitHeight + 26
                    radius: 14
                    color: backend.assistantStatus.available ? "#ECFDF5" : "#FFF7ED"
                    border.color: backend.assistantStatus.available ? "#A7F3D0" : "#FED7AA"
                    border.width: 1

                    RowLayout {
                        id: statusRow
                        anchors { fill: parent; margins: 13 }
                        spacing: 12

                        Rectangle {
                            width: 36; height: 36; radius: 12
                            color: backend.assistantStatus.available ? "#10B981" : "#F59E0B"
                            Text { anchors.centerIn: parent; text: "AI"; font.pixelSize: 12; font.bold: true; color: "#FFFFFF" }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                text: backend.assistantStatus.provider + " — " + backend.assistantStatus.model
                                font.pixelSize: 13; font.bold: true; font.family: "Segoe UI"; color: "#0F172A"
                            }
                            Text {
                                text: backend.assistantStatus.message
                                font.pixelSize: 11; font.family: "Segoe UI"
                                color: backend.assistantStatus.available ? "#047857" : "#9A3412"
                                wrapMode: Text.WordWrap; Layout.fillWidth: true
                            }
                        }
                    }
                }

                // Chat bubble area + input
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 16
                    color: "#FFFFFF"
                    border.color: "#EEF2F8"
                    border.width: 1

                    ColumnLayout {
                        anchors { fill: parent; margins: 16 }
                        spacing: 12

                        ListView {
                            id: chatView
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            spacing: 10
                            model: backend.assistantMessages

                            delegate: Item {
                                width: chatView.width
                                implicitHeight: bubble.implicitHeight

                                Rectangle {
                                    id: bubble
                                    width: Math.min(parent.width * 0.78, msgText.implicitWidth + 36)
                                    implicitHeight: msgContent.implicitHeight + 22
                                    radius: 16
                                    color: modelData.role === "user" ? "#2563EB" : "#F8FAFC"
                                    border.color: modelData.role === "user" ? "#2563EB" : "#E2E8F0"
                                    border.width: 1
                                    anchors.right: modelData.role === "user" ? parent.right : undefined
                                    anchors.left:  modelData.role === "user" ? undefined : parent.left

                                    ColumnLayout {
                                        id: msgContent
                                        anchors { fill: parent; margins: 11 }
                                        spacing: 5

                                        RowLayout {
                                            Layout.fillWidth: true
                                            Text {
                                                text: modelData.role === "user" ? "You" : "StudyFlow Assistant"
                                                font.pixelSize: 10; font.bold: true; font.family: "Segoe UI"
                                                color: modelData.role === "user" ? "#DBEAFE" : "#64748B"
                                                Layout.fillWidth: true
                                            }
                                            Text {
                                                text: modelData.time
                                                font.pixelSize: 9; font.family: "Segoe UI"
                                                color: modelData.role === "user" ? "#BFDBFE" : "#94A3B8"
                                            }
                                        }

                                        Text {
                                            id: msgText
                                            Layout.fillWidth: true
                                            text: modelData.text
                                            font.pixelSize: 12; font.family: "Segoe UI"
                                            color: modelData.role === "user" ? "#FFFFFF" : "#0F172A"
                                            wrapMode: Text.WordWrap
                                        }
                                    }
                                }
                            }

                            onCountChanged: positionViewAtEnd()
                        }

                        // Quick prompts
                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: promptFlow.implicitHeight + 16
                            radius: 12
                            color: "#F8FAFC"
                            border.color: "#EEF2F8"
                            border.width: 1

                            Flow {
                                id: promptFlow
                                anchors { fill: parent; margins: 8 }
                                spacing: 8

                                Repeater {
                                    model: backend.assistantPrompts
                                    delegate: AppButton {
                                        label: modelData.label; variant: "secondary"; small: true
                                        onClicked: { messageInput.text = modelData.prompt; messageInput.forceActiveFocus() }
                                    }
                                }
                            }
                        }

                        // Message input
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: msgArea.implicitHeight + 16
                                radius: 12
                                color: "#F8FAFC"
                                border.color: msgArea.activeFocus ? "#93C5FD" : "#DDE4EF"
                                border.width: 1
                                Behavior on border.color { ColorAnimation { duration: 150 } }

                                TextArea {
                                    id: msgArea
                                    anchors { fill: parent; margins: 8 }
                                    placeholderText: "Ask what to study, which topic is weak, or how to prepare…"
                                    wrapMode: TextEdit.WordWrap
                                    font.pixelSize: 12
                                    font.family: "Segoe UI"
                                    background: Item {}
                                    Keys.onReturnPressed: function(ev) {
                                        if (ev.modifiers & Qt.ControlModifier) {
                                            messageInput.text = msgArea.text
                                            root.sendPrompt("")
                                            msgArea.text = ""
                                            ev.accepted = true
                                        }
                                    }
                                }
                            }

                            // Hidden backing for sendPrompt compatibility
                            TextInput {
                                id: messageInput
                                visible: false
                            }

                            AppButton {
                                label: "Send"; variant: "primary"
                                onClicked: {
                                    messageInput.text = msgArea.text
                                    root.sendPrompt("")
                                    msgArea.text = ""
                                }
                            }
                        }
                    }
                }
            }

            // ── Context sidebar ─────────────────────────────────────────
            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                spacing: 14

                // Study context card (dark)
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: ctxCol.implicitHeight + 32
                    radius: 16
                    color: "#0F172A"

                    ColumnLayout {
                        id: ctxCol
                        anchors { fill: parent; margins: 16 }
                        spacing: 12

                        Text { text: "Injected Study Context"; font.pixelSize: 14; font.bold: true; font.family: "Segoe UI"; color: "#FFFFFF" }

                        Repeater {
                            model: [
                                { label: "Due today",     value: backend.assistantContextSummary.dueToday,     color: "#3B82F6" },
                                { label: "Overdue",       value: backend.assistantContextSummary.overdue,       color: "#EF4444" },
                                { label: "Weak subjects", value: backend.assistantContextSummary.weakSubjects,  color: "#F59E0B" },
                                { label: "Next topic",    value: backend.assistantContextSummary.nextTopic,     color: "#10B981" }
                            ]
                            delegate: Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: 52
                                radius: 12
                                color: "#1E293B"
                                border.color: "#2D3F58"
                                border.width: 1

                                RowLayout {
                                    anchors { fill: parent; margins: 12 }
                                    spacing: 10
                                    Rectangle { width: 4; height: 22; radius: 2; color: modelData.color }
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2
                                        Text { text: modelData.label; font.pixelSize: 10; font.family: "Segoe UI"; color: "#7A95B0" }
                                        Text { text: String(modelData.value); font.pixelSize: 13; font.bold: true; font.family: "Segoe UI"; color: "#F1F5F9"; elide: Text.ElideRight; Layout.fillWidth: true }
                                    }
                                }
                            }
                        }
                    }
                }

                // LLM setup guide
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: guideCol.implicitHeight + 32
                    radius: 16
                    color: "#FFFFFF"
                    border.color: "#EEF2F8"
                    border.width: 1

                    ColumnLayout {
                        id: guideCol
                        anchors { fill: parent; margins: 16 }
                        spacing: 10

                        Text { text: "Local LLM Setup"; font.pixelSize: 14; font.bold: true; font.family: "Segoe UI"; color: "#0F172A" }

                        Text {
                            text: "Install Ollama and run `ollama pull llama3.2:3b`, then start Ollama. Until then, StudyFlow uses offline context-aware guidance."
                            font.pixelSize: 11; font.family: "Segoe UI"; color: "#64748B"
                            wrapMode: Text.WordWrap; Layout.fillWidth: true
                        }

                        TagPill {
                            tagText:  backend.assistantStatus.available ? "Connected" : "Offline fallback"
                            tagColor: backend.assistantStatus.available ? "#10B981"  : "#F59E0B"
                        }
                    }
                }
            }
        }
    }
}
