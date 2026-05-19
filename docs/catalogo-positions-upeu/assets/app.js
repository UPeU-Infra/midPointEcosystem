/**
 * Catálogo de Positions UPeU — app.js
 * TOC activo al scroll, filtro de tabla, hamburger menu, smooth scroll
 */

(function () {
  'use strict';

  /* ============================================================
     TOC — resaltar entrada activa al hacer scroll
     ============================================================ */
  function initTOC() {
    const links = document.querySelectorAll('#toc-list a[href^="#"]');
    const sections = [];

    links.forEach(function (a) {
      const id = a.getAttribute('href').slice(1);
      const el = document.getElementById(id);
      if (el) sections.push({ id, el, a });
    });

    function onScroll() {
      const scrollY = window.scrollY + 120; // offset header + breadcrumb
      let current = sections[0];
      for (let i = 0; i < sections.length; i++) {
        if (sections[i].el.offsetTop <= scrollY) current = sections[i];
      }
      links.forEach(function (a) { a.classList.remove('active'); });
      if (current) current.a.classList.add('active');
      updateBreadcrumb(current);
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* ============================================================
     BREADCRUMB dinámico
     ============================================================ */
  function updateBreadcrumb(currentSection) {
    const bc = document.getElementById('breadcrumb');
    if (!bc || !currentSection) return;

    // Intentar encontrar el padre h2 de la sección actual
    const el = currentSection.el;
    let sectionName = '';
    let parentName = 'Catálogo UPeU';

    // Buscar el section padre para obtener el h2
    const parentSection = el.closest('.section') || el.parentElement;
    if (parentSection) {
      const h2 = parentSection.querySelector('h2.section-title');
      if (h2) parentName = h2.textContent.trim();
    }

    // Nombre del elemento actual
    if (el.tagName === 'H2') {
      sectionName = el.textContent.trim();
      bc.innerHTML = '<span>UPeU IGA</span><span class="current">' + escHtml(sectionName) + '</span>';
    } else if (el.tagName === 'H3' || el.tagName === 'SECTION') {
      sectionName = currentSection.a.textContent.trim();
      bc.innerHTML = '<span>UPeU IGA</span><span>' + escHtml(parentName) + '</span><span class="current">' + escHtml(sectionName) + '</span>';
    } else {
      bc.innerHTML = '<span>UPeU IGA</span><span class="current">' + escHtml(currentSection.a.textContent.trim()) + '</span>';
    }
  }

  function escHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  /* ============================================================
     FILTRO DE TABLA — busca en todas las tablas #catalog-table*
     ============================================================ */
  function initTableFilter() {
    const input = document.getElementById('pos-search');
    const counter = document.getElementById('search-count');
    if (!input) return;

    // Recolectar todas las filas de datos del catálogo
    const allRows = Array.from(document.querySelectorAll('table.pos-catalog tbody tr'));

    function filterRows() {
      const q = input.value.trim().toLowerCase();
      let visible = 0;

      allRows.forEach(function (tr) {
        const text = tr.textContent.toLowerCase();
        const match = !q || text.includes(q);
        tr.style.display = match ? '' : 'none';
        if (match) visible++;
      });

      if (counter) {
        if (q) {
          counter.textContent = visible + ' resultado' + (visible !== 1 ? 's' : '') + ' de ' + allRows.length;
        } else {
          counter.textContent = allRows.length + ' positions en total';
        }
      }

      // Mostrar/ocultar secciones vacías
      document.querySelectorAll('.pos-subsection').forEach(function (sec) {
        const visibleInSection = Array.from(sec.querySelectorAll('tbody tr')).some(function (tr) {
          return tr.style.display !== 'none';
        });
        sec.style.display = visibleInSection ? '' : 'none';
      });
    }

    input.addEventListener('input', filterRows);
    filterRows(); // inicializar contador
  }

  /* ============================================================
     HAMBURGER MENU
     ============================================================ */
  function initHamburger() {
    const btn = document.getElementById('hamburger');
    const sidebar = document.getElementById('sidebar');
    if (!btn || !sidebar) return;

    btn.addEventListener('click', function () {
      sidebar.classList.toggle('open');
      btn.setAttribute('aria-expanded', sidebar.classList.contains('open'));
    });

    // Cerrar sidebar al hacer click en un enlace (mobile)
    sidebar.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () {
        if (window.innerWidth <= 768) {
          sidebar.classList.remove('open');
          btn.setAttribute('aria-expanded', 'false');
        }
      });
    });

    // Cerrar al hacer click fuera del sidebar (mobile)
    document.addEventListener('click', function (e) {
      if (window.innerWidth <= 768 &&
          sidebar.classList.contains('open') &&
          !sidebar.contains(e.target) &&
          !btn.contains(e.target)) {
        sidebar.classList.remove('open');
        btn.setAttribute('aria-expanded', 'false');
      }
    });
  }

  /* ============================================================
     SMOOTH SCROLL — compensar header fijo
     ============================================================ */
  function initSmoothScroll() {
    const OFFSET = 90; // header + breadcrumb
    document.querySelectorAll('a[href^="#"]').forEach(function (a) {
      a.addEventListener('click', function (e) {
        const id = a.getAttribute('href').slice(1);
        const target = document.getElementById(id);
        if (target) {
          e.preventDefault();
          const top = target.getBoundingClientRect().top + window.scrollY - OFFSET;
          window.scrollTo({ top: top, behavior: 'smooth' });
          // Actualizar URL sin recargar
          history.replaceState(null, '', '#' + id);
        }
      });
    });
  }

  /* ============================================================
     BOTÓN IMPRIMIR
     ============================================================ */
  function initPrint() {
    const btn = document.getElementById('btn-print');
    if (btn) btn.addEventListener('click', function () { window.print(); });
  }

  /* ============================================================
     INIT
     ============================================================ */
  document.addEventListener('DOMContentLoaded', function () {
    initTOC();
    initTableFilter();
    initHamburger();
    initSmoothScroll();
    initPrint();
  });

})();
