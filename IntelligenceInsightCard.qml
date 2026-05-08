import QtQuick 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property string title: ""
    property string body: ""
    property string badge: ""
    property string iconName: "spark"
    property color accentColor: "#3B82F6"

    radius: 14
    color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.08)
    border.width: 1
    border.color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.18)
    implicitHeight: content.implicitHeight + 22

    ColumnLayout {
        id: content
        anchors.fill: parent
        anchors.margins: 12
        spacing: 7

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Rectangle {
                width: 28
                height: 28
                radius: 10
                color: "#FFFFFF"

                AppIcon {
                    anchors.centerIn: parent
                    name: root.iconName
                    size: 14
                    tint: root.accentColor
                }
            }

            Text {
                Layout.fillWidth: true
                text: root.title
                font.pixelSize: 12
                font.bold: true
                font.family: "Segoe UI"
                color: "#0F172A"
                wrapMode: Text.WordWrap
            }

            TagPill {
                visible: root.badge.length > 0
                tagText: root.badge
                tagColor: root.accentColor
            }
        }

        Text {
            Layout.fillWidth: true
            text: root.body
            wrapMode: Text.WordWrap
            font.pixelSize: 11
            font.family: "Segoe UI"
            color: "#475569"
        }
    }
}
