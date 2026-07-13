# p4a-recipes/ — İsteğe Bağlı, İleri Seviye Recipe'ler

Bu klasör, `buildozer.spec`'teki `p4a.local_recipes = p4a-recipes/`
ayarıyla python-for-android'e tanıtılan **özel derleme tarifleridir**.

## llama_cpp_python/

Uygulamanın yerel AI modelini (Phi-3 Mini / Gemma 2B / TinyLlama, GGUF
formatında) çalıştırmak için kullanılan `llama-cpp-python` paketinin
Android ARM64 için cross-compile edilmesini sağlayan **deneysel** bir
recipe.

**Varsayılan APK derlemesine dahil DEĞİLDİR.** `buildozer.spec`'in
`requirements =` satırında bu paket YOKTUR — bilinçli bir mühendislik
kararıdır:

- llama-cpp-python, python-for-android'in resmi/bakımlı recipe
  deposunda yer almaz. CMake + NDK toolchain'iyle cross-compile etmek
  kırılgandır ve NDK/derleyici sürüm güncellemeleriyle sık bozulur.
- Uygulama, model kurulu olmasa bile **tamamen çalışır durumdadır**:
  `core/nlp_engine.py`, `llama_cpp` içe aktarılamadığında (veya model
  dosyası yoksa) otomatik olarak, yaygın komutları (wifi, sessiz mod,
  pil bazlı otomasyon, parlaklık, bluetooth vb.) düzenli ifadelerle
  tanıyan bir **STUB (kural tabanlı) motoruna** düşer. Yani "modelsiz
  APK" = "sınırlı ama gerçek işlevsellik", çökmeyen bir uygulama demektir.
- Bu yaklaşım, görevin "llama-cpp-python Android'de çalışamıyorsa,
  işlevselliği kaybetmeden onu isteğe bağlı hale getir" gereksinimini
  karşılar.

### Model desteğini derlemeye eklemek isterseniz

1. `buildozer.spec` → `requirements =` satırına `,llama-cpp-python`
   ekleyin.
2. `buildozer android clean` çalıştırıp yeniden derleyin (temiz derleme
   şart, aksi halde eski önbellek çakışabilir).
3. Derleme süresi belirgin şekilde uzar (tüm llama.cpp C++ kaynağı
   ARM64 için derlenir) ve NDK/CMake sürüm uyumsuzluklarına karşı ek
   hata ayıklama gerekebilir. Bu durumda derleme loglarını paylaşarak
   ilerlemek en hızlı yoldur.
4. Derleme başarısız olursa uygulama **hiçbir şekilde bozulmaz** —
   `llama-cpp-python`'ı requirements'tan çıkarıp tekrar derlemeniz
   yeterlidir; STUB motoru zaten devrede kalır.
