type Job = {
  title: string;
  company: string;
  location: string | null;
  apply_url: string;
  apply_url_type: string;
  source: string;
  sent_at: string;
};

const APPLY_LABEL: Record<string, string> = {
  direct_apply: "Apply",
  job_detail: "View posting",
  company_careers: "Careers",
  source_search: "Search",
};

async function getJobs(userId: string): Promise<Job[]> {
  try {
    const res = await fetch(`${process.env.WORKER_URL}/users/${userId}/jobs`, { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    return data.jobs ?? [];
  } catch {
    return [];
  }
}

export default async function Dashboard({ params }: { params: Promise<{ userId: string }> }) {
  const { userId } = await params;
  const jobs = await getJobs(userId);

  return (
    <main className="wrap">
      <h1>Your matched jobs</h1>
      <p className="sub">Jobs we've sent you, newest first. New matches arrive each day on Telegram.</p>

      <div className="card">
        {jobs.length === 0 ? (
          <p className="hint">
            No jobs yet. Once you connect Telegram and the next daily run completes, your matches
            show up here.
          </p>
        ) : (
          <ul className="jobs">
            {jobs.map((j, i) => (
              <li key={i} className="job">
                <div className="job-main">
                  <div className="job-title">{j.title}</div>
                  <div className="job-meta">
                    {j.company}{j.location ? ` · ${j.location}` : ""} · <span className="src">{j.source}</span>
                  </div>
                </div>
                <a className="apply" href={j.apply_url} target="_blank" rel="noreferrer">
                  {APPLY_LABEL[j.apply_url_type] ?? "Open"}
                </a>
              </li>
            ))}
          </ul>
        )}
        <div className="links">
          <a href="/">Back to start</a>
          <a href={`/manage/${userId}`}>Manage / delete my data</a>
        </div>
      </div>
    </main>
  );
}
