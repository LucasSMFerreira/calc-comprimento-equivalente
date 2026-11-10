// Estado da calculadora: tudo que o usuário escolheu.
const estado = { unidade: "pol", padrao: "pvc", diametro: '3/4"', itens: [] };
let tabela = null; // vem de /api/tabela
let leituraPendente = null; // itens lidos de planilha/texto esperando confirmação
let materialTrechos = null; // material do trecho reto aberto na caixa de trechos
const TRECHO = "trecho-reto";


const $ = (id) => document.getElementById(id);
const br = (n, casas = 2) => n.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
const conexao = (id) => tabela.conexoes.find((c) => c.id === id);
const urlFoto = (id, material) => `/api/fotos/${tabela.versao.id}/${id}/${material}`;
const somar = (lista) => Math.round(lista.reduce((soma, t) => soma + t, 0) * 1000) / 1000;


function avisar(mensagem) {
  $("aviso").textContent = mensagem;
  $("aviso").hidden = false;
  clearTimeout(avisar.timer);
  avisar.timer = setTimeout(() => ($("aviso").hidden = true), 4000);
}

async function api(caminho, opcoes = {}) {
  const resposta = await fetch(caminho, opcoes);
  if (!resposta.ok) {
    const erro = await resposta.json().catch(() => ({}));
    const detalhe = Array.isArray(erro.detail) ? "Dados inválidos." : erro.detail;
    throw new Error(detalhe || `Erro ${resposta.status}`);
  }
  return resposta;
}

function salvar() {
  try { localStorage.setItem("calculadora", JSON.stringify(estado)); } catch { /* sem armazenamento */ }
}

function carregarSalvo() {
  try {
    const salvo = JSON.parse(localStorage.getItem("calculadora"));
    if (salvo) Object.assign(estado, salvo);
  } catch { /* ignora */ }
  // remove itens que não existem na tabela atual
  estado.itens = estado.itens.filter((i) => conexao(i.conexao_id)?.materiais.includes(i.material));
  if (!tabela.diametros.includes(estado.diametro)) estado.diametro = tabela.diametros[0];
}
  // trecho reto salvo antes da caixa de trechos vira um pedaço só
  estado.itens.forEach((i) => { if (i.conexao_id === TRECHO && !i.trechos) i.trechos = [i.quantidade]; });

// ---------- 1. Tubulação ----------
function montarDiametros() {
  const select = $("diametro");
  $("campo-padrao").hidden = estado.unidade !== "mm";
  document.querySelectorAll("[data-unidade]").forEach((b) =>
    b.classList.toggle("ativo", b.dataset.unidade === estado.unidade));

  if (estado.unidade === "pol") {
    select.innerHTML = tabela.diametros.map((d) => `<option value='${d}'>${d}</option>`).join("");
    $("equivale").textContent = "";
  } else {
    const mapa = tabela.padroes_mm[estado.padrao].mapa;
    select.innerHTML = Object.entries(mapa)
      .map(([mm, pol]) => `<option value='${pol}'>${mm} mm</option>`).join("");
    if (!Object.values(mapa).includes(estado.diametro)) estado.diametro = Object.values(mapa)[0];
    $("equivale").textContent = `= ${estado.diametro} na tabela`;
  }
  select.value = estado.diametro;
}

// ---------- 2. Catálogo ----------
function montarCatalogo() {
  const termo = $("busca").value.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const visiveis = tabela.conexoes.filter((c) =>
    c.nome.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().includes(termo));
  $("catalogo").innerHTML = visiveis.map((c) => {
    const qtd = estado.itens.filter((i) => i.conexao_id === c.id).reduce((s, i) => s + i.quantidade, 0);
    return `<button class="peca" data-id="${c.id}" title="Adicionar ${c.nome}">
            ${qtd ? `<span class="contador">${c.id === TRECHO ? `${br(qtd)} m` : br(qtd, 0)}</span>` : ""}
      <img src="${urlFoto(c.id, c.materiais[0])}" alt="" loading="lazy">${c.nome}</button>`;
  }).join("");
}

function adicionar(conexaoId, material, quantidade = 1) {
  const existente = estado.itens.find((i) => i.conexao_id === conexaoId && i.material === material);
  if (conexaoId === TRECHO) {
    // trecho reto: cada valor é um pedaço medido; a quantidade é a soma dos pedaços
    const item = existente || { conexao_id: TRECHO, material, quantidade: 0, trechos: [] };
    if (!existente) estado.itens.push(item);
    item.trechos.push(quantidade);
    item.quantidade = somar(item.trechos);
    return;
  }
  if (existente) existente.quantidade += quantidade;
  else estado.itens.push({ conexao_id: conexaoId, material, quantidade });
}

function juntarRepetidos() {
  // depois de trocar o material, duas linhas podem virar a mesma conexão: junta numa só
  const juntos = [];
  for (const item of estado.itens) {
    const igual = juntos.find((j) => j.conexao_id === item.conexao_id && j.material === item.material);
    if (!igual) { juntos.push(item); continue; }
    igual.quantidade += item.quantidade;
    if (item.trechos) { igual.trechos.push(...item.trechos); igual.quantidade = somar(igual.trechos); }
  }
  estado.itens = juntos;
}

// ---------- Caixa de trechos retos ----------
const itemTrecho = (material) => estado.itens.find((i) => i.conexao_id === TRECHO && i.material === material);

function abrirTrechos(material) {
  materialTrechos = material;
  $("painel-trechos").hidden = false;
  desenharTrechos();
  $("trecho-valor").focus();
}

function desenharTrechos() {
  if ($("painel-trechos").hidden) return;
  const trechos = itemTrecho(materialTrechos)?.trechos ?? [];
  $("trechos-titulo").textContent = `Trechos retos (${materialTrechos})`;
  $("lista-trechos").innerHTML = trechos
    .map((t, i) => `<li>${br(t)} m <button data-remover="${i}" title="Remover">✕</button></li>`).join("");
  const conta = trechos.length > 1 ? ` (${trechos.map((t) => br(t)).join(" + ")})` : "";
  $("trechos-total").textContent = `${br(somar(trechos))} m${conta}`;
}

function somarTrecho() {
  const valor = Number($("trecho-valor").value.replace(",", "."));
  if (!(valor > 0)) return avisar("Digite um comprimento maior que zero, em metros. Ex.: 1,20");
  adicionar(TRECHO, materialTrechos, valor);
  $("trecho-valor").value = "";
  $("trecho-valor").focus();
  atualizar();
}

function removerTrecho(indice) {
  const item = itemTrecho(materialTrechos);
  item.trechos.splice(indice, 1);
  item.quantidade = somar(item.trechos);
  if (!item.trechos.length) estado.itens.splice(estado.itens.indexOf(item), 1);
  atualizar();
}

// ---------- 3. Itens e resultado ----------
function linhaHtml(linha, indice) {
  const item = estado.itens[indice];
  const c = conexao(item.conexao_id);
  const opcoes = c.materiais.map((m) => `<option ${m === item.material ? "selected" : ""}>${m}</option>`).join("");
  const quantidade = item.conexao_id === TRECHO
    ? `${br(item.quantidade)} m <button data-acao="trechos" title="Ver e somar trechos">✎ Trechos</button>`
    : `<button data-acao="menos">−</button>
      <input data-campo="quantidade" type="number" min="1" step="1" value="${item.quantidade}">
      <button data-acao="mais">+</button>`;
  return `<tr data-indice="${indice}">
    <td><img src="${urlFoto(c.id, item.material)}" alt=""></td>
    <td>${c.nome}</td>
    <td><select data-campo="material">${opcoes}</select></td>
    <td><span class="qtd">${quantidade}</span></td>
    <td>${linha ? br(linha.leq_unitario) : "–"}</td>
    <td>${linha ? br(linha.subtotal) : "–"}</td>
    <td><button data-acao="remover" title="Remover">✕</button></td></tr>`;
}

let pedidoAtual = 0; // evita que uma resposta antiga sobrescreva uma mais nova

async function atualizar() {
  const meuPedido = ++pedidoAtual;
  salvar();
  montarCatalogo();
  $("vazio").hidden = estado.itens.length > 0;
  let resultado = null;
  try {
    const resposta = await api("/api/calcular", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ diametro: estado.diametro, itens: estado.itens }),
    });
    resultado = await resposta.json();
  } catch (erro) {
    avisar(erro.message);
  }
     if (meuPedido !== pedidoAtual) return; // chegou outra atualização no meio do caminho 



  const linhaDe = (i) => resultado?.linhas.find((l) => l.conexao_id === i.conexao_id && l.material === i.material);
  $("itens").innerHTML = estado.itens.map((item, indice) => linhaHtml(linhaDe(item), indice)).join("");
  $("total-conexoes").textContent = `${br(resultado?.total_conexoes ?? 0)} m`;
  $("total-retos").textContent = `${br(resultado?.total_trechos_retos ?? 0)} m`;
  $("total").textContent = `${br(resultado?.total ?? 0)} m`;
    desenharTrechos();
}

// ---------- Importar planilha / texto ----------
function mostrarConfirmacao(leitura) {
  leituraPendente = leitura;
  const itens = leitura.itens.map((i) =>
    `<li>${br(i.quantidade, Number.isInteger(i.quantidade) ? 0 : 2)} × ${conexao(i.conexao_id).nome} (${i.material})</li>`).join("");
  const pendentes = leitura.pendentes.map((p) => `<li class="erro">${p}</li>`).join("");
  const avisos = leitura.avisos.map((a) => `<li>${a}</li>`).join("");
  $("confirmacao").innerHTML = `
    <strong>Confira o que eu entendi${leitura.usou_ia ? " (com ajuda da IA)" : ""}:</strong>
    ${leitura.diametro ? `<span>Diâmetro: ${leitura.diametro}</span>` : ""}
    <ul>${itens || "<li>Nenhum item reconhecido.</li>"}</ul>
    ${pendentes ? `<span>Não entendi:</span><ul>${pendentes}</ul>` : ""}
    ${avisos ? `<span>Avisos:</span><ul>${avisos}</ul>` : ""}
    <div class="acoes"><button id="btn-confirmar" class="principal" ${leitura.itens.length ? "" : "disabled"}>
      Adicionar à calculadora</button><button id="btn-cancelar">Cancelar</button></div>`;
  $("confirmacao").hidden = false;
}

function confirmarLeitura() {
  if (leituraPendente.diametro) {
    estado.unidade = "pol";
    estado.diametro = leituraPendente.diametro;
    montarDiametros();
  }
  leituraPendente.itens.forEach((i) => adicionar(i.conexao_id, i.material, i.quantidade));
  atualizar();
  $("confirmacao").hidden = true;
  $("painel-texto").hidden = true;
}

// ---------- Eventos ----------
function ligarEventos() {
  document.querySelectorAll("[data-unidade]").forEach((botao) =>
    botao.addEventListener("click", () => { estado.unidade = botao.dataset.unidade; montarDiametros(); atualizar(); }));
  $("padrao").addEventListener("change", (e) => { estado.padrao = e.target.value; montarDiametros(); atualizar(); });
  $("diametro").addEventListener("change", (e) => { estado.diametro = e.target.value; montarDiametros(); atualizar(); });
  $("busca").addEventListener("input", montarCatalogo);

  $("catalogo").addEventListener("click", (e) => {
    const botao = e.target.closest(".peca");
    if (!botao) return;
    const material = conexao(botao.dataset.id).materiais[0];
    if (botao.dataset.id === TRECHO) return abrirTrechos(material); // abre a caixa para somar os trechos
    adicionar(botao.dataset.id, material);
    atualizar();
  });

  $("itens").addEventListener("click", (e) => {
    const acao = e.target.dataset.acao;
    if (!acao) return;
    const indice = Number(e.target.closest("tr").dataset.indice);
    const item = estado.itens[indice];
    if (acao === "trechos") return abrirTrechos(item.material);
    if (acao === "mais") item.quantidade += 1;
    if (acao === "menos") item.quantidade = Math.max(1, item.quantidade - 1);
    if (acao === "remover") estado.itens.splice(indice, 1);
    atualizar();
  });

  $("itens").addEventListener("change", (e) => {
    const indice = Number(e.target.closest("tr").dataset.indice);
    const item = estado.itens[indice];
    if (e.target.dataset.campo === "material") {
      item.material = e.target.value;
      juntarRepetidos();
      if (item.conexao_id === TRECHO) materialTrechos = item.material;
    }
    if (e.target.dataset.campo === "quantidade") {
      const valor = Number(e.target.value);
      if (valor > 0) item.quantidade = valor; else avisar("A quantidade precisa ser maior que zero.");
    }
    atualizar();
  });

  $("btn-limpar").addEventListener("click", () => {
    if (estado.itens.length && confirm("Apagar todos os itens?")) {
      estado.itens = [];
      $("painel-trechos").hidden = true;
      atualizar();
    }
  });

  $("btn-somar-trecho").addEventListener("click", somarTrecho);
  $("trecho-valor").addEventListener("keydown", (e) => { if (e.key === "Enter") somarTrecho(); });
  $("lista-trechos").addEventListener("click", (e) => {
    if (e.target.dataset.remover) removerTrecho(Number(e.target.dataset.remover));
  });
  $("btn-fechar-trechos").addEventListener("click", () => { $("painel-trechos").hidden = true; });

  $("btn-texto").addEventListener("click", () => { $("painel-texto").hidden = !$("painel-texto").hidden; });

  $("btn-interpretar").addEventListener("click", async () => {
    const botao = $("btn-interpretar");
    botao.disabled = true;
    botao.textContent = "Interpretando... (com IA pode levar até 1 min)";
    try {
      const resposta = await api("/api/itens/texto", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto: $("texto").value, usar_ia: $("usar-ia").checked }),
      });
      mostrarConfirmacao(await resposta.json());
    } catch (erro) {
      avisar(erro.message);
    } finally {
      botao.disabled = false;
      botao.textContent = "Interpretar";
    }
  });

  $("arquivo-itens").addEventListener("change", async (e) => {
    const dados = new FormData();
    dados.append("arquivo", e.target.files[0]);
    e.target.value = "";
    try {
      const resposta = await api("/api/itens/planilha", { method: "POST", body: dados });
      mostrarConfirmacao(await resposta.json());
    } catch (erro) {
      avisar(erro.message);
    }
  });

  $("confirmacao").addEventListener("click", (e) => {
    if (e.target.id === "btn-confirmar") confirmarLeitura();
    if (e.target.id === "btn-cancelar") $("confirmacao").hidden = true;
  });

  $("btn-pdf").addEventListener("click", async () => {
    try {
      const resposta = await api("/api/memorial", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ diametro: estado.diametro, itens: estado.itens }),
      });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(await resposta.blob());
      link.download = "memorial-de-calculo.pdf";
      link.click();
    } catch (erro) {
      avisar(erro.message);
    }
  });
}

async function iniciar() {
  tabela = await (await api("/api/tabela")).json();
  $("versao").textContent = `v${tabela.versao.id} – ${tabela.versao.nome}`;
  $("padrao").innerHTML = Object.entries(tabela.padroes_mm)
    .map(([chave, p]) => `<option value="${chave}">${p.nome}</option>`).join("");
  carregarSalvo();
  $("padrao").value = estado.padrao;
  montarDiametros();
  ligarEventos();
  atualizar();
}

iniciar().catch((erro) => avisar(`Não consegui carregar a tabela: ${erro.message}`));