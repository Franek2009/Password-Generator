"""Compact desktop controls and cancellable, per-request advanced computation."""

import secrets
from threading import Event

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.advanced import CompletionCounter, GenerationCancelled, compile_rules
from app.advanced_rules import AdvancedRules, CharacterType
from app.errors import GenerationError


class RulesPanel(QWidget):
    changed = Signal()

    def __init__(self, rules, parent=None):
        super().__init__(parent)
        self._restoring = False
        self.controls = {}
        self.labels = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.toggle = QToolButton()
        self.toggle.setCheckable(True)
        self.toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle.setArrowType(Qt.RightArrow)
        self.toggle.setSizePolicy(
            self.sizePolicy().horizontalPolicy(), self.sizePolicy().verticalPolicy()
        )
        layout.addWidget(self.toggle)
        self.body = QWidget()
        rows = QVBoxLayout(self.body)
        rows.setContentsMargins(0, 0, 0, 0)
        self.enabled = QCheckBox()
        rows.addWidget(self.enabled)
        self.fields = QWidget()
        form = QFormLayout(self.fields)
        form.setContentsMargins(0, 0, 0, 0)
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        for key in ("min_uppercase", "min_lowercase", "min_digits", "min_symbols"):
            spin = QSpinBox()
            spin.setRange(0, 64)
            self._row(form, key, spin)
            spin.valueChanged.connect(self._changed)
        self.custom_enabled = QCheckBox()
        form.addRow(self.custom_enabled)
        self.custom_enabled.toggled.connect(self._changed)
        for key in ("custom_alphabet", "forbidden_characters"):
            edit = QLineEdit()
            self._row(form, key, edit)
            edit.textChanged.connect(self._changed)
        for key in ("first_type", "last_type"):
            combo = QComboBox()
            for value in CharacterType:
                combo.addItem(value.value, value)
            self._row(form, key, combo)
            combo.currentIndexChanged.connect(self._changed)
        self.limit_runs = QCheckBox()
        form.addRow(self.limit_runs)
        self.limit_runs.toggled.connect(self._changed)
        spin = QSpinBox()
        spin.setRange(1, 64)
        spin.setValue(2)
        self._row(form, "max_identical_run", spin)
        spin.valueChanged.connect(self._changed)
        rows.addWidget(self.fields)
        layout.addWidget(self.body)
        self.body.hide()
        self.toggle.toggled.connect(self._expand)
        self.enabled.toggled.connect(self._changed)
        self.restore(rules)

    def _row(self, form, key, control):
        label = QLabel()
        label.setWordWrap(True)
        label.setBuddy(control)
        form.addRow(label, control)
        self.controls[key] = control
        self.labels[key] = label

    def _expand(self, expanded):
        self.toggle.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
        self.body.setVisible(expanded)

    def _changed(self, *_):
        self.fields.setEnabled(self.enabled.isChecked())
        self.controls["custom_alphabet"].setEnabled(self.custom_enabled.isChecked())
        self.controls["max_identical_run"].setEnabled(self.limit_runs.isChecked())
        if not self._restoring:
            self.changed.emit()

    def rules(self):
        values = {
            key: control.value()
            for key, control in self.controls.items()
            if isinstance(control, QSpinBox)
        }
        values.update(
            {
                key: control.text()
                for key, control in self.controls.items()
                if isinstance(control, QLineEdit)
            }
        )
        values.update(
            {
                key: CharacterType(control.currentData())
                for key, control in self.controls.items()
                if isinstance(control, QComboBox)
            }
        )
        values["max_identical_run"] = (
            values["max_identical_run"] if self.limit_runs.isChecked() else None
        )
        return AdvancedRules(
            enabled=self.enabled.isChecked(),
            custom_alphabet_enabled=self.custom_enabled.isChecked(),
            **values,
        )

    def restore(self, rules):
        self._restoring = True
        try:
            self.enabled.setChecked(rules.enabled)
            self.custom_enabled.setChecked(rules.custom_alphabet_enabled)
            self.limit_runs.setChecked(rules.max_identical_run is not None)
            for key, control in self.controls.items():
                value = getattr(rules, key)
                if isinstance(control, QSpinBox):
                    control.setValue(value if value is not None else 2)
                elif isinstance(control, QLineEdit):
                    control.setText(value)
                else:
                    control.setCurrentIndex(control.findData(value))
            self._changed()
        finally:
            self._restoring = False

    def retranslate(self, t):
        self.toggle.setText(t("advanced_rules"))
        self.enabled.setText(t("advanced_enabled"))
        self.custom_enabled.setText(t("custom_alphabet_enabled"))
        self.limit_runs.setText(t("limit_runs"))
        for key, label in self.labels.items():
            label.setText(t(key))
            self.controls[key].setAccessibleName(t(key))
        for key in ("first_type", "last_type"):
            combo = self.controls[key]
            for i in range(combo.count()):
                combo.setItemText(
                    i, t("character_" + CharacterType(combo.itemData(i)).value)
                )


class RulesJob(QThread):
    completed = Signal(object, str, bool)

    def __init__(self, config, generate=False, parent=None):
        super().__init__(parent)
        self.config = config
        self.generate = generate
        self.cancelled = Event()

    def run(self):
        counter = None
        try:
            counter = CompletionCounter(
                compile_rules(self.config), self.cancelled.is_set
            )
            total = counter.total()
            if not total:
                raise GenerationError("no_valid_password", "No valid password")
            result = counter.unrank(secrets.randbelow(total)) if self.generate else None
            if not self.cancelled.is_set():
                self.completed.emit(result, "", total == 1)
        except GenerationCancelled:
            pass
        except Exception as error:  # noqa: BLE001 - worker boundary reports failure without logging secrets
            if not self.cancelled.is_set():
                self.completed.emit(
                    None, getattr(error, "code", "unknown_error"), False
                )
        finally:
            if counter is not None:
                counter.close()
