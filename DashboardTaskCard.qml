import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var   taskData:    ({})
    property color accentColor: "#3B82F6"
    property bool  _hov: false

    radius: 14
    color: _hov ? "#FAFCFF" : "#FFFFFF"
    border.width: 1
    border.color: _hov
        ? Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.28)
        : Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.13)
    implicitHeight: cardContent.implicitHeight + 28

    Behavior on color       { ColorAnimation { duration: 140 } }
    Behavior on border.color{ ColorAnimation { duration: 140 } }

    ColumnLayout {
        id: cardContent
        anchors { fill: parent; margins: 14 }
        spacing: 10

        // Top row: subject pill + difficulty + urgency score
        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            TagPill {
                tagText: taskData.subjectShort || taskData.subject || ""
                tagColor: taskData.subjectColor || "#64748B"
            }

            TagPill {
                tagText: taskData.difficulty || ""
                tagColor: taskData.difficultyColor || "#64748B"
                outlined: true
            }

            Item { Layout.fillWidth: true }

            Text {
                text: (taskData.urgencyScore || 0) + " pts"
                font.pixelSize: 10
                font.family: "Segoe UI"
                color: "#B0BEC5"
            }
        }

        // Topic name
        Text {
            Layout.fillWidth: true
            text: taskData.name || ""
            wrapMode: Text.WordWrap
            font.pixelSize: 14
            font.bold: true
            font.family: "Segoe UI"
            color: "#0F172A"
        }

        // Scheduled time
        Text {
            Layout.fillWidth: true
            text: taskData.scheduledText || ""
            font.pixelSize: 11
            font.family: "Segoe UI"
            color: "#64748B"
        }

        // Confidence + status
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Rectangle {
                radius: 8
                color: "#F8FAFC"
                border.color: "#E8EEF4"
                border.width: 1
                implicitWidth: confidenceText.implicitWidth + 14
                implicitHeight: 24
                Text {
                    id: confidenceText
                    anchors.centerIn: parent
                    text: taskData.confidenceLabel || ""
                    font.pixelSize: 10
                    font.family: "Segoe UI"
                    color: "#475569"
                }
            }

            Item { Layout.fillWidth: true }

            TagPill {
                tagText:  taskData.status || ""
                tagColor: taskData.statusColor || accentColor
            }
        }

        // Rating buttons
        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            Repeater {
                model: [
                    { label: "Again", rating: 1, color: "#EF4444" },
                    { label: "Hard",  rating: 2, color: "#F59E0B" },
                    { label: "Good",  rating: 3, color: "#10B981" },
                    { label: "Easy",  rating: 4, color: "#3B82F6" }
                ]

                delegate: Rectangle {
                    id: ratingBtn
                    property bool rHov: false

                    radius: 9
                    color: taskData.isCompleted
                        ? "#F1F5F9"
                        : (rHov
                            ? Qt.rgba(modelData.color.r, modelData.color.g, modelData.color.b, 0.22)
                            : Qt.rgba(modelData.color.r, modelData.color.g, modelData.color.b, 0.09))
                    border.width: 1
                    border.color: taskData.isCompleted
                        ? "#E2E8F0"
                        : Qt.rgba(modelData.color.r, modelData.color.g, modelData.color.b, rHov ? 0.50 : 0.20)
                    implicitWidth:  ratingLbl.implicitWidth + 14
                    implicitHeight: 28

                    Behavior on color       { ColorAnimation { duration: 120 } }
                    Behavior on border.color{ ColorAnimation { duration: 120 } }

                    Text {
                        id: ratingLbl
                        anchors.centerIn: parent
                        text: modelData.label
                        font.pixelSize: 10
                        font.bold: true
                        font.family: "Segoe UI"
                        color: taskData.isCompleted ? "#94A3B8" : modelData.color
                    }

                    MouseArea {
                        anchors.fill: parent
                        enabled: !taskData.isCompleted
                        hoverEnabled: true
                        onEntered:  ratingBtn.rHov = true
                        onExited:   ratingBtn.rHov = false
                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked:  backend.completeRevision(taskData.id, modelData.rating)
                    }
                }
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        onEntered: root._hov = true
        onExited:  root._hov = false
        propagateComposedEvents: true
        function onClicked(mouse) {
            mouse.accepted = false
        }
    }
}
