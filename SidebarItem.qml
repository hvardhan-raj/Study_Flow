import QtQuick 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    width: parent.width
    height: 42

    property string label:  ""
    property string icon:   ""
    property bool   active: false
    property bool   hovered: false

    signal clicked()

    Rectangle {
        anchors {
            left: parent.left; right: parent.right
            leftMargin: 10; rightMargin: 10
            verticalCenter: parent.verticalCenter
        }
        height: 36
        radius: 10
        color: root.active  ? Qt.rgba(59/255, 130/255, 246/255, 0.18)
             : root.hovered ? Qt.rgba(1, 1, 1, 0.04)
             : "transparent"

        Behavior on color { ColorAnimation { duration: 120 } }

        // Active left accent bar
        Rectangle {
            visible: root.active
            width: 3
            height: 18
            radius: 2
            color: "#3B82F6"
            anchors {
                left: parent.left
                verticalCenter: parent.verticalCenter
                leftMargin: -1
            }
        }

        RowLayout {
            anchors { fill: parent; leftMargin: 14; rightMargin: 10 }
            spacing: 10

            Text {
                text: root.icon
                font.pixelSize: 14
                color: root.active ? "#3B82F6" : (root.hovered ? "#C0D0E0" : "#607485")
                Behavior on color { ColorAnimation { duration: 120 } }
            }

            Text {
                text: root.label
                font.pixelSize: 12
                font.family: "Segoe UI"
                font.weight: root.active ? Font.DemiBold : Font.Normal
                color: root.active ? "#FFFFFF" : (root.hovered ? "#C0D0E0" : "#7A8FA3")
                Behavior on color { ColorAnimation { duration: 120 } }
            }

            Item { Layout.fillWidth: true }
        }
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        onEntered:  root.hovered = true
        onExited:   root.hovered = false
        onClicked:  root.clicked()
        cursorShape: Qt.PointingHandCursor
    }
}
