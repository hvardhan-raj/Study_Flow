import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    property var toastModel: []
    property var backendRef: null

    anchors.right: parent.right
    anchors.top: parent.top
    anchors.margins: 20
    width: 340
    z: 1000

    Column {
        anchors.right: parent.right
        width: parent.width
        spacing: 10

        Repeater {
            model: root.toastModel

            delegate: Rectangle {
                id: toastCard
                width: root.width
                radius: 18
                color: "#FFFFFF"
                border.width: 1
                border.color: Qt.rgba(modelData.color.r, modelData.color.g, modelData.color.b, 0.18)
                implicitHeight: content.implicitHeight + 22
                opacity: 1.0

                Behavior on opacity { NumberAnimation { duration: 180 } }
                Behavior on y { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }

                RowLayout {
                    id: content
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 10

                    Rectangle {
                        Layout.preferredWidth: 34
                        Layout.preferredHeight: 34
                        radius: 12
                        color: Qt.rgba(modelData.color.r, modelData.color.g, modelData.color.b, 0.12)

                        AppIcon {
                            anchors.centerIn: parent
                            name: modelData.icon
                            size: 16
                            tint: modelData.color
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        Text {
                            text: modelData.title
                            font.pixelSize: 12
                            font.bold: true
                            font.family: "Segoe UI"
                            color: "#0F172A"
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Text {
                            text: modelData.message
                            font.pixelSize: 10
                            font.family: "Segoe UI"
                            color: "#64748B"
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }

                    AppButton {
                        label: ""
                        iconName: "close"
                        iconColor: "#94A3B8"
                        variant: "ghost"
                        small: true
                        implicitWidth: 28
                        onClicked: if (root.backendRef) root.backendRef.dismissToast(modelData.id)
                    }
                }

                Timer {
                    interval: Number(modelData.duration || 3600)
                    running: true
                    repeat: false
                    onTriggered: if (root.backendRef) root.backendRef.dismissToast(modelData.id)
                }
            }
        }
    }
}
