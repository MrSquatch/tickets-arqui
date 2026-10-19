# Tickets FISI

Registro y notificación de incidencias técnicas en laboratorios de la FISI.
Proyecto del curso de **Arquitectura de Software**.

**Integrantes:**
- Lavaud Guevara, Jean Alessandro
- Sandoval Falcon, David Brian

## ¿Qué hace?

Un docente reporta una falla (pantalla interactiva o proyector) desde una página web, confirma un resumen y el sistema registra un **ticket** y avisa por correo a soporte técnico. La atención y resolución de la incidencia queda fuera del alcance.

## Arquitectura

Es una **nube híbrida**: los servicios propios corren en contenedores (Docker Compose) sobre un servidor Proxmox de la facultad, y se consumen servicios de nube pública.

- **Local (Docker Compose):**
  - Frontend (Nginx)
  - API (FastAPI)
  - Cola de mensajes (RabbitMQ)
  - Servicio de notificaciones (Python)
- **Nube pública:**
  - Supabase (PostgreSQL + autenticación)
  - Vercel Functions (función serverless)
  - Resend (envío de correo)

Desde el servidor solo salen conexiones hacia internet; no se expone ningún puerto.

## Flujo resumido

1. El docente inicia sesión contra Supabase y envía el reporte a la API.
2. La API guarda el ticket en Supabase como `Registrado`.
3. La API deja un aviso en RabbitMQ, sin esperar el correo.
4. El servicio de notificaciones toma el aviso y llama a la función serverless, que envía el correo con Resend.
5. Si el envío funciona, el servicio pide a la API actualizar el estado a `Notificado`.
6. Si el envío falla, el ticket queda en `Fallo de envío` y el aviso se reintenta.

## Retos del parcial

| Reto | Solución | Detalle |
|---|---|---|
| 1. Middleware | RabbitMQ | Cola entre la API y las notificaciones: desacopla y no pierde avisos si algo falla. |
| 2. Servicios web / API | FastAPI | `POST /tickets` y `PATCH /tickets/{id}/estado`; es la única que escribe en la base de datos. |
| 3. Cloud | Nube híbrida: Proxmox (IaaS privado) + Supabase + Vercel | Contenedores en un servidor de la facultad, más servicios de nube pública. |
| 4. Microservicio | Servicio de notificaciones | Contenedor independiente: consume la cola, reintenta y actualiza el estado vía la API. |
| 5. Serverless | Vercel Functions | Función en Python, sin estado, que envía el correo con Resend. |
