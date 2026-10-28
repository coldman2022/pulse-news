'use strict';
/* Read an independently built opt-in preview of first-party Reddit RSS.
   Do not make browser-side Reddit API or CORS requests. */
(() => {
  const status = document.querySelector('#reddit-feed-status');
  const root = document.querySelector('#reddit-feed-list');
  const count = document.querySelector('#reddit-feed-count');
  const controls = [...document.querySelectorAll('[data-reddit-topic]')];
  let posts = [];
  let topic = '';
  const allowlist = new Set(['LocalLLaMA','technology','ChatGPT','ukraine','Polska','ImmigrationCanada','UXDesign','movies','MovieSuggestions']);
  const allowedTopics = new Set(['AI','Технології','Україна','Польща','Імміграція','Дизайн','Кіно']);
  const safeLink = raw => {
    try {
      const u = new URL(raw);
      return u.origin === 'https://www.reddit.com' &&
        /^\/r\/[-\w]+\/comments\/[a-z0-9]+\//i.test(u.pathname) ? u.href : '';
    } catch { return ''; }
  };
  const el = (tag, value, css) => {
    const node=document.createElement(tag);
    if(value) node.textContent=value;
    if(css) node.className=css;
    return node;
  };
  function render(){
    root.replaceChildren();
    const visible = posts.filter(p => (!topic || p.topic === topic) &&
      allowlist.has(p.community) && allowedTopics.has(p.topic) &&
      safeLink(p.url) && typeof p.title === 'string');
    count.textContent = visible.length ? visible.length+' дописів' : '';
    controls.forEach(c => {
      const selected = c.dataset.redditTopic === topic;
      c.classList.toggle('active',selected);
      c.setAttribute('aria-pressed',String(selected));
    });
    for(const p of visible){
      const card = el('article',null,'reddit-post');
      const title = el('a',p.title,'reddit-post-title');
      title.href = safeLink(p.url);
      title.target = '_blank';
      title.rel = 'noopener noreferrer';
      const meta = el('div',null,'reddit-post-meta');
      meta.append(el('span','r/'+p.community), el('span',p.topic));
      if(Number.isFinite(p.published) && p.published > 0){
        const date = new Date(p.published*1000);
        if(!Number.isNaN(date.getTime())){
          const stamp = el('time',date.toLocaleDateString('uk-UA',{day:'numeric',month:'short'})+' · '+
            date.toLocaleTimeString('uk-UA',{hour:'2-digit',minute:'2-digit'}));
          stamp.dateTime = date.toISOString();
          meta.append(stamp);
        }
      }
      card.append(title,meta);
      root.append(card);
    }
    if(!visible.length && posts.length)root.append(el('p','Немає дописів у цій темі. Обери інший розділ.','reddit-no-posts'));
  }
  controls.forEach(b=>b.onclick=()=>{topic=b.dataset.redditTopic;render();});
  async function load(){
    try{
      const response=await fetch('./reddit.json',{cache:'no-store'});
      if(!response.ok)throw new Error('HTTP '+response.status);
      const data=await response.json();
      posts=Array.isArray(data.posts)?data.posts:[];
      if(data.status==='ended'){
        status.textContent='Пробний RSS-доступ завершився 13 листопада 2026 року. Посилання на спільноти нижче залишаються доступними.';
      }else if(data.status==='unavailable'){
        status.textContent='Reddit зараз не надає дописи для Pulse. Можливе блокування RSS — відкрий спільноти нижче.';
      }else if(data.status==='cached'){
        status.textContent='Тимчасово показуємо останні отримані дописи; нові запити до Reddit не вдалися.';
      }else if(posts.length){
        status.textContent='Пробна автоматична стрічка Reddit · оновлюється не частіше ніж раз на 6 годин · дописи користувачів, не перевірені новини.';
      }else{
        status.textContent='У доступних RSS-стрічках зараз немає нових дописів.';
      }
      render();
    }catch{
      status.textContent='Не вдалося завантажити Reddit-стрічку. Перейди до спільнот за прямими посиланнями нижче.';
    }
  }
  load();
})();
