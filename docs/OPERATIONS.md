# Operação e validação do Legenda v2

Este documento cobre os testes operacionais que complementam os testes unitários.

## 1. Teste de carga WebSocket

O utilitário:

```text
bin/load_test_websocket.py
```

abre vários clientes simultâneos, autentica cada um e mantém as conexões ativas.

Exemplo com 50 clientes por 60 segundos:

```bash
python bin/load_test_websocket.py \
  --url ws://127.0.0.1:8098 \
  --room principal \
  --token TOKEN \
  --clients 50 \
  --seconds 60
```

A saída JSON contém:

- clientes solicitados;
- conexões bem-sucedidas;
- falhas;
- taxa de sucesso;
- latência média de conexão;
- P95 de conexão;
- mensagens recebidas;
- primeiras mensagens de erro.

Critério inicial recomendado:

```text
success_rate = 1.0
failed = 0
```

Durante o teste, acompanhe também `web/admin.html` para observar memória,
CPU, filas e clientes conectados.

## 2. Teste de falha e recuperação

A lógica de watchdog do orquestrador é testada unitariamente por
`tests/test_orchestrator.py`.

Ela cobre dois casos:

1. processo encerra inesperadamente e `desired_running=true`: reinicia;
2. processo foi parado administrativamente: não reinicia.

Teste manual em ambiente de homologação:

```bash
python bin/orchestrator.py instances.json
```

Localize o PID da sala:

```bash
curl -H "Authorization: Bearer TOKEN" http://127.0.0.1:8070/api/status
```

Finalize somente o processo `srvouve.py` da sala e verifique se o PID muda
automaticamente após o ciclo de reconciliação.

Depois teste parada administrativa:

```bash
curl -X POST \
  -H "Authorization: Bearer TOKEN" \
  http://127.0.0.1:8070/api/stop/NOME_DA_INSTANCIA
```

A instância deve permanecer parada.

## 3. Retenção de dados

Configuração padrão:

```json
{
  "retention_days": 30,
  "retention_extra_dirs": ["logs"]
}
```

Na inicialização de cada sessão, arquivos antigos com extensões:

```text
.jsonl
.srt
.vtt
.wav
.log
```

são removidos dos diretórios configurados quando ultrapassam o período.

Para auditar sem remover:

```bash
python bin/retention.py --dir transcripts --days 30 --dry-run
```

Para executar manualmente:

```bash
python bin/retention.py --dir transcripts --days 30
```

Use `retention_days=0` para desabilitar a limpeza automática.

Para logs de Caddy/aplicação no Linux, há também:

```text
deploy/logrotate-legenda.example
```

## 4. HTTPS e WSS

Exemplos prontos:

```text
deploy/Caddyfile.example
deploy/nginx-legenda.conf.example
```

O desenho recomendado é:

```text
Internet/LAN
    |
    v
 HTTPS/WSS :443
    |
    v
 Caddy/Nginx
    |
    +--> /             -> web estático
    +--> /ws/          -> 127.0.0.1:8098
    +--> /orchestrator-api/ -> 127.0.0.1:8070
    +--> /fleet-api/        -> 127.0.0.1:8050
    +--> /corpus-api/       -> 127.0.0.1:8060
```

A porta TCP 8097 do cliente Lazarus não deve ser publicada na Internet.

## 5. Teste prolongado

Em homologação, mantenha uma instância por pelo menos 4 horas com áudio real.

Registre a cada 15 minutos:

- RSS/memória;
- CPU;
- tamanho das filas;
- número de clientes;
- erros STT;
- parciais descartados;
- eventos descartados;
- tamanho do WAV;
- tamanho JSONL/SRT/VTT.

Critérios de atenção:

- crescimento contínuo de memória sem estabilização;
- aumento progressivo da fila STT;
- eventos finais descartados;
- processo reiniciando sem causa externa;
- WAV inconsistente com timestamps.

## 6. Checklist de release candidate

Antes de criar `v2.0.0-rc1`:

- [ ] CI Linux verde;
- [ ] build Windows portátil verde;
- [ ] teste de carga WebSocket aprovado;
- [ ] recuperação de processo validada;
- [ ] retenção validada em dry-run;
- [ ] HTTPS/WSS validado no hostname final;
- [ ] TCP 8097 protegido por firewall/VPN;
- [ ] cliente Lazarus compilado;
- [ ] teste prolongado concluído;
- [ ] benchmark com corpus real arquivado.


## 7. Compilação do cliente Lazarus

O workflow:

```text
.github/workflows/lazarus-build.yml
```

instala Lazarus no runner Linux, baixa o lNet upstream, compila os pacotes:

```text
lnetbase.lpk
lnetvisual.lpk
```

e depois executa:

```bash
lazbuild src/legenda.lpi --build-mode=Default
```

O executável Linux é publicado como artifact:

```text
legenda-lazarus-linux
```

As dependências antigas `indylaz` e `industrial` foram removidas. O indicador
visual usa agora apenas `TShape` da LCL.

## 8. Smoke test Lazarus sem microfone

Inicie o servidor mock:

```bash
python bin/mock_caption_server.py --host 127.0.0.1 --port 8097 --count 5
```

Abra o cliente Lazarus e conecte em:

```text
IP: 127.0.0.1
Porta: 8097
```

O cliente deve receber, uma por vez, frases como:

```text
Teste de conexão do Legenda.
O protocolo JSONL está funcionando.
O cliente Lazarus recebeu uma legenda final.
Esta execução não utiliza microfone nem reconhecimento de voz.
Teste concluído.
```

Esse teste valida:

- conexão TCP;
- framing JSONL;
- parsing de CaptionEvent v2;
- atualização da última frase;
- atualização do rótulo;
- atualização do histórico.

O CI também executa um teste de integração de rede em loopback que recebe três
eventos JSONL completos e valida sequência, sessão e versão do protocolo.


## 9. Soak test sintético do protocolo

Para testar volume sem microfone nem STT:

```bash
python bin/protocol_soak.py --events 10000 --payload-size 128
```

O teste abre um socket TCP real em loopback, transmite `CaptionEvent v2` em
JSONL e valida:

- quantidade enviada/recebida;
- perda;
- sequência;
- framing por LF;
- JSON válido;
- versão do protocolo;
- tipo de evento;
- erros de envio;
- throughput em eventos/s.

O CI executa uma versão reduzida com 1.000 eventos em cada suíte.

## 10. Release readiness

Antes de criar uma tag:

```bash
python bin/release_readiness.py
```

Para saída processável:

```bash
python bin/release_readiness.py --json
```

A verificação cobre:

- arquivos essenciais;
- workflows Linux/Windows;
- exemplos Caddy/Nginx;
- autenticação de sala ativa no exemplo;
- timeout WebSocket;
- retenção ativa;
- control plane em loopback;
- token de controle definido;
- `config.json`, `instances.json` e `nodes.json` fora do Git.

Uma falha retorna exit code 2 e deve bloquear a criação da release candidate.


## 11. Build nativo do cliente Lazarus no Windows

O workflow:

```text
.github/workflows/lazarus-windows.yml
```

usa runner `windows-latest`, instala Lazarus 4.0.0, baixa o lNet upstream e
compila:

```text
lnetbase.lpk
lnetvisual.lpk
src/legenda.lpi
```

Quando aprovado, o workflow publica:

```text
legenda-lazarus-windows
  └── legenda.exe
```

A versão do Lazarus é fixada para evitar que uma atualização automática do
pacote altere o comportamento do build sem revisão do projeto.

O job possui timeout de 30 minutos para impedir bloqueio indefinido do pipeline.


## 12. Benchmark automatizado por matriz

Depois de gerar o manifesto real do corpus:

```bash
python bin/prepare_corpus_manifest.py \
  --corpus-dir corpus \
  --output corpus/manifest.jsonl \
  --strict
```

execute toda a matriz:

```bash
python bin/benchmark_suite.py benchmark_suite.example.json
```

O arquivo de exemplo executa, por padrão:

```text
faster-whisper tiny  / CPU / int8
faster-whisper base  / CPU / int8
faster-whisper small / CPU / int8
```

e deixa uma configuração CUDA preparada, porém desabilitada.

Ao final, o comando chama automaticamente:

```text
bin/quality_report.py
```

e gera:

```text
benchmark_results/report.html
```

Para continuar a matriz mesmo quando uma configuração falhar:

```bash
python bin/benchmark_suite.py benchmark_suite.example.json --continue-on-error
```

Assim o benchmark físico do corpus passa a exigir apenas gravação dos áudios e
execução de um único comando.
