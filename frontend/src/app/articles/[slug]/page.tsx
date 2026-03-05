import { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { fetchArticle, fetchArticles } from "@/lib/api";
import ArticleCard from "@/components/ArticleCard";
import ShareButtons from "@/components/ShareButtons";

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const article = await fetchArticle(slug);

  if (!article) {
    return { title: "Article Not Found | Protocol Pulse" };
  }

  return {
    title: `${article.title} | Protocol Pulse`,
    description: article.summary,
    openGraph: {
      title: article.title,
      description: article.summary,
      type: "article",
      publishedTime: article.published_at,
      authors: [article.author],
      images: article.cover_image_url ? [article.cover_image_url] : [],
    },
    twitter: {
      card: "summary_large_image",
      title: article.title,
      description: article.summary,
      images: article.cover_image_url ? [article.cover_image_url] : [],
    },
  };
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

export default async function ArticlePage({ params }: PageProps) {
  const { slug } = await params;
  const article = await fetchArticle(slug);

  if (!article) {
    notFound();
  }

  const relatedData = await fetchArticles(1, 4, article.category);
  const related = (relatedData?.articles ?? [])
    .filter((a) => a.slug !== article.slug)
    .slice(0, 3);

  return (
    <article className="pb-20">
      {/* Back link */}
      <div className="max-w-7xl mx-auto px-4 py-4">
        <Link
          href="/articles"
          className="text-[#CC0000] hover:text-[#FF4444] hover:drop-shadow-[0_0_8px_rgba(204,0,0,0.3)] text-sm transition-all duration-300 inline-flex items-center gap-1"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M10 4L6 8l4 4" />
          </svg>
          Back to Intel
        </Link>
      </div>

      {/* Hero image with Ken Burns effect */}
      {article.cover_image_url && (
        <div className="relative w-full h-[300px] md:h-[500px] overflow-hidden">
          <Image
            src={article.cover_image_url}
            alt={article.title}
            fill
            className="object-cover ken-burns"
            sizes="100vw"
            priority
          />
          {/* Multi-layer gradient overlay */}
          <div className="absolute inset-0 bg-gradient-to-t from-[#0A0A0A] via-[#0A0A0A]/30 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-r from-[#0A0A0A]/20 via-transparent to-[#0A0A0A]/20" />
        </div>
      )}

      {/* Article header */}
      <div className="max-w-3xl mx-auto px-4 -mt-24 relative z-10 animate-fade-in-up">
        <span className="inline-block bg-[#CC0000]/10 backdrop-blur-sm text-[#CC0000] text-xs uppercase tracking-wider px-3 py-1 rounded-full border border-[#CC0000]/20 mb-4 shadow-[0_0_15px_rgba(204,0,0,0.1)]">
          {article.category}
        </span>

        <h1 className="text-3xl md:text-4xl lg:text-5xl font-bold leading-tight mb-6 drop-shadow-[0_2px_20px_rgba(0,0,0,0.5)]">
          {article.title}
        </h1>

        <div className="flex flex-wrap items-center gap-3 text-[#888888] text-sm mb-10 pb-8 border-b border-white/[0.06]">
          {/* Author avatar placeholder */}
          <div className="w-9 h-9 rounded-full bg-[#CC0000]/15 backdrop-blur-sm border border-[#CC0000]/20 flex items-center justify-center text-[#CC0000] text-xs font-bold shadow-[0_0_10px_rgba(204,0,0,0.1)]">
            {article.author.charAt(0).toUpperCase()}
          </div>
          <span className="font-medium text-[#EDEDED]">
            {article.author}
          </span>
          <span className="text-[#CC0000]/50">·</span>
          <time dateTime={article.published_at}>
            {formatDate(article.published_at)}
          </time>
          {article.read_time_minutes > 0 && (
            <>
              <span className="text-[#CC0000]/50">·</span>
              <span>{article.read_time_minutes} min read</span>
            </>
          )}
          <div className="ml-auto">
            <ShareButtons title={article.title} slug={article.slug} />
          </div>
        </div>

        {/* Article body */}
        {article.content && (
          <div
            className="article-body animate-fade-in-up-delay-1"
            dangerouslySetInnerHTML={{ __html: article.content }}
          />
        )}

        {/* Source attribution */}
        {article.source_url && (
          <div className="mt-12 pt-6 border-t border-white/[0.06]">
            <p className="text-[#888888] text-sm">
              Source:{" "}
              <a
                href={article.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#CC0000] hover:text-[#FF4444] hover:drop-shadow-[0_0_8px_rgba(204,0,0,0.3)] transition-all duration-300"
              >
                {article.source_type || "Original"}
              </a>
            </p>
          </div>
        )}
      </div>

      {/* Related articles */}
      {related.length > 0 && (
        <div className="max-w-7xl mx-auto px-4 mt-20">
          <div className="border-t border-white/[0.06] pt-12">
            <h2 className="text-xl md:text-2xl font-bold mb-2">
              Related Intel
            </h2>
            <div className="w-16 h-[3px] bg-[#CC0000] mt-3 mb-8 rounded-full shadow-[0_0_10px_rgba(204,0,0,0.3)]" />
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {related.map((a) => (
                <ArticleCard key={a.id} article={a} />
              ))}
            </div>
          </div>
        </div>
      )}
    </article>
  );
}
