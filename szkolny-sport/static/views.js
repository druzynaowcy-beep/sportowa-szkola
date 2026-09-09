/* Widoki SPA. */
var Views = {};

function condText(o) {
  var v = fmtNum(o.cond_value || 0);
  var sp = o.cond_sport && o.cond_sport !== "any" ? " (" + sportMeta(o.cond_sport).name.toLowerCase() + ")" : "";
  var per = {day: "dnia", week: "tygodnia", month: "miesiąca"}[o.cond_period] || "";
  var perW = per ? " w ciągu " + per : "";
  switch (o.cond_type) {
    case "distance_single": return "Jedna aktywność min. " + v + " km" + sp + perW;
    case "distance_total": return "Łącznie " + v + " km" + sp + perW;
    case "active_days": return "Aktywność w min. " + v + " dni" + perW;
    case "activities_count": return "Min. " + v + " aktywności" + perW;
    case "variety": return "Wszystkie 3 rodzaje aktywności" + perW;
    case "weekend_both": return "Aktywność w sobotę i niedzielę";
    case "first_activity": return "Dodaj pierwszą aktywność";
    case "comments_count": return "Skomentuj " + v + " aktywności kolegów";
    case "joins_count": return "Dołącz do wydarzenia z tablicy";
    case "achievements_count": return "Zdobądź " + v + " osiągnięć";
    case "total_distance": return "Łącznie " + v + " km" + sp;
    case "streak": return "Seria " + v + " dni z aktywnością z rzędu";
    case "month_days": return v + " dni z aktywnością w jednym miesiącu";
    case "active_months": return "Aktywność w " + v + " różnych miesiącach";
    case "variety_week": return "3 rodzaje aktywności w jednym tygodniu";
    case "all_sports_day": return "3 rodzaje aktywności jednego dnia";
    case "activities_count_all": return v + " aktywności łącznie";
    case "sports_min_each": return "Min. " + v + " km w każdym z 3 sportów";
    case "comments_given": return "Napisz " + v + " komentarzy";
    case "likes_given": return "Rozdaj " + v + " polubień";
    case "likes_received": return "Zbierz " + v + " polubień";
    case "announcements_created": return "Dodaj ogłoszenie na tablicy";
    case "follows_count": return "Zaobserwuj " + v + " osób";
    case "marathon_month": return "Przebiegnij 42,2 km w jednym miesiącu";
    case "bike100_week": return "Przejedź 100 km rowerem w jednym tygodniu";
    case "longest_activity": return "Pojedyncza aktywność min. " + v + " km";
    case "longest_sport": return "Jeden bieg min. " + v + " km";
    case "points_total": return "Zdobądź łącznie " + v + " pkt";
    case "missions_completed": return "Ukończ " + v + " różnych misji";
    case "monthly_mission": return "Ukończ misję miesięczną";
    default:
      if (o.cond_type === "activities_count" && !o.cond_period) return v + " aktywności łącznie";
      return "Spełnij warunek wyzwania";
  }
}
function periodLabel(kind, key) {
  if (kind === "dzienna") return "📆 Dziś (" + fmtDate(key) + ")";
  if (kind === "tygodniowa") return "📆 Tydzień " + key;
  if (kind === "miesieczna") return "📆 " + fmtMonth(key);
  return "✨ Wyzwanie specjalne";
}
function rerender() { route(); }

/* ---------- element listy aktywnosci ---------- */
function feedItem(a) {
  var sm = sportMeta(a.type), u = a.user || {};
  var canDel = S.me && (S.me.id === a.user_id || S.me.role === "admin");
  return '<div class="feed-item" data-id="' + a.id + '">' +
    '<div class="feed-head"><span class="ava">' + baseIcon(u.avatar_base) + "</span><div>" +
    '<b><a href="#/u/' + a.user_id + '">' + esc(u.name || "?") + "</a></b> " +
    (u.class_name ? '<span class="chip">' + esc(u.class_name) + "</span>" : "") +
    '<div class="small muted">' + fmtDate(a.date) + " · " + sm.icon + " " + sm.name +
    " · " + esc(providerName(a.provider)) + "</div></div></div>" +
    '<div class="feed-body"><b>' + fmtNum(a.distance_km) + " km</b>" +
    (a.duration_min ? " · " + a.duration_min + " min" : "") +
    ' · <span class="chip green">+' + fmtNum(a.points) + " pkt</span></div>" +
    '<div class="feed-actions">' +
    (S.me ? '<button class="like-btn' + (a.liked ? " liked" : "") + '" data-act="like" data-id="' + a.id + '">👍 <span>' + a.likes + "</span></button>"
          : '<span class="chip">👍 ' + a.likes + "</span>") +
    '<button class="like-btn" data-act="comments" data-id="' + a.id + '">💬 <span>' + a.comments_count + "</span></button>" +
    (canDel ? '<button class="btn btn-small btn-danger" data-act="del" data-id="' + a.id + '">Usuń</button>' : "") +
    "</div><div class=\"comments\" hidden></div></div>";
}

function bindFeed(app) {
  app.querySelectorAll("[data-act]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var id = btn.getAttribute("data-id"), act = btn.getAttribute("data-act");
      var item = btn.closest(".feed-item");
      if (act === "like") {
        var liked = btn.classList.contains("liked");
        (liked ? DEL("/api/activities/" + id + "/like") : POST("/api/activities/" + id + "/like"))
          .then(function (d) {
            btn.classList.toggle("liked", !liked);
            btn.querySelector("span").textContent = d.likes;
            if (d.achievements && d.achievements.length) celebrate(d, "Nowa odznaka!");
          }).catch(handleErr);
      } else if (act === "del") {
        if (!confirm("Usunąć tę aktywność?")) return;
        DEL("/api/activities/" + id).then(function () {
          item.remove(); refreshMe(); toast("Usunięto aktywność.");
        }).catch(handleErr);
      } else if (act === "comments") {
        var box = item.querySelector(".comments");
        if (box.hidden) {
          box.hidden = false;
          loadComments(id, box, btn);
        } else box.hidden = true;
      }
    });
  });
}
function loadComments(id, box, btn) {
  GET("/api/activities/" + id + "/comments").then(function (d) {
    var html = d.items.length ? d.items.map(function (c) {
      return '<div class="comment"><b><a href="#/u/' + c.user_id + '">' + esc(c.user_name) + "</a></b>" +
        (c.class_name ? ' <span class="chip">' + esc(c.class_name) + "</span>" : "") +
        ": " + esc(c.content) + "</div>";
    }).join("") : '<div class="muted small">Brak komentarzy. Bądź pierwszy!</div>';
    if (S.me) {
      html += '<form class="comment-form"><input class="input" name="content" maxlength="500" placeholder="Napisz komentarz…" required>' +
        '<button class="btn btn-small btn-primary">Wyślij</button></form>';
    }
    box.innerHTML = html;
    var form = box.querySelector("form");
    if (form) form.addEventListener("submit", function (e) {
      e.preventDefault();
      var content = form.content.value.trim();
      if (!content) return;
      POST("/api/activities/" + id + "/comments", {content: content}).then(function (r) {
        form.content.value = "";
        loadComments(id, box, btn);
        var cnt = btn.querySelector("span");
        cnt.textContent = parseInt(cnt.textContent, 10) + 1;
        celebrate(r, "Aktywność społeczna!");
      }).catch(handleErr);
    });
  }).catch(handleErr);
}

/* ---------- strona glowna ---------- */
Views.home = function (app) {
  Promise.all([GET("/api/top"), GET("/api/contests"), GET("/api/feed?limit=10")]).then(function (r) {
    var top = r[0], contests = r[1].items, feed = r[2].items;
    var active = contests.filter(function (c) { return c.status === "aktywny"; });
    var finished = contests.filter(function (c) { return c.status !== "aktywny"; });
    function topCard(t, title, icon) {
      var cards = t.top.length ? t.top.map(function (u, i) {
        return '<div class="top-card' + (i === 0 ? " first" : "") + '"><div class="medal">' + medal(i) + "</div>" +
          '<div class="avatar-sm">' + baseIcon(u.avatar_base) + "</div>" +
          '<div class="nm"><a href="#/u/' + u.id + '">' + esc(u.name) + "</a></div>" +
          '<div class="small muted">' + esc(u.class_name || "") + "</div>" +
          '<div><span class="chip gold">' + fmtNum(u.points) + " pkt</span></div></div>";
      }).join("") : '<div class="muted">Brak punktów w tym okresie.</div>';
      return '<div class="card"><h3>' + icon + " " + title + '</h3><div class="small muted">' + esc(t.label) +
        " (" + fmtDate(t.start) + " – " + fmtDate(t.end) + ")</div><div class=\"top3 mt\">" + cards + "</div></div>";
    }
    var html = "";
    if (!S.me) {
      html += '<div class="hero"><h1>🏆 Sportowa Szkoła</h1><p>Biegaj, jeźdź na rowerze i spaceruj. Zdobywaj punkty, odznaki i pnij się w rankingu szkoły!</p>' +
        '<div class="btn-row" style="justify-content:center"><a class="btn btn-accent" href="#/register">Załóż konto</a>' +
        '<a class="btn btn-ghost" style="color:#fff;border-color:#fff" href="#/login">Zaloguj się</a></div></div>';
    } else {
      html += '<div class="hero"><h1>Cześć, ' + esc(S.me.name.split(" ")[0]) + "! 👋</h1>" +
        "<p>Masz <b>" + fmtNum(S.me.points.total) + " pkt</b>. " +
        (S.me.role === "uczen" ? "Dodaj aktywność i walcz o podium!" : "Miłego dnia!") + "</p>" +
        '<div class="btn-row" style="justify-content:center"><a class="btn btn-accent" href="#/profil">➕ Dodaj aktywność</a>' +
        '<a class="btn btn-ghost" style="color:#fff;border-color:#fff" href="#/rankingi">🏆 Ranking</a></div></div>';
    }
    if (finished.length && finished[0].winner) {
      var f = finished[0];
      html += '<div class="card contest finished">🎉 <b>' + esc(f.title) + " – zwycięzca: </b>" +
        '<a href="#/u/' + f.winner.id + '">' + esc(f.winner.name) + "</a> (" + fmtNum(f.winner_points || 0) + " pkt)</div>";
    }
    html += topCard(top.week, "Najbardziej aktywni – tydzień", "🔥");
    html += topCard(top.month, "Najbardziej aktywni – miesiąc", "⭐");
    html += topCard(top.year, "Najbardziej aktywni – rok szkolny", "👑");
    if (active.length) {
      html += '<div class="card contest"><h3>🎖️ Aktywne konkursy</h3>' + active.map(function (c) {
        return "<div><b>" + esc(c.title) + "</b> <span class=\"small muted\">(" + fmtDate(c.start_date) +
          " – " + fmtDate(c.end_date) + ")</span><div class=\"small\">" + esc(c.description || "") + "</div></div>";
      }).join("") + "</div>";
    }
    html += '<div class="card"><h3>📰 Ostatnie aktywności</h3><div id="feed">' +
      (feed.length ? feed.map(feedItem).join("") : '<div class="muted">Brak aktywności.</div>') +
      '</div><div class="center mt"><button class="btn" id="more">Pokaż więcej</button></div></div>';
    app.innerHTML = html;
    bindFeed(app);
    var offset = 10;
    document.getElementById("more").addEventListener("click", function () {
      GET("/api/feed?limit=10&offset=" + offset).then(function (d) {
        if (!d.items.length) { toast("To już wszystkie aktywności."); return; }
        var wrap = document.getElementById("feed");
        var div = document.createElement("div");
        div.innerHTML = d.items.map(feedItem).join("");
        wrap.appendChild(div); bindFeed(div);
        offset += 10;
      }).catch(handleErr);
    });
  }).catch(handleErr);
};

/* ---------- logowanie / rejestracja ---------- */
Views.login = function (app) {
  if (S.me) { location.hash = "#/profil"; return; }
  var sCfgL = S.meta.integrations && S.meta.integrations.strava_configured;
  app.innerHTML = '<div class="card" style="max-width:440px;margin:0 auto"><h2>🔑 Logowanie</h2>' +
    (sCfgL ? '<div class="center"><a class="btn btn-accent" style="width:100%" href="/strava/login">🟠 Zaloguj przez Stravę</a></div><p class="small muted center">lub kontem szkolnym:</p>' : "") +
    '<form class="form" id="f"><label>E-mail</label><input class="input" name="email" type="email" required>' +
    '<label>Hasło</label><input class="input" name="password" type="password" required>' +
    '<div class="mt"><button class="btn btn-primary" style="width:100%">Zaloguj się</button></div></form>' +
    '<p class="small muted center">Nie masz konta? <a href="#/register">Zarejestruj się</a></p>' +
    '<div class="small muted">Konta demo: <b>admin@szkola.pl / admin123</b>, <b>anna.kowalska@szkola.pl / uczen123</b>, <b>marek.tomaszewski@szkola.pl / nauczyciel123</b></div></div>';
  document.getElementById("f").addEventListener("submit", function (e) {
    e.preventDefault();
    POST("/api/login", {email: e.target.email.value, password: e.target.password.value}).then(function (d) {
      S.me = d.me; renderNav(); renderUserbox(); location.hash = "#/profil"; toast("Witaj, " + S.me.name + "!");
    }).catch(handleErr);
  });
};
Views.register = function (app) {
  if (S.me) { location.hash = "#/profil"; return; }
  var opts = S.classes.map(function (c) { return '<option value="' + c.id + '">' + esc(c.name) + "</option>"; }).join("");
  var sCfgR = S.meta.integrations && S.meta.integrations.strava_configured;
  app.innerHTML = '<div class="card" style="max-width:480px;margin:0 auto"><h2>📝 Rejestracja ucznia</h2>' +
    (sCfgR ? '<div class="center"><a class="btn btn-accent" style="width:100%" href="/strava/login">🟠 Załóż konto przez Stravę</a></div><p class="small muted center">lub załóż konto szkolne:</p>' : "") +
    '<form class="form" id="f"><label>Imię i nazwisko</label><input class="input" name="name" required minlength="2">' +
    '<label>E-mail</label><input class="input" name="email" type="email" required>' +
    '<label>Hasło (min. 6 znaków)</label><input class="input" name="password" type="password" required minlength="6">' +
    '<label>Klasa</label><select class="select" name="class_id"><option value="">— wybierz —</option>' + opts + "</select>" +
    '<label class="check"><input type="checkbox" name="rodo" required><span>Akceptuję <a href="#/polityka" target="_blank">politykę prywatności</a> i wyrażam zgodę na przetwarzanie danych (RODO). *</span></label>' +
    '<div class="mt"><button class="btn btn-accent" style="width:100%">Załóż konto</button></div></form>' +
    '<p class="small muted">Kontynuując, potwierdzasz zapoznanie się z zasadami. Zmiana klasy możliwa tylko przez administratora.</p></div>';
  document.getElementById("f").addEventListener("submit", function (e) {
    e.preventDefault();
    var fd = {name: e.target.name.value, email: e.target.email.value, password: e.target.password.value,
      class_id: e.target.class_id.value ? parseInt(e.target.class_id.value, 10) : null, rodo: e.target.rodo.checked};
    POST("/api/register", fd).then(function (d) {
      S.me = d.me; renderNav(); renderUserbox(); location.hash = "#/profil"; toast("Konto utworzone. Powodzenia! 🎉");
    }).catch(handleErr);
  });
};

/* ---------- moj profil ---------- */
Views.profil = function (app) {
  Promise.all([GET("/api/stats/mine"), GET("/api/connections"), GET("/api/activities?user_id=mine&limit=30"), GET("/api/strava/status")])
    .then(function (r) {
      var st = r[0], conns = r[1].connections, acts = r[2].items, me = S.me, stv = r[3];
      var classCard = (!me.class_id ? '<div class="card" style="border:2px solid var(--accent)"><h3>🏫 Wybierz swoją klasę</h3>' +
        '<form class="form" id="classf"><label>Klasa (wybór jednorazowy – późniejsza zmiana tylko przez admina)</label>' +
        '<select class="select" name="class_id">' + S.classes.map(function (c) {
          return '<option value="' + c.id + '">' + esc(c.name) + "</option>";
        }).join("") + '</select><div class="mt"><button class="btn btn-small btn-accent">Zapisz klasę</button></div></form></div>' : "");
      if (stv.flash) toast(stv.flash, /nie uda|błąd|anulow|wygas/i.test(stv.flash) ? "err" : "ok");
      var equipped = (me.avatar_items || []).map(function (id) { return {id: id, name: itemName(id), icon: itemIcon(id)}; });
      var weekly = st.weekly_series.map(function (w) {
        return {label: fmtDate(w.start).slice(0, 5), value: w.points};
      });
      var donutHtml = donut([
        {label: "Bieg", value: st.dist_total.bieg || 0, color: "#e53935"},
        {label: "Rower", value: st.dist_total.rower || 0, color: "#1976d2"},
        {label: "Spacer", value: st.dist_total.spacer || 0, color: "#43a047"}
      ]);
      var html = classCard + '<div class="grid g2">' +
        '<div class="card"><div class="center">' + avatarHTML(baseIcon(me.avatar_base), equipped) +
        "<h2>" + esc(me.name) + "</h2>" +
        (me.class_name ? '<span class="chip">' + esc(me.class_name) + "</span> " : "") +
        '<span class="chip">' + (me.role === "uczen" ? "uczeń" : esc(me.role)) + "</span> " +
        '<div class="mt"><span class="chip gold" style="font-size:16px">⭐ ' + fmtNum(me.points.total) + " pkt</span></div>" +
        '<div class="small muted mt">🏃 aktywności: ' + fmtNum(me.points.aktywnosci) + " · 🎯 misje: " + fmtNum(me.points.misje) +
        " · 📅 regularność: " + fmtNum(me.points.regularnosc) + " · 🏅 odznaki: " + fmtNum(me.points.osiagniecia) + "</div>" +
        '<div class="mt btn-row" style="justify-content:center"><button class="btn btn-small" id="editAva">🎨 Edytuj postać i profil</button></div>' +
        "</div></div>" +
        '<div class="card"><h3>📊 Statystyki</h3><div class="stat-grid">' +
        stat(fmtNum(st.dist_total.any) + " km", "dystans łącznie") +
        stat(st.total_activities, "aktywności") +
        stat(st.streak + " dni", "najdłuższa seria") +
        stat("#" + (st.rank_school || "—"), "miejsce w szkole") +
        stat(me.class_name ? "#" + (st.rank_class || "—") : "—", "miejsce w klasie") +
        stat(fmtNum(st.weekly_avg8) + " pkt", "śr. tygodniowa (8 tyg.)") +
        stat(fmtNum(st.best_week.points) + " pkt", "najlepszy tydzień") +
        stat(fmtNum(st.best_month.points) + " pkt", "najlepszy miesiąc") +
        stat(st.missions_done, "misji ukończonych") +
        stat(st.achievements_count, "zdobytych odznak") +
        "</div></div></div>" +
        '<div class="card"><h3>🔑 Zmiana hasła</h3><form class="form" id="pwf"><div class="form-row"><div><label>Obecne hasło</label><input class="input" name="current" type="password" required></div><div><label>Nowe hasło (min. 6 znaków)</label><input class="input" name="new" type="password" required minlength="6"></div></div><div class="mt"><button class="btn btn-small">Zmień hasło</button></div></form></div>' +
        '<div class="grid g2"><div class="card"><h3>📈 Punkty – ostatnie 8 tygodni</h3>' + barChart(weekly) + "</div>" +
        '<div class="card"><h3>🚴 Podział dystansu (km)</h3>' + donutHtml +
        '<div class="small muted center mt">Ten miesiąc: <b>' + fmtNum(st.month_now.points) + " pkt</b> · Poprzedni: <b>" +
        fmtNum(st.month_prev.points) + " pkt</b></div></div></div>" +
        '<div class="card"><h3>🔗 Połączone konta sportowe</h3><div class="grid auto">' +
        (function () { var stravaCfg = S.meta.integrations && S.meta.integrations.strava_configured; return conns.map(function (c) {
          var status = c.connected
            ? (c.real ? "✅ Połączono <b>(prawdziwe)</b>" + (c.athlete ? " – " + esc(c.athlete) : "") : "✅ Połączono (demo)")
            : "❌ Nie połączono";
          var btns;
          if (c.connected) {
            btns = '<button class="btn btn-small btn-primary" data-sync="' + c.id + '">🔄 Synchronizuj' + (c.real ? "" : " (demo)") + "</button>" +
              '<button class="btn btn-small" data-disc="' + c.id + '">Odłącz</button>';
          } else if (c.id === "strava" && stravaCfg) {
            btns = '<a class="btn btn-small btn-accent" href="/strava/connect">🔗 Połącz przez Strava</a>';
          } else {
            btns = '<button class="btn btn-small btn-accent" data-conn="' + c.id + '">Połącz (demo)</button>';
          }
          return '<div class="mission' + (c.connected ? " done" : "") + '"><b>' + esc(c.name) + "</b><div class=\"small\">" +
            status + '</div><div class="mt btn-row">' + btns + "</div></div>";
        }).join("") + '</div><p class="small muted">Synchronizacja pobiera Twoje aktywności (bieg, rower, spacer) i przelicza je na punkty.' +
        (stravaCfg ? " Strava: <b>prawdziwa integracja</b> (logowanie przez Stravę)." : " Tryb demo – administrator może włączyć prawdziwą Stravę w panelu (zakładka Integracje).") + "</p></div>" +
        '<div class="card" style="background:#f8fafc"><b>⌚ Zegarek sportowy lub inna aplikacja?</b>' +
        '<div class="small">Większość urządzeń (<b>Garmin, Polar, Suunto, Coros, Apple Watch, Samsung, Amazfit, Huawei…</b>) może <b>automatycznie przesyłać treningi do Stravy</b>. Włącz synchronizację ze Stravą w aplikacji swojego zegarka (zwykle: Ustawienia → Połączone aplikacje / Partnerzy), a tutaj połącz konto Strava – treningi spłyną same, nic więcej nie trzeba robić.</div></div>'; })() +
        '<div class="card"><h3>➕ Dodaj aktywność ręcznie</h3><form class="form" id="addAct"><div class="form-row">' +
        '<div><label>Rodzaj</label><select class="select" name="type">' +
        S.meta.sports.map(function (s) {
          return '<option value="' + s.id + '">' + s.icon + " " + s.name + " (" + String(s.mult).replace(".", ",") + " pkt/km)</option>";
        }).join("") + '</select></div><div><label>Dystans (km)</label><input class="input" name="distance_km" type="number" step="0.1" min="0.1" max="500" required></div>' +
        '<div><label>Data</label><input class="input" name="date" type="date" value="' + new Date().toISOString().slice(0, 10) + '" required></div>' +
        '<div><label>Czas (min, opcjonalnie)</label><input class="input" name="duration_min" type="number" min="0" max="1440"></div>' +
        '</div><div class="mt"><button class="btn btn-primary">Zapisz aktywność</button></div></form></div>' +
        '<div class="card"><h3>🗂️ Moje aktywności</h3>' +
        (acts.length ? acts.map(feedItem).join("") : '<div class="muted">Brak aktywności. Dodaj pierwszą powyżej!</div>') + "</div>";
      app.innerHTML = html;
      bindFeed(app);
      app.querySelectorAll("[data-conn]").forEach(function (b) {
        b.addEventListener("click", function () {
          POST("/api/connect/" + b.getAttribute("data-conn")).then(function () {
            toast("Połączono konto."); refreshMe().then(rerender);
          }).catch(handleErr);
        });
      });
      app.querySelectorAll("[data-disc]").forEach(function (b) {
        b.addEventListener("click", function () {
          DEL("/api/connect/" + b.getAttribute("data-disc")).then(function () {
            toast("Odłączono konto."); refreshMe().then(rerender);
          }).catch(handleErr);
        });
      });
      app.querySelectorAll("[data-sync]").forEach(function (b) {
        b.addEventListener("click", function () {
          b.disabled = true; b.textContent = "Synchronizacja…";
          POST("/api/sync/" + b.getAttribute("data-sync")).then(function (d) {
            if (!d.created.length) toast("Brak nowych aktywności.");
            else toast("Zsynchronizowano " + d.created.length + " aktywności! 🎉", "ok");
            celebrate(d, "Synchronizacja zakończona!");
            refreshMe().then(rerender);
          }).catch(function (e) { handleErr(e); rerender(); });
        });
      });
      document.getElementById("addAct").addEventListener("submit", function (e) {
        e.preventDefault();
        POST("/api/activities", {type: e.target.type.value, distance_km: e.target.distance_km.value,
          date: e.target.date.value, duration_min: e.target.duration_min.value || 0}).then(function (d) {
          toast("Dodano aktywność: +" + fmtNum(d.activity.points) + " pkt 🎉", "ok");
          celebrate(d, "Aktywność zapisana!");
          refreshMe().then(rerender);
        }).catch(handleErr);
      });
      document.getElementById("editAva").addEventListener("click", avatarModal);
      document.getElementById("pwf").addEventListener("submit", function (e) {
        e.preventDefault();
        POST("/api/me/password", {current: e.target.current.value, new: e.target.new.value}).then(function () {
          e.target.reset(); toast("Hasło zmienione. 🔑", "ok");
        }).catch(handleErr);
      });
      var cf = document.getElementById("classf");
      if (cf) cf.addEventListener("submit", function (e) {
        e.preventDefault();
        PUT("/api/me", {class_id: parseInt(e.target.class_id.value, 10)}).then(function (d) {
          S.me = d.me; toast("Zapisano klasę. 🏫", "ok"); rerender();
        }).catch(handleErr);
      });
    }).catch(handleErr);
};
function stat(v, l) { return '<div class="stat"><div class="v">' + v + '</div><div class="l">' + l + "</div></div>"; }

function avatarModal() {
  var selBase = S.me.avatar_base, selItems = (S.me.avatar_items || []).slice();
  function draw() {
    var avail = S.me.avatar_items_available || [];
    var html = "<h2>🎨 Twoja postać</h2>" +
      '<div class="center">' + avatarHTML(baseIcon(selBase), selItems.map(function (id) {
        return {name: itemName(id), icon: itemIcon(id)};
      })) + "</div>" +
      '<form class="form" id="pname"><label>Imię i nazwisko</label>' +
      '<input class="input" name="name" value="' + esc(S.me.name) + '"></form>' +
      "<h3>Postać</h3><div class=\"pick-grid\">" + S.meta.avatar_bases.map(function (b) {
        return '<div class="pick' + (selBase === b.id ? " sel" : "") + '" data-base="' + b.id + '"><div class="ic">' +
          b.icon + '</div><div class="nm">' + esc(b.name) + "</div></div>";
      }).join("") + "</div><h3 class=\"mt\">Dodatki (kliknij, aby założyć/zdjąć)</h3><div class=\"pick-grid\">" +
      avail.map(function (it) {
        var lock = it.unlocked ? "" : " lock";
        var sel = selItems.indexOf(it.id) >= 0 ? " sel" : "";
        var req = it.unlocked ? (it.via_reward ? "🎁 nagroda" : "odblokowany") : "od " + fmtNum(it.min_points) + " pkt";
        return '<div class="pick' + lock + sel + '" data-item="' + it.id + '"><div class="ic">' + it.icon +
          '</div><div class="nm">' + esc(it.name) + '</div><div class="rq">' + req + "</div></div>";
      }).join("") + '</div><div class="mt btn-row"><button class="btn btn-primary" id="saveAva">💾 Zapisz</button>' +
      '<button class="btn" onclick="closeModal()">Anuluj</button></div>';
    openModal(html);
    document.querySelectorAll("[data-base]").forEach(function (el) {
      el.addEventListener("click", function () { selBase = el.getAttribute("data-base"); draw(); });
    });
    document.querySelectorAll("[data-item]").forEach(function (el) {
      el.addEventListener("click", function () {
        var id = el.getAttribute("data-item");
        if (el.classList.contains("lock")) { toast("Odblokuj ten dodatek, zdobywając punkty lub nagrody.", "err"); return; }
        var i = selItems.indexOf(id);
        if (i >= 0) selItems.splice(i, 1); else selItems.push(id);
        draw();
      });
    });
    document.getElementById("saveAva").addEventListener("click", function () {
      var name = document.querySelector("#pname input").value;
      PUT("/api/me", {name: name, avatar_base: selBase, avatar_items: selItems}).then(function (d) {
        S.me = d.me; renderUserbox(); closeModal(); rerender(); toast("Zapisano profil. 🎨", "ok");
      }).catch(handleErr);
    });
  }
  draw();
}

/* ---------- profil publiczny ---------- */
Views.user = function (app, id) {
  GET("/api/users/" + id).then(function (u) {
    var equipped = (u.avatar_items || []).map(function (x) { return {name: itemName(x), icon: itemIcon(x)}; });
    var followBtn = "";
    if (S.me && S.me.id !== u.id) {
      followBtn = u.followed
        ? '<button class="btn btn-small" id="unf">✔ Obserwujesz – przestań</button>'
        : '<button class="btn btn-small btn-primary" id="fol">➕ Obserwuj</button>';
    }
    app.innerHTML = '<div class="card"><div class="center">' + avatarHTML(baseIcon(u.avatar_base), equipped) +
      "<h2>" + esc(u.name) + "</h2>" +
      (u.class_name ? '<span class="chip">' + esc(u.class_name) + "</span> " : "") +
      '<span class="chip gold">⭐ ' + fmtNum(u.points.total) + " pkt</span> " +
      '<span class="chip">👀 ' + u.followers + " obserwujących</span>" +
      '<div class="mt">' + followBtn + "</div></div></div>" +
      '<div class="card"><h3>📊 W skrócie</h3><div class="stat-grid">' +
      stat(fmtNum(u.stats.dist_total.any) + " km", "dystans") +
      stat(u.stats.total_activities, "aktywności") +
      stat(u.stats.streak + " dni", "najdłuższa seria") +
      stat("#" + (u.stats.rank_school || "—"), "miejsce w szkole") +
      stat(u.stats.achievements_count, "odznak") +
      "</div></div>" +
      '<div class="card"><h3>🏅 Ostatnie odznaki</h3><div class="badge-grid">' +
      (u.achievements_recent.length ? u.achievements_recent.map(function (a) {
        a.unlocked = true;
        return '<div class="badge-cell">' + badgeSVG(a, 64) + '<div class="bn">' + esc(a.name) + "</div></div>";
      }).join("") : '<div class="muted">Brak odznak.</div>') + "</div></div>" +
      '<div class="card"><h3>📰 Ostatnie aktywności</h3>' +
      (u.recent.length ? u.recent.map(feedItem).join("") : '<div class="muted">Brak aktywności.</div>') + "</div>";
    bindFeed(app);
    var fol = document.getElementById("fol"), unf = document.getElementById("unf");
    if (fol) fol.addEventListener("click", function () {
      POST("/api/follow/" + u.id).then(function (d) { celebrate(d, "Obserwujesz!"); rerender(); }).catch(handleErr);
    });
    if (unf) unf.addEventListener("click", function () {
      DEL("/api/follow/" + u.id).then(rerender).catch(handleErr);
    });
  }).catch(handleErr);
};

/* ---------- rankingi ---------- */
var RK = {tab: "ind", page: 1, classId: ""};
Views.rankingi = function (app) {
  var classOpts = '<option value="">Wszystkie klasy</option>' + S.classes.map(function (c) {
    return '<option value="' + c.id + '"' + (String(RK.classId) === String(c.id) ? " selected" : "") + ">" + esc(c.name) + "</option>";
  }).join("");
  app.innerHTML = '<div class="card"><h2>🏆 Rankingi</h2><div class="tabs">' +
    '<button data-t="ind" class="' + (RK.tab === "ind" ? "active" : "") + '">👤 Indywidualny</button>' +
    '<button data-t="klasa" class="' + (RK.tab === "klasa" ? "active" : "") + '">🏫 Moja klasa</button>' +
    '<button data-t="klasy" class="' + (RK.tab === "klasy" ? "active" : "") + '">📊 Klasy (szkoła)</button>' +
    '<button data-t="nau" class="' + (RK.tab === "nau" ? "active" : "") + '">🧑‍🏫 Nauczyciele</button></div>' +
    '<div id="rkbody"></div></div>';
  app.querySelectorAll("[data-t]").forEach(function (b) {
    b.addEventListener("click", function () { RK.tab = b.getAttribute("data-t"); RK.page = 1; Views.rankingi(app); });
  });
  var body = document.getElementById("rkbody");
  function pager(p, cb) {
    return '<div class="pager"><button class="btn btn-small" id="pp" ' + (p.page <= 1 ? "disabled" : "") + ">← Poprzednia</button>" +
      "<span>Strona " + p.page + " z " + p.pages + " (" + p.total + ")</span>" +
      '<button class="btn btn-small" id="pn" ' + (p.page >= p.pages ? "disabled" : "") + ">Następna →</button></div>";
  }
  function bindPager(p) {
    var pp = document.getElementById("pp"), pn = document.getElementById("pn");
    if (pp) pp.addEventListener("click", function () { RK.page--; Views.rankingi(app); });
    if (pn) pn.addEventListener("click", function () { RK.page++; Views.rankingi(app); });
  }
  function table(list, startRank) {
    return '<table class="table"><tr><th>#</th><th>Uczeń</th><th>Klasa</th><th>Km</th><th>Punkty</th></tr>' +
      list.map(function (u, i) {
        var r = startRank + i;
        var cls = r === 1 ? "pos1" : r === 2 ? "pos2" : r === 3 ? "pos3" : "";
        var me = S.me && S.me.id === u.id ? " ⭐" : "";
        return "<tr><td><span class=\"rank-pos " + cls + "\">" + (r <= 3 ? medal(r - 1) : r) + "</span></td>" +
          '<td><a href="#/u/' + u.id + '">' + esc(u.name) + "</a>" + me + "</td><td>" + esc(u.class_name || "—") +
          "</td><td>" + fmtNum(u.km) + "</td><td><b>" + fmtNum(u.points) + "</b></td></tr>";
      }).join("") + "</table>";
  }
  if (RK.tab === "klasy") {
    GET("/api/rankings/classes").then(function (d) {
      body.innerHTML = '<table class="table"><tr><th>#</th><th>Klasa</th><th>Uczniowie</th><th>Średnia</th><th>Suma</th><th>Km</th></tr>' +
        d.items.map(function (c, i) {
          var cls = i === 0 ? "pos1" : i === 1 ? "pos2" : i === 2 ? "pos3" : "";
          return "<tr><td><span class=\"rank-pos " + cls + "\">" + (i < 3 ? medal(i) : i + 1) + "</span></td><td><b>" +
            esc(c.name) + "</b></td><td>" + c.count + "</td><td><b>" + fmtNum(c.avg) + "</b></td><td>" +
            fmtNum(c.sum) + "</td><td>" + fmtNum(c.km) + "</td></tr>";
        }).join("") + "</table><p class=\"small muted\">Sortowanie wg średniej punktów na ucznia.</p>";
    }).catch(handleErr);
    return;
  }
  if (RK.tab === "klasa") {
    if (!S.me || !S.me.class_id) { body.innerHTML = '<div class="muted">Zaloguj się na konto ucznia z przypisaną klasą.</div>'; return; }
    GET("/api/rankings/individual?role=uczen&per_page=100&class_id=" + S.me.class_id).then(function (d) {
      body.innerHTML = "<h3>Klasa " + esc(S.me.class_name || "") + "</h3>" + table(d.items, 1);
    }).catch(handleErr);
    return;
  }
  var role = RK.tab === "nau" ? "nauczyciel" : "uczen";
  var url = "/api/rankings/individual?role=" + role + "&page=" + RK.page + "&per_page=15" +
    (RK.tab === "ind" && RK.classId ? "&class_id=" + RK.classId : "");
  GET(url).then(function (d) {
    var html = "";
    if (RK.tab === "ind") {
      html += '<div class="mt" style="margin-bottom:12px"><label class="small muted">Filtruj wg klasy: </label>' +
        '<select class="select" id="rkclass" style="max-width:200px;display:inline-block">' + classOpts + "</select></div>";
    }
    html += table(d.items, (d.page - 1) * d.per_page + 1) + pager(d);
    body.innerHTML = html; bindPager(d);
    var sel = document.getElementById("rkclass");
    if (sel) sel.addEventListener("change", function () { RK.classId = sel.value; RK.page = 1; Views.rankingi(app); });
  }).catch(handleErr);
};

/* ---------- misje ---------- */
Views.misje = function (app) {
  GET("/api/missions").then(function (d) {
    var kinds = ["dzienna", "tygodniowa", "miesieczna", "okazjonalna"];
    var html = '<div class="card"><h2>🎯 Misje</h2><p class="muted">Misje sprawdzane są automatycznie po każdej aktywności. Dzienne i tygodniowe odnawiają się w kolejnych okresach.</p></div>';
    kinds.forEach(function (k) {
      var list = d.items.filter(function (m) { return m.kind === k; });
      if (!list.length) return;
      html += '<div class="card"><h3>' + esc(S.meta.mission_kinds[k]) + "</h3>" +
        '<div class="small muted" style="margin-bottom:10px">' + periodLabel(k, list[0].period_key) + '</div><div class="grid auto">' +
        list.map(function (m) {
          var pct = m.target > 0 ? Math.min(100, Math.round(100 * m.progress / m.target)) : 0;
          return '<div class="mission' + (m.completed ? " done" : "") + '"><div class="mh"><span class="mi">' +
            (m.badge_icon || "🎯") + "</span><div><b>" + esc(m.title) + "</b>" +
            '<div class="small muted">' + esc(m.description || "") + "</div></div></div>" +
            '<div class="small mt">' + esc(condText(m)) + "</div>" +
            '<div class="progress"><div style="width:' + pct + '%"></div></div>' +
            '<div class="small mt">' + fmtNum(m.progress) + " / " + fmtNum(m.target) +
            ' · <span class="chip gold">+' + fmtNum(m.points) + " pkt</span>" +
            (m.avatar_item ? ' · 🎁 <span class="chip">' + itemIcon(m.avatar_item) + " " + esc(itemName(m.avatar_item)) + "</span>" : "") +
            (m.completed ? ' · <span class="chip green">✔ ukończona</span>' : "") + "</div></div>";
        }).join("") + "</div></div>";
    });
    app.innerHTML = html;
  }).catch(handleErr);
};

/* ---------- odznaki ---------- */
var OD = {cat: ""};
Views.odznaki = function (app) {
  GET("/api/achievements?user_id=mine").then(function (d) {
    var cats = Object.keys(S.meta.categories);
    var got = d.items.filter(function (a) { return a.unlocked; }).length;
    var html = '<div class="card"><h2>🏅 Odznaki (' + got + "/" + d.items.length + ")</h2>" +
      '<div class="tabs"><button data-c="" class="' + (OD.cat === "" ? "active" : "") + '">Wszystkie</button>' +
      cats.map(function (c) {
        return '<button data-c="' + c + '" class="' + (OD.cat === c ? "active" : "") + '">' +
          esc(S.meta.categories[c].name) + "</button>";
      }).join("") + '</div><div id="odgrid"></div></div>';
    app.innerHTML = html;
    function draw() {
      var list = d.items.filter(function (a) { return !OD.cat || a.category === OD.cat; });
      var g = document.getElementById("odgrid");
      g.innerHTML = '<div class="badge-grid">' + list.map(function (a) {
        return '<div class="badge-cell' + (a.unlocked ? "" : " locked") + '" data-a="' + a.id + '">' +
          badgeSVG(a, 64) + '<div class="bn">' + esc(a.name) + '</div><div class="pts">+' +
          fmtNum(a.reward_points) + " pkt</div></div>";
      }).join("") + "</div>";
      g.querySelectorAll("[data-a]").forEach(function (el) {
        el.addEventListener("click", function () {
          var a = d.items.filter(function (x) { return x.id === parseInt(el.getAttribute("data-a"), 10); })[0];
          openModal('<div class="center">' + badgeSVG(a, 110) + "<h2>" + esc(a.name) + "</h2>" +
            "<p>" + esc(a.description || "") + "</p>" +
            '<p><span class="chip">' + esc(a.category_name) + '</span> <span class="chip">ranga: ' + esc(a.rank) + "</span></p>" +
            "<p><b>Warunek:</b> " + esc(condText(a)) + "</p>" +
            "<p><b>Nagroda:</b> +" + fmtNum(a.reward_points) + " pkt" +
            (a.reward_item ? " + 🎁 " + itemIcon(a.reward_item) + " " + esc(itemName(a.reward_item)) : "") + "</p>" +
            (a.unlocked ? '<p class="chip green">✔ Zdobyta ' + fmtDate(a.unlocked_at) + "</p>"
                        : '<p class="chip red">Do zdobycia</p>') +
            '<div class="mt"><button class="btn" onclick="closeModal()">Zamknij</button></div></div>');
        });
      });
    }
    draw();
    app.querySelectorAll("[data-c]").forEach(function (b) {
      b.addEventListener("click", function () { OD.cat = b.getAttribute("data-c"); Views.odznaki(app); });
    });
  }).catch(handleErr);
};

/* ---------- rekordy ---------- */
Views.rekordy = function (app) {
  GET("/api/records").then(function (d) {
    function holder(u) {
      return u ? '<div class="mt"><span class="avatar-sm">' + baseIcon(u.avatar_base) + '</span><div><b><a href="#/u/' +
        u.id + '">' + esc(u.name) + "</a></b></div>" + '<div class="small muted">' + esc(u.class_name || "") + "</div></div>" : "";
    }
    var html = '<div class="card center"><h2>📜 Księga rekordów</h2><p class="muted">Rekordy aktualizowane są automatycznie.</p></div><div class="grid g2">';
    html += '<div class="card center"><div class="big" style="font-size:44px">🏃</div><h3>Najdłuższy dystans w tygodniu (uczeń)</h3>' +
      (d.week_distance_user ? '<div class="stat"><div class="v">' + fmtNum(d.week_distance_user.km) + ' km</div><div class="l">tydzień ' +
        d.week_distance_user.week + "</div></div>" + holder(d.week_distance_user.user) : '<div class="muted">Brak danych.</div>') + "</div>";
    html += '<div class="card center"><div class="big" style="font-size:44px">🏫</div><h3>Najdłuższy dystans w tygodniu (klasa)</h3>' +
      (d.week_distance_class ? '<div class="stat"><div class="v">' + fmtNum(d.week_distance_class.km) + ' km</div><div class="l">klasa ' +
        esc(d.week_distance_class.class.name) + " · tydzień " + d.week_distance_class.week + "</div></div>"
        : '<div class="muted">Brak danych.</div>') + "</div>";
    html += '<div class="card center"><div class="big" style="font-size:44px">⭐</div><h3>Najwięcej punktów w miesiącu</h3>' +
      (d.month_points ? '<div class="stat"><div class="v">' + fmtNum(d.month_points.points) + ' pkt</div><div class="l">' +
        fmtMonth(d.month_points.month) + "</div></div>" + holder(d.month_points.user) : '<div class="muted">Brak danych.</div>') + "</div>";
    html += '<div class="card center"><div class="big" style="font-size:44px">🔥</div><h3>Najdłuższa seria dni z aktywnością</h3>' +
      (d.streak ? '<div class="stat"><div class="v">' + d.streak.days + ' dni</div><div class="l">z rzędu</div></div>' +
        holder(d.streak.user) : '<div class="muted">Brak danych.</div>') + "</div>";
    app.innerHTML = html + "</div>";
  }).catch(handleErr);
};

/* ---------- ogloszenia ---------- */
Views.ogloszenia = function (app) {
  GET("/api/announcements").then(function (d) {
    var html = '<div class="card"><h2>📢 Tablica ogłoszeń</h2>';
    if (S.me) {
      html += '<form class="form" id="ann"><div class="form-row"><div><label>Tytuł</label>' +
        '<input class="input" name="title" required minlength="3" placeholder="np. Sobota 10:00 – wspólny bieg"></div>' +
        '<div><label>Data wydarzenia (opcjonalnie)</label><input class="input" name="event_date" type="date"></div></div>' +
        '<label>Treść</label><textarea class="input" name="content" required minlength="3"></textarea>' +
        '<div class="mt"><button class="btn btn-primary">Dodaj ogłoszenie</button></div></form>';
    } else html += '<p class="muted">Zaloguj się, aby dodawać ogłoszenia.</p>';
    html += "</div>";
    html += d.items.length ? d.items.map(function (a) {
      var canDel = S.me && (S.me.id === a.user_id || S.me.role === "admin");
      return '<div class="ann"><h3>' + esc(a.title) + "</h3><p>" + esc(a.content) + "</p>" +
        '<div class="small muted"><a href="#/u/' + a.user_id + '">' + esc(a.user_name) + "</a>" +
        (a.class_name ? " (" + esc(a.class_name) + ")" : "") + " · " + fmtDate(a.created_at) +
        (a.event_date ? ' · 📅 <b>' + fmtDate(a.event_date) + "</b>" : "") + "</div>" +
        '<div class="mt btn-row"><span class="chip">🙋 ' + a.joins + " chętnych</span>" +
        (S.me ? (a.joined ? '<button class="btn btn-small btn-ok" data-leave="' + a.id + '">✔ Dołączasz – wypisz się</button>'
                          : '<button class="btn btn-small btn-accent" data-join="' + a.id + '">Dołączę!</button>') : "") +
        (canDel ? '<button class="btn btn-small btn-danger" data-delann="' + a.id + '">Usuń</button>' : "") + "</div></div>";
    }).join("") : '<div class="card muted">Brak ogłoszeń.</div>';
    app.innerHTML = html;
    var f = document.getElementById("ann");
    if (f) f.addEventListener("submit", function (e) {
      e.preventDefault();
      POST("/api/announcements", {title: f.title.value, content: f.content.value, event_date: f.event_date.value})
        .then(function (r) { celebrate(r, "Ogłoszenie dodane!"); rerender(); }).catch(handleErr);
    });
    app.querySelectorAll("[data-join]").forEach(function (b) {
      b.addEventListener("click", function () {
        POST("/api/announcements/" + b.getAttribute("data-join") + "/join").then(function (r) {
          celebrate(r, "Dołączono!"); rerender();
        }).catch(handleErr);
      });
    });
    app.querySelectorAll("[data-leave]").forEach(function (b) {
      b.addEventListener("click", function () {
        DEL("/api/announcements/" + b.getAttribute("data-leave") + "/join").then(rerender).catch(handleErr);
      });
    });
    app.querySelectorAll("[data-delann]").forEach(function (b) {
      b.addEventListener("click", function () {
        if (!confirm("Usunąć ogłoszenie?")) return;
        DEL("/api/announcements/" + b.getAttribute("data-delann")).then(rerender).catch(handleErr);
      });
    });
  }).catch(handleErr);
};

/* ---------- konkursy ---------- */
Views.konkursy = function (app) {
  GET("/api/contests").then(function (d) {
    var active = d.items.filter(function (c) { return c.status === "aktywny"; });
    var fin = d.items.filter(function (c) { return c.status !== "aktywny"; });
    var html = '<div class="card"><h2>🎖️ Konkursy i nagrody</h2><p class="muted">Zwycięzca to uczeń z największą liczbą punktów w okresie konkursu. Nagrody: dyplomy, punkty z WF-u, upominki.</p>';
    if (S.me && S.me.role === "admin") {
      html += '<form class="form" id="cc"><div class="form-row"><div><label>Tytuł</label><input class="input" name="title" required></div>' +
        '<div><label>Opis</label><input class="input" name="description"></div>' +
        '<div><label>Od</label><input class="input" name="start_date" type="date" required></div>' +
        '<div><label>Do</label><input class="input" name="end_date" type="date" required></div></div>' +
        '<div class="mt"><button class="btn btn-accent">Utwórz konkurs</button></div></form>';
    }
    html += "</div><h3>Aktywne</h3>" + (active.length ? active.map(function (c) {
      return '<div class="card contest"><h3>' + esc(c.title) + "</h3><p>" + esc(c.description || "") + "</p>" +
        '<div class="small muted">' + fmtDate(c.start_date) + " – " + fmtDate(c.end_date) + "</div>" +
        (S.me && S.me.role === "admin" ? '<div class="mt btn-row"><button class="btn btn-small btn-primary" data-fin="' + c.id + '">Zakończ i wyłoń zwycięzcę</button>' +
          '<button class="btn btn-small btn-danger" data-delc="' + c.id + '">Usuń</button></div>' : "") + "</div>";
    }).join("") : '<div class="card muted">Brak aktywnych konkursów.</div>');
    html += "<h3>Zakończone</h3>" + (fin.length ? fin.map(function (c) {
      return '<div class="card contest finished"><h3>' + esc(c.title) + "</h3>" +
        '<div class="small muted">' + fmtDate(c.start_date) + " – " + fmtDate(c.end_date) + "</div>" +
        (c.winner ? '<div class="mt">🏆 <b>Zwycięzca:</b> <a href="#/u/' + c.winner.id + '">' + esc(c.winner.name) +
          "</a> (" + fmtNum(c.winner_points || 0) + " pkt)</div>" : '<div class="muted">Brak zwycięzcy.</div>') + "</div>";
    }).join("") : '<div class="card muted">Brak zakończonych konkursów.</div>');
    app.innerHTML = html;
    var f = document.getElementById("cc");
    if (f) f.addEventListener("submit", function (e) {
      e.preventDefault();
      POST("/api/contests", {title: f.title.value, description: f.description.value,
        start_date: f.start_date.value, end_date: f.end_date.value}).then(function () {
        toast("Utworzono konkurs.", "ok"); rerender();
      }).catch(handleErr);
    });
    app.querySelectorAll("[data-fin]").forEach(function (b) {
      b.addEventListener("click", function () {
        POST("/api/contests/" + b.getAttribute("data-fin") + "/finish").then(function (r) {
          toast(r.contest.winner ? "Zwycięzca: " + r.contest.winner.name + " 🏆" : "Brak zwycięzcy.", "ok");
          rerender();
        }).catch(handleErr);
      });
    });
    app.querySelectorAll("[data-delc]").forEach(function (b) {
      b.addEventListener("click", function () {
        if (!confirm("Usunąć konkurs?")) return;
        DEL("/api/contests/" + b.getAttribute("data-delc")).then(rerender).catch(handleErr);
      });
    });
  }).catch(handleErr);
};

/* ---------- admin ---------- */
var AD = {tab: "ov", page: 1, q: "", role: ""};
Views.admin = function (app) {
  app.innerHTML = '<div class="card"><h2>⚙️ Panel administratora</h2><div class="tabs admin-tabs">' +
    '<button data-t="ov" class="' + (AD.tab === "ov" ? "active" : "") + '">📊 Przegląd</button>' +
    '<button data-t="users" class="' + (AD.tab === "users" ? "active" : "") + '">👥 Użytkownicy</button>' +
    '<button data-t="classes" class="' + (AD.tab === "classes" ? "active" : "") + '">🏫 Klasy</button>' +
    '<button data-t="missions" class="' + (AD.tab === "missions" ? "active" : "") + '">🎯 Misje</button>' +
    '<button data-t="exp" class="' + (AD.tab === "exp" ? "active" : "") + '">📥 Eksport</button>' +
    '<button data-t="integr" class="' + (AD.tab === "integr" ? "active" : "") + '">🔌 Integracje</button></div>' +
    '<div id="adbody"></div></div>';
  app.querySelectorAll("[data-t]").forEach(function (b) {
    b.addEventListener("click", function () { AD.tab = b.getAttribute("data-t"); AD.page = 1; Views.admin(app); });
  });
  var body = document.getElementById("adbody");
  if (AD.tab === "ov") {
    GET("/api/admin/overview").then(function (d) {
      body.innerHTML = '<div class="stat-grid">' +
        stat(d.users_by_role.uczen || 0, "uczniów") +
        stat(d.users_by_role.nauczyciel || 0, "nauczycieli") +
        stat(d.activities_total, "aktywności") +
        stat(fmtNum(d.km_total) + " km", "dystans łącznie") +
        stat(d.activities_7d, "aktywności (7 dni)") + "</div>" +
        '<h3 class="mt">Klasy</h3><table class="table"><tr><th>Klasa</th><th>Uczniowie</th><th>Śr. pkt</th><th>Suma</th></tr>' +
        d.classes.map(function (c) {
          return "<tr><td><b>" + esc(c.name) + "</b></td><td>" + c.count + "</td><td>" + fmtNum(c.avg) +
            "</td><td>" + fmtNum(c.sum) + "</td></tr>";
        }).join("") + "</table>";
    }).catch(handleErr);
  } else if (AD.tab === "users") {
    var url = "/api/admin/users?page=" + AD.page + "&per_page=15&q=" + encodeURIComponent(AD.q) + "&role=" + AD.role;
    GET(url).then(function (d) {
      var html = '<div class="btn-row" style="margin-bottom:12px"><input class="input" id="aq" style="max-width:220px" placeholder="Szukaj…" value="' +
        esc(AD.q) + '"><select class="select" id="ar" style="max-width:160px"><option value="">Wszystkie role</option>' +
        ["uczen", "nauczyciel", "admin"].map(function (r) {
          return '<option value="' + r + '"' + (AD.role === r ? " selected" : "") + ">" + r + "</option>";
        }).join("") + '</select><button class="btn btn-small btn-primary" id="as">Szukaj</button></div>' +
        '<table class="table"><tr><th>ID</th><th>Użytkownik</th><th>Rola</th><th>Klasa</th><th>Pkt</th><th></th></tr>' +
        d.items.map(function (u) {
          return "<tr><td>" + u.id + "</td><td><b>" + esc(u.name) + "</b><br><span class=\"small muted\">" + esc(u.email) +
            "</span></td><td>" + esc(u.role) + "</td><td>" + esc(u.class_name || "—") + "</td><td><b>" + fmtNum(u.points) +
            '</b></td><td><div class="btn-row"><button class="btn btn-small" data-ed="' + u.id + '">Edytuj</button>' +
            (S.me.id !== u.id ? '<button class="btn btn-small btn-danger" data-rm="' + u.id + '">Usuń</button>' : "") + "</div></td></tr>";
        }).join("") + "</table>" +
        '<div class="pager"><button class="btn btn-small" id="pp" ' + (d.page <= 1 ? "disabled" : "") + ">←</button><span>" +
        d.page + "/" + d.pages + "</span>" + '<button class="btn btn-small" id="pn" ' + (d.page >= d.pages ? "disabled" : "") + ">→</button></div>";
      body.innerHTML = html;
      document.getElementById("as").addEventListener("click", function () {
        AD.q = document.getElementById("aq").value; AD.role = document.getElementById("ar").value; AD.page = 1;
        Views.admin(app);
      });
      var pp = document.getElementById("pp"), pn = document.getElementById("pn");
      if (pp) pp.addEventListener("click", function () { if (AD.page > 1) { AD.page--; Views.admin(app); } });
      if (pn) pn.addEventListener("click", function () { AD.page++; Views.admin(app); });
      body.querySelectorAll("[data-ed]").forEach(function (b) {
        b.addEventListener("click", function () { editUserModal(parseInt(b.getAttribute("data-ed"), 10)); });
      });
      body.querySelectorAll("[data-rm]").forEach(function (b) {
        b.addEventListener("click", function () {
          if (!confirm("Usunąć użytkownika i wszystkie jego dane? (prawo do bycia zapomnianym)")) return;
          DEL("/api/admin/users/" + b.getAttribute("data-rm")).then(function () {
            toast("Usunięto użytkownika."); Views.admin(app);
          }).catch(handleErr);
        });
      });
    }).catch(handleErr);
  } else if (AD.tab === "classes") {
    body.innerHTML = '<form class="form btn-row" id="nc"><input class="input" name="name" style="max-width:160px" placeholder="np. 5C" required maxlength="10">' +
      '<button class="btn btn-small btn-accent">➕ Dodaj klasę</button></form><div id="clist" class="mt"></div>';
    document.getElementById("nc").addEventListener("submit", function (e) {
      e.preventDefault();
      POST("/api/admin/classes", {name: e.target.name.value}).then(function () {
        GET("/api/classes").then(function (d) { S.classes = d.classes; });
        toast("Dodano klasę.", "ok"); Views.admin(app);
      }).catch(handleErr);
    });
    GET("/api/rankings/classes").then(function (d) {
      document.getElementById("clist").innerHTML = '<table class="table"><tr><th>Klasa</th><th>Uczniowie</th><th>Śr. pkt</th><th></th></tr>' +
        d.items.map(function (c) {
          return "<tr><td><b>" + esc(c.name) + "</b></td><td>" + c.count + "</td><td>" + fmtNum(c.avg) +
            '</td><td><button class="btn btn-small btn-danger" data-rc="' + c.id + '">Usuń</button></td></tr>';
        }).join("") + "</table>";
      body.querySelectorAll("[data-rc]").forEach(function (b) {
        b.addEventListener("click", function () {
          DEL("/api/admin/classes/" + b.getAttribute("data-rc")).then(function () {
            toast("Usunięto klasę."); Views.admin(app);
          }).catch(handleErr);
        });
      });
    }).catch(handleErr);
  } else if (AD.tab === "missions") {
    GET("/api/admin/missions").then(function (d) {
      body.innerHTML = '<button class="btn btn-small btn-accent" id="nmiss">➕ Nowa misja</button>' +
        '<table class="table mt"><tr><th>Tytuł</th><th>Rodzaj</th><th>Warunek</th><th>Pkt</th><th></th></tr>' +
        d.items.map(function (m) {
          return "<tr><td>" + (m.badge_icon || "") + " <b>" + esc(m.title) + "</b>" +
            (m.active ? "" : ' <span class="chip red">wyłączona</span>') + "</td><td>" + esc(m.kind) + "</td><td class=\"small\">" +
            esc(condText(m)) + "</td><td>" + fmtNum(m.points) + '</td><td><div class="btn-row"><button class="btn btn-small" data-em="' +
            m.id + '">Edytuj</button><button class="btn btn-small btn-danger" data-dm="' + m.id + '">Usuń</button></div></td></tr>';
        }).join("") + "</table>";
      document.getElementById("nmiss").addEventListener("click", function () { missionModal(null); });
      body.querySelectorAll("[data-em]").forEach(function (b) {
        b.addEventListener("click", function () {
          var m = d.items.filter(function (x) { return x.id === parseInt(b.getAttribute("data-em"), 10); })[0];
          missionModal(m);
        });
      });
      body.querySelectorAll("[data-dm]").forEach(function (b) {
        b.addEventListener("click", function () {
          if (!confirm("Usunąć misję?")) return;
          DEL("/api/admin/missions/" + b.getAttribute("data-dm")).then(function () { Views.admin(app); }).catch(handleErr);
        });
      });
    }).catch(handleErr);
  } else if (AD.tab === "integr") {
    GET("/api/admin/integrations").then(function (d) {
      var s = d.strava;
      body.innerHTML = "<h3>🟠 Strava (prawdziwa integracja)</h3>" +
        "<p>Status: " + (s.configured ? '<span class="chip green">✔ skonfigurowana (' +
          (s.source === "env" ? "zmienne środowiskowe" : "panel") + ")</span>"
          : '<span class="chip red">✘ nieskonfigurowana – działa tryb demo</span>') +
        ' <span class="chip">' + s.real_users + " prawdziwych połączeń</span></p>" +
        "<p><b>Adres zwrotny (callback) do wpisania w ustawieniach aplikacji Strava:</b></p>" +
        '<p><code style="background:#f1f5f9;padding:6px 10px;border-radius:8px;word-break:break-all">' +
        esc(s.callback_url) + "</code></p>" +
        '<form class="form" id="stravaform"><div class="form-row"><div><label>Client ID</label>' +
        '<input class="input" name="client_id" value="' + esc(s.client_id || "") + '"></div>' +
        '<div><label>Client Secret</label><input class="input" name="client_secret" type="password" placeholder="••••••"></div></div>' +
        '<div class="mt btn-row"><button class="btn btn-primary btn-small">💾 Zapisz klucze</button>' +
        '<button type="button" class="btn btn-small btn-danger" id="stravadel">Wyczyść</button></div></form>' +
        '<div class="card mt" style="background:#f8fafc"><b>Jak uzyskać klucze? (2 min, za darmo)</b><ol class="small">' +
        "<li>Zaloguj się na <b>strava.com</b> → <b>Ustawienia → Moje API</b> (strava.com/settings/api).</li>" +
        "<li>Utwórz aplikację: nazwa np. „Sportowa Szkoła”, kategoria „Education”.</li>" +
        "<li>W polu <b>Authorization Callback Domain</b> wpisz samą domenę z adresu powyżej (bez https:// i bez ścieżki /strava/callback).</li>" +
        "<li>Przepisz <b>Client ID</b> i <b>Client Secret</b> do formularza powyżej i zapisz.</li>" +
        "<li>Uczniowie łączą konta w profilu → „Połącz przez Strava” → logowanie Stravą → Synchronizuj.</li></ol>" +
        '<p class="small muted">Pobierane są aktywności z ostatnich 30 dni (bieg, rower, spacer). Duplikaty są pomijane. Tokeny odświeżają się automatycznie.</p></div>';
      document.getElementById("stravaform").addEventListener("submit", function (e) {
        e.preventDefault();
        POST("/api/admin/integrations/strava", {client_id: e.target.client_id.value,
          client_secret: e.target.client_secret.value}).then(function () {
          toast("Zapisano klucze Strava.", "ok"); Views.admin(app);
        }).catch(handleErr);
      });
      document.getElementById("stravadel").addEventListener("click", function () {
        if (!confirm("Wyczyścić klucze Strava? Prawdziwe połączenia przestaną się synchronizować.")) return;
        DEL("/api/admin/integrations/strava").then(function () { Views.admin(app); }).catch(handleErr);
      });
    }).catch(handleErr);
  } else if (AD.tab === "exp") {
    body.innerHTML = "<p>Pobierz dane szkoły (CSV, otwiera się w Excelu):</p><div class=\"btn-row\">" +
      '<a class="btn" href="/api/admin/export/users">👥 Użytkownicy</a>' +
      '<a class="btn" href="/api/admin/export/activities">🏃 Aktywności</a>' +
      '<a class="btn" href="/api/admin/export/points">⭐ Punkty / ranking</a></div>';
  }
};
function editUserModal(uid) {
  GET("/api/admin/users?q=&role=&page=1&per_page=1000").then(function () {
    openModal("<h2>Edytuj użytkownika #" + uid + '</h2><form class="form" id="eu"><label>Imię i nazwisko</label>' +
      '<input class="input" name="name" id="eun" required><label>Rola</label><select class="select" id="eur">' +
      '<option value="uczen">uczeń</option><option value="nauczyciel">nauczyciel</option><option value="admin">admin</option></select>' +
      '<label>Klasa</label><select class="select" id="euc"><option value="">— brak —</option>' +
      S.classes.map(function (c) { return '<option value="' + c.id + '">' + esc(c.name) + "</option>"; }).join("") +
      '</select><div class="mt btn-row"><button class="btn btn-primary">Zapisz</button>' +
      '<button type="button" class="btn" onclick="closeModal()">Anuluj</button></div></form>');
    GET("/api/users/" + uid).then(function (u) {
      document.getElementById("eun").value = u.name;
    }).catch(function () {});
    document.getElementById("eu").addEventListener("submit", function (e) {
      e.preventDefault();
      PUT("/api/admin/users/" + uid, {name: document.getElementById("eun").value,
        role: document.getElementById("eur").value,
        class_id: document.getElementById("euc").value ? parseInt(document.getElementById("euc").value, 10) : null})
        .then(function () { closeModal(); toast("Zapisano.", "ok"); rerender(); }).catch(handleErr);
    });
  }).catch(handleErr);
}
function missionModal(m) {
  m = m || {title: "", description: "", kind: "tygodniowa", cond_type: "distance_total",
    cond_sport: "any", cond_value: 10, cond_period: "week", points: 10, badge_icon: "🎯", avatar_item: "", active: 1};
  var condTypes = ["distance_single", "distance_total", "active_days", "activities_count", "variety",
    "weekend_both", "first_activity", "comments_count", "joins_count", "achievements_count"];
  openModal("<h2>" + (m.id ? "Edytuj misję" : "Nowa misja") + '</h2><form class="form" id="mm">' +
    '<label>Tytuł</label><input class="input" name="title" value="' + esc(m.title) + '" required>' +
    '<label>Opis</label><input class="input" name="description" value="' + esc(m.description || "") + '">' +
    '<div class="form-row"><div><label>Rodzaj</label><select class="select" name="kind">' +
    Object.keys(S.meta.mission_kinds).map(function (k) {
      return '<option value="' + k + '"' + (m.kind === k ? " selected" : "") + ">" + esc(S.meta.mission_kinds[k]) + "</option>";
    }).join("") + '</select></div><div><label>Typ warunku</label><select class="select" name="cond_type">' +
    condTypes.map(function (t) {
      return '<option value="' + t + '"' + (m.cond_type === t ? " selected" : "") + ">" + t + "</option>";
    }).join("") + "</select></div>" +
    '<div><label>Sport</label><select class="select" name="cond_sport">' +
    ["any", "bieg", "rower", "spacer"].map(function (s) {
      return '<option value="' + s + '"' + (m.cond_sport === s ? " selected" : "") + ">" + s + "</option>";
    }).join("") + '</select></div><div><label>Wartość warunku</label><input class="input" name="cond_value" type="number" step="0.1" value="' +
    m.cond_value + '"></div><div><label>Okres</label><select class="select" name="cond_period">' +
    ["day", "week", "month", "ever"].map(function (p) {
      return '<option value="' + p + '"' + (m.cond_period === p ? " selected" : "") + ">" + p + "</option>";
    }).join("") + '</select></div><div><label>Punkty</label><input class="input" name="points" type="number" step="0.5" value="' +
    m.points + '"></div><div><label>Ikona (emoji)</label><input class="input" name="badge_icon" value="' +
    esc(m.badge_icon || "🎯") + '"></div><div><label>Dodatek-nagroda</label><select class="select" name="avatar_item"><option value="">— brak —</option>' +
    S.meta.avatar_items.map(function (it) {
      return '<option value="' + it.id + '"' + (m.avatar_item === it.id ? " selected" : "") + ">" + it.icon + " " + esc(it.name) + "</option>";
    }).join("") + "</select></div></div>" +
    '<div class="mt btn-row"><button class="btn btn-primary">Zapisz</button>' +
    '<button type="button" class="btn" onclick="closeModal()">Anuluj</button></div></form>');
  document.getElementById("mm").addEventListener("submit", function (e) {
    e.preventDefault();
    var f = e.target, payload = {title: f.title.value, description: f.description.value, kind: f.kind.value,
      cond_type: f.cond_type.value, cond_sport: f.cond_sport.value, cond_value: parseFloat(f.cond_value.value) || 0,
      cond_period: f.cond_period.value, points: parseFloat(f.points.value) || 0,
      badge_icon: f.badge_icon.value, avatar_item: f.avatar_item.value};
    var req = m.id ? PUT("/api/admin/missions/" + m.id, payload) : POST("/api/admin/missions", payload);
    req.then(function () { closeModal(); toast("Zapisano misję.", "ok"); rerender(); }).catch(handleErr);
  });
}

/* ---------- RODO ---------- */
Views.polityka = function (app) {
  app.innerHTML = '<div class="card"><h2>🔒 Polityka prywatności / RODO</h2>' +
    "<p><b>Administrator danych:</b> Szkoła Podstawowa (dane do uzupełnienia przed wdrożeniem).</p>" +
    "<h3>Jakie dane zbieramy?</h3><ul><li>Imię i nazwisko, adres e-mail, klasa, rola w systemie.</li>" +
    "<li>Aktywności sportowe (rodzaj, dystans, data, źródło) – w celu naliczania punktów i rankingów.</li>" +
    "<li>Treści dodawane przez użytkownika (ogłoszenia, komentarze, polubienia).</li></ul>" +
    "<h3>W jakim celu?</h3><p>Prowadzenie szkolnej rywalizacji sportowej, statystyki, rankingi, konkursy – na podstawie zgody użytkownika (art. 6 ust. 1 lit. a RODO). " +
    "W przypadku uczniów niepełnoletnich zgodę wyraża rodzic/opiekun prawny.</p>" +
    "<h3>Twoje prawa</h3><ul><li>Dostęp do danych, ich sprostowanie i usunięcie (prawo do bycia zapomnianym – realizowane przez administratora).</li>" +
    "<li>Ograniczenie przetwarzania, przenoszenie danych, sprzeciw.</li><li>Cofnięcie zgody w dowolnym momencie.</li>" +
    "<li>Skarga do Prezesa UODO.</li></ul>" +
    "<h3>Bezpieczeństwo</h3><p>Hasła przechowywane są w postaci skrótu (hash), połączenie z serwerem powinno być szyfrowane (HTTPS). Dane nie są przekazywane podmiotom trzecim bez zgody.</p>" +
    "<h3>Pliki cookie</h3><p>Strona używa wyłącznie niezbędnego pliku cookie sesji logowania.</p></div>";
};

Views.notfound = function (app) {
  app.innerHTML = '<div class="card center"><h2>404 – Nie znaleziono strony</h2><a class="btn btn-primary" href="#/">🏠 Strona główna</a></div>';
};

window.Views = Views;
