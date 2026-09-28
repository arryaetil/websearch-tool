"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Image from "next/image";
import {
  ArrowDownToLine, ArrowRight, ArrowUpRight, Check,
  CircleHelp, Command, FileSearch, FileText, Fingerprint,
  Globe2, Layers3, Link2, LoaderCircle, Menu, PanelLeftClose, Plus,
  Search, X,
} from "lucide-react";

type Identity = "confirmed" | "possible" | "unrelated";
type Claim = { summary: string; quote: string };
type Source = {
  url: string;
  title: string;
  identity: Identity;
  reason: string;
  confidence_score?: number;
  claims: Claim[];
  retrieved_at: string;
  sha256: string;
};
type Report = {
  saved_run?: { id: string; created_at: number; expires_at: number };
  subject: { name: string; city: string; employer: string };
  sources: Source[];
  confirmed_findings: { summary: string; quote: string; url: string }[];
  risk_flags?: string[];
  review_status: string;
  limitations: string[];
  errors: string[];
  metrics?: {
    total_seconds: number; search_seconds: number; fetch_seconds: number;
    assess_seconds: number; search_queries: number; pages_read: number;
    model_calls: number; input_tokens: number; output_tokens: number;
    estimated_usd: number | null;
  };
};
type SavedRun = { id: string; created_at: number; expires_at: number; name: string; city: string; employer: string };

const label: Record<Identity, string> = {
  confirmed: "Strong identity match",
  possible: "Needs review",
  unrelated: "Different person",
};

function Brand() {
  return <div className="brand" aria-label="KYCX Adverse Media Check">
    <div className="brand-type"><div className="original-wordmark"><Image src="/kycx-original-logo.png" width={4000} height={4000} alt="KYCX" priority/></div></div>
  </div>;
}

function StatusPill({ identity }: { identity: Identity }) {
  return <span className={`status-pill ${identity}`}><span className="status-dot"/>{label[identity]}</span>;
}

export default function Home() {
  const [name, setName] = useState("");
  const [city, setCity] = useState("");
  const [employer, setEmployer] = useState("");
  const [report, setReport] = useState<Report | null>(null);
  const [savedRuns, setSavedRuns] = useState<SavedRun[]>([]);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [selected, setSelected] = useState(0);
  const [filter, setFilter] = useState<"all" | Identity>("all");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const resultRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        inputRef.current?.focus();
      } else if (event.key === "/" && !(event.target instanceof HTMLInputElement)) {
        event.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  async function refreshRuns() {
    try {
      const response = await fetch("/api/runs", { cache: "no-store" });
      if (response.ok) setSavedRuns((await response.json()).runs);
    } catch { /* The current check remains usable if history is unavailable. */ }
  }

  useEffect(() => { void refreshRuns(); }, []);
  useEffect(() => { if (report) resultRef.current?.focus(); }, [report]);

  async function openRun(id: string) {
    setError("");
    try {
      const response = await fetch(`/api/runs/${id}`, { cache: "no-store" });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Could not open saved run.");
      setReport(payload as Report);
      setActiveRunId(id);
      setName(payload.subject.name);
      setCity(payload.subject.city);
      setEmployer(payload.subject.employer || "");
      setSelected(0);
      setFilter("all");
      setSidebarOpen(false);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not open saved run."); }
  }

  async function removeRun(id: string) {
    const run = savedRuns.find((item) => item.id === id);
    if (!window.confirm(`Delete the saved check for ${run?.name || "this person"}?`)) return;
    try {
      const response = await fetch(`/api/runs/${id}`, { method: "DELETE" });
      if (!response.ok) throw new Error("Could not delete saved run.");
      if (activeRunId === id) { setReport(null); setActiveRunId(null); }
      await refreshRuns();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not delete saved run."); }
  }

  const sources = report?.sources ?? [];
  const counts = {
    confirmed: sources.filter((source) => source.identity === "confirmed").length,
    possible: sources.filter((source) => source.identity === "possible").length,
    unrelated: sources.filter((source) => source.identity === "unrelated").length,
  };
  const filtered = sources.filter((source) => filter === "all" || source.identity === filter);
  const current = filtered.find((source) => sources.indexOf(source) === selected);
  const highestConfidence = sources.reduce<number | null>((highest, source) =>
    source.confidence_score === undefined ? highest : Math.max(highest ?? 0, source.confidence_score), null);

  async function runResearch(event: FormEvent) {
    event.preventDefault();
    if (!name.trim() || !city.trim()) {
      setError("Enter a full name and city to start an investigation.");
      return;
    }
    setRunning(true);
    setError("");
    try {
      const response = await fetch("/api/research", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ name, city, employer }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Adverse media check failed.");
      setReport(payload as Report);
      setActiveRunId(payload.saved_run?.id ?? null);
      await refreshRuns();
      setSelected(0);
      setFilter("all");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Adverse media check failed. Try again.");
    } finally {
      setRunning(false);
    }
  }

  async function downloadPdf() {
    if (!report) return;
    setError("");
    try {
      const response = await fetch("/api/report", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ report }),
      });
      if (!response.ok) throw new Error("Could not create the PDF draft.");
      const objectUrl = URL.createObjectURL(await response.blob());
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = "adverse-media-check-draft.pdf";
      anchor.click();
      URL.revokeObjectURL(objectUrl);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not download the PDF.");
    }
  }

  function changeFilter(value: "all" | Identity) {
    setFilter(value);
    const first = sources.findIndex((source) => value === "all" || source.identity === value);
    setSelected(first);
  }

  function startNew() {
    setReport(null);
    setActiveRunId(null);
    setName("");
    setCity("");
    setEmployer("");
    setError("");
    setSidebarOpen(false);
    setTimeout(() => inputRef.current?.focus(), 0);
  }

  return <div className="app-shell">
    <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
      <div className="sidebar-top"><Brand/><button className="icon-button sidebar-close" onClick={() => setSidebarOpen(false)} aria-label="Close menu"><PanelLeftClose size={18}/></button></div>

      <button className="new-research" onClick={startNew}><Plus size={17}/> New check</button>
      <div className="saved-runs"><div className="saved-runs-header">Saved checks · 7 days <span>{savedRuns.length}</span></div><div className="saved-runs-list">{savedRuns.map((run) => <div className="saved-run" key={run.id}><button className="saved-run-open" onClick={() => void openRun(run.id)}><strong>{run.name}</strong><small>{run.city} · {new Date(run.created_at * 1000).toLocaleDateString("en-GB")}</small></button><button className="saved-run-delete" onClick={() => void removeRun(run.id)} aria-label={`Delete check for ${run.name}`} title="Delete saved check"><X size={14}/></button></div>)}</div>{savedRuns.length > 0 && <button className="saved-runs-clear" onClick={async () => { if (!window.confirm("Delete all saved checks?")) return; try { const response = await fetch("/api/runs", { method: "DELETE" }); if (!response.ok) throw new Error("Could not delete saved checks."); setReport(null); setActiveRunId(null); await refreshRuns(); } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not delete saved checks."); } }}>Delete all checks</button>}</div>
      <div className="sidebar-bottom"><div className="sidebar-separator"/><div className="powered-by"><span>POWERED BY</span><Image src="/ibc-group-official.png" width={108} height={49} alt="ibc group"/></div></div>
    </aside>
    {sidebarOpen && <button className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} aria-label="Close menu"/>}

    <main className="main-area">
      <header className="topbar"><button className="icon-button mobile-menu" onClick={() => setSidebarOpen(true)} aria-label="Open menu"><Menu size={19}/></button><div className="topbar-right"><form action="/api/logout" method="post"><button className="signout-button" type="submit">Sign out</button></form></div></header>
      <div className="tech-hero"><div className="content"><h1>Adverse media check</h1></div></div>

      <div className="content">
        <form className="search-panel" onSubmit={runResearch}><div className="search-panel-header"><div className="search-icon"><Search size={19}/></div><div><strong>Check a person</strong></div><span className="shortcut"><Command size={12}/> /</span></div><div className="search-fields"><label className="field field-name"><span>FULL NAME <em>*</em></span><input ref={inputRef} value={name} onChange={(event) => setName(event.target.value)} placeholder="e.g. Jordan Example" autoComplete="off" required minLength={3}/></label><label className="field"><span>CITY OR REGION <em>*</em></span><input value={city} onChange={(event) => setCity(event.target.value)} placeholder="e.g. Utrecht" autoComplete="off" required minLength={2}/></label><label className="field"><span>EMPLOYER <small>FOR A STRONG MATCH</small></span><input value={employer} onChange={(event) => setEmployer(event.target.value)} placeholder="e.g. Example Studio" autoComplete="off"/></label><button className="search-submit" type="submit" disabled={running}>{running ? <LoaderCircle size={18} className="spin"/> : <ArrowRight size={18}/>}<span>{running ? "Checking" : "Run check"}</span></button></div></form>


        {error && <div className="error-banner" role="alert"><CircleHelp size={17}/><span>{error}</span><button onClick={() => setError("")} aria-label="Dismiss error"><X size={16}/></button></div>}

        {running && <div className="running-panel" role="status" aria-live="polite"><LoaderCircle size={21} className="spin"/><div><strong>Check in progress</strong><span>Searching sources and assessing identity. This can take a minute.</span></div></div>}

        {report ? <>
          <section className="case-heading"><div className="case-heading-left"><div className="case-avatar">{report.subject.name.split(" ").map((part) => part[0]).slice(0, 2).join("").toUpperCase()}</div><div><div className="case-title-line"><h2 ref={resultRef} tabIndex={-1}>{report.subject.name}</h2></div><div className="case-subline"><span><Globe2 size={14}/>{report.subject.city}</span>{report.subject.employer && <><i/><span>{report.subject.employer}</span></>}</div></div></div><div className="case-actions"><button className="outline-button" onClick={downloadPdf} ><ArrowDownToLine size={16}/> Export draft</button></div></section>

          <section className="result-summary" aria-label="Check summary"><div><strong>{report.confirmed_findings.length}</strong><span>linked adverse {report.confirmed_findings.length === 1 ? "finding" : "findings"}</span></div><div><strong>{highestConfidence === null ? "—" : `${highestConfidence}/3`}</strong><span>identity confidence</span></div><div><strong>{counts.possible}</strong><span>sources need identity review</span></div></section>
          <div className="risk-summary"><strong>Risk flags</strong>{report.risk_flags?.length ? <ul>{report.risk_flags.map((flag) => <li key={flag}>{flag}</li>)}</ul> : <span>No flags from the sources reviewed</span>}<small>Identity confidence measures matching evidence, not the likelihood of misconduct.</small></div>

          {report.errors.length > 0 && <details className="coverage-details"><summary>{report.errors.length} {report.errors.length === 1 ? "source" : "sources"} could not be read</summary><ul>{report.errors.map((item, index) => <li key={index}>{item}</li>)}</ul></details>}

          <section className="results-section"><div className="section-heading"><div><h2 id="sources-heading">Source analysis <span className="section-count">{sources.length}</span></h2></div></div>
            <div className="results-workspace"><div className="source-pane"><div className="source-pane-header"><span><Layers3 size={15}/> Sources</span></div><div className="filter-row">{(["all", "confirmed", "possible", "unrelated"] as const).map((value) => <button key={value} type="button" aria-pressed={filter === value} className={filter === value ? "filter active" : "filter"} onClick={() => changeFilter(value)}>{value === "all" ? `All ${sources.length}` : value === "confirmed" ? `Matched ${counts.confirmed}` : value === "possible" ? `Review ${counts.possible}` : `Other ${counts.unrelated}`}</button>)}</div><div className="source-list">{filtered.length ? filtered.map((source) => { const index = sources.indexOf(source); return <button key={`${source.url}-${index}`} type="button" aria-pressed={selected === index} className={`source-item ${selected === index ? "selected" : ""}`} onClick={() => setSelected(index)}><div className="source-item-top"><span className={`source-mini-icon ${source.identity}`}><FileText size={15}/></span><span className="source-domain">{(() => { try { return new URL(source.url).hostname.replace(/^www\./, ""); } catch { return "SOURCE"; } })()}</span></div><strong>{source.title || "Untitled source"}</strong><div className="source-item-bottom"><StatusPill identity={source.identity}/><span>{source.claims.length} {source.claims.length === 1 ? "finding" : "findings"}</span></div></button>; }) : <div className="source-empty">No sources in this category.</div>}</div></div>

              <div className="detail-pane">{current ? <><div className="detail-topline"><span>SOURCE {String(selected + 1).padStart(2, "0")} <span>/</span> {String(sources.length).padStart(2, "0")}</span><span className="detail-updated">Retrieved {new Date(current.retrieved_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}</span></div><div className="detail-title-row">
  <div className="detail-title-content">
    <div className="detail-domain"><Globe2 size={14}/>{(() => { try { return new URL(current.url).hostname; } catch { return "Source"; } })()}</div>
    <h3><a className="source-title-link" href={current.url} target="_blank" rel="noopener noreferrer">{current.title || "Untitled source"}<ArrowUpRight size={17}/></a></h3>
  </div>
  <a className="open-source-button" href={current.url} target="_blank" rel="noopener noreferrer">Open source <ArrowUpRight size={15}/></a>
</div><div className="identity-assessment"><div className="assessment-header"><div><Fingerprint size={18}/><span>IDENTITY ASSESSMENT</span></div><StatusPill identity={current.identity}/></div><p>{current.reason || "No explanation returned."}</p><div className="assessment-foot"><span className={`assessment-indicator ${current.identity}`}/>{current.confidence_score === undefined ? "Identity confidence unavailable for this saved check" : `Identity confidence ${current.confidence_score}/3 · ${current.identity === "confirmed" ? "name, city and employer linked" : current.identity === "possible" ? "more identity evidence needed" : "different person"}`}</div></div><div className="findings-head"><div><span className="purple-bar"/><h4>Source findings</h4><span>{current.claims.length}</span></div><small>Only verbatim supported claims are shown</small></div>{current.claims.length ? <div className="claims-list">{current.claims.map((claim, index) => <div className="claim-card" key={index}><div className="claim-number">{String(index + 1).padStart(2, "0")}</div><div><strong>{claim.summary}</strong><div className="quote"><span>“</span>{claim.quote}<span>”</span></div><div className="claim-verified"><Check size={13}/> Quote found on source page</div></div></div>)}</div> : <div className="no-findings"><FileSearch size={25}/><strong>No findings linked</strong><span>{current.identity === "possible" ? "This source needs an analyst’s identity check before any claims can be used." : current.identity === "unrelated" ? "This source appears to describe someone else." : "No supported claims were extracted from this source."}</span></div>}<div className="source-meta"><div className="source-url"><Link2 size={13}/><a href={current.url} target="_blank" rel="noopener noreferrer">{current.url}</a></div><span>SHA-256: {current.sha256.slice(0, 12)}…</span></div></> : <div className="detail-empty"><FileSearch size={30}/><h3>{filtered.length === 0 && sources.length > 0 ? "No sources in this category" : "No readable sources found"}</h3><p>{filtered.length === 0 && sources.length > 0 ? "Choose another filter to view a source." : "Try adding another identity clue and run the check again."}</p></div>}</div></div></section>

          {report.metrics && <details className="run-metrics"><summary>Run details</summary><div className="run-metrics-values"><span><strong>{report.metrics.total_seconds.toFixed(1)}s</strong> total</span><span>Search {report.metrics.search_seconds.toFixed(1)}s</span><span>Read {report.metrics.fetch_seconds.toFixed(1)}s</span><span>Assess {report.metrics.assess_seconds.toFixed(1)}s</span><span>{report.metrics.search_queries} searches · {report.metrics.model_calls} model calls</span><span>{report.metrics.estimated_usd === null ? "Cost unavailable" : `Est. provider cost $${report.metrics.estimated_usd.toFixed(3)}`}</span></div></details>}


        </> : null}
        <footer className="page-footer"><span>© 2026 KYCX · ibc group</span></footer>
      </div>
    </main>
  </div>;
}
