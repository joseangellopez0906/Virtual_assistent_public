import tkinter as tk
from tkinter import scrolledtext
import threading
import speech_recognition as sr
import google.generativeai as genai
import pygame
import time
import os
import asyncio
import edge_tts
import torch
import functools
import shutil
from dotenv import load_dotenv

# Carga las variables desde el archivo .env
load_dotenv()

# ==========================================
# PARCHE DE SEGURIDAD PYTORCH 2.6+
# ==========================================
torch.load = functools.partial(torch.load, weights_only=False)
try:
    from fairseq.data.dictionary import Dictionary
    torch.serialization.add_safe_globals([Dictionary])
except Exception:
    pass

# ==========================================
# CONFIGURACIÓN TÉCNICA (STARK INDUSTRIES)
# ==========================================
GEMINI_KEY = os.getenv("GEMINI_KEY")

if not GEMINI_KEY:
    print("❌ ERROR: No se encontró la GEMINI_KEY en el archivo .env")
    #print("Gemini Key: ", GEMINI_KEY)
    exit()

MODEL_PATH = "Jarvis_Proyect_200e_4600s.pth" 
INDEX_PATH = "Jarvis_Proyect.index"

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel(
    model_name='gemini-2.5-flash', 
    system_instruction=(
        "Eres Jarvis. Responde breve, técnico y deletrea números grandes. "
        "Tu misión es ayudar a Angel a resolver sus dudas y problemas. "
        "Ubicación: Algun lugar en el mundo, G, México. Sin emojis."
    )
)

# RVC en CPU para evitar errores de memoria en Zapopan
from rvc_python.infer import RVCInference
rvc_engine = RVCInference(device="cpu") 
pygame.mixer.init()

# ==========================================
# MOTOR DE VOZ (EDGE-TTS + RVC)
# ==========================================

def speak(text, update_status_func):
    if not text: return
    update_status_func("Jarvis: Ajustando frecuencia Stark...")
    
    if pygame.mixer.get_init():
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
    
    try:
        # 1. Base Neuronal con Edge-TTS
        # Forzamos una tasa de muestreo limpia
        communicate = edge_tts.Communicate(text, "es-MX-JorgeNeural", pitch="-10Hz")
        asyncio.run(communicate.save("base_temp.wav"))
        
        # 2. Transformación RVC con Seguro de Vida
        try:
            rvc_engine.load_model(MODEL_PATH)
            # El error 'tuple' suele ser porque rvc-python no encuentra el hubert_base.pt
            # o el audio de entrada está corrupto/abierto.
            rvc_engine.infer_file("base_temp.wav", "jarvis_output.wav")
            audio_final = "jarvis_output.wav"
        except Exception as rvc_err:
            # Si el tensor falla, no nos detenemos. El revenue no espera.
            print(f"Fallo técnico en RVC: {rvc_err}")
            print("Aplicando bypass: Usando base neuronal de alta calidad.")
            audio_final = "base_temp.wav"
        
        # 3. Reproducción
        pygame.mixer.music.load(audio_final)
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
            
    except Exception as e:
        print(f"Error crítico de audio: {e}")
        update_status_func("Sistema de audio en mantenimiento.")
async def saludo_inicial(app_instance):
    texto = (
        "Buenos Días Señor Angel. Su canal de youtube ha tenido un buen crecimiento. "
        "Vayan a inventores punto digital si les interesa una página web. "
        "Quedo a sus órdenes, señor."
    )
    app_instance.update_status("EJECUTANDO PROTOCOLO DE INICIO...")
    app_instance.update_chat(f"Jarvis: {texto}")
    
    communicate = edge_tts.Communicate(texto, "es-MX-JorgeNeural", pitch="-10Hz")
    await communicate.save("base_temp.wav")
    
    try:
        rvc_engine.load_model(MODEL_PATH)
        rvc_engine.infer_file("base_temp.wav", "saludo_jarvis.wav")
        audio_final = "saludo_jarvis.wav"
    except:
        audio_final = "base_temp.wav"

    pygame.mixer.music.load(audio_final)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.1)
    app_instance.update_status("SISTEMAS ONLINE. ESCUCHANDO...")

# ==========================================
# LÓGICA DE INTELIGENCIA Y ESCUCHA
# ==========================================

def get_gemini_response(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error en el cerebro: {e}"

def bg_listening_loop(app_instance):
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=2)

    while True:
        with mic as source:
            try:
                audio = recognizer.listen(source, timeout=3, phrase_time_limit=3)
                user_text = recognizer.recognize_google(audio, language="es-MX").lower()
                
                if "jarvis" in user_text:
                    app_instance.update_status("⚡ ACTIVADO. Dígame...")
                    audio_prompt = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    prompt_text = recognizer.recognize_google(audio_prompt, language="es-MX")
                    
                    app_instance.update_chat(f"Tú: {prompt_text}")
                    response = get_gemini_response(prompt_text)
                    app_instance.update_chat(f"Jarvis: {response}")
                    speak(response, app_instance.update_status)
                    app_instance.update_status("Escuchando...")
                    
            except:
                continue

# ==========================================
# INTERFAZ GRÁFICA (GUI)
# ==========================================

class JarvisApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SISTEMA JARVIS v1.0 - RVC LOCAL")
        self.root.geometry("600x500")
        self.root.configure(bg="#0a0a14")

        self.chat_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, bg="#0d0d1a", fg="#00ffff", font=("Consolas", 11))
        self.chat_area.pack(pady=10, padx=10, expand=True, fill=tk.BOTH)
        self.chat_area.config(state=tk.DISABLED)

        self.status_var = tk.StringVar()
        self.status_label = tk.Label(root, textvariable=self.status_var, fg="#ff0000", bg="#0a0a14", font=("Consolas", 12, "bold"))
        self.status_label.pack(pady=5)

        self.listen_thread = threading.Thread(target=bg_listening_loop, args=(self,), daemon=True)
        self.listen_thread.start()

    def update_chat(self, text):
        self.root.after(0, lambda: self._update_chat_safe(text))

    def _update_chat_safe(self, text):
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.insert(tk.END, text + "\n")
        self.chat_area.yview(tk.END)
        self.chat_area.config(state=tk.DISABLED)

    def update_status(self, text):
        self.root.after(0, lambda: self.status_var.set(f"STATUS: {text.upper()}"))

if __name__ == "__main__":
    root = tk.Tk()
    app = JarvisApp(root)
    # Ejecuta el saludo inicial después de 1 segundo
    root.after(1000, lambda: asyncio.run(saludo_inicial(app)))
    root.mainloop()