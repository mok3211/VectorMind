const btn = document.getElementById('btn');
const logEl = document.getElementById('log');

function setLog(text) {
  logEl.style.display = 'block';
  logEl.textContent = text;
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

btn.addEventListener('click', async () => {
  btn.disabled = true;
  setLog('准备中...');
  try {
    const tab = await getActiveTab();
    if (!tab?.url) throw new Error('没有获取到当前页面 URL');
    setLog('发送到本机小助手...');
    const r = await fetch('http://127.0.0.1:18765/api/chrome/collect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: tab.url, title: tab.title || null })
    });
    const text = await r.text();
    if (!r.ok) throw new Error(text);
    const obj = JSON.parse(text);
    if (obj.task_id) {
      setLog('已排队，任务ID：' + obj.task_id + '\n等待结果...');
      // 轮询任务状态
      for (let i = 0; i < 30; i++) {
        await new Promise((r) => setTimeout(r, 1000));
        const rr = await fetch(`http://127.0.0.1:18765/api/tasks/${obj.task_id}`);
        const jj = await rr.json();
        if (jj.status === 'success') {
          setLog('成功：\n' + JSON.stringify(jj.result, null, 2));
          return;
        }
        if (jj.status === 'failed') {
          setLog('失败：\n' + (jj.error || 'unknown'));
          return;
        }
      }
      setLog('超时：任务仍在执行，请稍后再查任务状态：' + obj.task_id);
      return;
    }
    setLog('成功：\n' + text);
  } catch (e) {
    setLog('失败：' + (e?.message || String(e)));
  } finally {
    btn.disabled = false;
  }
});
