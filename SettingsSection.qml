import QtQuick 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property string sectionTitle: "Section"
    default property alias content: innerCol.data

    implicitHeight: innerCol.implicitHeight + 48
    radius: 14
    color: "#FFFFFF"
    border.color: "#EEF2F8"
    border.width: 1

    ColumnLayout {
        id: innerCol
        anchors { fill: parent; margins: 20 }
        spacing: 0

        Text {
            text: root.sectionTitle
            font.pixelSize: 10
            font.letterSpacing: 1.4
            font.bold: true
            font.family: "Segoe UI"
            color: "#94A3B8"
        }

        Item { height: 8 }
    }
}
