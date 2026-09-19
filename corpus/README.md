# Corpus de Referência — Legenda v2

Este diretório define a estrutura de um corpus próprio para avaliação de STT.

## Objetivo

Avaliar o comportamento do sistema em cenários relevantes para legendagem ao vivo,
sem misturar resultados sintéticos com resultados medidos.

## Categorias mínimas

- `clean`: fala limpa, ambiente silencioso;
- `noise`: ruído de fundo;
- `fast`: fala rápida;
- `distance`: microfone mais distante;
- `names`: nomes próprios e localidades;
- `acronyms`: siglas;
- `technical`: termos técnicos;
- `mixed`: frases que combinam várias dificuldades.

## Estrutura esperada

```text
corpus/
├── README.md
├── references/
│   ├── clean.jsonl
│   ├── noise.jsonl
│   ├── fast.jsonl
│   ├── distance.jsonl
│   ├── names.jsonl
│   ├── acronyms.jsonl
│   ├── technical.jsonl
│   └── mixed.jsonl
└── audio/
    ├── clean/
    ├── noise/
    ├── fast/
    ├── distance/
    ├── names/
    ├── acronyms/
    ├── technical/
    └── mixed/
```

Os arquivos de áudio não são versionados por padrão. O corpus textual pode ser.

## Formato das referências

Cada linha JSONL contém:

```json
{
  "id": "technical-001",
  "category": "technical",
  "reference": "o desfibrilador realizou o autoteste sem falhas",
  "speaker": "speaker-01",
  "notes": "fala natural"
}
```

O campo `speaker` deve ser um identificador pseudônimo. Não use dados pessoais
desnecessários.

## Regras de gravação

- WAV mono;
- PCM 16-bit;
- preferencialmente 16 kHz;
- uma frase por arquivo;
- não normalizar o áudio depois de uma coleta de ruído;
- registrar a categoria real da condição de gravação;
- evitar conteúdo sensível;
- obter consentimento dos locutores quando aplicável.

## Sugestão de tamanho inicial

Um corpus inicial útil pode ter 20 frases por categoria, com pelo menos 3 locutores.
O crescimento posterior deve preservar as mesmas categorias e critérios.

## Frases de referência sugeridas

As frases abaixo são apenas textos de coleta. Elas não representam resultado de benchmark.

### clean

- Bom dia a todos, vamos iniciar a reunião.
- O sistema está pronto para receber as próximas falas.
- A legenda deve aparecer com baixa latência na tela.

### noise

- Mesmo com ruído no ambiente, a fala deve permanecer compreensível.
- Há pessoas conversando ao fundo durante esta gravação.
- O microfone está captando som ambiente e voz ao mesmo tempo.

### fast

- Precisamos registrar rapidamente tudo o que foi discutido nesta reunião.
- A transcrição deve acompanhar o ritmo da fala sem perder informações.
- Vamos revisar os itens principais antes de concluir esta apresentação.

### distance

- Esta frase foi gravada com o locutor mais distante do microfone.
- O sistema deve lidar com menor intensidade de voz.
- A distância não deve impedir a compreensão da frase inteira.

### names

- Ribeirão Preto realizou uma nova reunião do conselho.
- Marcelo Maurin apresentou a demonstração do sistema.
- A Secretaria Municipal da Saúde participou da reunião.

### acronyms

- A ANVISA publicou uma nova orientação técnica.
- O NSPAC utiliza informações para apoiar o processo de trabalho.
- A RDC quinhentos e nove estabelece requisitos importantes.

### technical

- O desfibrilador realizou o autoteste sem falhas.
- O cardioversor apresenta monitorização de eletrocardiograma.
- A manutenção preventiva inclui inspeção visual e segurança elétrica.

### mixed

- A ANVISA discutiu em Ribeirão Preto os requisitos do equipamento.
- O NSPAC registrou dados técnicos durante uma reunião com ruído de fundo.
- A equipe avaliou rapidamente o desfibrilador e registrou o resultado.
