# Somos Sensoriales · Sistema de reserva de horas

Prototipo del sistema de reserva de citas para el centro terapéutico
**"Aquí Somos Sensoriales"**. Proyecto de la asignatura Ingeniería de Software
(INACAP), Evaluación 3.

Equipo: Tomás Torres, Germán Bastidas y Esteban Morales.

## ¿Qué hace?

- **Pacientes (o sus tutores):** se registran, piden horas con un especialista,
  ven sus citas y pueden cancelarlas con 24 horas de anticipación.
- **Especialistas:** publican sus horarios de 45 minutos, confirman o rechazan
  solicitudes, cancelan (casos excepcionales) y reagendan citas.
- **Administrador:** crea, edita y desactiva cuentas desde `/admin/` y revisa la
  auditoría.
- El sistema **no permite que dos pacientes reserven el mismo horario** y avisa
  cada cambio en la aplicación y por correo.

## Tecnologías

Python 3.13 · Django 5.2 LTS · Bootstrap 5 · SQLite (desarrollo) ·
PostgreSQL (producción) · GitHub Actions (CI) · Render (PaaS)

## Cómo ejecutarlo en tu computador

```bash
python -m venv venv
venv\Scripts\activate          # en Windows  (en Mac/Linux: source venv/bin/activate)
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py cargar_demo   # crea usuarios y horarios de ejemplo
python manage.py runserver
```

Abre http://127.0.0.1:8000 y entra con uno de estos usuarios
(contraseña: `Sensorial2026!`):

| Usuario | Correo | Rol |
|---|---|---|
| Ana García | ana.garcia@correo.cl | Paciente |
| Sofía Ramírez | sofia.ramirez@somossensoriales.cl | Especialista |
| Admin | admin@somossensoriales.cl | Administrador (`/admin/`) |

## Pruebas

```bash
coverage run manage.py test tests
coverage report
```

Las mismas pruebas se ejecutan solas en GitHub Actions en cada `push`
(archivo `.github/workflows/ci.yml`), junto con Bandit (seguridad del código)
y pip-audit (librerías con vulnerabilidades).

## Estructura

```
config/          settings.py (configuración), urls.py
usuarios/        Usuario, login con bloqueo, registro, auditoría, control de acceso
agenda/          CentroTerapeutico (Singleton), BloqueHorario, Cita, señal cita_cambiada
notificaciones/  avisos en la app y por correo (Observer + Factory)
templates/       pantallas HTML con Bootstrap 5
tests/           pruebas automáticas
docs/            diagramas UML, evidencias de pruebas y registro de defectos
```

## Despliegue en Render

1. Subir el repositorio a GitHub.
2. En Render: **New → Blueprint** y elegir el repositorio (usa `render.yaml`).
3. Escribir la variable `DEMO_PASSWORD` en el panel de Render.

Render crea la base de datos PostgreSQL, genera la clave secreta y despliega
solo cuando el CI de GitHub pasó.

## Seguridad (resumen)

- Contraseñas con hash PBKDF2 y mínimo 10 caracteres.
- Bloqueo de 15 minutos tras 5 intentos fallidos de inicio de sesión.
- La sesión se cierra tras 30 minutos sin uso.
- Cada vista revisa el rol y solo muestra datos del dueño (OWASP A01).
- HTTPS obligatorio, HSTS y cookies seguras en producción.
- Registro de auditoría que nadie puede editar (Ley 21.459).
- Los secretos se leen de variables de entorno, nunca del código.
