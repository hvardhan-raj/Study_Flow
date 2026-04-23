import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15

Rectangle {
    id: root
    color: "#F4F6FA"
    property bool composerOpen: false
    readonly property int difficultyColWidth: 110
    readonly property int scheduledColWidth: 130
    readonly property int confidenceColWidth: 100
    readonly property int statusColWidth: 100
    readonly property int actionsColWidth: 150

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        PageHeader {
            Layout.fillWidth: true
            pageTitle: "Task Inbox"
            pageSubtitle: "PENDING REVISIONS"
            rightContent: [
                AppButton { label: "Mark All Done"; variant: "secondary"; small: true; onClicked: backend.markAllTasksDone() },
                AppButton {
                    label: root.composerOpen ? "Close" : "+ Add Task"
                    variant: "primary"
                    small: true
                    onClicked: root.composerOpen = !root.composerOpen
                }
            ]
        }

        Rectangle {
            visible: root.composerOpen
            Layout.fillWidth: true
            implicitHeight: composerLayout.implicitHeight + 28
            color: "#FFFFFF"
            border.color: "#E2E8F0"

            ColumnLayout {
                id: composerLayout
                anchors.fill: parent
                anchors.margins: 14
                spacing: 12

                Text {
                    text: "Create A Task"
                    font.pixelSize: 13
                    font.bold: true
                    color: "#0F172A"
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 36
                        radius: 10
                        color: "#F8FAFC"
                        border.color: taskNameField.activeFocus ? "#93C5FD" : "#DDE4EF"

                        TextField {
                            id: taskNameField
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            placeholderText: "Topic or task name"
                            font.pixelSize: 12
                            background: Item {}
                        }
                    }

                    ComboBox {
                        id: subjectBox
                        Layout.preferredWidth: 160
                        model: backend.curriculumSubjectOptions
                        textRole: "name"
                        valueRole: "id"
                    }

                    ComboBox {
                        id: difficultyBox
                        Layout.preferredWidth: 120
                        model: ["Easy", "Medium", "Hard"]
                    }

                    ComboBox {
                        id: scheduleBox
                        Layout.preferredWidth: 130
                        textRole: "label"
                        valueRole: "key"
                        model: [
                            { label: "Today", key: "today" },
                            { label: "Tomorrow", key: "tomorrow" },
                            { label: "This Week", key: "this_week" },
                            { label: "Overdue", key: "overdue" }
                        ]
                    }

                    AppButton {
                        label: "Create"
                        variant: "primary"
                        enabled: taskNameField.text.trim().length > 0
                        onClicked: {
                            backend.addTask(
                                taskNameField.text,
                                subjectBox.currentValue,
                                difficultyBox.currentText,
                                scheduleBox.currentValue
                            )
                            taskNameField.text = ""
                            difficultyBox.currentIndex = 1
                            scheduleBox.currentIndex = 0
                            root.composerOpen = false
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 44
            color: "#FFFFFF"
            border.color: "#E2E8F0"

            RowLayout {
                anchors { fill: parent; leftMargin: 24 }
                spacing: 0

                Repeater {
                    model: backend.taskFilters
                    delegate: Item {
                        height: 44
                        implicitWidth: tabLbl.implicitWidth + countLbl.implicitWidth + 40

                        Rectangle { visible: modelData.active; anchors.bottom: parent.bottom; width: parent.width; height: 2; color: "#3B82F6" }

                        Row {
                            anchors.centerIn: parent
                            spacing: 6

                            Text {
                                id: tabLbl
                                text: modelData.label
                                font.pixelSize: 12
                                font.bold: modelData.active
                                color: modelData.active ? "#3B82F6" : "#64748B"
                            }

                            Text {
                                id: countLbl
                                text: "(" + modelData.count + ")"
                                font.pixelSize: 11
                                color: modelData.active ? "#3B82F6" : "#94A3B8"
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: backend.setTaskFilter(modelData.key)
                        }
                    }
                }

                Item { Layout.fillWidth: true }
                Text {
                    text: backend.inboxTasks.length + " tasks"
                    font.pixelSize: 11
                    color: "#64748B"
                    Layout.rightMargin: 24
                    Layout.alignment: Qt.AlignVCenter
                }
            }
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            clip: true

            ColumnLayout {
                width: parent.width
                spacing: 0

                Rectangle {
                    Layout.fillWidth: true
                    height: 36
                    color: "#F8FAFC"
                    border.color: "#E2E8F0"

                    RowLayout {
                        anchors { fill: parent; leftMargin: 24; rightMargin: 24 }
                        spacing: 12

                        Text {
                            Layout.fillWidth: true
                            text: "TOPIC / SUBJECT"
                            font.pixelSize: 9
                            font.letterSpacing: 1
                            color: "#94A3B8"
                        }
                        Text {
                            Layout.preferredWidth: root.difficultyColWidth
                            text: "DIFFICULTY"
                            font.pixelSize: 9
                            font.letterSpacing: 1
                            color: "#94A3B8"
                        }
                        Text {
                            Layout.preferredWidth: root.scheduledColWidth
                            text: "SCHEDULED"
                            font.pixelSize: 9
                            font.letterSpacing: 1
                            color: "#94A3B8"
                        }
                        Text {
                            Layout.preferredWidth: root.confidenceColWidth
                            text: "CONFIDENCE"
                            font.pixelSize: 9
                            font.letterSpacing: 1
                            color: "#94A3B8"
                        }
                        Text {
                            Layout.preferredWidth: root.statusColWidth
                            text: "STATUS"
                            font.pixelSize: 9
                            font.letterSpacing: 1
                            color: "#94A3B8"
                        }
                        Text {
                            Layout.preferredWidth: root.actionsColWidth
                            horizontalAlignment: Text.AlignHCenter
                            text: "ACTIONS"
                            font.pixelSize: 9
                            font.letterSpacing: 1
                            color: "#94A3B8"
                        }
                    }
                }

                Repeater {
                    model: backend.inboxTasks

                    delegate: Rectangle {
                        property int taskConfidence: modelData.confidence
                        Layout.fillWidth: true
                        height: 66
                        color: index % 2 === 0 ? "#FFFFFF" : "#FAFBFD"
                        border.color: "#F1F5F9"

                        RowLayout {
                            anchors { fill: parent; leftMargin: 24; rightMargin: 24 }
                            spacing: 12

                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignVCenter
                                spacing: 2
                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.topic
                                    font.pixelSize: 12
                                    font.bold: true
                                    color: "#1A2332"
                                    elide: Text.ElideRight
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.subject
                                    font.pixelSize: 10
                                    color: modelData.subjectColor
                                    elide: Text.ElideRight
                                }
                            }

                            TagPill {
                                Layout.preferredWidth: root.difficultyColWidth
                                Layout.alignment: Qt.AlignVCenter
                                tagText: modelData.difficulty
                                tagColor: modelData.difficultyColor
                            }
                            Text {
                                Layout.preferredWidth: root.scheduledColWidth
                                Layout.alignment: Qt.AlignVCenter
                                text: modelData.scheduledText
                                font.pixelSize: 11
                                color: "#64748B"
                                elide: Text.ElideRight
                            }

                            Row {
                                Layout.preferredWidth: root.confidenceColWidth
                                Layout.alignment: Qt.AlignVCenter
                                spacing: 2
                                Repeater {
                                    model: 5
                                    Text { text: "*"; font.pixelSize: 12; color: index < taskConfidence ? "#F59E0B" : "#E2E8F0" }
                                }
                            }

                            TagPill {
                                Layout.preferredWidth: root.statusColWidth
                                Layout.alignment: Qt.AlignVCenter
                                tagText: modelData.status
                                tagColor: modelData.statusColor
                            }

                            RowLayout {
                                Layout.preferredWidth: root.actionsColWidth
                                Layout.alignment: Qt.AlignVCenter
                                spacing: 6
                                AppButton { label: "Review"; variant: "primary"; small: true; onClicked: backend.markTaskDone(modelData.id) }
                                AppButton { label: "Skip"; variant: "secondary"; small: true; onClicked: backend.skipTask(modelData.id) }
                            }
                        }
                    }
                }

                Rectangle {
                    visible: backend.inboxTasks.length === 0
                    Layout.fillWidth: true
                    implicitHeight: 140
                    color: "transparent"

                    Column {
                        anchors.centerIn: parent
                        spacing: 6

                        Text {
                            text: "No tasks in this view"
                            font.pixelSize: 14
                            font.bold: true
                            color: "#0F172A"
                            horizontalAlignment: Text.AlignHCenter
                        }

                        Text {
                            text: "Add a task or switch filters to see the rest of your revision queue."
                            font.pixelSize: 11
                            color: "#64748B"
                            horizontalAlignment: Text.AlignHCenter
                        }
                    }
                }
            }
        }
    }
}
