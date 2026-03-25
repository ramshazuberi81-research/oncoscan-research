/* ============================================================
   OncosenseAI — main.js
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {

  /* ── Animate stats on scroll ─────────────────────────────── */
  const animateValue = (el, start, end, duration, suffix = '') => {
    let startTime = null;
    const isFloat = String(end).includes('.');
    const decimals = isFloat ? String(end).split('.')[1].length : 0;

    const step = (timestamp) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      const current = start + (end - start) * ease;
      el.textContent = isFloat
        ? current.toFixed(decimals) + suffix
        : Math.floor(current) + suffix;
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };

  const statsObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el = entry.target;
        const raw = el.dataset.value;
        const suffix = el.dataset.suffix || '';
        const isFloat = raw.includes('.');
        animateValue(el, 0, parseFloat(raw), 1400, suffix);
        statsObserver.unobserve(el);
      }
    });
  }, { threshold: 0.5 });

  document.querySelectorAll('[data-value]').forEach(el => statsObserver.observe(el));

  /* ── Fade-in on scroll ───────────────────────────────────── */
  const fadeObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        fadeObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

  document.querySelectorAll('.fade-in').forEach(el => fadeObserver.observe(el));

  /* ── Nav scroll state ────────────────────────────────────── */
  const nav = document.querySelector('nav');
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 60);
  });

  /* ── Smooth scroll for anchor links ─────────────────────── */
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', e => {
      const target = document.querySelector(anchor.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  /* ── Live demo — symptom risk calculator ────────────────── */
  const form = document.getElementById('symptom-form');
  if (form) {
    const inputs = form.querySelectorAll('input, select');
    inputs.forEach(input => input.addEventListener('change', calculateRisk));
    calculateRisk();
  }

  function calculateRisk() {
    const age = parseInt(document.getElementById('age')?.value || 50);
    const checkboxes = document.querySelectorAll('.symptom-check:checked');
    const alarmSymptoms = ['rectal_bleeding','weight_loss','jaundice','palpable_mass'];
    let alarmCount = 0;
    let totalSymptoms = checkboxes.length;

    checkboxes.forEach(cb => {
      if (alarmSymptoms.includes(cb.value)) alarmCount++;
    });

    const familyHx = document.getElementById('family_hx')?.value || '0';
    const duration = parseInt(document.getElementById('duration')?.value || 2);

    // Simplified logistic model
    let logit = -3.5;
    logit += (age - 40) * 0.04;
    logit += alarmCount * 1.1;
    logit += (totalSymptoms - alarmCount) * 0.3;
    logit += parseFloat(familyHx) * 0.6;
    logit += Math.log(duration + 1) * 0.4;

    const prob = 1 / (1 + Math.exp(-logit));
    const pct = Math.round(prob * 100);

    const display = document.getElementById('risk-display');
    const tierEl = document.getElementById('risk-tier');
    const recEl  = document.getElementById('risk-rec');
    if (!display) return;

    display.textContent = pct + '%';

    if (prob < 0.15) {
      display.style.color = '#00ffaa';
      tierEl.textContent = '🟢 LOW RISK';
      recEl.textContent  = 'Routine follow-up. Reassess if symptoms persist > 4 weeks.';
    } else if (prob < 0.40) {
      display.style.color = '#ffcc44';
      tierEl.textContent = '🟡 ELEVATED';
      recEl.textContent  = 'Non-urgent referral recommended. Consider FIT test and bloods.';
    } else {
      display.style.color = '#ff4455';
      tierEl.textContent = '🔴 URGENT';
      recEl.textContent  = '2-week-wait urgent referral. Do not delay.';
    }
  }

});
