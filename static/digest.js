'use strict';
const $=s=>document.querySelector(s);
const make=(tag,txt,cls)=>{const e=document.createElement(tag);if(txt!=null)e.textContent=String(txt);if(cls)e.className=cls;return e;};
const fmt=ts=>{
  if(!ts)return '';
  const date=new Date(ts*1000);
  if(Number.isNaN(date.getTime()))return '';
  return date.toLocaleTimeString('uk-UA',{hour:'2-digit',minute:'2-digit',hour12:false})+' · '+
    date.toLocaleDateString('uk-UA',{day:'numeric',month:'short'});
};
function readCached(key){
 try{
   const data=JSON.parse(localStorage.getItem(key)||'{}');
   return data&&typeof data==='object'&&!Array.isArray(data)?data:{};
 }catch{return {};}
}
const cachedTitles=readCached('pulse-title-translations');
const cachedPreviews=readCached('pulse-translations');
let sharedPreviews={};
async function loadSharedPreviews(){
 try{
   const response=await fetch('./translations.json',{cache:'no-store'});
   if(!response.ok)return;
   const data=await response.json();
   if(data.schema===1 && data.articles && typeof data.articles==='object' &&
      !Array.isArray(data.articles))sharedPreviews=data.articles;
 }catch{/* Digests also work before the offline translation job runs. */}
}
async function loadDigest(){
 const target=$('#digest-sections');
 await loadSharedPreviews();
 try{
  const response=await fetch('./digest.json',{cache:'no-store'});
  if(!response.ok)throw new Error('HTTP '+response.status);
  const data=await response.json();
  if(!Array.isArray(data.sections))throw new Error('Invalid feed');
  const date=data.generated?new Date(data.generated*1000):null;
  $('#digest-period').textContent=(date?date.toLocaleString('uk-UA',{day:'numeric',month:'long',hour:'2-digit',minute:'2-digit',timeZone:'Europe/Warsaw'}):'')+' · час Польщі · '+(data.total||0)+' матеріалів';
  target.replaceChildren();
  for(const section of data.sections){
    const group=make('section',null,'digest-section');
    group.classList.add('digest-topic-'+(section.category==='Імміграція'?'migration':section.category==='AI'?'ai':section.category==='AI-події'?'events':'world'));
    const head=make('div',null,'digest-heading');
    head.append(make('h2',section.heading),make('span',(section.items||[]).length+' матеріалів'));
    group.append(head);
    if(!Array.isArray(section.items)||!section.items.length){
      group.append(make('p','За останні 24 години перевірені стрічки не дали матеріалів для цієї добірки.','digest-empty'));
    }else{
      const list=make('ol',null,'digest-items');
      for(const item of section.items){
        const row=make('li',null,'digest-item');
        const translated=cachedPreviews[item.id]||{};
        const saved=sharedPreviews[item.id];
        const shared=saved && saved.source_title===item.title ? saved : {};
        const title=(typeof translated.title==='string'&&translated.title)||
          shared.title||cachedTitles[item.id]||item.title;
        const summary=(typeof translated.summary==='string'&&translated.summary)||
          shared.summary||item.summary;
        const anchor=make('a',title,'digest-item-title');
        try{const url=new URL(item.url);if(url.protocol!=='https:')continue;anchor.href=url.href;}catch{continue;}
        anchor.target='_blank';anchor.rel='noopener noreferrer';
        row.append(anchor);
        if(summary)row.append(make('p',summary,'digest-item-summary'));
        const meta=make('div',null,'digest-item-meta');
        meta.append(make('span',item.publisher||'Джерело'),make('span',fmt(item.published)));
        row.append(meta);list.append(row);
      }
      group.append(list);
    }
    target.append(group);
  }
 }catch{
  $('#digest-period').textContent='Не вдалося завантажити огляд';
  target.replaceChildren(make('p','Огляд тимчасово недоступний. Перевірте збірку GitHub Actions або відкрийте загальну стрічку.','empty'));
 }
}
loadDigest();