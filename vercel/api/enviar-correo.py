from http.server import BaseHTTPRequestHandler
import json, os, urllib.request

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
        correo = {
            "from": "onboarding@resend.dev",
            "to": [os.environ["SOPORTE_EMAIL"]],
            "subject": f"[Ticket #{t['id']}] {t['categoria']} - {t['laboratorio']}",
            "text": f"Docente: {t['docente']}\nPabellón: {t['pabellon']}\n"
                    f"Laboratorio: {t['laboratorio']}\nFalla: {t['detalle']}",
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
