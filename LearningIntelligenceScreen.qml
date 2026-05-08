import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#F3F6F4"

    Theme { id: theme }

    property var dashboard: backend.intelligenceDashboard || ({})
    property var overview: dashboard.overview || ({})
    property var subjectRows: backend.subjectConfidence || []
    property var insights: backend.intelligenceInsights || []
    property var trendValues: backend.studyTrend || []
    property var trendLabels: backend.studyTrendLabels || []
    property var weekRows: backend.weekCompletion || []
    property var revisionSummary: backend.revisionWeekSummary || ({})
    property var retentionTrendRows: backend.retentionTrend || []

    function numberValue(value, digits) {
        return Number(value || 0).toFixed(digits)
    }

    function percentValue(value) {
        return numberValue(value, 1) + "%"
    }

    function clampPercent(value) {
        return Math.max(0, Math.min(100, Number(value || 0)))
    }

    function insightColor(name) {
        if (name === "Focus")
            return "#EF4444"
        if (name === "Schedule")
            return "#F59E0B"
        if (name === "Maintain")
            return "#10B981"
        return "#3B82F6"
    }

    function consistencyCaption() {
        var completed = Number(revisionSummary.completed || 0)
        var scheduled = Number(revisionSummary.scheduled || 0)
        return completed + " of " + scheduled + " revisions completed this week"
    }

    function consistencyTrend() {
        return clampPercent(revisionSummary.score || 0) >= 60 ? "Stable cadence" : "Needs rhythm"
    }

    function accuracyCaption() {
        if (dashboard.model_ready)
            return "Model is learning from completed revision outcomes"
        return "Using heuristic signals until more revision history is available"
    }

    function bestTopicText() {
        return String(overview.best_topic || "No recommendation yet")
    }

    function suggestedMinutesText() {
        var minutes = Number(overview.suggested_revision_minutes || 0)
        return minutes > 0 ? (minutes + " min active recall block") : "Build more review history"
    }

    function predictedImprovementText() {
        return "+" + numberValue(overview.predicted_improvement || 0, 1) + " pts"
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        PageHeader {
            Layout.fillWidth: true
            pageTitle: "Learning Intelligence"
            pageSubtitle: "AI-POWERED LEARNING ANALYTICS"
            rightContent: [
                AppButton {
                    label: "Refresh Cache"
                    variant: "secondary"
                    small: true
                    iconName: "refresh"
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
                spacing: 16

                GridLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 24
                    Layout.rightMargin: 24
                    Layout.topMargin: 22
                    columns: width >= 1320 ? 4 : (width >= 900 ? 2 : 1)
                    rowSpacing: 16
                    columnSpacing: 16

                    IntelligenceMetricCard {
                        Layout.fillWidth: true
                        title: "RETENTION SCORE"
                        valueText: percentValue(dashboard.retention_score)
                        caption: dashboard.last_updated
                            ? "Updated " + dashboard.last_updated
                            : "Waiting for the first intelligence snapshot"
                        trendText: clampPercent(dashboard.retention_score || 0) >= 70 ? "Healthy memory" : "Recovery needed"
                        trendUp: clampPercent(dashboard.retention_score || 0) >= 70
                        accentColor: "#0EA5E9"
                        progress: clampPercent(dashboard.retention_score)
                        iconName: "spark"
                        ringLabel: "retention"
                    }

                    IntelligenceMetricCard {
                        Layout.fillWidth: true
                        title: "WEAK TOPICS"
                        valueText: String(overview.weak_topics_count || (dashboard.weak_topics || []).length)
                        caption: String(overview.topics_forgetting_soon || 0) + " topics are likely to slip soon"
                        trendText: Number(overview.weak_topics_count || 0) <= 3 ? "Contained risk" : "Attention needed"
                        trendUp: Number(overview.weak_topics_count || 0) <= 3
                        accentColor: "#EF4444"
                        progress: clampPercent(100 - (Number(overview.weak_topics_count || 0) * 12))
                        iconName: "alert"
                        ringLabel: "coverage"
                    }

                    IntelligenceMetricCard {
                        Layout.fillWidth: true
                        title: "STUDY CONSISTENCY"
                        valueText: String(Math.round(revisionSummary.score || 0)) + "%"
                        caption: consistencyCaption()
                        trendText: consistencyTrend()
                        trendUp: clampPercent(revisionSummary.score || 0) >= 60
                        accentColor: "#10B981"
                        progress: clampPercent(revisionSummary.score || 0)
                        iconName: "calendar"
                        ringLabel: "weekly"
                    }

                    IntelligenceMetricCard {
                        Layout.fillWidth: true
                        title: "PREDICTION ACCURACY"
                        valueText: dashboard.model_ready
                            ? percentValue(overview.prediction_accuracy)
                            : "Heuristic"
                        caption: accuracyCaption()
                        trendText: dashboard.model_ready ? "Model active" : "Fallback mode"
                        trendUp: dashboard.model_ready
                        accentColor: "#8B5CF6"
                        progress: dashboard.model_ready ? clampPercent(overview.prediction_accuracy) : 42
                        iconName: "review"
                        ringLabel: dashboard.model_ready ? "fit" : "proxy"
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 24
                    Layout.rightMargin: 24
                    columns: width >= 1220 ? 2 : 1
                    rowSpacing: 16
                    columnSpacing: 16

                    Rectangle {
                        Layout.fillWidth: true
                        radius: 20
                        color: "#FFFFFF"
                        border.width: 1
                        border.color: "#E6EDF4"
                        implicitHeight: insightsColumn.implicitHeight + 30

                        ColumnLayout {
                            id: insightsColumn
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 14

                            RowLayout {
                                Layout.fillWidth: true

                                ColumnLayout {
                                    spacing: 3

                                    Text {
                                        text: "AI Insights"
                                        font.pixelSize: 17
                                        font.bold: true
                                        font.family: "Segoe UI"
                                        color: "#0F172A"
                                    }

                                    Text {
                                        text: dashboard.model_ready
                                            ? "Model-backed recommendations from your revision patterns"
                                            : "Signal-based recommendations while the model warms up"
                                        font.pixelSize: 11
                                        font.family: "Segoe UI"
                                        color: "#64748B"
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                TagPill {
                                    tagText: dashboard.model_ready ? "ML Active" : "Heuristic"
                                    tagColor: dashboard.model_ready ? "#10B981" : "#F59E0B"
                                }
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: width >= 760 ? 2 : 1
                                rowSpacing: 10
                                columnSpacing: 10

                                IntelligenceInsightCard {
                                    Layout.fillWidth: true
                                    title: "Topics Likely To Be Forgotten Soon"
                                    body: String(overview.topics_forgetting_soon || 0) + " topics are inside the near-drop window. Start with the highest risk stack before adding new material."
                                    badge: String(overview.topics_forgetting_soon || 0) + " soon"
                                    iconName: "alert"
                                    accentColor: "#EF4444"
                                }

                                IntelligenceInsightCard {
                                    Layout.fillWidth: true
                                    title: "Best Topic To Study Next"
                                    body: bestTopicText()
                                    badge: "Next focus"
                                    iconName: "spark"
                                    accentColor: "#3B82F6"
                                }

                                IntelligenceInsightCard {
                                    Layout.fillWidth: true
                                    title: "Suggested Revision Time"
                                    body: suggestedMinutesText()
                                    badge: "Timing"
                                    iconName: "calendar"
                                    accentColor: "#0EA5E9"
                                }

                                IntelligenceInsightCard {
                                    Layout.fillWidth: true
                                    title: "Predicted Performance Improvement"
                                    body: predictedImprovementText() + " if you execute the top recommended revision set today."
                                    badge: "Projected lift"
                                    iconName: "review"
                                    accentColor: "#8B5CF6"
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                radius: 16
                                color: "#F8FAFC"
                                border.width: 1
                                border.color: "#E8EEF5"
                                implicitHeight: signalColumn.implicitHeight + 20

                                ColumnLayout {
                                    id: signalColumn
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 10

                                    Text {
                                        text: "Live Signal Feed"
                                        font.pixelSize: 12
                                        font.bold: true
                                        font.family: "Segoe UI"
                                        color: "#0F172A"
                                    }

                                    Repeater {
                                        model: insights

                                        delegate: RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 10

                                            Rectangle {
                                                width: 10
                                                height: 10
                                                radius: 5
                                                color: insightColor(modelData.severity)
                                            }

                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 1

                                                Text {
                                                    Layout.fillWidth: true
                                                    text: modelData.title
                                                    font.pixelSize: 11
                                                    font.bold: true
                                                    font.family: "Segoe UI"
                                                    color: "#0F172A"
                                                    wrapMode: Text.WordWrap
                                                }

                                                Text {
                                                    Layout.fillWidth: true
                                                    text: modelData.body
                                                    font.pixelSize: 10
                                                    font.family: "Segoe UI"
                                                    color: "#64748B"
                                                    wrapMode: Text.WordWrap
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        radius: 20
                        color: "#FFFFFF"
                        border.width: 1
                        border.color: "#E6EDF4"
                        implicitHeight: chartColumn.implicitHeight + 30

                        ColumnLayout {
                            id: chartColumn
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12

                            Text {
                                text: "Retention Trend"
                                font.pixelSize: 17
                                font.bold: true
                                font.family: "Segoe UI"
                                color: "#0F172A"
                            }

                            Text {
                                text: "Last seven tracked study days ending today"
                                font.pixelSize: 11
                                font.family: "Segoe UI"
                                color: "#64748B"
                            }

                            IntelligenceLineChart {
                                Layout.fillWidth: true
                                values: retentionTrendRows.map(function(item) { return Number(item.value || 0) })
                                accentColor: "#3B82F6"
                                emptyText: "Complete more scheduled revisions to plot the trend"
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 0

                                Repeater {
                                    model: retentionTrendRows

                                    delegate: Item {
                                        Layout.fillWidth: true
                                        implicitHeight: labelColumn.implicitHeight

                                        Column {
                                            id: labelColumn
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            spacing: 3

                                            Text {
                                                anchors.horizontalCenter: parent.horizontalCenter
                                                text: modelData.day
                                                font.pixelSize: 9
                                                font.bold: modelData.isToday
                                                font.family: "Segoe UI"
                                                color: modelData.isToday ? "#0F172A" : "#94A3B8"
                                            }

                                            Text {
                                                anchors.horizontalCenter: parent.horizontalCenter
                                                text: Math.round(Number(modelData.value || 0)) + "%"
                                                font.pixelSize: 10
                                                font.bold: true
                                                font.family: "Segoe UI"
                                                color: "#475569"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.leftMargin: 24
                    Layout.rightMargin: 24
                    radius: 20
                    color: "#FFFFFF"
                    border.width: 1
                    border.color: "#E6EDF4"
                    implicitHeight: subjectColumn.implicitHeight + 30

                    ColumnLayout {
                        id: subjectColumn
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 12

                        Text {
                            text: "Subject Strength Distribution"
                            font.pixelSize: 17
                            font.bold: true
                            font.family: "Segoe UI"
                            color: "#0F172A"
                        }

                        Text {
                            text: "Confidence and mastery mix across subjects"
                            font.pixelSize: 11
                            font.family: "Segoe UI"
                            color: "#64748B"
                        }

                        Repeater {
                            model: subjectRows

                            delegate: ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 6

                                RowLayout {
                                    Layout.fillWidth: true

                                    Text {
                                        text: modelData.subject
                                        font.pixelSize: 11
                                        font.bold: true
                                        font.family: "Segoe UI"
                                        color: "#0F172A"
                                    }

                                    Item { Layout.fillWidth: true }

                                    Text {
                                        text: root.percentValue(modelData.pct)
                                        font.pixelSize: 10
                                        font.bold: true
                                        font.family: "Segoe UI"
                                        color: modelData.color
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    implicitHeight: 10
                                    radius: 5
                                    color: "#EDF2F7"

                                    Rectangle {
                                        width: parent.width * root.clampPercent(modelData.pct) / 100.0
                                        height: parent.height
                                        radius: parent.radius
                                        color: modelData.color
                                    }
                                }

                                Text {
                                    text: Math.round(modelData.progress || 0) + "% mastery across " + modelData.topicCount + " topic(s)"
                                    font.pixelSize: 10
                                    font.family: "Segoe UI"
                                    color: "#64748B"
                                }
                            }
                        }
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 24
                    Layout.rightMargin: 24
                    Layout.bottomMargin: 24
                    columns: width >= 1320 ? 3 : 1
                    rowSpacing: 16
                    columnSpacing: 16

                    Rectangle {
                        Layout.fillWidth: true
                        radius: 20
                        color: "#FFF7F7"
                        border.width: 1
                        border.color: "#F3C8C8"
                        implicitHeight: riskColumn.implicitHeight + 28

                        ColumnLayout {
                            id: riskColumn
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 12

                            Text {
                                text: "High Risk Topics"
                                font.pixelSize: 16
                                font.bold: true
                                font.family: "Segoe UI"
                                color: "#991B1B"
                            }

                            Text {
                                text: "Forgetting risk, urgency, and how long before retention slips"
                                font.pixelSize: 11
                                font.family: "Segoe UI"
                                color: "#7F1D1D"
                            }

                            Text {
                                visible: (dashboard.high_risk_topics || []).length === 0
                                text: "No high-risk topics yet."
                                font.pixelSize: 11
                                font.family: "Segoe UI"
                                color: "#94A3B8"
                            }

                            Repeater {
                                model: dashboard.high_risk_topics || []

                                delegate: IntelligenceTopicCard {
                                    Layout.fillWidth: true
                                    topicData: modelData
                                    mode: "risk"
                                    accentColor: "#EF4444"
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        radius: 20
                        color: "#FFF9F2"
                        border.width: 1
                        border.color: "#F6D7B8"
                        implicitHeight: focusColumn.implicitHeight + 28

                        ColumnLayout {
                            id: focusColumn
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 12

                            Text {
                                text: "Recommended Focus"
                                font.pixelSize: 16
                                font.bold: true
                                font.family: "Segoe UI"
                                color: "#9A3412"
                            }

                            Text {
                                text: "Expected score gain, priority, and estimated study time"
                                font.pixelSize: 11
                                font.family: "Segoe UI"
                                color: "#9A3412"
                            }

                            Text {
                                visible: (dashboard.recommended_topics || []).length === 0
                                text: "No focus recommendations yet."
                                font.pixelSize: 11
                                font.family: "Segoe UI"
                                color: "#94A3B8"
                            }

                            Repeater {
                                model: dashboard.recommended_topics || []

                                delegate: IntelligenceTopicCard {
                                    Layout.fillWidth: true
                                    topicData: modelData
                                    mode: "focus"
                                    accentColor: "#F59E0B"
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        radius: 20
                        color: "#F6F8FF"
                        border.width: 1
                        border.color: "#CFD9FF"
                        implicitHeight: weakColumn.implicitHeight + 28

                        ColumnLayout {
                            id: weakColumn
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 12

                            Text {
                                text: "Weak Topics"
                                font.pixelSize: 16
                                font.bold: true
                                font.family: "Segoe UI"
                                color: "#1D4ED8"
                            }

                            Text {
                                text: "Quiz accuracy, error frequency, and practice need"
                                font.pixelSize: 11
                                font.family: "Segoe UI"
                                color: "#1D4ED8"
                            }

                            Text {
                                visible: (dashboard.weak_topics || []).length === 0
                                text: "No weak-topic signals yet."
                                font.pixelSize: 11
                                font.family: "Segoe UI"
                                color: "#94A3B8"
                            }

                            Repeater {
                                model: dashboard.weak_topics || []

                                delegate: IntelligenceTopicCard {
                                    Layout.fillWidth: true
                                    topicData: modelData
                                    mode: "weak"
                                    accentColor: "#3B82F6"
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
