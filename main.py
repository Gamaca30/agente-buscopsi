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

def detectar_filtros(mensaje):
    mensaje = mensaje.lower()
    ubicaciones = ["aguascalientes", "baja california", "chiapas", "cdmx", "monterrey", "puebla", "yucatán", "jalisco"]
    idiomas = ["inglés", "ingles", "alemán", "aleman", "español"]

    ubicacion_detectada = next((u for u in ubicaciones if u in mensaje), None)
    idioma_detectado = next((i for i in idiomas if i in mensaje), None)
    return ubicacion_detectada, idioma_detectado

@app.route("/")
def index():
    return "Agente BuscoPsi listo."

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    mensaje = data.get("mensaje", "").lower()

    genero = "mujer" if "mujer" in mensaje else "hombre" if "hombre" in mensaje else "cualquiera"
    ubicacion_detectada, idioma_detectado = detectar_filtros(mensaje)
    filtros_activos = ubicacion_detectada or idioma_detectado

    try:
        url = API_TERAPEUTAS if filtros_activos else API_VERIFICADOS
        terapeutas = requests.get(url).json()

        print("Ubicación detectada:", ubicacion_detectada)
        print("Idioma detectado:", idioma_detectado)
        print("Se usó API:", url)
        print("Total terapeutas obtenidos:", len(terapeutas))

        grupo = terapeutas
        if genero != "cualquiera":
            grupo = [t for t in grupo if t.get("genero", "").lower() == genero]

        if ubicacion_detectada:
            grupo = [t for t in grupo if ubicacion_detectada.lower() in str(t.get("ubicacion", "")).lower()]
        
        if idioma_detectado:
            grupo = [t for t in grupo if idioma_detectado.lower() in str(t.get("idioma", "")).lower()]

        print("Total tras filtros aplicados:", len(grupo))

        if not grupo:
            return jsonify({"respuesta": "No encontré profesionales que cumplan con esos criterios por ahora."})

        cache = cache_mujeres if genero == "mujer" else cache_hombres if genero == "hombre" else cache_hombres + cache_mujeres
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

        return jsonify({"respuesta": f"Te recomiendo a {elegido['nombre']}: {elegido['link']}"})

    except Exception as e:
        return jsonify({"respuesta": f"Ups, hubo un error al buscar un profesional. ({str(e)})"})

    # GPT fallback
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
