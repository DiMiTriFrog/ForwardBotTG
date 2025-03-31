# 🤖 Telegram Forwarder Bot (No Trades No Gains Edition) 📈

Este bot está diseñado para reenviar mensajes de un grupo base de Telegram a múltiples grupos destino. Ha sido desarrollado y es utilizado principalmente para la comunidad gratuita de señales de trading **No Trades No Gains**.

✨ **Únete a nuestra comunidad:**

- **Canal de Telegram:** [@notradesnogains](https://t.me/notradesnogains)
- **Visita nuestra web:** [notradesnogains.com](https://notradesnogains.com)

---

## 🚀 Cómo Funciona

El bot permite a usuarios autorizados configurar un "grupo base" y uno o más "grupos destino". Cualquier mensaje enviado al grupo base será automáticamente reenviado por el bot a todos los grupos destino configurados por ese usuario.

## Setup

1.  **Clonar el repositorio:**
    ```bash
    git clone https://github.com/DiMiTriFrog/ForwardBotTG.git # O tu URL si lo has bifurcado
    cd ForwardBotTG
    ```
2.  **Crear un entorno virtual:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows usa `venv\Scripts\activate`
    ```
3.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configurar el Token del Bot:**
    - Copia o renombra `.env.example` a `.env` (si existe un `.env.example`).
    - Abre el archivo `.env` y reemplaza `YOUR_BOT_TOKEN_HERE` con tu Token de Bot real de Telegram (obtenido de @BotFather).
5.  **Ejecutar el bot:**
    ```bash
    python main.py
    ```

## Usage

1.  Inicia una conversación con tu bot en Telegram.
2.  Envía `/start` para ver el menú principal.
3.  **Añade el bot** a los grupos que quieres usar (tanto al grupo base como a los grupos destino). Asegúrate de que tenga permisos para leer y enviar mensajes.
4.  Usa el menú interactivo del bot para configurar:
    - **Grupo Base:** El grupo desde donde se copiarán los mensajes.
    - **Grupos Destino:** Los grupos a donde se enviarán las copias.
    - _Nota:_ Para registrar un grupo (base o destino), tendrás que **reenviar un mensaje cualquiera** de ese grupo al chat privado con el bot cuando te lo pida.
5.  Una vez configurado, el bot operará automáticamente.

## Features

- 📨 Reenvío (o copia) de mensajes de un grupo base a múltiples destinos.
- 👤 Configuración **por usuario**: Cada usuario gestiona sus propias reglas de reenvío.
- 💾 Base de datos **SQLite** para persistir las configuraciones.
- 🚫 Prevención de **conflictos**: No permite que dos usuarios configuren el mismo reenvío (mismo origen -> mismo destino).
- ⚙️ Menú **intuitivo** con botones para añadir, ver y borrar configuraciones.
- 🚀 Implementación **asíncrona** usando `python-telegram-bot`.

---

## 👨‍💻 Autor

- **Creador:** Pau Perales
- **Rol:** Desarrollador y usuario principal del bot para la comunidad [@notradesnogains](https://t.me/notradesnogains).
