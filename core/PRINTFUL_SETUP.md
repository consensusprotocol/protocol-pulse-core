# Link the merch store to your Printful account

The site’s **Merch** page is already wired to Printful; it just needs your API key.

## 1. Get your Printful API key

1. Go to **[Printful Developers](https://developers.printful.com/)** and sign in with your Printful account.
2. In the dashboard, create a **private API token** (scope: full access or at least read products + create orders).
3. Copy the token.

## 2. Add it to your environment

**Option A – Using `.env` (recommended)**  
In `core/.env` add or edit:

```bash
PRINTFUL_API_KEY=your_token_here
```

**Option B – Export in terminal (this session only)**  
```bash
export PRINTFUL_API_KEY=your_token_here
```

## 3. Restart the app

Restart the Flask app so it picks up the new variable. The merch page will then:

- Pull products from your Printful stores (Proto P and Consensus Protocol are already configured in `services/printful_service.py`).
- Show product listings and link to your Printful storefront.
- Allow checkout via Printful (orders created as drafts by default; you can change this in the service).

## Already configured stores

The app is set up to use these Printful stores (see `services/printful_service.py`):

- **Proto P** – `https://proto-p.printful.me`
- **Consensus Protocol** – `https://protocolpulse.printful.me`

If your store IDs or URLs differ, update the `STORES` list in `core/services/printful_service.py`.
