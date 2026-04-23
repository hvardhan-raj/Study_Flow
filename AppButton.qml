import QtQuick 2.15

// ── AppButton ────────────────────────────────────────────────────
//  variant: "primary" | "secondary" | "danger" | "ghost"
Rectangle {
    id: root
    property string label:   "Button"
    property string variant: "primary"
    property bool   small:   false
    property bool   enabled: true

    signal clicked()

    implicitWidth:  btnLabel.implicitWidth + (small ? 22 : 28)
    implicitHeight: small ? 28 : 34
    radius: implicitHeight / 2

    opacity: root.enabled ? 1.0 : 0.5

    property bool _hov: false

    color: {
        if (!root.enabled) return variant === "primary" ? "#6BA3DB" : "#F0F3F8"
        if (variant === "primary")   return _hov ? "#2563EB" : "#3B82F6"
        if (variant === "secondary") return _hov ? "#EEF2F8" : "#F8FAFC"
        if (variant === "danger")    return _hov ? "#DC2626" : "#EF4444"
        return "transparent"
    }

    border.color: {
        if (variant === "secondary") return "#DDE4EF"
        if (variant === "ghost")     return _hov ? "#3B82F6" : "transparent"
        return "transparent"
    }
    border.width: 1

    Behavior on color { ColorAnimation { duration: 130 } }
    Behavior on opacity { NumberAnimation { duration: 100 } }

    Text {
        id: btnLabel
        anchors.centerIn: parent
        text: root.label
        font.pixelSize: root.small ? 11 : 12
        font.bold: true
        font.family: "Segoe UI"
        color: {
            if (root.variant === "primary")   return "#FFFFFF"
            if (root.variant === "danger")    return "#FFFFFF"
            if (root.variant === "ghost")     return root._hov ? "#3B82F6" : "#64748B"
            return root._hov ? "#1E3A5C" : "#374151"
        }
        Behavior on color { ColorAnimation { duration: 130 } }
    }

    scale: _hov && root.enabled ? 0.975 : 1.0
    Behavior on scale { NumberAnimation { duration: 100; easing.type: Easing.OutQuad } }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        enabled: root.enabled
        onEntered:  root._hov = true
        onExited:   root._hov = false
        onClicked:  root.clicked()
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    }
}
