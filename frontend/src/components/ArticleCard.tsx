import Image from "next/image";
import Link from "next/link";
import { Article } from "@/lib/types";

function stripHtml(html: string): string {
  return html.replace(/<[^>]*>/g, '').replace(/&[^;]+;/g, ' ').trim();
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function ArticleCard({
  article,
  featured = false,
}: {
  article: Article;
  featured?: boolean;
}) {
  if (featured) {
    return (
      <Link href={`/articles/${article.slug}`} className="group block">
        <article className="relative w-full h-[400px] md:h-[600px] rounded-2xl overflow-hidden glass glow-line-top">
          {article.cover_image_url ? (
            <Image
              src={article.cover_image_url}
              alt={article.title}
              fill
              className="object-cover img-zoom"
              sizes="100vw"
              priority
            />
          ) : (
            <div className="w-full h-full bg-[#1F1F1F]" />
          )}
          {/* Multi-layer gradient for depth */}
          <div className="absolute inset-0 bg-gradient-to-t from-black via-black/50 to-black/0" />
          <div className="absolute inset-0 bg-gradient-to-r from-black/30 via-transparent to-transparent" />

          {/* Glassmorphism info bar at bottom */}
          <div className="absolute bottom-0 left-0 right-0 p-6 md:p-10 bg-black/30 backdrop-blur-lg border-t border-white/[0.08]">
            {/* LIVE INTELLIGENCE label with pulsing dot */}
            <div className="flex items-center gap-2 mb-3">
              <span className="pulse-dot" />
              <span className="text-[10px] uppercase tracking-[0.2em] text-[#CC0000] font-semibold">
                Live Intelligence
              </span>
            </div>

            <span className="inline-block bg-[#CC0000]/10 backdrop-blur-sm text-[#CC0000] text-xs uppercase tracking-wider px-3 py-1 rounded-full border border-[#CC0000]/20 mb-4 shadow-[0_0_15px_rgba(204,0,0,0.1)]">
              {article.category}
            </span>
            <h2 className="text-2xl md:text-4xl lg:text-5xl font-bold leading-tight mb-3 text-white drop-shadow-[0_2px_10px_rgba(0,0,0,0.5)] group-hover:drop-shadow-[0_2px_20px_rgba(204,0,0,0.2)] transition-all duration-500">
              {article.title}
            </h2>
            <p className="text-white/70 text-sm md:text-base line-clamp-2 mb-4 max-w-3xl">
              {stripHtml(article.summary)}
            </p>
            <div className="flex items-center gap-3 text-white/50 text-sm">
              <span>{article.author}</span>
              <span className="text-[#CC0000]">·</span>
              <time dateTime={article.created_at}>
                {formatDate(article.created_at)}
              </time>
              {article.read_time_minutes > 0 && (
                <>
                  <span className="text-[#CC0000]">·</span>
                  <span>{article.read_time_minutes} min read</span>
                </>
              )}
            </div>
          </div>
        </article>
      </Link>
    );
  }

  return (
    <Link href={`/articles/${article.slug}`} className="group block h-full">
      <article className="relative bg-white/[0.03] backdrop-blur-md border border-white/[0.06] rounded-xl overflow-hidden hover:border-[#CC0000]/30 hover:shadow-[0_0_40px_rgba(204,0,0,0.12)] hover:bg-white/[0.05] hover:-translate-y-1.5 transition-all duration-500 h-full flex flex-col glow-line-top">
        <div className="relative w-full aspect-video overflow-hidden">
          {article.cover_image_url ? (
            <Image
              src={article.cover_image_url}
              alt={article.title}
              fill
              className="object-cover img-zoom"
              sizes="(max-width: 768px) 100vw, (max-width: 1024px) 50vw, 33vw"
            />
          ) : (
            <div className="w-full h-full bg-[#1F1F1F] flex items-center justify-center">
              <span className="text-[#888888] text-sm">No image</span>
            </div>
          )}
          {/* Gradient overlay on image for depth */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
        </div>
        <div className="p-5 flex flex-col flex-1">
          <span className="inline-block bg-[#CC0000]/10 backdrop-blur-sm text-[#CC0000] text-xs uppercase tracking-wider px-2.5 py-1 rounded-full w-fit mb-3 border border-[#CC0000]/20">
            {article.category}
          </span>
          <h2 className="text-[#EDEDED] font-bold text-lg leading-snug line-clamp-2 mb-2 group-hover:text-white transition-colors duration-300">
            {article.title}
          </h2>
          <p className="text-sm text-[#888888] line-clamp-2 mb-4">
            {stripHtml(article.summary)}
          </p>
          <div className="mt-auto flex items-center gap-3 text-[#888888] text-xs">
            <span>{article.author}</span>
            <span className="text-[#CC0000]/50">·</span>
            <span>{formatDate(article.created_at)}</span>
            {article.read_time_minutes > 0 && (
              <>
                <span className="text-[#CC0000]/50">·</span>
                <span>{article.read_time_minutes} min</span>
              </>
            )}
          </div>
        </div>
      </article>
    </Link>
  );
}
