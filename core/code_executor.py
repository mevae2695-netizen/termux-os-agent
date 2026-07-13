"""
Güvenli Kod Çalıştırma Motoru (Sandbox)
Üretilen Python kodlarını izole bir ortamda çalıştırır.
İzin hataları, çökmeler ve timeout'lar chat akışına mesaj olarak yansır.
"""

import traceback
import signal
import threading
from typing import Callable, Optional

from core.android_api import (
    wifi_ac, wifi_kapat, wifi_durumu,
    bluetooth_ac, bluetooth_kapat, bluetooth_bagli_cihazlar,
    ses_seviyesi_ayarla, sessiz_mod_ac, sessiz_mod_kapat, titresim_modu_ac,
    parlaklık_ayarla, otomatik_parlaklık_ac, tasarruf_modu_ac,
    konum_al, konum_kaydet, kayıtlı_konumda_mi,
    pil_durumu, pil_yuzde,
    fotograf_cek,
    sms_gonder, arama_yap, son_smsleri_getir,
    bildirim_gonder, toast_goster,
    rehber_ara,
    uygulama_ac, uygulama_kapat, yuklü_uygulamaları_listele,
    alarm_kur,
    dosya_oku, dosya_yaz,
    dinamik_internet_verisi_al, dinamik_shell_komutu_calistir,
)
from core.permission_manager import IzinYoneticisi

# ---------------------------------------------------------------------------
# Güvenli namespace — model kodu sadece bu fonksiyonlara erişebilir
# ---------------------------------------------------------------------------
GUVENLI_NAMESPACE = {
    "__builtins__": {
        "print": print,
        "range": range,
        "len": len,
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
        "list": list,
        "dict": dict,
        "tuple": tuple,
        "set": set,
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "sorted": sorted,
        "enumerate": enumerate,
        "zip": zip,
        "isinstance": isinstance,
        "hasattr": hasattr,
        "getattr": getattr,
        "None": None,
        "True": True,
        "False": False,
    },
    # Wi-Fi
    "wifi_ac": wifi_ac,
    "wifi_kapat": wifi_kapat,
    "wifi_durumu": wifi_durumu,
    # Bluetooth
    "bluetooth_ac": bluetooth_ac,
    "bluetooth_kapat": bluetooth_kapat,
    "bluetooth_bagli_cihazlar": bluetooth_bagli_cihazlar,
    # Ses
    "ses_seviyesi_ayarla": ses_seviyesi_ayarla,
    "sessiz_mod_ac": sessiz_mod_ac,
    "sessiz_mod_kapat": sessiz_mod_kapat,
    "titresim_modu_ac": titresim_modu_ac,
    # Ekran
    "parlaklık_ayarla": parlaklık_ayarla,
    "otomatik_parlaklık_ac": otomatik_parlaklık_ac,
    "tasarruf_modu_ac": tasarruf_modu_ac,
    # Konum
    "konum_al": konum_al,
    "konum_kaydet": konum_kaydet,
    "kayıtlı_konumda_mi": kayıtlı_konumda_mi,
    # Pil
    "pil_durumu": pil_durumu,
    "pil_yuzde": pil_yuzde,
    # Kamera
    "fotograf_cek": fotograf_cek,
    # İletişim
    "sms_gonder": sms_gonder,
    "arama_yap": arama_yap,
    "son_smsleri_getir": son_smsleri_getir,
    # Bildirim
    "bildirim_gonder": bildirim_gonder,
    "toast_goster": toast_goster,
    # Rehber
    "rehber_ara": rehber_ara,
    # Uygulama
    "uygulama_ac": uygulama_ac,
    "uygulama_kapat": uygulama_kapat,
    "yuklü_uygulamaları_listele": yuklü_uygulamaları_listele,
    # Zamanlayıcı
    "alarm_kur": alarm_kur,
    # Dosya
    "dosya_oku": dosya_oku,
    "dosya_yaz": dosya_yaz,
    # Evrensel anahtarlar
    "dinamik_internet_verisi_al": dinamik_internet_verisi_al,
    "dinamik_shell_komutu_calistir": dinamik_shell_komutu_calistir,
}


class SandboxSonucu:
    def __init__(self):
        self.basarili: bool = False
        self.cikti: str = ""
        self.hata: Optional[str] = None
        self.izin_hatasi: bool = False
        self.eksik_izinler: list = []
        self.sure_ms: float = 0.0


class KodSandbox:
    """Üretilen kodları güvenli şekilde çalıştıran sandbox."""

    ZAMAN_ASIMI_SN = 30

    def __init__(self):
        self.izin_yoneticisi = IzinYoneticisi()

    def calistir(self, kod: str,
                 ilerleme_cb: Optional[Callable[[str], None]] = None) -> SandboxSonucu:
        """
        Kodu sandbox'ta çalıştırır.
        ilerleme_cb: print() çıktılarını canlı iletmek için isteğe bağlı callback.
        """
        import time
        sonuc = SandboxSonucu()
        ciktilar = []

        # İzin ön kontrolü
        eksik = self.izin_yoneticisi.kod_icin_gerekli_izinler(kod)
        if eksik:
            sonuc.izin_hatasi = True
            sonuc.eksik_izinler = eksik
            sonuc.hata = self.izin_yoneticisi.izin_hata_mesajı(eksik)
            return sonuc

        # Print çıktılarını yakala
        def yakalayici(*args, **kwargs):
            metin = " ".join(str(a) for a in args)
            ciktilar.append(metin)
            if ilerleme_cb:
                ilerleme_cb(metin)

        namespace = {**GUVENLI_NAMESPACE, "print": yakalayici}

        # Thread'de çalıştır (timeout için)
        hata_kap = [None]
        bitti = threading.Event()

        def calistir_thread():
            try:
                exec(compile(kod, "<osagent>", "exec"), namespace)  # noqa: S102
            except PermissionError as e:
                hata_kap[0] = ("izin", str(e))
            except Exception as e:
                hata_kap[0] = ("genel", traceback.format_exc(limit=5))
            finally:
                bitti.set()

        t = threading.Thread(target=calistir_thread, daemon=True)
        baslangic = time.time()
        t.start()
        tamamlandi = bitti.wait(timeout=self.ZAMAN_ASIMI_SN)
        sonuc.sure_ms = round((time.time() - baslangic) * 1000, 1)

        if not tamamlandi:
            sonuc.hata = f"⏱️ Zaman aşımı: Kod {self.ZAMAN_ASIMI_SN} saniye içinde tamamlanamadı."
            return sonuc

        if hata_kap[0]:
            tur, mesaj = hata_kap[0]
            if tur == "izin":
                sonuc.izin_hatasi = True
                sonuc.hata = (
                    "⚠️ Küçük bir engel çıktı!\n\n"
                    "Bu görevi yapabilmem için gerekli bir izin kapalı görünüyor.\n"
                    "Lütfen Ayarlar → Uygulama İzinleri'ni kontrol edin."
                )
            else:
                # Teknik hata mesajını sadeleştir
                satırlar = mesaj.strip().split("\n")
                son_satir = satırlar[-1] if satırlar else mesaj
                sonuc.hata = f"⚠️ Görev çalışırken bir hata oluştu:\n`{son_satir}`"
            return sonuc

        sonuc.basarili = True
        sonuc.cikti = "\n".join(ciktilar) if ciktilar else "✅ Görev başarıyla tamamlandı."
        return sonuc

    def on_izle(self, kod: str) -> list:
        """
        Kodu çalıştırmadan önce güvenlik analizi yapar.
        Yasaklı pattern'ler içeriyorsa uyarı listesi döner.
        """
        uyarilar = []
        yasakli = [
            ("import os", "os modülü doğrudan kullanılamaz"),
            ("import sys", "sys modülü doğrudan kullanılamaz"),
            ("__import__", "__import__ kullanılamaz"),
            ("open(", "open() yerine dosya_oku() / dosya_yaz() kullanın"),
            ("subprocess", "subprocess yerine dinamik_shell_komutu_calistir() kullanın"),
            ("socket", "socket modülü kullanılamaz"),
            ("eval(", "eval() kullanılamaz"),
        ]
        for kalip, aciklama in yasakli:
            if kalip in kod:
                uyarilar.append(aciklama)
        return uyarilar


# Singleton
_sandbox = KodSandbox()


def kodu_calistir(kod: str,
                  ilerleme_cb: Optional[Callable[[str], None]] = None) -> SandboxSonucu:
    """Dışarıdan kullanılan ana arayüz."""
    return _sandbox.calistir(kod, ilerleme_cb)
