import QtQuick 2.15
import QtQuick.Layouts 1.15
import Qt5Compat.GraphicalEffects

Rectangle {
    id: root

    property var topicData: ({})
    property string mode: "risk"
    property color accentColor: "#EF4444"

    function percent(value) {
        return Number(value || 0).toFixed(1) + "%"
    }

    function score(value) {
        return Number(value || 0).toFixed(1)
    }

    function badgeColor(label) {
        var text = String(label || "").toLowerCase()
        if (text === "high")
            return "#EF4444"
        if (text === "medium")
            return "#F59E0B"
        return "#10B981"
    }

    radius: 16
    color: "#FFFFFF"
    border.width: 1
    border.color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.16)
    implicitHeight: body.implicitHeight + 26

    layer.enabled: true
    layer.effect: DropShadow {
        horizontalOffset: 0
        verticalOffset: 6
        radius: 16
        samples: 20
        color: "#120F172A"
    }

    ColumnLayout {
        id: body
        anchors.fill: parent
        anchors.margins: 13
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Rectangle {
                width: 30
                height: 30
                radius: 10
                color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.12)

                AppIcon {
                    anchors.centerIn: parent
                    name: root.mode === "risk" ? "alert" : (root.mode === "focus" ? "spark" : "review")
                    size: 15
                    tint: root.accentColor
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                Text {
                    Layout.fillWidth: true
                    text: root.topicData.topic || ""
                    font.pixelSize: 13
                    font.bold: true
                    font.family: "Segoe UI"
                    color: "#0F172A"
                    elide: Text.ElideRight
                }

                Text {
                    text: root.topicData.subject || ""
                    font.pixelSize: 10
                    font.family: "Segoe UI"
                    color: "#64748B"
                }
            }

            TagPill {
                visible: root.mode === "weak"
                tagText: root.topicData.practice_need || ""
                tagColor: root.badgeColor(root.topicData.practice_need)
            }

            TagPill {
                visible: root.mode !== "weak"
                tagText: root.mode === "focus" ? ("+" + root.score(root.topicData.projected_gain) + " pts") : root.percent(root.topicData.retention_score)
                tagColor: root.accentColor
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 6
            radius: 3
            color: "#E8EEF5"

            Rectangle {
                width: parent.width * Math.max(0, Math.min(100, root.mode === "risk" ? (root.topicData.forgetting_risk || 0) * 100 : (root.topicData.quiz_accuracy || root.topicData.retention_score || 0))) / 100.0
                height: parent.height
                radius: parent.radius
                color: root.mode === "weak" ? root.accentColor : Qt.darker(root.accentColor, 1.1)
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            rowSpacing: 8
            columnSpacing: 12

            Repeater {
                model: root.mode === "risk"
                    ? [
                        { label: "Forgetting risk", value: root.percent((root.topicData.forgetting_risk || 0) * 100) },
                        { label: "Urgency", value: root.topicData.overdue_days > 0 ? (Number(root.topicData.overdue_days).toFixed(1) + "d overdue") : "Due soon" },
                        { label: "Retention drop", value: Number(root.topicData.retention_window_days || 0).toFixed(1) + "d left" },
                        { label: "Stability", value: root.score(root.topicData.stability) }
                    ]
                    : (root.mode === "focus"
                        ? [
                            { label: "Expected gain", value: "+" + root.score(root.topicData.projected_gain) + " pts" },
                            { label: "Priority", value: root.score(root.topicData.priority_score) },
                            { label: "Study time", value: Math.round(root.topicData.estimated_minutes || 0) + " min" },
                            { label: "Reviews", value: Math.round(root.topicData.review_count || 0) }
                        ]
                        : [
                            { label: "Quiz accuracy", value: root.percent(root.topicData.quiz_accuracy) },
                            { label: "Error frequency", value: root.percent(root.topicData.error_frequency) },
                            { label: "Practice need", value: root.topicData.practice_need || "Low" },
                            { label: "Last review", value: Number(root.topicData.days_since_last_review || 0).toFixed(1) + "d ago" }
                        ])

                delegate: ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Text {
                        text: modelData.label
                        font.pixelSize: 9
                        font.bold: true
                        font.letterSpacing: 0.7
                        font.family: "Segoe UI"
                        color: "#94A3B8"
                    }

                    Text {
                        text: modelData.value
                        font.pixelSize: 11
                        font.bold: true
                        font.family: "Segoe UI"
                        color: "#0F172A"
                    }
                }
            }
        }
    }
}
