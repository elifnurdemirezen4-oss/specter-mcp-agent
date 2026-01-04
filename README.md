# SPECTER 👻: AI Destekli Kurumsal Masaüstü Asistanı

Specter, **Model Context Protocol (MCP)** mimarisini kullanarak yerel LLM'leri (Ollama) Google Workspace araçlarıyla (Gmail, Calendar, Drive, Sheets) entegre eden, Python tabanlı akıllı bir masaüstü asistanıdır.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![MCP](https://img.shields.io/badge/Protocol-MCP-green)
![Ollama](https://img.shields.io/badge/AI-Ollama-orange)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

## 🌟 Özellikler

* **🤖 Yerel Yapay Zeka Entegrasyonu:** Ollama üzerinden Llama3 (veya diğer modeller) ile çalışır. Verileriniz buluta gitmeden yerelde işlenir.
* **📧 Akıllı E-Posta Yönetimi:**
    * Gelen kutusunu analiz eder ve özetler.
    * Gelen maile bağlama uygun cevap taslakları hazırlar.
    * Doğal dil komutlarıyla mail gönderir.
* **📅 Takvim Otomasyonu:** "Yarın Ahmet ile toplantı ayarla" gibi komutları algılar ve Google Takvim'e işler.
* **👥 Akıllı Kişi Rehberi:** Google Sheets tabanlı bir CRM gibi çalışır. İsimleri "Bulanık Arama" (Fuzzy Search) ile bulur (Örn: "Elif" yazınca "Elif Nur Demirezen"i bulur).
* **🖥️ Modern Arayüz:** PyQt5 ile geliştirilmiş, Dark Mode destekli, asenkron çalışan (donmayan) kullanıcı arayüzü.

## 🛠️ Kullanılan Teknolojiler
* **mcp (Model Context Protocol):** AI ajanları ve araçlar arası standart.
* **PyQt5:** Python için grafik arayüz kütüphanesi.
* **Google Client Library:** Workspace API entegrasyonu.
* **Ollama:** Yerel LLM (Llama3 vb.) çalıştırıcısı.
  
## 🏗️ Mimari

Proje 3 ana katmandan oluşur:

1.  **Backend (MCP Server):** `server.py`
    * FastMCP kullanarak Google API'leri ile konuşur.
    * OAuth2.0 kimlik doğrulamasını yönetir.
2.  **AI Engine:** `ai_engine.py`
    * Soyutlama katmanı (Abstraction) içerir.
    * Ollama ile JSON formatında yapılandırılmış çıktı üretir.
3.  **Frontend (GUI):** `gui_app.py`
    * PyQt5 ve `asyncio` entegrasyonu.
    * `stdio_client` üzerinden sunucu ile IPC (Inter-Process Communication) haberleşmesi yapar.

## 🚀 Kurulum

### 1. Gereksinimler
* Python 3.10 veya üzeri
* [Ollama](https://ollama.com/) (Yüklü ve `llama3` modeli çekilmiş olmalı)
* Google Cloud Console üzerinden alınmış `credentials.json` dosyası.

### 2. Google API Ayarları
Uygulamanın çalışabilmesi için Google Cloud ayarlarının yapılması gerekmektedir:
1. [Google Cloud Console](https://console.cloud.google.com/)'da yeni bir proje oluşturun.
2. **Gmail**, **Calendar**, **Drive** ve **Sheets** API'lerini kütüphaneden bulup etkinleştirin.
3. **OAuth Consent Screen** (İzin Ekranı) yapılandırmasını tamamlayın (Test kullanıcısı olarak kendi mailinizi ekleyin).
4. "Desktop App" seçeneği ile bir **OAuth Client ID** oluşturun.
5. İndirdiğiniz JSON dosyasının adını `credentials.json` olarak değiştirin ve proje ana dizinine atın.

### 3. Kurulum ve Çalıştırma

Gerekli kütüphaneleri yükleyin:
```bash
pip install -r requirements.txt
```
Uygulamayı başlatın:
```bash
python gui_app.py
```
⚠️ Önemli Not: İlk çalıştırmada tarayıcınız otomatik olarak açılarak Google hesabınızla giriş yapmanız ve izinleri onaylamanız istenecektir. Bu işlemden sonra oluşacak token.json dosyası, sonraki girişlerde otomatik yetkilendirme sağlar.
