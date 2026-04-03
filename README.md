# Canvas QTI Quiz Maker v3.0

Una herramienta de escritorio ligera y autónoma diseñada para que educadores y profesores puedan crear cuestionarios (quizzes) compatibles con Canvas LMS sin necesidad de conocimientos de programación ni formateo de código. 

La aplicación genera paquetes QTI 1.2 (.zip) estándar que se importan nativamente en la herramienta de cuestionarios clásicos de Canvas.

## Características Principales

* **Interfaz Gráfica Intuitiva:** Diseño moderno y limpio basado en `ttkbootstrap`.
* **Múltiples Tipos de Preguntas:** * Opción Múltiple (MC)
  * Respuesta Múltiple (MR)
  * Verdadero / Falso (TF)
  * Respuesta Corta (Short Answer)
  * Numérica (Exacta o por Rango)
  * Ensayo (Manual grading)
  * Emparejamiento (Matching)
* **Importación Masiva de Texto:** Permite pegar bloques de texto plano para generar decenas de preguntas de opción múltiple en segundos.
* **Autónomo (Standalone):** No requiere que el usuario final instale Python ni librerías adicionales.

## Instalación y Descarga

Los usuarios finales no necesitan clonar este repositorio. 
Para descargar la aplicación lista para usar:
1. Ve a la pestaña **Actions** o **Releases** en este repositorio.
2. Descarga la versión correspondiente a tu sistema operativo (Windows `.exe`, macOS `.app`, o Linux).
3. Descomprime el archivo y haz doble clic para ejecutar.

## Compilación (Para Desarrolladores)

Si deseas modificar el código fuente y recompilar la aplicación:

1. Clona el repositorio.
2. Crea un entorno virtual: `python -m venv venv`
3. Instala las dependencias: `pip install pyinstaller ttkbootstrap`
4. Compila:
   * Windows/Linux: `pyinstaller --windowed --onefile CanvasQuizMakerv03.py`
   * macOS: `pyinstaller --windowed CanvasQuizMakerv03.py`
