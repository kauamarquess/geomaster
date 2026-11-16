// Mapa-múndi interativo (Leaflet + GeoJSON) para os desafios "clique no país".
//
// Decisões importantes:
//  - NÃO há mapa-base (tiles): ele mostraria nomes de países e entregaria a resposta.
//    O fundo é só o "oceano" (cor de fundo) e os países vêm de data/geojson/countries.geojson.
//  - Cada país tem um identificador único em properties.id (código ISO alfa-3, ex.: "BRA").
//    É esse mesmo código que as perguntas usam em "targetId".
//  - Países minúsculos (Vaticano, Malta, Singapura...) ganham um ponto clicável extra,
//    porque no mapa-múndi eles ocupam menos de 1 pixel.
//
// O Leaflet é carregado por <script> no index.html (variável global L), por isso este arquivo
// só usa "L" quando o mapa é realmente criado. Assim a parte de dados pode ser testada no Node.

export const COUNTRIES_URL = "./data/geojson/countries.geojson";

// Erro específico dos dados do mapa (a interface mostra uma mensagem amigável).
export class MapDataError extends Error {
  constructor(message, details = {}) {
    super(message);
    this.name = "MapDataError";
    this.details = details;
  }
}

// ---------------------------------------------------------------------------
// Dados
// ---------------------------------------------------------------------------

// Confere o GeoJSON: identificadores existentes, únicos e geometrias válidas.
export function validateCountries(geojson) {
  const countries = new Map(); // id -> { id, name }
  const problems = [];
  if (!geojson || geojson.type !== "FeatureCollection" || !Array.isArray(geojson.features)) {
    return { countries, problems: ["o arquivo não é um GeoJSON do tipo FeatureCollection"] };
  }
  geojson.features.forEach((feature, index) => {
    const id = feature?.properties?.id;
    const name = feature?.properties?.name;
    if (typeof id !== "string" || !/^[A-Z0-9]{3}$/.test(id)) {
      problems.push(`registro ${index}: identificador inválido (${String(id)})`);
    } else if (countries.has(id)) {
      problems.push(`identificador repetido: ${id}`);
    } else {
      countries.set(id, { id, name: typeof name === "string" && name.trim() ? name : id });
    }
    const type = feature?.geometry?.type;
    if (type !== "Polygon" && type !== "MultiPolygon") {
      problems.push(`${String(id)}: geometria inválida`);
    }
  });
  if (countries.size === 0) problems.push("nenhum país encontrado");
  return { countries, problems };
}

let countriesPromise = null;

// Carrega e valida os países uma única vez (o resultado fica guardado).
export function loadCountries(url = COUNTRIES_URL) {
  if (!countriesPromise) {
    countriesPromise = (async () => {
      let response;
      try {
        response = await fetch(url);
      } catch {
        throw new MapDataError("Não foi possível carregar os dados do mapa.");
      }
      if (!response.ok) throw new MapDataError("Não foi possível carregar os dados do mapa (countries.geojson).");
      let geojson;
      try { geojson = await response.json(); } catch {
        throw new MapDataError("O arquivo countries.geojson está corrompido.");
      }
      const { countries, problems } = validateCountries(geojson);
      if (problems.length > 0) {
        throw new MapDataError(`Dados do mapa inválidos: ${problems.slice(0, 3).join("; ")}`, { problems });
      }
      return { geojson, countries, ids: new Set(countries.keys()) };
    })();
    countriesPromise.catch(() => { countriesPromise = null; }); // permite tentar de novo depois de um erro
  }
  return countriesPromise;
}

// Limpa o cache (usado nos testes).
export function resetCountriesCache() {
  countriesPromise = null;
}

// ---------------------------------------------------------------------------
// Geometria: maior pedaço de cada país (ex.: o continente da França, sem as ilhas distantes)
// ---------------------------------------------------------------------------

// Devolve { area, south, west, north, east } do maior polígono (pela caixa que o envolve).
export function largestPolygonBox(geometry) {
  const polygons = geometry.type === "MultiPolygon" ? geometry.coordinates : [geometry.coordinates];
  let best = null;
  for (const polygon of polygons) {
    let west = Infinity, east = -Infinity, south = Infinity, north = -Infinity;
    for (const [lng, lat] of polygon[0]) { // [0] = contorno externo
      west = Math.min(west, lng); east = Math.max(east, lng);
      south = Math.min(south, lat); north = Math.max(north, lat);
    }
    const area = (east - west) * (north - south);
    if (!best || area > best.area) best = { area, south, west, north, east };
  }
  return best;
}

// Ponto de dentro do país (para rótulos e testes): o ponto do maior pedaço que fica mais
// longe das bordas. O centro da "caixa" falharia em países compridos como o Chile.
function pointInRing(x, y, ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

function distanceToRingSquared(x, y, ring) {
  let best = Infinity;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [x1, y1] = ring[j];
    const [x2, y2] = ring[i];
    const dx = x2 - x1;
    const dy = y2 - y1;
    const lengthSquared = dx * dx + dy * dy;
    const t = lengthSquared === 0 ? 0 : Math.max(0, Math.min(1, ((x - x1) * dx + (y - y1) * dy) / lengthSquared));
    const px = x1 + t * dx - x;
    const py = y1 + t * dy - y;
    best = Math.min(best, px * px + py * py);
  }
  return best;
}

// Devolve { lat, lng } dentro do maior pedaço do país (e fora de "buracos", como o Lesoto na África do Sul).
export function interiorPoint(geometry) {
  const polygons = geometry.type === "MultiPolygon" ? geometry.coordinates : [geometry.coordinates];
  const areaOf = polygon => {
    const xs = polygon[0].map(c => c[0]);
    const ys = polygon[0].map(c => c[1]);
    return (Math.max(...xs) - Math.min(...xs)) * (Math.max(...ys) - Math.min(...ys));
  };
  const polygon = polygons.reduce((best, current) => (areaOf(current) > areaOf(best) ? current : best));
  const [outer, ...holes] = polygon;
  const score = (x, y) => {
    if (!pointInRing(x, y, outer) || holes.some(hole => pointInRing(x, y, hole))) return -1;
    return Math.min(...[outer, ...holes].map(ring => distanceToRingSquared(x, y, ring)));
  };

  let west = Math.min(...outer.map(c => c[0])), east = Math.max(...outer.map(c => c[0]));
  let south = Math.min(...outer.map(c => c[1])), north = Math.max(...outer.map(c => c[1]));
  let best = { x: outer[0][0], y: outer[0][1], score: -1 };
  // Busca em grade e refina duas vezes ao redor do melhor ponto.
  for (let pass = 0, steps = 24; pass < 3; pass += 1, steps = 8) {
    const dx = (east - west) / steps;
    const dy = (north - south) / steps;
    for (let i = 0; i <= steps; i += 1) {
      for (let j = 0; j <= steps; j += 1) {
        const x = west + i * dx;
        const y = south + j * dy;
        const value = score(x, y);
        if (value > best.score) best = { x, y, score: value };
      }
    }
    west = best.x - dx; east = best.x + dx; south = best.y - dy; north = best.y + dy;
  }
  return { lat: best.y, lng: best.x };
}

// Abaixo disso (em graus quadrados) o país ganha um ponto clicável.
export const TINY_AREA_DEGREES = 0.8;

// ---------------------------------------------------------------------------
// Estilos
// ---------------------------------------------------------------------------
const STYLE = {
  base: { fillColor: "#f9fbff", fillOpacity: 1, color: "#8fa8cc", weight: 0.8 },
  hover: { fillColor: "#dbe8ff", fillOpacity: 1, color: "#6f8fbf", weight: 1 },
  selected: { fillColor: "#2563eb", fillOpacity: 0.9, color: "#173b75", weight: 1.6 },
  correct: { fillColor: "#22a06b", fillOpacity: 0.95, color: "#126b46", weight: 1.6 },
  wrong: { fillColor: "#ef4444", fillOpacity: 0.95, color: "#a02020", weight: 1.6 }
};
const DOT_STYLE = {
  base: { fillColor: "#f9fbff", fillOpacity: 1, color: "#6f8fbf", weight: 1.5 },
  hover: { fillColor: "#dbe8ff", fillOpacity: 1, color: "#2563eb", weight: 2 },
  selected: { fillColor: "#2563eb", fillOpacity: 1, color: "#173b75", weight: 2 },
  correct: { fillColor: "#22a06b", fillOpacity: 1, color: "#126b46", weight: 2 },
  wrong: { fillColor: "#ef4444", fillOpacity: 1, color: "#a02020", weight: 2 }
};

// Enquadramento inicial: o mundo todo, sem o miolo da Antártida.
const WORLD_BOUNDS = [[-58, -170], [82, 180]];
const prefersReducedMotion = () => !!globalThis.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

// ---------------------------------------------------------------------------
// Mapa
// ---------------------------------------------------------------------------

// Cria o mapa dentro de "element". Devolve a API de controle.
//   options.onSelect(countryId)        -> resposta definitiva (clique, ou botão Confirmar)
//   options.onSelectionChange(id|null) -> mudou a seleção (no modo com confirmação)
//   options.confirmSelection           -> true: primeiro seleciona, depois confirma (telas de toque)
//   options.touch                      -> true: pontos dos países minúsculos maiores (dedo)
export function initializeWorldMap(element, data, options = {}) {
  const L = globalThis.L;
  if (!L) throw new Error("A biblioteca Leaflet não foi carregada (assets/vendor/leaflet).");
  const { onSelect = () => {}, onSelectionChange = () => {} } = options;
  let confirmMode = !!options.confirmSelection;

  const map = L.map(element, {
    minZoom: 1, maxZoom: 8, zoomSnap: 0.25, zoomDelta: 0.5, wheelPxPerZoomLevel: 100,
    worldCopyJump: false, maxBounds: [[-85, -200], [85, 200]], maxBoundsViscosity: 0.9,
    preferCanvas: true, attributionControl: true
  });
  map.attributionControl.setPrefix('<a href="https://leafletjs.com" target="_blank" rel="noopener">Leaflet</a>');
  map.attributionControl.addAttribution("Dados: Natural Earth");
  // Sem "tolerance": uma margem extra nas bordas faria o país vizinho roubar o clique (ex.: Argentina x Chile).
  // Quem precisa de ajuda para ser acertado são os países minúsculos, que têm pontos próprios.
  const renderer = L.canvas({ padding: 0.5 });
  const DOT_RADIUS = options.touch ? 6 : 4.5; // pequenos para não esconder os países; o ponto mais próximo vence

  // Estado
  const entries = new Map(); // id -> { layer, dot, box, geometry, interior (calculado quando preciso) }
  const touched = new Set(); // ids que foram pintados (para limpar na próxima pergunta)
  let tooltips = [];
  let selectedId = null;
  let hoverId = null;
  let locked = true;         // travado até uma pergunta começar

  // Ponto de dentro do país, calculado só quando necessário e guardado.
  function interiorOf(entry) {
    if (!entry.interior) {
      const point = interiorPoint(entry.geometry);
      entry.interior = [point.lat, point.lng];
    }
    return entry.interior;
  }

  function paint(id, kind) {
    const entry = entries.get(id);
    if (!entry) return;
    entry.layer.setStyle(STYLE[kind]);
    entry.dot?.setStyle(DOT_STYLE[kind]);
    if (kind !== "base") touched.add(id);
    // Só seleção e resultado vão para a frente. Passar o mouse NÃO reordena
    // (senão um país "cobriria" os pontos dos microestados vizinhos).
    if (kind === "selected" || kind === "correct" || kind === "wrong") {
      entry.layer.bringToFront();
      raiseDots();
    }
  }

  // Mantém os pontos dos países minúsculos sempre acima de todos os polígonos.
  function raiseDots() {
    dotGroup.eachLayer(dot => dot.bringToFront());
  }

  // Ponto minúsculo mais próximo do local do clique (Vaticano e San Marino ficam a poucos pixels).
  function nearestDotId(containerPoint, fallbackId) {
    if (!containerPoint) return fallbackId;
    let best = null;
    for (const [id, entry] of entries) {
      if (!entry.dot) continue;
      const p = map.latLngToContainerPoint(entry.dot.getLatLng());
      const distance = Math.hypot(p.x - containerPoint.x, p.y - containerPoint.y);
      if (distance <= DOT_RADIUS + 2 && (!best || distance < best.distance)) best = { id, distance };
    }
    return best ? best.id : fallbackId;
  }

  function setHover(id) {
    if (hoverId && hoverId !== selectedId) paint(hoverId, "base");
    hoverId = id;
    if (id && id !== selectedId) paint(id, "hover");
  }

  function setSelected(id) {
    if (selectedId && selectedId !== id) paint(selectedId, "base");
    selectedId = id;
    if (id) paint(id, "selected");
    onSelectionChange(id);
  }

  function choose(id) {
    if (locked) return;
    if (confirmMode) { setSelected(id); return; }
    setHover(null);
    setSelected(id);
    locked = true;
    onSelect(id);
  }

  // Camadas dos países + pontos dos países minúsculos
  const dotGroup = L.layerGroup();
  const geoLayer = L.geoJSON(data.geojson, {
    renderer,
    style: () => ({ ...STYLE.base }),
    onEachFeature(feature, layer) {
      const id = feature.properties.id;
      const box = largestPolygonBox(feature.geometry);
      const entry = { layer, dot: null, box, geometry: feature.geometry, interior: null };
      entries.set(id, entry);
      layer.on({ click: () => choose(id), mouseover: () => !locked && setHover(id), mouseout: () => !locked && setHover(null) });
      if (box.area < TINY_AREA_DEGREES) {
        const dot = L.circleMarker(interiorOf(entry), { renderer, radius: DOT_RADIUS, ...DOT_STYLE.base });
        dot.on({
          click: e => choose(nearestDotId(e.containerPoint, id)),
          mouseover: e => !locked && setHover(nearestDotId(e.containerPoint, id)),
          mouseout: () => !locked && setHover(null)
        });
        entry.dot = dot;
        dotGroup.addLayer(dot);
      }
    }
  }).addTo(map);
  dotGroup.addTo(map);

  // Botão extra: voltar a ver o mundo todo
  const ResetControl = L.Control.extend({
    options: { position: "topleft" },
    onAdd() {
      const bar = L.DomUtil.create("div", "leaflet-bar leaflet-control");
      const button = L.DomUtil.create("a", "map-reset", bar);
      button.href = "#";
      button.title = "Ver o mundo todo";
      button.setAttribute("role", "button");
      button.setAttribute("aria-label", "Ver o mundo todo");
      button.textContent = "◎";
      L.DomEvent.disableClickPropagation(bar);
      L.DomEvent.on(button, "click", event => { L.DomEvent.preventDefault(event); fitWorld(true); });
      return bar;
    }
  });
  new ResetControl().addTo(map);

  function fitWorld(animate = false) {
    if (!element.clientWidth || !element.clientHeight) return; // mapa escondido: nada a ajustar
    map.invalidateSize();
    const bounds = L.latLngBounds(WORLD_BOUNDS);
    map.setMinZoom(Math.max(0.5, map.getBoundsZoom(bounds, false) - 0.5));
    if (animate && !prefersReducedMotion()) map.flyToBounds(bounds, { duration: 0.6 });
    else map.fitBounds(bounds, { animate: false });
  }

  const onWindowResize = () => {
    if (!element.clientWidth) return;
    map.invalidateSize();
    map.setMinZoom(Math.max(0.5, map.getBoundsZoom(L.latLngBounds(WORLD_BOUNDS), false) - 0.5));
  };
  window.addEventListener("resize", onWindowResize);

  function clearTooltips() {
    tooltips.forEach(tooltip => map.removeLayer(tooltip));
    tooltips = [];
  }

  function addLabel(id, text, kind) {
    const entry = entries.get(id);
    if (!entry) return;
    const tooltip = L.tooltip({ permanent: true, direction: "top", offset: [0, -6], className: `map-label ${kind}`, interactive: false })
      .setLatLng(interiorOf(entry)).setContent(text);
    tooltip.addTo(map);
    tooltips.push(tooltip);
  }

  const nameOf = id => data.countries.get(id)?.name ?? id;

  function boundsOf(ids) {
    const boxes = ids.map(id => entries.get(id)?.box).filter(Boolean);
    if (boxes.length === 0) return null;
    return L.latLngBounds(
      [Math.min(...boxes.map(b => b.south)), Math.min(...boxes.map(b => b.west))],
      [Math.max(...boxes.map(b => b.north)), Math.max(...boxes.map(b => b.east))]
    );
  }

  const api = {
    map,

    // Nova pergunta: limpa cores e rótulos, volta ao mundo todo e libera os cliques.
    begin() {
      clearTooltips();
      touched.forEach(id => paint(id, "base"));
      touched.clear();
      selectedId = null;
      hoverId = null;
      onSelectionChange(null);
      locked = false;
      fitWorld(false);
    },

    // Botão "Confirmar" (modo de toque).
    confirm() {
      if (locked || !selectedId) return false;
      locked = true;
      onSelect(selectedId);
      return true;
    },

    clearSelection() {
      if (locked) return;
      if (selectedId) paint(selectedId, "base");
      selectedId = null;
      onSelectionChange(null);
    },

    // Mostra o resultado: país certo em verde, escolha errada em vermelho, com rótulos.
    showResult({ targetId, targetName, chosenId }) {
      locked = true;
      setHover(null);
      if (selectedId && selectedId !== targetId && selectedId !== chosenId) paint(selectedId, "base");
      selectedId = null;
      onSelectionChange(null);
      if (chosenId && chosenId !== targetId) {
        paint(chosenId, "wrong");
        addLabel(chosenId, nameOf(chosenId), "wrong");
      }
      paint(targetId, "correct");
      addLabel(targetId, targetName ?? nameOf(targetId), "correct");

      const bounds = boundsOf([targetId, chosenId].filter(Boolean));
      if (bounds && element.clientWidth) {
        const view = { maxZoom: 5.5, padding: [40, 40] };
        if (prefersReducedMotion()) map.fitBounds(bounds, { ...view, animate: false });
        else map.flyToBounds(bounds, { ...view, duration: 0.9 });
      }
    },

    setConfirmMode(value) { confirmMode = !!value; },
    getSelectedId: () => selectedId,
    isLocked: () => locked,
    hasCountry: id => entries.has(id),

    // Posição de um país na tela (útil para testes automáticos de clique).
    getScreenPoint(id) {
      const entry = entries.get(id);
      if (!entry) return null;
      const point = map.latLngToContainerPoint(interiorOf(entry));
      return { x: point.x, y: point.y };
    },

    destroy() {
      window.removeEventListener("resize", onWindowResize);
      map.remove();
    }
  };

  element.__geomasterMap = api; // permite que os testes automáticos controlem o mapa
  return api;
}

// ---------------------------------------------------------------------------
// Ponte com a tela da partida (js/screens/quiz.js)
// ---------------------------------------------------------------------------

// Cria o "mapRenderer" que a tela da partida usa nas perguntas do tipo mapa:
//   render(container, question, onSelect)           -> nova pergunta
//   showResult(container, feedback, chosenAnswer)   -> mostra acerto/erro no mapa
export function createMapChallengeRenderer(options = {}) {
  const loadData = options.loadData ?? (() => loadCountries());
  const isTouchDevice = options.isTouchDevice
    ?? (() => !!globalThis.matchMedia?.("(pointer: coarse)").matches);

  let parts = null;     // elementos da tela do mapa (criados uma vez)
  let handle = null;    // API do mapa (criada uma vez, depois que os dados carregam)
  let activeOnSelect = () => {};
  let touchMode = false; // true: seleciona e depois confirma (telas de toque)
  let chain = Promise.resolve(); // garante a ordem: carregar -> começar -> mostrar resultado

  function build(container) {
    if (parts && container.contains(parts.wrap)) return parts;
    const wrap = document.createElement("div");
    wrap.className = "world-map-wrap";
    const mapElement = document.createElement("div");
    mapElement.className = "world-map";
    mapElement.setAttribute("aria-label", "Mapa-múndi interativo");

    const confirmBar = document.createElement("div");
    confirmBar.className = "map-confirm";
    confirmBar.hidden = true;
    const confirmText = document.createElement("span");
    confirmText.textContent = "País selecionado";
    const confirmButton = document.createElement("button");
    confirmButton.type = "button";
    confirmButton.className = "button button-primary";
    confirmButton.textContent = "Confirmar escolha";
    const clearButton = document.createElement("button");
    clearButton.type = "button";
    clearButton.className = "button button-quiet";
    clearButton.textContent = "Limpar";
    confirmBar.append(confirmText, confirmButton, clearButton);
    confirmButton.addEventListener("click", () => handle?.confirm());
    clearButton.addEventListener("click", () => handle?.clearSelection());

    const hint = document.createElement("p");
    hint.className = "map-hint";

    wrap.append(mapElement, confirmBar);
    container.replaceChildren(wrap, hint);
    parts = { wrap, mapElement, confirmBar, hint };
    return parts;
  }

  function showError(message) {
    if (!parts) return;
    parts.confirmBar.hidden = true;
    parts.hint.textContent = message;
    parts.hint.classList.add("error");
  }

  return {
    render(container, question, onSelect) {
      const ui = build(container);
      activeOnSelect = onSelect;
      const touch = isTouchDevice();
      ui.hint.classList.remove("error");
      ui.hint.textContent = touch
        ? "Toque em um país para selecioná-lo e confirme. Arraste para mover e use dois dedos para ampliar."
        : "Clique em um país. Use a roda do mouse (ou os botões + e −) para ampliar e arraste para mover.";
      ui.confirmBar.hidden = true;

      chain = chain.then(async () => {
        const data = await loadData();
        if (!handle) {
          handle = initializeWorldMap(ui.mapElement, data, {
            touch,
            onSelect: id => activeOnSelect({ countryId: id }),
            // A barra "Confirmar" só aparece no modo de toque, quando há um país selecionado.
            onSelectionChange: id => { ui.confirmBar.hidden = !(id && touchMode); }
          });
        }
        handle.setConfirmMode(touch);
        touchMode = touch;
        handle.begin();
      }).catch(error => {
        console.error("GeoMaster: falha no mapa.", error);
        showError(error instanceof MapDataError
          ? error.message
          : `Não foi possível mostrar o mapa: ${error.message}`);
      });
    },

    showResult(container, feedback, chosenAnswer) {
      chain = chain.then(() => {
        if (!handle) return;
        parts.confirmBar.hidden = true;
        handle.showResult({
          targetId: feedback.correctAnswer.countryId,
          targetName: feedback.correctAnswer.name,
          chosenId: chosenAnswer?.countryId ?? null
        });
      }).catch(error => console.error("GeoMaster: falha ao mostrar o resultado no mapa.", error));
    }
  };
}
