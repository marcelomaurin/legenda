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
- persistência JSONL por sessão;
- exportação automática SRT e WebVTT;
- gravação WAV da sessão preservando a linha do tempo;
- diarização opcional pós-sessão com pyannote Community-1;
- sala web autenticada por token HMAC com validade;
- convites assinados por URL;
- seleção de idioma por participante;
- tradução plugável com cache;
- suporte a LibreTranslate local/remoto;
- testes unitários e CI leve no GitHub Actions.

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

## Arquivos gerados por sessão

Com a configuração padrão, a pasta `transcripts/` recebe:

```text
<session_id>.jsonl
<session_id>.srt
<session_id>.vtt
<session_id>.wav
```

O WAV é montado com os intervalos de silêncio preservados, permitindo reconciliar
corretamente os timestamps da transcrição com a diarização.

## Diarização de locutores

A diarização é opcional e fica separada das dependências básicas:

```bash
pip install -r requirements-diarization.txt
```

O pipeline padrão usa:

```text
pyannote/speaker-diarization-community-1
```

Depois de encerrar uma sessão:

```bash
python bin/diarize_session.py SESSION_ID --token SEU_TOKEN_HF
```

O comando gera:

```text
SESSION_ID.diarized.jsonl
SESSION_ID.diarized.srt
SESSION_ID.diarized.vtt
```

Os eventos passam a receber o campo `speaker`, definido pelo maior intervalo de
sobreposição entre a fala transcrita e a diarização.

## Próximas etapas

- tradução simultânea;
- salas;
- painel de métricas;
- benchmark WER e latência;
- seleção de dispositivo de áudio pela interface.


## Salas e autenticação

Cada processo do servidor representa uma sala de áudio ativa. A configuração:

```json
"active_room": "principal",
"room_name": "Sala principal",
"room_auth_required": true,
"room_auth_secret": "TROQUE-ESTA-CHAVE-POR-UMA-CHAVE-SEGURA-32C"
```

O segredo real deve ficar apenas em `config.json`, que já é ignorado pelo Git.

Gere um convite com validade:

```bash
python bin/generate_room_token.py principal \
  --ttl 7200 \
  --web-url http://SERVIDOR:8080/
```

O comando imprime o token e uma URL semelhante a:

```text
http://SERVIDOR:8080/?room=principal&token=TOKEN
```

O token contém sala, papel e expiração, assinados com HMAC-SHA256. O servidor
rejeita token adulterado, expirado ou emitido para outra sala.

Papéis previstos:

```text
viewer
presenter
admin
```

Nesta versão, o papel já é autenticado e entregue ao cliente; permissões
administrativas específicas podem ser acrescentadas sobre essa base.

### Várias salas ao mesmo tempo

Uma instância captura um fluxo de áudio e publica uma sala ativa. Para dois
auditórios simultâneos, execute duas instâncias com `active_room`, dispositivo
de áudio e portas diferentes. Isso evita misturar duas fontes físicas em uma
mesma sessão.

## Tradução simultânea

Os clientes escolhem o idioma individualmente:

```json
"allowed_languages": ["pt-BR", "en", "es"]
```

A tradução é feita apenas na distribuição WebSocket. O JSONL/SRT/VTT original
continua preservando a transcrição de origem.

Para usar LibreTranslate:

```json
"translation_provider": "libretranslate",
"translation_endpoint": "http://127.0.0.1:5000",
"translation_api_key": ""
```

Se o idioma solicitado for o mesmo idioma de origem, nenhuma chamada de tradução
é feita. Traduções repetidas usam cache em memória.

Por padrão:

```json
"translate_partials": false
```

Assim, clientes em outro idioma recebem apenas frases finais traduzidas, evitando
multiplicar custo e latência durante as atualizações parciais. Se o tradutor local
for rápido o suficiente, essa opção pode ser ativada.

O navegador pode trocar de idioma sem reconectar. Ele envia:

```json
{
  "type": "set_language",
  "language": "es"
}
```

## Protocolo de entrada WebSocket

A primeira mensagem do navegador é obrigatoriamente:

```json
{
  "type": "auth",
  "room": "principal",
  "token": "TOKEN_ASSINADO",
  "language": "pt-BR"
}
```

Depois da validação, o servidor responde com `welcome`, contendo sala, sessão,
papel autenticado e idiomas disponíveis.

## Testes

Os testes leves não carregam Whisper, PyAudio ou PyTorch:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Eles verificam:

- assinatura e expiração dos tokens;
- isolamento entre salas;
- detecção de adulteração;
- geração SRT/WebVTT;
- normalização de idioma;
- cache de tradução.

O workflow em `.github/workflows/tests.yml` executa essa suíte em push e pull
request.
