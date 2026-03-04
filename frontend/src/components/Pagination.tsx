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

  // Show up to 5 page numbers centered on current
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
          className="px-4 py-2 bg-[#141414] border border-[#1F1F1F] rounded text-[#EDEDED] text-sm transition-all duration-200 hover:border-[#CC0000]"
        >
          Previous
        </Link>
      ) : (
        <span className="px-4 py-2 bg-[#141414] border border-[#1F1F1F] rounded text-[#888888] text-sm cursor-not-allowed opacity-50">
          Previous
        </span>
      )}

      {pages.map((p) => (
        <Link
          key={p}
          href={buildHref(p)}
          className={`px-3 py-2 rounded text-sm transition-all duration-200 ${
            p === page
              ? "bg-[#CC0000] text-white"
              : "bg-[#141414] border border-[#1F1F1F] text-[#EDEDED] hover:border-[#CC0000]"
          }`}
        >
          {p}
        </Link>
      ))}

      {has_next ? (
        <Link
          href={buildHref(page + 1)}
          className="px-4 py-2 bg-[#141414] border border-[#1F1F1F] rounded text-[#EDEDED] text-sm transition-all duration-200 hover:border-[#CC0000]"
        >
          Next
        </Link>
      ) : (
        <span className="px-4 py-2 bg-[#141414] border border-[#1F1F1F] rounded text-[#888888] text-sm cursor-not-allowed opacity-50">
          Next
        </span>
      )}
    </nav>
  );
}
