() => {
  // Read-only check before a screenshot: which posts are rendered on the current Threads page and where.
  const posts = [...document.querySelectorAll('div[data-pressable-container="true"]')];
  const items = posts.map((p) => {
    const a = [...p.querySelectorAll('a[href*="/post/"]')].map((x) => x.getAttribute('href'))[0] || '';
    const b = p.getBoundingClientRect();
    return { id: a.replace('/@', '').replace('/post/', ' '), y: Math.round(b.top + scrollY), h: Math.round(b.height) };
  }).filter((i) => i.y < innerHeight + 200);
  let navlog = null;
  try { navlog = JSON.parse(sessionStorage.getItem('__navlog') || '[]').length; } catch (e) { navlog = 'err'; }
  return {
    url: location.href,
    t: new Date().toISOString(),
    ih: innerHeight,
    n: items.length,
    items: items.map((i) => i.id + ' y=' + i.y + ' h=' + i.h),
    dialogs: document.querySelectorAll('[role=dialog]').length,
    navlog,
  };
}
