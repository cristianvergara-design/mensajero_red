"""
Aplicación de Mensajería en Red Local (Broadcast UDP)
=====================================================
- Muestra una imagen PNG en la esquina inferior derecha
- Doble clic: envía mensaje.txt por UDP broadcast a toda la red
- Las demás computadoras con la app abierta reciben y muestran el mensaje
- El emisor no escucha su propio mensaje
"""

import tkinter as tk
from tkinter import messagebox
import socket
import threading
import os
import sys
import subprocess
import json
import uuid

# ============ CONFIGURACIÓN ============
PUERTO_BROADCAST = 5000
TAMANO_BUFFER = 4096

# ID único de esta instancia para ignorar mensajes propios
ID_INSTANCIA = str(uuid.uuid4())


# ============ OBTENER CARPETA DE LA APLICACIÓN ============
def obtener_carpeta_app():
    """
    Obtiene la carpeta donde está la aplicación.
    Funciona tanto como script Python como con ejecutable compilado (PyInstaller).
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


# ============ ENVÍO POR BROADCAST ============
def enviar_mensaje_broadcast():
    """Envía el contenido de mensaje.txt por UDP broadcast a toda la red."""
    ruta_mensaje = os.path.join(obtener_carpeta_app(), "mensaje.txt")
    if not os.path.exists(ruta_mensaje):
        mostrar_popup("Error: No se encontró el archivo mensaje.txt", "Error")
        return

    with open(ruta_mensaje, "r", encoding="utf-8") as f:
        contenido = f.read().strip()

    if not contenido:
        mostrar_popup("Error: mensaje.txt está vacío", "Error")
        return

    try:
        # Enviar como JSON con ID único
        datos = json.dumps({"id": ID_INSTANCIA, "mensaje": contenido})
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(datos.encode("utf-8"), ("<broadcast>", PUERTO_BROADCAST))
        sock.close()
        print(f"[ENVIADO] Mensaje enviado por broadcast: {contenido}")
        mostrar_popup("Mensaje enviado a toda la red", "Sistema")
    except Exception as e:
        print(f"[ERROR] No se pudo enviar: {e}")
        mostrar_popup(f"Error al enviar: {e}", "Error")


# ============ SONIDO ============
def reproducir_sonido():
    """Reproduce el archivo ALERTA.mp3 al recibir un mensaje."""
    ruta_sonido = os.path.join(obtener_carpeta_app(), "ALERTA.mp3")
    if not os.path.exists(ruta_sonido):
        print(f"[SONIDO] No se encontró {ruta_sonido}")
        return

    try:
        subprocess.Popen(
            ["powershell", "-c", f"(New-Object Media.SoundPlayer '{ruta_sonido}').PlaySync()"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        print(f"[SONIDO] Error: {e}")
        try:
            os.startfile(ruta_sonido)
        except:
            pass


# ============ RECEPCIÓN POR BROADCAST ============
def iniciar_receptor():
    """Escucha mensajes UDP broadcast y muestra popup al recibir."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", PUERTO_BROADCAST))
    sock.settimeout(1)

    print(f"[RECEPTOR] Escuchando en puerto UDP {PUERTO_BROADCAST}...")

    while True:
        try:
            datos, addr = sock.recvfrom(TAMANO_BUFFER)

            # Decodificar JSON
            try:
                data = json.loads(datos.decode("utf-8"))
                id_remota = data.get("id", "")
                mensaje = data.get("mensaje", "")
            except (json.JSONDecodeError, AttributeError):
                # Formato antiguo (texto plano)
                mensaje = datos.decode("utf-8")
                id_remota = ""

            # Ignorar mensajes propios
            if id_remota == ID_INSTANCIA:
                continue

            if not mensaje:
                continue

            print(f"[RECIBIDO] De {addr[0]}: {mensaje}")
            reproducir_sonido()
            mostrar_popup(mensaje, f"Mensaje de {addr[0]}")
        except socket.timeout:
            continue
        except Exception as e:
            print(f"[ERROR] Receptor: {e}")


# ============ POPUP ============
def mostrar_popup(mensaje, titulo="Mensaje"):
    """Muestra una ventana emergente con un mensaje."""
    def _mostrar():
        root = tk.Tk()
        root.withdraw()
        if titulo == "Error":
            messagebox.showerror(titulo, mensaje)
        else:
            messagebox.showinfo(titulo, mensaje)
        root.destroy()

    threading.Thread(target=_mostrar, daemon=True).start()


# ============ INTERFAZ GRÁFICA ============
def crear_interfaz(ruta_icono):
    """Crea la ventana con la imagen en la esquina inferior derecha."""
    root = tk.Tk()
    root.title("Mensajero de Red")

    try:
        img = tk.PhotoImage(file=ruta_icono)
    except Exception as e:
        print(f"[ERROR] No se pudo cargar la imagen: {e}")
        img = tk.PhotoImage(width=100, height=100)
        img.put("#2196F3", to=(0, 0, 99, 99))

    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-transparentcolor", "#f0f0f0")

    ancho_pantalla = root.winfo_screenwidth()
    alto_pantalla = root.winfo_screenheight()
    ancho_ventana = 100
    alto_ventana = 100
    x = ancho_pantalla - ancho_ventana - 20
    y = alto_pantalla - alto_ventana - 60
    root.geometry(f"{ancho_ventana}x{alto_ventana}+{x}+{y}")

    label = tk.Label(root, image=img, cursor="hand2", bg="#f0f0f0")
    label.pack(expand=True, fill="both")
    label.image = img

    drag_data = {"x": 0, "y": 0, "dragging": False}

    def on_press(event):
        drag_data["x"] = event.x
        drag_data["y"] = event.y
        drag_data["dragging"] = False

    def on_motion(event):
        if abs(event.x - drag_data["x"]) > 5 or abs(event.y - drag_data["y"]) > 5:
            drag_data["dragging"] = True
            x = root.winfo_x() + event.x - drag_data["x"]
            y = root.winfo_y() + event.y - drag_data["y"]
            root.geometry(f"+{x}+{y}")

    def on_double_click(event):
        threading.Thread(target=enviar_mensaje_broadcast, daemon=True).start()

    def on_right_click(event):
        menu = tk.Menu(root, tearoff=0)
        menu.add_command(label="Enviar mensaje", command=lambda: threading.Thread(target=enviar_mensaje_broadcast, daemon=True).start())
        menu.add_separator()
        menu.add_command(label="Salir", command=root.destroy)
        menu.post(event.x_root, event.y_root)

    label.bind("<ButtonPress-1>", on_press)
    label.bind("<B1-Motion>", on_motion)
    label.bind("<Double-Button-1>", on_double_click)
    label.bind("<Button-3>", on_right_click)

    root.bind("<Escape>", lambda e: root.destroy())

    return root


# ============ PUNTO DE ENTRADA ============
def main():
    print("=" * 50)
    print("  MENSAJERO DE RED LOCAL (Broadcast UDP)")
    print("=" * 50)
    print(f"  Puerto UDP: {PUERTO_BROADCAST}")
    print(f"  ID instancia: {ID_INSTANCIA}")
    print(f"  Carpeta app: {obtener_carpeta_app()}")
    print("=" * 50)

    threading.Thread(target=iniciar_receptor, daemon=True).start()

    ruta_icono = os.path.join(obtener_carpeta_app(), "icono.png")
    root = crear_interfaz(ruta_icono)

    print("\n[APP] Aplicación iniciada.")
    print("[APP] Doble clic: enviar mensaje por broadcast")
    print("[APP] Clic + arrastrar: mover ventana")
    print("[APP] Clic derecho: menú de opciones")
    print("[APP] Escape: salir\n")

    root.mainloop()


if __name__ == "__main__":
    main()
