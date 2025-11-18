// 環境配置
const config = {
  development: {
    apiBaseUrl: "http://localhost:8000",
    timeout: 30000,
  },
  production: {
    apiBaseUrl:
      import.meta.env.VITE_API_BASE_URL ||
      "https://talent-search-api.onrender.com",
    timeout: 30000,
  },
};

// 自動檢測環境
const env =
  import.meta.env.MODE === "production" ? "production" : "development";

console.log(`🌐 環境: ${env}`);
console.log(`🔗 API URL: ${config[env].apiBaseUrl}`);

export default config[env];
