/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  experimental: {
    serverComponentsExternalPackages: ['@prisma/client'],
  },
};

// Bypass system proxy for local Python API
if (!process.env.NO_PROXY) {
  process.env.NO_PROXY = 'localhost,127.0.0.1,::1';
}
if (!process.env.no_proxy) {
  process.env.no_proxy = 'localhost,127.0.0.1,::1';
}

module.exports = nextConfig;
