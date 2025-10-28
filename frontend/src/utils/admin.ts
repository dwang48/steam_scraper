export function getAdminUrl(): string {
  const envAdmin = import.meta.env.VITE_ADMIN_URL as string | undefined;
  if (envAdmin && envAdmin.trim()) {
    return normalizeUrl(envAdmin);
  }

  const envApiBase = import.meta.env.VITE_API_BASE as string | undefined;
  if (envApiBase && envApiBase.trim()) {
    try {
      const apiUrl = new URL(envApiBase, window.location.origin);
      apiUrl.pathname = "/admin/";
      apiUrl.search = "";
      apiUrl.hash = "";
      return apiUrl.toString();
    } catch {
      // fall through to window-based guess
    }
  }

  if (typeof window !== "undefined") {
    const origin = window.location.origin;
    try {
      const url = new URL("/admin/", origin);
      url.search = "";
      url.hash = "";
      return url.toString();
    } catch {
      return `${origin.replace(/\/$/, "")}/admin/`;
    }
  }

  return "/admin/";
}

function normalizeUrl(url: string): string {
  try {
    const parsed = new URL(url);
    if (!parsed.pathname.endsWith("/admin/") && parsed.pathname !== "/admin") {
      parsed.pathname = parsed.pathname.replace(/\/?$/, "/admin/");
    } else if (parsed.pathname === "/admin") {
      parsed.pathname = "/admin/";
    }
    parsed.search = "";
    parsed.hash = "";
    return parsed.toString();
  } catch {
    return url.endsWith("/") ? url : `${url}/`;
  }
}
