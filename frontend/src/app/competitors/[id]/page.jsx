import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { apiFetch } from "@/lib/api";
import RunButton from "./RunButton";

const SOURCE_LABELS = {
  github_repo: "GitHub repo",
  hn_query: "Hacker News query",
  youtube_channel_id: "YouTube channel",
  jobs_board_type: "Jobs board type",
  jobs_board_token: "Jobs board token",
  pricing_url: "Pricing page",
  news_query: "News query",
  blog_rss_url: "Blog RSS",
};

export default async function CompetitorDetailPage({ params }) {
  const [competitor, briefs] = await Promise.all([
    apiFetch(`/competitors/${params.id}`),
    apiFetch(`/competitors/${params.id}/briefs`),
  ]);

  const configuredSources = Object.entries(SOURCE_LABELS).filter(
    ([key]) => competitor[key]
  );

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-10 text-slate-100">
      <div className="mx-auto max-w-2xl">
        <Link href="/" className="text-sm text-indigo-400 hover:underline">
          &larr; Back to dashboard
        </Link>

        <div className="mt-2 flex items-center justify-between">
          <h1 className="text-2xl font-semibold">{competitor.name}</h1>
          <RunButton competitorId={competitor._id} />
        </div>
        <p className="text-sm text-slate-400">
          Tracking signals from the last {competitor.since_days} days
        </p>

        {configuredSources.length > 0 && (
          <div className="mt-4 rounded-lg bg-slate-900 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">
              Sources
            </p>
            <ul className="mt-2 space-y-1 text-sm">
              {configuredSources.map(([key, label]) => (
                <li key={key} className="text-slate-300">
                  <span className="text-slate-500">{label}:</span>{" "}
                  {competitor[key]}
                </li>
              ))}
            </ul>
          </div>
        )}

        <h2 className="mt-8 text-lg font-medium">Briefs</h2>
        {briefs.length === 0 ? (
          <p className="mt-2 text-sm text-slate-400">
            No briefs yet. Click &quot;Run now&quot; to generate the first one.
          </p>
        ) : (
          <ul className="mt-4 space-y-4">
            {briefs.map((brief) => (
              <li key={brief._id} className="rounded-lg bg-slate-900 p-4">
                <p className="text-xs text-slate-500">
                  {new Date(brief.created_at).toLocaleString()}
                </p>
                <div className="prose prose-invert prose-sm mt-2 max-w-none">
                  <ReactMarkdown>{brief.content}</ReactMarkdown>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
