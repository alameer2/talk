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

try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

try:
    from elevenlabs import generate, set_api_key, Voice
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False

try:
    import boto3
    AWS_POLLY_AVAILABLE = True
except ImportError:
    AWS_POLLY_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

class TTSEngine:
    """محرك تحويل النص إلى كلام مع دعم متعدد المحركات"""
    
    def __init__(self, engine_type: str = "gtts", speech_rate: float = 1.0, api_key: str = None, credentials: dict = None):
        """
        تهيئة محرك TTS
        
        Args:
            engine_type (str): نوع المحرك ("gtts", "pyttsx3", "azure", "elevenlabs", "polly", "lahajati")
            speech_rate (float): سرعة الكلام (1.0 = عادي)
            api_key (str): مفتاح API للمحركات السحابية (اختياري لبعض المحركات)
            credentials (dict): معلومات إضافية للمحركات (مثل region للـ Azure وAWS، voice_id لـ Lahajati)
        """
        self.engine_type = engine_type.lower()
        self.speech_rate = speech_rate
        self.api_key = api_key
        self.credentials = credentials or {}
        self.logger = logging.getLogger(__name__)
        
        # تهيئة محرك pyttsx3 إذا كان مطلوب
        if self.engine_type == "pyttsx3":
            self._init_pyttsx3()
        elif self.engine_type == "elevenlabs" and api_key:
            self._init_elevenlabs()
    
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
        elif self.engine_type == "azure":
            return self._azure_convert(text, output_file)
        elif self.engine_type == "elevenlabs":
            return self._elevenlabs_convert(text, output_file)
        elif self.engine_type == "polly":
            return self._polly_convert(text, output_file)
        elif self.engine_type == "lahajati":
            return self._lahajati_convert(text, output_file)
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
            
            # تحسين معاملات gTTS للعربية
            # استخدام slow=True عندما تكون السرعة أقل من 1.0
            # هذا يحسن دقة النطق للنصوص العربية المشكّلة
            use_slow = self.speech_rate < 1.0
            
            # إنشاء كائن gTTS
            tts = gTTS(
                text=text, 
                lang='ar',
                slow=use_slow,
                lang_check=True
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
            'pyttsx3_available': PYTTSX3_AVAILABLE,
            'azure_available': AZURE_AVAILABLE,
            'elevenlabs_available': ELEVENLABS_AVAILABLE,
            'polly_available': AWS_POLLY_AVAILABLE
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
    
    def _init_elevenlabs(self):
        """تهيئة محرك ElevenLabs"""
        try:
            if not ELEVENLABS_AVAILABLE:
                raise ImportError("ElevenLabs غير متاح")
            
            if self.api_key:
                set_api_key(self.api_key)
                self.logger.info("تم تهيئة ElevenLabs بنجاح")
            else:
                self.logger.error("يجب توفير API Key لـ ElevenLabs")
                
        except Exception as e:
            self.logger.error(f"خطأ في تهيئة ElevenLabs: {str(e)}")
    
    def _azure_convert(self, text: str, output_file: str) -> Optional[str]:
        """تحويل النص باستخدام Azure Cognitive Services"""
        try:
            if not AZURE_AVAILABLE:
                self.logger.error("Azure SDK غير متاح. قم بتثبيت: pip install azure-cognitiveservices-speech")
                return None
            
            if not self.api_key:
                self.logger.error("يجب توفير AZURE_SPEECH_KEY")
                return None
            
            azure_region = self.credentials.get('azure_region', os.getenv('AZURE_REGION', 'eastus'))
            
            # إعداد تكوين Azure
            speech_config = speechsdk.SpeechConfig(
                subscription=self.api_key,
                region=azure_region
            )
            
            # اختيار صوت عربي
            speech_config.speech_synthesis_voice_name = "ar-SA-ZariyahNeural"
            speech_config.speech_synthesis_output_format = speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
            
            # إنشاء مُركِّب الكلام
            audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
            
            # تحويل النص
            result = synthesizer.speak_text_async(text).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                self.logger.info(f"تم إنشاء ملف صوتي بـ Azure: {output_file}")
                return output_file
            else:
                self.logger.error(f"فشل Azure TTS: {result.reason}")
                return None
                
        except Exception as e:
            self.logger.error(f"خطأ في Azure TTS: {str(e)}")
            return None
    
    def _elevenlabs_convert(self, text: str, output_file: str) -> Optional[str]:
        """تحويل النص باستخدام ElevenLabs"""
        try:
            if not ELEVENLABS_AVAILABLE:
                self.logger.error("ElevenLabs غير متاح")
                return None
            
            if not self.api_key:
                self.logger.error("يجب توفير API Key لـ ElevenLabs")
                return None
            
            # إنشاء الصوت
            audio = generate(
                text=text,
                voice="Rachel",
                model="eleven_multilingual_v2"
            )
            
            # حفظ الملف
            with open(output_file, 'wb') as f:
                f.write(audio)
            
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                self.logger.info(f"تم إنشاء ملف صوتي بـ ElevenLabs: {output_file}")
                return output_file
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"خطأ في ElevenLabs: {str(e)}")
            return None
    
    def _polly_convert(self, text: str, output_file: str) -> Optional[str]:
        """تحويل النص باستخدام AWS Polly"""
        try:
            if not AWS_POLLY_AVAILABLE:
                self.logger.error("boto3 غير متاح. قم بتثبيت: pip install boto3")
                return None
            
            aws_access = self.credentials.get('aws_access_key', os.getenv('AWS_ACCESS_KEY_ID'))
            aws_secret = self.credentials.get('aws_secret_key', os.getenv('AWS_SECRET_ACCESS_KEY'))
            aws_region = self.credentials.get('aws_region', os.getenv('AWS_REGION', 'us-east-1'))
            
            if not aws_access or not aws_secret:
                self.logger.error("يجب توفير AWS Access Key و Secret Key")
                return None
            
            # إنشاء عميل Polly
            polly_client = boto3.client(
                'polly',
                aws_access_key_id=aws_access,
                aws_secret_access_key=aws_secret,
                region_name=aws_region
            )
            
            # تحويل النص إلى كلام
            response = polly_client.synthesize_speech(
                Text=text,
                OutputFormat='mp3',
                VoiceId='Zeina',
                LanguageCode='arb'
            )
            
            # حفظ الملف
            if 'AudioStream' in response:
                with open(output_file, 'wb') as f:
                    f.write(response['AudioStream'].read())
                
                self.logger.info(f"تم إنشاء ملف صوتي بـ AWS Polly: {output_file}")
                return output_file
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"خطأ في AWS Polly: {str(e)}")
            return None
    
    def _lahajati_convert(self, text: str, output_file: str) -> Optional[str]:
        """تحويل النص باستخدام Lahajati AI (108 لهجة عربية)"""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                if not REQUESTS_AVAILABLE:
                    self.logger.error("requests library غير متاح. قم بتثبيت: pip install requests")
                    return None
                
                if not self.api_key:
                    self.logger.error("❌ يجب توفير API Key لـ Lahajati. يمكنك الحصول عليه مجاناً (10k chars/month) من https://lahajati.ai/")
                    return None
                
                voice_id = self.credentials.get('voice_id', None)
                
                if not voice_id:
                    self.logger.error("❌ يجب اختيار صوت من القائمة أولاً. اذهب إلى إعدادات Lahajati في الشريط الجانبي واختر الصوت المناسب.")
                    return None
                
                # التحقق من وجود خيارات متقدمة
                dialect_id = self.credentials.get('dialect_id', None)
                performance_id = self.credentials.get('performance_id', None)
                custom_prompt = self.credentials.get('custom_prompt', None)
                
                use_advanced = dialect_id or performance_id or custom_prompt
                
                if use_advanced:
                    # استخدام absolute-control endpoint
                    api_url = 'https://lahajati.ai/api/v1/text-to-speech-absolute-control'
                    self.logger.info("🎛️ استخدام Absolute Control API للخيارات المتقدمة")
                else:
                    # استخدام pro endpoint العادي
                    api_url = 'https://lahajati.ai/api/v1/text-to-speech-pro'
                
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                    'Accept': 'audio/mpeg'
                }
                
                data = {
                    "text": text,
                    "id_voice": voice_id
                }
                
                if use_advanced:
                    # تحديد نوع التحكم
                    if custom_prompt:
                        data["control_mode"] = 1
                        data["custom_prompt_text"] = custom_prompt
                        self.logger.info(f"📝 استخدام نص مخصص: {custom_prompt[:50]}...")
                    else:
                        data["control_mode"] = 0
                        if dialect_id:
                            data["dialect_id"] = dialect_id
                            self.logger.info(f"🗣️ لهجة محددة: {dialect_id}")
                        if performance_id:
                            data["performance_id"] = performance_id
                            self.logger.info(f"🎭 نوع أداء: {performance_id}")
                else:
                    data["version"] = "lahajati_text_to_speech_pro_v1"
                
                self.logger.info(f"🔄 محاولة {attempt + 1}/{max_retries} - إرسال طلب إلى Lahajati API...")
                response = requests.post(api_url, headers=headers, json=data, stream=True, timeout=60)
                
                if response.status_code == 200:
                    with open(output_file, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                        self.logger.info(f"✅ تم إنشاء ملف صوتي بـ Lahajati: {output_file}")
                        return output_file
                    else:
                        self.logger.error("❌ الملف الناتج فارغ")
                        return None
                        
                elif response.status_code == 401:
                    self.logger.error("❌ خطأ 401: API Key غير صحيح أو منتهي الصلاحية. تأكد من API Key في https://lahajati.ai/")
                    return None
                    
                elif response.status_code == 403:
                    self.logger.error("❌ خطأ 403: تجاوزت حدود الاستخدام المجاني (10k حرف/شهر) أو ليس لديك صلاحية.")
                    return None
                    
                elif response.status_code == 422:
                    error_details = response.json() if response.headers.get('content-type') == 'application/json' else response.text
                    self.logger.error(f"❌ خطأ 422: بيانات غير صحيحة - {error_details}")
                    return None
                    
                elif response.status_code == 429:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        self.logger.warning(f"⏳ خطأ 429: طلبات كثيرة. انتظار {wait_time} ثانية...")
                        import time
                        time.sleep(wait_time)
                        continue
                    else:
                        self.logger.error("❌ خطأ 429: تجاوزت عدد الطلبات المسموح. حاول لاحقاً.")
                        return None
                        
                elif response.status_code >= 500:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        self.logger.warning(f"⚠️ خطأ {response.status_code}: مشكلة في السيرفر. إعادة المحاولة بعد {wait_time} ثانية...")
                        import time
                        time.sleep(wait_time)
                        continue
                    else:
                        self.logger.error(f"❌ خطأ {response.status_code}: مشكلة في سيرفر Lahajati. حاول لاحقاً.")
                        return None
                else:
                    self.logger.error(f"❌ خطأ {response.status_code}: {response.text}")
                    return None
                    
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    self.logger.warning(f"⏱️ انتهت مهلة الاتصال. محاولة {attempt + 2}/{max_retries}...")
                    import time
                    time.sleep(retry_delay)
                    continue
                else:
                    self.logger.error("❌ انتهت مهلة الاتصال بعد عدة محاولات. تحقق من اتصال الإنترنت.")
                    return None
                    
            except requests.exceptions.ConnectionError:
                if attempt < max_retries - 1:
                    self.logger.warning(f"🔌 خطأ في الاتصال. محاولة {attempt + 2}/{max_retries}...")
                    import time
                    time.sleep(retry_delay)
                    continue
                else:
                    self.logger.error("❌ فشل الاتصال بـ Lahajati API. تحقق من اتصال الإنترنت.")
                    return None
                    
            except Exception as e:
                self.logger.error(f"❌ خطأ غير متوقع في Lahajati: {str(e)}")
                return None
        
        return None
