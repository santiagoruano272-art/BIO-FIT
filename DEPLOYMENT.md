# 🚀 Despliegue en Render

Sigue estos pasos para desplegar BIO-FIT en Render:

## 📋 Paso 1: Preparar el repositorio

1. Asegúrate de que tu proyecto esté en GitHub (o GitLab/Bitbucket)
2. Verifica que los siguientes archivos estén en tu repositorio:
   - `render.yaml` (configuración de Render)
   - `requirements.txt` (dependencias)
   - `build.sh` (script de construcción)
   - `manage.py` (archivo de Django)

## 📝 Paso 2: Configurar Firebase (IMPORTANTE)

⚠️ **Nota**: Render no puede manejar archivos de credenciales JSON de Firebase directamente. Tienes dos opciones:

### Opción 1: Convertir credenciales JSON a variable de entorno (recomendado)

1. Abre tu archivo `bio-fit-serviceAccountKey.json`
2. Copia todo su contenido
3. En Render, crearás una variable de entorno llamada `FIREBASE_CREDENTIALS_JSON` con ese contenido
4. Modifica el código para leer las credenciales desde la variable de entorno

### Opción 2: Usar Firebase solo para autenticación web

Si no necesitas Firebase Admin en el backend, puedes simplificar la configuración.

## 🌐 Paso 3: Desplegar en Render

1. **Crear cuenta en Render**: Ve a [render.com](https://render.com) y registrate
2. **Nuevo Web Service**:
   - Haz clic en "New +" → "Web Service"
   - Conecta tu repositorio de GitHub
   - Selecciona el repositorio de BIO-FIT
3. **Configurar el servicio**:
   - **Name**: `bio-fit` (o el nombre que prefieras)
   - **Region**: Elige la más cercana a ti
   - **Branch**: `main` (o la rama que uses)
   - **Runtime**: `Python 3`
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn biofit.wsgi:application`
   - **Plan**: Free (para empezar)
4. **Variables de Entorno**:
   Haz clic en "Advanced" → "Add Environment Variable" y agrega:
   - `DJANGO_SECRET_KEY`: (Render lo genera automáticamente si usas render.yaml)
   - `DEBUG`: `False`
   - `ALLOWED_HOSTS`: `.onrender.com`
   - `GROQ_API_KEY`: Tu clave de Groq
   - `GROQ_MODEL`: `llama-3.3-70b-versatile`
   - `FIREBASE_API_KEY`: Tu API Key de Firebase
   - `SESSION_COOKIE_SECURE`: `True`
   - `CSRF_COOKIE_SECURE`: `True`
5. **Desplegar**: Haz clic en "Create Web Service"

## ⏳ Paso 4: Esperar el despliegue

Render comenzará a construir y desplegar tu aplicación. Esto puede tardar unos minutos.

## ✅ Paso 5: Verificar el despliegue

Cuando el despliegue termine, Render te dará una URL como:
`https://bio-fit.onrender.com`

Abre esa URL en tu navegador para ver tu aplicación en funcionamiento!

## 📌 Notas importantes

- **Base de Datos**: El proyecto usa SQLite por defecto. En Render, los datos de SQLite se pierden en cada reinicio. Para producción, considera usar PostgreSQL (Render lo ofrece como servicio adicional).
- **Firebase**: Si necesitas Firebase Admin en el backend, deberás modificar el código para leer las credenciales desde una variable de entorno en lugar de un archivo.
- **Dominios personalizados**: Puedes agregar tu propio dominio en la sección "Custom Domains" de Render.

## 🆘 Solución de problemas

Si algo sale mal:
1. Revisa los logs en el dashboard de Render
2. Verifica que todas las variables de entorno estén configuradas correctamente
3. Asegúrate de que `DEBUG` esté en `False` en producción

¡Listo! Tu proyecto BIO-FIT está en línea 🎉
