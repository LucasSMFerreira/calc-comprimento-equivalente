const $ = (id) => document.getElementById(id);

function avisar(mensagem) {
  $("aviso").textContent = mensagem;
  $("aviso").hidden = false;
  setTimeout(() => ($("aviso").hidden = true), 4000);
}

async function api(caminho, opcoes = {}) {
  opcoes.headers = { ...(opcoes.headers || {}), "X-Admin-Token": $("token").value };
  const resposta = await fetch(caminho, opcoes);
  const dados = await resposta.json().catch(() => ({}));
  if (!resposta.ok) throw new Error(dados.detail || `Erro ${resposta.status}`);
  return dados;
}

function arquivoSelecionado() {
  const dados = new FormData();
  dados.append("arquivo", $("arquivo").files[0]);
  return dados;
}

async function listarVersoes() {
  const versoes = await api("/api/tabelas");
  $("versoes").innerHTML = versoes.map((v) => `<tr>
    <td>v${v.id}</td><td>${v.nome}</td><td>${v.criada_em.replace("T", " ")}</td>
    <td>${v.ativa ? "<strong>Em uso</strong>" : ""}</td>
    <td><a class="botao" href="/api/tabelas/${v.id}/exportar">Exportar</a>
      ${v.ativa ? "" : `<button data-ativar="${v.id}">Usar esta</button>`}</td></tr>`).join("");
}

$("btn-previa").addEventListener("click", async () => {
  if (!$("arquivo").files.length) return avisar("Escolha um arquivo .xlsx.");
  try {
    const p = await api("/api/tabelas/previa", { method: "POST", body: arquivoSelecionado() });
    const lista = (itens, classe = "") => itens.map((t) => `<li class="${classe}">${t}</li>`).join("");
    $("previa").innerHTML = p.valida
      ? `<strong>Planilha válida:</strong> ${p.conexoes} conexões, ${p.diametros.length} diâmetros, ${p.fotos} fotos.
         <span>O que muda em relação à tabela em uso:</span>
         <ul>${lista(p.mudancas) || "<li>Nenhum valor diferente.</li>"}</ul>
         ${p.avisos.length ? `<span>Valores para conferir:</span><ul>${lista(p.avisos)}</ul>` : ""}
         <div class="acoes"><button id="btn-salvar" class="principal">Salvar e usar esta tabela</button></div>`
      : `<strong class="erro">A planilha tem erros e não pode ser usada:</strong><ul>${lista(p.erros, "erro")}</ul>`;
    $("previa").hidden = false;
  } catch (erro) {
    avisar(erro.message);
  }
});

$("previa").addEventListener("click", async (e) => {
  if (e.target.id !== "btn-salvar") return;
  const dados = arquivoSelecionado();
  dados.append("nome", $("nome").value || "Tabela enviada");
  try {
    const { id } = await api("/api/tabelas", { method: "POST", body: dados });
    avisar(`Versão v${id} salva e em uso.`);
    $("previa").hidden = true;
    listarVersoes();
  } catch (erro) {
    avisar(erro.message);
  }
});

$("versoes").addEventListener("click", async (e) => {
  const id = e.target.dataset.ativar;
  if (!id) return;
  try {
    await api(`/api/tabelas/${id}/ativar`, { method: "POST" });
    avisar(`Agora a calculadora usa a versão v${id}.`);
    listarVersoes();
  } catch (erro) {
    avisar(erro.message);
  }
});

listarVersoes().catch((erro) => avisar(erro.message));