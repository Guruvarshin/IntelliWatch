import Link from "next/link";
import { auth, signOut } from "@/auth";
import { apiFetch } from "@/lib/api";

export default async function Dashboard() {
  const session = await auth();
  const competitors = await apiFetch("/competitors");

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-10 text-slate-100">
      <div className="mx-auto max-w-2xl">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold">IntelliWatch</h1>
            <p className="text-sm text-slate-400">{session?.user?.email}</p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/settings"
              className="rounded-md bg-slate-800 px-4 py-2 text-sm hover:bg-slate-700"
            >
              Settings
            </Link>
            <form
              action={async () => {
                "use server";
                await signOut({ redirectTo: "/login" });
              }}
            >
              <button className="rounded-md bg-slate-800 px-4 py-2 text-sm hover:bg-slate-700">
                Log out
              </button>
            </form>
          </div>
        </div>

        <div className="mt-8 flex items-center justify-between">
          <h2 className="text-lg font-medium">Your competitors</h2>
          <Link
            href="/competitors/new"
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500"
          >
            + Add competitor
          </Link>
        </div>

        {competitors.length === 0 ? (
          <p className="mt-6 text-sm text-slate-400">
            No competitors yet. Add one to start tracking.
          </p>
        ) : (
          <ul className="mt-6 space-y-3">
            {competitors.map((c) => (
              <li key={c._id}>
                <Link
                  href={`/competitors/${c._id}`}
                  className="block rounded-lg bg-slate-900 px-4 py-3 hover:bg-slate-800"
                >
                  <p className="font-medium">{c.name}</p>
                  <p className="text-xs text-slate-400">
                    Tracking since the last {c.since_days} days
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
