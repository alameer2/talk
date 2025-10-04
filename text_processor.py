import re
import unicodedata
from typing import List, Dict, Any
import logging

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_PROCESSING_AVAILABLE = True
except ImportError:
    ARABIC_PROCESSING_AVAILABLE = False

try:
    from mishkal.tashkeel import TashkeelClass
    TASHKEEL_AVAILABLE = True
except ImportError:
    TASHKEEL_AVAILABLE = False

class TextProcessor:
    """معالج النصوص العربية وعلامات الترقيم"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # تهيئة محرك التشكيل
        self.tashkeel_engine = None
        if TASHKEEL_AVAILABLE:
            try:
                self.tashkeel_engine = TashkeelClass()
                self.logger.info("تم تهيئة محرك التشكيل بنجاح")
            except Exception as e:
                self.logger.warning(f"فشل تهيئة محرك التشكيل: {str(e)}")
        
        # قاموس علامات الترقيم وتأثيرها على التوقف
        self.punctuation_pauses = {
            '.': 0.8,      # نقطة - توقف طويل
            '!': 0.6,      # تعجب - توقف متوسط
            '?': 0.6,      # استفهام - توقف متوسط  
            '؟': 0.6,      # استفهام عربي
            '،': 0.3,      # فاصلة عربية - توقف قصير
            ',': 0.3,      # فاصلة - توقف قصير
            ';': 0.4,      # فاصلة منقوطة - توقف متوسط
            ':': 0.4,      # نقطتان - توقف متوسط
            '...': 1.0,    # نقط متتابعة - توقف طويل
            '-': 0.2,      # شرطة - توقف قصير
            '–': 0.2,      # شرطة متوسطة
            '—': 0.3,      # شرطة طويلة
        }
        
        # الأرقام العربية والإنجليزية
        self.arabic_numbers = '٠١٢٣٤٥٦٧٨٩'
        self.english_numbers = '0123456789'
        
        # علامات الترقيم التي تحتاج تنظيف
        self.unwanted_chars = ['«', '»', '"', '"', ''', ''', '`', '~', '^']
    
    def add_tashkeel(self, text: str) -> str:
        """
        إضافة التشكيل التلقائي للنص العربي
        
        Args:
            text (str): النص بدون تشكيل
            
        Returns:
            str: النص مع التشكيل
        """
        if not text or not self.tashkeel_engine:
            return text
        
        try:
            # إضافة التشكيل باستخدام mishkal
            vocalized_text = self.tashkeel_engine.tashkeel(text)
            self.logger.info("تم إضافة التشكيل للنص بنجاح")
            return vocalized_text
        except Exception as e:
            self.logger.error(f"خطأ في إضافة التشكيل: {str(e)}")
            return text
    
    def process_arabic_text(self, text: str, handle_punctuation: bool = True, for_tts: bool = True, add_tashkeel: bool = False) -> str:
        """
        معالجة شاملة للنص العربي
        
        Args:
            text (str): النص الأصلي
            handle_punctuation (bool): معالجة علامات الترقيم
            for_tts (bool): إذا كان النص لـ TTS (لا يتم تطبيق RTL)
            add_tashkeel (bool): إضافة التشكيل التلقائي
            
        Returns:
            str: النص بعد المعالجة
        """
        if not text:
            return ""
        
        try:
            # إضافة التشكيل أولاً للنص الخام (قبل أي تنظيف)
            # هذا يحسن دقة التشكيل لأن mishkal يحتاج السياق الكامل
            if add_tashkeel and self.tashkeel_engine:
                text = self.add_tashkeel(text)
            
            # تنظيف أولي
            processed_text = self._clean_text(text)
            
            # معالجة الأرقام
            processed_text = self._process_numbers(processed_text)
            
            # معالجة علامات الترقيم
            if handle_punctuation:
                processed_text = self._process_punctuation(processed_text)
            
            # تطبيق تشكيل النص العربي فقط للعرض (ليس لـ TTS)
            # gTTS يتعامل مع النص العربي بشكل صحيح دون معالجة RTL
            if not for_tts and ARABIC_PROCESSING_AVAILABLE:
                processed_text = self._reshape_arabic_text(processed_text)
            
            # تنظيف نهائي
            processed_text = self._final_cleanup(processed_text)
            
            return processed_text
            
        except Exception as e:
            self.logger.error(f"خطأ في معالجة النص: {str(e)}")
            return text  # إرجاع النص الأصلي في حالة الخطأ
    
    def _clean_text(self, text: str) -> str:
        """تنظيف أولي للنص"""
        # إزالة الأحرف غير المرغوبة
        for char in self.unwanted_chars:
            text = text.replace(char, '')
        
        # إزالة المسافات الزائدة والأسطر الجديدة
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # إزالة التكرارات المتتالية لنفس علامة الترقيم
        text = re.sub(r'([.!?؟،,;:])\1+', r'\1', text)
        
        return text
    
    def _process_numbers(self, text: str) -> str:
        """تحويل الأرقام لتسهيل النطق"""
        # تحويل الأرقام الإنجليزية إلى عربية إذا كان النص عربي أساساً
        if self._is_primarily_arabic(text):
            translation_table = str.maketrans(self.english_numbers, self.arabic_numbers)
            text = text.translate(translation_table)
        
        # معالجة التواريخ والأرقام المعقدة
        text = re.sub(r'(\d+)[:/\-](\d+)[:/\-](\d+)', r'\1 \2 \3', text)
        
        return text
    
    def _process_punctuation(self, text: str) -> str:
        """معالجة علامات الترقيم لإضافة توقفات طبيعية"""
        for punct, pause_duration in self.punctuation_pauses.items():
            if punct in text:
                # إضافة مسافات حول علامات الترقيم لتسهيل التوقف
                if punct in ['.', '!', '?', '؟']:
                    text = text.replace(punct, f'{punct} ')
                elif punct in ['،', ',']:
                    text = text.replace(punct, f'{punct} ')
        
        # معالجة خاصة للنقط المتتابعة
        text = re.sub(r'\.{3,}', ' ... ', text)
        
        # إزالة المسافات الزائدة بعد المعالجة
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def _reshape_arabic_text(self, text: str) -> str:
        """تطبيق تشكيل النص العربي للعرض الصحيح"""
        try:
            # تطبيق التشكيل العربي
            reshaped_text = arabic_reshaper.reshape(text)
            
            # تطبيق اتجاه النص (من اليمين إلى اليسار)
            bidi_text = get_display(reshaped_text)
            
            return str(bidi_text)
            
        except Exception as e:
            self.logger.warning(f"تعذر تطبيق التشكيل العربي: {str(e)}")
            return text
    
    def _final_cleanup(self, text: str) -> str:
        """تنظيف نهائي للنص"""
        # إزالة المسافات الزائدة
        text = re.sub(r'\s+', ' ', text)
        
        # إزالة المسافات في البداية والنهاية
        text = text.strip()
        
        # التأكد من وجود نقطة في نهاية الجملة إذا لم تكن موجودة
        if text and not text[-1] in '.!?؟':
            text += '.'
        
        return text
    
    def _is_primarily_arabic(self, text: str) -> bool:
        """فحص ما إذا كان النص عربي بشكل أساسي"""
        if not text:
            return False
        
        arabic_chars = 0
        total_chars = 0
        
        for char in text:
            if char.isalpha():
                total_chars += 1
                # فحص ما إذا كان الحرف عربي
                if '\u0600' <= char <= '\u06FF' or '\u0750' <= char <= '\u077F':
                    arabic_chars += 1
        
        if total_chars == 0:
            return False
        
        # إذا كان أكثر من 70% من الأحرف عربية
        return (arabic_chars / total_chars) > 0.7
    
    def split_text_by_length(self, text: str, max_length: int = 200) -> List[str]:
        """تقسيم النص الطويل إلى أجزاء أقصر للمعالجة"""
        if len(text) <= max_length:
            return [text]
        
        parts = []
        sentences = re.split(r'[.!?؟]\s+', text)
        
        current_part = ""
        for sentence in sentences:
            if len(current_part + sentence) <= max_length:
                current_part += sentence + ". "
            else:
                if current_part:
                    parts.append(current_part.strip())
                current_part = sentence + ". "
        
        if current_part:
            parts.append(current_part.strip())
        
        return parts
    
    def extract_speech_segments(self, text: str) -> List[Dict[str, Any]]:
        """استخراج مقاطع الكلام مع معلومات التوقف"""
        segments = []
        
        # تقسيم النص حسب علامات الترقيم الرئيسية
        parts = re.split(r'([.!?؟])', text)
        
        current_text = ""
        for i, part in enumerate(parts):
            if part.strip():
                if part in '.!?؟':
                    # علامة ترقيم - إنهاء المقطع الحالي
                    if current_text.strip():
                        segments.append({
                            'text': current_text.strip(),
                            'pause_after': self.punctuation_pauses.get(part, 0.5),
                            'punctuation': part
                        })
                        current_text = ""
                else:
                    current_text += part
        
        # إضافة أي نص متبقي
        if current_text.strip():
            segments.append({
                'text': current_text.strip(),
                'pause_after': 0.3,
                'punctuation': ''
            })
        
        return segments
    
    def normalize_text(self, text: str) -> str:
        """تطبيع النص العربي (توحيد الأشكال المختلفة للأحرف)"""
        if not text:
            return ""
        
        # توحيد الهمزات
        text = re.sub(r'[آأإ]', 'ا', text)
        text = re.sub(r'[ؤئ]', 'ء', text)
        
        # توحيد التاء المربوطة والهاء
        text = re.sub(r'ة', 'ه', text)
        
        # توحيد الألف المقصورة
        text = re.sub(r'ى', 'ي', text)
        
        # إزالة التشكيل
        text = re.sub(r'[\u064B-\u0652]', '', text)
        
        # توحيد المسافات
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def get_text_statistics(self, text: str) -> Dict[str, int]:
        """حساب إحصائيات النص"""
        if not text:
            return {'characters': 0, 'words': 0, 'sentences': 0, 'arabic_chars': 0}
        
        # عدد الأحرف
        char_count = len(text)
        
        # عدد الكلمات
        word_count = len(text.split())
        
        # عدد الجمل (تقريبي)
        sentence_count = len(re.split(r'[.!?؟]', text))
        
        # عدد الأحرف العربية
        arabic_count = len(re.findall(r'[\u0600-\u06FF\u0750-\u077F]', text))
        
        return {
            'characters': char_count,
            'words': word_count,
            'sentences': sentence_count,
            'arabic_chars': arabic_count
        }
