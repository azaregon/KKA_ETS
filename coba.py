import io
import speech_recognition as sr
from pydub import AudioSegment



audio = AudioSegment.from_file("C:\\Users\\dumpt\\Documents\\Porjectssss\\tugas IF\\KKA\\Project ETS\\Main-App\\patient_condition_note\\7a1182da-f9df-4639-b107-a8e6cf32682d.webm", format="webm")

# Export to a BytesIO buffer (in memory, no file saved)
wav_io = io.BytesIO()
audio.export(wav_io, format="wav")
wav_io.seek(0)
# Inisialisasi recognizer
r = sr.Recognizer()

# Gunakan mikrofon sebagai sumber suara
with sr.AudioFile(wav_io) as source:
    print("Katakan sesuatu!")
    # Dengarkan audio dari mikrofon
    audio = r.record(source)  # read the entire file

try:
    # Konversi suara ke teks menggunakan Google Web Speech API
    text = r.recognize_google(audio, language='id-ID')
    print(f"Anda berkata: {text}")
except sr.UnknownValueError:
    print("Maaf, saya tidak mengerti apa yang Anda katakan.")
except sr.RequestError as e:
    print(f"Terjadi kesalahan saat meminta hasil dari layanan Google Speech Recognition; {e}")
