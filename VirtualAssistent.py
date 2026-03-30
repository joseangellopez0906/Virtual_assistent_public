import os
import subprocess
import speech_recognition as sr
import google.generativeai as genai

# CONFIGURACIÓN STARK - API KEY INTEGRADA
GEMINI_KEY = "AIzaSyDmu10Ulevj_quI3m6iiGaml0A_0mhOrCc"

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash', 
    system_instruction="Eres Jarvis. Responde breve, técnico y deletrea números (ej. 'sesenta y cinco mil'). Sin emojis.")

def jarvis_talk(text):
    print(f"Jarvis: {text}")
    clean_text = text.replace('"', '').replace('\n', ' ')
    
    # 1. Piper genera el audio crudo
    cmd_piper = f'echo "{clean_text}" | ./piper --model es_ES-jarvis.onnx --output_file tmp.wav'
    subprocess.run(cmd_piper, shell=True, check=True)
    
    # 2. SOX aplica el 'Efecto Stark' (Eco metálico + Compresión)
    # Ajustamos para que suene pro en tus videos
    cmd_sox = "sox tmp.wav response.wav overdrive 10 echo 0.8 0.88 60 0.4"
    subprocess.run(cmd_sox, shell=True)
    
    # 3. Reproducir (aplay para Linux, cambia según tu OS)
    subprocess.run("aplay response.wav", shell=True)

def main():
    # Inicializamos el reconocedor de voz de Google (gratuito)
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("🚀 Sistemas Online. Di 'Jarvis' seguido de tu orden...")

    with mic as source:
        # Ajuste de ruido ambiental automático
        recognizer.adjust_for_ambient_noise(source, duration=1)
        
        while True:
            try:
                print("👂 Escuchando...")
                audio = recognizer.listen(source, timeout=None, phrase_time_limit=5)
                
                # Convertimos voz a texto
                user_text = recognizer.recognize_google(audio, language="es-MX").lower()
                print(f"Tú: {user_text}")

                # Si detecta la palabra clave "Jarvis"
                if "jarvis" in user_text:
                    prompt = user_text.replace("jarvis", "").strip()
                    
                    if not prompt:
                        response_text = "Dígame, señor Ángel. Estoy a su servicio."
                    else:
                        # Gemini genera la respuesta
                        gemini_res = model.generate_content(prompt)
                        response_text = gemini_res.text

                    # Piper + Sox hablan
                    jarvis_talk(response_text)

            except sr.UnknownValueError:
                # No entendió lo que dijiste, no pasa nada
                continue
            except sr.RequestError as e:
                print(f"Error de conexión con el servicio de voz: {e}")
                break
            except Exception as e:
                print(f"Error inesperado: {e}")
                continue

if __name__ == "__main__":
    main()