import QtQuick 2.15

// ── AppButton ────────────────────────────────────────────────────
//  variant: "primary" | "secondary" | "danger" | "ghost"
Rectangle {
    id: root
    property string label:   "Button"
    property string variant: "primary"
    property bool   small:   false
    property bool   enabled: true
    property string iconName: ""
    property color iconColor: btnLabel.color

    signal clicked()

    implicitWidth:  btnRow.implicitWidth + (small ? 22 : 28)
    implicitHeight: small ? 28 : 34
    radius: implicitHeight / 2

    opacity: root.enabled ? 1.0 : 0.5

    property bool _hov: false
    property bool _pressed: false

    color: {
        if (!root.enabled) return variant === "primary" ? "#6BA3DB" : "#F0F3F8"
        if (variant === "primary")   return _pressed ? "#1D4ED8" : (_hov ? "#2563EB" : "#3B82F6")
        if (variant === "secondary") return _pressed ? "#E2E8F0" : (_hov ? "#EEF2F8" : "#F8FAFC")
        if (variant === "danger")    return _pressed ? "#B91C1C" : (_hov ? "#DC2626" : "#EF4444")
        if (variant === "success")   return _pressed ? "#059669" : (_hov ? "#10B981" : "#34D399")
        if (variant === "warning")   return _pressed ? "#D97706" : (_hov ? "#F59E0B" : "#FBBF24")
        return "transparent"
    }

    border.color: {
        if (variant === "secondary") return "#DDE4EF"
        if (variant === "warning")   return "transparent"
        if (variant === "success")   return "transparent"
        if (variant === "ghost")     return _hov ? "#3B82F6" : "transparent"
        return "transparent"
    }
    border.width: 1

    Behavior on color { ColorAnimation { duration: 130 } }
    Behavior on opacity { NumberAnimation { duration: 100 } }

    Row {
        id: btnRow
        anchors.centerIn: parent
        spacing: root.iconName.length > 0 && root.label.length > 0 ? 6 : 0

        AppIcon {
            anchors.verticalCenter: parent.verticalCenter
            visible: root.iconName.length > 0
            name: root.iconName
            size: root.small ? 12 : 14
            tint: root.iconColor
        }

        Text {
            id: btnLabel
            anchors.verticalCenter: parent.verticalCenter
            text: root.label
            font.pixelSize: root.small ? 11 : 12
            font.bold: true
            font.family: "Segoe UI"
            color: {
                if (root.variant === "primary" || root.variant === "danger" || root.variant === "warning" || root.variant === "success") return "#FFFFFF"
                if (root.variant === "ghost") return root._hov ? "#3B82F6" : "#64748B"
                return root._hov ? "#1E3A5C" : "#374151"
            }
            Behavior on color { ColorAnimation { duration: 130 } }
        }
    }

    scale: root._pressed && root.enabled ? 0.965 : (_hov && root.enabled ? 0.982 : 1.0)
    Behavior on scale { NumberAnimation { duration: 100; easing.type: Easing.OutQuad } }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        enabled: root.enabled
        onEntered:  root._hov = true
        onExited:   {
            root._hov = false
            root._pressed = false
        }
        onPressed: root._pressed = true
        onReleased: root._pressed = containsMouse
        onClicked:  root.clicked()
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    }
}
