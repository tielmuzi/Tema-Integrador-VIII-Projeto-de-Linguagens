const root = document.querySelector('#dashboardRoot');
const navItems = [...document.querySelectorAll('[data-view]')];
const pageInfo = {
  dashboard: ['VISÃO GERAL', 'ODS 10: inclusão social e redução de barreiras comunicacionais.'],
  pesquisa: ['PESQUISA COMUNITÁRIA', 'Indicadores calculados a partir das respostas reais do formulário.'],
  monitoramento: ['MONITORAMENTO', 'Pontos e medições demonstrativas, identificados como simulados.'],
  risco: ['CLASSIFICAÇÃO DE RISCO', 'Ajuste os limiares e teste diferentes níveis de água e chuva.'],
  compilador: ['COMPILADOR DSL', 'Scanner, parser, análise sintática e interpretação em Python.'],
  relatorios: ['RELATÓRIOS', 'Resumo exportável com separação entre pesquisa real e telemetria simulada.'],
};
const state = { view: 'dashboard', dashboard: null, examples: [], selectedExample: '', source: '', result: null, tab: 'saida', riskPreview: null };

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' })[char]);
}

function number(value) {
  return new Intl.NumberFormat('pt-BR').format(Number(value || 0));
}

function dateTime(value) {
  if (!value) return 'Sem registro';
  return new Date(value).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `Falha HTTP ${response.status}`);
  return data;
}

async function refreshData() {
  state.dashboard = await api('/api/dashboard');
}

function notify(message, isError = false) {
  const toast = root.querySelector('#toast');
  toast.textContent = message;
  toast.className = `toast visible ${isError ? 'error' : ''}`;
  window.clearTimeout(notify.timeout);
  notify.timeout = window.setTimeout(() => { toast.className = 'toast'; }, 3200);
}

function metrics(items) {
  return `<div class="metric-grid">${items.map((item) => `<article class="metric-card"><div class="metric-icon ${esc(item.tone || '')}">${esc(item.icon)}</div><div class="metric-value">${esc(item.value)}</div><div class="metric-label">${esc(item.label)}</div><span class="data-badge ${item.real ? 'real' : 'simulated'}">${item.real ? '◉ dado real' : '◉ simulado'}</span></article>`).join('')}</div>`;
}

function barRows(items, total, labelKey = 'label', valueKey = 'count') {
  if (!items?.length) return '<p class="empty-state">Sem dados disponíveis.</p>';
  const max = Math.max(1, ...items.map((item) => Number(item[valueKey] || 0)));
  return `<div class="rank-list">${items.map((item) => {
    const amount = Number(item[valueKey] || 0);
    return `<div class="rank-item"><div class="rank-caption"><span>${esc(item[labelKey])}</span><strong>${number(amount)}${total ? ` <small>/ ${number(total)}</small>` : ''}</strong></div><div class="rank-track"><i style="width:${Math.max(amount ? 4 : 0, amount / max * 100)}%"></i></div></div>`;
  }).join('')}</div>`;
}

function panel(title, content, badge = '') {
  return `<section class="data-panel"><div class="panel-heading"><h2>${esc(title)}</h2>${badge ? `<span class="data-badge ${badge === 'REAL' ? 'real' : 'simulated'}">◉ ${esc(badge)}</span>` : ''}</div>${content}</section>`;
}

function dashboardView() {
  const { research, monitoring } = state.dashboard;
  const latest = monitoring.measurements.slice(0, 12).reverse();
  const chartMaximum = Math.max(1, ...latest.map((item) => Math.max(item.water_cm, item.rain_mm)));
  const trend = latest.length ? `<div class="trend-chart">${latest.map((item) => `<div class="trend-column"><div class="trend-bars"><i class="water-bar" style="height:${Math.max(3, item.water_cm / chartMaximum * 100)}%" title="Nível: ${item.water_cm} cm"></i><i class="rain-bar" style="height:${Math.max(3, item.rain_mm / chartMaximum * 100)}%" title="Chuva: ${item.rain_mm} mm"></i></div><small>${esc(item.point_id)}</small></div>`).join('')}</div><div class="chart-legend"><span><i class="water-key"></i>Nível da água (cm)</span><span><i class="rain-key"></i>Chuva (mm)</span></div>` : '<p class="empty-state">Registre medições para iniciar o histórico.</p>';
  const alerts = monitoring.alerts.slice(0, 6).map((alert) => `<div class="feed-row"><div><strong>${esc(alert.point_name)}</strong><small>${esc(dateTime(alert.created_at))}</small></div><span class="risk-tag ${esc(alert.risk.toLowerCase())}">${esc(alert.risk)}</span></div>`).join('') || '<p class="empty-state">Nenhum alerta simulado.</p>';
  const programs = monitoring.programs.slice(0, 5).map((item) => `<div class="feed-row"><div><strong>${item.accepted ? 'Programa aceito' : 'Programa com erro'}</strong><small>${esc(dateTime(item.executed_at))}</small></div><span class="run-dot ${item.accepted ? 'ok' : 'fail'}"></span></div>`).join('') || '<p class="empty-state">Execute um programa no compilador para criar o histórico.</p>';
  return `${metrics([
    { icon: '▤', value: number(research.total_respostas), label: 'respostas da pesquisa', real: true, tone: 'cyan' },
    { icon: '⌖', value: number(monitoring.counts.points), label: 'pontos monitorados', tone: 'blue' },
    { icon: '⌁', value: number(monitoring.counts.measurements), label: 'medições', tone: 'teal' },
    { icon: '△', value: number(monitoring.counts.alerts), label: 'alertas emitidos', tone: 'orange' },
    { icon: '</>', value: number(monitoring.counts.programs), label: 'execuções da DSL', tone: 'violet' },
  ])}<div class="dashboard-grid">${panel('ODS 10 · Inclusão e igualdade de oportunidades', '<p>O projeto busca promover a inclusão de pessoas em situação de vulnerabilidade (meta 10.2) e reduzir desigualdades de resultados, incluindo barreiras comunicacionais (meta 10.3).</p><p class="panel-note">Co-alinhamento ao ODS 4: práticas pedagógicas inclusivas e acessíveis (metas 4.5 e 4.a), com tecnologia assistiva. O monitoramento e os alertas desta versão são demonstrativos.</p>', 'PROPÓSITO')}${panel('Nível da água e precipitação', `${trend}<p class="panel-note">Histórico inteiramente simulado para demonstração.</p>`, 'SIMULADO')}${panel('Problemas mais citados', barRows(research.impactos.slice(0, 5), research.total_respostas), 'REAL')}${panel('Alertas recentes', alerts, 'SIMULADO')}${panel('Programas executados', programs, 'SIMULADO')}</div>`;
}

function researchView() {
  const data = state.dashboard.research;
  const highRisk = data.risco.distribuicao.find((item) => item.label === 'alto')?.count || 0;
  const adopted = data.adocao_sistema.find((item) => item.label === 'sim')?.count || 0;
  const sensorSupport = data.sensores.reduce((sum, item) => sum + item.count, 0);
  const regions = data.perfis.map((profile) => ({ label: profile.regiao, count: profile.risco }));
  return `${metrics([
    { icon: '▤', value: number(data.total_respostas), label: 'respostas analisadas', real: true, tone: 'cyan' },
    { icon: '△', value: `${data.risco.alto_percentual}%`, label: `${number(highRisk)} em risco alto estimado`, real: true, tone: 'orange' },
    { icon: '✓', value: `${adopted}/${data.total_respostas}`, label: 'usariam o sistema', real: true, tone: 'teal' },
    { icon: '⌁', value: `${sensorSupport}/${data.total_respostas}`, label: 'apoiam sensores', real: true, tone: 'blue' },
  ])}<div class="dashboard-grid research-grid">${panel('Problemas mais citados', barRows(data.impactos, data.total_respostas), 'REAL')}${panel('Canais de alerta preferidos', barRows(data.canais, data.total_respostas), 'REAL')}${panel('Informações desejadas nos alertas', barRows(data.informacoes_alerta, data.total_respostas), 'REAL')}${panel('Risco estimado por resposta', `<div class="profile-list">${data.perfis.map((profile) => `<div class="profile-row"><div><strong>${esc(profile.regiao)}</strong><small>${esc(profile.frequencia)}</small></div><span class="risk-tag ${esc(profile.faixa)}">${number(profile.risco)} · ${esc(profile.faixa)}</span></div>`).join('')}</div><p class="panel-note">Estimativa calculada a partir da suscetibilidade, frequência e impactos relatados.</p>`, 'REAL')}</div>`;
}

function monitoringView() {
  const data = state.dashboard.monitoring;
  const spots = [[24, 35], [68, 62], [44, 72], [80, 30], [35, 22], [56, 45]];
  const markers = data.points.map((point, index) => {
    const [left, top] = spots[index % spots.length];
    const risk = point.latest?.risk || 'SEM DADO';
    return `<button class="map-marker ${esc(risk.toLowerCase().replace(' ', '-'))}" style="left:${left}%;top:${top}%" type="button" title="${esc(point.name)} · ${esc(risk)}" data-action="focus-point" data-id="${esc(point.id)}"><span>⌖</span><small>${esc(point.id)}</small></button>`;
  }).join('');
  const points = data.points.map((point) => `<article class="point-card" id="point-${esc(point.id)}"><div class="point-title"><div class="point-pin">⌖</div><div><small>${esc(point.id)} · SIMULADO</small><h3>${esc(point.name)}</h3></div><button class="icon-button danger" type="button" data-action="delete-point" data-id="${esc(point.id)}" title="Excluir ponto" aria-label="Excluir ${esc(point.name)}">×</button></div><p>Bairro: ${esc(point.neighborhood)}<br>Canal: ${esc(point.channel)}</p><div class="point-reading">${point.latest ? `<span>${number(point.latest.water_cm)} cm</span><span>${number(point.latest.rain_mm)} mm</span><span class="risk-tag ${esc(point.latest.risk.toLowerCase())}">${esc(point.latest.risk)}</span>` : '<span>Sem medições</span>'}</div><button class="text-button" type="button" data-action="simulate-point" data-id="${esc(point.id)}">Simular enchente →</button></article>`).join('') || '<p class="empty-state">Cadastre um ponto para começar.</p>';
  const rows = data.measurements.slice(0, 12).map((item) => {
    const point = data.points.find((candidate) => candidate.id === item.point_id);
    return `<tr><td>${esc(item.point_id)}</td><td>${esc(point?.name || 'Ponto removido')}</td><td>${number(item.rain_mm)} mm</td><td>${number(item.water_cm)} cm</td><td><span class="risk-tag ${esc(item.risk.toLowerCase())}">${esc(item.risk)}</span></td><td>${esc(dateTime(item.measured_at))}</td></tr>`;
  }).join('') || '<tr><td colspan="6" class="empty-state">Nenhuma medição.</td></tr>';
  return `<div class="action-row"><button class="secondary-button" type="button" data-action="new-point">＋ Novo ponto</button><button class="primary-button" type="button" data-action="new-measurement">⌁ Nova medição</button></div><div class="monitor-grid">${panel('Mapa esquemático de pontos', `<div class="map-canvas"><svg class="river-path" viewBox="0 0 1000 360" preserveAspectRatio="none" aria-hidden="true"><path d="M-20 170 C180 65 310 285 510 165 S790 75 1030 220"/></svg><div class="map-grid"></div>${markers}<span class="map-caption">MAPA ESQUEMÁTICO · POSIÇÕES DEMONSTRATIVAS</span></div>`, 'SIMULADO')}<div class="point-list">${points}</div></div>${panel('Histórico de medições', `<div class="table-scroll"><table><thead><tr><th>Ponto</th><th>Local</th><th>Chuva</th><th>Nível</th><th>Risco</th><th>Data</th></tr></thead><tbody>${rows}</tbody></table></div>`, 'SIMULADO')}`;
}

function classify(water, rain, rules = state.dashboard.monitoring.rules) {
  for (const level of ['CRÍTICO', 'ALERTA', 'ATENÇÃO']) {
    const rule = rules.find((item) => item.level === level);
    if (rule && (water >= rule.water_min || rain >= rule.rain_min)) return level;
  }
  return 'NORMAL';
}

function rulesFromForm() {
  const fields = [...root.querySelectorAll('[data-rule]')];
  if (!fields.length) return state.dashboard.monitoring.rules;
  return fields.reduce((rules, field) => {
    let rule = rules.find((item) => item.level === field.dataset.rule);
    if (!rule) { rule = { level: field.dataset.rule }; rules.push(rule); }
    rule[field.dataset.field] = Number(field.value);
    return rules;
  }, []);
}

function riskView() {
  const rules = state.dashboard.monitoring.rules;
  const water = state.riskPreview?.water ?? 60;
  const rain = state.riskPreview?.rain ?? 30;
  const risk = classify(water, rain, rulesFromForm());
  const ruleCards = rules.map((rule) => `<article class="rule-card ${esc(rule.level.toLowerCase())}"><div class="rule-heading"><span class="risk-tag ${esc(rule.level.toLowerCase())}">${esc(rule.level)}</span><span class="data-badge simulated">limiar</span></div><label>Nível mínimo (cm)<input type="number" min="0" max="1000" step="1" value="${esc(rule.water_min)}" data-rule="${esc(rule.level)}" data-field="water_min"></label><label>Chuva mínima (mm)<input type="number" min="0" max="1000" step="1" value="${esc(rule.rain_min)}" data-rule="${esc(rule.level)}" data-field="rain_min"></label></article>`).join('');
  return `<section class="data-panel risk-simulator"><div class="panel-heading"><div><h2>Simulador de risco</h2><p>Teste as regras sem gravar uma medição.</p></div><span class="data-badge simulated">◉ SIMULADO</span></div><div class="simulator-layout"><div class="range-controls"><label>Nível da água <output id="waterOutput">${number(water)} cm</output><input id="waterRange" type="range" min="0" max="200" value="${water}"></label><label>Precipitação <output id="rainOutput">${number(rain)} mm</output><input id="rainRange" type="range" min="0" max="120" value="${rain}"></label></div><div class="risk-result ${esc(risk.toLowerCase())}"><span class="risk-symbol">${risk === 'NORMAL' ? '✓' : risk === 'ATENÇÃO' ? '△' : '!'}</span><span class="risk-tag ${esc(risk.toLowerCase())}">${esc(risk)}</span><small>resultado da classificação</small></div></div></section><div class="rule-grid">${ruleCards}</div><div class="action-row"><span class="panel-note">O maior nível alcançado por água OU chuva prevalece.</span><button class="primary-button" type="button" data-action="save-rules">Salvar regras</button></div>`;
}

function compilerView() {
  const examples = state.examples.map((example) => `<option value="${esc(example.id)}" ${state.selectedExample === example.id ? 'selected' : ''}>${esc(example.name)}</option>`).join('');
  const result = state.result;
  let output = '<p class="console-muted">Clique em Validar ou Executar para analisar o programa.</p>';
  if (result) {
    if (state.tab === 'tokens') output = `<pre>${esc(JSON.stringify(result.tokens, null, 2))}</pre>`;
    else if (state.tab === 'ast') output = `<pre>${esc(JSON.stringify(result.ast, null, 2))}</pre>`;
    else if (state.tab === 'erros') {
      const errors = [...(result.lexical_errors || []), ...(result.syntax_errors || [])];
      output = errors.length ? errors.map((error) => `<div class="compiler-error"><strong>${esc(error.message)}</strong><small>L${error.line}:C${error.column}</small>${error.context ? `<pre>${esc(error.context)}</pre>` : ''}</div>`).join('') : '<p class="console-muted">Nenhum erro encontrado.</p>';
    } else output = result.accepted ? (result.output.length ? result.output.map((line) => `<div class="console-output-line">${esc(line)}</div>`).join('') : '<p class="console-muted">Programa válido, sem saídas.</p>') : `<p class="console-error">${esc(result.message)}</p>`;
  }
  return `<div class="compiler-toolbar"><label class="select-wrap"><span class="sr-only">Carregar exemplo</span><select id="exampleSelect"><option value="">Carregar exemplo…</option>${examples}</select></label><div class="action-row"><button class="secondary-button" type="button" data-action="clear-editor" title="Limpar editor">⌫ Limpar</button><button class="secondary-button" type="button" data-action="validate-program">◎ Validar</button><button class="primary-button" type="button" data-action="run-program">▶ Executar</button></div></div><div class="compiler-layout"><section class="data-panel editor-surface"><div class="panel-heading"><div><span class="panel-kicker">EDITOR .MIN</span><span id="compilerStatus" class="compiler-status">${result ? result.accepted ? 'Programa aceito' : 'Revise o programa' : 'Aguardando análise'}</span></div><button class="icon-button" type="button" data-action="format-source" title="Formatar linhas">↵</button></div><textarea id="programEditor" spellcheck="false" aria-label="Editor da DSL Escudo d'Água">${esc(state.source)}</textarea><div class="editor-foot"><span id="cursorStatus">UTF-8 · DSL v1</span><span>${number(state.source.split('\n').length)} linhas</span></div></section><section class="data-panel compiler-output"><div class="tab-bar">${[['saida', 'Saída'], ['tokens', 'Tokens'], ['ast', 'AST'], ['erros', 'Erros']].map(([key, label]) => `<button type="button" class="tab-button ${state.tab === key ? 'active' : ''}" data-action="compiler-tab" data-tab="${key}">${label}</button>`).join('')}</div><div class="compiler-result" id="compilerResult">${output}</div></section></div>`;
}

function reportsView() {
  const { research, monitoring } = state.dashboard;
  const alerts = monitoring.alerts.map((alert) => `<tr><td>${esc(alert.point_name)}</td><td>${esc(alert.risk)}</td><td>${esc(alert.message)}</td><td>${esc(dateTime(alert.created_at))}</td><td>SIMULADO</td></tr>`).join('') || '<tr><td colspan="5" class="empty-state">Sem alertas simulados.</td></tr>';
  const programs = monitoring.programs.map((program) => `<div class="report-program"><div><strong>${program.accepted ? 'Programa aceito' : 'Execução com erros'}</strong><small>${esc(dateTime(program.executed_at))}</small></div><pre>${esc(program.source)}</pre></div>`).join('') || '<p class="empty-state">Nenhum programa executado ainda.</p>';
  return `<div class="action-row report-actions"><div><span class="data-badge real">◉ Pesquisa REAL</span><span class="data-badge simulated">◉ Monitoramento SIMULADO</span></div><div><button class="secondary-button" type="button" data-action="export-csv">▤ Exportar CSV</button><button class="primary-button" type="button" data-action="export-pdf">↓ Exportar PDF</button></div></div>${metrics([
    { icon: '▤', value: number(research.total_respostas), label: 'respostas', real: true, tone: 'cyan' },
    { icon: '⌖', value: number(monitoring.counts.points), label: 'pontos', tone: 'blue' },
    { icon: '⌁', value: number(monitoring.counts.measurements), label: 'medições', tone: 'teal' },
    { icon: '△', value: number(monitoring.counts.alerts), label: 'alertas', tone: 'orange' },
    { icon: '</>', value: number(monitoring.counts.programs), label: 'programas executados', tone: 'violet' },
  ])}<div class="dashboard-grid report-page">${panel('Principais problemas da pesquisa', barRows(research.impactos, research.total_respostas), 'REAL')}${panel('Histórico de alertas', `<div class="table-scroll"><table><thead><tr><th>Ponto</th><th>Risco</th><th>Mensagem</th><th>Data</th><th>Origem</th></tr></thead><tbody>${alerts}</tbody></table></div>`, 'SIMULADO')}${panel('Programas executados', programs, 'SIMULADO')}</div>`;
}

function renderContent() {
  const content = root.querySelector('#viewContent');
  if (!state.dashboard) {
    content.innerHTML = '<section class="data-panel"><p class="empty-state">Carregando dados locais…</p></section>';
    return;
  }
  const views = { dashboard: dashboardView, pesquisa: researchView, monitoramento: monitoringView, risco: riskView, compilador: compilerView, relatorios: reportsView };
  content.innerHTML = `<div class="view-content view-${state.view}">${views[state.view]()}</div>`;
  if (state.view === 'risco') updateRiskPreview();
}

function renderShell() {
  const [title, description] = pageInfo[state.view];
  root.innerHTML = `<header class="workspace-header"><div><span class="eyebrow">ESCUDO D'ÁGUA / MONITORAMENTO</span><h1>${title}</h1><p>${description}</p></div><div class="header-status"><span class="status-dot"></span> SERVIDOR LOCAL <small>v1.0</small></div></header><main id="viewContent" aria-live="polite"></main><dialog id="actionDialog" class="action-dialog"></dialog><div id="toast" class="toast" role="status"></div>`;
  renderContent();
}

function setView(view) {
  if (!pageInfo[view]) return;
  state.view = view;
  navItems.forEach((item) => item.classList.toggle('active', item.dataset.view === view));
  renderShell();
}

function updateRiskPreview() {
  const waterInput = root.querySelector('#waterRange');
  const rainInput = root.querySelector('#rainRange');
  if (!waterInput || !rainInput) return;
  const water = Number(waterInput.value);
  const rain = Number(rainInput.value);
  const risk = classify(water, rain, rulesFromForm());
  root.querySelector('#waterOutput').textContent = `${number(water)} cm`;
  root.querySelector('#rainOutput').textContent = `${number(rain)} mm`;
  const result = root.querySelector('.risk-result');
  result.className = `risk-result ${risk.toLowerCase()}`;
  result.querySelector('.risk-tag').className = `risk-tag ${risk.toLowerCase()}`;
  result.querySelector('.risk-tag').textContent = risk;
  result.querySelector('.risk-symbol').textContent = risk === 'NORMAL' ? '✓' : risk === 'ATENÇÃO' ? '△' : '!';
}

function openDialog(title, formHtml) {
  const dialog = root.querySelector('#actionDialog');
  dialog.innerHTML = `<div class="dialog-heading"><h2>${esc(title)}</h2><button class="icon-button" type="button" data-action="close-dialog" aria-label="Fechar">×</button></div>${formHtml}`;
  dialog.showModal();
}

function pointForm() {
  openDialog('Novo ponto de monitoramento', `<form data-form="point"><label>Nome do ponto<input name="name" maxlength="120" required placeholder="Ex.: Centro"></label><label>Bairro ou região<input name="neighborhood" maxlength="120" required placeholder="Ex.: Centro"></label><label>Canal ou referência<input name="channel" maxlength="120" required placeholder="Ex.: Córrego Central"></label><div class="dialog-actions"><button class="secondary-button" type="button" data-action="close-dialog">Cancelar</button><button class="primary-button" type="submit">Cadastrar ponto</button></div></form>`);
}

function measurementForm() {
  const points = state.dashboard.monitoring.points;
  if (!points.length) return notify('Cadastre um ponto antes de registrar uma medição.', true);
  openDialog('Nova medição simulada', `<form data-form="measurement"><label>Ponto<select name="point_id">${points.map((point) => `<option value="${esc(point.id)}">${esc(point.id)} · ${esc(point.name)}</option>`).join('')}</select></label><label>Nível da água (cm)<input name="water_cm" type="number" min="0" max="1000" required value="45"></label><label>Precipitação (mm)<input name="rain_mm" type="number" min="0" max="1000" required value="20"></label><div class="dialog-actions"><button class="secondary-button" type="button" data-action="close-dialog">Cancelar</button><button class="primary-button" type="submit">Registrar medição</button></div><p class="panel-note">A medição será identificada como simulada.</p></form>`);
}

async function compile(execute) {
  const editor = root.querySelector('#programEditor');
  if (!editor) return;
  state.source = editor.value;
  try {
    state.result = await api('/api/compile', { method: 'POST', body: JSON.stringify({ source: state.source, execute }) });
    state.tab = state.result.accepted ? 'saida' : 'erros';
    await refreshData();
    renderShell();
    notify(execute ? 'Programa enviado ao interpretador.' : 'Programa validado sem execução.');
  } catch (error) {
    notify(error.message, true);
  }
}

function exportCsv() {
  const monitoring = state.dashboard.monitoring;
  const research = state.dashboard.research;
  const rows = [['tipo', 'ponto', 'local', 'chuva_mm', 'nivel_cm', 'risco', 'data', 'origem']];
  rows.push(['pesquisa', '', `${research.total_respostas} respostas`, '', '', `${research.risco.alto_percentual}% risco alto`, '', 'real']);
  for (const item of research.impactos) rows.push(['problema', '', item.label, item.count, '', '', '', 'real']);
  for (const item of monitoring.measurements) {
    const point = monitoring.points.find((candidate) => candidate.id === item.point_id);
    rows.push(['medicao', item.point_id, point?.name || '', item.rain_mm, item.water_cm, item.risk, item.measured_at, 'simulado']);
  }
  for (const item of monitoring.alerts) rows.push(['alerta', item.point_id, item.point_name, '', '', item.risk, item.created_at, 'simulado']);
  const csv = `\uFEFF${rows.map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(';')).join('\r\n')}`;
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = 'escudo-dagua-relatorio.csv';
  link.click();
  URL.revokeObjectURL(url);
  notify('CSV exportado.');
}

async function handleClick(event) {
  const nav = event.target.closest('[data-view]');
  if (nav) return setView(nav.dataset.view);
  const button = event.target.closest('[data-action]');
  if (!button) return;
  const action = button.dataset.action;
  try {
    if (action === 'new-point') return pointForm();
    if (action === 'new-measurement') return measurementForm();
    if (action === 'close-dialog') return root.querySelector('#actionDialog').close();
    if (action === 'validate-program') return compile(false);
    if (action === 'run-program') return compile(true);
    if (action === 'clear-editor') {
      state.selectedExample = '';
      state.source = '';
      state.result = null;
      return renderShell();
    }
    if (action === 'format-source') {
      const editor = root.querySelector('#programEditor');
      state.source = editor.value.split('\n').map((line) => line.trim()).filter(Boolean).join('\n') + '\n';
      return renderShell();
    }
    if (action === 'compiler-tab') {
      state.source = root.querySelector('#programEditor')?.value ?? state.source;
      state.tab = button.dataset.tab;
      return renderContent();
    }
    if (action === 'save-rules') {
      const rules = [...root.querySelectorAll('[data-rule]')].reduce((items, input) => {
        let rule = items.find((item) => item.level === input.dataset.rule);
        if (!rule) { rule = { level: input.dataset.rule }; items.push(rule); }
        rule[input.dataset.field] = Number(input.value);
        return items;
      }, []);
      await api('/api/rules', { method: 'POST', body: JSON.stringify({ rules }) });
      await refreshData(); renderContent(); notify('Regras de risco salvas.'); return;
    }
    if (action === 'delete-point') {
      if (!window.confirm(`Excluir o ponto ${button.dataset.id} e seu histórico?`)) return;
      await api(`/api/points/${encodeURIComponent(button.dataset.id)}`, { method: 'DELETE' });
      await refreshData(); renderContent(); notify('Ponto e histórico removidos.'); return;
    }
    if (action === 'simulate-point') {
      await api('/api/simulate', { method: 'POST', body: JSON.stringify({ point_id: button.dataset.id }) });
      await refreshData(); renderContent(); notify('Simulação de enchente registrada.'); return;
    }
    if (action === 'focus-point') {
      root.querySelector(`#point-${CSS.escape(button.dataset.id)}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }); return;
    }
    if (action === 'export-csv') return exportCsv();
    if (action === 'export-pdf') {
      document.body.classList.add('printing-report');
      window.print();
      window.setTimeout(() => document.body.classList.remove('printing-report'), 500);
      return;
    }
  } catch (error) {
    notify(error.message, true);
  }
}

async function handleSubmit(event) {
  const form = event.target.closest('form[data-form]');
  if (!form) return;
  event.preventDefault();
  const data = Object.fromEntries(new FormData(form));
  try {
    if (form.dataset.form === 'point') await api('/api/points', { method: 'POST', body: JSON.stringify(data) });
    else await api('/api/measurements', { method: 'POST', body: JSON.stringify(data) });
    root.querySelector('#actionDialog').close();
    await refreshData();
    renderContent();
    notify(form.dataset.form === 'point' ? 'Ponto cadastrado.' : 'Medição registrada.');
  } catch (error) {
    notify(error.message, true);
  }
}

root.addEventListener('click', handleClick);
root.addEventListener('submit', handleSubmit);
root.addEventListener('input', (event) => {
  if (event.target.matches('#programEditor')) {
    state.source = event.target.value;
    const lineCount = event.target.value.split('\n').length;
    root.querySelector('.editor-foot span:last-child').textContent = `${number(lineCount)} linhas`;
  }
  if (event.target.matches('#waterRange, #rainRange, [data-rule]')) updateRiskPreview();
});
root.addEventListener('change', async (event) => {
  if (event.target.matches('#exampleSelect') && event.target.value) {
    const example = state.examples.find((item) => item.id === event.target.value);
    if (example) { state.selectedExample = example.id; state.source = example.source; state.result = null; renderContent(); }
  }
});
navItems.forEach((item) => item.addEventListener('click', () => setView(item.dataset.view)));

async function init() {
  root.innerHTML = '<main class="loading-state">Carregando Escudo d\'Água…</main>';
  try {
    [state.dashboard, state.examples] = await Promise.all([api('/api/dashboard'), api('/api/examples')]);
    state.source = `INICIO\nAREA Centro (SENSOR, NIVEL);\nNIVEL Centro = 85;\nMONITORE Centro;\nALARME;\nFIM`;
    renderShell();
  } catch (error) {
    root.innerHTML = `<section class="data-panel load-error"><h1>Falha ao carregar os dados</h1><p>${esc(error.message)}</p><p>Inicie o servidor local para usar os módulos da aplicação.</p></section>`;
  }
}

init();
