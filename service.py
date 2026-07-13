"""
service.py — Android Foreground Service Giriş Noktası
Buildozer bu dosyayı ayrı bir Android Service process'i olarak çalıştırır.

Bu servis:
  - Düşük öncelikli bildirimle ön planda (foreground) çalışır
  - Sistem tarafından öldürülmez
  - Bildirim çubuğunda görünmez (IMPORTANCE_MIN)
  - 5 saniyede bir aktif kuralları kontrol eder
  - AI modeli ASLA bu süreçte yüklenmez → sıfır bellek / pil tüketimi
"""

import time
import os
import sys

# p4a, servis giriş dosyasını (service.py) ayrı bir Python süreci olarak
# çalıştırırken çalışma dizinini her zaman doğru ayarlamayabilir. Bu
# uygulama artık Termux'a bağımlı olmadığından (bkz. KURULUM.md), Termux'a
# özgü ~/.osagent/app yolunu eklemek yerine, bu dosyanın gerçekte bulunduğu
# proje kök dizinini sys.path'e ekliyoruz — böylece `from core...` importları
# hem cihazda hem de geliştirme ortamında güvenilir şekilde çalışır.
_PROJE_KOKU = os.path.dirname(os.path.abspath(__file__))
if _PROJE_KOKU not in sys.path:
    sys.path.insert(0, _PROJE_KOKU)


def foreground_bildirim_ayarla():
    """
    Android Foreground Service bildirimi.
    IMPORTANCE_MIN: sistem otomatik olarak bu bildirimi bildirim çubuğundan gizler.
    """
    try:
        from jnius import autoclass  # type: ignore

        PythonService    = autoclass("org.kivy.android.PythonService")
        NotificationMgr  = autoclass("android.app.NotificationManager")
        NotificationCompat = autoclass("androidx.core.app.NotificationCompat")
        Context          = autoclass("android.content.Context")

        service = PythonService.mService
        if service is None:
            return

        kanal_id = "osagent_service"

        # Bildirim kanalı oluştur (Android 8+)
        try:
            NotificationChannel = autoclass("android.app.NotificationChannel")
            nm = service.getSystemService(Context.NOTIFICATION_SERVICE)
            kanal = NotificationChannel(
                kanal_id,
                "OS Agent Servisi",
                NotificationMgr.IMPORTANCE_MIN  # Tamamen gizli
            )
            kanal.setShowBadge(False)
            nm.createNotificationChannel(kanal)
        except Exception:
            pass

        # Bildirim oluştur
        builder = NotificationCompat.Builder(service, kanal_id)
        builder.setContentTitle("OS Agent")
        builder.setContentText("Otomasyon motoru çalışıyor")
        builder.setPriority(NotificationCompat.PRIORITY_MIN)
        builder.setOngoing(True)
        builder.setSmallIcon(service.getApplicationInfo().icon)
        builder.setSilent(True)

        service.startForeground(1, builder.build())

    except Exception as e:
        # Android dışı ortam (test) veya jnius yok
        print(f"[Service] Foreground bildirimi kurulamadı (normal): {e}")


def main():
    print("[Service] Arka plan servisi başlatıldı.")
    foreground_bildirim_ayarla()

    from core.arkaplan_servisi import ArkaplanServisi
    servis = ArkaplanServisi()

    print("[Service] Kural döngüsü başlıyor...")
    while True:
        try:
            # Aktif kuralları kontrol et
            servis._kuralları_kontrol_et()
        except Exception as e:
            print(f"[Service] Döngü hatası: {e}")
        time.sleep(5)


if __name__ == "__main__":
    main()
