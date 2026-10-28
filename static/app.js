'use strict';
const $ = s => document.querySelector(s);
let articles = [], sourceStatuses = [], updated = 0, mode = 'all', category = '', saved = {}, visibleLimit = 60;
let storageOK = true;
try { saved = JSON.parse(localStorage.getItem('pulse-saved') || '{}'); if (!saved || Array.isArray(saved) || typeof saved !== 'object') saved = {}; } catch { storageOK = false; }
$('#today').textContent = new Intl.DateTimeFormat('uk-UA', {day:'numeric',month:'long',year:'numeric'}).format(new Date());
const el = (tag, text, cls) => {const n = document.createElement(tag); if(text) n.textContent=text; if(cls) n.className=cls; return n;};
function link(text, url) {const a=el('a',text); a.href=url; a.target='_blank'; a.rel='noopener noreferrer'; return a;}
function persist() {try{localStorage.setItem('pulse-saved',JSON.stringify(saved));}catch{storageOK=false;}}

const translationState = Object.create(null);
let translationCache = {};
try {
  const previous = JSON.parse(localStorage.getItem('pulse-translations') || '{}');
  if (previous && typeof previous === 'object' && !Array.isArray(previous)) translationCache = previous;
} catch { /* Private browsing can block storage. */ }

/* Only headlines visible in the viewport are translated automatically.
   A small local daily budget and one request at a time protect the public API. */
const AUTO_MAX_CHARS = 2400;
let autoEnabled = true;
try { autoEnabled = localStorage.getItem('pulse-auto-headlines') !== 'off'; } catch {}
let translatedTitles = {};
try {
  const stored = JSON.parse(localStorage.getItem('pulse-title-translations') || '{}');
  if (stored && typeof stored === 'object' && !Array.isArray(stored)) translatedTitles = stored;
} catch {}
const todayKey = () => {
  const n = new Date();
  return [n.getFullYear(), String(n.getMonth()+1).padStart(2,'0'), String(n.getDate()).padStart(2,'0')].join('-');
};
let dailyUsage = {day:todayKey(), chars:0};
try {
  const usage = JSON.parse(localStorage.getItem('pulse-auto-usage') || '{}');
  if (usage.day === todayKey() && Number.isFinite(usage.chars) && usage.chars >= 0)
    dailyUsage = {day:usage.day, chars:usage.chars};
} catch {}
const autoQueue = [];
const autoSeen = new Set();
let autoBusy = false, autoPaused = false, viewportObserver = null;
const dwellTimers = new Map();
function trackUsage(chars) {
  if (dailyUsage.day !== todayKey()) dailyUsage = {day:todayKey(), chars:0};
  dailyUsage.chars += chars;
  try { localStorage.setItem('pulse-auto-usage', JSON.stringify(dailyUsage)); } catch {}
}
function storeTitle(id, title) {
  translatedTitles[id] = title;
  const recent = Object.entries(translatedTitles).slice(-300);
  translatedTitles = Object.fromEntries(recent);
  try { localStorage.setItem('pulse-title-translations', JSON.stringify(translatedTitles)); } catch {}
}
function translationStatus() {
  if (dailyUsage.day !== todayKey()) dailyUsage = {day:todayKey(), chars:0};
  const remaining = Math.max(0,AUTO_MAX_CHARS-dailyUsage.chars);
  $('#translation-budget').textContent = autoEnabled
    ? autoPaused ? 'Автопереклад тимчасово недоступний — доступна кнопка перекладу'
      : remaining ? 'Лише видимі заголовки · ліміт '+remaining+' символів на сьогодні'
        : 'Денний ліміт автоперекладу вичерпано'
    : 'Автопереклад вимкнено';
}
function isArticleOnScreen(id) {
  const card=$('#news').querySelector('[data-pulse-article-id="'+id+'"]');
  if (!card) return false;
  const bounds=card.getBoundingClientRect();
  return bounds.height > 0 && bounds.bottom > 0 && bounds.top < window.innerHeight;
}
function queueVisible(article) {
  if (!autoEnabled || autoPaused || !article || articleLanguage(article)==='uk' ||
      translatedTitles[article.id] || autoSeen.has(article.id) ||
      translationState[article.id]?.loading) return;
  const title=(article.title||'').trim();
  if (!title || title.length>350) return;
  if (dailyUsage.day !== todayKey()) dailyUsage = {day:todayKey(), chars:0};
  if (dailyUsage.chars + title.length > AUTO_MAX_CHARS) {translationStatus();return;}
  autoSeen.add(article.id);
  autoQueue.push(article);
  void drainAutoQueue();
}
async function drainAutoQueue() {
  if (autoBusy) return;
  autoBusy = true;
  try {
    while (autoQueue.length && autoEnabled && !autoPaused) {
      const article=autoQueue.shift();
      if (!article || translatedTitles[article.id] || translationState[article.id]?.loading) continue;
      // The visitor may have scrolled elsewhere while another title was translating.
      // Skip off-screen requests; allow a retry when the article is visible again.
      if (!isArticleOnScreen(article.id)) { autoSeen.delete(article.id); continue; }
      if (dailyUsage.day !== todayKey()) dailyUsage={day:todayKey(),chars:0};
      const title=article.title.trim();
      if (dailyUsage.chars+title.length>AUTO_MAX_CHARS) {translationStatus(); break;}
      // Count attempted text before sending, including unsuccessful requests.
      trackUsage(title.length);
      translationStatus();
      try {
        const translatedParts=[];
        for (const chunk of translationChunks(title)) {
          translatedParts.push(await translatePiece(chunk,articleLanguage(article)));
        }
        const translated=translatedParts.join(' ');
        storeTitle(article.id,translated);
        render();
      } catch (error) {
        console.warn('Pulse lazy translation paused:',error);
        autoPaused=true;
        autoQueue.length=0;
        translationStatus();
      }
    }
  } finally {autoBusy=false;}
}
function watchVisibleHeadlines(rows) {
  if (viewportObserver) viewportObserver.disconnect();
  for (const timer of dwellTimers.values()) clearTimeout(timer);
  dwellTimers.clear();
  if (!autoEnabled || autoPaused || typeof IntersectionObserver==='undefined') return;
  viewportObserver = new IntersectionObserver(entries => {
    for (const entry of entries) {
      const id=entry.target.dataset.pulseArticleId;
      if (!id) continue;
      if (!entry.isIntersecting) {
        if (dwellTimers.has(id)) clearTimeout(dwellTimers.get(id));
        dwellTimers.delete(id);
      } else if (!dwellTimers.has(id)) {
        const article=rows.get(id);
        if (!article || translatedTitles[id] || articleLanguage(article)==='uk') continue;
        const timer=setTimeout(() => {
          dwellTimers.delete(id);
          if (entry.target.isConnected && autoEnabled) queueVisible(article);
        }, 650);
        dwellTimers.set(id,timer);
      }
    }
  }, {threshold:0.35, rootMargin:'0px 0px 35px 0px'});
  for (const [id, article] of rows) {
    if (articleLanguage(article)==='uk' || translatedTitles[id]) continue;
    const card=$('#news').querySelector('[data-pulse-article-id="'+id+'"]');
    if (card) viewportObserver.observe(card);
  }
}

const byteCount = text => new TextEncoder().encode(text).length;
function translationChunks(text) {
  // MyMemory accepts a maximum of 500 UTF-8 bytes per request.
  const parts = [];
  let part = '';
  for (const word of (text || '').trim().split(/\s+/).filter(Boolean)) {
    for (const char of Array.from(word)) {
      if (byteCount(char) > 440) continue;
    }
    const candidate = part ? part + ' ' + word : word;
    if (byteCount(candidate) <= 440) { part = candidate; continue; }
    if (part) { parts.push(part); part = ''; }
    if (byteCount(word) <= 440) { part = word; continue; }
    let piece = '';
    for (const char of Array.from(word)) {
      if (byteCount(piece + char) > 440) { if (piece) parts.push(piece); piece = ''; }
      piece += char;
    }
    part = piece;
  }
  if (part) parts.push(part);
  return parts;
}
function articleLanguage(article) {
  if (article.language) return article.language;
  if (article.source === 'ITC.ua' || article.category === 'Україна') return 'uk';
  if (article.source.startsWith('RMF24')) return 'pl';
  return 'en';
}
async function translatePiece(text, language) {
  const url = new URL('https://api.mymemory.translated.net/get');
  url.searchParams.set('q', text);
  url.searchParams.set('langpair', language + '|uk');
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 12000);
  try {
    const response = await fetch(url, {signal: controller.signal});
    if (!response.ok) throw new Error('Translation API HTTP ' + response.status);
    const data = await response.json();
    const result = String(data?.responseData?.translatedText || '').trim();
    if (Number(data?.responseStatus) !== 200 || !result ||
        /MYMEMORY WARNING|USED ALL AVAILABLE|DAILY LIMIT/i.test(result)) {
      throw new Error('Translation API quota or error');
    }
    return result;
  } finally { clearTimeout(timer); }
}
async function translateArticlePreview(article) {
  const lang = articleLanguage(article);
  if (lang === 'uk') return {title: article.title, summary: article.summary || ''};
  if (!['en', 'pl', 'de', 'fr', 'es', 'it'].includes(lang)) throw new Error('Unsupported language');
  const pieces = translationChunks(article.title || '');
  if (!pieces.length) throw new Error('Empty title');
  const title = translatedTitles[article.id] || (await Promise.all(pieces.map(p => translatePiece(p, lang)))).join(' ');
  const summaryParts = translationChunks(article.summary || '');
  const summaries = [];
  for (const part of summaryParts.slice(0, 4)) summaries.push(await translatePiece(part, lang));
  return {title, summary: summaries.join(' ')};
}
function storeTranslation(id, value) {
  translationCache[id] = value;
  const entries = Object.entries(translationCache).slice(-100);
  translationCache = Object.fromEntries(entries);
  try { localStorage.setItem('pulse-translations', JSON.stringify(translationCache)); } catch { /* Optional cache. */ }
}

function render(){
 $('#saved-count').textContent=Object.keys(saved).length;
 const q=$('#search').value.trim().toLocaleLowerCase('uk');
 const weight={'Імміграція':36,'AI':24,'AI-події':20,'Світ':3};
 const list=(mode==='saved'?Object.values(saved):articles)
   .filter(a=>(!category||a.category===category)&&(!$('#source').value||a.source===$('#source').value)
      &&(!$('#country').value||a.country===$('#country').value)
      &&(!$('#origin').value||a.origin===$('#origin').value)
      &&(!q||(a.title+' '+a.summary+' '+(a.publisher||'')+' '+(a.country||'')).toLocaleLowerCase('uk').includes(q)))
   .sort((a,b)=>{
      if($('#sort').value==='recent') return (b.published||0)-(a.published||0);
      const score=a=>(a.published||0)+3600*(weight[a.category]||0)+(a.origin==='official'?12*3600:0)+(a.origin==='developer'?3*3600:0);
      return score(b)-score(a);
   });
 $('#news').replaceChildren();
 const viewportRows=new Map();
 const failed=sourceStatuses.filter(s=>!s.ok).map(s=>s.name+(s.cached?' (кеш)':''));
 const working=sourceStatuses.filter(s=>s.ok).length;
 $('#status').textContent=`${list.length} матеріалів · ${working}/${sourceStatuses.length} потоків доступні`+(updated?' • Збір: '+new Date(updated*1000).toLocaleString('uk-UA',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}):'')+(failed.length?' • Помилки джерел: '+failed.length:'')+(!storageOK?' • Закладки можуть не зберегтися.':'');
 const issues=$('#feed-issues'); issues.replaceChildren();
 if(!failed.length) issues.append(el('li','Усі джерела відповіли.'));
 else for(const name of failed) issues.append(el('li',name));
 $('#load-more').hidden=list.length<=visibleLimit;
 $('#load-more').textContent=`Показати ще ${Math.min(60,list.length-visibleLimit)} із ${list.length-visibleLimit} матеріалів`;
 if(!list.length) $('#news').append(el('p',mode==='saved'?'Збережених новин за цими фільтрами немає. Натисніть «Зберегти» біля матеріалу або змініть фільтри.':articles.length?'Нічого не знайдено. Змініть пошук або фільтри.':'Джерела не повернули новин. Повторіть спробу пізніше.','empty'));
 for(const a of list.slice(0,visibleLimit)){
  const row=el('article',null,'story'), stamp=el('div',a.published?new Date(a.published*1000).toLocaleTimeString('uk-UA',{hour:'2-digit',minute:'2-digit'}):'Без дати','stamp');
  row.dataset.pulseArticleId=a.id;
  viewportRows.set(a.id,a);
  stamp.append(el('span',a.published?new Date(a.published*1000).toLocaleDateString('uk-UA',{day:'numeric',month:'short'}):''));
  const body=el('div'), meta=el('div',null,'meta');meta.append(el('b',a.publisher||a.source),el('span',a.category));
  if(a.country && a.country!=='Світ') meta.append(el('span',a.country));
  const originNames={official:'Держорган',developer:'Розробник AI',discovery:'Через Google News',research:'Наукова публікація',expert:'Експертний блог',community:'Спільнота',media:'Медіа'};
  const origin=el('span',originNames[a.origin]||'Джерело','origin origin-'+(a.origin||'media'));
  meta.append(origin);
  const translation=translationState[a.id] || {};
  const shown=translation.shown === true;
  const userSelectedOriginal=translation.shown === false;
  const autoTitle=autoEnabled && !userSelectedOriginal ? translatedTitles[a.id] : '';
  const h=el('h2');h.append(link(shown ? translation.title : (autoTitle || a.title),a.url));
  const actions=el('div',null,'actions');
  actions.append(link('Читати оригінал',a.url));
  const preview=el('p',shown ? translation.summary : a.summary,'summary');
  const lang=articleLanguage(a);
  if (lang!=='uk') {
    const translate=el('button',translation.loading?'Перекладаємо…':shown?'Показати оригінал':'Перекласти анонс','translate-btn');
    translate.type='button';
    translate.disabled=Boolean(translation.loading);
    translate.setAttribute('aria-label',(shown?'Показати оригінал: ':'Перекласти українською: ')+a.title);
    translate.onclick=async ()=>{
      if (translationState[a.id]?.shown) {translationState[a.id]={...translationState[a.id],shown:false};render();return;}
      if (translationCache[a.id]) {translationState[a.id]={...translationCache[a.id],shown:true};render();return;}
      autoSeen.add(a.id);
      translationState[a.id]={loading:true};render();
      try {
        const result=await translateArticlePreview(a);
        storeTranslation(a.id,result);
        translationState[a.id]={...result,shown:true};
      } catch {
        translationState[a.id]={error:true};
      }
      render();
    };
    actions.append(translate);
    if (translation.error) {
      const fallback='https://translate.google.com/?sl=auto&tl=uk&text='+encodeURIComponent(a.title+'\n\n'+(a.summary||''))+'&op=translate';
      const warning=el('span','Автопереклад тимчасово недоступний.','translation-error');
      actions.append(warning,link('Відкрити текст у Google Translate',fallback));
    }
  }
  const save=el('button',saved[a.id]?'Збережено ✓':'Зберегти');save.setAttribute('aria-pressed',String(Boolean(saved[a.id])));save.setAttribute('aria-label',(saved[a.id]?'Вилучити зі збереженого: ':'Зберегти: ')+a.title);
  save.onclick=()=>{saved[a.id]?delete saved[a.id]:saved[a.id]=a;persist();render(); const focus=[...document.querySelectorAll('.actions button')].find(b=>b.getAttribute('aria-label').endsWith(a.title));if(focus)focus.focus();};actions.append(save);body.append(meta,h,preview,actions);row.append(stamp,body);$('#news').append(row);
 }
 translationStatus();
 watchVisibleHeadlines(viewportRows);
}
async function load(){
 $('#refresh').disabled=true;$('#refresh').textContent='Оновлення…';$('#status').textContent='Завантажуємо новини з джерел…';
 try{const r=await fetch('./news.json', {cache:'no-store'});if(!r.ok)throw Error();const data=await r.json();articles=data.articles;sourceStatuses=data.sources;updated=data.updated;
 const selected=$('#source').value;$('#source').replaceChildren(new Option('Усі джерела',''));for(const name of [...new Set([...sourceStatuses.map(s=>s.name),...Object.values(saved).map(a=>a.source)])].sort())$('#source').append(new Option(name,name));$('#source').value=selected;
 const previousCountry=$('#country').value;
 $('#country').replaceChildren(new Option('Усі країни',''));
 for(const name of [...new Set(articles.map(a=>a.country).filter(Boolean))].sort())$('#country').append(new Option(name,name));
 $('#country').value=previousCountry;
 render();
 }catch{render();$('#status').textContent='Не вдалося завантажити стрічку. Перевірте з’єднання та повторіть спробу.';}
 finally{$('#refresh').disabled=false;$('#refresh').textContent='Оновити стрічку';}
}
function resetFilter(){visibleLimit=60;render();}
 $('#search').oninput=resetFilter;$('#source').onchange=resetFilter;$('#country').onchange=resetFilter;
 $('#origin').onchange=resetFilter;$('#sort').onchange=resetFilter;$('#refresh').onclick=load;
 $('#load-more').onclick=()=>{visibleLimit+=60;render();};
$('#auto-translate').checked=autoEnabled;
$('#auto-translate').onchange=()=>{
  autoEnabled=$('#auto-translate').checked;
  try {localStorage.setItem('pulse-auto-headlines',autoEnabled?'on':'off');}catch{}
  if(!autoEnabled)autoQueue.length=0;
  if(autoEnabled)autoPaused=false;
  translationStatus();
  render();
};
translationStatus();
for(const b of document.querySelectorAll('[data-mode]')){b.onclick=()=>{mode=b.dataset.mode;visibleLimit=60;for(const n of document.querySelectorAll('[data-mode]')){n.classList.toggle('active',n===b);n.setAttribute('aria-pressed',String(n===b));}render();};b.setAttribute('aria-pressed',String(b.classList.contains('active')));}
for(const b of document.querySelectorAll('[data-category]')){b.onclick=()=>{category=b.dataset.category;visibleLimit=60;for(const n of document.querySelectorAll('[data-category]')){n.classList.toggle('active',n===b);n.setAttribute('aria-pressed',String(n===b));}render();};b.setAttribute('aria-pressed',String(b.classList.contains('active')));}
load();setInterval(load,300000);

