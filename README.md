# 🎤 Legenda

Servidor simples de legendas em tempo real para palestras, aulas, reuniões e apresentações.

O projeto captura áudio do microfone, converte a fala para texto usando reconhecimento de voz em português do Brasil e envia a transcrição para clientes conectados por socket TCP.

## 📌 Objetivo

O **Legenda** foi criado para apoiar acessibilidade e acompanhamento de falas em tempo real, permitindo que outros programas, telas, painéis ou interfaces recebam o texto reconhecido e exibam como legenda.

Ele pode ser usado em:

- palestras;
- aulas;
- apresentações;
- eventos presenciais;
- sistemas de acessibilidade;
- painéis de legenda em rede local;
- protótipos de transcrição ao vivo.

## ⚙️ Funcionamento geral

O script principal é:

```text
bin/srvouve.py
```

Fluxo atual:

1. Abre um servidor TCP na porta `8097`.
2. Aguarda clientes se conectarem.
3. Captura áudio pelo microfone local.
4. Usa `speech_recognition` para enviar o áudio ao reconhecedor Google.
5. Reconhece a fala em `pt-BR`.
6. Coloca o texto reconhecido em uma fila interna.
7. Envia cada texto reconhecido para todos os clientes TCP conectados.

## 🧱 Estrutura atual

```text
legenda/
├── README.md
└── bin/
    └── srvouve.py
```

## 🐍 Requisitos

- Python 3.
- Microfone funcionando no computador onde o servidor será executado.
- Acesso à internet para uso do reconhecimento Google via biblioteca `speech_recognition`.
- Porta TCP `8097` liberada na máquina local ou na rede.

Bibliotecas Python usadas diretamente pelo script:

```python
speech_recognition
socket
threading
queue
```

A biblioteca `socket`, `threading` e `queue` fazem parte da biblioteca padrão do Python. A dependência externa principal é `SpeechRecognition`.

Em muitos ambientes também será necessário instalar o suporte de áudio do microfone, normalmente via `PyAudio`.

## 📦 Instalação

Clone o repositório:

```bash
git clone https://github.com/marcelomaurin/legenda.git
cd legenda
```

Crie um ambiente virtual, se desejar:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Instale as dependências principais:

```bash
pip install SpeechRecognition PyAudio
```

Em Linux, se houver erro ao instalar ou usar o `PyAudio`, instale antes os pacotes de áudio do sistema. Em distribuições Debian/Ubuntu/Raspberry Pi OS, normalmente:

```bash
sudo apt update
sudo apt install python3-pyaudio portaudio19-dev
```

Depois tente novamente:

```bash
pip install SpeechRecognition PyAudio
```

## ▶️ Execução do servidor

Execute:

```bash
python3 bin/srvouve.py
```

Ao iniciar, o programa:

- abre o servidor na porta `8097`;
- ajusta o ruído ambiente por aproximadamente 1 segundo;
- começa a ouvir frases pelo microfone;
- envia cada frase reconhecida aos clientes conectados.

Exemplo de mensagens no terminal:

```text
Servidor escutando na porta 8097
Ajuste do ruído de fundo. Aguarde...
Fale algo:
Iniciou análise
Você disse: teste de legenda
```

## 🔌 Conectando um cliente TCP

Qualquer cliente TCP pode se conectar ao servidor na porta `8097`.

Exemplo usando `nc`/`netcat` na mesma máquina:

```bash
nc 127.0.0.1 8097
```

Em outra máquina da rede, use o IP do computador que está rodando o servidor:

```bash
nc IP_DO_SERVIDOR 8097
```

Quando o servidor reconhecer uma fala, o texto será enviado para os clientes conectados.

## 🧪 Exemplo de cliente Python

```python
import socket

HOST = '127.0.0.1'
PORT = 8097

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    while True:
        data = s.recv(4096)
        if not data:
            break
        print(data.decode('utf-8'))
```

Salve como `cliente_legenda.py` e execute:

```bash
python3 cliente_legenda.py
```

## 🗣️ Idioma do reconhecimento

O idioma configurado no código atual é:

```python
language='pt-BR'
```

Isso significa que o servidor está preparado inicialmente para reconhecer português do Brasil.

Para outro idioma, altere essa configuração no arquivo `bin/srvouve.py`.

Exemplos:

```python
language='en-US'
language='es-ES'
language='pt-PT'
```

## 🌐 Porta utilizada

A porta atual do servidor é:

```text
8097
```

Ela é definida no trecho de configuração do socket em `bin/srvouve.py`.

Caso precise usar outra porta, altere o valor no `bind` do servidor.

## 🧵 Modelo de execução

O servidor usa threads para separar responsabilidades:

- uma thread aceita conexões de clientes;
- uma thread envia mensagens da fila para os clientes;
- uma thread por cliente mantém a conexão aberta;
- o loop principal captura e reconhece o áudio.

A fila interna mantém até 10 textos recentes antes do envio.

## ✅ Recursos atuais

- Captura de áudio via microfone.
- Ajuste inicial de ruído ambiente.
- Reconhecimento de voz em português do Brasil.
- Servidor TCP para múltiplos clientes.
- Envio de texto reconhecido para todos os clientes conectados.
- Remoção automática de clientes desconectados.

## ⚠️ Limitações atuais

- Depende de internet para o reconhecimento Google usado pela biblioteca `speech_recognition`.
- Não possui interface gráfica própria neste repositório.
- Não salva transcrições em arquivo na implementação atual.
- Não possui autenticação de clientes TCP.
- Não criptografa a comunicação TCP.
- Não possui protocolo estruturado com JSON; envia texto puro em UTF-8.
- Não possui configuração externa para porta, idioma ou tempo de captura.
- O reconhecimento é feito em blocos de fala com limite de tempo, não como streaming contínuo real palavra por palavra.

## 🔒 Cuidados de segurança

Como o servidor escuta em `0.0.0.0`, ele aceita conexões vindas da rede, não apenas da máquina local.

Use com cuidado em redes públicas. Para uso local, recomenda-se:

- executar em rede confiável;
- bloquear a porta no firewall quando não for necessária;
- alterar o `bind` para `127.0.0.1` se desejar aceitar apenas conexões locais;
- adicionar autenticação se for expor o serviço em rede.

## 🛠️ Melhorias sugeridas

Possíveis evoluções para o projeto:

- Criar arquivo `requirements.txt`.
- Criar configuração externa para porta, idioma e tempo de captura.
- Adicionar salvamento automático da transcrição.
- Criar uma interface cliente para exibir legenda em tela cheia.
- Criar modo de legenda para projetor ou segunda tela.
- Adicionar protocolo JSON com timestamp.
- Adicionar autenticação simples para clientes.
- Permitir reconhecimento offline usando modelos locais.
- Criar serviço systemd para Linux/Raspberry Pi.
- Criar instalador para Windows.

## 🧰 Solução de problemas

### Erro ao acessar o microfone

Verifique se o microfone está conectado e se o sistema operacional liberou permissão de uso.

### Erro relacionado ao PyAudio

Instale as dependências de áudio do sistema operacional e reinstale o pacote Python.

### Nenhum cliente recebe texto

Verifique:

- se o servidor está rodando;
- se o cliente conectou na porta `8097`;
- se o firewall está bloqueando a porta;
- se o IP usado pelo cliente é o IP correto do servidor.

### Reconhecimento falha com erro de API

O reconhecimento atual depende de serviço externo. Verifique a conexão com a internet.

## 📄 Licença

Nenhuma licença foi identificada no repositório no momento desta documentação. Recomenda-se adicionar um arquivo `LICENSE` para definir claramente as permissões de uso, modificação e distribuição.

## 👤 Autor

Projeto mantido por [Marcelo Maurin Martins](https://github.com/marcelomaurin).
