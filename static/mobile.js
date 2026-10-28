'use strict';
/* Pulse mobile dock v20: menus expand in place, search is never a separate page. */
(() => {
  const home = location.pathname.endsWith('/') || location.pathname.endsWith('/index.html');
  const icons = {
    news:'<path d="M4 5h16M4 10h16M4 15h11M4 20h11"/>',
    focus:'<circle cx="12" cy="12" r="8"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
    search:'<circle cx="10.7" cy="10.7" r="6.7"/><path d="m16 16 5 5"/>',
    save:'<path d="M6 4h12v17l-6-4-6 4z"/>',
    menu:'<rect x="4" y="4" width="6" height="6"/><rect x="14" y="4" width="6" height="6"/><rect x="4" y="14" width="6" height="6"/><rect x="14" y="14" width="6" height="6"/>',
    up:'<path d="m5 14 7-7 7 7M12 7v14"/>'
  };
  const icon = key => '<svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+icons[key]+'</svg>';
  const dock=document.createElement('nav');
  dock.className='pulse-dock';
  dock.setAttribute('aria-label','Головне меню Pulse');
  const entries=[
    {key:'news',label:'Стрічка',mode:'all',href:'./'},
    {key:'focus',label:'Для мене',mode:'focus',href:'./?mode=focus'},
    {key:'search',label:'Пошук',mode:'search'},
    {key:'save',label:'Збережене',mode:'saved',href:'./?mode=saved'},
    {key:'menu',label:'Меню',mode:'menu'}
  ];
  const buttons=new Map();
  for(const item of entries) {
    const control=['menu','search'].includes(item.mode)?document.createElement('button'):document.createElement('a');
    control.className='pulse-dock-item';
    control.dataset.dock=item.mode;
    if(control.tagName==='A')control.href=item.href;
    else control.type='button';
    control.innerHTML=icon(item.key)+'<span>'+item.label+'</span>';
    dock.append(control);
    buttons.set(item.mode,control);
  }
  const sheet=document.createElement('div');
  sheet.className='pulse-dock-sheet';
  sheet.id='pulse-dock-sheet';
  sheet.hidden=true;
  sheet.innerHTML='<a href="./#events-section">Календар подій</a>'+
    '<a href="./digest.html">Огляд дня</a>'+
    '<a href="./opportunities.html">Імміграційні можливості</a>'+
    '<a href="./reddit.html">Обговорення Reddit</a>'+
    '<a href="./motivation.html">Мотивація · історії підприємців</a>'+
    '<a href="./?mode=archive">Весь архів</a>';

  // This panel belongs to the bottom navigation and searches the existing
  // static editorial feed, even when opened from a different Pulse section.
  const backdrop=document.createElement('div');
  backdrop.className='pulse-dock-backdrop';
  backdrop.hidden=true;
  const searchPanel=document.createElement('section');
  searchPanel.className='pulse-dock-search';
  searchPanel.id='pulse-dock-search';
  searchPanel.hidden=true;
  searchPanel.setAttribute('role','dialog');
  searchPanel.setAttribute('aria-modal','true');
  searchPanel.setAttribute('aria-label','Пошук у Pulse');
  searchPanel.innerHTML=
    '<div class="pulse-dock-search-top"><strong>Пошук у Pulse</strong>'+
    '<button class="pulse-dock-search-close" type="button" aria-label="Закрити пошук">×</button></div>'+
    '<label class="pulse-dock-search-field" for="pulse-dock-search-input">'+
    icon('search')+
    '<input id="pulse-dock-search-input" type="search" autocomplete="off" enterkeyhint="search" placeholder="Тема, новина або джерело" aria-label="Пошук у Pulse"></label>'+
    '<div id="pulse-dock-search-results" class="pulse-dock-search-results" aria-live="polite"></div>';
  document.body.append(backdrop,searchPanel,sheet,dock);
  const searchInput=searchPanel.querySelector('#pulse-dock-search-input');
  const searchResults=searchPanel.querySelector('#pulse-dock-search-results');
  const searchButton=buttons.get('search');
  const menu=buttons.get('menu');
  menu.setAttribute('aria-controls',sheet.id);
  menu.setAttribute('aria-expanded','false');
  searchButton.setAttribute('aria-controls',searchPanel.id);
  searchButton.setAttribute('aria-expanded','false');
  let primaryMode=home?'all':'menu';
  let library=null;
  let libraryPromise=null;
  let previousOverflow='';
  function selected(mode) {
    if(!['search','menu'].includes(mode))primaryMode=mode;
    buttons.forEach((button,key)=>{
      const current=key===mode;
      button.classList.toggle('is-active',current);
      if(current && !['search','menu'].includes(key))button.setAttribute('aria-current','page');
      else button.removeAttribute('aria-current');
    });
  }
  function closeSheet() {
    sheet.hidden=true;
    menu.setAttribute('aria-expanded','false');
    if(searchPanel.hidden)selected(primaryMode);
  }
  function closeSearch() {
    if(searchPanel.hidden)return;
    searchPanel.hidden=true;
    backdrop.hidden=true;
    searchButton.setAttribute('aria-expanded','false');
    document.body.classList.remove('pulse-search-open');
    document.body.style.overflow=previousOverflow;
    selected(primaryMode);
  }
  const normalize=value=>String(value||'').toLocaleLowerCase('uk').trim();
  function safeArticleLink(url) {
    try {
      const parsed=new URL(url,location.href);
      return parsed.protocol==='https:' && !parsed.username && !parsed.password ? parsed.href : '';
    }catch {return '';}
  }
  function empty(message) {
    const p=document.createElement('p');
    p.className='pulse-dock-search-hint';
    p.textContent=message;
    searchResults.replaceChildren(p);
  }
  function renderSearch() {
    if(!library) {
      empty('Завантажуємо стрічку для пошуку…');
      return;
    }
    const query=normalize(searchInput.value);
    if(!query) {
      const hint=document.createElement('p');
      hint.className='pulse-dock-search-hint';
      hint.textContent='Знайди потрібне, не виходячи з поточного екрана.';
      const quick=document.createElement('div');
      quick.className='pulse-dock-search-quick';
      for(const term of ['Імміграція','AI','Польща','Дизайн']) {
        const chip=document.createElement('button');
        chip.type='button';chip.textContent=term;
        chip.onclick=()=>{searchInput.value=term;renderSearch();searchInput.focus();};
        quick.append(chip);
      }
      searchResults.replaceChildren(hint,quick);
      return;
    }
    const words=query.split(/\s+/).filter(Boolean);
    const results=[];
    let total=0;
    for(const item of library) {
      const haystack=normalize([
        item.title,item.summary,item.category,item.publisher,item.source,item.country,
        ...(item.related_sources||[]).flatMap(source=>[source.title,source.publisher,source.source])
      ].join(' '));
      if(words.every(word=>haystack.includes(word))) {
        total++;
        if(results.length<15)results.push(item);
      }
    }
    const summary=document.createElement('p');
    summary.className='pulse-dock-search-count';
    summary.textContent=total?('Знайдено '+total+' · показано '+Math.min(total,15)):'Нічого не знайдено';
    searchResults.replaceChildren(summary);
    for(const item of results) {
      const href=safeArticleLink(item.url);
      if(!href)continue;
      const row=document.createElement('a');
      row.className='pulse-dock-search-result';
      row.href=href;row.target='_blank';row.rel='noopener noreferrer';
      const topic=document.createElement('span');
      topic.className='pulse-dock-search-result-topic';
      topic.textContent=item.category||'Стаття';
      const title=document.createElement('strong');
      title.textContent=item.title||'Без заголовка';
      const source=document.createElement('span');
      source.className='pulse-dock-search-result-source';
      source.textContent=item.publisher||item.source||'Джерело';
      row.append(topic,title,source);
      searchResults.append(row);
    }
  }
  async function loadSearch() {
    if(library)return library;
    if(!libraryPromise) {
      libraryPromise=fetch('./feed.json',{cache:'no-store'}).then(async response=>{
        if(!response.ok)throw Error('Feed unavailable');
        const data=await response.json();
        if(!Array.isArray(data.articles))throw Error('Unexpected feed');
        library=data.articles;
        return library;
      }).catch(error=>{libraryPromise=null;throw error;});
    }
    return libraryPromise;
  }
  async function openSearch() {
    closeSheet();
    previousOverflow=document.body.style.overflow;
    searchPanel.hidden=false;
    backdrop.hidden=false;
    searchButton.setAttribute('aria-expanded','true');
    selected('search');
    document.body.classList.add('pulse-search-open');
    document.body.style.overflow='hidden';
    renderSearch();
    searchInput.focus({preventScroll:true});
    try {await loadSearch();if(!searchPanel.hidden)renderSearch();}
    catch {if(!searchPanel.hidden)empty('Пошук тимчасово недоступний. Перевір з’єднання і відкрий пошук ще раз.');}
  }
  menu.addEventListener('click',()=>{
    closeSearch();
    sheet.hidden=!sheet.hidden;
    menu.setAttribute('aria-expanded',String(!sheet.hidden));
    selected(sheet.hidden?primaryMode:'menu');
  });
  searchButton.addEventListener('click',()=>{
    if(searchPanel.hidden)openSearch();
    else closeSearch();
  });
  searchPanel.querySelector('.pulse-dock-search-close').addEventListener('click',closeSearch);
  searchInput.addEventListener('input',renderSearch);
  backdrop.addEventListener('click',closeSearch);
  document.addEventListener('keydown',event=>{
    if(event.key==='Escape') {
      if(!searchPanel.hidden)closeSearch();
      else closeSheet();
    }
  });
  document.addEventListener('pointerdown',event=>{
    if(!sheet.hidden&&!sheet.contains(event.target)&&!menu.contains(event.target))closeSheet();
  });

  if(home) {
    const initial=new URLSearchParams(location.search).get('mode');
    selected(['all','focus','saved','archive'].includes(initial)?initial:'all');
    for(const item of entries) {
      if(['all','focus','saved'].includes(item.mode)) {
        buttons.get(item.mode).addEventListener('click',event=>{
          event.preventDefault();closeSheet();closeSearch();
          const control=document.querySelector('aside [data-mode="'+item.mode+'"]');
          if(control)control.click();
          selected(item.mode);
          // "For me" is a distinct section with its own hero, not a jump into
          // the middle of the home page.
          window.scrollTo({top:0,behavior:'smooth'});
        });
      }
    }
    window.addEventListener('pulse-mode',event=>{
      closeSheet();
      closeSearch();
      selected(event.detail.mode);
    });
    if(new URLSearchParams(location.search).has('search')) {
      openSearch();
    }
  } else {
    selected('menu');
  }

  const up=document.createElement('button');
  up.type='button';
  up.className='pulse-up';
  up.setAttribute('aria-label','Повернутися вгору');
  up.title='Повернутися вгору';
  up.innerHTML=icon('up');
  up.hidden=true;
  document.body.append(up);
  up.addEventListener('click',()=>window.scrollTo({top:0,behavior:'smooth'}));
  const sync=()=>{up.hidden=window.scrollY<Math.max(550,window.innerHeight*.7);};
  window.addEventListener('scroll',sync,{passive:true});
  sync();
})();
