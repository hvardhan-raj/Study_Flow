import QtQuick 2.15
import QtQuick.Layouts 1.15

// ── StatCard ─────────────────────────────────────────────────────
//  White card: title, big value, subtitle & trend badge
Rectangle {
    id: root

    property string cardTitle:   "LABEL"
    property string value:       "—"
    property string subtitle:    ""
    property string trend:       ""
    property bool   trendUp:     true
    property color  valueColor:  "#0F172A"
    property color  accentColor: "#3B82F6"
    property real   progressValue: -1

    width:  180
    implicitHeight: progressValue >= 0 ? 124 : 106
    radius: 14
    color:  "#FFFFFF"
    border.color: "#EEF2F8"
    border.width: 1

    // Accent strip
    Rectangle {
        width: 28; height: 3; radius: 2
        color: root.accentColor
        anchors { top: parent.top; left: parent.left; topMargin: 0; leftMargin: 18 }
    }

    ColumnLayout {
        anchors { fill: parent; margins: 18; topMargin: 16 }
        spacing: 5

        Text {
            text: root.cardTitle
            font.pixelSize: 9
            font.letterSpacing: 1.4
            font.bold: true
            font.family: "Segoe UI"
            color: "#94A3B8"
        }

        Text {
            text: root.value
            font.pixelSize: 24
            font.bold: true
            font.family: "Segoe UI"
            color: root.valueColor
        }

        RowLayout {
            spacing: 6
            visible: root.subtitle !== "" || root.trend !== ""

            // Trend badge
            Rectangle {
                visible: root.trend !== ""
                implicitWidth: trendLbl.implicitWidth + 10
                implicitHeight: 18
                radius: 9
                color: root.trendUp
                        ? Qt.rgba(16/255, 185/255, 129/255, 0.10)
                        : Qt.rgba(239/255, 68/255, 68/255, 0.10)
                Text {
                    id: trendLbl
                    anchors.centerIn: parent
                    text: root.trend
                    font.pixelSize: 9
                    font.bold: true
                    font.family: "Segoe UI"
                    color: root.trendUp ? "#059669" : "#DC2626"
                }
            }

            Text {
                Layout.fillWidth: true
                text: root.subtitle
                font.pixelSize: 10
                font.family: "Segoe UI"
                color: "#94A3B8"
                elide: Text.ElideRight
            }
        }

        Rectangle {
            visible: root.progressValue >= 0
            Layout.fillWidth: true
            implicitHeight: 6
            radius: 3
            color: "#E2E8F0"

            Rectangle {
                width: Math.max(0, Math.min(parent.width, parent.width * Math.max(0, Math.min(root.progressValue, 100)) / 100.0))
                height: parent.height
                radius: parent.radius
                color: root.accentColor
            }
        }
    }
}
