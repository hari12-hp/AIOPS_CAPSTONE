const $ = id => document.getElementById(id);
const config = window.MATH_ASSISTANT_CONFIG || {};
const api = path => `${(config.apiBase || '').replace(/\/$/, '')}${path}`;
const question = $('question'), solve = $('solve'), answer = $('answer'), error = $('error');
let busy = false;
let latestAnswer = '';
function renderAnswer(value) {
  latestAnswer = value;
  $('answer-text').textContent = value;
  if (window.renderMathInElement) window.renderMathInElement($('answer-text'), {
    delimiters: [{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false},{left:'\\(',right:'\\)',display:false},{left:'\\[',right:'\\]',display:true}],
    throwOnError:false, trust:false, strict:'ignore'
  });
}
function status(health) {
  const ok = health.status === 'ok' && health.configured;
  $('status').className = `status ${ok ? 'ready' : 'problem'}`;
  $('status').replaceChildren(Object.assign(document.createElement('i'), {}), document.createTextNode(ok ? 'Ready to explore' : 'Service unavailable'));
}
async function refresh() {
  try {
    const response = await fetch(api('/health'));
    if (!response.ok) throw new Error('Unavailable');
    status(await response.json());
  } catch { status({status: 'error'}); }
}
function updateCount() { $('char-count').textContent = `${question.value.length.toLocaleString()} / 8,000`; }
async function submit() {
  if (busy) return;
  const value = question.value.trim();
  error.textContent = '';
  if (!value) { error.textContent = 'Enter a mathematics question first.'; question.focus(); return; }
  busy = true;
  solve.disabled = true;
  solve.textContent = 'Solving…';
  question.setAttribute('aria-busy', 'true');
  $('progress').hidden = false;
  answer.hidden = true;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 190000);
  try {
    const response = await fetch(api('/v1/solve'), {method: 'POST', headers: {'content-type': 'application/json'}, body: JSON.stringify({question: value}), signal: controller.signal});
    const result = await response.json();
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Please enter a question with 1–8,000 characters.');
    renderAnswer(result.answer);
    $('latency').textContent = `Answered in ${result.latency_seconds.toFixed(2)} seconds · Generated locally`;
    $('copy').textContent = 'Copy answer';
    answer.hidden = false;
  } catch (failure) { error.textContent = failure.name === 'AbortError' ? 'This answer took too long. Try a shorter question.' : failure.message === 'Failed to fetch' ? 'Unable to connect. Check that the local services are running.' : failure.message; }
  finally {
    clearTimeout(timeout);
    busy = false;
    solve.disabled = false;
    solve.innerHTML = 'Solve problem <span aria-hidden="true">↗</span>';
    $('progress').hidden = true;
    question.removeAttribute('aria-busy');
    refresh();
  }
}
solve.addEventListener('click', submit);
question.addEventListener('input', updateCount);
question.addEventListener('keydown', event => { if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) { event.preventDefault(); submit(); } });
document.querySelectorAll('[data-example]').forEach(button => button.addEventListener('click', () => { question.value = button.dataset.example; updateCount(); question.focus(); }));
$('copy').addEventListener('click', async () => { try { await navigator.clipboard.writeText(latestAnswer); $('copy').textContent = 'Copied'; } catch { $('copy').textContent = 'Select the answer to copy'; } });
refresh();
