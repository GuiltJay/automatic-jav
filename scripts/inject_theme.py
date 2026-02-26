import os

HTML_FILES = [
    "docs/index.html",
    "docs/home.html",
    "docs/missav.html",
    "docs/onejav.html",
    "docs/javct.html",
    "docs/models.html",
    "docs/codes.html",
    "docs/sitemap.html",
    "docs/stats.html",
]

JS_INJECT = """
<!-- Theme Toggle -->
<script>
  (function(){
    const toggle = document.createElement('button');
    toggle.innerHTML = '🌓';
    toggle.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9999;background:var(--card, #fff);border:1px solid var(--border, #ccc);color:var(--text, #000);padding:10px;border-radius:50%;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,0.2);display:flex;align-items:center;justify-content:center;font-size:22px;';
    toggle.onclick = () => {
      const isLight = document.body.getAttribute('data-theme') === 'light';
      document.body.setAttribute('data-theme', isLight ? 'dark' : 'light');
      localStorage.setItem('theme', isLight ? 'dark' : 'light');
    };
    document.body.appendChild(toggle);
    if(localStorage.getItem('theme') === 'light') document.body.setAttribute('data-theme', 'light');
  })();
</script>
</body>
"""

for fpath in HTML_FILES:
    if not os.path.exists(fpath):
        continue
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
        
    if "<!-- Theme Toggle -->" not in content:
        content = content.replace("</body>", JS_INJECT)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Injected theme into {fpath}")

