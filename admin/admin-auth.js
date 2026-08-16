(()=>{
  const config=window.TEAMSPIRIT_ADMIN_CONFIG||{},base=String(config.apiBase||"").replace(/\/$/,"");
  const key="teamspirit-admin-session",login=document.getElementById("adminLogin"),form=document.getElementById("adminLoginForm"),error=document.getElementById("adminLoginError");
  let token=sessionStorage.getItem(key)||"";
  const request=async(path,options={})=>{if(!base)throw new Error("Backend Editor chưa được kết nối");const response=await fetch(base+path,{...options,headers:{"Content-Type":"application/json",...(token?{Authorization:`Bearer ${token}`}:{ }),...(options.headers||{})}});const data=await response.json().catch(()=>({ok:false,error:"Phản hồi backend không hợp lệ"}));if(response.status===401){token="";sessionStorage.removeItem(key);login.hidden=false}if(!response.ok||data.ok===false)throw new Error(data.error||`HTTP ${response.status}`);return data};
  window.teamspiritAdminApi=request;
  window.teamspiritAdminReady=new Promise(resolve=>{
    const ready=()=>{login.hidden=true;document.documentElement.classList.add("admin-authenticated");resolve()};
    if(token)request("/api/auth/me").then(data=>data.authenticated?ready():Promise.reject()).catch(()=>{token="";sessionStorage.removeItem(key);login.hidden=false});
    form.addEventListener("submit",async event=>{event.preventDefault();const button=form.querySelector("button");button.disabled=true;error.textContent="";try{const data=await request("/api/auth/login",{method:"POST",body:JSON.stringify({username:document.getElementById("adminUsername").value.trim(),password:document.getElementById("adminPassword").value})});token=data.token;sessionStorage.setItem(key,token);form.reset();ready()}catch(ex){error.textContent=ex.message||"Không thể đăng nhập"}finally{button.disabled=false}});
  });
})();
