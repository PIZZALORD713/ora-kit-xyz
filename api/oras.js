const SUGARTOWN_ORAS_CONTRACT = "0xd564c25b760cb278a55bdd98831f4ff4b6c97b38";
const PIZZALORD_WALLET = "0x28af3356C6aaF449d20C59d2531941DDfB94d713";

function getApiKey() {
  const apiKey =
    process.env.MORALIS_API_KEY ||
    process.env.MORALIS_WEB3_API_KEY ||
    process.env.MORALIS_API;

  if (!apiKey) {
    throw new Error("Missing Moralis API key.");
  }
  return apiKey;
}

async function requestJson(url, apiKey) {
  const response = await fetch(url, {
    headers: {
      accept: "application/json",
      "user-agent": "orakit-preview/0.1",
      "X-API-Key": apiKey,
    },
  });

  const body = await response.text();
  if (!response.ok) {
    throw new Error(`Moralis HTTP ${response.status}: ${body.slice(0, 300)}`);
  }
  return JSON.parse(body);
}

async function requestPublicJson(url) {
  const response = await fetch(url, {
    headers: {
      accept: "application/json",
      "user-agent": "orakit-preview/0.1",
    },
  });

  const body = await response.text();
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${body.slice(0, 300)}`);
  }
  return JSON.parse(body);
}

function parseMetadata(value) {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim()) {
    try {
      const parsed = JSON.parse(value);
      return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
    } catch {
      return {};
    }
  }
  return {};
}

function normalizeImageUri(value) {
  if (!value) return "";
  if (value.startsWith("ipfs://")) {
    return `https://ipfs.io/ipfs/${value.slice("ipfs://".length)}`;
  }
  return value;
}

function normalizeTraits(metadata) {
  const raw = metadata.attributes || metadata.traits || [];
  const traits = {};
  if (!Array.isArray(raw)) return traits;

  for (const item of raw) {
    if (!item || typeof item !== "object") continue;
    const name = item.trait_type || item.name || item.key;
    const value = item.value;
    if (name && value !== undefined && value !== null) {
      traits[String(name)] = String(value);
    }
  }
  return traits;
}

async function resolveWallet(value, apiKey) {
  const query = value.trim();
  if (!query) {
    throw new Error("Wallet address or ENS name is required.");
  }
  if (query.toLowerCase() === "pizzalord.eth") {
    return [PIZZALORD_WALLET, query];
  }
  if (query.toLowerCase().startsWith("0x") && query.length === 42) {
    return [query, null];
  }

  const encoded = encodeURIComponent(query);
  const resolverErrors = [];

  try {
    const data = await requestJson(`https://deep-index.moralis.io/api/v2.2/resolve/ens/${encoded}`, apiKey);
    const address = data.address;
    if (typeof address === "string" && address.startsWith("0x")) {
      return [address, query];
    }
    resolverErrors.push("Moralis returned no address");
  } catch (error) {
    resolverErrors.push(`Moralis: ${error.message}`);
  }

  try {
    const data = await requestPublicJson(`https://api.ensideas.com/ens/resolve/${encoded}`);
    const address = data.address;
    if (typeof address === "string" && address.startsWith("0x")) {
      return [address, query];
    }
    resolverErrors.push("ENSIdeas returned no address");
  } catch (error) {
    resolverErrors.push(`ENSIdeas: ${error.message}`);
  }

  throw new Error(`Could not resolve "${query}" to an EVM wallet. ${resolverErrors.join("; ")}`);
}

async function fetchWalletNfts(wallet, apiKey) {
  const results = [];
  let cursor = "";

  for (let pageIndex = 0; pageIndex < 10; pageIndex += 1) {
    const params = new URLSearchParams({
      chain: "eth",
      format: "decimal",
      normalizeMetadata: "true",
      media_items: "false",
      limit: "100",
    });
    if (cursor) params.set("cursor", cursor);

    const data = await requestJson(
      `https://deep-index.moralis.io/api/v2.2/${encodeURIComponent(wallet)}/nft?${params}`,
      apiKey,
    );
    if (Array.isArray(data.result)) {
      results.push(...data.result.filter((item) => item && typeof item === "object"));
    }
    cursor = String(data.cursor || "");
    if (!cursor) break;
  }

  return results;
}

function nftToOra(item) {
  const contract = String(item.token_address || "").toLowerCase();
  if (contract !== SUGARTOWN_ORAS_CONTRACT) return null;

  const tokenId = String(item.token_id || "");
  const normalized = parseMetadata(item.normalized_metadata);
  const raw = parseMetadata(item.metadata);
  const metadata = { ...raw, ...normalized };
  const name = String(metadata.name || item.name || `Sugartown Oras #${tokenId}`);

  const media = item.media && typeof item.media === "object" ? item.media : {};
  const mediaCollection =
    media.media_collection && typeof media.media_collection === "object" ? media.media_collection : {};
  const highMedia = mediaCollection.high && typeof mediaCollection.high === "object" ? mediaCollection.high : {};
  const image =
    metadata.image ||
    metadata.image_url ||
    highMedia.url ||
    `https://nfts.visitsugartown.com/nfts/oras/${tokenId}.png`;

  return {
    name,
    oraNumber: tokenId,
    image: normalizeImageUri(String(image)),
    traits: normalizeTraits(metadata),
    openseaUrl: `https://opensea.io/assets/ethereum/${SUGARTOWN_ORAS_CONTRACT}/${tokenId}`,
    contractAddress: SUGARTOWN_ORAS_CONTRACT,
    previewSource: "metadata",
  };
}

async function lookupOras(walletQuery) {
  const apiKey = getApiKey();
  const [wallet, resolvedFrom] = await resolveWallet(walletQuery, apiKey);
  const nfts = await fetchWalletNfts(wallet, apiKey);
  const oras = nfts.map(nftToOra).filter(Boolean);
  oras.sort((a, b) => {
    const left = Number.parseInt(a.oraNumber, 10);
    const right = Number.parseInt(b.oraNumber, 10);
    if (Number.isNaN(left) || Number.isNaN(right)) {
      return a.oraNumber.localeCompare(b.oraNumber);
    }
    return left - right;
  });

  return {
    success: true,
    wallet,
    resolvedFrom,
    totalOras: oras.length,
    oras,
    source: "moralis",
    collection: {
      name: "Sugartown Oras",
      chain: "ethereum",
      contractAddress: SUGARTOWN_ORAS_CONTRACT,
    },
  };
}

module.exports = async function handler(request, response) {
  const url = new URL(request.url, "https://ora-kit-xyz.vercel.app");
  const wallet = url.searchParams.get("wallet") || "";

  response.setHeader("Cache-Control", "no-store");
  response.setHeader("Content-Type", "application/json");

  try {
    const payload = await lookupOras(wallet);
    response.status(200).json(payload);
  } catch (error) {
    response.status(500).json({ success: false, error: error.message });
  }
};
