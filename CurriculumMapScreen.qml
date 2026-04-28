import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#F4F6FA"

    property string editingTopicId: ""
    property string editingParentId: ""
    property string deletingSubjectId: ""
    property string deletingSubjectName: ""

    function openSubjectDialog() {
        subjectNameField.text = ""
        addSubjectDialog.open()
    }

    function openTopicDialog(topicId, parentId, subjectName) {
        editingTopicId = topicId || ""
        editingParentId = parentId || ""
        var topic = findTopicById(topicId)
        topicNameField.text = topic ? topic.name : ""
        var desiredSubjectId = topic ? topic.subjectId : (subjectName || (backend.curriculumSubjectOptions.length > 0 ? backend.curriculumSubjectOptions[0].id : ""))
        var targetIndex = 0
        for (var i = 0; i < backend.curriculumSubjectOptions.length; ++i) {
            if (backend.curriculumSubjectOptions[i].id === desiredSubjectId) {
                targetIndex = i
                break
            }
        }
        topicSubjectBox.currentIndex = targetIndex
        topicDifficultyBox.currentIndex = ["Easy", "Medium", "Hard"].indexOf(topic ? topic.difficulty : "Medium")
        topicNotesField.text = topic ? (topic.notes || "") : ""
        suggestionBadge.text = ""
        topicDialog.open()
    }

    function findTopicById(topicId) {
        for (var i = 0; i < backend.curriculumSubjects.length; ++i) {
            var roots = backend.curriculumSubjects[i].topics || []
            var found = findInNodes(roots, topicId)
            if (found)
                return found
        }
        return null
    }

    function findInNodes(nodes, topicId) {
        for (var i = 0; i < nodes.length; ++i) {
            if (nodes[i].id === topicId)
                return nodes[i]
            var nested = findInNodes(nodes[i].children || [], topicId)
            if (nested)
                return nested
        }
        return null
    }

    function confirmDeleteSubject(subjectId, subjectName) {
        deletingSubjectId = subjectId || ""
        deletingSubjectName = subjectName || ""
        deleteSubjectDialog.open()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        PageHeader {
            Layout.fillWidth: true
            pageTitle: "Topic Manager"
            pageSubtitle: "HIERARCHY, BULK IMPORT, AND NLP SUGGESTIONS"
            rightContent: [
                AppButton { label: "Import"; iconName: "refresh"; variant: "secondary"; small: true; onClicked: importDialog.open() },
                AppButton { label: "Add Subject"; iconName: "check"; variant: "secondary"; small: true; onClicked: root.openSubjectDialog() },
                AppButton { label: "Add Topic"; iconName: "review"; variant: "primary"; small: true; onClicked: root.openTopicDialog("", "", "") }
            ]
        }

        Rectangle {
            Layout.fillWidth: true
            color: "#FFFFFF"
            border.color: "#E2E8F0"
            implicitHeight: toolbarRow.implicitHeight + 24

            RowLayout {
                id: toolbarRow
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10

                TextField {
                    id: searchField
                    Layout.preferredWidth: 260
                    placeholderText: "Search topics or subjects"
                    text: backend.curriculumSearch
                    onTextChanged: backend.setCurriculumSearch(text)
                }

                Repeater {
                    model: ["All", "Easy", "Medium", "Hard"]
                    delegate: Rectangle {
                        property bool selected: modelData === backend.curriculumDifficulty
                        radius: 16
                        implicitWidth: filterLabel.implicitWidth + 22
                        implicitHeight: 30
                        color: selected ? "#3B82F6" : "#F8FAFC"
                        border.width: 1
                        border.color: selected ? "#3B82F6" : "#E2E8F0"

                        Text {
                            id: filterLabel
                            anchors.centerIn: parent
                            text: modelData
                            font.pixelSize: 11
                            font.bold: selected
                            color: selected ? "#FFFFFF" : "#64748B"
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: backend.setCurriculumDifficulty(modelData)
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                Repeater {
                    model: backend.curriculumSummary.stats || []
                    delegate: Rectangle {
                        radius: 14
                        color: Qt.rgba(modelData.color.r, modelData.color.g, modelData.color.b, 0.10)
                        implicitWidth: statLabel.implicitWidth + statValue.implicitWidth + 26
                        implicitHeight: 28

                        Row {
                            anchors.centerIn: parent
                            spacing: 6
                            Text { id: statLabel; text: modelData.label; font.pixelSize: 10; color: "#64748B" }
                            Text { id: statValue; text: modelData.value; font.pixelSize: 10; font.bold: true; color: modelData.color }
                        }
                    }
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
                spacing: 14

                Repeater {
                    model: backend.curriculumSubjects
                    delegate: Rectangle {
                        property var subjectData: modelData
                        Layout.fillWidth: true
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        radius: 20
                        color: "#FFFFFF"
                        border.width: 1
                        border.color: Qt.rgba(subjectData.accentColor.r, subjectData.accentColor.g, subjectData.accentColor.b, 0.16)
                        implicitHeight: subjectColumn.implicitHeight + 28

                        ColumnLayout {
                            id: subjectColumn
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10

                                Rectangle {
                                    width: 34
                                    height: 34
                                    radius: 10
                                    color: Qt.rgba(subjectData.accentColor.r, subjectData.accentColor.g, subjectData.accentColor.b, 0.14)
                                    border.width: 1
                                    border.color: Qt.rgba(subjectData.accentColor.r, subjectData.accentColor.g, subjectData.accentColor.b, 0.26)

                                    Text {
                                        anchors.centerIn: parent
                                        text: (subjectData.iconText && subjectData.iconText.length > 0)
                                            ? subjectData.iconText
                                            : String(subjectData.subjectName || "?").slice(0, 2).toUpperCase()
                                        font.pixelSize: 12
                                        font.bold: true
                                        color: "#0F172A"
                                    }
                                }

                                ColumnLayout {
                                    spacing: 2
                                    Text { text: subjectData.subjectName; font.pixelSize: 15; font.bold: true; color: "#1A2332" }
                                    Text { text: subjectData.topicCount + " topics"; font.pixelSize: 10; color: "#94A3B8" }
                                }

                                Item { Layout.fillWidth: true }

                                AppButton {
                                    label: "+ Topic"
                                    variant: "secondary"
                                    small: true
                                    onClicked: root.openTopicDialog("", "", subjectData.subjectId)
                                }
                                AppButton {
                                    label: "Delete"
                                    variant: "danger"
                                    small: true
                                    onClicked: root.confirmDeleteSubject(subjectData.subjectId, subjectData.subjectName)
                                }
                            }

                            Repeater {
                                model: subjectData.topics
                                delegate: TopicTreeCard {
                                    Layout.fillWidth: true
                                    nodeData: modelData
                                    accentColor: subjectData.accentColor
                                    onRequestEdit: function(topicId) { root.openTopicDialog(topicId, "", nodeData.subject) }
                                    onRequestAddChild: function(topicId, subjectName) { root.openTopicDialog("", topicId, subjectName) }
                                }
                            }
                        }
                    }
                }

                Item {
                    visible: backend.curriculumSubjects.length === 0
                    Layout.fillWidth: true
                    implicitHeight: 220

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 8
                        Text { text: "No topics match this view"; font.pixelSize: 15; font.bold: true; color: "#1A2332" }
                        Text { text: "Try a different filter, or add/import topics to begin."; font.pixelSize: 11; color: "#94A3B8" }
                    }
                }

                Item { height: 16 }
            }
        }
    }

    RoundedDialog {
        id: deleteSubjectDialog
        width: 380
        title: "Delete Subject"
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            if (root.deletingSubjectId.length > 0) {
                backend.deleteSubject(root.deletingSubjectId)
            }
            root.deletingSubjectId = ""
            root.deletingSubjectName = ""
        }
        onRejected: {
            root.deletingSubjectId = ""
            root.deletingSubjectName = ""
        }

        ColumnLayout {
            anchors.fill: parent
            spacing: 10

            Text {
                Layout.fillWidth: true
                text: "Delete \"" + root.deletingSubjectName + "\" and all its topics?"
                wrapMode: Text.WordWrap
                font.pixelSize: 13
                font.bold: true
                color: "#1A2332"
            }

            Text {
                Layout.fillWidth: true
                text: "This removes the subject, its topics, and their revision history from the local database."
                wrapMode: Text.WordWrap
                font.pixelSize: 11
                color: "#64748B"
            }
        }
    }

    RoundedDialog {
        id: addSubjectDialog
        width: 380
        title: "Add Subject"
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: backend.addSubject(subjectNameField.text, "")

        ColumnLayout {
            anchors.fill: parent
            spacing: 12

            TextField {
                id: subjectNameField
                Layout.fillWidth: true
                placeholderText: "Subject name"
            }

            Text {
                Layout.fillWidth: true
                text: "StudyFlow will assign a unique pastel color automatically."
                wrapMode: Text.WordWrap
                font.pixelSize: 10
                color: "#64748B"
            }
        }
    }

    RoundedDialog {
        id: topicDialog
        width: 420
        title: editingTopicId ? "Edit Topic" : "Add Topic"
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: backend.upsertTopic(
            editingTopicId,
            topicNameField.text,
            topicSubjectBox.currentValue,
            topicDifficultyBox.currentText,
            editingParentId,
            topicNotesField.text
        )

        ColumnLayout {
            anchors.fill: parent
            spacing: 10

            TextField {
                id: topicNameField
                Layout.fillWidth: true
                placeholderText: "Topic name"
                onEditingFinished: {
                    var suggestion = backend.suggestTopicDifficulty(text)
                    if (suggestion.difficulty) {
                        topicDifficultyBox.currentIndex = ["Easy", "Medium", "Hard"].indexOf(suggestion.difficulty)
                        suggestionBadge.text = "Suggested " + suggestion.difficulty + " (" + Math.round(suggestion.confidence * 100) + "%)"
                    } else if (text.length > 0) {
                        suggestionBadge.text = "No strong suggestion yet"
                    }
                }
            }

            ComboBox {
                id: topicSubjectBox
                Layout.fillWidth: true
                model: backend.curriculumSubjectOptions
                textRole: "name"
                valueRole: "id"
            }

            ComboBox {
                id: topicDifficultyBox
                Layout.fillWidth: true
                model: ["Easy", "Medium", "Hard"]
            }

            Text {
                id: suggestionBadge
                Layout.fillWidth: true
                color: "#3B82F6"
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }

            TextArea {
                id: topicNotesField
                Layout.fillWidth: true
                Layout.preferredHeight: 100
                placeholderText: "Notes"
                wrapMode: TextEdit.WordWrap
            }
        }
    }

    RoundedDialog {
        id: importDialog
        width: 520
        title: "Bulk Import Topics"
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: backend.importTopics(importText.text, importSubjectBox.currentValue, csvModeCheck.checked)

        ColumnLayout {
            anchors.fill: parent
            spacing: 10

            ComboBox {
                id: importSubjectBox
                Layout.fillWidth: true
                model: backend.curriculumSubjectOptions
                textRole: "name"
                valueRole: "id"
            }

            CheckBox {
                id: csvModeCheck
                text: "Treat input as CSV rows"
            }

            Text {
                Layout.fillWidth: true
                text: csvModeCheck.checked
                    ? "CSV format: topic or subject,topic,difficulty. Header rows like subject,topic,difficulty are also supported. Missing subjects will be created automatically."
                    : "Line format: one topic per line, or Subject | Topic | Difficulty."
                wrapMode: Text.WordWrap
                font.pixelSize: 10
                color: "#64748B"
            }

            TextArea {
                id: importText
                Layout.fillWidth: true
                Layout.preferredHeight: 180
                placeholderText: csvModeCheck.checked
                    ? "subject,topic,difficulty\nPhysics,Wave Optics,Hard\nChemistry,Hydrocarbons,Medium"
                    : "Physics | Wave Optics | Hard\nChemistry | Hydrocarbons | Medium\nStandalone Topic"
                wrapMode: TextEdit.WordWrap
            }
        }
    }
}
