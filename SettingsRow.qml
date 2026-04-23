import QtQuick 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property string label:       ""
    property string value:       ""
    property color  valueColor:  "#374151"
    property bool   isToggle:    false
    property bool   toggleOn:    false
    property bool   isDanger:    false
    property string dangerLabel: ""
    property string settingKey:  ""

    signal toggled(string settingKey)
    signal dangerClicked()

    Layout.fillWidth: true
    height: 46

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: "#F1F5F9"
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10

            Text {
                text: root.label
                font.pixelSize: 12
                font.family: "Segoe UI"
                color: "#374151"
                Layout.fillWidth: true
            }

            // Danger button
            Rectangle {
                visible: root.isDanger
                implicitWidth:  dangerLbl.implicitWidth + 22
                implicitHeight: 28
                radius: 14
                color: "#EF4444"
                Text {
                    id: dangerLbl
                    anchors.centerIn: parent
                    text: root.dangerLabel
                    font.pixelSize: 11
                    font.bold: true
                    font.family: "Segoe UI"
                    color: "#FFFFFF"
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.dangerClicked()
                }
            }

            // Plain value text
            Text {
                visible: !root.isToggle && !root.isDanger
                text:    root.value
                font.pixelSize: 12
                font.family: "Segoe UI"
                color:   root.valueColor
            }

            // Toggle switch
            Rectangle {
                visible: root.isToggle
                width: 40
                height: 22
                radius: 11
                color: root.toggleOn ? "#3B82F6" : "#D1D9E6"
                Behavior on color { ColorAnimation { duration: 160 } }

                Rectangle {
                    width: 18; height: 18
                    radius: 9
                    color: "#FFFFFF"
                    anchors.verticalCenter: parent.verticalCenter
                    x: root.toggleOn ? parent.width - width - 2 : 2
                    Behavior on x { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.toggled(root.settingKey)
                }
            }
        }
    }
}
