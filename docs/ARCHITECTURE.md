# Legenda v2 — arquitetura

## Objetivo

O Legenda v2 evolui o protótipo original para uma plataforma de legendagem e
transcrição em tempo real. A primeira etapa mantém o reconhecimento Google já
existente, mas desacopla transporte, evento e apresentação para permitir novos
motores de STT, VAD, transcrição incremental, diarização, tradução e clientes web.

## Fluxo atual da v2

```text
Microfone
   |
SpeechRecognition
   |
CaptionEvent
   |
fila thread-safe
   |
JSON Lines / TCP :8097
   |
cliente Lazarus
   +--> janela de legenda
   +--> histórico
```

## Protocolo CaptionEvent v2

Cada mensagem ocupa uma linha UTF-8 terminada em `\n`.

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

O uso de JSON Lines resolve a falta de enquadramento do TCP original e permite
evoluir o protocolo sem depender da interface gráfica.

## Compatibilidade

O cliente Lazarus aceita eventos JSON v2 e mantém fallback para texto puro,
permitindo conectar temporariamente a servidores antigos.

A segunda conexão TCP na porta 8098 foi retirada. Ela era legado de outro projeto
e não fazia parte do servidor de legendas.

## Persistência

Eventos finais são gravados em `transcripts/<session_id>.jsonl`.
Isso permitirá gerar TXT, SRT e WebVTT sem alterar a captura de áudio.

## Próximas camadas

1. interface comum de motores STT;
2. whisper.cpp/faster-whisper local;
3. VAD para segmentação por fala;
4. eventos `partial` e `final`;
5. WebSocket;
6. cliente web responsivo;
7. exportação SRT/WebVTT;
8. diarização de locutores;
9. tradução simultânea;
10. métricas de latência e WER.
