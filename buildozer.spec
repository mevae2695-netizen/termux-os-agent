[app]

# -----------------------------------------------------------------------
# Uygulama kimliği
# -----------------------------------------------------------------------
title = OS Agent
package.name = osagent
package.domain = com.osagent
version = 1.2.0

# -----------------------------------------------------------------------
# Kaynak
# -----------------------------------------------------------------------
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db
source.exclude_dirs = .data,__pycache__,.git,.buildozer,bin,p4a-recipes
source.exclude_patterns = *.pyc,*.pyo,tests/*,*.md,colab_build.ipynb

# -----------------------------------------------------------------------
# Gereksinimler
#   • Python ve Kivy runtime APK içine gömülür — Termux GEREKMİYOR
#   • llama-cpp-python varsayılan derlemede YOK (bkz. p4a-recipes/README.md).
#     Uygulama modelsizken de "kural tabanlı" (STUB) motorla tam
#     fonksiyonel kalır (core/nlp_engine.py). Model isteğe bağlı olarak
#     ayrı bir "gelişmiş" derlemeyle eklenebilir.
#   • plyer: pyjnius'un üstüne, test edilmiş Android API sarmalayıcıları
#     (bildirim, konum, batarya vb.) için eklendi.
#   • certifi: urllib ile yapılan HTTPS indirmelerinde (model indirme,
#     hava durumu vb. API çağrıları) bazı Android cihazlarda görülen
#     "CERTIFICATE_VERIFY_FAILED" hatasını önler.
# -----------------------------------------------------------------------
requirements = python3==3.11,kivy==2.3.0,kivymd==1.2.0,pillow,android,pyjnius,plyer,certifi

# p4a-recipes/ klasörü İLERİ SEVİYE/isteğe bağlı bir llama-cpp-python
# recipe'i barındırır. Varsayılan `requirements` listesine dahil DEĞİLDİR;
# sadece kullanıcı bilinçli olarak requirements listesine
# "llama-cpp-python" ekler ve deneysel derlemeyi göze alırsa devreye girer.
p4a.local_recipes = p4a-recipes/
p4a.bootstrap = sdl2

# -----------------------------------------------------------------------
# Android Foreground Service
# -----------------------------------------------------------------------
services = ArkaplanServisi:service.py:foreground

# -----------------------------------------------------------------------
# İzinler — Termux bağımsız, tüm izinler APK'ya gömülü
# -----------------------------------------------------------------------
android.permissions =
    ACCESS_FINE_LOCATION,
    ACCESS_COARSE_LOCATION,
    READ_CONTACTS,
    WRITE_CONTACTS,
    SEND_SMS,
    READ_SMS,
    RECEIVE_SMS,
    CALL_PHONE,
    READ_PHONE_STATE,
    CAMERA,
    READ_EXTERNAL_STORAGE,
    WRITE_EXTERNAL_STORAGE,
    MANAGE_EXTERNAL_STORAGE,
    VIBRATE,
    RECEIVE_BOOT_COMPLETED,
    FOREGROUND_SERVICE,
    FOREGROUND_SERVICE_LOCATION,
    POST_NOTIFICATIONS,
    INTERNET,
    ACCESS_NETWORK_STATE,
    CHANGE_NETWORK_STATE,
    ACCESS_WIFI_STATE,
    CHANGE_WIFI_STATE,
    BLUETOOTH,
    BLUETOOTH_ADMIN,
    BLUETOOTH_CONNECT,
    BLUETOOTH_SCAN,
    CHANGE_AUDIO_SETTINGS,
    MODIFY_AUDIO_SETTINGS,
    KILL_BACKGROUND_PROCESSES,
    REQUEST_INSTALL_PACKAGES,
    com.android.alarm.permission.SET_ALARM

# -----------------------------------------------------------------------
# Android API seviyeleri
#   api/sdk = 33 (Android 13) bilinçli olarak seçildi: api=34 hedeflemek,
#   ön plan (foreground) servisleri için manifestte açık bir
#   `foregroundServiceType` bildirimini ZORUNLU kılıyor ve bu olmadan
#   servis çalışma anında (MissingForegroundServiceTypeException) çöküyor.
#   Buildozer/p4a'nın servis şablonu bu alanı henüz otomatik eklemiyor.
#   api=33 aynı izinlerle (FOREGROUND_SERVICE_LOCATION dahil) çalışır ve
#   bu çökmeyi önler. Play Store'a yüklemeyecekseniz (bu APK doğrudan
#   kurulum için) api=33 güvenli ve stabildir.
# -----------------------------------------------------------------------
android.minapi = 26
android.api = 33
android.ndk = 25b
android.sdk = 33
android.archs = arm64-v8a
android.accept_sdk_license = True
android.enable_androidx = True
android.gradle_dependencies = androidx.core:core:1.12.0

# -----------------------------------------------------------------------
# Görsel
# -----------------------------------------------------------------------
android.presplash.filename = assets/splash.png
android.icon.filename = assets/icon.png
android.presplash_color = #100F14

# -----------------------------------------------------------------------
# Davranış
# -----------------------------------------------------------------------
android.fullscreen = 0
android.orientation = portrait
android.wakelock = 0
android.allow_backup = 0

[buildozer]
log_level = 2
warn_on_root = 1
