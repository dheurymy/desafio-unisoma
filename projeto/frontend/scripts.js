const $ = (id) => document.getElementById(id);

const PASSOS = {
    1: { el: $("passo1"), btn: $("btnPlanilha"), status: $("arquivoSelecionado") },
    2: { el: $("passo2"), btn: $("btnExecutar"), status: $("statusProcessamento") },
    3: { el: $("passo3"), btn: $("btnResultado"), status: $("statusResultado") },
};

/* ---------- utilidades ---------- */

function setEstado(n, estado, texto) {
    const p = PASSOS[n];

    p.el.dataset.estado = estado;
    p.btn.disabled = estado === "bloqueado" || estado === "rodando";

    if (texto !== undefined) {
        p.status.textContent = texto;
    }
}

function log(msg, tipo = "info") {
    const linha = document.createElement("div");

    const hora = document.createElement("span");
    hora.className = "log-hora";
    hora.textContent = new Date().toLocaleTimeString("pt-BR");

    linha.append(hora, document.createTextNode(msg));

    if (tipo !== "info") {
        linha.className = "log-" + tipo;
    }

    const logs = $("logs");

    logs.appendChild(linha);
    logs.scrollTop = logs.scrollHeight;
}

async function api(metodo, ...args) {
    if (!window.pywebview || !window.pywebview.api) {
        throw new Error(
            "Interface não conectada ao Python. Abra o app pelo executável."
        );
    }

    return await window.pywebview.api[metodo](...args);
}

function resetarAPartirDe(n) {
    const textos = {
        2: "Aguardando planilha",
        3: "Ainda não gerado",
    };

    for (let i = n; i <= 3; i++) {
        setEstado(i, "bloqueado", textos[i]);
    }

    $("resumo").hidden = true;
}

/* ---------- passo 1 ---------- */

async function selecionarPlanilha() {
    try {
        const caminho = await api("selecionar_planilha");

        if (!caminho) return;

        const nome = caminho.split(/[\\/]/).pop();

        $("logs").replaceChildren();

        setEstado(1, "ok", nome);

        PASSOS[1].btn.textContent = "Trocar planilha";

        log(`Planilha selecionada: ${nome}`);

        resetarAPartirDe(2);

        setEstado(2, "ativo", "Pronto para gerar");
    } catch (e) {
        log(e.message, "erro");
    }
}

/* ---------- passo 2 ---------- */

async function executar() {
    setEstado(2, "rodando", "Otimizando...");

    resetarAPartirDe(3);

    const soNecessarias = $("chkSoNecessarias").checked;

    log(
        soNecessarias
            ? "Executando o modelo de otimização (só as turmas necessárias)..."
            : "Executando o modelo de otimização..."
    );

    try {
        const res = await api("executar", soNecessarias);

        if (res.pdf) {
            log("Relatório PDF gerado.", "ok");
        }

        const incs = res.inconsistencias || [];

        incs.forEach((i) => log(i, "aviso"));

        if (!res.ok) {
            setEstado(
                2,
                "erro",
                res.mensagem || "Não foi possível ensalar"
            );

            log(
                res.mensagem || "Falha no ensalamento.",
                "erro"
            );

            if (incs.length) {
                log(
                    "Detalhes na aba Inconsistências do Excel.",
                    "aviso"
                );
            }

            mostrarResumo([]);

            if (res.arquivo_gerado) {
                setEstado(
                    3,
                    "ativo",
                    "Planilha com inconsistências"
                );
            }

            return;
        }

        const msg = incs.length
            ? `${res.mensagem} · ${incs.length} inconsistência(s)`
            : res.mensagem || "Turmas geradas";

        setEstado(2, "ok", msg);

        log(
            res.mensagem || "Ensalamento concluído.",
            "ok"
        );

        if (incs.length) {
            log(
                `${incs.length} inconsistência(s) registradas na aba Inconsistências.`,
                "aviso"
            );
        }

        mostrarResumo(res.turmas || []);

        setEstado(3, "ativo", "Excel e PDF prontos");
    } catch (e) {
        setEstado(2, "erro", "Falha no processamento");
        log(e.message, "erro");
    }
}

/* ---------- resumo ---------- */

function mostrarResumo(turmas) {
    const corpo = $("resumoCorpo");

    corpo.replaceChildren();

    turmas.forEach((t) => {
        const tr = document.createElement("tr");

        [t.turma, t.total, t.m, t.f].forEach((v) => {
            const td = document.createElement("td");
            td.textContent = v;
            tr.appendChild(td);
        });

        corpo.appendChild(tr);
    });

    $("resumo").hidden = turmas.length === 0;
}

/* ---------- resultado ---------- */

async function abrirResultado() {
    try {
        await api("abrir_resultado");
        log("Excel e PDF abertos.");
    } catch (e) {
        log(e.message, "erro");
    }
}

/* ---------- inicialização ---------- */

document.addEventListener("DOMContentLoaded", () => {
    PASSOS[1].btn.addEventListener("click", selecionarPlanilha);
    PASSOS[2].btn.addEventListener("click", executar);
    PASSOS[3].btn.addEventListener("click", abrirResultado);

    log("Sistema iniciado.");
});