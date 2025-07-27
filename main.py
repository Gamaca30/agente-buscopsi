from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os
import requests
import random

app = Flask(__name__)
CORS(app)

# Clave OpenAI desde variable de entorno
openai.api_key = os.getenv("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")

API_TERAPEUTAS = "https://buscopsi.mx/wp-json/buscopsi/v1/terapeutas"
API_VERIFICADOS = "https://buscopsi.mx/wp-json/buscopsi/v1/verificados"

# Memoria de IDs recomendados para no repetir
recomendados_cache = []

@app.route("/")
def index():
    return "Agente BuscoPsi listo."

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    mensaje = data.get("mensaje", "").lower()

    # Si el mensaje pide un terapeuta, usamos la API de verificados
    if "terapeuta" in mensaje or "alguien" in mensaje:
        global recomendados_cache
        terapeutas = requests.get(API_VERIFICADOS).json()

        if not terapeutas:
            return jsonify({"respuesta": "No se encontraron terapeutas por ahora."})

        if len(recomendados_cache) == len(terapeutas):
            recomendados_cache = []  # reiniciar si ya se recomendaron todos

        disponibles = [t for t in terapeutas if t["link"] not in recomendados_cache]
        elegido = random.choice(disponibles)
        recomendados_cache.append(elegido["link"])

        return jsonify({
            "respuesta": f"Te recomiendo a {elegido['nombre']}: {elegido['link']}"
        })

    # Si no pide terapeuta, responde con OpenAI
    respuesta = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Sos un asistente de BuscoPsi, ayudás a elegir profesionales."},
            {"role": "user", "content": mensaje}
        ]
    )
    texto = respuesta.choices[0].message.content.strip()
    return jsonify({"respuesta": texto})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
