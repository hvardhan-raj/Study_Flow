import QtQuick 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property var values: []
    property color accentColor: "#3B82F6"
    property color fillColor: Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.14)
    property color gridColor: "#E2E8F0"
    property string emptyText: "No chart data"

    implicitHeight: 180

    Canvas {
        id: chartCanvas
        anchors.fill: parent

        onPaint: {
            var ctx = getContext("2d")
            var w = width
            var h = height
            var count = root.values ? root.values.length : 0
            var cellWidth = count > 0 ? (w / count) : w
            var left = cellWidth / 2
            var right = w - (cellWidth / 2)
            var top = 10
            var bottom = h - 18

            ctx.reset()

            for (var row = 0; row < 4; row++) {
                var gy = top + ((bottom - top) * row / 3.0)
                ctx.beginPath()
                ctx.lineWidth = 1
                ctx.strokeStyle = root.gridColor
                ctx.moveTo(left, gy)
                ctx.lineTo(right, gy)
                ctx.stroke()
            }

            if (!root.values || root.values.length < 2)
                return

            var maxValue = 1
            for (var i = 0; i < root.values.length; i++)
                maxValue = Math.max(maxValue, Number(root.values[i] || 0))

            function px(index) {
                return left + ((right - left) * index / Math.max(1, root.values.length - 1))
            }

            function py(value) {
                return bottom - ((bottom - top) * Number(value || 0) / maxValue)
            }

            ctx.beginPath()
            ctx.moveTo(px(0), bottom)
            for (var areaIndex = 0; areaIndex < root.values.length; areaIndex++)
                ctx.lineTo(px(areaIndex), py(root.values[areaIndex]))
            ctx.lineTo(px(root.values.length - 1), bottom)
            ctx.closePath()
            ctx.fillStyle = root.fillColor
            ctx.fill()

            ctx.beginPath()
            ctx.lineWidth = 3
            ctx.lineJoin = "round"
            ctx.lineCap = "round"
            ctx.strokeStyle = root.accentColor
            for (var lineIndex = 0; lineIndex < root.values.length; lineIndex++) {
                var x = px(lineIndex)
                var y = py(root.values[lineIndex])
                if (lineIndex === 0)
                    ctx.moveTo(x, y)
                else
                    ctx.lineTo(x, y)
            }
            ctx.stroke()

            for (var pointIndex = 0; pointIndex < root.values.length; pointIndex++) {
                var pointX = px(pointIndex)
                var pointY = py(root.values[pointIndex])
                ctx.beginPath()
                ctx.fillStyle = "#FFFFFF"
                ctx.arc(pointX, pointY, 4, 0, Math.PI * 2, false)
                ctx.fill()
                ctx.beginPath()
                ctx.lineWidth = 2
                ctx.strokeStyle = root.accentColor
                ctx.arc(pointX, pointY, 4, 0, Math.PI * 2, false)
                ctx.stroke()
            }
        }
    }

    Text {
        anchors.centerIn: parent
        visible: !root.values || root.values.length < 2
        text: root.emptyText
        font.pixelSize: 11
        font.family: "Segoe UI"
        color: "#94A3B8"
    }
}
