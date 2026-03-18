const yorumlar = [
  { metin: '"Birleşme sürecindeki hukuki riskleri haftalar yerine günlerde kapattık."', isim: '— CFO, Teknoloji Şirketi' },
  { metin: '"Ceza dosyamızda strateji ve iletişim yönetimi kusursuzdu."', isim: '— Kurucu Ortak, Özel Sağlık Grubu' },
  { metin: '"Kurumsal itibarımızı koruyan net bir savunma planı sundular."', isim: '— CEO, Holding' }
];

let i = 0;
setInterval(() => {
  i = (i + 1) % yorumlar.length;
  const t = document.getElementById('testimonialText');
  const n = document.getElementById('testimonialName');
  if (!t || !n) return;
  t.style.opacity = '0';
  n.style.opacity = '0';
  setTimeout(() => {
    t.textContent = yorumlar[i].metin;
    n.textContent = yorumlar[i].isim;
    t.style.opacity = '1';
    n.style.opacity = '1';
  }, 220);
}, 3500);

const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add('show');
    }
  });
}, { threshold: 0.2 });

document.querySelectorAll('.fade-up').forEach((el, idx) => {
  setTimeout(() => observer.observe(el), idx * 90);
});
