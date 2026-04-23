import sys
from PySide6.QtCore import QObject, Property
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

class Backend(QObject):
    @Property(str)
    def testString(self):
        return "Hello from Python!"

def main():
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    backend = Backend()
    engine.rootContext().setContextProperty("backend", backend)
    engine.loadData(b"""
    import QtQuick 2.15
    import QtQuick.Window 2.15
    Window {
        visible: true; width: 200; height: 200
        Component.onCompleted: console.log("backend string:", backend.testString)
    }
    """)
    if not engine.rootObjects():
        return -1
    # app.exec() # Don't block
    return 0

if __name__ == "__main__":
    sys.exit(main())
