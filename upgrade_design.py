#!/usr/bin/env python3
"""
upgrade_design.py
=================
Upgrades all HTML pages (except pricing.html) in the ai-sales-pipeline site
to match the premium dark-mode design from pricing.html.

Preserves ALL meta tags, JSON-LD schemas, title tags, canonical/alternate links,
and body content. Only changes: visual design (fonts, colors, layout, nav, footer,
animations).
"""

import os
import re
import shutil
import html as html_mod

BASE_DIR = "/Users/teddy/ai-sales-pipeline"
PRICING_FILE = os.path.join(BASE_DIR, "pricing.html")

# Files to skip
SKIP_FILES = {"pricing.html"}

# ──────────────────────────────────────────────
# 1. PREMIUM DESIGN TEMPLATE ELEMENTS
# ──────────────────────────────────────────────

GOOGLE_FONTS = '    <link rel="preconnect" href="https://fonts.googleapis.com">\n    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&display=swap" rel="stylesheet">'

TAILWIND_CDN = """    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        primary: {
                            50: '#fff7f0',
                            100: '#ffead9',
                            200: '#ffd4b3',
                            300: '#ffb380',
                            400: '#ff8c4d',
                            500: '#ff6b35',
                            600: '#ff5a1f',
                            700: '#e04a12',
                            800: '#b33c0f',
                            900: '#8c2f0c',
                        },
                        accent: {
                            50: '#e6fbff',
                            100: '#b3f2ff',
                            200: '#80e9ff',
                            300: '#4de0ff',
                            400: '#1ad7ff',
                            500: '#00d4ff',
                            600: '#00a9cc',
                            700: '#007f99',
                            800: '#005466',
                            900: '#002a33',
                        },
                        dark: {
                            50: '#2a2a2a',
                            100: '#1f1f1f',
                            200: '#1a1a1a',
                            300: '#151515',
                            400: '#111111',
                            500: '#0d0d0d',
                            600: '#0a0a0a',
                            700: '#080808',
                            800: '#050505',
                            900: '#020202',
                        }
                    },
                    fontFamily: {
                        heading: ['"Space Grotesk"', 'system-ui', 'sans-serif'],
                        body: ['"DM Sans"', 'system-ui', 'sans-serif'],
                    }
                }
            }
        }
    </script>"""

PREMIUM_CSS = """    <style>
        /* ============ BASE ============ */
        * { margin: 0; padding: 0; box-sizing: border-box; }

        :root {
            --dark-bg: #0a0a0a;
            --dark-alt: #111111;
            --orange: #ff6b35;
            --orange-dark: #ff5a1f;
            --white: #ffffff;
            --gray-light: #f0f0f0;
            --gray-dark: #1a1a1a;
            --gray-medium: #2a2a2a;
            --blue-accent: #00d4ff;
        }

        html { scroll-behavior: smooth; }

        body {
            font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: var(--dark-bg);
            color: var(--white);
            line-height: 1.6;
            overflow-x: hidden;
        }

        h1, h2, h3, h4, h5, h6 {
            font-family: 'Space Grotesk', system-ui, sans-serif;
        }

        /* ============ FILM GRAIN OVERLAY ============ */
        body::after {
            content: '';
            position: fixed;
            inset: 0;
            z-index: 9999;
            pointer-events: none;
            opacity: 0.025;
            background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
            background-repeat: repeat;
            background-size: 256px 256px;
        }

        /* ============ NAVIGATION ============ */
        nav {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1000;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1.2rem 2rem;
            background-color: rgba(10, 10, 10, 0.7);
            backdrop-filter: blur(0px);
            transition: backdrop-filter 0.3s ease, background-color 0.3s ease, border-color 0.3s ease;
            border-bottom: 1px solid rgba(255, 107, 53, 0);
        }

        nav.scrolled {
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            background-color: rgba(10, 10, 10, 0.92);
            border-bottom: 1px solid rgba(255, 107, 53, 0.2);
        }

        .nav-logo {
            font-family: 'Space Grotesk', system-ui, sans-serif;
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--white);
            text-decoration: none;
            letter-spacing: -0.5px;
        }

        .nav-links {
            display: flex;
            gap: 2.5rem;
            list-style: none;
            align-items: center;
        }

        .nav-links a {
            color: rgba(255, 255, 255, 0.85);
            text-decoration: none;
            font-size: 0.95rem;
            font-weight: 500;
            transition: color 0.3s ease;
            position: relative;
            font-family: 'DM Sans', sans-serif;
        }

        .nav-links a:hover { color: var(--orange); }

        .nav-links a::after {
            content: '';
            position: absolute;
            bottom: -5px;
            left: 0;
            width: 0;
            height: 2px;
            background: linear-gradient(90deg, var(--orange), transparent);
            transition: width 0.3s ease;
        }

        .nav-links a:hover::after { width: 100%; }

        .nav-cta {
            background: linear-gradient(135deg, var(--orange), var(--orange-dark));
            color: var(--white) !important;
            padding: 0.7rem 1.4rem;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9rem;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(255, 107, 53, 0.3);
        }

        .nav-cta:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 25px rgba(255, 107, 53, 0.5);
        }

        .nav-cta::after { display: none !important; }

        /* Mobile hamburger */
        .hamburger {
            display: none;
            flex-direction: column;
            gap: 5px;
            cursor: pointer;
            z-index: 1001;
            padding: 4px;
        }

        .hamburger span {
            display: block;
            width: 24px;
            height: 2px;
            background: var(--white);
            border-radius: 2px;
            transition: all 0.3s ease;
        }

        .hamburger.active span:nth-child(1) {
            transform: rotate(45deg) translate(5px, 5px);
        }
        .hamburger.active span:nth-child(2) { opacity: 0; }
        .hamburger.active span:nth-child(3) {
            transform: rotate(-45deg) translate(5px, -5px);
        }

        @media (max-width: 768px) {
            .hamburger { display: flex; }

            .nav-links {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(10, 10, 10, 0.98);
                backdrop-filter: blur(20px);
                flex-direction: column;
                justify-content: center;
                align-items: center;
                gap: 2rem;
                z-index: 999;
            }

            .nav-links.open { display: flex; }

            .nav-links a {
                font-size: 1.3rem;
                font-weight: 600;
            }

            nav { padding: 1rem 1.5rem; }
            .nav-logo { font-size: 1.3rem; }
        }

        /* ============ SECTION DIVIDERS ============ */
        .section-divider {
            height: 1px;
            max-width: 1200px;
            margin: 0 auto;
            background: linear-gradient(90deg, transparent, var(--orange), var(--blue-accent), transparent);
            opacity: 0.3;
        }

        /* ============ SCROLL REVEAL ANIMATIONS ============ */
        .reveal {
            opacity: 0;
            transform: translateY(40px);
            transition: opacity 0.8s cubic-bezier(0.22, 1, 0.36, 1), transform 0.8s cubic-bezier(0.22, 1, 0.36, 1);
        }

        .reveal.visible {
            opacity: 1;
            transform: translateY(0);
        }

        .reveal-d1 { transition-delay: 0.1s; }
        .reveal-d2 { transition-delay: 0.2s; }
        .reveal-d3 { transition-delay: 0.3s; }

        /* ============ GLASSMORPHIC CARDS ============ */
        .glass-card {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 16px;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            transition: all 0.4s cubic-bezier(0.22, 1, 0.36, 1);
        }

        .glass-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 20px 60px rgba(255, 107, 53, 0.12);
            border-color: rgba(255, 107, 53, 0.2);
        }

        /* ============ CTA BUTTONS ============ */
        .btn-primary {
            display: inline-block;
            background: linear-gradient(135deg, var(--orange), var(--orange-dark));
            color: var(--white);
            padding: 0.9rem 2rem;
            border-radius: 50px;
            text-decoration: none;
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 700;
            font-size: 0.95rem;
            transition: all 0.3s ease;
            box-shadow: 0 8px 25px rgba(255, 107, 53, 0.3);
            text-align: center;
        }

        .btn-primary:hover {
            transform: translateY(-3px);
            box-shadow: 0 12px 35px rgba(255, 107, 53, 0.5);
        }

        /* ============ CONTENT STYLING ============ */
        .content-section {
            max-width: 1200px;
            margin: 0 auto;
            padding: 4rem 2rem;
        }

        .content-section h2 {
            font-family: 'Space Grotesk', system-ui, sans-serif;
            color: var(--white);
            font-size: clamp(1.6rem, 3vw, 2.2rem);
            font-weight: 700;
            margin-bottom: 1.5rem;
            text-align: center;
        }

        .content-section h3 {
            font-family: 'Space Grotesk', system-ui, sans-serif;
            color: var(--orange);
            font-size: 1.3rem;
            font-weight: 700;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }

        .content-section p {
            color: rgba(255, 255, 255, 0.75);
            line-height: 1.8;
            margin-bottom: 1rem;
            font-size: 1rem;
        }

        .content-section a {
            color: var(--orange);
            text-decoration: underline;
            text-decoration-color: rgba(255, 107, 53, 0.3);
            transition: text-decoration-color 0.3s ease;
        }

        .content-section a:hover {
            text-decoration-color: var(--orange);
        }

        .content-section strong {
            color: var(--white);
        }

        /* ============ LISTS ============ */
        .content-section ul, .content-section ol {
            margin-bottom: 1.5rem;
            padding-left: 0;
            list-style: none;
        }

        .content-section ul li, .content-section ol li {
            position: relative;
            padding: 0.5rem 0 0.5rem 1.8rem;
            color: rgba(255, 255, 255, 0.75);
            line-height: 1.7;
        }

        .content-section ul li::before {
            content: '';
            position: absolute;
            left: 0;
            top: 0.85rem;
            width: 8px;
            height: 8px;
            background: var(--orange);
            border-radius: 2px;
            transform: rotate(45deg);
        }

        .content-section ol {
            counter-reset: item;
        }

        .content-section ol li {
            counter-increment: item;
        }

        .content-section ol li::before {
            content: counter(item);
            position: absolute;
            left: 0;
            top: 0.5rem;
            width: 22px;
            height: 22px;
            background: rgba(255, 107, 53, 0.15);
            color: var(--orange);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.75rem;
            font-weight: 700;
        }

        /* ============ TABLES ============ */
        .content-section table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            margin: 2rem 0;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.06);
        }

        .content-section table thead th {
            background: rgba(255, 107, 53, 0.1);
            color: var(--white);
            padding: 1rem 1.25rem;
            text-align: left;
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 600;
            font-size: 0.9rem;
            border-bottom: 1px solid rgba(255, 107, 53, 0.2);
        }

        .content-section table td {
            padding: 0.85rem 1.25rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            color: rgba(255, 255, 255, 0.7);
            font-size: 0.95rem;
        }

        .content-section table tr:last-child td {
            border-bottom: none;
        }

        .content-section table tr:hover td {
            background: rgba(255, 255, 255, 0.02);
        }

        /* ============ BLOCKQUOTES ============ */
        .content-section blockquote {
            border-left: 3px solid var(--orange);
            padding: 1rem 1.5rem;
            margin: 1.5rem 0;
            background: rgba(255, 107, 53, 0.04);
            border-radius: 0 12px 12px 0;
            color: rgba(255, 255, 255, 0.7);
            font-style: italic;
        }

        /* ============ HERO SECTION ============ */
        .page-hero {
            position: relative;
            padding: 10rem 2rem 4rem;
            text-align: center;
            background:
                radial-gradient(ellipse at 30% 30%, rgba(255, 107, 53, 0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 70% 70%, rgba(0, 212, 255, 0.05) 0%, transparent 50%),
                linear-gradient(180deg, #0a0a0a 0%, #080808 100%);
        }

        .page-hero h1 {
            font-size: clamp(2rem, 4.5vw, 3.2rem);
            font-weight: 800;
            line-height: 1.15;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, #fff 0%, #00d4ff 50%, #ff6b35 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            max-width: 900px;
            margin-left: auto;
            margin-right: auto;
        }

        .page-hero .subtitle {
            color: rgba(240, 240, 240, 0.65);
            font-size: clamp(1rem, 2vw, 1.15rem);
            max-width: 650px;
            margin: 0 auto;
            line-height: 1.7;
        }

        /* ============ BLOG / ARTICLE LAYOUT ============ */
        .article-layout {
            max-width: 780px;
            margin: 0 auto;
            padding: 3rem 2rem 4rem;
        }

        .article-layout p {
            color: rgba(255, 255, 255, 0.75);
            line-height: 1.85;
            margin-bottom: 1.25rem;
            font-size: 1.05rem;
        }

        .article-layout h2 {
            text-align: left;
            margin-top: 3rem;
        }

        .article-layout h3 {
            margin-top: 2rem;
        }

        .byline-info {
            text-align: center;
            color: rgba(255, 255, 255, 0.4);
            font-size: 0.9rem;
            margin-bottom: 2rem;
            padding-bottom: 2rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }

        /* ============ FOOTER ============ */
        footer {
            background-color: var(--dark-alt);
            padding: 3rem 2rem;
            border-top: 1px solid rgba(255, 107, 53, 0.2);
        }

        .footer-content {
            max-width: 1200px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 2.5rem;
            margin-bottom: 2rem;
        }

        .footer-section h3 {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--white);
            margin-bottom: 1rem;
        }

        .footer-section ul { list-style: none; }
        .footer-section ul li { margin-bottom: 0.7rem; }

        .footer-section a {
            color: rgba(240, 240, 240, 0.65);
            text-decoration: none;
            font-size: 0.9rem;
            transition: color 0.3s ease;
        }

        .footer-section a:hover { color: var(--orange); }

        .footer-bottom {
            text-align: center;
            padding-top: 2rem;
            border-top: 1px solid rgba(255, 107, 53, 0.1);
            color: rgba(240, 240, 240, 0.5);
            font-size: 0.85rem;
        }

        /* ============ RESPONSIVE ============ */
        @media (max-width: 768px) {
            .page-hero { padding: 8rem 1.5rem 3rem; }
            .content-section { padding: 3rem 1.5rem; }
            .article-layout { padding: 2rem 1.5rem 3rem; }
        }
    </style>"""


def get_nav_html(is_spanish=False):
    """Return the glassmorphic nav HTML."""
    if is_spanish:
        return """
<!-- ============ NAVIGATION ============ -->
<nav id="navbar">
    <a href="/es/" class="nav-logo">AI Sales Pipeline</a>

    <div class="hamburger" id="hamburger" onclick="document.getElementById('navLinks').classList.toggle('open'); this.classList.toggle('active');">
        <span></span><span></span><span></span>
    </div>

    <div class="nav-links" id="navLinks">
        <a href="/features.html" onclick="document.getElementById('navLinks').classList.remove('open'); document.getElementById('hamburger').classList.remove('active');">Funciones</a>
        <a href="/pricing.html" onclick="document.getElementById('navLinks').classList.remove('open'); document.getElementById('hamburger').classList.remove('active');">Precios</a>
        <a href="/comparison.html" onclick="document.getElementById('navLinks').classList.remove('open'); document.getElementById('hamburger').classList.remove('active');">Comparar</a>
        <a href="/simulation.html" onclick="document.getElementById('navLinks').classList.remove('open'); document.getElementById('hamburger').classList.remove('active');">Simulacion</a>
        <a href="/" onclick="document.getElementById('navLinks').classList.remove('open'); document.getElementById('hamburger').classList.remove('active');">English</a>
        <a href="/#contact" class="nav-cta" onclick="document.getElementById('navLinks').classList.remove('open'); document.getElementById('hamburger').classList.remove('active');">Agendar Demo</a>
    </div>
</nav>"""
    else:
        return """
<!-- ============ NAVIGATION ============ -->
<nav id="navbar">
    <a href="/" class="nav-logo">AI Sales Pipeline</a>

    <div class="hamburger" id="hamburger" onclick="document.getElementById('navLinks').classList.toggle('open'); this.classList.toggle('active');">
        <span></span><span></span><span></span>
    </div>

    <div class="nav-links" id="navLinks">
        <a href="/features.html" onclick="document.getElementById('navLinks').classList.remove('open'); document.getElementById('hamburger').classList.remove('active');">Features</a>
        <a href="/pricing.html" onclick="document.getElementById('navLinks').classList.remove('open'); document.getElementById('hamburger').classList.remove('active');">Pricing</a>
        <a href="/comparison.html" onclick="document.getElementById('navLinks').classList.remove('open'); document.getElementById('hamburger').classList.remove('active');">Compare</a>
        <a href="/simulation.html" onclick="document.getElementById('navLinks').classList.remove('open'); document.getElementById('hamburger').classList.remove('active');">Simulation</a>
        <a href="/es/" onclick="document.getElementById('navLinks').classList.remove('open'); document.getElementById('hamburger').classList.remove('active');">Espa&ntilde;ol</a>
        <a href="/#contact" class="nav-cta" onclick="document.getElementById('navLinks').classList.remove('open'); document.getElementById('hamburger').classList.remove('active');">Book Demo</a>
    </div>
</nav>"""


def get_footer_html(is_spanish=False):
    """Return the dark footer HTML."""
    if is_spanish:
        return """
<!-- ============ FOOTER ============ -->
<footer>
    <div class="footer-content">
        <div class="footer-section">
            <h3 style="color:var(--orange);">Funciones</h3>
            <ul>
                <li><a href="/features/ai-sms-real-estate.html">SMS con IA</a></li>
                <li><a href="/features/ai-email-real-estate.html">Email con IA</a></li>
                <li><a href="/features/ai-voice-calls-real-estate.html">Llamadas con IA</a></li>
                <li><a href="/features/ai-clone-video-real-estate.html">Video Clon IA</a></li>
                <li><a href="/features/lead-scoring-real-estate.html">Puntuacion de Leads</a></li>
                <li><a href="/features/seller-workflows-real-estate.html">Flujos de Vendedores</a></li>
                <li><a href="/features/buyer-workflows-real-estate.html">Flujos de Compradores</a></li>
            </ul>
        </div>
        <div class="footer-section">
            <h3 style="color:var(--orange);">Recursos</h3>
            <ul>
                <li><a href="/">Inicio</a></li>
                <li><a href="/features.html">Todas las Funciones</a></li>
                <li><a href="/comparison.html">Comparacion de CRM</a></li>
                <li><a href="/ai-crm-real-estate.html">CRM con IA para Inmobiliarias</a></li>
                <li><a href="/fsbo-automation.html">Automatizacion FSBO</a></li>
                <li><a href="/expired-listing-automation.html">Listados Vencidos</a></li>
            </ul>
        </div>
        <div class="footer-section">
            <h3 style="color:var(--orange);">Contacto</h3>
            <ul>
                <li><a href="/#contact">Agendar Demo</a></li>
                <li><a href="tel:+19082307844">(908) 230-7844</a></li>
                <li><a href="mailto:jorgeramirez76@gmail.com">jorgeramirez76@gmail.com</a></li>
            </ul>
        </div>
    </div>
    <div class="footer-bottom">
        <p>&copy; 2026 AI Sales Pipeline. Todos los derechos reservados.</p>
    </div>
</footer>"""
    else:
        return """
<!-- ============ FOOTER ============ -->
<footer>
    <div class="footer-content">
        <div class="footer-section">
            <h3 style="color:var(--orange);">Features</h3>
            <ul>
                <li><a href="/features/ai-sms-real-estate.html">AI SMS</a></li>
                <li><a href="/features/ai-email-real-estate.html">AI Email</a></li>
                <li><a href="/features/ai-voice-calls-real-estate.html">AI Voice Calls</a></li>
                <li><a href="/features/ai-clone-video-real-estate.html">AI Clone Video</a></li>
                <li><a href="/features/lead-scoring-real-estate.html">Lead Scoring</a></li>
                <li><a href="/features/seller-workflows-real-estate.html">Seller Workflows</a></li>
                <li><a href="/features/buyer-workflows-real-estate.html">Buyer Workflows</a></li>
            </ul>
        </div>
        <div class="footer-section">
            <h3 style="color:var(--orange);">Resources</h3>
            <ul>
                <li><a href="/">Home</a></li>
                <li><a href="/features.html">All Features</a></li>
                <li><a href="/comparison.html">CRM Comparison</a></li>
                <li><a href="/ai-crm-real-estate.html">AI CRM for Real Estate</a></li>
                <li><a href="/fsbo-automation.html">FSBO Automation</a></li>
                <li><a href="/expired-listing-automation.html">Expired Listing Automation</a></li>
            </ul>
        </div>
        <div class="footer-section">
            <h3 style="color:var(--orange);">Contact</h3>
            <ul>
                <li><a href="/#contact">Book a Demo</a></li>
                <li><a href="tel:+19082307844">(908) 230-7844</a></li>
                <li><a href="mailto:jorgeramirez76@gmail.com">jorgeramirez76@gmail.com</a></li>
            </ul>
        </div>
    </div>
    <div class="footer-bottom">
        <p>&copy; 2026 AI Sales Pipeline. All rights reserved.</p>
    </div>
</footer>"""


FOUNDER_BACKLINK = """
<!-- Founder backlink -- SEO link to thejorgeramirezgroup.com -->
<div style="background: #050505; padding: 24px 40px; border-top: 1px solid rgba(255,107,53,0.15); text-align: center; font-size: 0.85rem; color: rgba(240,240,240,0.6);">
    <p style="margin: 0; line-height: 1.7;">
        Built and operated by <strong style="color: #ff6b35;">Jorge Ramirez</strong>, a 15-year licensed New Jersey real estate agent and founder of
        <a href="https://www.thejorgeramirezgroup.com" rel="noopener" style="color: #ff6b35; text-decoration: underline;">The Jorge Ramirez Group</a>
        at Keller Williams Premier Properties. Specializing in <a href="https://www.thejorgeramirezgroup.com" rel="noopener" style="color: rgba(240,240,240,0.6);">luxury real estate in Summit, Westfield, Short Hills, and the surrounding Union, Essex, Morris, Hudson, and Middlesex counties</a>.
    </p>
</div>"""


BOTTOM_SCRIPTS = """
<!-- ============ SCRIPTS ============ -->
<script>
// Navigation scroll effect
const navbar = document.getElementById('navbar');
window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
        navbar.classList.add('scrolled');
    } else {
        navbar.classList.remove('scrolled');
    }
});

// Scroll reveal (IntersectionObserver)
const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            revealObserver.unobserve(entry.target);
        }
    });
}, {
    threshold: 0.08,
    rootMargin: '0px 0px -60px 0px'
});

document.querySelectorAll('.reveal').forEach(el => {
    revealObserver.observe(el);
});
</script>"""


# ──────────────────────────────────────────────
# 2. PARSING HELPERS
# ──────────────────────────────────────────────

def extract_head_meta(html_content):
    """Extract all meta tags, title, canonical/alternate links, and JSON-LD blocks from <head>."""
    head_match = re.search(r'<head[^>]*>(.*?)</head>', html_content, re.DOTALL | re.IGNORECASE)
    if not head_match:
        return "", "", [], [], []

    head = head_match.group(1)

    # Title
    title_match = re.search(r'<title[^>]*>.*?</title>', head, re.DOTALL | re.IGNORECASE)
    title_tag = title_match.group(0) if title_match else "<title>AI Sales Pipeline</title>"

    # Meta tags (self-closing or not)
    meta_tags = re.findall(r'<meta\s[^>]*/?>', head, re.IGNORECASE)

    # Canonical + alternate + other important link tags (not stylesheet, not preconnect, not fonts)
    link_tags = re.findall(r'<link\s[^>]*/?>', head, re.IGNORECASE)
    seo_links = []
    for lt in link_tags:
        # Keep canonical, alternate, manifest, apple-touch-icon, icon
        if any(attr in lt.lower() for attr in ['rel="canonical"', "rel='canonical'",
                                                 'rel="alternate"', "rel='alternate'",
                                                 'rel="manifest"', "rel='manifest'",
                                                 'rel="icon"', "rel='icon'",
                                                 'rel="apple-touch-icon"', "rel='apple-touch-icon'"]):
            seo_links.append(lt)

    # JSON-LD schema blocks
    jsonld_blocks = re.findall(
        r'<script\s+type=["\']application/ld\+json["\'][^>]*>.*?</script>',
        head, re.DOTALL | re.IGNORECASE
    )

    return title_tag, meta_tags, seo_links, jsonld_blocks, head


def extract_body_content(html_content):
    """Extract the main body content, stripping old nav/header and footer."""
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL | re.IGNORECASE)
    if not body_match:
        return ""

    body = body_match.group(1)

    # Remove old navigation/header blocks
    # Pattern: <nav ...>...</nav> or <header ...>...</header> at the start
    body = re.sub(r'^\s*<!--[^>]*NAVIGATION[^>]*-->\s*', '', body, flags=re.IGNORECASE)
    body = re.sub(r'<nav\b[^>]*>.*?</nav>', '', body, count=1, flags=re.DOTALL | re.IGNORECASE)

    # Remove old footer
    body = re.sub(r'<footer\b[^>]*>.*?</footer>', '', body, count=1, flags=re.DOTALL | re.IGNORECASE)

    # Remove old header elements (styled headers that act as nav)
    # Only remove if it's a site header, not a content header
    header_match = re.search(r'<header\b[^>]*class=["\'][^"\']*(?:blog-header|site-header|main-header)[^"\']*["\'][^>]*>.*?</header>', body, re.DOTALL | re.IGNORECASE)
    if not header_match:
        # Check for a header at the very start that's nav-like
        header_match = re.search(r'^\s*<header\b[^>]*>.*?</header>', body, re.DOTALL | re.IGNORECASE)
        if header_match:
            header_content = header_match.group(0)
            # If header contains nav-like links, remove it
            if re.search(r'<a\b[^>]*>.*?(?:Features|Pricing|Home|Demo).*?</a>', header_content, re.IGNORECASE):
                body = body[:header_match.start()] + body[header_match.end():]

    # Remove any old founder backlink div
    body = re.sub(
        r'<!--\s*Founder backlink.*?-->\s*<div[^>]*>.*?thejorgeramirezgroup.*?</div>',
        '', body, flags=re.DOTALL | re.IGNORECASE
    )
    # Also catch the backlink without a comment
    body = re.sub(
        r'<div[^>]*style="[^"]*background:\s*#050505[^"]*"[^>]*>.*?thejorgeramirezgroup.*?</div>',
        '', body, flags=re.DOTALL | re.IGNORECASE
    )

    # Remove old inline scripts at the bottom (nav scroll, IntersectionObserver, etc.)
    body = re.sub(
        r'<script>\s*(?://\s*Navigation|//\s*Scroll|//\s*FAQ|//\s*Nav|const\s+navbar|window\.addEventListener|document\.querySelectorAll\([\'"]\.reveal).*?</script>',
        '', body, flags=re.DOTALL | re.IGNORECASE
    )

    # Remove old <style> blocks that might be in the body
    body = re.sub(r'<style\b[^>]*>.*?</style>', '', body, flags=re.DOTALL | re.IGNORECASE)

    # Remove GA / analytics scripts at the bottom (keep them — we re-add them)
    # Actually, let's keep GA scripts
    ga_scripts = re.findall(
        r'(?:<!--\s*(?:Google|GA|Analytics).*?-->\s*)?<script[^>]*(?:google|analytics|gtag|gtm)[^>]*>.*?</script>',
        body, re.DOTALL | re.IGNORECASE
    )

    # Clean up empty divs and excessive whitespace
    body = body.strip()

    return body, ga_scripts


def detect_page_type(filepath):
    """Detect whether a file is blog, feature, spanish, or core page."""
    rel_path = os.path.relpath(filepath, BASE_DIR)

    if rel_path.startswith("blog/") or "blog-" in rel_path:
        return "blog"
    elif rel_path.startswith("features/"):
        return "feature"
    elif rel_path.startswith("es/"):
        return "spanish"
    else:
        return "core"


def extract_page_title_text(html_content):
    """Extract the h1 text from the page for the hero section."""
    h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_content, re.DOTALL | re.IGNORECASE)
    if h1_match:
        # Strip HTML tags from inside h1
        return re.sub(r'<[^>]+>', '', h1_match.group(1)).strip()
    return ""


def extract_subtitle(html_content):
    """Try to extract a subtitle or first descriptive paragraph."""
    # Look for a .byline, .subtitle, or first p after h1
    byline_match = re.search(r'<p\s+class=["\'][^"\']*byline[^"\']*["\'][^>]*>(.*?)</p>', html_content, re.DOTALL | re.IGNORECASE)
    if byline_match:
        return re.sub(r'<[^>]+>', '', byline_match.group(1)).strip()

    subtitle_match = re.search(r'<p\s+class=["\'][^"\']*subtitle[^"\']*["\'][^>]*>(.*?)</p>', html_content, re.DOTALL | re.IGNORECASE)
    if subtitle_match:
        return re.sub(r'<[^>]+>', '', subtitle_match.group(1)).strip()

    return ""


def clean_body_for_dark(body_content):
    """Override old light-mode inline styles to dark equivalents."""
    replacements = [
        # Background colors -> dark
        (r'background:\s*#fff(?:fff)?(?:\s*;)', 'background: var(--dark-bg);'),
        (r'background:\s*white(?:\s*;)', 'background: var(--dark-bg);'),
        (r'background-color:\s*#fff(?:fff)?(?:\s*;)', 'background-color: var(--dark-bg);'),
        (r'background-color:\s*white(?:\s*;)', 'background-color: var(--dark-bg);'),
        (r'background:\s*#f[0-9a-f]{5}(?:\s*;)', 'background: var(--dark-alt);'),
        (r'background:\s*#e[0-9a-f]{5}(?:\s*;)', 'background: var(--dark-alt);'),
        # Text colors -> white
        (r'color:\s*#333(?:333)?(?:\s*;)', 'color: var(--white);'),
        (r'color:\s*#222(?:222)?(?:\s*;)', 'color: var(--white);'),
        (r'color:\s*#000(?:000)?(?:\s*;)', 'color: var(--white);'),
        (r'color:\s*black(?:\s*;)', 'color: var(--white);'),
        (r'color:\s*#555(?:555)?(?:\s*;)', 'color: rgba(255, 255, 255, 0.75);'),
        (r'color:\s*#666(?:666)?(?:\s*;)', 'color: rgba(255, 255, 255, 0.65);'),
        (r'color:\s*#777(?:777)?(?:\s*;)', 'color: rgba(255, 255, 255, 0.6);'),
        (r'color:\s*#888(?:888)?(?:\s*;)', 'color: rgba(255, 255, 255, 0.55);'),
        (r'color:\s*#999(?:999)?(?:\s*;)', 'color: rgba(255, 255, 255, 0.5);'),
        # Blue headers -> orange or white
        (r'background:\s*linear-gradient\(135deg,\s*#0052cc[^)]*\)', 'background: linear-gradient(135deg, rgba(255, 107, 53, 0.08), rgba(0, 212, 255, 0.05))'),
        (r'background:\s*#0052cc(?:\s*;)', 'background: var(--dark-bg);'),
        (r'color:\s*#0052cc(?:\s*;)', 'color: var(--orange);'),
        # Borders
        (r'border(?:-bottom|-top|-left|-right)?:\s*1px\s+solid\s+#(?:e[0-9a-f]{5}|d[0-9a-f]{5}|ccc)(?:\s*;)', 'border: 1px solid rgba(255, 255, 255, 0.06);'),
        # Box shadows that reference light colors
        (r'box-shadow:\s*[^;]*rgba\(0,\s*0,\s*0,\s*0\.1\)[^;]*;', 'box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);'),
    ]

    result = body_content
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result


def strip_old_header_element(body):
    """Remove <header> elements that serve as page headers (not content headers)."""
    # Remove blog-header class headers
    body = re.sub(
        r'<header\s+class=["\']blog-header["\'][^>]*>.*?</header>',
        '', body, flags=re.DOTALL | re.IGNORECASE
    )
    # Remove standalone header with just h1/subtitle
    body = re.sub(
        r'<header\b[^>]*>\s*<h1\b.*?</header>',
        '', body, flags=re.DOTALL | re.IGNORECASE
    )
    return body


# ──────────────────────────────────────────────
# 3. PAGE REBUILDER
# ──────────────────────────────────────────────

def rebuild_page(filepath):
    """Read, parse, and rebuild an HTML file with the premium design."""
    rel_path = os.path.relpath(filepath, BASE_DIR)
    page_type = detect_page_type(filepath)
    is_spanish = (page_type == "spanish")

    with open(filepath, 'r', encoding='utf-8') as f:
        original = f.read()

    # Detect lang attribute
    lang_match = re.search(r'<html\s+lang=["\']([^"\']+)["\']', original, re.IGNORECASE)
    lang = lang_match.group(1) if lang_match else ("es-US" if is_spanish else "en-US")

    # Extract SEO elements from head
    title_tag, meta_tags, seo_links, jsonld_blocks, raw_head = extract_head_meta(original)

    # Extract page title text for hero
    page_title = extract_page_title_text(original)
    subtitle = extract_subtitle(original)

    # Extract body content
    body_content, ga_scripts = extract_body_content(original)

    # Strip old header elements from body
    body_content = strip_old_header_element(body_content)

    # Remove the h1 from body content (we'll put it in the hero)
    if page_title:
        body_content = re.sub(r'<h1\b[^>]*>.*?</h1>', '', body_content, count=1, flags=re.DOTALL | re.IGNORECASE)

    # Remove byline from body if it exists (we show it in hero)
    body_content = re.sub(
        r'<p\s+class=["\'][^"\']*byline[^"\']*["\'][^>]*>.*?</p>',
        '', body_content, count=1, flags=re.DOTALL | re.IGNORECASE
    )

    # Clean light-mode inline styles
    body_content = clean_body_for_dark(body_content)

    # Remove old header-like blocks that remain
    # Remove <header> ... </header> that might contain background:linear-gradient
    body_content = re.sub(
        r'<header\b[^>]*style="[^"]*background[^"]*"[^>]*>.*?</header>',
        '', body_content, flags=re.DOTALL | re.IGNORECASE
    )

    # Wrap content sections with reveal class
    # Add .reveal to h2 tags
    body_content = re.sub(
        r'<h2\b([^>]*)>',
        lambda m: '<h2' + m.group(1) + ' class="reveal">' if 'class=' not in m.group(1) else '<h2' + m.group(1).replace('class="', 'class="reveal ').replace("class='", "class='reveal ") + '>',
        body_content,
        flags=re.IGNORECASE
    )

    # Wrap <section> tags with reveal if they don't have it
    body_content = re.sub(
        r'<section\b([^>]*)>',
        lambda m: '<section' + m.group(1) + ' class="reveal">' if 'class=' not in m.group(1) else '<section' + m.group(1) + '>',
        body_content,
        flags=re.IGNORECASE
    )

    # Determine content wrapper class
    if page_type == "blog":
        wrapper_class = "article-layout content-section"
    else:
        wrapper_class = "content-section"

    # Build meta tags string — filter out charset and viewport since we hardcode them
    filtered_meta = [m for m in meta_tags
                     if 'charset=' not in m.lower()
                     and 'name="viewport"' not in m.lower()
                     and "name='viewport'" not in m.lower()]
    meta_str = "\n".join(f"    {m}" for m in filtered_meta)
    seo_links_str = "\n".join(f"    {l}" for l in seo_links)
    jsonld_str = "\n".join(f"    {j}" for j in jsonld_blocks)

    # Check if preconnect already in meta
    has_preconnect = any('fonts.googleapis.com' in m for m in meta_tags) or any('fonts.googleapis.com' in l for l in seo_links)

    # Build the hero section
    hero_html = f'''
<!-- ============ HERO ============ -->
<section class="page-hero">
    <div style="position:relative;z-index:10;max-width:900px;margin:0 auto;">
        <h1 class="reveal">{page_title if page_title else "AI Sales Pipeline"}</h1>'''

    if subtitle:
        hero_html += f'\n        <p class="subtitle reveal reveal-d1">{subtitle}</p>'

    hero_html += '''
    </div>
</section>

<div class="section-divider"></div>'''

    # Build the new page
    new_html = f'''<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {title_tag}
{meta_str}

{seo_links_str}

{GOOGLE_FONTS}

{TAILWIND_CDN}

{PREMIUM_CSS}

{jsonld_str}
</head>
<body>

{get_nav_html(is_spanish)}

{hero_html}

<!-- ============ MAIN CONTENT ============ -->
<div class="{wrapper_class}">
{body_content}
</div>

<div class="section-divider"></div>

<!-- ============ FINAL CTA ============ -->
<section style="padding:4rem 2rem;background:linear-gradient(135deg,rgba(255,107,53,0.12) 0%,rgba(255,90,31,0.08) 50%,rgba(0,212,255,0.06) 100%);text-align:center;">
    <div style="max-width:700px;margin:0 auto;">
        <h2 class="reveal" style="font-size:clamp(1.6rem,3vw,2.2rem);font-weight:800;margin-bottom:1rem;color:var(--white);">{"Listo para Empezar?" if is_spanish else "Ready to Get Started?"}</h2>
        <p class="reveal reveal-d1" style="color:rgba(255,255,255,0.6);font-size:1rem;margin-bottom:2rem;line-height:1.7;">
            {"Agenda tu consulta gratuita. Sin compromiso." if is_spanish else "Schedule your free consultation and demo. No obligation."}
        </p>
        <a href="https://aisalespipeline.com/#contact" class="btn-primary reveal reveal-d2" style="padding:1rem 2.5rem;font-size:1rem;">{"Agendar Demo Gratis" if is_spanish else "Book Your Free Consultation"}</a>
    </div>
</section>

{get_footer_html(is_spanish)}

{FOUNDER_BACKLINK}

{BOTTOM_SCRIPTS}

</body>
</html>
'''

    return new_html


# ──────────────────────────────────────────────
# 4. MAIN EXECUTION
# ──────────────────────────────────────────────

def collect_html_files():
    """Collect all HTML files to process."""
    files = []
    for root, dirs, filenames in os.walk(BASE_DIR):
        for fname in filenames:
            if fname.endswith('.html') and fname not in SKIP_FILES:
                full_path = os.path.join(root, fname)
                # Skip any .bak files
                if not full_path.endswith('.bak'):
                    files.append(full_path)
    # Deduplicate
    return sorted(set(files))


def main():
    files = collect_html_files()
    print(f"\n{'='*60}")
    print(f"  PREMIUM DESIGN UPGRADE")
    print(f"  Found {len(files)} HTML files to process")
    print(f"  Template: pricing.html (will NOT be modified)")
    print(f"{'='*60}\n")

    success_count = 0
    error_count = 0

    for filepath in files:
        rel_path = os.path.relpath(filepath, BASE_DIR)
        page_type = detect_page_type(filepath)

        try:
            # Create backup
            bak_path = filepath + ".bak"
            shutil.copy2(filepath, bak_path)

            # Rebuild
            new_html = rebuild_page(filepath)

            # Write
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_html)

            success_count += 1
            print(f"  [OK] {rel_path:<55} ({page_type})")

        except Exception as e:
            error_count += 1
            print(f"  [ERR] {rel_path:<55} -> {e}")

    print(f"\n{'='*60}")
    print(f"  COMPLETE: {success_count} upgraded, {error_count} errors")
    print(f"  Backups saved as *.bak alongside each file")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
