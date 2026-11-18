const $ = id => document.getElementById(id);
const config = window.MATH_ASSISTANT_CONFIG || {};
const api = path => `${(config.apiBase || '').replace(/\/$/, '')}${path}`;
const names = {inspect: '01 · Environment inspection', ingest: '02 · Dataset ingestion', eda: '03 · Exploratory analysis', clean: '04 · Spark cleaning', split: '05 · Deterministic split', benchmark: '06 · CPU resource benchmark', train: '07 · LoRA training', evaluate_base: '08 · Base model evaluation', evaluate_adapter: '09 · Adapter evaluation', acceptance: '10 · Generation acceptance', register: '11 · Model registration'};
let fetching = false;
function text(id, value) { $(id).textContent = value; }
function duration(seconds) { return typeof seconds !== 'number' ? '—' : seconds >= 60 ? `${(seconds / 60).toFixed(1)} min` : `${seconds.toFixed(2)} s`; }
async function refresh() {
  if (fetching) return;
  fetching = true;
  $('refresh').disabled = true;
  try {
    const responses = await Promise.all([fetch(api('/v1/pipeline/status')), fetch(api('/v1/pipeline/logs'))]);
    if (responses.some(response => !response.ok)) throw new Error('Pipeline service is unavailable.');
    const [data, log] = await Promise.all(responses.map(response => response.json()));
    const generation = data.candidates?.qwen_cpu_v2?.generation_acceptance;
    text('records', data.quality?.output_count?.toLocaleString() ?? '—');
    text('splits', data.splits ? Object.entries(data.splits).map(([name, value]) => `${value.count} ${name}`).join(' · ') : 'Awaiting split report');
    text('throughput', data.quality?.records_per_second?.toFixed(1) ?? '—');
    text('accuracy', generation ? `${Math.round(generation.accuracy * 100)}%` : '—');
    text('acceptance', generation ? `${generation.cases.filter(c => c.passed).length} / ${generation.cases.length} passed · ${generation.status.replaceAll('_', ' ')}` : 'Awaiting generation results');
    text('train-time', duration(data.training?.metrics?.train_runtime));
    text('parameters', data.training ? `${data.training.trainable_parameters.toLocaleString()} trainable parameters` : 'CPU LoRA adapter');
    text('loss', data.evaluation?.mean_completion_loss?.toFixed(4) ?? '—');
    text('registry', data.registration ? `Version ${data.registration.version} · ${data.registration.validation_status.replaceAll('_', ' ')}` : 'Awaiting registration');
    text('commit', data.pipeline?.git_commit ? `${data.pipeline.git_commit.slice(0, 12)}${data.pipeline.git_dirty ? ' + saved working tree' : ''}` : '—');
    text('pipeline-result', data.pipeline ? `${data.pipeline.status} · ${duration(data.pipeline.seconds ?? (data.pipeline.status === 'running' ? Date.now() / 1000 - data.pipeline.started_at : undefined))}` : 'No orchestration run yet');
    const state = data.pipeline?.status || 'pending';
    $('console-status').className = `status ${state === 'failed' ? 'problem' : 'ready'}`;
    $('console-status').replaceChildren(document.createElement('i'), document.createTextNode(data.evidence_source === 'submitted' ? 'Saved pipeline evidence' : state === 'running' ? 'Pipeline running' : state === 'completed' ? 'Pipeline complete' : state === 'failed' ? 'Pipeline needs attention' : 'Evidence available'));
    $('stage-table').replaceChildren();
    for (const stage of data.stages || []) {
      const row = document.createElement('tr');
      const label = document.createElement('td'); label.textContent = names[stage.name] || stage.name;
      const stateCell = document.createElement('td'); const badge = document.createElement('span'); badge.className = `badge ${stage.status}`; badge.textContent = stage.status; stateCell.append(badge);
      const seconds = document.createElement('td'); seconds.textContent = duration(stage.seconds ?? (stage.status === 'running' ? Date.now() / 1000 - stage.started_at : undefined));
      const experiment = document.createElement('td');
      if (stage.run_id && data.evidence_source !== 'submitted') { const link = document.createElement('a'); link.href = `${config.mlflowUrl || 'http://localhost:5000'}/#/experiments/${config.mlflowExperimentId || 2}/runs/${stage.run_id}?workflowType=machine_learning`; link.target = '_blank'; link.rel = 'noopener'; link.textContent = `${stage.run_id.slice(0, 12)} ↗`; experiment.append(link); } else { experiment.textContent = stage.run_id ? `${stage.run_id.slice(0, 12)} · saved` : '—'; }
      if (stage.error) { const failure = document.createElement('p'); failure.className = 'error'; failure.textContent = stage.error; label.append(failure); }
      row.append(label, stateCell, seconds, experiment); $('stage-table').append(row);
    }
    text('logs', log.lines.join('\n') || 'No pipeline log yet.');
    $('logs').scrollTop = $('logs').scrollHeight;
    text('updated', `Updated ${new Date().toLocaleTimeString()} · refreshes every 5s`);
    text('console-error', '');
  } catch (error) { text('console-error', `${error.message} Check that the local backend is running.`); }
  finally { fetching = false; $('refresh').disabled = false; }
}
$('mlflow').href = config.mlflowUrl || 'http://localhost:5000';
$('grafana').href = config.grafanaUrl || 'http://localhost:13000/d/local-math-assistant';
$('prometheus').href = config.prometheusUrl || 'http://localhost:19090';
$('refresh').addEventListener('click', refresh);
refresh();
setInterval(refresh, 5000);
