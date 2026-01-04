"""
AI Engine Module
----------------
Bu modül, uygulamanın yapay zeka ile iletişim kuran katmanıdır.
Soyutlama (Abstraction) prensibi kullanılarak tasarlanmıştır.

Yazar: [Elif Nur Demirezen]
"""

import json
import ollama
import locale
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

# --- LOCALE AYARLARI ---
# Hedef: Tarih ve gün isimlerinin Türkçe (yerel formatta) alınmasını garanti altına almak.
try:
    locale.setlocale(locale.LC_TIME, "tr_TR.UTF-8")  # Linux/MacOS ortamları için
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, "Turkish_Turkey.1254")  # Windows ortamları için
    except locale.Error:
        pass
    
class BaseAIEngine(ABC):
    """
    Soyut Temel Sınıf (Abstract Base Class - Interface).
    
    Bu sınıf, uygulamada kullanılacak herhangi bir LLM (Large Language Model)
    istemcisi için bir şablon (blueprint) görevi görür.
    
    Tasarım Deseni: Strategy Pattern
    Amaç: İleride Ollama yerine OpenAI, Claude veya başka bir model entegre 
    edilmek istendiğinde, ana kod yapısını değiştirmeden sadece bu sınıfı 
    implemente eden yeni bir sınıf yazılmasını sağlamak.
    """
    
    @abstractmethod
    def generate_summary_and_reply(self, email_content: str) -> Dict[str, str]:
        """
        Gelen e-posta içeriğini analiz eder, özet çıkarır ve taslak cevap hazırlar.
        
        Args:
            email_content (str): Analiz edilecek ham e-posta metni.
            
        Returns:
            Dict[str, str]: Özet, taslak cevap ve tespit edilen tarih bilgilerini içeren sözlük.
        """
        pass

    @abstractmethod
    def decide_action(self, user_query: str) -> Dict[str, Any]:
        """
        Kullanıcının doğal dildeki komutunu yapılandırılmış bir aksiyona dönüştürür.
        
        Args:
            user_query (str): Kullanıcıdan gelen emir (örn: "Yarına toplantı koy").
            
        Returns:
            Dict[str, Any]: Hedef kişi, tarih ve mail taslağını içeren yapılandırılmış veri.
        """
        pass

    def _get_time_context(self) -> str:
        """
        LLM (Large Language Model) için zamansal bağlam (Temporal Context) oluşturur.
        
        LLM'ler "şimdi" kavramına sahip değildir. Bu metod, modele referans alabileceği
        statik bir zaman penceresi sunar.
        
        Returns:
            str: Sistem saatine göre hesaplanmış, prompt içine gömülecek zaman metni.
        """
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        next_week = now + timedelta(days=7)
        
        return f"""
        REFERANS ZAMAN BİLGİLERİ (Buna Kesinlikle Uy):
        - BUGÜNÜN TARİHİ: {now.strftime('%Y-%m-%d')} ({now.strftime('%A')})
        - ŞU ANKİ SAAT: {now.strftime('%H:%M')}
        - YARININ TARİHİ: {tomorrow.strftime('%Y-%m-%d')} ({tomorrow.strftime('%A')})
        - HAFTAYA BUGÜN: {next_week.strftime('%Y-%m-%d')}
        - BULUNDUĞUMUZ YIL: {now.year}
        """

    def _clean_and_parse_json(self, text: str) -> Optional[Dict]:
        """
        LLM çıktısını temizler ve güvenli bir şekilde JSON formatına ayrıştırır.
        
        Model bazen çıktıyı Markdown blokları (```json ... ```) içine hapseder.
        Bu metod, ham string verisini temizleyip Python Dictionary nesnesine çevirir.
        
        Args:
            text (str): LLM'den dönen ham yanıt.
            
        Returns:
            Optional[Dict]: Başarılı ise sözlük, hata durumunda None.
        """
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            try:
                # Markdown formatındaki kod bloklarını temizle
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0]
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0]
                return json.loads(text.strip())
            except Exception as e:
                print(f"❌ JSON Parse Hatası: {e}")
                return None

class OllamaClient(BaseAIEngine):
    """
    Ollama API İstemcisi.
    
    BaseAIEngine arayüzünü uygulayan somut sınıftır (Concrete Class).
    Yerel makinede çalışan (Local Host) Ollama modelleri ile iletişim kurar.
    """
    def __init__(self, model_name: str = "llama3"):
        self.model_name = model_name

    def generate_summary_and_reply(self, email_content: str) -> Dict[str, str]:
        # Context Injection: Modelin zaman algısını oluştur
        time_context = self._get_time_context()
        
        # System Prompt Engineering: Modelin rolünü ve kısıtlamalarını belirle
        prompt = f"""
        Sen profesyonel bir kurumsal iletişim asistanısın.
        {time_context}
        ANALİZ EDİLECEK MAIL:
        {email_content}
        GÖREVLER:
        1. DİL: Gelen mail Türkçe ise TÜRKÇE, İngilizce ise İNGİLİZCE cevap yaz.
        2. TARİH TESPİTİ: Zaman ifadelerini ISO formatına (YYYY-MM-DDTHH:MM:SS) çevir.
        SADECE JSON FORMATINDA CEVAP VER:
        {{
            "summary": "Mailin tek cümlelik özeti",
            "draft_reply": "Cevap metni...",
            "detected_date": "YYYY-MM-DDTHH:MM:SS" (Tarih yoksa null),
            "meeting_title": "Toplantı: [Konu/Kişi]"
        }}
        """
        try:
            response = ollama.chat(model=self.model_name, messages=[{'role': 'user', 'content': prompt}], format='json')
            result = self._clean_and_parse_json(response['message']['content'])
            if result: return result
            raise ValueError("Boş Yanıt")
        except Exception as e:
            return {"summary": "Hata", "draft_reply": f"Hata: {e}", "detected_date": None, "meeting_title": "Hata"}

    def decide_action(self, user_query: str) -> Dict[str, Any]:
        time_context = self._get_time_context()
        # DEĞİŞİKLİK BURADA BAŞLIYOR
        prompt = f"""
        Sen üst düzey bir yönetici asistanısın.
        {time_context}
        KULLANICI EMRİ: "{user_query}"
        
        GÖREVLERİN:
        1. target_name: Kişi ismini bul.
        2. draft_text: Mail taslağını yaz.
        3. extracted_date: Kullanıcı "yarın", "haftaya", "salı günü" gibi bir zaman belirttiyse, 
           bunu MUTLAKA yukarıdaki referans zamana bakarak "YYYY-MM-DDTHH:MM:SS" formatına çevir.
           Eğer tarih yoksa null ver.
           
        DİKKAT: "draft_text" içinde tarih geçiyorsa, "extracted_date" asla null olamaz!
        
        SADECE JSON FORMATINDA CEVAP VER:
        {{
            "target_name": "İsim",
            "draft_text": "Mail metni...",
            "extracted_date": "2026-01-05T09:00:00", 
            "meeting_title": "Toplantı: [İsim]"
        }}
        """
        try:
            response = ollama.chat(model=self.model_name, messages=[{'role': 'user', 'content': prompt}], format='json')
            result = self._clean_and_parse_json(response['message']['content'])
            if not result:
                return {"target_name": None, "draft_text": "AI yanıtı anlaşılamadı.", "extracted_date": None, "meeting_title": "Hata"}
            return result
        except Exception as e:
            return {"target_name": None, "draft_text": "Sistem hatası.", "extracted_date": None, "meeting_title": "Hata"}