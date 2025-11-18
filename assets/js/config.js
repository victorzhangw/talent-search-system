// 環境配置
const config = {
  development: {
    apiBaseUrl: "http://localhost:8000",
    timeout: 30000,
  },
  production: {
    apiBaseUrl: "https://api.yourdomain.com",
    timeout: 30000,
  },
};

// 自動檢測環境
const env =
  window.location.hostname === "localhost" ? "development" : "production";

export default config[env];
