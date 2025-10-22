/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    typedRoutes: true,
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8123/api/:path*',
      },
      {
        source: '/health',
        destination: 'http://127.0.0.1:8123/health',
      },
    ];
  },
};

module.exports = nextConfig;
