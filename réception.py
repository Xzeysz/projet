import socket
import base64
from Crypto.Cipher import AES

# Clé AES (doit être identique à celle utilisée par l'émetteur)
AES_KEY = b"0123456789abcdef"  # 16 octets pour AES-128

# Adresse et port sur lesquels le récepteur écoutera
HOST = "0.0.0.0"  # '0.0.0.0' signifie écoute sur toutes les interfaces réseau disponibles
PORT = 5000

def decrypt_message(encrypted_message):
    """
    Déchiffre un message encodé en base64.
    
    Le message chiffré est constitué du nonce (les 16 premiers octets)
    suivi du ciphertext.
    """
    try:
        # Décodage du message depuis le format base64 en bytes
        data = base64.b64decode(encrypted_message)
    except Exception as e:
        print("Erreur lors du décodage base64 :", e)
        return None

    # Récupération du nonce (16 octets) et du ciphertext
    nonce = data[:16]
    ciphertext = data[16:]

    # Création du cipher avec le nonce
    cipher = AES.new(AES_KEY, AES.MODE_EAX, nonce=nonce)
    try:
        plaintext = cipher.decrypt(ciphertext)
        return plaintext.decode("utf-8")
    except Exception as e:
        print("Erreur lors du décryptage :", e)
        return None

def main():
    # Création et configuration de la socket serveur
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)  # possibilité de gérer jusqu'à 5 connexions en file d'attente
        print(f"Serveur en écoute sur {HOST}:{PORT}")

        while True:
            conn, addr = server_socket.accept()
            with conn:
                print("Connexion établie depuis :", addr)
                data = conn.recv(4096)  # taille du buffer de réception
                if data:
                    # Décodage du message reçu
                    encrypted_msg = data.decode()
                    # Décryptage du message pour récupérer les coordonnées
                    plain_text = decrypt_message(encrypted_msg)
                    if plain_text:
                        print("Coordonnées reçues et décryptées :", plain_text)
                    else:
                        print("Le décryptage a échoué.")
                else:
                    print("Aucune donnée reçue.")

if __name__ == "__main__":
    main()
