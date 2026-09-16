/* Rdzen aplikacji: API, stan, nawigacja, router, powiadomienia. */
var S = {me: null, meta: null, classes: []};

function api(method, url, body) {
  return fetch(url, {
    method: method,
    headers: {"Content-Type": "application/json"},
    body: body ? JSON.stringify(body) : undefined
  }).then(function (res) {
    return res.json().catch(function () { return {}; }).then(function (data) {
      if (!res.ok) throw new Error(data.error || ("Błąd " + res.status));
      return data;
    });
  });
}
function GET(u) { return api("GET", u); }
function POST(u, b) { return api("POST", u, b || {}); }
function PUT(u, b) { return api("PUT", u, b || {}); }
function DEL(u) { return api("DELETE", u); }

function toast(msg, type) {
  var el = document.createElement("div");
  el.className = "toast " + (type || "");
  el.textContent = msg;
  document.getElementById("toast-root").appendChild(el);
  setTimeout(function () { el.remove(); }, 3800);
}
function openModal(html) {
  var root = document.getElementById("modal-root");
  root.innerHTML = '<div class="modal-overlay" id="moverlay"><div class="modal">' + html + "</div></div>";
  document.getElementById("moverlay").addEventListener("click", function (e) {
    if (e.target.id === "moverlay") closeModal();
  });
}
function closeModal() { document.getElementById("modal-root").innerHTML = ""; }
document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeModal(); });

function celebrate(res, title) {
  var m = (res && res.missions) || [], a = (res && res.achievements) || [], b = (res && res.bonuses) || [];
  if (res && res.me) { S.me = res.me; renderUserbox(); }
  if (!m.length && !a.length && !b.length) return;
  var html = '<div class="celebrate"><div class="big">🎉</div><h2>' + esc(title || "Gratulacje!") + "</h2>";
  m.forEach(function (x) {
    html += '<div class="rw">🎯 <b>Misja ukończona:</b> ' + esc(x.title) + " <b>+" + fmtNum(x.points) + " pkt</b></div>";
  });
  a.forEach(function (x) {
    html += '<div class="rw">🏅 <b>Odznaka:</b> ' + x.icon + " " + esc(x.name) +
      " <b>+" + fmtNum(x.reward_points) + " pkt</b></div>";
  });
  b.forEach(function (x) {
    html += '<div class="rw">📅 <b>Bonus za regularność</b> (' + esc(x.week_key) + '): +' +
      fmtNum(x.bonus) + " pkt</div>";
  });
  html += '<button class="btn btn-primary mt" onclick="closeModal()">Super!</button></div>';
  openModal(html);
}

function handleErr(e) { toast(e.message || "Wystąpił błąd.", "err"); }

/* --- nawigacja --- */
var NAV = [
  ["#/", "🏠 Główna", "home", false],
  ["#/rankingi", "🏆 Rankingi", "rankingi", false],
  ["#/misje", "🎯 Misje", "misje", true],
  ["#/odznaki", "🏅 Odznaki", "odznaki", true],
  ["#/rekordy", "📜 Rekordy", "rekordy", false],
  ["#/ogloszenia", "📢 Ogłoszenia", "ogloszenia", false],
  ["#/konkursy", "🎖️ Konkursy", "konkursy", false],
  ["#/poradnik", "📖 Poradnik", "poradnik", false]
];
var currentPage = "home";

function renderNav() {
  var nav = document.getElementById("mainnav");
  var html = "";
  NAV.forEach(function (n) {
    if (n[3] && !S.me) return;
    html += '<a href="' + n[0] + '" class="' + (currentPage === n[2] ? "active" : "") + '">' + n[1] + "</a>";
  });
  if (S.me && S.me.role === "admin") {
    html += '<a href="#/admin" class="' + (currentPage === "admin" ? "active" : "") + '">⚙️ Admin</a>';
  }
  nav.innerHTML = html;
  nav.classList.remove("open");
}

function renderUserbox() {
  var box = document.getElementById("userbox");
  if (!S.me) {
    box.innerHTML = '<a href="#/login">Zaloguj</a> <a class="btn btn-small btn-accent" href="#/register">Rejestracja</a>';
    return;
  }
  var pts = S.me.points ? S.me.points.total : 0;
  box.innerHTML = '<span class="chip">⭐ ' + fmtNum(pts) + " pkt</span> " +
    '<a href="#/profil" title="Mój profil">' + baseIcon(S.me.avatar_base) + " " + esc(S.me.name.split(" ")[0]) + "</a> " +
    '<a href="#" id="logout" title="Wyloguj">⏻</a>';
  document.getElementById("logout").addEventListener("click", function (e) {
    e.preventDefault();
    POST("/api/logout").then(function () {
      S.me = null; renderNav(); renderUserbox(); location.hash = "#/";
      toast("Wylogowano.");
    }).catch(handleErr);
  });
}

/* --- router --- */
function route() {
  var h = (location.hash || "#/").replace(/^#/, "") || "/";
  var app = document.getElementById("app");
  var mUser = h.match(/^\/u\/(\d+)$/);
  var page = "home", param = null;
  if (h === "/" || h === "") page = "home";
  else if (h === "/login") page = "login";
  else if (h === "/register") page = "register";
  else if (h === "/profil") page = "profil";
  else if (h === "/rankingi") page = "rankingi";
  else if (h === "/misje") page = "misje";
  else if (h === "/odznaki") page = "odznaki";
  else if (h === "/rekordy") page = "rekordy";
  else if (h === "/ogloszenia") page = "ogloszenia";
  else if (h === "/konkursy") page = "konkursy";
  else if (h === "/poradnik") page = "poradnik";
  else if (h === "/admin") page = "admin";
  else if (h === "/polityka") page = "polityka";
  else if (mUser) { page = "user"; param = mUser[1]; }
  else page = "notfound";
  if ((page === "profil" || page === "misje" || page === "odznaki") && !S.me) {
    location.hash = "#/login"; return;
  }
  if (page === "admin" && (!S.me || S.me.role !== "admin")) {
    location.hash = "#/"; return;
  }
  currentPage = page;
  renderNav(); renderUserbox();
  app.innerHTML = '<div class="loading">Ładowanie…</div>';
  window.scrollTo(0, 0);
  try {
    Views[page](app, param);
  } catch (e) {
    console.error(e);
    app.innerHTML = '<div class="card"><div class="err">Nie udało się wczytać strony.</div></div>';
  }
}

function refreshMe() {
  return GET("/api/me").then(function (d) {
    S.me = d.me; renderNav(); renderUserbox(); return S.me;
  });
}

function init() {
  document.getElementById("hamburger").addEventListener("click", function () {
    document.getElementById("mainnav").classList.toggle("open");
  });
  Promise.all([GET("/api/meta"), GET("/api/classes"), GET("/api/me")]).then(function (r) {
    S.meta = r[0]; S.classes = r[1].classes; S.me = r[2].me;
    window.addEventListener("hashchange", route);
    route();
  }).catch(function (e) {
    document.getElementById("app").innerHTML =
      '<div class="card"><div class="err">Brak połączenia z serwerem: ' + esc(e.message) + "</div></div>";
  });
}
document.addEventListener("DOMContentLoaded", init);
