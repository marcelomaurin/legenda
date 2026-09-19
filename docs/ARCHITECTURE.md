# Legenda v2 — arquitetura

## Objetivo

O Legenda v2 transforma o protótipo original em uma plataforma de legendagem
em tempo real com captura segmentada por voz, motores STT intercambiáveis,
eventos incrementais e múltiplos clientes.

## Pipeline implementado

```text
PyAudio
  |
  | PCM mono 16-bit / 16 kHz
  v
WebRTC VAD
  |
  +-- início de fala
  +-- partial snapshots
  +-- fim de fala
  |
  v
fila de transcrição
  |
  v
SpeechEngine
  |
  +-- GoogleSpeechEngine
  |
  +-- FasterWhisperSpeechEngine
         |
         +-- Silero VAD interno opcional
         +-- hotwords
         +-- CPU ou CUDA
  |
  v
CaptionEvent
  |
  +-- TCP JSONL --> Lazarus / somente final
  +-- WebSocket -> Web / partial + final
  +-- JSONL ----> arquivo / somente final
  +-- SRT/VTT --> legendas sincronizadas
  +-- WAV ------> áudio temporal da sessão
```

## Por que existem dois níveis de VAD

O primeiro VAD trabalha diretamente na captura e decide quando uma fala começa
e termina. Isso reduz áudio inútil e possibilita eventos parciais.

Quando o motor é faster-whisper, o filtro VAD interno pode permanecer ligado como
segunda barreira contra silêncio e ruído dentro do segmento já detectado.

## SpeechEngine

`bin/stt_engines.py` define a interface:

```text
transcribe_pcm(pcm, sample_rate, sample_width) -> TranscriptionResult
```

Dessa forma rede, interface e persistência não dependem do fornecedor de STT.

## Captura VAD

`bin/vad_capture.py` usa frames de 30 ms por padrão. A máquina de estados possui:

```text
SILÊNCIO
   |
   | proporção mínima de frames com voz
   v
FALA
   |
   +-- gera snapshots parciais
   |
   | proporção mínima de frames sem voz
   v
FINALIZA SEGMENTO
```

Um `max_utterance_ms` força o fechamento de falas muito longas.

## Eventos incrementais

Todos os snapshots da mesma fala compartilham `utterance_id`.

Partial:

```json
{
  "type": "partial",
  "utterance_id": "4a72fd981211",
  "final": false,
  "text": "vamos iniciar a"
}
```

Final:

```json
{
  "type": "caption",
  "utterance_id": "4a72fd981211",
  "final": true,
  "text": "Vamos iniciar a reunião."
}
```

## Métricas incorporadas ao protocolo

O evento contém:

- `start_ms`;
- `end_ms`;
- `latency_ms`;
- `engine`;
- `sequence`.

Isso permite medir latência e comparar engines posteriormente.

## Concorrência

A captura não executa inferência diretamente. Ela coloca trabalhos numa fila
dedicada. Isso impede que uma inferência lenta bloqueie imediatamente a leitura
do microfone.

Atualizações parciais podem ser descartadas sob pressão. Eventos finais recebem
prioridade de enfileiramento porque representam a transcrição consolidada.

## Compatibilidade

O Lazarus continua no TCP 8097 e recebe apenas eventos finais. O navegador usa
WebSocket 8098 e recebe partial/final.

## Exportação e diarização

Cada evento final é acrescentado também aos arquivos SRT e WebVTT. O áudio final
dos segmentos é reconstruído em um WAV de sessão preservando os offsets de
`start_ms`.

A diarização é executada depois da sessão por `bin/diarize_session.py`. O
pipeline `pyannote/speaker-diarization-community-1` trabalha sobre o WAV completo
e o resultado exclusivo de diarização é reconciliado com cada legenda pelo maior
tempo de sobreposição. Isso evita tentar identificar locutores a partir de frases
isoladas.

## Próximas extensões

1. salas e autenticação;
4. tradução simultânea;
5. painel de telemetria;
6. benchmark WER/latência;
7. múltiplos workers STT quando o engine permitir;
8. configuração de dispositivo de entrada pela interface.
