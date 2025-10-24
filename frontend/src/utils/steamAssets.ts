// 多个CDN源，按优先级排列
const STEAM_CDN_HOSTS = [
  "https://cdn.cloudflare.steamstatic.com/steam/apps",
  "https://steamcdn-a.akamaihd.net/steam/apps", // 备选CDN
  "https://steamcdn-b.akamaihd.net/steam/apps"  // 备选CDN
];

export type SteamAssetVariant = "capsule" | "header" | "library_vertical";

export function getSteamImageUrl(appId: number, variant: SteamAssetVariant = "capsule", hostIndex: number = 0) {
  if (!appId) return "";

  // 获取当前CDN主机，如果超出范围则使用默认的
  const cdnHost = STEAM_CDN_HOSTS[Math.min(hostIndex, STEAM_CDN_HOSTS.length - 1)];

  switch (variant) {
    case "header":
      return `${cdnHost}/${appId}/header.jpg`;
    case "library_vertical":
      return `${cdnHost}/${appId}/library_600x900_2x.jpg`;
    case "capsule":
    default:
      return `${cdnHost}/${appId}/capsule_616x353.jpg`;
  }
}

export function getSteamStoreUrl(appId: number, fallback?: string) {
  if (fallback && fallback.trim()) return fallback;
  if (!appId) return "";
  return `https://store.steampowered.com/app/${appId}`;
}

export function getSteamImageCandidates(appId: number) {
  const variants: SteamAssetVariant[] = ["capsule", "header", "library_vertical"];
  const candidates: string[] = [];
  
  // 为每个variant生成多个CDN源
  for (const variant of variants) {
    for (let hostIndex = 0; hostIndex < STEAM_CDN_HOSTS.length; hostIndex++) {
      const url = getSteamImageUrl(appId, variant, hostIndex);
      if (url) {
        candidates.push(url);
      }
    }
  }
  
  // 去重并返回
  return Array.from(new Set(candidates));
}
