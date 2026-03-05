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
          className="px-4 py-2 bg-[#141414] border border-[#1F1F1F] rounded-lg text-[#EDEDED] text-sm transition-all duration-200 hover:border-[#CC0000] hover:text-white"
        >
          Previous
        </Link>
      ) : (
        <span className="px-4 py-2 bg-[#141414] border border-[#1F1F1F] rounded-lg text-[#888888] text-sm cursor-not-allowed opacity-50">
          Previous
        </span>
      )}

      {pages.map((p) => (
        <Link
          key={p}
          href={buildHref(p)}
          className={`px-3.5 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
            p === page
              ? "bg-[#CC0000] text-white shadow-[0_0_15px_rgba(204,0,0,0.3)]"
              : "bg-[#141414] border border-[#1F1F1F] text-[#EDEDED] hover:border-[#CC0000] hover:text-white"
          }`}
        >
          {p}
        </Link>
      ))}

      {has_next ? (
        <Link
          href={buildHref(page + 1)}
          className="px-4 py-2 bg-[#141414] border border-[#1F1F1F] rounded-lg text-[#EDEDED] text-sm transition-all duration-200 hover:border-[#CC0000] hover:text-white"
        >
          Next
        </Link>
      ) : (
        <span className="px-4 py-2 bg-[#141414] border border-[#1F1F1F] rounded-lg text-[#888888] text-sm cursor-not-allowed opacity-50">
          Next
        </span>
      )}
    </nav>
  );
}
