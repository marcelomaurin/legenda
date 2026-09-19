# Legenda v2

Plataforma de legendagem e transcrição em tempo real para palestras, aulas,
reuniões, apresentações e cenários de acessibilidade.

A versão 2 moderniza o projeto original sem abandonar o cliente desktop Lazarus.
O servidor passa a trabalhar com eventos estruturados, persistência por sessão e
distribuição simultânea por TCP e WebSocket.

## Arquitetura atual

```text
Microfone
   |
   v
SpeechRecognition
   |
   v
CaptionEvent v2
   |
   +-- TCP 8097 / JSON Lines --> cliente Lazarus
   |
   +-- WebSocket 8098 --------> navegador
   |
   +-- JSONL -----------------> histórico da sessão
```

## Principais melhorias da v2

- protocolo JSON versionado;
- delimitador correto de mensagens no TCP;
- `session_id`, sequência, timestamp e idioma;
- lista de clientes protegida para acesso concorrente;
- uso de `sendall`;
- histórico de transcrição em JSON Lines;
- configuração externa;
- WebSocket para navegadores;
- cliente web responsivo e acessível;
- reconexão automática no navegador;
- compatibilidade temporária do Lazarus com texto puro;
- remoção da segunda conexão TCP legada;
- remoção do código herdado do projeto Doctor.

## Instalação do servidor

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

No Windows:

```bat
.venv\Scripts\activate
pip install -r requirements.txt
```

Se necessário, copie a configuração de exemplo:

```bash
cp config.example.json config.json
```

No Windows:

```bat
copy config.example.json config.json
```

## Execução

```bash
python bin/srvouve.py
```

Por padrão:

- TCP: `8097`;
- WebSocket: `8098`;
- idioma: `pt-BR`;
- transcrições: `transcripts/`.

## Cliente web

Sirva a pasta `web`:

```bash
python -m http.server 8080 -d web
```

Acesse:

```text
http://127.0.0.1:8080
```

Para apontar o navegador para outro servidor:

```text
http://HOST_WEB:8080/?host=IP_DO_SERVIDOR&port=8098
```

## Evento de legenda

```json
{
  "version": 2,
  "type": "caption",
  "session_id": "20260919-114700-a1b2c3d4",
  "sequence": 1,
  "timestamp": "2026-09-19T11:47:02.120-03:00",
  "language": "pt-BR",
  "text": "Vamos iniciar a reunião.",
  "final": true
}
```

No TCP cada evento termina com `\n`. No WebSocket cada evento ocupa um frame.

## Estrutura

```text
legenda/
├── bin/
│   └── srvouve.py
├── src/
│   └── cliente Lazarus
├── web/
│   └── index.html
├── docs/
│   └── ARCHITECTURE.md
├── config.example.json
└── requirements.txt
```

## Próxima evolução

A arquitetura foi preparada para receber:

- VAD para detectar início/fim de fala;
- Whisper local / whisper.cpp / faster-whisper;
- transcrição parcial e definitiva;
- diarização de locutores;
- vocabulário contextual;
- tradução;
- exportação SRT/WebVTT;
- métricas de latência e WER;
- salas e múltiplas sessões.

Consulte `docs/ARCHITECTURE.md` para detalhes.
