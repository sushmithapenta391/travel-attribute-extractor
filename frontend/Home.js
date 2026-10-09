/* Travel NLU - Home / front page. Drop-in: add <script src="home.js"></script> just before </body>
   (after the last existing <script>). It injects the CSS, nav button and Home view by itself. */
(() => {
  const CSS = `
main{max-width:1280px}
.home-hero{
  position:relative;
  overflow:hidden;
  border:1px solid var(--line);
  border-radius:18px;
  max-width:1000px;
  margin:0 auto 20px;
  padding:28px 20px 22px;
  background:var(--card);
  text-align:center;
}
.home-hero>*:not(.aurora){position:relative;z-index:1}
.aurora{position:absolute;inset:-30%;z-index:0;filter:blur(70px);opacity:.5;pointer-events:none}
[data-theme=light] .aurora{opacity:.28}
.aurora i{position:absolute;border-radius:50%;animation:drift 12s ease-in-out infinite alternate}
.aurora i:nth-child(1){width:340px;height:340px;background:#E8722C;left:8%;top:20%}
.aurora i:nth-child(2){width:300px;height:300px;background:#4f46e5;right:10%;top:25%;animation-delay:-4s}
.aurora i:nth-child(3){width:260px;height:260px;background:#1F9A5A;left:42%;bottom:5%;animation-delay:-8s}
@keyframes drift{to{transform:translate(70px,-40px) scale(1.25)}}
.hbadge{display:inline-block;font:600 .72rem Sora,sans-serif;padding:5px 12px;border-radius:20px;border:1px solid var(--line);background:var(--bg);color:var(--accent);margin-bottom:14px}
.htitle{font:700 3.4rem/1.2 Sora,sans-serif;margin:0 0 34px;background:linear-gradient(90deg,var(--ink),var(--accent),var(--ink));background-size:200% auto;-webkit-background-clip:text;background-clip:text;color:transparent;animation:shine 6s linear infinite}
@keyframes shine{to{background-position:200% center}}
.demo{max-width:1000px;margin:0 auto;min-height:220px;padding:28px;border-radius:16px;background:var(--bg);border:1px solid var(--line)}
#dmWords{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;min-height:90px}
.dw{padding:9px 13px 5px;font-size:1.2rem;border-radius:8px;text-align:center;animation:pop .3s ease both;transition:background .3s}
.dw b{display:block;font-weight:500}.dw small{display:block;font:600 .7rem Sora,sans-serif;opacity:.9;min-height:1rem}
.dw.on{color:#fff;transform:translateY(-3px)}[data-theme=light] .dw.on{color:var(--ink)}
#dmAttrs{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin-top:20px}
.ac{font-size:1rem;padding:6px 14px;border-radius:16px;border:1px solid var(--accent);animation:pop .35s ease both}
.ac i{font-style:normal;color:var(--accent);margin-right:6px;font-weight:600}
@keyframes pop{from{opacity:0;transform:scale(.7) translateY(8px)}}
.home-hero .row{margin-top:34px}
.home-hero .row button{font-size:1.1rem;padding:14px 28px}
.hgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px}
.hcard{position:relative;text-align:left;cursor:pointer;padding:28px 24px;min-height:150px;border-radius:14px;border:1px solid var(--line);background:var(--card);color:var(--ink);
  animation:rise .5s ease both;animation-delay:calc(var(--i)*60ms);transition:transform .2s,border-color .2s;--mx:50%;--my:50%}
.hcard::before{content:"";position:absolute;inset:0;border-radius:14px;opacity:0;transition:opacity .25s;background:radial-gradient(180px circle at var(--mx) var(--my),rgba(232,114,44,.22),transparent 70%)}
.hcard:hover{transform:translateY(-4px);border-color:var(--accent)}.hcard:hover::before{opacity:1}
.hcard .ic{font-size:2.2rem}.hcard h3{margin:12px 0 6px;font:600 1.25rem Sora,sans-serif}.hcard p{margin:0;font-size:14.5px;color:var(--mut)}
@keyframes rise{from{opacity:0;transform:translateY(18px)}}
.hplane{font-size:3.6rem;animation:flt 2.8s ease-in-out infinite alternate;margin-bottom:10px}
@keyframes flt{to{transform:translate(10px,-8px) rotate(6deg)}}
.about{display:grid;grid-template-columns:1.3fr 1fr;gap:24px;align-items:center}
.about-img{width:100%;height:auto;border-radius:12px;border:1px solid var(--line);background:var(--bg)}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px}
.steps div{display:flex;gap:8px;align-items:center;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);font-size:12.5px}
.steps b{background:var(--accent);color:#1a0d04;border-radius:50%;width:20px;height:20px;flex:none;display:grid;place-items:center;font:700 11px Sora,sans-serif}
@media(max-width:760px){.about{grid-template-columns:1fr}}
.about.wk{display:flex;gap:24px;align-items:flex-start}
.wk-main{flex:1;min-width:0;font-size:14px;line-height:1.65}
.wk-main h2{margin:0 0 10px;font-size:1.35rem}
.wk-main h3{margin:20px 0 8px;padding-bottom:4px;border-bottom:1px solid var(--line);font:600 1.05rem Sora,sans-serif}
.wk-main p{margin:0 0 10px;color:var(--ink)}
.wk-main code{background:var(--bg);border:1px solid var(--line);border-radius:4px;padding:1px 5px;font-size:.85em}
.wk-dl{display:grid;grid-template-columns:150px 1fr;gap:6px 12px;margin:0}
.wk-dl dt{font:600 .68rem Sora,sans-serif;color:#fff;padding:4px 8px;border-radius:5px;align-self:start;text-align:center}
[data-theme=light] .wk-dl dt{color:var(--ink)}
.wk-dl dd{margin:0;font-size:13px;color:var(--mut)}.wk-dl dd b{color:var(--ink);font-weight:500}
.infobox{width:290px;flex:none;border:1px solid var(--line);border-radius:10px;background:var(--bg);padding:12px}
.ib-title{font:700 .95rem Sora,sans-serif;text-align:center;margin-bottom:4px}
.infobox table{margin-top:10px;font-size:12.5px}.infobox th{width:38%;color:var(--mut);font:600 .72rem Sora,sans-serif}
@media(max-width:900px){.about.wk{flex-direction:column}.infobox{width:100%}.wk-dl{grid-template-columns:1fr}}
#beStatus.up{color:#4ADE80;border-color:#4ADE80}#beStatus.down{color:#FF6B5E;border-color:#FF6B5E}`;

  const VIEW = `
<div class="home-hero">
  <div class="aurora"><i></i><i></i><i></i></div>
  <div class="hplane">✈</div>
  <h1 class="htitle">Travel Attribute Extractor</h1>
  <div class="demo"><div id="dmWords"></div><div id="dmAttrs"></div></div>
  <div class="row" style="justify-content:center">
    <button class="primary" data-go="extract">Start extracting →</button>
    <button class="ghost" data-go="eval">See accuracy</button>
    <span id="beStatus" class="chip">checking backend…</span>
  </div>
  </div>
   <div class="copyright">© 2026 Penta Sushmitha</div>
<div class="hgrid" id="homeCards"></div>

</div>

<div class="hgrid" id="homeCards"></div>
<section class="about wk" style="margin-top:20px">
  <article class="wk-main">
    <h2>About Travel Attribute Extractor</h2>
    <p><b>Travel</b> is the movement of people between distant places, on foot or by road, rail, air or water, either one way or as a round trip. Almost every travel request, whether to an agent or to a booking site, states the same few facts: where from, where to, when, by what, and for how many people.</p>
    <p><b>Travel Attribute Extractor</b> reads such a request written in ordinary English and returns those facts as structured JSON. It is a sequence-labelling task (a form of named entity recognition), not a chatbot: a sentence goes in, labelled tokens and clean attributes come out.</p>

    <h3>BIO tagging</h3>
    <p>Each word (token) gets one tag. <b>B-</b> marks the beginning of an entity, <b>I-</b> continues it, and <b>O</b> means the word is outside any entity. In "flight from <b>New Delhi</b>", New is <code>B-SOURCE</code>, Delhi is <code>I-SOURCE</code> and the rest are <code>O</code>. Multi-word values such as "25 September" or "window seat" stay together this way.</p>

    <h3>Attributes it extracts</h3>
    <dl class="wk-dl"><dt style="background:var(--SOURCE)">SOURCE</dt><dd><b>Departure city.</b> e.g. "from Hyderabad"</dd><dt style="background:var(--DESTINATION)">DESTINATION</dt><dd><b>Arrival city.</b> e.g. "to Delhi"</dd><dt style="background:var(--DATE)">DATE</dt><dd><b>Outbound travel date.</b> e.g. "25 September, tomorrow, Friday, 12/10/2026"</dd><dt style="background:var(--RETURN_DATE)">RETURN_DATE</dt><dd><b>Date of the return leg, makes the trip a round trip.</b> e.g. "returning on 2 October"</dd><dt style="background:var(--PASSENGERS)">PASSENGERS</dt><dd><b>Generic traveller count.</b> e.g. "3 people"</dd><dt style="background:var(--PASSENGER_ADULT)">PASSENGER_ADULT</dt><dd><b>Number of adults; child and infant counts are tagged separately and summed.</b> e.g. "2 adults and 1 child"</dd><dt style="background:var(--CLASS)">CLASS</dt><dd><b>Cabin or coach class.</b> e.g. "economy, business, sleeper"</dd><dt style="background:var(--MODE)">MODE</dt><dd><b>Way of travelling.</b> e.g. "flight, train, bus, cab"</dd><dt style="background:var(--TIME)">TIME</dt><dd><b>Preferred time of day or clock time.</b> e.g. "morning, 6 pm"</dd><dt style="background:var(--BUDGET)">BUDGET</dt><dd><b>Maximum spend in rupees.</b> e.g. "under 8000"</dd><dt style="background:var(--SEAT)">SEAT</dt><dd><b>Seat preference.</b> e.g. "window seat, aisle seat"</dd><dt style="background:var(--MEAL)">MEAL</dt><dd><b>Meal preference.</b> e.g. "veg meal, non-veg"</dd><dt style="background:var(--STOPS)">STOPS</dt><dd><b>Non-stop or direct request.</b> e.g. "non-stop, direct"</dd><dt style="background:var(--VIA)">VIA</dt><dd><b>Intermediate stop on a multi-leg route.</b> e.g. "via Vijayawada"</dd></dl>

    <h3>Modes of travel</h3>
    <p><b>Flight</b>: fastest over long distances, priced by class (economy, premium, business). <b>Train</b>: affordable and reliable on Indian routes, with classes such as sleeper and AC. <b>Bus</b>: cheapest for short and medium trips. <b>Cab</b>: door to door, priced per vehicle rather than per person.</p>

    <h3>How it works</h3>
    <div class="steps">
      <div><b>1</b><span>Tokenize the sentence</span></div>
      <div><b>2</b><span>Tag each token (BIO)</span></div>
      <div><b>3</b><span>Merge tags into attributes</span></div>
      <div><b>4</b><span>Validate and output JSON</span></div>
    </div>
    <p style="margin-top:10px">The tagger understands <b>negation</b> ("not from Delhi, from Hyderabad" ignores Delhi), <b>multi-leg routes</b> ("A to B via C"), <b>round trips</b> and separate adult, child and infant counts. After extraction it also resolves dates to ISO format, checks for problems (missing city, past date, infant without adult), and estimates distance and fare.</p>

    <h3>Technology</h3>
    <p>The backend is a <b>Flask</b> (Python) API with a rule-based tagger and a gazetteer of 30 cities. The frontend is plain HTML, CSS and JavaScript. The tagging function is isolated, so it can be replaced by a fine-tuned <b>RoBERTa</b> token-classification model; the Annotate tab exports BIO data (JSONL and CoNLL) for exactly that purpose.</p>

    <h3>Tools in this app</h3>
    <p><b>Extractor</b> shows tokens, tags and JSON for one sentence. <b>Batch Extractor</b> handles many lines with CSV/JSON export. <b>Label Reference</b> lists every tag. <b>History</b> and <b>Dashboard</b> track your session. <b>Evaluation</b> reports precision, recall and F1 per entity. <b>Itinerary</b> prints a boarding-pass summary and a calendar file. <b>Destination Guide</b> gives places, food and stay types. <b>Annotate</b> builds a labelled dataset.</p>
  </article>
  <aside class="infobox">
    <div class="ib-title">Travel Attribute Extractor</div>
    <svg class="about-img" style="margin-top:10px" viewBox="0 0 320 230" xmlns="http://www.w3.org/2000/svg" aria-label="Route illustration">
    <circle cx="48" cy="40" r="22" fill="#E8722C" opacity=".12"/><circle cx="280" cy="190" r="30" fill="#4f46e5" opacity=".12"/>
    <path d="M18 62h46M34 52h30" stroke="var(--mut)" stroke-width="5" stroke-linecap="round" opacity=".3"/>
    <path d="M250 40h50M262 30h30" stroke="var(--mut)" stroke-width="5" stroke-linecap="round" opacity=".3"/>
    <path d="M70 170 Q 160 20 250 80" fill="none" stroke="var(--accent)" stroke-width="3" stroke-dasharray="7 7"/>
    <g transform="translate(70 170)"><circle r="13" fill="#2E9FC8"/><circle r="5" fill="#fff"/></g>
    <g transform="translate(250 80)"><circle r="13" fill="#2EA05A"/><circle r="5" fill="#fff"/></g>
    <text x="160" y="72" font-size="30" text-anchor="middle" transform="rotate(8 160 72)">✈</text>
    <text x="70" y="204" font-size="13" text-anchor="middle" fill="var(--ink)" font-weight="600">SOURCE</text>
    <text x="250" y="114" font-size="13" text-anchor="middle" fill="var(--ink)" font-weight="600">DESTINATION</text>
    <rect x="100" y="196" width="40" height="16" rx="8" fill="#66531A"/><text x="120" y="208" font-size="9" text-anchor="middle" fill="#fff">DATE</text>
    <rect x="150" y="196" width="46" height="16" rx="8" fill="#6B2B47"/><text x="173" y="208" font-size="9" text-anchor="middle" fill="#fff">ADULT</text>
    <rect x="204" y="196" width="40" height="16" rx="8" fill="#453471"/><text x="224" y="208" font-size="9" text-anchor="middle" fill="#fff">CLASS</text>
  </svg>
    <table>
      <tr><th>Task</th><td>Sequence labelling (NER)</td></tr>
      <tr><th>Input</th><td>One travel sentence</td></tr>
      <tr><th>Output</th><td>BIO tags and JSON</td></tr>
      <tr><th>Tag scheme</th><td>BIO</td></tr>
      <tr><th>Labels</th><td>15</td></tr>
      <tr><th>Cities known</th><td>30</td></tr>
      <tr><th>Backend</th><td>Flask (Python)</td></tr>
      <tr><th>Tagger</th><td>Rule-based, RoBERTa-ready</td></tr>
    </table>
  </aside>
</section>`;

  // inject CSS, nav button, view
  const st = document.createElement("style"); st.textContent = CSS; document.head.appendChild(st);
  const navFirst = document.querySelector("nav button");
  const nb = document.createElement("button"); nb.dataset.view = "home"; nb.textContent = "Home";
  navFirst.parentNode.insertBefore(nb, navFirst);
  const view = document.createElement("div"); view.className = "view"; view.id = "view-home"; view.innerHTML = VIEW;
  document.querySelector("main").insertBefore(view, document.querySelector("main").firstChild);

  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const go = v => document.querySelector(`nav button[data-view="${v}"]`).click();
  const showHome = () => {
    document.querySelectorAll("nav button").forEach(x => x.classList.remove("active"));
    document.querySelectorAll(".view").forEach(x => x.classList.remove("active"));
    nb.classList.add("active"); view.classList.add("active");
    ping();
  };
  nb.onclick = showHome;

  const CARDS = [["extract","⚡","Extractor","Sentence → BIO tags → JSON"],["batch","📦","Batch Extractor","Chala requests okesari, CSV/JSON export"],
    ["labels","🏷️","Label Reference","15 entity types, examples tho"],["history","🕘","History","Pata extractions malli open cheyyi"],
    ["dashboard","📊","Dashboard","Routes, modes, classes live"],["eval","🧪","Evaluation","Precision / Recall / F1"],
    ["itinerary","🎫","Itinerary","Boarding pass + calendar .ics"],["destination","🌍","Destination Guide","Places, food, stay types"],
    ["annotate","✍️","Annotate","RoBERTa training data build cheyyi"]];
  $("homeCards").innerHTML = CARDS.map(([v,ic,t,d],i) =>
    `<button class="hcard" style="--i:${i}" data-go="${v}"><span class="ic">${ic}</span><h3>${t}</h3><p>${d}</p></button>`).join("");
  view.querySelectorAll("[data-go]").forEach(b => {
    b.addEventListener("click", () => go(b.dataset.go));
    b.addEventListener("mousemove", e => { const r = b.getBoundingClientRect();
      b.style.setProperty("--mx", (e.clientX-r.left)+"px"); b.style.setProperty("--my", (e.clientY-r.top)+"px"); });
  });

  async function ping() {
    const s = $("beStatus");
    try { await fetch(API.replace("/extract","/cities")); s.textContent = "● Backend online"; s.className = "chip up"; }
    catch (e) { s.textContent = "● Backend offline — run python app.py"; s.className = "chip down"; }
  }

  const D = [
    {t:[["Book","O"],["a","O"],["flight","MODE"],["from","O"],["Hyderabad","SOURCE"],["to","O"],["Delhi","DESTINATION"],["on","O"],["25","DATE"],["September","DATE"],["for","O"],["2","PASSENGER_ADULT"],["adults","PASSENGER_ADULT"]],
     a:{mode:"flight",source:"Hyderabad",destination:"Delhi",date:"25 September",adults:2}},
    {t:[["Flight","MODE"],["not","O"],["from","O"],["Delhi","O"],[",","O"],["from","O"],["Pune","SOURCE"],["to","O"],["Goa","DESTINATION"],["returning","O"],["2","RETURN_DATE"],["October","RETURN_DATE"]],
     a:{mode:"flight",source:"Pune",destination:"Goa",return_date:"2 October"}},
    {t:[["Train","MODE"],["from","O"],["Chennai","SOURCE"],["via","O"],["Vijayawada","VIA"],["to","O"],["Delhi","DESTINATION"],["tomorrow","DATE"],["morning","TIME"],["under","O"],["8000","BUDGET"]],
     a:{mode:"train",source:"Chennai",via:"Vijayawada",destination:"Delhi",date:"tomorrow",time:"morning",budget:8000}},
    {t:[["Non","STOPS"],["-","STOPS"],["stop","STOPS"],["flight","MODE"],["to","O"],["Dubai","DESTINATION"],["with","O"],["window","SEAT"],["seat","SEAT"],["and","O"],["veg","MEAL"],["meal","MEAL"]],
     a:{stops:"non-stop",mode:"flight",destination:"Dubai",seat:"window seat",meal:"veg meal"}}
  ];
  (async function loop() {
    const W = $("dmWords"), A = $("dmAttrs");
    for (let n = 0; ; n = (n+1) % D.length) {
      const d = D[n]; W.innerHTML = ""; A.innerHTML = "";
      for (const [w] of d.t) { W.insertAdjacentHTML("beforeend", `<span class="dw"><b>${esc(w)}</b><small></small></span>`); await sleep(110); }
      await sleep(450);
      const els = [...W.children];
      for (let i = 0; i < els.length; i++) {
        const tag = d.t[i][1];
        if (tag !== "O") { els[i].style.background = `var(--${tag})`; els[i].classList.add("on"); els[i].querySelector("small").textContent = tag.replace("PASSENGER_",""); await sleep(150); }
      }
      await sleep(350);
      for (const [k,v] of Object.entries(d.a)) { A.insertAdjacentHTML("beforeend", `<span class="ac"><i>${k}</i>${esc(v)}</span>`); await sleep(170); }
      await sleep(3200);
    }
  })();

  showHome();   // Home is the first thing you see
})();