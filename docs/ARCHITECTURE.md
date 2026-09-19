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


## Sala autenticada e distribuição por idioma

O servidor mantém um `active_room` por processo. O áudio, a sessão e os eventos
pertencem a essa sala.

```text
Convite assinado
      |
      v
WebSocket
      |
      v
AUTH {room, token, language}
      |
      +-- HMAC inválido/expirado -> rejeita
      |
      v
cliente autenticado
      |
      +-- pt-BR -> evento original
      +-- en    -> tradutor -> evento inglês
      +-- es    -> tradutor -> evento espanhol
```

Os tokens usam HMAC-SHA256 e carregam `room`, `role` e `exp`. Dessa forma
não é necessário persistir cada convite no servidor.

## Tradução

A interface `Translator` está em `bin/translation.py`.

Implementações atuais:

- `PassthroughTranslator`;
- `LibreTranslateTranslator`;
- `CachedTranslator`.

A tradução ocorre somente para o cliente WebSocket. O evento original permanece
imutável para auditoria, exportação e diarização.

O cache usa a chave:

```text
(texto, idioma_origem, idioma_destino)
```

e evita repetir traduções idênticas durante a mesma execução.

## Estratégia de salas

Uma instância corresponde a uma fonte de áudio/sala ativa. Isso é deliberado:
captura física, VAD e STT permanecem isolados. Múltiplas salas simultâneas podem
ser executadas como processos separados com dispositivos e portas próprios.

Essa separação simplifica falhas, observabilidade e dimensionamento horizontal.


## Telemetria administrativa

A classe `Telemetry` mantém apenas métricas agregadas e uma janela limitada das
últimas latências STT. Ela não armazena conteúdo das falas.

```text
STT / filas / clientes / tradução
             |
             v
         Telemetry
             |
             v
      snapshot periódico
             |
             v
 WebSocket admin autenticado
             |
             v
       web/admin.html
```

O canal de administração reutiliza a conexão WebSocket já existente. Depois do
`welcome`, somente clientes autenticados com `role=admin` podem enviar
`subscribe_telemetry`.

O snapshot inclui:

- uptime;
- engine STT;
- filas;
- contagem de eventos;
- erros;
- clientes TCP/WebSocket;
- distribuição por idioma/papel;
- média e P95 de latência;
- CPU/memória do processo quando `psutil` estiver disponível.

Essa abordagem mantém observabilidade separada do fluxo de legenda e evita
expor métricas administrativas a espectadores comuns.


## Benchmark STT

O benchmark é deliberadamente separado do servidor ao vivo.

```text
dataset fixo
   |
   +-- áudio WAV
   +-- referência textual
   |
   v
SpeechEngine
   |
   v
hipótese
   |
   +-- WER
   +-- tempo de inferência
   +-- RTF
   +-- latência P95
   |
   v
JSON + CSV
```

Isso permite comparar engines e modelos sem interferência de rede, WebSocket,
interface gráfica ou fila de eventos.

As métricas principais são:

- WER para precisão;
- RTF para capacidade de acompanhar tempo real;
- latência média para custo típico;
- P95 para identificar caudas de latência.

O resultado por amostra preserva referência e hipótese, permitindo inspecionar
quais termos causam mais erro e avaliar o efeito de hotwords.


## Descoberta e seleção de áudio

`bin/audio_devices.py` encapsula a enumeração PyAudio. O servidor expõe dois
comandos administrativos:

```text
list_audio_devices
set_audio_device
```

A listagem pode ser feita sem interromper a captura. A troca é persistida na
configuração, mas só é aplicada após reinício, porque substituir um stream PyAudio
ativo no meio da sessão poderia perder frames ou criar inconsistência temporal.

## Orquestração multi-instância

O `bin/orchestrator.py` implementa um supervisor simples de processos:

```text
instances.json
     |
     v
Orchestrator
     |
     +-- config sala A -> srvouve.py
     |
     +-- config sala B -> srvouve.py
     |
     +-- config sala C -> srvouve.py
```

Cada processo recebe seu arquivo via variável:

```text
LEGENDA_CONFIG=/caminho/instancia.json
```

O servidor passa a aceitar essa variável no carregamento da configuração.

Os caminhos relativos do `base_config` e `runtime_dir` são resolvidos em
relação ao arquivo de definição de instâncias, permitindo rodar o orquestrador
como serviço sem depender do diretório corrente.

O supervisor reinicia processos que terminem inesperadamente e mantém portas,
dispositivos, diretórios de transcrição e identificadores de sala isolados.


## Corpus de referência

O corpus separa texto de referência e áudio bruto.

```text
corpus/references/*.jsonl
          |
          +-- id
          +-- category
          +-- reference
          +-- speaker pseudônimo
          |
          v
prepare_corpus_manifest.py
          |
          +---- procura WAV correspondente
          |
          v
corpus/manifest.jsonl
          |
          v
benchmark_stt.py
          |
          +-- resultado global
          +-- resultado por categoria
```

Os áudios são deliberadamente excluídos do Git. Isso evita crescimento excessivo
do repositório e reduz risco de publicação acidental de gravações.

O benchmark preserva a categoria em cada `BenchmarkRow` e calcula, para cada
grupo:

- número de amostras;
- WER médio;
- latência média;
- P95;
- RTF médio.

Com isso, a seleção do motor/modelo pode considerar o perfil de erro do domínio,
e não apenas um único número agregado.


## Control plane do orquestrador

O plano de controle fica fora dos processos de STT:

```text
web/orchestrator.html
          |
          | HTTP + Bearer token
          v
orchestrator_control.py
          |
          v
     Orchestrator
      /   |   \
     /    |    \
sala A  sala B  sala C
```

O supervisor mantém dois estados distintos:

- `running`: estado real do processo;
- `desired_running`: intenção administrativa.

Se `desired_running=true` e o processo cair, o watchdog o reinicia. Se um
administrador executar `stop`, o estado desejado passa para falso e a sala
permanece desligada.

A API não manipula diretamente áudio nem STT. Ela controla apenas o ciclo de vida
dos processos, reduzindo acoplamento entre administração e processamento de fala.

## Implantação como serviço

O unit `deploy/legenda-orchestrator.service` usa um único processo supervisor.
As instâncias de sala são processos filhos e herdam o ciclo de vida do
orquestrador.

O serviço usa:

```text
WorkingDirectory=/opt/legenda
User=legenda
Group=audio
Restart=on-failure
```

O grupo `audio` é necessário para acesso aos dispositivos de captura em
instalações Linux típicas.


## Coleta web do corpus

A coleta é separada do servidor STT principal:

```text
web/corpus.html
      |
      | getUserMedia
      v
captura PCM no navegador
      |
      v
downsample para 16 kHz
      |
      v
encode WAV PCM 16-bit
      |
      | HTTP POST
      v
corpus_collection_server.py
      |
      +-- valida category/id
      +-- valida assinatura RIFF/WAVE
      +-- limita tamanho
      |
      v
corpus/audio/<category>/<id>.wav
```

Essa separação evita misturar a coleta controlada do dataset com o pipeline
operacional de legendagem ao vivo.

O endpoint só aceita IDs presentes nas referências textuais, reduzindo risco de
criação de arquivos arbitrários. O nome de arquivo não vem diretamente do usuário:
é derivado de `category` e `id` previamente validados.


## Relatório de qualidade

O `quality_report.py` funciona somente sobre resultados persistidos:

```text
benchmark_results/*.json
          |
          v
quality_report.py
          |
          +-- resumo global
          +-- comparação entre configurações
          +-- métricas por categoria
          |
          v
benchmark_results/report.html
```

Nenhuma inferência é executada durante a geração do relatório. Isso mantém a
separação entre medição e apresentação e evita que uma visualização altere o
resultado experimental.

O relatório pode ser regenerado sempre que novos benchmarks forem adicionados.


## Gestão multi-nó

A camada fleet fica acima dos orquestradores locais:

```text
                 web/fleet.html
                       |
                       v
                fleet_server.py
                 /      |      \
                /       |       \
               v        v        v
          Node A     Node B     Node C
             |          |          |
      orchestrator orchestrator orchestrator
          /  \        /  \       /  \
       salas        salas       salas
```

O fleet não executa STT. Ele consulta e controla os nós por HTTP.

Cada nó mantém:

- suas portas;
- seus dispositivos de áudio;
- seus processos;
- seu token de controle.

O fleet mantém:

- catálogo de nós;
- token central;
- timeout de consulta;
- visão agregada.

O navegador recebe somente o estado consolidado e envia ações ao fleet. O token
interno de cada nó fica apenas em `nodes.json`.

## Windows

No Windows, o processo supervisor é iniciado pelo Task Scheduler:

```text
Boot
  |
  v
LegendaOrchestrator
  |
  v
.venv\Scripts\python.exe bin\orchestrator.py instances.json
```

Essa opção evita introduzir dependência de gerenciadores de serviço de terceiros
e mantém o mesmo código Python usado no Linux.


## Distribuição Windows portátil

O build Windows gera uma distribuição autocontida:

```text
Legenda-<version>/
├── python/
│   ├── python.exe
│   └── Lib/site-packages/
├── bin/
├── web/
├── corpus/
├── deploy/
├── docs/
├── config.example.json
├── instances.example.json
├── nodes.example.json
└── VERSION.json
```

O Python embeddable é obtido durante o build e o arquivo `python*._pth` é
ajustado para habilitar `site` e `Lib\site-packages`.

As dependências são instaladas com wheels binários dentro do próprio pacote.

O computador alvo não precisa ter Python no PATH.

O workflow separa duas responsabilidades:

```text
tests.yml
  -> CI leve frequente

windows-release.yml
  -> build pesado apenas manual/tag
```

Isso evita reconstruir faster-whisper e suas dependências a cada commit comum.
