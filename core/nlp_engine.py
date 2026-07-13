"""
NLP Motoru — Yerel AI Model Yöneticisi
Phi-3-mini, Gemma-2B veya TinyLlama ile Türkçe NL → Python kodu dönüşümü.

Aç-Kapa Hafıza Yönetimi:
  - Model yalnızca istek geldiğinde RAM'e yüklenir
  - Kod üretimi tamamlanınca gc.collect() + model=None ile sıfırlanır
  - Arka plan servisi çalışırken model asla RAM'de değildir
"""

import gc
import json
import re
import time
from typing import Optional

from core.android_api import ANDROID_API_DOKUMAN

# ---------------------------------------------------------------------------
# Kapsam dışı istek tespiti (modelsiz, hızlı regex kontrolü)
# ---------------------------------------------------------------------------
KAPSAM_DISI_KALIPLAR = [
    r"\bweb\s*site\b",
    r"\bhtml\b",
    r"\bcss\b",
    r"\bjava\s*script\b",
    r"\bweb\s*tasarım\b",
    r"\bblog\b.*\byaz\b",
    r"\bmakal[e]\b.*\byaz\b",
    r"\bkod\s*yaz\b(?!.*telefon)",
    r"\buygulama\s*geliştir\b",
    r"\bveri\s*tabanı\s*kur\b(?!.*telefon)",
    r"\bsunucu\s*kur\b",
    r"\bapi\s*yaz\b",
    r"\byapay\s*zeka\s*eğit\b",
]

KAPSAM_DISI_YANIT = (
    "🤖 Ben sadece telefonunun içindeki donanımları kontrol etmek ve "
    "günlük görevleri otomatikleştirmek için tasarlandım. "
    "Web sitesi, kodlama, yazarlık veya sunucu işlemleri yapamam.\n\n"
    "Bunun yerine bana şunları söyleyebilirsin:\n"
    "• \"Eve varınca Wi-Fi'ı aç\"\n"
    "• \"Pilim %20'nin altına düşünce ekranı karart\"\n"
    "• \"Her gün sabah 08:00'de sessiz modu kapat\""
)

# ---------------------------------------------------------------------------
# Sistem promptu
# ---------------------------------------------------------------------------
SISTEM_PROMPTU = f"""Sen, yalnızca Android telefon donanımını kontrol etmek ve otomasyon görevleri oluşturmak için tasarlanmış özel bir Türkçe yapay zeka asistanısın.

YAPAMAYACAKLARIN:
- Web sitesi, HTML, CSS, JavaScript yazma
- Blog, makale, içerik yazarlığı
- Genel programlama veya yazılım geliştirme
- Sunucu kurulumu veya veritabanı yönetimi

YAPABİLECEKLERİN:
- Android telefon donanımını kontrol etmek
- Belirli koşullara bağlı otomasyonlar oluşturmak
- SMS göndermek, alarm kurmak, uygulama açmak
- Pil, internet verisi gibi bilgileri almak

Mevcut Fonksiyonlar:
{ANDROID_API_DOKUMAN}

CEVAP FORMAT:
Telefon/otomasyon görevi ise:
{{
  "tur": "otomasyon",
  "baslik": "Kısa başlık",
  "aciklama": "Türkçe açıklama",
  "tetikleyici": "anlik|konum:EV|pil:20|saat:07:30|tekrar:3600",
  "kod": "Python kodu"
}}

Kapsam dışıysa:
{{
  "tur": "ret",
  "mesaj": "Kibarca Türkçe red"
}}

Eksik bilgi varsa:
{{
  "tur": "eksik_bilgi",
  "mesaj": "Açıklama",
  "eylem_butonu": "Buton etiketi",
  "eylem_tipi": "konum_kaydet|izin_iste|bilgi_gir"
}}
"""

# ---------------------------------------------------------------------------
# Stub yanıtlar (model yokken)
# ---------------------------------------------------------------------------
_STUB_ORNEKLER = [
    (r"wifi.*(aç|aktif|etkinleştir)", {
        "tur": "otomasyon", "baslik": "Wi-Fi Aç",
        "aciklama": "Wi-Fi bağdaştırıcısını açar.",
        "tetikleyici": "anlik",
        "kod": "sonuc = wifi_ac()\ntoast_goster(sonuc)",
    }),
    (r"wifi.*(kapat|devre dışı|kapat)", {
        "tur": "otomasyon", "baslik": "Wi-Fi Kapat",
        "aciklama": "Wi-Fi bağdaştırıcısını kapatır.",
        "tetikleyici": "anlik",
        "kod": "sonuc = wifi_kapat()\ntoast_goster(sonuc)",
    }),
    (r"sessiz", {
        "tur": "otomasyon", "baslik": "Sessiz Mod",
        "aciklama": "Telefonu sessiz moda alır.",
        "tetikleyici": "anlik",
        "kod": "sonuc = sessiz_mod_ac()\ntoast_goster(sonuc)",
    }),
    (r"(pil|batarya).*(az|düş|%)", {
        "tur": "otomasyon", "baslik": "Düşük Pil Tasarrufu",
        "aciklama": "Pil %20'nin altına düşünce tasarruf modunu açar.",
        "tetikleyici": "pil:20",
        "kod": (
            "yuzde = pil_yuzde()\n"
            "if yuzde < 20:\n"
            "    tasarruf_modu_ac()\n"
            "    bildirim_gonder('Pil Tasarrufu', f'Pil %{yuzde} — Tasarruf modu açıldı.')"
        ),
    }),
    (r"eve.*(wifi|wi-fi)", {
        "tur": "eksik_bilgi",
        "mesaj": "'Ev' konumu henüz kaydedilmemiş. Şu anki konumunuzu ev olarak kaydetmek ister misiniz?",
        "eylem_butonu": "📍 Şu Anki Konumu Ev Olarak Kaydet",
        "eylem_tipi": "konum_kaydet",
    }),
    (r"(parlaklık|ekran).*(düş|azalt|karart)", {
        "tur": "otomasyon", "baslik": "Ekranı Karart",
        "aciklama": "Ekran parlaklığını düşürür.",
        "tetikleyici": "anlik",
        "kod": "parlaklık_ayarla(30)\ntoast_goster('Ekran karartıldı.')",
    }),
    (r"bluetooth.*(aç|aktif)", {
        "tur": "otomasyon", "baslik": "Bluetooth Aç",
        "aciklama": "Bluetooth'u açar.",
        "tetikleyici": "anlik",
        "kod": "sonuc = bluetooth_ac()\ntoast_goster(sonuc)",
    }),
]


class NLPMotoru:
    def __init__(self):
        self._model = None

    def model_yukle(self, yol: str) -> bool:
        if self._model is not None:
            return True
        if not yol or not __import__("os").path.isfile(yol):
            self._model = "STUB"
            return True
        try:
            from llama_cpp import Llama  # type: ignore
            self._model = Llama(
                model_path=yol,
                n_ctx=2048,
                n_threads=4,
                n_gpu_layers=0,
                verbose=False,
            )
            return True
        except ImportError:
            self._model = "STUB"
            return True
        except Exception as e:
            self._model = "STUB"
            return True

    def model_bosalt(self):
        if self._model and self._model != "STUB":
            try:
                del self._model
            except Exception:
                pass
        self._model = None
        gc.collect()

    def kapsam_disi_mi(self, metin: str) -> bool:
        ml = metin.lower()
        return any(re.search(k, ml) for k in KAPSAM_DISI_KALIPLAR)

    def isle(self, model_yolu: str, metin: str, hafiza: str = "") -> dict:
        if self.kapsam_disi_mi(metin):
            return {"tur": "ret", "mesaj": KAPSAM_DISI_YANIT}

        t0 = time.time()
        self.model_yukle(model_yolu)
        try:
            if self._model == "STUB":
                sonuc = self._stub(metin)
            else:
                raw = self._llm(metin, hafiza)
                sonuc = self._parse(raw)
            sonuc["_sure_sn"] = round(time.time() - t0, 2)
            return sonuc
        except Exception as e:
            return {"tur": "hata", "mesaj": f"İşlem hatası: {e}"}
        finally:
            self.model_bosalt()

    def _llm(self, metin: str, hafiza: str) -> str:
        hafiza_blok = f"\nKayıtlı bağlam:\n{hafiza}\n" if hafiza else ""
        prompt = (
            f"<|system|>\n{SISTEM_PROMPTU}{hafiza_blok}<|end|>\n"
            f"<|user|>\n{metin}<|end|>\n"
            f"<|assistant|>\n"
        )
        cikti = self._model(prompt, max_tokens=512, temperature=0.1, stop=["</s>", "<|end|>"])
        return cikti["choices"][0]["text"].strip()

    def _parse(self, ham: str) -> dict:
        m = re.search(r"\{[\s\S]*\}", ham)
        if not m:
            return {"tur": "otomasyon", "baslik": "Görev", "aciklama": ham[:200],
                    "tetikleyici": "anlik", "kod": "toast_goster('Görev tamamlandı.')"}
        try:
            return json.loads(m.group())
        except Exception:
            return {"tur": "hata", "mesaj": "Model yanıtı işlenemedi."}

    def _stub(self, metin: str) -> dict:
        ml = metin.lower()
        for (kalip, yanit) in _STUB_ORNEKLER:
            if re.search(kalip, ml):
                return dict(yanit)
        return {
            "tur": "otomasyon",
            "baslik": "Özel Görev",
            "aciklama": f'"{metin}" görevi oluşturuldu.',
            "tetikleyici": "anlik",
            "kod": "toast_goster('Görev çalıştırıldı.')",
        }


_motor = NLPMotoru()


def metni_isle(model_yolu: str, metin: str, hafiza: str = "") -> dict:
    return _motor.isle(model_yolu, metin, hafiza)
