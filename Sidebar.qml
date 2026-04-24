import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    width: 220
    color: "#111827"

    property int  activePage: 0
    property var  pages: []
    signal pageSelected(int index)

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ── Logo ──────────────────────────────────────────────────────
        Item { height: 22 }

        RowLayout {
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            spacing: 11

            Rectangle {
                width: 36; height: 36
                radius: 11
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#3B82F6" }
                    GradientStop { position: 1.0; color: "#1D4ED8" }
                }
                Text {
                    anchors.centerIn: parent
                    text: "S"
                    font.pixelSize: 17
                    font.bold: true
                    color: "white"
                }
            }

            ColumnLayout {
                spacing: 1
                Text {
                    text: "StudyFlow"
                    font.pixelSize: 14
                    font.bold: true
                    color: "#FFFFFF"
                    font.family: "Segoe UI"
                }
                Text {
                    text: "Smart Study Schedule System"
                    font.pixelSize: 9
                    color: "#6B7C94"
                    font.family: "Segoe UI"
                }
            }
        }

        Item { height: 28 }

        // ── Nav label ────────────────────────────────────────────────
        Text {
            Layout.leftMargin: 20
            text: "NAVIGATION"
            font.pixelSize: 9
            font.letterSpacing: 1.8
            font.bold: true
            color: "#4B5E73"
            font.family: "Segoe UI"
        }

        Item { height: 6 }

        // ── Nav items ────────────────────────────────────────────────
        Repeater {
            model: root.pages
            delegate: SidebarItem {
                label:    modelData.label
                icon:     modelData.icon
                active:   (index === root.activePage)
                onClicked: root.pageSelected(index)
            }
        }

        Item { Layout.fillHeight: true }
        Text {
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            Layout.bottomMargin: 18
            wrapMode: Text.WordWrap
            font.pixelSize: 10
            font.family: "Segoe UI"
            color: "#6B7C94"
        }
    }
}
