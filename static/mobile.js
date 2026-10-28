'use strict';
/* Pulse phone navigation: installable website, no app store or external service. */
(() => {
  const home = location.pathname.endsWith('/') || location.pathname.endsWith('/index.html');
  const icons = {
    news:'<path d="M4 5h16M4 10h16M4 15h11M4 20h11"/>',
    focus:'<circle cx="12" cy="12" r="8"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
    search:'<circle cx="10.7" cy="10.7" r="6.7"/><path d="m16 16 5 5"/>',
    save:'<path d="M6 4h12v17l-6-4-6 4z"/>',
    menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
    up:'<path d="m5 14 7-7 7 7M12 7v14"/>'
  };
  const icon = key => '<svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+icons[key]+'</svg>';
  const dock=document.createElement('nav');
  dock.className='pulse-dock';
  dock.setAttribute('aria-label','Головне меню Pulse');
  const entries=[
    {key:'news',label:'Стрічка',mode:'all',href:'./'},
    {key:'focus',label:'Для мене',mode:'focus',href:'./?mode=focus'},
    {key:'search',label:'Пошук',mode:'search',href:'./?search=1'},
    {key:'save',label:'Збережене',mode:'saved',href:'./?mode=saved'},
    {key:'menu',label:'Меню',mode:'menu'}
  ];
  const buttons=new Map();
  for(const item of entries){
    const control=item.mode==='menu'?document.createElement('button'):document.createElement('a');
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
    '<a href="./?mode=archive">Весь архів</a>';
  document.body.append(sheet,dock);
  const menu=buttons.get('menu');
  menu.setAttribute('aria-controls',sheet.id);
  menu.setAttribute('aria-expanded','false');
  function closeSheet(){
    sheet.hidden=true;menu.setAttribute('aria-expanded','false');
  }
  menu.addEventListener('click',()=>{
    sheet.hidden=!sheet.hidden;
    menu.setAttribute('aria-expanded',String(!sheet.hidden));
  });
  document.addEventListener('keydown',e=>{if(e.key==='Escape')closeSheet();});
  document.addEventListener('pointerdown',e=>{
    if(!sheet.hidden&&!sheet.contains(e.target)&&!menu.contains(e.target))closeSheet();
  });
  function selected(mode){
    buttons.forEach((button,key)=>{
      const current=key===mode;
      button.classList.toggle('is-active',current);
      if(current)button.setAttribute('aria-current','page');
      else button.removeAttribute('aria-current');
    });
  }
  if(home){
    const initial=new URLSearchParams(location.search).get('mode');
    selected(['all','focus','saved','archive'].includes(initial)?initial:'all');
    for(const item of entries){
      if(['all','focus','saved'].includes(item.mode)){
        buttons.get(item.mode).addEventListener('click',e=>{
          e.preventDefault();closeSheet();
          const control=document.querySelector('aside [data-mode="'+item.mode+'"]');
          if(control)control.click();
          selected(item.mode);
          if(item.mode==='all')window.scrollTo({top:0,behavior:'smooth'});
          else document.querySelector('#news')?.scrollIntoView({behavior:'smooth',block:'start'});
        });
      }
    }
    buttons.get('search').addEventListener('click',e=>{
      e.preventDefault();closeSheet();
      const input=document.querySelector('#search');
      input?.scrollIntoView({behavior:'smooth',block:'center'});
      input?.focus({preventScroll:true});
    });
    window.addEventListener('pulse-mode',e=>selected(e.detail.mode));
    if(new URLSearchParams(location.search).has('search')){
      document.querySelector('#search')?.scrollIntoView({block:'center'});
      document.querySelector('#search')?.focus({preventScroll:true});
    }
  }else{
    const file=location.pathname.split('/').pop();
    if(file==='reddit.html'||file==='digest.html'||file==='opportunities.html'){
      selected('menu');
    }
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