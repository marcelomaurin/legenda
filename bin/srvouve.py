#!/usr/bin/env python3

import speech_recognition as sr
import socket
import threading
from queue import Queue

# Variáveis globais 
r = sr.Recognizer()
clients = []  # Lista para manter os clientes conectados

# Fila para o último texto dito
last_said = Queue(maxsize=10)

def broadcast_message(message: str):
    # Faz uma cópia da lista para evitar problema ao remover enquanto itera
    for client in clients[:]:
        try:
            client.send(message.encode('utf-8'))
        except:
            try:
                client.close()
            except:
                pass
            clients.remove(client)

def sender_thread():
    """Thread responsável por ler da fila e enviar para todos os clientes."""
    while True:
        message = last_said.get(block=True)  # Espera até ter algo na fila
        broadcast_message(message)

def client_handler(client_socket):
    """Aqui você pode tratar mensagens vindas do cliente, se quiser.
       No momento, ele não recebe nada do cliente, então pode ficar vazio
       ou apenas manter a conexão aberta.
    """
    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break  # cliente desconectou
            # Se quiser tratar comandos do cliente, faz aqui
    except:
        pass
    finally:
        if client_socket in clients:
            clients.remove(client_socket)
        client_socket.close()
        print("Cliente desconectado")

def accept_connections(server):
    while True:
        client_sock, addr = server.accept()
        print(f"Conexão aceita de {addr}")
        clients.append(client_sock)
        client_thread = threading.Thread(target=client_handler, args=(client_sock,))
        client_thread.daemon = True
        client_thread.start()

def setup():
    # Configuração do servidor
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', 8097))
    server.listen(5)
    print("Servidor escutando na porta 8097")

    # Thread que aceita conexões
    accept_thread = threading.Thread(target=accept_connections, args=(server,))
    accept_thread.daemon = True
    accept_thread.start()

    # Thread que consome a fila e envia aos clientes
    sender = threading.Thread(target=sender_thread)
    sender.daemon = True
    sender.start()

def loop():
    with sr.Microphone() as source:
        # Ajuste para o ruído de fundo fora do loop para não repetir a cada iteração
        print("Ajuste do ruído de fundo. Aguarde...")
        r.adjust_for_ambient_noise(source, duration=1)
        r.pause_threshold = 0.8  # corrigido o nome (tava pause_threashold)

        while True:
            print("Fale algo:")
            audio = r.listen(source, phrase_time_limit=5)
            try:
                print("Iniciou análise")
                text = r.recognize_google(audio, language='pt-BR')
                print("Você disse: " + text)

                # Mantém só os últimos 10 textos
                if last_said.full():
                    last_said.get_nowait()

                # Agora, **não** manda mais direto pro socket.
                # Só coloca na fila pra sender_thread cuidar.
                last_said.put(text)

            except sr.UnknownValueError:
                print("Não consegui entender o áudio")
            except sr.RequestError as e:
                print(f"Erro ao solicitar resultados da API; {e}")

if __name__ == "__main__":
    setup()
    loop()
