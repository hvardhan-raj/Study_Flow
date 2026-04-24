import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15

Rectangle {
    id: root
    color: "#F4F6FA"

    property var backendRef: (typeof backend !== "undefined" && backend !== null) ? backend : null
    property var monthCells: backendRef ? backendRef.calendarCells : []
    property var selectedSessions: backendRef ? backendRef.selectedDaySessions : []
    property var dueSoon: backendRef ? backendRef.upcomingReminders : []
    property var weekRows: backendRef ? backendRef.weekCompletion : []
    property var weekSummary: backendRef ? backendRef.revisionWeekSummary : ({ score: 0, completed: 0, remaining: 0, missed: 0, scheduled: 0 })
    property string monthLabel: backendRef ? backendRef.calendarMonthLabel : "Revision Schedule"
    property string dayLabel: backendRef ? backendRef.selectedDayLabel : "Select a day"
    property string totalText: backendRef ? backendRef.selectedDayTotalText : "0 min"

    function sessionCardColor(session) {
        if (!session)
            return "#3B82F6"
        return session.color || session.subjectColor || "#3B82F6"
    }

    function sessionBgColor(session) {
        var accent = sessionCardColor(session)
        return Qt.rgba(accent.r, accent.g, accent.b, 0.08)
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        PageHeader {
            Layout.fillWidth: true
            pageTitle: "Revision Schedule"
            pageSubtitle: "CALENDAR, DUE SESSIONS, AND WEEKLY LOAD"
            rightContent: [
                AppButton { label: "Today"; variant: "secondary"; small: true; onClicked: if (root.backendRef) root.backendRef.goToToday() }
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
                    Layout.topMargin: 20
                    spacing: 16

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 3
                        radius: 18
                        color: "#FFFFFF"
                        border.color: "#E2E8F0"
                        implicitHeight: calendarPanel.implicitHeight + 36

                        ColumnLayout {
                            id: calendarPanel
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 14

                            RowLayout {
                                Layout.fillWidth: true

                                AppButton {
                                    label: "<"
                                    variant: "ghost"
                                    small: true
                                    onClicked: if (root.backendRef) root.backendRef.changeCalendarMonth(-1)
                                }

                                Text {
                                    text: root.monthLabel
                                    font.pixelSize: 17
                                    font.bold: true
                                    color: "#0F172A"
                                    Layout.fillWidth: true
                                    horizontalAlignment: Text.AlignHCenter
                                }

                                AppButton {
                                    label: ">"
                                    variant: "ghost"
                                    small: true
                                    onClicked: if (root.backendRef) root.backendRef.changeCalendarMonth(1)
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8

                                Repeater {
                                    model: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                                    delegate: Text {
                                        Layout.fillWidth: true
                                        text: modelData
                                        font.pixelSize: 10
                                        font.bold: true
                                        color: "#94A3B8"
                                        horizontalAlignment: Text.AlignHCenter
                                    }
                                }
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: 7
                                columnSpacing: 8
                                rowSpacing: 8

                                Repeater {
                                    model: root.monthCells

                                    delegate: Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 74
                                        radius: 12
                                        color: modelData.isSelected ? "#3B82F6" : (modelData.isToday ? "#EFF6FF" : "#F8FAFC")
                                        border.color: modelData.isSelected ? "#3B82F6" : (modelData.isToday ? "#BFDBFE" : "#E2E8F0")
                                        opacity: modelData.isValid ? 1.0 : 0.5

                                        ColumnLayout {
                                            anchors.fill: parent
                                            anchors.margins: 8
                                            spacing: 4

                                            Text {
                                                text: modelData.dayNum
                                                visible: modelData.isValid
                                                font.pixelSize: 13
                                                font.bold: modelData.isToday || modelData.isSelected
                                                color: modelData.isSelected ? "#FFFFFF" : "#1A2332"
                                            }

                                            Rectangle {
                                                visible: modelData.taskCount > 0 && modelData.isValid
                                                implicitWidth: 22
                                                implicitHeight: 18
                                                radius: 9
                                                color: modelData.isSelected ? Qt.rgba(1, 1, 1, 0.18) : "#DBEAFE"

                                                Text {
                                                    anchors.centerIn: parent
                                                    text: modelData.taskCount
                                                    font.pixelSize: 10
                                                    font.bold: true
                                                    color: modelData.isSelected ? "#FFFFFF" : "#2563EB"
                                                }
                                            }

                                            Item { Layout.fillHeight: true }
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            enabled: modelData.isValid && root.backendRef
                                            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                            onClicked: root.backendRef.selectCalendarDay(modelData.dateStr)
                                        }
                                    }
                                }
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 2
                        spacing: 16

                        Rectangle {
                            Layout.fillWidth: true
                            radius: 18
                            color: "#FFFFFF"
                            border.color: "#E2E8F0"
                            implicitHeight: selectedPanel.implicitHeight + 34

                            ColumnLayout {
                                id: selectedPanel
                                anchors.fill: parent
                                anchors.margins: 18
                                spacing: 12

                                RowLayout {
                                    Layout.fillWidth: true
                                    Text {
                                        text: root.dayLabel
                                        font.pixelSize: 16
                                        font.bold: true
                                        color: "#0F172A"
                                        Layout.fillWidth: true
                                    }
                                    TagPill {
                                        tagText: root.selectedSessions.length + (root.selectedSessions.length === 1 ? " session" : " sessions")
                                        tagColor: "#3B82F6"
                                    }
                                }

                                Repeater {
                                    model: root.selectedSessions

                                    delegate: Rectangle {
                                        Layout.fillWidth: true
                                        implicitHeight: 64
                                        radius: 12
                                        color: root.sessionBgColor(modelData)
                                        border.color: Qt.rgba(root.sessionCardColor(modelData).r, root.sessionCardColor(modelData).g, root.sessionCardColor(modelData).b, 0.16)

                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.margins: 12
                                            spacing: 10

                                            Rectangle {
                                                Layout.preferredWidth: 4
                                                Layout.fillHeight: true
                                                radius: 2
                                                color: root.sessionCardColor(modelData)
                                            }

                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 3

                                                Text {
                                                    text: modelData.topic
                                                    font.pixelSize: 12
                                                    font.bold: true
                                                    color: "#0F172A"
                                                    elide: Text.ElideRight
                                                    Layout.fillWidth: true
                                                }

                                                RowLayout {
                                                    spacing: 6

                                                    Text { text: modelData.subject; font.pixelSize: 10; color: root.sessionCardColor(modelData) }
                                                    Text { text: modelData.time; font.pixelSize: 10; color: "#64748B" }
                                                    Text { text: modelData.durationText; font.pixelSize: 10; color: "#94A3B8" }
                                                }
                                            }

                                            TagPill {
                                                tagText: modelData.completed ? "Done" : modelData.status
                                                tagColor: modelData.completed ? "#10B981" : root.sessionCardColor(modelData)
                                            }
                                        }
                                    }
                                }

                                Text {
                                    visible: root.selectedSessions.length === 0
                                    text: "No sessions planned for this day."
                                    font.pixelSize: 11
                                    color: "#94A3B8"
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    implicitHeight: 42
                                    radius: 10
                                    color: "#F8FAFC"
                                    border.color: "#E2E8F0"

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 12
                                        anchors.rightMargin: 12
                                        Text { text: "Total scheduled"; font.pixelSize: 11; color: "#64748B"; Layout.fillWidth: true }
                                        Text { text: root.totalText; font.pixelSize: 12; font.bold: true; color: "#0F172A" }
                                    }
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 16

                            Rectangle {
                                Layout.fillWidth: true
                                radius: 18
                                color: "#FFFFFF"
                                border.color: "#E2E8F0"
                                implicitHeight: weekPanel.implicitHeight + 34

                                ColumnLayout {
                                    id: weekPanel
                                    anchors.fill: parent
                                    anchors.margins: 18
                                    spacing: 10

                                    RowLayout {
                                        Layout.fillWidth: true
                                        Text { text: "This Week"; font.pixelSize: 15; font.bold: true; color: "#0F172A"; Layout.fillWidth: true }
                                        TagPill { tagText: root.weekSummary.score + "% complete"; tagColor: "#10B981" }
                                    }

                                    Repeater {
                                        model: root.weekRows
                                        delegate: RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 8

                                            Text {
                                                text: modelData.day
                                                font.pixelSize: 11
                                                font.bold: modelData.isToday
                                                color: modelData.isToday ? "#2563EB" : "#64748B"
                                                Layout.preferredWidth: 30
                                            }

                                            Rectangle {
                                                Layout.fillWidth: true
                                                implicitHeight: 8
                                                radius: 4
                                                color: "#E2E8F0"

                                                Rectangle {
                                                    width: parent.width * (modelData.scheduled > 0 ? modelData.completed / modelData.scheduled : 0)
                                                    height: parent.height
                                                    radius: 4
                                                    color: modelData.completed === modelData.scheduled && modelData.scheduled > 0 ? "#10B981" : "#3B82F6"
                                                }
                                            }

                                            Text {
                                                text: modelData.completed + "/" + modelData.scheduled
                                                font.pixelSize: 10
                                                color: "#94A3B8"
                                            }
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                radius: 18
                                color: "#FFFFFF"
                                border.color: "#E2E8F0"
                                implicitHeight: duePanel.implicitHeight + 34

                                ColumnLayout {
                                    id: duePanel
                                    anchors.fill: parent
                                    anchors.margins: 18
                                    spacing: 10

                                    Text { text: "Next Due"; font.pixelSize: 15; font.bold: true; color: "#0F172A" }

                                    Repeater {
                                        model: root.dueSoon
                                        delegate: RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 8

                                            Rectangle {
                                                Layout.preferredWidth: 8
                                                Layout.preferredHeight: 8
                                                radius: 4
                                                color: modelData.color
                                            }

                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 2
                                                Text {
                                                    text: modelData.title
                                                    font.pixelSize: 11
                                                    font.bold: true
                                                    color: "#0F172A"
                                                    elide: Text.ElideRight
                                                    Layout.fillWidth: true
                                                }
                                                Text {
                                                    text: modelData.subject + " • " + modelData.when
                                                    font.pixelSize: 10
                                                    color: "#94A3B8"
                                                    elide: Text.ElideRight
                                                    Layout.fillWidth: true
                                                }
                                            }
                                        }
                                    }

                                    Text {
                                        visible: root.dueSoon.length === 0
                                        text: "No upcoming sessions."
                                        font.pixelSize: 11
                                        color: "#94A3B8"
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
                    Layout.bottomMargin: 24
                    radius: 18
                    color: "#FFFFFF"
                    border.color: "#E2E8F0"
                    implicitHeight: summaryRow.implicitHeight + 32

                    RowLayout {
                        id: summaryRow
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 14

                        Repeater {
                            model: [
                                { label: "Completed", value: root.weekSummary.completed, color: "#10B981" },
                                { label: "Remaining", value: root.weekSummary.remaining, color: "#F59E0B" },
                                { label: "Missed", value: root.weekSummary.missed, color: "#EF4444" },
                                { label: "Scheduled", value: root.weekSummary.scheduled, color: "#3B82F6" }
                            ]

                            delegate: Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: 62
                                radius: 14
                                color: Qt.rgba(modelData.color.r, modelData.color.g, modelData.color.b, 0.08)
                                border.color: Qt.rgba(modelData.color.r, modelData.color.g, modelData.color.b, 0.14)

                                Column {
                                    anchors.centerIn: parent
                                    spacing: 4
                                    Text { text: modelData.value; font.pixelSize: 18; font.bold: true; color: "#0F172A"; horizontalAlignment: Text.AlignHCenter }
                                    Text { text: modelData.label; font.pixelSize: 10; color: modelData.color; horizontalAlignment: Text.AlignHCenter }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
