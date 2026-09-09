/* Wspolne funkcje: formatowanie, wykresy SVG, odznaki, awatary. */
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
    return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c];
  });
}
function fmtNum(n) {
  var v = Math.round(Number(n || 0) * 10) / 10;
  return String(v).replace(".", ",");
}
function fmtDate(iso) {
  if (!iso) return "—";
  var d = String(iso).slice(0, 10).split("-");
  if (d.length < 3) return iso;
  return d[2].replace(/^0/, "") + "." + d[1] + "." + d[0];
}
function fmtMonth(mk) {
  var mies = ["styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
    "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień"];
  if (!mk) return "—";
  var y = mk.slice(0, 4), m = parseInt(mk.slice(5, 7), 10);
  return (mies[m - 1] || mk) + " " + y;
}
function medal(i) { return ["🥇", "🥈", "🥉"][i] || (i + 1) + "."; }

function barChart(series, opts) {
  opts = opts || {};
  var W = opts.w || 560, H = opts.h || 220, padL = 8, padB = 34, padT = 28, gap = 10;
  var max = 1;
  series.forEach(function (s) { max = Math.max(max, s.value); });
  var n = Math.max(series.length, 1), bw = (W - padL * 2 - gap * (n - 1)) / n, bars = "";
  series.forEach(function (s, i) {
    var h = Math.max(2, (H - padB - padT) * (s.value / max));
    var x = padL + i * (bw + gap), y = H - padB - h;
    bars += '<rect x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + bw.toFixed(1) +
      '" height="' + h.toFixed(1) + '" rx="5" fill="' + (s.color || "#1976d2") + '"/>';
    bars += '<text x="' + (x + bw / 2).toFixed(1) + '" y="' + (y - 6).toFixed(1) +
      '" text-anchor="middle" font-size="12" font-weight="700" fill="#33475e">' + fmtNum(s.value) + "</text>";
    bars += '<text x="' + (x + bw / 2).toFixed(1) + '" y="' + (H - 8) +
      '" text-anchor="middle" font-size="11" fill="#64748b">' + esc(s.label) + "</text>";
  });
  return '<svg class="chart" viewBox="0 0 ' + W + " " + H + '">' + bars + "</svg>";
}

function donut(parts) {
  var size = 170, r = 60, cx = 85, cy = 85;
  var total = 0;
  parts.forEach(function (p) { total += p.value; });
  total = total || 1;
  var a0 = -Math.PI / 2, segs = "";
  parts.forEach(function (p) {
    var a1 = a0 + 2 * Math.PI * (p.value / total);
    var large = a1 - a0 > Math.PI ? 1 : 0;
    var x0 = cx + r * Math.cos(a0), y0 = cy + r * Math.sin(a0);
    var x1 = cx + r * Math.cos(a1), y1 = cy + r * Math.sin(a1);
    if (p.value > 0) {
      segs += '<path d="M' + cx + "," + cy + " L" + x0.toFixed(1) + "," + y0.toFixed(1) +
        " A" + r + "," + r + " 0 " + large + " 1 " + x1.toFixed(1) + "," + y1.toFixed(1) +
        ' Z" fill="' + p.color + '"/>';
    }
    a0 = a1;
  });
  segs += '<circle cx="' + cx + '" cy="' + cy + '" r="34" fill="#fff"/>' +
    '<text x="' + cx + '" y="' + (cy + 7) + '" text-anchor="middle" font-size="19" font-weight="800" fill="#1b2b3c">' +
    fmtNum(total) + "</text>";
  var legend = '<div class="legend">' + parts.map(function (p) {
    return '<span><i style="background:' + p.color + '"></i>' + esc(p.label) + ": <b>" + fmtNum(p.value) + "</b></span>";
  }).join("") + "</div>";
  return '<div class="center"><svg class="chart" style="max-width:220px" viewBox="0 0 ' + size + " " + size + '">' +
    segs + "</svg>" + legend + "</div>";
}

function badgeSVG(a, size) {
  size = size || 72;
  var un = !!a.unlocked, col = un ? a.color : "#9aa4b0";
  var ring = !un ? "#7d8a99" : a.rank === "legendarny" ? "#FFD700" :
    a.rank === "trudny" ? "#FF9800" : "#ffffff";
  var inner = un ? "rgba(255,255,255,.28)" : "rgba(255,255,255,.18)";
  var filt = un ? "" : ' style="filter:grayscale(1)" opacity=".85"';
  var cls = un && a.rank === "legendarny" ? ' class="shine"' : "";
  return "<svg" + cls + ' width="' + size + '" height="' + size + '" viewBox="0 0 72 72">' +
    '<circle cx="36" cy="36" r="34" fill="' + col + '"/>' +
    '<circle cx="36" cy="36" r="34" fill="none" stroke="' + ring + '" stroke-width="4"/>' +
    '<circle cx="36" cy="36" r="25" fill="' + inner + '"/>' +
    '<text x="36" y="47" text-anchor="middle" font-size="28"' + filt + ">" + a.icon + "</text></svg>";
}

function avatarHTML(baseIcon, items) {
  var its = (items || []).map(function (i) {
    return '<span title="' + esc(i.name || "") + '">' + i.icon + "</span>";
  }).join("");
  return '<div class="avatar-stage"><div class="avatar-base">' + baseIcon + "</div>" +
    '<div class="avatar-items">' + its + "</div></div>";
}

function sportMeta(id) {
  var m = (window.S && S.meta && S.meta.sports || []).filter(function (s) { return s.id === id; })[0];
  return m || {id: id, name: id, icon: "🏅", mult: 1};
}
function providerName(id) {
  var m = (window.S && S.meta && S.meta.providers || []).filter(function (s) { return s.id === id; })[0];
  return m ? m.name : id;
}
function baseIcon(id) {
  var m = (window.S && S.meta && S.meta.avatar_bases || []).filter(function (s) { return s.id === id; })[0];
  return m ? m.icon : "🏃";
}
function itemIcon(id) {
  var m = (window.S && S.meta && S.meta.avatar_items || []).filter(function (s) { return s.id === id; })[0];
  return m ? m.icon : "❔";
}
function itemName(id) {
  var m = (window.S && S.meta && S.meta.avatar_items || []).filter(function (s) { return s.id === id; })[0];
  return m ? m.name : id;
}
