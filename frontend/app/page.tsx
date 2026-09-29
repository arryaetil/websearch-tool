"use client";

import { CSSProperties, FormEvent, useEffect, useRef, useState } from "react";
import Image from "next/image";
import {
  Archive, ArrowDownToLine, ArrowRight, ArrowUpRight, Check,
  CircleCheck, CircleDashed, CircleHelp, CircleMinus, CircleX, Command, FileSearch, FileText, Fingerprint,
  Globe2, Layers3, Link2, LoaderCircle, Menu, OctagonAlert, PanelLeftClose, Plus,
  Search, SearchX, UserSearch, X, AtSign, BrainCircuit, BriefcaseBusiness, Building2, Gauge, Gavel,
  History, Landmark, ListChecks, Newspaper, Radar, Route, Scale, ScrollText, ShieldAlert, Telescope,
  ThumbsDown, ThumbsUp,
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
  retrieved_at: string;
  sha256: string;
};
type FlagGroup = "act" | "review" | "coverage";
type Flag = { code: string; group: FlagGroup; label: string; reason: string; source_urls: string[] };
type CoverageStatus = "searched" | "not_applicable" | "failed" | "stale" | "manual";
type CoverageEntry = { key: string; label: string; status: CoverageStatus; detail: string; url?: string };
type Profession = "unknown" | "healthcare" | "lawyer" | "other";
type ReviewItem = { text: string; refs: string[]; direction?: "supports" | "contradicts" };
type ReviewRecord = Record<string, string | string[]> & { refs: string[] };
type Review = {
  score: number | null; ceiling?: number; label: string; status?: string;
  summary: ReviewItem[]; reasons: ReviewItem[]; refs?: Record<string, string>;
  sections?: Record<string, ReviewRecord[]>; name_variations_searched?: string[];
  deeper_search?: { needed: boolean; queries: string[] };
};

type Report = {
  saved_run?: { id: string; created_at: number; expires_at: number };
  subject: { name: string; city: string; employer: string; aliases?: string[]; birth_year?: number | ""; profession?: Profession | "" };
  sources: Source[];
  confirmed_findings: { summary: string; quote: string; url: string }[];
  risk_flags?: string[];
  flags?: Flag[];
  coverage?: CoverageEntry[];
  next_identifiers?: string[];
  review?: Review | null;
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

// Evidence tiers, not probabilities: the meter never shows a percentage.
const tierWord = ["No match", "Name only", "Candidate", "Strong match"];

function TierMeter({ score }: { score: number }) {
  return <span className={`tier-meter tier-${score}`} role="img" aria-label={`Evidence level ${score} of 3`}>
    {[1, 2, 3].map((step) => <i key={step} className={step <= score ? "on" : ""}/>)}
  </span>;
}

const flagGroupWord: Record<FlagGroup, string> = { act: "Act", review: "Review", coverage: "Coverage" };
const FlagIcon = ({ group }: { group: FlagGroup }) =>
  group === "act" ? <OctagonAlert size={17}/> : group === "review" ? <UserSearch size={17}/> : <SearchX size={17}/>;

const cardRows: [CardKey, string][] = [["name", "Name"], ["city", "City"], ["employer", "Employer"], ["age", "Age"]];
// Report sections of the original researcher, each with its own icon.
const reviewSections: [string, string, typeof Fingerprint, string[]][] = [
  ["identity_matches", "Identity matches", Fingerprint, ["name", "description", "confidence"]],
  ["media_mentions", "Media mentions", Newspaper, ["title", "source", "date", "summary"]],
  ["legal_public_records", "Legal and public records", Gavel, ["issue_type", "source", "date", "summary"]],
  ["business_records", "Business records", Building2, ["entity", "role", "status", "source"]],
  ["professional_profiles", "Professional profiles", BriefcaseBusiness, ["platform", "role", "company"]],
  ["social_media_presence", "Social media presence", AtSign, ["platform", "description"]],
];

const coverageIcon: Record<string, typeof Fingerprint> = {
  web: Globe2, sanctions: Scale, follow_up: Route, deep_search: Telescope,
  "manual-0": Gavel, "manual-1": Building2, "manual-2": Landmark,
};

function SectionIcon({ icon: Icon, tone = "blue" }: { icon: typeof Fingerprint; tone?: "blue" | "violet" | "amber" | "mint" }) {
  return <span className={`section-icon tone-${tone}`} aria-hidden="true"><Icon size={16} strokeWidth={1.8}/></span>;
}


function CardIcon({ status }: { status: CardStatus }) {
  if (status === "conflict") return <CircleX size={15} aria-label="Contradicts"/>;
  if (status === "absent") return <CircleMinus size={15} aria-label="Not stated"/>;
  if (status === "partial") return <CircleDashed size={15} aria-label="Partial match"/>;
  return <CircleCheck size={15} aria-label="Matches"/>;
}

function describeField(field: CardField, supplied: boolean) {
  const shown = field.quote ? `“${field.quote}”` : field.value ? String(field.value) : "";
  if (field.status === "absent") return field.note || (supplied ? "Not stated in this source" : "Not supplied for this check");
  if (field.status === "partial") return `${shown} · partial name`;
  if (field.note) return shown ? `${shown} · ${field.note}` : field.note;
  return shown || "Stated in this source";
}

function sourceCountLabel(source: Source) {
  if (source.identity === "possible" && source.candidate_claims?.length) {
    const count = source.candidate_claims.length;
    return `${count} ${count === 1 ? "item" : "items"} to review`;
  }
  return `${source.claims.length} ${source.claims.length === 1 ? "finding" : "findings"}`;
}

function CandidateClaims({ source }: { source: Source }) {
  const claims = source.identity === "possible" ? source.candidate_claims || [] : [];
  if (!claims.length) return null;
  return <section className="candidate-claims" aria-label="Items needing identity review">
    <h4><SectionIcon icon={ListChecks} tone="amber"/>Items to review</h4>
    <p>These quotes may concern the person. Confirm the identity before using them as findings.</p>
    <div className="claims-list">{claims.map((claim, index) => <div className="claim-card" key={index}>
      <div className="claim-number">{String(index + 1).padStart(2, "0")}</div>
      <div><strong>{claim.summary}</strong><div className="quote"><span>“</span>{claim.quote}<span>”</span></div></div>
    </div>)}</div>
  </section>;
}

const coverageWord: Record<CoverageStatus, string> = {
  searched: "Searched", not_applicable: "Not applicable", failed: "Not searched", stale: "Outdated list", manual: "Manual check",
};

export default function Home() {
  const [name, setName] = useState("");
  const [city, setCity] = useState("");
  const [employer, setEmployer] = useState("");
  const [aliases, setAliases] = useState("");
  const [birthYear, setBirthYear] = useState("");
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
      setAliases((payload.subject.aliases || []).join(", "));
      setBirthYear(payload.subject.birth_year ? String(payload.subject.birth_year) : "");
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
  const supplied: Record<CardKey, boolean> = {
    name: true, city: true, employer: Boolean(report?.subject.employer),
    age: Boolean(report?.subject.birth_year), profession: Boolean(report?.subject.profession && report.subject.profession !== "unknown"),
  };

  function showSource(url: string) {
    const index = sources.findIndex((source) => source.url === url);
    if (index < 0) return false;
    setFilter("all");
    setSelected(index);
    document.getElementById("sources-heading")?.scrollIntoView({ behavior: "smooth", block: "start" });
    return true;
  }

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
        body: JSON.stringify({ name, city, employer, aliases, birth_year: birthYear ? Number(birthYear) : null }),
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
    setAliases("");
    setBirthYear("");
    setError("");
    setSidebarOpen(false);
    setTimeout(() => inputRef.current?.focus(), 0);
  }

  return <div className="app-shell">
    <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
      <div className="sidebar-top"><Brand/><button className="icon-button sidebar-close" onClick={() => setSidebarOpen(false)} aria-label="Close menu"><PanelLeftClose size={18}/></button></div>

      <button className="new-research" onClick={startNew}><Plus size={17}/> New check</button>
      <div className="saved-runs"><div className="saved-runs-header"><History size={13} aria-hidden="true"/> Saved checks · 7 days <span>{savedRuns.length}</span></div><div className="saved-runs-list">{savedRuns.map((run) => <div className="saved-run" key={run.id}><button className="saved-run-open" onClick={() => void openRun(run.id)}><strong>{run.name}</strong><small>{run.city} · {new Date(run.created_at * 1000).toLocaleDateString("en-GB")}</small></button><button className="saved-run-delete" onClick={() => void removeRun(run.id)} aria-label={`Delete check for ${run.name}`} title="Delete saved check"><X size={14}/></button></div>)}</div>{savedRuns.length > 0 && <button className="saved-runs-clear" onClick={async () => { if (!window.confirm("Delete all saved checks?")) return; try { const response = await fetch("/api/runs", { method: "DELETE" }); if (!response.ok) throw new Error("Could not delete saved checks."); setReport(null); setActiveRunId(null); await refreshRuns(); } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not delete saved checks."); } }}>Delete all checks</button>}</div>
      <div className="sidebar-bottom"><div className="sidebar-separator"/><div className="powered-by"><span>POWERED BY</span><Image src="/ibc-group-official.png" width={108} height={49} alt="ibc group"/></div></div>
    </aside>
    {sidebarOpen && <button className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} aria-label="Close menu"/>}

    <main className="main-area">
      <header className="topbar"><button className="icon-button mobile-menu" onClick={() => setSidebarOpen(true)} aria-label="Open menu"><Menu size={19}/></button><div className="topbar-right"><form action="/api/logout" method="post"><button className="signout-button" type="submit">Sign out</button></form></div></header>
      <div className="tech-hero"><div className="content"><h1>Adverse media check</h1></div></div>

      <div className="content">
        <form className="search-panel" onSubmit={runResearch}><div className="search-panel-header"><div className="search-icon"><Search size={19}/></div><div><strong>Check a person</strong></div><span className="shortcut"><Command size={12}/> /</span></div><div className="search-fields"><label className="field field-name"><span>FULL NAME <em>*</em></span><input ref={inputRef} value={name} onChange={(event) => setName(event.target.value)} placeholder="e.g. Jordan Example" autoComplete="off" required minLength={3}/></label><label className="field"><span>CITY OR REGION <em>*</em></span><input value={city} onChange={(event) => setCity(event.target.value)} placeholder="e.g. Utrecht" autoComplete="off" required minLength={2}/></label><label className="field"><span>EMPLOYER <small>FOR A STRONG MATCH</small></span><input value={employer} onChange={(event) => setEmployer(event.target.value)} placeholder="e.g. Example Studio" autoComplete="off"/></label><label className="field"><span>KNOWN AS <small>NICKNAMES, COMMA SEPARATED</small></span><input value={aliases} onChange={(event) => setAliases(event.target.value)} placeholder="e.g. Appie" autoComplete="off" maxLength={160}/></label><label className="field"><span>BIRTH YEAR <small>YEAR ONLY</small></span><input value={birthYear} onChange={(event) => setBirthYear(event.target.value.replace(/\D/g, "").slice(0, 4))} placeholder="e.g. 1972" inputMode="numeric" autoComplete="off" pattern="(19|20)[0-9]{2}" title="A four-digit year, for example 1972"/></label><button className="search-submit" type="submit" disabled={running}>{running ? <LoaderCircle size={18} className="spin"/> : <ArrowRight size={18}/>}<span>{running ? "Checking" : "Run check"}</span></button></div></form>


        {error && <div className="error-banner" role="alert"><CircleHelp size={17}/><span>{error}</span><button onClick={() => setError("")} aria-label="Dismiss error"><X size={16}/></button></div>}

        {running && <div className="running-panel" role="status" aria-live="polite"><LoaderCircle size={21} className="spin"/><div><strong>Check in progress</strong><span>Searching sources and assessing identity. This can take a minute.</span></div></div>}

        {report ? <>
          <section className="case-heading"><div className="case-heading-left"><div className="case-avatar">{report.subject.name.split(" ").map((part) => part[0]).slice(0, 2).join("").toUpperCase()}</div><div><div className="case-title-line"><h2 ref={resultRef} tabIndex={-1}>{report.subject.name}</h2></div><div className="case-subline"><span><Globe2 size={14}/>{report.subject.city}</span>{report.subject.employer && <><i/><span>{report.subject.employer}</span></>}</div></div></div><div className="case-actions"><button className="outline-button" onClick={downloadPdf} ><ArrowDownToLine size={16}/> Export draft</button></div></section>

          {report.review && <section className="review-panel" aria-labelledby="review-heading"><div className="review-head"><SectionIcon icon={BrainCircuit} tone="violet"/><div className="review-title"><h3 id="review-heading">Review agent</h3><small>How well the sources match the details supplied. Advisory: it does not change confirmed findings.</small></div><div className="review-score"><strong>{report.review.score ?? "—"}</strong><span className={`verdict verdict-${report.review.label.toLowerCase().replace(/\s+/g, "-")}`}>{report.review.label}</span></div></div>{report.review.score !== null && <div className="score-bar" role="img" aria-label={`Review score ${report.review.score} of 100`}><i style={{ "--score": report.review.score / 100 } as CSSProperties}/></div>}<ul className="review-summary">{report.review.summary.map((item, index) => <li key={index}>{item.text}{item.refs.map((ref) => { const url = report.review?.refs?.[ref]; return url ? <button key={ref} type="button" className="ref-chip" onClick={() => { if (!showSource(url)) window.open(url, "_blank", "noopener"); }} aria-label={`Show source ${ref}`}>{ref}</button> : null; })}</li>)}</ul>{report.review.reasons.length > 0 && <ul className="review-reasons">{report.review.reasons.map((item, index) => <li key={index} className={item.direction}>{item.direction === "contradicts" ? <ThumbsDown size={14} aria-label="Contradicts"/> : <ThumbsUp size={14} aria-label="Supports"/>}<span>{item.text}</span>{item.refs.map((ref) => { const url = report.review?.refs?.[ref]; return url ? <button key={ref} type="button" className="ref-chip" onClick={() => { if (!showSource(url)) window.open(url, "_blank", "noopener"); }}>{ref}</button> : null; })}</li>)}</ul>}{report.review.sections && <div className="review-sections">{reviewSections.map(([key, title, icon, fields]) => { const records = report.review?.sections?.[key] || []; return <section key={key} className={`review-section ${records.length ? "" : "empty"}`}><h4><SectionIcon icon={icon} tone={key === "legal_public_records" ? "amber" : "blue"}/>{title}<span>{records.length}</span></h4>{records.length ? <ul>{records.map((record, index) => <li key={index}><strong>{String(record[fields[0]] || "")}</strong><span>{fields.slice(1).map((field) => record[field]).filter(Boolean).join(" · ")}</span>{record.refs.map((ref) => { const url = report.review?.refs?.[ref]; return url ? <button key={ref} type="button" className="ref-chip" onClick={() => { if (!showSource(url)) window.open(url, "_blank", "noopener"); }}>{ref}</button> : null; })}</li>)}</ul> : <p>Nothing in the sources found.</p>}</section>; })}</div>}{report.review.name_variations_searched && report.review.name_variations_searched.length > 0 && <details className="review-queries"><summary><Search size={13} aria-hidden="true"/> Searches run ({report.review.name_variations_searched.length})</summary><ul>{report.review.name_variations_searched.map((query) => <li key={query}><code>{query}</code></li>)}</ul></details>}</section>}

          <section className="result-summary" aria-label="Check summary"><div><strong>{report.confirmed_findings.length}</strong><span>linked adverse {report.confirmed_findings.length === 1 ? "finding" : "findings"}</span></div><div>{highestConfidence === null ? <strong>—</strong> : <><strong>{tierWord[highestConfidence]}</strong><TierMeter score={highestConfidence}/></>}<span>highest identity match</span></div><div><strong>{counts.possible}</strong><span>{counts.possible === 1 ? "source needs" : "sources need"} identity review</span></div></section>

          {report.flags ? <section className="flag-panel" aria-labelledby="flags-heading"><div className="flag-panel-head"><h3 id="flags-heading"><SectionIcon icon={ShieldAlert} tone="amber"/>Risk flags</h3><small>Identity level measures matching evidence, not the likelihood of misconduct.</small></div>{report.flags.length ? <ul className="flag-list">{report.flags.map((flag, index) => { const target = flag.source_urls[0]; const internal = target && sources.some((source) => source.url === target); return <li key={`${flag.code}-${index}`} className={`flag-row ${flag.group}`}><span className="flag-icon" aria-hidden="true"><FlagIcon group={flag.group}/></span><div className="flag-text"><strong>{flag.label}</strong><span>{flag.reason}</span></div><div className="flag-actions">{target && (internal ? <button type="button" className="flag-link" onClick={() => showSource(target)}>View source</button> : <a className="flag-link" href={target} target="_blank" rel="noopener noreferrer">Open <ArrowUpRight size={13}/></a>)}<span className={`flag-tag ${flag.group}`}>{flagGroupWord[flag.group]}</span></div></li>; })}</ul> : <p className="flag-empty">No flags in the sources searched. This is not a clearance.</p>}{report.next_identifiers && report.next_identifiers.length > 0 && <ul className="next-identifiers">{report.next_identifiers.map((hint) => <li key={hint}>{hint}</li>)}</ul>}</section>
          : <div className="risk-summary"><strong>Risk flags</strong>{report.risk_flags === undefined ? <span>Unavailable for this saved check</span> : report.risk_flags.length ? <ul>{report.risk_flags.map((flag) => <li key={flag}>{flag}</li>)}</ul> : <span>No flags from the sources reviewed</span>}<small>Identity confidence measures matching evidence, not the likelihood of misconduct.</small></div>}

          {report.coverage && <section className="coverage-panel" aria-labelledby="coverage-heading"><h3 id="coverage-heading"><SectionIcon icon={Radar}/>Sources searched</h3><ul>{report.coverage.map((entry) => <li key={entry.key} className={`coverage-item ${entry.status}`}><div className="coverage-top"><strong>{(() => { const Icon = coverageIcon[entry.key] || Globe2; return <Icon size={14} aria-hidden="true"/>; })()}{entry.label}</strong><span className="coverage-status">{coverageWord[entry.status]}</span></div><small>{entry.detail}</small>{entry.url && <a href={entry.url} target="_blank" rel="noopener noreferrer">Search manually <ArrowUpRight size={12}/></a>}</li>)}</ul></section>}

          {report.errors.length > 0 && <details className="coverage-details"><summary>{report.errors.length} {report.errors.length === 1 ? "source" : "sources"} could not be read</summary><ul>{report.errors.map((item, index) => <li key={index}>{item}</li>)}</ul></details>}

          <section className="results-section"><div className="section-heading"><div><h2 id="sources-heading"><SectionIcon icon={Layers3} tone="violet"/>Source analysis <span className="section-count">{sources.length}</span></h2></div></div>
            <div className="results-workspace"><div className="source-pane"><div className="source-pane-header"><span><Layers3 size={15}/> Sources</span></div><div className="filter-row">{(["all", "confirmed", "possible", "unrelated"] as const).map((value) => <button key={value} type="button" aria-pressed={filter === value} className={filter === value ? "filter active" : "filter"} onClick={() => changeFilter(value)}>{value === "all" ? `All ${sources.length}` : value === "confirmed" ? `Matched ${counts.confirmed}` : value === "possible" ? `Review ${counts.possible}` : `Other ${counts.unrelated}`}</button>)}</div><div className="source-list">{filtered.length ? filtered.map((source) => { const index = sources.indexOf(source); return <button key={`${source.url}-${index}`} type="button" aria-pressed={selected === index} className={`source-item ${selected === index ? "selected" : ""}`} onClick={() => setSelected(index)}><div className="source-item-top"><span className={`source-mini-icon ${source.identity}`}><FileText size={15}/></span><span className="source-domain">{(() => { try { return new URL(source.url).hostname.replace(/^www\./, ""); } catch { return "SOURCE"; } })()}</span></div><strong>{source.title || "Untitled source"}</strong><div className="source-item-bottom"><StatusPill identity={source.identity}/><span>{sourceCountLabel(source)}</span></div></button>; }) : <div className="source-empty">No sources in this category.</div>}</div></div>

              <div className="detail-pane" key={selected}>{current ? <><div className="detail-topline"><span>SOURCE {String(selected + 1).padStart(2, "0")} <span>/</span> {String(sources.length).padStart(2, "0")}</span><span className="detail-updated">Retrieved {new Date(current.retrieved_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}</span></div><div className="detail-title-row">
  <div className="detail-title-content">
    <div className="detail-domain"><Globe2 size={14}/>{(() => { try { return new URL(current.url).hostname; } catch { return "Source"; } })()}</div>
    <h3><a className="source-title-link" href={current.url} target="_blank" rel="noopener noreferrer">{current.title || "Untitled source"}<ArrowUpRight size={17}/></a></h3>
  </div>
  <a className="open-source-button" href={current.url} target="_blank" rel="noopener noreferrer">Open source <ArrowUpRight size={15}/></a>
</div><div className="identity-assessment"><div className="assessment-header"><div><SectionIcon icon={Fingerprint}/><span>IDENTITY ASSESSMENT</span></div><StatusPill identity={current.identity}/></div><p>{current.reason || "No explanation returned."}</p>{current.identity_card && <dl className="identity-card">{cardRows.map(([key, rowLabel]) => { const field = current.identity_card![key]; return <div key={key} className={`identity-row ${field.status}`}><dt><CardIcon status={field.status}/>{rowLabel}</dt><dd>{describeField(field, supplied[key])}</dd></div>; })}</dl>}<div className="assessment-foot">{current.confidence_score === undefined ? <><span className={`assessment-indicator ${current.identity}`}/>Identity confidence unavailable for this saved check</> : <><TierMeter score={current.confidence_score}/><span className="tier-label">{tierWord[current.confidence_score]} · {current.confidence_score} of 3</span><span className="tier-note">Evidence level, not a probability</span></>}</div></div><CandidateClaims source={current}/><div className="findings-head"><div><SectionIcon icon={ScrollText} tone="violet"/><h4>Source findings</h4><span>{current.claims.length}</span></div><small>Only verbatim supported claims are shown</small></div>{current.claims.length ? <div className="claims-list">{current.claims.map((claim, index) => <div className="claim-card" key={index}><div className="claim-number">{String(index + 1).padStart(2, "0")}</div><div><strong>{claim.summary}</strong><div className="quote"><span>“</span>{claim.quote}<span>”</span></div><div className="claim-verified"><Check size={13}/> Quote found on source page</div></div></div>)}</div> : <div className="no-findings"><FileSearch size={25}/><strong>No findings linked</strong><span>{current.identity === "possible" ? "This source needs an analyst’s identity check before any claims can be used." : current.identity === "unrelated" ? "This source appears to describe someone else." : "No supported claims were extracted from this source."}</span></div>}<div className="source-meta"><div className="source-url"><Link2 size={13}/><a href={current.url} target="_blank" rel="noopener noreferrer">{current.url}</a></div><span className="source-meta-right">{current.archive && <a className="archive-link" href={current.archive.url} target="_blank" rel="noopener noreferrer"><Archive size={13}/> Archived copy</a>}<span>SHA-256: {current.sha256.slice(0, 12)}…</span></span></div></> : <div className="detail-empty"><FileSearch size={30}/><h3>{filtered.length === 0 && sources.length > 0 ? "No sources in this category" : "No readable sources found"}</h3><p>{filtered.length === 0 && sources.length > 0 ? "Choose another filter to view a source." : "Try adding another identity clue and run the check again."}</p></div>}</div></div></section>

          {report.metrics && <details className="run-metrics"><summary><Gauge size={14} aria-hidden="true"/> Run details</summary><div className="run-metrics-values"><span><strong>{report.metrics.total_seconds.toFixed(1)}s</strong> total</span><span>Search {report.metrics.search_seconds.toFixed(1)}s</span><span>Read {report.metrics.fetch_seconds.toFixed(1)}s</span><span>Assess {report.metrics.assess_seconds.toFixed(1)}s</span><span>{report.metrics.search_queries} searches · {report.metrics.model_calls} model calls</span><span>{report.metrics.estimated_usd === null ? "Cost unavailable" : `Est. provider cost $${report.metrics.estimated_usd.toFixed(3)}`}</span></div></details>}


        </> : null}
        <footer className="page-footer"><span>© 2026 KYCX · ibc group</span></footer>
      </div>
    </main>
  </div>;
}
