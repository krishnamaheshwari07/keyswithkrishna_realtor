// Original animated props for Keys with Krishna Reels (drawn in-house, no third-party art).
// Each prop: function(id) -> SVG/HTML string. Elements carry data-anim="name:delay:dur" (seconds, relative to scene start).
const GOLD = "#fac951", TEAL = "#032b38", TEAL2 = "#04566b", GREEN = "#00784e", LIME = "#6ebe28", WHITE = "#ffffff", NAVY = "#082035", RED = "#e2574c";
const doc = (lines, w = 420, h = 540) => {
  let l = "";
  for (let i = 0; i < lines; i++) l += `<rect x="40" y="${110 + i * 46}" width="${i % 3 == 2 ? 220 : 340}" height="14" rx="7" fill="#d5dde0"/>`;
  return `<rect width="${w}" height="${h}" rx="22" fill="${WHITE}"/><rect x="40" y="44" width="200" height="26" rx="13" fill="${TEAL2}"/>${l}`;
};
const PROPS = {
  lawyer: () => `
  <svg viewBox="0 0 900 760" class="prop">
    <g data-anim="flyInRight:0.15:0.6" style="transform-origin:450px 380px"><g transform="translate(250,90) rotate(-4)">${doc(8)}
      <path d="M60 480 C 110 430, 150 520, 200 470 S 290 440, 340 480" stroke="${NAVY}" stroke-width="7" fill="none" stroke-linecap="round" pathLength="1" class="draw" data-anim="draw:0.9:0.9"/>
      <rect x="40" y="500" width="340" height="4" fill="#9fb0b5"/></g></g>
    <g data-anim="dropBang:0.55:0.55" style="transform-origin:120px 640px"><g transform="translate(40,360)">
      <rect x="20" y="300" width="230" height="40" rx="14" fill="#c9a03a"/>
      <g transform="rotate(-35 140 150)"><rect x="128" y="120" width="26" height="230" rx="12" fill="#8a6a2a"/>
      <rect x="60" y="40" width="170" height="96" rx="30" fill="${GOLD}"/><rect x="50" y="52" width="26" height="72" rx="10" fill="#c9a03a"/><rect x="214" y="52" width="26" height="72" rx="10" fill="#c9a03a"/></g></g></g>
    <g data-anim="stamp:1.5:0.45" style="transform-origin:640px 560px"><g transform="translate(520,500) rotate(-12)">
      <rect width="250" height="96" rx="14" fill="none" stroke="${GREEN}" stroke-width="10"/>
      <text x="125" y="64" text-anchor="middle" font-family="Inter" font-weight="800" font-size="44" fill="${GREEN}">REVIEWED</text></g></g>
  </svg>`,
  cheque: () => `
  <svg viewBox="0 0 900 760" class="prop">
    <g data-anim="flyInLeft:0.1:0.65" style="transform-origin:450px 360px"><g transform="translate(60,170) rotate(-6)">
      <rect width="780" height="360" rx="26" fill="${WHITE}"/><rect width="780" height="70" rx="26" fill="${TEAL2}"/><rect y="44" width="780" height="26" fill="${TEAL2}"/>
      <text x="40" y="48" font-family="Inter" font-weight="800" font-size="30" fill="${WHITE}">CERTIFIED DRAFT</text>
      <text x="40" y="150" font-family="Inter" font-weight="600" font-size="28" fill="#6b7f85">PAY TO THE ORDER OF</text>
      <rect x="40" y="170" width="460" height="6" rx="3" fill="#c9d3d6"/>
      <rect x="560" y="120" width="180" height="70" rx="14" fill="#eef3f4" stroke="#c9d3d6" stroke-width="3"/>
      <text x="650" y="168" text-anchor="middle" font-family="Inter" font-weight="800" font-size="36" fill="${NAVY}">$ ✓</text>
      <path d="M440 300 C 480 260, 520 330, 560 290 S 640 270, 700 300" stroke="${NAVY}" stroke-width="6" fill="none" stroke-linecap="round" pathLength="1" class="draw" data-anim="draw:0.8:0.7"/>
      <rect x="40" y="290" width="300" height="12" rx="6" fill="#d5dde0"/></g></g>
    <g data-anim="stamp:1.35:0.45" style="transform-origin:300px 520px"><g transform="translate(150,470) rotate(-10)">
      <rect width="330" height="100" rx="14" fill="none" stroke="${RED}" stroke-width="10"/>
      <text x="165" y="68" text-anchor="middle" font-family="Inter" font-weight="800" font-size="50" fill="${RED}">CERTIFIED</text></g></g>
    <g data-anim="popIn:1.0:0.4" style="transform-origin:720px 610px"><g transform="translate(640,560)">
      <rect width="160" height="150" rx="18" fill="${GOLD}"/><rect width="160" height="44" rx="18" fill="#c9a03a"/><rect y="26" width="160" height="18" fill="#c9a03a"/>
      <text x="80" y="122" text-anchor="middle" font-family="Inter" font-weight="800" font-size="60" fill="${NAVY}">15</text></g></g>
  </svg>`,
  swatches: () => {
    const cols = ["#e9dcc5", "#8aa39b", "#3c5a6b", "#c98f5a", "#f4f1ea"];
    let g = "";
    cols.forEach((c, i) => {
      g += `<g data-anim="fan${i}:${0.15 + i * 0.12}:0.55" style="transform-origin:450px 700px"><g>
        <rect x="370" y="180" width="160" height="520" rx="20" fill="${c}" stroke="${WHITE}" stroke-width="6"/>
        <rect x="370" y="620" width="160" height="80" rx="0" fill="${WHITE}" opacity=".9"/><circle cx="450" cy="660" r="14" fill="${TEAL}"/></g></g>`;
    });
    return `<svg viewBox="0 0 900 760" class="prop">${g}
      <g data-anim="popIn:1.0:0.4" style="transform-origin:760px 230px"><g transform="translate(690,160)">
      <circle cx="70" cy="70" r="70" fill="${GOLD}"/><text x="70" y="92" text-anchor="middle" font-family="Inter" font-weight="800" font-size="56" fill="${NAVY}">⏰</text></g></g></svg>`;
  },
  clipboard: () => {
    let rows = "";
    for (let i = 0; i < 4; i++) rows += `<rect x="70" y="${170 + i * 95}" width="54" height="54" rx="10" fill="none" stroke="${TEAL2}" stroke-width="6"/>
      <rect x="150" y="${185 + i * 95}" width="${i % 2 ? 200 : 250}" height="20" rx="10" fill="#d5dde0"/>
      <path d="M80 ${197 + i * 95} l16 16 l30 -34" stroke="${GREEN}" stroke-width="10" fill="none" stroke-linecap="round" stroke-linejoin="round" pathLength="1" class="draw" data-anim="draw:${0.7 + i * 0.3}:0.3"/>`;
    return `<svg viewBox="0 0 900 760" class="prop">
      <g data-anim="riseIn:0.1:0.6" style="transform-origin:450px 400px"><g transform="translate(240,40)">
      <rect width="420" height="600" rx="28" fill="#c9a03a"/><rect x="20" y="40" width="380" height="540" rx="18" fill="${WHITE}"/>
      <rect x="130" y="-10" width="160" height="60" rx="16" fill="${NAVY}"/>${rows}</g></g>
      <g data-anim="swing:0.5:1.2" style="transform-origin:740px 300px"><g transform="translate(680,250)">
      <circle cx="60" cy="60" r="50" fill="none" stroke="${GOLD}" stroke-width="16"/><rect x="95" y="95" width="26" height="110" rx="12" transform="rotate(-45 108 150)" fill="${GOLD}"/></g></g>
    </svg>`;
  },
  mortgage: () => `
  <svg viewBox="0 0 900 760" class="prop">
    <g data-anim="flyInTop:0.05:0.5" style="transform-origin:450px 380px"><g transform="translate(300,120) rotate(8)">${doc(8)}</g></g>
    <g data-anim="flyInLeft:0.2:0.5" style="transform-origin:450px 380px"><g transform="translate(230,140) rotate(-7)">${doc(8)}</g></g>
    <g data-anim="flyInRight:0.35:0.5" style="transform-origin:450px 380px"><g transform="translate(260,110) rotate(1)">${doc(8)}
      <text x="40" y="62" font-family="Inter" font-weight="800" font-size="24" fill="${WHITE}">MORTGAGE</text></g></g>
    <g data-anim="stamp:1.1:0.45" style="transform-origin:470px 560px"><g transform="translate(300,510) rotate(-12)">
      <rect width="340" height="104" rx="14" fill="none" stroke="${GREEN}" stroke-width="10"/>
      <text x="170" y="72" text-anchor="middle" font-family="Inter" font-weight="800" font-size="56" fill="${GREEN}">APPROVED</text></g></g>
  </svg>`,
  house: () => `
  <svg viewBox="0 0 900 760" class="prop">
    <g data-anim="riseIn:0.1:0.6" style="transform-origin:450px 500px"><g transform="translate(220,170)">
      <path d="M230 0 L460 190 L410 190 L410 420 L50 420 L50 190 L0 190 Z" fill="${WHITE}"/>
      <rect x="190" y="270" width="90" height="150" rx="10" fill="${TEAL2}"/><rect x="90" y="230" width="70" height="70" rx="8" fill="${GOLD}"/><rect x="310" y="230" width="70" height="70" rx="8" fill="${GOLD}"/></g></g>
    <g data-anim="swing:0.6:1.4" style="transform-origin:700px 220px"><g transform="translate(640,180)">
      <circle cx="40" cy="40" r="34" fill="none" stroke="${GOLD}" stroke-width="14"/><rect x="66" y="32" width="120" height="18" rx="9" fill="${GOLD}"/><rect x="150" y="44" width="16" height="30" fill="${GOLD}"/></g></g>
  </svg>`,
  keys: () => `
  <svg viewBox="0 0 900 760" class="prop">
    <g data-anim="swing:0.1:1.6" style="transform-origin:450px 120px"><g transform="translate(300,100)">
      <circle cx="150" cy="40" r="36" fill="none" stroke="${GOLD}" stroke-width="12"/>
      <g transform="rotate(20 150 76)"><circle cx="150" cy="170" r="70" fill="none" stroke="${GOLD}" stroke-width="22"/><rect x="138" y="236" width="24" height="230" rx="10" fill="${GOLD}"/><rect x="160" y="400" width="50" height="22" fill="${GOLD}"/><rect x="160" y="440" width="36" height="22" fill="${GOLD}"/></g>
      <g transform="rotate(-25 150 76)"><circle cx="150" cy="160" r="56" fill="none" stroke="${WHITE}" stroke-width="18"/><rect x="140" y="212" width="20" height="190" rx="9" fill="${WHITE}"/><rect x="158" y="350" width="40" height="18" fill="${WHITE}"/></g></g></g>
  </svg>`,
};

Object.assign(PROPS, {
  shield: () => `
  <svg viewBox="0 0 900 760" class="prop">
    <g data-anim="riseIn:0.1:0.6" style="transform-origin:450px 400px"><g transform="translate(250,120)">
      <path d="M200 0 L400 70 L400 250 C400 400 300 480 200 520 C100 480 0 400 0 250 L0 70 Z" fill="${TEAL2}" stroke="${GOLD}" stroke-width="14"/>
      <path d="M120 260 l60 60 l110 -130" stroke="${WHITE}" stroke-width="30" fill="none" stroke-linecap="round" stroke-linejoin="round" pathLength="1" class="draw" data-anim="draw:0.7:0.5"/></g></g>
    <g data-anim="flyInLeft:0.4:0.5" style="transform-origin:150px 560px"><g transform="translate(40,470)">
      <path d="M90 0 L180 70 L150 70 L150 170 L30 170 L30 70 L0 70 Z" fill="${WHITE}"/><rect x="72" y="110" width="36" height="60" fill="${GOLD}"/></g></g>
    <g data-anim="popIn:1.1:0.4" style="transform-origin:760px 560px"><g transform="translate(680,480)">
      <rect width="170" height="160" rx="18" fill="${GOLD}"/><rect width="170" height="44" rx="18" fill="#c9a03a"/><rect y="26" width="170" height="18" fill="#c9a03a"/>
      <text x="85" y="128" text-anchor="middle" font-family="Inter" font-weight="800" font-size="40" fill="${NAVY}">DAY 1</text></g></g>
  </svg>`,
  movingbox: () => {
    const box = (x, y, w, h, d) => `<g data-anim="dropIn:${d}:0.5" style="transform-origin:${x + w / 2}px ${y + h}px"><g>
      <rect x="${x}" y="${y}" width="${w}" height="${h}" rx="10" fill="#c98f5a"/><rect x="${x}" y="${y}" width="${w}" height="${h * 0.22}" fill="#b47a46"/>
      <rect x="${x + w / 2 - 18}" y="${y}" width="36" height="${h * 0.5}" fill="#e7c48f"/></g></g>`;
    return `<svg viewBox="0 0 900 760" class="prop">${box(150, 420, 300, 260, 0.1)}${box(470, 470, 260, 210, 0.3)}${box(240, 200, 240, 220, 0.5)}
      <g data-anim="popIn:1.0:0.4" style="transform-origin:700px 300px"><g transform="translate(620,220)">
      <circle cx="80" cy="80" r="80" fill="${GOLD}"/><path d="M80 30 L80 85 L115 105" stroke="${NAVY}" stroke-width="14" fill="none" stroke-linecap="round"/></g></g></svg>`;
  },
  search: () => `
  <svg viewBox="0 0 900 760" class="prop">
    <g data-anim="riseIn:0.1:0.5" style="transform-origin:450px 500px"><g transform="translate(170,200)">
      <path d="M230 0 L460 190 L410 190 L410 420 L50 420 L50 190 L0 190 Z" fill="${WHITE}"/>
      <rect x="190" y="270" width="90" height="150" rx="10" fill="${TEAL2}"/><rect x="90" y="230" width="70" height="70" rx="8" fill="#d5dde0"/><rect x="310" y="230" width="70" height="70" rx="8" fill="#d5dde0"/></g></g>
    <g data-anim="scan:0.5:1.6" style="transform-origin:500px 400px"><g transform="translate(420,260)">
      <circle cx="110" cy="110" r="95" fill="rgba(250,201,81,.18)" stroke="${GOLD}" stroke-width="24"/><rect x="170" y="180" width="40" height="160" rx="18" transform="rotate(-45 190 260)" fill="${GOLD}"/></g></g>
  </svg>`,
  handshake: () => `
  <svg viewBox="0 0 900 760" class="prop">
    <g data-anim="flyInLeft:0.1:0.55" style="transform-origin:300px 400px"><g transform="translate(80,300)">
      <rect width="300" height="120" rx="40" fill="${TEAL2}"/><rect x="230" y="10" width="160" height="100" rx="40" fill="#e0b48c"/></g></g>
    <g data-anim="flyInRight:0.1:0.55" style="transform-origin:600px 400px"><g transform="translate(470,330)">
      <rect x="50" width="300" height="120" rx="40" fill="${NAVY}"/><rect x="-60" y="10" width="160" height="100" rx="40" fill="#c99a72"/></g></g>
    <g data-anim="popIn:0.8:0.4" style="transform-origin:450px 230px"><g transform="translate(380,160)">
      <circle cx="70" cy="70" r="70" fill="${GOLD}"/><path d="M40 72 l22 22 l40 -46" stroke="${NAVY}" stroke-width="16" fill="none" stroke-linecap="round" stroke-linejoin="round"/></g></g>
    <g data-anim="flyInTop:1.0:0.5" style="transform-origin:450px 600px"><g transform="translate(300,520)">
      <rect width="300" height="120" rx="18" fill="${WHITE}"/><rect x="30" y="30" width="160" height="16" rx="8" fill="#d5dde0"/><rect x="30" y="70" width="230" height="16" rx="8" fill="#d5dde0"/></g></g>
  </svg>`,
  calculator: () => {
    let keys = ""; for (let r = 0; r < 4; r++) for (let c = 0; c < 3; c++) keys += `<rect x="${40 + c * 100}" y="${200 + r * 80}" width="80" height="60" rx="12" fill="${c == 2 ? GOLD : "#d5dde0"}" data-anim="popIn:${0.4 + (r * 3 + c) * 0.04}:0.3" style="transform-origin:${80 + c * 100}px ${230 + r * 80}px"/>`;
    return `<svg viewBox="0 0 900 760" class="prop"><g data-anim="riseIn:0.1:0.5" style="transform-origin:450px 400px"><g transform="translate(270,60)">
      <rect width="380" height="560" rx="36" fill="${NAVY}"/><rect x="40" y="50" width="300" height="110" rx="16" fill="#cfe8d6"/>
      <text x="320" y="128" text-anchor="end" font-family="Inter" font-weight="800" font-size="60" fill="${NAVY}" data-anim="fadeUp:0.8:0.4">$ ✓</text>${keys}</g></g></svg>`;
  },
  chart: () => {
    const hs = [180, 260, 220, 340, 420]; let bars = "";
    hs.forEach((h, i) => bars += `<rect x="${140 + i * 130}" y="${640 - h}" width="90" height="${h}" rx="12" fill="${i == 4 ? GOLD : WHITE}" data-anim="growUp:${0.15 + i * 0.12}:0.5" style="transform-origin:${185 + i * 130}px 640px"/>`);
    return `<svg viewBox="0 0 900 760" class="prop"><rect x="100" y="640" width="720" height="8" rx="4" fill="${WHITE}" opacity=".7"/>${bars}
      <path d="M185 420 L315 340 L445 380 L575 260 L705 180" stroke="${LIME}" stroke-width="12" fill="none" stroke-linecap="round" stroke-linejoin="round" pathLength="1" class="draw" data-anim="draw:0.8:0.8"/></svg>`;
  },
  piggy: () => `
  <svg viewBox="0 0 900 760" class="prop">
    <g data-anim="riseIn:0.1:0.55" style="transform-origin:450px 500px"><g transform="translate(200,300)">
      <ellipse cx="250" cy="180" rx="240" ry="170" fill="#f2a7b8"/><circle cx="420" cy="150" r="70" fill="#f2a7b8"/><ellipse cx="470" cy="165" rx="35" ry="28" fill="#e28a9f"/>
      <rect x="200" y="20" width="110" height="18" rx="9" fill="${NAVY}"/><circle cx="400" cy="120" r="10" fill="${NAVY}"/>
      <rect x="90" y="300" width="50" height="80" rx="16" fill="#e28a9f"/><rect x="330" y="300" width="50" height="80" rx="16" fill="#e28a9f"/></g></g>
    ${[0, 1, 2].map(i => `<g data-anim="coinDrop:${0.6 + i * 0.3}:0.5" style="transform-origin:450px 200px"><g transform="translate(410,120)"><circle cx="45" cy="45" r="45" fill="${GOLD}" stroke="#c9a03a" stroke-width="8"/><text x="45" y="62" text-anchor="middle" font-family="Inter" font-weight="800" font-size="46" fill="#8a6a2a">$</text></g></g>`).join("")}
  </svg>`,
  calendar: () => {
    let cells = ""; for (let i = 0; i < 15; i++) cells += `<rect x="${40 + (i % 5) * 70}" y="${150 + Math.floor(i / 5) * 70}" width="54" height="54" rx="10" fill="${i == 11 ? GOLD : "#e3eaec"}"/>`;
    return `<svg viewBox="0 0 900 760" class="prop"><g data-anim="flyInTop:0.1:0.55" style="transform-origin:450px 380px"><g transform="translate(250,120)">
      <rect width="420" height="400" rx="26" fill="${WHITE}"/><rect width="420" height="100" rx="26" fill="${TEAL2}"/><rect y="70" width="420" height="30" fill="${TEAL2}"/>${cells}</g></g>
      <g data-anim="stamp:0.9:0.45" style="transform-origin:470px 470px"><circle cx="472" cy="477" r="58" fill="none" stroke="${RED}" stroke-width="10"/></g></svg>`;
  },
});
