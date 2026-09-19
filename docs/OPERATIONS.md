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
