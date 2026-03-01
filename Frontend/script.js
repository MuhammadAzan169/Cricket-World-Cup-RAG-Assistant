/* =============================================
   Cricket World Cup Companion — Enhanced Vanilla JS
   ============================================= */

// Auto-detect API base URL
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : '';

// Force scroll to top BEFORE the browser restores scroll position
if ('scrollRestoration' in history) {
  history.scrollRestoration = 'manual';
}
window.scrollTo(0, 0);

// Remove any hash from the URL so the browser doesn't auto-scroll to an anchor
if (window.location.hash) {
  history.replaceState(null, '', window.location.pathname + window.location.search);
}

document.addEventListener('DOMContentLoaded', () => {
  // Ensure we're at the top
  window.scrollTo(0, 0);

  // Initialize Lucide icons
  lucide.createIcons();

  // ── Boot all modules ──
  initNavbar();
  initParticleField('particle-canvas');
  initParticleField('particle-canvas-2');
  initTypewriter();
  initScrollAnimations();
  initStatsCounters();
  initTournamentTimeline();
  renderPlayerCards();
  renderMatchTimeline();
  initHeroParallax();
  initSmoothScrolling();
  
  // Initialize chat only if not redirected
  if (window.location.pathname.includes('index.html') || window.location.pathname === '/') {
    initChatInterface();
  }

  // Final scroll-to-top after all rendering is done
  requestAnimationFrame(() => {
    window.scrollTo(0, 0);
  });
});

/* =============================================================
   1. NAVBAR — enhanced with better scroll effects
   ============================================================= */
function initNavbar() {
  const nav = document.getElementById('navbar');
  if (!nav) return;
  
  let lastScrollY = window.scrollY;
  
  window.addEventListener('scroll', () => {
    const currentScrollY = window.scrollY;
    
    // Show/hide based on scroll direction
    if (currentScrollY > lastScrollY && currentScrollY > 100) {
      nav.style.transform = 'translateY(-100%)';
    } else {
      nav.style.transform = 'translateY(0)';
    }
    
    // Glass effect on scroll
    nav.classList.toggle('scrolled', currentScrollY > 50);
    
    // Highlight active section
    highlightActiveNavLink(currentScrollY);
    
    lastScrollY = currentScrollY;
  });
}

function highlightActiveNavLink(scrollY) {
  const sections = ['hero', 'timeline', 'players', 'matches', 'chat'];
  const navLinks = document.querySelectorAll('.navbar-links a');
  
  let currentSection = 'hero';
  
  sections.forEach(section => {
    const element = document.getElementById(section);
    if (element) {
      const rect = element.getBoundingClientRect();
      if (rect.top <= 100 && rect.bottom >= 100) {
        currentSection = section;
      }
    }
  });
  
  navLinks.forEach(link => {
    link.classList.remove('active');
    if (link.getAttribute('href') === `#${currentSection}`) {
      link.classList.add('active');
    }
  });
}

/* =============================================================
   2. PARTICLE FIELD — enhanced with better performance
   ============================================================= */
function initParticleField(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  
  const ctx = canvas.getContext('2d');
  let particles = [];
  let animationId;
  let mouse = { x: 0, y: 0, radius: 100 };
  
  // Handle resize
  function resizeCanvas() {
    canvas.width = canvas.offsetWidth * window.devicePixelRatio;
    canvas.height = canvas.offsetHeight * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    initParticles();
  }
  
  // Initialize particles
  function initParticles() {
    particles = [];
    const particleCount = canvasId === 'particle-canvas-2' ? 40 : 80;
    
    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * canvas.width / window.devicePixelRatio,
        y: Math.random() * canvas.height / window.devicePixelRatio,
        size: Math.random() * 3 + 1,
        speedX: (Math.random() - 0.5) * 0.3,
        speedY: (Math.random() - 0.5) * 0.3,
        color: `hsla(${42 + Math.random() * 30}, 55%, 55%, ${Math.random() * 0.4 + 0.1})`
      });
    }
  }
  
  // Draw particles
  function drawParticles() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    particles.forEach(particle => {
      // Update position
      particle.x += particle.speedX;
      particle.y += particle.speedY;
      
      // Bounce off edges
      if (particle.x <= 0 || particle.x >= canvas.width / window.devicePixelRatio) {
        particle.speedX *= -1;
      }
      if (particle.y <= 0 || particle.y >= canvas.height / window.devicePixelRatio) {
        particle.speedY *= -1;
      }
      
      // Mouse interaction
      const dx = mouse.x - particle.x;
      const dy = mouse.y - particle.y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      
      if (distance < mouse.radius) {
        const angle = Math.atan2(dy, dx);
        const force = (mouse.radius - distance) / mouse.radius;
        particle.x -= Math.cos(angle) * force * 2;
        particle.y -= Math.sin(angle) * force * 2;
      }
      
      // Draw particle
      ctx.beginPath();
      ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
      ctx.fillStyle = particle.color;
      ctx.fill();
    });
    
    // Connect particles with lines
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance < 100) {
          ctx.beginPath();
          ctx.strokeStyle = `hsla(42, 55%, 55%, ${0.1 * (1 - distance / 100)})`;
          ctx.lineWidth = 0.5;
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.stroke();
        }
      }
    }
    
    animationId = requestAnimationFrame(drawParticles);
  }
  
  // Mouse movement
  canvas.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect();
    mouse.x = e.clientX - rect.left;
    mouse.y = e.clientY - rect.top;
  });
  
  // Initialize
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);
  drawParticles();
  
  // Cleanup
  return () => {
    cancelAnimationFrame(animationId);
    window.removeEventListener('resize', resizeCanvas);
  };
}

/* =============================================================
   3. TYPEWRITER — enhanced with better typing effect
   ============================================================= */
function initTypewriter() {
  const textElement = document.getElementById('typewriter-text');
  const cursorElement = document.getElementById('typewriter-cursor');
  if (!textElement || !cursorElement) return;

  const texts = [
    'Who scored the most runs in 2023?',
    "Tell me about Dhoni's winning six",
    'Best bowling figures in World Cups',
    'Most dramatic final ever played',
    "Sachin's World Cup journey",
    'Australia dominance across decades'
  ];

  let textIndex = 0;
  let charIndex = 0;
  let isDeleting = false;
  let isPaused = false;
  const typingSpeed = 60;
  const deletingSpeed = 30;
  const pauseTime = 2000;

  function type() {
    const currentText = texts[textIndex];

    if (!isDeleting && charIndex === currentText.length) {
      if (!isPaused) {
        isPaused = true;
        setTimeout(() => {
          isPaused = false;
          isDeleting = true;
          type();
        }, pauseTime);
      }
      return;
    }

    if (isDeleting && charIndex === 0) {
      isDeleting = false;
      textIndex = (textIndex + 1) % texts.length;
    }

    charIndex += isDeleting ? -1 : 1;
    
    // Add typing sound effect simulation
    if (!isDeleting && charIndex > 0) {
      textElement.style.opacity = '0.9';
      setTimeout(() => textElement.style.opacity = '1', 50);
    }

    textElement.textContent = currentText.substring(0, charIndex);
    
    // Smooth cursor animation
    cursorElement.style.opacity = isPaused ? '0.5' : '1';
    cursorElement.style.transform = isPaused ? 'scale(1.2)' : 'scale(1)';

    setTimeout(type, isDeleting ? deletingSpeed : typingSpeed);
  }

  // Start typing
  setTimeout(type, 1000);
}

/* =============================================================
   4. SCROLL ANIMATIONS — enhanced IntersectionObserver
   ============================================================= */
function initScrollAnimations() {
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const delay = parseInt(entry.target.dataset.delay || '0', 10);
        setTimeout(() => {
          entry.target.classList.add('visible');
          
          // Add bounce effect for cards
          if (entry.target.classList.contains('stats-card') || 
              entry.target.classList.contains('feature-card') ||
              entry.target.classList.contains('player-card')) {
            entry.target.style.transform = 'translateY(0) scale(1)';
          }
        }, delay);
      }
    });
  }, observerOptions);

  // Observe all animatable elements
  document.querySelectorAll('.anim-on-scroll').forEach(el => observer.observe(el));
}

/* =============================================================
   5. STATS COUNTER — enhanced counting animation
   ============================================================= */
function initStatsCounters() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const valueElement = entry.target;
        const target = parseInt(valueElement.dataset.target, 10);
        const suffix = valueElement.dataset.suffix || '';
        const delay = parseInt(valueElement.closest('.stats-card')?.dataset.delay || '0', 10);

        setTimeout(() => {
          countUp(valueElement, target, suffix);
          
          // Add celebration effect
          const card = valueElement.closest('.stats-card');
          if (card) {
            card.style.boxShadow = '0 0 40px hsla(42, 55%, 55%, 0.4)';
            setTimeout(() => {
              card.style.boxShadow = '';
            }, 1000);
          }
        }, delay);
        
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  document.querySelectorAll('.stats-value').forEach(el => observer.observe(el));
}

function countUp(element, target, suffix, duration = 2000) {
  const startTime = Date.now();
  const startValue = 0;
  
  function update() {
    const elapsed = Date.now() - startTime;
    const progress = Math.min(elapsed / duration, 1);
    
    // Ease out cubic
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.floor(eased * target);
    
    element.textContent = current.toLocaleString() + suffix;
    
    // Add scale animation during counting
    const scale = 1 + (0.1 * eased);
    element.style.transform = `scale(${scale})`;
    
    if (progress < 1) {
      requestAnimationFrame(update);
    } else {
      element.style.transform = 'scale(1)';
      
      // Add completion effect
      element.style.color = 'var(--secondary)';
      setTimeout(() => {
        element.style.color = '';
      }, 500);
    }
  }
  
  update();
}

/* =============================================================
   6. HERO PARALLAX — enhanced with smooth effects
   ============================================================= */
function initHeroParallax() {
  const hero = document.getElementById('hero');
  if (!hero) return;

  window.addEventListener('scroll', () => {
    const scrolled = window.pageYOffset;
    const rate = scrolled * -0.5;
    
    // Parallax effect for background
    const bg = hero.querySelector('.hero-bg');
    if (bg) {
      bg.style.transform = `translateY(${rate * 0.5}px)`;
    }
    
    // Fade out content
    const content = hero.querySelector('.hero-inner');
    if (content) {
      const opacity = 1 - (scrolled / 500);
      content.style.opacity = Math.max(opacity, 0);
      content.style.transform = `translateY(${rate * 0.3}px) scale(${1 - scrolled * 0.0005})`;
    }
    
    // Hide scroll indicator
    const indicator = hero.querySelector('.scroll-indicator');
    if (indicator) {
      if (scrolled > 100) {
        indicator.style.opacity = '0';
        indicator.style.transform = 'translateX(-50%) translateY(20px)';
      } else {
        indicator.style.opacity = '1';
        indicator.style.transform = 'translateX(-50%) translateY(0)';
      }
    }
  });
}

/* =============================================================
   7. SMOOTH SCROLLING — enhanced navigation
   ============================================================= */
function initSmoothScrolling() {
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      e.preventDefault();
      
      const targetId = this.getAttribute('href');
      if (targetId === '#') return;
      
      const targetElement = document.querySelector(targetId);
      if (targetElement) {
        const headerHeight = document.querySelector('.navbar').offsetHeight;
        const targetPosition = targetElement.getBoundingClientRect().top + window.pageYOffset - headerHeight;
        
        window.scrollTo({
          top: targetPosition,
          behavior: 'smooth'
        });
        
        // Add active state to clicked link
        document.querySelectorAll('.navbar-links a').forEach(link => {
          link.classList.remove('active');
        });
        this.classList.add('active');
      }
    });
  });
}

/* =============================================================
   8. TOURNAMENT TIMELINE — enhanced with better animations
   ============================================================= */
function initTournamentTimeline() {
  const tournaments = [
    { year: 2003, winner: 'Australia', host: 'South Africa', emoji: '🇦🇺' },
    { year: 2007, winner: 'Australia', host: 'West Indies', emoji: '🇦🇺' },
    { year: 2011, winner: 'India', host: 'India/SL/BD', emoji: '🇮🇳' },
    { year: 2015, winner: 'Australia', host: 'AUS/NZ', emoji: '🇦🇺' },
    { year: 2019, winner: 'England', host: 'England', emoji: '🏴󠁧󠁢󠁥󠁮󠁧󠁿' },
    { year: 2023, winner: 'Australia', host: 'India', emoji: '🇦🇺' },
  ];

  const details = {
    2003: { 
      winner: 'Australia', 
      runnerUp: 'India', 
      venue: 'Johannesburg, SA', 
      highlight: "Ponting's 140* in the final", 
      motm: 'Ricky Ponting', 
      score: '359/2 vs 234',
      fact: 'Sachin scored 673 runs - tournament best'
    },
    2007: { 
      winner: 'Australia', 
      runnerUp: 'Sri Lanka', 
      venue: 'Bridgetown, WI', 
      highlight: 'Hat-trick of titles', 
      motm: 'Adam Gilchrist', 
      score: '281/4 vs 215/8',
      fact: 'First World Cup with Super 8 stage'
    },
    2011: { 
      winner: 'India', 
      runnerUp: 'Sri Lanka', 
      venue: 'Mumbai, India', 
      highlight: "Dhoni's iconic winning six", 
      motm: 'MS Dhoni', 
      score: '275/6 vs 274/6',
      fact: "India's first WC win in 28 years"
    },
    2015: { 
      winner: 'Australia', 
      runnerUp: 'New Zealand', 
      venue: 'Melbourne, AUS', 
      highlight: "Starc's 22 wickets", 
      motm: 'James Faulkner', 
      score: '186/3 vs 183',
      fact: 'Martin Guptill scored 237* - WC record'
    },
    2019: { 
      winner: 'England', 
      runnerUp: 'New Zealand', 
      venue: "Lord's, England", 
      highlight: 'Super Over drama', 
      motm: 'Ben Stokes', 
      score: '241 vs 241 → Super Over',
      fact: 'Won on boundary count rule'
    },
    2023: { 
      winner: 'Australia', 
      runnerUp: 'India', 
      venue: 'Ahmedabad, India', 
      highlight: "Head's match-winning century", 
      motm: 'Travis Head', 
      score: '241/4 vs 240',
      fact: "Kohli broke Sachin's ODI century record"
    },
  };

  const selector = document.getElementById('timeline-selector');
  const detailsPanel = document.getElementById('tournament-details');
  let selectedYear = null;

  // Clear existing content
  selector.innerHTML = '';

  // Render buttons with enhanced animations
  tournaments.forEach((t, i) => {
    const btn = document.createElement('button');
    btn.className = 'timeline-btn';
    btn.innerHTML = `
      <span class="trophy-icon"><i data-lucide="trophy" style="width:20px;height:20px;"></i></span>
      <span class="emoji">${t.emoji}</span>
      <span class="year">${t.year}</span>
      <span class="winner-name">${t.winner}</span>
    `;

    // Staggered entrance with bounce
    setTimeout(() => {
      btn.classList.add('animate-in');
      btn.style.animationDelay = `${i * 100}ms`;
    }, 100 + i * 100);

    btn.addEventListener('click', () => {
      // Add click feedback
      btn.style.transform = 'scale(0.95)';
      setTimeout(() => {
        btn.style.transform = '';
      }, 150);

      // Deselect others
      selector.querySelectorAll('.timeline-btn').forEach(b => {
        b.classList.remove('active');
        b.style.transform = 'scale(1)';
      });
      
      btn.classList.add('active');
      showTournamentDetails(t.year, details[t.year]);
      
      // Scroll details into view on mobile (only on user-initiated clicks, not auto-select)
      if (window.innerWidth < 768 && !isAutoSelect) {
        detailsPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    });

    selector.appendChild(btn);
  });

  // Auto-select first tournament (without scrolling)
  let isAutoSelect = true;
  setTimeout(() => {
    if (selector.firstChild) {
      selector.firstChild.click();
    }
    // Allow future clicks to scroll normally
    setTimeout(() => { isAutoSelect = false; }, 100);
  }, 1000);

  // Re-init lucide for new icons
  lucide.createIcons();

  function showTournamentDetails(year, data) {
    if (selectedYear === year) return;
    selectedYear = year;

    // If already showing, animate out first
    if (!detailsPanel.classList.contains('hidden')) {
      detailsPanel.classList.add('closing');
      setTimeout(() => {
        renderDetails(year, data);
        detailsPanel.classList.remove('closing');
      }, 300);
    } else {
      detailsPanel.classList.remove('hidden');
      renderDetails(year, data);
    }
  }

  function renderDetails(year, data) {
    detailsPanel.innerHTML = `
      <div class="tournament-details-header">
        <i data-lucide="trophy" style="width:32px;height:32px;color:var(--secondary)"></i>
        <h3>${year} ICC Cricket World Cup</h3>
      </div>
      <div class="tournament-details-grid">
        <div>
          <span class="detail-label">Champion</span>
          <span class="detail-value">${data.winner} 🏆</span>
        </div>
        <div>
          <span class="detail-label">Runner-up</span>
          <span class="detail-value">${data.runnerUp}</span>
        </div>
        <div>
          <span class="detail-label">Host Nation</span>
          <span class="detail-value">${data.venue.split(',')[1]?.trim() || data.venue}</span>
        </div>
        <div>
          <span class="detail-label">Final Score</span>
          <span class="detail-value">${data.score}</span>
        </div>
        <div>
          <span class="detail-label">Player of the Match</span>
          <span class="detail-value">${data.motm}</span>
        </div>
        <div>
          <span class="detail-label">Key Highlight</span>
          <span class="detail-highlight">${data.highlight}</span>
        </div>
        <div style="grid-column: 1 / -1; padding: 1.5rem; background: hsla(42,55%,55%,0.05);">
          <span class="detail-label">Did You Know?</span>
          <span class="detail-value" style="font-size: 0.95rem; line-height: 1.6;">${data.fact}</span>
        </div>
      </div>
    `;
    
    // Force re-animation with enhanced effect
    detailsPanel.style.animation = 'none';
    detailsPanel.offsetHeight;
    detailsPanel.style.animation = '';
    
    // Add glow effect
    detailsPanel.style.boxShadow = '0 0 60px hsla(42, 55%, 55%, 0.3)';
    setTimeout(() => {
      detailsPanel.style.boxShadow = '';
    }, 1000);
    
    lucide.createIcons();
  }
}

/* =============================================================
   9. PLAYER CARDS — enhanced with hover effects
   ============================================================= */
function renderPlayerCards() {
  const players = [
    { 
      name: 'Sachin Tendulkar', 
      country: 'India', 
      role: 'Batsman', 
      runs: 2278, 
      wickets: null, 
      matches: 45, 
      highlight: 'Most World Cup runs ever', 
      emoji: '🇮🇳',
      era: '1989-2012'
    },
    { 
      name: 'Ricky Ponting', 
      country: 'Australia', 
      role: 'Batsman', 
      runs: 1743, 
      wickets: null, 
      matches: 46, 
      highlight: 'Captained 2 World Cup wins', 
      emoji: '🇦🇺',
      era: '1995-2012'
    },
    { 
      name: 'Wasim Akram', 
      country: 'Pakistan', 
      role: 'Bowler', 
      runs: null, 
      wickets: 55, 
      matches: 38, 
      highlight: 'Most wickets for Pakistan in WCs', 
      emoji: '🇵🇰',
      era: '1984-2003'
    },
    { 
      name: 'Ben Stokes', 
      country: 'England', 
      role: 'All-rounder', 
      runs: 1104, 
      wickets: 24, 
      matches: 27, 
      highlight: 'Player of the Match in 2019 final', 
      emoji: '🏴\u200d',
      era: '2011-Present'
    },
    { 
      name: 'Kane Williamson', 
      country: 'New Zealand', 
      role: 'Batsman', 
      runs: 1032, 
      wickets: null, 
      matches: 25, 
      highlight: 'Led NZ to consecutive finals', 
      emoji: '🇳🇿',
      era: '2010-Present'
    },
    { 
      name: 'AB de Villiers', 
      country: 'South Africa', 
      role: 'Batsman', 
      runs: 1207, 
      wickets: null, 
      matches: 23, 
      highlight: 'Fastest 150 in World Cup history', 
      emoji: '🇿🇦',
      era: '2004-2018'
    },
  ];

  const grid = document.getElementById('players-grid');
  if (!grid) return;
  
  grid.innerHTML = '';

  players.forEach((p, i) => {
    const card = document.createElement('div');
    card.className = 'player-card anim-on-scroll';
    card.dataset.delay = String(i * 100);
    card.innerHTML = `
      <div class="orb"></div>
      <div class="card-body">
        <div class="player-header">
          <span class="player-emoji">${p.emoji}</span>
          <div>
            <div class="player-name">${p.name}</div>
            <div class="player-meta">${p.country} • ${p.role} • ${p.era}</div>
          </div>
        </div>
        <div class="player-stats">
          ${p.runs !== null ? `
            <div class="player-stat-box">
              <span class="stat-label">Runs</span>
              <span class="stat-number">${p.runs.toLocaleString()}</span>
            </div>
          ` : ''}
          ${p.wickets !== null ? `
            <div class="player-stat-box">
              <span class="stat-label">Wickets</span>
              <span class="stat-number">${p.wickets}</span>
            </div>
          ` : ''}
          <div class="player-stat-box">
            <span class="stat-label">Matches</span>
            <span class="stat-number">${p.matches}</span>
          </div>
          <div class="player-stat-box">
            <span class="stat-label">World Cups</span>
            <span class="stat-number">${Math.ceil(p.matches / 7)}</span>
          </div>
        </div>
        <div class="player-highlight">
          <span>★</span>
          <span>${p.highlight}</span>
        </div>
      </div>
    `;
    
    // Add hover effects
    card.addEventListener('mouseenter', () => {
      card.style.zIndex = '10';
    });
    
    card.addEventListener('mouseleave', () => {
      card.style.zIndex = '1';
    });
    
    grid.appendChild(card);
  });

  // Re-observe newly added scroll elements
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const delay = parseInt(entry.target.dataset.delay || '0', 10);
        setTimeout(() => {
          entry.target.classList.add('visible');
          
          // Add entrance animation
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0) scale(1)';
          
          // Add bounce effect
          setTimeout(() => {
            entry.target.style.transform = 'translateY(-10px) scale(1.02)';
            setTimeout(() => {
              entry.target.style.transform = 'translateY(0) scale(1)';
            }, 150);
          }, delay + 100);
        }, delay);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });

  grid.querySelectorAll('.anim-on-scroll').forEach(el => observer.observe(el));
}

/* =============================================================
   10. MATCH TIMELINE — enhanced with better animations
   ============================================================= */
function renderMatchTimeline() {
  const matches = [
    { 
      year: 2003, 
      match: 'Final: Australia vs India', 
      result: 'AUS won by 125 runs', 
      score: '359/2 vs 234', 
      moment: "Ponting's 140* masterclass",
      icon: 'trophy'
    },
    { 
      year: 2007, 
      match: 'Super 8: Ireland vs Pakistan', 
      result: 'IRE won by 3 wickets', 
      score: '132 vs 132/7', 
      moment: 'Biggest upset in WC history',
      icon: 'zap'
    },
    { 
      year: 2011, 
      match: 'Final: India vs Sri Lanka', 
      result: 'IND won by 6 wickets', 
      score: '275/6 vs 274/6', 
      moment: 'Dhoni finishes it with a six!',
      icon: 'target'
    },
    { 
      year: 2015, 
      match: 'QF: NZ vs SA', 
      result: 'NZ won by 4 wickets', 
      score: '298/6 vs 299/6', 
      moment: "Grant Elliott's last-ball six",
      icon: 'heart'
    },
    { 
      year: 2019, 
      match: 'Final: England vs New Zealand', 
      result: 'ENG won (boundary count)', 
      score: '241 vs 241 → Super Over tied!', 
      moment: 'Greatest final ever played',
      icon: 'award'
    },
    { 
      year: 2023, 
      match: 'Final: India vs Australia', 
      result: 'AUS won by 6 wickets', 
      score: '240 vs 241/4', 
      moment: "Travis Head's stunning century",
      icon: 'star'
    },
  ];

  const container = document.getElementById('match-timeline');
  if (!container) return;
  
  container.querySelectorAll('.match-item:not(.match-timeline-line)').forEach(el => el.remove());

  matches.forEach((m, i) => {
    const item = document.createElement('div');
    const direction = i % 2 === 0 ? 'even' : 'odd';
    item.className = `match-item ${direction} anim-on-scroll`;
    item.dataset.delay = String(i * 100);
    item.style.setProperty('--anim', i % 2 === 0 ? 'slide-in-left' : 'slide-in-right');

    item.innerHTML = `
      <div class="match-card" style="flex:1">
        <div class="match-card-header">
          <span class="match-year">${m.year}</span>
          <span class="match-dot-sep">•</span>
          <span class="match-name">${m.match}</span>
        </div>
        <p class="match-result">${m.result}</p>
        <p class="match-score">${m.score}</p>
        <div class="match-moment">
          <i data-lucide="${m.icon}" style="width:16px;height:16px;color:var(--secondary)"></i>
          <span>${m.moment}</span>
        </div>
      </div>
      <div class="match-center-dot"></div>
      <div class="match-spacer"></div>
    `;

    container.appendChild(item);
  });

  lucide.createIcons();

  // Enhanced observer with staggered animations
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const delay = parseInt(entry.target.dataset.delay || '0', 10);
        const isEven = entry.target.classList.contains('even');
        
        setTimeout(() => {
          entry.target.style.opacity = '1';
          entry.target.style.transform = isEven ? 'translateX(0)' : 'translateX(0)';
          entry.target.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
          
          // Add bounce effect
          setTimeout(() => {
            entry.target.style.transform = isEven ? 'translateX(-10px)' : 'translateX(10px)';
            setTimeout(() => {
              entry.target.style.transform = 'translateX(0)';
            }, 200);
          }, 600);
        }, delay);
        
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.2 });

  container.querySelectorAll('.anim-on-scroll').forEach(el => observer.observe(el));
}

/* =============================================================
   11. CHAT INTERFACE — connected to FastAPI backend
   ============================================================= */
function initChatInterface() {
  const messagesContainer = document.getElementById('chat-messages');
  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send-btn');
  const suggestionsContainer = document.getElementById('chat-suggestions');

  let isProcessing = false;

  const suggestedQuestions = [
    'Who won the 2011 World Cup?',
    'Tell me about the 2019 final',
    "Virat Kohli's World Cup records",
    "MS Dhoni's best moments",
    "Australia's 2023 victory",
    "Sachin Tendulkar's legacy",
    'Best bowling figures in World Cup',
    'Most runs in a single tournament'
  ];

  // Initialize chat
  messagesContainer.innerHTML = '';
  addMessage('bot', "Welcome to Cricket World Cup Companion! 🏏 I'm your expert on ICC World Cups from 2003 to 2023. Ask me anything about the tournaments, players, matches, or statistics!");

  // Render suggestions
  renderSuggestions();

  // Set up form submission
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    if (input.value.trim() && !isProcessing) {
      sendMessage(input.value.trim());
    }
  });

  // Enable/disable send button
  input.addEventListener('input', () => {
    const hasText = input.value.trim().length > 0;
    sendBtn.disabled = !hasText || isProcessing;
    sendBtn.style.opacity = (hasText && !isProcessing) ? '1' : '0.5';
    sendBtn.style.cursor = (hasText && !isProcessing) ? 'pointer' : 'not-allowed';
  });

  // Enter key to send
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (input.value.trim() && !isProcessing) {
        sendMessage(input.value.trim());
      }
    }
  });

  function renderSuggestions() {
    suggestionsContainer.innerHTML = '';
    suggestedQuestions.forEach((q, i) => {
      const btn = document.createElement('button');
      btn.className = 'suggestion-btn';
      btn.textContent = q;
      btn.style.animationDelay = `${i * 100}ms`;

      // Add click animation
      btn.addEventListener('click', (e) => {
        e.target.style.transform = 'scale(0.95)';
        setTimeout(() => {
          e.target.style.transform = '';
        }, 150);
        if (!isProcessing) sendMessage(q);
      });

      suggestionsContainer.appendChild(btn);
    });
  }

  async function sendMessage(text) {
    if (!text.trim() || isProcessing) return;

    isProcessing = true;
    sendBtn.disabled = true;
    sendBtn.style.opacity = '0.5';

    // Add user message
    addMessage('user', text.trim());

    // Clear input
    input.value = '';

    // Show typing indicator
    const typingEl = showTypingIndicator();

    try {
      // Call FastAPI backend
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: text.trim() }),
        signal: AbortSignal.timeout(120000), // 2 min timeout
      });

      typingEl.remove();

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error (${response.status})`);
      }

      const data = await response.json();
      addMessage('bot', data.answer, data);

    } catch (error) {
      typingEl.remove();
      console.error('Chat error:', error);

      let errorMsg;
      if (error.name === 'TimeoutError' || error.name === 'AbortError') {
        errorMsg = '⏱️ The request timed out. The server might be processing a complex query — please try again.';
      } else if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
        errorMsg = '🔌 Cannot connect to the server. Make sure the backend is running:\n\npython server.py\n\n(Server should be at http://localhost:8000)';
      } else {
        errorMsg = `⚠️ ${error.message}`;
      }
      addMessage('bot', errorMsg);
    } finally {
      isProcessing = false;
      sendBtn.disabled = false;
      sendBtn.style.opacity = '1';
      input.focus();

      // Scroll to bottom
      setTimeout(() => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
      }, 100);
    }
  }

  function addMessage(sender, text, metadata = null) {
    const msg = document.createElement('div');
    msg.className = `chat-msg ${sender}`;

    // Timestamp
    const time = new Date().toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });

    // Format text: parse markdown-like formatting
    const formattedText = formatMarkdown(text);

    // Build metadata footer for bot messages
    let metaHtml = '';
    if (sender === 'bot' && metadata) {
      const parts = [];
      if (metadata.query_type) parts.push(`Type: ${metadata.query_type}`);
      if (metadata.search_results) parts.push(`Sources: ${metadata.search_results}`);
      if (metadata.processing_time) parts.push(`${metadata.processing_time}s`);
      if (parts.length > 0) {
        metaHtml = `<div class="chat-msg-meta" style="margin-top:0.5rem;font-size:0.7rem;color:var(--muted-foreground);opacity:0.6;">${parts.join(' · ')}</div>`;
      }
    }

    msg.innerHTML = `
      <div class="chat-msg-avatar">
        <i data-lucide="${sender === 'user' ? 'user' : 'bot'}"
           style="width:14px;height:14px;color:${sender === 'user' ? 'var(--secondary)' : 'var(--accent)'}"></i>
      </div>
      <div class="chat-msg-bubble">
        <div class="chat-msg-text">${formattedText}</div>
        ${metaHtml}
        <div class="chat-msg-time">${time}</div>
      </div>
    `;

    messagesContainer.appendChild(msg);
    lucide.createIcons();

    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Animation
    msg.style.animation = 'message-in 0.3s ease forwards';
  }

  function showTypingIndicator() {
    const typing = document.createElement('div');
    typing.className = 'chat-typing';
    typing.innerHTML = `
      <div class="chat-msg-avatar">
        <i data-lucide="bot" style="width:14px;height:14px;color:var(--accent)"></i>
      </div>
      <div class="typing-bubble">
        <div class="typing-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    `;

    messagesContainer.appendChild(typing);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    lucide.createIcons();

    return typing;
  }
}

/* =============================================================
   11.5. MARKDOWN FORMATTING — for chat messages
   ============================================================= */
function formatMarkdown(text) {
  if (!text) return '';

  let html = text;

  // Escape HTML entities
  html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  // Code blocks (``` ... ```)
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
  // Inline code (`text`)
  html = html.replace(/`([^`]+)`/g, '<code style="background:hsla(220,15%,18%,0.8);padding:0.15em 0.4em;border-radius:4px;font-size:0.88em;">$1</code>');

  // Tables — convert markdown tables to styled HTML
  html = html.replace(/((?:^\|.+\|$\n?)+)/gm, (match) => {
    const rows = match.trim().split('\n').filter(r => r.trim());
    if (rows.length < 2) return match;

    let tableHtml = '<div style="overflow-x:auto;margin:0.75rem 0;"><table style="width:100%;border-collapse:collapse;font-size:0.85rem;">';
    let isHeader = true;
    rows.forEach((row) => {
      // Skip separator rows (|---|---|)
      if (/^\|[\s\-:]+\|$/.test(row.trim())) {
        isHeader = false;
        return;
      }

      const cells = row.split('|').filter((c, i, arr) => i > 0 && i < arr.length - 1);
      const tag = isHeader ? 'th' : 'td';
      const style = isHeader
        ? 'style="padding:0.5rem 0.75rem;border-bottom:2px solid hsla(42,55%,55%,0.3);text-align:left;color:var(--secondary);font-weight:600;"'
        : 'style="padding:0.4rem 0.75rem;border-bottom:1px solid hsla(220,15%,18%,0.5);text-align:left;"';

      tableHtml += '<tr>';
      cells.forEach(cell => {
        tableHtml += `<${tag} ${style}>${cell.trim()}</${tag}>`;
      });
      tableHtml += '</tr>';
      if (isHeader) isHeader = false;
    });
    tableHtml += '</table></div>';
    return tableHtml;
  });

  // Bold (**text**)
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

  // Italic (*text*)
  html = html.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '<em>$1</em>');

  // Headings
  html = html.replace(/^#### (.+)$/gm, '<h4 style="color:var(--secondary);margin:0.75rem 0 0.25rem;font-size:0.95rem;">$1</h4>');
  html = html.replace(/^### (.+)$/gm, '<h3 style="color:var(--secondary);margin:0.75rem 0 0.25rem;font-size:1rem;">$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h3 style="color:var(--secondary);margin:0.75rem 0 0.25rem;font-size:1.05rem;">$1</h3>');
  html = html.replace(/^# (.+)$/gm, '<h2 style="color:var(--secondary);margin:0.75rem 0 0.25rem;font-size:1.1rem;">$1</h2>');

  // Horizontal rules
  html = html.replace(/^---$/gm, '<hr style="border:none;border-top:1px solid hsla(220,15%,18%,0.5);margin:0.75rem 0;">');

  // Bullet points (-, *, •)
  html = html.replace(/^[\u2022\-\*]\s+(.+)$/gm, '<li style="margin:0.2rem 0;padding-left:0.25rem;">$1</li>');
  // Wrap consecutive <li> in <ul>
  html = html.replace(/((?:<li[^>]*>.*?<\/li>\s*)+)/g, '<ul style="margin:0.5rem 0;padding-left:1.25rem;list-style:disc;">$1</ul>');

  // Numbered lists
  html = html.replace(/^\d+\.\s+(.+)$/gm, '<li style="margin:0.2rem 0;">$1</li>');

  // Double line breaks = paragraph breaks
  html = html.replace(/\n\n/g, '<br><br>');
  // Single line breaks
  html = html.replace(/\n/g, '<br>');

  return html;
}

/* =============================================================
   12. INITIAL LOAD ANIMATIONS — page load effects
   ============================================================= */
window.addEventListener('load', () => {
  // Ensure scroll is at the top after everything has loaded
  window.scrollTo(0, 0);

  // Add loaded class to body for transition effects
  document.body.classList.add('loaded');
  
  // Initialize all icons again to ensure they're loaded
  setTimeout(() => lucide.createIcons(), 500);
  
  // Add confetti effect on first CTA click
  const ctaButtons = document.querySelectorAll('.btn-primary');
  ctaButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      btn.style.animation = 'pulse 0.5s ease';
      setTimeout(() => btn.style.animation = '', 500);
    });
  });
});

/* =============================================================
   13. REDIRECT FUNCTION — for chatbot page
   ============================================================= */
window.redirectToChatbot = function(message) {
  const encodedMessage = encodeURIComponent(message);
  window.location.href = `chatbot.html?q=${encodedMessage}`;
};