const $ = id => document.getElementById(id);
async function api(url, options={}) {
  const response = await fetch(url, {headers:{"Content-Type":"application/json"}, ...options});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}
function esc(value) {
  return String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
async function refresh() {
  const [s, blocks, fileList, dirs, journal] = await Promise.all([
    api("/api/status"), api("/api/blocks"), api("/api/files"), api("/api/directories"), api("/api/journal")
  ]);
  $("total").textContent=s.total_blocks; $("used").textContent=s.used_blocks;
  $("free").textContent=s.free_blocks; $("percent").textContent=s.usage_percent+"%";
  $("blockmap").innerHTML=blocks.bitmap.map((bit,i)=>`<i class="block ${bit?"used":""}" title="Block ${i}: ${bit?"Used":"Free"}"></i>`).join("");
  $("file-list").innerHTML=fileList.map(f=>`<div class="file-row"><span>▤ ${esc(f.path)} <small>· ${f.size} bytes · ${f.block_count} block(s)</small></span><span><button data-read="${esc(f.path)}">Read</button><button data-delete="${esc(f.path)}">Delete</button></span></div>`).join("") || '<p class="muted">No files created yet.</p>';
  $("directory-list").innerHTML=dirs.map(d=>`<span class="chip">${esc(d)}</span>`).join("");
  $("journal").innerHTML=journal.map(tx=>`<div class="journal-item"><b>${esc(tx.status)}</b> · ${esc(tx.operation)} · ${esc(tx.path)}</div>`).join("") || "Journal is empty.";
}
$("file-form").addEventListener("submit",async e=>{e.preventDefault();const fd=new FormData(e.target);try{await api("/api/files",{method:"POST",body:JSON.stringify({path:fd.get("path"),content:fd.get("content")})});e.target.reset();await refresh()}catch(err){alert(err.message)}});
$("dir-form").addEventListener("submit",async e=>{e.preventDefault();const fd=new FormData(e.target);try{await api("/api/directories",{method:"POST",body:JSON.stringify({path:fd.get("path")})});e.target.reset();await refresh()}catch(err){alert(err.message)}});
$("file-list").addEventListener("click",async e=>{
  const del=e.target.dataset.delete, read=e.target.dataset.read;
  try {
    if(del){await api("/api/files/"+encodeURIComponent(del).replaceAll("%2F","/"),{method:"DELETE"});await refresh()}
    if(read){const result=await api("/api/files/"+encodeURIComponent(read).replaceAll("%2F","/"));alert("File content:\n\n"+result.content)}
  } catch(err){alert(err.message)}
});
$("crash").addEventListener("click",async()=>{try{$("recovery-message").textContent=(await api("/api/crash",{method:"POST"})).message;await refresh()}catch(e){$("recovery-message").textContent=e.message}});
$("recover").addEventListener("click",async()=>{try{$("recovery-message").textContent=(await api("/api/recover",{method:"POST"})).message;await refresh()}catch(e){$("recovery-message").textContent=e.message}});
$("analyze").addEventListener("click",async()=>{$("optimization-result").textContent=JSON.stringify(await api("/api/fragmentation"),null,2)});
$("optimize").addEventListener("click",async()=>{try{$("optimization-result").textContent=JSON.stringify((await api("/api/optimize",{method:"POST"})).result,null,2);await refresh()}catch(e){$("optimization-result").textContent=e.message}});
$("benchmark").addEventListener("click",async()=>{$("optimization-result").textContent=JSON.stringify(await api("/api/benchmark"),null,2)});
refresh().catch(e=>console.error(e));
