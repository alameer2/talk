import streamlit as st
import os
import tempfile
import shutil
from pathlib import Path
import time

# استيراد الوحدات المخصصة
from srt_processor import SRTProcessor
from tts_engine import TTSEngine
from audio_utils import AudioUtils
from text_processor import TextProcessor

# إعدادات الصفحة
st.set_page_config(
    page_title="محول ملفات SRT إلى كلام عربي",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# إنشاء المجلدات المطلوبة
def create_directories():
    """إنشاء المجلدات المطلوبة للتطبيق"""
    directories = ['upload', 'output', 'temp']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)

def main():
    create_directories()
    
    # العنوان الرئيسي
    st.title("🎙️ محول ملفات الترجمة SRT إلى كلام عربي")
    st.markdown("---")
    
    # الشريط الجانبي للإعدادات
    with st.sidebar:
        st.header("⚙️ إعدادات التحويل")
        
        # إعدادات الصوت
        st.subheader("🔊 إعدادات الصوت")
        tts_engine = st.selectbox(
            "محرك تحويل النص إلى كلام:",
            ["gTTS (جوجل - يحتاج إنترنت)", "pyttsx3 (محلي - بدون إنترنت)"],
            help="gTTS يوفر جودة صوت أفضل لكن يحتاج إنترنت"
        )
        
        speech_rate = st.slider(
            "سرعة الكلام:",
            min_value=0.5,
            max_value=2.0,
            value=1.0,
            step=0.1,
            help="1.0 = السرعة العادية"
        )
        
        # إعدادات الإخراج
        st.subheader("📁 إعدادات الإخراج")
        output_format = st.selectbox(
            "نوع الإخراج:",
            ["ملف صوتي واحد متكامل", "ملفات منفصلة لكل سطر ترجمة"],
            help="اختر طريقة تنظيم ملفات الصوت"
        )
        
        audio_quality = st.selectbox(
            "جودة الصوت:",
            ["عالية (192 kbps)", "متوسطة (128 kbps)", "منخفضة (64 kbps)"],
            index=1
        )
        
        # إعدادات متقدمة
        st.subheader("🔧 إعدادات متقدمة")
        pause_duration = st.slider(
            "مدة التوقف بين الجمل (ثانية):",
            min_value=0.0,
            max_value=3.0,
            value=0.5,
            step=0.1
        )
        
        handle_punctuation = st.checkbox(
            "معالجة علامات الترقيم",
            value=True,
            help="إضافة توقف طبيعي عند الفواصل وعلامات التعجب"
        )
        
        # التحقق من توفر محرك التشكيل
        from text_processor import TASHKEEL_AVAILABLE
        
        if TASHKEEL_AVAILABLE:
            add_tashkeel = st.checkbox(
                "إضافة التشكيل التلقائي ✅",
                value=True,
                help="إضافة الحركات (التشكيل) للنص العربي لتحسين النطق الصحيح - يُنصح بتفعيله للحصول على نطق دقيق"
            )
        else:
            st.warning("⚠️ محرك التشكيل غير متوفر - سيتم تخطي التشكيل")
            add_tashkeel = False
    
    # المحتوى الرئيسي
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📁 رفع ملف الترجمة SRT")
        
        # خيارات رفع الملف
        upload_method = st.radio(
            "طريقة رفع الملف:",
            ["رفع مباشر", "من مجلد upload"],
            horizontal=True
        )
        
        srt_file = None
        
        if upload_method == "رفع مباشر":
            srt_file = st.file_uploader(
                "اختر ملف SRT:",
                type=['srt'],
                help="حدد ملف الترجمة بصيغة SRT"
            )
        else:
            # عرض الملفات في مجلد upload
            upload_dir = Path("upload")
            srt_files = list(upload_dir.glob("*.srt"))
            
            if srt_files:
                selected_file = st.selectbox(
                    "اختر ملف من مجلد upload:",
                    [f.name for f in srt_files]
                )
                if selected_file:
                    srt_file = upload_dir / selected_file
            else:
                st.info("لا توجد ملفات SRT في مجلد upload")
    
    with col2:
        st.header("ℹ️ معلومات المشروع")
        st.markdown("""
        **المميزات:**
        - دعم كامل للغة العربية
        - معالجة ذكية لعلامات الترقيم
        - الحفاظ على التوقيت الدقيق
        - خيارات متعددة للإخراج
        - مجاني تماماً
        
        **المكتبات المستخدمة:**
        - gTTS للتحويل عبر الإنترنت
        - pyttsx3 للتحويل المحلي
        - pysrt لمعالجة ملفات SRT
        - pydub لمعالجة الصوت
        - mishkal للتشكيل التلقائي
        
        **💡 نصيحة:**
        فعّل "التشكيل التلقائي" للحصول على نطق أفضل ودقة أعلى
        """)
    
    # معالجة الملف
    if srt_file is not None:
        st.markdown("---")
        st.header("🔄 معالجة الملف")
        
        # قراءة الملف
        try:
            if isinstance(srt_file, str) or isinstance(srt_file, Path):
                # ملف من مجلد upload
                file_content = open(srt_file, 'r', encoding='utf-8').read()
                file_name = Path(srt_file).stem
            else:
                # ملف مرفوع مباشرة
                file_content = str(srt_file.read(), 'utf-8')
                file_name = srt_file.name.split('.')[0]
            
            # معالج SRT
            processor = SRTProcessor()
            subtitles = processor.parse_srt_content(file_content)
            
            if not subtitles:
                st.error("❌ لم يتم العثور على ترجمات صالحة في الملف")
                return
            
            # عرض معلومات الملف
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("عدد السطور", len(subtitles))
            with col2:
                total_duration = max([sub['end_time'] for sub in subtitles]) if subtitles else 0
                st.metric("المدة الإجمالية", f"{total_duration:.1f}s")
            with col3:
                total_chars = sum([len(sub['text']) for sub in subtitles])
                st.metric("عدد الأحرف", total_chars)
            
            # معاينة النص
            with st.expander("معاينة محتوى الملف", expanded=False):
                for i, sub in enumerate(subtitles[:5]):  # أول 5 سطور
                    st.write(f"**{i+1}.** [{sub['start_time']:.1f}s - {sub['end_time']:.1f}s] {sub['text']}")
                if len(subtitles) > 5:
                    st.write(f"... و {len(subtitles) - 5} سطر آخر")
            
            # زر بدء التحويل
            if st.button("🚀 بدء التحويل إلى كلام", type="primary"):
                convert_to_speech(
                    subtitles, 
                    file_name, 
                    tts_engine, 
                    speech_rate, 
                    output_format, 
                    audio_quality, 
                    pause_duration, 
                    handle_punctuation,
                    add_tashkeel
                )
        
        except Exception as e:
            st.error(f"❌ خطأ في قراءة الملف: {str(e)}")

def convert_to_speech(subtitles, file_name, tts_engine, speech_rate, output_format, audio_quality, pause_duration, handle_punctuation, add_tashkeel=False):
    """تحويل الترجمات إلى كلام"""
    
    # شريط التقدم
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # إعداد محرك TTS
        engine_type = "gtts" if "gTTS" in tts_engine else "pyttsx3"
        tts = TTSEngine(engine_type, speech_rate)
        
        # معالج النصوص
        text_proc = TextProcessor()
        
        # معالج الصوت
        audio_util = AudioUtils()
        
        # إعداد جودة الصوت
        bitrate_map = {
            "عالية (192 kbps)": "192k",
            "متوسطة (128 kbps)": "128k", 
            "منخفضة (64 kbps)": "64k"
        }
        bitrate = bitrate_map[audio_quality]
        
        status_text.text("🔄 بدء معالجة الترجمات...")
        
        if output_format == "ملف صوتي واحد متكامل":
            # إنشاء ملف صوتي واحد
            audio_segments = []
            
            for i, subtitle in enumerate(subtitles):
                progress = (i + 1) / len(subtitles)
                progress_bar.progress(progress)
                status_text.text(f"🎙️ معالجة السطر {i+1} من {len(subtitles)}")
                
                # معالجة النص
                processed_text = text_proc.process_arabic_text(
                    subtitle['text'], 
                    handle_punctuation,
                    for_tts=True,
                    add_tashkeel=add_tashkeel
                )
                
                if processed_text.strip():
                    # تحويل إلى كلام
                    audio_file = tts.text_to_speech(processed_text, f"temp/subtitle_{i}.wav")
                    
                    if audio_file:
                        # حساب التوقيت الدقيق مع الصمت
                        start_silence = subtitle['start_time'] * 1000
                        duration = (subtitle['end_time'] - subtitle['start_time']) * 1000
                        
                        # تحميل الملف الصوتي
                        audio = audio_util.load_audio(audio_file)
                        if audio:
                            # إنشاء المقطع مع الصمت في البداية
                            segment = audio_util.create_timed_segment_optimized(
                                audio, 
                                start_silence, 
                                duration,
                                pause_duration * 1000
                            )
                            if segment:
                                audio_segments.append(segment)
            
            if audio_segments:
                status_text.text("🔧 دمج ملفات الصوت...")
                final_audio = audio_util.combine_audio_segments(audio_segments)
                
                # حفظ الملف النهائي
                output_path = f"output/{file_name}_complete.mp3"
                audio_util.export_audio(final_audio, output_path, bitrate)
                
                status_text.text("✅ تم إنشاء الملف الصوتي بنجاح!")
                
                # رابط التحميل
                with open(output_path, "rb") as f:
                    st.download_button(
                        "⬇️ تحميل الملف الصوتي الكامل",
                        f.read(),
                        file_name=f"{file_name}_complete.mp3",
                        mime="audio/mpeg"
                    )
        
        else:
            # إنشاء ملفات منفصلة
            output_files = []
            
            for i, subtitle in enumerate(subtitles):
                progress = (i + 1) / len(subtitles)
                progress_bar.progress(progress)
                status_text.text(f"🎙️ إنشاء ملف للسطر {i+1} من {len(subtitles)}")
                
                # معالجة النص
                processed_text = text_proc.process_arabic_text(
                    subtitle['text'], 
                    handle_punctuation,
                    for_tts=True,
                    add_tashkeel=add_tashkeel
                )
                
                if processed_text.strip():
                    # تحويل إلى كلام
                    audio_file = tts.text_to_speech(processed_text, f"temp/subtitle_{i}.wav")
                    
                    if audio_file:
                        # تحويل إلى MP3
                        output_path = f"output/{file_name}_line_{i+1:03d}.mp3"
                        audio_util.convert_to_mp3(audio_file, output_path, bitrate)
                        output_files.append(output_path)
            
            status_text.text(f"✅ تم إنشاء {len(output_files)} ملف صوتي!")
            
            # أرشيف ZIP للملفات المتعددة
            if output_files:
                zip_path = f"output/{file_name}_all_files.zip"
                audio_util.create_zip_archive(output_files, zip_path)
                
                with open(zip_path, "rb") as f:
                    st.download_button(
                        f"⬇️ تحميل جميع الملفات ({len(output_files)} ملف)",
                        f.read(),
                        file_name=f"{file_name}_all_files.zip",
                        mime="application/zip"
                    )
        
        # تنظيف الملفات المؤقتة
        shutil.rmtree("temp", ignore_errors=True)
        Path("temp").mkdir(exist_ok=True)
        
        progress_bar.progress(1.0)
        st.success("🎉 تم إنجاز التحويل بنجاح!")
        
    except Exception as e:
        st.error(f"❌ خطأ أثناء التحويل: {str(e)}")
        progress_bar.empty()
        status_text.empty()

if __name__ == "__main__":
    main()
