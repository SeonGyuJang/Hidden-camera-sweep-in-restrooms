// ── Drawer ─────────────────────────────────────────────────────────────────
function openDrawer() {
  document.getElementById('drawer').classList.add('open');
  document.getElementById('overlay').classList.add('open');
  document.body.style.overflow = 'hidden';
}
function closeDrawer() {
  document.getElementById('drawer').classList.remove('open');
  document.getElementById('overlay').classList.remove('open');
  document.body.style.overflow = '';
}

// ── Flash auto-dismiss ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.t-flash').forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity .35s, transform .35s';
      el.style.opacity = '0';
      el.style.transform = 'translateY(-6px)';
      setTimeout(() => el.remove(), 350);
    }, 2800);
  });
});

// ── localStorage team memory ───────────────────────────────────────────────
function saveTeam(tid) {
  try { localStorage.setItem('last_team', tid); } catch(e) {}
}
function loadTeam() {
  try { return localStorage.getItem('last_team'); } catch(e) { return null; }
}
