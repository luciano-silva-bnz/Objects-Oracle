(function () {
    'use strict';

    const config = window.APP_CONFIG || {};
    const state = {
        allPromocoes: [],
        inputFilteredPromocoes: [],
        filteredPromocoes: [],
        selectedVigenciaKeys: new Set(),
        selectedMonthKeys: new Set(),
        selectedAuthorKeys: new Set(),
        meta: null,
        loading: false,
        applying: false,
    };

    const elements = {};
    let filtrosAbertos = false;

    document.addEventListener('DOMContentLoaded', init);

    function init() {
        bindElements();
        renderFiliais();
        bindEvents();
        updateSelectedFiliaisInfo();
        fetchPromocoes();
    }

    function bindElements() {
        elements.filiaisContainer = document.getElementById('filiaisContainer');
        elements.filiaisInfo = document.getElementById('filiaisSelecionadasInfo');
        elements.btnSelecionarTodas = document.getElementById('btnSelecionarTodas');
        elements.btnLimparFiliais = document.getElementById('btnLimparFiliais');
        elements.btnBuscar = document.getElementById('btnBuscar');
        elements.btnAplicarFiltros = document.getElementById('btnAplicarFiltros');
        elements.btnLimparFiltros = document.getElementById('btnLimparFiltros');
        elements.btnAplicarVigencias = document.getElementById('btnAplicarVigencias');
        elements.btnLimparVigencias = document.getElementById('btnLimparVigencias');
        elements.btnSelecionarMeses = document.getElementById('btnSelecionarMeses');
        elements.btnLimparMeses = document.getElementById('btnLimparMeses');
        elements.btnSelecionarAutores = document.getElementById('btnSelecionarAutores');
        elements.btnLimparAutores = document.getElementById('btnLimparAutores');

        elements.toggleFiltros = document.getElementById('toggleFiltros');
        elements.filtrosWrap = document.getElementById('filtrosWrap');

        elements.operador = document.getElementById('operadorFiltros');
        elements.filtroTexto = document.getElementById('filtroTexto');
        elements.filtroCodigos = document.getElementById('filtroCodigos');
        elements.filtroBins = document.getElementById('filtroBins');

        elements.statusConsulta = document.getElementById('statusConsulta');
        elements.apiErrors = document.getElementById('apiErrors');
        elements.filterNotFoundAlert = document.getElementById('filterNotFoundAlert');
        elements.resumoPromocoes = document.getElementById('resumoPromocoes');
        elements.resumoFiliaisOk = document.getElementById('resumoFiliaisOk');

        elements.vigenciaList = document.getElementById('vigenciaList');
        elements.vigenciaSelecionadasInfo = document.getElementById('vigenciaSelecionadasInfo');
        elements.mesesVigenciaContainer = document.getElementById('mesesVigenciaContainer');
        elements.autoresContainer = document.getElementById('autoresContainer');
        elements.autorSelecionadosInfo = document.getElementById('autorSelecionadosInfo');
        elements.promocoesBody = document.getElementById('promocoesBody');

        elements.filterLoadingOverlay = document.getElementById('filterLoadingOverlay');
        elements.filterLoadingText = document.getElementById('filterLoadingText');
    }

    function bindEvents() {
        elements.btnSelecionarTodas.addEventListener('click', () => {
            setFilialSelection(true);
        });

        elements.btnLimparFiliais.addEventListener('click', () => {
            setFilialSelection(false);
        });

        elements.toggleFiltros.addEventListener('click', toggleFiltros);
        elements.filiaisContainer.addEventListener('change', updateSelectedFiliaisInfo);
        elements.btnBuscar.addEventListener('click', fetchPromocoes);

        elements.btnAplicarFiltros.addEventListener('click', () => {
            applyFiltersWithLoading('Aplicando filtros...');
        });

        elements.btnLimparFiltros.addEventListener('click', () => {
            elements.filtroTexto.value = '';
            elements.filtroCodigos.value = '';
            elements.filtroBins.value = '';
            elements.operador.value = 'and';
            state.selectedMonthKeys.clear();
            state.selectedAuthorKeys.clear();
            applyFiltersWithLoading('Limpando filtros...');
        });

        elements.btnAplicarVigencias.addEventListener('click', () => {
            applyFiltersWithLoading('Aplicando seleção de campanhas...');
        });

        elements.btnLimparVigencias.addEventListener('click', () => {
            state.selectedVigenciaKeys.clear();
            updateSelectedVigenciasInfo();
            updateVigenciaSelectionStyles();
            applyFiltersWithLoading('Limpando seleção de campanhas...');
        });

        elements.vigenciaList.addEventListener('click', onVigenciaClick);
        elements.mesesVigenciaContainer.addEventListener('click', onMesClick);
        elements.autoresContainer.addEventListener('click', onAutorClick);

        elements.btnSelecionarMeses.addEventListener('click', () => {
            const selectedFiliais = getSelectedFiliais();
            const filialSet = new Set(selectedFiliais);
            const scopedPromocoes = state.allPromocoes.filter((promo) => filialSet.has(Number(promo.filial)));
            const allMonthKeys = getAvailableMonthKeys(scopedPromocoes);
            state.selectedMonthKeys = new Set(allMonthKeys);
            renderMonthFilters(scopedPromocoes);
        });

        elements.btnLimparMeses.addEventListener('click', () => {
            state.selectedMonthKeys.clear();
            const selectedFiliais = getSelectedFiliais();
            const filialSet = new Set(selectedFiliais);
            const scopedPromocoes = state.allPromocoes.filter((promo) => filialSet.has(Number(promo.filial)));
            renderMonthFilters(scopedPromocoes);
        });

        elements.btnSelecionarAutores.addEventListener('click', () => {
            const selectedFiliais = getSelectedFiliais();
            const filialSet = new Set(selectedFiliais);
            const scopedPromocoes = state.allPromocoes.filter((promo) => filialSet.has(Number(promo.filial)));
            const authorKeys = getAvailableAuthorKeys(scopedPromocoes);
            state.selectedAuthorKeys = new Set(authorKeys);
            renderAuthorFilters(scopedPromocoes);
        });

        elements.btnLimparAutores.addEventListener('click', () => {
            state.selectedAuthorKeys.clear();
            const selectedFiliais = getSelectedFiliais();
            const filialSet = new Set(selectedFiliais);
            const scopedPromocoes = state.allPromocoes.filter((promo) => filialSet.has(Number(promo.filial)));
            renderAuthorFilters(scopedPromocoes);
        });

        [elements.filtroTexto, elements.filtroCodigos, elements.filtroBins].forEach((input) => {
            input.addEventListener('keydown', (event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    applyFiltersWithLoading('Aplicando filtros...');
                }
            });
        });
    }

    function renderFiliais() {
        const filiais = Array.isArray(config.filiais) ? config.filiais : [];
        if (filiais.length === 0) {
            elements.filiaisContainer.innerHTML = '<p class="col-span-3 text-xs text-slate-400">Nenhuma filial cadastrada.</p>';
            return;
        }

        elements.filiaisContainer.innerHTML = filiais
            .map((filial) => {
                const id = `filial-${filial}`;
                return `
                    <label for="${id}" class="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900/60 px-2 py-2 text-xs text-slate-200">
                        <input id="${id}" type="checkbox" class="filial-checkbox accent-cyan-400" value="${escapeHtml(String(filial))}" checked>
                        <span>Filial ${escapeHtml(String(filial))}</span>
                    </label>
                `;
            })
            .join('');
    }

    function toggleFiltros() {
        filtrosAbertos = !filtrosAbertos;
        elements.filtrosWrap.classList.toggle('hidden', !filtrosAbertos);
        elements.toggleFiltros.textContent = filtrosAbertos ? 'Ocultar filtros' : 'Exibir filtros';
    }

    function setFilialSelection(checked) {
        getFilialCheckboxes().forEach((checkbox) => {
            checkbox.checked = checked;
        });
        updateSelectedFiliaisInfo();
    }

    function getFilialCheckboxes() {
        return Array.from(elements.filiaisContainer.querySelectorAll('.filial-checkbox'));
    }

    function getSelectedFiliais() {
        return getFilialCheckboxes()
            .filter((checkbox) => checkbox.checked)
            .map((checkbox) => Number.parseInt(checkbox.value, 10))
            .filter((value) => Number.isFinite(value) && value > 0);
    }

    function updateSelectedFiliaisInfo() {
        const selected = getSelectedFiliais();
        elements.filiaisInfo.textContent = `${selected.length} selecionada(s)`;
    }

    function onVigenciaClick(event) {
        const target = event.target.closest('.vigencia-item[data-key]');
        if (!target) {
            return;
        }

        const key = String(target.getAttribute('data-key') || '');
        if (key === '') {
            return;
        }

        if (state.selectedVigenciaKeys.has(key)) {
            state.selectedVigenciaKeys.delete(key);
        } else {
            state.selectedVigenciaKeys.add(key);
        }

        target.classList.toggle('is-selected', state.selectedVigenciaKeys.has(key));
        updateSelectedVigenciasInfo();
    }

    function updateSelectedVigenciasInfo() {
        elements.vigenciaSelecionadasInfo.textContent = state.selectedVigenciaKeys.size > 0
            ? `${state.selectedVigenciaKeys.size} campanha(s) selecionada(s). Clique em "Aplicar seleção".`
            : 'Nenhuma campanha selecionada.';
    }

    function onMesClick(event) {
        const button = event.target.closest('.month-chip[data-month-key]');
        if (!button) {
            return;
        }

        const monthKey = String(button.getAttribute('data-month-key') || '');
        if (monthKey === '') {
            return;
        }

        if (state.selectedMonthKeys.has(monthKey)) {
            state.selectedMonthKeys.delete(monthKey);
        } else {
            state.selectedMonthKeys.add(monthKey);
        }

        const selectedFiliais = getSelectedFiliais();
        const filialSet = new Set(selectedFiliais);
        const scopedPromocoes = state.allPromocoes.filter((promo) => filialSet.has(Number(promo.filial)));
        renderMonthFilters(scopedPromocoes);
    }

    function onAutorClick(event) {
        const button = event.target.closest('.author-chip[data-author-key]');
        if (!button) {
            return;
        }

        const authorKey = String(button.getAttribute('data-author-key') || '');
        if (authorKey === '') {
            return;
        }

        if (state.selectedAuthorKeys.has(authorKey)) {
            state.selectedAuthorKeys.delete(authorKey);
        } else {
            state.selectedAuthorKeys.add(authorKey);
        }

        const selectedFiliais = getSelectedFiliais();
        const filialSet = new Set(selectedFiliais);
        const scopedPromocoes = state.allPromocoes.filter((promo) => filialSet.has(Number(promo.filial)));
        renderAuthorFilters(scopedPromocoes);
    }

    function applyFiltersWithLoading(message) {
        if (state.loading || state.applying) {
            return;
        }

        state.applying = true;
        showFilterOverlay(message);

        window.setTimeout(() => {
            applyFiltersAndRender();
            hideFilterOverlay();
            state.applying = false;
        }, 10);
    }

    function showFilterOverlay(message) {
        elements.filterLoadingText.textContent = message;
        elements.filterLoadingOverlay.classList.remove('hidden');
    }

    function hideFilterOverlay() {
        elements.filterLoadingOverlay.classList.add('hidden');
    }

    async function fetchPromocoes() {
        const filiais = getSelectedFiliais();
        if (filiais.length === 0) {
            state.allPromocoes = [];
            state.inputFilteredPromocoes = [];
            state.filteredPromocoes = [];
            state.selectedVigenciaKeys.clear();
            state.selectedAuthorKeys.clear();
            state.meta = null;
            setStatus('Selecione ao menos uma filial para consultar.');
            renderErrors([]);
            renderAll();
            return;
        }

        const apiUrl = config.apiUrl || 'api/promocoes.php';
        const estado = config.estado || 'ACEPTADA';
        const operador = elements.operador.value || 'and';
        const params = new URLSearchParams({
            filiais: filiais.join(','),
            estado,
            op: operador,
        });

        setLoading(true);
        showFilterOverlay(`Consultando campanhas de ${filiais.length} filial(is)...`);
        setStatus(`Processando consulta para ${filiais.length} filial(is)...`);

        try {
            const response = await fetch(`${apiUrl}?${params.toString()}`, {
                method: 'GET',
                headers: {
                    Accept: 'application/json',
                },
            });

            const payload = await response.json();
            if (!response.ok) {
                const backendError = payload && payload.error ? ` ${payload.error}` : '';
                throw new Error(`Falha na consulta (${response.status}).${backendError}`);
            }

            state.allPromocoes = Array.isArray(payload.data) ? payload.data : [];
            state.selectedVigenciaKeys.clear();
            state.selectedAuthorKeys.clear();
            state.meta = payload.meta || null;
            applyFiltersAndRender();

            const timestamp = state.meta && state.meta.atualizadoEm ? formatDate(state.meta.atualizadoEm) : 'agora';
            setStatus(`Consulta finalizada em ${timestamp}.`);
            renderErrors(state.meta && Array.isArray(state.meta.filiaisComErro) ? state.meta.filiaisComErro : []);
        } catch (error) {
            state.allPromocoes = [];
            state.inputFilteredPromocoes = [];
            state.filteredPromocoes = [];
            state.selectedVigenciaKeys.clear();
            state.selectedAuthorKeys.clear();
            state.meta = null;
            renderAll();
            renderErrors([]);
            setStatus(error instanceof Error ? error.message : 'Erro desconhecido na consulta.');
        } finally {
            hideFilterOverlay();
            setLoading(false);
        }
    }

    function setLoading(isLoading) {
        state.loading = isLoading;

        [
            elements.btnBuscar,
            elements.btnAplicarFiltros,
            elements.btnLimparFiltros,
            elements.btnAplicarVigencias,
            elements.btnLimparVigencias,
            elements.btnSelecionarMeses,
            elements.btnLimparMeses,
            elements.btnSelecionarAutores,
            elements.btnLimparAutores,
        ].forEach((button) => {
            button.disabled = isLoading;
            button.style.opacity = isLoading ? '0.7' : '1';
        });

        elements.statusConsulta.classList.toggle('status-processing', isLoading);
        elements.btnBuscar.textContent = isLoading ? 'Consultando...' : 'Atualizar campanhas';
    }

    function setStatus(message) {
        elements.statusConsulta.textContent = message;
    }

    function applyFiltersAndRender() {
        const selectedFiliais = getSelectedFiliais();
        const filialSet = new Set(selectedFiliais);

        if (selectedFiliais.length === 0) {
            state.inputFilteredPromocoes = [];
            state.filteredPromocoes = [];
            state.selectedVigenciaKeys.clear();
            state.selectedAuthorKeys.clear();
            setStatus('Nenhuma filial selecionada nos filtros.');
            renderFilterNotFound([], []);
            renderMonthFilters([]);
            renderAuthorFilters([]);
            renderAll();
            return;
        }

        const termo = (elements.filtroTexto.value || '').trim().toLowerCase();
        const codigos = tokenize(elements.filtroCodigos.value);
        const bins = tokenize(elements.filtroBins.value);
        const operador = elements.operador.value === 'or' ? 'or' : 'and';
        const filialScopedPromocoes = state.allPromocoes.filter((promo) => filialSet.has(Number(promo.filial)));
        const availableMonthKeys = getAvailableMonthKeys(filialScopedPromocoes);
        state.selectedMonthKeys = new Set([...state.selectedMonthKeys].filter((key) => availableMonthKeys.includes(key)));
        renderMonthFilters(filialScopedPromocoes);
        const availableAuthorKeys = getAvailableAuthorKeys(filialScopedPromocoes);
        state.selectedAuthorKeys = new Set([...state.selectedAuthorKeys].filter((key) => availableAuthorKeys.includes(key)));
        renderAuthorFilters(filialScopedPromocoes);

        const availability = collectAvailability(filialScopedPromocoes);
        const missingCodigos = codigos.filter((codigo) => !availability.codigos.has(codigo));
        const missingBins = bins.filter((bin) => !availability.bins.has(bin));
        renderFilterNotFound(missingCodigos, missingBins);

        state.inputFilteredPromocoes = filialScopedPromocoes.filter((promo) => {
            const monthMatch = state.selectedMonthKeys.size === 0
                ? true
                : promoMatchesAnySelectedMonth(promo, state.selectedMonthKeys);
            const authorMatch = state.selectedAuthorKeys.size === 0
                ? true
                : state.selectedAuthorKeys.has(normalizeAuthorKey(promo.autor));
            const textMatch = termo === '' ? true : buildSearchBlob(promo).includes(termo);
            const codigoMatch = codigos.length === 0 ? true : promoHasAnyCodigo(promo, codigos);
            const binMatch = bins.length === 0 ? true : promoHasAnyBin(promo, bins);

            const checks = [];
            if (state.selectedMonthKeys.size > 0) {
                checks.push(monthMatch);
            }
            if (state.selectedAuthorKeys.size > 0) {
                checks.push(authorMatch);
            }
            if (termo !== '') {
                checks.push(textMatch);
            }
            if (codigos.length > 0) {
                checks.push(codigoMatch);
            }
            if (bins.length > 0) {
                checks.push(binMatch);
            }

            if (checks.length === 0) {
                return true;
            }

            return operador === 'or' ? checks.some(Boolean) : checks.every(Boolean);
        });

        pruneSelectedVigencias();
        if (state.selectedVigenciaKeys.size > 0) {
            state.filteredPromocoes = state.inputFilteredPromocoes.filter((promo) =>
                state.selectedVigenciaKeys.has(getPromoKey(promo))
            );
        } else {
            state.filteredPromocoes = state.inputFilteredPromocoes;
        }

        renderAll();
    }

    function buildSearchBlob(promo) {
        const items = Array.isArray(promo.itens) ? promo.itens : [];
        const formas = Array.isArray(promo.formasPagamento) ? promo.formasPagamento : [];
        const bines = Array.isArray(promo.bines) ? promo.bines : [];

        const itensText = items.map((item) => `${item.nombre || ''} ${item.codigoBarras || ''}`).join(' ');
        const formasText = formas
            .map((forma) => `${forma.descripcion || ''} ${(forma.bines || []).join(' ')}`)
            .join(' ');

        return [
            promo.titulo || '',
            promo.descripcion || '',
            promo.autor || '',
            promo.tipo || '',
            itensText,
            formasText,
            bines.join(' '),
            promo.vigenciaDesde || '',
            promo.vigenciaHasta || '',
            String(promo.limitePromocionesPorTicket ?? ''),
            String(promo.filial || ''),
        ]
            .join(' ')
            .toLowerCase();
    }

    function promoHasAnyCodigo(promo, tokens) {
        const itens = Array.isArray(promo.itens) ? promo.itens : [];
        const codigoSet = new Set(
            itens
                .map((item) => normalizeToken(item.codigoBarras))
                .filter((codigo) => codigo !== '')
        );
        return tokens.some((token) => codigoSet.has(token));
    }

    function promoHasAnyBin(promo, tokens) {
        const bins = Array.isArray(promo.bines) ? promo.bines : [];
        const binSet = new Set(
            bins
                .map((bin) => normalizeToken(bin))
                .filter((bin) => bin !== '')
        );
        return tokens.some((token) => binSet.has(token));
    }

    function tokenize(raw) {
        const parts = (raw || '').split(/[\s,;]+/g);
        return parts
            .map((value) => normalizeToken(value))
            .filter((value, index, self) => value !== '' && self.indexOf(value) === index);
    }

    function normalizeToken(value) {
        return String(value || '').trim();
    }

    function renderAll() {
        renderResumo();
        renderVigencias();
        renderTabela();
    }

    function renderResumo() {
        elements.resumoPromocoes.textContent = String(state.filteredPromocoes.length);

        const filiaisComSucesso = state.meta && Array.isArray(state.meta.filiaisComSucesso)
            ? state.meta.filiaisComSucesso.length
            : 0;
        elements.resumoFiliaisOk.textContent = String(filiaisComSucesso);
    }

    function renderVigencias() {
        if (state.inputFilteredPromocoes.length === 0) {
            elements.vigenciaSelecionadasInfo.textContent = 'Nenhuma campanha selecionada.';
            elements.vigenciaList.innerHTML = '<p class="text-sm text-slate-400">Nenhuma campanha para exibir.</p>';
            return;
        }

        updateSelectedVigenciasInfo();

        elements.vigenciaList.innerHTML = state.inputFilteredPromocoes
            .map((promo) => {
                const key = getPromoKey(promo);
                const isSelected = state.selectedVigenciaKeys.has(key) ? 'is-selected' : '';
                return `
                    <article class="vigencia-item ${isSelected}" data-key="${escapeHtml(key)}">
                        <h3>${escapeHtml(promo.titulo || 'Sem título')}</h3>
                        <p class="vigencia-filial">Filial: ${escapeHtml(String(promo.filial || '-'))}</p>
                        <p>Início: ${escapeHtml(formatDate(promo.vigenciaDesde))}</p>
                        <p>Fim: ${escapeHtml(formatDate(promo.vigenciaHasta))}</p>
                    </article>
                `;
            })
            .join('');
    }

    function updateVigenciaSelectionStyles() {
        const cards = elements.vigenciaList.querySelectorAll('.vigencia-item[data-key]');
        cards.forEach((card) => {
            const key = String(card.getAttribute('data-key') || '');
            card.classList.toggle('is-selected', state.selectedVigenciaKeys.has(key));
        });
    }

    function renderTabela() {
        if (state.filteredPromocoes.length === 0) {
            elements.promocoesBody.innerHTML = `
                <tr>
                    <td colspan="7" class="px-4 py-8 text-center text-sm text-slate-400">
                        Nenhuma promoção encontrada para os filtros aplicados.
                    </td>
                </tr>
            `;
            return;
        }

        elements.promocoesBody.innerHTML = state.filteredPromocoes
            .map((promo) => {
                const itens = Array.isArray(promo.itens) ? promo.itens : [];
                const formas = Array.isArray(promo.formasPagamento) ? promo.formasPagamento : [];

                const itensHtml = itens.length > 0
                    ? itens
                        .map((item) => `
                            <div class="mb-1 rounded-md border border-slate-700/70 bg-slate-900/70 p-1.5 text-[11px]">
                                <p class="font-semibold text-slate-100">${escapeHtml(item.nombre || 'Sem nome')}</p>
                                <p class="text-slate-300">${escapeHtml(item.codigoBarras || '-')}</p>
                            </div>
                        `)
                        .join('')
                    : '<span class="text-xs text-slate-400">Sem itens.</span>';

                const formasHtml = formas.length > 0
                    ? formas
                        .map((forma) => `
                            <div class="mb-1 rounded-md border border-cyan-500/20 bg-cyan-500/5 p-1.5 text-[11px]">
                                <p class="font-semibold text-cyan-100">${escapeHtml(forma.descripcion || 'Sem descrição')}</p>
                                <p class="text-slate-300">Tipo: ${escapeHtml(String(forma.codigoTipoPago ?? '-'))}</p>
                                <p class="text-slate-300 break-words">
                                    BINs: ${escapeHtml((Array.isArray(forma.bines) && forma.bines.length > 0) ? forma.bines.join(', ') : '-')}
                                </p>
                            </div>
                        `)
                        .join('')
                    : '<span class="text-xs text-slate-400">Sem forma de pagamento.</span>';

                const limite = promo.limitePromocionesPorTicket === null || promo.limitePromocionesPorTicket === undefined
                    ? '-'
                    : String(promo.limitePromocionesPorTicket);
                const autorLabel = String(promo.autor || '').trim() === '' ? 'Sem autor' : String(promo.autor).trim();
                const tipoLabel = mapTipoCampanha(promo.tipo);

                return `
                    <tr class="align-top">
                        <td class="px-2 py-2 text-sm font-semibold text-slate-100">${escapeHtml(String(promo.filial || '-'))}</td>
                        <td class="px-2 py-2 text-sm text-slate-100">
                            <div class="table-text-block table-title">${escapeHtml(promo.titulo || '-')}</div>
                            <div class="table-text-block table-subtitle">${escapeHtml(`${autorLabel} | ${tipoLabel}`)}</div>
                        </td>
                        <td class="px-2 py-2 text-sm text-slate-200">
                            <div class="table-text-block table-description">${escapeHtml(promo.descripcion || '-')}</div>
                        </td>
                        <td class="px-2 py-2"><div class="cell-scroll">${itensHtml}</div></td>
                        <td class="px-2 py-2"><div class="cell-scroll">${formasHtml}</div></td>
                        <td class="px-2 py-2 text-sm font-semibold text-amber-200">${escapeHtml(limite)}</td>
                        <td class="px-2 py-2 text-xs text-slate-200">
                            <p>Início: ${escapeHtml(formatDate(promo.vigenciaDesde))}</p>
                            <p>Fim: ${escapeHtml(formatDate(promo.vigenciaHasta))}</p>
                        </td>
                    </tr>
                `;
            })
            .join('');
    }

    function collectAvailability(promocoes) {
        const codigos = new Set();
        const bins = new Set();

        promocoes.forEach((promo) => {
            const itens = Array.isArray(promo.itens) ? promo.itens : [];
            const promoBins = Array.isArray(promo.bines) ? promo.bines : [];
            const formas = Array.isArray(promo.formasPagamento) ? promo.formasPagamento : [];

            itens.forEach((item) => {
                const codigo = normalizeToken(item.codigoBarras);
                if (codigo !== '') {
                    codigos.add(codigo);
                }
            });

            promoBins.forEach((bin) => {
                const binNormalized = normalizeToken(bin);
                if (binNormalized !== '') {
                    bins.add(binNormalized);
                }
            });

            formas.forEach((forma) => {
                const formaBins = Array.isArray(forma.bines) ? forma.bines : [];
                formaBins.forEach((bin) => {
                    const binNormalized = normalizeToken(bin);
                    if (binNormalized !== '') {
                        bins.add(binNormalized);
                    }
                });
            });
        });

        return { codigos, bins };
    }

    function getAvailableMonthKeys(promocoes) {
        const monthSet = new Set();
        promocoes.forEach((promo) => {
            promoMonthKeys(promo).forEach((key) => monthSet.add(key));
        });
        return [...monthSet].sort();
    }

    function promoMatchesAnySelectedMonth(promo, selectedKeys) {
        const monthKeys = promoMonthKeys(promo);
        return monthKeys.some((key) => selectedKeys.has(key));
    }

    function promoMonthKeys(promo) {
        const start = parsePromoDate(promo.vigenciaDesde);
        const end = parsePromoDate(promo.vigenciaHasta);
        if (!start || !end) {
            return [];
        }

        const startMonth = new Date(start.getFullYear(), start.getMonth(), 1);
        const endMonth = new Date(end.getFullYear(), end.getMonth(), 1);
        if (startMonth > endMonth) {
            return [];
        }

        const keys = [];
        const cursor = new Date(startMonth);
        while (cursor <= endMonth) {
            keys.push(toMonthKey(cursor));
            cursor.setMonth(cursor.getMonth() + 1);
        }
        return keys;
    }

    function parsePromoDate(rawValue) {
        const raw = String(rawValue || '').trim();
        if (raw === '') {
            return null;
        }
        const withTimezoneColon = raw.replace(/([+-]\d{2})(\d{2})$/, '$1:$2');
        const parsed = new Date(withTimezoneColon);
        if (Number.isNaN(parsed.getTime())) {
            return null;
        }
        return parsed;
    }

    function toMonthKey(dateObj) {
        const month = String(dateObj.getMonth() + 1).padStart(2, '0');
        return `${dateObj.getFullYear()}-${month}`;
    }

    function monthLabelFromKey(key) {
        const parts = key.split('-');
        if (parts.length !== 2) {
            return key;
        }
        const year = Number(parts[0]);
        const month = Number(parts[1]);
        const date = new Date(year, Math.max(month - 1, 0), 1);
        return date.toLocaleDateString('pt-BR', { month: 'short', year: 'numeric' });
    }

    function renderMonthFilters(promocoes) {
        const monthKeys = getAvailableMonthKeys(promocoes);
        if (monthKeys.length === 0) {
            elements.mesesVigenciaContainer.innerHTML = '<p class="text-xs text-slate-400">Nenhum período de vigência disponível.</p>';
            return;
        }

        elements.mesesVigenciaContainer.innerHTML = monthKeys
            .map((key) => {
                const isSelected = state.selectedMonthKeys.has(key) ? 'is-selected' : '';
                return `
                    <button type="button" class="month-chip ${isSelected}" data-month-key="${escapeHtml(key)}">
                        ${escapeHtml(monthLabelFromKey(key))}
                    </button>
                `;
            })
            .join('');
    }

    function normalizeAuthorKey(authorValue) {
        const raw = String(authorValue || '').trim();
        return raw === '' ? '__SEM_AUTOR__' : raw.toUpperCase();
    }

    function authorLabelFromKey(authorKey) {
        return authorKey === '__SEM_AUTOR__' ? 'Sem autor' : authorKey;
    }

    function getAvailableAuthorKeys(promocoes) {
        const authorSet = new Set();
        promocoes.forEach((promo) => {
            authorSet.add(normalizeAuthorKey(promo.autor));
        });
        return [...authorSet].sort();
    }

    function renderAuthorFilters(promocoes) {
        const authorKeys = getAvailableAuthorKeys(promocoes);
        if (authorKeys.length === 0) {
            elements.autorSelecionadosInfo.textContent = 'Nenhum autor selecionado.';
            elements.autoresContainer.innerHTML = '<p class="text-xs text-slate-400">Nenhum autor disponível.</p>';
            return;
        }

        elements.autorSelecionadosInfo.textContent = state.selectedAuthorKeys.size > 0
            ? `${state.selectedAuthorKeys.size} autor(es) selecionado(s).`
            : 'Nenhum autor selecionado.';

        elements.autoresContainer.innerHTML = authorKeys
            .map((authorKey) => {
                const isSelected = state.selectedAuthorKeys.has(authorKey) ? 'is-selected' : '';
                return `
                    <button type="button" class="author-chip ${isSelected}" data-author-key="${escapeHtml(authorKey)}">
                        ${escapeHtml(authorLabelFromKey(authorKey))}
                    </button>
                `;
            })
            .join('');
    }

    function renderFilterNotFound(missingCodigos, missingBins) {
        const hasCodigos = Array.isArray(missingCodigos) && missingCodigos.length > 0;
        const hasBins = Array.isArray(missingBins) && missingBins.length > 0;

        if (!hasCodigos && !hasBins) {
            elements.filterNotFoundAlert.classList.add('hidden');
            elements.filterNotFoundAlert.innerHTML = '';
            return;
        }

        const codigosHtml = hasCodigos
            ? `<p><strong>EANs não encontrados (${missingCodigos.length}):</strong> ${escapeHtml(missingCodigos.join(', '))}</p>`
            : '';

        const binsHtml = hasBins
            ? `<p><strong>BINs não encontrados (${missingBins.length}):</strong> ${escapeHtml(missingBins.join(', '))}</p>`
            : '';

        elements.filterNotFoundAlert.classList.remove('hidden');
        elements.filterNotFoundAlert.innerHTML = `
            <p class="mb-1 font-semibold">Alguns filtros não foram encontrados nas campanhas das filiais selecionadas:</p>
            <div class="not-found-list">
                ${codigosHtml}
                ${binsHtml}
            </div>
        `;
    }

    function mapTipoCampanha(tipoRaw) {
        const tipo = String(tipoRaw || '').trim().toUpperCase();
        if (tipo === 'DESCUENTO_VARIABLE') {
            return '% Desconto';
        }
        if (tipo === 'PRECIO_FIJO') {
            return 'Pre\u00e7o Fixo';
        }
        if (tipo === '') {
            return 'Tipo nao informado';
        }
        return tipo;
    }

    function renderErrors(errors) {
        if (!Array.isArray(errors) || errors.length === 0) {
            elements.apiErrors.classList.add('hidden');
            elements.apiErrors.innerHTML = '';
            return;
        }

        const errorHtml = errors
            .map((error) => `
                <li>Filial ${escapeHtml(String(error.filial || '-'))}: HTTP ${escapeHtml(String(error.status || 0))} - ${escapeHtml(String(error.mensagem || 'Erro desconhecido'))}</li>
            `)
            .join('');

        elements.apiErrors.classList.remove('hidden');
        elements.apiErrors.innerHTML = `
            <p class="mb-1 font-semibold">Algumas filiais apresentaram erro na consulta:</p>
            <ul class="list-disc space-y-1 pl-5">${errorHtml}</ul>
        `;
    }

    function pruneSelectedVigencias() {
        if (state.selectedVigenciaKeys.size === 0) {
            return;
        }

        const validKeys = new Set(state.inputFilteredPromocoes.map(getPromoKey));
        for (const key of state.selectedVigenciaKeys) {
            if (!validKeys.has(key)) {
                state.selectedVigenciaKeys.delete(key);
            }
        }
    }

    function getPromoKey(promo) {
        return [
            String(promo.filial || ''),
            String(promo.id || ''),
            String(promo.vigenciaDesde || ''),
            String(promo.vigenciaHasta || ''),
        ].join('|');
    }

    function formatDate(value) {
        const raw = String(value || '').trim();
        if (raw === '') {
            return '-';
        }

        const withTimezoneColon = raw.replace(/([+-]\d{2})(\d{2})$/, '$1:$2');
        const date = new Date(withTimezoneColon);
        if (Number.isNaN(date.getTime())) {
            return raw;
        }

        return date.toLocaleString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    }

    function escapeHtml(value) {
        return String(value)
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#39;');
    }
})();
