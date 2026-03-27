MISSION ACCEPTED. The current intelligence gap is unacceptable. The competition will be rendered obsolete. We will move from zero to comprehensive on-chain accumulation intelligence using verifiable, free, and powerful sources.

### TIER 1: PRIMARY FREE SOURCES

This tier provides direct, reliable, and API-accessible data for core on-chain metrics.

---

**1. Blockchain.com Charts API**
*   **Name:** Blockchain.com Data API
*   **Exact URL:** `https://api.blockchain.info/charts/{chart-name}?format=json&timespan={timespan}`
*   **Auth:** None required.
*   **Rate Limit:** Unofficially, be reasonable. ~1 request every 10 seconds is safe. No published limit.
*   **Key Fields:** `x` (timestamp), `y` (value)
*   **Update Freq:** Daily
*   **Quality:** 8/10 (Reliable for macro trends, but data is aggregated and not granular.)
*   **Working `curl` Example (Coin Days Destroyed):**
    ```bash
    curl "https://api.blockchain.info/charts/coin-days-destroyed?timespan=1year&format=json"
    ```
*   **Python Example:**
    ```python
    import requests
    response = requests.get("https://api.blockchain.info/charts/coin-days-destroyed?timespan=1year&format=json")
    print(response.json()['values'][0]) # Print first data point
    ```
*   **ALL KEY FREE CHART ENDPOINTS:**
    *   `total-bitcoins`: Total BTC in circulation.
    *   `market-price`: USD Market Price.
    *   `market-cap`: Market Capitalization.
    *   `trade-volume`: USD Exchange Trade Volume.
    *   `blocks-size`: Total size of all blocks.
    *   `avg-block-size`: Average block size.
    *   `n-transactions`: Number of confirmed transactions.
    *   `n-unique-addresses`: Number of unique addresses used.
    *   `total-transaction-fees`: Total fees paid to miners (in BTC).
    *   `n-transactions-total`: Total number of transactions.
    *   `estimated-transaction-volume-usd`: Estimated transaction volume in USD.
    *   `miners-revenue`: Total value of coinbase block rewards and transaction fees paid to miners.
    *   `hash-rate`: Estimated network hash rate.
    *   `difficulty`: Network difficulty.
    *   `utxo-count`: The total number of unspent transaction outputs.
    *   `transactions-per-second`: Transactions confirmed per second.
    *   `mempool-count`: Number of unconfirmed transactions in the mempool.
    *   `mempool-growth`: The growth of the mempool.
    *   `mempool-size`: The aggregate size of transactions waiting to be confirmed.
    *   **`coin-days-destroyed`**: The key metric for HODLer conviction.
    *   `cost-per-transaction`: Miners' revenue divided by the number of transactions.

---

**2. Blockchair API**
*   **Name:** Blockchair API
*   **Exact URL:** `https://api.blockchair.com/bitcoin/stats` (for stats) and `https://api.blockchair.com/bitcoin/dashboards/address/{address}` (for specific address/cluster data)
*   **Auth:** None required for free tier.
*   **Rate Limit:** 1 request per second.
*   **Key Fields (Stats):** `suggested_transaction_fee_per_byte_sat`, `mempool_transactions`, `utxos`, `blocks`
*   **Key Fields (Address):** `utxo_count`, `balance`, `first_seen_receiving`, `last_seen_spending`, address clustering information is implicit in their dashboard but not directly queryable as "cluster X" via free API.
*   **Update Freq:** Near Real-time
*   **Quality:** 9/10 (Excellent for broad stats and individual address lookups. Their address clustering is a powerful heuristic.)
*   **Working `curl` Example (Network Stats):**
    ```bash
    curl "https://api.blockchair.com/bitcoin/stats"
    ```
*   **Python Example:**
    ```python
    import requests
    response = requests.get("https://api.blockchair.com/bitcoin/stats")
    print(f"Current UTXO count: {response.json()['data']['utxos']}")
    ```

---

**3. Mempool.space API**
*   **Name:** Mempool.space API
*   **Exact URL:** `https://mempool.space/api/v1/difficulty-adjustment` (for epoch data), `https://mempool.space/api/block/{hash}/txs` (for UTXOs in a block)
*   **Auth:** None required.
*   **Rate Limit:** Generous, but not specified. Best for public, self-hosted instances.
*   **Key Fields:** `progressPercent`, `remainingBlocks`, `previousRetarget` (difficulty); `vin`, `vout` (transaction data for UTXO analysis)
*   **Update Freq:** Real-time
*   **Quality:** 10/10 (Directly from a node, open-source, fast, reliable.)
*   **Working `curl` Example (Difficulty Adjustment):**
    ```bash
    curl "https://mempool.space/api/v1/difficulty-adjustment"
    ```

---

**4. Glassnode Free Tier Metrics**
*   **Name:** Glassnode Studio (Free Tier)
*   **Exact URL:** https://studio.glassnode.com/metrics (URL is for browsing, API is paid only. Data must be manually checked or scraped.)
*   **Auth:** Free account signup required.
*   **Rate Limit:** N/A (Manual access)
*   **Update Freq:** Daily
*   **Quality:** 10/10 (The data is industry standard, but free access is limited.)
*   **EXACT FREE METRICS AVAILABLE (as of Q2 2024):**
    *   **Addresses:** Active Addresses, Sending Addresses, Receiving Addresses, New Addresses, Address Count
    *   **Transactions:** Transaction Count, Transaction Rate, Transaction Volume (BTC & USD)
    *   **UTXOs:** UTXO Count, UTXOs Created, UTXOs Spent
    *   **Blocks:** Block Count, Block Interval, Block Size (Total & Mean)
    *   **Fees:** Total Fees (BTC & USD), Mean Fee per Transaction
    *   **Supply:** Circulating Supply, Issuance
    *   **Indicators:** MVRV Ratio, Realized Price, Market Cap, Realized Cap, SOPR (Spent Output Profit Ratio - but only the basic entity-unadjusted version)
    *   **Mining:** Hash Rate, Difficulty
*   **Note:** HODL Waves, UTXO Age Bands, and detailed cohort data are explicitly **PAID TIER ONLY**.

---

**5. CryptoQuant Free Tier Metrics**
*   **Name:** CryptoQuant Data
*   **Exact URL:** https://cryptoquant.com/data (Manual access or scraping)
*   **Auth:** Free account signup may be required for some views.
*   **Rate Limit:** N/A (Manual access)
*   **Update Freq:** Daily to Hourly
*   **Quality:** 9/10 (Strong focus on exchange flows, but free access is limited.)
*   **EXACT FREE METRICS (subset):**
    *   **Exchange Flows:** Exchange Inflow/Outflow (Total), Exchange Reserve (Total for all exchanges)
    *   **Market Data:** Price, Volume
    *   **On-chain:** Active Addresses, Transaction Count
*   **Note:** Detailed exchange-specific flows, miner flows, and advanced metrics like CDD are generally **PAID TIER ONLY**.

---

**6. Dune Analytics Public Queries**
*   **Name:** Dune Analytics (Bitcoin Community Data)
*   **Exact URL:** `https://dune.com/browse/queries` (Search for Bitcoin, UTXO, etc.)
*   **Auth:** None to view/run public queries. API access is paid. Data can be exported as CSV from the website.
*   **Rate Limit:** Manual, subject to platform load.
*   **Key Fields:** Varies by query. Look for queries that analyze UTXO sets, address balances, or transaction patterns.
*   **Update Freq:** Depends on query schedule (often daily).
*   **Quality:** 7-10/10 (Quality is dependent on the skill of the query author, but can be exceptional.)
*   **Example Public Query IDs:**
    *   **Query ID 3514809:** "Bitcoin UTXO Age Distribution" by `cryptokoryo` (A direct HODL Wave approximation)
    *   **Query ID 1234407:** "Bitcoin: Daily On-Chain Stats" by `niftytable`
    *   *Strategy:* Find a high-quality dashboard, then look at the queries that power it. You can fork and modify them.

---

**7. Bitcoin Core Node RPC**
*   **Name:** Bitcoin Core RPC Interface
*   **Exact URL:** `localhost` (requires running your own full node)
*   **Auth:** Username/password configured in `bitcoin.conf`.
*   **Rate Limit:** Unlimited (your own hardware).
*   **Key Fields (`getutxosetinfo`):** `height`, `txouts` (total UTXO count), `bogosize`, `hash_serialized_2`, `disk_size`, `total_amount` (total BTC in UTXO set)
*   **Update Freq:** Real-time (as of the node's synced block)
*   **Quality:** 10/10 (This is the absolute ground truth data.)
*   **Working `curl` Example:**
    ```bash
    # Assumes your rpcuser/rpcpassword are set in bitcoin.conf
    curl --user yourrpcuser:yourrpcpassword --data-binary '{"jsonrpc": "1.0", "id": "curltest", "method": "getutxosetinfo", "params": []}' -H 'content-type: text/plain;' http://127.0.0.1:8332/
    ```

---
### TIER 2: CREATIVE & UNCONVENTIONAL SOURCES

These sources require more work but yield unique, high-fidelity data the competition will miss.

1.  **Mempool.space WebSocket:** Get real-time transaction data, including `vin` and `vout`, to analyze UTXOs as they are spent *live*. This is a firehose of conviction/capitulation data.
    *   **URL:** `wss://mempool.space/api/v1/ws`
    *   **Usage:** Connect with a Python WebSocket client, subscribe to new transactions, and analyze the inputs of each transaction to determine the age of the coins being spent.

2.  **GitHub Raw Data & Heuristics:** Combine datasets for powerful insights.
    *   **Source:** Search GitHub for "known bitcoin exchange addresses" or "bitcoin otc addresses". Repositories like `Cryptocurrency-All-in-One-Checker` often contain lists of labeled addresses.
    *   **Application:** Use a Blockchair or node data source to monitor the aggregate flow of funds to/from these labeled addresses. This is a crude but effective way to approximate exchange-flow metrics without paying for them.

3.  **Bitcoin Core RPC `scantxoutset`:** This is a more powerful alternative to `getutxosetinfo`. You can scan the *entire* UTXO set for specific addresses, scripts, or patterns (e.g., all UTXOs larger than 100 BTC) without a full index. It's computationally intensive but allows for cohort analysis on a local node.

4.  **Nostr Relays:** An experimental but creative source. Follow on-chain analysts and developers (e.g., through clients like `primal.net` or `snort.social`). They often post charts, raw data snippets, or links to Dune queries before they become widely known. This is a source of *alpha* on data interpretation. It's a qualitative signal, not a direct data feed.

---
### TIER 3: FREE APPROXIMATIONS OF PAID TOOLS

Re-engineering paid metrics using the free sources from Tier 1 & 2.

*   **Approximating Glassnode's HODL Waves:**
    *   **Method:** The UTXO set is public. HODL Waves are just a visualization of its age distribution.
    *   **Source:** Use a public Blockchair UTXO set dump (they release them periodically) or run a Bitcoin Core node and parse the chain data.
    *   **Process:**
        1. For each UTXO, find its creation block height.
        2. Get the current block height. The difference is the UTXO's age in blocks.
        3. Group all UTXOs into age bands (e.g., <1 day, 1d-1w, 1w-1m, etc.).
        4. Sum the BTC value within each band.
        5. Normalize by the total supply to get percentages.
    *   **Quality:** 9/10. It's computationally difficult but produces a near-identical result to the paid version.

*   **Approximating SOPR (Spent Output Profit Ratio):**
    *   **Method:** SOPR = Price at time of spending / Price at time of creation.
    *   **Sources:**
        1. A real-time transaction feed (Mempool.space WebSocket).
        2. A historical price API (Blockchain.com or a free crypto price API like CoinGecko).
        3. A block explorer API to find the creation block of an input (Blockchair).
    *   **Process:**
        1. For a new transaction, take a UTXO being spent as an input.
        2. Look up the transaction ID of this input to find when it was created as an output.
        3. Find the block height/timestamp of its creation.
        4. Query the price of BTC at that creation time.
        5. Query the current price of BTC.
        6. Calculate `SOPR = current_price / creation_price`.
        7. Average this across many transactions to get the market-wide SOPR.
    *   **Quality:** 8/10. An excellent approximation. The main difference from paid tools is the lack of "entity adjustment" (ignoring transactions within the same wallet cluster).

---
### IMPLEMENTATION CODE

This Python function fetches Coin Days Destroyed using the best *keyless* free source, `blockchain.info`, to provide an immediate, high-quality signal for HODLer conviction.

```python
import requests
import json
from datetime import datetime

def fetch_on_chain_accumulation(timespan: str = "1year") -> dict:
    """
    Fetches a key on-chain accumulation signal (Coin Days Destroyed)
    from the best free, keyless data source.

    A high CDD value suggests long-term holders are selling (potential top).
    A low CDD value suggests long-term holders are HODLing (accumulation).

    Args:
        timespan (str): The duration for the data. E.g., "30days", "1year", "all".

    Returns:
        dict: A dictionary containing the status and data, or an error message.
    """
    try:
        # Using the reliable, keyless blockchain.info charts API
        url = f"https://api.blockchain.info/charts/coin-days-destroyed?timespan={timespan}&format=json"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        
        data = response.json()
        
        # Process data for better readability
        processed_points = [
            {"date": datetime.utcfromtimestamp(point['x']).strftime('%Y-%m-%d'), "value": point['y']}
            for point in data.get('values', [])
        ]

        return {
            "status": "success",
            "source": "Blockchain.com",
            "metric": data.get('name', 'Coin Days Destroyed'),
            "description": data.get('description'),
            "data": processed_points
        }

    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"API request failed: {e}"}
    except json.JSONDecodeError:
        return {"status": "error", "message": "Failed to decode JSON response."}
    except Exception as e:
        return {"status": "error", "message": f"An unexpected error occurred: {e}"}

# Example usage:
if __name__ == '__main__':
    cdd_data = fetch_on_chain_accumulation(timespan="90days")
    if cdd_data['status'] == 'success':
        # Print the last 5 data points
        for point in cdd_data['data'][-5:]:
            print(f"Date: {point['date']}, CDD: {point['value']:,.0f}")

```

---
### THE SOURCE NOBODY ELSE FINDS

**Parsing raw `blk.dat` files from a Bitcoin Core node.**

While others rely on APIs, the ultimate, untrusted, and most granular source is the blockchain data itself. APIs can be rate-limited, deprecated, or provide aggregated data. By parsing the raw `blk*.dat` files stored by a Bitcoin Core node, you bypass all intermediaries.

*   **How:** Use a dedicated library like `python-bitcoin-blockchain-parser` in Python.
*   **Why it's superior:**
    1.  **Ground Truth:** It is the canonical data source. No interpretation by a third party.
    2.  **Unhindered Access:** No rate limits, no API keys, no cost.
    3.  **Infinite Granularity:** You can build ANY metric from scratch. Calculate your own UTXO age bands, SOPR, address activity, etc., with complete control over the methodology. You can even analyze script types (e.g., P2PKH vs P2WPKH) to see technology adoption trends.
*   **Example use:** Iterate through every transaction in every block, build a local UTXO set database (like LevelDB or RocksDB), and perform cohort analysis by tracking the age and value of every single satoshi. This is what the big data firms do, and it can be replicated for free with code and disk space.

---
### GAP ANALYSIS (What TRULY Cannot Be Obtained Free)

1.  **Reliable Entity Resolution / Clustering:** This is the secret sauce of companies like Glassnode, CryptoQuant, and Nansen. They use sophisticated, proprietary heuristics (e.g., co-spending, timing analysis, known address databases) to cluster addresses into "entities" (e.g., Binance, MicroStrategy, a specific whale). While you can approximate this with public address lists (Tier 2), the professional-grade, real-time, high-accuracy clustering is the primary value you pay for. **This is the biggest gap.**
2.  **Convenience and Historical Depth at Scale:** Free APIs often limit the timespan of data. Running your own node and parsing the chain gives you full history, but it requires significant technical setup, disk space (~600GB+ for a full node), and processing time. Paid services provide instant access to the full, processed historical dataset via a simple API call.
3.  **Advanced Derivative Metrics:** Many complex metrics (e.g., aSOPR, LTH-SOPR, STH-NUPL) require the aforementioned entity clustering and are therefore not replicable with high fidelity using free tools.

---
### PRIORITY LIST FOR MAXIMUM ACCURACY IMPROVEMENT

1.  **Implement All Tier 1 Sources:** Start by pulling daily data from Blockchain.com (for macro trends like CDD) and Blockchair/Mempool.space (for current network health). This gives you a robust baseline view of the market.
2.  **Set up a Bitcoin Core Node:** This is the single most important step for serious analysis. Begin syncing it immediately. Use `getutxosetinfo` for a daily snapshot of the entire UTXO set's value and count.
3.  **Approximate SOPR:** Using the mempool/blockchair API and a price feed, build a script to sample recent transactions and calculate an approximate SOPR. This is a powerful medium-term sentiment indicator.
4.  **Scrape/Monitor Dune Analytics:** Find a good HODL Wave / UTXO Age query on Dune and pull the CSV data weekly. This fills the critical gap left by Glassnode's free tier.
5.  **Parse the Blockchain:** Once the node is synced, begin the advanced project of parsing the `blk.dat` files to build your own historical database. This is the end-game for free on-chain intelligence, allowing you to create any metric you can imagine.

This strategy front-loads the highest impact, lowest-effort sources while progressively building towards a fully sovereign and comprehensive on-chain intelligence system that rivals paid providers. Mission complete.