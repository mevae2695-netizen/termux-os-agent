"""
Model Yöneticisi
İlk açılışta modeli indirir, yerel depolamaya kaydeder ve
yönetir. Termux bağımlılığı yoktur — sadece standart Android
uygulama depolama dizini kullanılır.
"""

import os
import ssl
import threading
import urllib.request
import hashlib
import json
from typing import Callable, Optional

# Bazı Android cihazlarda/derlemelerinde Python'un ssl modülü sistem CA
# deposunu bulamayıp "CERTIFICATE_VERIFY_FAILED" hatası verebilir. certifi
# paketiyle gelen güncel CA paketini açıkça kullanarak buna karşı önlem
# alıyoruz. certifi yoksa (ör. masaüstü/Termux) varsayılan bağlama düşer.
try:
    import certifi
    _SSL_BAGLAM = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _SSL_BAGLAM = ssl.create_default_context()


# ---------------------------------------------------------------------------
# Kullanılabilir modeller kataloğu
# ---------------------------------------------------------------------------
MODEL_KATALOGU = {
    "phi3_mini_q4": {
        "isim": "Phi-3 Mini (Önerilen)",
        "aciklama": "Microsoft · ~2.2 GB · Türkçe anlama çok güçlü",
        "url": "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf",
        "dosya": "phi3-mini-q4.gguf",
        "boyut_mb": 2200,
        "sha256": None,  # İsteğe bağlı doğrulama
    },
    "gemma2b_q4": {
        "isim": "Gemma 2B (Hafif)",
        "aciklama": "Google · ~1.5 GB · Daha hızlı, biraz daha az doğru",
        "url": "https://huggingface.co/google/gemma-2b-it-GGUF/resolve/main/gemma-2b-it-q4_k_m.gguf",
        "dosya": "gemma2b-q4.gguf",
        "boyut_mb": 1500,
        "sha256": None,
    },
    "tinyllama_q4": {
        "isim": "TinyLlama 1.1B (Ultra Hafif)",
        "aciklama": "~600 MB · Eski telefon veya düşük depolama için",
        "url": "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.q4_k_m.gguf",
        "dosya": "tinyllama-q4.gguf",
        "boyut_mb": 600,
        "sha256": None,
    },
}


def model_dizini() -> str:
    """
    Android uygulama depolama dizini.
    Termux gerektirmez — standart Android iç depolama.
    /sdcard/Android/data/com.osagent.app/files/models/
    """
    try:
        from jnius import autoclass  # type: ignore
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        ctx = PythonActivity.mActivity
        external = ctx.getExternalFilesDir(None)
        if external:
            dizin = os.path.join(str(external.getAbsolutePath()), "models")
        else:
            dizin = os.path.join(str(ctx.getFilesDir().getAbsolutePath()), "models")
    except Exception:
        # Geliştirme / Termux ortamı
        dizin = os.path.join(
            os.environ.get("HOME", os.path.expanduser("~")),
            ".osagent", "models"
        )
    os.makedirs(dizin, exist_ok=True)
    return dizin


def model_yolu(model_anahtari: str) -> str:
    bilgi = MODEL_KATALOGU.get(model_anahtari, {})
    dosya = bilgi.get("dosya", model_anahtari + ".gguf")
    return os.path.join(model_dizini(), dosya)


def model_yuklu_mu(model_anahtari: str) -> bool:
    yol = model_yolu(model_anahtari)
    return os.path.isfile(yol) and os.path.getsize(yol) > 10_000_000


def herhangi_model_var_mi() -> Optional[str]:
    """Yüklü herhangi bir modelin anahtarını döner, yoksa None."""
    for anahtar in MODEL_KATALOGU:
        if model_yuklu_mu(anahtar):
            return anahtar
    # Özel yol var mı kontrol et
    return None


class ModelIndirici:
    """
    Arka planda model dosyasını indirir.
    İlerleme callback'i ile UI'a anlık bilgi gönderir.
    """

    def __init__(self):
        self._iptal = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def indir(
        self,
        model_anahtari: str,
        ilerleme_cb: Callable[[float, str], None],  # (yuzde, mesaj)
        tamamlandi_cb: Callable[[bool, str], None],  # (basarili, mesaj)
    ):
        self._iptal.clear()
        self._thread = threading.Thread(
            target=self._indir_thread,
            args=(model_anahtari, ilerleme_cb, tamamlandi_cb),
            daemon=True,
        )
        self._thread.start()

    def iptal_et(self):
        self._iptal.set()

    def _indir_thread(self, model_anahtari, ilerleme_cb, tamamlandi_cb):
        bilgi = MODEL_KATALOGU.get(model_anahtari)
        if not bilgi:
            tamamlandi_cb(False, "Bilinmeyen model anahtarı.")
            return

        url = bilgi["url"]
        hedef_yol = model_yolu(model_anahtari)
        gecici_yol = hedef_yol + ".tmp"

        try:
            ilerleme_cb(0.0, "Bağlantı kuruluyor…")

            istek = urllib.request.Request(url, headers={"User-Agent": "OSAgent/1.0"})
            with urllib.request.urlopen(istek, timeout=30, context=_SSL_BAGLAM) as yanit:
                toplam = int(yanit.headers.get("Content-Length", 0))
                indirilen = 0
                blok = 65536  # 64 KB

                with open(gecici_yol, "wb") as f:
                    while True:
                        if self._iptal.is_set():
                            f.close()
                            _dosya_sil(gecici_yol)
                            tamamlandi_cb(False, "İndirme iptal edildi.")
                            return

                        veri = yanit.read(blok)
                        if not veri:
                            break
                        f.write(veri)
                        indirilen += len(veri)

                        if toplam > 0:
                            yuzde = indirilen / toplam
                            mb_indirilen = indirilen / 1_048_576
                            mb_toplam = toplam / 1_048_576
                            mesaj = f"{mb_indirilen:.0f} MB / {mb_toplam:.0f} MB"
                        else:
                            yuzde = 0.5
                            mesaj = f"{indirilen / 1_048_576:.0f} MB indirildi"

                        ilerleme_cb(yuzde, mesaj)

            # SHA256 doğrulama (hash tanımlıysa)
            beklenen = bilgi.get("sha256")
            if beklenen:
                ilerleme_cb(0.99, "Dosya doğrulanıyor…")
                gercek = _sha256(gecici_yol)
                if gercek != beklenen:
                    _dosya_sil(gecici_yol)
                    tamamlandi_cb(False, "Dosya bozuk — lütfen tekrar deneyin.")
                    return

            # Geçiciyi kalıcıya taşı
            os.rename(gecici_yol, hedef_yol)
            ilerleme_cb(1.0, "Tamamlandı!")
            tamamlandi_cb(True, hedef_yol)

        except OSError as e:
            _dosya_sil(gecici_yol)
            if "No space" in str(e):
                tamamlandi_cb(False, "⚠️ Depolama alanı yetersiz. Boş alan açın ve tekrar deneyin.")
            else:
                tamamlandi_cb(False, f"Dosya yazma hatası: {e}")
        except Exception as e:
            _dosya_sil(gecici_yol)
            tamamlandi_cb(False, f"İndirme hatası: {e}")


def _dosya_sil(yol: str):
    try:
        if os.path.exists(yol):
            os.remove(yol)
    except Exception:
        pass


def _sha256(yol: str) -> str:
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for blok in iter(lambda: f.read(65536), b""):
            h.update(blok)
    return h.hexdigest()
