'use strict';
const $ = s => document.querySelector(s);
let articles = [], sourceStatuses = [], updated = 0, mode = 'all', category = '', saved = {};
let storageOK = true;
try { saved = JSON.parse(localStorage.getItem('pulse-saved') || '{}'); if (!saved || Array.isArray(saved) || typeof saved !== 'object') saved = {}; } catch { storageOK = false; }
$('#today').textContent = new Intl.DateTimeFormat('uk-UA', {day:'numeric',month:'long',year:'numeric'}).format(new Date());
const el = (tag, text, cls) => {const n = document.createElement(tag); if(text) n.textContent=text; if(cls) n.className=cls; return n;};
function link(text, url) {const a=el('a',text); a.href=url; a.target='_blank'; a.rel='noopener noreferrer'; return a;}
function persist() {try{localStorage.setItem('pulse-saved',JSON.stringify(saved));}catch{storageOK=false;}}
function render(){
 $('#saved-count').textContent=Object.keys(saved).length;
 const q=$('#search').value.trim().toLocaleLowerCase('uk');
 const list=(mode==='saved'?Object.values(saved):articles).filter(a=>(!category||a.category===category)&&(!$('#source').value||a.source===$('#source').value)&&(!q||(a.title+' '+a.summary).toLocaleLowerCase('uk').includes(q)));
 $('#news').replaceChildren();
 const failed=sourceStatuses.filter(s=>!s.ok).map(s=>s.name+(s.cached?' (кеш)':''));
 const working=sourceStatuses.filter(s=>s.ok).length;
 $('#status').textContent=`${list.length} матеріалів · ${working}/${sourceStatuses.length} RSS-джерел доступні`+(updated?' • Збір RSS: '+new Date(updated*1000).toLocaleString('uk-UA',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}):'')+(failed.length?' • Недоступні джерела: '+failed.join(', '):'')+(!storageOK?' • Браузер не дозволяє зберігати новини між сеансами.':'');
 if(!list.length) $('#news').append(el('p',mode==='saved'?'Збережених новин за цими фільтрами немає. Натисніть «Зберегти» біля матеріалу або змініть фільтри.':articles.length?'Нічого не знайдено. Змініть пошук або фільтри.':'Джерела не повернули новин. Повторіть спробу пізніше.','empty'));
 for(const a of list){
  const row=el('article',null,'story'), stamp=el('div',a.published?new Date(a.published*1000).toLocaleTimeString('uk-UA',{hour:'2-digit',minute:'2-digit'}):'Без дати','stamp');
  stamp.append(el('span',a.published?new Date(a.published*1000).toLocaleDateString('uk-UA',{day:'numeric',month:'short'}):''));
  const body=el('div'), meta=el('div',null,'meta');meta.append(el('b',a.source),el('span',a.category));
  const h=el('h2');h.append(link(a.title,a.url));
  const actions=el('div',null,'actions');actions.append(link('Читати оригінал',a.url),link('Перекласти українською','https://translate.google.com/translate?sl=auto&tl=uk&u='+encodeURIComponent(a.url)));
  const save=el('button',saved[a.id]?'Збережено ✓':'Зберегти');save.setAttribute('aria-pressed',String(Boolean(saved[a.id])));save.setAttribute('aria-label',(saved[a.id]?'Вилучити зі збереженого: ':'Зберегти: ')+a.title);
  save.onclick=()=>{saved[a.id]?delete saved[a.id]:saved[a.id]=a;persist();render(); const focus=[...document.querySelectorAll('.actions button')].find(b=>b.getAttribute('aria-label').endsWith(a.title));if(focus)focus.focus();};actions.append(save);body.append(meta,h,el('p',a.summary,'summary'),actions);row.append(stamp,body);$('#news').append(row);
 }
}
async function load(){
 $('#refresh').disabled=true;$('#refresh').textContent='Оновлення…';$('#status').textContent='Завантажуємо новини з джерел…';
 try{const r=await fetch('./news.json', {cache:'no-store'});if(!r.ok)throw Error();const data=await r.json();articles=data.articles;sourceStatuses=data.sources;updated=data.updated;
 const selected=$('#source').value;$('#source').replaceChildren(new Option('Усі джерела',''));for(const name of [...new Set([...sourceStatuses.map(s=>s.name),...Object.values(saved).map(a=>a.source)])].sort())$('#source').append(new Option(name,name));$('#source').value=selected;render();
 }catch{render();$('#status').textContent='Не вдалося завантажити стрічку. Перевірте з’єднання та повторіть спробу.';}
 finally{$('#refresh').disabled=false;$('#refresh').textContent='Оновити стрічку';}
}
$('#search').oninput=render;$('#source').onchange=render;$('#refresh').onclick=load;
for(const b of document.querySelectorAll('[data-mode]')){b.onclick=()=>{mode=b.dataset.mode;for(const n of document.querySelectorAll('[data-mode]')){n.classList.toggle('active',n===b);n.setAttribute('aria-pressed',String(n===b));}render();};b.setAttribute('aria-pressed',String(b.classList.contains('active')));}
for(const b of document.querySelectorAll('[data-category]')){b.onclick=()=>{category=b.dataset.category;for(const n of document.querySelectorAll('[data-category]')){n.classList.toggle('active',n===b);n.setAttribute('aria-pressed',String(n===b));}render();};b.setAttribute('aria-pressed',String(b.classList.contains('active')));}
load();setInterval(load,300000);

