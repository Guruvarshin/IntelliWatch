"use client";

import { useState } from "react";

function KeyField({ label, hint, isSet, value, onChange }) {
  return (
    <div>
      <label className="block text-sm text-slate-400">{label}</label>
      {hint && <p className="text-xs text-slate-500">{hint}</p>}
      <p className="text-xs text-slate-500">
        Status: {isSet ? "set" : "not set"}
      </p>
      <input
        type="password"
        placeholder={isSet ? "Leave blank to keep, or enter a new key" : "sk-..."}
        value={value}
        onChange={onChange}
        className="mt-1 w-full rounded-md bg-slate-800 px-3 py-2 text-slate-100 outline-none ring-1 ring-slate-700 focus:ring-indigo-500"
      />
    </div>
  );
}

export default function ApiKeysForm({ initialStatus }) {
  const [status, setStatus] = useState(initialStatus);
  const [openaiKey, setOpenaiKey] = useState("");
  const [anthropicKey, setAnthropicKey] = useState("");
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [loading, setLoading] = useState(false);

  const save = async () => {
    setError(null);
    setMessage(null);
    setLoading(true);

    const body = {};
    if (openaiKey.trim() !== "") body.openai_api_key = openaiKey.trim();
    if (anthropicKey.trim() !== "") body.anthropic_api_key = anthropicKey.trim();

    const res = await fetch("/api/settings/api-keys", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    setLoading(false);

    if (!res.ok) {
      setError(data.error ?? "Something went wrong.");
      return;
    }

    setStatus(data);
    setOpenaiKey("");
    setAnthropicKey("");
    setMessage("Saved.");
  };

  const clear = async (field) => {
    setError(null);
    setMessage(null);
    setLoading(true);

    const res = await fetch("/api/settings/api-keys", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ [field]: "" }),
    });

    const data = await res.json();
    setLoading(false);

    if (!res.ok) {
      setError(data.error ?? "Something went wrong.");
      return;
    }

    setStatus(data);
    setMessage("Cleared.");
  };

  return (
    <div className="space-y-4">
      {error && (
        <p className="rounded bg-red-950 px-3 py-2 text-sm text-red-400">
          {error}
        </p>
      )}
      {message && (
        <p className="rounded bg-emerald-950 px-3 py-2 text-sm text-emerald-400">
          {message}
        </p>
      )}

      <KeyField
        label="OpenAI API key"
        hint="Used for extraction and embeddings. Falls back to the app's shared key if not set."
        isSet={status.openai_api_key_set}
        value={openaiKey}
        onChange={(e) => setOpenaiKey(e.target.value)}
      />
      {status.openai_api_key_set && (
        <button
          type="button"
          onClick={() => clear("openai_api_key")}
          disabled={loading}
          className="text-xs text-red-400 hover:text-red-300 disabled:opacity-50"
        >
          Clear OpenAI key
        </button>
      )}

      <KeyField
        label="Anthropic API key"
        hint="Used for brief synthesis. Falls back to the app's shared key if not set."
        isSet={status.anthropic_api_key_set}
        value={anthropicKey}
        onChange={(e) => setAnthropicKey(e.target.value)}
      />
      {status.anthropic_api_key_set && (
        <button
          type="button"
          onClick={() => clear("anthropic_api_key")}
          disabled={loading}
          className="text-xs text-red-400 hover:text-red-300 disabled:opacity-50"
        >
          Clear Anthropic key
        </button>
      )}

      <button
        type="button"
        onClick={save}
        disabled={loading}
        className="w-full rounded-md bg-indigo-600 py-2 font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
      >
        {loading ? "Saving..." : "Save"}
      </button>
    </div>
  );
}
