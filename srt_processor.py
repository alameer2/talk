import pysrt
import re
from typing import List, Dict, Any, Optional
import logging

class SRTProcessor:
    """معالج ملفات SRT لاستخراج التوقيت والنص"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse_srt_content(self, content: str) -> List[Dict[str, Any]]:
        """
        تحليل محتوى ملف SRT واستخراج التوقيت والنص
        
        Args:
            content (str): محتوى ملف SRT
            
        Returns:
            List[Dict]: قائمة بالترجمات مع التوقيت والنص
        """
        try:
            # تحليل المحتوى باستخدام pysrt
            subtitles = pysrt.from_string(content)
            
            parsed_subtitles = []
            
            for subtitle in subtitles:
                # تحويل التوقيت إلى ثوان
                start_time = self._time_to_seconds(subtitle.start)
                end_time = self._time_to_seconds(subtitle.end)
                
                # تنظيف النص
                clean_text = self._clean_subtitle_text(subtitle.text)
                
                if clean_text.strip():  # تجاهل النصوص الفارغة
                    parsed_subtitles.append({
                        'index': subtitle.index,
                        'start_time': start_time,
                        'end_time': end_time,
                        'duration': end_time - start_time,
                        'text': clean_text,
                        'original_text': subtitle.text
                    })
            
            return parsed_subtitles
            
        except Exception as e:
            self.logger.error(f"خطأ في تحليل ملف SRT: {str(e)}")
            return []
    
    def parse_srt_file(self, file_path: str, encoding: str = 'utf-8') -> List[Dict[str, Any]]:
        """
        قراءة وتحليل ملف SRT من المسار
        
        Args:
            file_path (str): مسار ملف SRT
            encoding (str): ترميز الملف
            
        Returns:
            List[Dict]: قائمة بالترجمات
        """
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                content = file.read()
            return self.parse_srt_content(content)
            
        except UnicodeDecodeError:
            # محاولة مع ترميزات مختلفة
            encodings = ['utf-8-sig', 'cp1256', 'iso-8859-1', 'latin1']
            for enc in encodings:
                try:
                    with open(file_path, 'r', encoding=enc) as file:
                        content = file.read()
                    return self.parse_srt_content(content)
                except UnicodeDecodeError:
                    continue
            
            self.logger.error(f"فشل في قراءة الملف بجميع الترميزات المتاحة")
            return []
            
        except Exception as e:
            self.logger.error(f"خطأ في قراءة ملف SRT: {str(e)}")
            return []
    
    def _time_to_seconds(self, time_obj) -> float:
        """تحويل كائن التوقيت إلى ثوان"""
        try:
            return (time_obj.hours * 3600 + 
                   time_obj.minutes * 60 + 
                   time_obj.seconds + 
                   time_obj.milliseconds / 1000.0)
        except:
            return 0.0
    
    def _clean_subtitle_text(self, text: str) -> str:
        """تنظيف نص الترجمة من العلامات والتنسيقات غير المرغوبة"""
        if not text:
            return ""
        
        # إزالة علامات HTML
        text = re.sub(r'<[^>]+>', '', text)
        
        # إزالة علامات التنسيق الخاصة بـ SRT
        text = re.sub(r'\{[^}]+\}', '', text)
        
        # تنظيف الأسطر المتعددة
        text = re.sub(r'\n+', ' ', text)
        
        # تنظيف المسافات الزائدة
        text = re.sub(r'\s+', ' ', text)
        
        # إزالة المسافات في البداية والنهاية
        text = text.strip()
        
        return text
    
    def get_subtitle_stats(self, subtitles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """حساب إحصائيات الترجمات"""
        if not subtitles:
            return {
                'total_subtitles': 0,
                'total_duration': 0,
                'total_characters': 0,
                'total_words': 0,
                'average_duration': 0,
                'longest_subtitle': None,
                'shortest_subtitle': None
            }
        
        total_chars = sum(len(sub['text']) for sub in subtitles)
        total_words = sum(len(sub['text'].split()) for sub in subtitles)
        total_duration = max(sub['end_time'] for sub in subtitles) if subtitles else 0
        
        durations = [sub['duration'] for sub in subtitles]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # أطول وأقصر ترجمة
        longest = max(subtitles, key=lambda x: len(x['text'])) if subtitles else None
        shortest = min(subtitles, key=lambda x: len(x['text'])) if subtitles else None
        
        return {
            'total_subtitles': len(subtitles),
            'total_duration': total_duration,
            'total_characters': total_chars,
            'total_words': total_words,
            'average_duration': avg_duration,
            'longest_subtitle': longest,
            'shortest_subtitle': shortest
        }
    
    def filter_subtitles_by_time(self, subtitles: List[Dict[str, Any]], 
                                start_time: float = 0, 
                                end_time: Optional[float] = None) -> List[Dict[str, Any]]:
        """تصفية الترجمات حسب نطاق زمني محدد"""
        if end_time is None:
            end_time = float('inf')
        
        filtered = []
        for sub in subtitles:
            if start_time <= sub['start_time'] <= end_time or start_time <= sub['end_time'] <= end_time:
                filtered.append(sub)
        
        return filtered
    
    def merge_short_subtitles(self, subtitles: List[Dict[str, Any]], 
                             min_duration: float = 1.0) -> List[Dict[str, Any]]:
        """دمج الترجمات القصيرة مع الترجمات التالية"""
        if not subtitles:
            return []
        
        merged = []
        i = 0
        
        while i < len(subtitles):
            current = subtitles[i].copy()
            
            # إذا كانت الترجمة قصيرة جداً، ادمجها مع التالية
            while (i + 1 < len(subtitles) and 
                   current['duration'] < min_duration and
                   subtitles[i + 1]['start_time'] - current['end_time'] < 0.5):
                
                next_sub = subtitles[i + 1]
                current['text'] += " " + next_sub['text']
                current['end_time'] = next_sub['end_time']
                current['duration'] = current['end_time'] - current['start_time']
                i += 1
            
            merged.append(current)
            i += 1
        
        return merged
