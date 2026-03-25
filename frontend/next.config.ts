import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.pexels.com",
        pathname: "/photos/**",
      },
      {
        protocol: "https",
        hostname: "bitcoinmagazine.com",
        pathname: "/wp-content/**",
      },
    ],
  },
  async redirects() {
    return [
      {
        source: "/",
        destination: "/articles",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
