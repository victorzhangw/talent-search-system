import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import "./assets/css/style.css";
import keepAliveService from "./utils/keepAlive";

const app = createApp(App);

app.use(createPinia());
app.use(router);

app.mount("#app");

// 啟動 Keep-Alive 服務（防止 Render 免費版休眠）
if (import.meta.env.PROD) {
  // 只在生產環境啟用
  keepAliveService.start();
  console.log("🔄 Keep-alive service enabled for production");
}
