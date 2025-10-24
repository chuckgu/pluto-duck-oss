/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'export',
  experimental: {
    typedRoutes: true,
  },
  // Rewrites don't work with 'output: export', so we set NEXT_PUBLIC_BACKEND_URL instead
  env: {
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8123',
  },
};

module.exports = nextConfig;
