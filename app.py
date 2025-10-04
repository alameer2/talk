import streamlit as st
import os
import tempfile
import shutil
from pathlib import Path
import time
import json
import requests

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

def load_user_preferences():
    """تحميل إعدادات المستخدم المحفوظة"""
    prefs_file = Path("user_preferences.json")
    if prefs_file.exists():
        try:
            with open(prefs_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_user_preferences(preferences):
    """حفظ إعدادات المستخدم"""
    try:
        with open("user_preferences.json", 'w', encoding='utf-8') as f:
            json.dump(preferences, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"تعذر حفظ الإعدادات: {str(e)}")

@st.cache_data(ttl=3600)
def fetch_lahajati_voices(api_key):
    """جلب قائمة الأصوات المتاحة من Lahajati API مع دعم pagination"""
    try:
        all_voices = []
        page = 1
        per_page = 50
        
        while True:
            url = f'https://lahajati.ai/api/v1/voices?page={page}&per_page={per_page}'
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Accept': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data and len(data['data']) > 0:
                    for voice in data['data']:
                        voice_id = voice.get('id', voice.get('voice_id', ''))
                        voice_name = voice.get('voice_name', voice.get('name', voice.get('display_name', '')))
                        
                        if not voice_name or voice_name.strip() == '':
                            voice_name = f"صوت {voice_id[:8]}" if voice_id else "صوت غير معروف"
                        
                        gender_id = voice.get('gender', 0)
                        tags = voice.get('voice_tags', voice.get('tags', ''))
                        dialect = voice.get('dialect', voice.get('accent', ''))
                        
                        gender_map = {1: '🙎 ذكر', 2: '🙍 أنثى', 3: '👶 طفل'}
                        gender = gender_map.get(gender_id, '')
                        
                        display_name = f"{voice_name}"
                        if gender:
                            display_name += f" {gender}"
                        if dialect:
                            display_name += f" • {dialect}"
                        elif tags:
                            display_name += f" • {tags}"
                        
                        all_voices.append({
                            'id': voice_id,
                            'name': display_name,
                            'voice_name': voice_name,
                            'gender': gender,
                            'tags': tags,
                            'dialect': dialect,
                            'preview_url': voice.get('preview_url', voice.get('sample_url', ''))
                        })
                    
                    if len(data['data']) < per_page:
                        break
                    page += 1
                else:
                    break
            else:
                if page == 1:
                    st.error(f"خطأ في جلب الأصوات: {response.status_code}")
                break
        
        return all_voices
            
    except Exception as e:
        st.error(f"فشل الاتصال بـ Lahajati API: {str(e)}")
        return []

def main():
    create_directories()
    
    # تحميل الإعدادات المحفوظة
    if 'preferences_loaded' not in st.session_state:
        st.session_state.preferences = load_user_preferences()
        st.session_state.preferences_loaded = True
    
    # تهيئة session state للترجمات القابلة للتحرير
    if 'editable_subtitles' not in st.session_state:
        st.session_state.editable_subtitles = None
    if 'edited_texts' not in st.session_state:
        st.session_state.edited_texts = {}
    
    # تهيئة session state لإعدادات TTS
    if 'lahajati_voice_id' not in st.session_state:
        st.session_state.lahajati_voice_id = None
    if 'lahajati_api_key' not in st.session_state:
        st.session_state.lahajati_api_key = None
    
    # العنوان الرئيسي
    st.title("🎙️ محول ملفات الترجمة SRT إلى كلام عربي")
    st.markdown("---")
    
    # الشريط الجانبي للإعدادات
    with st.sidebar:
        st.header("⚙️ إعدادات التحويل")
        
        # إعدادات الصوت
        st.subheader("🔊 إعدادات الصوت")
        
        # قائمة محركات TTS المتاحة
        st.markdown("""
        **الخيارات المجانية بدون تسجيل:**
        - ✅ **gTTS**: مجاني تماماً (صوت واحد فقط)
        - ✅ **pyttsx3**: محلي بدون إنترنت
        
        **الخيارات المجانية مع تسجيل (تحتاج API Key):**
        - 🔑 **Lahajati**: 108 لهجة، 10k حرف/شهر
        - 🔑 **ElevenLabs**: AI، 10k حرف/شهر
        - 🔑 **Azure/AWS**: أصوات احترافية
        """)
        
        tts_engines_list = [
            "gTTS (مجاني - بدون تسجيل)",
            "pyttsx3 (محلي - بدون تسجيل)",
            "Lahajati (108 لهجة - يحتاج API Key)",
            "ElevenLabs (AI - يحتاج API Key)",
            "Azure TTS (احترافي - يحتاج API Key)",
            "AWS Polly (Amazon - يحتاج API Key)"
        ]
        
        default_engine = st.session_state.preferences.get('tts_engine', 0)
        tts_engine = st.selectbox(
            "محرك تحويل النص إلى كلام:",
            tts_engines_list,
            index=default_engine if default_engine < len(tts_engines_list) else 0,
            help="اختر محرك التحويل المناسب"
        )
        
        # تحذير حول قيود gTTS مع العربية
        if "gTTS" in tts_engine:
            st.success("""
            ✅ **gTTS - مجاني تماماً بدون تسجيل!**
            - لا يحتاج API key أو تسجيل
            - يعمل مباشرة عبر الإنترنت
            - **القيود**: صوت واحد فقط للعربية
            
            💡 **للحصول على نطق أفضل:**
            - فعّل "التشكيل التلقائي" ✅
            - قلل سرعة الكلام إلى 0.8-0.9
            - استخدم "معالجة علامات الترقيم"
            """)
        
        if "pyttsx3" in tts_engine:
            st.success("""
            ✅ **pyttsx3 - مجاني تماماً بدون تسجيل!**
            - لا يحتاج API key أو تسجيل
            - يعمل محلياً بدون إنترنت
            """)
            st.warning("""
            ⚠️ **تنبيه:** دعم العربية محدود على بعض الأنظمة.
            للحصول على نتائج أفضل، استخدم gTTS.
            """)
        
        # إعدادات API للمحركات السحابية
        azure_key = None
        azure_region = None
        elevenlabs_key = None
        aws_access_key = None
        aws_secret_key = None
        aws_region = None
        lahajati_key = None
        lahajati_voice_id = None
        
        if "Lahajati" in tts_engine:
            st.info("""
            🎯 **Lahajati:**
            - **108 لهجة عربية مختلفة** (مصري، خليجي، شامي، مغربي...)
            - **500+ صوت احترافي** بجودة استوديو
            - **مجاني: 10,000 حرف/شهر** (بدون بطاقة ائتمان)
            - سجّل مجاناً على: https://lahajati.ai/
            """)
            
            st.markdown("### 📋 خطوات الاستخدام:")
            st.markdown("""
            1. أدخل **API Key** في الحقل أدناه
            2. انتظر تحميل قائمة الأصوات
            3. **اختر الصوت** المناسب من القائمة
            4. ابدأ التحويل أو المعاينة
            """)
            
            with st.expander("⚙️ إعدادات Lahajati", expanded=True):
                lahajati_key = st.text_input(
                    "🔑 Lahajati API Key:",
                    type="password",
                    key="lahajati_key",
                    help="احصل على مفتاح API مجاناً من لوحة التحكم في lahajati.ai"
                )
                
                if not lahajati_key:
                    st.error("⚠️ **خطوة إلزامية:** يجب توفير API Key لاستخدام Lahajati.")
                    st.info("📝 سجّل مجاناً على [lahajati.ai](https://lahajati.ai/) للحصول على 10,000 حرف/شهر!")
                    lahajati_voice_id = None
                else:
                    st.session_state.lahajati_api_key = lahajati_key
                    os.environ['LAHAJATI_API_KEY'] = lahajati_key
                    
                    with st.spinner("🔄 جاري تحميل قائمة الأصوات..."):
                        voices_list = fetch_lahajati_voices(lahajati_key)
                    
                    if voices_list:
                        st.success(f"✅ تم العثور على {len(voices_list)} صوت!")
                        
                        all_dialects = sorted(set([v.get('dialect', '') for v in voices_list if v.get('dialect', '')]))
                        all_genders = sorted(set([v.get('gender', '') for v in voices_list if v.get('gender', '')]))
                        
                        col_filter1, col_filter2 = st.columns(2)
                        with col_filter1:
                            dialect_filter = st.selectbox(
                                "🗣️ تصفية حسب اللهجة:",
                                ["الكل"] + all_dialects,
                                help="اختر لهجة معينة أو عرض الكل"
                            )
                        
                        with col_filter2:
                            gender_filter = st.selectbox(
                                "👤 تصفية حسب النوع:",
                                ["الكل"] + all_genders,
                                help="اختر نوع الصوت"
                            )
                        
                        search_text = st.text_input(
                            "🔍 بحث في الأصوات:",
                            placeholder="ابحث بالاسم...",
                            help="ابحث عن صوت محدد بالاسم"
                        )
                        
                        filtered_voices = voices_list
                        if dialect_filter != "الكل":
                            filtered_voices = [v for v in filtered_voices if v.get('dialect', '') == dialect_filter]
                        if gender_filter != "الكل":
                            filtered_voices = [v for v in filtered_voices if v.get('gender', '') == gender_filter]
                        if search_text:
                            filtered_voices = [v for v in filtered_voices if search_text.lower() in v.get('voice_name', '').lower()]
                        
                        if filtered_voices:
                            st.info(f"📊 عدد الأصوات المتاحة: {len(filtered_voices)} من {len(voices_list)}")
                            
                            voice_names = [v['name'] for v in filtered_voices]
                            voice_ids = [v['id'] for v in filtered_voices]
                            
                            selected_voice_index = st.selectbox(
                                "🎤 اختر الصوت:",
                                range(len(voice_names)),
                                format_func=lambda i: voice_names[i],
                                help="اختر الصوت المناسب من القائمة"
                            )
                            
                            lahajati_voice_id = voice_ids[selected_voice_index]
                            selected_voice = filtered_voices[selected_voice_index]
                            
                            st.success(f"✅ **الصوت المختار:** {voice_names[selected_voice_index]}")
                            st.code(f"🔑 Voice ID: {lahajati_voice_id}", language=None)
                            
                            if selected_voice.get('preview_url'):
                                st.markdown("### 🎧 معاينة الصوت")
                                st.audio(selected_voice['preview_url'])
                            
                            with st.expander("🔍 عرض تفاصيل الصوت المختار", expanded=False):
                                st.json({
                                    'اسم الصوت': selected_voice.get('voice_name', ''),
                                    'النوع': selected_voice.get('gender', ''),
                                    'اللهجة': selected_voice.get('dialect', ''),
                                    'الوسوم': selected_voice.get('tags', ''),
                                    'المعرّف': selected_voice.get('id', '')
                                })
                            
                            if lahajati_voice_id:
                                st.session_state.lahajati_voice_id = lahajati_voice_id
                                os.environ['LAHAJATI_VOICE_ID'] = lahajati_voice_id
                        else:
                            st.warning("⚠️ لم يتم العثور على أصوات تطابق معايير البحث.")
                            lahajati_voice_id = None
                    else:
                        st.warning("⚠️ لم نتمكن من جلب قائمة الأصوات. تأكد من صحة API Key.")
                        lahajati_voice_id = st.text_input(
                            "Voice ID (معرّف الصوت) - إدخال يدوي:",
                            value="",
                            key="lahajati_voice_manual",
                            help="أدخل معرّف الصوت يدوياً"
                        )
                        if lahajati_voice_id:
                            os.environ['LAHAJATI_VOICE_ID'] = lahajati_voice_id
        
        if "Azure" in tts_engine:
            st.info("🎯 **Azure TTS:** أصوات احترافية بجودة عالية جداً.")
            with st.expander("⚙️ إعدادات Azure", expanded=True):
                azure_key = st.text_input("Azure Speech Key:", type="password", key="azure_key")
                azure_region = st.text_input("Azure Region:", value="eastus", key="azure_region")
                if azure_key:
                    os.environ['AZURE_SPEECH_KEY'] = azure_key
                    os.environ['AZURE_REGION'] = azure_region
        
        if "ElevenLabs" in tts_engine:
            st.info("""
            🤖 **ElevenLabs:**
            - أصوات واقعية جداً بتقنية AI
            - **مجاني: 10,000 حرف/شهر**
            - لهجات عربية إقليمية
            - سجّل مجاناً على: https://elevenlabs.io/
            """)
            with st.expander("⚙️ إعدادات ElevenLabs (اختياري)", expanded=False):
                elevenlabs_key = st.text_input(
                    "ElevenLabs API Key:",
                    type="password",
                    key="elevenlabs_key",
                    help="احصل على مفتاح API مجاناً من لوحة التحكم في elevenlabs.io"
                )
                
                if not elevenlabs_key:
                    st.warning("⚠️ يجب توفير API Key لاستخدام ElevenLabs. سجّل مجاناً على elevenlabs.io للحصول على 10,000 حرف/شهر!")
                
                if elevenlabs_key:
                    os.environ['ELEVENLABS_API_KEY'] = elevenlabs_key
        
        if "AWS Polly" in tts_engine:
            st.info("☁️ **AWS Polly:** خدمة Amazon لتحويل النص إلى كلام.")
            with st.expander("⚙️ إعدادات AWS", expanded=True):
                aws_access_key = st.text_input("AWS Access Key ID:", type="password", key="aws_access")
                aws_secret_key = st.text_input("AWS Secret Access Key:", type="password", key="aws_secret")
                aws_region = st.text_input("AWS Region:", value="us-east-1", key="aws_region")
                if aws_access_key and aws_secret_key:
                    os.environ['AWS_ACCESS_KEY_ID'] = aws_access_key
                    os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_key
                    os.environ['AWS_REGION'] = aws_region
        
        default_speed = st.session_state.preferences.get('speech_rate', 0.9)
        speech_rate = st.slider(
            "سرعة الكلام:",
            min_value=0.5,
            max_value=2.0,
            value=default_speed,
            step=0.1,
            help="للحصول على نطق أفضل للعربية، استخدم 0.8-0.9 (سرعة أقل = نطق أوضح)"
        )
        
        # إعدادات الإخراج
        st.subheader("📁 إعدادات الإخراج")
        
        default_format = st.session_state.preferences.get('output_format', 0)
        output_format = st.selectbox(
            "نوع الإخراج:",
            ["ملف صوتي واحد متكامل", "ملفات منفصلة لكل سطر ترجمة"],
            index=default_format,
            help="اختر طريقة تنظيم ملفات الصوت"
        )
        
        default_quality = st.session_state.preferences.get('audio_quality', 1)
        audio_quality = st.selectbox(
            "جودة الصوت:",
            ["عالية (192 kbps)", "متوسطة (128 kbps)", "منخفضة (64 kbps)"],
            index=default_quality
        )
        
        # إعدادات متقدمة
        st.subheader("🔧 إعدادات متقدمة")
        
        default_pause = st.session_state.preferences.get('pause_duration', 0.5)
        pause_duration = st.slider(
            "مدة التوقف بين الجمل (ثانية):",
            min_value=0.0,
            max_value=3.0,
            value=default_pause,
            step=0.1
        )
        
        default_punctuation = st.session_state.preferences.get('handle_punctuation', True)
        handle_punctuation = st.checkbox(
            "معالجة علامات الترقيم",
            value=default_punctuation,
            help="إضافة توقف طبيعي عند الفواصل وعلامات التعجب"
        )
        
        # التحقق من توفر محرك التشكيل
        from text_processor import TASHKEEL_AVAILABLE
        
        if TASHKEEL_AVAILABLE:
            default_tashkeel = st.session_state.preferences.get('add_tashkeel', True)
            add_tashkeel = st.checkbox(
                "إضافة التشكيل التلقائي ✅",
                value=default_tashkeel,
                help="إضافة الحركات (التشكيل) للنص العربي لتحسين النطق الصحيح - يُنصح بتفعيله للحصول على نطق دقيق"
            )
        else:
            st.warning("⚠️ محرك التشكيل غير متوفر - سيتم تخطي التشكيل")
            add_tashkeel = False
        
        # زر حفظ الإعدادات
        st.markdown("---")
        if st.button("💾 حفظ الإعدادات الحالية"):
            preferences = {
                'tts_engine': tts_engines_list.index(tts_engine),
                'speech_rate': speech_rate,
                'output_format': ["ملف صوتي واحد متكامل", "ملفات منفصلة لكل سطر ترجمة"].index(output_format),
                'audio_quality': ["عالية (192 kbps)", "متوسطة (128 kbps)", "منخفضة (64 kbps)"].index(audio_quality),
                'pause_duration': pause_duration,
                'handle_punctuation': handle_punctuation,
                'add_tashkeel': add_tashkeel
            }
            save_user_preferences(preferences)
            st.session_state.preferences = preferences
            st.success("✅ تم حفظ الإعدادات بنجاح!")
    
    # المحتوى الرئيسي
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📁 رفع ملفات الترجمة SRT")
        
        # نوع المعالجة
        processing_mode = st.radio(
            "نوع المعالجة:",
            ["ملف واحد", "معالجة دفعية (متعددة)"],
            horizontal=True,
            help="اختر بين معالجة ملف واحد أو عدة ملفات دفعة واحدة"
        )
        
        srt_files_list = []
        
        if processing_mode == "ملف واحد":
            # خيارات رفع ملف واحد
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
                if srt_file:
                    srt_files_list = [srt_file]
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
                        srt_files_list = [srt_file]
                else:
                    st.info("لا توجد ملفات SRT في مجلد upload")
        else:
            # معالجة دفعية
            batch_upload_method = st.radio(
                "طريقة رفع الملفات:",
                ["رفع مباشر", "من مجلد upload"],
                horizontal=True,
                key="batch_upload"
            )
            
            if batch_upload_method == "رفع مباشر":
                uploaded_files = st.file_uploader(
                    "اختر ملفات SRT متعددة:",
                    type=['srt'],
                    accept_multiple_files=True,
                    help="يمكنك اختيار عدة ملفات مرة واحدة"
                )
                if uploaded_files:
                    srt_files_list = uploaded_files
            else:
                # عرض جميع الملفات في مجلد upload
                upload_dir = Path("upload")
                available_files = list(upload_dir.glob("*.srt"))
                
                if available_files:
                    st.info(f"📂 تم العثور على {len(available_files)} ملف في مجلد upload")
                    selected_files = st.multiselect(
                        "اختر الملفات للمعالجة:",
                        [f.name for f in available_files],
                        default=[f.name for f in available_files]
                    )
                    if selected_files:
                        srt_files_list = [upload_dir / f for f in selected_files]
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
    
    # معالجة الملفات
    if srt_files_list:
        st.markdown("---")
        
        # معالجة كل ملف
        for file_idx, srt_file in enumerate(srt_files_list):
            if processing_mode == "معالجة دفعية (متعددة)":
                st.header(f"🔄 معالجة الملف {file_idx + 1} من {len(srt_files_list)}")
            else:
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
                    st.error(f"❌ لم يتم العثور على ترجمات صالحة في الملف: {file_name}")
                    continue
                
                # حفظ الترجمات في session state
                st.session_state.editable_subtitles = subtitles
                
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
                
                # إنشاء tabs للمعاينة والتحرير
                tab1, tab2, tab3 = st.tabs(["📝 معاينة", "✏️ تحرير النص", "🎧 معاينة صوتية"])
                
                with tab1:
                    # معاينة النص
                    st.subheader("معاينة محتوى الملف")
                    for i, sub in enumerate(subtitles[:10]):  # أول 10 سطور
                        st.write(f"**{i+1}.** [{sub['start_time']:.1f}s - {sub['end_time']:.1f}s] {sub['text']}")
                    if len(subtitles) > 10:
                        st.write(f"... و {len(subtitles) - 10} سطر آخر")
                
                with tab2:
                    # تحرير النص
                    st.subheader("تحرير نصوص الترجمة")
                    st.info("💡 يمكنك تعديل النصوص هنا قبل التحويل إلى كلام")
                    
                    # عرض أول 10 سطور قابلة للتحرير
                    num_to_show = min(10, len(subtitles))
                    for i in range(num_to_show):
                        sub = subtitles[i]
                        key = f"{file_name}_sub_{i}"
                        
                        # استخدام النص المحرر إذا كان موجوداً، وإلا استخدم النص الأصلي
                        current_text = st.session_state.edited_texts.get(key, sub['text'])
                        
                        edited_text = st.text_area(
                            f"السطر {i+1} [{sub['start_time']:.1f}s - {sub['end_time']:.1f}s]",
                            value=current_text,
                            key=key,
                            height=60
                        )
                        
                        # حفظ النص المحرر
                        st.session_state.edited_texts[key] = edited_text
                        subtitles[i]['text'] = edited_text
                    
                    if len(subtitles) > 10:
                        st.info(f"📌 يمكنك تحرير أول 10 سطور. باقي {len(subtitles) - 10} سطر سيتم معالجتها كما هي.")
                
                with tab3:
                    # معاينة صوتية
                    st.subheader("🎧 استماع لعينة صوتية")
                    st.info("استمع إلى أول 3 سطور لضبط الإعدادات قبل التحويل الكامل")
                    
                    # تحذير خاص لـ Lahajati
                    if "Lahajati" in tts_engine:
                        lahajati_voice_check = st.session_state.get('lahajati_voice_id')
                        lahajati_api_check = st.session_state.get('lahajati_api_key')
                        
                        if not lahajati_api_check:
                            st.error("⚠️ **مطلوب:** يجب إدخال API Key في إعدادات Lahajati في الشريط الجانبي!")
                        elif not lahajati_voice_check:
                            st.warning("⚠️ **مطلوب:** يجب اختيار صوت من قائمة Lahajati في الشريط الجانبي أولاً!")
                        else:
                            st.success(f"✅ الصوت المحدد: {lahajati_voice_check[:20]}...")
                    
                    preview_count = st.slider(
                        "عدد السطور للمعاينة:",
                        min_value=1,
                        max_value=min(5, len(subtitles)),
                        value=min(3, len(subtitles)),
                        key=f"preview_slider_{file_name}"
                    )
                    
                    preview_disabled = False
                    error_msg = None
                    
                    if "Lahajati" in tts_engine:
                        if not st.session_state.get('lahajati_api_key'):
                            preview_disabled = True
                            error_msg = "⚠️ **مطلوب:** يجب إدخال API Key في إعدادات Lahajati أولاً!"
                        elif not st.session_state.get('lahajati_voice_id'):
                            preview_disabled = True
                            error_msg = "⚠️ **مطلوب:** يجب اختيار صوت من قائمة Lahajati أولاً!"
                    elif "ElevenLabs" in tts_engine:
                        if not os.getenv('ELEVENLABS_API_KEY'):
                            preview_disabled = True
                            error_msg = "⚠️ **مطلوب:** يجب إدخال API Key في إعدادات ElevenLabs أولاً!"
                    elif "Azure" in tts_engine:
                        if not os.getenv('AZURE_SPEECH_KEY'):
                            preview_disabled = True
                            error_msg = "⚠️ **مطلوب:** يجب إدخال API Key في إعدادات Azure أولاً!"
                    elif "AWS" in tts_engine:
                        if not os.getenv('AWS_ACCESS_KEY_ID'):
                            preview_disabled = True
                            error_msg = "⚠️ **مطلوب:** يجب إدخال AWS credentials في إعدادات AWS Polly أولاً!"
                    
                    if st.button("🔊 إنشاء معاينة صوتية", key=f"preview_btn_{file_name}", disabled=preview_disabled):
                        with st.spinner("⏳ جاري إنشاء المعاينة..."):
                            preview_audio = generate_preview(
                                subtitles[:preview_count],
                                file_name,
                                tts_engine,
                                speech_rate,
                                pause_duration,
                                handle_punctuation,
                                add_tashkeel
                            )
                            
                            if preview_audio:
                                st.audio(preview_audio, format='audio/mp3')
                                st.success(f"✅ تم إنشاء معاينة لأول {preview_count} سطور")
                            else:
                                st.error("❌ فشل إنشاء المعاينة. راجع اللوقات أدناه لمعرفة السبب.")
                    
                    if error_msg and preview_disabled:
                        st.error(error_msg)
                
                # أزرار التحويل
                st.markdown("---")
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    if st.button(f"🚀 بدء التحويل الكامل", type="primary", key=f"convert_btn_{file_name}"):
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
                
                with col_btn2:
                    if st.button(f"🔄 إعادة تحميل الملف", key=f"reset_btn_{file_name}"):
                        # مسح التعديلات
                        for i in range(len(subtitles)):
                            key = f"{file_name}_sub_{i}"
                            if key in st.session_state.edited_texts:
                                del st.session_state.edited_texts[key]
                        st.rerun()
            
            except Exception as e:
                st.error(f"❌ خطأ في قراءة الملف {file_name}: {str(e)}")
            
            # فاصل بين الملفات في حالة المعالجة الدفعية
            if processing_mode == "معالجة دفعية (متعددة)" and file_idx < len(srt_files_list) - 1:
                st.markdown("---")

def generate_preview(subtitles, file_name, tts_engine, speech_rate, pause_duration, handle_punctuation, add_tashkeel=False):
    """إنشاء معاينة صوتية لعدد محدود من السطور"""
    try:
        # إعداد محرك TTS
        engine_type, api_key, credentials = get_engine_type_and_key(tts_engine)
        tts = TTSEngine(engine_type, speech_rate, api_key, credentials)
        
        # معالج النصوص
        text_proc = TextProcessor()
        
        # معالج الصوت
        audio_util = AudioUtils()
        
        # إنشاء ملفات صوتية للمعاينة
        audio_segments = []
        
        for i, subtitle in enumerate(subtitles):
            # معالجة النص
            processed_text = text_proc.process_arabic_text(
                subtitle['text'], 
                handle_punctuation,
                for_tts=True,
                add_tashkeel=add_tashkeel
            )
            
            if processed_text.strip():
                # تحويل إلى كلام
                audio_file = tts.text_to_speech(processed_text, f"temp/preview_{i}.wav")
                
                if audio_file:
                    # تحميل الملف الصوتي
                    audio = audio_util.load_audio(audio_file)
                    if audio:
                        # إضافة توقف صغير بين السطور
                        audio_with_pause = audio_util.add_pause(audio, pause_duration * 1000)
                        if audio_with_pause:
                            audio_segments.append(audio_with_pause)
        
        if audio_segments:
            # دمج المقاطع
            final_audio = audio_util.combine_audio_segments(audio_segments)
            
            # حفظ الملف
            preview_path = f"temp/preview_{file_name}.mp3"
            audio_util.export_audio(final_audio, preview_path, "128k")
            
            return preview_path
        
        return None
        
    except Exception as e:
        st.error(f"❌ خطأ في إنشاء المعاينة: {str(e)}")
        return None

def get_engine_type_and_key(tts_engine_name):
    """استخراج نوع المحرك ومفتاح API من اسم المحرك"""
    api_key = None
    credentials = {}
    
    if "gTTS" in tts_engine_name:
        engine_type = "gtts"
    elif "pyttsx3" in tts_engine_name:
        engine_type = "pyttsx3"
    elif "Lahajati" in tts_engine_name:
        engine_type = "lahajati"
        api_key = st.session_state.get('lahajati_api_key') or os.getenv('LAHAJATI_API_KEY')
        voice_id = st.session_state.get('lahajati_voice_id') or os.getenv('LAHAJATI_VOICE_ID')
        
        import logging
        logging.info(f"DEBUG: Lahajati - API Key: {'موجود' if api_key else 'غير موجود'}, Voice ID: {voice_id if voice_id else 'غير موجود'}")
        
        if voice_id:
            credentials['voice_id'] = voice_id
    elif "ElevenLabs" in tts_engine_name:
        engine_type = "elevenlabs"
        api_key = os.getenv('ELEVENLABS_API_KEY')
    elif "Azure" in tts_engine_name:
        engine_type = "azure"
        api_key = os.getenv('AZURE_SPEECH_KEY')
        credentials['azure_region'] = os.getenv('AZURE_REGION', 'eastus')
    elif "AWS Polly" in tts_engine_name:
        engine_type = "polly"
        credentials['aws_access_key'] = os.getenv('AWS_ACCESS_KEY_ID')
        credentials['aws_secret_key'] = os.getenv('AWS_SECRET_ACCESS_KEY')
        credentials['aws_region'] = os.getenv('AWS_REGION', 'us-east-1')
    else:
        engine_type = "gtts"
    
    return engine_type, api_key, credentials

def convert_to_speech(subtitles, file_name, tts_engine, speech_rate, output_format, audio_quality, pause_duration, handle_punctuation, add_tashkeel=False):
    """تحويل الترجمات إلى كلام"""
    
    # شريط التقدم
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # إعداد محرك TTS
        engine_type, api_key, credentials = get_engine_type_and_key(tts_engine)
        tts = TTSEngine(engine_type, speech_rate, api_key, credentials)
        
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
