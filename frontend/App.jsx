import { useState, useEffect, useRef } from "react";

// ─── Design Tokens ────────────────────────────────────────────────────────────
const tokens = {
  colors: {
    bg: "#0a0a0a",
    surface: "#111111",
    surface2: "#181818",
    surface3: "#1e1e1e",
    border: "#1f1f1f",
    border2: "#2a2a2a",
    text: "#e8e8e8",
    muted: "#555555",
    dim: "#333333",
    green: "#00ff88",
    greenDim: "rgba(0,255,136,0.08)",
    greenMid: "rgba(0,255,136,0.15)",
    red: "#ff4455",
    redDim: "rgba(255,68,85,0.08)",
    amber: "#ffaa00",
    amberDim: "rgba(255,170,0,0.08)",
    blue: "#4488ff",
    blueDim: "rgba(68,136,255,0.08)",
    // Paper mode accent
    paperAccent: "#ffaa00",
    paperDim: "rgba(255,170,0,0.06)",
    // Live mode accent
    liveAccent: "#00ff88",
    liveDim: "rgba(0,255,136,0.06)",
  },
  fonts: {
    mono: "'IBM Plex Mono', monospace",
    sans: "'IBM Plex Sans', sans-serif",
  },
};

// ─── Global Styles Injection ──────────────────────────────────────────────────
const injectStyles = () => {
  const style = document.createElement("style");
  style.textContent = `
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=IBM+Plex+Sans:wght@300;400;500&display=swap');
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html, body, #root { height: 100%; }
    body {
      background: ${tokens.colors.bg};
      color: ${tokens.colors.text};
      font-family: ${tokens.fonts.mono};
      font-size: 13px;
      overflow-x: hidden;
    }
    body::before {
      content: '';
      position: fixed; inset: 0;
      background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.025) 2px, rgba(0,0,0,0.025) 4px);
      pointer-events: none;
      z-index: 9999;
    }
    ::-webkit-scrollbar { width: 3px; height: 3px; }
    ::-webkit-scrollbar-track { background: ${tokens.colors.bg}; }
    ::-webkit-scrollbar-thumb { background: ${tokens.colors.dim}; }
    @keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.4;transform:scale(0.8)} }
    @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
    @keyframes fadeIn { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:translateY(0)} }
    @keyframes slideIn { from{opacity:0;transform:translateX(-8px)} to{opacity:1;transform:translateX(0)} }
    @keyframes liveGlow { 0%,100%{box-shadow:0 0 8px rgba(0,255,136,0.3)} 50%{box-shadow:0 0 20px rgba(0,255,136,0.6)} }
    @keyframes paperGlow { 0%,100%{box-shadow:0 0 8px rgba(255,170,0,0.2)} 50%{box-shadow:0 0 20px rgba(255,170,0,0.5)} }
    .fade-in { animation: fadeIn 0.35s ease forwards; }
    .s1{animation-delay:.04s} .s2{animation-delay:.08s} .s3{animation-delay:.12s}
    .s4{animation-delay:.16s} .s5{animation-delay:.20s} .s6{animation-delay:.24s}
    table { width:100%; border-collapse:collapse; }
    th { text-align:left; padding:8px 10px; font-size:10px; letter-spacing:.1em; text-transform:uppercase; color:${tokens.colors.muted}; font-weight:400; font-family:${tokens.fonts.mono}; }
    td { padding:9px 10px; font-family:${tokens.fonts.mono}; font-size:12px; }
    thead tr { border-bottom: 1px solid ${tokens.colors.border2}; }
    tbody tr { border-bottom: 1px solid ${tokens.colors.border}; transition: background .1s; }
    tbody tr:hover { background: ${tokens.colors.surface2}; }
    a { color: inherit; text-decoration: none; }
  `;
  document.head.appendChild(style);
};

// ─── Primitive Components ─────────────────────────────────────────────────────

const Card = ({ children, style, className }) => (
  <div className={className} style={{
    border: `1px solid ${tokens.colors.border}`,
    background: tokens.colors.surface,
    padding: 16,
    ...style,
  }}>{children}</div>
);

const CardTitle = ({ children, action }) => (
  <div style={{
    fontSize: 10, letterSpacing: ".15em", textTransform: "uppercase",
    color: tokens.colors.muted, marginBottom: 14,
    display: "flex", alignItems: "center", justifyContent: "space-between",
  }}>
    <span>{children}</span>
    {action && <span style={{ color: tokens.colors.blue, cursor: "pointer", fontSize: 10, letterSpacing: ".05em" }}>{action}</span>}
  </div>
);

const SectionTitle = ({ children }) => (
  <div style={{
    fontSize: 10, letterSpacing: ".2em", textTransform: "uppercase",
    color: tokens.colors.muted, marginBottom: 16, marginTop: 4,
    display: "flex", alignItems: "center", gap: 10,
  }}>
    {children}
    <div style={{ flex: 1, height: 1, background: tokens.colors.border }} />
  </div>
);

const Badge = ({ type, children }) => {
  const styles = {
    won:     { color: tokens.colors.green,  border: `1px solid ${tokens.colors.green}`,  background: tokens.colors.greenDim },
    lost:    { color: tokens.colors.red,    border: `1px solid ${tokens.colors.red}`,    background: tokens.colors.redDim },
    pending: { color: tokens.colors.amber,  border: `1px solid ${tokens.colors.amber}`,  background: tokens.colors.amberDim },
    paper:   { color: tokens.colors.blue,   border: `1px solid ${tokens.colors.blue}`,   background: tokens.colors.blueDim },
    live:    { color: tokens.colors.green,  border: `1px solid ${tokens.colors.green}`,  background: tokens.colors.greenDim },
    skip:    { color: tokens.colors.muted,  border: `1px solid ${tokens.colors.border2}`,background: "transparent" },
    back:    { color: tokens.colors.green,  border: `1px solid ${tokens.colors.green}`,  background: tokens.colors.greenDim },
    error:   { color: tokens.colors.red,    border: `1px solid ${tokens.colors.red}`,    background: tokens.colors.redDim },
    info:    { color: tokens.colors.blue,   border: `1px solid ${tokens.colors.blue}`,   background: tokens.colors.blueDim },
    warn:    { color: tokens.colors.amber,  border: `1px solid ${tokens.colors.amber}`,  background: tokens.colors.amberDim },
  };
  return (
    <span style={{
      display: "inline-block", padding: "2px 7px", fontSize: 10,
      letterSpacing: ".08em", textTransform: "uppercase",
      ...(styles[type] || styles.skip),
    }}>{children}</span>
  );
};

const AgentTag = ({ id }) => (
  <span style={{
    display: "inline-flex", alignItems: "center", justifyContent: "center",
    width: 20, height: 20, fontSize: 11, fontWeight: 600,
    border: `1px solid ${tokens.colors.border2}`, background: tokens.colors.surface2,
    color: tokens.colors.text,
  }}>{id}</span>
);

const WeightBar = ({ stat, mkt }) => (
  <div style={{ marginTop: 10 }}>
    <div style={{ fontSize: 9, color: tokens.colors.muted, marginBottom: 4, letterSpacing: ".08em" }}>
      STAT ← → MKT
    </div>
    <div style={{ height: 4, background: tokens.colors.border, position: "relative", overflow: "hidden" }}>
      <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${stat * 100}%`, background: tokens.colors.green, transition: "width .5s" }} />
    </div>
    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9, color: tokens.colors.muted, marginTop: 4 }}>
      <span>{stat.toFixed(2)}</span><span>{mkt.toFixed(2)}</span>
    </div>
  </div>
);

const Sparkline = ({ data, color = tokens.colors.green, negColor = tokens.colors.red }) => (
  <div style={{ display: "flex", alignItems: "flex-end", gap: 2, height: 32, marginTop: 10 }}>
    {data.map((v, i) => (
      <div key={i} style={{
        flex: 1, height: `${Math.abs(v)}%`,
        background: v >= 0 ? `${color}22` : `${negColor}22`,
        borderTop: `1px solid ${v >= 0 ? color : negColor}`,
      }} />
    ))}
  </div>
);

const Pulse = ({ color = tokens.colors.green }) => (
  <div style={{ width: 7, height: 7, borderRadius: "50%", background: color, animation: "pulse 2s ease-in-out infinite", flexShrink: 0 }} />
);

// ─── Mock Data ────────────────────────────────────────────────────────────────
const agents = [
  { id: "A", strategy: "flat", bankroll: 1012.40, start: 1000, picks: 13, winRate: 62, threshold: 0.620, stat: 0.80, mkt: 0.20, updates: 0, clv: 2.8 },
  { id: "B", strategy: "flat", bankroll: 987.50,  start: 1000, picks: 11, winRate: 55, threshold: 0.650, stat: 0.40, mkt: 0.60, updates: 0, clv: -0.4 },
  { id: "C", strategy: "flat", bankroll: 1008.00, start: 1000, picks: 12, winRate: 58, threshold: 0.700, stat: 0.60, mkt: 0.40, updates: 0, clv: 1.2 },
  { id: "D", strategy: "kelly", bankroll: 1026.30, start: 1000, picks: 11, winRate: 64, threshold: 0.600, stat: 0.50, mkt: 0.50, updates: 0, clv: 3.1, kellyFraction: 0.25 },
];

const picks = [
  { id:1, agent:"D", league:"EPL", home:"Man City", away:"Arsenal",    sel:"1X", odds:1.42, stake:8.30,  conf:0.668, ev:3.2, status:"won",    pnl:+3.77,  clv:+4.1 },
  { id:2, agent:"A", league:"BUN", home:"Bayern",   away:"Dortmund",   sel:"1X", odds:1.35, stake:10.00, conf:0.641, ev:2.8, status:"won",    pnl:+3.50,  clv:+2.9 },
  { id:3, agent:"C", league:"EPL", home:"Chelsea",  away:"Liverpool",  sel:"X2", odds:1.55, stake:10.00, conf:0.712, ev:4.1, status:"lost",   pnl:-10.00, clv:+1.8 },
  { id:4, agent:"B", league:"L1",  home:"PSG",      away:"Lyon",       sel:"12", odds:1.28, stake:10.00, conf:0.658, ev:1.9, status:"pending", pnl:null,  clv:null },
  { id:5, agent:"D", league:"SA",  home:"Inter",    away:"Milan",      sel:"1X", odds:1.48, stake:11.20, conf:0.671, ev:3.8, status:"pending", pnl:null,  clv:null },
  { id:6, agent:"A", league:"EPL", home:"Spurs",    away:"Newcastle",  sel:"12", odds:1.38, stake:10.00, conf:0.634, ev:2.2, status:"pending", pnl:null,  clv:null },
  { id:7, agent:"C", league:"BUN", home:"Leverkusen",away:"Frankfurt", sel:"1X", odds:1.45, stake:10.00, conf:0.708, ev:3.5, status:"won",    pnl:+4.50,  clv:+3.2 },
  { id:8, agent:"A", league:"L2",  home:"Bordeaux", away:"Nantes",     sel:"1X", odds:1.52, stake:10.00, conf:0.639, ev:2.6, status:"lost",   pnl:-10.00, clv:+0.8 },
  { id:9, agent:"D", league:"SA",  home:"Napoli",   away:"Lazio",      sel:"1X", odds:1.44, stake:9.80,  conf:0.662, ev:3.1, status:"won",    pnl:+4.31,  clv:+3.8 },
  { id:10,agent:"B", league:"LL",  home:"Barcelona",away:"Sevilla",    sel:"1X", odds:1.32, stake:10.00, conf:0.656, ev:2.1, status:"lost",   pnl:-10.00, clv:-1.2 },
];

const fixtures = [
  { league:"EPL",    home:"Man Utd",    away:"Wolves",     time:"18:30", dc:{"1X":1.30,"X2":2.10,"12":1.18}, best:"1X" },
  { league:"BUN",    home:"Leverkusen", away:"Frankfurt",  time:"19:30", dc:{"1X":1.45,"X2":2.40,"12":1.32}, best:"1X" },
  { league:"LA LIGA",home:"Real Madrid",away:"Atletico",   time:"20:00", dc:{"1X":1.55,"X2":1.85,"12":1.38}, best:"X2" },
  { league:"SERIE A",home:"Juventus",   away:"Roma",       time:"20:45", dc:{"1X":1.50,"X2":2.20,"12":1.35}, best:"1X" },
  { league:"LIGUE 1",home:"Monaco",     away:"Marseille",  time:"21:00", dc:{"1X":1.65,"X2":2.05,"12":1.42}, best:"12" },
  { league:"EFL",    home:"Leeds",      away:"Burnley",    time:"19:00", dc:{"1X":1.72,"X2":1.90,"12":1.48}, best:"X2" },
  { league:"BUN2",   home:"Hamburger",  away:"Hannover",   time:"18:30", dc:{"1X":1.55,"X2":2.15,"12":1.38}, best:"1X" },
  { league:"LL2",    home:"Elche",      away:"Valladolid", time:"20:30", dc:{"1X":1.68,"X2":1.98,"12":1.45}, best:"X2" },
];

const scheduledJobs = [
  { time:"04:00", name:"Backup → Object Storage",   status:"done",    next:"✓ done" },
  { time:"08:00", name:"Morning — Results + Odds",  status:"done",    next:"✓ done" },
  { time:"12:00", name:"Snapshot — Odds",           status:"done",    next:"✓ done" },
  { time:"16:00", name:"Analysis + P&L log",        status:"running", next:"in 1h 18m" },
  { time:"Sun 20:00", name:"Calendar Refresh",      status:"pending", next:"in 4d 3h" },
  { time:"Sun 20:30", name:"Agent Recalibration",   status:"pending", next:"in 4d 3h 30m" },
];

const logLines = [
  { time:"16:00:01", level:"INFO",  src:"scheduler",  msg:"Analysis job started" },
  { time:"16:00:02", level:"INFO",  src:"odds_api",   msg:"Fetching EPL odds snapshot" },
  { time:"16:00:03", level:"INFO",  src:"pipeline",   msg:"Fan-out: 12 fixtures queued" },
  { time:"16:00:04", level:"INFO",  src:"stat",       msg:"Man Utd v Wolves — confidence 0.641" },
  { time:"16:00:04", level:"INFO",  src:"market",     msg:"Man Utd v Wolves — edge +3.2%" },
  { time:"16:00:05", level:"INFO",  src:"synth",      msg:"Man Utd v Wolves → BACK 1X @ 1.30" },
  { time:"16:00:05", level:"INFO",  src:"agent_A",    msg:"Backing — stake £10.00, bankroll £1012.40" },
  { time:"16:00:05", level:"WARN",  src:"agent_B",    msg:"Below threshold 0.650 — skip" },
  { time:"16:00:06", level:"INFO",  src:"pnl",        msg:"P&L snapshot: net +£34.20" },
  { time:"16:00:07", level:"INFO",  src:"scheduler",  msg:"Analysis complete — 3 picks placed" },
  { time:"12:00:01", level:"INFO",  src:"scheduler",  msg:"Snapshot job started" },
  { time:"12:00:03", level:"INFO",  src:"odds_api",   msg:"Snapshot complete — 10 leagues" },
  { time:"08:00:01", level:"INFO",  src:"scheduler",  msg:"Morning job started" },
  { time:"08:00:02", level:"INFO",  src:"result",     msg:"Settling 4 pending picks" },
  { time:"08:00:04", level:"ERROR", src:"odds_api",   msg:"Rate limit warning — 347 calls remaining" },
  { time:"04:00:01", level:"INFO",  src:"backup",     msg:"Backup started — ledger.db" },
  { time:"04:00:03", level:"INFO",  src:"backup",     msg:"Backup complete — 2.1 MB uploaded" },
];

// P&L sparkline data (14-day paper trading)
const pnlHistory = [0, 12, 8, 22, 15, 34, 28, 42, 38, 51, 44, 58, 50, 34];
const sparkData = [50, 65, 45, 80, 60, 90, 55, 85, 70, 100];

// ─── Pages ────────────────────────────────────────────────────────────────────

const OverviewPage = ({ mode }) => (
  <div>
    <SectionTitle>Overview</SectionTitle>

    {/* Metrics */}
    <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:12, marginBottom:16 }} className="fade-in s1">
      {[
        { label:"Total Bankroll", value:"£4,034", sub:"↑ +£34 since start", color:tokens.colors.green, spark:sparkData },
        { label:"Avg CLV", value:"+2.3%", sub:"18 settled picks", color:tokens.colors.blue, spark:[30,45,35,70,40,85,55,90,60,75] },
        { label:"Win Rate", value:"61%", sub:"11 won / 7 lost", color:tokens.colors.amber, spark:[60,60,40,80,60,60,40,60,100,60] },
        { label:"Today's Fixtures", value:"12", sub:`analysis in 1h 18m`, color:tokens.colors.text, spark:[20,40,30,80,60,40,70,50,90,60] },
      ].map(({ label, value, sub, color, spark }) => (
        <Card key={label} style={{ position:"relative", overflow:"hidden" }}>
          <div style={{ position:"absolute", top:0, left:0, right:0, height:2, background:color }} />
          <div style={{ fontSize:10, color:tokens.colors.muted, letterSpacing:".15em", textTransform:"uppercase", marginBottom:8 }}>{label}</div>
          <div style={{ fontSize:26, fontWeight:500, color, lineHeight:1, marginBottom:6 }}>{value}</div>
          <div style={{ fontSize:11, color:tokens.colors.muted }}>{sub}</div>
          <Sparkline data={spark} color={color} />
        </Card>
      ))}
    </div>

    {/* Agents */}
    <SectionTitle>Agents</SectionTitle>
    <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:12, marginBottom:16 }} className="fade-in s2">
      {agents.map(a => {
        const pct = (a.bankroll / a.start) * 100;
        const up = a.bankroll >= a.start;
        return (
          <Card key={a.id}>
            <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:12 }}>
              <span style={{ fontSize:22, fontWeight:600 }}>{a.id}</span>
              <span style={{ fontSize:9, letterSpacing:".15em", textTransform:"uppercase", padding:"2px 6px", border:`1px solid ${tokens.colors.border2}`, color:tokens.colors.muted }}>{a.strategy}</span>
            </div>
            {[
              { label:"Bankroll", value: <span style={{ color: up ? tokens.colors.green : tokens.colors.red }}>£{a.bankroll.toFixed(2)}</span> },
              { label:"Picks / Win%", value:`${a.picks} / ${a.winRate}%` },
              { label:"Threshold", value:a.threshold.toFixed(3) },
            ].map(({ label, value }) => (
              <div key={label} style={{ marginBottom:8 }}>
                <div style={{ fontSize:9, color:tokens.colors.muted, letterSpacing:".1em", textTransform:"uppercase", marginBottom:3 }}>{label}</div>
                <div style={{ fontSize:13 }}>{value}</div>
              </div>
            ))}
            <WeightBar stat={a.stat} mkt={a.mkt} />
            <div style={{ marginTop:8, height:3, background:tokens.colors.border }}>
              <div style={{ height:"100%", width:`${Math.min(pct, 100)}%`, background: up ? tokens.colors.green : tokens.colors.red, transition:"width .5s" }} />
            </div>
          </Card>
        );
      })}
    </div>

    {/* Picks + Schedule */}
    <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12, marginBottom:16 }} className="fade-in s3">
      <Card>
        <CardTitle action="view all →">Recent Picks</CardTitle>
        <table>
          <thead><tr><th>Ag</th><th>Match</th><th>Sel</th><th>Odds</th><th>Stake</th><th>Status</th></tr></thead>
          <tbody>
            {picks.slice(0,6).map(p => (
              <tr key={p.id}>
                <td><AgentTag id={p.agent} /></td>
                <td><span style={{ color:tokens.colors.muted, fontSize:10 }}>{p.league} </span>{p.home} v {p.away}</td>
                <td>{p.sel}</td>
                <td>{p.odds}</td>
                <td>£{p.stake.toFixed(2)}</td>
                <td><Badge type={p.status}>{p.status}</Badge></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card>
        <CardTitle>Scheduled Jobs</CardTitle>
        {scheduledJobs.map(j => (
          <div key={j.time} style={{ display:"flex", alignItems:"center", gap:12, padding:"9px 0", borderBottom:`1px solid ${tokens.colors.border}` }}>
            <div style={{
              width:8, height:8, borderRadius:"50%", flexShrink:0,
              background: j.status==="done" ? tokens.colors.green : j.status==="running" ? tokens.colors.amber : tokens.colors.border2,
              border: j.status==="pending" ? `1px solid ${tokens.colors.muted}` : "none",
              animation: j.status==="running" ? "pulse 1s infinite" : "none",
            }} />
            <span style={{ color:tokens.colors.muted, fontSize:11, width:68, flexShrink:0 }}>{j.time}</span>
            <span style={{ flex:1, fontSize:12 }}>{j.name}</span>
            <span style={{ fontSize:10, color: j.status==="done" ? tokens.colors.green : j.status==="running" ? tokens.colors.amber : tokens.colors.muted }}>{j.next}</span>
          </div>
        ))}
      </Card>
    </div>

    {/* Fixtures + Logs */}
    <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }} className="fade-in s4">
      <Card>
        <CardTitle action="all 174 →">Today's Fixtures</CardTitle>
        {fixtures.slice(0,5).map((f, i) => (
          <div key={i} style={{ display:"flex", alignItems:"center", gap:10, padding:"9px 0", borderBottom:`1px solid ${tokens.colors.border}`, fontSize:12 }}>
            <span style={{ fontSize:9, letterSpacing:".1em", textTransform:"uppercase", color:tokens.colors.muted, width:68, flexShrink:0 }}>{f.league}</span>
            <span style={{ flex:1 }}>{f.home} v {f.away}</span>
            <div style={{ display:"flex", gap:4 }}>
              {Object.entries(f.dc).map(([sel, odd]) => (
                <span key={sel} style={{
                  padding:"2px 7px", border:`1px solid ${sel===f.best ? tokens.colors.green : tokens.colors.border2}`,
                  fontSize:11, color: sel===f.best ? tokens.colors.green : tokens.colors.muted,
                  background: sel===f.best ? tokens.colors.greenDim : tokens.colors.surface2,
                }}>{sel} {odd}</span>
              ))}
            </div>
            <span style={{ fontSize:11, color:tokens.colors.muted, flexShrink:0 }}>{f.time}</span>
          </div>
        ))}
      </Card>

      <Card>
        <CardTitle action="full logs →">Log Stream</CardTitle>
        <div style={{ background:"#080808", border:`1px solid ${tokens.colors.border}`, padding:10, fontSize:11, lineHeight:1.9, height:220, overflowY:"auto", fontFamily:tokens.fonts.mono }}>
          {logLines.slice(0,10).map((l, i) => (
            <div key={i} style={{ display:"flex", gap:10 }}>
              <span style={{ color:tokens.colors.dim, flexShrink:0 }}>{l.time}</span>
              <span style={{ flexShrink:0, width:38, color: l.level==="INFO" ? tokens.colors.blue : l.level==="WARN" ? tokens.colors.amber : tokens.colors.red }}>{l.level}</span>
              <span style={{ color:tokens.colors.muted, flexShrink:0, minWidth:60 }}>{l.src}</span>
              <span style={{ color:tokens.colors.text }}>{l.msg}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  </div>
);

const PicksFeedPage = () => {
  const [filter, setFilter] = useState("all");
  const filtered = filter === "all" ? picks : picks.filter(p => p.status === filter);
  const statuses = ["all", "won", "lost", "pending"];

  return (
    <div>
      <SectionTitle>Picks Feed</SectionTitle>
      {/* Stats row */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(5,1fr)", gap:12, marginBottom:16 }} className="fade-in s1">
        {[
          { label:"Total Picks", value:picks.length, color:tokens.colors.text },
          { label:"Won", value:picks.filter(p=>p.status==="won").length, color:tokens.colors.green },
          { label:"Lost", value:picks.filter(p=>p.status==="lost").length, color:tokens.colors.red },
          { label:"Pending", value:picks.filter(p=>p.status==="pending").length, color:tokens.colors.amber },
          { label:"Net P&L", value:"+£34.20", color:tokens.colors.green },
        ].map(({ label, value, color }) => (
          <Card key={label} style={{ textAlign:"center" }}>
            <div style={{ fontSize:9, color:tokens.colors.muted, letterSpacing:".15em", textTransform:"uppercase", marginBottom:8 }}>{label}</div>
            <div style={{ fontSize:22, fontWeight:500, color }}>{value}</div>
          </Card>
        ))}
      </div>

      {/* Filter tabs */}
      <div style={{ display:"flex", gap:0, borderBottom:`1px solid ${tokens.colors.border}`, marginBottom:16 }} className="fade-in s2">
        {statuses.map(s => (
          <div key={s} onClick={() => setFilter(s)} style={{
            padding:"8px 16px", fontSize:11, letterSpacing:".1em", textTransform:"uppercase",
            cursor:"pointer", borderBottom:`2px solid ${filter===s ? tokens.colors.green : "transparent"}`,
            color: filter===s ? tokens.colors.green : tokens.colors.muted,
            marginBottom:-1, transition:"all .15s",
          }}>{s}</div>
        ))}
      </div>

      <Card className="fade-in s3">
        <table>
          <thead>
            <tr>
              <th>Agent</th><th>League</th><th>Match</th><th>Selection</th>
              <th>Odds</th><th>Stake</th><th>Confidence</th><th>EV</th>
              <th>Status</th><th>P&L</th><th>CLV</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(p => (
              <tr key={p.id}>
                <td><AgentTag id={p.agent} /></td>
                <td style={{ color:tokens.colors.muted, fontSize:11 }}>{p.league}</td>
                <td>{p.home} v {p.away}</td>
                <td style={{ fontWeight:500 }}>{p.sel}</td>
                <td>{p.odds.toFixed(2)}</td>
                <td>£{p.stake.toFixed(2)}</td>
                <td style={{ color:tokens.colors.blue }}>{(p.conf*100).toFixed(1)}%</td>
                <td style={{ color:p.ev>0?tokens.colors.green:tokens.colors.red }}>+{p.ev.toFixed(1)}%</td>
                <td><Badge type={p.status}>{p.status}</Badge></td>
                <td style={{ color: p.pnl===null ? tokens.colors.muted : p.pnl>0 ? tokens.colors.green : tokens.colors.red }}>
                  {p.pnl===null ? "—" : `${p.pnl>0?"+":""}£${p.pnl.toFixed(2)}`}
                </td>
                <td style={{ color: p.clv===null ? tokens.colors.muted : p.clv>0 ? tokens.colors.green : tokens.colors.red }}>
                  {p.clv===null ? "—" : `${p.clv>0?"+":""}${p.clv.toFixed(1)}%`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
};

const PnLPage = () => {
  const days = pnlHistory.map((v, i) => ({ day: i + 1, pnl: v }));
  const max = Math.max(...pnlHistory);

  return (
    <div>
      <SectionTitle>P&L</SectionTitle>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:12, marginBottom:16 }} className="fade-in s1">
        {[
          { label:"Net P&L", value:"+£34.20", color:tokens.colors.green },
          { label:"ROI", value:"+0.86%", color:tokens.colors.green },
          { label:"Avg CLV", value:"+2.3%", color:tokens.colors.blue },
          { label:"Days Remaining", value:"11", color:tokens.colors.muted },
        ].map(({ label, value, color }) => (
          <Card key={label}>
            <div style={{ fontSize:9, color:tokens.colors.muted, letterSpacing:".15em", textTransform:"uppercase", marginBottom:8 }}>{label}</div>
            <div style={{ fontSize:26, fontWeight:500, color }}>{value}</div>
          </Card>
        ))}
      </div>

      {/* P&L chart */}
      <Card style={{ marginBottom:16 }} className="fade-in s2">
        <CardTitle>Cumulative P&L — Paper Trading (Day 1–14)</CardTitle>
        <div style={{ height:160, display:"flex", alignItems:"flex-end", gap:3, padding:"8px 0" }}>
          {days.map((d, i) => {
            const h = max > 0 ? (d.pnl / max) * 130 : 0;
            const isToday = i === 2;
            return (
              <div key={i} style={{ flex:1, display:"flex", flexDirection:"column", alignItems:"center", gap:4 }}>
                <div style={{
                  width:"100%", height: h || 3,
                  background: d.pnl >= 0 ? tokens.colors.greenDim : tokens.colors.redDim,
                  borderTop: `2px solid ${d.pnl>=0 ? tokens.colors.green : tokens.colors.red}`,
                  opacity: i > 2 ? 0.25 : 1,
                  position:"relative",
                }}>
                  {isToday && <div style={{ position:"absolute", top:-8, left:"50%", transform:"translateX(-50%)", fontSize:8, color:tokens.colors.amber, letterSpacing:".1em" }}>NOW</div>}
                </div>
                <div style={{ fontSize:9, color: isToday ? tokens.colors.amber : tokens.colors.muted }}>{d.day}</div>
              </div>
            );
          })}
        </div>
        <div style={{ display:"flex", justifyContent:"space-between", fontSize:9, color:tokens.colors.muted, letterSpacing:".08em", marginTop:4 }}>
          <span>Day 1 — 2026-03-30</span>
          <span style={{ color:tokens.colors.amber }}>▲ Today — Day 3</span>
          <span style={{ opacity:.4 }}>Day 14 — 2026-04-13</span>
        </div>
      </Card>

      {/* Per-agent P&L */}
      <SectionTitle>Per Agent</SectionTitle>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:12 }} className="fade-in s3">
        {agents.map(a => {
          const pnl = a.bankroll - a.start;
          const roi = ((pnl / a.start) * 100).toFixed(2);
          return (
            <Card key={a.id}>
              <div style={{ display:"flex", justifyContent:"space-between", marginBottom:12 }}>
                <span style={{ fontSize:20, fontWeight:600 }}>{a.id}</span>
                <Badge type={pnl>=0?"won":"lost"}>{pnl>=0?"+":""}£{pnl.toFixed(2)}</Badge>
              </div>
              <div style={{ fontSize:9, color:tokens.colors.muted, letterSpacing:".1em", textTransform:"uppercase", marginBottom:4 }}>ROI</div>
              <div style={{ fontSize:18, fontWeight:500, color:pnl>=0?tokens.colors.green:tokens.colors.red, marginBottom:12 }}>{roi}%</div>
              <div style={{ fontSize:9, color:tokens.colors.muted, letterSpacing:".1em", textTransform:"uppercase", marginBottom:4 }}>CLV avg</div>
              <div style={{ fontSize:14, color:a.clv>0?tokens.colors.blue:tokens.colors.red }}>{a.clv>0?"+":""}{a.clv}%</div>
              <div style={{ marginTop:10, height:3, background:tokens.colors.border }}>
                <div style={{ height:"100%", width:`${Math.min((a.bankroll/a.start)*100, 100)}%`, background:pnl>=0?tokens.colors.green:tokens.colors.red }} />
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
};

const AgentsPage = () => (
  <div>
    <SectionTitle>Agents</SectionTitle>
    <div style={{ display:"grid", gridTemplateColumns:"repeat(2,1fr)", gap:12 }} className="fade-in s1">
      {agents.map(a => {
        const pnl = a.bankroll - a.start;
        return (
          <Card key={a.id}>
            <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between", marginBottom:16 }}>
              <div>
                <div style={{ fontSize:28, fontWeight:600, marginBottom:4 }}>Agent {a.id}</div>
                <div style={{ fontSize:10, letterSpacing:".15em", textTransform:"uppercase", color:tokens.colors.muted }}>
                  {a.strategy} staking{a.strategy==="kelly" ? ` · kelly fraction ${a.kellyFraction}` : ""}
                </div>
              </div>
              <Badge type={pnl>=0?"won":"lost"}>{pnl>=0?"+":""}£{pnl.toFixed(2)}</Badge>
            </div>

            <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:12, marginBottom:16 }}>
              {[
                { label:"Bankroll", value:`£${a.bankroll.toFixed(2)}`, color: pnl>=0?tokens.colors.green:tokens.colors.red },
                { label:"Total Picks", value:a.picks },
                { label:"Win Rate", value:`${a.winRate}%` },
                { label:"Threshold", value:a.threshold.toFixed(3) },
                { label:"CLV Avg", value:`${a.clv>0?"+":""}${a.clv}%`, color:a.clv>0?tokens.colors.blue:tokens.colors.red },
                { label:"Updates", value:a.updates },
              ].map(({ label, value, color }) => (
                <div key={label} style={{ padding:"10px 12px", border:`1px solid ${tokens.colors.border}`, background:tokens.colors.surface2 }}>
                  <div style={{ fontSize:9, color:tokens.colors.muted, letterSpacing:".1em", textTransform:"uppercase", marginBottom:6 }}>{label}</div>
                  <div style={{ fontSize:15, fontWeight:500, color: color || tokens.colors.text }}>{value}</div>
                </div>
              ))}
            </div>

            <div style={{ marginBottom:12 }}>
              <div style={{ fontSize:10, color:tokens.colors.muted, letterSpacing:".12em", textTransform:"uppercase", marginBottom:8 }}>Signal Weights</div>
              <div style={{ display:"flex", gap:8, marginBottom:6 }}>
                <div style={{ flex: a.stat, height:24, background:tokens.colors.greenDim, border:`1px solid ${tokens.colors.green}`, display:"flex", alignItems:"center", justifyContent:"center", fontSize:10, color:tokens.colors.green }}>
                  STAT {(a.stat*100).toFixed(0)}%
                </div>
                <div style={{ flex: a.mkt, height:24, background:tokens.colors.blueDim, border:`1px solid ${tokens.colors.blue}`, display:"flex", alignItems:"center", justifyContent:"center", fontSize:10, color:tokens.colors.blue }}>
                  MKT {(a.mkt*100).toFixed(0)}%
                </div>
              </div>
            </div>

            <div style={{ fontSize:10, color:tokens.colors.muted, letterSpacing:".1em", textTransform:"uppercase", marginBottom:6 }}>Bankroll vs Starting</div>
            <div style={{ height:5, background:tokens.colors.border, marginBottom:4 }}>
              <div style={{ height:"100%", width:`${Math.min((a.bankroll/a.start)*100,100)}%`, background:pnl>=0?tokens.colors.green:tokens.colors.red, transition:"width .5s" }} />
            </div>
            <div style={{ display:"flex", justifyContent:"space-between", fontSize:9, color:tokens.colors.muted }}>
              <span>Start £{a.start.toFixed(2)}</span>
              <span style={{ color:pnl>=0?tokens.colors.green:tokens.colors.red }}>Now £{a.bankroll.toFixed(2)}</span>
            </div>
          </Card>
        );
      })}
    </div>
  </div>
);

const FixturesPage = () => {
  const [league, setLeague] = useState("all");
  const leagues = ["all", "EPL", "BUN", "LA LIGA", "SERIE A", "LIGUE 1", "EFL", "BUN2", "LL2"];
  const filtered = league === "all" ? fixtures : fixtures.filter(f => f.league === league);

  return (
    <div>
      <SectionTitle>Fixtures</SectionTitle>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:12, marginBottom:16 }} className="fade-in s1">
        {[
          { label:"Total Fixtures", value:174, color:tokens.colors.text },
          { label:"Today", value:12, color:tokens.colors.blue },
          { label:"Analysis Window", value:8, color:tokens.colors.green },
        ].map(({ label, value, color }) => (
          <Card key={label} style={{ textAlign:"center" }}>
            <div style={{ fontSize:9, color:tokens.colors.muted, letterSpacing:".15em", textTransform:"uppercase", marginBottom:8 }}>{label}</div>
            <div style={{ fontSize:28, fontWeight:500, color }}>{value}</div>
          </Card>
        ))}
      </div>

      <div style={{ display:"flex", gap:6, flexWrap:"wrap", marginBottom:16 }} className="fade-in s2">
        {leagues.map(l => (
          <div key={l} onClick={() => setLeague(l)} style={{
            padding:"4px 10px", fontSize:10, letterSpacing:".1em", textTransform:"uppercase",
            border:`1px solid ${league===l ? tokens.colors.green : tokens.colors.border2}`,
            background: league===l ? tokens.colors.greenDim : "transparent",
            color: league===l ? tokens.colors.green : tokens.colors.muted,
            cursor:"pointer", transition:"all .15s",
          }}>{l}</div>
        ))}
      </div>

      <Card className="fade-in s3">
        <table>
          <thead><tr><th>League</th><th>Home</th><th>Away</th><th>Kickoff</th><th>1X</th><th>X2</th><th>12</th><th>Best</th></tr></thead>
          <tbody>
            {filtered.map((f, i) => (
              <tr key={i}>
                <td style={{ fontSize:10, letterSpacing:".1em", textTransform:"uppercase", color:tokens.colors.muted }}>{f.league}</td>
                <td>{f.home}</td>
                <td>{f.away}</td>
                <td style={{ color:tokens.colors.muted }}>{f.time}</td>
                {["1X","X2","12"].map(sel => (
                  <td key={sel} style={{ color: sel===f.best ? tokens.colors.green : tokens.colors.text, fontWeight: sel===f.best ? 500 : 400 }}>
                    {f.dc[sel]}
                  </td>
                ))}
                <td><Badge type="back">{f.best}</Badge></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
};

const LogsPage = () => {
  const [level, setLevel] = useState("all");
  const levels = ["all", "INFO", "WARN", "ERROR"];
  const filtered = level === "all" ? logLines : logLines.filter(l => l.level === level);

  return (
    <div>
      <SectionTitle>Logs</SectionTitle>

      <div style={{ display:"flex", gap:6, marginBottom:16 }} className="fade-in s1">
        {levels.map(l => (
          <div key={l} onClick={() => setLevel(l)} style={{
            padding:"4px 10px", fontSize:10, letterSpacing:".1em", textTransform:"uppercase",
            border:`1px solid ${level===l ? tokens.colors.green : tokens.colors.border2}`,
            background: level===l ? tokens.colors.greenDim : "transparent",
            color: level===l ? tokens.colors.green : tokens.colors.muted,
            cursor:"pointer",
          }}>{l}</div>
        ))}
        <div style={{ marginLeft:"auto", fontSize:10, color:tokens.colors.muted, display:"flex", alignItems:"center", gap:6 }}>
          <Pulse color={tokens.colors.green} />
          Live
        </div>
      </div>

      <Card className="fade-in s2" style={{ padding:0 }}>
        <div style={{ background:"#080808", padding:16, fontFamily:tokens.fonts.mono, fontSize:12, lineHeight:2 }}>
          {filtered.map((l, i) => (
            <div key={i} style={{ display:"flex", gap:14, borderBottom:`1px solid ${tokens.colors.border}`, padding:"4px 0" }}>
              <span style={{ color:tokens.colors.dim, flexShrink:0, fontSize:11 }}>{l.time}</span>
              <span style={{
                flexShrink:0, width:40, fontSize:11,
                color: l.level==="INFO" ? tokens.colors.blue : l.level==="WARN" ? tokens.colors.amber : tokens.colors.red,
              }}>{l.level}</span>
              <span style={{ color:tokens.colors.muted, flexShrink:0, minWidth:80, fontSize:11 }}>{l.src}</span>
              <span style={{ color:tokens.colors.text }}>{l.msg}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};

const SettingsPage = ({ mode, setMode }) => (
  <div>
    <SectionTitle>Settings</SectionTitle>
    <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }} className="fade-in s1">
      <Card>
        <CardTitle>Trading Mode</CardTitle>
        <div style={{ marginBottom:16, fontSize:12, color:tokens.colors.muted, lineHeight:1.8 }}>
          Paper trading runs the full pipeline with no real money. Live mode activates the execution layer and places real bets via bookmaker API.
        </div>
        <div style={{ display:"flex", gap:0, marginBottom:16 }}>
          {["paper","live"].map(m => (
            <div key={m} onClick={() => setMode(m)} style={{
              flex:1, padding:"12px 0", textAlign:"center",
              fontSize:11, letterSpacing:".15em", textTransform:"uppercase",
              cursor:"pointer",
              background: mode===m ? (m==="paper" ? tokens.colors.amberDim : tokens.colors.greenDim) : tokens.colors.surface2,
              border:`1px solid ${mode===m ? (m==="paper" ? tokens.colors.amber : tokens.colors.green) : tokens.colors.border2}`,
              color: mode===m ? (m==="paper" ? tokens.colors.amber : tokens.colors.green) : tokens.colors.muted,
              transition:"all .2s",
            }}>
              {m === "live" && <span style={{ marginRight:6 }}>⚡</span>}{m}
            </div>
          ))}
        </div>
        {mode === "live" && (
          <div style={{ padding:12, border:`1px solid ${tokens.colors.red}`, background:tokens.colors.redDim, fontSize:12, color:tokens.colors.red, lineHeight:1.7 }}>
            ⚠ Live mode active. Real stakes will be placed. Ensure bookmaker API keys are configured and bankroll limits are set.
          </div>
        )}
        {mode === "paper" && (
          <div style={{ padding:12, border:`1px solid ${tokens.colors.amber}`, background:tokens.colors.amberDim, fontSize:12, color:tokens.colors.amber, lineHeight:1.7 }}>
            Paper trading active. All picks are simulated — no real money at risk.
          </div>
        )}
      </Card>

      <Card>
        <CardTitle>Pipeline Config</CardTitle>
        {[
          { key:"CONFIDENCE_THRESHOLD", value:"0.60" },
          { key:"FLAT_STAKE", value:"£10.00" },
          { key:"MIN_LEAD_HOURS", value:"2" },
          { key:"MAX_LEAD_HOURS", value:"48" },
          { key:"ANALYSIS_HOUR", value:"16:00 UTC" },
          { key:"CALENDAR_LOOKAHEAD", value:"7 days" },
        ].map(({ key, value }) => (
          <div key={key} style={{ display:"flex", justifyContent:"space-between", padding:"8px 0", borderBottom:`1px solid ${tokens.colors.border}`, fontSize:12 }}>
            <span style={{ color:tokens.colors.muted, fontFamily:tokens.fonts.mono, fontSize:11 }}>{key}</span>
            <span style={{ color:tokens.colors.text }}>{value}</span>
          </div>
        ))}
      </Card>

      <Card>
        <CardTitle>API Quota</CardTitle>
        <div style={{ marginBottom:16 }}>
          <div style={{ display:"flex", justifyContent:"space-between", fontSize:12, marginBottom:8 }}>
            <span style={{ color:tokens.colors.muted }}>Odds API</span>
            <span>347 <span style={{ color:tokens.colors.muted }}>/ 500</span></span>
          </div>
          <div style={{ height:6, background:tokens.colors.border }}>
            <div style={{ height:"100%", width:"69%", background:tokens.colors.amber }} />
          </div>
          <div style={{ fontSize:10, color:tokens.colors.muted, marginTop:6 }}>153 calls remaining · resets monthly</div>
        </div>
        <div>
          <div style={{ display:"flex", justifyContent:"space-between", fontSize:12, marginBottom:8 }}>
            <span style={{ color:tokens.colors.muted }}>Football Data API</span>
            <span style={{ color:tokens.colors.green }}>Unlimited</span>
          </div>
          <div style={{ height:6, background:tokens.colors.border }}>
            <div style={{ height:"100%", width:"100%", background:tokens.colors.green }} />
          </div>
        </div>
      </Card>

      <Card>
        <CardTitle>System</CardTitle>
        {[
          { key:"Host",         value:"brians-lab" },
          { key:"Uptime",       value:"3d 2h 14m" },
          { key:"Docker",       value:"running" },
          { key:"DB Size",      value:"2.1 MB" },
          { key:"Last Backup",  value:"04:00 today" },
          { key:"Tailscale IP", value:"100.x.x.x" },
        ].map(({ key, value }) => (
          <div key={key} style={{ display:"flex", justifyContent:"space-between", padding:"8px 0", borderBottom:`1px solid ${tokens.colors.border}`, fontSize:12 }}>
            <span style={{ color:tokens.colors.muted }}>{key}</span>
            <span style={{ color: value==="running" ? tokens.colors.green : tokens.colors.text }}>{value}</span>
          </div>
        ))}
      </Card>
    </div>
  </div>
);

// ─── Nav Config ───────────────────────────────────────────────────────────────
const navItems = [
  { id:"overview",  icon:"◈", label:"Overview" },
  { id:"picks",     icon:"◎", label:"Picks Feed",  badge: picks.filter(p=>p.status==="pending").length },
  { id:"pnl",       icon:"▲", label:"P&L" },
  { id:"agents",    icon:"⬡", label:"Agents" },
  { id:"fixtures",  icon:"▦", label:"Fixtures",    badge:174 },
  { id:"logs",      icon:"≡", label:"Logs" },
  { id:"settings",  icon:"⚙", label:"Settings" },
];

// ─── App Shell ────────────────────────────────────────────────────────────────
export default function App() {
  const [page, setPage] = useState("overview");
  const [mode, setMode] = useState("paper"); // "paper" | "live"
  const [time, setTime] = useState("");

  useEffect(() => { injectStyles(); }, []);

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setTime(now.toUTCString().split(" ")[4] + " UTC");
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  const modeColor   = mode === "paper" ? tokens.colors.amber : tokens.colors.green;
  const modeDim     = mode === "paper" ? tokens.colors.amberDim : tokens.colors.greenDim;
  const modeGlow    = mode === "paper" ? "paperGlow" : "liveGlow";

  const pages = { overview: <OverviewPage mode={mode} />, picks: <PicksFeedPage />, pnl: <PnLPage />, agents: <AgentsPage />, fixtures: <FixturesPage />, logs: <LogsPage />, settings: <SettingsPage mode={mode} setMode={setMode} /> };

  return (
    <div style={{ display:"flex", flexDirection:"column", height:"100vh" }}>

      {/* Header */}
      <div style={{
        borderBottom:`1px solid ${tokens.colors.border}`,
        padding:"0 24px", height:52,
        display:"flex", alignItems:"center", justifyContent:"space-between",
        background:tokens.colors.bg, position:"sticky", top:0, zIndex:100,
        flexShrink:0,
      }}>
        <div style={{ display:"flex", alignItems:"center", gap:16 }}>
          <span style={{ fontSize:11, fontWeight:600, letterSpacing:".2em", textTransform:"uppercase", color:tokens.colors.green }}>
            Pipeline Ops
          </span>
          <span style={{ color:tokens.colors.dim }}>/</span>
          <span style={{ color:tokens.colors.muted, fontSize:11, letterSpacing:".05em" }}>brians-lab</span>
        </div>

        <div style={{ display:"flex", alignItems:"center", gap:16 }}>
          {/* Mode indicator — prominent */}
          <div style={{
            display:"flex", alignItems:"center", gap:8,
            padding:"5px 14px",
            border:`1px solid ${modeColor}`,
            background: modeDim,
            cursor:"pointer",
            animation: `${modeGlow} 3s ease-in-out infinite`,
          }} onClick={() => setMode(mode==="paper"?"live":"paper")}>
            <div style={{ width:6, height:6, borderRadius:"50%", background:modeColor, animation:"pulse 1.5s infinite" }} />
            <span style={{ fontSize:10, letterSpacing:".2em", textTransform:"uppercase", color:modeColor, fontWeight:600 }}>
              {mode === "paper" ? "Paper Trading" : "⚡ Live"}
            </span>
          </div>

          <div style={{ display:"flex", alignItems:"center", gap:8, padding:"5px 10px", border:`1px solid ${tokens.colors.green}`, background:tokens.colors.greenDim }}>
            <Pulse />
            <span style={{ fontSize:10, letterSpacing:".15em", textTransform:"uppercase", color:tokens.colors.green }}>Running</span>
          </div>

          <span style={{ fontSize:11, color:tokens.colors.muted }}>{time}</span>
        </div>
      </div>

      <div style={{ display:"flex", flex:1, overflow:"hidden" }}>

        {/* Sidebar */}
        <div style={{ width:220, borderRight:`1px solid ${tokens.colors.border}`, flexShrink:0, overflowY:"auto", display:"flex", flexDirection:"column" }}>
          <div style={{ padding:"20px 16px 8px" }}>
            <div style={{ fontSize:10, letterSpacing:".2em", textTransform:"uppercase", color:tokens.colors.muted, marginBottom:8, padding:"0 8px" }}>View</div>
            {navItems.map(item => (
              <div key={item.id} onClick={() => setPage(item.id)} style={{
                display:"flex", alignItems:"center", gap:10,
                padding:"8px 10px", cursor:"pointer",
                color: page===item.id ? modeColor : tokens.colors.muted,
                background: page===item.id ? modeDim : "transparent",
                border: `1px solid ${page===item.id ? modeColor : "transparent"}`,
                marginBottom:2, transition:"all .15s", fontSize:12,
              }}>
                <span style={{ width:14, textAlign:"center", fontSize:13 }}>{item.icon}</span>
                <span>{item.label}</span>
                {item.badge !== undefined && (
                  <span style={{
                    marginLeft:"auto", fontSize:10, padding:"1px 6px",
                    background: item.id==="picks" ? tokens.colors.amberDim : tokens.colors.blueDim,
                    color: item.id==="picks" ? tokens.colors.amber : tokens.colors.blue,
                    border:`1px solid ${item.id==="picks" ? tokens.colors.amber : tokens.colors.blue}`,
                  }}>{item.badge}</span>
                )}
              </div>
            ))}
          </div>

          {/* Sidebar stats */}
          <div style={{ padding:"16px", borderTop:`1px solid ${tokens.colors.border}`, marginTop:"auto" }}>
            <div style={{ fontSize:10, letterSpacing:".15em", textTransform:"uppercase", color:tokens.colors.muted, marginBottom:10 }}>
              {mode === "paper" ? "Paper Trading" : "Live Trading"}
            </div>
            {[
              { label:"Started", value:"2026-03-30", sub:"Day 3 of 14" },
              { label:"Total Picks", value:"47", valueColor:modeColor, sub:"across 4 agents" },
              { label:"Net P&L", value:"+£34.20", valueColor:tokens.colors.green, sub:"settled 18 picks" },
            ].map(({ label, value, valueColor, sub }) => (
              <div key={label} style={{ padding:10, border:`1px solid ${tokens.colors.border}`, background:tokens.colors.surface, marginBottom:6 }}>
                <div style={{ fontSize:9, color:tokens.colors.muted, letterSpacing:".1em", textTransform:"uppercase", marginBottom:4 }}>{label}</div>
                <div style={{ fontSize:16, fontWeight:500, color:valueColor||tokens.colors.text }}>{value}</div>
                {sub && <div style={{ fontSize:10, color:tokens.colors.muted, marginTop:2 }}>{sub}</div>}
              </div>
            ))}

            {/* API quota */}
            <div style={{ padding:10, border:`1px solid ${tokens.colors.border}`, background:tokens.colors.surface, marginTop:4 }}>
              <div style={{ fontSize:9, color:tokens.colors.muted, letterSpacing:".1em", textTransform:"uppercase", marginBottom:6 }}>Odds API</div>
              <div style={{ display:"flex", justifyContent:"space-between", fontSize:12, marginBottom:6 }}>
                <span style={{ color:tokens.colors.text }}>347</span>
                <span style={{ color:tokens.colors.muted }}>/ 500</span>
              </div>
              <div style={{ height:4, background:tokens.colors.border }}>
                <div style={{ height:"100%", width:"69%", background:tokens.colors.amber }} />
              </div>
            </div>
          </div>
        </div>

        {/* Main content */}
        <div style={{ flex:1, padding:24, overflowY:"auto" }}>
          {pages[page]}
        </div>
      </div>
    </div>
  );
}