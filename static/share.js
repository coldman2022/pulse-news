'use strict';
/* Native iOS/Android sharing, with no app/plugin, login, tracker or backend. */
window.PulseShare = (() => {
  const live=document.createElement('span');
  live.className='visually-hidden';
  live.setAttribute('role','status');
  document.addEventListener('DOMContentLoaded',()=>document.body.append(live),{once:true});

  function deepLink(article, kind='article') {
    const id=String(article?.id||'');
    // Pulse uses a stable 20-hex id derived from the source URL.
    if(!/^[a-f0-9]{20}$/.test(id))return article?.url||location.href;
    const target=kind==='story'?'motivation.html':'';
    const path=target?'./'+target:'./';
    return new URL(path+'?'+(kind==='story'?'story':'article')+'='+id, document.baseURI).href;
  }
  async function share(article, kind='article') {
    const url=deepLink(article,kind);
    const payload={title:String(article?.title||'Новина у Pulse'),url};
    if(typeof navigator.share==='function'){
      try {await navigator.share(payload);return 'shared';}
      catch(error){if(error?.name==='AbortError')return 'cancelled';}
    }
    try {
      if(!navigator.clipboard?.writeText)throw Error('clipboard unavailable');
      await navigator.clipboard.writeText(url);
      live.textContent='Посилання на статтю скопійовано';
      return 'copied';
    }catch{
      window.prompt('Скопіюй посилання на статтю:',url);
      return 'manual';
    }
  }
  function button(article,kind='article') {
    const item=document.createElement('button');
    item.type='button';
    item.className='story-share';
    item.title='Поділитися статтею';
    item.setAttribute('aria-label','Поділитися: '+String(article?.title||'Стаття'));
    item.innerHTML='<svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 15V3m0 0-4 4m4-4 4 4"/><path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"/></svg>';
    item.addEventListener('click',()=>{share(article,kind);});
    return item;
  }
  return {deepLink,share,button};
})();
