"""
Arka Plan Servisi — "Ölmez Mimar"
Kullanıcı uygulamayı kapatsa bile aktif kuralları 5 saniyede bir kontrol eder.
Foreground Service olarak çalışır; IMPORTANCE_MIN seviyesinde bildirim kullanır
(sistem tarafından gizlenir — bildirim çubuğunda görünmez).

Android Foreground Service entegrasyonu buildozer.spec üzerinden yapılır.
Bu dosya service.py ile aynı süreçte veya ayrı bir Android Service process'inde çalışır.
"""

import time
import threading
import logging
from typing import Optional

from core.memory import Memory
from core.code_executor import kodu_calistir

logger = logging.getLogger("ArkaplanServisi")


class KuralDegerlendirici:
    """Tetikleyici koşulunu değerlendirir."""

    def __init__(self, memory: Memory):
        self.memory = memory
        self._son_saat_tetik: dict = {}  # kural_id → son tetiklenme zamanı

    def tetiklenmeli_mi(self, kural: dict) -> bool:
        tetik = kural.get("tetikleyici", "anlik")
        kural_id = kural["id"]

        if tetik == "anlik":
            # Anlık görevler arka planda yeniden tetiklenmez
            return False

        elif tetik.startswith("pil:"):
            try:
                esik = int(tetik.split(":")[1])
                from core.android_api import pil_yuzde, pil_durumu
                yuzde = pil_yuzde()
                sarjda = pil_durumu().get("sarj_oluyor", False)
                # Şarj değilken eşiğin altına düştüyse
                if yuzde <= esik and not sarjda:
                    # Son 5 dakikada tetiklenmediyse
                    return self._bekleme_gecti_mi(kural_id, 300)
                return False
            except Exception:
                return False

        elif tetik.startswith("konum:"):
            etiket = tetik.split(":", 1)[1]
            try:
                from core.android_api import kayıtlı_konumda_mi
                if kayıtlı_konumda_mi(etiket, 200):
                    return self._bekleme_gecti_mi(kural_id, 120)
                return False
            except Exception:
                return False

        elif tetik.startswith("saat:"):
            saat_str = tetik.split(":", 1)[1]
            try:
                import datetime
                hedef_h, hedef_m = map(int, saat_str.split(":"))
                simdi = datetime.datetime.now()
                if simdi.hour == hedef_h and simdi.minute == hedef_m:
                    return self._bekleme_gecti_mi(kural_id, 65)
                return False
            except Exception:
                return False

        elif tetik.startswith("tekrar:"):
            try:
                aralik_sn = int(tetik.split(":")[1])
                return self._bekleme_gecti_mi(kural_id, aralik_sn)
            except Exception:
                return False

        return False

    def _bekleme_gecti_mi(self, kural_id: str, bekleme_sn: int) -> bool:
        simdi = time.time()
        son = self._son_saat_tetik.get(kural_id, 0)
        if simdi - son >= bekleme_sn:
            self._son_saat_tetik[kural_id] = simdi
            return True
        return False


class ArkaplanServisi:
    """
    5 saniyede bir aktif kuralları kontrol eden hafif döngü.
    CPU ve pil kullanımı minimaldır çünkü AI modeli burada asla yüklenmez.
    """

    KONTROL_ARALIGI_SN = 5

    def __init__(self):
        self.memory = Memory()
        self.degerlendirici = KuralDegerlendirici(self.memory)
        self._calisiyor = False
        self._thread: Optional[threading.Thread] = None
        self._bildirim_stili: str = "minimal"  # 'minimal' | 'toast' | 'hicbiri'

    def baslat(self):
        if self._calisiyor:
            return
        self._calisiyor = True
        self._thread = threading.Thread(target=self._dongü, daemon=True)
        self._thread.start()
        logger.info("Arka plan servisi başlatıldı.")

    def durdur(self):
        self._calisiyor = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("Arka plan servisi durduruldu.")

    def _dongü(self):
        while self._calisiyor:
            try:
                self._kuralları_kontrol_et()
            except Exception as e:
                logger.error(f"Kontrol döngüsü hatası: {e}")
            time.sleep(self.KONTROL_ARALIGI_SN)

    def _kuralları_kontrol_et(self):
        kurallar = self.memory.aktif_kurallar()
        for kural in kurallar:
            if self.degerlendirici.tetiklenmeli_mi(kural):
                self._kurali_calistir(kural)

    def _kurali_calistir(self, kural: dict):
        kural_id = kural["id"]
        baslik = kural.get("baslik", "Kural")
        kod = kural.get("eylem_kodu", "")

        logger.info(f"Kural tetiklendi: {baslik} ({kural_id})")

        sonuc = kodu_calistir(kod)

        self.memory.kural_son_tetik_guncelle(kural_id)

        if not sonuc.basarili:
            logger.warning(f"Kural başarısız: {baslik} — {sonuc.hata}")
            return

        # Kullanıcıyı bilgilendir (stile göre)
        stili = self.memory.ayar_oku("bildirim_stili", "minimal")
        if stili == "minimal":
            try:
                from core.android_api import bildirim_gonder
                bildirim_gonder(baslik, sonuc.cikti[:80], ses=False)
            except Exception:
                pass
        elif stili == "toast":
            try:
                from core.android_api import toast_goster
                toast_goster(f"✓ {baslik}")
            except Exception:
                pass
        # stili == "hicbiri" → sessizce çalışır


# Singleton
_servis = ArkaplanServisi()


def servisi_baslat():
    _servis.baslat()


def servisi_durdur():
    _servis.durdur()


def servis_calisiyor_mu() -> bool:
    return _servis._calisiyor
