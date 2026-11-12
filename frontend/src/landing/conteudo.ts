// Textos e números da landing. Regra: todo número de mercado tem fonte com link e recorte certo
// (lugar, ano, quem pesquisou); todo número do projeto vem do README / docs/AVALIACAO.md / evals/.

export const REPOSITORIO = 'https://github.com/MarcusVinicius44/LucraFood'
export const LINKEDIN = 'https://www.linkedin.com/in/marcus-vinicius44'
export const AUTOR = 'Marcus Vinicius'
export const CONTATO_EMAIL = `mailto:marcusesc44@gmail.com?subject=${encodeURIComponent('Quero conhecer o LucraFood')}`
// O número fica só dentro do link, nunca escrito na página.
export const CONTATO_WHATSAPP = `https://wa.me/5579999757907?text=${encodeURIComponent('Olá, vi o LucraFood e quero saber mais')}`

export interface Fonte {
  id: string
  titulo: string
  quem: string
  url: string
}

export const FONTES: Fonte[] = [
  {
    id: 'ifb',
    titulo: 'Food service conta com 1,6 milhão de estabelecimentos ativos no Brasil',
    quem: 'Instituto Foodservice Brasil e Driva, 2023 (publicado pela Saipos)',
    url: 'https://saipos.com/noticia/food-service-conta-com-1-6-milhao-de-estabelecimentos-ativos-no-brasil',
  },
  {
    id: 'ifood',
    titulo: 'Delivery cresce no Brasil com 380 mil estabelecimentos cadastrados no iFood em 2024',
    quem: 'E-Commerce Brasil, 2024',
    url: 'https://www.ecommercebrasil.com.br/noticias/delivery-cresce-no-brasil-com-380-mil-estabelecimentos-cadastrados-no-ifood-em-2024',
  },
  {
    id: 'abrasel2025',
    titulo: 'WhatsApp representa 26% do faturamento com delivery em bares e restaurantes',
    quem: 'Pesquisa Abrasel com 2.176 empresários, publicada pela Mercado&Consumo em 16/03/2025',
    url: 'https://mercadoeconsumo.com.br/16/03/2025/foodservice/whatsapp-representa-26-do-faturamento-com-delivery-em-bares-e-restaurantes/',
  },
  {
    id: 'comissao',
    titulo: 'Comida no iFood fica 17,5% mais cara do que no restaurante, diz associação',
    quem: 'Abrasel, 2022 (publicado pelo TNH1)',
    url: 'https://www.tnh1.com.br/noticia/nid/comida-no-ifood-fica-175-mais-cara-do-que-no-restaurante-diz-associacao/',
  },
  {
    id: 'rs2026',
    titulo: 'Bares e restaurantes patinam no início do ano e apostam no segundo semestre',
    quem: 'Abrasel no RS, publicado pelo Jornal do Comércio em 17/07/2026',
    url: 'https://www.jornaldocomercio.com/economia/2026/07/1256638-bares-e-restaurantes-patinam-no-inicio-do-ano-e-apostam-no-segundo-semestre.html',
  },
]

export const fonte = (id: string) => FONTES.find((f) => f.id === id)!

export interface NumeroMercado {
  valor: string
  texto: string
  fonte: string
}

export const NUMEROS_MERCADO: NumeroMercado[] = [
  { valor: '1,6 milhão', texto: 'de estabelecimentos de alimentação ativos no Brasil, em 2023.', fonte: 'ifb' },
  { valor: '~380 mil', texto: 'estabelecimentos cadastrados no iFood em 2024.', fonte: 'ifood' },
  {
    valor: '71%',
    texto:
      'dos bares e restaurantes do país fazem delivery, que já é 30% do faturamento deles. Do que entra pelo delivery, 54% vem dos apps (marketplaces).',
    fonte: 'abrasel2025',
  },
  { valor: '16% a 25%', texto: 'é a comissão média cobrada pelos apps, às vezes acima de 30% (dado de 2022).', fonte: 'comissao' },
  {
    valor: '43%',
    texto: 'dos bares e restaurantes do Rio Grande do Sul operaram no prejuízo em janeiro de 2026 (21% em maio).',
    fonte: 'rs2026',
  },
]

// Números do projeto: README ("Resultados medidos") e docs/AVALIACAO.md, rodadas guardadas em evals/*/resultados/.
export const NUMEROS_PROJETO = [
  { valor: '251 de 254', texto: 'pratos lidos certo em 8 fotos de cardápios reais, e 251 de 251 preços (~5 s por foto)' },
  { valor: '17 de 17', texto: 'pratos e preços numa foto tirada com o celular' },
  { valor: '42 de 42', texto: 'ingredientes e quantidades na ficha por texto, em 5 rodadas seguidas' },
  { valor: '21 de 21', texto: 'itens ambíguos que o sistema pediu para o dono conferir' },
  { valor: '13 de 14', texto: 'respostas da conversa lidas certo ("uns 2 quilos", "pula essa")' },
]
