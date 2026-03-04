import Link from "next/link";
import { fetchArticles, fetchCategories } from "@/lib/api";
import ArticleCard from "@/components/ArticleCard";
import Pagination from "@/components/Pagination";

interface PageProps {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}

export default async function ArticlesPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const page = Number(params.page) || 1;
  const category = typeof params.category === "string" ? params.category : undefined;

  const [articlesData, categories] = await Promise.all([
    fetchArticles(page, 20, category),
    fetchCategories(),
  ]);

  // Build searchParams for pagination links
  const paginationParams: Record<string, string> = {};
  if (category) paginationParams.category = category;

  return (
    <div className="max-w-7xl mx-auto px-4 py-12">
      {/* Hero */}
      <div className="mb-10">
        <h1 className="text-3xl md:text-4xl font-bold mb-2">Latest Intelligence</h1>
        <p className="text-[#888888]">
          Real-time Bitcoin analysis and investigative reporting
        </p>
      </div>

      {/* Category filters */}
      {categories && categories.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-8">
          <Link
            href="/articles"
            className={`text-xs uppercase tracking-wider px-3 py-1.5 rounded transition-all duration-200 ${
              !category
                ? "bg-[#CC0000] text-white"
                : "bg-[#CC0000]/20 text-[#CC0000] hover:bg-[#CC0000]/30"
            }`}
          >
            All
          </Link>
          {categories.map((cat) => (
            <Link
              key={cat.name}
              href={`/articles?category=${encodeURIComponent(cat.name)}`}
              className={`text-xs uppercase tracking-wider px-3 py-1.5 rounded transition-all duration-200 ${
                category === cat.name
                  ? "bg-[#CC0000] text-white"
                  : "bg-[#CC0000]/20 text-[#CC0000] hover:bg-[#CC0000]/30"
              }`}
            >
              {cat.name} ({cat.count})
            </Link>
          ))}
        </div>
      )}

      {/* Articles grid */}
      {articlesData && articlesData.articles.length > 0 ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {articlesData.articles.map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))}
          </div>

          <Pagination
            pagination={articlesData.pagination}
            basePath="/articles"
            searchParams={paginationParams}
          />
        </>
      ) : (
        <div className="text-center py-24">
          <p className="text-[#888888] text-lg">No articles found.</p>
          {category && (
            <Link
              href="/articles"
              className="text-[#CC0000] hover:text-[#CC0000]/80 mt-4 inline-block"
            >
              Clear filters
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
