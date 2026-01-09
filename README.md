# 👻 SPECTER: MCP Tabanlı Yapay Zeka Otomasyonu

![Python Version](https://img.shields.io/badge/python-3.11-blue)
![Status](https://img.shields.io/badge/status-active-success)

## 📖 Proje Hakkında

**Specter**, Model Context Protocol (MCP) mimarisini kullanarak yerel LLM'leri (Ollama) Google Workspace araçlarıyla (Gmail, Calendar, Drive, Sheets) entegre eden, Python tabanlı bir yapay zeka otomasyonudur.


<img width="1098" height="828" alt="specter_ss" src="https://github.com/user-attachments/assets/a7e51e40-2393-4d71-9ac2-0543328eafa5" />

---
## 🎯 Projenin Amacı
Bu proje, eğitimcilerin üzerindeki yoğun idari iş yükünü (e-posta trafiği, takvim planlaması, rehber yönetimi) hafifletmek ve verimliliği artırmak amacıyla geliştirilmiştir.
---

## 🌟 Özellikler

* **🤖 Yerel Yapay Zeka:** Verileriniz buluta gitmez. Ollama üzerinden **Llama3** ile yerel çalışır.
* **📧 Akıllı Mail Analizi:** Gelen kutusunu tarar, mailleri özetler ve içeriğe en uygun yanıt taslağını saniyeler içinde hazırlar.
* **📅 Doğal Dil ile komut:** *"Yarın saat 9 için Elif'e mail hazırla"* dediğinizde sizin için bir mail taslağı hazırlar.
* **👥 Entegre CRM:** Google Sheets tabanlı kişi rehberi oluşturur. İsimleri "Bulanık Arama" (Fuzzy Search) ile bulur (Örn: "Elif" -> "Elif Nur Demirezen").
* **⚡ Asenkron Arayüz:** PyQt5 ve `asyncio` mimarisi sayesinde işlemler sırasında arayüz donmaz.

---

## 🛠️ Mimari ve Teknolojiler

Proje **Manager Design Pattern** kullanılarak 3 ana katmanda geliştirilmiştir:

1.  **Backend (MCP Server):** `fastmcp` kullanarak Google API'leri ile haberleşir. OAuth2.0 yönetimini sağlar.
2.  **AI Engine:** Soyutlanmış (Abstract) yapay zeka katmanı. Ollama ile JSON formatında yapılandırılmış çıktılar üretir.
3.  **Frontend (GUI):** `stdio_client` üzerinden sunucu ile IPC (Inter-Process Communication) haberleşmesi yapan PyQt5 arayüzü.

---

## 📂 Proje Yapısı

Dosyaların doğru çalışması için dizin yapısı aşağıdaki gibi olmalıdır:

```text
specter-mcp-agent/
├── ai_engine.py       # Yapay zeka mantık katmanı
├── gui_app.py         # PyQt5 Arayüz uygulaması (Başlatıcı)
├── server.py          # MCP Sunucusu ve Google servisleri
├── requirements.txt   # Kütüphane gereksinimleri
├── credentials.json   # Google Cloud'dan indirilecek (Siz ekleyeceksiniz)
└── token.json         # İlk girişten sonra otomatik oluşur (Silmeyin)
```
## 🚀 Kurulum

### 1. Gereksinimler
* Python 3.11.9
* [Ollama](https://ollama.com/) (Yüklü ve `llama3` modeli çekilmiş olmalı)
* Google Cloud Console üzerinden alınmış `credentials.json` dosyası.
  
### 2. Kütüphanelerin Yüklenmesi
* Terminali açın ve gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```
### 3. AI Modelinin Hazırlanması
* Specter varsayılan olarak llama3 modelini kullanır. Terminalden şu komutu çalıştırarak modeli indirin:
```bash
ollama pull llama3
```
### 4. Google API Ayarları
Uygulamanın çalışabilmesi için Google Cloud ayarlarının yapılması gerekmektedir:
1. [Google Cloud Console](https://console.cloud.google.com/)'da yeni bir proje oluşturun.
2. **Gmail**, **Calendar**, **Drive** ve **Sheets** API'lerini kütüphaneden bulup etkinleştirin.
3. **OAuth Consent Screen** (İzin Ekranı) yapılandırmasını tamamlayın (Test kullanıcısı olarak kendi mailinizi ekleyin).
4. "Desktop App" seçeneği ile bir **OAuth Client ID** oluşturun.
5. İndirdiğiniz JSON dosyasının adını `credentials.json` olarak değiştirin ve proje ana dizinine atın.

### 5. Kullanım 
Uygulamayı başlatın:
```bash
python gui_app.py
```
* İlk Çalıştırma: Tarayıcınız açılacak ve Google izni isteyecektir. Onayladıktan sonra token.json dosyası oluşur ve bir daha giriş yapmanız gerekmez.
  
###   👥 Kişi Rehberi (CRM) Nasıl Çalışır?
* İlk çalıştırmada Specter, Google Drive'ınızda Specter_Contact_List adında bir Excel (Sheets) dosyası oluşturur.
1. Drive'ınıza gidin.
2. Bu dosyayı açın.
3. `A` sütununa **İsim Soyisim**, `B` sütununa **E-Posta** adreslerini manuel olarak ekleyin.
4. Artık "Elif'e mail at" dediğinizde Specter bu listeden kişiyi bulacaktır.
   
### ⚠️ Sorun Giderme
* Hata: Connection refused (Ollama hatası)
* Çözüm: Ollama uygulamasının arka planda çalıştığından emin olun.
  
* Hata: Rehber erişilemedi
* Çözüm: credentials.json dosyasının doğru yerde olduğunu ve Sheets API'nin Google Cloud'da etkinleştirildiğini kontrol edin.
  
---
Lisans ve Telif Hakkı
Bu proje, Ankara Üniversitesi BOZ213 - Nesne Tabanlı Programlama dersi kapsamında geliştirilmiştir.

Kaynak kodlar yalnızca eğitim ve inceleme amacıyla kullanılabilir. İzinsiz ticari kullanım, kopyalama ve dağıtım yasaktır.

© 2026 Elif Nur Demirezen. Tüm hakları saklıdır.
