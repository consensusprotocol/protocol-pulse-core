# Protocol Pulse

## Overview
Protocol Pulse is a Web3 and cryptocurrency news platform that leverages AI to generate high-quality articles, podcasts, and other content. It combines automated content generation from Reddit trends and other social media with manual editorial oversight. The platform aims to be a leading modern media network for blockchain, cryptocurrency, and decentralized web coverage, democratizing access to Web3 journalism through AI-powered insights and expert analysis.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Design Principles
Protocol Pulse is built on a Flask web application with a responsive Bootstrap 5 frontend. It prioritizes AI-driven content generation, sophisticated content management, and real-time data integration. The system emphasizes SEO, user experience (UI/UX) with interactive elements, and a modular design using Jinja2 templates.

### Key Features
- **AI Content Generation**: Utilizes multiple AI providers (OpenAI, Anthropic) with customizable templates for various content types, including articles and podcasts. Automated generation is triggered by trending topics from social media.
- **Multimodal Content Engine**: Automates the creation of comprehensive content bundles from videos (e.g., YouTube), generating articles, podcasts, and social media clips with AI-generated scripts and video wrappers.
- **Content Management System (CMS)**: Provides full CRUD operations for articles (with SEO and categorization), podcast management, and an administrative dashboard for content and AI generation workflows. Articles enforce a 5-section structure (TL;DR, The Report, The Bitcoin Lens, Transactor Intelligence, Sources).
- **Social Media Aggregation**: Extracts trending topics from cryptocurrency and blockchain subreddits, X (Twitter) handles, and YouTube channels. It also monitors X Spaces, transcribing them to generate recap articles with speaker identification and sentiment analysis.
- **Verified Signal Collection System**: Gathers and verifies signals from X, Nostr, and Stacker News, storing authentic URLs, engagement metrics, and author attribution. It prioritizes signals from key Bitcoin influencers and integrates these signals into daily intelligence briefings.
- **Interactive UI/UX Elements**: Features include a Live Settlement Terminal for real-time blockchain data, an interactive Sovereign Merchant Map using Leaflet.js, a Satoshi Clock, and a Gas Alert HUD.
- **Decentralized Social Aggregator (Value Stream)**: A platform where content ranking is based on economic signals (sats) rather than engagement farming, supporting cross-platform content curation and a Web of Trust for curators.
- **Affiliate Education Article System**: An automated system generating problem-first educational content that subtly recommends relevant affiliate products, incorporating a "Grok Gate" for AI fact-checking.

### Technical Implementation
- **Backend**: Flask with SQLAlchemy ORM, application factory pattern.
- **Frontend**: Bootstrap 5, Jinja2, custom CSS for dark theme, JavaScript for interactivity.
- **Database**: SQLite for development, configurable for production.
- **SEO**: Meta tags, structured data (Schema.org), semantic HTML.
- **Image Handling**: Dynamic header image generation with cache-busting and fallback mechanisms.

## External Dependencies

- **AI/ML**: OpenAI API (GPT-5, GPT-4o), Anthropic API (Claude Sonnet-4), AssemblyAI (transcription, analysis), Gemini Imagen 3 (image generation), ElevenLabs API (voice synthesis).
- **Social Media/Data**: Reddit API, YouTube Data API, yt-dlp, youtube-transcript-api, Tweepy (X/Twitter).
- **Blockchain/Crypto Data**: Mempool.space API, BTC Map API.
- **CRM**: HighLevel API (GHL).
- **Affiliate/E-commerce**: Amazon Product Advertising API (PA-API).
- **Web3 Integration**: WebLN (Lightning Network tipping).
- **Development/Utility**: Bootstrap CDN, Font Awesome, SQLite, Flask Extensions (SQLAlchemy, Flask-Login), python-telegram-bot, httpx, FFmpeg.