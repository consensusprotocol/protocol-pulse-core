"use client";

import { useState } from "react";

export default function ShareButtons({
  title,
  slug,
}: {
  title: string;
  slug: string;
}) {
  const [copied, setCopied] = useState(false);

  const url =
    typeof window !== "undefined"
      ? `${window.location.origin}/articles/${slug}`
      : `/articles/${slug}`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback: do nothing
    }
  };

  const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(title)}&url=${encodeURIComponent(url)}`;

  return (
    <div className="flex items-center gap-1">
      <button
        onClick={handleCopy}
        className="text-[#888888] hover:text-[#EDEDED] hover:drop-shadow-[0_0_8px_rgba(237,237,237,0.15)] transition-all duration-200 p-2 rounded-lg hover:bg-white/[0.05]"
        title="Copy link"
      >
        {copied ? (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="#CC0000" strokeWidth="2">
            <path d="M3 8l3 3 7-7" />
          </svg>
        ) : (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M6.5 9.5l3-3M5.5 7L4 8.5a2.12 2.12 0 003 3L8.5 10M10.5 9l1.5-1.5a2.12 2.12 0 00-3-3L7.5 6" />
          </svg>
        )}
      </button>
      <a
        href={twitterUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="text-[#888888] hover:text-[#EDEDED] hover:drop-shadow-[0_0_8px_rgba(237,237,237,0.15)] transition-all duration-200 p-2 rounded-lg hover:bg-white/[0.05]"
        title="Share on X"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <path d="M9.3 6.8L14.5 1h-1.2L8.8 6.1 5.2 1H1l5.4 7.9L1 15h1.2l4.7-5.5L10.8 15H15L9.3 6.8zm-1.7 1.9l-.5-.8L2.8 1.9h1.9l3.5 5 .5.8 4.5 6.4h-1.9L7.6 8.7z" />
        </svg>
      </a>
    </div>
  );
}
