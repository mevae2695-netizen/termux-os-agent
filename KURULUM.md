# OS Agent — Kurulum Rehberi

## 🎯 Ne Değişti?

| Eski (v1.0) | v1.1 | v1.2 (bu sürüm) |
|---|---|---|
| Termux kurulması gerekiyordu | ❌ Termux gerekmez (dokümantasyonda) | ✅ Kod da artık gerçekten Termux'a bağımlı değil (bkz. aşağıda) |
| Model manuel indiriliyordu | ✅ Uygulama ilk açılışta kendi indirir | ✅ Aynı, artık SSL sertifika hatalarına karşı sağlamlaştırıldı |
| Termux:API eklentisi gerekiyordu | ❌ Gerekmez (iddia edildi) | ✅ `core/android_api.py` artık gerçekten pyjnius/plyer kullanıyor — önceki sürümde çoğu fonksiyon hâlâ `termux-*` komutlarını çağırıyordu ve bir APK'da sessizce çalışmazdı |
| Ayrı kurulum adımları | ✅ APK kur, aç, kullan | ✅ Aynı + Buildozer/Colab derlemesi ilk denemede başarılı olacak şekilde düzeltildi |

### v1.2 ile gelen düzeltmeler (özet)

- `buildozer.spec`: geçersiz/riskli ayarlar temizlendi, AndroidX + gerçek
  ikon/splash dosyaları eklendi, API 33 hedeflenerek ön plan servisinin
  Android 14 üzerinde çökmesi önlendi.
- `core/android_api.py`: Wi-Fi, Bluetooth, pil, konum, SMS, bildirim,
  toast, rehber, uygulama yönetimi ve alarm fonksiyonlarının TÜMÜ
  gerçek Android API'lerine (pyjnius/plyer) taşındı — artık hiçbiri
  var olmayan `termux-*` komutlarına bağımlı değil.
- `core/permission_manager.py`: izin kontrolü artık `dumpsys` yerine
  uygulama içi `ContextCompat.checkSelfPermission` kullanıyor.
- `core/memory.py`: veritabanı yolu artık Termux'a özgü sabit bir yol
  değil, uygulamaya özel Android depolama dizini.
- `llama-cpp-python` isteğe bağlı hale getirildi — model kurulu
  olmasa/derlenemese bile uygulama kural-tabanlı motorla tam
  çalışır durumda kalır (bkz. `p4a-recipes/README.md`).

---

## 🚀 Kurulum (3 Adım)

### 1. APK'yı Derle (Google Colab)
`colab_build.ipynb` dosyasını Google Colab'da açın ve adımları sırayla çalıştırın.

### 2. Telefona Kur
APK'yı telefona aktarın → Ayarlar → Güvenlik → Bilinmeyen Kaynaklar → APK'ya dokun → Kur

### 3. İlk Açılış
Uygulama açılınca şu sıra gerçekleşir:

```
1. Model Seçim Ekranı
   ↓  Phi-3 Mini / Gemma 2B / TinyLlama seç
2. Model İndirme (tek seferlik, yalnızca internet gerekir)
   ↓  İlerleme çubuğu — uygulama kapatılıp açılabilir
3. İzin Ekranı
   ↓  Android standart izin diyalogları
4. Chat Ekranı — Kullanmaya başla!
```

---

## 🧠 Model Seçenekleri

| Model | Boyut | Performans |
|-------|-------|-----------|
| **Phi-3 Mini (Önerilen)** | ~2.2 GB | Türkçe anlama çok güçlü |
| Gemma 2B | ~1.5 GB | Dengeli — hız + doğruluk |
| TinyLlama 1.1B | ~600 MB | Eski telefon / az depolama için |

Model telefona yüklendikten sonra internet **hiç** gerekmez.

---

## 💬 Örnek Komutlar

| Ne Söylersiniz | Ne Yapar |
|---|---|
| `Wi-Fi'ı aç` | Anında Wi-Fi açar |
| `Pilim %20'ye düşünce ekranı karart` | Kalıcı kural oluşturur |
| `Eve varınca Wi-Fi'ı aç` | Konum tabanlı otomasyon |
| `Her sabah 07:30'da sessiz modu kapat` | Saat tabanlı otomasyon |
| `İstanbul'un hava durumunu söyle` | İnternet API kullanır |
| `İşlemci sıcaklığını göster` | Linux shell komutu çalıştırır |
| `Ahmet'e SMS gönder: 10 dk gecikiyorum` | Rehberden bulup SMS atar |

---

## 🏗️ Proje Yapısı

```
os-agent/
├── main.py                      # Ana KivyMD uygulaması
│   ├── ModelSecimEkrani         # İlk açılış — hangi model?
│   ├── ModelIndirmeEkrani       # İndirme ilerleme çubuğu
│   ├── OnboardingEkrani         # İzin + güven metni
│   ├── ChatEkrani               # Ana chat arayüzü
│   ├── GorevPaneliEkrani        # Aktif kural yönetimi
│   └── AyarlarEkrani            # Bildirim stili, model değiştirme
├── service.py                   # Android Foreground Service
├── buildozer.spec               # APK derleme konfigürasyonu
├── colab_build.ipynb            # Google Colab derleme rehberi
├── core/
│   ├── model_yoneticisi.py      # ⭐ YENİ: Otomatik model indirici
│   ├── android_api.py           # Android donanım fonksiyonları
│   ├── nlp_engine.py            # Yerel AI model yöneticisi
│   ├── code_executor.py         # Güvenli kod çalıştırma sandbox'ı
│   ├── memory.py                # SQLite kural ve konum hafızası
│   ├── arkaplan_servisi.py      # Kural kontrol döngüsü
│   └── permission_manager.py   # İzin yönetimi
└── p4a-recipes/
    └── llama_cpp_python/        # ARM64 derleme recipe
```

---

## 🔒 Mimari Özet

```
İlk Açılış:
  Model Seçimi → İndirme (HuggingFace, tek seferlik) → İzinler → Chat

Normal Kullanım:
  Kullanıcı yazar → Kapsam kontrolü → Model RAM'e yükle (~1sn)
  → Python kodu üret → Sandbox exec() → Sonucu göster → Model sil

Arka Planda (her 5 sn):
  Aktif kuralları kontrol et → Koşul sağlandıysa kodu çalıştır
  (AI modeli asla yüklü değil → %1 pil kullanımı)
```
