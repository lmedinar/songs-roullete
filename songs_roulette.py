#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Spotify Random Playlists GUI
- PyQt5 app with i18n (ES/EN/中文)
- Encrypted INI storage for Spotify OAuth credentials (Fernet)
- Updates local JSON DB with all playlists + tracks
- Generates random playlists from a source playlist
- Safe for PyInstaller packaging; works on Windows portable and Arch Linux.

Author: (you)
License: MIT
"""

import os
import sys
import json
import time

# import base64
import random
import traceback
from datetime import datetime
from dataclasses import dataclass

# ---- Third-party deps ----
# pip install PyQt5 spotipy cryptography
from PyQt5 import QtCore, QtGui, QtWidgets

from cryptography.fernet import Fernet, InvalidToken
from spotipy import Spotify, SpotifyException
from spotipy.oauth2 import SpotifyOAuth

# =======================
# ---- CONFIG GLOBAL ----
# =======================

APP_NAME = "Spotify Random Playlists"
DATA_JSON = "data.json"  # Base de datos local
INI_PATH = "config.ini"  # INI cifrado (en realidad un blob Fernet)
KEY_PATH = "key.bin"  # Clave simétrica Fernet
SETTINGS_JSON = "settings.json"  # Preferencias no sensibles (idioma, etc.)

# Tiempo de espera entre llamadas a la API (segundos). Ajustable:
API_SLEEP_SECONDS = 0.25

# Lote máximo que permite Spotify para add_tracks_to_playlist
ADD_BATCH_SIZE = 100

# Scopes necesarios
SCOPES = (
    "playlist-read-private "
    "playlist-read-collaborative "
    "playlist-modify-public "
    "playlist-modify-private "
    "user-library-read"
)

# =======================
# ---- I18N STRINGS  ----
# =======================

LANG = {
    "es": {
        "app_title": "Song Roulette - Generador de playlists aleatorias para Spotify",
        "menu_options": "Opciones",
        "menu_credentials": "Credenciales…",
        "menu_language": "Idioma…",
        "btn_update_db": "Actualizar Base de Datos",
        "updating_db": "Actualizando base de datos…",
        "db_updated_ok": "Base de datos actualizada",
        "db_updated_ok_msg": "Se actualizó correctamente la base de datos local.",
        "random_section": "Generación de playlist aleatorias",
        "num_songs": "Número de canciones:",
        "source_playlist": "Playlist de origen:",
        "playlist_name": "Nombre de la playlist:",
        "name_hint": "Dejar en blanco para usar: RANDOM - <fecha y hora actuales>",
        "btn_generate": "Generar playlist",
        "progress_add": "Agregando canciones…",
        "playlist_done": "Playlist generada con éxito",
        "error_title": "Error",
        "credentials_title": "Credenciales de Spotify",
        "client_id": "Client ID",
        "client_secret": "Client Secret",
        "redirect_uri": "Redirect URI",
        "verify": "Verificar y guardar",
        "cancel": "Cancelar",
        "credentials_ok": "Verificación exitosa",
        "credentials_ok_msg": "Las credenciales fueron verificadas y guardadas.",
        "credentials_fail": "No se pudieron verificar las credenciales.\n\nDetalle:\n{err}",
        "language_title": "Seleccionar idioma",
        "select_language": "Idioma:",
        "save": "Guardar",
        "must_auth_browser": "Se abrirá el navegador para autorizar tu cuenta de Spotify.",
        "no_playlists": "No hay playlists disponibles en la base de datos local.\nPrimero ejecuta 'Update database'.",
        "not_enough_tracks": "La playlist de origen tiene menos canciones que las solicitadas.\nSe usarán todas las disponibles.",
        "loading": "Cargando…",
    },
    "en": {
        "app_title": "Song Roulette - Random Playlist Generator for Spotify",
        "menu_options": "Options",
        "menu_credentials": "Credentials…",
        "menu_language": "Language…",
        "btn_update_db": "Update database",
        "updating_db": "Updating database…",
        "db_updated_ok": "Database updated",
        "db_updated_ok_msg": "Local database was updated successfully.",
        "random_section": "Random playlist generation",
        "num_songs": "Number of tracks:",
        "source_playlist": "Source playlist:",
        "playlist_name": "Playlist name:",
        "name_hint": "Leave empty to use: RANDOM - <current date & time>",
        "btn_generate": "Generate playlist",
        "progress_add": "Adding tracks…",
        "playlist_done": "Playlist created successfully",
        "error_title": "Error",
        "credentials_title": "Spotify Credentials",
        "client_id": "Client ID",
        "client_secret": "Client Secret",
        "redirect_uri": "Redirect URI",
        "verify": "Verify & Save",
        "cancel": "Cancel",
        "credentials_ok": "Verification successful",
        "credentials_ok_msg": "Credentials verified and saved.",
        "credentials_fail": "Could not verify credentials.\n\nDetails:\n{err}",
        "language_title": "Select language",
        "select_language": "Language:",
        "save": "Save",
        "must_auth_browser": "A browser window will open to authorize your Spotify account.",
        "no_playlists": "No playlists found in local DB.\nPlease run 'Update database' first.",
        "not_enough_tracks": "Source playlist has fewer tracks than requested.\nAll available will be used.",
        "loading": "Loading…",
    },
    "zh": {
        "app_title": "歌曲轮盘 - Spotify 随机播放列表生成器",
        "menu_options": "选项",
        "menu_credentials": "账号凭证…",
        "menu_language": "语言…",
        "btn_update_db": "更新数据库",
        "updating_db": "正在更新数据库…",
        "db_updated_ok": "数据库已更新",
        "db_updated_ok_msg": "已成功更新本地数据库。",
        "random_section": "生成随机播放列表",
        "num_songs": "歌曲数量：",
        "source_playlist": "源播放列表：",
        "playlist_name": "播放列表名称：",
        "name_hint": "留空则使用：RANDOM - <当前日期时间>",
        "btn_generate": "生成播放列表",
        "progress_add": "正在添加歌曲…",
        "playlist_done": "播放列表创建成功",
        "error_title": "错误",
        "credentials_title": "Spotify 账号凭证",
        "client_id": "Client ID",
        "client_secret": "Client Secret",
        "redirect_uri": "Redirect URI",
        "verify": "验证并保存",
        "cancel": "取消",
        "credentials_ok": "验证成功",
        "credentials_ok_msg": "凭据已验证并保存。",
        "credentials_fail": "无法验证凭据。\n\n详情：\n{err}",
        "language_title": "选择语言",
        "select_language": "语言：",
        "save": "保存",
        "must_auth_browser": "系统将打开浏览器来授权你的 Spotify 账号。",
        "no_playlists": "本地数据库中没有播放列表。\n请先运行“更新数据库”。",
        "not_enough_tracks": "来源播放列表的歌曲少于请求数量。\n将使用全部可用歌曲。",
        "loading": "正在加载…",
    },
}

DEFAULT_LANG = "en"

# ===========================
# ---- STORAGE / CRYPTO  ----
# ===========================


def ensure_key():
    """Ensure a Fernet key exists; create if missing."""
    if not os.path.exists(KEY_PATH):
        key = Fernet.generate_key()
        with open(KEY_PATH, "wb") as f:
            f.write(key)
    with open(KEY_PATH, "rb") as f:
        return f.read()


def encrypt_to_ini(plain_text: str):
    """Encrypt and write to INI_PATH."""
    key = ensure_key()
    f = Fernet(key)
    token = f.encrypt(plain_text.encode("utf-8"))
    with open(INI_PATH, "wb") as fh:
        fh.write(token)


def decrypt_from_ini() -> str:
    """Decrypt and return plaintext from INI_PATH."""
    if not os.path.exists(INI_PATH):
        return ""
    key = ensure_key()
    f = Fernet(key)
    with open(INI_PATH, "rb") as fh:
        blob = fh.read()
    try:
        return f.decrypt(blob).decode("utf-8")
    except InvalidToken:
        return ""


def load_settings():
    """Load non-sensitive settings (language)."""
    if not os.path.exists(SETTINGS_JSON):
        return {"language": DEFAULT_LANG}
    try:
        with open(SETTINGS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"language": DEFAULT_LANG}


def save_settings(settings: dict):
    """Save non-sensitive settings."""
    with open(SETTINGS_JSON, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


@dataclass
class SpotifyCreds:
    client_id: str
    client_secret: str
    redirect_uri: str


def save_creds(creds: SpotifyCreds):
    """Store Spotify credentials as an INI-like plaintext, encrypted as a whole."""
    content = (
        "[spotify]\n"
        f"client_id={creds.client_id}\n"
        f"client_secret={creds.client_secret}\n"
        f"redirect_uri={creds.redirect_uri}\n"
    )
    encrypt_to_ini(content)


def load_creds() -> SpotifyCreds or None:
    """Load creds from encrypted INI. Return None if missing/invalid."""
    plain = decrypt_from_ini()
    if not plain:
        return None
    lines = [ln.strip() for ln in plain.splitlines() if ln.strip()]
    kv = {}
    for ln in lines:
        if ln.startswith("["):
            continue
        if "=" in ln:
            k, v = ln.split("=", 1)
            kv[k.strip()] = v.strip()
    if all(k in kv for k in ("client_id", "client_secret", "redirect_uri")):
        return SpotifyCreds(kv["client_id"], kv["client_secret"], kv["redirect_uri"])
    return None


# ===========================
# ---- OAUTH / CLIENT    ----
# ===========================


def make_spotify(creds: SpotifyCreds) -> Spotify:
    """Build a Spotify client with OAuth (opens browser on first auth)."""
    auth = SpotifyOAuth(
        client_id=creds.client_id,
        client_secret=creds.client_secret,
        redirect_uri=creds.redirect_uri,
        scope=SCOPES,
        open_browser=True,
        cache_path=".cache-spotify-rand",  # token cache on disk
    )
    token = auth.get_access_token(as_dict=False)  # triggers browser if needed
    if not token:
        raise RuntimeError("No OAuth token obtained.")
    return Spotify(auth_manager=auth)


def verify_creds(creds: SpotifyCreds) -> bool:
    """Try to authenticate and hit a trivial endpoint."""
    sp = make_spotify(creds)
    me = sp.current_user()
    return bool(me and me.get("id"))


def _liked_name(lang_key: str) -> str:
    # Puedes ajustar las traducciones si quieres otro matiz
    return {
        "es": "Me gusta",
        "en": "Liked Songs",
        "zh": "我喜欢的歌曲",
    }.get(lang_key, "Liked Songs")


# ===========================
# ---- THREADING WORKERS ----
# ===========================


class WorkerSignals(QtCore.QObject):
    progress = QtCore.pyqtSignal(int)  # 0-100
    status = QtCore.pyqtSignal(str)  # status text
    error = QtCore.pyqtSignal(str)  # error text
    done = QtCore.pyqtSignal(object)  # payload (e.g., result)


class UpdateDBWorker(QtCore.QRunnable):
    """
    Background task: enumerate all playlists and tracks into data.json
    Emits progress by total tracks.
    """

    def __init__(self, lang_key: str, creds: SpotifyCreds):
        super().__init__()
        self.signals = WorkerSignals()
        self.lang_key = lang_key
        self.creds = creds

    def run(self):
        try:
            sp = make_spotify(self.creds)
            # First pass: count total tracks across all playlists
            playlists = []
            limit = 50
            offset = 0
            total_playlists = None

            while True:
                resp = sp.current_user_playlists(limit=limit, offset=offset)
                if total_playlists is None:
                    total_playlists = resp.get("total", 0)
                items = resp.get("items", [])
                playlists.extend(items)
                offset += len(items)
                if not items or offset >= total_playlists:
                    break
                time.sleep(API_SLEEP_SECONDS)

            # Gather total tracks number
            total_tracks = 0
            for pl in playlists:
                total_tracks += pl.get("tracks", {}).get("total", 0)

            # --- NEW: count liked songs (saved tracks) ---
            liked_limit = 50
            liked_total = 0
            try:
                liked_first = sp.current_user_saved_tracks(limit=liked_limit, offset=0)
                liked_total = liked_first.get("total", 0) or 0
            except Exception:
                liked_total = 0

            total_tracks += liked_total

            # Avoid division by zero
            total_tracks = max(total_tracks, 1)

            # Second pass: fetch tracks for each playlist
            db = {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "playlists": [],
            }
            done_tracks = 0

            for pl in playlists:
                pl_entry = {
                    "id": pl["id"],
                    "name": pl["name"],
                    "owner": pl.get("owner", {}).get("display_name") or "",
                    "tracks": [],
                }
                # paginate tracks
                t_limit = 100
                t_offset = 0
                while True:
                    tr = sp.playlist_items(pl["id"], limit=t_limit, offset=t_offset)
                    items = tr.get("items", [])
                    for it in items:
                        track = it.get("track") or {}
                        if not track:
                            continue
                        pl_entry["tracks"].append(
                            {
                                "id": track.get("id"),
                                "name": track.get("name"),
                                "uri": track.get("uri"),
                                "artists": [
                                    a.get("name") for a in track.get("artists", []) if a
                                ],
                                "album": track.get("album", {}).get("name"),
                            }
                        )
                        done_tracks += 1
                        pct = int((done_tracks / total_tracks) * 100)
                        self.signals.progress.emit(min(pct, 100))
                    t_offset += len(items)
                    if not items or len(items) < t_limit:
                        break
                    time.sleep(API_SLEEP_SECONDS)
                db["playlists"].append(pl_entry)

            # --- NEW: fetch liked/saved tracks as a virtual playlist ---
            liked_tracks = []
            t_limit = 50
            t_offset = 0

            try:
                while True:
                    saved = sp.current_user_saved_tracks(limit=t_limit, offset=t_offset)
                    items = saved.get("items", [])
                    for it in items:
                        track = (it or {}).get("track") or {}
                        if not track:
                            continue
                        liked_tracks.append(
                            {
                                "id": track.get("id"),
                                "name": track.get("name"),
                                "uri": track.get("uri"),
                                "artists": [
                                    a.get("name") for a in track.get("artists", []) if a
                                ],
                                "album": track.get("album", {}).get("name"),
                            }
                        )
                        # Avanza la barra de progreso usando el total combinado
                        done_tracks += 1
                        pct = int((done_tracks / total_tracks) * 100)
                        self.signals.progress.emit(min(pct, 100))
                    t_offset += len(items)
                    if not items or len(items) < t_limit:
                        break
                    time.sleep(API_SLEEP_SECONDS)

                # Inserta la playlist virtual al DB
                if liked_tracks:
                    db["playlists"].append(
                        {
                            "id": "__liked__",  # ID virtual
                            "name": _liked_name(self.lang_key),  # Nombre localizado
                            "owner": "",  # sin dueño visible
                            "tracks": liked_tracks,
                        }
                    )

            except Exception:
                # Si falla, simplemente no la añadimos (no rompemos la actualización)
                pass

            with open(DATA_JSON, "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, indent=2)

            self.signals.done.emit(db)
        except Exception as e:
            self.signals.error.emit(
                f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            )


class GenerateRandomWorker(QtCore.QRunnable):
    """
    Background task: create a random playlist from local DB source and push to Spotify.
    """

    def __init__(
        self,
        lang_key: str,
        creds: SpotifyCreds,
        source_playlist_id: str,
        requested_n: int,
        new_name: str,
        tracks_in_source: list,
    ):
        super().__init__()
        self.signals = WorkerSignals()
        self.lang_key = lang_key
        self.creds = creds
        self.source_playlist_id = source_playlist_id
        self.requested_n = requested_n
        self.new_name = new_name
        self.tracks_in_source = tracks_in_source  # list of track URIs

    def run(self):
        try:
            sp = make_spotify(self.creds)
            me = sp.current_user()
            user_id = me["id"]

            uris = [t["uri"] for t in self.tracks_in_source if t.get("uri")]
            if not uris:
                raise RuntimeError("Source playlist has no tracks with URIs.")

            if self.requested_n > len(uris):
                # use all available
                chosen = uris
            else:
                chosen = random.sample(uris, self.requested_n)

            # Create playlist
            playlist = sp.user_playlist_create(
                user=user_id,
                name=self.new_name,
                public=False,
                description="Generated by Spotify Random Playlists",
            )

            # Add in batches
            total = len(chosen)
            added = 0
            for i in range(0, total, ADD_BATCH_SIZE):
                batch = chosen[i : i + ADD_BATCH_SIZE]
                sp.playlist_add_items(playlist_id=playlist["id"], items=batch)
                added += len(batch)
                pct = int((added / total) * 100)
                self.signals.progress.emit(min(pct, 100))
                time.sleep(API_SLEEP_SECONDS)

            self.signals.done.emit(
                {"playlist_id": playlist["id"], "name": playlist["name"]}
            )
        except Exception as e:
            self.signals.error.emit(
                f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            )


# =======================
# ---- DIALOGS (UI)  ----
# =======================


class CredentialsDialog(QtWidgets.QDialog):
    """Dialog to set Spotify OAuth credentials and verify."""

    def __init__(self, parent, lang_key: str, initial: SpotifyCreds = None):
        super().__init__(parent)
        self.lang_key = lang_key
        self.setWindowTitle(LANG[lang_key]["credentials_title"])
        self.setModal(True)

        self.clientIdEdit = QtWidgets.QLineEdit()
        self.clientSecretEdit = QtWidgets.QLineEdit()
        self.clientSecretEdit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.redirectUriEdit = QtWidgets.QLineEdit()

        if initial:
            self.clientIdEdit.setText(initial.client_id)
            self.clientSecretEdit.setText(initial.client_secret)
            self.redirectUriEdit.setText(initial.redirect_uri)

        form = QtWidgets.QFormLayout()
        form.addRow(LANG[lang_key]["client_id"], self.clientIdEdit)
        form.addRow(LANG[lang_key]["client_secret"], self.clientSecretEdit)
        form.addRow(LANG[lang_key]["redirect_uri"], self.redirectUriEdit)

        self.infoLabel = QtWidgets.QLabel(LANG[lang_key]["must_auth_browser"])
        self.infoLabel.setWordWrap(True)
        self.infoLabel.setStyleSheet("color: #666;")

        self.btnVerify = QtWidgets.QPushButton(LANG[lang_key]["verify"])
        self.btnCancel = QtWidgets.QPushButton(LANG[lang_key]["cancel"])
        self.btnVerify.clicked.connect(self.on_verify)
        self.btnCancel.clicked.connect(self.reject)

        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(self.btnVerify)
        btns.addWidget(self.btnCancel)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.infoLabel)
        layout.addLayout(btns)

        self.resize(480, 220)

    def on_verify(self):
        cid = self.clientIdEdit.text().strip()
        csec = self.clientSecretEdit.text().strip()
        ruri = self.redirectUriEdit.text().strip()
        creds = SpotifyCreds(cid, csec, ruri)
        try:
            ok = verify_creds(creds)
            if ok:
                save_creds(creds)
                QtWidgets.QMessageBox.information(
                    self,
                    LANG[self.lang_key]["credentials_ok"],
                    LANG[self.lang_key]["credentials_ok_msg"],
                )
                self.accept()
                return
            else:
                QtWidgets.QMessageBox.critical(
                    self,
                    LANG[self.lang_key]["error_title"],
                    LANG[self.lang_key]["credentials_fail"].format(err="Unknown"),
                )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                LANG[self.lang_key]["error_title"],
                LANG[self.lang_key]["credentials_fail"].format(err=str(e)),
            )


class LanguageDialog(QtWidgets.QDialog):
    """Dialog to select UI language."""

    def __init__(self, parent, lang_key: str):
        super().__init__(parent)
        self.setModal(True)
        self.lang_key = lang_key
        self.setWindowTitle(LANG[lang_key]["language_title"])

        self.combo = QtWidgets.QComboBox()
        # Display labels localized to current language
        # but store language codes as data
        labels = {"es": "Español", "en": "English", "zh": "中文（简体）"}
        for code, label in labels.items():
            self.combo.addItem(label, code)
        # set current
        idx = self.combo.findData(lang_key)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)

        form = QtWidgets.QFormLayout()
        form.addRow(LANG[lang_key]["select_language"], self.combo)

        self.btnSave = QtWidgets.QPushButton(LANG[lang_key]["save"])
        self.btnCancel = QtWidgets.QPushButton(LANG[lang_key]["cancel"])
        self.btnSave.clicked.connect(self.accept)
        self.btnCancel.clicked.connect(self.reject)

        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(self.btnSave)
        btns.addWidget(self.btnCancel)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(btns)
        self.resize(360, 140)

    def selected_language(self) -> str:
        return self.combo.currentData()


# =======================
# ---- MAIN WINDOW   ----
# =======================


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, lang_key: str):
        super().__init__()
        self.lang_key = lang_key
        self.thread_pool = QtCore.QThreadPool()

        self.setWindowTitle(LANG[lang_key]["app_title"])
        self.setMinimumSize(720, 520)

        # ---- Menu ----
        menubar = self.menuBar()
        self.menuOptions = menubar.addMenu(LANG[lang_key]["menu_options"])

        self.actCreds = QtWidgets.QAction(LANG[lang_key]["menu_credentials"], self)
        self.actLang = QtWidgets.QAction(LANG[lang_key]["menu_language"], self)
        self.menuOptions.addAction(self.actCreds)
        self.menuOptions.addAction(self.actLang)

        self.actCreds.triggered.connect(self.open_credentials)
        self.actLang.triggered.connect(self.open_language)

        # ---- Central Widget ----
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        v = QtWidgets.QVBoxLayout(central)

        # Update DB
        self.btnUpdate = QtWidgets.QPushButton(LANG[lang_key]["btn_update_db"])
        self.btnUpdate.setFixedWidth(350)
        self.btnUpdate.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btnUpdate.clicked.connect(self.on_update_db)

        topRow = QtWidgets.QHBoxLayout()
        topRow.addStretch(1)
        topRow.addWidget(self.btnUpdate)
        topRow.addStretch(1)

        self.progressDB = QtWidgets.QProgressBar()
        self.progressDB.setRange(0, 100)
        self.progressDB.setValue(0)
        self.progressDB.setTextVisible(True)
        self.progressDB.setFixedWidth(420)

        progRow = QtWidgets.QHBoxLayout()
        progRow.addStretch(1)
        progRow.addWidget(self.progressDB)
        progRow.addStretch(1)

        v.addLayout(topRow)
        v.addLayout(progRow)

        v.addWidget(self._hline())

        # Random generation section

        self.secTitle = QtWidgets.QLabel(f"<b>{LANG[lang_key]['random_section']}</b>")
        v.addWidget(self.secTitle)
        # secTitle = QtWidgets.QLabel(f"<b>{LANG[lang_key]['random_section']}</b>")
        # secTitle = QtWidgets.QLabel()
        # v.addWidget(secTitle)

        form = QtWidgets.QFormLayout()

        # Labels como widgets dedicados (para poder re-traducir)
        lblNumSongs = QtWidgets.QLabel()
        lblSource = QtWidgets.QLabel()
        lblPlaylistName = QtWidgets.QLabel()

        self.spinCount = QtWidgets.QSpinBox()
        self.spinCount.setMinimum(1)
        self.spinCount.setMaximum(10000)
        self.spinCount.setValue(20)

        self.comboSource = QtWidgets.QComboBox()
        self.comboSource.setMinimumWidth(360)

        self.editName = QtWidgets.QLineEdit()
        self.hintName = QtWidgets.QLabel(LANG[lang_key]["name_hint"])
        self.hintName.setStyleSheet("color:#666; font-size: 13px;")
        self.hintName.setWordWrap(True)
        self.tracksLabel = QtWidgets.QLabel(LANG[lang_key]["num_songs"])
        self.playlistEleccion = QtWidgets.QLabel(LANG[lang_key]["source_playlist"])
        self.playlistName = QtWidgets.QLabel(LANG[lang_key]["playlist_name"])

        form.addRow(self.tracksLabel, self.spinCount)
        form.addRow(self.playlistEleccion, self.comboSource)
        form.addRow(self.playlistName, self.editName)
        form.addRow("", self.hintName)

        v.addLayout(form)

        self.btnGenerate = QtWidgets.QPushButton(LANG[lang_key]["btn_generate"])
        self.btnGenerate.setFixedWidth(220)
        self.btnGenerate.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btnGenerate.clicked.connect(self.on_generate)

        genRow = QtWidgets.QHBoxLayout()
        genRow.addStretch(1)
        genRow.addWidget(self.btnGenerate)
        genRow.addStretch(1)

        v.addLayout(genRow)

        self.progressGen = QtWidgets.QProgressBar()
        self.progressGen.setRange(0, 100)
        self.progressGen.setValue(0)
        self.progressGen.setTextVisible(True)
        self.progressGen.setFixedWidth(420)

        genProgRow = QtWidgets.QHBoxLayout()
        genProgRow.addStretch(1)
        genProgRow.addWidget(self.progressGen)
        genProgRow.addStretch(1)

        v.addLayout(genProgRow)

        # Load local DB (if exists) to fill comboSource
        self.local_db = self.load_local_db()
        self.refresh_source_combo()

        self._set_enabled(True)

    # -------- Helpers UI --------
    def _hline(self):
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        return line

    def retranslate(self):
        """Update texts when language changes."""
        self.setWindowTitle(LANG[self.lang_key]["app_title"])
        self.menuOptions.setTitle(LANG[self.lang_key]["menu_options"])
        self.actCreds.setText(LANG[self.lang_key]["menu_credentials"])
        self.actLang.setText(LANG[self.lang_key]["menu_language"])
        self.btnUpdate.setText(LANG[self.lang_key]["btn_update_db"])
        self.hintName.setText(LANG[self.lang_key]["name_hint"])
        self.btnGenerate.setText(LANG[self.lang_key]["btn_generate"])
        self.tracksLabel.setText(LANG[self.lang_key]["num_songs"])
        self.playlistEleccion.setText(LANG[self.lang_key]["source_playlist"])
        self.playlistName.setText(LANG[self.lang_key]["playlist_name"])
        self.secTitle.setText(f"<b>{LANG[self.lang_key]['random_section']}</b>")
        # Labels in the form are static; easiest is to reconstruct:
        # (In a production app, keep references to QLabel form items.)

    def _set_enabled(self, enabled: bool):
        """Enable/disable interactive widgets."""
        self.menuBar().setEnabled(enabled)
        self.btnUpdate.setEnabled(enabled)
        self.spinCount.setEnabled(enabled)
        self.comboSource.setEnabled(enabled)
        self.editName.setEnabled(enabled)
        self.btnGenerate.setEnabled(enabled)

    def show_error(self, msg: str):
        QtWidgets.QMessageBox.critical(self, LANG[self.lang_key]["error_title"], msg)

    def show_info(self, title: str, msg: str):
        QtWidgets.QMessageBox.information(self, title, msg)

    def load_local_db(self):
        if not os.path.exists(DATA_JSON):
            return None
        try:
            with open(DATA_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    # def refresh_source_combo(self):
    #     self.comboSource.clear()
    #     if not self.local_db or not self.local_db.get("playlists"):
    #         self.comboSource.addItem("—")
    #         return
    #     for pl in self.local_db["playlists"]:
    #         self.comboSource.addItem(pl["name"], pl["id"])

    def refresh_source_combo(self):
        self.comboSource.clear()
        if not self.local_db or not self.local_db.get("playlists"):
            self.comboSource.addItem("—")
            return

        # Ordenar playlists de mayor a menor según el número de canciones
        playlists_sorted = sorted(
            self.local_db["playlists"],
            key=lambda p: len(p.get("tracks", [])),
            reverse=True,
        )

        for pl in playlists_sorted:
            name = f"{pl['name']}  ({len(pl.get('tracks', []))})"
            self.comboSource.addItem(name, pl["id"])

    def get_creds_or_prompt(self) -> SpotifyCreds or None:
        creds = load_creds()
        if creds:
            # quick verify silently
            try:
                if verify_creds(creds):
                    return creds
            except Exception:
                # Fall back to dialog
                pass

        dlg = CredentialsDialog(self, self.lang_key, initial=creds)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            return load_creds()
        return None

    # -------- Menu actions --------
    def open_credentials(self):
        creds = load_creds()
        dlg = CredentialsDialog(self, self.lang_key, initial=creds)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            # Verified and saved inside dialog
            pass

    def open_language(self):
        dlg = LanguageDialog(self, self.lang_key)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            new_lang = dlg.selected_language()
            if new_lang and new_lang in LANG and new_lang != self.lang_key:
                self.lang_key = new_lang
                settings = load_settings()
                settings["language"] = new_lang
                save_settings(settings)
                self.retranslate()

    # -------- Actions --------
    def on_update_db(self):
        creds = self.get_creds_or_prompt()
        if not creds:
            return
        self._set_enabled(False)
        self.progressDB.setValue(0)

        worker = UpdateDBWorker(self.lang_key, creds)
        worker.signals.progress.connect(self.progressDB.setValue)
        worker.signals.error.connect(self._on_worker_error)
        worker.signals.done.connect(self._on_db_done)
        self.thread_pool.start(worker)

    def _on_worker_error(self, msg: str):
        self._set_enabled(True)
        self.show_error(msg)

    def _on_db_done(self, db):
        self.local_db = db
        self.refresh_source_combo()
        self._set_enabled(True)
        self.show_info(
            LANG[self.lang_key]["db_updated_ok"],
            LANG[self.lang_key]["db_updated_ok_msg"],
        )

    def on_generate(self):
        # Preconditions: must have local DB
        if not self.local_db or not self.local_db.get("playlists"):
            self.show_error(LANG[self.lang_key]["no_playlists"])
            return

        creds = self.get_creds_or_prompt()
        if not creds:
            return

        count = int(self.spinCount.value())
        idx = self.comboSource.currentIndex()
        src_id = self.comboSource.itemData(idx)
        if not src_id or src_id == "—":
            self.show_error(LANG[self.lang_key]["no_playlists"])
            return

        # Resolve tracks for selected playlist from local DB
        tracks = []
        for pl in self.local_db["playlists"]:
            if pl["id"] == src_id:
                tracks = pl.get("tracks", [])
                break

        if not tracks:
            self.show_error(LANG[self.lang_key]["no_playlists"])
            return

        entered_name = self.editName.text().strip()
        if not entered_name:
            entered_name = "RANDOM - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # If fewer tracks than requested, warn but continue
        if count > len(tracks):
            QtWidgets.QMessageBox.warning(
                self, APP_NAME, LANG[self.lang_key]["not_enough_tracks"]
            )
            count = len(tracks)

        self._set_enabled(False)
        self.progressGen.setValue(0)

        worker = GenerateRandomWorker(
            self.lang_key, creds, src_id, count, entered_name, tracks_in_source=tracks
        )
        worker.signals.progress.connect(self.progressGen.setValue)
        worker.signals.error.connect(self._on_worker_error_gen)
        worker.signals.done.connect(self._on_gen_done)
        self.thread_pool.start(worker)

    def _on_worker_error_gen(self, msg: str):
        self._set_enabled(True)
        self.show_error(msg)

    def _on_gen_done(self, payload):
        self._set_enabled(True)
        self.progressGen.setValue(100)
        QtWidgets.QMessageBox.information(
            self, APP_NAME, LANG[self.lang_key]["playlist_done"]
        )


# =======================
# ---- APP STARTUP   ----
# =======================


def main():
    # High-DPI friendly
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)

    # Load language setting
    settings = load_settings()
    lang_key = settings.get("language", DEFAULT_LANG)
    if lang_key not in LANG:
        lang_key = DEFAULT_LANG

    win = MainWindow(lang_key)
    win.show()

    # On first run, if no creds or invalid, the first "Update DB" or "Generate" will prompt.
    # If you want to force asking at startup, uncomment:
    # _ = win.get_creds_or_prompt()

    sys.exit(app.exec_())


if __name__ == "__main__":
    # Improve compatibility with PyInstaller
    try:
        import multiprocessing

        multiprocessing.freeze_support()
    except Exception:
        pass
    main()
