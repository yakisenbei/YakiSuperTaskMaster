from __future__ import annotations

import sys
import os
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlEngine

from taskmaster.controller import TaskMasterController


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)

    # Workaround: Some QtQuick.Controls styles (e.g., Fusion/Material) are broken
    # in this environment and fail to instantiate core controls like TextField/Menu.
    # Force the lightweight Basic style before the QApplication is created.
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

    app = QApplication(argv)

    engine = QQmlApplicationEngine()
    controller = TaskMasterController()
    controller.setParent(app)
    QQmlEngine.setObjectOwnership(controller, QQmlEngine.ObjectOwnership.CppOwnership)
    engine.rootContext().setContextProperty("TM", controller)

    qml_path = Path(__file__).resolve().parent / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))

    if not engine.rootObjects():
        return 1

    return app.exec()
