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

## Validações antes de produção

Os principais recursos planejados para a v2 já estão implementados. Antes de
uso em produção, ainda é recomendável:

- coletar corpus real suficiente para obter métricas representativas;
- validar o modelo STT escolhido no hardware de destino;
- testar HTTPS/WSS no ambiente final;
- executar teste prolongado de estabilidade com várias horas de áudio;
- validar o cliente Lazarus compilado na versão de Lazarus usada em produção.


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


## Dispositivos de áudio

Para listar os microfones e interfaces de entrada disponíveis:

```bash
python bin/list_audio_devices.py
```

Exemplo de saída:

```json
[
  {
    "index": 1,
    "name": "USB Audio Device",
    "max_input_channels": 2,
    "default_sample_rate": 48000,
    "is_default": true
  }
]
```

O dispositivo usado pela instância é definido por:

```json
"input_device_index": 1
```

Quando o valor é `null`, o PyAudio usa o dispositivo padrão do sistema.

O painel administrativo também possui a seção **Áudio**. Um administrador pode:

- atualizar a lista de dispositivos;
- visualizar o dispositivo atualmente configurado;
- escolher outro dispositivo;
- salvar o novo índice.

A alteração é persistida no arquivo de configuração da instância. Para segurança,
o stream ativo não é trocado durante uma sessão: o painel informa que é
necessário reiniciar a instância.

## Múltiplas salas / instâncias

O arquivo de exemplo:

```text
instances.example.json
```

mostra duas salas independentes:

```text
Conselho de Saúde
  TCP 8097
  WebSocket 8098
  microfone 1

Auditório
  TCP 8197
  WebSocket 8198
  microfone 2
```

Copie o exemplo:

```bash
cp instances.example.json instances.json
```

e inicie:

```bash
python bin/orchestrator.py instances.json
```

O orquestrador:

- lê uma configuração base;
- aplica overrides por sala;
- gera configurações runtime separadas;
- inicia um processo `srvouve.py` por sala;
- define `LEGENDA_CONFIG` para cada processo;
- monitora os processos;
- reinicia automaticamente uma instância que encerrar inesperadamente;
- encerra as salas de forma ordenada com Ctrl+C.

Os arquivos runtime ficam, por padrão, em:

```text
.runtime/instances/
```

e não são versionados pelo Git.

### Exemplo de definição

```json
{
  "base_config": "config.json",
  "runtime_dir": ".runtime/instances",
  "instances": [
    {
      "name": "conselho",
      "overrides": {
        "active_room": "conselho",
        "room_name": "Conselho de Saúde",
        "port": 8097,
        "websocket_port": 8098,
        "input_device_index": 1,
        "transcript_dir": "transcripts/conselho"
      }
    },
    {
      "name": "auditorio",
      "overrides": {
        "active_room": "auditorio",
        "room_name": "Auditório",
        "port": 8197,
        "websocket_port": 8198,
        "input_device_index": 2,
        "transcript_dir": "transcripts/auditorio"
      }
    }
  ]
}
```

Essa separação permite que uma falha, saturação de fila ou troca de dispositivo
em uma sala não interrompa as demais.


## Corpus de referência do Legenda

O repositório agora contém um corpus textual estruturado em:

```text
corpus/
├── README.md
└── references/
    ├── clean.jsonl
    ├── noise.jsonl
    ├── fast.jsonl
    ├── distance.jsonl
    ├── names.jsonl
    ├── acronyms.jsonl
    ├── technical.jsonl
    └── mixed.jsonl
```

As categorias permitem avaliar separadamente onde o reconhecimento perde
qualidade:

- `clean`: fala limpa;
- `noise`: ruído de fundo;
- `fast`: fala rápida;
- `distance`: maior distância do microfone;
- `names`: nomes próprios e localidades;
- `acronyms`: siglas;
- `technical`: termos técnicos;
- `mixed`: combinação de dificuldades.

Os arquivos de áudio devem ser colocados em:

```text
corpus/audio/<categoria>/<id>.wav
```

Por exemplo:

```text
corpus/audio/technical/technical-001.wav
```

Os áudios não são versionados pelo Git.

### Validar o corpus

```bash
python bin/validate_corpus.py --corpus-dir corpus
```

O validador verifica:

- IDs duplicados;
- categorias inválidas;
- referências vazias;
- presença dos áudios;
- WAV mono;
- PCM 16-bit;
- sample rate;
- quantidade de locutores;
- cobertura por categoria.

O formato recomendado é:

```text
mono
PCM 16-bit
16 kHz
```

### Gerar o manifesto

Quando as gravações estiverem disponíveis:

```bash
python bin/prepare_corpus_manifest.py \
  --corpus-dir corpus \
  --output corpus/manifest.jsonl
```

Para exigir que todas as referências tenham áudio:

```bash
python bin/prepare_corpus_manifest.py \
  --corpus-dir corpus \
  --output corpus/manifest.jsonl \
  --strict
```

O manifesto resultante já pode ser usado diretamente:

```bash
python bin/benchmark_stt.py corpus/manifest.jsonl \
  --engine faster-whisper \
  --model small \
  --device cpu \
  --compute-type int8
```

### Resultado por categoria

Além do resultado global, o benchmark agora calcula:

```text
CATEGORIA          N      WER    LAT(ms)        P95      RTF
clean             ...
noise             ...
names             ...
acronyms          ...
technical         ...
```

Isso permite identificar, por exemplo, um modelo que tenha bom WER global mas
desempenho ruim justamente em siglas ou termos técnicos.

### Política de coleta

As referências textuais podem ser versionadas. Os áudios reais ficam fora do Git.

Para locutores, use identificadores pseudônimos como:

```text
speaker-01
speaker-02
speaker-03
```

Evite dados pessoais desnecessários e registre apenas gravações cuja utilização
no corpus seja autorizada.

Um corpus inicial razoável é de aproximadamente 20 frases por categoria e pelo
menos 3 locutores, crescendo posteriormente sem alterar os critérios de coleta.


## Gestão central do orquestrador

O orquestrador agora expõe uma API HTTP de controle:

```text
GET  /api/health
GET  /api/status
POST /api/start/<instancia>
POST /api/stop/<instancia>
POST /api/restart/<instancia>
```

A configuração fica em `instances.json`:

```json
{
  "control_host": "127.0.0.1",
  "control_port": 8070,
  "control_token": "TOKEN-DE-CONTROLE"
}
```

Quando `control_token` está preenchido, as chamadas exigem:

```text
Authorization: Bearer TOKEN-DE-CONTROLE
```

Por segurança, o exemplo usa `127.0.0.1`. Para administração remota, prefira
publicar essa API atrás de um proxy HTTPS/VPN em vez de expor diretamente a
porta de controle.

O painel central está em:

```text
web/orchestrator.html
```

Exemplo:

```text
http://SERVIDOR:8080/orchestrator.html?api=http://127.0.0.1:8070#token=TOKEN
```

O token permanece no fragmento da URL.

O painel mostra, para cada instância:

- nome;
- sala;
- estado atual;
- estado desejado;
- PID;
- exit code;
- porta TCP;
- porta WebSocket;
- dispositivo de áudio;
- engine;
- modelo.

Também permite:

- iniciar;
- parar;
- reiniciar.

Uma parada administrativa altera `desired_running=false`, portanto o watchdog
não religa a instância. Se um processo marcado para execução encerrar sozinho,
o supervisor continua reiniciando-o automaticamente.

## Serviço systemd

Foram adicionados:

```text
deploy/legenda-orchestrator.service
deploy/install_systemd.sh
```

A instalação pressupõe uma cópia do projeto em `/opt/legenda` com ambiente
virtual já criado.

Exemplo:

```bash
sudo mkdir -p /opt/legenda
# copie/clone o projeto para /opt/legenda

cd /opt/legenda
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp config.example.json config.json
cp instances.example.json instances.json

chmod +x deploy/install_systemd.sh
sudo deploy/install_systemd.sh /opt/legenda
```

O instalador:

- cria o usuário de serviço `legenda` se necessário;
- adiciona o usuário ao grupo `audio`;
- ajusta o diretório da aplicação;
- instala o unit file;
- executa `systemctl daemon-reload`;
- habilita o serviço no boot;
- reinicia o orquestrador.

Comandos úteis:

```bash
sudo systemctl status legenda-orchestrator
sudo systemctl restart legenda-orchestrator
sudo journalctl -u legenda-orchestrator -f
```

O arquivo real `instances.json` é ignorado pelo Git porque pode conter token de
controle e configuração específica de hardware.


## Coleta assistida do corpus pelo navegador

Foram adicionados:

```text
bin/corpus_collection_server.py
web/corpus.html
```

O servidor de coleta usa, por padrão:

```text
127.0.0.1:8060
```

Para iniciar:

```bash
python bin/corpus_collection_server.py \
  --corpus-dir corpus \
  --host 127.0.0.1 \
  --port 8060 \
  --token TOKEN-DE-COLETA
```

Sirva a pasta web:

```bash
python -m http.server 8080 -d web
```

Abra:

```text
http://127.0.0.1:8080/corpus.html?api=http://127.0.0.1:8060#token=TOKEN-DE-COLETA
```

A página:

- carrega as referências cadastradas;
- permite filtrar por categoria;
- mostra frase, ID e locutor pseudônimo;
- solicita acesso ao microfone;
- grava a fala;
- converte o áudio localmente para WAV mono PCM 16-bit em 16 kHz;
- permite ouvir antes de salvar;
- permite refazer;
- envia o WAV para a categoria/ID corretos;
- mostra o progresso de coleta por categoria;
- marca amostras já gravadas.

O servidor só aceita uploads cujo `category` e `id` existam nas referências
do corpus e limita cada upload a 20 MB.

### Endpoints

```text
GET  /api/health
GET  /api/references
POST /api/audio/<category>/<id>
```

Quando um token é configurado, use:

```text
Authorization: Bearer TOKEN-DE-COLETA
```

### Microfone e HTTPS

Em `localhost`, os navegadores normalmente permitem acesso ao microfone em
contexto local. Ao abrir a página a partir de outro computador ou hostname,
navegadores modernos geralmente exigem HTTPS para `getUserMedia`.

Portanto, para coleta remota, publique a interface por HTTPS ou use um túnel/VPN
com terminação TLS. Não exponha diretamente a API de coleta sem autenticação.


## Relatório consolidado de qualidade

Depois de executar vários benchmarks, gere um relatório HTML com:

```bash
python bin/quality_report.py \
  --input-dir benchmark_results \
  --output benchmark_results/report.html
```

O relatório consolida:

- número de execuções;
- WER médio entre execuções;
- RTF médio;
- latência média;
- comparação global por engine/model/device;
- WER, latência média, P95 e RTF por categoria do corpus.

A tabela global é ordenada por WER e, em caso de empate aproximado, por RTF.

O relatório **não cria dados**. Se não existirem JSONs de benchmark válidos,
a página informa explicitamente que ainda não há resultados medidos.

Arquivos aceitos são os JSONs gerados por:

```text
bin/benchmark_stt.py
```

Exemplo de fluxo completo:

```bash
python bin/prepare_corpus_manifest.py --corpus-dir corpus --output corpus/manifest.jsonl

python bin/benchmark_stt.py corpus/manifest.jsonl \
  --engine faster-whisper --model tiny --device cpu --compute-type int8

python bin/benchmark_stt.py corpus/manifest.jsonl \
  --engine faster-whisper --model small --device cpu --compute-type int8

python bin/quality_report.py \
  --input-dir benchmark_results \
  --output benchmark_results/report.html
```

Abra então:

```text
benchmark_results/report.html
```

Esse relatório facilita a escolha do modelo com base em evidência do próprio
ambiente de uso, inclusive identificando categorias em que a precisão cai.


## Instalação no Windows

Foram adicionados:

```text
deploy/install_windows.ps1
deploy/uninstall_windows.ps1
```

O instalador usa o Agendador de Tarefas do Windows para iniciar o orquestrador
automaticamente no boot, sem exigir NSSM ou outro serviço externo.

Exemplo:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\deploy\install_windows.ps1 -AppDir "C:\Legenda"
```

O script:

- cria o ambiente virtual em `.venv`;
- atualiza o pip;
- instala `requirements.txt`;
- cria `config.json` a partir do exemplo, se necessário;
- cria `instances.json` a partir do exemplo, se necessário;
- registra a tarefa `LegendaOrchestrator`;
- configura execução no boot;
- configura reinício automático da tarefa;
- executa sob a conta `SYSTEM`;
- inicia o orquestrador após a instalação.

Para remover somente a tarefa automática:

```powershell
.\deploy\uninstall_windows.ps1
```

Os arquivos de configuração e dados não são apagados pelo desinstalador.

## Gestão de múltiplos nós físicos

Quando as salas estão distribuídas em computadores diferentes, cada computador
continua executando seu próprio `orchestrator.py`.

O servidor central:

```text
bin/fleet_server.py
```

consulta os control planes desses nós e apresenta uma visão consolidada.

Crie:

```bash
cp nodes.example.json nodes.json
```

Exemplo:

```json
{
  "fleet_token": "TOKEN-CENTRAL",
  "timeout_seconds": 3,
  "nodes": [
    {
      "id": "servidor-principal",
      "name": "Servidor principal",
      "url": "http://127.0.0.1:8070",
      "token": "TOKEN-NO-1"
    },
    {
      "id": "auditorio-2",
      "name": "Nó Auditório 2",
      "url": "http://192.168.1.50:8070",
      "token": "TOKEN-NO-2"
    }
  ]
}
```

Inicie:

```bash
python bin/fleet_server.py nodes.json --host 127.0.0.1 --port 8050
```

O painel fica em:

```text
web/fleet.html
```

Exemplo:

```text
http://127.0.0.1:8080/fleet.html?api=http://127.0.0.1:8050#token=TOKEN-CENTRAL
```

O fleet mostra:

- nós online/offline;
- latência de consulta;
- salas de cada nó;
- PID;
- portas TCP/WebSocket;
- microfone;
- engine;
- modelo;
- estado real e desejado.

Também permite iniciar, parar e reiniciar uma instância em qualquer nó cadastrado.

### Segurança multi-nó

Existem dois níveis de token:

```text
fleet_token
    |
    v
fleet_server
    |
    +--> token do nó A
    +--> token do nó B
    +--> token do nó C
```

Assim, o navegador não precisa conhecer os tokens internos de cada máquina.

O arquivo real:

```text
nodes.json
```

fica fora do Git.

Para redes maiores, recomenda-se comunicação entre os nós por VPN ou HTTPS,
evitando expor os control planes diretamente na rede pública.


## Release automatizado para Windows

O workflow:

```text
.github/workflows/windows-release.yml
```

gera um pacote Windows portátil contendo:

- runtime Python embutido;
- dependências instaladas dentro do próprio pacote;
- servidor STT;
- orquestrador;
- fleet server;
- páginas web;
- corpus textual;
- arquivos de configuração de exemplo;
- scripts de instalação/desinstalação;
- documentação;
- `VERSION.json`.

O pacote não depende de Python previamente instalado no computador de destino.

### Build local do pacote

Em uma máquina Windows com PowerShell e Python disponíveis para preparar o build:

```powershell
.\deploy\build_windows_portable.ps1 -Version "2.0.0-rc1"
```

A saída é:

```text
dist/
├── Legenda-2.0.0-rc1-win64.zip
└── Legenda-2.0.0-rc1-win64.zip.sha256
```

O ZIP contém seu próprio:

```text
python\python.exe
python\Lib\site-packages\...
```

### GitHub Actions

O workflow pode ser executado manualmente por `workflow_dispatch`.

Também é executado automaticamente quando uma tag no formato `v*` é criada.

Exemplo:

```bash
git tag v2.0.0-rc1
git push origin v2.0.0-rc1
```

Nesse caso, o GitHub Actions:

1. executa os testes leves;
2. monta o runtime Windows portátil;
3. instala as dependências dentro do pacote;
4. valida o runtime empacotado;
5. gera ZIP;
6. calcula SHA256;
7. publica o artefato;
8. cria um GitHub Release para a tag.

### Instalação do pacote portátil

Depois de extrair o ZIP:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\deploy\install_portable_windows.ps1 -AppDir "C:\Legenda"
```

Esse instalador usa o Python que acompanha o pacote:

```text
C:\Legenda\python\python.exe
```

e registra o orquestrador para iniciar no boot pelo Task Scheduler.

Durante atualização, preserva quando existentes:

```text
config.json
instances.json
nodes.json
```

Assim uma atualização de versão não substitui os parâmetros locais, tokens e
mapeamento de dispositivos.

Para remover a inicialização automática preservando os dados:

```powershell
.\deploy\uninstall_portable_windows.ps1
```

Para remover também o diretório da aplicação:

```powershell
.\deploy\uninstall_portable_windows.ps1 -RemoveData
```

### Verificação de integridade

Cada release inclui:

```text
Legenda-<versao>-win64.zip.sha256
```

O hash pode ser conferido no PowerShell:

```powershell
Get-FileHash .\Legenda-2.0.0-rc1-win64.zip -Algorithm SHA256
```


## Hardening final

Os serviços administrativos aplicam uma regra adicional: qualquer bind fora de
loopback exige token. Por exemplo, iniciar o fleet, o control plane ou o coletor
em `0.0.0.0` sem autenticação agora falha na inicialização.

As comparações de Bearer token usam comparação em tempo constante.

O WebSocket principal usa:

```json
"websocket_auth_timeout_seconds": 10
```

Clientes que conectarem e não enviarem a primeira mensagem de autenticação nesse
intervalo são desconectados.

A gravação WAV dos segmentos finais ocorre antes do STT. Assim, falha de
transcrição ou resultado vazio não elimina o áudio bruto capturado.

`save_transcript` e `export_subtitles` são independentes: é possível gerar
SRT/VTT mesmo com JSONL desabilitado.

No encerramento, o servidor tenta drenar as filas de STT e eventos antes de
fechar o WAV, reduzindo risco de perda dos últimos segmentos.

### Persistência do dispositivo de áudio

Por padrão, o orquestrador preserva entre reinícios:

```json
"runtime_persist_keys": ["input_device_index"]
```

Isso impede que uma troca de microfone feita pelo painel seja perdida quando o
supervisor reinicia.

Para descartar ajustes runtime e reconstruir tudo a partir de
`instances.json`:

```json
"reset_runtime_settings": true
```

Depois da primeira inicialização com essa opção, volte o valor para `false`.


## Observação de segurança do TCP legado

A autenticação por token protege o WebSocket e os serviços administrativos, mas
a porta TCP usada pelo cliente Lazarus legado mantém compatibilidade com o
protocolo existente e **não possui autenticação própria**.

Quando o servidor estiver com:

```json
"host": "0.0.0.0"
```

a porta TCP deve ser considerada acessível à rede onde o host está conectado.

Em ambientes não confiáveis, utilize uma das opções:

- firewall permitindo apenas os clientes Lazarus autorizados;
- VPN entre cliente e servidor;
- bind em interface/endereço restrito;
- proxy/túnel seguro para transportar a conexão.

Não publique a porta TCP 8097 diretamente na Internet.

O WebSocket, que possui autenticação de sala, deve ser preferido para novos
clientes.
