#!/usr/bin/env python3
import csv
import json
from collections import defaultdict, Counter
from pathlib import Path

INPUT_CSV = "results/processed/missav.csv"
OUTPUT_HTML = "docs/missav.html"
OUTPUT_JSON = "docs/missav.json"

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>MissAV · JAV.guru</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>

<style>
:root {
  --bg:#0b1220;
  --card:#111a2e;
  --accent:#8b5cf6;
  --pill:#1e293b;
}

body {
  margin:0;
  font-family:system-ui;
  background:var(--bg);
  color:white;
  padding:12px;
}

/* GRID */
#container {
  display:grid;
  grid-template-columns:repeat(2,1fr);
  gap:12px;
}

@media(min-width:768px){
  #container { grid-template-columns:repeat(4,1fr); }
}

@media(min-width:1200px){
  #container { grid-template-columns:repeat(6,1fr); }
}

.video-card {
  background:var(--card);
  border-radius:14px;
  padding:10px;
}

.video-card img {
  width:100%;
  border-radius:10px;
}

.code {
  font-weight:700;
  margin:6px 0;
  font-size:14px;
}

.pills {
  display:flex;
  flex-wrap:wrap;
  gap:6px;
}

.pill {
  background:var(--pill);
  padding:5px 10px;
  border-radius:999px;
  font-size:11px;
  cursor:pointer;
}

.pill:hover { background:var(--accent); }

video {
  width:100%;
  border-radius:10px;
  margin-top:8px;
}

/* STICKY MINI PLAYER */
#miniPlayer {
  position:fixed;
  bottom:15px;
  right:15px;
  width:240px;
  display:none;
  background:#000;
  border-radius:10px;
  overflow:hidden;
  box-shadow:0 0 20px rgba(0,0,0,0.6);
  z-index:999;
}

#miniPlayer video {
  width:100%;
}
</style>
</head>

<body>

<h2>🎬 MissAV</h2>
<input id="filter" placeholder="Search..." style="width:100%;padding:10px;margin-bottom:12px;">

<div id="container"></div>
<div id="miniPlayer"><video controls></video></div>

<script>

let DATA = [];
let activePlayer = null;
let activeCard = null;

fetch("missav.json")
  .then(r => r.json())
  .then(data => {
    DATA = data;
    initVirtual();
  });

/* ------------------------
   VIRTUAL SCROLL
------------------------ */

function initVirtual(){

  const container = document.getElementById("container");
  const rowHeight = 340; // approx card height
  const buffer = 5;

  let startIndex = 0;
  let endIndex = 0;

  function render(){

    const q = filter.value.toLowerCase();
    const filtered = DATA.filter(v =>
      v.code.toLowerCase().includes(q)
    );

    const scrollTop = window.scrollY;
    const screenHeight = window.innerHeight;

    const itemsPerRow = getItemsPerRow();
    const totalRows = Math.ceil(filtered.length / itemsPerRow);

    const startRow = Math.max(0, Math.floor(scrollTop / rowHeight) - buffer);
    const endRow = Math.min(totalRows,
      Math.ceil((scrollTop + screenHeight) / rowHeight) + buffer);

    startIndex = startRow * itemsPerRow;
    endIndex = Math.min(filtered.length, endRow * itemsPerRow);

    container.innerHTML = "";

    for(let i = startIndex; i < endIndex; i++){
      renderCard(filtered[i]);
    }

    container.style.paddingTop = startRow * rowHeight + "px";
    container.style.paddingBottom =
      (totalRows - endRow) * rowHeight + "px";
  }

  function getItemsPerRow(){
    if(window.innerWidth >= 1200) return 6;
    if(window.innerWidth >= 768) return 4;
    return 2;
  }

  window.addEventListener("scroll", render);
  window.addEventListener("resize", render);
  filter.oninput = render;

  render();
}

/* ------------------------
   CARD RENDER
------------------------ */

function renderCard(v){

  const thumb = `https://imgproxy.mrspidyxd.workers.dev/?url=https://fourhoi.com/${v.code}/cover-n.jpg`;
  const preview = `https://fourhoi.com/${v.code}/preview.mp4`;

  const card = document.createElement("div");
  card.className = "video-card";

  card.innerHTML = `
    <img src="${thumb}" loading="lazy">
    <div class="code">${v.code.toUpperCase()}</div>
    <div class="pills">
      <div class="pill preview">Preview</div>
    </div>
    <video controls style="display:none;"></video>
  `;

  const previewBtn = card.querySelector(".preview");
  const player = card.querySelector("video");

  previewBtn.onclick = () => {
    activatePlayer(player, preview);
  };

  document.getElementById("container").appendChild(card);
}

/* ------------------------
   PLAYER + STICKY
------------------------ */

function activatePlayer(player, url){

  if(activePlayer && activePlayer !== player){
    activePlayer.pause();
  }

  activePlayer = player;
  activeCard = player.closest(".video-card");

  player.style.display = "block";
  player.src = url;
  player.play().catch(()=>{});
}

/* Sticky logic */
window.addEventListener("scroll", () => {

  if(!activePlayer || !activeCard) return;

  const rect = activeCard.getBoundingClientRect();

  if(rect.bottom < 0 || rect.top > window.innerHeight){
    const mini = document.getElementById("miniPlayer");
    const miniVideo = mini.querySelector("video");

    mini.style.display = "block";
    miniVideo.src = activePlayer.src;
    miniVideo.play().catch(()=>{});
  }
  else{
    document.getElementById("miniPlayer").style.display = "none";
  }
});

</script>
</body>
</html>
"""


def generate():

    grouped = defaultdict(lambda: {"code": "", "entries": []})

    with open(INPUT_CSV,newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            page_url = r["page_url"].strip()
            code = r["video_code"].strip()
            playlist = r["playlist_url"].strip()
            quality = r["quality"].strip()
            source = r["source"].strip()

            if not page_url or not playlist:
                continue

            grouped[page_url]["code"] = code
            grouped[page_url]["entries"].append({
                "quality": quality,
                "source": source,
                "url": playlist
            })

    data = [
        {"code": v["code"], "entries": v["entries"]}
        for v in grouped.values()
    ]

    # Compact JSON (CDN friendly)
    OUTPUT_JSON.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")

    OUTPUT_HTML.write_text(HTML, encoding="utf-8")

    print("[✓] Missav Page build generated.")


if __name__ == "__main__":
    generate()
