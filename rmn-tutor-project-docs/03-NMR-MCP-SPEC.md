# Especificação inicial do NMR MCP

## 1. Objetivo

Fornecer ao Claude ferramentas determinísticas para consultar informações do espectro de RMN sem depender de estimativas visuais para valores numéricos.

O MCP não deve "pensar" no lugar do tutor. Ele deve fornecer dados e operações.

## 2. Princípio

```text
NMR Engine
   ↓
NMR Tools
   ↓
Claude
```

O engine pode ser implementado com Python/nmrglue ou outra biblioteca apropriada após validação.

## 3. Ferramentas candidatas

### get_spectrum_metadata

Retorna:

- tipo de experimento;
- solvente;
- frequência;
- largura espectral;
- eixo;
- outras informações disponíveis.

### get_peak_list

Retorna a lista de picos/sinais identificados e metadados disponíveis.

### get_peaks_in_region

Entrada:

- ppm_start;
- ppm_end.

Saída:

- picos encontrados na região;
- intensidades quando disponíveis;
- informações auxiliares.

### get_peak

Entrada:

- ppm aproximado ou identificador do pico.

Saída:

- posição;
- intensidade;
- identificador;
- outros dados disponíveis.

### get_integration

Entrada:

- início/fim da região.

Saída:

- integral;
- integral normalizada, se disponível.

### get_spectrum_region

Entrada:

- ppm_start;
- ppm_end.

Saída:

- dados necessários para uma visualização/consulta ampliada.

### calculate_delta

Calcula diferença em ppm entre sinais selecionados.

### calculate_j

Quando o espectro e a digitalização permitirem, calcular/estimar a separação entre linhas apropriadas para obtenção de J.

Esta ferramenta deve declarar claramente suas limitações.

## 4. Ferramentas estruturais futuras

- validate_smiles;
- molecular_formula_from_smiles;
- molecular_weight_from_smiles;
- compare_formula;
- compare_hypothesis_with_spectrum.

Essas tarefas podem ser delegadas ao RDKit.

## 5. Regras do MCP

- Não inventar valores.
- Retornar ausência de dado explicitamente.
- Preferir números com unidade/contexto.
- Não esconder incerteza ou falha de detecção.
- Não transformar heurística em fato.

## 6. Exemplo de interação

Claude:
"Quero verificar os sinais entre 6 e 8 ppm."

→ get_peaks_in_region(6, 8)

Tool:
"Foram encontrados X sinais ..."

Claude:
usa esses resultados para orientar o estudante.

## 7. O que o MCP não deve fazer inicialmente

- entregar a molécula final automaticamente;
- consultar bases de moléculas para "dar a resposta";
- substituir a análise pedagógica;
- esconder resultados ambíguos.

## 8. Decisões em aberto

- formato dos dados de entrada;
- se o engine trabalha com arquivo bruto, texto exportado ou imagem;
- algoritmo exato de detecção de picos;
- como representar integrações;
- protocolo de execução do MCP;
- se o MCP ficará local ou remoto;
- versionamento do schema das tools.
