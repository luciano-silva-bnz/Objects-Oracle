<?php
declare(strict_types=1);

require_once dirname(__DIR__) . '/config/bootstrap.php';

$filiais = app_read_filiais(app_project_path('storage/filiais.json'));
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Schanntech Club Promo</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="assets/styles.css">
</head>
<body class="app-shell">
    <div class="background-glow"></div>
    <main class="relative z-10 mx-auto max-w-[1880px] px-3 py-4 md:px-6">
        <header class="mb-4 rounded-2xl border border-slate-700/70 bg-slate-900/80 p-5 shadow-2xl backdrop-blur">
            <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div class="brand-area">
                    <img class="brand-logo" src="assets/bonanza-logo.png" alt="Bonanza supermercados">
                    <div>
                        <h1 class="text-[2rem] font-bold text-white">Schanntech Club Promo</h1>
                        <p class="text-sm text-slate-300">Consulta de campanhas, itens, meios de pagamento e BINs.</p>
                    </div>
                </div>
                <div class="header-actions">
                    <button id="toggleFiltros" type="button" class="btn-secondary">
                        Exibir filtros
                    </button>
                    <a
                        href="admin/filiais.php"
                        class="btn-secondary no-highlight-link"
                    >
                        Administrar Filiais
                    </a>
                </div>
            </div>
        </header>

        <section class="mb-4 panel">
            <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                <div class="summary-card xl:col-span-1">
                    <p class="summary-label">Promo&ccedil;&otilde;es vis&iacute;veis</p>
                    <p id="resumoPromocoes" class="summary-value">0</p>
                </div>
                <div class="summary-card xl:col-span-1">
                    <p class="summary-label">Filiais com retorno</p>
                    <p id="resumoFiliaisOk" class="summary-value">0</p>
                </div>
                <div class="summary-card xl:col-span-3">
                    <p class="summary-label">Status</p>
                    <p id="statusConsulta" class="summary-small">Aguardando consulta...</p>
                </div>
            </div>

            <div id="apiErrors" class="mt-3 hidden rounded-lg border border-rose-400/50 bg-rose-400/10 px-3 py-2 text-sm text-rose-100"></div>

            <div id="filtrosWrap" class="mt-3 hidden rounded-xl border border-slate-700/80 bg-[#071429]/85 p-3">
                <h2 class="panel-title mb-3">Filtros</h2>
                <div class="mb-3 grid gap-2 md:grid-cols-4">
                    <label class="grid gap-1 md:col-span-2">
                        <span class="text-[11px] uppercase tracking-wide text-slate-300">Busca geral</span>
                        <input id="filtroTexto" type="text" class="input-field" placeholder="T&iacute;tulo, descri&ccedil;&atilde;o, item, BIN...">
                    </label>
                    <label class="grid gap-1">
                        <span class="text-[11px] uppercase tracking-wide text-slate-300">C&oacute;digos de barras</span>
                        <textarea id="filtroCodigos" class="input-field compact-area" placeholder="Cole EANs"></textarea>
                    </label>
                    <label class="grid gap-1">
                        <span class="text-[11px] uppercase tracking-wide text-slate-300">BINs</span>
                        <textarea id="filtroBins" class="input-field compact-area" placeholder="Cole BINs"></textarea>
                    </label>
                </div>

                <div class="mb-3 rounded-lg border border-slate-700/70 bg-slate-950/35 p-2">
                    <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
                        <span class="text-[11px] uppercase tracking-wide text-slate-300">Filtro mensal de vig&ecirc;ncia</span>
                        <div class="flex flex-wrap items-center gap-1">
                            <button id="btnSelecionarMeses" type="button" class="btn-secondary btn-xs">Selecionar todos</button>
                            <button id="btnLimparMeses" type="button" class="btn-secondary btn-xs">Limpar meses</button>
                        </div>
                    </div>
                    <div id="mesesVigenciaContainer" class="month-filter-list"></div>
                </div>

                <div class="mb-3 rounded-lg border border-slate-700/70 bg-slate-950/35 p-2">
                    <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
                        <span class="text-[11px] uppercase tracking-wide text-slate-300">Autores / Patrocinador</span>
                        <div class="flex flex-wrap items-center gap-1 author-actions">
                            <button id="btnSelecionarAutores" type="button" class="btn-secondary btn-xs">Todos</button>
                            <button id="btnLimparAutores" type="button" class="btn-secondary btn-xs">Limpar</button>
                        </div>
                    </div>
                    <p id="autorSelecionadosInfo" class="mb-2 text-xs text-slate-300">Nenhum autor selecionado.</p>
                    <div id="autoresContainer" class="author-list"></div>
                </div>

                <div id="filterNotFoundAlert" class="mb-3 hidden rounded-lg border border-amber-400/60 bg-amber-400/10 px-3 py-2 text-xs text-amber-100"></div>

                <div class="mb-3 filter-actions">
                    <div class="filter-actions-left">
                        <div class="grid gap-1">
                            <label class="text-[11px] uppercase tracking-wide text-slate-300" for="operadorFiltros">Operador</label>
                            <select id="operadorFiltros" class="input-field min-w-[170px]">
                                <option value="and">AND (todos)</option>
                                <option value="or">OR (qualquer)</option>
                            </select>
                        </div>
                        <button id="btnSelecionarTodas" type="button" class="btn-secondary">Selecionar todas</button>
                        <button id="btnLimparFiliais" type="button" class="btn-secondary">Limpar</button>
                        <button id="btnBuscar" type="button" class="btn-secondary">Atualizar campanhas</button>
                        <span id="filiaisSelecionadasInfo" class="ml-1 text-xs text-slate-300">0 selecionada(s)</span>
                    </div>
                    <div class="filter-actions-right">
                        <button id="btnAplicarFiltros" type="button" class="btn-primary">Aplicar filtros</button>
                        <button id="btnLimparFiltros" type="button" class="btn-secondary">Limpar filtros</button>
                    </div>
                </div>

                <div id="filiaisContainer" class="grid max-h-56 grid-cols-3 gap-2 overflow-auto rounded-xl border border-slate-700/70 bg-slate-950/45 p-2 md:grid-cols-5 xl:grid-cols-8"></div>
            </div>
        </section>

        <section class="grid gap-3 xl:grid-cols-12">
            <div class="panel xl:col-span-2">
                <div class="mb-2 flex items-center justify-between gap-2">
                    <h2 class="panel-title">Vig&ecirc;ncia das campanhas</h2>
                    <div class="flex items-center gap-1 vigencia-actions">
                        <button id="btnAplicarVigencias" type="button" class="btn-secondary btn-xs">Aplicar</button>
                        <button id="btnLimparVigencias" type="button" class="btn-secondary btn-xs">Limpar</button>
                    </div>
                </div>
                <p id="vigenciaSelecionadasInfo" class="mb-3 text-xs text-slate-300">Nenhuma campanha selecionada.</p>
                <div id="vigenciaList" class="vigencia-list space-y-2 overflow-auto pr-1"></div>
            </div>

            <div class="panel xl:col-span-10">
                <h2 class="panel-title mb-4">Campanhas e detalhes</h2>
                <div class="overflow-auto rounded-xl border border-slate-700/70">
                    <table class="min-w-[1450px] table-fixed compact-table">
                        <thead>
                            <tr class="bg-slate-800/70 text-left text-xs uppercase tracking-wide text-slate-200">
                                <th class="w-20 px-2 py-2">Filial</th>
                                <th class="w-56 px-2 py-2">T&iacute;tulo</th>
                                <th class="w-64 px-2 py-2">Descri&ccedil;&atilde;o</th>
                                <th class="w-80 px-2 py-2">Itens (nome + c&oacute;digo de barras)</th>
                                <th class="w-80 px-2 py-2">Formas de pagamento / BINs</th>
                                <th class="w-24 px-2 py-2">Limite</th>
                                <th class="w-48 px-2 py-2">Vig&ecirc;ncia</th>
                            </tr>
                        </thead>
                        <tbody id="promocoesBody" class="divide-y divide-slate-800 bg-slate-950/40"></tbody>
                    </table>
                </div>
            </div>
        </section>
    </main>

    <div id="filterLoadingOverlay" class="filter-loading-overlay hidden" aria-hidden="true">
        <div class="filter-loading-card">
            <div class="filter-loading-spinner"></div>
            <p id="filterLoadingText" class="filter-loading-text">Aplicando filtros...</p>
        </div>
    </div>

    <script>
        window.APP_CONFIG = {
            filiais: <?= json_encode($filiais, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) ?>,
            apiUrl: 'api/promocoes.php',
            estado: 'ACEPTADA'
        };
    </script>
    <script src="assets/app.js"></script>
</body>
</html>
