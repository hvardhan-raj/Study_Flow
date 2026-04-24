import QtQuick 2.15
import Qt5Compat.GraphicalEffects

Item {
    id: root
    property string name: "info"
    property color tint: "#475569"
    property int size: 16

    width: size
    height: size

    function iconSource(iconName) {
        var key = String(iconName || "info").toLowerCase()
        var known = [
            "alert", "bell", "calendar", "check", "close", "info",
            "play", "refresh", "report", "skip", "spark",
            "stop", "review"
        ]
        return known.indexOf(key) >= 0 ? "assets/icons/" + key + ".svg" : "assets/icons/info.svg"
    }

    Image {
        id: glyph
        anchors.fill: parent
        source: root.iconSource(root.name)
        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: true
        sourceSize.width: root.size
        sourceSize.height: root.size
    }

    ColorOverlay {
        anchors.fill: glyph
        source: glyph
        color: root.tint
    }
}
