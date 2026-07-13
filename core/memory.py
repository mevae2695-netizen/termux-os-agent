"""
SQLite tabanlı kural ve konum hafızası.
Tüm aktif kurallar, kaydedilmiş konumlar ve uygulama ayarları burada saklanır.
"""

import sqlite3
import json
import os
import uuid
from datetime import datetime
from typing import List, Optional


def _varsayilan_db_yolu() -> str:
    """
    Veritabanı dosyasının konumu.
    Gerçek bir APK'da Termux'a özgü /data/data/com.termux yolu erişilemez
    (uygulama kum havuzu dışıdır) — bunun yerine uygulamaya özel Android
    depolama dizinini (getFilesDir) pyjnius ile kullanıyoruz, tıpkı
    core/model_yoneticisi.py'deki model_dizini() ile aynı desende.
    """
    try:
        from jnius import autoclass  # type: ignore
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        ctx = PythonActivity.mActivity
        dizin = str(ctx.getFilesDir().getAbsolutePath())
    except Exception:
        # Geliştirme ortamı (masaüstü/Termux)
        dizin = os.path.join(os.environ.get("HOME", os.path.expanduser("~")), ".osagent")
    return os.path.join(dizin, "hafiza.db")


DB_YOLU = _varsayilan_db_yolu()


class Memory:
    def __init__(self, db_yolu: str = DB_YOLU):
        os.makedirs(os.path.dirname(db_yolu), exist_ok=True)
        self.db_yolu = db_yolu
        self._tabloları_olustur()

    def _baglanti(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_yolu)
        con.row_factory = sqlite3.Row
        return con

    def _tabloları_olustur(self):
        with self._baglanti() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS kurallar (
                    id          TEXT PRIMARY KEY,
                    baslik      TEXT NOT NULL,
                    aciklama    TEXT,
                    tetikleyici TEXT NOT NULL,
                    eylem_kodu  TEXT NOT NULL,
                    aktif       INTEGER DEFAULT 1,
                    olusturulma TEXT NOT NULL,
                    son_tetik   TEXT
                );

                CREATE TABLE IF NOT EXISTS konumlar (
                    etiket  TEXT PRIMARY KEY,
                    enlem   REAL NOT NULL,
                    boylam  REAL NOT NULL,
                    kayit   TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ayarlar (
                    anahtar TEXT PRIMARY KEY,
                    deger   TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chat_gecmisi (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    rol         TEXT NOT NULL,
                    icerik      TEXT NOT NULL,
                    zaman       TEXT NOT NULL
                );
            """)

    # ------------------------------------------------------------------
    # KURALLAR
    # ------------------------------------------------------------------
    def kural_ekle(self, baslik: str, aciklama: str,
                   tetikleyici: str, eylem_kodu: str) -> str:
        kural_id = str(uuid.uuid4())[:8]
        with self._baglanti() as con:
            con.execute(
                """INSERT INTO kurallar
                   (id, baslik, aciklama, tetikleyici, eylem_kodu, aktif, olusturulma)
                   VALUES (?, ?, ?, ?, ?, 1, ?)""",
                (kural_id, baslik, aciklama, tetikleyici,
                 eylem_kodu, datetime.now().isoformat())
            )
        return kural_id

    def kural_guncelle_aktif(self, kural_id: str, aktif: bool):
        with self._baglanti() as con:
            con.execute(
                "UPDATE kurallar SET aktif=? WHERE id=?",
                (1 if aktif else 0, kural_id)
            )

    def kural_sil(self, kural_id: str):
        with self._baglanti() as con:
            con.execute("DELETE FROM kurallar WHERE id=?", (kural_id,))

    def kural_son_tetik_guncelle(self, kural_id: str):
        with self._baglanti() as con:
            con.execute(
                "UPDATE kurallar SET son_tetik=? WHERE id=?",
                (datetime.now().isoformat(), kural_id)
            )

    def tum_kurallar(self) -> List[dict]:
        with self._baglanti() as con:
            rows = con.execute("SELECT * FROM kurallar ORDER BY olusturulma DESC").fetchall()
        return [dict(r) for r in rows]

    def aktif_kurallar(self) -> List[dict]:
        with self._baglanti() as con:
            rows = con.execute(
                "SELECT * FROM kurallar WHERE aktif=1"
            ).fetchall()
        return [dict(r) for r in rows]

    def kural_getir(self, kural_id: str) -> Optional[dict]:
        with self._baglanti() as con:
            row = con.execute(
                "SELECT * FROM kurallar WHERE id=?", (kural_id,)
            ).fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # KONUMLAR
    # ------------------------------------------------------------------
    def konum_kaydet(self, etiket: str, enlem: float, boylam: float):
        with self._baglanti() as con:
            con.execute(
                """INSERT INTO konumlar (etiket, enlem, boylam, kayit)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(etiket) DO UPDATE SET
                       enlem=excluded.enlem,
                       boylam=excluded.boylam,
                       kayit=excluded.kayit""",
                (etiket, enlem, boylam, datetime.now().isoformat())
            )

    def konum_getir(self, etiket: str) -> Optional[dict]:
        with self._baglanti() as con:
            row = con.execute(
                "SELECT * FROM konumlar WHERE etiket=?", (etiket,)
            ).fetchone()
        return dict(row) if row else None

    def tum_konumlar(self) -> List[dict]:
        with self._baglanti() as con:
            rows = con.execute("SELECT * FROM konumlar").fetchall()
        return [dict(r) for r in rows]

    def konum_sil(self, etiket: str):
        with self._baglanti() as con:
            con.execute("DELETE FROM konumlar WHERE etiket=?", (etiket,))

    # ------------------------------------------------------------------
    # AYARLAR
    # ------------------------------------------------------------------
    def ayar_yaz(self, anahtar: str, deger):
        serialized = json.dumps(deger, ensure_ascii=False)
        with self._baglanti() as con:
            con.execute(
                """INSERT INTO ayarlar (anahtar, deger) VALUES (?, ?)
                   ON CONFLICT(anahtar) DO UPDATE SET deger=excluded.deger""",
                (anahtar, serialized)
            )

    def ayar_oku(self, anahtar: str, varsayilan=None):
        with self._baglanti() as con:
            row = con.execute(
                "SELECT deger FROM ayarlar WHERE anahtar=?", (anahtar,)
            ).fetchone()
        if row:
            try:
                return json.loads(row["deger"])
            except Exception:
                return row["deger"]
        return varsayilan

    # ------------------------------------------------------------------
    # CHAT GEÇMİŞİ
    # ------------------------------------------------------------------
    def mesaj_ekle(self, rol: str, icerik: str):
        """rol: 'kullanici' | 'asistan' | 'sistem'"""
        with self._baglanti() as con:
            con.execute(
                "INSERT INTO chat_gecmisi (rol, icerik, zaman) VALUES (?, ?, ?)",
                (rol, icerik, datetime.now().isoformat())
            )

    def son_mesajlar(self, adet: int = 20) -> List[dict]:
        with self._baglanti() as con:
            rows = con.execute(
                "SELECT * FROM chat_gecmisi ORDER BY id DESC LIMIT ?", (adet,)
            ).fetchall()
        return list(reversed([dict(r) for r in rows]))

    def chat_gecmisini_temizle(self):
        with self._baglanti() as con:
            con.execute("DELETE FROM chat_gecmisi")
