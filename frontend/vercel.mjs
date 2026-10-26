// Vercelでのみ評価する。DB接続情報をブラウザービルドへ渡さない。
const backend = process.env.CLOUD_RUN_API_ORIGIN;
if (!backend)
  throw new Error("CLOUD_RUN_API_ORIGIN is required for deployment");
const parsed = new URL(backend);
if (
  parsed.protocol !== "https:" ||
  parsed.origin !== backend ||
  !parsed.hostname.endsWith(".run.app")
) {
  throw new Error("CLOUD_RUN_API_ORIGIN must be an HTTPS Cloud Run origin");
}

export const config = {
  framework: "vite",
  buildCommand: "npm run build",
  installCommand: "npm ci",
  outputDirectory: "dist",
  // 本番公開はGitHub Actionsの承認ゲート経由だけに限定する。
  git: { deploymentEnabled: false },
  rewrites: [
    { source: "/api/:path*", destination: `${backend}/api/:path*` },
    { source: "/((?!api(?:/|$)|assets/).*)", destination: "/index.html" },
  ],
  headers: [
    {
      source: "/api/:path*",
      headers: [{ key: "Cache-Control", value: "private, no-store" }],
    },
    {
      source: "/(.*)",
      headers: [
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        { key: "X-Frame-Options", value: "DENY" },
        {
          key: "Content-Security-Policy",
          value:
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        },
      ],
    },
  ],
};
