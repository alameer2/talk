import os
import shutil
import zipfile
from pathlib import Path
from typing import List, Optional
import logging

try:
    from pydub import AudioSegment
    from pydub.silence import split_on_silence
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

class AudioUtils:
    """أدوات معالجة وتحرير الملفات الصوتية"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        if not PYDUB_AVAILABLE:
            self.logger.warning("pydub غير متاح - بعض الميزات قد لا تعمل")
    
    def load_audio(self, audio_file: str) -> Optional[AudioSegment]:
        """تحميل ملف صوتي"""
        if not PYDUB_AVAILABLE:
            return None
        
        try:
            return AudioSegment.from_file(audio_file)
        except Exception as e:
            self.logger.error(f"خطأ في تحميل الملف الصوتي: {str(e)}")
            return None
    
    def create_silence(self, duration_ms: float) -> Optional[AudioSegment]:
        """إنشاء فترة صمت"""
        if not PYDUB_AVAILABLE:
            return None
        
        try:
            return AudioSegment.silent(duration=int(duration_ms))
        except Exception as e:
            self.logger.error(f"خطأ في إنشاء الصمت: {str(e)}")
            return None
    
    def add_pause(self, audio: AudioSegment, pause_ms: float) -> Optional[AudioSegment]:
        """إضافة توقف في نهاية المقطع الصوتي"""
        if not PYDUB_AVAILABLE or not audio:
            return audio
        
        try:
            if pause_ms > 0:
                pause = AudioSegment.silent(duration=int(pause_ms))
                return audio + pause
            return audio
        except Exception as e:
            self.logger.error(f"خطأ في إضافة التوقف: {str(e)}")
            return audio
    
    def combine_audio_segments(self, segments: List[AudioSegment]) -> Optional[AudioSegment]:
        """
        دمج عدة مقاطع صوتية في ملف واحد
        
        Args:
            segments (List[AudioSegment]): قائمة بالمقاطع الصوتية
            
        Returns:
            AudioSegment: المقطع المدمج أو None
        """
        if not PYDUB_AVAILABLE or not segments:
            return None
        
        try:
            # بدء بمقطع فارغ
            combined = AudioSegment.empty()
            
            # دمج جميع المقاطع
            for segment in segments:
                if segment:
                    combined += segment
            
            return combined
            
        except Exception as e:
            self.logger.error(f"خطأ في دمج المقاطع الصوتية: {str(e)}")
            return None
    
    def export_audio(self, audio_segment: AudioSegment, output_path: str, 
                    bitrate: str = "128k", format: str = "mp3") -> bool:
        """
        تصدير المقطع الصوتي إلى ملف
        
        Args:
            audio_segment (AudioSegment): المقطع الصوتي
            output_path (str): مسار ملف الإخراج
            bitrate (str): معدل البت
            format (str): صيغة الملف
            
        Returns:
            bool: True إذا تم التصدير بنجاح
        """
        if not PYDUB_AVAILABLE or not audio_segment:
            return False
        
        try:
            # إنشاء مجلد الإخراج
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # تصدير الملف
            audio_segment.export(
                output_path,
                format=format,
                bitrate=bitrate,
                parameters=["-ar", "16000"]  # معدل عينة منخفض لتقليل الحجم
            )
            
            # التحقق من نجاح التصدير
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                self.logger.info(f"تم تصدير الملف الصوتي: {output_path}")
                return True
            else:
                self.logger.error(f"فشل في تصدير الملف: {output_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"خطأ في تصدير الملف الصوتي: {str(e)}")
            return False
    
    def convert_to_mp3(self, input_file: str, output_file: str, bitrate: str = "128k") -> bool:
        """
        تحويل ملف صوتي إلى MP3
        
        Args:
            input_file (str): مسار الملف الأصلي
            output_file (str): مسار ملف الإخراج
            bitrate (str): معدل البت
            
        Returns:
            bool: True إذا تم التحويل بنجاح
        """
        if not PYDUB_AVAILABLE:
            # إذا لم تكن pydub متاحة، نسخ الملف فقط
            try:
                shutil.copy2(input_file, output_file)
                return True
            except:
                return False
        
        try:
            # تحميل الملف الأصلي
            audio = AudioSegment.from_file(input_file)
            
            # تصدير إلى MP3
            return self.export_audio(audio, output_file, bitrate, "mp3")
            
        except Exception as e:
            self.logger.error(f"خطأ في تحويل الملف إلى MP3: {str(e)}")
            return False
    
    def adjust_volume(self, audio_segment: AudioSegment, volume_change_db: float) -> AudioSegment:
        """
        تعديل مستوى الصوت
        
        Args:
            audio_segment (AudioSegment): المقطع الصوتي
            volume_change_db (float): التغيير في مستوى الصوت (بالديسيبل)
            
        Returns:
            AudioSegment: المقطع بعد تعديل الصوت
        """
        if not PYDUB_AVAILABLE or not audio_segment:
            return audio_segment
        
        try:
            return audio_segment + volume_change_db
        except:
            return audio_segment
    
    def remove_silence(self, audio_segment: AudioSegment, silence_thresh: int = -50) -> AudioSegment:
        """
        إزالة الصمت من بداية ونهاية المقطع
        
        Args:
            audio_segment (AudioSegment): المقطع الصوتي
            silence_thresh (int): حد الصمت (بالديسيبل)
            
        Returns:
            AudioSegment: المقطع بعد إزالة الصمت
        """
        if not PYDUB_AVAILABLE or not audio_segment:
            return audio_segment
        
        try:
            # إزالة الصمت من البداية والنهاية
            chunks = split_on_silence(
                audio_segment,
                min_silence_len=500,  # 0.5 ثانية
                silence_thresh=silence_thresh,
                keep_silence=100  # الاحتفاظ ببعض الصمت
            )
            
            if chunks:
                combined = AudioSegment.empty()
                for chunk in chunks:
                    combined += chunk
                return combined
            else:
                return audio_segment
                
        except:
            return audio_segment
    
    def create_zip_archive(self, file_paths: List[str], zip_path: str) -> bool:
        """
        إنشاء أرشيف ZIP للملفات
        
        Args:
            file_paths (List[str]): قائمة بمسارات الملفات
            zip_path (str): مسار ملف ZIP
            
        Returns:
            bool: True إذا تم إنشاء الأرشيف بنجاح
        """
        try:
            # إنشاء مجلد الإخراج
            Path(zip_path).parent.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in file_paths:
                    if os.path.exists(file_path):
                        # إضافة الملف باسم الملف فقط (بدون المسار الكامل)
                        arcname = os.path.basename(file_path)
                        zipf.write(file_path, arcname)
            
            # التحقق من نجاح إنشاء الأرشيف
            if os.path.exists(zip_path) and os.path.getsize(zip_path) > 0:
                self.logger.info(f"تم إنشاء أرشيف ZIP: {zip_path}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"خطأ في إنشاء أرشيف ZIP: {str(e)}")
            return False
    
    def get_audio_info(self, file_path: str) -> dict:
        """
        الحصول على معلومات الملف الصوتي
        
        Args:
            file_path (str): مسار الملف الصوتي
            
        Returns:
            dict: معلومات الملف
        """
        info = {
            'file_exists': os.path.exists(file_path),
            'file_size': 0,
            'duration': 0,
            'format': None,
            'channels': None,
            'frame_rate': None
        }
        
        try:
            if os.path.exists(file_path):
                info['file_size'] = os.path.getsize(file_path)
                
                if PYDUB_AVAILABLE:
                    audio = AudioSegment.from_file(file_path)
                    info['duration'] = len(audio) / 1000.0  # بالثواني
                    info['channels'] = audio.channels
                    info['frame_rate'] = audio.frame_rate
                    info['format'] = file_path.split('.')[-1].lower()
                
        except Exception as e:
            self.logger.error(f"خطأ في الحصول على معلومات الملف: {str(e)}")
        
        return info
