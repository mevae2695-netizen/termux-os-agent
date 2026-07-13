"""
Android Donanım API Köprüsü
Tüm telefon donanım fonksiyonları burada tanımlıdır.
Yerel model bu listeyi context olarak alır ve Python kodu üretirken
sadece bu fonksiyonları kullanır.

v1.2 notu: Bu modül artık Termux:API komutlarına (termux-*) bağımlı
DEĞİLDİR. Önceki sürüm, gerçek bir APK'da hiçbir zaman var olmayacak
`termux-wifi-connectioninfo`, `termux-battery-status`, `termux-sms-send`
gibi Termux komutlarını `subprocess` ile çağırmaya çalışıyordu — bunlar
buildozer ile üretilen bağımsız bir APK içinde sessizce başarısız
olurdu. Tüm fonksiyonlar artık pyjnius (doğrudan Android SDK çağrıları)
veya plyer (test edilmiş, p4a destekli Android sarmalayıcılar) kullanır.
Android dışı bir ortamda (ör. masaüstünde test) çalıştırıldığında her
fonksiyon güvenli, anlamlı bir düşüş (fallback) değeri döndürür.
"""

import os
import ssl
import subprocess
import json

try:
    import certifi
    _SSL_BAGLAM = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _SSL_BAGLAM = ssl.create_default_context()

# ---------------------------------------------------------------------------
# Platform algılama – Android ortamında mı (pyjnius kullanılabilir mi)?
# ---------------------------------------------------------------------------
try:
    from jnius import autoclass, PythonJavaClass, java_method  # type: ignore

    ANDROID = True
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    Context = autoclass("android.content.Context")
    Settings = autoclass("android.provider.Settings")
    WifiManager = autoclass("android.net.wifi.WifiManager")
    AudioManager = autoclass("android.media.AudioManager")
    BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
    ConnectivityManager = autoclass("android.net.ConnectivityManager")
    Intent = autoclass("android.content.Intent")
    Uri = autoclass("android.net.Uri")
    IntentFilter = autoclass("android.content.IntentFilter")
    BatteryManager = autoclass("android.os.BatteryManager")
    SmsManager = autoclass("android.telephony.SmsManager")
    NotificationManager = autoclass("android.app.NotificationManager")
    NotificationCompat = autoclass("androidx.core.app.NotificationCompat")
    LocationManager = autoclass("android.location.LocationManager")
    PackageManager = autoclass("android.content.pm.PackageManager")
    ApplicationInfo = autoclass("android.content.pm.ApplicationInfo")
    ActivityManager = autoclass("android.app.ActivityManager")
    Toast = autoclass("android.widget.Toast")
    JString = autoclass("java.lang.String")
    ContactsContract = autoclass("android.provider.ContactsContract$Contacts")
    AlarmClock = autoclass("android.provider.AlarmClock")
except Exception:
    ANDROID = False

try:
    from plyer import notification as _plyer_notification  # type: ignore
except Exception:
    _plyer_notification = None


def _activity():
    """Ön plandaki Activity örneğini döndürür."""
    return PythonActivity.mActivity


# ---------------------------------------------------------------------------
# Geriye dönük uyumluluk: masaüstü/test ortamında shell komutu ile
# yaklaşık davranış üretmek için küçük bir yardımcı (Termux'a özgü
# değildir — sadece Linux/POSIX kabuk komutları çalıştırır).
# ---------------------------------------------------------------------------
def _shell(cmd: str) -> str:
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout.strip()
    except Exception as e:
        return f"HATA: {e}"


# ===========================================================================
# 1. WI-FI
# ===========================================================================
def wifi_ac():
    """Wi-Fi'ı açar."""
    if ANDROID:
        try:
            ctx = _activity()
            wm = ctx.getSystemService(Context.WIFI_SERVICE)
            # Android 10 (API 29)+ uygulamaların Wi-Fi'ı doğrudan
            # setWifiEnabled ile açması/kapatması engellenmiştir; bu durumda
            # kullanıcıyı Wi-Fi panelini açık bırakan sistem ayarına yönlendiriyoruz.
            basarili = wm.setWifiEnabled(True)
            if basarili:
                return "Wi-Fi açıldı."
            ctx.startActivity(Intent(Settings.ACTION_WIFI_SETTINGS))
            return "Android 10+ Wi-Fi'ı doğrudan açmama izin vermiyor; Wi-Fi ayarları açıldı."
        except Exception as e:
            return f"HATA: Wi-Fi açılamadı ({e})"
    return "Wi-Fi açma komutu gönderildi. (Android dışı ortam)"


def wifi_kapat():
    """Wi-Fi'ı kapatır."""
    if ANDROID:
        try:
            ctx = _activity()
            wm = ctx.getSystemService(Context.WIFI_SERVICE)
            basarili = wm.setWifiEnabled(False)
            if basarili:
                return "Wi-Fi kapatıldı."
            ctx.startActivity(Intent(Settings.ACTION_WIFI_SETTINGS))
            return "Android 10+ Wi-Fi'ı doğrudan kapatmama izin vermiyor; Wi-Fi ayarları açıldı."
        except Exception as e:
            return f"HATA: Wi-Fi kapatılamadı ({e})"
    return "Wi-Fi kapatma komutu gönderildi. (Android dışı ortam)"


def wifi_durumu() -> dict:
    """Mevcut Wi-Fi bağlantı durumunu döndürür."""
    if ANDROID:
        try:
            ctx = _activity()
            wm = ctx.getSystemService(Context.WIFI_SERVICE)
            info = wm.getConnectionInfo()
            ip_int = info.getIpAddress()
            ip = ".".join(str((ip_int >> (8 * i)) & 0xFF) for i in range(4))
            ssid = info.getSSID() or ""
            return {
                "durum": "bagli" if wm.isWifiEnabled() else "kapali",
                "ssid": ssid.strip('"'),
                "ip": ip,
            }
        except Exception as e:
            return {"durum": "bilinmiyor", "hata": str(e)}
    return {"durum": "bilinmiyor", "ssid": "", "ip": ""}


# ===========================================================================
# 2. BLUETOOTH
# ===========================================================================
def bluetooth_ac():
    """Bluetooth'u açar."""
    if ANDROID:
        try:
            adapter = BluetoothAdapter.getDefaultAdapter()
            if adapter and not adapter.isEnabled():
                adapter.enable()
            return "Bluetooth açıldı."
        except Exception as e:
            return f"HATA: Bluetooth açılamadı ({e})"
    return "Bluetooth açma komutu gönderildi. (Android dışı ortam)"


def bluetooth_kapat():
    """Bluetooth'u kapatır."""
    if ANDROID:
        try:
            adapter = BluetoothAdapter.getDefaultAdapter()
            if adapter and adapter.isEnabled():
                adapter.disable()
            return "Bluetooth kapatıldı."
        except Exception as e:
            return f"HATA: Bluetooth kapatılamadı ({e})"
    return "Bluetooth kapatma komutu gönderildi. (Android dışı ortam)"


def bluetooth_bagli_cihazlar() -> list:
    """
    Eşleştirilmiş (bonded) Bluetooth cihazlarını listeler.
    Not: Android, üçüncü taraf uygulamaların "şu an aktif bağlı" cihaz
    listesine erişimini kısıtlar; en yakın ve güvenilir eşdeğer,
    eşleştirilmiş cihaz listesidir.
    """
    if ANDROID:
        try:
            adapter = BluetoothAdapter.getDefaultAdapter()
            if not adapter:
                return []
            eslesmis = adapter.getBondedDevices().toArray()
            return [d.getName() for d in eslesmis]
        except Exception:
            return []
    return []


# ===========================================================================
# 3. SES ve MÜZİK
# ===========================================================================
def ses_seviyesi_ayarla(seviye: int, tip: str = "music"):
    """
    Ses seviyesini ayarlar.
    seviye: 0-15 arası
    tip: 'music' | 'ring' | 'notification' | 'alarm'
    """
    tip_map = {
        "music": "STREAM_MUSIC",
        "ring": "STREAM_RING",
        "notification": "STREAM_NOTIFICATION",
        "alarm": "STREAM_ALARM",
    }
    stream = tip_map.get(tip, "STREAM_MUSIC")
    if ANDROID:
        try:
            ctx = _activity()
            am = ctx.getSystemService(Context.AUDIO_SERVICE)
            stream_id = getattr(AudioManager, stream)
            am.setStreamVolume(stream_id, seviye, 0)
            return f"Ses seviyesi {seviye} olarak ayarlandı."
        except Exception as e:
            return f"HATA: Ses ayarlanamadı ({e})"
    return f"Ses {seviye} yapıldı. (Android dışı ortam)"


def sessiz_mod_ac():
    """Sessiz modu açar (titreşim yok)."""
    if ANDROID:
        try:
            ctx = _activity()
            am = ctx.getSystemService(Context.AUDIO_SERVICE)
            am.setRingerMode(0)  # RINGER_MODE_SILENT
            return "Sessiz mod açıldı."
        except Exception as e:
            return f"HATA: {e}"
    return "Sessiz mod açıldı. (Android dışı ortam)"


def sessiz_mod_kapat():
    """Normal ses moduna döner."""
    if ANDROID:
        try:
            ctx = _activity()
            am = ctx.getSystemService(Context.AUDIO_SERVICE)
            am.setRingerMode(2)  # RINGER_MODE_NORMAL
            return "Normal ses moduna geçildi."
        except Exception as e:
            return f"HATA: {e}"
    return "Normal ses moduna geçildi. (Android dışı ortam)"


def titresim_modu_ac():
    """Titreşim modunu açar."""
    if ANDROID:
        try:
            ctx = _activity()
            am = ctx.getSystemService(Context.AUDIO_SERVICE)
            am.setRingerMode(1)  # RINGER_MODE_VIBRATE
            return "Titreşim modu açıldı."
        except Exception as e:
            return f"HATA: {e}"
    return "Titreşim modu açıldı. (Android dışı ortam)"


# ===========================================================================
# 4. EKRAN PARLAKLIĞI
# ===========================================================================
def parlaklık_ayarla(deger: int):
    """
    Ekran parlaklığını ayarlar.
    deger: 0-255 arası (0=en karanlık, 255=en parlak)
    Not: Android 6+'da bu sistem ayarını değiştirmek için
    `WRITE_SETTINGS` özel izni (Settings.System.canWrite) gerekir;
    kullanıcı bu izni ilk kullanımda manuel olarak vermelidir.
    """
    if ANDROID:
        try:
            ctx = _activity()
            if not Settings.System.canWrite(ctx):
                intent = Intent(Settings.ACTION_MANAGE_WRITE_SETTINGS)
                intent.setData(Uri.parse(f"package:{ctx.getPackageName()}"))
                ctx.startActivity(intent)
                return "Parlaklık ayarı izni gerekiyor; ayarlar ekranı açıldı."
            Settings.System.putInt(
                ctx.getContentResolver(),
                Settings.System.SCREEN_BRIGHTNESS,
                max(0, min(255, deger)),
            )
            return f"Parlaklık {deger} olarak ayarlandı."
        except Exception as e:
            return f"HATA: {e}"
    return f"Parlaklık {deger} yapıldı. (Android dışı ortam)"


def otomatik_parlaklık_ac():
    """Otomatik parlaklığı açar."""
    if ANDROID:
        try:
            ctx = _activity()
            if not Settings.System.canWrite(ctx):
                intent = Intent(Settings.ACTION_MANAGE_WRITE_SETTINGS)
                intent.setData(Uri.parse(f"package:{ctx.getPackageName()}"))
                ctx.startActivity(intent)
                return "Parlaklık ayarı izni gerekiyor; ayarlar ekranı açıldı."
            Settings.System.putInt(
                ctx.getContentResolver(),
                Settings.System.SCREEN_BRIGHTNESS_MODE,
                Settings.System.SCREEN_BRIGHTNESS_MODE_AUTOMATIC,
            )
            return "Otomatik parlaklık açıldı."
        except Exception as e:
            return f"HATA: {e}"
    return "Otomatik parlaklık açıldı. (Android dışı ortam)"


def tasarruf_modu_ac():
    """Batarya tasarruf modunu açar (parlaklığı düşürür)."""
    parlaklık_ayarla(30)
    return "Tasarruf modu: Parlaklık düşürüldü."


# ===========================================================================
# 5. KONUM
# ===========================================================================
def konum_al() -> dict:
    """
    Bilinen en güncel GPS/ağ konumunu döndürür (LocationManager'ın son
    bilinen konumu — canlı bir GPS taraması başlatmaz, bu yüzden anlık ve
    senkron olarak dönebilir).
    """
    if ANDROID:
        try:
            ctx = _activity()
            lm = ctx.getSystemService(Context.LOCATION_SERVICE)
            konum = None
            for provider in (LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER):
                try:
                    konum = lm.getLastKnownLocation(provider)
                    if konum:
                        break
                except Exception:
                    continue
            if konum is None:
                return {"hata": "Konum alınamadı (son bilinen konum yok)."}
            return {
                "enlem": konum.getLatitude(),
                "boylam": konum.getLongitude(),
                "dogruluk": konum.getAccuracy(),
            }
        except Exception as e:
            return {"hata": f"Konum alınamadı: {e}"}
    return {"hata": "Konum alınamadı (Android dışı ortam)."}


def konum_kaydet(etiket: str) -> dict:
    """Mevcut konumu bir etiketle kaydeder."""
    from core.memory import Memory
    konum = konum_al()
    if "hata" not in konum:
        Memory().konum_kaydet(etiket, konum["enlem"], konum["boylam"])
        return {"basarili": True, "mesaj": f"'{etiket}' konumu kaydedildi.", "konum": konum}
    return {"basarili": False, "mesaj": "Konum alınamadı."}


def kayıtlı_konumda_mi(etiket: str, tolerans_metre: float = 200) -> bool:
    """Cihazın kayıtlı konuma yakın olup olmadığını kontrol eder."""
    from core.memory import Memory
    import math
    kayitli = Memory().konum_getir(etiket)
    if not kayitli:
        return False
    mevcut = konum_al()
    if "hata" in mevcut:
        return False
    lat1, lon1 = mevcut["enlem"], mevcut["boylam"]
    lat2, lon2 = kayitli["enlem"], kayitli["boylam"]
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    mesafe = R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return mesafe <= tolerans_metre


# ===========================================================================
# 6. PİL
# ===========================================================================
def pil_durumu() -> dict:
    """
    Pil yüzdesi ve şarj durumunu döndürür.
    Android'in klasik "sticky broadcast" numarasıyla senkron olarak okunur:
    registerReceiver(None, filter) son ACTION_BATTERY_CHANGED broadcast'ini
    anında geri döndürür (yeni bir alıcı kaydetmez).
    """
    if ANDROID:
        try:
            ctx = _activity()
            filtre = IntentFilter(Intent.ACTION_BATTERY_CHANGED)
            durum_intent = ctx.registerReceiver(None, filtre)
            seviye = durum_intent.getIntExtra("level", -1)
            olcek = durum_intent.getIntExtra("scale", -1)
            durum_kodu = durum_intent.getIntExtra("status", -1)
            yuzde = int(seviye * 100 / olcek) if olcek > 0 else 0
            sarj_oluyor = durum_kodu in (
                BatteryManager.BATTERY_STATUS_CHARGING,
                BatteryManager.BATTERY_STATUS_FULL,
            )
            return {"yuzde": yuzde, "sarj_oluyor": sarj_oluyor, "durum": "sarj" if sarj_oluyor else "normal"}
        except Exception as e:
            return {"yuzde": 0, "sarj_oluyor": False, "durum": f"hata: {e}"}
    return {"yuzde": 0, "sarj_oluyor": False, "durum": "bilinmiyor"}


def pil_yuzde() -> int:
    """Anlık pil yüzdesini döndürür (0-100)."""
    return pil_durumu().get("yuzde", 0)


# ===========================================================================
# 7. UÇUŞ MODU
# ===========================================================================
def ucus_modu_durumu() -> bool:
    """Uçuş modunun açık olup olmadığını döndürür."""
    if ANDROID:
        try:
            ctx = _activity()
            deger = Settings.Global.getInt(ctx.getContentResolver(), Settings.Global.AIRPLANE_MODE_ON, 0)
            return deger != 0
        except Exception:
            return False
    return False


# ===========================================================================
# 8. KAMERA
# ===========================================================================
def fotograf_cek(dosya_yolu: str = None) -> str:
    """
    Kamera uygulamasını açıp fotoğraf çekilmesini ister (ACTION_IMAGE_CAPTURE).
    Not: Gerçek kamera erişimi Android'de asenkron bir Activity sonucu
    (onActivityResult) gerektirir; bu fonksiyon senkron bir "fotoğraf byte'ı
    döndürme" işlemi yapamaz — kamera uygulamasını doğru MediaStore hedefine
    yazacak şekilde başlatır ve kullanıcı çektikten sonra dosya belirtilen
    konumda oluşur.
    """
    if ANDROID:
        try:
            from plyer import camera  # type: ignore
            hedef = dosya_yolu or os.path.join(
                str(_activity().getExternalFilesDir(None).getAbsolutePath()), "goruntu.jpg"
            )
            camera.take_picture(filename=hedef, on_complete=lambda path: None)
            return f"Kamera açıldı, fotoğraf {hedef} konumuna kaydedilecek."
        except Exception as e:
            return f"HATA: Kamera açılamadı ({e})"
    return f"Fotoğraf {dosya_yolu or '(varsayılan konum)'} kaydedildi. (Android dışı ortam)"


# ===========================================================================
# 9. SMS ve TELEFON
# ===========================================================================
def sms_gonder(numara: str, mesaj: str) -> str:
    """Belirtilen numaraya SMS gönderir (SmsManager)."""
    if ANDROID:
        try:
            sm = SmsManager.getDefault()
            sm.sendTextMessage(numara, None, mesaj, None, None)
            return f"SMS {numara} numarasına gönderildi."
        except Exception as e:
            return f"HATA: SMS gönderilemedi ({e})"
    return "SMS gönderildi. (Android dışı ortam)"


def arama_yap(numara: str) -> str:
    """Belirtilen numarayı doğrudan arar (ACTION_CALL, CALL_PHONE izni gerektirir)."""
    if ANDROID:
        try:
            ctx = _activity()
            intent = Intent(Intent.ACTION_CALL)
            intent.setData(Uri.parse(f"tel:{numara}"))
            ctx.startActivity(intent)
            return f"{numara} aranıyor."
        except Exception as e:
            return f"HATA: Arama başlatılamadı ({e})"
    return f"{numara} aranıyor. (Android dışı ortam)"


def son_smsleri_getir(adet: int = 5) -> list:
    """Gelen kutusundaki son SMS mesajlarını ContentResolver ile listeler."""
    if ANDROID:
        try:
            ctx = _activity()
            cr = ctx.getContentResolver()
            uri = Uri.parse("content://sms/inbox")
            imlec = cr.query(uri, None, None, None, "date DESC")
            sonuc = []
            if imlec and imlec.moveToFirst():
                sayac = 0
                while sayac < adet:
                    try:
                        adres = imlec.getString(imlec.getColumnIndexOrThrow("address"))
                        govde = imlec.getString(imlec.getColumnIndexOrThrow("body"))
                        tarih = imlec.getLong(imlec.getColumnIndexOrThrow("date"))
                        sonuc.append({"adres": adres, "mesaj": govde, "tarih": tarih})
                    except Exception:
                        pass
                    sayac += 1
                    if not imlec.moveToNext():
                        break
                imlec.close()
            return sonuc
        except Exception:
            return []
    return []


# ===========================================================================
# 10. BİLDİRİM
# ===========================================================================
def bildirim_gonder(baslik: str, mesaj: str, ses: bool = False) -> str:
    """Gerçek bir Android sistem bildirimi gönderir (NotificationCompat)."""
    if ANDROID:
        try:
            ctx = _activity()
            kanal_id = "osagent_kullanici"
            nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE)
            try:
                NotificationChannel = autoclass("android.app.NotificationChannel")
                onem = NotificationManager.IMPORTANCE_DEFAULT if ses else NotificationManager.IMPORTANCE_LOW
                kanal = NotificationChannel(kanal_id, "OS Agent Bildirimleri", onem)
                nm.createNotificationChannel(kanal)
            except Exception:
                pass
            builder = NotificationCompat.Builder(ctx, kanal_id)
            builder.setContentTitle(baslik)
            builder.setContentText(mesaj)
            builder.setSmallIcon(ctx.getApplicationInfo().icon)
            builder.setAutoCancel(True)
            if not ses:
                builder.setSilent(True)
            nm.notify(int(__import__("time").time()) % 100000, builder.build())
            return "Bildirim gönderildi."
        except Exception as e:
            return f"HATA: Bildirim gönderilemedi ({e})"
    if _plyer_notification:
        try:
            _plyer_notification.notify(title=baslik, message=mesaj)
            return "Bildirim gönderildi."
        except Exception:
            pass
    return "Bildirim gönderildi. (Android dışı ortam)"


def toast_goster(mesaj: str) -> str:
    """
    Ekranda kısa süreliğine mesaj gösterir (Toast).
    Toast.show() Android'de UI thread'inde çağrılmak ZORUNDADIR; bu yüzden
    pyjnius'un PythonJavaClass mekanizmasıyla gerçek bir Runnable oluşturup
    Activity.runOnUiThread ile UI thread'ine gönderiyoruz.
    """
    if ANDROID:
        try:
            activity = _activity()
            metin = mesaj

            class _ToastRunnable(PythonJavaClass):
                __javainterfaces__ = ["java/lang/Runnable"]
                __javacontext__ = "app"

                @java_method("()V")
                def run(self):
                    Toast.makeText(activity, JString(metin), Toast.LENGTH_SHORT).show()

            activity.runOnUiThread(_ToastRunnable())
            return f"Toast: {mesaj}"
        except Exception as e:
            return f"HATA: Toast gösterilemedi ({e})"
    return f"Toast: {mesaj} (Android dışı ortam)"


# ===========================================================================
# 11. REHBER
# ===========================================================================
def rehber_ara(isim: str) -> list:
    """İsme göre rehberde arama yapar (ContactsContract, READ_CONTACTS gerektirir)."""
    if ANDROID:
        try:
            ctx = _activity()
            cr = ctx.getContentResolver()
            uri = ContactsContract.CONTENT_URI
            imlec = cr.query(uri, None, None, None, None)
            sonuc = []
            isim_lower = isim.lower()
            if imlec and imlec.moveToFirst():
                while True:
                    try:
                        ad = imlec.getString(
                            imlec.getColumnIndexOrThrow(ContactsContract.DISPLAY_NAME)
                        )
                        if ad and isim_lower in ad.lower():
                            sonuc.append({"name": ad})
                    except Exception:
                        pass
                    if not imlec.moveToNext():
                        break
                imlec.close()
            return sonuc
        except Exception:
            return []
    return []


# ===========================================================================
# 12. UYGULAMA YÖNETİMİ
# ===========================================================================
def uygulama_ac(paket_adi: str) -> str:
    """Belirtilen paketi başlatır. Örnek: uygulama_ac('com.whatsapp')"""
    if ANDROID:
        try:
            ctx = _activity()
            pm = ctx.getPackageManager()
            intent = pm.getLaunchIntentForPackage(paket_adi)
            if intent is None:
                return f"HATA: {paket_adi} bulunamadı veya başlatılamıyor."
            ctx.startActivity(intent)
            return f"{paket_adi} açıldı."
        except Exception as e:
            return f"HATA: {e}"
    return f"{paket_adi} açıldı. (Android dışı ortam)"


def uygulama_kapat(paket_adi: str) -> str:
    """
    Belirtilen paketi arka planda öldürmeye çalışır.
    Not: Normal (root olmayan, sistem uygulaması olmayan) bir uygulama,
    Android'de başka bir uygulamayı zorla kapatamaz (`am force-stop` sistem
    yetkisi gerektirir ve Termux'ta bile genelde root ister). En yakın
    resmi API, yalnızca ARKA PLANDAKİ (cached/background) süreçleri
    sonlandırabilen killBackgroundProcesses'tir.
    """
    if ANDROID:
        try:
            ctx = _activity()
            am = ctx.getSystemService(Context.ACTIVITY_SERVICE)
            am.killBackgroundProcesses(paket_adi)
            return f"{paket_adi} arka plan süreci sonlandırıldı (ön plandaysa kapatılamaz)."
        except Exception as e:
            return f"HATA: {e}"
    return f"{paket_adi} kapatıldı. (Android dışı ortam)"


def yuklü_uygulamaları_listele() -> list:
    """Yüklü (sistem dışı) uygulamaların paket adlarını listeler."""
    if ANDROID:
        try:
            ctx = _activity()
            pm = ctx.getPackageManager()
            uygulamalar = pm.getInstalledApplications(0).toArray()
            sonuc = []
            for app in uygulamalar:
                if (app.flags & ApplicationInfo.FLAG_SYSTEM) == 0:
                    sonuc.append(str(app.packageName))
            return sonuc
        except Exception:
            return []
    return []


# ===========================================================================
# 13. ZAMANLAYICI ve ALARM
# ===========================================================================
def alarm_kur(saat: int, dakika: int, etiket: str = "Alarm") -> str:
    """
    Sistem Saat uygulamasında gerçek bir alarm kurar
    (AlarmClock.ACTION_SET_ALARM, EXTRA_SKIP_UI ile arayüz açmadan).
    """
    if ANDROID:
        try:
            ctx = _activity()
            intent = Intent(AlarmClock.ACTION_SET_ALARM)
            intent.putExtra(AlarmClock.EXTRA_HOUR, saat)
            intent.putExtra(AlarmClock.EXTRA_MINUTES, dakika)
            intent.putExtra(AlarmClock.EXTRA_MESSAGE, etiket)
            intent.putExtra(AlarmClock.EXTRA_SKIP_UI, True)
            intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            ctx.startActivity(intent)
            return f"Alarm {saat}:{dakika:02d} için kuruldu."
        except Exception as e:
            return f"HATA: Alarm kurulamadı ({e})"
    return f"Alarm {saat}:{dakika:02d} için kuruldu. (Android dışı ortam)"


# ===========================================================================
# 14. DOSYA ve DEPOLAMA
# ===========================================================================
def dosya_oku(yol: str) -> str:
    """Bir metin dosyasını okur."""
    try:
        with open(yol, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"HATA: {yol} bulunamadı."
    except PermissionError:
        return f"HATA: {yol} için izin yok."


def dosya_yaz(yol: str, icerik: str) -> str:
    """Bir metin dosyasına yazar."""
    try:
        os.makedirs(os.path.dirname(yol) or ".", exist_ok=True)
        with open(yol, "w", encoding="utf-8") as f:
            f.write(icerik)
        return f"{yol} yazıldı."
    except PermissionError:
        return f"HATA: {yol} için yazma izni yok."


# ===========================================================================
# 15. EVRENSEL ANAHTARLAR
# ===========================================================================
def dinamik_internet_verisi_al(url: str, parametreler: dict = None) -> dict:
    """
    Evrensel anahtar 1: Herhangi bir HTTP GET isteği yapar.
    Hava durumu, borsa, haberler gibi API'ler için kullanılır.
    Örnek: dinamik_internet_verisi_al("https://wttr.in/Istanbul?format=j1")
    """
    import urllib.request
    import urllib.parse
    try:
        if parametreler:
            url += "?" + urllib.parse.urlencode(parametreler)
        with urllib.request.urlopen(url, timeout=10, context=_SSL_BAGLAM) as r:
            raw = r.read().decode("utf-8")
            try:
                return {"basarili": True, "veri": json.loads(raw)}
            except Exception:
                return {"basarili": True, "veri": raw}
    except Exception as e:
        return {"basarili": False, "hata": str(e)}


def dinamik_shell_komutu_calistir(komut: str) -> str:
    """
    Evrensel anahtar 2: Linux çekirdek komutlarını çalıştırır.
    İnternet gerektirmeyen derin sistem bilgisi için kullanılır.
    Örnek: dinamik_shell_komutu_calistir("cat /sys/class/thermal/thermal_zone0/temp")
    """
    try:
        result = subprocess.run(
            komut, shell=True, capture_output=True, text=True, timeout=15
        )
        cikti = result.stdout.strip()
        hata = result.stderr.strip()
        if result.returncode != 0:
            return f"UYARI (kod {result.returncode}): {hata or cikti}"
        return cikti or "(komut çıktısız tamamlandı)"
    except subprocess.TimeoutExpired:
        return "HATA: Komut zaman aşımına uğradı."
    except Exception as e:
        return f"HATA: {e}"


# ===========================================================================
# FONKSIYON DOKÜMANı – Model bu listeyi context olarak alır
# ===========================================================================
ANDROID_API_DOKUMAN = """
# Kullanılabilir Android Fonksiyonları

## Wi-Fi
- wifi_ac() → Wi-Fi'ı açar
- wifi_kapat() → Wi-Fi'ı kapatır
- wifi_durumu() → dict: {'durum', 'ssid', 'ip'}

## Bluetooth
- bluetooth_ac() → Bluetooth'u açar
- bluetooth_kapat() → Bluetooth'u kapatır
- bluetooth_bagli_cihazlar() → list

## Ses
- ses_seviyesi_ayarla(seviye: int, tip: str) → tip: 'music'|'ring'|'notification'|'alarm'
- sessiz_mod_ac() → Sessiz mod
- sessiz_mod_kapat() → Normal ses
- titresim_modu_ac() → Titreşim

## Ekran Parlaklığı
- parlaklık_ayarla(deger: int) → 0-255
- otomatik_parlaklık_ac()
- tasarruf_modu_ac() → Parlaklığı düşürür

## Konum
- konum_al() → dict: {'enlem', 'boylam', 'dogruluk'}
- konum_kaydet(etiket: str) → Mevcut konumu kaydeder
- kayıtlı_konumda_mi(etiket: str, tolerans_metre: float) → bool

## Pil
- pil_durumu() → dict: {'yuzde', 'sarj_oluyor', 'durum'}
- pil_yuzde() → int (0-100)

## Kamera
- fotograf_cek(dosya_yolu: str) → Kamera uygulamasını açar

## SMS ve Telefon
- sms_gonder(numara: str, mesaj: str)
- arama_yap(numara: str)
- son_smsleri_getir(adet: int) → list

## Bildirim
- bildirim_gonder(baslik: str, mesaj: str, ses: bool)
- toast_goster(mesaj: str) → Kısa ekran mesajı

## Rehber
- rehber_ara(isim: str) → list

## Uygulama Yönetimi
- uygulama_ac(paket_adi: str)
- uygulama_kapat(paket_adi: str) → Sadece arka plandaki süreci sonlandırır
- yuklü_uygulamaları_listele() → list

## Evrensel Anahtarlar
- dinamik_internet_verisi_al(url: str, parametreler: dict) → dict
- dinamik_shell_komutu_calistir(komut: str) → str

## Kural Hafızası
- konum_kaydet(etiket: str) → mevcut konumu kaydeder
- kayıtlı_konumda_mi(etiket: str) → bool
"""
