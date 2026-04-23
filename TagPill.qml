import QtQuick 2.15

// Coloured pill tag  e.g. "Biology", "Hard", "Pending"
Rectangle {
    id: root
    property string tagText:  "Tag"
    property color  tagColor: "#3B82F6"
    property bool   outlined: false

    implicitWidth:  label.implicitWidth + 16
    implicitHeight: 22
    radius:         11

    color:        root.outlined ? "transparent" : Qt.rgba(root.tagColor.r, root.tagColor.g, root.tagColor.b, 0.10)
    border.color: root.outlined ? Qt.rgba(root.tagColor.r, root.tagColor.g, root.tagColor.b, 0.55) : "transparent"
    border.width: root.outlined ? 1 : 0

    Text {
        id: label
        anchors.centerIn: parent
        text:  root.tagText
        font.pixelSize: 10
        font.bold: true
        font.family: "Segoe UI"
        color: root.tagColor
    }
}
