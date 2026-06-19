"use client";

import { useMemo, useState } from "react";
import JobCard, { type Job } from "./JobCard";

const PAGE = 15;

// Search + paginated list so a long tab stays manageable. Filtering is
// client-side over the already-loaded jobs (title / company / location).
export default function JobList({ jobs, emptyText }: { jobs: Job[]; emptyText: string }) {
  const [q, setQ] = useState("");
  const [shown, setShown] = useState(PAGE);

  const filtered = useMemo(() => {
    const t = q.trim().toLowerCase();
    if (!t) return jobs;
    return jobs.filter((j) =>
      `${j.title} ${j.company} ${j.location ?? ""}`.toLowerCase().includes(t),
    );
  }, [jobs, q]);

  if (jobs.length === 0) return <p className="hint">{emptyText}</p>;

  return (
    <>
      <input
        className="search" type="text" placeholder="Search title, company, or location…"
        value={q} onChange={(e) => { setQ(e.target.value); setShown(PAGE); }}
      />
      {filtered.length === 0 ? (
        <p className="hint">No matches for “{q}”.</p>
      ) : (
        <ul className="jobs">{filtered.slice(0, shown).map((j) => <JobCard key={j.canonical_key} job={j} />)}</ul>
      )}
      {filtered.length > shown && (
        <button className="mini" style={{ marginTop: 12 }} onClick={() => setShown((s) => s + PAGE)}>
          Show more ({filtered.length - shown})
        </button>
      )}
    </>
  );
}
