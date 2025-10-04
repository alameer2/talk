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
    
    def create_timed_segment(self, audio_file: str, start_silence_ms: float, 
                           duration_ms: float, pause_ms: float = 500) -> Optional[AudioSegment]:
        """
        إنشاء مقطع صوتي مع توقيت محدد
        
        Args:
            audio_file (str): مسار الملف الصوتي
            start_silence_ms (float): الصمت في البداية (بالميلي ثانية)
            duration_ms (float): مدة المقطع المطلوبة
            pause_ms (float): مدة التوقف في النهاية
            
        Returns:
            AudioSegment: المقطع الصوتي أو None
        """
        if not PYDUB_AVAILABLE:
            self.logger.error("pydub مطلوب لمعالجة الصوت")
            return None
        
        try:
            # تحميل الملف الصوتي
            audio = AudioSegment.from_file(audio_file)
            
            # إنشاء صمت في البداية
            if start_silence_ms > 0:
                start_silence = AudioSegment.silent(duration=int(start_silence_ms))
            else:
                start_silence = AudioSegment.empty()
            
            # تعديل سرعة الصوت ليناسب المدة المطلوبة
            audio_duration = len(audio)
            target_duration = duration_ms - pause_ms
            
            if target_duration > 0 and audio_duration > 0:
                # تعديل السرعة إذا كانت المدة مختلفة
                speed_ratio = audio_duration / target_duration
                if speed_ratio != 1.0:
                    # تغيير السرعة مع الحفاظ على الطبقة الصوتية
                    audio = audio._spawn(audio.raw_data, overrides={
                        "frame_rate": int(audio.frame_rate * speed_ratio)
                    }).set_frame_rate(audio.frame_rate)
            
            # إضافة توقف في النهاية
            if pause_ms > 0:
                end_pause = AudioSegment.silent(duration=int(pause_ms))
                audio = audio + end_pause
            
            # دمج الصمت مع الصوت
            final_segment = start_silence + audio
            
            return final_segment
            
        except Exception as e:
            self.logger.error(f"خطأ في إنشاء المقطع الصوتي: {str(e)}")
            return None
    
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
                parameters=["-ar", "22050"]  # تقليل معدل العينة لتوفير المساحة
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
                return sum(chunks)
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
