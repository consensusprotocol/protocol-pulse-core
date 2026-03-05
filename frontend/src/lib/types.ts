export interface Article {
  id: number;
  title: string;
  slug: string;
  summary: string;
  content?: string;
  category: string;
  tags: string[];
  author: string;
  cover_image_url: string;
  source_url: string;
  source_type: string;
  published_at: string;
  created_at: string;
  read_time_minutes: number;
}

export interface PaginationInfo {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface ArticlesResponse {
  articles: Article[];
  pagination: PaginationInfo;
  meta: {
    generated_at: string;
  };
}

export interface CategoryInfo {
  name: string;
  count: number;
  slug: string;
}

export interface PriceInfo {
  price: number;
  usd: number;
  change_24h: number;
  usd_24h_change: number;
  market_cap: number;
}

export interface PriceData {
  prices: {
    bitcoin: PriceInfo;
    gold: PriceInfo;
    silver: PriceInfo;
    last_updated: string;
  };
  meta: {
    generated_at: string;
  };
}
