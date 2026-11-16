// Painel de informações do país mostrado depois de cada resposta.
// Dados locais (data/country-info.json): capital, moeda, sub-região e um vizinho, tirados do próprio banco.
// Dados online (Wikipédia, sem chave de acesso): descrição do país e fotos das cidades.
// Se a internet falhar, o painel mostra só o que existe localmente e o jogo segue normalmente.
// Todo texto vindo de fora entra na tela com textContent (nunca innerHTML).

const TIMEOUT_MS = 8000;
const summaryCache = new Map();
const photoCache = new Map();
let local = null; // { info, questionCountries, cities }
let loading = null;

export function initCountryInfo() {
  loading ??= Promise.all([
    fetch("./data/country-info.json").then(r => r.json()),
    fetch("./data/question-countries.json").then(r => r.json()),
    fetch("./data/country-cities.json").then(r => r.json())
  ]).then(([info, questionCountries, cities]) => { local = { info, questionCountries, cities }; })
    .catch(error => { console.warn("GeoMaster: painel de países indisponível.", error); });
  return loading;
}

// Perguntas de mapa e bandeira já trazem targetId; as de múltipla escolha vêm do mapa pergunta→país.
export function countryIdFor(question) {
  return question?.targetId ?? local?.questionCountries[question?.id] ?? guessFromText(question) ?? null;
}

// Plano B (ex.: perguntas do modo ?dev=1 ou perguntas novas ainda fora do mapa): procura o nome do país no enunciado.
const plain = text => String(text).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
let nameIndex = null;
function guessFromText(question) {
  if (!local || !question?.text) return null;
  nameIndex ??= Object.entries(local.info)
    .flatMap(([id, c]) => [[plain(c.name), id], [plain(c.nameEn), id]])
    .sort((a, b) => b[0].length - a[0].length); // "Guiné-Bissau" antes de "Guiné"
  const text = ` ${plain(question.text)} `;
  return nameIndex.find(([name]) => text.includes(` ${name} `))?.[1] ?? null;
}

async function getJson(url) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(url, { signal: controller.signal });
    return response.ok ? await response.json() : null;
  } catch { return null; } finally { clearTimeout(timer); }
}

function fetchSummary(country) {
  if (!summaryCache.has(country.name)) {
    summaryCache.set(country.name, (async () => {
      const pt = await getJson(`https://pt.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(country.name)}`);
      if (pt?.extract) return { text: pt.extract, url: pt.content_urls?.desktop?.page };
      const en = await getJson(`https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(country.nameEn)}`);
      return en?.extract ? { text: en.extract, url: en.content_urls?.desktop?.page, english: true } : null;
    })());
  }
  return summaryCache.get(country.name);
}

// Busca a foto do verbete mais provável para "cidade país" (ex.: "Lisbon Portugal").
function fetchCityPhoto(city, countryEn) {
  const key = `${city}|${countryEn}`;
  if (!photoCache.has(key)) {
    const params = new URLSearchParams({
      action: "query", format: "json", origin: "*", generator: "search", gsrlimit: "1",
      gsrsearch: `${city} ${countryEn}`, prop: "pageimages", piprop: "thumbnail", pithumbsize: "480"
    });
    photoCache.set(key, getJson(`https://en.wikipedia.org/w/api.php?${params}`).then(data => {
      const page = Object.values(data?.query?.pages ?? {})[0];
      return page?.thumbnail?.source ? { src: page.thumbnail.source, title: page.title } : null;
    }));
  }
  return photoCache.get(key);
}

// Curiosidade sorteada entre os fatos que temos para aquele país.
function pickFact(country, random) {
  const facts = [];
  if (country.capital) facts.push(`A capital registrada para ${country.name} é ${country.capital}.`);
  if (country.currency) facts.push(`A moeda registrada para ${country.name} é ${country.currency}.`);
  if (country.subregion) facts.push(`Na classificação M49 da ONU, ${country.name} fica em: ${country.subregion}.`);
  if (country.neighbors?.length) facts.push(`Um dos vizinhos terrestres de ${country.name} é ${country.neighbors[0]}.`);
  return facts.length ? facts[Math.floor(random() * facts.length)] : null;
}

const el = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
};

export function clearCountryCard(container) {
  container.dataset.token = "";
  container.hidden = true;
  container.replaceChildren();
}

export async function showCountryCard(container, countryId, random = Math.random) {
  await initCountryInfo();
  const country = local?.info[countryId];
  if (!country) { clearCountryCard(container); return; }

  const token = String(Date.now() + random()); // evita que uma resposta atrasada apareça na pergunta seguinte
  container.dataset.token = token;
  const stale = () => container.dataset.token !== token;

  const fact = pickFact(country, random);
  const loadingNote = el("p", "country-loading", "Carregando descrição e fotos…");
  const desc = el("p", "country-desc");
  const source = el("p", "country-source");
  const gallery = el("div", "country-gallery");
  container.replaceChildren(el("h4", "", `Conheça: ${country.name}`));
  if (fact) {
    const box = el("div", "country-fact");
    box.append(el("b", "", "💡 Curiosidade: "), document.createTextNode(fact));
    container.append(box);
  }
  container.append(desc, source, loadingNote, gallery);
  container.hidden = false;

  const cities = local.cities[countryId] ?? (country.capital ? [country.capital] : []);
  const [summary, photos] = await Promise.all([
    fetchSummary(country),
    Promise.all(cities.map(city => fetchCityPhoto(city, country.nameEn)))
  ]);
  if (stale()) return;

  loadingNote.remove();
  if (summary) {
    desc.textContent = summary.text;
    source.append(document.createTextNode(`Fonte: Wikipédia${summary.english ? " (em inglês)" : ""}`));
    if (summary.url) {
      const link = el("a", "", " — ler mais");
      link.href = summary.url; link.target = "_blank"; link.rel = "noopener noreferrer";
      source.append(link);
    }
  } else {
    desc.textContent = "Não foi possível carregar a descrição agora. Verifique a conexão.";
  }
  const found = photos.filter(Boolean);
  found.forEach(photo => {
    const figure = el("figure");
    const image = el("img");
    image.src = photo.src; image.alt = `Foto de ${photo.title}`; image.loading = "lazy";
    image.onerror = () => figure.remove();
    figure.append(image, el("figcaption", "", photo.title));
    gallery.append(figure);
  });
  if (found.length > 0) source.append(document.createTextNode(" · Fotos: Wikipédia/Wikimedia Commons"));
}
