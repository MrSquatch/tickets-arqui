import os, json, time
import pika, requests

RABBIT_URL = os.environ["RABBIT_URL"]
API_URL = os.environ["API_URL"]
SERVICE_TOKEN = os.environ["SERVICE_TOKEN"]
NOTIFY_URL = os.environ.get("NOTIFY_URL", "")
NOTIFY_TOKEN = os.environ.get("NOTIFY_TOKEN", "")
COLA = "ticket.registrado"

def enviar_correo(ticket):
    if not NOTIFY_URL:  # modo simulado
        print(f"[SIMULADO] correo a soporte por ticket #{ticket['id']}")
        return True
    r = requests.post(NOTIFY_URL, json=ticket, timeout=15,
                      headers={"Authorization": f"Bearer {NOTIFY_TOKEN}"})
    return r.status_code == 200

def actualizar_estado(id_, estado):
    requests.patch(f"{API_URL}/tickets/{id_}/estado", json={"estado": estado}, timeout=10,
                   headers={"X-Service-Token": SERVICE_TOKEN})

def procesar(ch, method, props, body):
    ticket = json.loads(body)
    ok = False
    try:
        ok = enviar_correo(ticket)
    except Exception as e:
        print("error al enviar:", e)
    if ok:
        actualizar_estado(ticket["id"], "Notificado")
        ch.basic_ack(method.delivery_tag)
    else:
        if not method.redelivered:           # solo la primera vez
            actualizar_estado(ticket["id"], "Fallo de envío")
        print("fallo, se reintenta en 10 s")
        time.sleep(10)
        ch.basic_nack(method.delivery_tag, requeue=True)  # el mensaje NO se pierde

while True:  # reintenta conectar hasta que RabbitMQ esté listo
    try:
        con = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
        ch = con.channel()
        ch.queue_declare(queue=COLA, durable=True)
        ch.basic_qos(prefetch_count=1)
        ch.basic_consume(queue=COLA, on_message_callback=procesar)
        print("Esperando mensajes...")
        ch.start_consuming()
    except Exception as e:
        print("sin conexión, reintento:", e)
        time.sleep(3)
