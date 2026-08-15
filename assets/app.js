/**
 * Tazkiyah — Modern Learning Platform Client Suite
 * Features:
 * - Theme Management (Light, Dark, Sepia) with persistence
 * - Font Size Scaler with persistence
 * - Global Instant Search (Ctrl+K / Cmd+K) with client-side indexing
 * - One-Click Citation Copying for Hadith & Quran
 * - Reading Progress Tracker (LocalStorage)
 * - English Vocabulary Interactive Tooltips
 * - Active Recall Interactive Self-Check
 */

(function () {
  'use strict';

  // --- Constants & State ---
  const STORAGE_THEME = 'tazkiyah_theme';
  const STORAGE_FONT_SIZE = 'tazkiyah_fontsize';
  const STORAGE_READ_ITEMS = 'tazkiyah_read_items';
  let searchIndex = [];
  let isSearchOpen = false;

  // --- Initialize on DOM Load ---
  document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initFontSize();
    initReadingToolbar();
    initSearch();
    initCopyButtons();
    initReadingProgress();
    initVocabTooltips();
    initSelfCheckQuizzes();
  });

  // --- 1. Theme Management ---
  function initTheme() {
    const savedTheme = localStorage.getItem(STORAGE_THEME) || 'light';
    setTheme(savedTheme);

    const themeButtons = document.querySelectorAll('[data-theme-btn]');
    themeButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const theme = btn.getAttribute('data-theme-btn');
        setTheme(theme);
      });
    });
  }

  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(STORAGE_THEME, theme);
    document.querySelectorAll('[data-theme-btn]').forEach(btn => {
      if (btn.getAttribute('data-theme-btn') === theme) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
  }

  // --- 2. Font Size Scaling ---
  function initFontSize() {
    const savedSize = parseInt(localStorage.getItem(STORAGE_FONT_SIZE) || '100', 10);
    setFontSize(savedSize);

    const incBtn = document.getElementById('btn-font-inc');
    const decBtn = document.getElementById('btn-font-dec');
    const resetBtn = document.getElementById('btn-font-reset');

    if (incBtn) {
      incBtn.addEventListener('click', () => {
        const current = parseInt(localStorage.getItem(STORAGE_FONT_SIZE) || '100', 10);
        if (current < 130) setFontSize(current + 10);
      });
    }
    if (decBtn) {
      decBtn.addEventListener('click', () => {
        const current = parseInt(localStorage.getItem(STORAGE_FONT_SIZE) || '100', 10);
        if (current > 85) setFontSize(current - 10);
      });
    }
    if (resetBtn) {
      resetBtn.addEventListener('click', () => setFontSize(100));
    }
  }

  function setFontSize(percentage) {
    document.documentElement.style.setProperty('--content-font-scale', `${percentage}%`);
    localStorage.setItem(STORAGE_FONT_SIZE, percentage.toString());
    const display = document.getElementById('font-size-display');
    if (display) display.textContent = `${percentage}%`;
  }

  // --- 3. Reading Toolbar & Navigation ---
  function initReadingToolbar() {
    const progressBar = document.getElementById('scroll-progress-bar');
    if (progressBar) {
      window.addEventListener('scroll', () => {
        const docHeight = document.documentElement.scrollHeight - window.innerHeight;
        const scrollPercent = (window.scrollY / (docHeight || 1)) * 100;
        progressBar.style.width = `${Math.min(100, Math.max(0, scrollPercent))}%`;
      }, { passive: true });
    }
  }

  // --- 4. Global Search Modal (Ctrl + K) ---
  function initSearch() {
    const modal = document.getElementById('search-modal');
    const input = document.getElementById('search-input');
    const resultsContainer = document.getElementById('search-results');
    const openBtns = document.querySelectorAll('[data-search-trigger]');
    const closeBtn = document.getElementById('search-close-btn');

    const rootPath = document.body.getAttribute('data-root') || './';
    fetch(rootPath + 'search_index.json')
      .then(res => res.json())
      .then(data => { searchIndex = data; })
      .catch(() => { searchIndex = []; });

    function openSearch() {
      if (!modal) return;
      modal.classList.add('open');
      isSearchOpen = true;
      if (input) {
        input.value = '';
        input.focus();
      }
      renderSearchResults('');
    }

    function closeSearch() {
      if (!modal) return;
      modal.classList.remove('open');
      isSearchOpen = false;
    }

    openBtns.forEach(btn => btn.addEventListener('click', openSearch));
    if (closeBtn) closeBtn.addEventListener('click', closeSearch);

    if (modal) {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) closeSearch();
      });
    }

    window.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        isSearchOpen ? closeSearch() : openSearch();
      } else if (e.key === '/' && !isSearchOpen && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
        e.preventDefault();
        openSearch();
      } else if (e.key === 'Escape' && isSearchOpen) {
        closeSearch();
      }
    });

    if (input) {
      input.addEventListener('input', () => {
        renderSearchResults(input.value.trim());
      });
    }

    function renderSearchResults(query) {
      if (!resultsContainer) return;
      if (!query) {
        resultsContainer.innerHTML = '<div class="search-empty-hint">কী-ওয়ার্ড, সূরার নাম বা হাদিস নম্বর লিখে খুঁজুন... (যেমন: <em>কিবর, বুখারি, সালাত, অহংকার</em>)</div>';
        return;
      }

      const q = query.toLowerCase();
      const matched = searchIndex.filter(item => {
        return item.title.toLowerCase().includes(q) ||
               item.topic.toLowerCase().includes(q) ||
               (item.keywords && item.keywords.some(k => k.toLowerCase().includes(q))) ||
               (item.snippet && item.snippet.toLowerCase().includes(q));
      }).slice(0, 15);

      if (matched.length === 0) {
        resultsContainer.innerHTML = `<div class="search-empty-hint">"<strong>${escapeHtml(query)}</strong>" এর জন্য কোনো ফলাফল পাওয়া যায়নি।</div>`;
        return;
      }

      resultsContainer.innerHTML = matched.map(item => {
        const itemUrl = rootPath + item.url;
        return `
          <a href="${itemUrl}" class="search-result-item">
            <div class="search-result-topic">${escapeHtml(item.topic)}</div>
            <div class="search-result-title">${highlightQuery(item.title, query)}</div>
            ${item.snippet ? `<div class="search-result-snippet">${highlightQuery(item.snippet, query)}</div>` : ''}
          </a>
        `;
      }).join('');
    }
  }

  function highlightQuery(text, query) {
    if (!query) return escapeHtml(text);
    const escapedQ = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${escapedQ})`, 'gi');
    return escapeHtml(text).replace(regex, '<mark>$1</mark>');
  }

  function escapeHtml(s) {
    if (!s) return '';
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // --- 5. One-Click Citation Copying ---
  function initCopyButtons() {
    const quotes = document.querySelectorAll('blockquote, .hadith-card, .ayat-card');
    quotes.forEach((block) => {
      if (block.classList.contains('notice-box')) return;

      const btn = document.createElement('button');
      btn.className = 'copy-citation-btn';
      btn.type = 'button';
      btn.title = 'রেফারেন্সসহ কপি করুন';
      btn.innerHTML = '<span class="icon">📋</span> <span class="label">কপি করুন</span>';

      btn.addEventListener('click', () => {
        const pageTitle = document.querySelector('h1')?.innerText || document.title;
        const text = block.innerText.trim();
        const fullCitation = `${text}\n\n[উৎস: ${pageTitle} — তাযকিয়াহ্]`;

        navigator.clipboard.writeText(fullCitation).then(() => {
          btn.classList.add('copied');
          btn.innerHTML = '<span class="icon">✓</span> <span class="label">কপি হয়েছে!</span>';
          showToast('ক্লিপবোর্ডে কপি করা হয়েছে');
          setTimeout(() => {
            btn.classList.remove('copied');
            btn.innerHTML = '<span class="icon">📋</span> <span class="label">কপি করুন</span>';
          }, 2000);
        }).catch(() => {
          showToast('কপি করতে সমস্যা হয়েছে');
        });
      });

      block.style.position = 'relative';
      block.appendChild(btn);
    });
  }

  function showToast(msg) {
    let toast = document.getElementById('tazkiyah-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'tazkiyah-toast';
      toast.className = 'tazkiyah-toast';
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => {
      toast.classList.remove('show');
    }, 2500);
  }

  // --- 6. Reading Progress Tracker ---
  function initReadingProgress() {
    const pageKey = window.location.pathname;
    const progressToggle = document.getElementById('mark-completed-toggle');

    let readItems = {};
    try {
      readItems = JSON.parse(localStorage.getItem(STORAGE_READ_ITEMS) || '{}');
    } catch (e) {
      readItems = {};
    }

    if (progressToggle) {
      progressToggle.checked = !!readItems[pageKey];
      progressToggle.addEventListener('change', () => {
        if (progressToggle.checked) {
          readItems[pageKey] = Date.now();
          showToast('✓ এই পাঠটি সম্পূর্ণ হিসেবে চিহ্নিত হয়েছে!');
        } else {
          delete readItems[pageKey];
          showToast('চিহ্নিত করা বাতিল হয়েছে');
        }
        localStorage.setItem(STORAGE_READ_ITEMS, JSON.stringify(readItems));
      });
    }

    const docLinks = document.querySelectorAll('.card-list a, .topic-index a');
    docLinks.forEach(link => {
      const href = link.getAttribute('href');
      if (href && !href.startsWith('http') && !href.endsWith('.pdf')) {
        const isRead = Object.keys(readItems).some(k => k.endsWith(href.replace(/^\.\//, '')));
        if (isRead) {
          const badge = document.createElement('span');
          badge.className = 'read-status-badge';
          badge.innerHTML = '✓ পড়া সম্পন্ন';
          link.appendChild(badge);
        }
      }
    });
  }

  // --- 7. English Vocabulary Tooltips ---
  function initVocabTooltips() {
    const content = document.querySelector('.prose-content');
    if (!content) return;

    const regex = /([A-Za-z][A-Za-z0-9'-]+(?:\s+[A-Za-z0-9'-]+)*)\s*\(([\u0980-\u09FF\s,]+)\)/g;

    const walker = document.createTreeWalker(content, NodeFilter.SHOW_TEXT, null, false);
    const textNodes = [];
    while (walker.nextNode()) {
      if (walker.currentNode.parentElement &&
          !['SCRIPT', 'STYLE', 'CODE', 'PRE', 'BUTTON', 'A', 'H1', 'H2', 'H3'].includes(walker.currentNode.parentElement.tagName)) {
        textNodes.push(walker.currentNode);
      }
    }

    textNodes.forEach(node => {
      const text = node.nodeValue;
      if (regex.test(text)) {
        const span = document.createElement('span');
        span.innerHTML = text.replace(regex, (match, enWord, bnMean) => {
          return `<span class="vocab-term" data-tooltip="${bnMean.trim()}">${enWord} <span class="vocab-mean">(${bnMean.trim()})</span></span>`;
        });
        if (node.parentNode) {
          node.parentNode.replaceChild(span, node);
        }
      }
    });
  }

  // --- 8. Interactive Self-Check Quizzes ---
  function initSelfCheckQuizzes() {
    const quizCards = document.querySelectorAll('.self-check-card');
    quizCards.forEach(card => {
      const options = card.querySelectorAll('.quiz-option');
      const feedback = card.querySelector('.quiz-feedback');

      options.forEach(opt => {
        opt.addEventListener('click', () => {
          const isCorrect = opt.getAttribute('data-correct') === 'true';
          options.forEach(o => o.classList.remove('selected', 'correct', 'incorrect'));

          if (isCorrect) {
            opt.classList.add('correct');
            if (feedback) {
              feedback.className = 'quiz-feedback correct';
              feedback.textContent = '✓ সঠিক উত্তর! মাশাআল্লাহ।';
            }
          } else {
            opt.classList.add('incorrect');
            if (feedback) {
              feedback.className = 'quiz-feedback incorrect';
              feedback.textContent = '✕ উত্তরটি সঠিক নয়। পুনরায় চেষ্টা করুন।';
            }
          }
        });
      });
    });
  }

})();
