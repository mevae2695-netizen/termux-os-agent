"""
İzin Yöneticisi
Android izin durumlarını kontrol eder, eksik izinleri yakalar ve
kullanıcıya chat akışı içinden nazik mesaj gösterir.
"""

from typing import Optional

try:
    from jnius import autoclass  # type: ignore

    ANDROID = True
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    ContextCompat = autoclass("androidx.core.content.ContextCompat")
    PackageManager = autoclass("android.content.pm.PackageManager")
    Settings = autoclass("android.provider.Settings")
    Intent = autoclass("android.content.Intent")
    Uri = autoclass("android.net.Uri")
except Exception:
    ANDROID = False

# İzin adı → kullanıcı dostu Türkçe açıklama
IZIN_ACIKLAMALARI = {
    "android.permission.ACCESS_FINE_LOCATION":    "Konum (Hassas GPS)",
    "android.permission.ACCESS_COARSE_LOCATION":  "Konum (Yaklaşık)",
    "android.permission.READ_CONTACTS":           "Rehber Okuma",
    "android.permission.WRITE_CONTACTS":          "Rehber Yazma",
    "android.permission.SEND_SMS":                "SMS Gönderme",
    "android.permission.READ_SMS":                "SMS Okuma",
    "android.permission.CALL_PHONE":              "Telefon Araması",
    "android.permission.CAMERA":                  "Kamera",
    "android.permission.READ_EXTERNAL_STORAGE":   "Depolama Okuma",
    "android.permission.WRITE_EXTERNAL_STORAGE":  "Depolama Yazma",
    "android.permission.BLUETOOTH":               "Bluetooth",
    "android.permission.BLUETOOTH_ADMIN":         "Bluetooth Yönetimi",
    "android.permission.VIBRATE":                 "Titreşim",
    "android.permission.RECEIVE_BOOT_COMPLETED":  "Açılışta Çalışma",
    "android.permission.FOREGROUND_SERVICE":      "Arka Plan Servisi",
    "android.permission.POST_NOTIFICATIONS":      "Bildirim Gösterme",
    "android.permission.MANAGE_EXTERNAL_STORAGE": "Tüm Dosyalara Erişim",
}

# Fonksiyon adı → gerektirdiği izinler
FONKSIYON_IZINLERİ = {
    "konum_al":               ["android.permission.ACCESS_FINE_LOCATION"],
    "konum_kaydet":           ["android.permission.ACCESS_FINE_LOCATION"],
    "kayıtlı_konumda_mi":     ["android.permission.ACCESS_FINE_LOCATION"],
    "sms_gonder":             ["android.permission.SEND_SMS"],
    "son_smsleri_getir":      ["android.permission.READ_SMS"],
    "arama_yap":              ["android.permission.CALL_PHONE"],
    "fotograf_cek":           ["android.permission.CAMERA"],
    "rehber_ara":             ["android.permission.READ_CONTACTS"],
    "dosya_yaz":              ["android.permission.WRITE_EXTERNAL_STORAGE"],
    "dosya_oku":              ["android.permission.READ_EXTERNAL_STORAGE"],
}


class IzinYoneticisi:
    def __init__(self, paket_adi: str = "com.osagent.app"):
        self.paket_adi = paket_adi

    def izin_durumu(self, izin: str) -> bool:
        """
        Belirli bir iznin verilip verilmediğini kontrol eder.
        `dumpsys` normal (root olmayan) bir uygulama sürecinden
        çalıştırılamaz ve sistem yetkisi ister — bunun yerine uygulama
        kendi izinlerini doğrudan ContextCompat.checkSelfPermission ile
        (in-process, resmi Android API) sorar.
        """
        if not ANDROID:
            # Geliştirme ortamı: izin sistemi yok, verilmiş varsayılır.
            return True
        try:
            ctx = PythonActivity.mActivity
            sonuc = ContextCompat.checkSelfPermission(ctx, izin)
            return sonuc == PackageManager.PERMISSION_GRANTED
        except Exception:
            return False

    def tum_izinleri_kontrol_et(self) -> dict:
        """Tüm izinlerin durumunu döndürür."""
        sonuc = {}
        for izin, aciklama in IZIN_ACIKLAMALARI.items():
            sonuc[izin] = {
                "aciklama": aciklama,
                "verildi": self.izin_durumu(izin)
            }
        return sonuc

    def fonksiyon_icin_eksik_izinler(self, fonksiyon_adi: str) -> list:
        """Bir fonksiyon için eksik izinleri döndürür."""
        gerekli = FONKSIYON_IZINLERİ.get(fonksiyon_adi, [])
        eksik = []
        for izin in gerekli:
            if not self.izin_durumu(izin):
                eksik.append({
                    "izin": izin,
                    "aciklama": IZIN_ACIKLAMALARI.get(izin, izin)
                })
        return eksik

    def kod_icin_gerekli_izinler(self, python_kodu: str) -> list:
        """Python kodunu analiz ederek gereken izinleri tespit eder."""
        eksikler = []
        for fonk, izinler in FONKSIYON_IZINLERİ.items():
            if fonk in python_kodu:
                for izin in izinler:
                    if not self.izin_durumu(izin):
                        bilgi = {
                            "izin": izin,
                            "aciklama": IZIN_ACIKLAMALARI.get(izin, izin)
                        }
                        if bilgi not in eksikler:
                            eksikler.append(bilgi)
        return eksikler

    def izin_hata_mesajı(self, eksik_izinler: list) -> str:
        """Kullanıcıya gösterilecek Türkçe hata mesajını üretir."""
        if not eksik_izinler:
            return ""
        izin_listesi = ", ".join(i["aciklama"] for i in eksik_izinler)
        return (
            f"⚠️ Küçük bir engel çıktı!\n\n"
            f"Bu görevi yapabilmem için şu izin(ler) kapalı görünüyor: **{izin_listesi}**\n\n"
            f"Lütfen Ayarlar → Uygulama İzinleri yolunu takip edin."
        )

    def ayarlar_sayfasını_ac(self):
        """
        Android izin ayarları sayfasını açar.
        `am start` kabuk komutu, normal bir uygulama sürecinden
        çalıştırılamaz (Termux'ta bile ayrı bir yetkilendirme ister) —
        bunun yerine gerçek bir Android Intent ile ayarlar ekranı açılır.
        """
        if not ANDROID:
            return
        try:
            ctx = PythonActivity.mActivity
            intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
            intent.setData(Uri.parse(f"package:{self.paket_adi}"))
            intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            ctx.startActivity(intent)
        except Exception:
            pass


class IzinHatası(Exception):
    """İzin eksikliğinden kaynaklanan hatalar için özel istisna."""
    def __init__(self, mesaj: str, eksik_izinler: list = None):
        super().__init__(mesaj)
        self.eksik_izinler = eksik_izinler or []
