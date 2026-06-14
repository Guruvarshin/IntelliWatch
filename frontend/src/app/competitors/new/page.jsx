"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const initialState = {
  name: "",
  since_days: 7,
  github_repo: "",
  hn_query: "",
  youtube_channel_id: "",
  jobs_board_type: "",
  jobs_board_token: "",
  pricing_url: "",
  news_query: "",
  blog_rss_url: "",
};

function toBody(form) {
  const body = { name: form.name, since_days: Number(form.since_days) || 7 };
  for (const key of Object.keys(initialState)) {
    if (key === "name" || key === "since_days") continue;
    body[key] = form[key].trim() === "" ? null : form[key].trim();
  }
  return body;
}

function Field({ label, hint, ...props }) {
  return (
    <div>
      <label className="block text-sm text-slate-400">{label}</label>
      {hint && <p className="text-xs text-slate-500">{hint}</p>}
      <input
        {...props}
        className="mt-1 w-full rounded-md bg-slate-800 px-3 py-2 text-slate-100 outline-none ring-1 ring-slate-700 focus:ring-indigo-500"
      />
    </div>
  );
}

export default function NewCompetitorPage() {
  const router = useRouter();
  const [form, setForm] = useState(initialState);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const res = await fetch("/api/competitors", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(toBody(form)),
    });

    if (!res.ok) {
      const data = await res.json();
      setError(data.error ?? "Something went wrong.");
      setLoading(false);
      return;
    }

    router.push("/");
  };

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-10 text-slate-100">
      <form
        onSubmit={handleSubmit}
        className="mx-auto max-w-lg space-y-4 rounded-xl bg-slate-900 p-8 shadow-xl"
      >
        <h1 className="text-xl font-semibold">Add a competitor</h1>

        {error && (
          <p className="rounded bg-red-950 px-3 py-2 text-sm text-red-400">
            {error}
          </p>
        )}

        <Field
          label="Name"
          required
          value={form.name}
          onChange={set("name")}
        />

        <Field
          label="Track signals from the last N days"
          type="number"
          min="1"
          value={form.since_days}
          onChange={set("since_days")}
        />

        <p className="pt-2 text-xs uppercase tracking-wide text-slate-500">
          Sources (all optional)
        </p>

        <Field
          label="GitHub repo"
          hint="owner/repo, e.g. vercel/next.js"
          value={form.github_repo}
          onChange={set("github_repo")}
        />
        <Field
          label="Hacker News search query"
          value={form.hn_query}
          onChange={set("hn_query")}
        />
        <Field
          label="YouTube channel ID"
          value={form.youtube_channel_id}
          onChange={set("youtube_channel_id")}
        />
        <Field
          label="Jobs board type"
          hint='"greenhouse" or "lever"'
          value={form.jobs_board_type}
          onChange={set("jobs_board_type")}
        />
        <Field
          label="Jobs board token"
          hint="company token used in the board's public API"
          value={form.jobs_board_token}
          onChange={set("jobs_board_token")}
        />
        <Field
          label="Pricing page URL"
          type="url"
          value={form.pricing_url}
          onChange={set("pricing_url")}
        />
        <Field
          label="News search query"
          value={form.news_query}
          onChange={set("news_query")}
        />
        <Field
          label="Blog RSS URL"
          type="url"
          value={form.blog_rss_url}
          onChange={set("blog_rss_url")}
        />

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-indigo-600 py-2 font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {loading ? "Adding..." : "Add competitor"}
          </button>
          <a
            href="/"
            className="flex w-full items-center justify-center rounded-md bg-slate-800 py-2 font-medium text-slate-200 hover:bg-slate-700"
          >
            Cancel
          </a>
        </div>
      </form>
    </main>
  );
}
