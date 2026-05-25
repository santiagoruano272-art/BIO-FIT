# 🏋️ BIO-FIT

¡Hola! Bienvenido a **BIO-FIT**, un proyecto creado con dedicación, esfuerzo y muchas ganas de ayudar a las personas a sentirse mejor consigo mismas.

Este proyecto nació en el **SENA**, gracias a un grupo de aprendices que creemos que la tecnología no solo sirve para programar, sino también para mejorar vidas y ayudar a que las personas obtengan una mayor seguridad consigo mismas. Queríamos construir algo útil, cercano y humano; una herramienta que acompañe a las personas en su proceso de cambiar hábitos, mejorar su salud y alcanzar sus metas físicas sin sentirse perdidas mientras lo hacen.

---

# 🤔 ¿Qué es BIO-FIT?

Muchas veces las personas quieren empezar una vida más saludable, pero no saben cómo hacerlo. Buscan rutinas, dietas o consejos en internet y terminan encontrando información confusa, planes genéricos o recomendaciones que no se adaptan realmente a sus necesidades.

Por eso creamos **BIO-FIT** 💚

BIO-FIT es una plataforma pensada para ayudar a mejorar el bienestar físico y nutricional, enfocándose en el consumo de calorías diarias de manera más personalizada y adaptándose a los objetivos de cada usuario. Nuestro objetivo es que cada persona pueda recibir recomendaciones acordes a sus necesidades, hábitos y metas, combinando entrenamiento, alimentación y tecnología en un solo lugar.

Más que una página web, queremos que BIO-FIT sea una guía y un apoyo para quienes desean empezar a cuidarse sin complicaciones.

---

# 👥 Equipo de desarrollo

Este proyecto fue desarrollado por aprendices del programa **ANÁLISIS Y DESARROLLO DE SOFTWARE – Ficha 3147269**, quienes trabajamos en equipo para convertir esta idea en realidad:

* **María Camila Llorente Sierra** ✍️  
* **Diego Alejandro Torres Mendivelso** 💻  
* **Erik Santiago Ruano Ascuntar** 🛠️  
* **Daniel Matías Pardo Núñez** 🚀  

Cada integrante aportó ideas, creatividad y muchas horas de trabajo para construir BIO-FIT.

---

# 🛠️ Tecnologías utilizadas

Para desarrollar BIO-FIT utilizamos herramientas modernas que nos permitieron crear una plataforma rápida, segura y eficiente:

* **Python** → Lenguaje principal del proyecto.  
* **Django** → Framework utilizado para el desarrollo web.  
* **Firebase** → Sistema utilizado para autenticación y almacenamiento de datos.  
* **Groq AI** → Implementado para generar recomendaciones inteligentes y personalizadas mediante modelos de inteligencia artificial.  
* **Django-environ** → Utilizado para manejar variables de entorno y proteger información sensible.  
* **Render** → Plataforma utilizada para el despliegue y publicación del proyecto en la nube.

---

# 📋 Requisitos previos

Antes de ejecutar el proyecto, necesitas tener instalado lo siguiente:

* **Python 3.10 o superior**  
* **Git**  
* **Visual Studio Code (VS Code)**  
* Una cuenta en **Firebase**  
* Una cuenta en **Groq Cloud**

---

# 📥 Instalación

Sigue estos pasos para tener BIO-FIT funcionando en tu computador:

## 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/bio-fit.git
```

## 2. Entrar a la carpeta del proyecto

```bash
cd bio-fit
```

## 3. Crear el entorno virtual

```bash
python -m venv env
```

---

# 🚀 Ejecución local

## 1. Activar el entorno virtual

### Windows

```bash
.\env\Scripts\activate
```

### Mac/Linux

```bash
source env/bin/activate
```

---

## 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

---

## 3. Ejecutar el servidor

```bash
python manage.py runserver
```

---

## 4. Abrir en el navegador

```bash
http://127.0.0.1:8000/
```

---

# 🗄️ Base de datos

BIO-FIT utiliza **Firebase** para gestionar la autenticación y el almacenamiento de información.

Solo necesitas:

* Crear un proyecto en Firebase.  
* Descargar las credenciales en formato JSON.  
* Habilitar el inicio de sesión por correo electrónico.  

Gracias a esto, los datos de los usuarios permanecen seguros y organizados.

---

# 🔐 Variables de entorno

Para proteger información importante y evitar exponer credenciales sensibles dentro del código, BIO-FIT utiliza un archivo `.env`.

Dentro del archivo `.env` debes configurar las siguientes variables:

```env
SECRET_KEY=Clave secreta generada para la seguridad interna de Django.

FIREBASE_CREDENTIALS_PATH=Ruta del archivo JSON descargado desde Firebase > Configuración del proyecto > Cuentas de servicio.

FIREBASE_API_KEY=Web API Key obtenida desde Firebase > Configuración del proyecto > Tus apps.

GROQ_MODEL=Nombre del modelo de inteligencia artificial seleccionado dentro de Groq Cloud.

GROQ_API_KEY=API Key generada desde el panel de desarrolladores de Groq Cloud.
```

---

# 👤 Usuario de prueba

Si deseas explorar BIO-FIT rápidamente, puedes ingresar con este usuario de prueba:

```txt
Usuario: matias@gmail.com
Contraseña: matias12345
```

---

# 🌐 Despliegue

Para publicar y compartir nuestro proyecto utilizamos **Render**, una plataforma de despliegue en la nube que facilita alojar aplicaciones web modernas de forma rápida y segura.

## ¿Por qué utilizamos Render?

Elegimos Render porque ofrece una solución sencilla y eficiente para desplegar proyectos desarrollados con Django, permitiendo automatizar procesos importantes como:

* Despliegue continuo desde GitHub.  
* Configuración segura de variables de entorno.  
* Hosting en la nube.  
* Administración automática del servidor.  
* Facilidad para futuras actualizaciones y escalabilidad.

## ¿Cómo beneficia a BIO-FIT?

Gracias a Render, BIO-FIT puede:

* Estar disponible online desde cualquier lugar.  
* Mantener una ejecución estable del backend.  
* Facilitar pruebas y demostraciones del proyecto.  
* Simplificar las actualizaciones del sistema.  
* Brindar un entorno más profesional para el despliegue de aplicaciones reales.

Esto nos ayudó a convertir BIO-FIT en una plataforma accesible, funcional y preparada para crecer en el futuro.

---

# 📸 Evidencias del proyecto

Aquí podrás visualizar algunas capturas y avances del sistema:

* Panel principal  
* Plan personalizado  
* Sistema de recomendaciones  
* Interfaz de entrenamiento y recomendación para el consumo de calorías diario

---

# 💚 Nuestro propósito

BIO-FIT no es solo un proyecto académico. Es una idea construida con dedicación, aprendizaje y el deseo de crear una herramienta que realmente pueda ayudar a las personas.

Queremos demostrar que la tecnología también puede ser cercana, motivadora y capaz de generar cambios positivos en la vida de alguien.

Gracias por visitar BIO-FIT 🚀
