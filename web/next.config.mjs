/** @type {import('next').NextConfig} */
const nextConfig = {
  // Resume uploads pass through the server route; allow a small body.
  experimental: {
    serverActions: { bodySizeLimit: "5mb" },
  },
};

export default nextConfig;
