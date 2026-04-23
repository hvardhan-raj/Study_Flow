import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property var nodeData: ({})
    property color accentColor: "#3B82F6"
    property int depth: 0
    signal requestEdit(string topicId)
    signal requestAddChild(string topicId, string subjectName)

    implicitHeight: contentColumn.implicitHeight

    ColumnLayout {
        id: contentColumn
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 10

        Rectangle {
            Layout.fillWidth: true
            radius: 14
            color: "#FFFFFF"
            border.width: 1
            border.color: Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.18)
            implicitHeight: cardColumn.implicitHeight + 24
            Layout.leftMargin: depth * 18

            ColumnLayout {
                id: cardColumn
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Rectangle {
                        width: 8
                        height: 8
                        radius: 4
                        color: accentColor
                    }

                    Text {
                        Layout.fillWidth: true
                        text: nodeData.name || ""
                        font.pixelSize: 13
                        font.bold: true
                        color: "#1A2332"
                        wrapMode: Text.WordWrap
                    }

                    TagPill {
                        tagText: nodeData.difficulty || ""
                        tagColor: nodeData.difficultyColor || accentColor
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Text {
                        text: "Progress " + (nodeData.progress || 0) + "%"
                        font.pixelSize: 10
                        color: "#64748B"
                    }

                    Text {
                        text: "Confidence " + (nodeData.confidence || 0) + "/5"
                        font.pixelSize: 10
                        color: "#64748B"
                    }

                    Item { Layout.fillWidth: true }

                    Text {
                        text: nodeData.examDate ? "Exam " + nodeData.examDate : ""
                        visible: text.length > 0
                        font.pixelSize: 10
                        color: "#94A3B8"
                    }
                }

                Text {
                    Layout.fillWidth: true
                    visible: (nodeData.notes || "").length > 0
                    text: nodeData.notes || ""
                    font.pixelSize: 10
                    color: "#64748B"
                    wrapMode: Text.WordWrap
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6

                    AppButton {
                        label: nodeData.isCompleted ? "Completed" : "Mark Complete"
                        variant: nodeData.isCompleted ? "secondary" : "primary"
                        small: true
                        onClicked: backend.markTopicComplete(nodeData.id)
                    }

                    AppButton {
                        label: "+ Child"
                        variant: "secondary"
                        small: true
                        onClicked: root.requestAddChild(nodeData.id, nodeData.subjectId)
                    }

                    AppButton {
                        label: "Edit"
                        variant: "secondary"
                        small: true
                        onClicked: root.requestEdit(nodeData.id)
                    }

                    AppButton {
                        label: "Delete"
                        variant: "ghost"
                        small: true
                        onClicked: backend.deleteTopic(nodeData.id)
                    }
                }
            }
        }

        Repeater {
            model: nodeData.children || []
            delegate: Loader {
                Layout.fillWidth: true
                source: "TopicTreeCard.qml"
                onLoaded: {
                    item.nodeData = modelData
                    item.accentColor = root.accentColor
                    item.depth = root.depth + 1
                    item.requestEdit.connect(function(topicId) { root.requestEdit(topicId) })
                    item.requestAddChild.connect(function(topicId, subjectName) { root.requestAddChild(topicId, subjectName) })
                }
            }
        }
    }
}
