"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function RunButton({ competitorId }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleClick = async () => {
    setLoading(true);
    setError(null);

    const res = await fetch(`/api/competitors/${competitorId}/run`, {
      method: "POST",
    });

    if (!res.ok) {
      const data = await res.json();
      setError(data.error ?? "Run failed.");
      setLoading(false);
      return;
    }

    setLoading(false);
    router.refresh();
  };

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        onClick={handleClick}
        disabled={loading}
        className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500 disabled:opacity-50"
      >
        {loading ? "Running... (this can take a minute)" : "Run now"}
      </button>
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}
