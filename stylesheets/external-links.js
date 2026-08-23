/*
 * 《AI 时代的可靠性架构》 · 外链新标签打开
 *
 * 目标：指向站外的链接（http/https，host 与本站在不同域）在新标签页打开，
 * 并带 rel="noopener noreferrer" 防 tabnabbing / 隐私回传。
 *
 * 为什么按 host 判定、而不是看 href 是否以 "http" 开头：
 * MkDocs Material 开了 navigation.instant，运行时会把它认为的「站内链接」
 * 的 href 属性重写成绝对地址（如 http://host/...），届时 href 属性也以
 * "http" 开头，若只按前缀匹配会把站内导航也误判成外链、点击就开新标签。
 * 用 a.host !== location.host 判定才是稳定的「是否站外」判据。
 *
 * 为什么用 MutationObserver：
 * navigation.instant 页面内瞬时切换不会触发完整 reload，DOMContentLoaded
 * 只跑一次；用 observer 监听新增 <a>，保证瞬时导航后加载的外链也被处理。
 *
 * 作用域：仅站点 HTML 渲染层，不改动 Markdown 源。
 */
(function () {
  'use strict';

  function isExternal(a) {
    // 仅处理 http/https；排除 mailto:/tel:/javascript: 等协议
    if (a.protocol !== 'http:' && a.protocol !== 'https:') return false;
    // host 含端口；不同域（host）才视为外链
    return a.host !== location.host;
  }

  function fixExternalLinks() {
    document.querySelectorAll('a[href]').forEach(function (a) {
      if (!isExternal(a)) return;
      if (!a.hasAttribute('target')) {
        a.setAttribute('target', '_blank');
      }
      a.setAttribute('rel', 'noopener noreferrer');
    });
  }

  var observer = null;

  function start() {
    fixExternalLinks();
    if (document.body && !observer) {
      observer = new MutationObserver(fixExternalLinks);
      observer.observe(document.body, { childList: true, subtree: true });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
