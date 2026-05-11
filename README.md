# 🏋️BIO-FIT

¡Hola! Bienvenido a **BIO-FIT**, un proyecto creado con dedicación, esfuerzo y muchas ganas de ayudar a las personas a sentirse mejor consigo mismas.

Este proyecto nació en el **SENA**, gracias a un grupo de aprendices que creemos que la tecnología no solo sirve para programar, sino también para mejorar vidas, y ayudar a que obtengan una mayor seguridad consigo mismas. Queríamos construir algo útil, cercano y humano, una herramienta que acompañe a las personas en su proceso de cambiar hábitos, mejorar su salud y alcanzar sus metas físicas sin sentirse perdidas mientras lo hacen.

---

## 🤔 ¿Qué es BIO-FIT?

Muchas veces las personas quieren empezar una vida más saludable, pero no saben cómo hacerlo. Buscan rutinas, dietas o consejos en internet y terminan encontrando información confusa, planes genéricos o recomendaciones que no se adaptan a lo que ellos buscan en sí.

Por eso creamos **BIO-FIT** 💚

BIO-FIT es una plataforma pensada para ayudarte a mejorar tu bienestar físico y nutricional enfoncandose en el consumo de calorías díarias de manera más personalizada y obviamente adptandose a lo que quieren lograr. Nuestro objetivo es que cada usuario pueda recibir recomendaciones acordes a sus necesidades, hábitos y metas, combinando entrenamiento, consumo de calorías y tecnología en un solo lugar.

Más que una página web, queremos que BIO-FIT sea una guía y un apoyo para quienes desean empezar a cuidarse sin complicaciones.

---

## 👥 Equipo de desarrollo

Este proyecto fue desarrollado por aprendices del programa **ANALISIS Y DESARROLLO DE SOFTWARE – Ficha 3147269**, quienes trabajamos en equipo para convertir esta idea en realidad:

* **María Camila Llorente Sierra** ✍️  
* **Diego Alejandro Torres Mendivelso** 💻  
* **Erik Santiago Ruano Ascuntar** 🛠️  
* **Daniel Matias Pardo Núñez** 🚀  

Cada integrante aportó ideas, creatividad y muchas horas de trabajo para construir BIO-FIT.

---

## 🛠️ Tecnologías utilizadas

Para desarrollar BIO-FIT utilizamos herramientas modernas que nos permitieron crear una plataforma rápida, segura y eficiente:

* **Python** → Lenguaje principal del proyecto.  
* **Django** → Framework utilizado para el desarrollo web.  
* **Firebase** → Sistema utilizado para autenticación y almacenamiento de datos.  
* **OpenAI** → Implementado para generar recomendaciones inteligentes y personalizadas.  
* **Django-environ** → Utilizado para manejar variables de entorno y proteger información sensible.

---

## 📋 Requisitos previos

Antes de ejecutar el proyecto, necesitas tener instalado lo siguiente:

* **Python 3.10 o superior**  
* **Git**  
* **Visual Studio Code (VS Code)**  
* Una cuenta en **Firebase**

---

## 📥 Instalación

Sigue estos pasos para tener BIO-FIT funcionando en tu computador:

1. **Clonar el repositorio**
```bash
git clone https://github.com/tu-usuario/bio-fit.git
```

2. **Entrar a la carpeta del proyecto**
```bash
cd bio-fit
```

3. **Crear el entorno virtual**
```bash
python -m venv env
```

---

## 🚀 Ejecución local

1. **Activar el entorno virtual**

### Windows
```bash
.\env\Scripts\activate
```

### Mac/Linux
```bash
source env/bin/activate
```

2. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

3. **Ejecutar el servidor**
```bash
python manage.py runserver
```

4. **Abrir en el navegador**
```bash
http://127.0.0.1:8000/
```

---

## 🗄️ Base de datos

BIO-FIT utiliza **Firebase** para gestionar la autenticación y el almacenamiento de información.

Solo necesitas:

* Crear un proyecto en Firebase.  
* Descargar las credenciales en formato JSON.  
* Habilitar el inicio de sesión por correo electrónico.

Gracias a esto, los datos de los usuarios permanecen seguros y organizados.

---

## 🔐 Variables de entorno

Para proteger información importante del proyecto utilizamos un archivo `.env`.

Dentro de este archivo debes configurar:

```env
SECRET_KEY=
FIREBASE_CONFIG=
API_IA_KEY=
```

Estas variables permiten mantener seguras las credenciales y conexiones del sistema.

---

## 👤 Usuario de prueba

Si deseas explorar BIO-FIT rápidamente, puedes ingresar con este usuario de prueba:

```txt
Usuario: visitante@biofit.com
Contraseña: BioFit2026*
```

---

## 🌐 Despliegue

Para publicar y compartir nuestro proyecto utilizamos **Render**, una plataforma que nos permite mantener BIO-FIT disponible de forma online y accesible desde cualquier lugar.

---

## 📸 Evidencias del proyecto

Aquí podrás visualizar algunas capturas y avances del sistema:

* Panel principal  
* Plan personalizado  
* Sistema de recomendaciones  
* Interfaz de entrenamiento y recomendación para el consumo de calorías a diario

---

## 💚 Nuestro propósito

BIO-FIT no es solo un proyecto académico. Es una idea construida con dedicación, aprendizaje y el deseo de crear una herramienta que realmente pueda ayudar a las personas.

Queremos demostrar que la tecnología también puede ser cercana, motivadora y capaz de generar cambios positivos en la vida de alguien.

Gracias por visitar BIO-FIT 🚀
