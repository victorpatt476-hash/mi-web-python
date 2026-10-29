from flask import Flask, render_template_string

app = Flask(__name__)

# Página principal
@app.route("/")
def home():
    return """
    <html>
        <head><title>Mi Web con Python</title></head>
        <body style="font-family: Arial; text-align: center; margin-top: 50px;">
            <h1>¡Hola desde mi propio servidor de Python! 🚀</h1>
            <p>Este servidor corre con Flask y está listo para la acción.</p>
            <a href="/api/estado">Ver Estado de la API</a>
        </body>
    </html>
    """

# Una ruta de API que devuelve JSON (ideal para tus pruebas con bots)
@app.route("/api/estado")
def estado():
    return {"status": "online", "servidor": "Flask + Render", "base_datos": "Pendiente de conectar"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
