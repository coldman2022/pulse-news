'use strict';
const $ = s => document.querySelector(s);
const params = new URLSearchParams(location.search);
const initialMode = params.get('mode');
let sharedArticleId = /^[a-f0-9]{20}$/.test(params.get('article')||'')?params.get('article'):null;
let sharedScrolled = false;
let articles = [], archiveArticles = [], archiveCount = 0, focusArticles = [], baseFocusArticles = [], focusPool = [], briefArticles = [], sourceStatuses = [], updated = 0, mode = 'all', category = '', saved = {}, votes = {}, visibleLimit = 60;
if (['all','focus','saved','archive'].includes(initialMode)) mode = initialMode;
let storageOK = true;
const imagesEnabled = true;
try { saved = JSON.parse(localStorage.getItem('pulse-saved') || '{}'); if (!saved || Array.isArray(saved) || typeof saved !== 'object') saved = {}; } catch { storageOK = false; }
try {
  const previous = JSON.parse(localStorage.getItem('pulse-feedback-v1') || '{}');
  if(previous && typeof previous==='object' && !Array.isArray(previous)){
    votes = Object.fromEntries(Object.entries(previous).filter(([id,v])=>
      id.length<=150 && v && [-1,1].includes(v.value) && typeof v.category==='string'
    ).slice(-400));
  }
} catch { votes = {}; }
function saveFeedback() {
  try { localStorage.setItem('pulse-feedback-v1', JSON.stringify(votes)); } catch { storageOK=false; }
}
function voteOn(article,value) {
  if(votes[article.id]?.value===value) delete votes[article.id];
  else votes[article.id]={value,category:article.category||''};
  if(Object.keys(votes).length>400)delete votes[Object.keys(votes)[0]];
  saveFeedback();
  focusArticles=personalizedFocus();
  render();
}
function personalizedFocus() {
  const disliked = a => votes[a.id]?.value===-1;
  if(!focusPool.length || !Object.keys(votes).length)return baseFocusArticles.filter(a=>!disliked(a));
  const topics={};
  for(const feedback of Object.values(votes)) {
    if(feedback.category) topics[feedback.category]=(topics[feedback.category]||0)+feedback.value;
  }
  const ranked=focusPool.filter(a=>!disliked(a)).map(a=>({
    article:a,
    score:(Number(a.relevance_score)||0)+Math.max(-3,Math.min(3,topics[a.category]||0))*2
      +(votes[a.id]?.value===1?3:0)
  })).sort((a,b)=>b.score-a.score||(b.article.published||0)-(a.article.published||0));
  const selection=[], categories={};
  for(const item of ranked) {
    const key=item.article.category||'';
    if((categories[key]||0)>=8)continue;
    selection.push(item.article);
    categories[key]=(categories[key]||0)+1;
    if(selection.length>=18)break;
  }
  return selection.sort((a,b)=>(b.published||0)-(a.published||0));
}
const today=new Date();
$('#today').textContent = new Intl.DateTimeFormat('uk-UA', {day:'numeric',month:'long',year:'numeric'}).format(today) + ' р.';
$('#today').dateTime=[today.getFullYear(),String(today.getMonth()+1).padStart(2,'0'),String(today.getDate()).padStart(2,'0')].join('-');
const el = (tag, text, cls) => {const n = document.createElement(tag); if(text) n.textContent=text; if(cls) n.className=cls; return n;};
function link(text, url) {const a=el('a',text); a.href=url; a.target='_blank'; a.rel='noopener noreferrer'; return a;}
function persist() {try{localStorage.setItem('pulse-saved',JSON.stringify(saved));}catch{storageOK=false;}}

const translationState = Object.create(null);
let sharedTranslations = Object.create(null);
let sharedTranslationsPending = true;
function sharedTranslation(article){
  const item=sharedTranslations[article.id];
  return item && item.source_title===article.title &&
    item.language===articleLanguage(article) && typeof item.title==='string' &&
    typeof item.summary==='string' ? item : null;
}
async function loadSharedTranslations(){
  try{
    const response=await fetch('./translations.json',{cache:'no-store'});
    if(!response.ok)throw Error('Batch translations unavailable');
    const data=await response.json();
    if(data.schema!==1 || !data.articles || Array.isArray(data.articles) ||
       typeof data.articles!=='object')throw Error('Unexpected translations format');
    sharedTranslations=data.articles;
  }catch{
    // Browsers still retain on-demand MyMemory translations if the batch is absent.
  }finally{
    sharedTranslationsPending=false;
    if(articles.length || archiveArticles.length || focusArticles.length)render();
  }
}
let translationCache = {};
try {
  const previous = JSON.parse(localStorage.getItem('pulse-translations') || '{}');
  if (previous && typeof previous === 'object' && !Array.isArray(previous)) translationCache = previous;
} catch { /* Private browsing can block storage. */ }

/* Only headlines visible in the viewport are translated automatically.
   A small local daily budget and one request at a time protect the public API. */
const AUTO_MAX_CHARS = 2400;
const autoEnabled = true;
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
 if (dailyUsage.day !== todayKey()) dailyUsage={day:todayKey(), chars:0};
}
function isArticleOnScreen(id) {
  const card=$('#news').querySelector('[data-pulse-article-id="'+id+'"]');
  if (!card) return false;
  const bounds=card.getBoundingClientRect();
  return bounds.height > 0 && bounds.bottom > 0 && bounds.top < window.innerHeight;
}
function queueVisible(article) {
  if (!autoEnabled || autoPaused || sharedTranslationsPending || !article ||
      sharedTranslation(article) || articleLanguage(article)==='uk' ||
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
      if (!article || sharedTranslation(article) || translatedTitles[article.id] ||
          translationState[article.id]?.loading) continue;
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
  if (!autoEnabled || autoPaused || sharedTranslationsPending ||
      typeof IntersectionObserver==='undefined') return;
  viewportObserver = new IntersectionObserver(entries => {
    for (const entry of entries) {
      const id=entry.target.dataset.pulseArticleId;
      if (!id) continue;
      if (!entry.isIntersecting) {
        if (dwellTimers.has(id)) clearTimeout(dwellTimers.get(id));
        dwellTimers.delete(id);
      } else if (!dwellTimers.has(id)) {
        const article=rows.get(id);
        if (!article || sharedTranslation(article) || translatedTitles[id] ||
            articleLanguage(article)==='uk') continue;
        const timer=setTimeout(() => {
          dwellTimers.delete(id);
          if (entry.target.isConnected && autoEnabled) queueVisible(article);
        }, 650);
        dwellTimers.set(id,timer);
      }
    }
  }, {threshold:0.35, rootMargin:'0px 0px 35px 0px'});
  for (const [id, article] of rows) {
    if (articleLanguage(article)==='uk' || sharedTranslation(article) || translatedTitles[id]) continue;
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
  'thumb-up':['M7 10v11','M7 10h2l4-7a3 3 0 0 1 3 3l-1 4h4.5a2 2 0 0 1 1.9 2.6l-2 7A2 2 0 0 1 17.5 21H7','M7 10H4a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h3'],
 };
 for(const d of (paths[kind]||[])) {
  const p=document.createElementNS('http://www.w3.org/2000/svg','path');p.setAttribute('d',d);
  svg.append(p);
 }
 if(kind==='thumb-down') {
   svg.style.transform='rotate(180deg)';
   for(const d of paths['thumb-up']) {
     const p=document.createElementNS('http://www.w3.org/2000/svg','path');p.setAttribute('d',d);svg.append(p);
   }
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
 return time+' · '+dayMonth;
}
function editorialLayout(index) {
 if(index===0)return 'story--feature';
 const p=(index-1)%8;
 return p===0 || p===5 ? 'story--wide' : p===1 || p===4 ? 'story--compact' : 'story--standard';
}

function render(){
 if(mode==='focus')focusArticles=personalizedFocus();
 const resetFeedback=$('#feedback-reset');
 resetFeedback.hidden=mode!=='focus'||!Object.keys(votes).length;
 document.body.dataset.pulseMode=mode;
 const personalHero=$('#focus-hero');
 personalHero.hidden=mode!=='focus';
 const heroStat=$('#focus-hero-stat');
 heroStat.textContent=mode==='focus' ? (focusArticles.length ? focusArticles.length+' головних матеріалів у добірці' : 'Добірка оновлюється') : '';
 $('#saved-count').textContent=Object.keys(saved).length;
 const q=$('#search').value.trim().toLocaleLowerCase('uk');
 const archiveCutoff = Date.now()/1000 - 7*86400;
 const list=(mode==='saved'?Object.values(saved):mode==='focus'?focusArticles:mode==='archive'?archiveArticles:articles)
   .filter(a=>(mode!=='archive'||!a.published||a.published<archiveCutoff||a.id===sharedArticleId)
      &&(!category||a.category===category)
      &&(!$('#source').value||a.source===$('#source').value||
         (a.related_sources||[]).some(r=>r.source===$('#source').value))
      &&(!$('#country').value||a.country===$('#country').value)
      &&(!$('#origin').value||a.origin===$('#origin').value||
         (a.related_sources||[]).some(r=>r.origin===$('#origin').value))
      &&(!q||[a.title,a.summary,a.publisher,a.country,
        ...(a.related_sources||[]).flatMap(r=>[r.title,r.publisher,r.source])]
        .join(' ').toLocaleLowerCase('uk').includes(q)))
   .sort((a,b)=>(b.published||0)-(a.published||0));
 // A shared article is surfaced first only while opening a deliberate deep link.
 if(sharedArticleId){
   const target=list.findIndex(a=>a.id===sharedArticleId);
   if(target>0)list.unshift(...list.splice(target,1));
 }
 const news=$('#news');
 news.replaceChildren();
 const viewportRows=new Map();
 const failed=sourceStatuses.filter(s=>!s.ok).map(s=>s.name+(s.cached?' (кеш)':''));
 const working=sourceStatuses.filter(s=>s.ok).length;
 $('#status').textContent=mode==='focus' ? list.length+' головних · '+briefArticles.length+' коротко' : mode==='all' ? list.length+' новин · '+archiveCount+' в архіві' : list.length+' матеріалів';
 const issues=$('#feed-issues'); issues.replaceChildren();
 if(!failed.length) issues.append(el('li','Усі джерела відповіли.'));
 else for(const name of failed) issues.append(el('li',name));
 $('#load-more').hidden=mode==='focus'||list.length<=visibleLimit;
 $('#load-more').textContent=`Показати ще ${Math.min(60,list.length-visibleLimit)} із ${list.length-visibleLimit} матеріалів`;
 if(!list.length && !(mode==='focus'&&briefArticles.length)) news.append(el('p',mode==='saved'?'Збережених новин немає. Додайте матеріал іконкою закладки або змініть фільтри.':articles.length||focusArticles.length?'Нічого не знайдено. Змініть пошук або фільтри.':'Джерела не повернули новин. Повторіть спробу пізніше.','empty'));
 for(const [index,a] of list.slice(0,visibleLimit).entries()){
  const layout=editorialLayout(index);
  const image=imagesEnabled&&(index===0||index%3===0||layout==='story--wide')?safePreviewImage(a.image_url):'';
  const topicTone={'Імміграція':'migration','AI':'ai','AI-події':'events','Світ':'world','Україна':'ukraine','Польща':'poland','Бізнес':'business','Технології':'tech','Наука':'science','Дизайн':'design','Кіно':'cinema','Мотивація':'motivation'};
  const tone=topicTone[a.category]||'neutral';
  const card=el('article',null,'story '+layout+' story--topic-'+tone+(image?' story--with-image':' story--no-image'));
  card.dataset.pulseArticleId=a.id;
  viewportRows.set(a.id,a);

  const translation=translationState[a.id]||{};
  const shown=translation.shown===true;
  const userSelectedOriginal=translation.shown===false;
  const shared=sharedTranslation(a);
  const autoTitle=autoEnabled&&!userSelectedOriginal?(shared?.title || translatedTitles[a.id]):'';
  const content=el('div',null,'story-content');
  const copy=el('div',null,'story-copy');
  const h=el('h2',null,'story-heading');
  h.append(link(userSelectedOriginal ? a.title : (shown&&translation.title)||autoTitle||a.title,a.url));
  const summary=el('p',userSelectedOriginal?a.summary:((shown&&translation.summary)||shared?.summary||a.summary),'story-summary');
  copy.append(h,summary);

  const lang=articleLanguage(a);
  const tButton=el('button',null,'translate-btn story-translate');
  tButton.type='button';
  tButton.disabled=Boolean(translation.loading)||lang==='uk';
  tButton.append(newsIcon('languages'));
  const label=lang==='uk'?'Вже українською':translation.loading?'Перекладаємо':shown||autoTitle?'Показати оригінал':'Перекласти українською';
  tButton.setAttribute('aria-label',label+': '+a.title);
  tButton.title=label;
  if(lang!=='uk')tButton.onclick=async()=>{
    if(translationState[a.id]?.shown ||
       ((shared || translatedTitles[a.id]) && translationState[a.id]?.shown!==false)){
      translationState[a.id]={...translationState[a.id],shown:false};render();return;
    }
    if(shared){
      translationState[a.id]={shown:true};render();return;
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
  if(translation.error)copy.append(el('span','Переклад недоступний','translation-error'));
  if(Array.isArray(a.related_sources) && a.related_sources.length) {
    const valid=a.related_sources.filter(r=>r.url && /^https:\/\//.test(r.url));
    if(valid.length) {
      const sources=el('details',null,'story-sources');
      const count=valid.length;
      const countLabel=count===1?'джерело':count<5?'джерела':'джерел';
      sources.append(el('summary','Ще '+count+' '+countLabel,'story-sources-toggle'));
      const list=el('ul',null,'story-source-links');
      for(const entry of valid) {
        const item=el('li');
        const name=entry.publisher||entry.source||'Джерело';
        const sourceLink=link(name+' · '+entry.title,entry.url);
        sourceLink.setAttribute('aria-label','Інше джерело: '+name+'. '+entry.title);
        item.append(sourceLink);list.append(item);
      }
      sources.append(list);copy.append(sources);
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
  const metadata=el('div',null,'story-meta');
  metadata.append(el('span',a.category||'Новини','story-tag story-tag--topic'));
  if(a.category==='Імміграція'&&a.migration_scope==='ukrainian')metadata.append(el('span','Для українців','migration-scope'));
  if(a.category==='Імміграція'&&a.migration_scope==='general')metadata.append(el('span','Загальні правила','migration-scope'));
  const publisher=el('span',a.publisher||a.source||'Джерело','story-publisher-bottom');
   publisher.title=a.publisher||a.source||'Джерело';
   metadata.append(publisher);
  const date=document.createElement('time');date.className='story-date';
  date.textContent=articleDate(a.published);
  if(a.published)date.dateTime=new Date(a.published*1000).toISOString();
  metadata.append(date);
  const tools=el('div',null,'story-tools');
  tools.append(tButton);
  const saver=el('button',null,'story-bookmark'+(saved[a.id]?' is-saved':''));
  saver.type='button';saver.append(newsIcon('bookmark'));
  saver.title=saved[a.id]?'Прибрати зі збереженого':'Зберегти статтю';
  saver.setAttribute('aria-label',(saved[a.id]?'Прибрати зі збереженого: ':'Зберегти статтю: ')+a.title);
  saver.setAttribute('aria-pressed',String(Boolean(saved[a.id])));
  saver.onclick=()=>{
    if(saved[a.id])delete saved[a.id];
    else saved[a.id]=a;
    persist();render();
  };
  tools.append(saver);
  // Sharing is invoked by holding anywhere on the card, not a toolbar icon.
  if(mode==='focus') {
    const reactions=el('div',null,'story-feedback');
    reactions.setAttribute('role','group');
    reactions.setAttribute('aria-label','Оцініть релевантність статті');
    for(const [value,label] of [[1,'Цікаво'],[-1,'Нецікаво']]) {
      const button=el('button',null,'story-feedback-button');
      button.type='button';button.append(newsIcon(value===1?'thumb-up':'thumb-down'));
      button.title=label;button.setAttribute('aria-label',label+': '+a.title);
      button.setAttribute('aria-pressed',String(votes[a.id]?.value===value));
      button.onclick=()=>voteOn(a,value);
      reactions.append(button);
    }
    tools.prepend(reactions);
  }
  bottom.append(metadata,tools);
  card.append(content,bottom);
  if(window.PulseShare)window.PulseShare.enableLongPress(card,a);
  news.append(card);
 }
 renderBrief();
 $('#focus-explainer').hidden=mode!=='focus';
 $('#focus-help').hidden=mode!=='focus'||$('#how-focus-works').getAttribute('aria-expanded')!=='true';
 translationStatus();
 watchVisibleHeadlines(viewportRows);
}

function renderBrief(){
 const section=$('#brief'), root=$('#brief-list');
 root.replaceChildren();
 if(mode!=='focus'){section.hidden=true;return;}
 const q=$('#search').value.trim().toLocaleLowerCase('uk');
 const filtered=briefArticles.filter(a=>
   (!category||a.category===category)&&
   (!$('#source').value||a.source===$('#source').value)&&
   (!$('#country').value||a.country===$('#country').value)&&
   (!$('#origin').value||a.origin===$('#origin').value)&&
   (!q||(a.title+' '+(a.summary||'')+' '+(a.publisher||'')).toLocaleLowerCase('uk').includes(q))
 );
 section.hidden=!filtered.length;
 for(const a of filtered){
   const row=el('div',null,'brief-item');
   const translation=translationState[a.id]||{};
   const shared=sharedTranslation(a);
   const currentTitle=translation.shown===false?a.title:(translation.shown&&translation.title)||shared?.title||translatedTitles[a.id]||a.title;
   const title=link(currentTitle,a.url);
   title.className='brief-title';
   const meta=el('div',null,'brief-meta');
   meta.append(el('span',a.category||'Новини','brief-topic'));
   meta.append(el('span',a.publisher||a.source||'Джерело','brief-publisher'));
   const stamp=document.createElement('time');
   stamp.textContent=articleDate(a.published);
   if(a.published)stamp.dateTime=new Date(a.published*1000).toISOString();
   meta.append(stamp);
   const tools=el('div',null,'brief-tools');
   const lang=articleLanguage(a);
   const translate=el('button',null,'brief-action brief-translate');
   translate.type='button';translate.append(newsIcon('languages'));
   translate.disabled=Boolean(translation.loading)||lang==='uk';
   translate.title=lang==='uk'?'Вже українською':translation.loading?'Перекладаємо':'Перекласти / показати оригінал';
   translate.setAttribute('aria-label',translate.title+': '+a.title);
   if(lang!=='uk')translate.onclick=async()=>{
     if(translationState[a.id]?.shown || ((shared||translatedTitles[a.id]) && translationState[a.id]?.shown!==false)){
       translationState[a.id]={...translationState[a.id],shown:false};render();return;
     }
     if(shared){translationState[a.id]={shown:true};render();return;}
     if(translationCache[a.id]){
       translationState[a.id]={...translationCache[a.id],shown:true};render();return;
     }
     translationState[a.id]={loading:true};render();
     try{
       const result=await translateArticlePreview(a);
       storeTranslation(a.id,result);
       translationState[a.id]={...result,shown:true};
     }catch{translationState[a.id]={error:true};}
     render();
   };
   const saver=el('button',null,'brief-action brief-save'+(saved[a.id]?' is-saved':''));
   saver.type='button';saver.append(newsIcon('bookmark'));
   saver.title=saved[a.id]?'Прибрати зі збереженого':'Зберегти статтю';
   saver.setAttribute('aria-label',saver.title+': '+a.title);
   saver.setAttribute('aria-pressed',String(Boolean(saved[a.id])));
   saver.onclick=()=>{
     if(saved[a.id])delete saved[a.id];
     else saved[a.id]=a;
     persist();render();
   };
   tools.append(translate,saver);
   row.append(title,meta,tools);
   if(window.PulseShare)window.PulseShare.enableLongPress(row,a);
   root.append(row);
 }
}
async function load(){
  $('#status').textContent='Завантажуємо новини з джерел…';
  try{
    const requestedMode = mode === 'archive' ? 'archive' : mode === 'focus' ? 'focus' : 'all';
    const feedUrl = requestedMode === 'archive' ? './news.json'
      : requestedMode === 'focus' ? './personal.json' : './feed.json';
    const r=await fetch(feedUrl,{cache:'no-store'});
    if(!r.ok)throw Error('HTTP '+r.status);
    const data=await r.json();
    if(requestedMode==='focus'){
      if(!Array.isArray(data.featured)||!Array.isArray(data.brief))throw Error('Incorrect personal feed');
      baseFocusArticles=data.featured;
      focusPool=Array.isArray(data.candidates)?data.candidates:[];
      focusArticles=personalizedFocus();briefArticles=data.brief;
    }else{
      if(!Array.isArray(data.articles))throw Error('Incorrect news feed');
      if(requestedMode==='archive'){
        archiveArticles=data.articles;
        archiveCount=data.articles.length;
      }else{
        articles=data.articles;
        archiveCount=Number.isFinite(data.archive_total)?data.archive_total:data.articles.length;
      }
    }
    // A friend following a Pulse link can still see a story from an older archive.
    if(sharedArticleId && requestedMode==='all' && !articles.some(a=>a.id===sharedArticleId)){
      mode='archive';
      for(const n of document.querySelectorAll('[data-mode]')){
        const active=n.dataset.mode==='archive';
        n.classList.toggle('active',active);
        n.setAttribute('aria-pressed',String(active));
      }
      window.dispatchEvent(new CustomEvent('pulse-mode',{detail:{mode}}));
      return await load();
    }
    sourceStatuses=Array.isArray(data.sources)?data.sources:[];
    updated=data.updated||0;
    const selected=$('#source').value;
    $('#source').replaceChildren(new Option('Усі джерела',''));
    for(const name of [...new Set([...sourceStatuses.map(s=>s.name),...Object.values(saved).map(a=>a.source)])].filter(Boolean).sort())
      $('#source').append(new Option(name,name));
    $('#source').value=selected;
    const previousCountry=$('#country').value;
    $('#country').replaceChildren(new Option('Усі країни',''));
    const current=requestedMode==='archive'?archiveArticles:requestedMode==='focus'?focusArticles.concat(briefArticles):articles;
    for(const name of [...new Set(current.map(a=>a.country).filter(Boolean))].sort())
      $('#country').append(new Option(name,name));
    $('#country').value=previousCountry;
    render();
    if(sharedArticleId&&!sharedScrolled){
      const target=document.querySelector('[data-pulse-article-id="'+sharedArticleId+'"]');
      if(target){sharedScrolled=true;requestAnimationFrame(()=>target.scrollIntoView({block:'center'}));}
    }
  }catch{render();$('#status').textContent='Не вдалося завантажити стрічку. Перевірте з’єднання та повторіть спробу.';}
  finally{/* The feed still refreshes automatically every five minutes. */}
}
function resetFilter(){visibleLimit=60;render();}
 $('#search').oninput=resetFilter;$('#source').onchange=resetFilter;$('#country').onchange=resetFilter;
 $('#origin').onchange=resetFilter;
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
 translationStatus();
for(const b of document.querySelectorAll('[data-mode]')){b.onclick=()=>{sharedArticleId=null;mode=b.dataset.mode;visibleLimit=60;for(const n of document.querySelectorAll('[data-mode]')){const active=n.dataset.mode===mode;n.classList.toggle('active',active);n.setAttribute('aria-pressed',String(active));}window.dispatchEvent(new CustomEvent('pulse-mode',{detail:{mode}}));if(mode==='all'&&!articles.length || mode==='archive'&&!archiveArticles.length || mode==='focus'&&!focusArticles.length)load();else render();};const active=b.dataset.mode===mode;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));}
for(const b of document.querySelectorAll('[data-category]')){b.onclick=()=>{category=b.dataset.category;visibleLimit=60;for(const n of document.querySelectorAll('[data-category]')){n.classList.toggle('active',n===b);n.setAttribute('aria-pressed',String(n===b));}render();};b.setAttribute('aria-pressed',String(b.classList.contains('active')));}
$('#how-focus-works').onclick=()=>{const b=$('#how-focus-works');const expanded=b.getAttribute('aria-expanded')==='true';$('#focus-help').hidden=expanded;b.setAttribute('aria-expanded',String(!expanded));};
$('#feedback-reset').onclick=()=>{votes={};saveFeedback();focusArticles=personalizedFocus();render();};
void loadSharedTranslations();
load();setInterval(load,300000);



/* Pulse Reddit preview: only practical AI discussions, no inferred summaries.
   Reddit is optional: show subreddit shortcuts when RSS is unavailable. */
(() => {
  const section=document.querySelector('#reddit-preview');
  const root=document.querySelector('#reddit-preview-list');
  if(!section||!root)return;
  const allowedCommunities=new Set([
    'LocalLLaMA','ClaudeAI','ChatGPT','vibecoding','FigmaDesign','UXDesign','selfhosted'
  ]);
  const topics=new Set(['Розробка','Дизайн','Адміністрування','AI у роботі']);
  const safeRedditUrl=(raw,community)=>{
    try{
      const url=new URL(raw);
      return url.origin==='https://www.reddit.com' &&
        new RegExp('^/r/'+community+'/comments/[a-z0-9]+(?:/|$)','i').test(url.pathname) &&
        !url.username&&!url.password ? url.href : '';
    }catch{return '';}
  };
  const node=(tag,cls,value)=>{
    const n=document.createElement(tag);
    n.className=cls;n.textContent=value;
    return n;
  };
  const shortcuts=()=>{
    const suggestions=[
      ['ClaudeAI','Практика з Claude і Claude Code'],
      ['vibecoding','Створення застосунків з AI'],
      ['FigmaDesign','AI у дизайні'],
      ['selfhosted','Автоматизація та сервери']
    ];
    for(const [community,label] of suggestions){
      const card=node('article','reddit-preview-item','');
      const name=node('a','reddit-preview-title',label);
      name.href='https://www.reddit.com/r/'+community+'/new/';
      name.target='_blank';name.rel='noopener noreferrer';
      card.append(name,node('span','reddit-preview-source','r/'+community));
      root.append(card);
    }
    section.hidden=false;
  };
  async function loadPreview(){
    try{
      const response=await fetch('./reddit.json',{cache:'no-store'});
      if(!response.ok)throw Error('Reddit data failed');
      const data=await response.json();
      if(!['ok','cached'].includes(data.status)||!Array.isArray(data.posts)){
        shortcuts();return;
      }
      const recent=data.posts.filter(p=>p&&
        allowedCommunities.has(p.community)&&topics.has(p.work_topic)&&
        Number.isFinite(p.work_score)&&p.work_score>=3&&
        typeof p.title==='string'&&p.title.length>9&&
        Number.isFinite(p.published)&&safeRedditUrl(p.url,p.community)
      ).sort((a,b)=>b.work_score-a.work_score||b.published-a.published);
      const chosen=[],seen=new Set();
      for(const post of recent){
        if(chosen.length===4)break;
        const key=post.title.trim().toLowerCase();
        if(seen.has(key))continue;
        seen.add(key);chosen.push(post);
      }
      if(!chosen.length){shortcuts();return;}
      for(const p of chosen){
        const card=node('article','reddit-preview-item','');
        const subject=node('span','reddit-preview-topic',p.work_topic);
        const title=node('a','reddit-preview-title',p.title);
        title.href=safeRedditUrl(p.url,p.community);
        title.target='_blank';title.rel='noopener noreferrer';
        card.append(subject,title,node('span','reddit-preview-source','r/'+p.community));
        root.append(card);
      }
      section.hidden=false;
    }catch{shortcuts();}
  }
  loadPreview();
})();
