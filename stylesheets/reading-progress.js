/*
 * 《AI 时代的可靠性架构》 · 接续阅读进度保存
 *
 * 目标：让读者记住「上次读到哪一章 + 页面内滚动位置」，下次打开站点时在页底
 * 浮出「继续阅读」提示条，一键跳回并恢复滚动位置。
 *
 * 存储：localStorage（键 reading-progress:v1），单设备、零后端。
 *   —— 进度只存在于本机浏览器；换设备 / 清缓存即丢失（设计使然）。
 *
 * 为什么用 document$：
 *   Material 9.x 在 navigation.instant 下页面切换是 SPA 式（无完整 reload）。
 *   window.document$（Material 全局暴露的 observable，见 bundle 里
 *   window.document$=<obs>）在初始加载与每次导航后都会 emit，是官方推荐的
 *   「内容已就绪」信号，用它做路由检测最干净。若未来版本不再暴露它，回退到
 *   MutationObserver + DOMContentLoaded 检测 location.pathname 变化
 *   （与 external-links.js 同款思路）。
 *
 * 为什么用 sessionStorage 记 banner 关闭状态：
 *   提示条不希望每次翻页都弹；× 关闭后本会话（标签页生命周期）内不再打扰。
 *
 * 作用域：仅站点 HTML 渲染层，不改动 Markdown 源。
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'reading-progress:v1'; // 带版本号，便于以后格式演进
  var DISMISS_KEY = 'rp-banner-dismissed';
  var THROTTLE_MS = 500;   // 滚动节流：最多每 500ms 落盘一次
  var MIN_SCROLL = 80;     // 少于该像素不认为「读过」，避免误存/误恢复

  /* ---------- 存储安全包装（隐私模式 / 禁用存储时不崩） ---------- */
  var store = {
    get: function () {
      try {
        var raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return null;
        var data = JSON.parse(raw);
        return data && typeof data === 'object' ? data : null;
      } catch (e) { return null; }
    },
    set: function (data) {
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(data)); } catch (e) {}
    },
    sessionDismissed: function () {
      try { return sessionStorage.getItem(DISMISS_KEY) === '1'; } catch (e) { return false; }
    },
    markDismissed: function () {
      try { sessionStorage.setItem(DISMISS_KEY, '1'); } catch (e) {}
    }
  };

  var currentPath = location.pathname;
  var currentTitle = '';  // 每页进入时缓存标题；避免瞬时切换时读到下一页的 h1
  var lastY = 0;
  var lastRatio = 0;      // 滚动时即时缓存比例；避免瞬时切换时按新页高度误算
  var throttleTimer = null;
  var restored = false;   // 本次页面访问是否已恢复过，避免重复跳

  /* ---------- 工具 ---------- */
  function scroller() {
    return document.scrollingElement || document.documentElement;
  }

  function getTitle() {
    var h1 = document.querySelector('h1');
    if (h1 && h1.textContent) {
      // 剥掉 Material permalink 附在 h1 尾部的 ¶ 字符
      var t = h1.textContent.replace(/¶\s*$/, '').trim();
      if (t) return t;
    }
    return document.title || '';
  }

  function captureTitle() {
    var t = getTitle();
    if (t) currentTitle = t;
  }

  /* ---------- 保存 ---------- */
  function saveProgress() {
    var y = Math.round(lastY);
    if (y < MIN_SCROLL) return; // 还没真正往下读，保留上次的有效记录
    store.set({
      path: currentPath,
      // 用缓存标题 / 比例，而不是即时读取：页面瞬时切换时 DOM 可能已换成新页，
      // 若按新页 h1 / 高度来存旧页位置，会存出「旧路径 + 新标题 + 错比例」。
      title: currentTitle || getTitle(),
      y: y,
      ratio: lastRatio,
      ts: Date.now()
    });
  }

  function flushPending() {
    if (throttleTimer) { clearTimeout(throttleTimer); throttleTimer = null; }
    saveProgress(); // 把上一页最后一次滚动位置落盘（此时缓存仍是上一页的）
  }

  function onScroll() {
    lastY = window.scrollY || scroller().scrollTop || 0;
    var el = scroller();
    var max = el.scrollHeight - window.innerHeight;
    if (max > 0) {
      lastRatio = Math.min(1, Math.max(0, lastY / max)); // 滚动时即时算，页面必是当前页
    }
    if (throttleTimer) return;
    throttleTimer = setTimeout(function () {
      throttleTimer = null;
      saveProgress();
    }, THROTTLE_MS);
  }

  /* ---------- 恢复 ---------- */
  function scrollTarget(saved) {
    var el = scroller();
    var max = Math.max(0, el.scrollHeight - window.innerHeight);
    var y = saved.y || 0;
    if (y > max) {
      // 内容长度变了（增删改）：退回按比例换算，再截断到可见范围
      y = saved.ratio > 0 ? Math.round(saved.ratio * max) : max;
    }
    return Math.max(0, Math.min(y, max));
  }

  function hasRealAnchor() {
    var h = location.hash;
    if (h.length < 2) return false;
    // 只认「对应到页面真实元素 id」的锚点；Material 偶发的 #1 之类碎片不挡恢复
    try {
      return !!document.getElementById(decodeURIComponent(h.slice(1)));
    } catch (e) { return true; }
  }

  function doRestore(saved) {
    if (hasRealAnchor()) return; // 有真实锚点跳转时尊重锚点，不抢滚动
    var el = scroller();
    var max = Math.max(0, el.scrollHeight - window.innerHeight);
    if (max <= 0) return;
    var y = scrollTarget(saved);
    if (y < MIN_SCROLL) return;
    window.scrollTo(0, y);
    restored = true;
  }

  function restoreScroll(saved) {
    // 多帧 + load 兜底：等 instant 导航换内容 / 图片 / 字体把高度铺满后再落位
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { doRestore(saved); });
    });
    setTimeout(function () { doRestore(saved); }, 250);
    if (document.readyState === 'complete') {
      doRestore(saved);
    } else {
      window.addEventListener('load', function () { doRestore(saved); }, { once: true });
    }
  }

  /* ---------- 提示条 ---------- */
  function showBanner(saved) {
    if (!saved || saved.path === currentPath) return;
    if (store.sessionDismissed()) return;         // 本会话已点过 ×
    if (document.querySelector('.rp-banner')) return; // 已展示，不重复

    var pct = Math.round(Math.min(100, Math.max(0, (saved.ratio || 0) * 100)));
    var title = saved.title || saved.path;

    var banner = document.createElement('div');
    banner.className = 'rp-banner';
    banner.setAttribute('role', 'status');

    var text = document.createElement('span');
    text.className = 'rp-banner__text';
    text.textContent = '继续上次阅读 · ' + title + '（已读 ' + pct + '%）';
    banner.appendChild(text);

    var go = document.createElement('button');
    go.type = 'button';
    go.className = 'rp-banner__btn';
    go.textContent = '继续阅读';
    go.addEventListener('click', function () {
      // 整页跳转：进入 saved.path 后走「同页 → 恢复滚动」分支
      location.href = saved.path;
    });
    banner.appendChild(go);

    var close = document.createElement('button');
    close.type = 'button';
    close.className = 'rp-banner__close';
    close.setAttribute('aria-label', '关闭');
    close.textContent = '×';
    close.addEventListener('click', function () {
      store.markDismissed();
      banner.remove();
    });
    banner.appendChild(close);

    document.body.appendChild(banner);
  }

  /* ---------- 路由切换 ---------- */
  function handleEnter(path) {
    var saved = store.get();
    if (!saved) return;
    if (saved.path === path) {
      // 回到了上次读的那一页：恢复滚动位置（而非弹条）
      if (!restored && saved.y > MIN_SCROLL) restoreScroll(saved);
    } else {
      showBanner(saved);
    }
  }

  function onRouteChange() {
    flushPending();                   // 先存上一页位置（缓存仍是旧页的）
    currentPath = location.pathname;  // 再切当前路径
    captureTitle();                   // document$ 在内容换好后才 emit，此刻拿到的是新页标题
    restored = false;
    handleEnter(currentPath);
  }

  /* ---------- 启动 ---------- */
  function startFallback() {
    // 无 document$ 的兜底：DOMContentLoaded 首判 + MutationObserver 盯 path 变化
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () {
        handleEnter(location.pathname);
      });
    } else {
      handleEnter(location.pathname);
    }
    var last = location.pathname;
    var observer = new MutationObserver(function () {
      if (location.pathname !== last) {
        last = location.pathname;
        onRouteChange();
      }
    });
    if (document.body) observer.observe(document.body, { childList: true, subtree: true });
  }

  function init() {
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('pagehide', flushPending);

    if (window.document$ && typeof window.document$.subscribe === 'function') {
      // Material 官方信号：初始加载 + 每次 instant 导航后都会 emit
      window.document$.subscribe(onRouteChange);
    } else {
      startFallback();
    }

    // 初始页面无论如何都走一次判断（覆盖 document$ 未即时 emit 的边角）
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () {
        captureTitle();
        handleEnter(location.pathname);
      });
    } else {
      captureTitle();
      handleEnter(location.pathname);
    }
  }

  init();
})();
