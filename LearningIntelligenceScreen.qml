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
            pageTitle: "Learning Intelligence"
            pageSubtitle: "ANALYTICS, RECALL HEALTH, AND STUDY INSIGHTS"
            rightContent: [
                AppButton { label: "Export Report"; variant: "secondary"; small: true; onClicked: backend.exportLearningReport() }
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

                // ── Stat cards ─────────────────────────────────────────
                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 24; Layout.rightMargin: 24; Layout.topMargin: 22
                    spacing: 14

                    Repeater {
                        model: backend.intelligenceStats
                        delegate: StatCard {
                            Layout.fillWidth: true
                            cardTitle: modelData.title; value: modelData.value
                            subtitle:  modelData.subtitle; trend: modelData.trend
                            trendUp:   modelData.trendUp; accentColor: modelData.accentColor
                            valueColor: modelData.valueColor
                        }
                    }
                }

                // ── Study trend + Subject confidence ───────────────────
                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 24; Layout.rightMargin: 24
                    spacing: 18

                    // Study Trend chart
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredWidth: 3
                        implicitHeight: 300; radius: 16
                        color: "#FFFFFF"; border.color: "#EEF2F8"; border.width: 1

                        ColumnLayout {
                            anchors { fill: parent; margins: 22 }
                            spacing: 12

                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "Study Trend"; font.pixelSize: 15; font.bold: true; font.family: "Segoe UI"; color: "#0F172A"; Layout.fillWidth: true }
                                TagPill { tagText: "14 days"; tagColor: "#3B82F6" }
                            }

                            Text {
                                text: "Minutes logged per session, normalized into a trend line."
                                font.pixelSize: 11; font.family: "Segoe UI"; color: "#64748B"
                                Layout.fillWidth: true; wrapMode: Text.WordWrap
                            }

                            Canvas {
                                id: studyChart
                                Layout.fillWidth: true; Layout.fillHeight: true
                                property var values: backend.studyTrend
                                onValuesChanged: requestPaint()
                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.clearRect(0, 0, width, height)
                                    var vals = studyChart.values || []
                                    if (vals.length === 0) return
                                    var minV = Math.min.apply(Math, vals)
                                    var maxV = Math.max.apply(Math, vals)
                                    var range = Math.max(1, maxV - minV)
                                    var px = 18, py = 18
                                    function xAt(i) { return px + (i / Math.max(1, vals.length - 1)) * (width - px * 2) }
                                    function yAt(v) { return height - py - ((v - minV) / range) * (height - py * 2) }

                                    // Grid lines
                                    ctx.strokeStyle = "#EEF2F8"; ctx.lineWidth = 1
                                    for (var g = 0; g < 4; g++) {
                                        var gy = py + g * ((height - py * 2) / 3)
                                        ctx.beginPath(); ctx.moveTo(px, gy); ctx.lineTo(width - px, gy); ctx.stroke()
                                    }

                                    // Area fill
                                    var grad = ctx.createLinearGradient(0, 0, 0, height)
                                    grad.addColorStop(0, "rgba(59,130,246,0.25)")
                                    grad.addColorStop(1, "rgba(59,130,246,0.02)")
                                    ctx.beginPath(); ctx.moveTo(xAt(0), yAt(vals[0]))
                                    for (var i = 1; i < vals.length; i++) ctx.lineTo(xAt(i), yAt(vals[i]))
                                    ctx.lineTo(xAt(vals.length - 1), height - py)
                                    ctx.lineTo(xAt(0), height - py); ctx.closePath()
                                    ctx.fillStyle = grad; ctx.fill()

                                    // Line
                                    ctx.beginPath(); ctx.moveTo(xAt(0), yAt(vals[0]))
                                    for (var j = 1; j < vals.length; j++) ctx.lineTo(xAt(j), yAt(vals[j]))
                                    ctx.strokeStyle = "#2563EB"; ctx.lineWidth = 2.5; ctx.stroke()

                                    // Dots
                                    for (var k = 0; k < vals.length; k++) {
                                        ctx.beginPath(); ctx.arc(xAt(k), yAt(vals[k]), 3.5, 0, Math.PI * 2)
                                        ctx.fillStyle = "#FFFFFF"; ctx.fill()
                                        ctx.strokeStyle = "#2563EB"; ctx.lineWidth = 2; ctx.stroke()
                                    }
                                }
                            }
                        }
                    }

                    // Subject Confidence
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredWidth: 2
                        implicitHeight: 300; radius: 16
                        color: "#FFFFFF"; border.color: "#EEF2F8"; border.width: 1

                        ColumnLayout {
                            anchors { fill: parent; margins: 22 }
                            spacing: 14

                            Text { text: "Subject Confidence"; font.pixelSize: 15; font.bold: true; font.family: "Segoe UI"; color: "#0F172A" }

                            Repeater {
                                model: backend.subjectConfidence
                                delegate: ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 5

                                    RowLayout {
                                        Layout.fillWidth: true
                                        Text { text: modelData.subject; font.pixelSize: 12; font.bold: true; font.family: "Segoe UI"; color: "#334155"; Layout.fillWidth: true; elide: Text.ElideRight }
                                        Text { text: modelData.pct + "%"; font.pixelSize: 12; font.bold: true; font.family: "Segoe UI"; color: modelData.color }
                                    }

                                    Rectangle {
                                        Layout.fillWidth: true; height: 7; radius: 4; color: "#EEF2F8"
                                        Rectangle {
                                            width: parent.width * (modelData.pct / 100)
                                            height: parent.height; radius: parent.radius; color: modelData.color
                                            Behavior on width { NumberAnimation { duration: 500; easing.type: Easing.OutCubic } }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // ── Activity heatmap + Subject health ──────────────────
                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 24; Layout.rightMargin: 24
                    spacing: 18

                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredWidth: 2
                        implicitHeight: 260; radius: 16
                        color: "#FFFFFF"; border.color: "#EEF2F8"; border.width: 1

                        ColumnLayout {
                            anchors { fill: parent; margins: 22 }
                            spacing: 12

                            Text { text: "Activity Heatmap"; font.pixelSize: 15; font.bold: true; font.family: "Segoe UI"; color: "#0F172A" }

                            Grid {
                                columns: 8; rows: 7; spacing: 7
                                Layout.alignment: Qt.AlignHCenter

                                Repeater {
                                    model: backend.activityHeatmap
                                    delegate: Rectangle {
                                        width: 22; height: 22; radius: 6
                                        color: modelData < 20  ? "#EEF2F8"
                                             : modelData < 45  ? "#BFDBFE"
                                             : modelData < 75  ? "#60A5FA"
                                             : "#2563EB"
                                    }
                                }
                            }

                            Text { text: "Darker = more minutes or completed reviews."; font.pixelSize: 11; font.family: "Segoe UI"; color: "#94A3B8"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredWidth: 3
                        implicitHeight: 260; radius: 16
                        color: "#FFFFFF"; border.color: "#EEF2F8"; border.width: 1

                        ColumnLayout {
                            anchors { fill: parent; margins: 22 }
                            spacing: 10

                            Text { text: "Subject Health"; font.pixelSize: 15; font.bold: true; font.family: "Segoe UI"; color: "#0F172A" }

                            Repeater {
                                model: backend.analyticsSubjectRows
                                delegate: Rectangle {
                                    Layout.fillWidth: true; height: 44; radius: 12
                                    color: "#F8FAFC"; border.color: "#EEF2F8"; border.width: 1

                                    RowLayout {
                                        anchors { fill: parent; leftMargin: 12; rightMargin: 12 }
                                        spacing: 10

                                        Rectangle { width: 4; height: 22; radius: 2; color: modelData.color }

                                        Text { text: modelData.subject; font.pixelSize: 12; font.bold: true; font.family: "Segoe UI"; color: "#0F172A"; Layout.fillWidth: true; elide: Text.ElideRight }

                                        TagPill {
                                            tagText:  modelData.risk + " risk"
                                            tagColor: modelData.risk === "High" ? "#EF4444" : (modelData.risk === "Medium" ? "#F59E0B" : "#10B981")
                                        }

                                        Text { text: modelData.nextAction; font.pixelSize: 11; font.family: "Segoe UI"; color: "#64748B"; width: 120; elide: Text.ElideRight }
                                    }
                                }
                            }
                        }
                    }
                }

                // ── AI Study Insights (dark card) ─────────────────────
                Rectangle {
                    Layout.fillWidth: true
                    Layout.leftMargin: 24; Layout.rightMargin: 24; Layout.bottomMargin: 24
                    implicitHeight: insightInner.implicitHeight + 44
                    radius: 16
                    color: "#0F172A"

                    ColumnLayout {
                        id: insightInner
                        anchors { fill: parent; margins: 22 }
                        spacing: 14

                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "AI Study Insights"; font.pixelSize: 15; font.bold: true; font.family: "Segoe UI"; color: "#FFFFFF"; Layout.fillWidth: true }
                            Text { text: "From task history & topic confidence"; font.pixelSize: 11; font.family: "Segoe UI"; color: "#4B6A88" }
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            columnSpacing: 12
                            rowSpacing: 12

                            Repeater {
                                model: backend.intelligenceInsights
                                delegate: Rectangle {
                                    Layout.fillWidth: true
                                    implicitHeight: insightCard.implicitHeight + 28
                                    radius: 14
                                    color: "#1E293B"
                                    border.color: "#2D3F58"
                                    border.width: 1

                                    ColumnLayout {
                                        id: insightCard
                                        anchors { fill: parent; margins: 14 }
                                        spacing: 7

                                        RowLayout {
                                            spacing: 6
                                            Rectangle { width: 8; height: 8; radius: 4; color: modelData.color }
                                            Text { text: modelData.severity; font.pixelSize: 10; font.bold: true; font.family: "Segoe UI"; color: modelData.color; Layout.fillWidth: true }
                                        }

                                        Text { text: modelData.title; font.pixelSize: 13; font.bold: true; font.family: "Segoe UI"; color: "#F1F5F9"; Layout.fillWidth: true; elide: Text.ElideRight }

                                        Text { text: modelData.body; font.pixelSize: 11; font.family: "Segoe UI"; color: "#94A3B8"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
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
