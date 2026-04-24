import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15

Rectangle {
    id: root
    color: "#F4F6FA"

    function sessionColor(session) {
        return session && (session.statusColor || session.color || session.subjectColor) ? (session.statusColor || session.color || session.subjectColor) : "#3B82F6"
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        PageHeader {
            Layout.fillWidth: true
            pageTitle: "Calendar"
            pageSubtitle: "MONTHLY SESSION VIEW"
            rightContent: [
                AppButton { label: "Today"; iconName: "calendar"; variant: "secondary"; small: true; onClicked: backend.goToToday() }
            ]
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: 24
            Layout.rightMargin: 24
            Layout.topMargin: 20
            Layout.bottomMargin: 24
            spacing: 16

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 18
                color: "#FFFFFF"
                border.color: "#E2E8F0"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 14

                    RowLayout {
                        Layout.fillWidth: true
                        AppButton { label: "<"; variant: "ghost"; iconName: ""; small: true; onClicked: backend.changeCalendarMonth(-1) }
                        Text { text: backend.calendarMonthLabel; font.pixelSize: 18; font.bold: true; color: "#1A2332"; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
                        AppButton { label: ">"; variant: "ghost"; iconName: ""; small: true; onClicked: backend.changeCalendarMonth(1) }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 7
                        columnSpacing: 8
                        rowSpacing: 8

                        Repeater {
                            model: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                            delegate: Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 28
                                radius: 10
                                color: "#F8FAFC"
                                border.color: "#E2E8F0"
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData
                                    font.pixelSize: 10
                                    font.bold: true
                                    color: index >= 5 ? "#EF4444" : "#94A3B8"
                                }
                            }
                        }

                        Repeater {
                            model: backend.calendarCells
                            delegate: Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 78
                                radius: 14
                                color: modelData.isSelected ? "#3B82F6" : (modelData.isToday ? "#EFF6FF" : "#F8FAFC")
                                border.color: modelData.isSelected ? "#3B82F6" : (modelData.isToday ? "#BFDBFE" : "#E2E8F0")
                                opacity: modelData.isValid ? 1.0 : 0.45

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    spacing: 5

                                    Text {
                                        visible: modelData.isValid
                                        text: modelData.dayNum
                                        font.pixelSize: 13
                                        font.bold: modelData.isToday || modelData.isSelected
                                        color: modelData.isSelected ? "#FFFFFF" : "#1A2332"
                                    }

                                    Row {
                                        visible: modelData.isValid && modelData.indicatorColors && modelData.indicatorColors.length > 0
                                        spacing: 3

                                        Repeater {
                                            model: modelData.indicatorColors || []
                                            delegate: Rectangle {
                                                width: 7
                                                height: 7
                                                radius: 3.5
                                                color: modelData
                                                border.color: parent.parent.parent.parent.modelData.isSelected ? "#FFFFFF" : "transparent"
                                                border.width: 1
                                            }
                                        }
                                    }

                                    Rectangle {
                                        visible: modelData.isValid && modelData.taskCount > 0
                                        implicitWidth: 24
                                        implicitHeight: 18
                                        radius: 9
                                        color: modelData.isSelected ? Qt.rgba(1, 1, 1, 0.16) : "#E2E8F0"

                                        Text {
                                            anchors.centerIn: parent
                                            text: modelData.taskCount
                                            font.pixelSize: 10
                                            font.bold: true
                                            color: modelData.isSelected ? "#FFFFFF" : "#334155"
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
            }

            Rectangle {
                Layout.preferredWidth: 320
                Layout.fillHeight: true
                radius: 18
                color: "#FFFFFF"
                border.color: "#E2E8F0"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 14

                    ColumnLayout {
                        spacing: 2
                        Text { text: backend.selectedDayLabel; font.pixelSize: 18; font.bold: true; color: "#1A2332" }
                        Text { text: backend.selectedDaySessions.length + (backend.selectedDaySessions.length === 1 ? " session scheduled" : " sessions scheduled"); font.pixelSize: 11; color: "#94A3B8" }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: "#F1F5F9" }

                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 10
                        model: backend.selectedDaySessions

                        delegate: Rectangle {
                            width: ListView.view.width
                            implicitHeight: 66
                            radius: 12
                            color: Qt.rgba(root.sessionColor(modelData).r, root.sessionColor(modelData).g, root.sessionColor(modelData).b, 0.08)
                            border.color: Qt.rgba(root.sessionColor(modelData).r, root.sessionColor(modelData).g, root.sessionColor(modelData).b, 0.16)

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 10

                                Rectangle { Layout.preferredWidth: 4; Layout.fillHeight: true; radius: 2; color: root.sessionColor(modelData) }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 3

                                    Text { text: modelData.topic; font.pixelSize: 12; font.bold: true; color: "#1A2332"; Layout.fillWidth: true; elide: Text.ElideRight }

                                    RowLayout {
                                        spacing: 6
                                        Text { text: modelData.subject; font.pixelSize: 10; color: modelData.color }
                                        Text { text: "•"; font.pixelSize: 10; color: "#CBD5E1" }
                                        Text { text: modelData.time + " • " + modelData.durationText; font.pixelSize: 10; color: "#94A3B8" }
                                    }
                                }

                                TagPill {
                                    tagText: modelData.completed ? "Done" : modelData.status
                                    tagColor: modelData.completed ? "#10B981" : root.sessionColor(modelData)
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 40
                        radius: 10
                        color: "#F8FAFC"
                        border.color: "#E2E8F0"

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            Text { text: "Total today:"; font.pixelSize: 11; color: "#64748B"; Layout.fillWidth: true }
                            Text { text: backend.selectedDayTotalText; font.pixelSize: 13; font.bold: true; color: "#1A2332" }
                        }
                    }
                }
            }
        }
    }
}
