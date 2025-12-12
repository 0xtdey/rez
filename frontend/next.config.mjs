/** @type {import('next').NextConfig} */
const nextConfig = {
    // Transpile Privy and related packages for SSR compatibility
    transpilePackages: [
        "@privy-io/react-auth",
        "@walletconnect/ethereum-provider",
        "@walletconnect/modal",
    ],

    // Webpack config for Privy SSR compatibility
    webpack: (config, { isServer }) => {
        if (!isServer) {
            config.resolve.fallback = {
                ...config.resolve.fallback,
                fs: false,
                net: false,
                tls: false,
                crypto: false,
            };
        }

        config.externals = [
            ...(config.externals || []),
            "pino-pretty",
            "lokijs",
            "encoding",
        ];

        return config;
    },
};

export default nextConfig;
