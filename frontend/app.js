const pretty=x=>JSON.stringify(x,null,2);
async function get(path,id){try{document.querySelector(id).textContent=pretty(await (await fetch(path)).json())}catch(e){document.querySelector(id).textContent=e.message}}
async function refresh(){await Promise.all([get('/health','#health'),get('/v1/pipeline/status','#pipeline')])}
document.querySelector('#solve').onclick=async()=>{const output=document.querySelector('#answer'); output.textContent='Solving…';const r=await fetch('/v1/solve',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({question:document.querySelector('#question').value})});output.textContent=pretty(await r.json());refresh()}; refresh();
