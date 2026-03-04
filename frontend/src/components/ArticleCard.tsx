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

export default function ArticleCard({ article }: { article: Article }) {
  return (
    <Link href={`/articles/${article.slug}`}>
      <article className="bg-[#141414] border border-[#1F1F1F] rounded-lg overflow-hidden transition-all duration-200 hover:shadow-lg hover:-translate-y-1 h-full flex flex-col">
        <div className="relative w-full aspect-video">
          {article.cover_image_url ? (
            <Image
              src={article.cover_image_url}
              alt={article.title}
              fill
              className="object-cover"
              sizes="(max-width: 768px) 100vw, (max-width: 1024px) 50vw, 33vw"
            />
          ) : (
            <div className="w-full h-full bg-[#1F1F1F] flex items-center justify-center">
              <span className="text-[#888888] text-sm">No image</span>
            </div>
          )}
        </div>
        <div className="p-4 flex flex-col flex-1">
          <span className="bg-[#CC0000]/20 text-[#CC0000] text-xs uppercase tracking-wider px-2 py-1 rounded w-fit mb-3">
            {article.category}
          </span>
          <h2 className="text-[#EDEDED] font-bold text-lg leading-snug line-clamp-2 mb-3">
            {article.title}
          </h2>
          <div className="mt-auto flex items-center gap-3 text-[#888888] text-sm">
            <span>{article.author}</span>
            <span>·</span>
            <span>{formatDate(article.published_at)}</span>
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
