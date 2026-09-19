# Legenda v2

Plataforma de legendagem e transcrição em tempo real para palestras, aulas,
reuniões, apresentações e cenários de acessibilidade.

A versão 2 substitui a captura em blocos fixos por uma arquitetura baseada em
frames de áudio, VAD, motores STT intercambiáveis e eventos parciais/finais.

## Arquitetura

```text
Microfone
   |
   v
PCM 16 kHz / 30 ms
   |
   v
WebRTC VAD
   |
   +--> partial snapshots
   |
   +--> segmento final
            |
            v
      SpeechEngine
       /       \
 Google     faster-whisper
                |
                +--> Silero VAD interno opcional
            |
            v
       CaptionEvent v2
            |
            +-- TCP 8097 / JSONL --> Lazarus (somente final)
            +-- WebSocket 8098 ---> navegador (partial + final)
            +-- JSONL ------------> histórico (somente final)
```

## Recursos implementados

- detecção de atividade de voz em frames curtos;
- começo/fim de fala por VAD;
- transcrição parcial durante a fala;
- transcrição final consolidada;
- motor Google preservado como fallback;
- faster-whisper local;
- filtro Silero VAD opcional dentro do faster-whisper;
- hotwords/contexto terminológico;
- `utterance_id`;
- timestamps relativos de início/fim;
- latência de cada inferência;
- protocolo JSON versionado;
- TCP e WebSocket;
- cliente Lazarus compatível;
- cliente web responsivo e acessível;
- persistência JSONL por sessão.

## Instalação

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

Copie a configuração:

```bash
cp config.example.json config.json
```

No Windows:

```bat
copy config.example.json config.json
```

## Escolha do motor STT

### Whisper local

```json
"stt_engine": "faster-whisper",
"whisper_model": "small",
"whisper_device": "cpu",
"whisper_compute_type": "int8"
```

Com GPU NVIDIA compatível:

```json
"whisper_device": "cuda",
"whisper_compute_type": "float16"
```

### Google

```json
"stt_engine": "google"
```

Se o motor remoto for usado e você quiser evitar chamadas intermediárias:

```json
"partial_enabled": false
```

## Hotwords / vocabulário contextual

```json
"hotwords": "ANVISA LifeShock Ribeirão Preto desfibrilador cardioversor"
```

O campo é usado pelo motor faster-whisper para favorecer termos esperados.

## VAD

Configuração padrão:

```json
"sample_rate": 16000,
"vad_frame_ms": 30,
"vad_mode": 2,
"vad_padding_ms": 300,
"vad_start_ratio": 0.6,
"vad_end_ratio": 0.8
```

O `vad_mode` varia de 0 a 3. Valores maiores tornam a detecção mais agressiva
contra ruído.

## Partial e final

Durante a fala o navegador pode receber:

```json
{
  "type": "partial",
  "utterance_id": "4a72fd981211",
  "text": "vamos iniciar a",
  "final": false
}
```

Ao detectar o fim da fala:

```json
{
  "type": "caption",
  "utterance_id": "4a72fd981211",
  "text": "Vamos iniciar a reunião.",
  "final": true
}
```

O cliente Lazarus recebe apenas o evento final para evitar oscilação da interface.

## Execução

```bash
python bin/srvouve.py
```

Por padrão:

- TCP: `8097`;
- WebSocket: `8098`;
- áudio: mono PCM 16 kHz;
- STT: faster-whisper;
- modelo: `small`;
- transcrições: `transcripts/`.

## Cliente web

```bash
python -m http.server 8080 -d web
```

Abra:

```text
http://127.0.0.1:8080
```

Para outro computador:

```text
http://HOST_WEB:8080/?host=IP_DO_SERVIDOR&port=8098
```

## Evento completo

```json
{
  "version": 2,
  "type": "caption",
  "session_id": "20260919-114700-a1b2c3d4",
  "utterance_id": "4a72fd981211",
  "sequence": 8,
  "timestamp": "2026-09-19T11:47:02.120-03:00",
  "language": "pt",
  "text": "Vamos iniciar a reunião.",
  "final": true,
  "start_ms": 15220,
  "end_ms": 18460,
  "latency_ms": 384,
  "engine": "faster-whisper"
}
```

## Próximas etapas

- exportação SRT/WebVTT;
- identificação de locutores;
- tradução simultânea;
- salas;
- painel de métricas;
- benchmark WER e latência;
- seleção de dispositivo de áudio pela interface.
