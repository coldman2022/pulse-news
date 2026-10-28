'use strict';
/* Share any Pulse card by holding it (touch) or right-clicking it (desktop).
   Native iOS/Android Web Share API stays behind an explicit user tap. */
window.PulseShare = (() => {
  const LONG_PRESS_MS=550;
  const MOVE_TOLERANCE_PX=12;
  const links=new WeakMap();
  const live=document.createElement('span');
  live.className='visually-hidden';
  live.setAttribute('role','status');
  live.setAttribute('aria-live','polite');

  const overlay=document.createElement('div');
  overlay.className='pulse-share-backdrop';
  overlay.hidden=true;
  const sheet=document.createElement('section');
  sheet.className='pulse-share-sheet';
  sheet.setAttribute('role','dialog');
  sheet.setAttribute('aria-modal','true');
  sheet.setAttribute('aria-label','Дії зі статтею');
  sheet.hidden=true;

  const heading=document.createElement('div');
  heading.className='pulse-share-heading';
  const label=document.createElement('strong');
  label.textContent='Стаття';
  const closeButton=document.createElement('button');
  closeButton.type='button';
  closeButton.className='pulse-share-close';
  closeButton.setAttribute('aria-label','Закрити меню статті');
  closeButton.textContent='×';
  heading.append(label,closeButton);

  const shareButton=document.createElement('button');
  shareButton.type='button';
  shareButton.className='pulse-share-action pulse-share-native';
  shareButton.textContent='Поділитися';
  const copyButton=document.createElement('button');
  copyButton.type='button';
  copyButton.className='pulse-share-action pulse-share-copy';
  copyButton.textContent='Копіювати посилання';
  sheet.append(heading,shareButton,copyButton);

  let active=null;
  let previousOverflow='';
  let lastFocus=null;
  let press=null;
  let suppressClickUntil=0;

  function ensureMounted(){
    if(!overlay.isConnected)document.body.append(overlay,sheet,live);
  }
  function deepLink(article,kind='article'){
    const id=String(article?.id||'');
    if(!/^[a-f0-9]{20}$/.test(id))return article?.url||location.href;
    const path=kind==='story'?'./motivation.html':'./';
    return new URL(path+'?'+(kind==='story'?'story':'article')+'='+id,document.baseURI).href;
  }
  function close(){
    if(sheet.hidden)return;
    sheet.hidden=true;
    overlay.hidden=true;
    active=null;
    document.body.style.overflow=previousOverflow;
    if(lastFocus?.isConnected && typeof lastFocus.focus==='function'){
      lastFocus.focus({preventScroll:true});
    }
    lastFocus=null;
  }
  function open(article,kind='article'){
    ensureMounted();
    if(sheet.hidden){
      lastFocus=document.activeElement;
      previousOverflow=document.body.style.overflow;
    }
    active={article,kind};
    label.textContent=String(article?.title||'Стаття').slice(0,120);
    sheet.hidden=false;
    overlay.hidden=false;
    document.body.style.overflow='hidden';
    closeButton.focus({preventScroll:true});
  }
  async function copy(article,kind='article'){
    const url=deepLink(article,kind);
    try{
      if(!navigator.clipboard?.writeText)throw Error('Clipboard not supported');
      await navigator.clipboard.writeText(url);
      live.textContent='Посилання скопійовано';
      return 'copied';
    }catch{
      window.prompt('Скопіюй посилання:',url);
      return 'manual';
    }
  }
  async function share(article,kind='article'){
    const url=deepLink(article,kind);
    if(typeof navigator.share==='function'){
      try{
        await navigator.share({title:String(article?.title||'Новина у Pulse'),url});
        return 'shared';
      }catch(error){
        if(error?.name==='AbortError')return 'cancelled';
      }
    }
    return copy(article,kind);
  }
  // Close before sharing, but call share synchronously during the user gesture.
  shareButton.addEventListener('click',()=>{
    const item=active;
    close();
    if(item)share(item.article,item.kind);
  });
  copyButton.addEventListener('click',()=>{
    const item=active;
    close();
    if(item)copy(item.article,item.kind);
  });
  closeButton.addEventListener('click',close);
  overlay.addEventListener('click',close);
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'&&!sheet.hidden){e.preventDefault();close();}
  });

  function targetFor(node){
    return node?.closest?.('.pulse-holdable')||null;
  }
  function eligible(event,root){
    if(!root || !links.has(root))return false;
    // Pressing other controls should continue to work exactly as before.
    if(event.target.closest('button,input,select,textarea,summary,[contenteditable]'))return false;
    return true;
  }
  function clearPress(){
    if(press?.timer)clearTimeout(press.timer);
    press=null;
  }
  function showFor(root){
    const item=links.get(root);
    if(!item)return;
    suppressClickUntil=Date.now()+850;
    open(item.article,item.kind);
  }

  document.addEventListener('pointerdown',event=>{
    if(!sheet.hidden)return;
    const root=targetFor(event.target);
    if(!eligible(event,root) || event.pointerType==='mouse' ||
       event.button!==0 || !event.isPrimary)return;
    clearPress();
    const x=event.clientX,y=event.clientY,id=event.pointerId;
    press={root,x,y,id,timer:setTimeout(()=>{
      const current=press;
      if(!current || current.id!==id || !current.root.isConnected)return;
      clearPress();
      showFor(root);
    },LONG_PRESS_MS)};
  },{passive:true});

  document.addEventListener('pointermove',event=>{
    if(!press||event.pointerId!==press.id)return;
    if(Math.hypot(event.clientX-press.x,event.clientY-press.y)>MOVE_TOLERANCE_PX)clearPress();
  },{passive:true});
  document.addEventListener('pointerup',event=>{
    if(press&&event.pointerId===press.id)clearPress();
  },{passive:true});
  document.addEventListener('pointercancel',clearPress,{passive:true});
  document.addEventListener('scroll',clearPress,{capture:true,passive:true});

  document.addEventListener('contextmenu',event=>{
    const root=targetFor(event.target);
    if(!eligible(event,root))return;
    event.preventDefault();
    clearPress();
    // iOS may emit contextmenu after the pointer timer; avoid reopening the sheet.
    if(sheet.hidden)showFor(root);
  });
  document.addEventListener('click',event=>{
    if(Date.now()<suppressClickUntil && targetFor(event.target)){
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  },true);
  // Keyboard users can invoke the same actions without a touch gesture.
  document.addEventListener('keydown',event=>{
    if(event.key!=='ContextMenu' && !(event.shiftKey&&event.key==='F10'))return;
    const root=targetFor(document.activeElement);
    if(!root)return;
    event.preventDefault();
    showFor(root);
  });

  function enableLongPress(root,article,kind='article'){
    links.set(root,{article,kind});
    root.classList.add('pulse-holdable');
    root.dataset.pulseHoldable='';
  }
  return {deepLink,share,copy,enableLongPress};
})();
