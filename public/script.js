async function checkout(plan){
  try{
    const res = await fetch("/create-checkout-session", {
      method: "POST",
      headers: { "Content-Type":"application/json" },
      body: JSON.stringify({ plan })
    });

    const raw = await res.text();   // read ONCE
    let data;
    try { data = JSON.parse(raw); }
    catch { data = { detail: raw }; }

    if(!res.ok){
      alert("Error: " + (data.detail || "checkout failed"));
      return;
    }

    if(data.url){
      window.location.href = data.url;
    } else {
      alert("No checkout URL returned.");
    }
  } catch(e){
    alert("Network error: " + e);
  }
