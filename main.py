from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import os
import requests
import random

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
CORS(app)

API_VERIFICADOS = "https://buscopsi.mx/wp-json/buscopsi/v1/verificados"
API_TERAPEUTAS = "https://buscopsi.mx/wp-json/buscopsi/v1/terapeutas"

cache_hombres = []
cache_mujeres = []

@app.route("/")
def index():
    return "Agente BuscoPsi listo."

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    mensaje = data.get("mensaje", "").lower()

    genero = "mujer" if "mujer" in mensaje else "hombre" if "hombre" in mensaje else "cualquiera"

    # Detectar si el usuario pidió filtros específicos
    filtros_activos = any(palabra in mensaje for palabra in [
        "zona", "ubicación", "ubicacion", "idioma", "obra social", "especialidad", "modalidad", "atención", "atencion"
    ])

    url_api = API_TERAPEUTAS if filtros_activos else API_VERIFICADOS

    if "terapeuta" in mensaje or "alguien" in mensaje or "psicologo" in mensaje or "recomendás" in mensaje:
        try:
            terapeutas = requests.get(url_api).json()
            if not terapeutas:
                return jsonify({"respuesta": "No se encontraron terapeutas disponibles por ahora."})

            if genero == "mujer":
                grupo = [t for t in terapeutas if t.get("genero", "").lower() == "mujer"]
                cache = cache_mujeres
            elif genero == "hombre":
                grupo = [t for t in terapeutas if t.get("genero", "").lower() == "hombre"]
                cache = cache_hombres
            else:
                grupo = terapeutas
                cache = cache_hombres + cache_mujeres

            usados_links = [t["link"] for t in cache]
            disponibles = [t for t in grupo if t["link"] not in usados_links]

            if not disponibles:
                if genero == "mujer":
                    cache_mujeres.clear()
                elif genero == "hombre":
                    cache_hombres.clear()
                disponibles = grupo

            elegido = random.choice(disponibles)
            if genero == "mujer":
                cache_mujeres.append(elegido)
            elif genero == "hombre":
                cache_hombres.append(elegido)

            return jsonify({
                "respuesta": f"Te recomiendo a {elegido['nombre']}: {elegido['link']}"
            })

        except Exception as e:
            return jsonify({"respuesta": f"Ups, hubo un error al buscar un profesional. ({str(e)})"})

    # Si no es consulta directa, responde GPT
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Sos Pablo, el asistente oficial de BuscoPsi.mx. "
                        "Tu única función es ayudar a encontrar psicólogos de la plataforma BuscoPsi. "
                        "Nunca sugieras otros sitios como Doctoralia, ni inventes profesionales. "
                        "Si no encontrás un profesional con los filtros pedidos, respondé con respeto diciendo que no hay disponibles por ahora. "
                        "Si piden información sobre costos de sesiones, respondé que depende de cada profesional y que no se maneja esa información directamente. "
                        "Si un profesional está interesado en sumarse, explicale que puede registrarse en https://buscopsi.com/registro/ y ver precios en https://buscopsi.com/oferta/. "
                        "Nunca aceptes terapeutas sin matrícula. Respondé con claridad, calidez y profesionalismo."
                    )
                },
                {"role": "user", "content": mensaje}
            ]
        )
        texto = response.choices[0].message.content.strip()
        return jsonify({"respuesta": texto})
    except Exception as e:
        return jsonify({"respuesta": f"Ups, hubo un error. ({str(e)})"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
