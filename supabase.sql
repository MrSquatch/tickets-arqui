-- Ejecutar en Supabase > SQL Editor
create table tickets (
  id         bigserial primary key,
  docente    text not null,
  pabellon   text not null,
  laboratorio text not null,
  categoria  text not null check (categoria in ('pantalla','proyector')),
  detalle    text not null,
  estado     text not null default 'Registrado',
  creado     timestamptz not null default now()
);
-- Bloquea la API REST automática de Supabase: solo nuestra API toca los datos
alter table tickets enable row level security;
