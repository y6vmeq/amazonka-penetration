() => {
  const st = window.__crawl;
  if (!st) return { none: true };
  return { running: st.running, stopReason: st.stopReason, pages: st.pages.length, posts: Object.keys(st.posts).length,
           queueLeft: st.queue.length, queue: st.queue.map(q => q.replace('https://www.threads.com', '')).slice(0, 60),
           log: (st.log || []).slice(-(window.__logTail || 40)) };
}
