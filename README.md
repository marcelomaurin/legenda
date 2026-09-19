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
- testes unitários e CI leve no GitHub Actions;
- painel administrativo de telemetria em tempo real;
- métricas de CPU, memória, filas, clientes, idiomas e latência STT.

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
http://SERVIDOR:8080/?room=principal#token=TOKEN
```

O token contém sala, papel e expiração, assinados com HMAC-SHA256. O servidor
rejeita token adulterado, expirado ou emitido para outra sala. O token fica no
fragmento `#token=`, evitando envio no request HTTP e reduzindo exposição em
logs do servidor web.

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


## Painel administrativo

O painel está em:

```text
web/admin.html
```

Ele usa o mesmo WebSocket do serviço principal, mas exige token com papel
`admin`.

Gere um convite administrativo:

```bash
python bin/generate_room_token.py principal \
  --role admin \
  --ttl 7200 \
  --web-url http://SERVIDOR:8080/admin.html
```

Abra a URL gerada no navegador. O token continua no fragmento `#token=`.

Depois da autenticação o painel envia:

```json
{
  "type": "subscribe_telemetry"
}
```

O servidor só aceita essa assinatura quando o papel autenticado é `admin`.

O painel acompanha:

- clientes WebSocket conectados;
- clientes TCP/Lazarus;
- distribuição de participantes por idioma;
- distribuição por papel;
- número de eventos parciais e finais;
- latência média do STT;
- latência P95 do STT;
- tamanho e capacidade das filas;
- erros de STT;
- erros de tradução;
- parciais descartados;
- eventos descartados;
- uptime;
- engine ativa;
- CPU do processo;
- memória residente do processo.

O intervalo padrão é:

```json
"telemetry_interval_seconds": 2
```

A telemetria é enviada somente aos administradores que explicitamente se
inscreverem. Participantes normais continuam recebendo apenas legendas.

CPU e memória são obtidas com `psutil`. Caso essa biblioteca não esteja
disponível, o restante do painel continua funcionando e esses dois indicadores
aparecem como indisponíveis.

### Exemplo de evento de telemetria

```json
{
  "type": "telemetry",
  "room": "principal",
  "session_id": "...",
  "engine": "faster-whisper",
  "uptime_seconds": 845,
  "events": {
    "partial": 183,
    "final": 61,
    "total": 244,
    "dropped": 0
  },
  "stt": {
    "errors": 0,
    "dropped_partials": 2,
    "latency_avg_ms": 412.5,
    "latency_p95_ms": 680
  },
  "clients": {
    "tcp": 1,
    "websocket": 18,
    "by_language": {
      "pt-BR": 12,
      "en": 4,
      "es": 2
    }
  }
}
```


## Benchmark de reconhecimento

O projeto inclui uma ferramenta para comparar engines e modelos usando o mesmo
conjunto de áudios e transcrições de referência:

```text
bin/benchmark_stt.py
```

O manifesto é JSON Lines. Exemplo:

```json
{"id":"01","audio":"benchmark_samples/01.wav","reference":"bom dia a todos"}
{"id":"02","audio":"benchmark_samples/02.wav","reference":"vamos iniciar a reunião"}
```

Os WAVs devem ser mono PCM 16-bit. Para faster-whisper, recomenda-se 16 kHz para
manter o mesmo formato usado pelo servidor.

### Testar um modelo

```bash
python bin/benchmark_stt.py benchmark_manifest.jsonl \
  --engine faster-whisper \
  --model tiny \
  --device cpu \
  --compute-type int8
```

Repita com outros modelos:

```bash
python bin/benchmark_stt.py benchmark_manifest.jsonl \
  --engine faster-whisper --model base --device cpu --compute-type int8

python bin/benchmark_stt.py benchmark_manifest.jsonl \
  --engine faster-whisper --model small --device cpu --compute-type int8
```

Em CUDA:

```bash
python bin/benchmark_stt.py benchmark_manifest.jsonl \
  --engine faster-whisper \
  --model small \
  --device cuda \
  --compute-type float16
```

Cada execução produz:

```text
benchmark_results/
├── DATA-engine-model.json
└── DATA-engine-model.csv
```

O JSON contém:

- WER médio;
- latência média;
- latência P95;
- RTF médio;
- tempo total de áudio;
- tempo total de inferência;
- resultado por amostra;
- hipótese reconhecida;
- referência utilizada.

### WER

O benchmark usa Word Error Rate:

```text
WER = (substituições + inserções + deleções) / palavras da referência
```

Quanto menor, melhor.

Exemplo:

```text
Referência : bom dia a todos
Hipótese   : bom dia para todos

Substituições = 1
Palavras       = 4

WER = 1 / 4 = 0,25
```

### RTF

RTF é o Real-Time Factor:

```text
RTF = tempo de inferência / duração do áudio
```

Interpretação:

```text
RTF < 1,0  -> processa mais rápido que o tempo real
RTF = 1,0  -> acompanha exatamente o tempo real
RTF > 1,0  -> não consegue acompanhar tempo real
```

Exemplo:

```text
áudio       = 10 s
inferência  = 2 s
RTF         = 0,20
```

### Comparar resultados

Use:

```text
bin/compare_benchmarks.py
```

Exemplo:

```bash
python bin/compare_benchmarks.py \
  benchmark_results/tiny.json \
  benchmark_results/base.json \
  benchmark_results/small.json
```

A saída resume:

```text
ENGINE             MODEL        DEVICE      WER    LAT(ms)      P95      RTF
faster-whisper     tiny         cpu       0.1520      180.0    240.0   0.1200
faster-whisper     base         cpu       0.0980      310.0    420.0   0.2100
faster-whisper     small        cpu       0.0610      690.0    910.0   0.4600
```

Esses números são apenas um exemplo de formato, não resultados medidos do
projeto.

O comparador também gera:

```text
benchmark_results/comparison.csv
```

### Metodologia recomendada

Para uma avaliação útil, utilize o mesmo conjunto de gravações em todos os
modelos, incluindo:

- fala limpa;
- ambiente com ruído;
- fala mais rápida;
- diferentes locutores;
- palavras técnicas;
- nomes próprios;
- siglas;
- gravação em distância maior do microfone.

Para o contexto técnico do Legenda, também é interessante criar um subconjunto
com termos institucionais ou especializados e repetir o teste com e sem
`hotwords`.

Assim a escolha de modelo deixa de ser subjetiva e pode ser justificada por uma
relação mensurável entre precisão e custo computacional.
