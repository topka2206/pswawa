// IndexNow для Netlify: после каждого успешного продакшен-деплоя сообщает Bing/Яндексу,
// какие страницы изменились. Сравнивает хэши HTML с прошлым деплоем (кэш Netlify),
// поэтому отправляются только новые и изменённые страницы. Ошибки не роняют деплой.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const CACHE_FILE = '.indexnow-hashes.json';

function pageFile(publishDir, url) {
  const p = new URL(url).pathname;
  return path.join(publishDir, p.endsWith('/') ? p + 'index.html' : p);
}

async function run({ constants, utils, inputs, dryRun = false }) {
  const { key, host } = inputs;
  const sitemap = fs.readFileSync(path.join(constants.PUBLISH_DIR, 'sitemap.xml'), 'utf8');
  const urls = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);

  // Хэши страниц сейчас
  const now = {};
  for (const u of urls) {
    const f = pageFile(constants.PUBLISH_DIR, u);
    if (fs.existsSync(f)) now[u] = crypto.createHash('sha1').update(fs.readFileSync(f)).digest('hex');
  }

  // Хэши с прошлого деплоя
  let prev = {};
  if (utils) await utils.cache.restore(CACHE_FILE);
  if (fs.existsSync(CACHE_FILE)) {
    try { prev = JSON.parse(fs.readFileSync(CACHE_FILE, 'utf8')); } catch (e) { prev = {}; }
  }
  const changed = Object.keys(now).filter((u) => prev[u] !== now[u]);
  console.log(`IndexNow: страниц ${urls.length}, изменилось ${changed.length}`);

  if (changed.length && !dryRun) {
    const body = { host, key, keyLocation: `https://${host}/${key}.txt`, urlList: changed.slice(0, 10000) };
    const res = await fetch('https://api.indexnow.org/indexnow', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body: JSON.stringify(body),
    });
    console.log(`IndexNow: ответ ${res.status} (200/202 — принято)`);
    if (res.status >= 300) return now; // не сохраняем хэши — повторим при следующем деплое
  }

  fs.writeFileSync(CACHE_FILE, JSON.stringify(now));
  if (utils) await utils.cache.save(CACHE_FILE);
  return changed;
}

module.exports = {
  async onSuccess({ constants, utils, inputs }) {
    if (process.env.CONTEXT !== 'production') {
      console.log('IndexNow: не продакшен — пропускаю');
      return;
    }
    try {
      await run({ constants, utils, inputs });
    } catch (e) {
      console.log('IndexNow: не удалось отправить —', e.message);
    }
  },
};
