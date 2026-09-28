"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Image from "next/image";
import {
  ArrowDownToLine, ArrowRight, ArrowUpRight, Check, CheckCheck,
  CircleHelp, Clock3, Command, FileSearch, FileText, Fingerprint,
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
  claims: Claim[];
  retrieved_at: string;
  sha256: string;
};
type Report = {
  subject: { name: string; city: string; employer: string };
  sources: Source[];
  confirmed_findings: { summary: string; quote: string; url: string }[];
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

const label: Record<Identity, string> = {
  confirmed: "Strong match",
  possible: "Needs review",
  unrelated: "Different person",
};

function Brand() {
  return <div className="brand" aria-label="KYCX Adverse Media Check">
    <div className="brand-type"><div className="original-wordmark"><Image src="/kycx-original-logo.png" width={4000} height={4000} alt="KYCX" priority/></div><small>ADVERSE MEDIA CHECK</small></div>
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
  const [selected, setSelected] = useState(0);
  const [filter, setFilter] = useState<"all" | Identity>("all");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

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

  const sources = report?.sources ?? [];
  const counts = {
    confirmed: sources.filter((source) => source.identity === "confirmed").length,
    possible: sources.filter((source) => source.identity === "possible").length,
    unrelated: sources.filter((source) => source.identity === "unrelated").length,
  };
  const filtered = sources.filter((source) => filter === "all" || source.identity === filter);
  const current = sources[selected];

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
      setSelected(0);
      setFilter("all");
      window.scrollTo({ top: 0, behavior: "smooth" });
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
    if (first >= 0) setSelected(first);
  }

  function startNew() {
    setReport(null);
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
      <div className="sidebar-bottom"><div className="sidebar-separator"/><div className="powered-by"><span>POWERED BY</span><Image src="/ibc-group-official.png" width={108} height={49} alt="ibc group"/></div></div>
    </aside>
    {sidebarOpen && <button className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} aria-label="Close menu"/>}

    <main className="main-area">
      <header className="topbar"><button className="icon-button mobile-menu" onClick={() => setSidebarOpen(true)} aria-label="Open menu"><Menu size={19}/></button><div className="topbar-right"><form action="/api/logout" method="post"><button className="signout-button" type="submit">Sign out</button></form></div></header>
      <div className="tech-hero"><div className="content"><h1>Adverse media check</h1></div></div>

      <div className="content">
        <form className="search-panel" onSubmit={runResearch}><div className="search-panel-header"><div className="search-icon"><Search size={19}/></div><div><strong>Check a person</strong></div><span className="shortcut"><Command size={12}/> /</span></div><div className="search-fields"><label className="field field-name"><span>FULL NAME <em>*</em></span><input ref={inputRef} value={name} onChange={(event) => setName(event.target.value)} placeholder="e.g. Jordan Example" autoComplete="off"/></label><label className="field"><span>CITY OR REGION <em>*</em></span><input value={city} onChange={(event) => setCity(event.target.value)} placeholder="e.g. Utrecht" autoComplete="off"/></label><label className="field"><span>EMPLOYER <small>FOR A STRONG MATCH</small></span><input value={employer} onChange={(event) => setEmployer(event.target.value)} placeholder="e.g. Example Studio" autoComplete="off"/></label><button className="search-submit" type="submit" disabled={running}>{running ? <LoaderCircle size={18} className="spin"/> : <ArrowRight size={18}/>}<span>{running ? "Checking" : "Run check"}</span></button></div></form>


        {error && <div className="error-banner" role="alert"><CircleHelp size={17}/><span>{error}</span><button onClick={() => setError("")} aria-label="Dismiss error"><X size={16}/></button></div>}

        {running && <div className="running-panel"><LoaderCircle size={21} className="spin"/><div><strong>Adverse media check in progress</strong><span>Searching public sources, reading pages and checking identity clues. This can take a minute.</span></div></div>}

        {report ? <>
          <section className="case-heading"><div className="case-heading-left"><div className="case-avatar">{report.subject.name.split(" ").map((part) => part[0]).slice(0, 2).join("").toUpperCase()}</div><div><div className="case-title-line"><h2>{report.subject.name}</h2></div><div className="case-subline"><span><Globe2 size={14}/>{report.subject.city}</span>{report.subject.employer && <><i/><span>{report.subject.employer}</span></>}<i/><span><Clock3 size={14}/> Check draft</span></div></div></div><div className="case-actions"><button className="outline-button" onClick={downloadPdf} ><ArrowDownToLine size={16}/> Export draft</button></div></section>

          {report.metrics && <div className="run-metrics" aria-label="Check time and estimated provider cost"><span><strong>{report.metrics.total_seconds.toFixed(1)}s</strong> total</span><span>Search {report.metrics.search_seconds.toFixed(1)}s</span><span>Read {report.metrics.fetch_seconds.toFixed(1)}s</span><span>Assess {report.metrics.assess_seconds.toFixed(1)}s</span><span>{report.metrics.search_queries} searches · {report.metrics.model_calls} model calls</span><span>{report.metrics.estimated_usd === null ? "Cost unavailable" : `Est. provider cost $${report.metrics.estimated_usd.toFixed(3)}`}</span></div>}

          <section className="metrics-row" aria-label="Adverse media check overview"><div className="metric"><div className="metric-icon purple"><FileSearch size={18}/></div><div><span>SOURCES REVIEWED</span><strong>{sources.length.toString().padStart(2, "0")}</strong></div></div><div className="metric"><div className="metric-icon mint"><CheckCheck size={18}/></div><div><span>STRONG MATCHES</span><strong>{counts.confirmed.toString().padStart(2, "0")}</strong></div></div><div className="metric"><div className="metric-icon amber"><CircleHelp size={18}/></div><div><span>NEEDS REVIEW</span><strong>{counts.possible.toString().padStart(2, "0")}</strong></div></div><div className="metric"><div className="metric-icon slate"><X size={17}/></div><div><span>OTHER PEOPLE</span><strong>{counts.unrelated.toString().padStart(2, "0")}</strong></div></div></section>

          <section className="results-section"><div className="section-heading"><div><h2 id="sources-heading">Source analysis <span className="section-count">{sources.length}</span></h2></div></div>
            <div className="results-workspace"><div className="source-pane"><div className="source-pane-header"><span><Layers3 size={15}/> Sources</span></div><div className="filter-row">{(["all", "confirmed", "possible", "unrelated"] as const).map((value) => <button key={value} className={filter === value ? "filter active" : "filter"} onClick={() => changeFilter(value)}>{value === "all" ? "All" : value === "confirmed" ? "Matched" : value === "possible" ? "Review" : "Other"}</button>)}</div><div className="source-list">{filtered.length ? filtered.map((source) => { const index = sources.indexOf(source); return <button key={`${source.url}-${index}`} className={`source-item ${selected === index ? "selected" : ""}`} onClick={() => setSelected(index)}><div className="source-item-top"><span className={`source-mini-icon ${source.identity}`}><FileText size={15}/></span><span className="source-domain">{(() => { try { return new URL(source.url).hostname.replace(/^www\./, ""); } catch { return "SOURCE"; } })()}</span><ArrowUpRight size={14}/></div><strong>{source.title || "Untitled source"}</strong><div className="source-item-bottom"><StatusPill identity={source.identity}/><span>{source.claims.length} {source.claims.length === 1 ? "finding" : "findings"}</span></div></button>; }) : <div className="source-empty">No sources in this category.</div>}</div></div>

              <div className="detail-pane">{current ? <><div className="detail-topline"><span>SOURCE {String(selected + 1).padStart(2, "0")} <span>/</span> {String(sources.length).padStart(2, "0")}</span><span className="detail-updated">Retrieved {new Date(current.retrieved_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}</span></div><div className="detail-title-row">
  <div className="detail-title-content">
    <div className="detail-domain"><Globe2 size={14}/>{(() => { try { return new URL(current.url).hostname; } catch { return "Source"; } })()}</div>
    <h3><a className="source-title-link" href={current.url} target="_blank" rel="noopener noreferrer">{current.title || "Untitled source"}<ArrowUpRight size={17}/></a></h3>
  </div>
  <a className="open-source-button" href={current.url} target="_blank" rel="noopener noreferrer">Open source <ArrowUpRight size={15}/></a>
</div><div className="identity-assessment"><div className="assessment-header"><div><Fingerprint size={18}/><span>IDENTITY ASSESSMENT</span></div><StatusPill identity={current.identity}/></div><p>{current.reason || "No explanation returned."}</p><div className="assessment-foot"><span className={`assessment-indicator ${current.identity}`}/>{current.identity === "confirmed" ? "Name, city and employer found in source" : current.identity === "possible" ? "More evidence needed before linking findings" : "Not linked to the researched person"}</div></div><div className="findings-head"><div><span className="purple-bar"/><h4>Source findings</h4><span>{current.claims.length}</span></div><small>Only verbatim supported claims are shown</small></div>{current.claims.length ? <div className="claims-list">{current.claims.map((claim, index) => <div className="claim-card" key={index}><div className="claim-number">{String(index + 1).padStart(2, "0")}</div><div><strong>{claim.summary}</strong><div className="quote"><span>“</span>{claim.quote}<span>”</span></div><div className="claim-verified"><Check size={13}/> Quote found on source page</div></div></div>)}</div> : <div className="no-findings"><FileSearch size={25}/><strong>No findings linked</strong><span>{current.identity === "possible" ? "This source needs an analyst’s identity check before any claims can be used." : current.identity === "unrelated" ? "This source appears to describe someone else." : "No supported claims were extracted from this source."}</span></div>}<div className="source-meta"><div className="source-url"><Link2 size={13}/><a href={current.url} target="_blank" rel="noopener noreferrer">{current.url}</a></div><span>SHA-256: {current.sha256.slice(0, 12)}…</span></div></> : <div className="detail-empty"><FileSearch size={30}/><h3>No readable sources found</h3><p>Search coverage may be incomplete. Try adding another identity clue or review sources manually.</p></div>}</div></div></section>


        </> : null}
        <footer className="page-footer"><span>© 2026 KYCX · ibc group</span></footer>
      </div>
    </main>
  </div>;
}
