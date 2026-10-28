'use strict';
/* Pulse v29: client-only read history, radar, collections, daily digest & search. */
window.PulseHub=(()=>{
 const KEY={read:'pulse-read-v1',radar:'pulse-radar-v1',collections:'pulse-collections-v1',saved:'pulse-saved'};
 const get=(key,otherwise)=>{try{return JSON.parse(localStorage.getItem(key))??otherwise;}catch{return otherwise;}};
 const put=(key,data)=>{try{localStorage.setItem(key,JSON.stringify(data));return true;}catch{return false;}};
 const make=(tag,cls,value)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(value!==undefined)n.textContent=value;return n;};
 const validId=id=>typeof id==='string'&&/^[a-f0-9]{20}$/.test(id);
 const lower=s=>String(s||'').toLocaleLowerCase('uk');
 function readMap(){const x=get(KEY.read,{});return x&&typeof x==='object'&&!Array.isArray(x)?x:{};}
 function isRead(id){return Boolean(readMap()[id]);}
 function markRead(id){
   if(!validId(id))return;
   const all=readMap();all[id]=Date.now();
   put(KEY.read,Object.fromEntries(Object.entries(all).filter(([key,v])=>validId(key)&&Number.isFinite(v))
      .sort((a,b)=>b[1]-a[1]).slice(0,3000)));
   document.querySelectorAll('[data-pulse-article-id]').forEach(card=>{
     if(card.dataset.pulseArticleId===id)card.classList.add('pulse-is-read');
   });
 }
 function radar(){const x=get(KEY.radar,[]);return Array.isArray(x)?x.filter(s=>typeof s==='string'&&s.length>=2&&s.length<=45).slice(0,25):[];}
 function addRadar(term){
   term=String(term||'').trim().replace(/\s+/g,' ').slice(0,45);const all=radar();
   if(term.length<2||all.length>=25||all.some(x=>lower(x)===lower(term)))return false;
   return put(KEY.radar,[...all,term]);
 }
 function removeRadar(term){put(KEY.radar,radar().filter(t=>t!==term));}
 function saved(){const v=get(KEY.saved,{});return v&&typeof v==='object'&&!Array.isArray(v)?v:{};}
 function folders(){
   const v=get(KEY.collections,{names:['Прочитати пізніше','Бізнес-ідеї','AI-інструменти'],assign:{},notes:{}});
   return {names:Array.isArray(v.names)?v.names.filter(x=>typeof x==='string'&&x.length<=45).slice(0,30):[],
      assign:v.assign&&typeof v.assign==='object'?v.assign:{},
      notes:v.notes&&typeof v.notes==='object'?v.notes:{}};
 }
 function matchesRadar(article,words=radar()){
   const text=lower([article.title,article.summary,article.category,article.publisher].join(' '));
   return words.some(w=>text.includes(lower(w)));
 }
 function searchTerms(query){
   const yes=[],no=[];
   for(let part of (String(query||'').match(/-?"[^"]+"|-?\S+/g)||[]).slice(0,20)){
     const negative=part.startsWith('-');if(negative)part=part.slice(1);
     const term=lower(part.replace(/^"|"$/g,'').trim());
     if(term)(negative?no:yes).push(term);
   }
   return {yes,no};
 }
 function matchesQuery(article,query,translated=''){
   const {yes,no}=searchTerms(query);
   const hay=lower([article.title,article.summary,article.category,article.publisher,article.source,article.country,translated,
     ...(article.related_sources||[]).flatMap(x=>[x.title,x.publisher])].join(' '));
   return yes.every(term=>hay.includes(term))&&!no.some(term=>hay.includes(term));
 }
 async function fetchJson(name,fallback){
   try{const r=await fetch('./'+name,{cache:'no-store'});if(!r.ok)throw Error(name);return await r.json();}
   catch{return fallback;}
 }
 function safeUrl(url){try{const x=new URL(url);return x.protocol==='https:'&&!x.username&&!x.password?x.href:'';}catch{return '';}}
 function titleFor(a,cache){const t=cache[a.id];return t&&t.source_title===a.title?t:null;}
 async function loadTranslations(){
   const data=await fetchJson('translations.json',{articles:{}});
   return data?.articles&&typeof data.articles==='object'&&!Array.isArray(data.articles)?data.articles:{};
 }
 async function loadIndex(){
   const [archive,founders,translations]=await Promise.all([
     fetchJson('news.json',{articles:[]}),fetchJson('motivation.json',{articles:[]}),loadTranslations()]);
   const index=new Map();
   for(const a of [...(archive.articles||[]),...(founders.articles||[]),...Object.values(saved())]){
     if(!a?.id||!safeUrl(a.url))continue;
     if(!index.has(a.url))index.set(a.url,a);
   }
   return {items:[...index.values()].sort((a,b)=>(b.published||0)-(a.published||0)),translations};
 }
 function result(a,translations){
   const card=make('article','hub-result'+(isRead(a.id)?' pulse-is-read':''));
   const meta=make('div','hub-result-meta',[a.category,a.publisher||a.source,a.published?
     new Date(a.published*1000).toLocaleDateString('uk-UA',{day:'numeric',month:'short'}):''].filter(Boolean).join(' · '));
   const tr=titleFor(a,translations||{});
   const link=make('a','hub-result-title',tr?.title||a.title||'Новина');link.href=safeUrl(a.url)||'#';
   link.target='_blank';link.rel='noopener noreferrer';link.onclick=()=>markRead(a.id);
   card.append(meta,link);
   const text=tr?.summary||a.summary||'';
   if(text)card.append(make('p','hub-result-excerpt',String(text).replace(/\s+/g,' ').slice(0,280)));
   return card;
 }
 function installHome(){
   const toolbar=document.querySelector('.toolbar');if(!toolbar)return;
   const el=make('div','hub-home-toolbar');el.id='hub-home-toolbar';
   const unread=make('button','hub-chip','Непрочитані');unread.type='button';unread.id='hub-unread-filter';unread.setAttribute('aria-pressed','false');
   for(const [label,href] of [['Мій день','today.html'],['Радар','radar.html'],['Колекції','collections.html']]){
     const a=make('a','hub-chip',label);a.href='./'+href;el.append(a);
   }
   el.insertBefore(unread,el.children[1]||null);toolbar.after(el);
 }
 function installReadTracking(){
   document.addEventListener('click',event=>{
     const anchor=event.target?.closest?.('a[href]');
     const card=anchor?.closest?.('[data-pulse-article-id]');
     if(card&&!anchor.getAttribute('href').startsWith('#'))markRead(card.dataset.pulseArticleId);
   },true);
 }
 async function today(){
   const root=document.querySelector('#hub-main');if(!root)return;
   const [digest,feed,eventData,translations]=await Promise.all([
     fetchJson('digest.json',{sections:[]}),fetchJson('feed.json',{articles:[]}),
     fetchJson('events.json',{events:[]}),loadTranslations()]);
   const now=Date.now()/1000,latest=(feed.articles||[]).filter(a=>a.published>now-86400&&a.published<now+300);
   const radarResults=latest.filter(a=>matchesRadar(a)),items=new Map();
   const sections=(digest.sections||[]).filter(s=>Array.isArray(s.items));
   for(let i=0;i<10;i++)for(const section of sections){
     const a=section.items[i];if(a&&items.size<10&&!items.has(a.url))items.set(a.url,{...a,category:section.category});
   }
   const brief=[...items.values()];
   const hero=make('section','hub-hero');
   hero.append(make('p','hub-kicker','PULSE · МІЙ ДЕНЬ'),make('h1','','Доброго дня.'),
     make('p','hub-muted','Коротко про важливе за 24 години, без безкінечної стрічки.'));
   const metrics=make('div','hub-metrics');
   for(const [n,label] of [[brief.length,'Головних'],[radarResults.length,'За темами'],[latest.filter(a=>!isRead(a.id)).length,'Непрочитаних']]){
     const m=make('div','hub-metric');m.append(make('strong','',String(n)),make('span','',label));metrics.append(m);
   }
   hero.append(metrics);root.append(hero);
   root.append(make('h2','hub-section-heading','Головне за день'),
     make('p','hub-muted','Автоматичний відбір реальних публікацій із RSS-описами та посиланнями. Це не AI-переказ і не фактчекінг.'));
   const feedRoot=make('div','hub-results');for(const a of brief)feedRoot.append(result(a,translations));
   if(!brief.length)feedRoot.append(make('p','hub-empty','Нових матеріалів у щоденній добірці поки немає.'));
   root.append(feedRoot);
   const section=make('section','hub-section');
   section.append(make('h2','hub-section-heading','Мій радар'),
     make('p','hub-muted',radar().length?'Твої ключові слова: '+radar().join(', '):'Додай ключові слова, щоб знаходити важливі публікації.'));
   const matches=make('div','hub-results');for(const a of radarResults.slice(0,5))matches.append(result(a,translations));
   if(!radarResults.length)matches.append(make('p','hub-empty','Свіжих збігів поки немає.'));
   section.append(matches);
   const link=make('a','hub-text-link','Налаштувати радар');link.href='./radar.html';section.append(link);root.append(section);
   const future=(Array.isArray(eventData.events)?eventData.events:[]).filter(e=>{
     const when=Date.parse(e.start||e.start_date||e.date||'');
     return Number.isFinite(when)&&when>=Date.now()&&when<Date.now()+14*86400000;
   }).slice(0,4);
   const next=make('section','hub-section');next.append(make('h2','hub-section-heading','Найближчі події'));
   if(!future.length)next.append(make('p','hub-empty','Наразі немає знайдених подій на найближчі два тижні.'));
   for(const e of future){
     const row=make('p','hub-event');
     const url=safeUrl(e.url||e.link);
     if(url){const a=make('a','',e.title||e.name||'Подія');a.href=url;a.target='_blank';a.rel='noopener noreferrer';row.append(a);}
     else row.textContent=e.title||e.name||'Подія';
     next.append(row);
   }
   root.append(next);
 }
 async function radarPage(){
   const root=document.querySelector('#hub-main');if(!root)return;
   root.append(make('p','hub-muted','Слідкуй за своїми ключовими словами в новинах та архіві. Усе зберігається лише у браузері.'));
   const form=make('form','hub-form'),input=make('input','hub-input');input.placeholder='Наприклад: CUKR, Figma, Claude';input.maxLength=45;input.required=true;
   const button=make('button','hub-primary','Додати');button.type='submit';form.append(input,button);
   const chips=make('div','hub-radar-tags'),status=make('p','hub-muted'),out=make('div','hub-results');
   root.append(form,chips,status,out);
   const {items,translations}=await loadIndex();
   function render(){
     chips.replaceChildren();
     for(const term of radar()){const b=make('button','hub-topic',term+' ×');b.type='button';b.title='Прибрати '+term;b.onclick=()=>{removeRadar(term);render();};chips.append(b);}
     const found=radar().length?items.filter(a=>matchesRadar(a)):[];
     status.textContent='Збігів: '+found.length+'. Показано до 70.';
     out.replaceChildren();
     for(const a of found.slice(0,70))out.append(result(a,translations));
     if(!found.length)out.append(make('p','hub-empty','Збережи тему, щоб побачити відповідні статті.'));
   }
   form.onsubmit=e=>{e.preventDefault();if(addRadar(input.value))input.value='';render();};
   render();
 }
 async function searchPage(){
   const root=document.querySelector('#hub-main');if(!root)return;
   const form=make('form','hub-form'),input=make('input','hub-input');
   input.type='search';input.placeholder='Пошук по всьому Pulse…';input.value=new URLSearchParams(location.search).get('q')||'';
   const submit=make('button','hub-primary','Знайти');submit.type='submit';form.append(input,submit);
   const options=make('div','hub-search-settings'),topic=make('select','hub-select'),range=make('select','hub-select'),source=make('select','hub-select');
   for(const [value,label] of [['','Усі теми'],['Імміграція','Імміграція'],['AI','AI'],['Мотивація','Мотивація'],['Бізнес','Бізнес'],['Польща','Польща'],['Світ','Світ']]){
     const opt=make('option','',label);opt.value=value;topic.append(opt);
   }
   for(const [value,label] of [['0','Увесь архів'],['7','За 7 днів'],['30','За місяць'],['90','За 3 місяці']]){
     const opt=make('option','',label);opt.value=value;range.append(opt);
   }
   const unread=make('label','hub-checkbox'),onlyUnread=make('input');onlyUnread.type='checkbox';
   unread.append(onlyUnread,make('span','','Лише непрочитані'));options.append(topic,range,source,unread);
   const status=make('p','hub-muted','Завантажуємо архів…'),out=make('div','hub-results');
   root.append(form,options,make('p','hub-muted','Візьми точну фразу у лапки; додай -слово, щоб виключити його. Пошук включає архів, мотивацію та збережене.'),status,out);
   const {items,translations}=await loadIndex();
   const anySource=make('option','','Усі джерела');anySource.value='';source.append(anySource);
   for(const value of [...new Set(items.map(a=>a.publisher||a.source).filter(Boolean))].sort()){
     const opt=make('option','',value);opt.value=value;source.append(opt);
   }
   function render(){
     const now=Date.now()/1000,days=Number(range.value),query=input.value.trim();
     const matched=items.filter(a=>(!topic.value||a.category===topic.value)
       &&(!source.value||a.publisher===source.value||a.source===source.value)
       &&(!days||a.published>=now-days*86400)
       &&(!onlyUnread.checked||!isRead(a.id))
       &&matchesQuery(a,query,[titleFor(a,translations)?.title,titleFor(a,translations)?.summary].join(' ')));
     status.textContent='Знайдено '+matched.length+' · показано '+Math.min(80,matched.length);
     out.replaceChildren();for(const a of matched.slice(0,80))out.append(result(a,translations));
     if(!matched.length)out.append(make('p','hub-empty','Нічого не знайдено. Зміни фразу або фільтри.'));
   }
   form.onsubmit=e=>{e.preventDefault();history.replaceState(null,'','?q='+encodeURIComponent(input.value.trim()));render();};
   input.oninput=render;topic.onchange=render;source.onchange=render;range.onchange=render;onlyUnread.onchange=render;render();
 }
 function collectionsPage(){
   const root=document.querySelector('#hub-main');if(!root)return;
   root.append(make('p','hub-muted','Збережені статті, папки та нотатки залишаються на цьому пристрої. Перед очищенням Safari експортуй копію.'));
   const form=make('form','hub-form'),input=make('input','hub-input');
   input.placeholder='Нова колекція';input.maxLength=45;const create=make('button','hub-primary','Створити');create.type='submit';form.append(input,create);
   const exportButton=make('button','hub-chip','Експортувати JSON');exportButton.type='button';
   const selectFolder=make('select','hub-select');selectFolder.setAttribute('aria-label','Фільтр за колекцією');
   const status=make('p','hub-muted'),out=make('div','hub-results');root.append(form,selectFolder,exportButton,status,out);
   function render(){
     const data=folders(),articles=Object.values(saved()).filter(a=>a?.id&&a.url);
     const selected=selectFolder.value;
     selectFolder.replaceChildren();
     for(const [value,label] of [['','Усі колекції'],['__unassigned','Без колекції'],...data.names.map(x=>[x,x])]){
       const item=make('option','',label);item.value=value;selectFolder.append(item);
     }
     selectFolder.value=selected;
     status.textContent=articles.length+' збережених · '+data.names.length+' колекцій';
     out.replaceChildren();if(!articles.length)out.append(make('p','hub-empty','Збережи статтю закладкою в основній стрічці.'));
     for(const a of articles.sort((a,b)=>(b.published||0)-(a.published||0))){
       if(selectFolder.value==='__unassigned'&&data.assign[a.id])continue;
       if(selectFolder.value&&selectFolder.value!=='__unassigned'&&data.assign[a.id]!==selectFolder.value)continue;
       const card=result(a,{}),actions=make('div','hub-collection-actions'),select=make('select','hub-select');
       const base=make('option','','Без колекції');base.value='';select.append(base);
       for(const name of data.names){const opt=make('option','',name);opt.value=name;select.append(opt);}
       select.value=data.assign[a.id]||'';
       select.onchange=()=>{const d=folders();d.assign[a.id]=select.value;put(KEY.collections,d);if(selectFolder.value)render();};
       const note=make('textarea','hub-note');note.placeholder='Твоя нотатка…';note.maxLength=900;note.rows=2;note.value=data.notes[a.id]||'';
       note.onchange=()=>{const d=folders();d.notes[a.id]=note.value;put(KEY.collections,d);};
       actions.append(select,note);card.append(actions);out.append(card);
     }
   }
   form.onsubmit=e=>{e.preventDefault();const name=input.value.trim().slice(0,45),data=folders();
     if(name&&data.names.length<30&&!data.names.some(x=>lower(x)===lower(name))){
       data.names.push(name);put(KEY.collections,data);input.value='';render();
     }
   };
   selectFolder.onchange=render;
   exportButton.onclick=()=>{
     const data={exported:new Date().toISOString(),saved:saved(),collections:folders()};
     const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});
     const url=URL.createObjectURL(blob),a=make('a');a.href=url;a.download='pulse-collections.json';a.click();
     setTimeout(()=>URL.revokeObjectURL(url),2000);
   };
   render();
 }
 installReadTracking();
 document.addEventListener('DOMContentLoaded',()=>{
   installHome();
   const page=document.body.dataset.hubPage;
   if(page==='today')today();
   if(page==='radar')radarPage();
   if(page==='search')searchPage();
   if(page==='collections')collectionsPage();
 });
 return {isRead,markRead,readMap,radar,matchesRadar,matchesQuery,searchTerms,folders,saved};
})();
