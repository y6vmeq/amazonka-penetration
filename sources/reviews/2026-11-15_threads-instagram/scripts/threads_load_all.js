() => {
  // Scroll the logged-out Threads page to its end until nothing new loads. Read-only: no clicks.
  const st = window.__loadAll = { running: true, log: [], done: false };
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const count = () => document.querySelectorAll('div[data-pressable-container="true"]').length;
  (async () => {
    let stable = 0, last = '';
    for (let i = 0; i < 60 && stable < 5; i++) {
      window.scrollTo(0, document.documentElement.scrollHeight);
      await sleep(1600);
      const sig = [count(), document.documentElement.scrollHeight, (window.__gql || []).length].join('/');
      st.log.push(sig);
      if (sig === last) stable++; else stable = 0;
      last = sig;
    }
    window.scrollTo(0, 0);
    await sleep(800);
    st.running = false; st.done = true;
  })();
  return 'started';
}
