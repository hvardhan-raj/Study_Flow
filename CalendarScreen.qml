import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15

Rectangle {
    id: root
    color: "#F4F6FA"

    function safeText(value, fallback) {
        return value === undefined || value === null || value === "" ? fallback : String(value)
    }

    function selectedDateObject() {
        var dateText = (typeof backend !== "undefined") ? backend.selectedDate : ""
        var parsed = dateText ? new Date(dateText + "T00:00:00") : new Date()
        return isNaN(parsed.getTime()) ? new Date() : parsed
    }

    function monthLabel() {
        var explicitLabel = (typeof backend !== "undefined") ? backend.calendarMonthLabel : ""
        return safeText(explicitLabel, Qt.formatDate(selectedDateObject(), "MMMM yyyy"))
    }

    function dayLabel() {
        var explicitLabel = (typeof backend !== "undefined") ? backend.selectedDayLabel : ""
        return safeText(explicitLabel, Qt.formatDate(selectedDateObject(), "dddd, d MMMM"))
    }

    function sessionsList() {
        return (typeof backend !== "undefined" && backend.selectedDaySessions) ? backend.selectedDaySessions : []
    }

    function sessionCountLabel() {
        var sessions = sessionsList()
        return sessions.length + (sessions.length === 1 ? " session scheduled" : " sessions scheduled")
    }

    function sessionTime(session) {
        return safeText(session && session.time, "Study")
    }

    function sessionTopic(session) {
        return safeText(session && (session.topic || session.name || session.subject), "Study session")
    }

    function sessionSubject(session) {
        return safeText(session && session.subject, "General")
    }

    function sessionDuration(session) {
        if (session && session.duration !== undefined && session.duration !== null)
            return session.duration + " min"
        return safeText(session && session.durationText, "--")
    }

    function sessionColor(session) {
        return safeText(session && (session.color || session.subjectColor), "#3B82F6")
    }

    function totalTodayText() {
        var explicitText = (typeof backend !== "undefined") ? backend.selectedDayTotalText : ""
        if (explicitText !== undefined && explicitText !== null && explicitText !== "")
            return String(explicitText)

        var sessions = sessionsList()
        var total = 0
        for (var i = 0; i < sessions.length; ++i) {
            var duration = sessions[i] ? sessions[i].duration : 0
            total += Number(duration || 0)
        }
        return total + " min"
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        PageHeader {
            Layout.fillWidth: true
            pageTitle: "Calendar"
            pageSubtitle: "MONTHLY SESSION VIEW"
            rightContent: [
                AppButton { label: "Today"; variant: "secondary"; small: true; onClicked: backend.goToToday() },
                AppButton { label: "+ Add Session"; variant: "primary"; small: true }
            ]
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.margins: 24
                spacing: 14

                RowLayout {
                    Text {
                        text: "<"
                        font.pixelSize: 16; color: "#64748B"
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: backend.changeCalendarMonth(-1) }
                    }

                    Text {
                        text: root.monthLabel()
                        font.pixelSize: 18; font.bold: true; color: "#1A2332"
                        Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter
                    }

                    Text {
                        text: ">"
                        font.pixelSize: 16; color: "#64748B"
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: backend.changeCalendarMonth(1) }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 36
                    radius: 8
                    color: "#FFFFFF"
                    border.color: "#E2E8F0"

                    RowLayout {
                        anchors.fill: parent
                        spacing: 0
                        Repeater {
                            model: ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
                            Text { Layout.fillWidth: true; text: modelData; font.pixelSize: 11; font.bold: true; color: (index >= 5) ? "#EF4444" : "#94A3B8"; horizontalAlignment: Text.AlignHCenter }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 12
                    color: "#FFFFFF"
                    border.color: "#E2E8F0"
                    clip: true

                    Grid {
                        anchors.fill: parent
                        anchors.margins: 4
                        columns: 7
                        rows: 6
                        spacing: 2

                        Repeater {
                            model: backend.calendarCells

                            delegate: Item {
                                width: (parent.width - 12) / 7
                                height: (parent.height - 10) / 6
                                property int cellTaskCount: modelData.taskCount
                                property bool cellSelected: modelData.isSelected

                                Rectangle {
                                    anchors.fill: parent
                                    anchors.margins: 2
                                    radius: 8
                                    color: modelData.isSelected ? "#3B82F6" : (modelData.isToday ? "#EFF6FF" : "transparent")
                                    border.color: modelData.isToday && !modelData.isSelected ? "#BFDBFE" : "transparent"

                                    ColumnLayout {
                                        anchors { fill: parent; margins: 4 }
                                        spacing: 3

                                        Text {
                                            visible: modelData.isValid
                                            text: modelData.dayNum
                                            font.pixelSize: 13
                                            font.bold: modelData.isSelected || modelData.isToday
                                            color: modelData.isSelected ? "#FFFFFF" : (modelData.isToday ? "#3B82F6" : "#374151")
                                            Layout.alignment: Qt.AlignHCenter
                                        }

                                        Row {
                                            visible: modelData.isValid && modelData.taskCount > 0
                                            spacing: 2
                                            Layout.alignment: Qt.AlignHCenter

                                            Repeater {
                                                model: Math.min(cellTaskCount, 4)
                                                Rectangle { width: 5; height: 5; radius: 3; color: cellSelected ? "#BFDBFE" : ["#3B82F6","#10B981","#F59E0B","#EF4444"][index % 4] }
                                            }
                                        }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        enabled: modelData.isValid
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: backend.selectCalendarDay(modelData.dateStr)
                                    }
                                }
                            }
                        }
                    }
                }

                RowLayout {
                    spacing: 14
                    Repeater {
                        model: backend.calendarLegend
                        delegate: RowLayout {
                            spacing: 4
                            Rectangle { width: 8; height: 8; radius: 4; color: modelData.color }
                            Text { text: modelData.label; font.pixelSize: 10; color: "#64748B" }
                        }
                    }
                }
            }

            Rectangle {
                Layout.preferredWidth: 280
                Layout.fillHeight: true
                color: "#FFFFFF"
                border.color: "#E2E8F0"

                ColumnLayout {
                    anchors { fill: parent; margins: 20 }
                    spacing: 14

                    ColumnLayout {
                        spacing: 2
                        Text { text: root.dayLabel(); font.pixelSize: 18; font.bold: true; color: "#1A2332" }
                        Text { text: root.sessionCountLabel(); font.pixelSize: 11; color: "#94A3B8" }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: "#F1F5F9" }

                    Repeater {
                        model: backend.selectedDaySessions
                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Text { text: root.sessionTime(modelData); font.pixelSize: 11; color: "#94A3B8"; Layout.preferredWidth: 38 }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 52; radius: 8
                                color: Qt.rgba(parseInt(root.sessionColor(modelData).slice(1,3),16)/255, parseInt(root.sessionColor(modelData).slice(3,5),16)/255, parseInt(root.sessionColor(modelData).slice(5,7),16)/255, 0.08)

                                Rectangle { width: 3; height: 32; radius: 2; color: root.sessionColor(modelData); anchors { left: parent.left; verticalCenter: parent.verticalCenter } }

                                ColumnLayout {
                                    anchors { fill: parent; leftMargin: 12; rightMargin: 10 }
                                    spacing: 2
                                    Text { text: root.sessionTopic(modelData); font.pixelSize: 12; font.bold: true; color: "#1A2332"; elide: Text.ElideRight; Layout.fillWidth: true }
                                    RowLayout {
                                        spacing: 6
                                        Text { text: root.sessionSubject(modelData); font.pixelSize: 10; color: root.sessionColor(modelData) }
                                        Text { text: "."; font.pixelSize: 10; color: "#CBD5E1" }
                                        Text { text: root.sessionDuration(modelData); font.pixelSize: 10; color: "#94A3B8" }
                                    }
                                }
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }
                    AppButton { label: "+ Add Session"; variant: "primary"; Layout.fillWidth: true }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 40; radius: 8
                        color: "#F8FAFC"; border.color: "#E2E8F0"
                        RowLayout {
                            anchors { fill: parent; leftMargin: 12; rightMargin: 12 }
                            Text { text: "Total today:"; font.pixelSize: 11; color: "#64748B"; Layout.fillWidth: true }
                            Text { text: root.totalTodayText(); font.pixelSize: 13; font.bold: true; color: "#1A2332" }
                        }
                    }
                }
            }
        }
    }
}
