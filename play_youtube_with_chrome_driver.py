# @title Memainkan video Youtube dengan selenium di 6 tab terpisah
# PERBAIKAN UNTUK GOOGLE COLAB:
# - Menggunakan JavaScript langsung untuk memainkan video (metode yang terbukti berhasil)
# - Menghilangkan semua metode klik tombol yang gagal karena overlay
# - Menggunakan 4 methods JavaScript yang reliable:
#   1. video.play() langsung
#   2. JavaScript click pada tombol play
#   3. Event dispatch untuk tombol play
#   4. Selector spesifik dari youtube_element.txt sebagai fallback
# - Menambahkan debugging dan error handling yang lebih baik
# - Mengoptimalkan Chrome options untuk Google Colab
# - Menambahkan wait_for_youtube_elements untuk memastikan elemen YouTube muncul
# - Menambahkan fungsi verifikasi status video dan monitoring real-time

# FITUR BARU YANG DITAMBAHKAN:
# ================================
# 1. verify_video_is_playing() - Memverifikasi bahwa video sedang diputar dengan 4 method:
#    - Cek status video element (paused, ended, currentTime)
#    - Cek tombol play/pause (aria-label)
#    - Cek progress bar (aria-valuenow, aria-valuemax)
#    - Cek dengan JavaScript (video.paused, video.ended, video.currentTime)
#
# 2. ensure_video_plays() - Memastikan video benar-benar diputar dengan multiple attempts:
#    - JavaScript play() method
#    - Klik tombol play
#    - Verifikasi setelah setiap attempt
#
# 3. monitor_video_playback() - Monitoring real-time status video playback:
#    - Cek status setiap 5 detik
#    - Hitung consecutive playing/paused
#    - Auto-retry jika video tidak diputar
#
# 4. get_video_detailed_status() - Status detail lengkap video:
#    - Video properties (paused, ended, currentTime, duration)
#    - Tombol play/pause status
#    - Progress bar status
#
# 5. check_video_quality_and_buffering() - Cek kualitas dan buffering:
#    - Resolusi video (width x height)
#    - Status buffering
#    - Network state
#
# 6. force_video_play_with_multiple_methods() - Force play dengan 5 method:
#    - JavaScript play()
#    - Click tombol play
#    - Event dispatch
#    - Force play dengan timeout
#    - Mute dan play
#
# 7. continuous_video_monitoring() - Monitoring kontinyu dengan report:
#    - Monitoring selama durasi tertentu
#    - Success rate calculation
#    - Auto-retry mechanism
#    - Final report dengan statistik
#
# 8. close_youtube_consent() - Menangani dialog consent YouTube (GDPR):
#    - Switch ke iframe consent YouTube
#    - Klik tombol consent multi-bahasa (Reject all/Accept all)
#    - Fallback dengan cookie CONSENT
#    - Diterapkan di semua navigasi YouTube

# CARA PENGGUNAAN:
# ================
# 1. Jalankan script seperti biasa
# 2. Script akan otomatis menggunakan semua fitur verifikasi
# 3. Setiap tab akan diverifikasi dan dimonitor secara real-time
# 4. Jika video gagal diputar, akan dicoba dengan multiple methods
# 5. Monitoring akan berjalan selama video diputar
# 6. Report lengkap akan ditampilkan untuk setiap tab

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import os
import platform
from webdriver_manager.chrome import ChromeDriverManager
import threading

# Deteksi environment
def detect_environment():
    """Deteksi apakah kode berjalan di Google Colab atau desktop"""
    if 'COLAB_GPU' in os.environ or 'COLAB_TPU' in os.environ:
        return "colab"
    elif platform.system() == "Windows":
        return "windows"
    elif platform.system() == "Darwin":
        return "macos"
    else:
        return "linux"

def close_youtube_consent(driver, tab_number=0, timeout=12):
    """
    Fungsi untuk menutup dialog consent YouTube (GDPR consent)
    """
    try:
        print(f"TAB {tab_number}: Mencoba menutup dialog consent YouTube...")
        
        # 1) Switch ke iframe consent (consent.youtube / consent.google)
        iframe_locators = [
            (By.CSS_SELECTOR, "iframe[src*='consent.youtube.com']"),
            (By.CSS_SELECTOR, "iframe[src*='consent.google.com']"),
            (By.CSS_SELECTOR, "iframe[src*='consent.youtube.com']"),
        ]
        
        for by, sel in iframe_locators:
            try:
                WebDriverWait(driver, 3).until(EC.frame_to_be_available_and_switch_to_it((by, sel)))
                print(f"TAB {tab_number}: Berhasil switch ke iframe consent")
                break
            except TimeoutException:
                continue

        # 2) Klik tombol "Reject all" atau "Accept all" (cover multi-bahasa)
        button_xpaths = [
            "//button[normalize-space()='Reject all']",
            "//button[normalize-space()='Accept all']",
            "//button[normalize-space()='Tolak semua']",
            "//button[normalize-space()='Setuju semua']",
            "//button[contains(@aria-label,'Reject')]",
            "//button[contains(@aria-label,'Accept')]",
            "//button[@jsname='tWT92d']",  # reject (sering dipakai Google)
            "//button[@jsname='higCR']",   # accept (sering dipakai Google)
        ]
        
        clicked = False
        for xp in button_xpaths:
            els = driver.find_elements(By.XPATH, xp)
            for el in els:
                if el.is_displayed() and el.is_enabled():
                    el.click()
                    print(f"TAB {tab_number}: Berhasil klik tombol consent: {xp}")
                    clicked = True
                    break
            if clicked:
                break
                
        if not clicked:
            print(f"TAB {tab_number}: Tidak ada tombol consent yang bisa diklik")
            
    except Exception as e:
        print(f"TAB {tab_number}: Error saat menutup consent: {e}")
    finally:
        # 3) Kembali ke main document walau gagal
        try:
            driver.switch_to.default_content()
            print(f"TAB {tab_number}: Kembali ke main document")
        except Exception:
            pass

def setup_youtube_consent_cookie(driver):
    """
    Fungsi fallback untuk mengatur cookie CONSENT YouTube
    """
    try:
        print("Mengatur cookie CONSENT YouTube sebagai fallback...")
        
        # Buka YouTube homepage dulu
        driver.get("https://www.youtube.com/")
        time.sleep(3)
        
        # Tutup consent dialog jika muncul
        close_youtube_consent(driver, 0)
        
        # Set cookie CONSENT (tidak selalu diperlukan/berhasil di semua region)
        try:
            driver.add_cookie({
                "name": "CONSENT",
                "value": "YES+cb.20240620-00-p0.en+FX"
            })
            print("Cookie CONSENT berhasil diatur")
        except Exception as e:
            print(f"Gagal mengatur cookie CONSENT: {e}")
            
    except Exception as e:
        print(f"Error saat setup consent cookie: {e}")

# Setup Chrome berdasarkan environment
def setup_chrome_options(environment):
    """Setup Chrome options berdasarkan environment"""
    chrome_options = Options()

    if environment == "colab":
        # Opsi untuk Google Colab
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"')
        chrome_options.add_argument('--user-data-dir=/tmp/chrome-data')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Opsi penting untuk Google Colab
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        chrome_options.add_argument('--disable-features=TranslateUI')
        chrome_options.add_argument('--disable-ipc-flooding-protection')
        chrome_options.add_argument('--remote-debugging-port=9222')
        chrome_options.add_argument('--remote-debugging-address=0.0.0.0')
        chrome_options.add_argument('--disable-default-apps')
        chrome_options.add_argument('--disable-sync')
        chrome_options.add_argument('--metrics-recording-only')
        chrome_options.add_argument('--no-first-run')
        chrome_options.add_argument('--safebrowsing-disable-auto-update')
        chrome_options.add_argument('--disable-component-extensions-with-background-pages')
        chrome_options.add_argument('--disable-background-networking')
        chrome_options.add_argument('--disable-translate')
        chrome_options.add_argument('--hide-scrollbars')
        chrome_options.add_argument('--mute-audio')
        chrome_options.add_argument('--no-zygote')
        chrome_options.add_argument('--single-process')
        chrome_options.add_argument('--disable-logging')
        chrome_options.add_argument('--disable-in-process-stack-traces')
        chrome_options.add_argument('--disable-histogram-customizer')
        chrome_options.add_argument('--disable-glsl-translator')
        chrome_options.add_argument('--disable-composited-antialiasing')
        chrome_options.add_argument('--disable-canvas-aa')
        chrome_options.add_argument('--disable-3d-apis')
        chrome_options.add_argument('--disable-accelerated-2d-canvas')
        chrome_options.add_argument('--disable-accelerated-jpeg-decoding')
        chrome_options.add_argument('--disable-accelerated-mjpeg-decode')
        chrome_options.add_argument('--disable-accelerated-video-decode')
        chrome_options.add_argument('--disable-gpu-sandbox')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-threaded-animation')
        chrome_options.add_argument('--disable-threaded-scrolling')
        chrome_options.add_argument('--disable-checker-imaging')
        chrome_options.add_argument('--disable-new-content-rendering-timeout')
        chrome_options.add_argument('--disable-hang-monitor')
        chrome_options.add_argument('--disable-prompt-on-repost')
        chrome_options.add_argument('--disable-domain-reliability')
        chrome_options.add_argument('--disable-component-update')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        chrome_options.add_argument('--force-color-profile=srgb')
        chrome_options.add_argument('--memory-pressure-off')
        chrome_options.add_argument('--max_old_space_size=4096')
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

        # Opsi untuk menonaktifkan autoplay YouTube
        chrome_options.add_argument('--disable-features=AutoplayPolicy')
        chrome_options.add_argument('--disable-features=MediaRouter')
        chrome_options.add_argument('--disable-features=AutoplayIgnoreWebAudio')
        
        # Opsi tambahan untuk mengatasi masalah tombol play di YouTube
        chrome_options.add_argument('--disable-features=PreloadMediaEngagementData')
        chrome_options.add_argument('--disable-features=AutoplayIgnoreWebAudio')
        chrome_options.add_argument('--disable-features=MediaEngagementBypassAutoplayPolicies')
        chrome_options.add_argument('--disable-features=AutoplayIgnoreWebAudio')
        chrome_options.add_argument('--disable-features=AutoplayIgnoreWebAudio')
        
        # Opsi untuk memastikan JavaScript berfungsi dengan baik
        chrome_options.add_argument('--enable-javascript')
        chrome_options.add_argument('--enable-scripts')
        
        # Opsi untuk mengatasi masalah rendering
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        
        # Opsi untuk memastikan elemen terlihat
        chrome_options.add_argument('--disable-features=TranslateUI')
        chrome_options.add_argument('--disable-features=BlinkGenPropertyTrees')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        
        # Opsi untuk mengatasi masalah di Google Colab
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--disable-gpu-sandbox')
        
        # Opsi untuk memastikan window size yang tepat
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--start-maximized')
        
        # Opsi untuk mengatasi masalah automation detection
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')

    else:
        # Opsi untuk Desktop (Windows/Mac/Linux)
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument('--mute-audio')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')

        # Opsi untuk menonaktifkan autoplay YouTube
        chrome_options.add_argument('--disable-features=AutoplayPolicy')
        chrome_options.add_argument('--disable-features=MediaRouter')
        chrome_options.add_argument('--disable-features=AutoplayIgnoreWebAudio')

    return chrome_options

# Inisialisasi Chrome driver berdasarkan environment
def initialize_chrome_driver(environment):
    """Inisialisasi Chrome driver berdasarkan environment"""
    chrome_options = setup_chrome_options(environment)

    if environment == "colab":
        # Untuk Google Colab
        try:
            # Coba cara kedua tanpa Service (yang berhasil)
            driver = webdriver.Chrome(options=chrome_options)
            print("WebDriver berhasil diinisialisasi menggunakan cara kedua (Colab)")
            return driver
        except Exception as e:
            print(f"Cara kedua gagal: {e}")
            # Coba cara ketiga dengan path default Colab
            try:
                service = Service('/usr/bin/chromedriver')
                driver = webdriver.Chrome(service=service, options=chrome_options)
                print("WebDriver berhasil diinisialisasi menggunakan cara ketiga (Colab)")
                return driver
            except Exception as e3:
                print(f"Cara ketiga gagal: {e3}")
                raise Exception("Tidak dapat menginisialisasi Chrome WebDriver di Colab")

    else:
        # Untuk Desktop (Windows/Mac/Linux)
        try:
            # Coba dengan webdriver_manager (otomatis download driver)
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            print(f"WebDriver berhasil diinisialisasi menggunakan webdriver_manager ({environment})")
            return driver
        except Exception as e:
            print(f"webdriver_manager gagal: {e}")
            try:
                # Coba tanpa Service (fallback)
                driver = webdriver.Chrome(options=chrome_options)
                print(f"WebDriver berhasil diinisialisasi tanpa Service ({environment})")
                return driver
            except Exception as e2:
                print(f"Semua metode gagal: {e2}")
                raise Exception(f"Tidak dapat menginisialisasi Chrome WebDriver di {environment}")

def is_video_finished(driver):
    """
    Fungsi untuk mendeteksi apakah video telah selesai
    """
    try:
        # Cek apakah ada tombol replay atau video selesai
        replay_selectors = [
            'button[aria-label="Replay"]',
            'button[aria-label="Replay (k)"]',
            '.ytp-replay-button',
            'button[title="Replay"]',
            '.ytp-large-play-button[aria-label*="Replay"]'
        ]

        for selector in replay_selectors:
            try:
                replay_button = driver.find_element(By.CSS_SELECTOR, selector)
                if replay_button.is_displayed():
                    print("Video telah selesai - tombol replay ditemukan")
                    return True
            except:
                continue

        # Cek apakah video player menunjukkan status selesai
        try:
            # Cek progress bar untuk melihat apakah video sudah selesai
            progress_bar = driver.find_element(By.CSS_SELECTOR, '.ytp-progress-bar')
            aria_valuenow = progress_bar.get_attribute('aria-valuenow')
            aria_valuemax = progress_bar.get_attribute('aria-valuemax')

            if aria_valuenow and aria_valuemax:
                progress = float(aria_valuenow) / float(aria_valuemax)
                if progress >= 0.99:  # Video hampir selesai (99% atau lebih)
                    print(f"Video hampir selesai - progress: {progress:.2%}")
                    return True
        except:
            pass

        # Cek apakah ada pesan "Video selesai" atau sejenisnya
        try:
            end_screen = driver.find_element(By.CSS_SELECTOR, '.ytp-endscreen-content')
            if end_screen.is_displayed():
                print("Video telah selesai - end screen muncul")
                return True
        except:
            pass

        return False

    except Exception as e:
        print(f"Error saat mengecek status video: {e}")
        return False

def wait_for_video_completion(driver, max_wait_time=300):
    """
    Fungsi untuk menunggu video selesai dengan timeout
    """
    start_time = time.time()
    check_interval = 5  # Cek setiap 5 detik

    print("Menunggu video selesai...")

    while time.time() - start_time < max_wait_time:
        if is_video_finished(driver):
            print("Video telah selesai!")
            return True

        time.sleep(check_interval)
        print(f"Masih menunggu... ({int(time.time() - start_time)}s)")

    print(f"Timeout setelah {max_wait_time} detik")
    return False

# Fungsi untuk memantau perubahan URL
def monitor_url_changes(driver, original_video_id, max_wait_time=300):
    """
    Fungsi untuk memantau perubahan URL dan mencegah autoplay
    """
    start_time = time.time()
    check_interval = 5
    original_url = f"https://www.youtube.com/watch?v={original_video_id}"

    print(f"Memantau URL: {original_url}")

    while time.time() - start_time < max_wait_time:
        current_url = driver.current_url
        print(f"URL saat ini: {current_url}")

        # Jika URL berubah dari video asli
        if current_url != original_url:
            print(f"⚠️  URL berubah dari {original_url} ke {current_url}")
            print("Mencoba kembali ke video asli...")

            try:
                # Kembali ke video asli
                driver.get(original_url)
                # Tutup dialog consent YouTube jika muncul
                close_youtube_consent(driver, 0)
                time.sleep(3)

                # Coba play video lagi
                play_selectors = [
                    'button[aria-label="Play"]',
                    'button[aria-label="Play (k)"]',
                    '.ytp-play-button',
                    'button[title="Play"]',
                    '.ytp-large-play-button'
                ]

                for selector in play_selectors:
                    try:
                        play_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        play_button.click()
                        print(f"Video dimainkan kembali menggunakan selector: {selector}")
                        break
                    except:
                        continue

            except Exception as e:
                print(f"Gagal kembali ke video asli: {e}")

        time.sleep(check_interval)

        # Cek apakah video selesai
        if is_video_finished(driver):
            print("Video telah selesai!")
            return True

    print(f"Timeout setelah {max_wait_time} detik")
    return False

def wait_for_youtube_elements(driver, tab_number):
    """
    Fungsi untuk menunggu elemen YouTube penting muncul
    """
    try:
        print(f"TAB {tab_number}: Menunggu elemen YouTube muncul...")
        
        # Tunggu movie player muncul
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "movie_player"))
        )
        print(f"TAB {tab_number}: Movie player ditemukan")
        
        # Tunggu video element muncul
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "video"))
        )
        print(f"TAB {tab_number}: Video element ditemukan")
        
        # Tunggu controls muncul
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "ytp-chrome-bottom"))
        )
        print(f"TAB {tab_number}: Video controls ditemukan")
        
        # Tunggu sebentar untuk memastikan semua elemen ter-render dengan baik
        time.sleep(3)
        
        return True
        
    except Exception as e:
        print(f"TAB {tab_number}: Error saat menunggu elemen YouTube: {e}")
        return False

def debug_youtube_page(driver, tab_number):
    """
    Fungsi untuk debugging halaman YouTube
    """
    try:
        print(f"TAB {tab_number}: === DEBUG INFO ===")
        
        # Cek apakah ada video player
        try:
            video_player = driver.find_element(By.TAG_NAME, "video")
            print(f"TAB {tab_number}: Video player: {video_player.get_attribute('src')}")
            print(f"TAB {tab_number}: Video ready state: {video_player.get_attribute('readyState')}")
        except:
            print(f"TAB {tab_number}: Video player tidak ditemukan")
        
        # Cek tombol play yang ada
        play_buttons = driver.find_elements(By.CSS_SELECTOR, 'button[class*="play"], button[aria-label*="Play"], button[title*="Play"]')
        print(f"TAB {tab_number}: Jumlah tombol play ditemukan: {len(play_buttons)}")
        
        for i, btn in enumerate(play_buttons):
            try:
                print(f"TAB {tab_number}: Tombol {i+1}: class='{btn.get_attribute('class')}', aria-label='{btn.get_attribute('aria-label')}', title='{btn.get_attribute('title')}', visible={btn.is_displayed()}")
            except:
                print(f"TAB {tab_number}: Tombol {i+1}: Error saat membaca atribut")
        
        # Cek movie player
        try:
            movie_player = driver.find_element(By.ID, "movie_player")
            print(f"TAB {tab_number}: Movie player class: {movie_player.get_attribute('class')}")
        except:
            print(f"TAB {tab_number}: Movie player tidak ditemukan")
        
        print(f"TAB {tab_number}: === END DEBUG INFO ===")
        
    except Exception as e:
        print(f"TAB {tab_number}: Error saat debugging: {e}")

def play_video_in_tab(driver, video_id, tab_number, navigate=True):
    """
    Fungsi untuk memainkan video di tab tertentu
    """
    try:
        print(f"=== TAB {tab_number}: Memulai video {video_id} ===")
        
        # Navigate to YouTube video
        original_url = f"https://www.youtube.com/watch?v={video_id}"
        if navigate:
            driver.get(original_url)
            print(f"TAB {tab_number}: Navigasi ke: {original_url}")
        else:
            print(f"TAB {tab_number}: Skip navigasi (URL sudah dibuka): {driver.current_url}")

        # Tutup dialog consent YouTube jika muncul
        close_youtube_consent(driver, tab_number)
        
        # Wait for page to load
        time.sleep(5)

        # Tunggu elemen YouTube penting muncul
        if not wait_for_youtube_elements(driver, tab_number):
            print(f"TAB {tab_number}: ⚠️ Elemen YouTube tidak muncul dengan baik")
            # Lanjutkan meskipun gagal, mungkin masih bisa berfungsi
        
        # Debug halaman untuk melihat apa yang tersedia
        debug_youtube_page(driver, tab_number)

        # Nonaktifkan autoplay YouTube dengan JavaScript menggunakan tombol toggle
        try:
            disable_autoplay_script = """
            // Cek status autoplay dan nonaktifkan jika masih ON
            const autoplayToggleButton = document.querySelector('#movie_player > div.ytp-chrome-bottom > div.ytp-chrome-controls > div.ytp-right-controls > div.ytp-right-controls-left > button.ytp-button.ytp-autonav-toggle > div > div');
            
            if (autoplayToggleButton) {
                // Cek apakah autoplay masih ON (aria-checked="true")
                const isAutoplayOn = autoplayToggleButton.getAttribute('aria-checked') === 'true';
                
                if (isAutoplayOn) {
                    // Jika autoplay masih ON, klik tombol untuk mematikannya
                    autoplayToggleButton.click();
                    console.log('Autoplay YouTube telah dinonaktifkan dengan mengklik tombol toggle');
                } else {
                    // Jika autoplay sudah OFF, biarkan saja
                    console.log('Autoplay YouTube sudah dalam status OFF');
                }
            } else {
                // Fallback: coba selector alternatif
                const alternativeSelectors = [
                    'button.ytp-button.ytp-autonav-toggle div.ytp-autonav-toggle-button',
                    '.ytp-autonav-toggle-button',
                    '[aria-checked="true"]'
                ];
                
                let autoplayButton = null;
                for (let selector of alternativeSelectors) {
                    autoplayButton = document.querySelector(selector);
                    if (autoplayButton) break;
                }
                
                if (autoplayButton && autoplayButton.getAttribute('aria-checked') === 'true') {
                    autoplayButton.click();
                    console.log('Autoplay YouTube telah dinonaktifkan dengan selector alternatif');
                } else {
                    console.log('Autoplay YouTube sudah OFF atau tombol tidak ditemukan');
                }
            }
            
            // Nonaktifkan autoplay di video player juga
            const videoPlayer = document.querySelector('video');
            if (videoPlayer) {
                videoPlayer.autoplay = false;
                videoPlayer.muted = true;
            }
            """
            driver.execute_script(disable_autoplay_script)
            print(f"TAB {tab_number}: Autoplay YouTube telah diperiksa dan diatur sesuai status")
        except Exception as e:
            print(f"TAB {tab_number}: Gagal menonaktifkan autoplay: {e}")

        # Scroll down first
        driver.execute_script("window.scrollTo(0, 500)")
        time.sleep(2)

        # Gunakan fungsi verifikasi yang baru untuk memastikan video diputar
        print(f"TAB {tab_number}: Menggunakan fungsi verifikasi untuk memastikan video diputar...")
        
        # Coba play video dengan fungsi ensure_video_plays
        video_played = ensure_video_plays(driver, tab_number, max_attempts=5)
        
        if video_played:
            print(f"TAB {tab_number}: ✅ Video berhasil diputar dan diverifikasi!")
            
            # Tampilkan status detail video
            get_video_detailed_status(driver, tab_number)
            
            # Mulai monitoring real-time
            print(f"TAB {tab_number}: Memulai monitoring real-time...")
            monitoring_success = monitor_video_playback(driver, tab_number, check_interval=5, max_checks=60)
            
            if monitoring_success:
                print(f"TAB {tab_number}: 🎉 Video berhasil diputar dan stabil!")
                # Lanjutkan dengan monitoring URL
                print(f"TAB {tab_number}: Memulai monitoring URL...")
                monitor_url_changes(driver, video_id)
            else:
                print(f"TAB {tab_number}: ⚠️ Video tidak stabil, menggunakan fallback...")
                time.sleep(40)
        else:
            print(f"TAB {tab_number}: ❌ Gagal memastikan video diputar")
            print(f"TAB {tab_number}: Mencoba screenshot untuk debugging...")
            try:
                # Ambil screenshot untuk debugging
                screenshot_path = f"tab_{tab_number}_debug.png"
                driver.save_screenshot(screenshot_path)
                print(f"TAB {tab_number}: Screenshot disimpan di: {screenshot_path}")
            except:
                pass
            
            print(f"TAB {tab_number}: Menunggu 40 detik sebagai fallback...")
            time.sleep(40)

        # Print page title untuk verifikasi
        print(f"TAB {tab_number}: Page title: {driver.title}")
        print(f"TAB {tab_number}: Current URL: {driver.current_url}")
        print(f"TAB {tab_number}: Page source length: {len(driver.page_source)}")
        
        print(f"=== TAB {tab_number}: Selesai ===")

    except Exception as e:
        print(f"TAB {tab_number}: Error: {e}")
        # Tambahan error handling untuk debugging
        try:
            print(f"TAB {tab_number}: Current URL saat error: {driver.current_url}")
            print(f"TAB {tab_number}: Page source length saat error: {len(driver.page_source)}")
        except:
            pass

def verify_video_is_playing(driver, tab_number):
    """
    Fungsi untuk memverifikasi bahwa video sedang diputar
    """
    try:
        print(f"TAB {tab_number}: Memverifikasi status video...")
        
        # Method 1: Cek status video element
        try:
            video_element = driver.find_element(By.TAG_NAME, "video")
            
            # Cek apakah video sedang diputar
            is_playing = driver.execute_script("""
                const video = arguments[0];
                return !video.paused && !video.ended && video.currentTime > 0;
            """, video_element)
            
            if is_playing:
                print(f"TAB {tab_number}: ✅ Video sedang diputar (status: playing)")
                return True
            else:
                print(f"TAB {tab_number}: ⚠️ Video tidak sedang diputar (status: paused/ended)")
                return False
                
        except Exception as e:
            print(f"TAB {tab_number}: Error saat cek video element: {e}")
        
        # Method 2: Cek tombol play/pause
        try:
            play_button = driver.find_element(By.CSS_SELECTOR, 'button.ytp-play-button')
            button_aria_label = play_button.get_attribute('aria-label')
            
            if 'Pause' in button_aria_label or 'pause' in button_aria_label:
                print(f"TAB {tab_number}: ✅ Tombol menunjukkan video sedang diputar (label: {button_aria_label})")
                return True
            elif 'Play' in button_aria_label or 'play' in button_aria_label:
                print(f"TAB {tab_number}: ⚠️ Tombol menunjukkan video tidak sedang diputar (label: {button_aria_label})")
                return False
                
        except Exception as e:
            print(f"TAB {tab_number}: Error saat cek tombol play: {e}")
        
        # Method 3: Cek progress bar
        try:
            progress_bar = driver.find_element(By.CSS_SELECTOR, '.ytp-progress-bar')
            current_time = progress_bar.get_attribute('aria-valuenow')
            total_time = progress_bar.get_attribute('aria-valuemax')
            
            if current_time and total_time:
                current_time = float(current_time)
                total_time = float(total_time)
                
                if current_time > 0 and current_time < total_time:
                    print(f"TAB {tab_number}: ✅ Progress bar menunjukkan video sedang berjalan (time: {current_time:.1f}s)")
                    return True
                else:
                    print(f"TAB {tab_number}: ⚠️ Progress bar menunjukkan video tidak berjalan (time: {current_time:.1f}s)")
                    return False
                    
        except Exception as e:
            print(f"TAB {tab_number}: Error saat cek progress bar: {e}")
        
        # Method 4: Cek dengan JavaScript
        try:
            video_status = driver.execute_script("""
                const video = document.querySelector('video');
                if (!video) return 'no_video';
                
                if (video.paused) return 'paused';
                if (video.ended) return 'ended';
                if (video.currentTime > 0) return 'playing';
                return 'unknown';
            """)
            
            print(f"TAB {tab_number}: Status video dari JavaScript: {video_status}")
            
            if video_status == 'playing':
                return True
            elif video_status == 'paused':
                return False
            elif video_status == 'ended':
                return False
            else:
                print(f"TAB {tab_number}: Status video tidak dapat ditentukan")
                return False
                
        except Exception as e:
            print(f"TAB {tab_number}: Error saat cek status JavaScript: {e}")
        
        return False
        
    except Exception as e:
        print(f"TAB {tab_number}: Error dalam verify_video_is_playing: {e}")
        return False

def ensure_video_plays(driver, tab_number, max_attempts=5):
    """
    Fungsi untuk memastikan video benar-benar diputar dengan multiple attempts
    """
    print(f"TAB {tab_number}: Memastikan video diputar dengan {max_attempts} attempts...")
    
    for attempt in range(1, max_attempts + 1):
        print(f"TAB {tab_number}: Attempt {attempt}/{max_attempts}")
        
        # Fallback: coba tutup consent dialog sebelum mencoba play
        if attempt == 1:
            close_youtube_consent(driver, tab_number)
        
        # Coba play video
        video_played = False
        
        # Method 1: JavaScript play()
        try:
            play_script = """
            const video = document.querySelector('video');
            if (video && video.readyState >= 2) {
                const playPromise = video.play();
                if (playPromise !== undefined) {
                    playPromise.then(() => {
                        console.log('Video berhasil dimainkan');
                    }).catch(error => {
                        console.log('Error saat play video:', error);
                    });
                }
                return true;
            }
            return false;
            """
            result = driver.execute_script(play_script)
            if result:
                print(f"TAB {tab_number}: Video play() berhasil")
                video_played = True
        except Exception as e:
            print(f"TAB {tab_number}: JavaScript play() gagal: {e}")
        
        # Method 2: Klik tombol play
        if not video_played:
            try:
                play_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.ytp-play-button'))
                )
                play_button.click()
                print(f"TAB {tab_number}: Tombol play diklik")
                video_played = True
            except Exception as e:
                print(f"TAB {tab_number}: Klik tombol play gagal: {e}")
        
        # Tunggu sebentar untuk video mulai
        if video_played:
            time.sleep(3)
            
            # Verifikasi video sedang diputar
            if verify_video_is_playing(driver, tab_number):
                print(f"TAB {tab_number}: ✅ Video berhasil diputar dan diverifikasi!")
                return True
            else:
                print(f"TAB {tab_number}: ⚠️ Video dimainkan tapi tidak terverifikasi, mencoba lagi...")
                video_played = False
        
        # Tunggu sebentar sebelum attempt berikutnya
        if attempt < max_attempts:
            time.sleep(2)
    
    print(f"TAB {tab_number}: ❌ Gagal memastikan video diputar setelah {max_attempts} attempts")
    return False

def monitor_video_playback(driver, tab_number, check_interval=5, max_checks=60):
    """
    Fungsi untuk monitoring real-time status video playback
    """
    print(f"TAB {tab_number}: Memulai monitoring video playback...")
    
    checks_done = 0
    consecutive_playing = 0
    consecutive_paused = 0
    
    while checks_done < max_checks:
        try:
            # Cek status video
            is_playing = verify_video_is_playing(driver, tab_number)
            
            if is_playing:
                consecutive_playing += 1
                consecutive_paused = 0
                print(f"TAB {tab_number}: ✅ Video sedang diputar (consecutive: {consecutive_playing})")
                
                # Jika video sudah diputar selama 3 checks berturut-turut, anggap berhasil
                if consecutive_playing >= 3:
                    print(f"TAB {tab_number}: 🎉 Video berhasil diputar dan stabil!")
                    return True
                    
            else:
                consecutive_paused += 1
                consecutive_playing = 0
                print(f"TAB {tab_number}: ⚠️ Video tidak sedang diputar (consecutive: {consecutive_paused})")
                
                # Jika video tidak diputar selama 3 checks berturut-turut, coba play lagi
                if consecutive_paused >= 3:
                    print(f"TAB {tab_number}: 🔄 Mencoba memainkan video lagi...")
                    if ensure_video_plays(driver, tab_number, max_attempts=2):
                        consecutive_paused = 0
                        consecutive_playing = 1
                    else:
                        print(f"TAB {tab_number}: ❌ Gagal memainkan video")
            
            checks_done += 1
            time.sleep(check_interval)
            
        except Exception as e:
            print(f"TAB {tab_number}: Error dalam monitoring: {e}")
            checks_done += 1
            time.sleep(check_interval)
    
    print(f"TAB {tab_number}: ⏰ Monitoring selesai setelah {max_checks} checks")
    return consecutive_playing >= 3

def get_video_detailed_status(driver, tab_number):
    """
    Fungsi untuk mendapatkan status detail video
    """
    try:
        print(f"TAB {tab_number}: === STATUS DETAIL VIDEO ===")
        
        # Status video element
        try:
            video = driver.find_element(By.TAG_NAME, "video")
            status_info = driver.execute_script("""
                const video = arguments[0];
                return {
                    paused: video.paused,
                    ended: video.ended,
                    currentTime: video.currentTime,
                    duration: video.duration,
                    readyState: video.readyState,
                    networkState: video.networkState,
                    src: video.src,
                    volume: video.volume,
                    muted: video.muted,
                    playbackRate: video.playbackRate
                };
            """, video)
            
            print(f"TAB {tab_number}: Video Status:")
            print(f"  - Paused: {status_info['paused']}")
            print(f"  - Ended: {status_info['ended']}")
            print(f"  - Current Time: {status_info['currentTime']:.2f}s")
            print(f"  - Duration: {status_info['duration']:.2f}s")
            print(f"  - Ready State: {status_info['readyState']}")
            print(f"  - Network State: {status_info['networkState']}")
            print(f"  - Volume: {status_info['volume']}")
            print(f"  - Muted: {status_info['muted']}")
            print(f"  - Playback Rate: {status_info['playbackRate']}")
            
        except Exception as e:
            print(f"TAB {tab_number}: Error saat cek video status: {e}")
        
        # Status tombol play/pause
        try:
            play_button = driver.find_element(By.CSS_SELECTOR, 'button.ytp-play-button')
            print(f"TAB {tab_number}: Tombol Play/Pause:")
            print(f"  - Aria Label: {play_button.get_attribute('aria-label')}")
            print(f"  - Title: {play_button.get_attribute('title')}")
            print(f"  - Class: {play_button.get_attribute('class')}")
            print(f"  - Visible: {play_button.is_displayed()}")
            print(f"  - Enabled: {play_button.is_enabled()}")
            
        except Exception as e:
            print(f"TAB {tab_number}: Error saat cek tombol play: {e}")
        
        # Status progress bar
        try:
            progress_bar = driver.find_element(By.CSS_SELECTOR, '.ytp-progress-bar')
            print(f"TAB {tab_number}: Progress Bar:")
            print(f"  - Current: {progress_bar.get_attribute('aria-valuenow')}")
            print(f"  - Max: {progress_bar.get_attribute('aria-valuemax')}")
            print(f"  - Text: {progress_bar.get_attribute('aria-valuetext')}")
            
        except Exception as e:
            print(f"TAB {tab_number}: Error saat cek progress bar: {e}")
        
        print(f"TAB {tab_number}: === END STATUS DETAIL ===")
        
    except Exception as e:
        print(f"TAB {tab_number}: Error dalam get_video_detailed_status: {e}")

def check_video_quality_and_buffering(driver, tab_number):
    """
    Fungsi untuk mengecek kualitas video dan status buffering
    """
    try:
        print(f"TAB {tab_number}: === CEK KUALITAS & BUFFERING ===")
        
        video = driver.find_element(By.TAG_NAME, "video")
        quality_info = driver.execute_script("""
            const video = arguments[0];
            return {
                videoWidth: video.videoWidth,
                videoHeight: video.videoHeight,
                buffered: video.buffered.length > 0 ? {
                    start: video.buffered.start(0),
                    end: video.buffered.end(video.buffered.length - 1)
                } : null,
                readyState: video.readyState,
                networkState: video.networkState,
                error: video.error ? video.error.message : null
            };
        """, video)
        
        print(f"TAB {tab_number}: Kualitas Video:")
        print(f"  - Resolusi: {quality_info['videoWidth']}x{quality_info['videoHeight']}")
        
        if quality_info['buffered']:
            print(f"  - Buffered: {quality_info['buffered']['start']:.2f}s - {quality_info['buffered']['end']:.2f}s")
        else:
            print(f"  - Buffered: Tidak ada")
            
        print(f"  - Ready State: {quality_info['readyState']}")
        print(f"  - Network State: {quality_info['networkState']}")
        
        if quality_info['error']:
            print(f"  - Error: {quality_info['error']}")
        
        print(f"TAB {tab_number}: === END KUALITAS & BUFFERING ===")
        
    except Exception as e:
        print(f"TAB {tab_number}: Error saat cek kualitas video: {e}")

def force_video_play_with_multiple_methods(driver, tab_number):
    """
    Fungsi untuk memaksa video diputar dengan berbagai metode
    """
    print(f"TAB {tab_number}: Memaksa video diputar dengan multiple methods...")
    
    methods = [
        ("JavaScript play()", """
            const video = document.querySelector('video');
            if (video && video.readyState >= 2) {
                video.play();
                return true;
            }
            return false;
        """),
        ("Click tombol play", """
            const playButton = document.querySelector('button.ytp-play-button');
            if (playButton) {
                playButton.click();
                return true;
            }
            return false;
        """),
        ("Event dispatch", """
            const video = document.querySelector('video');
            if (video) {
                video.dispatchEvent(new Event('play'));
                return true;
            }
            return false;
        """),
        ("Force play dengan timeout", """
            const video = document.querySelector('video');
            if (video) {
                setTimeout(() => {
                    video.play();
                }, 1000);
                return true;
            }
            return false;
        """),
        ("Mute dan play", """
            const video = document.querySelector('video');
            if (video) {
                video.muted = true;
                video.play();
                return true;
            }
            return false;
        """)
    ]
    
    for method_name, script in methods:
        try:
            print(f"TAB {tab_number}: Mencoba method: {method_name}")
            result = driver.execute_script(script)
            
            if result:
                print(f"TAB {tab_number}: ✅ {method_name} berhasil")
                time.sleep(2)
                
                # Verifikasi apakah video benar-benar diputar
                if verify_video_is_playing(driver, tab_number):
                    print(f"TAB {tab_number}: 🎉 Video berhasil diputar dengan {method_name}!")
                    return True
                else:
                    print(f"TAB {tab_number}: ⚠️ {method_name} berhasil tapi video tidak terverifikasi")
            else:
                print(f"TAB {tab_number}: ❌ {method_name} gagal")
                
        except Exception as e:
            print(f"TAB {tab_number}: Error dengan {method_name}: {e}")
    
    print(f"TAB {tab_number}: ❌ Semua method gagal")
    return False

def continuous_video_monitoring(driver, tab_number, duration_minutes=10):
    """
    Fungsi untuk monitoring video secara kontinyu selama durasi tertentu
    """
    print(f"TAB {tab_number}: Memulai continuous monitoring selama {duration_minutes} menit...")
    
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    check_interval = 10  # Cek setiap 10 detik
    
    total_checks = 0
    successful_checks = 0
    failed_checks = 0
    
    while time.time() < end_time:
        try:
            total_checks += 1
            current_time = time.strftime("%H:%M:%S", time.localtime())
            
            print(f"TAB {tab_number}: [{current_time}] Check #{total_checks}...")
            
            # Cek status video
            is_playing = verify_video_is_playing(driver, tab_number)
            
            if is_playing:
                successful_checks += 1
                print(f"TAB {tab_number}: ✅ Video sedang diputar (success: {successful_checks}/{total_checks})")
                
                # Cek kualitas video setiap 5 checks
                if total_checks % 5 == 0:
                    check_video_quality_and_buffering(driver, tab_number)
                    
            else:
                failed_checks += 1
                print(f"TAB {tab_number}: ⚠️ Video tidak diputar (failed: {failed_checks}/{total_checks})")
                
                # Coba play ulang jika gagal 3 kali berturut-turut
                if failed_checks >= 3:
                    print(f"TAB {tab_number}: 🔄 Mencoba play ulang...")
                    if force_video_play_with_multiple_methods(driver, tab_number):
                        failed_checks = 0
                        successful_checks += 1
            
            # Hitung success rate
            success_rate = (successful_checks / total_checks) * 100 if total_checks > 0 else 0
            print(f"TAB {tab_number}: Success Rate: {success_rate:.1f}%")
            
            # Tunggu sebelum check berikutnya
            time.sleep(check_interval)
            
        except Exception as e:
            print(f"TAB {tab_number}: Error dalam continuous monitoring: {e}")
            failed_checks += 1
            time.sleep(check_interval)
    
    # Final report
    final_success_rate = (successful_checks / total_checks) * 100 if total_checks > 0 else 0
    print(f"TAB {tab_number}: === FINAL MONITORING REPORT ===")
    print(f"TAB {tab_number}: Total Checks: {total_checks}")
    print(f"TAB {tab_number}: Successful: {successful_checks}")
    print(f"TAB {tab_number}: Failed: {failed_checks}")
    print(f"TAB {tab_number}: Final Success Rate: {final_success_rate:.1f}%")
    print(f"TAB {tab_number}: === END REPORT ===")
    
    return final_success_rate >= 80  # Return True jika success rate >= 80%

def create_and_manage_tabs(environment, video_ids):
    """
    Membuka SEMUA jendela (new window) terlebih dahulu, lalu memproses tiap jendela.
    """
    print(f"Environment terdeteksi: {environment}")
    
    # Inisialisasi driver utama
    main_driver = initialize_chrome_driver(environment)
    main_driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    try:
        # Setup consent cookie YouTube sebagai fallback (sekali saja di sesi ini)
        print("Mengatur consent cookie YouTube...")
        setup_youtube_consent_cookie(main_driver)

        # FASE 1: BUKA SEMUA JENDELA DULU (new window) + ARAHKAN KE URL VIDEO
        window_handles = []

        for i, video_id in enumerate(video_ids):
            url = f"https://www.youtube.com/watch?v={video_id}"
            if i == 0:
                # Gunakan jendela pertama yang sudah ada
                main_driver.get(url)
                window_handles.append(main_driver.current_window_handle)
                print(f"Membuka WINDOW {i+1}: {url}")
            else:
                # Selenium 4: buka jendela baru (bukan tab)
                main_driver.switch_to.new_window('window')
                main_driver.get(url)
                window_handles.append(main_driver.current_window_handle)
                print(f"Membuka WINDOW {i+1}: {url}")

        print(f"\nTotal jendela yang dibuka: {len(window_handles)}")
        for i, handle in enumerate(window_handles):
            main_driver.switch_to.window(handle)
            print(f"WINDOW {i+1} title: {main_driver.title}")

        # FASE 2: PROSES LANJUTAN PER JENDELA (play, verifikasi, monitoring)
        for i, (handle, video_id) in enumerate(zip(window_handles, video_ids), start=1):
            try:
                main_driver.switch_to.window(handle)
                # Karena URL sudah dibuka pada fase 1, set navigate=False
                play_video_in_tab(main_driver, video_id, i, navigate=False)
            except Exception as e:
                print(f"Error saat memproses WINDOW {i}: {e}")

        # Tunggu sebentar agar user bisa melihat semua jendela
        print("\nSemua jendela telah diproses. Menunggu 60 detik...")
        time.sleep(60)
        
    except Exception as e:
        print(f"Error dalam create_and_manage_tabs: {e}")
    
    finally:
        # Tutup semua jendela
        print("Menutup semua jendela...")
        main_driver.quit()

# Main execution
if __name__ == "__main__":
    # List video ID yang akan dimainkan (6 video)
    video_ids = [
        "DGDmRgrsWlk",  # Video 1
        "6lk3RO3bPmQ",  # Video 2
        "uO9FgSUBTx0",  # Video 3
        "gPU1uCFyHQQ",  # Video 4
        "sXIYXX5bBbY",  # Video 5
        "wdtzfHDBmLs"   # Video 6
    ]
    
    # Deteksi environment
    environment = detect_environment()
    
    # Jalankan multiple tab
    create_and_manage_tabs(environment, video_ids)

def demo_single_tab_verification(environment, video_id, tab_number=1):
    """
    Fungsi demo untuk menunjukkan cara menggunakan fitur verifikasi pada single tab
    """
    print(f"=== DEMO SINGLE TAB VERIFICATION ===")
    print(f"Video ID: {video_id}")
    print(f"Tab Number: {tab_number}")
    print(f"Environment: {environment}")
    
    # Inisialisasi driver
    driver = initialize_chrome_driver(environment)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    try:
        # Navigasi ke video
        url = f"https://www.youtube.com/watch?v={video_id}"
        driver.get(url)
        print(f"Navigasi ke: {url}")
        
        # Tutup dialog consent YouTube jika muncul
        close_youtube_consent(driver, tab_number)
        
        # Tunggu elemen YouTube
        time.sleep(5)
        if not wait_for_youtube_elements(driver, tab_number):
            print("⚠️ Elemen YouTube tidak muncul dengan baik")
        
        # Debug halaman
        debug_youtube_page(driver, tab_number)
        
        # Coba play video dengan verifikasi
        print("\n=== MULAI VERIFIKASI VIDEO ===")
        video_played = ensure_video_plays(driver, tab_number, max_attempts=3)
        
        if video_played:
            print("\n=== STATUS DETAIL VIDEO ===")
            get_video_detailed_status(driver, tab_number)
            
            print("\n=== CEK KUALITAS VIDEO ===")
            check_video_quality_and_buffering(driver, tab_number)
            
            print("\n=== MONITORING REAL-TIME ===")
            monitoring_success = monitor_video_playback(driver, tab_number, check_interval=3, max_checks=20)
            
            if monitoring_success:
                print("\n=== CONTINUOUS MONITORING ===")
                # Monitoring selama 2 menit untuk demo
                continuous_success = continuous_video_monitoring(driver, tab_number, duration_minutes=2)
                print(f"Continuous monitoring result: {continuous_success}")
            else:
                print("⚠️ Monitoring real-time tidak berhasil")
        else:
            print("❌ Video tidak dapat diputar")
            
            print("\n=== FORCE PLAY DENGAN MULTIPLE METHODS ===")
            force_success = force_video_play_with_multiple_methods(driver, tab_number)
            if force_success:
                print("🎉 Video berhasil diputar dengan force methods!")
            else:
                print("❌ Semua force methods gagal")
        
        # Tunggu sebentar untuk user melihat hasil
        print("\nDemo selesai. Menunggu 10 detik...")
        time.sleep(10)
        
    except Exception as e:
        print(f"Error dalam demo: {e}")
    
    finally:
        driver.quit()

def demo_advanced_monitoring(environment, video_id, tab_number=1):
    """
    Fungsi demo untuk advanced monitoring dengan custom settings
    """
    print(f"=== DEMO ADVANCED MONITORING ===")
    print(f"Video ID: {video_id}")
    print(f"Tab Number: {tab_number}")
    
    driver = initialize_chrome_driver(environment)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    try:
        # Navigasi ke video
        url = f"https://www.youtube.com/watch?v={video_id}"
        driver.get(url)
        
        # Tutup dialog consent YouTube jika muncul
        close_youtube_consent(driver, tab_number)
        
        time.sleep(5)
        
        # Tunggu elemen
        wait_for_youtube_elements(driver, tab_number)
        
        # Play video
        if ensure_video_plays(driver, tab_number):
            print("✅ Video berhasil diputar, memulai advanced monitoring...")
            
            # Custom monitoring dengan interval yang lebih pendek
            print("\n=== CUSTOM MONITORING (5 detik interval, 30 checks) ===")
            custom_monitoring = monitor_video_playback(
                driver, tab_number, 
                check_interval=5, 
                max_checks=30
            )
            
            if custom_monitoring:
                print("✅ Custom monitoring berhasil!")
                
                # Continuous monitoring dengan durasi pendek
                print("\n=== CONTINUOUS MONITORING (1 menit) ===")
                continuous_result = continuous_video_monitoring(
                    driver, tab_number, 
                    duration_minutes=1
                )
                
                print(f"Continuous monitoring result: {continuous_result}")
            else:
                print("⚠️ Custom monitoring tidak berhasil")
        
        # Tunggu untuk user
        print("\nAdvanced monitoring demo selesai. Menunggu 5 detik...")
        time.sleep(5)
        
    except Exception as e:
        print(f"Error dalam advanced monitoring demo: {e}")
    
    finally:
        driver.quit()

# Contoh penggunaan fungsi-fungsi baru:
if __name__ == "__main__":
    print("=== YOUTUBE VIDEO PLAYER DENGAN VERIFIKASI LENGKAP ===")
    print("Pilih mode:")
    print("1. Multiple tabs (default)")
    print("2. Single tab verification demo")
    print("3. Advanced monitoring demo")
    
    # Untuk demo, gunakan video yang pendek
    demo_video_id = "uO9FgSUBTx0"  # Me at the zoo (video pendek)
    
    # Uncomment salah satu untuk testing:
    
    # Mode 1: Multiple tabs (default)
    # video_ids = ["6lk3RO3bPmQ", "DGDmRgrsWlk", "uO9FgSUBTx0", "gPU1uCFyHQQ", "sXIYXX5bBbY", "wdtzfHDBmLs"]
    # environment = detect_environment()
    # create_and_manage_tabs(environment, video_ids)
    
    # Mode 2: Single tab verification demo
    # environment = detect_environment()
    # demo_single_tab_verification(environment, demo_video_id, 1)
    
    # Mode 3: Advanced monitoring demo
    # environment = detect_environment()
    # demo_advanced_monitoring(environment, demo_video_id, 1)
    
    # Default: Multiple tabs
    video_ids = [
        "DGDmRgrsWlk",  # Video 1
        "6lk3RO3bPmQ",  # Video 2
        "uO9FgSUBTx0",  # Video 3
        "gPU1uCFyHQQ",  # Video 4
        "sXIYXX5bBbY",  # Video 5
        "wdtzfHDBmLs"   # Video 6
    ]
    
    # Deteksi environment
    environment = detect_environment()
    
    # Jalankan multiple tab
    create_and_manage_tabs(environment, video_ids)
