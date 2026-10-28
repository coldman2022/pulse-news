'use strict';
const $ = selector => document.querySelector(selector);
const node = (tag, content, cls) => {
  const n = document.createElement(tag);
  if (content !== undefined && content !== null) n.textContent = String(content);
  if (cls) n.className = cls;
  return n;
};
let all = [], visible = 30;
let saved = {};
try {
  const parsed = JSON.parse(localStorage.getItem('pulse-opportunities-saved') || '{}');
  if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) saved = parsed;
} catch { /* optional browser storage */ }
function store() {
  try { localStorage.setItem('pulse-opportunities-saved', JSON.stringify(saved)); }
  catch { /* not all browsers support storage */ }
}
function safeLink(value) {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' ? url.href : '';
  } catch { return ''; }
}
const fmtDate = stamp => {
  if (!stamp) return 'Не вказано';
  const date = new Date(stamp * 1000);
  if (Number.isNaN(date.getTime())) return 'Не вказано';
  return date.toLocaleTimeString('uk-UA', {hour:'2-digit',minute:'2-digit',hour12:false}) +
    ' · ' + date.toLocaleDateString('uk-UA', {day:'numeric',month:'short'});
};
const evidenceOfficial = card => card.evidence === 'офіційне повідомлення';
function render() {
  const q = $('#opp-search').value.trim().toLocaleLowerCase('uk');
  const country = $('#opp-country').value;
  const signal = $('#opp-signal').value;
  const evidence = $('#opp-evidence').value;
  const savedOnly = $('#opp-view').value === 'saved';
  const list = all.filter(card => {
    if (savedOnly && !saved[card.id]) return false;
    if (country && card.country !== country) return false;
    if (signal && card.signal !== signal) return false;
    if (evidence && card.evidence !== evidence) return false;
    return !q || [card.title,card.summary,card.country,card.source].join(' ').toLocaleLowerCase('uk').includes(q);
  });
  const root = $('#opp-list');
  root.replaceChildren();
  $('#opp-status').textContent = list.length + ' повідомлень у вибраному фільтрі';
  if (!list.length) root.append(node('p','Немає повідомлень за вибраними параметрами. Спробуйте змінити фільтри або зачекати на наступний збір RSS.','empty'));
  for (const item of list.slice(0, visible)) {
    const card = node('article', null,'opp-card');
    const top = node('div',null,'opp-card-top');
    top.append(node('span', item.country || 'Не визначено','opp-country'));
    top.append(node('span',item.evidence,'opp-evidence'+(evidenceOfficial(item)?' is-official':'')));
    card.append(top);
    card.append(node('div',item.signal,'opp-signal'));
    card.append(node('h2',item.title));
    if(item.summary) card.append(node('p',item.summary,'opp-summary'));
    const details = node('dl',null,'opp-facts');
    for(const [name,value] of [
      ['Дата повідомлення',fmtDate(item.published)],
      ['Умови участі','Перевірити в першоджерелі'],
      ['Початок прийому','Не підтверджено'],
      ['Дедлайн','Не підтверджено']
    ]) details.append(node('dt',name),node('dd',value));
    card.append(details);
    const bottom=node('div',null,'opp-bottom');
    bottom.append(node('span',item.source || 'Джерело','opp-source'));
    const link=safeLink(item.url);
    if (link) {
      const a=node('a','Перейти до публікації ↗','opp-link');
      a.href=link;a.target='_blank';a.rel='noopener noreferrer';
      bottom.append(a);
    }
    const save=node('button',saved[item.id]?'Збережено ✓':'Зберегти','opp-save');
    save.type='button';
    save.setAttribute('aria-pressed',String(Boolean(saved[item.id])));
    save.onclick=()=>{if(saved[item.id])delete saved[item.id];else saved[item.id]=true;store();render();};
    bottom.append(save);
    card.append(bottom);
    root.append(card);
  }
  $('#opp-more').hidden=list.length<=visible;
  $('#opp-more').textContent='Показати ще ('+(list.length-visible)+' залишилося)';
}
function reset(){visible=30;render();}
async function load(){
  try {
    const r=await fetch('./opportunities.json',{cache:'no-store'});
    if(!r.ok)throw new Error('HTTP '+r.status);
    const data=await r.json();
    if(!Array.isArray(data.cards))throw new Error('Invalid data');
    all=data.cards;
    $('#opp-total').textContent=String(all.length);
    $('#opp-official').textContent=String(all.filter(evidenceOfficial).length);
    $('#opp-updated').textContent=data.updated?new Date(data.updated*1000).toLocaleString('uk-UA',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}):'—';
    const countries=[...new Set(all.map(x=>x.country).filter(x=>x&&x!=='Не визначено'))].sort();
    const signals=[...new Set(all.map(x=>x.signal).filter(Boolean))].sort();
    for(const country of countries)$('#opp-country').append(new Option(country,country));
    for(const signal of signals)$('#opp-signal').append(new Option(signal,signal));
    render();
  } catch {
    $('#opp-status').textContent='Немає доступу до opportunities.json. Перевірте останню збірку GitHub Actions.';
  }
}
for (const id of ['opp-search','opp-country','opp-signal','opp-evidence','opp-view']) {
  $('#'+id).addEventListener(id==='opp-search'?'input':'change',reset);
}
$('#opp-more').onclick=()=>{visible+=30;render();};
load();
