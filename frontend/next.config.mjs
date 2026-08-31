/** @type {import('next').NextConfig} */

// The API is a separate deployment. Proxying it through Next keeps the browser on a
// single origin, so no CORS preflight and no cookie SameSite problems — which matters
// most for the PDF stream the viewer pulls straight from /api/v1/documents/:id/pdf.
// Point this at the deployed API host in production; it defaults to the local worker.
const API_TARGET = process.env.API_PROXY_TARGET ?? "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  // Next generates editor-agent rule files into the project root on `next dev`. They are
  // build output for a tool, not source, and they reappear on every dev boot — so turn the
  // generation off rather than ignoring the files after the fact.
  agentRules: false,
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${API_TARGET}/api/v1/:path*` }];
  },
};
export default nextConfig;
