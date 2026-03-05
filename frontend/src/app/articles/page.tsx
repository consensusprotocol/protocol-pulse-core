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

  // Split: first 2 large, then the rest
  const firstRow = rest.slice(0, 2);
  const gridRest = rest.slice(2);

  const paginationParams: Record<string, string> = {};
  if (category) paginationParams.category = category;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Category filters */}
      {categories && categories.length > 0 && (
        <div className="sticky top-16 z-30 bg-[#0A0A0A]/95 backdrop-blur-sm py-3 -mx-4 px-4 mb-8 border-b border-[#1F1F1F]">
          <div className="flex gap-2 overflow-x-auto category-scroll pb-1">
            <Link
              href="/articles"
              className={`flex-shrink-0 text-xs uppercase tracking-wider px-4 py-2 rounded-full font-medium transition-all duration-200 ${
                !category
                  ? "bg-[#CC0000] text-white shadow-[0_0_15px_rgba(204,0,0,0.3)]"
                  : "bg-[#141414] text-[#888888] border border-[#1F1F1F] hover:border-[#CC0000]/50 hover:text-[#EDEDED]"
              }`}
            >
              All
            </Link>
            {categories.map((cat) => (
              <Link
                key={cat.name}
                href={`/articles?category=${encodeURIComponent(cat.name)}`}
                className={`flex-shrink-0 text-xs uppercase tracking-wider px-4 py-2 rounded-full font-medium transition-all duration-200 ${
                  category === cat.name
                    ? "bg-[#CC0000] text-white shadow-[0_0_15px_rgba(204,0,0,0.3)]"
                    : "bg-[#141414] text-[#888888] border border-[#1F1F1F] hover:border-[#CC0000]/50 hover:text-[#EDEDED]"
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
              <div className="mb-10">
                <ArticleCard article={featured} featured />
              </div>
            )}

            {/* Section header */}
            <div className="mb-8">
              <h2 className="text-xl md:text-2xl font-bold">Latest Intel</h2>
              <div className="w-10 h-0.5 bg-[#CC0000] mt-2" />
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
              <div className="bg-[#141414] border border-[#1F1F1F] rounded-xl p-5">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-[#EDEDED] mb-4">
                  Trending
                </h3>
                <div className="w-8 h-0.5 bg-[#CC0000] mb-4" />
                <ul className="space-y-4">
                  {articles.slice(0, 5).map((article, i) => (
                    <li key={article.id}>
                      <Link
                        href={`/articles/${article.slug}`}
                        className="group flex gap-3"
                      >
                        <span className="text-[#CC0000] font-bold text-sm tabular-nums flex-shrink-0">
                          {String(i + 1).padStart(2, "0")}
                        </span>
                        <span className="text-sm text-[#888888] group-hover:text-[#EDEDED] transition-colors line-clamp-2 leading-snug">
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
