const API_HEALTH = "https://swipex-jrem.onrender.com/health";

export default {
  async fetch(request, env) {
    return env.ASSETS.fetch(request);
  },
  async scheduled(event, env, ctx) {
    ctx.waitUntil(fetch(API_HEALTH).catch(() => {}));
  },
};