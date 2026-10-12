import os, json
import pika, psycopg2, requests
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI()
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
DATABASE_URL = os.environ["DATABASE_URL"]
RABBIT_URL = os.environ["RABBIT_URL"]
SERVICE_TOKEN = os.environ["SERVICE_TOKEN"]
COLA = "ticket.registrado"

# Reglas de negocio: transiciones de estado permitidas
TRANSICIONES = {
    "Registrado": ["Notificado", "Fallo de envío"],
    "Fallo de envío": ["Notificado"],
}

class TicketIn(BaseModel):
    pabellon: str
    laboratorio: str
    categoria: str
    detalle: str

class EstadoIn(BaseModel):
    estado: str

def sql(consulta, params=(), devolver=False):
    con = psycopg2.connect(DATABASE_URL)
    try:
        with con, con.cursor() as cur:
            cur.execute(consulta, params)
            return cur.fetchone() if devolver else None
    finally:
        con.close()

def usuario_actual(authorization):
    """Valida la sesión preguntándole a Supabase Auth quién es el dueño del token."""
    if not authorization:
        raise HTTPException(401, "Falta token")
    r = requests.get(f"{SUPABASE_URL}/auth/v1/user", timeout=10,
                     headers={"Authorization": authorization, "apikey": SUPABASE_ANON_KEY})
    if r.status_code != 200:
        raise HTTPException(401, "Sesión inválida")
    return r.json()["email"]

def publicar(mensaje):
    """Deja el mensaje en la cola (middleware) y se desentiende."""
    con = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
    ch = con.channel()
    ch.queue_declare(queue=COLA, durable=True)
    ch.basic_publish(exchange="", routing_key=COLA, body=json.dumps(mensaje),
                     properties=pika.BasicProperties(delivery_mode=2))
    con.close()

@app.post("/tickets", status_code=201)
def crear_ticket(t: TicketIn, authorization: str = Header(None)):
    docente = usuario_actual(authorization)
    if t.categoria not in ("pantalla", "proyector"):
        raise HTTPException(400, "Categoría inválida")
    (id_,) = sql(
        "insert into tickets (docente,pabellon,laboratorio,categoria,detalle) "
        "values (%s,%s,%s,%s,%s) returning id",
        (docente, t.pabellon, t.laboratorio, t.categoria, t.detalle), devolver=True)
    publicar({"id": id_, "docente": docente, **t.model_dump()})
    return {"id": id_, "estado": "Registrado"}

@app.patch("/tickets/{id_}/estado")
def cambiar_estado(id_: int, e: EstadoIn, x_service_token: str = Header(None)):
    if x_service_token != SERVICE_TOKEN:
        raise HTTPException(403, "No autorizado")
    fila = sql("select estado from tickets where id=%s", (id_,), devolver=True)
    if not fila:
        raise HTTPException(404, "Ticket no existe")
    if e.estado not in TRANSICIONES.get(fila[0], []):
        raise HTTPException(400, f"Transición inválida: {fila[0]} -> {e.estado}")
    sql("update tickets set estado=%s where id=%s", (e.estado, id_))
    return {"id": id_, "estado": e.estado}
