import ftd2xx as ftd
import keyboard
import time

# --- Configuration du port série DMX ---
device_index = 0  # Numéro du device FTD

try:
    ser = ftd.open(device_index)
    ser.setBaudRate(250000)  # Baudrate standard DMX
    ser.setDataCharacteristics(8, 2, 0)  # 8 data bits, 2 stop bits, no parity
    print(f"Device FTD ouvert sur l'index {device_index}")
except Exception as e:
    print("Erreur lors de l'ouverture du device FTD :", e)
    exit(1)

# --- Variables DMX ---
pan_value = 127   # Valeur initiale pour PAN (canal 1)
tilt_value = 127  # Valeur initiale pour TILT (canal 2)
step = 5          # Incrément pour chaque appui

# --- Fonction d'envoi de la trame DMX ---
def send_dmx(pan, tilt):
    # Préparer 512 canaux ; attend un start code (0) avant les données
    dmx_data = bytearray(512)
    dmx_data[0] = pan    # Canal 1 : PAN
    dmx_data[1] = tilt   # Canal 2 : TILT
    packet = bytes([0]) + dmx_data  # Trame DMX complète (513 octets)

    try:
        # Générer le BREAK
        ser.setBreakOn()
        time.sleep(0.001)  # Environ 1 ms de break
        ser.setBreakOff()

        # Envoi de la trame
        ser.write(packet)
        ser.purge()  # Equivalent de flush()
        print(f"DMX transmis  =>  PAN: {pan} | TILT: {tilt}")
    except Exception as e:
        print("Erreur d'envoi DMX :", e)

# --- Affichage des instructions ---
print("\nContrôle du projecteur DMX via ENTTEC OpenDMX USB")
print("Configuration:")
print("  - Canal 1 : PAN")
print("  - Canal 2 : TILT\n")
print("Touches (clavier AZERTY) :")
print("  Z : Augmenter le PAN")
print("  S : Diminuer le PAN")
print("  Q : Augmenter le TILT")
print("  D : Diminuer le TILT")
print("  A ou ESC : Quitter\n")

# --- Boucle principale ---
try:
    # On envoie une trame initiale pour commencer
    send_dmx(pan_value, tilt_value)
    # Définir un délai d'actualisation DMX (~20 images/sec)
    rafraichissement = 0.05  
    dernier_envoi = time.time()
    
    while True:
        # Quitter si "A" ou "ESC" est pressé
        if keyboard.is_pressed("a") or keyboard.is_pressed("esc"):
            print("Fin du programme.")
            break

        # Mises à jour en fonction des touches (AZERTY)
        touche_pressee = False
        if keyboard.is_pressed("d"):
            pan_value = min(255, pan_value + step)
            touche_pressee = True
        if keyboard.is_pressed("q"):
            pan_value = max(0, pan_value - step)
            touche_pressee = True
        if keyboard.is_pressed("z"):
            tilt_value = min(255, tilt_value + step)
            touche_pressee = True
        if keyboard.is_pressed("s"):
            tilt_value = max(0, tilt_value - step)
            touche_pressee = True

        # Envoi en continue de la trame DMX pour un signal stable
        if time.time() - dernier_envoi >= rafraichissement or touche_pressee:
            send_dmx(pan_value, tilt_value)
            dernier_envoi = time.time()
            
        # Petite pause pour limiter l'utilisation CPU
        time.sleep(0.01)
finally:
    ser.close()
    print("Device FTD fermé.")
