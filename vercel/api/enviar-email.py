from http.server import BaseHTTPRequestHandler
from datetime import datetime, timezone, timedelta
from html import escape
import json, os, urllib.request

CATEGORIAS = {"pantalla": "Pantalla interactiva", "proyector": "Proyector"}
PABELLONES = {"Nuevo pabellón": "NP", "Antiguo pabellón": "AP"}


def armar_correo(t):
    """Devuelve asunto, texto plano y HTML a partir de los datos del ticket."""
    categoria = CATEGORIAS.get(t["categoria"], t["categoria"])
    pabellon = PABELLONES.get(t["pabellon"], t["pabellon"])
    hora = datetime.now(timezone(timedelta(hours=-5))).strftime("%d/%m/%Y %H:%M")  # hora de Lima
    filas = [("Docente", t["docente"]), ("Pabellón", t["pabellon"]),
             ("Laboratorio", t["laboratorio"]), ("Categoría", categoria), ("Registrado", hora)]

    asunto = f"[Ticket #{t['id']}] {categoria} - Lab {t['laboratorio']}{pabellon}"

    texto = (f"Nueva incidencia #{t['id']}\n\n"
             + "\n".join(f"{k}: {v}" for k, v in filas)
             + f"\n\nDescripción de la falla:\n{t['detalle']}\n")

    # escape() evita que lo escrito por el docente rompa el HTML
    tabla = "".join(
        f'<tr><td style="padding:8px 12px;color:#6b7280;width:120px">{k}</td>'
        f'<td style="padding:8px 12px;font-weight:600">{escape(str(v))}</td></tr>'
        for k, v in filas)
    detalle_html = escape(t["detalle"]).replace("\n", "<br>")

    html = f"""
<div style="font-family:Arial,Helvetica,sans-serif;background:#f3f4f6;padding:24px">
  <div style="max-width:560px;margin:auto;background:#ffffff;border-radius:8px;overflow:hidden">
    <div style="background:#1f3a5f;color:#ffffff;padding:18px 24px">
      <div style="font-size:12px;opacity:.8">FISI - Soporte técnico</div>
      <div style="font-size:20px;font-weight:bold">Nueva incidencia #{t['id']}</div>
    </div>
    <div style="padding:20px 24px">
      <table style="width:100%;border-collapse:collapse;font-size:14px">{tabla}</table>
      <p style="margin:18px 0 6px;color:#6b7280;font-size:13px">Descripción de la falla</p>
      <div style="background:#f9fafb;border-left:4px solid #2e6da4;padding:12px 14px;font-size:14px">{detalle_html}</div>
    </div>
    <div style="padding:12px 24px;background:#f9fafb;color:#9ca3af;font-size:12px">
      Mensaje automático del sistema de registro de tickets.
    </div>
  </div>
</div>"""
    return asunto, texto, html


class handler(BaseHTTPRequestHandler):
    def _responder(self, codigo, cuerpo):
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(cuerpo).encode())

    def do_POST(self):
        if self.headers.get("Authorization") != f"Bearer {os.environ['NOTIFY_TOKEN']}":
            return self._responder(401, {"error": "no autorizado"})
        t = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        asunto, texto, html = armar_correo(t)
        correo = {
            "from": "Tickets FISI <onboarding@resend.dev>",
            "to": [os.environ["SOPORTE_EMAIL"]],
            "subject": asunto,
            "text": texto,
            "html": html,
        }
        req = urllib.request.Request("https://api.resend.com/emails",
            data=json.dumps(correo).encode(), method="POST",
            headers={"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}",
                     "Content-Type": "application/json", "User-Agent": "tickets-fisi/1.0"})
        try:
            urllib.request.urlopen(req, timeout=10)
            self._responder(200, {"ok": True})
        except Exception as e:
            self._responder(502, {"error": str(e)})
