RAÍCES DE BIENESTAR — versión pública preparada

1) INSTALACIÓN LOCAL
Windows:
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
py app.py
Abre http://127.0.0.1:5000

2) PUBLICACIÓN
El proyecto incluye requirements.txt, Procfile y runtime.txt para servicios de hosting compatibles con Flask/Gunicorn.
Antes de publicar:
- Cambia SECRET_KEY por una clave aleatoria y privada.
- Usa HTTPS.
- Para un proyecto real con muchos usuarios, cambia SQLite por PostgreSQL.
- No recolectes más datos personales de los necesarios.
- Añade política de privacidad, términos y consentimiento informado adecuados a tu contexto.
- El chat incluido es un asistente de orientación general basado en reglas; no es un terapeuta ni un servicio de emergencia.

3) IMPORTANTE
Esta versión ya tiene:
- cuentas y sesiones
- contraseñas almacenadas con hash
- base de datos SQLite
- registros emocionales por usuario
- gráfica
- recursos
- chat
- diseño responsive
