# Mapa interativo de RDR2

## Como abrir

Dê dois cliques em **`Abrir mapa.bat`**. Ele liga um pequeno servidor local
(`servidor.py`) e abre o mapa em http://localhost:8765 no navegador.
Deixe a janela preta aberta enquanto usa o mapa; feche-a para parar.

Com o servidor ligado, tudo é salvo em arquivos nesta pasta:

| O que | Onde |
|---|---|
| Pinos marcados como encontrados | `progresso.json` |
| Filtros, "ocultar encontrados", posição do mapa, grupos abertos | `configuracao.json` |

Esses dois arquivos são o seu progresso pessoal e ficam **fora do git** (ver
`.gitignore`). O repositório só tem os dados com tudo a encontrar. Quem clonar
começa do zero; os dois arquivos são criados na primeira marcação.

### No celular (ou outro aparelho)

Com o PC e o celular na mesma rede Wi-Fi, abra no celular o endereço que a janela
preta mostra em "No celular", algo como `http://192.168.0.10:8765`. (No celular,
`localhost` aponta para o próprio celular, por isso precisa do IP do PC.)
Na primeira vez o Windows pergunta se libera o Python na rede: permita em
**redes privadas**. O que for marcado em qualquer aparelho vai para o mesmo `progresso.json`,
e as páginas abertas se atualizam sozinhas em até 4 segundos.
Para não aceitar outros aparelhos: `python servidor.py --so-este-pc`.

Se o servidor parar enquanto o mapa está aberto, aparece um aviso vermelho e a
mudança não é salva. Abra o `.bat` de novo e recarregue a página.

Também dá para abrir o `index.html` direto com dois cliques, sem servidor, mas aí
as marcações ficam salvas só naquele navegador e não vão para o `progresso.json`.
Depois de clonar, abra o `.bat` (ou rode `python preparar.py`) uma vez para gerar
o `dados.js`, que também fica fora do git.

Precisa de internet: o fundo é o mapa oficial da Rockstar (o mesmo do Social Club),
carregado aos poucos conforme você navega, e a biblioteca Leaflet vem de um CDN.

## Arquivos

| Arquivo | Para que serve |
|---|---|
| `Abrir mapa.bat` | Atalho que liga o servidor e abre o mapa |
| `servidor.py` | Servidor local que salva o progresso |
| `index.html` | O mapa |
| `preparar.py` | Gera `dados.js` a partir dos JSONs |
| `rdr2map_*.json` | Dados dos pinos e ícones (nunca são alterados pelo mapa) |
| `dados.js` | Pinos e ícones já convertidos — gerado, fora do git |
| `progresso.json`, `configuracao.json` | Seu progresso — fora do git |

Se editar `progresso.json` à mão, faça com o servidor fechado: ele lê o arquivo só
ao iniciar e sobrescreveria sua edição na próxima marcação.

## Como os pinos foram alinhados

Os pinos originais estão em outro sistema de coordenadas. A conversão em
`preparar.py` foi calculada casando 636 itens de coleção (pontas de flecha, ovos,
garrafas, fósseis e flores) com as mesmas posições do projeto aberto
[RDR2 Collectors Map](https://github.com/jeanropke/RDR2CollectorsMap), que usa o
mapa da Rockstar. O erro mediano é de cerca de 5 px no zoom máximo.

## Recursos

- Filtros por grupo e por categoria (plantas e Red Dead Online começam ocultos)
- Busca por nome ou categoria
- Marcar pinos como encontrados, com progresso por categoria
- Opção de ocultar os encontrados
- Link direto para um pino: `http://localhost:8765/#pino=205`
