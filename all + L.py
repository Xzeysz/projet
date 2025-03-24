import cv2
import pyaudio
import threading
import queue
import time

# -------------------------
# CONFIGURATION AUDIO
# -------------------------
AUDIO_DEVICE_INDEX = 6  # Indice du périphérique audio (carte de capture)
FORMAT = pyaudio.paInt16   # Format 16 bits
CHANNELS = 2             # 2 canaux (stéréo selon les infos)
RATE = 44100             # Taux d'échantillonnage (44100 Hz)
CHUNK = 2048             # Taille d'un bloc audio (modifiable selon les besoins)

# File d'attente pour transférer les blocs audio de l'entrée à la sortie
audio_queue = queue.Queue(maxsize=20)

def input_callback(in_data, frame_count, time_info, status_flags):
    """Callback du flux d'entrée : enfile les données capturées."""
    try:
        audio_queue.put_nowait(in_data)
    except queue.Full:
        # Si la file est pleine, ignorer ce bloc pour éviter un blocage.
        pass
    return (None, pyaudio.paContinue)

def output_callback(in_data, frame_count, time_info, status_flags):
    """Callback du flux de sortie : récupère les données dans la file ou renvoie du silence."""
    try:
        data = audio_queue.get_nowait()
    except queue.Empty:
        # Retourne du silence si rien n'est disponible.
        data = b'\x00' * (frame_count * CHANNELS * 2)  # 2 octets par échantillon
    return (data, pyaudio.paContinue)

def audio_duplex():
    """Lance la capture et la restitution audio en mode callback."""
    p = pyaudio.PyAudio()
    try:
        input_stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            input_device_index=AUDIO_DEVICE_INDEX,
            stream_callback=input_callback
        )
        output_stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            output=True,
            frames_per_buffer=CHUNK,
            stream_callback=output_callback
        )
    except Exception as e:
        print("Erreur lors de l'ouverture des flux audio :", e)
        p.terminate()
        return

    input_stream.start_stream()
    output_stream.start_stream()
    print("Audio duplex en mode callback démarré.")

    try:
        while input_stream.is_active() and output_stream.is_active():
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass

    input_stream.stop_stream()
    output_stream.stop_stream()
    input_stream.close()
    output_stream.close()
    p.terminate()

# Lancer la partie audio dans un thread séparé afin qu'elle fonctionne en parallèle
audio_thread = threading.Thread(target=audio_duplex, daemon=True)
audio_thread.start()

# -------------------------
# CONFIGURATION VIDEO & DÉTECTION DE MOUVEMENT
# -------------------------
VIDEO_DEVICE_INDEX = 1  # Indice du périphérique vidéo (carte de capture vidéo)

# Utilisation du backend DirectShow (pour Windows)
cap = cv2.VideoCapture(VIDEO_DEVICE_INDEX, cv2.CAP_DSHOW)
if not cap.isOpened():
    print(f"Erreur : impossible d'ouvrir le périphérique vidéo à l'indice {VIDEO_DEVICE_INDEX}.")
    exit(1)

# Réduction de la taille du buffer (si supporté)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# Définition de la résolution souhaitée (1920 x 1080)
width = 1920
height = 1080
cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

# Vidanger quelques frames pour vider le tampon initial
for _ in range(30):
    ret, _ = cap.read()
    if not ret:
        break

# Mesurer le temps nécessaire pour obtenir la première frame
start_time = time.time()
ret, frame = cap.read()
if ret:
    print(f"Première frame capturée après {time.time() - start_time:.2f} secondes")
else:
    print("Erreur lors de la lecture de la première frame.")

# Création et initialisation de la fenêtre vidéo en plein écran
window_name = "Flux vidéo"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
is_fullscreen = True
print("Affichage du flux vidéo en plein écran. Appuyez sur 'q' pour quitter ou 'espace' pour basculer.")

# Initialisation du soustracteur de fond MOG2 pour la détection de mouvement
fgbg = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=16, detectShadows=True)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Erreur lors de la lecture du flux vidéo.")
        break

    # Détecter le mouvement à l'aide du soustracteur de fond
    fgmask = fgbg.apply(frame)
    _, thresh = cv2.threshold(fgmask, 244, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)
    thresh = cv2.dilate(thresh, kernel, iterations=2)

    # Extraire les contours du masque
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Sélectionner le contour le plus grand (parmi ceux au-dessus d'un seuil) pour le suivi
    max_contour = None
    max_area = 0
    min_area_threshold = 500
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > min_area_threshold and area > max_area:
            max_area = area
            max_contour = cnt

    if max_contour is not None:
        x, y, w, h = cv2.boundingRect(max_contour)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

    cv2.imshow(window_name, frame)
    
    key = cv2.waitKey(1) & 0xFF
    # Quitter en appuyant sur 'q'
    if key == ord('q'):
        break
    # Basculement entre plein écran et mode fenêtré via la touche espace
    elif key == ord(' '):
        if is_fullscreen:
            cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
            is_fullscreen = False
        else:
            cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            is_fullscreen = True

cap.release()
cv2.destroyAllWindows()
