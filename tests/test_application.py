from PySide6.QtGui import QIcon, QPixmap

from app import application


def test_configure_application_sets_identity(monkeypatch, qapp, tmp_path):
    version_path = tmp_path / "VERSION"
    version_path.write_text("1.0.2\n", encoding="utf-8")

    monkeypatch.setattr(
        "app.versioning.resource_path",
        lambda *parts: version_path,
    )

    application.configure_application(qapp)

    assert qapp.applicationName() == "Password Generator"
    assert qapp.applicationDisplayName() == "Password Generator"
    assert qapp.applicationVersion() == "1.0.2"


def test_configure_application_sets_icon_when_available(
    monkeypatch,
    qapp,
    tmp_path,
):
    icon_path = tmp_path / "icon.png"
    pixmap = QPixmap(16, 16)
    pixmap.fill()
    assert pixmap.save(str(icon_path))

    monkeypatch.setattr(
        application,
        "resource_path",
        lambda *parts: icon_path,
    )
    qapp.setWindowIcon(QIcon())

    application.configure_application(qapp)

    assert not qapp.windowIcon().isNull()
