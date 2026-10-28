'use strict';
(() => {
  const list=document.querySelector('#motivation-list');
  const status=document.querySelector('#motivation-status');
  const more=document.querySelector('#motivation-more');
  const filters=[...document.querySelectorAll('[data-journey-type]')];
  const requested=new URLSearchParams(location.search).get('story');
  const sharedStory=/^[a-f0-9]{20}$/.test(requested||'')?requested:null;
  let articles=[],selectedType='',visible=18;

  function element(tag,text,css){
    const node=document.createElement(tag);
    if(css)node.className=css;
    if(text)node.textContent=text;
    return node;
  }
  function safeUrl(raw){
    try{
      const uri=new URL(raw);
      return uri.protocol==='https:' && !uri.username && !uri.password ? uri.href : '';
    }catch{return '';}
  }
  function render(){
    const matches=articles.filter(article=>!selectedType || article.story_type===selectedType)
      .sort((a,b)=>(b.published||0)-(a.published||0));
    if(sharedStory){
      const found=matches.findIndex(a=>a.id===sharedStory);
      if(found>0)matches.unshift(...matches.splice(found,1));
    }
    list.replaceChildren();
    status.textContent=matches.length ?
      matches.length+' підтверджених історій із посиланнями на першоджерела' :
      'Зараз немає нових історій цього типу. Вище — перевірені приклади з першоджерел.';
    more.hidden=matches.length<=visible;
    more.textContent='Показати більше · '+(matches.length-visible);
    for(const article of matches.slice(0,visible)){
      const url=safeUrl(article.url);
      if(!url)continue;
      const card=element('article',null,'motivation-story');
      card.dataset.motivationId=article.id;
      const top=element('div',null,'motivation-story-top');
      top.append(element('span',article.story_type||'Історія','motivation-tag'));
      const time=document.createElement('time');
      if(article.published){
        time.dateTime=new Date(article.published*1000).toISOString();
        time.textContent=new Date(article.published*1000).toLocaleDateString('uk-UA',{day:'numeric',month:'short',year:'numeric'});
      }
      top.append(time);
      const heading=element('h3',null,'motivation-story-title');
      const link=element('a',article.title||'Історія засновника');
      link.href=url;link.target='_blank';link.rel='noopener noreferrer';
      heading.append(link);
      card.append(top,heading);
      if(article.summary){
        card.append(element('p',article.summary,'motivation-story-summary'));
      }
      const footer=element('div',null,'motivation-story-footer');
      footer.append(element('span',article.publisher||article.source||'Видання','motivation-story-source'));
      const actions=element('div',null,'motivation-story-actions');
      const open=element('a','Читати ↗');
      open.href=url;open.target='_blank';open.rel='noopener noreferrer';
      actions.append(open);
      if(window.PulseShare)actions.append(window.PulseShare.button(article,'story'));
      footer.append(actions);
      card.append(footer);
      list.append(card);
    }
    if(sharedStory){
      const row=list.querySelector('[data-motivation-id="'+sharedStory+'"]');
      if(row)requestAnimationFrame(()=>row.scrollIntoView({block:'center'}));
    }
  }

  filters.forEach(button=>button.addEventListener('click',()=>{
    selectedType=button.dataset.journeyType;
    visible=18;
    filters.forEach(item=>{
      const active=item===button;
      item.classList.toggle('active',active);
      item.setAttribute('aria-pressed',String(active));
    });
    render();
  }));
  more.addEventListener('click',()=>{visible+=18;render();});
  fetch('./motivation.json',{cache:'no-store'}).then(async response=>{
    if(!response.ok)throw Error('Network');
    const data=await response.json();
    if(!Array.isArray(data.articles))throw Error('Invalid feed');
    articles=data.articles;
    render();
  }).catch(()=>{
    status.textContent='Не вдалося завантажити свіжі історії. Перевір інтернет-з’єднання.';
  });
})();
