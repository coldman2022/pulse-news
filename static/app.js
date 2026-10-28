'use strict';
const $ = s => document.querySelector(s);
let articles = [], sourceStatuses = [], updated = 0, mode = 'all', category = '', saved = {}, visibleLimit = 60;
let storageOK = true;
let imagesEnabled = true;
try { imagesEnabled = localStorage.getItem('pulse-show-images') !== 'off'; } catch {}
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
        // Update the visible title without replacing all images and article cards.
        const card=$('#news').querySelector('[data-pulse-article-id="'+article.id+'"]');
        if(card&&autoEnabled&&translationState[article.id]?.shown!==false){
          const heading=card.querySelector('.story-heading a');
          if(heading) heading.textContent=translated;
          const button=card.querySelector('.story-translate');
          if(button&&!translationState[article.id]?.shown){
            button.title='Показати оригінал';
            button.setAttribute('aria-label','Показати оригінал: '+article.title);
          }
        }
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

function newsIcon(kind) {
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
 svg.setAttribute('viewBox','0 0 24 24');
 svg.setAttribute('width','19');svg.setAttribute('height','19');
 svg.setAttribute('fill','none');svg.setAttribute('stroke','currentColor');
 svg.setAttribute('stroke-width','1.8');svg.setAttribute('stroke-linecap','round');
 svg.setAttribute('stroke-linejoin','round');svg.setAttribute('aria-hidden','true');
 const paths={
  bookmark:['M6 3.8h12a1 1 0 0 1 1 1V21l-7-4.8L5 21V4.8a1 1 0 0 1 1-1z'],
  languages:['m5 8 6 6','m4 14 6-6 2-3H2','M2 5h12','M7 2h1','m22 22-5-10-5 10','M14 18h6'],
  external:['M13 5h6v6','M19 5l-9 9','M19 13v6H5V5h6'],
 };
 for(const d of (paths[kind]||[])) {
  const p=document.createElementNS('http://www.w3.org/2000/svg','path');p.setAttribute('d',d);
  svg.append(p);
 }
 return svg;
}
function safePreviewImage(value) {
 try {
  const u=new URL(value);
  if(u.protocol!=='https:' || !u.hostname || u.username || u.password || value.length>1800)return '';
  return u.href;
 } catch{return '';}
}
function articleDate(ts) {
 if(!ts)return 'Без дати';
 const date=new Date(ts*1000);
 if(Number.isNaN(date.getTime()))return 'Без дати';
 const dayMonth=date.toLocaleDateString('uk-UA',{day:'numeric',month:'short'});
 const time=date.toLocaleTimeString('uk-UA',{hour:'2-digit',minute:'2-digit',hour12:false});
 return dayMonth+' · '+time;
}
function editorialLayout(index) {
 if(index===0)return 'story--feature';
 const p=(index-1)%8;
 return p===0 || p===5 ? 'story--wide' : p===1 || p===4 ? 'story--compact' : 'story--standard';
}

function render(){
 $('#saved-count').textContent=Object.keys(saved).length;
 const q=$('#search').value.trim().toLocaleLowerCase('uk');
 const list=(mode==='saved'?Object.values(saved):articles)
   .filter(a=>(!category||a.category===category)&&(!$('#source').value||a.source===$('#source').value)
      &&(!$('#country').value||a.country===$('#country').value)
      &&(!$('#origin').value||a.origin===$('#origin').value)
      &&(!q||(a.title+' '+a.summary+' '+(a.publisher||'')+' '+(a.country||'')).toLocaleLowerCase('uk').includes(q)))
   .sort((a,b)=>(b.published||0)-(a.published||0));
 const news=$('#news');
 news.replaceChildren();
 const viewportRows=new Map();
 const failed=sourceStatuses.filter(s=>!s.ok).map(s=>s.name+(s.cached?' (кеш)':''));
 const working=sourceStatuses.filter(s=>s.ok).length;
 $('#status').textContent=`${list.length} матеріалів · ${working}/${sourceStatuses.length} потоків доступні`+(updated?' • Збір: '+new Date(updated*1000).toLocaleString('uk-UA',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}):'')+(failed.length?' • Помилки джерел: '+failed.length:'')+(!storageOK?' • Закладки можуть не зберегтися.':'');
 const issues=$('#feed-issues'); issues.replaceChildren();
 if(!failed.length) issues.append(el('li','Усі джерела відповіли.'));
 else for(const name of failed) issues.append(el('li',name));
 $('#load-more').hidden=list.length<=visibleLimit;
 $('#load-more').textContent=`Показати ще ${Math.min(60,list.length-visibleLimit)} із ${list.length-visibleLimit} матеріалів`;
 if(!list.length) news.append(el('p',mode==='saved'?'Збережених новин немає. Додайте матеріал іконкою закладки або змініть фільтри.':articles.length?'Нічого не знайдено. Змініть пошук або фільтри.':'Джерела не повернули новин. Повторіть спробу пізніше.','empty'));
 const originNames={official:'Держорган',developer:'Розробник AI',discovery:'Google News',research:'Дослідження',expert:'Експерт',community:'Спільнота',media:'Медіа'};
 for(const [index,a] of list.slice(0,visibleLimit).entries()){
  const layout=editorialLayout(index);
  const image=imagesEnabled&&(index===0||index%3===0||layout==='story--wide')?safePreviewImage(a.image_url):'';
  const topicTone={'Імміграція':'migration','AI':'ai','AI-події':'events','Світ':'world','Україна':'ukraine','Польща':'poland','Бізнес':'business','Технології':'tech','Наука':'science','Дизайн':'design'};
  const tone=topicTone[a.category]||'neutral';
  const card=el('article',null,'story '+layout+' story--topic-'+tone+(image?' story--with-image':' story--no-image'));
  card.dataset.pulseArticleId=a.id;
  viewportRows.set(a.id,a);

  const top=el('div',null,'story-top');
  const source=el('div',null,'story-source');
  source.append(el('span','PULSE / '+(a.publisher||a.source),'story-publisher'));
  const saver=el('button',null,'story-bookmark'+(saved[a.id]?' is-saved':''));
  saver.type='button';saver.append(newsIcon('bookmark'));
  saver.title=saved[a.id]?'Прибрати зі збереженого':'Зберегти статтю';
  saver.setAttribute('aria-label',(saved[a.id]?'Прибрати зі збереженого: ':'Зберегти статтю: ')+a.title);
  saver.setAttribute('aria-pressed',String(Boolean(saved[a.id])));
  saver.onclick=()=>{
    if(saved[a.id]) delete saved[a.id];
    else saved[a.id]=a;
    persist();render();
  };
  top.append(source,saver);

  const translation=translationState[a.id]||{};
  const shown=translation.shown===true;
  const userSelectedOriginal=translation.shown===false;
  const autoTitle=autoEnabled&&!userSelectedOriginal?translatedTitles[a.id]:'';
  const content=el('div',null,'story-content');
  const copy=el('div',null,'story-copy');
  const h=el('h2',null,'story-heading');
  h.append(link(shown?translation.title:(autoTitle||a.title),a.url));
  const summary=el('p',shown?translation.summary:a.summary,'story-summary');
  copy.append(h,summary);

  const lang=articleLanguage(a);
  let translateButton=null;
  if(lang!=='uk'){
   const tButton=el('button',null,'translate-btn story-translate');
   tButton.type='button';
   tButton.disabled=Boolean(translation.loading);
   tButton.append(newsIcon('languages'));
   const label=translation.loading?'Перекладаємо':shown||autoTitle?'Показати оригінал':'Перекласти українською';
   tButton.setAttribute('aria-label',label+': '+a.title);
   tButton.title=label;
   tButton.onclick=async()=>{
    if(translationState[a.id]?.shown || (translatedTitles[a.id] && translationState[a.id]?.shown!==false)){
      translationState[a.id]={...translationState[a.id],shown:false};render();return;
    }
    if(translationCache[a.id]){
      translationState[a.id]={...translationCache[a.id],shown:true};render();return;
    }
    autoSeen.add(a.id);
    translationState[a.id]={loading:true};render();
    try{
      const result=await translateArticlePreview(a);
      storeTranslation(a.id,result);
      translationState[a.id]={...result,shown:true};
    }catch{translationState[a.id]={error:true};}
    render();
   };
   translateButton=tButton;
   if(translation.error){
     const warning=el('span','Переклад недоступний','translation-error');
     copy.append(warning);
   }
  }
  content.append(copy);

  if(image){
    const figure=el('figure',null,'story-media');
    const mediaLink=link('',a.url);
    mediaLink.setAttribute('aria-label','Відкрити статтю: '+a.title);
    const img=document.createElement('img');
    img.alt='';img.loading='lazy';img.decoding='async';
    img.referrerPolicy='no-referrer';
    img.src=image;
    img.addEventListener('error',()=>{
      figure.remove();
      card.classList.remove('story--with-image');
      card.classList.add('story--no-image');
      if(index===0) content.append(el('div',null,'story-abstract'));
    },{once:true});
    mediaLink.append(img);figure.append(mediaLink);
    if(a.image_credit)figure.append(el('figcaption',a.image_credit,'story-credit'));
    content.append(figure);
  }else if(index===0){
    content.append(el('div',null,'story-abstract'));
  }
  const bottom=el('div',null,'story-bottom');
  const date=document.createElement('time');date.className='story-date';
  date.textContent=articleDate(a.published);
  if(a.published) date.dateTime=new Date(a.published*1000).toISOString();
  bottom.append(date);
  bottom.append(el('span',a.category||'Новини','story-tag story-tag--topic'));
  if(translateButton)bottom.append(translateButton);
  card.append(top,content,bottom);
  news.append(card);
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
 $('#origin').onchange=resetFilter;$('#refresh').onclick=load;
 $('#load-more').onclick=()=>{visibleLimit+=60;render();};
const filterToggle=$('#filter-toggle');
const filterPanel=$('#filter-panel');
filterToggle.onclick=()=>{
  const expanded=filterToggle.getAttribute('aria-expanded')==='true';
  filterToggle.setAttribute('aria-expanded',String(!expanded));
  filterPanel.hidden=expanded;
};
$('#clear-filters').onclick=()=>{
  $('#source').value='';$('#country').value='';$('#origin').value='';
  filterPanel.hidden=true;filterToggle.setAttribute('aria-expanded','false');
  resetFilter();
};
$('#show-images').checked=imagesEnabled;
$('#show-images').onchange=()=>{
  imagesEnabled=$('#show-images').checked;
  try{localStorage.setItem('pulse-show-images',imagesEnabled?'on':'off');}catch{}
  render();
};
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

