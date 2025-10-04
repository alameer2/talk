import os
import tempfile
import logging
from typing import Optional
from pathlib import Path

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

class TTSEngine:
    """محرك تحويل النص إلى كلام مع دعم متعدد المحركات"""
    
    def __init__(self, engine_type: str = "gtts", speech_rate: float = 1.0):
        """
        تهيئة محرك TTS
        
        Args:
            engine_type (str): نوع المحرك ("gtts" أو "pyttsx3")
            speech_rate (float): سرعة الكلام (1.0 = عادي)
        """
        self.engine_type = engine_type.lower()
        self.speech_rate = speech_rate
        self.logger = logging.getLogger(__name__)
        
        # تهيئة محرك pyttsx3 إذا كان مطلوب
        if self.engine_type == "pyttsx3":
            self._init_pyttsx3()
    
    def _init_pyttsx3(self):
        """تهيئة محرك pyttsx3"""
        try:
            if not PYTTSX3_AVAILABLE:
                raise ImportError("pyttsx3 غير متاح")
            
            self.pyttsx3_engine = pyttsx3.init()
            
            # إعداد السرعة
            rate = self.pyttsx3_engine.getProperty('rate')
            self.pyttsx3_engine.setProperty('rate', int(rate * self.speech_rate))
            
            # محاولة العثور على صوت عربي
            voices = self.pyttsx3_engine.getProperty('voices')
            arabic_voice = None
            
            for voice in voices:
                # البحث عن أصوات عربية
                if any(lang in voice.id.lower() for lang in ['ar', 'arabic', 'عربي']):
                    arabic_voice = voice
                    break
            
            if arabic_voice:
                self.pyttsx3_engine.setProperty('voice', arabic_voice.id)
                self.logger.info(f"تم العثور على صوت عربي: {arabic_voice.name}")
            else:
                self.logger.warning("لم يتم العثور على صوت عربي، سيتم استخدام الصوت الافتراضي")
                
        except Exception as e:
            self.logger.error(f"خطأ في تهيئة pyttsx3: {str(e)}")
            self.pyttsx3_engine = None
    
    def text_to_speech(self, text: str, output_file: str = None) -> Optional[str]:
        """
        تحويل النص إلى كلام
        
        Args:
            text (str): النص المراد تحويله
            output_file (str): مسار ملف الإخراج (اختياري)
            
        Returns:
            str: مسار ملف الصوت المُنشأ أو None في حالة الفشل
        """
        if not text.strip():
            return None
        
        # إنشاء ملف مؤقت إذا لم يتم تحديد مسار
        if output_file is None:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                output_file = tmp_file.name
        
        # إنشاء مجلد الإخراج إذا لم يكن موجود
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        if self.engine_type == "gtts":
            return self._gtts_convert(text, output_file)
        elif self.engine_type == "pyttsx3":
            return self._pyttsx3_convert(text, output_file)
        else:
            # محاولة استخدام المحرك المتاح
            if GTTS_AVAILABLE:
                return self._gtts_convert(text, output_file)
            elif PYTTSX3_AVAILABLE:
                return self._pyttsx3_convert(text, output_file)
            else:
                self.logger.error("لا يوجد محرك TTS متاح")
                return None
    
    def _gtts_convert(self, text: str, output_file: str) -> Optional[str]:
        """تحويل النص باستخدام gTTS"""
        try:
            if not GTTS_AVAILABLE:
                self.logger.error("gTTS غير متاح")
                return None
            
            # إنشاء كائن gTTS
            tts = gTTS(
                text=text, 
                lang='ar', 
                slow=False if self.speech_rate >= 1.0 else True
            )
            
            # حفظ الملف
            tts.save(output_file)
            
            # التحقق من وجود الملف
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                self.logger.info(f"تم إنشاء ملف صوتي: {output_file}")
                return output_file
            else:
                self.logger.error(f"فشل في إنشاء ملف الصوت: {output_file}")
                return None
                
        except Exception as e:
            self.logger.error(f"خطأ في gTTS: {str(e)}")
            
            # محاولة احتياطية مع pyttsx3
            if PYTTSX3_AVAILABLE:
                self.logger.info("محاولة استخدام pyttsx3 كبديل")
                return self._pyttsx3_convert(text, output_file)
            
            return None
    
    def _pyttsx3_convert(self, text: str, output_file: str) -> Optional[str]:
        """تحويل النص باستخدام pyttsx3"""
        try:
            if not PYTTSX3_AVAILABLE or self.pyttsx3_engine is None:
                self.logger.error("pyttsx3 غير متاح أو لم يتم تهيئته")
                return None
            
            # حفظ الملف الصوتي
            self.pyttsx3_engine.save_to_file(text, output_file)
            self.pyttsx3_engine.runAndWait()
            
            # التحقق من وجود الملف
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                self.logger.info(f"تم إنشاء ملف صوتي بـ pyttsx3: {output_file}")
                return output_file
            else:
                self.logger.error(f"فشل في إنشاء ملف الصوت بـ pyttsx3: {output_file}")
                return None
                
        except Exception as e:
            self.logger.error(f"خطأ في pyttsx3: {str(e)}")
            return None
    
    def get_available_engines(self) -> list:
        """الحصول على قائمة بالمحركات المتاحة"""
        available = []
        
        if GTTS_AVAILABLE:
            available.append("gtts")
        
        if PYTTSX3_AVAILABLE:
            available.append("pyttsx3")
        
        return available
    
    def test_engine(self, test_text: str = "اختبار الصوت") -> bool:
        """اختبار عمل المحرك"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=True) as tmp_file:
                result = self.text_to_speech(test_text, tmp_file.name)
                return result is not None
        except:
            return False
    
    def get_engine_info(self) -> dict:
        """معلومات المحرك الحالي"""
        info = {
            'engine_type': self.engine_type,
            'speech_rate': self.speech_rate,
            'available_engines': self.get_available_engines(),
            'gtts_available': GTTS_AVAILABLE,
            'pyttsx3_available': PYTTSX3_AVAILABLE
        }
        
        if self.engine_type == "pyttsx3" and hasattr(self, 'pyttsx3_engine') and self.pyttsx3_engine:
            try:
                voices = self.pyttsx3_engine.getProperty('voices')
                info['available_voices'] = [voice.name for voice in voices]
                current_voice = self.pyttsx3_engine.getProperty('voice')
                info['current_voice'] = current_voice
            except:
                pass
        
        return info
