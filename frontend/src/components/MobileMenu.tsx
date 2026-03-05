"use client";

import { useState } from "react";
import Link from "next/link";

interface MobileMenuProps {
  links: { href: string; label: string }[];
}

export default function MobileMenu({ links }: MobileMenuProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="md:hidden">
      <button
        onClick={() => setOpen(!open)}
        className="text-[#888888] hover:text-[#EDEDED] transition-colors p-2"
        aria-label="Toggle menu"
      >
        {open ? (
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 4l12 12M16 4L4 16" />
          </svg>
        ) : (
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 5h14M3 10h14M3 15h14" />
          </svg>
        )}
      </button>

      {open && (
        <div className="absolute top-[calc(4rem+1px)] left-0 right-0 bg-black/80 backdrop-blur-xl border-b border-white/[0.06] z-40">
          <div className="max-w-7xl mx-auto px-4 py-6 flex flex-col gap-1">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className="text-[#888888] hover:text-[#EDEDED] text-sm font-medium uppercase tracking-wider transition-all duration-200 py-3 px-4 rounded-lg hover:bg-white/[0.03]"
              >
                {link.label}
              </Link>
            ))}
          </div>
          <div className="red-gradient-line" />
        </div>
      )}
    </div>
  );
}
