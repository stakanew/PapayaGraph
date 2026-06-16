def apply_dark_theme(app):
    dark_stylesheet = """
        QMainWindow {
            background-color: #1e1e1e;
            color: #d4d4d4;
        }
        QWidget {
            background-color: #2d2d2d;
            color: #d4d4d4;
            font-family: Arial;
            font-size: 13px;
        }
        QMenuBar {
            background-color: #252526;
            color: #d4d4d4;
        }
        QMenuBar::item {
            background-color: transparent;
            padding: 4px 10px;
        }
        QMenuBar::item:selected {
            background-color: #3e3e42;
        }
        QMenu {
            background-color: #252526;
            color: #d4d4d4;
            border: 1px solid #454545;
        }
        QMenu::item:selected {
            background-color: #ff8c00;
            color: #ffffff;
        }
        QSplitter::handle {
            background-color: #1e1e1e;
        }
        QStatusBar {
            background-color: #007acc;
            color: white;
        }
        QLineEdit, QTextEdit, QPlainTextEdit, QTreeWidget, QListWidget {
            background-color: #1e1e1e;
            color: #d4d4d4;
            border: 1px solid #3c3c3c;
            padding: 4px;
        }
        QPushButton {
            background-color: #3a3d41;
            color: #ffffff;
            border: 1px solid #454545;
            padding: 6px 12px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #505357;
        }
        QPushButton:pressed {
            background-color: #ff8c00;
        }
        QScrollBar:vertical {
            border: none;
            background: #1e1e1e;
            width: 14px;
            margin: 0px 0px 0px 0px;
        }
        QScrollBar::handle:vertical {
            background: #424242;
            min-height: 20px;
            border-radius: 7px;
        }
        QScrollBar::handle:vertical:hover {
            background: #4f4f4f;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: none;
        }
    """
    app.setStyleSheet(dark_stylesheet)
