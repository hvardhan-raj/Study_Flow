import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#F3F6F4"

    property var dashboard: backend.intelligenceDashboard

    function percentValue(value) {
        if (value === undefined || value === null)
            return "0.0%"
        return Number(value).toFixed(1) + "%"
    }

    function scoreValue(value) {
        if (value === undefined || value === null)
            return "0.000"
        return Number(value).toFixed(3)
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        PageHeader {
            Layout.fillWidth: true
            pageTitle: "Learning Intelligence"
            pageSubtitle: "BACKGROUND ML PREDICTIONS, INSTANT READS"
            rightContent: [
                AppButton {
                    label: "Refresh Cache"
                    variant: "secondary"
                    small: true
                    onClicked: backend.refreshIntelligence()
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

                Rectangle {
                    Layout.fillWidth: true
                    Layout.leftMargin: 24
                    Layout.rightMargin: 24
                    Layout.topMargin: 22
                    radius: 18
                    color: "#0E1A16"
                    implicitHeight: statusColumn.implicitHeight + 32

                    ColumnLayout {
                        id: statusColumn
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 8

                        Text {
                            text: dashboard.model_ready ? "Model ready" : "Heuristic fallback"
                            color: dashboard.model_ready ? "#7DD3A7" : "#FACC15"
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            font.bold: true
                        }

                        Text {
                            text: "Retention Score"
                            color: "#D7E4DD"
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                        }

                        Text {
                            text: percentValue(dashboard.retention_score)
                            color: "#FFFFFF"
                            font.family: "Segoe UI"
                            font.pixelSize: 30
                            font.bold: true
                        }

                        Text {
                            text: dashboard.last_updated ? "Last updated " + dashboard.last_updated : "Background worker is preparing the first cache snapshot."
                            color: "#8FA39A"
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 24
                    Layout.rightMargin: 24
                    Layout.bottomMargin: 24
                    columns: width >= 1200 ? 2 : 1
                    rowSpacing: 18
                    columnSpacing: 18

                    Repeater {
                        model: [
                            { title: "High Risk Topics", tone: "#B91C1C", items: dashboard.high_risk_topics || [], kind: "risk" },
                            { title: "Recommended Focus", tone: "#C2410C", items: dashboard.recommended_topics || [], kind: "priority" },
                            { title: "Weak Topics", tone: "#1D4ED8", items: dashboard.weak_topics || [], kind: "weak" }
                        ]

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: listColumn.implicitHeight + 28
                            radius: 18
                            color: "#FFFFFF"
                            border.color: "#D9E3DC"
                            border.width: 1

                            ColumnLayout {
                                id: listColumn
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 12

                                Rectangle {
                                    Layout.fillWidth: true
                                    height: 36
                                    radius: 10
                                    color: modelData.tone

                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData.title
                                        color: "#FFFFFF"
                                        font.family: "Segoe UI"
                                        font.pixelSize: 13
                                        font.bold: true
                                    }
                                }

                                Text {
                                    visible: modelData.items.length === 0
                                    text: "No cached topics yet."
                                    color: "#64748B"
                                    font.family: "Segoe UI"
                                    font.pixelSize: 12
                                }

                                Repeater {
                                    model: modelData.items

                                    delegate: Rectangle {
                                        Layout.fillWidth: true
                                        radius: 14
                                        color: "#F8FBF9"
                                        border.color: "#E5ECE7"
                                        border.width: 1
                                        implicitHeight: cardColumn.implicitHeight + 20

                                        ColumnLayout {
                                            id: cardColumn
                                            anchors.fill: parent
                                            anchors.margins: 10
                                            spacing: 6

                                            RowLayout {
                                                Layout.fillWidth: true
                                                spacing: 8

                                                Text {
                                                    text: modelData.topic
                                                    color: "#102019"
                                                    font.family: "Segoe UI"
                                                    font.pixelSize: 13
                                                    font.bold: true
                                                    Layout.fillWidth: true
                                                    elide: Text.ElideRight
                                                }

                                                Text {
                                                    text: model.kind === "priority" ? "Priority " + scoreValue(modelData.priority_score) : percentValue(modelData.retention_score)
                                                    color: modelData.engine_mode === "ml" ? "#166534" : "#92400E"
                                                    font.family: "Segoe UI"
                                                    font.pixelSize: 11
                                                    font.bold: true
                                                }
                                            }

                                            Text {
                                                text: modelData.subject
                                                color: "#5B6B63"
                                                font.family: "Segoe UI"
                                                font.pixelSize: 11
                                            }

                                            RowLayout {
                                                Layout.fillWidth: true
                                                spacing: 12

                                                Text {
                                                    text: "Risk " + percentValue(modelData.forgetting_risk * 100)
                                                    color: "#475569"
                                                    font.family: "Segoe UI"
                                                    font.pixelSize: 11
                                                }

                                                Text {
                                                    text: "Overdue " + Number(modelData.overdue_days).toFixed(1) + "d"
                                                    color: "#475569"
                                                    font.family: "Segoe UI"
                                                    font.pixelSize: 11
                                                }

                                                Text {
                                                    text: "Stability " + Number(modelData.stability).toFixed(1)
                                                    color: "#475569"
                                                    font.family: "Segoe UI"
                                                    font.pixelSize: 11
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
}
