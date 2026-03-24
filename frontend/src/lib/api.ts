import { Article, ArticlesResponse, CategoryInfo, PriceData } from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "https://protocolpulse.replit.app";

export async function fetchArticles(
  page = 1,
  perPage = 20,
  category?: string,
  sort = "newest"
): Promise<ArticlesResponse | null> {
  try {
    const params = new URLSearchParams({
      page: String(page),
      per_page: String(perPage),
      sort,
    });
    if (category) params.set("category", category);

    const res = await fetch(`${API_BASE_URL}/api/v2/articles?${params}`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchArticle(slug: string): Promise<Article | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v2/articles/${slug}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    const data = await res.json();
    // API returns { article: {...}, meta: {...} } — unwrap
    return data.article ?? data;
  } catch {
    return null;
  }
}

export async function fetchCategories(): Promise<CategoryInfo[] | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v2/categories`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function searchArticles(
  query: string,
  page = 1
): Promise<ArticlesResponse | null> {
  try {
    const params = new URLSearchParams({
      q: query,
      page: String(page),
    });
    const res = await fetch(`${API_BASE_URL}/api/v2/search?${params}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchPrices(): Promise<PriceData | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v2/prices`, {
      next: { revalidate: 30 },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}
