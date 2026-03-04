import { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { fetchArticle } from "@/lib/api";

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
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

  return (
    <article className="pb-16">
      {/* Back link */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <Link
          href="/articles"
          className="text-[#CC0000] hover:text-[#CC0000]/80 text-sm transition-all duration-200"
        >
          &larr; Back to Intel
        </Link>
      </div>

      {/* Hero image */}
      {article.cover_image_url && (
        <div className="relative w-full max-w-5xl mx-auto aspect-video mb-8">
          <Image
            src={article.cover_image_url}
            alt={article.title}
            fill
            className="object-cover rounded-lg"
            sizes="(max-width: 1024px) 100vw, 1024px"
            priority
          />
        </div>
      )}

      {/* Article header */}
      <div className="max-w-3xl mx-auto px-4">
        <span className="bg-[#CC0000]/20 text-[#CC0000] text-xs uppercase tracking-wider px-2 py-1 rounded">
          {article.category}
        </span>

        <h1 className="text-3xl md:text-4xl font-bold mt-4 mb-4 leading-tight">
          {article.title}
        </h1>

        <div className="flex flex-wrap items-center gap-3 text-[#888888] text-sm mb-10">
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

        {/* Article body */}
        {article.content && (
          <div
            className="article-body"
            dangerouslySetInnerHTML={{ __html: article.content }}
          />
        )}

        {/* Source attribution */}
        {article.source_url && (
          <div className="mt-12 pt-6 border-t border-[#1F1F1F]">
            <p className="text-[#888888] text-sm">
              Source:{" "}
              <a
                href={article.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#CC0000] hover:text-[#CC0000]/80 transition-all duration-200"
              >
                {article.source_type || "Original"}
              </a>
            </p>
          </div>
        )}
      </div>
    </article>
  );
}
