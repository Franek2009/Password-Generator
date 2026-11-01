"""Scrollable plain-text result; spacing is typography, never password data."""

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QFont,
    QFontDatabase,
    QKeySequence,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import QApplication, QMenu, QTextEdit


class ResultView(QTextEdit):
    def __init__(self):
        super().__init__()
        self._raw = ""
        self.transcription = False
        self.human = False
        self.setReadOnly(True)
        self.setAcceptRichText(False)
        self.setMinimumHeight(92)
        self.setMaximumHeight(210)
        self.setTabChangesFocus(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_copy_menu)

    def text(self):
        # QTextDocument.toPlainText normalizes e.g. non-breaking spaces.
        # Custom word lists may contain them, so retain the exact original.
        return self._raw

    def setPlainText(self, text):
        self._raw = text
        super().setPlainText(text)
        self.format_result()

    def setText(self, text):
        self.setPlainText(text)

    def clear(self):
        self.setPlainText("")

    def setCursorPosition(self, position):
        cursor = self.textCursor()
        cursor.setPosition(position)
        self.setTextCursor(cursor)

    def format_result(self):
        cursor = QTextCursor(self.document())
        cursor.select(QTextCursor.Document)
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        font.setPointSize(24 if self.transcription else 18)
        normal = QTextCharFormat()
        normal.setFont(font)
        cursor.setCharFormat(normal)
        if self.transcription and not self.human:
            spaced = QTextCharFormat(normal)
            spaced.setFontLetterSpacingType(QFont.AbsoluteSpacing)
            spaced.setFontLetterSpacing(14)
            for i in range(3, len(self.text()) - 1, 4):
                cursor.setPosition(i)
                cursor.setPosition(i + 1, QTextCursor.KeepAnchor)
                cursor.setCharFormat(spaced)
        self.setCursorPosition(0)

    def copy(self):
        if self.text():
            QApplication.clipboard().setText(self.text())

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Copy):
            self.copy()
        else:
            super().keyPressEvent(event)

    def show_copy_menu(self, position):
        menu = QMenu(self)
        action = menu.addAction(self.accessibleDescription())
        action.setEnabled(bool(self.text()))
        action.triggered.connect(self.copy)
        menu.exec(self.mapToGlobal(position))
