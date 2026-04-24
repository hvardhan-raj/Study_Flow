import QtQuick 2.15
import QtQuick.Controls 2.15

Dialog {
    id: root
    modal: true
    padding: 18

    background: Rectangle {
        radius: 24
        color: "#FFFFFF"
        border.color: "#E2E8F0"
        border.width: 1
    }

    Overlay.modal: Rectangle {
        color: Qt.rgba(15 / 255, 23 / 255, 42 / 255, 0.28)
    }
}
