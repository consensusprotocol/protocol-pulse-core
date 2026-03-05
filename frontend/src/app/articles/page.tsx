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
  const category =
    typeof params.category === "string" ? params.category : undefined;

  const [articlesData, categories] = await Promise.all([
    fetchArticles(page, 20, category),
    fetchCategories(),
  ]);

  const articles = articlesData?.articles ?? [];
  const featured = articles[0];
  const rest = articles.slice(1);

  const firstRow = rest.slice(0, 2);
  const gridRest = rest.slice(2);

  const paginationParams: Record<string, string> = {};
  if (category) paginationParams.category = category;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Category filters */}
      {categories && categories.length > 0 && (
        <div className="sticky top-[calc(4rem+1px)] z-30 bg-black/60 backdrop-blur-xl py-3 -mx-4 px-4 mb-8 border-b border-white/[0.06]">
          <div className="flex gap-2 overflow-x-auto category-scroll pb-1">
            <Link
              href="/articles"
              className={`flex-shrink-0 text-xs uppercase tracking-wider px-4 py-2 rounded-full font-medium transition-all duration-300 ${
                !category
                  ? "bg-[#CC0000] text-white shadow-[0_0_20px_rgba(204,0,0,0.35)]"
                  : "bg-white/[0.03] backdrop-blur-sm text-[#888888] border border-white/[0.06] hover:border-[#CC0000]/30 hover:text-[#EDEDED] hover:shadow-[0_0_15px_rgba(204,0,0,0.08)]"
              }`}
            >
              All
            </Link>
            {categories.map((cat) => (
              <Link
                key={cat.name}
                href={`/articles?category=${encodeURIComponent(cat.name)}`}
                className={`flex-shrink-0 text-xs uppercase tracking-wider px-4 py-2 rounded-full font-medium transition-all duration-300 ${
                  category === cat.name
                    ? "bg-[#CC0000] text-white shadow-[0_0_20px_rgba(204,0,0,0.35)]"
                    : "bg-white/[0.03] backdrop-blur-sm text-[#888888] border border-white/[0.06] hover:border-[#CC0000]/30 hover:text-[#EDEDED] hover:shadow-[0_0_15px_rgba(204,0,0,0.08)]"
                }`}
              >
                {cat.name}
              </Link>
            ))}
          </div>
        </div>
      )}

      {articles.length > 0 ? (
        <div className="flex gap-8">
          {/* Main content */}
          <div className="flex-1 min-w-0">
            {/* Featured hero */}
            {featured && page === 1 && (
              <div className="mb-10 animate-fade-in-up">
                <ArticleCard article={featured} featured />
              </div>
            )}

            {/* Section header */}
            <div className="mb-8">
              <h2 className="text-xl md:text-2xl font-bold">Latest Intel</h2>
              <div className="w-16 h-[3px] bg-[#CC0000] mt-3 rounded-full shadow-[0_0_10px_rgba(204,0,0,0.3)]" />
            </div>

            {/* First row: 2 large cards */}
            {firstRow.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                {firstRow.map((article) => (
                  <ArticleCard key={article.id} article={article} />
                ))}
              </div>
            )}

            {/* Rest: 3-column grid */}
            {gridRest.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {gridRest.map((article) => (
                  <ArticleCard key={article.id} article={article} />
                ))}
              </div>
            )}

            {articlesData && (
              <Pagination
                pagination={articlesData.pagination}
                basePath="/articles"
                searchParams={paginationParams}
              />
            )}
          </div>

          {/* Sidebar - desktop only */}
          <aside className="hidden lg:block w-72 flex-shrink-0">
            <div className="sticky top-24">
              <div className="bg-white/[0.03] backdrop-blur-md border border-white/[0.06] rounded-xl p-5 relative glow-line-top">
                <div className="flex items-center gap-2 mb-4">
                  <span className="pulse-dot" />
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-[#EDEDED]">
                    Trending
                  </h3>
                </div>
                <div className="w-8 h-[2px] bg-[#CC0000] mb-5 rounded-full shadow-[0_0_8px_rgba(204,0,0,0.3)]" />
                <ul className="space-y-4">
                  {articles.slice(0, 5).map((article, i) => (
                    <li key={article.id}>
                      <Link
                        href={`/articles/${article.slug}`}
                        className="group flex gap-3 py-1"
                      >
                        <span className="text-[#CC0000]/70 font-bold text-sm tabular-nums flex-shrink-0 group-hover:text-[#CC0000] group-hover:drop-shadow-[0_0_6px_rgba(204,0,0,0.3)] transition-all duration-300">
                          {String(i + 1).padStart(2, "0")}
                        </span>
                        <span className="text-sm text-[#888888] group-hover:text-[#EDEDED] transition-colors duration-300 line-clamp-2 leading-snug">
                          {article.title}
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </aside>
        </div>
      ) : (
        <div className="text-center py-24">
          <p className="text-[#888888] text-lg">No articles found.</p>
          {category && (
            <Link
              href="/articles"
              className="text-[#CC0000] hover:text-[#FF4444] mt-4 inline-block"
            >
              Clear filters
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
