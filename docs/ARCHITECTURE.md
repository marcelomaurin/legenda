# Legenda v2 — arquitetura

## Objetivo

O Legenda v2 evolui o protótipo original para uma plataforma de legendagem e
transcrição em tempo real. A primeira etapa mantém o reconhecimento Google já
existente, mas desacopla transporte, evento e apresentação para permitir novos
motores de STT, VAD, transcrição incremental, diarização, tradução e clientes web.

## Fluxo implementado

```text
Microfone
   |
SpeechRecognition
   |
CaptionEvent
   |
fila thread-safe
   |
   +---------------- TCP/JSONL :8097 ----------------> Lazarus
   |
   +---------------- WebSocket :8098 ----------------> navegador
   |
   +---------------- JSONL --------------------------> transcripts/
```

## Protocolo CaptionEvent v2

No TCP, cada mensagem ocupa uma linha UTF-8 terminada em `\n`.
No WebSocket, cada frame contém um objeto JSON.

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

## Cliente Lazarus

O desktop utiliza TCP 8097 e aceita o protocolo JSON v2, mantendo fallback
temporário para texto puro. A antiga segunda conexão TCP e o acoplamento com o
projeto Doctor foram removidos.

## Cliente web

`web/index.html` recebe eventos pelo WebSocket 8098 e oferece reconexão
automática, fonte responsiva, aumento/redução da fonte, modo tela cheia,
`aria-live`, sessão e horário.

Para desenvolvimento local:

```bash
python -m http.server 8080 -d web
```

Depois abra `http://127.0.0.1:8080`.

## Persistência

Eventos finais são gravados em `transcripts/<session_id>.jsonl`. A estrutura
permite gerar TXT, SRT e WebVTT posteriormente sem alterar a captura.

## Próximas camadas

1. interface comum de motores STT;
2. whisper.cpp/faster-whisper local;
3. VAD;
4. eventos partial/final;
5. exportação SRT/WebVTT;
6. salas/sessões;
7. diarização;
8. tradução;
9. métricas de latência e WER;
10. painel administrativo.
