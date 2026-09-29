"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Image from "next/image";
import {
  ArrowDownToLine, ArrowRight, ArrowUpRight, CircleHelp, Command,
  Globe2, LoaderCircle, Menu, PanelLeftClose, Plus, Search, X,
} from "lucide-react";

type Identity = "confirmed" | "possible" | "unrelated";
type Claim = { summary: string; quote: string; type?: string };
type CardStatus = "full" | "partial" | "match" | "conflict" | "absent";
type CardField = { status: CardStatus; value?: string | number | null; quote?: string | null; note?: string };
type CardKey = "name" | "city" | "employer" | "age" | "profession";
type Source = {
  url: string;
  title: string;
  identity: Identity;
  reason: string;
  confidence_score?: number;
  identity_card?: Record<CardKey, CardField>;
  archive?: { url: string; timestamp: string } | null;
  claims: Claim[];
  candidate_claims?: Claim[];
  leads?: { kind: string; value: string; source_url: string }[];
  retrieved_at: string;
  sha256: string;
};
type FlagGroup = "act" | "review" | "coverage";
type Flag = { code: string; group: FlagGroup; label: string; reason: string; source_urls: string[] };
type CoverageStatus = "searched" | "not_applicable" | "failed" | "stale" | "manual";
type CoverageEntry = { key: string; label: string; status: CoverageStatus; detail: string; url?: string };
type Profession = "unknown" | "healthcare" | "lawyer" | "other";
type Report = {
  saved_run?: { id: string; created_at: number; expires_at: number };
  subject: { name: string; city: string; employer: string; aliases?: string[]; birth_year?: number | ""; profession?: Profession | "" };
  sources: Source[];
  confirmed_findings: { summary: string; quote: string; url: string }[];
  sanction_hits?: { list: string; matched_name: string; identity: Identity; reason: string; url: string }[];
  candidate_findings?: { summary: string; quote: string; url: string; type: string; confidence_score: number }[];
  confidence_score?: number;
  confidence_reasoning?: string;
  risk_flags?: string[];
  flags?: Flag[];
  coverage?: CoverageEntry[];
  next_identifiers?: string[];
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

// Four ordered evidence tiers shown on a 100-point scale, not probabilities.
const scoreOutOf100 = (tier: number) => [0, 33, 67, 100][Math.max(0, Math.min(3, Math.round(tier)))] ?? 0;

const coverageWord: Record<CoverageStatus, string> = {
  searched: "Searched", not_applicable: "Not applicable", failed: "Not searched", stale: "Outdated list", manual: "Manual check",
};

function ReportSections({ report, onSource, sourcesRef }: { report: Report; onSource: (url: string) => void; sourcesRef: React.RefObject<HTMLDetailsElement | null> }) {
  const relevant = report.sources.filter((source) => source.claims.length || source.candidate_claims?.length);
  const legal = relevant.filter((source) => [...source.claims, ...(source.candidate_claims || [])]
    .some((claim) => ["charge", "conviction", "settlement", "fine", "sanction", "professional_measure"].includes(claim.type || "")));
  const identities = report.sources.filter((source) => source.identity !== "unrelated");
  const businessLeads = report.sources.flatMap((source) => source.leads || []).filter((lead) => lead.kind === "company");
  const evidence = (items: Source[]) => items.length ? items.map((source) => <div className="legacy-item" key={source.url}>
    <strong>{source.title || "Untitled source"}</strong>
    <span>{source.identity === "confirmed" ? "Strong identity match" : "Identity to verify"} · confidence {source.confidence_score === undefined ? "—" : scoreOutOf100(source.confidence_score)}/100</span>
    {[...source.claims, ...(source.candidate_claims || [])].map((claim, index) => <div key={index}>
      <p>{claim.type || "report"}: {claim.summary}</p><blockquote>“{claim.quote}”</blockquote>
    </div>)}
    <button type="button" onClick={() => onSource(source.url)}>Inspect evidence <ArrowRight size={13}/></button>
    <a href={source.url} target="_blank" rel="noopener noreferrer">Original source <ArrowUpRight size={13}/></a>
  </div>) : <p className="legacy-empty">Insufficient data from readable sources.</p>;
  return <>
    <div className="legacy-columns">
      <div className="legacy-column">
        <details><summary>Identity Matches <span>{identities.length}</span></summary><div className="legacy-content">{identities.length ? identities.map((source) => <div className="legacy-item" key={source.url}><strong>{source.identity_card?.name?.value || source.title || "Possible identity"}</strong><span>{source.identity === "confirmed" ? "Strong match" : "Needs review"} · identity evidence {source.confidence_score === undefined ? "—" : scoreOutOf100(source.confidence_score)}/100</span><p>{source.reason}</p><button type="button" onClick={() => onSource(source.url)}>Inspect identity <ArrowRight size={13}/></button></div>) : <p className="legacy-empty">No identity leads in the readable sources.</p>}</div></details>
        <details><summary>Business Records <span>{businessLeads.length}</span></summary><div className="legacy-content">{businessLeads.length ? businessLeads.map((lead, index) => <div className="legacy-item" key={`${lead.source_url}-${index}`}><strong>{lead.value}</strong><span>Company mentioned in a source; registry role not verified</span><button type="button" onClick={() => onSource(lead.source_url)}>Inspect source <ArrowRight size={13}/></button></div>) : <p className="legacy-empty">No source-linked company leads found. Company roles were not independently verified.</p>}</div></details>
      </div>
      <div className="legacy-column">
        <details open><summary>Media Mentions <span>{relevant.length}</span></summary><div className="legacy-content">{evidence(relevant)}</div></details>
        <details><summary>Legal Public Records <span>{legal.length + (report.sanction_hits?.length || 0)}</span></summary><div className="legacy-content">{legal.length ? <><p className="legacy-empty">Reported legal claims from media or public pages; verify the original record.</p>{evidence(legal)}</> : <p className="legacy-empty">No source-supported legal claim extracted. This does not rule out a record.</p>}{report.sanction_hits?.map((hit, index) => <div className="legacy-item" key={`${hit.url}-${index}`}><strong>Sanctions list candidate · {hit.matched_name}</strong><span>{hit.list} · {hit.identity === "confirmed" ? "Strong match" : "Verify identity"}</span><p>{hit.reason}</p><a href={hit.url} target="_blank" rel="noopener noreferrer">Official list <ArrowUpRight size={13}/></a></div>)}</div></details>
      </div>
    </div>
    <details className="legacy-sources" ref={sourcesRef}><summary>Sources <span>{report.sources.length}</span></summary><div className="legacy-content">{report.sources.length ? report.sources.map((source, index) => <details className="source-evidence" data-source-index={index} key={`${source.url}-${index}`}><summary><strong>{source.title || "Untitled source"}</strong><span>{source.identity === "confirmed" ? "Strong match" : source.identity === "possible" ? "Identity to verify" : "Other person"} · identity evidence {source.confidence_score === undefined ? "—" : scoreOutOf100(source.confidence_score)}/100</span></summary><div className="source-evidence-body"><p>{source.reason}</p>{[...source.claims, ...(source.candidate_claims || [])].map((claim, claimIndex) => <blockquote key={claimIndex}><strong>{claim.summary}</strong><br/>“{claim.quote}”</blockquote>)}<a href={source.url} target="_blank" rel="noopener noreferrer">{source.url} <ArrowUpRight size={13}/></a>{source.archive && <a href={source.archive.url} target="_blank" rel="noopener noreferrer">Archived copy <ArrowUpRight size={13}/></a>}</div></details>) : <p className="legacy-empty">No readable sources found.</p>}{report.coverage && <div className="source-coverage"><strong>Automatic search coverage</strong>{report.coverage.filter((entry) => entry.status !== "manual" && entry.key !== "big").map((entry) => <p key={entry.key}>{entry.label}: {coverageWord[entry.status]} · {entry.detail}</p>)}</div>}{report.errors?.length > 0 && <div className="source-coverage"><strong>Unreadable pages</strong>{report.errors.map((item, index) => <p key={index}>{item}</p>)}</div>}</div></details>
  </>;
}

export default function Home() {
  const [name, setName] = useState("");
  const [city, setCity] = useState("");
  const [employer, setEmployer] = useState("");
  const [context, setContext] = useState("");
  const [aliases, setAliases] = useState("");
  const [birthYear, setBirthYear] = useState("");
  const [profession, setProfession] = useState<Profession>("unknown");
  const [report, setReport] = useState<Report | null>(null);
  const [savedRuns, setSavedRuns] = useState<SavedRun[]>([]);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const resultRef = useRef<HTMLHeadingElement>(null);
  const sourcesRef = useRef<HTMLDetailsElement>(null);

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
      setContext("");
      setAliases((payload.subject.aliases || []).join(", "));
      setBirthYear(payload.subject.birth_year ? String(payload.subject.birth_year) : "");
      setProfession(payload.subject.profession || "unknown");
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
  const highestConfidence = sources.reduce<number | null>((highest, source) =>
    source.confidence_score === undefined ? highest : Math.max(highest ?? 0, source.confidence_score), null);
  const adverseIdentityScore = report?.confidence_score ?? highestConfidence ?? 0;
  const adverseSource = sources.filter((source) => source.claims.length || source.candidate_claims?.length)
    .sort((a, b) => (b.confidence_score ?? 0) - (a.confidence_score ?? 0))[0];
  const identityVerdict = ["No adverse identity lead", "Name lead — review", "Candidate — review", "Strong identity match"][adverseIdentityScore];
  const nameForms = Array.from(new Set(sources.map((source) => source.identity_card?.name?.value)
    .filter((value): value is string => typeof value === "string" && Boolean(value))));
  const decisionFlags = report?.flags?.filter((flag) => flag.group !== "coverage") || [];
  const relevantSources = sources.filter((source) => source.claims.length || source.candidate_claims?.length);
  const strongSources = relevantSources.filter((source) => source.identity === "confirmed");
  const reviewSources = relevantSources.filter((source) => source.identity === "possible");

  function showSource(url: string) {
    const index = sources.findIndex((source) => source.url === url);
    if (index < 0) return false;
    if (sourcesRef.current) {
      sourcesRef.current.open = true;
      const sourceEntry = sourcesRef.current.querySelector<HTMLDetailsElement>(`[data-source-index="${index}"]`);
      if (sourceEntry) sourceEntry.open = true;
      requestAnimationFrame(() => sourceEntry?.scrollIntoView({ behavior: "smooth", block: "center" }));
    }
    return true;
  }

  async function runResearch(event: FormEvent) {
    event.preventDefault();
    if (name.trim().split(/\s+/).length < 2) {
      setError("Enter a full name to start an investigation.");
      return;
    }
    setRunning(true);
    setError("");
    try {
      const response = await fetch("/api/research", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ name, city, employer, context, aliases, birth_year: birthYear ? Number(birthYear) : null, profession }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Adverse media check failed.");
      setReport(payload as Report);
      setActiveRunId(payload.saved_run?.id ?? null);
      await refreshRuns();
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

  function startNew() {
    setReport(null);
    setActiveRunId(null);
    setName("");
    setCity("");
    setEmployer("");
    setContext("");
    setAliases("");
    setBirthYear("");
    setProfession("unknown");
    setError("");
    setSidebarOpen(false);
    setTimeout(() => inputRef.current?.focus(), 0);
  }

  return <div className="app-shell">
    <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
      <div className="sidebar-top"><Brand/><button className="icon-button sidebar-close" onClick={() => setSidebarOpen(false)} aria-label="Close menu"><PanelLeftClose size={18}/></button></div>

      <button className="new-research" onClick={startNew}><Plus size={17}/> New check</button>
      <div className="saved-runs"><div className="saved-runs-header">Saved checks · 7 days <span>{savedRuns.length}</span></div><div className="saved-runs-list">{savedRuns.map((run) => <div className="saved-run" key={run.id}><button className="saved-run-open" onClick={() => void openRun(run.id)}><strong>{run.name}</strong><small>{run.city || "Location not supplied"} · {new Date(run.created_at * 1000).toLocaleDateString("en-GB")}</small></button><button className="saved-run-delete" onClick={() => void removeRun(run.id)} aria-label={`Delete check for ${run.name}`} title="Delete saved check"><X size={14}/></button></div>)}</div>{savedRuns.length > 0 && <button className="saved-runs-clear" onClick={async () => { if (!window.confirm("Delete all saved checks?")) return; try { const response = await fetch("/api/runs", { method: "DELETE" }); if (!response.ok) throw new Error("Could not delete saved checks."); setReport(null); setActiveRunId(null); await refreshRuns(); } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not delete saved checks."); } }}>Delete all checks</button>}</div>
      <div className="sidebar-bottom"><div className="sidebar-separator"/><div className="powered-by"><span>POWERED BY</span><Image src="/ibc-group-official.png" width={108} height={49} alt="ibc group"/></div></div>
    </aside>
    {sidebarOpen && <button className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} aria-label="Close menu"/>}

    <main className="main-area">
      <header className="topbar"><button className="icon-button mobile-menu" onClick={() => setSidebarOpen(true)} aria-label="Open menu"><Menu size={19}/></button><div className="topbar-right"><form action="/api/logout" method="post"><button className="signout-button" type="submit">Sign out</button></form></div></header>
      <div className="tech-hero"><div className="content"><h1>Adverse media check</h1></div></div>

      <div className="content">
        <form className="search-panel legacy-form" onSubmit={runResearch}>
          <div className="search-panel-header"><div className="search-icon"><Search size={19}/></div><div><strong>Person Check</strong></div><span className="shortcut"><Command size={12}/> /</span></div>
          <div className="legacy-form-body"><div className="legacy-section-title">Subject Information</div>
            <div className="legacy-form-columns">
              <div>
                <label className="field field-name"><span>Full name <em>*</em></span><input ref={inputRef} value={name} onChange={(event) => setName(event.target.value)} placeholder="Daan Vermeulen" autoComplete="off" required minLength={3}/></label>
                <label className="field"><span>City / Region <small>OPTIONAL IDENTITY CLUE</small></span><input value={city} onChange={(event) => setCity(event.target.value)} placeholder="Amsterdam" autoComplete="off"/></label>
                <label className="field"><span>Research context <small>OPTIONAL</small></span><input value={context} onChange={(event) => setContext(event.target.value)} placeholder="Company or public case reference" autoComplete="off" maxLength={300}/></label>
              </div>
              <div>
                <label className="field"><span>Birth year <small>OPTIONAL</small></span><input value={birthYear} onChange={(event) => setBirthYear(event.target.value.replace(/\D/g, "").slice(0, 4))} placeholder="e.g. 1972" inputMode="numeric" autoComplete="off" pattern="(19|20)[0-9]{2}" title="A four-digit year, for example 1972"/></label>
                <label className="field"><span>Employer <small>OPTIONAL</small></span><input value={employer} onChange={(event) => setEmployer(event.target.value)} placeholder="Company name" autoComplete="off"/></label>
                <label className="field"><span>Known as <small>NICKNAMES, COMMA SEPARATED</small></span><input value={aliases} onChange={(event) => setAliases(event.target.value)} placeholder="e.g. Appie" autoComplete="off" maxLength={160}/></label>
                <label className="field"><span>Profession <small>OPTIONAL IDENTITY CLUE</small></span><select value={profession} onChange={(event) => setProfession(event.target.value as Profession)}><option value="unknown">Unknown</option><option value="healthcare">Healthcare</option><option value="lawyer">Lawyer</option><option value="other">Other</option></select></label>
              </div>
            </div>
            <button className="search-submit" type="submit" disabled={running}>{running ? <LoaderCircle size={18} className="spin"/> : <ArrowRight size={18}/>}<span>{running ? "Checking" : "Get to know your customer"}</span></button>
          </div>
        </form>
        <div className="legacy-notice"><strong>Public-source review</strong> · Results require human analyst review before any decision.</div>


        {error && <div className="error-banner" role="alert"><CircleHelp size={17}/><span>{error}</span><button onClick={() => setError("")} aria-label="Dismiss error"><X size={16}/></button></div>}

        {running && <div className="running-panel" role="status" aria-live="polite"><LoaderCircle size={21} className="spin"/><div><strong>Check in progress</strong><span>Searching sources and assessing identity. This can take a minute.</span></div></div>}

        {report ? <>
          <section className="case-heading"><div className="case-heading-left"><div className="case-avatar">{report.subject.name.split(" ").map((part) => part[0]).slice(0, 2).join("").toUpperCase()}</div><div><div className="case-title-line"><h2 ref={resultRef} tabIndex={-1}>{report.subject.name}</h2></div><div className="case-subline"><span><Globe2 size={14}/>{report.subject.city || "Location not supplied"}</span>{report.subject.employer && <><i/><span>{report.subject.employer}</span></>}</div></div></div><div className="case-actions"><button className="outline-button" onClick={downloadPdf} ><ArrowDownToLine size={16}/> Export draft</button></div></section>

          <section className="legacy-score-card" aria-label="Identity confidence for adverse media">
            <div className="legacy-score-number"><strong>{scoreOutOf100(adverseIdentityScore)}</strong><span>/ 100 identity confidence</span></div>
            <div className="legacy-score-details"><h3>{identityVerdict}</h3><p>{adverseSource?.reason || "No source-supported adverse identity lead was found in the readable sources."}</p><div className="legacy-score-track"><span style={{ width: `${scoreOutOf100(adverseIdentityScore)}%` }}/></div><small>Four evidence levels (0, 33, 67, 100). This is not a probability of fraud or a risk score.</small></div>
          </section>
          <section className="source-summary" aria-labelledby="source-summary-title">
            <div className="source-summary-heading"><div><span>RESEARCH OVERVIEW</span><h3 id="source-summary-title">Summary of the sources</h3></div><strong>{relevantSources.length} relevant · {sources.length} read</strong></div>
            <p>{strongSources.length ? `${strongSources.length} ${strongSources.length === 1 ? "source has" : "sources have"} a strong identity match with reported findings.` : "No adverse finding has a strong identity match in the readable sources."} {reviewSources.length ? `${reviewSources.length} ${reviewSources.length === 1 ? "source mentions" : "sources mention"} possible adverse information that needs an analyst to confirm the person.` : "No unresolved adverse identity lead was extracted."}</p>
            {relevantSources.length ? <div className="source-summary-list">{relevantSources.slice(0, 5).map((source) => {
              const items = source.identity === "confirmed" ? source.claims : source.candidate_claims || [];
              return <div className="source-summary-item" key={source.url}>
                <span className={source.identity === "confirmed" ? "summary-status strong" : "summary-status review"}>{source.identity === "confirmed" ? "Linked" : "Verify identity"}</span>
                <div><strong>{source.title || "Untitled source"}</strong><p>{items.slice(0, 2).map((item) => item.summary).join(" · ") || "No adverse claim could be extracted from this source."}</p><button type="button" onClick={() => showSource(source.url)}>View evidence <ArrowRight size={13}/></button></div>
              </div>;
            })}{relevantSources.length > 5 && <span className="source-summary-more">{relevantSources.length - 5} more source mentions in Media Mentions below.</span>}</div> : <p className="source-summary-empty">No source-supported adverse mentions were extracted from the readable pages. Search coverage may be incomplete.</p>}
            <small>Summaries describe what sources report. They do not establish guilt or replace analyst review.</small>
          </section>
          {nameForms.length > 0 && <section className="legacy-variations"><h3>Name forms found in sources</h3>{nameForms.map((form) => <span key={form}>{form}</span>)}</section>}
          <section className="legacy-risk-card" aria-labelledby="flags-heading"><h3 id="flags-heading">Risk Flags</h3>
            {decisionFlags.length ? <div className="legacy-flag-list">{decisionFlags.map((flag, index) => <div key={`${flag.code}-${index}`} className={`legacy-flag ${flag.group}`}><strong>{flag.group === "act" ? "Reported finding" : "Needs review"} · {flag.label}</strong><p>{flag.reason}</p>{flag.source_urls[0] && (sources.some((source) => source.url === flag.source_urls[0]) ? <button type="button" onClick={() => showSource(flag.source_urls[0])}>View evidence <ArrowRight size={13}/></button> : <a href={flag.source_urls[0]} target="_blank" rel="noopener noreferrer">Open register <ArrowUpRight size={13}/></a>)}</div>)}</div> : <p className="legacy-empty">No risk flags in the sources searched. This is not a clearance.</p>}
            <p className="legacy-review-note">{report.confirmed_findings.length} linked findings · {report.candidate_findings?.length ?? 0} possible adverse leads for reviewer verification.</p>
          </section>

          <ReportSections report={report} onSource={showSource} sourcesRef={sourcesRef}/>



          {report.metrics && <details className="run-metrics"><summary>Run details</summary><div className="run-metrics-values"><span><strong>{report.metrics.total_seconds.toFixed(1)}s</strong> total</span><span>Search {report.metrics.search_seconds.toFixed(1)}s</span><span>Read {report.metrics.fetch_seconds.toFixed(1)}s</span><span>Assess {report.metrics.assess_seconds.toFixed(1)}s</span><span>{report.metrics.search_queries} searches · {report.metrics.model_calls} model calls</span><span>{report.metrics.estimated_usd === null ? "Cost unavailable" : `Est. provider cost $${report.metrics.estimated_usd.toFixed(3)}`}</span></div></details>}


        </> : null}
        <footer className="page-footer"><span>© 2026 KYCX · ibc group</span></footer>
      </div>
    </main>
  </div>;
}
