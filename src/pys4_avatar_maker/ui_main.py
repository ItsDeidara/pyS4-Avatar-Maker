import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout, QRadioButton, QGroupBox, QMessageBox, QLineEdit, QDialog, QScrollArea, QGridLayout, QCheckBox
)
from PyQt6.QtGui import QPixmap, QDesktopServices, QPainter
from PyQt6.QtCore import Qt, QUrl, QSettings
from .models import UserType, FTPConfig
from .controllers import create_avatar_package
from .services import process_batch_avatars
import tempfile
import os
from ftplib import FTP, error_perm

def is_image_file(path):
    return path.suffix.lower() in {'.png', '.jpg', '.jpeg'}

class FTPDirDialog(QDialog):
    def __init__(self, ftp_cfg, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Browse FTP Directories")
        self.setMinimumSize(400, 400)
        self.ftp_cfg = ftp_cfg
        self.current_dir = ftp_cfg.upload_dir or "/"
        self.ftp = FTP()
        layout = QVBoxLayout()
        self.path_label = QLabel(self.current_dir)
        layout.addWidget(self.path_label)
        self.dir_list = QVBoxLayout()
        self.dir_widget = QWidget()
        self.dir_widget.setLayout(self.dir_list)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.dir_widget)
        layout.addWidget(self.scroll)
        btn_hbox = QHBoxLayout()
        self.btn_select = QPushButton("Select")
        self.btn_select.clicked.connect(self.accept)
        btn_hbox.addWidget(self.btn_select)
        self.btn_up = QPushButton("Up")
        self.btn_up.clicked.connect(self.go_up)
        btn_hbox.addWidget(self.btn_up)
        layout.addLayout(btn_hbox)
        self.setLayout(layout)
        self.connect_and_list()
    def connect_and_list(self):
        try:
            self.ftp.connect(self.ftp_cfg.host, self.ftp_cfg.port)
            if self.ftp_cfg.username and self.ftp_cfg.password:
                self.ftp.login(self.ftp_cfg.username, self.ftp_cfg.password)
            else:
                self.ftp.login()
            self.ftp.cwd(self.current_dir)
            self.refresh_list()
        except Exception as e:
            QMessageBox.critical(self, "FTP Error", f"Failed to connect or list directory: {e}")
            self.reject()
    def refresh_list(self):
        for i in reversed(range(self.dir_list.count())):
            self.dir_list.itemAt(i).widget().setParent(None)
        dirs = []
        try:
            dirs = [name for name, facts in self.ftp.mlsd() if facts['type'] == 'dir']
        except Exception:
            # fallback for servers without MLSD
            dirs = []
            self.ftp.retrlines('LIST', lambda line: dirs.append(line.split()[-1]) if line.startswith('d') else None)
        for d in dirs:
            btn = QPushButton(d)
            btn.clicked.connect(lambda _, name=d: self.enter_dir(name))
            self.dir_list.addWidget(btn)
        self.path_label.setText(self.current_dir)
    def enter_dir(self, name):
        try:
            self.ftp.cwd(name)
            self.current_dir = self.ftp.pwd()
            self.refresh_list()
        except error_perm:
            QMessageBox.warning(self, "FTP", f"Cannot enter directory: {name}")
    def go_up(self):
        try:
            self.ftp.cwd("..")
            self.current_dir = self.ftp.pwd()
            self.refresh_list()
        except error_perm:
            pass
    def accept(self):
        self.selected_dir = self.current_dir
        self.ftp.quit()
        super().accept()
    def reject(self):
        self.ftp.quit()
        super().reject()

class AvatarMakerUI(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("pyS4AvatarMaker", "Config")
        self.setWindowTitle("pyS4 Avatar Maker")
        self.setMinimumSize(600, 700)
        self.setStyleSheet(self.dark_stylesheet())
        self.image_path = None
        self.user_type = UserType.LOCAL
        self.batch_input_dir = None
        self.batch_output_dir = None
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout()
        # User type group
        self.group_user = QGroupBox("User Type")
        user_hbox = QHBoxLayout()
        self.rb_offline = QRadioButton("Offline Activated")
        self.rb_local = QRadioButton("Local")
        self.rb_local.setChecked(True)
        self.rb_offline.toggled.connect(self.on_user_type_changed)
        self.rb_local.toggled.connect(self.on_user_type_changed)
        user_hbox.addWidget(self.rb_offline)
        user_hbox.addWidget(self.rb_local)
        self.group_user.setLayout(user_hbox)
        layout.addWidget(self.group_user)
        # Single image section
        self.label = QLabel("Tip: Click the image below to select a single avatar image.\nFor multiple avatars, use Batch Mode at the bottom.")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        self.img_label = QLabel()
        self.img_label.setMinimumSize(440, 440)
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet("border: 2px solid #444; background: #222;")
        avatar_path = str(self.default_avatar_path())
        # Always load and resize default_avatar.png on bootup
        if Path(avatar_path).exists():
            pixmap = QPixmap(avatar_path)
            # Resize to fit 440x440, keep aspect, smooth, center with padding if not square
            if pixmap.width() != 440 or pixmap.height() != 440:
                scaled = pixmap.scaled(440, 440, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                final = QPixmap(440, 440)
                final.fill(Qt.GlobalColor.transparent)
                painter = QPainter(final)
                x = (440 - scaled.width()) // 2
                y = (440 - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
                painter.end()
                pixmap = final
            # else: already 440x440
        else:
            QMessageBox.warning(self, "Missing Logo", f"default_avatar.png not found at {avatar_path}. Please add a 500x500 logo PNG.")
            pixmap = QPixmap(440, 440)
            pixmap.fill(Qt.GlobalColor.darkGray)
        self.img_label.setPixmap(pixmap)
        self.img_label.mousePressEvent = self.select_image
        layout.addWidget(self.img_label)
        self.btn_export = QPushButton("Export Avatar")
        layout.addWidget(self.btn_export)
        self.btn_export.clicked.connect(self.export_avatar)
        # FTP config UI (must be before config_boxes)
        ftp_group = QGroupBox("FTP Upload (Optional)")
        ftp_layout = QVBoxLayout()
        self.ftp_enable = QRadioButton("Enable FTP Upload")
        self.ftp_enable.setChecked(False)
        ftp_layout.addWidget(self.ftp_enable)
        self.ftp_host = QLineEdit()
        self.ftp_host.setPlaceholderText("FTP Host (e.g. 192.168.1.100)")
        self.ftp_port = QLineEdit()
        self.ftp_port.setPlaceholderText("Port (default 2121)")
        self.ftp_user = QLineEdit()
        self.ftp_user.setPlaceholderText("Username (optional)")
        self.ftp_pass = QLineEdit()
        self.ftp_pass.setPlaceholderText("Password (optional)")
        self.ftp_pass.setEchoMode(QLineEdit.EchoMode.Password)
        ftp_dir_hbox = QHBoxLayout()
        self.ftp_dir = QLineEdit()
        self.ftp_dir.setPlaceholderText("Upload Directory (default /)")
        btn_browse_ftp = QPushButton("Browse FTP")
        btn_browse_ftp.setMinimumWidth(120)
        btn_browse_ftp.clicked.connect(self.browse_ftp_dir)
        ftp_dir_hbox.addWidget(self.ftp_dir, 3)
        ftp_dir_hbox.addWidget(btn_browse_ftp, 1)
        for w in [self.ftp_host, self.ftp_port, self.ftp_user, self.ftp_pass]:
            ftp_layout.addWidget(w)
        ftp_layout.addLayout(ftp_dir_hbox)
        ftp_group.setLayout(ftp_layout)
        layout.addWidget(ftp_group)
        # Batch group
        batch_group = QGroupBox("Batch Mode")
        batch_layout = QVBoxLayout()
        self.batch_use_ftp = QCheckBox("Use FTP as Output")
        self.batch_use_ftp.setChecked(False)
        batch_layout.addWidget(self.batch_use_ftp)
        self.batch_use_ftp.toggled.connect(self.on_batch_use_ftp_toggled)
        input_hbox = QHBoxLayout()
        self.input_dir_edit = QLineEdit()
        self.input_dir_edit.setPlaceholderText("Select input folder with PNG/JPG images...")
        self.input_dir_edit.setReadOnly(True)
        btn_browse_input = QPushButton("Browse")
        btn_browse_input.clicked.connect(self.select_batch_input_dir)
        input_hbox.addWidget(self.input_dir_edit)
        input_hbox.addWidget(btn_browse_input)
        batch_layout.addLayout(input_hbox)
        output_hbox = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Select output directory...")
        self.output_dir_edit.setReadOnly(True)
        btn_browse_output = QPushButton("Browse")
        btn_browse_output.clicked.connect(self.select_batch_output_dir)
        btn_open_output = QPushButton("Open")
        btn_open_output.clicked.connect(self.open_output_dir)
        output_hbox.addWidget(self.output_dir_edit)
        output_hbox.addWidget(btn_browse_output)
        output_hbox.addWidget(btn_open_output)
        batch_layout.addLayout(output_hbox)
        self.btn_run_batch = QPushButton("Run Batch")
        self.btn_run_batch.setMinimumHeight(40)
        self.btn_run_batch.clicked.connect(self.run_batch)
        batch_layout.addWidget(self.btn_run_batch)
        # Add Open Batch Preview button
        btn_open_preview = QPushButton("Open Batch Preview")
        btn_open_preview.clicked.connect(self.open_batch_preview)
        batch_layout.addWidget(btn_open_preview)
        batch_group.setLayout(batch_layout)
        layout.addWidget(batch_group)
        layout.addStretch(1)
        self.setLayout(layout)
        # Now connect signals for config boxes
        config_boxes = [self.ftp_host, self.ftp_port, self.ftp_user, self.ftp_pass, self.ftp_dir, self.input_dir_edit, self.output_dir_edit]
        for box in config_boxes:
            box.editingFinished.connect(self.on_config_edited)
        self.batch_use_ftp.toggled.connect(self.on_config_edited)

    def default_avatar_path(self):
        # Use PyInstaller's _MEIPASS if bundled, else normal path
        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS) / "src" / "pys4_avatar_maker" / "default_avatar.png"
        return Path(__file__).parent / "default_avatar.png"

    def on_user_type_changed(self):
        if self.rb_local.isChecked():
            self.user_type = UserType.LOCAL
        else:
            self.user_type = UserType.OFFLINE_ACTIVATED

    def select_image(self, event):
        file, _ = QFileDialog.getOpenFileName(self, "Select Avatar Image", "", "Images (*.png *.jpg *.jpeg)")
        if file:
            self.image_path = Path(file)
            self.img_label.setPixmap(QPixmap(file).scaled(440, 440, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def export_avatar(self):
        if not self.image_path:
            QMessageBox.warning(self, "No Image", "Please select an avatar image first.")
            return
        file, _ = QFileDialog.getSaveFileName(self, "Save Avatar Package", "My Avatar.xavatar", "Avatar (*.xavatar)")
        if file:
            tmp_dir = Path(tempfile.mkdtemp())
            try:
                create_avatar_package(self.image_path, self.user_type, Path(file), tmp_dir)
                QMessageBox.information(self, "Success", "Avatar ready! Copy it to a USB device and use it with PS4-Xplorer.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export avatar: {e}")
            finally:
                if tmp_dir.exists():
                    for f in tmp_dir.iterdir():
                        f.unlink(missing_ok=True)
                    tmp_dir.rmdir()

    def select_batch_input_dir(self):
        dir_ = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if dir_:
            self.batch_input_dir = Path(dir_)
            self.input_dir_edit.setText(str(dir_))
            images = [p for p in self.batch_input_dir.iterdir() if p.is_file() and is_image_file(p)]
            if images:
                self.show_batch_preview(images)

    def select_batch_output_dir(self):
        dir_ = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_:
            self.batch_output_dir = Path(dir_)
            self.output_dir_edit.setText(str(dir_))

    def open_output_dir(self):
        if self.batch_output_dir and self.batch_output_dir.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.batch_output_dir)))

    def run_batch(self):
        # Always get the input dir from the UI field
        input_dir = Path(self.input_dir_edit.text())
        if not input_dir.exists() or not input_dir.is_dir():
            QMessageBox.warning(self, "Missing Folders", "Please select a valid input folder with images.")
            return
        images = [p for p in input_dir.iterdir() if p.is_file() and is_image_file(p)]
        if not images:
            QMessageBox.warning(self, "No Images", "No PNG or JPG images found in the input folder.")
            return
        # Batch FTP logic: ignore 'Enable FTP Upload' toggle, use FTP config if 'Use FTP as Output' is checked
        ftp_cfg = None
        if self.batch_use_ftp.isChecked():
            if not self.ftp_host.text():
                QMessageBox.warning(self, "FTP Required", "Please enter the FTP host to use FTP as output.")
                return
            try:
                port = int(self.ftp_port.text()) if self.ftp_port.text() else 2121
            except ValueError:
                port = 2121
            ftp_cfg = FTPConfig(
                host=self.ftp_host.text(),
                port=port,
                username=self.ftp_user.text() or None,
                password=self.ftp_pass.text() or None,
                upload_dir=self.ftp_dir.text() or "/"
            )
        output_dir = self.batch_output_dir if not self.batch_use_ftp.isChecked() else input_dir  # dummy, not used if FTP only
        result = process_batch_avatars(images, self.user_type, output_dir, ftp_cfg)
        msg = f"Batch complete!\nTotal avatars: {result.total}\nTransferred via FTP: {result.ftp_transferred}"
        QMessageBox.information(self, "Batch Result", msg)

    def browse_ftp_dir(self):
        if not self.ftp_host.text():
            QMessageBox.warning(self, "FTP Host Required", "Please enter the FTP host before browsing directories.")
            return
        try:
            port = int(self.ftp_port.text()) if self.ftp_port.text() else 2121
        except ValueError:
            port = 2121
        ftp_cfg = FTPConfig(
            host=self.ftp_host.text(),
            port=port,
            username=self.ftp_user.text() or None,
            password=self.ftp_pass.text() or None,
            upload_dir=self.ftp_dir.text() or "/"
        )
        dlg = FTPDirDialog(ftp_cfg, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.ftp_dir.setText(dlg.selected_dir)

    def on_batch_use_ftp_toggled(self):
        # Disable output dir selection if using FTP as output
        use_ftp = self.batch_use_ftp.isChecked()
        self.output_dir_edit.setDisabled(use_ftp)
        # Only disable browse/open for output dir, not input dir
        for btn in self.findChildren(QPushButton):
            if btn.text() in ["Browse", "Open"] and btn.parent() is not None and self.output_dir_edit in btn.parent().findChildren(QLineEdit):
                btn.setDisabled(use_ftp)
        self.on_config_edited()

    def on_config_edited(self):
        # Save all config to QSettings
        self.settings.setValue("ftp/host", self.ftp_host.text())
        self.settings.setValue("ftp/port", self.ftp_port.text())
        self.settings.setValue("ftp/user", self.ftp_user.text())
        self.settings.setValue("ftp/pass", self.ftp_pass.text())
        self.settings.setValue("ftp/dir", self.ftp_dir.text())
        self.settings.setValue("ftp/enabled", self.ftp_enable.isChecked())
        self.settings.setValue("batch/input_dir", self.input_dir_edit.text())
        self.settings.setValue("batch/output_dir", self.output_dir_edit.text())
        self.settings.setValue("batch/use_ftp", self.batch_use_ftp.isChecked())
        self.settings.setValue("user_type", "offline" if self.rb_offline.isChecked() else "local")

    def load_settings(self):
        self.ftp_host.setText(self.settings.value("ftp/host", ""))
        self.ftp_port.setText(self.settings.value("ftp/port", ""))
        self.ftp_user.setText(self.settings.value("ftp/user", ""))
        self.ftp_pass.setText(self.settings.value("ftp/pass", ""))
        self.ftp_dir.setText(self.settings.value("ftp/dir", "/"))
        self.ftp_enable.setChecked(self.settings.value("ftp/enabled", False, type=bool))
        self.input_dir_edit.setText(self.settings.value("batch/input_dir", ""))
        self.output_dir_edit.setText(self.settings.value("batch/output_dir", ""))
        self.batch_use_ftp.setChecked(self.settings.value("batch/use_ftp", False, type=bool))
        user_type = self.settings.value("user_type", "local")
        if user_type == "offline":
            self.rb_offline.setChecked(True)
        else:
            self.rb_local.setChecked(True)

    def open_batch_preview(self):
        input_dir = Path(self.input_dir_edit.text())
        if not input_dir.exists() or not input_dir.is_dir():
            QMessageBox.warning(self, "No Input Folder", "Please select a valid input folder first.")
            return
        images = [p for p in input_dir.iterdir() if p.is_file() and is_image_file(p)]
        if not images:
            QMessageBox.warning(self, "No Images", "No PNG or JPG images found in the input folder.")
            return
        self.show_batch_preview(images)

    def show_batch_preview(self, images):
        # Open the preview window as non-modal
        self._batch_preview = ImagePreviewDialog(images, self)
        self._batch_preview.setModal(False)
        self._batch_preview.show()

    @staticmethod
    def dark_stylesheet():
        return """
        QWidget { background: #181818; color: #f0f0f0; }
        QGroupBox { border: 1px solid #333; margin-top: 10px; }
        QGroupBox:title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }
        QLabel { color: #f0f0f0; }
        QPushButton { background: #222; color: #fff; border: 1px solid #444; padding: 8px 16px; border-radius: 4px; }
        QPushButton:hover { background: #333; }
        QRadioButton { color: #f0f0f0; }
        QLineEdit { background: #222; color: #fff; border: 1px solid #444; border-radius: 4px; padding: 4px; }
        """

class ImagePreviewDialog(QDialog):
    def __init__(self, image_paths, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Image Preview")
        self.setMinimumSize(600, 400)
        layout = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        grid = QGridLayout()
        for idx, img_path in enumerate(image_paths):
            label = QLabel()
            pixmap = QPixmap(str(img_path)).scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            label.setPixmap(pixmap)
            label.setFixedSize(110, 110)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(label, idx // 5, idx % 5)
        content.setLayout(grid)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.setLayout(layout)

def main():
    app = QApplication(sys.argv)
    win = AvatarMakerUI()
    win.show()
    sys.exit(app.exec()) 