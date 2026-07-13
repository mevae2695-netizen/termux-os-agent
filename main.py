"""
OS Agent — Ana KivyMD Uygulaması
Premium chat arayüzü: Gemini / Claude / ChatGPT kalitesinde.

Ekranlar:
  ModelSecimEkranı  : İlk açılış — hangi model indirilsin?
  ModelIndirmeEkranı: İndirme ilerleme çubuğu
  OnboardingEkranı  : İzin + güven metni
  ChatEkranı        : Ana chat arayüzü
  GorevPaneliEkranı : Sağ swipe ile aktif kural yönetimi
  AyarlarEkranı     : Bildirim stili, model yönetimi
"""

import os
import threading
from datetime import datetime

from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.uix.screenmanager import ScreenManager, FadeTransition

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.boxlayout import MDBoxLayout

from core.memory import Memory
from core.nlp_engine import metni_isle
from core.code_executor import kodu_calistir
from core.arkaplan_servisi import servisi_baslat
from core.model_yoneticisi import (
    MODEL_KATALOGU,
    ModelIndirici,
    herhangi_model_var_mi,
    model_yolu,
    model_yuklu_mu,
)


# ===========================================================================
# KV Arayüz Tanımı
# ===========================================================================
KV = """
#:import FadeTransition kivy.uix.screenmanager.FadeTransition
#:import dp kivy.metrics.dp
#:import sp kivy.metrics.sp

ScreenManager:
    id: sm
    transition: FadeTransition(duration=0.3)
    ModelSecimEkrani:
        name: "model_secim"
    ModelIndirmeEkrani:
        name: "model_indirme"
    OnboardingEkrani:
        name: "onboarding"
    ChatEkrani:
        name: "chat"
    GorevPaneliEkrani:
        name: "gorev_paneli"
    AyarlarEkrani:
        name: "ayarlar"


# ------------------------------------------------------------------
# Model Seçim Ekranı
# ------------------------------------------------------------------
<ModelSecimEkrani>:
    MDBoxLayout:
        orientation: "vertical"
        md_bg_color: app.zemin

        MDBoxLayout:
            orientation: "vertical"
            padding: dp(32), dp(56), dp(32), dp(8)
            spacing: dp(10)
            size_hint_y: None
            height: dp(140)

            MDLabel:
                text: "OS Agent"
                font_style: "H4"
                bold: True
                halign: "center"
                theme_text_color: "Custom"
                text_color: app.vurgu

            MDLabel:
                text: "Telefonunuzu doğal dille yönetin"
                font_style: "Subtitle1"
                halign: "center"
                theme_text_color: "Custom"
                text_color: app.soluk

        MDLabel:
            text: "Yapay zeka modeli seçin"
            font_style: "H6"
            bold: True
            halign: "center"
            theme_text_color: "Custom"
            text_color: app.beyaz
            size_hint_y: None
            height: dp(40)

        MDLabel:
            text: "Model yalnızca bir kez indirilir ve cihazınızda saklanır."
            font_size: sp(13)
            halign: "center"
            theme_text_color: "Custom"
            text_color: app.soluk
            size_hint_y: None
            height: dp(28)

        MDScrollView:
            do_scroll_x: False
            MDBoxLayout:
                id: model_listesi
                orientation: "vertical"
                padding: dp(20), dp(12)
                spacing: dp(12)
                size_hint_y: None
                height: self.minimum_height


# ------------------------------------------------------------------
# Model İndirme Ekranı
# ------------------------------------------------------------------
<ModelIndirmeEkrani>:
    indir_yuzde: 0
    model_isim: ""

    MDBoxLayout:
        orientation: "vertical"
        md_bg_color: app.zemin
        padding: dp(36)
        spacing: dp(24)

        Widget:
            size_hint_y: None
            height: dp(60)

        MDLabel:
            text: "Model İndiriliyor"
            font_style: "H5"
            bold: True
            halign: "center"
            theme_text_color: "Custom"
            text_color: app.beyaz

        MDLabel:
            id: model_isim_etiket
            text: root.model_isim
            font_style: "Subtitle1"
            halign: "center"
            theme_text_color: "Custom"
            text_color: app.vurgu

        MDBoxLayout:
            orientation: "vertical"
            size_hint_y: None
            height: dp(80)
            spacing: dp(10)

            MDProgressBar:
                id: ilerleme_cubugu
                value: root.indir_yuzde
                max: 100
                color: app.vurgu

            MDLabel:
                id: ilerleme_metin
                text: "Bağlanıyor…"
                font_size: sp(14)
                halign: "center"
                theme_text_color: "Custom"
                text_color: app.soluk

        MDCard:
            orientation: "vertical"
            padding: dp(20)
            radius: [14]
            md_bg_color: app.kart
            size_hint_y: None
            height: self.minimum_height

            MDLabel:
                text: "💡  İpucu"
                font_style: "Subtitle1"
                bold: True
                theme_text_color: "Custom"
                text_color: app.vurgu
                size_hint_y: None
                height: dp(32)

            MDLabel:
                text: "İndirme sırasında uygulamayı kapatabilirsiniz. Bir sonraki açılışta kaldığı yerden devam eder."
                font_size: sp(13)
                theme_text_color: "Custom"
                text_color: app.soluk
                size_hint_y: None
                height: self.texture_size[1]
                text_size: self.width, None

        Widget:

        MDFlatButton:
            text: "İptal"
            theme_text_color: "Custom"
            text_color: app.soluk
            pos_hint: {"center_x": 0.5}
            on_release: root.iptal_et()


# ------------------------------------------------------------------
# Onboarding / İzin Ekranı
# ------------------------------------------------------------------
<OnboardingEkrani>:
    MDBoxLayout:
        orientation: "vertical"
        md_bg_color: app.zemin

        MDBoxLayout:
            orientation: "vertical"
            padding: dp(32), dp(52), dp(32), dp(0)
            spacing: dp(10)
            size_hint_y: None
            height: dp(120)

            MDLabel:
                text: "Son Adım"
                font_style: "H5"
                bold: True
                halign: "center"
                theme_text_color: "Custom"
                text_color: app.vurgu

            MDLabel:
                text: "Telefonunuzu yönetmek için izinlere ihtiyaç var"
                font_style: "Subtitle1"
                halign: "center"
                theme_text_color: "Custom"
                text_color: app.soluk

        MDScrollView:
            MDBoxLayout:
                orientation: "vertical"
                padding: dp(20)
                spacing: dp(16)
                size_hint_y: None
                height: self.minimum_height

                MDCard:
                    orientation: "vertical"
                    padding: dp(20)
                    radius: [16]
                    md_bg_color: app.kart
                    size_hint_y: None
                    height: self.minimum_height

                    MDLabel:
                        text: "🔒  Gizlilik Taahhüdü"
                        font_style: "H6"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: app.beyaz
                        size_hint_y: None
                        height: dp(36)

                    MDLabel:
                        text: app.guven_metni
                        markup: True
                        font_size: sp(14)
                        theme_text_color: "Custom"
                        text_color: app.soluk
                        size_hint_y: None
                        height: self.texture_size[1]
                        text_size: self.width, None

                MDBoxLayout:
                    orientation: "vertical"
                    size_hint_y: None
                    height: dp(130)
                    spacing: dp(10)

                    MDRaisedButton:
                        text: "İzinleri Ver ve Başla  →"
                        font_size: sp(16)
                        height: dp(52)
                        radius: [26]
                        md_bg_color: app.vurgu
                        pos_hint: {"center_x": 0.5}
                        on_release: root.izin_iste()

                    MDFlatButton:
                        text: "Şimdi değil (kısıtlı mod)"
                        theme_text_color: "Custom"
                        text_color: app.soluk
                        pos_hint: {"center_x": 0.5}
                        on_release: root.kisitli_baslat()


# ------------------------------------------------------------------
# Chat Ekranı
# ------------------------------------------------------------------
<ChatEkrani>:
    MDBoxLayout:
        orientation: "vertical"
        md_bg_color: app.zemin

        MDTopAppBar:
            title: "OS Agent"
            specific_text_color: app.beyaz
            md_bg_color: app.kart
            elevation: 0
            left_action_items: [["menu", lambda x: root.gorev_panelini_ac()]]
            right_action_items:
                [["cog-outline", lambda x: root.ayarlara_git()], \
                 ["delete-outline", lambda x: root.gecmisi_temizle()]]

        ScrollView:
            id: mesaj_scroll
            do_scroll_x: False
            MDBoxLayout:
                id: mesaj_kutu
                orientation: "vertical"
                padding: dp(14), dp(10)
                spacing: dp(10)
                size_hint_y: None
                height: self.minimum_height

        BoxLayout:
            id: buton_alani
            size_hint_y: None
            height: dp(0)
            padding: dp(14), dp(0), dp(14), dp(6)
            spacing: dp(8)

        MDBoxLayout:
            orientation: "horizontal"
            padding: dp(10), dp(6), dp(10), dp(14)
            spacing: dp(6)
            size_hint_y: None
            height: dp(68)
            md_bg_color: app.kart

            MDTextFieldRound:
                id: giris
                hint_text: "Bir görev yaz…"
                font_size: sp(15)
                fill_color: app.zemin
                normal_color: app.zemin
                color_active: app.vurgu
                on_text_validate: root.gonder()

            MDIconButton:
                icon: "send"
                theme_text_color: "Custom"
                text_color: app.vurgu
                on_release: root.gonder()


# ------------------------------------------------------------------
# Görev Paneli
# ------------------------------------------------------------------
<GorevPaneliEkrani>:
    MDBoxLayout:
        orientation: "vertical"
        md_bg_color: app.zemin

        MDTopAppBar:
            title: "Aktif Görevler"
            specific_text_color: app.beyaz
            md_bg_color: app.kart
            elevation: 0
            left_action_items: [["arrow-left", lambda x: root.geri_don()]]

        MDScrollView:
            MDList:
                id: kural_listesi
                padding: dp(6)


# ------------------------------------------------------------------
# Ayarlar Ekranı
# ------------------------------------------------------------------
<AyarlarEkrani>:
    MDBoxLayout:
        orientation: "vertical"
        md_bg_color: app.zemin

        MDTopAppBar:
            title: "Ayarlar"
            specific_text_color: app.beyaz
            md_bg_color: app.kart
            elevation: 0
            left_action_items: [["arrow-left", lambda x: root.geri_don()]]

        MDScrollView:
            MDBoxLayout:
                orientation: "vertical"
                padding: dp(16)
                spacing: dp(16)
                size_hint_y: None
                height: self.minimum_height

                # Model bilgisi
                MDCard:
                    orientation: "vertical"
                    padding: dp(16)
                    radius: [12]
                    md_bg_color: app.kart
                    size_hint_y: None
                    height: self.minimum_height

                    MDLabel:
                        text: "🧠  Yüklü Model"
                        font_style: "Subtitle1"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: app.beyaz
                        size_hint_y: None
                        height: dp(36)

                    MDLabel:
                        id: aktif_model_etiketi
                        text: app.aktif_model_isim
                        font_size: sp(14)
                        theme_text_color: "Custom"
                        text_color: app.vurgu
                        size_hint_y: None
                        height: dp(28)

                    MDRaisedButton:
                        text: "Farklı Model Yükle"
                        height: dp(42)
                        radius: [8]
                        md_bg_color: app.zemin
                        font_size: sp(13)
                        on_release: root.model_degistir()

                # Bildirim stili
                MDCard:
                    orientation: "vertical"
                    padding: dp(16)
                    radius: [12]
                    md_bg_color: app.kart
                    size_hint_y: None
                    height: self.minimum_height

                    MDLabel:
                        text: "🔔  Bildirim Stili"
                        font_style: "Subtitle1"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: app.beyaz
                        size_hint_y: None
                        height: dp(36)

                    MDLabel:
                        text: "Kural tetiklendiğinde nasıl bildirilsin?"
                        font_size: sp(13)
                        theme_text_color: "Custom"
                        text_color: app.soluk
                        size_hint_y: None
                        height: dp(24)

                    MDBoxLayout:
                        orientation: "vertical"
                        size_hint_y: None
                        height: self.minimum_height
                        spacing: dp(6)
                        padding: dp(0), dp(8), dp(0), dp(0)

                        MDRaisedButton:
                            text: "📳  Minimal Bildirim (varsayılan)"
                            height: dp(44)
                            radius: [8]
                            font_size: sp(13)
                            md_bg_color: app.vurgu if app.bildirim_stili == "minimal" else app.zemin
                            on_release: app.bildirim_stili_kaydet("minimal")

                        MDRaisedButton:
                            text: "💬  Sadece Toast"
                            height: dp(44)
                            radius: [8]
                            font_size: sp(13)
                            md_bg_color: app.vurgu if app.bildirim_stili == "toast" else app.zemin
                            on_release: app.bildirim_stili_kaydet("toast")

                        MDRaisedButton:
                            text: "🎮  Hiçbir Şey (Oyun / Gizlilik Modu)"
                            height: dp(44)
                            radius: [8]
                            font_size: sp(13)
                            md_bg_color: app.vurgu if app.bildirim_stili == "hicbiri" else app.zemin
                            on_release: app.bildirim_stili_kaydet("hicbiri")

                # Servis durumu
                MDCard:
                    orientation: "vertical"
                    padding: dp(16)
                    radius: [12]
                    md_bg_color: app.kart
                    size_hint_y: None
                    height: self.minimum_height

                    MDLabel:
                        text: "⚙️  Servis Durumu"
                        font_style: "Subtitle1"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: app.beyaz
                        size_hint_y: None
                        height: dp(36)

                    MDLabel:
                        text: "⬤  Arka plan otomasyon motoru aktif"
                        font_size: sp(14)
                        theme_text_color: "Custom"
                        text_color: [0.2, 0.9, 0.5, 1]
                        size_hint_y: None
                        height: dp(28)
"""


# ===========================================================================
# Ekranlar
# ===========================================================================

class ModelSecimEkrani(MDScreen):
    def on_enter(self):
        self.ids.model_listesi.clear_widgets()
        for anahtar, bilgi in MODEL_KATALOGU.items():
            self._kart_ekle(anahtar, bilgi)

    def _kart_ekle(self, anahtar: str, bilgi: dict):
        from kivy.metrics import dp
        app = MDApp.get_running_app()
        yuklu = model_yuklu_mu(anahtar)

        kart = MDCard(
            orientation="vertical",
            padding=[dp(18), dp(16)],
            radius=[16],
            md_bg_color=app.kart,
            size_hint_y=None,
            height=dp(130),
            ripple_behavior=True,
            elevation=2,
        )

        baslik = MDLabel(
            text=bilgi["isim"] + ("  ✓" if yuklu else ""),
            font_style="H6",
            bold=True,
            theme_text_color="Custom",
            text_color=app.vurgu if yuklu else app.beyaz,
            size_hint_y=None,
            height=dp(32),
        )

        aciklama = MDLabel(
            text=bilgi["aciklama"],
            font_size="13sp",
            theme_text_color="Custom",
            text_color=app.soluk,
            size_hint_y=None,
            height=dp(24),
        )

        etiket = "Kullan  →" if yuklu else f"İndir ({bilgi['boyut_mb']} MB)  →"
        btn = MDRaisedButton(
            text=etiket,
            height=dp(40),
            radius=[8],
            md_bg_color=app.vurgu if yuklu else app.zemin,
            font_size="13sp",
        )
        btn.bind(on_release=lambda x, a=anahtar, y=yuklu: self._secim_yap(a, y))

        kart.add_widget(baslik)
        kart.add_widget(aciklama)
        kart.add_widget(btn)
        self.ids.model_listesi.add_widget(kart)

    def _secim_yap(self, anahtar: str, yuklu: bool):
        app = MDApp.get_running_app()
        app.secili_model = anahtar
        if yuklu:
            app.aktif_model_anahtar = anahtar
            app.aktif_model_isim = MODEL_KATALOGU[anahtar]["isim"]
            app.memory.ayar_yaz("aktif_model", anahtar)
            self._sonraki_adima_gec()
        else:
            self.manager.get_screen("model_indirme").model_isim = MODEL_KATALOGU[anahtar]["isim"]
            self.manager.current = "model_indirme"
            self.manager.get_screen("model_indirme").basla(anahtar)

    def _sonraki_adima_gec(self):
        app = MDApp.get_running_app()
        izin_verildi = app.memory.ayar_oku("izin_tamamlandi", False)
        if izin_verildi:
            self.manager.current = "chat"
        else:
            self.manager.current = "onboarding"


class ModelIndirmeEkrani(MDScreen):
    indir_yuzde = NumericProperty(0)
    model_isim = StringProperty("")

    def __init__(self, **kw):
        super().__init__(**kw)
        self._indirici = ModelIndirici()

    def basla(self, model_anahtari: str):
        self.indir_yuzde = 0
        self.ids.ilerleme_metin.text = "Bağlantı kuruluyor…"
        self._indirici.indir(
            model_anahtari,
            ilerleme_cb=self._ilerleme,
            tamamlandi_cb=self._tamamlandi,
        )

    def _ilerleme(self, yuzde: float, mesaj: str):
        Clock.schedule_once(lambda dt: self._guncelle_ui(yuzde, mesaj), 0)

    def _guncelle_ui(self, yuzde: float, mesaj: str):
        self.indir_yuzde = yuzde * 100
        self.ids.ilerleme_metin.text = mesaj

    def _tamamlandi(self, basarili: bool, mesaj: str):
        Clock.schedule_once(lambda dt: self._tamamlandi_ui(basarili, mesaj), 0)

    def _tamamlandi_ui(self, basarili: bool, mesaj: str):
        app = MDApp.get_running_app()
        if basarili:
            anahtar = app.secili_model
            app.aktif_model_anahtar = anahtar
            app.aktif_model_isim = MODEL_KATALOGU[anahtar]["isim"]
            app.memory.ayar_yaz("aktif_model", anahtar)
            izin_verildi = app.memory.ayar_oku("izin_tamamlandi", False)
            self.manager.current = "onboarding" if not izin_verildi else "chat"
        else:
            self.ids.ilerleme_metin.text = mesaj
            self.ids.ilerleme_metin.text_color = [0.9, 0.3, 0.3, 1]

    def iptal_et(self):
        self._indirici.iptal_et()
        self.manager.current = "model_secim"


class OnboardingEkrani(MDScreen):
    def izin_iste(self):
        try:
            from android.permissions import request_permissions, Permission  # type: ignore
            request_permissions([
                Permission.ACCESS_FINE_LOCATION,
                Permission.READ_CONTACTS,
                Permission.SEND_SMS,
                Permission.READ_SMS,
                Permission.CALL_PHONE,
                Permission.CAMERA,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
            ], callback=self._izin_sonucu)
        except ImportError:
            self._tamamla()

    def _izin_sonucu(self, izinler, sonuclar):
        self._tamamla()

    def _tamamla(self):
        MDApp.get_running_app().memory.ayar_yaz("izin_tamamlandi", True)
        self.manager.current = "chat"

    def kisitli_baslat(self):
        self.manager.current = "chat"


class ChatEkrani(MDScreen):
    def on_enter(self):
        gecmis = MDApp.get_running_app().memory.son_mesajlar(30)
        if not gecmis:
            self._mesaj_ekle(self._hosgeldin(), "asistan")
        else:
            for m in gecmis:
                self._mesaj_ekle(m["icerik"], m["rol"])

    def _hosgeldin(self):
        app = MDApp.get_running_app()
        return (
            f"👋 Merhaba! Ben OS Agent.\n\n"
            f"Yüklü model: [b]{app.aktif_model_isim}[/b]\n\n"
            "Bana doğal dille görev verebilirsin:\n"
            "• \"Pilim %20'ye düşünce ekranı karart\"\n"
            "• \"Eve varınca Wi-Fi'ı aç\"\n"
            "• \"Her sabah 07:30'da sessiz modu kapat\"\n\n"
            "Hiçbir veri internete gitmez. [b]Tamamen cihazında çalışırım.[/b]"
        )

    def gonder(self):
        giris = self.ids.giris
        metin = giris.text.strip()
        if not metin:
            return
        giris.text = ""
        self._butonlari_temizle()
        self._mesaj_ekle(metin, "kullanici")
        MDApp.get_running_app().memory.mesaj_ekle("kullanici", metin)
        yaziyor = self._yaziyor_baslat()
        threading.Thread(
            target=self._arka_planda,
            args=(metin, yaziyor),
            daemon=True,
        ).start()

    def _arka_planda(self, metin: str, yaziyor):
        app = MDApp.get_running_app()
        konumlar = app.memory.tum_konumlar()
        ozet = ("Kayıtlı konumlar: " + ", ".join(k["etiket"] for k in konumlar)) if konumlar else ""
        yol = model_yolu(app.aktif_model_anahtar) if app.aktif_model_anahtar else ""
        sonuc = metni_isle(yol, metin, ozet)
        Clock.schedule_once(lambda dt: self._yaziyor_durdur(yaziyor), 0)
        Clock.schedule_once(lambda dt: self._isle(sonuc), 0.1)

    def _isle(self, sonuc: dict):
        app = MDApp.get_running_app()
        tur = sonuc.get("tur", "hata")

        if tur == "ret":
            m = sonuc.get("mesaj", "Bu isteği yapamam.")
            self._mesaj_ekle(m, "asistan")
            app.memory.mesaj_ekle("asistan", m)

        elif tur == "eksik_bilgi":
            m = sonuc.get("mesaj", "")
            self._mesaj_ekle(m, "sistem")
            app.memory.mesaj_ekle("asistan", m)
            btn_etiket = sonuc.get("eylem_butonu", "")
            eylem = sonuc.get("eylem_tipi", "")
            if btn_etiket:
                self._buton_ekle(btn_etiket, eylem)

        elif tur == "otomasyon":
            baslik = sonuc.get("baslik", "Görev")
            aciklama = sonuc.get("aciklama", "")
            kod = sonuc.get("kod", "")
            tetik = sonuc.get("tetikleyici", "anlik")

            sb = kodu_calistir(kod)

            if sb.izin_hatasi:
                self._mesaj_ekle(sb.hata, "sistem")
                self._buton_ekle("⚙️ Uygulama İzinlerini Aç", "izin_iste")
            elif not sb.basarili:
                self._mesaj_ekle(f"⚠️ {sb.hata}", "sistem")
            else:
                kural_notu = ""
                if tetik != "anlik":
                    kid = app.memory.kural_ekle(baslik, aciklama, tetik, kod)
                    kural_notu = f"\n\n📌 Kural kaydedildi. Görev panelinde yönetebilirsin."
                cikti = sb.cikti
                yanit = f"✅ [b]{baslik}[/b]\n{aciklama}{kural_notu}"
                if cikti and "tamamlandı" not in cikti:
                    yanit += f"\n\n{cikti}"
                self._mesaj_ekle(yanit, "asistan")
                app.memory.mesaj_ekle("asistan", yanit)

        elif tur == "hata":
            self._mesaj_ekle(f"⚠️ {sonuc.get('mesaj', 'Bilinmeyen hata.')}", "sistem")

    # ---- UI yardımcıları ----

    def _mesaj_ekle(self, metin: str, gonderici: str):
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.widget import Widget
        from kivy.metrics import dp

        app = MDApp.get_running_app()
        renk_map = {
            "kullanici": app.vurgu,
            "asistan":   app.kart,
            "sistem":    [0.14, 0.11, 0.06, 1],
        }
        radius_map = {
            "kullanici": [18, 18, 4, 18],
            "asistan":   [18, 18, 18, 4],
            "sistem":    [12, 12, 12, 12],
        }

        kart = MDCard(
            orientation="vertical",
            padding=[dp(12), dp(10)],
            size_hint_x=0.84,
            md_bg_color=renk_map.get(gonderici, app.kart),
            radius=radius_map.get(gonderici, [12]*4),
            elevation=0,
        )

        etiket = MDLabel(
            text=metin,
            markup=True,
            theme_text_color="Custom",
            text_color=[1, 1, 1, 1] if gonderici == "kullanici" else app.beyaz,
            font_size="15sp",
            size_hint_y=None,
        )
        etiket.bind(texture_size=lambda i, v: setattr(i, "height", v[1]))
        etiket.bind(width=lambda i, v: setattr(i, "text_size", (v, None)))
        kart.add_widget(etiket)

        kutu = BoxLayout(size_hint_y=None)
        kutu.bind(minimum_height=kutu.setter("height"))
        if gonderici == "kullanici":
            kutu.add_widget(Widget())
        kutu.add_widget(kart)
        if gonderici != "kullanici":
            kutu.add_widget(Widget())

        kart.bind(height=lambda i, v: setattr(kutu, "height", v + 4))
        self.ids.mesaj_kutu.add_widget(kutu)
        Clock.schedule_once(self._alta_kay, 0.1)

    def _alta_kay(self, dt):
        try:
            self.ids.mesaj_scroll.scroll_y = 0
        except Exception:
            pass

    def _yaziyor_baslat(self):
        from kivy.metrics import dp
        app = MDApp.get_running_app()
        kart = MDCard(
            orientation="horizontal",
            padding=[dp(14), dp(12)],
            size_hint_x=0.28,
            size_hint_y=None,
            height=dp(44),
            md_bg_color=app.kart,
            radius=[18, 18, 18, 4],
            elevation=0,
        )
        etiket = MDLabel(
            text="● ● ●",
            theme_text_color="Custom",
            text_color=app.soluk,
            font_size="13sp",
            halign="center",
        )
        kart.add_widget(etiket)
        self.ids.mesaj_kutu.add_widget(kart)
        Clock.schedule_once(self._alta_kay, 0.1)
        return kart

    def _yaziyor_durdur(self, widget):
        try:
            self.ids.mesaj_kutu.remove_widget(widget)
        except Exception:
            pass

    def _buton_ekle(self, etiket: str, eylem: str):
        from kivy.metrics import dp
        app = MDApp.get_running_app()
        alan = self.ids.buton_alani
        alan.height = dp(60)
        btn = MDRaisedButton(
            text=etiket,
            height=dp(44),
            radius=[22],
            md_bg_color=app.vurgu,
            font_size="13sp",
        )
        btn.bind(on_release=lambda x: self._eylem(eylem))
        alan.add_widget(btn)

    def _butonlari_temizle(self):
        from kivy.metrics import dp
        alan = self.ids.buton_alani
        alan.clear_widgets()
        alan.height = dp(0)

    def _eylem(self, eylem: str):
        self._butonlari_temizle()
        if eylem == "konum_kaydet":
            threading.Thread(target=self._konum_kaydet, daemon=True).start()
        elif eylem == "izin_iste":
            try:
                from core.permission_manager import IzinYoneticisi
                IzinYoneticisi().ayarlar_sayfasını_ac()
            except Exception:
                pass

    def _konum_kaydet(self):
        from core.android_api import konum_al
        app = MDApp.get_running_app()
        konum = konum_al()
        if "hata" not in konum:
            app.memory.konum_kaydet("ev", konum["enlem"], konum["boylam"])
            Clock.schedule_once(lambda dt: self._mesaj_ekle(
                "✅ [b]Ev konumu kaydedildi.[/b]\nArtık bu konuma yaklaştığında otomasyon tetiklenebilir.",
                "asistan",
            ), 0)
        else:
            Clock.schedule_once(lambda dt: self._mesaj_ekle(
                "⚠️ Konum alınamadı. GPS açık mı kontrol edin.", "sistem"
            ), 0)

    def gorev_panelini_ac(self):
        self.manager.current = "gorev_paneli"

    def ayarlara_git(self):
        self.manager.current = "ayarlar"

    def gecmisi_temizle(self):
        MDApp.get_running_app().memory.chat_gecmisini_temizle()
        self.ids.mesaj_kutu.clear_widgets()
        self._mesaj_ekle(self._hosgeldin(), "asistan")


class GorevPaneliEkrani(MDScreen):
    def on_enter(self):
        self._yukle()

    def _yukle(self):
        app = MDApp.get_running_app()
        liste = self.ids.kural_listesi
        liste.clear_widgets()
        kurallar = app.memory.tum_kurallar()

        if not kurallar:
            from kivy.metrics import dp
            bos = MDLabel(
                text="Henüz kaydedilmiş bir görev yok.\nChat'ten yeni bir görev tanımlayın.",
                halign="center",
                theme_text_color="Custom",
                text_color=app.soluk,
                font_size="15sp",
            )
            liste.add_widget(bos)
            return

        for k in kurallar:
            self._satir_ekle(k)

    def _satir_ekle(self, kural: dict):
        from kivymd.uix.list import TwoLineAvatarIconListItem
        from kivymd.uix.selectioncontrol import MDSwitch
        from kivymd.uix.button import MDIconButton

        app = MDApp.get_running_app()
        satir = TwoLineAvatarIconListItem(
            text=kural.get("baslik", "Görev"),
            secondary_text=f"Tetikleyici: {kural.get('tetikleyici', '?')}",
            theme_text_color="Custom",
            text_color=app.beyaz,
            secondary_theme_text_color="Custom",
            secondary_text_color=app.soluk,
        )
        sw = MDSwitch(active=bool(kural.get("aktif", 1)), pos_hint={"center_y": 0.5})
        kid = kural["id"]
        sw.bind(active=lambda w, v, k=kid: app.memory.kural_guncelle_aktif(k, v))
        satir.add_widget(sw)

        del_btn = MDIconButton(
            icon="delete-outline",
            theme_text_color="Custom",
            text_color=[0.9, 0.3, 0.3, 1],
        )
        del_btn.bind(on_release=lambda x, k=kid: self._sil(k))
        satir.add_widget(del_btn)
        self.ids.kural_listesi.add_widget(satir)

    def _sil(self, kid: str):
        MDApp.get_running_app().memory.kural_sil(kid)
        self._yukle()

    def geri_don(self):
        self.manager.current = "chat"


class AyarlarEkrani(MDScreen):
    def on_enter(self):
        app = MDApp.get_running_app()
        self.ids.aktif_model_etiketi.text = app.aktif_model_isim

    def model_degistir(self):
        self.manager.current = "model_secim"

    def geri_don(self):
        self.manager.current = "chat"


# ===========================================================================
# Ana Uygulama
# ===========================================================================
class OSAgentApp(MDApp):

    # Renk paleti (koyu, premium)
    zemin = [0.06, 0.06, 0.08, 1]
    kart  = [0.11, 0.11, 0.15, 1]
    vurgu = [0.38, 0.48, 1.00, 1]
    beyaz = [0.95, 0.95, 0.97, 1]
    soluk = [0.54, 0.54, 0.62, 1]

    aktif_model_anahtar = StringProperty("")
    aktif_model_isim    = StringProperty("Model seçilmedi")
    bildirim_stili      = StringProperty("minimal")
    secili_model        = StringProperty("")

    guven_metni = (
        "OS Agent [b]%100 açık kaynaklıdır[/b]. Tüm kaynak kodunu inceleyebilir "
        "ve değiştirebilirsiniz.\n\n"
        "[b]Hiçbir veriniz internete gitmez.[/b] Yapay zeka modeli ve tüm otomasyon "
        "mantığı tamamen cihazınızda çalışır. İnternet bağlantısı gerektirmez.\n\n"
        "Konumunuz, rehberiniz ve SMS'leriniz yalnızca sizin tanımladığınız "
        "otomasyonlar için kullanılır."
    )

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Indigo"
        self.memory = Memory()
        self.bildirim_stili = self.memory.ayar_oku("bildirim_stili", "minimal")

        # Daha önce seçilmiş bir model var mı?
        kayitli = self.memory.ayar_oku("aktif_model", "")
        if kayitli and model_yuklu_mu(kayitli):
            self.aktif_model_anahtar = kayitli
            self.aktif_model_isim = MODEL_KATALOGU.get(kayitli, {}).get("isim", kayitli)
        else:
            # Herhangi bir gguf var mı?
            bulunan = herhangi_model_var_mi()
            if bulunan:
                self.aktif_model_anahtar = bulunan
                self.aktif_model_isim = MODEL_KATALOGU.get(bulunan, {}).get("isim", bulunan)
                self.memory.ayar_yaz("aktif_model", bulunan)

        return Builder.load_string(KV)

    def on_start(self):
        servisi_baslat()

        if not self.aktif_model_anahtar:
            # İlk açılış — model seçim ekranına git
            self.root.ids.sm.current = "model_secim"
        else:
            izin_verildi = self.memory.ayar_oku("izin_tamamlandi", False)
            self.root.ids.sm.current = "onboarding" if not izin_verildi else "chat"

    def on_pause(self):
        return True

    def on_resume(self):
        pass

    def bildirim_stili_kaydet(self, stil: str):
        self.bildirim_stili = stil
        self.memory.ayar_yaz("bildirim_stili", stil)


if __name__ == "__main__":
    OSAgentApp().run()
