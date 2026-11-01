import webview
from backend.api import Api

api = Api()

window = webview.create_window(
    "Gerador de Salas - ABC Aprendiz",
    "frontend/index.html",
    js_api=api
)

webview.start(debug=False)