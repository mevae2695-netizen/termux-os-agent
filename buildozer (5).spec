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
# Gereksinimler (Sürüm takıntısını aşmak için python3'ü yalın bıraktık)
# -----------------------------------------------------------------------
requirements = python3,kivy==2.3.0,kivymd==1.2.0,pillow==11.1.0,android,pyjnius,plyer,certifi

p4a.bootstrap = sdl2

# -----------------------------------------------------------------------
# Android Foreground Service
# -----------------------------------------------------------------------
services = ArkaplanServisi:service.py:foreground

# -----------------------------------------------------------------------
# İzinler
# -----------------------------------------------------------------------
android.permissions = ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION, READ_CONTACTS, WRITE_CONTACTS, SEND_SMS, READ_SMS, RECEIVE_SMS, CALL_PHONE, READ_PHONE_STATE, CAMERA, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, MANAGE_EXTERNAL_STORAGE, VIBRATE, RECEIVE_BOOT_COMPLETED, FOREGROUND_SERVICE, FOREGROUND_SERVICE_LOCATION, POST_NOTIFICATIONS, INTERNET, ACCESS_NETWORK_STATE, CHANGE_NETWORK_STATE, ACCESS_WIFI_STATE, CHANGE_WIFI_STATE, BLUETOOTH, BLUETOOTH_ADMIN, BLUETOOTH_CONNECT, BLUETOOTH_SCAN, CHANGE_AUDIO_SETTINGS, MODIFY_AUDIO_SETTINGS, KILL_BACKGROUND_PROCESSES, REQUEST_INSTALL_PACKAGES, com.android.alarm.permission.SET_ALARM

# -----------------------------------------------------------------------
# Android API seviyeleri
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
# Davranış
# -----------------------------------------------------------------------
android.fullscreen = 0
android.orientation = portrait
android.wakelock = 0
android.allow_backup = 0

[buildozer]
log_level = 2
warn_on_root = 1
