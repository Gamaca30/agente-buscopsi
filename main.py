from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import os
import requests
import random

# Inicializar cliente de OpenAI (versión nueva)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
CORS(app)

API_TERAPEUTAS = "https://buscopsi.mx/wp-json/buscopsi/v1/terapeutas"
API_VERIFICADOS = "https://buscopsi.mx/wp-json/buscopsi/v1/verificados"

# Lista para evitar repetir terapeutas recomendados
recomendados_cache = []

@app.route("/")
def index():
    return "Agente BuscoPsi listo."

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    mensaje = data.get("mensaje", "").lower()

    # Si el mensaje pide un terapeuta, se usa la API de verificados
    if "terapeuta" in mensaje or "alguien" in mensaje:
        global recomendados_cache
        terapeutas = requests.get(API_VERIFICADOS).json()

        if not terapeutas:
            return jsonify({"respuesta": "No se encontraron terapeutas por ahora."})

        if len(recomendados_cache) == len(terapeutas):
            recomendados_cache = []

        disponibles = [t for t in terapeutas if t["link"] not in recomendados_cache]
        elegido = random.choice(disponibles)
        recomendados_cache.append(elegido["link"])

        return jsonify({
            "respuesta": f"Te recomiendo a {elegido['nombre']}: {elegido['link']}"
        })

    # Si no es consulta de terapeuta, responde con OpenAI
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Sos un asistente de BuscoPsi, ayudás a elegir profesionales."},
                {"role": "user", "content": mensaje}
            ]
        )
        texto = response.choices[0].message.content.strip()
        return jsonify({"respuesta": texto})
    except Exception as e:
        return jsonify({"respuesta": f"Ups, hubo un error. ({str(e)})"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
