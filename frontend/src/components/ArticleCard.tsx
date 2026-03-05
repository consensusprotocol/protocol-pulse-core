import Image from "next/image";
import Link from "next/link";
import { Article } from "@/lib/types";

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
        <article className="relative w-full h-[400px] md:h-[600px] rounded-2xl overflow-hidden">
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
          <div className="absolute inset-0 bg-gradient-to-t from-black via-black/40 to-transparent" />
          <div className="absolute bottom-0 left-0 right-0 p-6 md:p-10">
            <span className="inline-block bg-[#CC0000] text-white text-xs uppercase tracking-wider px-3 py-1 rounded-full mb-4">
              {article.category}
            </span>
            <h2 className="text-2xl md:text-4xl lg:text-5xl font-bold leading-tight mb-3 text-white group-hover:text-[#EDEDED] transition-colors">
              {article.title}
            </h2>
            <p className="text-[#CCCCCC] text-sm md:text-base line-clamp-2 mb-4 max-w-3xl">
              {article.summary}
            </p>
            <div className="flex items-center gap-3 text-[#888888] text-sm">
              <span>{article.author}</span>
              <span>·</span>
              <time dateTime={article.published_at}>
                {formatDate(article.published_at)}
              </time>
              {article.read_time_minutes > 0 && (
                <>
                  <span>·</span>
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
      <article className="bg-[#141414] border border-[#1F1F1F] rounded-xl overflow-hidden hover:border-[#CC0000]/30 hover:shadow-[0_0_30px_rgba(204,0,0,0.1)] hover:-translate-y-1 transition-all duration-300 h-full flex flex-col">
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
        </div>
        <div className="p-5 flex flex-col flex-1">
          <span className="inline-block bg-[#CC0000]/20 text-[#CC0000] text-xs uppercase tracking-wider px-2.5 py-1 rounded-full w-fit mb-3">
            {article.category}
          </span>
          <h2 className="text-[#EDEDED] font-bold text-lg leading-snug line-clamp-2 mb-2 group-hover:text-white transition-colors">
            {article.title}
          </h2>
          <p className="text-sm text-[#888888] line-clamp-2 mb-4">
            {article.summary}
          </p>
          <div className="mt-auto flex items-center gap-3 text-[#888888] text-xs">
            <span>{article.author}</span>
            <span>·</span>
            <span>{formatDate(article.published_at)}</span>
            {article.read_time_minutes > 0 && (
              <>
                <span>·</span>
                <span>{article.read_time_minutes} min</span>
              </>
            )}
          </div>
        </div>
      </article>
    </Link>
  );
}
