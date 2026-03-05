import Link from "next/link";
import { PaginationInfo } from "@/lib/types";

interface PaginationProps {
  pagination: PaginationInfo;
  basePath: string;
  searchParams?: Record<string, string>;
}

export default function Pagination({
  pagination,
  basePath,
  searchParams = {},
}: PaginationProps) {
  const { page, total_pages, has_prev, has_next } = pagination;

  function buildHref(p: number): string {
    const params = new URLSearchParams(searchParams);
    params.set("page", String(p));
    return `${basePath}?${params.toString()}`;
  }

  const pages: number[] = [];
  const start = Math.max(1, page - 2);
  const end = Math.min(total_pages, start + 4);
  for (let i = start; i <= end; i++) {
    pages.push(i);
  }

  return (
    <nav className="flex items-center justify-center gap-2 mt-12">
      {has_prev ? (
        <Link
          href={buildHref(page - 1)}
          className="px-4 py-2 bg-white/[0.03] backdrop-blur-sm border border-white/[0.06] rounded-lg text-[#EDEDED] text-sm transition-all duration-300 hover:border-[#CC0000]/30 hover:shadow-[0_0_20px_rgba(204,0,0,0.1)] hover:text-white"
        >
          Previous
        </Link>
      ) : (
        <span className="px-4 py-2 bg-white/[0.02] border border-white/[0.04] rounded-lg text-[#888888] text-sm cursor-not-allowed opacity-40">
          Previous
        </span>
      )}

      {pages.map((p) => (
        <Link
          key={p}
          href={buildHref(p)}
          className={`px-3.5 py-2 rounded-lg text-sm font-medium transition-all duration-300 ${
            p === page
              ? "bg-[#CC0000] text-white shadow-[0_0_20px_rgba(204,0,0,0.35)]"
              : "bg-white/[0.03] backdrop-blur-sm border border-white/[0.06] text-[#EDEDED] hover:border-[#CC0000]/30 hover:shadow-[0_0_20px_rgba(204,0,0,0.1)] hover:text-white"
          }`}
        >
          {p}
        </Link>
      ))}

      {has_next ? (
        <Link
          href={buildHref(page + 1)}
          className="px-4 py-2 bg-white/[0.03] backdrop-blur-sm border border-white/[0.06] rounded-lg text-[#EDEDED] text-sm transition-all duration-300 hover:border-[#CC0000]/30 hover:shadow-[0_0_20px_rgba(204,0,0,0.1)] hover:text-white"
        >
          Next
        </Link>
      ) : (
        <span className="px-4 py-2 bg-white/[0.02] border border-white/[0.04] rounded-lg text-[#888888] text-sm cursor-not-allowed opacity-40">
          Next
        </span>
      )}
    </nav>
  );
}
