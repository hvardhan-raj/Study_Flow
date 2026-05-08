import QtQuick 2.15
import QtQuick.Layouts 1.15
import Qt5Compat.GraphicalEffects

Rectangle {
    id: root

    property string title: ""
    property string valueText: ""
    property string caption: ""
    property string trendText: ""
    property bool trendUp: true
    property color accentColor: "#3B82F6"
    property real progress: 0
    property string iconName: "spark"
    property string ringLabel: ""

    radius: 18
    color: "#FFFFFF"
    border.width: 1
    border.color: "#E6EDF4"
    implicitHeight: 154

    layer.enabled: true
    layer.effect: DropShadow {
        horizontalOffset: 0
        verticalOffset: 8
        radius: 18
        samples: 24
        color: "#160F172A"
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 14

        Item {
            Layout.preferredWidth: 72
            Layout.preferredHeight: 72

            Canvas {
                id: ringCanvas
                anchors.fill: parent

                onPaint: {
                    var ctx = getContext("2d")
                    var w = width
                    var h = height
                    var cx = w / 2
                    var cy = h / 2
                    var radius = Math.min(w, h) / 2 - 7
                    var value = Math.max(0, Math.min(100, root.progress))
                    var start = -Math.PI / 2
                    var end = start + (Math.PI * 2 * value / 100.0)

                    ctx.reset()
                    ctx.beginPath()
                    ctx.lineWidth = 8
                    ctx.strokeStyle = "#E8EEF5"
                    ctx.arc(cx, cy, radius, 0, Math.PI * 2, false)
                    ctx.stroke()

                    ctx.beginPath()
                    ctx.lineCap = "round"
                    ctx.lineWidth = 8
                    ctx.strokeStyle = root.accentColor
                    ctx.arc(cx, cy, radius, start, end, false)
                    ctx.stroke()
                }
            }

            Column {
                anchors.centerIn: parent
                spacing: 1

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: Math.round(Math.max(0, Math.min(100, root.progress))) + "%"
                    font.pixelSize: 13
                    font.bold: true
                    font.family: "Segoe UI"
                    color: "#0F172A"
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: root.ringLabel
                    visible: root.ringLabel.length > 0
                    font.pixelSize: 9
                    font.family: "Segoe UI"
                    color: "#94A3B8"
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 5

            RowLayout {
                Layout.fillWidth: true

                Text {
                    text: root.title
                    font.pixelSize: 10
                    font.bold: true
                    font.letterSpacing: 1.2
                    font.family: "Segoe UI"
                    color: "#94A3B8"
                }

                Item { Layout.fillWidth: true }

                Rectangle {
                    implicitWidth: 28
                    implicitHeight: 28
                    radius: 10
                    color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.12)

                    AppIcon {
                        anchors.centerIn: parent
                        name: root.iconName
                        size: 14
                        tint: root.accentColor
                    }
                }
            }

            Text {
                text: root.valueText
                font.pixelSize: 24
                font.bold: true
                font.family: "Segoe UI"
                color: "#0F172A"
            }

            Text {
                Layout.fillWidth: true
                text: root.caption
                wrapMode: Text.WordWrap
                font.pixelSize: 11
                font.family: "Segoe UI"
                color: "#64748B"
            }

            Rectangle {
                visible: root.trendText.length > 0
                implicitWidth: trendLabel.implicitWidth + 14
                implicitHeight: 22
                radius: 11
                color: root.trendUp ? "#ECFDF5" : "#FEF2F2"

                Text {
                    id: trendLabel
                    anchors.centerIn: parent
                    text: root.trendText
                    font.pixelSize: 10
                    font.bold: true
                    font.family: "Segoe UI"
                    color: root.trendUp ? "#059669" : "#DC2626"
                }
            }
        }
    }
}
