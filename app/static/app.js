// Estado da calculadora: tudo que o usuário escolheu.
const estado = { unidade: "pol", padrao: "pvc", diametro: '3/4"', itens: [] };
let tabela = null; // vem de /api/tabela
let leituraPendente = null; // itens lidos de planilha/texto esperando confirmação

const $ = (id) => document.getElementById(id);
const br = (n, casas = 2) => n.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
const conexao = (id) => tabela.conexoes.find((c) => c.id === id);
const urlFoto = (id, material) => `/api/fotos/${tabela.versao.id}/${id}/${material}`;

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
      ${qtd ? `<span class="contador">${br(qtd, 0)}</span>` : ""}
      <img src="${urlFoto(c.id, c.materiais[0])}" alt="" loading="lazy">${c.nome}</button>`;
  }).join("");
}

function adicionar(conexaoId, material, quantidade = 1) {
  const existente = estado.itens.find((i) => i.conexao_id === conexaoId && i.material === material);
  if (existente) existente.quantidade += quantidade;
  else estado.itens.push({ conexao_id: conexaoId, material, quantidade });
}

// ---------- 3. Itens e resultado ----------
function linhaHtml(linha, indice) {
  const item = estado.itens[indice];
  const c = conexao(item.conexao_id);
  const opcoes = c.materiais.map((m) => `<option ${m === item.material ? "selected" : ""}>${m}</option>`).join("");
  const passo = item.conexao_id === "trecho-reto" ? "0.1" : "1";
  return `<tr data-indice="${indice}">
    <td><img src="${urlFoto(c.id, item.material)}" alt=""></td>
    <td>${c.nome}</td>
    <td><select data-campo="material">${opcoes}</select></td>
    <td><span class="qtd"><button data-acao="menos">−</button>
      <input data-campo="quantidade" type="number" min="${passo}" step="${passo}" value="${item.quantidade}">
      <button data-acao="mais">+</button></span></td>
    <td>${linha ? br(linha.leq_unitario) : "–"}</td>
    <td>${linha ? br(linha.subtotal) : "–"}</td>
    <td><button data-acao="remover" title="Remover">✕</button></td></tr>`;
}

async function atualizar() {
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
  const linhaDe = (i) => resultado?.linhas.find((l) => l.conexao_id === i.conexao_id && l.material === i.material);
  $("itens").innerHTML = estado.itens.map((item, indice) => linhaHtml(linhaDe(item), indice)).join("");
  $("total-conexoes").textContent = `${br(resultado?.total_conexoes ?? 0)} m`;
  $("total-retos").textContent = `${br(resultado?.total_trechos_retos ?? 0)} m`;
  $("total").textContent = `${br(resultado?.total ?? 0)} m`;
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
    adicionar(botao.dataset.id, conexao(botao.dataset.id).materiais[0]);
    atualizar();
  });

  $("itens").addEventListener("click", (e) => {
    const acao = e.target.dataset.acao;
    if (!acao) return;
    const indice = Number(e.target.closest("tr").dataset.indice);
    const item = estado.itens[indice];
    const passo = item.conexao_id === "trecho-reto" ? 0.5 : 1;
    if (acao === "mais") item.quantidade += passo;
    if (acao === "menos") item.quantidade = Math.max(passo, item.quantidade - passo);
    if (acao === "remover") estado.itens.splice(indice, 1);
    atualizar();
  });

  $("itens").addEventListener("change", (e) => {
    const indice = Number(e.target.closest("tr").dataset.indice);
    const item = estado.itens[indice];
    if (e.target.dataset.campo === "material") item.material = e.target.value;
    if (e.target.dataset.campo === "quantidade") {
      const valor = Number(e.target.value);
      if (valor > 0) item.quantidade = valor; else avisar("A quantidade precisa ser maior que zero.");
    }
    atualizar();
  });

  $("btn-limpar").addEventListener("click", () => {
    if (estado.itens.length && confirm("Apagar todos os itens?")) { estado.itens = []; atualizar(); }
  });

  $("btn-texto").addEventListener("click", () => { $("painel-texto").hidden = !$("painel-texto").hidden; });

  $("btn-interpretar").addEventListener("click", async () => {
    const botao = $("btn-interpretar");
    botao.disabled = true;
    botao.textContent = "Interpretando... (com IA pode levar até 1 min)";
    try {
      const resposta = await api("/api/itens/texto", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto: $("texto").value }),
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