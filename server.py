"""
MCP Server & Google Integration Module
--------------------------------------
Bu modül, Model Context Protocol (MCP) kullanarak bir arka uç sunucusu (Backend Server) olarak çalışır.
Google Workspace API'leri (Gmail, Calendar, Drive, Sheets) ile etkileşimi yönetir.

Özellikler:
- OAuth2.0 Kimlik Doğrulama
- Servis Yöneticisi (Manager) Tasarım Deseni
- FastMCP Sunucu Entegrasyonu

Yazar: [Elif Nur Demirezen]
"""

import os.path
import base64
import difflib
import sys
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from mcp.server.fastmcp import FastMCP

# --- KONFİGÜRASYON ---
CONTACTS_FILE_NAME = "Specter_Contact_List"
# Google API Scopes (Erişim Kapsamları):
# Uygulamanın kullanıcının hesabında nelere erişebileceğini tanımlar.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify', 
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/spreadsheets', 
    'https://www.googleapis.com/auth/drive'         
]

# --- YARDIMCI FONKSİYONLAR ---
def log(msg: str) -> None:
    """
    MCP Protokolü Uyumluluğu için Güvenli Loglama.
    
    Standart çıktı (stdout), MCP istemci-sunucu iletişimi için rezerve edilmiştir.
    Bu nedenle loglar, iletişim akışını bozmamak için 'stderr' kanalına yazılır.
    """
    sys.stderr.write(f"{msg}\n")
    sys.stderr.flush()

# --- KİMLİK DOĞRULAMA SERVİSİ ---
class GoogleAuthManager:
    """
    Google OAuth2.0 Kimlik Doğrulama Yöneticisi.
    
    Bu sınıf, 'token.json' ve 'credentials.json' dosyalarını kullanarak
    kullanıcı yetkilendirmesini (Authorization) yönetir. Token süresi dolduğunda
    otomatik yenileme (Refresh Token) mekanizmasını işletir.
    """
    def __init__(self):
        self.creds = None
        self._authenticate()

    def _authenticate(self) -> None:
        """Yetkilendirme akışını başlatır veya mevcut token'ı yükler."""
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists('credentials.json'):
                    raise FileNotFoundError("Kritik Hata: 'credentials.json' bulunamadı.")
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            # Yeni token'ı diske kaydet
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())

    def get_service(self, service_name: str, version: str) -> Resource:
        """Yetkilendirilmiş API servis istemcisi (Resource) döndürür."""
        return build(service_name, version, credentials=self.creds)

# --- ALAN SERVİSLERİ (DOMAIN MANAGERS) ---
# Kapsülleme (Encapsulation) Prensibi:
# Her sınıf, sadece tek bir sorumluluğu (Single Responsibility) üstlenir.

class ContactManager:
    """
    Kişi Yönetim Servisi.
    
    Google Sheets ve Drive API'lerini kullanarak basit bir CRM işlevi görür.
    Rehber oluşturma, okuma ve "Bulanık Arama" (Fuzzy Search) işlemlerini yapar.
    """
    def __init__(self, drive_service: Resource, sheets_service: Resource):
        self.drive = drive_service
        self.sheets = sheets_service
        self._cached_sheet_id: Optional[str] = None # API çağrılarını azaltmak için önbellek

    def _get_sheet_id(self) -> Optional[str]:
        """Rehber dosyasını Drive'da arar, bulamazsa Lazy Initialization ile oluşturur."""
        if self._cached_sheet_id:
            return self._cached_sheet_id

        # 1. Drive API ile dosyayı ara
        try:
            results = self.drive.files().list(
                q=f"name = '{CONTACTS_FILE_NAME}' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false",
                pageSize=1, fields="files(id, name)").execute()
            files = results.get('files', [])
            
            if files:
                log(f"✅ Rehber bulundu: {files[0]['name']}")
                self._cached_sheet_id = files[0]['id']
                return self._cached_sheet_id
        except Exception as e:
            log(f"⚠️ Arama hatası: {e}")

        # 2. Dosya yoksa oluştur (Fallback)
        return self._create_sheet()

    def _create_sheet(self) -> Optional[str]:
        """Yeni bir Google Sheet oluşturur ve varsayılan başlıkları (Header) ekler."""
        log("ℹ️ Rehber oluşturuluyor...")
        try:
            file_metadata = {'name': CONTACTS_FILE_NAME, 'mimeType': 'application/vnd.google-apps.spreadsheet'}
            spreadsheet = self.drive.files().create(body=file_metadata, fields='id').execute()
            new_id = spreadsheet.get('id')
            
            values = [['İsim Soyisim', 'E-Posta Adresi']]
            self.sheets.spreadsheets().values().update(
                spreadsheetId=new_id, range='A1:B1',
                valueInputOption='RAW', body={'values': values}).execute()
            
            self._cached_sheet_id = new_id
            return new_id
        except Exception as e:
            log(f"❌ Oluşturma hatası: {e}")
            return None

    def find_email(self, name: str) -> str:
        """
        Verilen isme göre e-posta adresini bulur.
        
        Algoritma: Difflib kullanarak 'String Similarity' (Benzerlik) analizi yapar.
        Bu sayede kullanıcı 'Engin' yazdığında 'Engin Vardar' kaydını bulabilir.
        """
        sheet_id = self._get_sheet_id()
        if not sheet_id: return "HATA: Rehber erişilemedi."

        try:
            result = self.sheets.spreadsheets().values().get(spreadsheetId=sheet_id, range='A:B').execute()
            rows = result.get('values', [])
            if len(rows) < 2: return "Rehber boş."

            target = name.lower().strip()
            best_match = None
            highest_score = 0.0

            for row in rows[1:]:
                if len(row) < 2: continue
                contact_name, contact_email = row[0].lower().strip(), row[1].strip()
                
                # Tam eşleşme (Exact Match)
                if target in contact_name: return contact_email
                
                # Bulanık eşleşme (Fuzzy Match)
                score = difflib.SequenceMatcher(None, target, contact_name).ratio()
                if score > 0.6 and score > highest_score:
                    highest_score = score
                    best_match = contact_email
            
            return best_match if best_match else "BULUNAMADI"
        except Exception as e:
            return f"HATA: {e}"

class EmailManager:
    """
    E-Posta Servisi.
    Gmail API üzerindeki okuma (Fetch) ve gönderme (Send) işlemlerini kapsüller.
    """
    def __init__(self, service: Resource):
        self.service = service

    def get_latest(self) -> str:
        """Gelen kutusundaki (Inbox) en son maili getirir ve parse eder."""
        try:
            res = self.service.users().messages().list(userId='me', maxResults=1, labelIds=['INBOX']).execute()
            msgs = res.get('messages', [])
            if not msgs: return "Gelen kutusu boş."
            
            msg = self.service.users().messages().get(userId='me', id=msgs[0]['id'], format='full').execute()
            headers = msg['payload']['headers']
            
            subj = next((h['value'] for h in headers if h['name'] == 'Subject'), '(Yok)')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '(Bilinmiyor)')
            sender_email = sender.split("<")[1].split(">")[0] if "<" in sender else sender
            
            return f"From: {sender}\nSenderEmail: {sender_email}\nSubject: {subj}\nContent: {msg.get('snippet','')}"
        except Exception as e:
            return f"Hata: {e}"

    def send(self, to: str, subject: str, content: str) -> str:
        """MIMEText formatında mail oluşturur ve base64 kodlaması ile API'ye iletir."""
        try:
            if "<" in to: to = to.split("<")[1].replace(">", "")
            msg = MIMEText(content)
            msg['to'] = to
            msg['subject'] = subject
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            self.service.users().messages().send(userId='me', body={'raw': raw}).execute()
            return "Mail Gönderildi!"
        except Exception as e:
            return f"Hata: {e}"

class CalendarManager:
    """
    Takvim Yönetim Servisi.
    Google Calendar API üzerinden etkinlik (Event) oluşturma işlemlerini yönetir.
    """
    def __init__(self, service: Resource):
        self.service = service

    def schedule(self, summary: str, iso_datetime: str) -> str:
        """Verilen ISO tarih formatına göre 1 saatlik standart toplantı oluşturur."""
        try:
            if not iso_datetime: return "Tarih hatası"
            clean_date = iso_datetime.replace("Z", "")
            start_dt = datetime.fromisoformat(clean_date)
            end_dt = start_dt + timedelta(hours=1)
            
            event = {
                'summary': summary,
                'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Europe/Istanbul'},
                'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Europe/Istanbul'},
            }
            self.service.events().insert(calendarId='primary', body=event).execute()
            return f"Takvime Eklendi: {start_dt.strftime('%H:%M')}"
        except Exception as e:
            return f"Takvim Hatası: {e}"

# --- INITIALIZATION (BAĞIMLILIK ENJEKSİYONU) ---
# Global servisleri başlat ve Dependency Injection ile yöneticilere dağıt.
auth = GoogleAuthManager()
contacts_mgr = ContactManager(auth.get_service('drive', 'v3'), auth.get_service('sheets', 'v4'))
email_mgr = EmailManager(auth.get_service('gmail', 'v1'))
calendar_mgr = CalendarManager(auth.get_service('calendar', 'v3'))

mcp = FastMCP("TeacherAssistantServer")

# --- MCP ARAÇLARI (TOOLS) ---
# Bu fonksiyonlar, dış dünyadan (Client) gelen istekleri karşılayan uç noktalardır (Endpoints).
# Logic katmanı burada değil, yukarıdaki Manager sınıflarındadır.

@mcp.tool()
def find_email_by_name(name: str) -> str:
    """Kişi isminden e-posta adresini bulur."""
    return contacts_mgr.find_email(name)

@mcp.tool()
def get_latest_email() -> str:
    """Son gelen e-postayı getirir."""
    return email_mgr.get_latest()

@mcp.tool()
def send_email_action(to_email: str, subject: str, content: str) -> str:
    """Belirtilen alıcıya e-posta gönderir."""
    return email_mgr.send(to_email, subject, content)

@mcp.tool()
def schedule_meeting(summary: str, iso_datetime: str) -> str:
    """Takvime yeni bir toplantı ekler."""
    return calendar_mgr.schedule(summary, iso_datetime)

if __name__ == "__main__":
    log("🚀 Sunucu başlatılıyor...")
    # Cache Warming: İlk çalıştırmada rehber kontrolü yap
    contacts_mgr._get_sheet_id()
    mcp.run()