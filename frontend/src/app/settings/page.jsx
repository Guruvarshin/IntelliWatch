import Link from "next/link";
import { apiFetch } from "@/lib/api";
import ApiKeysForm from "./ApiKeysForm";

export default async function SettingsPage() {
  const status = await apiFetch("/me/api-keys");

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-10 text-slate-100">
      <div className="mx-auto max-w-lg space-y-6 rounded-xl bg-slate-900 p-8 shadow-xl">
        <div>
          <h1 className="text-xl font-semibold">Settings</h1>
          <p className="text-sm text-slate-400">
            Bring your own API keys (BYOK). Keys are encrypted at rest and
            used instead of the app&apos;s shared keys when set.
          </p>
        </div>

        <ApiKeysForm initialStatus={status} />

        <Link href="/" className="block text-sm text-slate-400 hover:text-slate-200">
          &larr; Back to dashboard
        </Link>
      </div>
    </main>
  );
}
