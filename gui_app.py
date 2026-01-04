"""
GUI Application Module
----------------------
Kullanıcı Arayüzü (Frontend) modülü.
PyQt5 kütüphanesi kullanılarak geliştirilmiştir.

Mimari Özellikler:
- Multithreading (QThread ile Asenkron İşlemler)
- IPC (Inter-Process Communication) ile Backend (Server) Haberleşmesi

Yazar: [Elif Nur Demirezen]
"""
import sys
import asyncio
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTextEdit, QLabel, 
                             QMessageBox, QFrame, QLineEdit)
from PyQt5.QtCore import QThread, pyqtSignal
from ai_engine import OllamaClient
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# --- UI STİL TANIMLAMALARI (CSS) ---
STYLESHEET = """
QMainWindow { background-color: #121212; }
QFrame#Card { background-color: #1e1e1e; border: 1px solid #333; border-radius: 10px; }
QLabel { color: #e0e0e0; font-family: 'Segoe UI'; font-size: 14px; }
QLabel#Header { color: #4deeea; font-weight: bold; font-size: 16px; }
QLabel#Info { color: #aaa; font-size: 12px; }
QPushButton { background-color: #333; color: white; border: none; padding: 10px; border-radius: 5px; font-weight: bold; }
QPushButton:hover { background-color: #444; }
QPushButton#ActionBtn { background-color: #4deeea; color: #121212; }
QPushButton#ActionBtn:hover { background-color: #26c6da; }
QPushButton#UrgentBtn { background-color: #cf6679; color: #121212; }
QPushButton#CommandBtn { background-color: #7c4dff; color: white; }
QTextEdit, QLineEdit { background-color: #2d2d2d; color: #fff; border: 1px solid #444; border-radius: 5px; font-family: 'Consolas'; padding: 5px; }
"""

class Worker(QThread):
    """
    Arka Plan İşçisi (Worker Thread).
    
    GUI'nin donmasını (Freezing) engellemek için, ağ istekleri ve AI işlemleri
    bu sınıf içinde, ana akıştan (Main Thread) bağımsız bir iş parçacığında çalıştırılır.
    """
    finished = pyqtSignal(dict) # İşlem tamamlandığında GUI'ye veri taşıyan sinyal
    
    def __init__(self, task: str, payload: dict = None):
        super().__init__()
        self.task = task
        self.payload = payload or {}
        self.ai = OllamaClient()

    async def _run_async(self):
        """
        MCP İstemci Protokolü.
        server.py dosyasını bir alt süreç (Subprocess) olarak başlatır ve 
        Stdio (Standart Giriş/Çıkış) üzerinden haberleşir.
        """
        server_params = StdioServerParameters(command=sys.executable, args=["server.py"], env=None)
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Görev Yönlendiricisi (Task Router)
                if self.task == "analyze_last_mail":
                    res = await session.call_tool("get_latest_email", arguments={})
                    raw_mail = res.content[0].text
                    
                    # Regex ile gönderen mailini ayıkla
                    sender_match = re.search(r"SenderEmail: ([\w\.-]+@[\w\.-]+)", raw_mail)
                    sender_email = sender_match.group(1) if sender_match else None
                    
                    # AI Motorunu tetikle
                    ai_res = self.ai.generate_summary_and_reply(raw_mail)
                    return {"status": "success", "raw_mail": raw_mail, "sender": sender_email, **ai_res}

                elif self.task == "process_command":
                    cmd = self.payload.get("command")
                    ai_res = self.ai.decide_action(cmd)
                    found_email = None
                    
                    # İsim tespit edildiyse sunucudan mail adresini iste
                    if ai_res.get("target_name"):
                        email_res = await session.call_tool("find_email_by_name", arguments={"name": ai_res.get("target_name")})
                        if "@" in email_res.content[0].text:
                            found_email = email_res.content[0].text
                    return {"status": "command_processed", "found_email": found_email, **ai_res}

                elif self.task == "send_reply":
                    await session.call_tool("send_email_action", arguments=self.payload)
                    return {"status": "sent"}

                elif self.task == "add_calendar":
                    res = await session.call_tool("schedule_meeting", arguments=self.payload)
                    return {"status": "calendar_added", "msg": res.content[0].text}

    def run(self):
        """Thread başladığında (start) devreye giren giriş noktası."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            res = loop.run_until_complete(self._run_async())
            self.finished.emit(res)
        except Exception as e:
            self.finished.emit({"status": "error", "msg": str(e)})
        finally:
            loop.close()

class AI_Mail_Assistant(QMainWindow):
    """
    Ana Pencere Sınıfı.
    
    Kullanıcı arayüzünü oluşturur, düzenler ve kullanıcı etkileşimlerini (Events)
    ilgili Worker thread'lerine yönlendirir.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SPECTER")
        self.setGeometry(100, 100, 1100, 800)
        self.setStyleSheet(STYLESHEET)
        
        # Application State (Uygulama Durumu)
        self.current_sender = None
        self.detected_date = None
        self.meeting_title = "Toplantı"
        
        self.init_ui()

    def init_ui(self):
        """Arayüz bileşenlerini (Widgets) ve yerleşimi (Layout) başlatır."""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        panels_layout = QHBoxLayout()
        panels_layout.addLayout(self._create_left_panel(), 40)
        panels_layout.addLayout(self._create_right_panel(), 60)
        
        main_layout.addLayout(panels_layout)
        main_layout.addWidget(self._create_command_bar())

    # --- UI FACTORY METHODS (Modüler UI Oluşturucular) ---
    # Kod tekrarını önlemek ve okunabilirliği artırmak için UI parçalara bölünmüştür.

    def _create_left_panel(self) -> QVBoxLayout:
        """Sol panel: Kontrol butonları ve özet alanı."""
        layout = QVBoxLayout()
        
        # Kontrol Kartı
        card_action = QFrame(objectName="Card")
        lay_act = QVBoxLayout(card_action)
        lay_act.addWidget(QLabel("KONTROL PANELİ", objectName="Header"))
        
        self.btn_analyze = QPushButton("📧 Son Gelen Maili Analiz Et", objectName="ActionBtn")
        self.btn_analyze.clicked.connect(self.start_analysis)
        lay_act.addWidget(self.btn_analyze)
        
        self.status_lbl = QLabel("Sistem hazır.", objectName="Info")
        lay_act.addWidget(self.status_lbl)
        layout.addWidget(card_action)

        # Özet Kartı
        card_sum = QFrame(objectName="Card")
        lay_sum = QVBoxLayout(card_sum)
        lay_sum.addWidget(QLabel("AI ÖZETİ", objectName="Header"))
        self.txt_summary = QTextEdit(readOnly=True, placeholderText="Mail Özeti...")
        lay_sum.addWidget(self.txt_summary)
        layout.addWidget(card_sum, stretch=1)
        
        return layout

    def _create_right_panel(self) -> QVBoxLayout:
        """Sağ panel: Taslak düzenleme ve takvim onayı."""
        layout = QVBoxLayout()
        
        # Taslak Kartı
        card_draft = QFrame(objectName="Card")
        lay_draft = QVBoxLayout(card_draft)
        
        h_head = QHBoxLayout()
        h_head.addWidget(QLabel("MAİL TASLAĞI", objectName="Header"))
        h_head.addStretch()
        self.lbl_to = QLabel("Kime: -", styleSheet="color: #4deeea; font-weight: bold;")
        h_head.addWidget(self.lbl_to)
        lay_draft.addLayout(h_head)
        
        self.txt_draft = QTextEdit(placeholderText="Taslak metin...")
        lay_draft.addWidget(self.txt_draft)
        
        self.btn_send = QPushButton("🚀 Gönder", objectName="ActionBtn", enabled=False)
        self.btn_send.clicked.connect(self.send_mail)
        lay_draft.addWidget(self.btn_send)
        layout.addWidget(card_draft, stretch=2)

        # Takvim Kartı (Başlangıçta Gizli)
        self.card_calendar = QFrame(objectName="Card", visible=False)
        self.card_calendar.setStyleSheet("QFrame#Card { border: 1px solid #cf6679; }")
        lay_cal = QVBoxLayout(self.card_calendar)
        lay_cal.addWidget(QLabel("📅 TAKVİM ÖNERİSİ", objectName="Header"))
        self.lbl_cal_info = QLabel()
        lay_cal.addWidget(self.lbl_cal_info)
        
        btn_add = QPushButton("Takvime Ekle", objectName="UrgentBtn")
        btn_add.clicked.connect(self.add_to_calendar)
        lay_cal.addWidget(btn_add)
        layout.addWidget(self.card_calendar)
        
        return layout

    def _create_command_bar(self) -> QFrame:
        """Alt panel: Hızlı komut giriş satırı."""
        frame = QFrame(objectName="Card")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        
        layout.addWidget(QLabel("⚡ HIZLI KOMUT:", styleSheet="color: #7c4dff; font-weight: bold;"))
        self.input_cmd = QLineEdit(placeholderText='Örn: "Elif\'e yarın için toplantı maili hazırla"')
        self.input_cmd.returnPressed.connect(self.run_custom_command)
        layout.addWidget(self.input_cmd)
        
        btn_run = QPushButton("ÇALIŞTIR", objectName="CommandBtn")
        btn_run.clicked.connect(self.run_custom_command)
        layout.addWidget(btn_run)
        return frame

    # --- İŞ MANTIĞI (Business Logic) ---

    def start_analysis(self):
        """Mail analiz sürecini başlatır."""
        self._set_processing_state(True, "⏳ Son mail analiz ediliyor...")
        self.worker = Worker("analyze_last_mail")
        self.worker.finished.connect(self.on_analysis_done)
        self.worker.start()

    def run_custom_command(self):
        """Doğal dil komutunu işler."""
        cmd = self.input_cmd.text()
        if not cmd: return
        self.status_lbl.setText(f"⚙️ İşleniyor: {cmd}")
        self.input_cmd.clear()
        self.card_calendar.setVisible(False)
        self.worker = Worker("process_command", {"command": cmd})
        self.worker.finished.connect(self.on_command_done)
        self.worker.start()

    def _set_processing_state(self, processing: bool, msg: str):
        """UI durumunu (Meşgul/Hazır) günceller."""
        self.btn_analyze.setEnabled(not processing)
        self.btn_send.setEnabled(False)
        self.status_lbl.setText(msg)
        if processing:
            self.txt_summary.clear()
            self.txt_draft.clear()
            self.card_calendar.setVisible(False)

    def on_analysis_done(self, res):
        """Analiz tamamlandığında sonuçları UI'ya basar."""
        self.btn_analyze.setEnabled(True)
        if res.get("status") == "error":
            QMessageBox.critical(self, "Hata", res.get("msg"))
            self.status_lbl.setText("❌ Hata.")
            return

        self.status_lbl.setText("✅ Analiz tamamlandı.")
        self.txt_summary.setText(res.get("summary"))
        self.update_draft_area(res.get("draft_reply"), res.get("sender"), res.get("detected_date"), res.get("meeting_title"))

    def on_command_done(self, res):
        """Komut işleme tamamlandığında sonuçları UI'ya basar."""
        if res.get("status") == "error": return
        
        email = res.get("found_email")
        self.status_lbl.setText(f"✅ Kişi: {res.get('target_name')} ({email})" if email else "⚠️ Kişi bulunamadı")
        self.current_sender = email
        self.update_draft_area(res.get("draft_text"), email, res.get("extracted_date"), res.get("meeting_title"))

    def update_draft_area(self, text, to_email, date, title):
        """Taslak ve Takvim widget'larını günceller."""
        self.txt_draft.setText(text)
        self.lbl_to.setText(f"Kime: {to_email}" if to_email else "Kime: (Rehberde Bulunamadı)")
        self.btn_send.setEnabled(bool(to_email))
        
        if date:
            self.detected_date = date
            self.meeting_title = title
            self.card_calendar.setVisible(True)
            self.lbl_cal_info.setText(f"Başlık: {title}\nTarih: {date}")

    def send_mail(self):
        """Mail gönderimini tetikler."""
        self.worker = Worker("send_reply", {
            "to_email": self.current_sender,
            "subject": f"Konu: {self.meeting_title}",
            "content": self.txt_draft.toPlainText()
        })
        self.worker.finished.connect(lambda: QMessageBox.information(self, "Bilgi", "Mail Gönderildi!"))
        self.worker.start()

    def add_to_calendar(self):
        """Takvim kaydını tetikler."""
        self.worker = Worker("add_calendar", {
            "summary": self.meeting_title,
            "iso_datetime": self.detected_date
        })
        self.worker.finished.connect(lambda x: QMessageBox.information(self, "Takvim", x.get("msg")))
        self.worker.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AI_Mail_Assistant()
    window.show()
    sys.exit(app.exec_())