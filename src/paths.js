// Vite 会在构建时写入部署前缀，同时支持站点根目录和 GitHub Pages 子目录。
export function assetUrl(path) {
  return `${import.meta.env.BASE_URL}${path.replace(/^\/+/, '')}`;
}
