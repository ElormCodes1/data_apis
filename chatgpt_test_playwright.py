# from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
# import time
# import os
# import random
# import subprocess
# import sys
# from dotenv import load_dotenv

# load_dotenv()

# EMAIL_VALUE = os.getenv('EMAIL_VALUE')
# PASSWORD_VALUE = os.getenv('PASSWORD_VALUE')
# PROMPT = "write a short piece about the sdr"

# # Check and install Playwright browsers if needed
# def ensure_browsers_installed():
#     """Check if Playwright browsers are installed, install if missing"""
#     try:
#         # Try to get browser path to check if installed
#         with sync_playwright() as p:
#             browser_path = p.chromium.executable_path
#             if browser_path and os.path.exists(browser_path):
#                 print("✓ Playwright browsers are installed")
#                 return True
#     except Exception:
#         pass
    
#     # Browsers not found, try to install programmatically
#     print("⚠ Playwright browsers not found. Attempting to install Chromium...")
#     try:
#         # Use subprocess to run playwright install command
#         result = subprocess.run(
#             [sys.executable, "-m", "playwright", "install", "chromium"],
#             capture_output=True,
#             text=True,
#             timeout=300  # 5 minute timeout
#         )
#         if result.returncode == 0:
#             print("✓ Chromium installed successfully")
#             return True
#         else:
#             print(f"⚠ Installation output: {result.stderr}")
#     except subprocess.TimeoutExpired:
#         print("⚠ Installation timed out")
#     except Exception as e:
#         print(f"⚠ Could not install automatically: {e}")
    
#     # If auto-install failed, show manual instructions
#     print("\n" + "="*80)
#     print("❌ PLAYWRIGHT BROWSERS NOT INSTALLED")
#     print("="*80)
#     print("Please install Playwright browsers manually by running:")
#     print("\n    playwright install chromium\n")
#     print("Or install all browsers:")
#     print("\n    playwright install\n")
#     print("Make sure you're in your virtual environment when running the command.")
#     print("="*80 + "\n")
#     return False

# # Simulate human behavior
# def simulate_human_behavior(page):
#     """Simulate human-like mouse movements and scrolling"""
#     try:
#         print("👤 Simulating human behavior...")
        
#         # Random small mouse movements
#         for _ in range(random.randint(2, 4)):
#             x_offset = random.randint(-50, 50)
#             y_offset = random.randint(-50, 50)
#             page.mouse.move(x_offset, y_offset)
#             #time.sleep(random.uniform(0.1, 0.3))
        
#         # Scroll down slightly
#         page.evaluate(f"window.scrollBy(0, {random.randint(50, 200)});")
#         #time.sleep(random.uniform(0.5, 1.0))
        
#         # Scroll back up
#         page.evaluate(f"window.scrollBy(0, -{random.randint(30, 100)});")
#         #time.sleep(random.uniform(0.3, 0.7))
        
#         print("✓ Human behavior simulation complete")
#     except Exception as e:
#         print(f"⚠ Could not simulate human behavior: {e}")

# # Helper function to find elements with better error handling
# def find_element_safe(page, xpath, description, timeout=30000, state='visible'):
#     """Find an element with better error handling and debugging"""
#     try:
#         print(f"🔍 Looking for {description}...")
#         locator = page.locator(f'xpath={xpath}')
        
#         # Try attached first, then visible
#         try:
#             locator.wait_for(state='attached', timeout=min(timeout // 2, 10000))
#             print(f"✓ {description} found in DOM")
#         except (PlaywrightTimeoutError, Exception):
#             print(f"⚠ {description} not in DOM yet, waiting for {state} state...")
#             locator.wait_for(state=state, timeout=timeout)
        
#         count = locator.count()
#         if count == 0:
#             raise Exception(f"{description} found but count is 0")
        
#         print(f"✓ Found {description} (count: {count})")
#         return locator.first if count > 1 else locator
        
#     except PlaywrightTimeoutError as e:
#         print(f"❌ Timeout waiting for {description}")
#         print(f"   XPath: {xpath}")
#         print(f"   Current URL: {page.url}")
#         print(f"   Page title: {page.title()}")
#         # Try to find similar elements for debugging
#         try:
#             # Try to find any button in the area
#             similar = page.locator('button').count()
#             print(f"   Total buttons on page: {similar}")
#         except:
#             pass
#         raise
#     except Exception as e:
#         print(f"❌ Error finding {description}: {e}")
#         print(f"   XPath: {xpath}")
#         print(f"   Current URL: {page.url}")
#         raise

# print("🚀 Starting Playwright browser with stealth mode...")

# # Ensure browsers are installed before proceeding
# if not ensure_browsers_installed():
#     sys.exit(1)

# try:
#     with sync_playwright() as p:
#         # Launch browser with stealth options
#         try:
#             browser = p.chromium.launch(
#                 headless=False,
#                 args=[
#                     '--disable-blink-features=AutomationControlled',
#                     '--disable-dev-shm-usage',
#                     '--no-sandbox',
#                     '--window-size=1920,1080',
#                 ]
#             )
#         except Exception as e:
#             error_str = str(e)
#             # Check for browser installation errors (shouldn't happen if check passed, but just in case)
#             if any(keyword in error_str for keyword in ["Executable doesn't exist", "BrowserType.launch"]):
#                 print("\n" + "="*80)
#                 print("❌ BROWSER LAUNCH FAILED")
#                 print("="*80)
#                 print("Browsers may not be properly installed. Try running:")
#                 print("\n    playwright install chromium --force\n")
#                 print("="*80 + "\n")
#                 sys.exit(1)
#             else:
#                 # For other errors, print the actual error for debugging
#                 print(f"❌ Error launching browser: {e}")
#                 raise
        
#         # Create context with stealth settings
#         context = browser.new_context(
#             viewport={'width': 1920, 'height': 1080},
#             user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
#             locale='en-US',
#             timezone_id='America/New_York',
#             # Playwright automatically handles most stealth features
#         )
        
#         # Add stealth scripts to context
#         context.add_init_script("""
#         // Remove webdriver property
#         Object.defineProperty(navigator, 'webdriver', {
#             get: () => undefined
#         });
        
#         // Add Chrome runtime object
#         window.navigator.chrome = {
#             runtime: {},
#             loadTimes: function() {},
#             csi: function() {},
#             app: {}
#         };
        
#         // Fix plugins
#         Object.defineProperty(navigator, 'plugins', {
#             get: () => [1, 2, 3, 4, 5]
#         });
        
#         // Fix languages
#         Object.defineProperty(navigator, 'languages', {
#             get: () => ['en-US', 'en']
#         });
        
#             // Remove automation from window object
#             delete window.navigator.__proto__.webdriver;
#         """)
        
#         page = context.new_page()
        
#         print("✓ Automation indicators removed")
#         print("🌐 Navigating to ChatGPT...")
#         page.goto('https://chatgpt.com', wait_until='networkidle', timeout=60000)
        
#         # Wait for page load
#         print("⏳ Waiting for page to load...")
#         print(f"Page URL: {page.url}")
#         print(f"Page title: {page.title()}")
        
#         # Wait for page to be interactive
#         page.wait_for_load_state('domcontentloaded')
#         page.wait_for_load_state('networkidle', timeout=30000)
#         #time.sleep(3)
        
#         # Verify we're on the right page
#         if 'chatgpt.com' not in page.url.lower():
#             print(f"⚠ Warning: Unexpected URL: {page.url}")
        
#         simulate_human_behavior(page)
        
#         try:
#             # Find and click the first element
#             first_button = find_element_safe(
#                 page, 
#                 '//*[@id="conversation-header-actions"]/div/div/button[1]',
#                 'first button',
#                 timeout=30000
#             )
#             first_button.click()
#             print("✓ First element clicked successfully")
            
#             # Wait for popup to appear after first click
#             print("⏳ Waiting for popup to appear...")
#             #time.sleep(3)
            
#             # Find and click the second element inside the popup
#             second_button = find_element_safe(
#                 page,
#                 '/html/body/div[4]/div/div/div/div/div/div/form/div[1]/button[1]',
#                 'second button in popup',
#                 timeout=30000
#             )
#             second_button.click()
#             print("✓ Second element clicked successfully")
            
#             # Function to fill email and proceed to password (can be called multiple times)
#             def fill_email_and_proceed_to_password():
#                 # Wait for the email input field to appear
#                 print("⏳ Waiting for email input field to appear...")
#                 #time.sleep(2)
                
#                 # Find and fill the email input field
#                 email_input = find_element_safe(
#                     page,
#                     '/html/body/div[2]/div[1]/div[1]/div[2]/c-wiz/main/div[2]/div/div/div[1]/form/span/section/div/div/div[1]/div[1]/div[1]/div/div[1]/input',
#                     'email input field',
#                     timeout=30000
#                 )
                
#                 # Clear any existing text and fill with the email value
#                 email_input.fill('')  # Clear first
#                 email_input.fill(EMAIL_VALUE)
#                 print(f"✓ Email input field filled with: {EMAIL_VALUE}")
                
#                 # Click the button after email input to proceed to password
#                 next_button = find_element_safe(
#                     page,
#                     '/html/body/div[2]/div[1]/div[1]/div[2]/c-wiz/main/div[3]/div/div[1]/div/div/button',
#                     'next button after email',
#                     timeout=30000
#                 )
#                 next_button.click()
#                 print("✓ Button clicked successfully")
                
#                 # Wait for the password input field to appear after clicking the button
#                 print("⏳ Waiting for password input field to appear...")
#                 #time.sleep(2)
            
#             # Retry loop: keep trying until password input is found
#             password_input = None
#             max_retries = 10  # Maximum number of retry attempts
#             retry_count = 0
            
#             while password_input is None and retry_count < max_retries:
#                 retry_count += 1
#                 print(f"\n🔄 Attempt {retry_count}/{max_retries} to find password input field...")
                
#                 # Fill email and proceed to password
#                 fill_email_and_proceed_to_password()
                
#                 # Try to find password input field
#                 try:
#                     password_input = find_element_safe(
#                         page,
#                         '/html/body/div[2]/div[1]/div[1]/div[2]/c-wiz/main/div[2]/div/div/div[1]/form/span/section[2]/div/div/div[1]/div[1]/div/div/div/div/div[1]/div/div[1]/input',
#                         'password input field',
#                         timeout=5000
#                     )
#                     print("✓ Found the password input field!")
#                     break  # Success! Exit the loop
#                 except PlaywrightTimeoutError:
#                     # Password input not found, try fallback element
#                     print("⚠ Password input field not found, trying fallback element...")
#                     try:
#                         fallback_element = find_element_safe(
#                             page,
#                             '/html/body/div[2]/div[1]/div[1]/div[2]/c-wiz/main/div[3]/div/div/div/div/div',
#                             'fallback element',
#                             timeout=10000
#                         )
#                         fallback_element.click()
#                         print("✓ Fallback element clicked successfully")
#                         #time.sleep(1)  # Small delay before retrying
#                         # Loop will continue and restart from email
#                     except Exception as e:
#                         print(f"⚠ Could not find fallback element: {e}")
#                         #time.sleep(2)  # Wait before retrying
#                         # Loop will continue and restart from email
            
#             # Check if we found the password input
#             if password_input is None:
#                 raise Exception(f"Could not find password input field after {max_retries} attempts")
            
#             # Fill the password input field
#             print("✓ Filling password input field...")
#             password_input.fill('')  # Clear first
#             password_input.fill(PASSWORD_VALUE)
#             print(f"✓ Password input field filled")
            
#             # Click the submit button after password is filled
#             #time.sleep(1)  # Small delay before looking for submit button
#             submit_button = find_element_safe(
#                 page,
#                 '/html/body/div[2]/div[1]/div[1]/div[2]/c-wiz/main/div[3]/div/div[1]/div/div/button',
#                 'submit button after password',
#                 timeout=30000
#             )
#             submit_button.click()
#             print("✓ Submit button clicked successfully")
            
#             # Wait for the page to load after login
#             print("⏳ Waiting for ChatGPT interface to load...")
#             #time.sleep(5)
            
#             # Wait for the textarea to appear
#             prompt_textarea = find_element_safe(
#                 page,
#                 '/html/body/div[1]/div[1]/div/div/div/main/div/div/div[2]/div[2]/div/div/div[2]/form/div[2]/div/div[1]/div/textarea',
#                 'prompt textarea',
#                 timeout=30000
#             )
            
#             # Clear any existing text and fill with the prompt
#             prompt_textarea.fill('')  # Clear first
#             prompt_textarea.fill(PROMPT)
#             print(f"✓ Prompt textarea filled with: {PROMPT}")
            
#             # Click the send button
#             #time.sleep(1)  # Small delay before looking for send button
#             send_button = find_element_safe(
#                 page,
#                 '/html/body/div[1]/div[1]/div/div[2]/div/main/div/div/div[2]/div[1]/div/div/div[2]/form/div[2]/div/div[3]/div/button',
#                 'send button',
#                 timeout=30000
#             )
#             send_button.click()
#             print("✓ Send button clicked successfully")
            
#             # Wait for the response to appear
#             print("⏳ Waiting for ChatGPT response...")
#             response_element = find_element_safe(
#                 page,
#                 '/html/body/div[1]/div[1]/div/div[2]/div/main/div/div/div[1]/div[2]/article[4]/div/div/div[1]/div/div/div',
#                 'response element',
#                 timeout=60000
#             )
#             print("✓ Response element found!")
            
#             # Get all text content from the response element (including all nested text)
#             response_text = response_element.inner_text()
            
#             # Fallback: if inner_text is empty, try text_content
#             if not response_text or response_text.strip() == '':
#                 response_text = response_element.text_content()
            
#             # If still empty, use evaluate to get all text
#             if not response_text or response_text.strip() == '':
#                 response_text = page.evaluate("""
#                     () => {
#                         const element = document.evaluate('/html/body/div[1]/div[1]/div/div[2]/div/main/div/div/div[1]/div[2]/article[4]/div/div/div[1]/div/div/div', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
#                         return element ? (element.innerText || element.textContent || '') : '';
#                     }
#                 """)
            
#             print("\n" + "="*80)
#             print("CHATGPT RESPONSE:")
#             print("="*80)
#             print(response_text)
#             print("="*80 + "\n")
            
#             # Keep browser open
#             try:
#                 #time.sleep(1000)
#             except KeyboardInterrupt:
#                 print("\n⚠ Interrupted by user")
        
#         except Exception as e:
#             print(f"❌ Error finding or clicking element: {e}")
#             print("Page content snippet (for debugging):")
#             try:
#                 print(page.content()[:1000])
#             except:
#                 pass
        
#         finally:
#             print("🧹 Closing browser...")
#             browser.close()
# except Exception as e:
#     # Check if this is a browser installation error that wasn't caught earlier
#     error_str = str(e)
#     if any(keyword in error_str for keyword in ["Executable doesn't exist", "BrowserType.launch"]):
#         print("\n" + "="*80)
#         print("❌ BROWSER LAUNCH FAILED")
#         print("="*80)
#         print("Browsers may not be properly installed. Try running:")
#         print("\n    playwright install chromium --force\n")
#         print("="*80 + "\n")
#         sys.exit(1)
#     else:
#         print(f"❌ Unexpected error: {e}")
#         import traceback
#         traceback.print_exc()
#         raise



# from patchright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
# import time
# import os
# import random
# import subprocess
# import sys
# from dotenv import load_dotenv

# load_dotenv()

# EMAIL_VALUE = os.getenv('EMAIL_VALUE')
# PASSWORD_VALUE = os.getenv('PASSWORD_VALUE')
# PROMPT = "write a short piece about the sdr"

# # Check and install Playwright browsers if needed (Patchright should handle this, but keep for safety)
# def ensure_browsers_installed():
#     """Check if Patchright browsers are installed, install if missing"""
#     try:
#         with sync_playwright() as p:
#             browser_path = p.chromium.executable_path
#             if browser_path and os.path.exists(browser_path):
#                 print("✓ Patchright browsers are installed")
#                 return True
#     except Exception:
#         pass
    
#     print("⚠ Patchright browsers not found. Attempting to install Chromium...")
#     try:
#         result = subprocess.run(
#             [sys.executable, "-m", "playwright", "install", "chromium"],
#             capture_output=True,
#             text=True,
#             timeout=300
#         )
#         if result.returncode == 0:
#             print("✓ Chromium installed successfully")
#             return True
#         else:
#             print(f"⚠ Installation output: {result.stderr}")
#     except Exception as e:
#         print(f"⚠ Could not install automatically: {e}")
    
#     print("\n" + "="*80)
#     print("❌ PLAYWRIGHT BROWSERS NOT INSTALLED")
#     print("="*80)
#     print("Please install manually:")
#     print("\n    playwright install chromium\n")
#     print("="*80 + "\n")
#     return False

# # Advanced human simulation with bezier-like mouse movements and typing
# def simulate_human_behavior(page):
#     """Simulate realistic human behavior"""
#     try:
#         print("👤 Simulating advanced human behavior...")
        
#         # Random mouse movements with smooth paths
#         page.mouse.move(0, 0, steps=5)
#         for _ in range(random.randint(3, 7)):
#             target_x = random.randint(100, 1800)
#             target_y = random.randint(100, 900)
#             page.mouse.move(target_x, target_y, steps=random.randint(15, 30))
#             #time.sleep(random.uniform(0.3, 1.2))
        
#         # Scroll naturally
#         scroll_amount = random.randint(100, 400)
#         page.evaluate(f"window.scrollBy(0, {scroll_amount});")
#         #time.sleep(random.uniform(0.8, 2.0))
#         page.evaluate(f"window.scrollBy(0, -{random.randint(50, 200)});")
        
#         print("✓ Advanced human behavior simulation complete")
#     except Exception as e:
#         print(f"⚠ Could not simulate human behavior: {e}")

# # Helper to type text slowly like a human
# def human_type(element, text):
#     """Type text with human-like delays"""
#     for char in text:
#         element.type(char, delay=random.uniform(80, 200))
#     #time.sleep(random.uniform(0.5, 1.5))

# # Enhanced find element with timeout handling
# def find_element_safe(page, xpath, description, timeout=30000, state='visible'):
#     try:
#         print(f"🔍 Looking for {description}...")
#         locator = page.locator(f'xpath={xpath}')
#         locator.wait_for(state=state, timeout=timeout)
#         print(f"✓ Found {description}")
#         return locator
#     except PlaywrightTimeoutError:
#         print(f"❌ Timeout for {description}")
#         raise
#     except Exception as e:
#         print(f"❌ Error finding {description}: {e}")
#         raise

# if not ensure_browsers_installed():
#     sys.exit(1)

# print("🚀 Starting undetected Patchright browser...")

# try:
#     with sync_playwright() as p:
#         # Launch with maximum stealth
#         browser = p.chromium.launch(
#             headless=False,  # Headful is crucial for evasion in 2025
#             args=[
#                 '--disable-blink-features=AutomationControlled',
#                 '--disable-dev-shm-usage',
#                 '--no-sandbox',
#                 '--disable-infobars',
#                 '--window-size=1920,1080',
#                 '--disable-gpu',  # Helps with fingerprinting
#                 '--disable-extensions',
#                 # Note: --user-data-dir cannot be used in launch(), use launch_persistent_context() if needed
#             ],
#             # Add residential proxy (replace with your own from Bright Data/Oxylabs/etc.)
#             # proxy={
#             #     "server": "http://residential-proxy-ip:port",
#             #     "username": "user",
#             #     "password": "pass"
#             # }
#         )

#         # Context with realistic fingerprint
#         context = browser.new_context(
#             viewport={'width': 1920, 'height': 1080},
#             user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
#             locale='en-US',
#             timezone_id='America/New_York',
#             permissions=['geolocation'],
#             geolocation={'latitude': 40.7128, 'longitude': -74.0060},  # NYC example
#             ignore_https_errors=True
#         )

#         # Super-enhanced stealth script for 2025 Cloudflare/OpenAI
#         context.add_init_script("""
#             // Remove all automation traces
#             Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
#             delete navigator.webdriver;
#             window.chrome = { runtime: {}, app: {}, loadTimes: () => {}, csi: () => {} };
#             Object.defineProperty(navigator, 'plugins', { get: () => [{name: 'Chrome PDF Viewer'}, {name: 'Widevine Content Decryption Module'}] });
#             Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
#             Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
#             Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
#             Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 0 });
#             Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
#             // Spoof permissions
#             navigator.permissions.query = () => Promise.resolve({ state: 'granted' });
#             // Hide Playwright CDP
#             window._playwright = undefined;
#         """)

#         page = context.new_page()
#         print("✓ Stealth applied successfully")

#         print("🌐 Navigating to ChatGPT...")
#         page.goto('https://chatgpt.com', wait_until='networkidle', timeout=60000)

#         page.wait_for_load_state('domcontentloaded')
#         page.wait_for_load_state('networkidle', timeout=30000)
#         #time.sleep(random.uniform(3, 6))

#         simulate_human_behavior(page)

#         # Login flow with human typing
#         try:
#             # Click login button (adjust XPath if needed)
#             login_button = find_element_safe(page, '//button[contains(text(), "Log in")]', 'login button')
#             login_button.click()
#             #time.sleep(random.uniform(2, 4))

#             # Fill email
#             email_input = find_element_safe(page, '//input[@type="email"]', 'email input')
#             human_type(email_input, EMAIL_VALUE)
#             next_button = find_element_safe(page, '//button[contains(text(), "Continue") or @type="submit"]', 'next button')
#             next_button.click()
#             #time.sleep(random.uniform(2, 5))

#             # Fill password
#             password_input = find_element_safe(page, '//input[@type="password"]', 'password input')
#             human_type(password_input, PASSWORD_VALUE)
#             submit_button = find_element_safe(page, '//button[contains(text(), "Log in") or @type="submit"]', 'submit button')
#             submit_button.click()
#             #time.sleep(random.uniform(5, 10))

#             # Wait for ChatGPT interface
#             print("⏳ Waiting for ChatGPT dashboard...")
#             page.wait_for_selector('textarea', timeout=60000)

#             # Fill prompt
#             textarea = find_element_safe(page, '//textarea[@id="prompt-textarea"]', 'prompt textarea')
#             human_type(textarea, PROMPT)

#             # Send
#             send_button = find_element_safe(page, '//button[@data-testid="send-button"]', 'send button')
#             send_button.click()
#             #time.sleep(random.uniform(1, 3))

#             # Wait for response
#             print("⏳ Waiting for response...")
#             response_selector = '//div[contains(@class, "markdown")]//p'  # Adjust as needed
#             page.wait_for_selector(response_selector, timeout=90000)

#             # Extract response
#             response_text = page.inner_text(response_selector)
#             print("\n" + "="*80)
#             print("CHATGPT RESPONSE:")
#             print("="*80)
#             print(response_text)
#             print("="*80 + "\n")

#             # Optional: Save cookies for future runs
#             context.storage_state(path="chatgpt_state.json")
#             print("✓ Session saved to chatgpt_state.json")

#         except Exception as e:
#             print(f"❌ Error during automation: {e}")
#             print("Page content snippet:")
#             print(page.content()[:2000])

#         finally:
#             print("🧹 Closing browser...")
#             browser.close()

# except Exception as e:
#     print(f"❌ Fatal error: {e}")
#     import traceback
#     traceback.print_exc()




from patchright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import os
import random
import subprocess
import sys
import platform
import atexit
from dotenv import load_dotenv

load_dotenv()

# Virtual display setup for headless mode
_xvfb_process = None

def setup_virtual_display():
    """Set up Xvfb virtual display for headless mode"""
    global _xvfb_process
    
    # Check if we're on Linux (Xvfb is typically Linux-only)
    if platform.system() != 'Linux':
        print("ℹ️  Virtual display not needed on non-Linux systems")
        return
    
    # Check if DISPLAY is already set
    if os.getenv('DISPLAY'):
        print(f"✓ Display already set: {os.getenv('DISPLAY')}")
        return
    
    # Check if Xvfb is available
    try:
        result = subprocess.run(['which', 'Xvfb'], capture_output=True, text=True)
        if result.returncode != 0:
            print("⚠️  Xvfb not found. Install with: sudo apt-get install xvfb")
            print("   Attempting to continue without virtual display...")
            return
    except Exception:
        print("⚠️  Could not check for Xvfb. Attempting to continue...")
        return
    
    # Start Xvfb
    try:
        print("🖥️  Starting virtual display (Xvfb)...")
        # Find an available display number
        display_num = 99
        for i in range(99, 200):
            test_result = subprocess.run(
                ['xdpyinfo', '-display', f':{i}'],
                capture_output=True,
                stderr=subprocess.DEVNULL
            )
            if test_result.returncode != 0:
                display_num = i
                break
        
        display = f':{display_num}'
        _xvfb_process = subprocess.Popen(
            ['Xvfb', display, '-screen', '0', '1920x1080x24', '-ac', '+extension', 'GLX'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Set DISPLAY environment variable
        os.environ['DISPLAY'] = display
        print(f"✓ Virtual display started on {display}")
        
        # Register cleanup function
        atexit.register(cleanup_virtual_display)
        
    except Exception as e:
        print(f"⚠️  Could not start Xvfb: {e}")
        print("   Attempting to continue without virtual display...")

def cleanup_virtual_display():
    """Clean up virtual display on exit"""
    global _xvfb_process
    if _xvfb_process:
        try:
            _xvfb_process.terminate()
            _xvfb_process.wait(timeout=5)
            print("✓ Virtual display stopped")
        except Exception:
            try:
                _xvfb_process.kill()
            except Exception:
                pass
        _xvfb_process = None

EMAIL_VALUE = os.getenv('EMAIL_VALUE')
print(EMAIL_VALUE)
PASSWORD_VALUE = os.getenv('PASSWORD_VALUE')
print(PASSWORD_VALUE)
PROMPT = "which one do you recommend"
CHAT_ID = "69466aea-f3fc-8333-b1de-19c38559bb09"

# Check and install Playwright browsers if needed
def ensure_browsers_installed():
    """Check if Patchright browsers are installed, install if missing"""
    # First, try to actually launch a browser to verify it works
    try:
        with sync_playwright() as p:
            # Try to launch a browser to verify it exists and works
            browser = p.chromium.launch(headless=True)
            browser.close()
            print("✓ Patchright browsers are installed and working")
            return True
    except Exception as e:
        error_str = str(e)
        if "Executable doesn't exist" in error_str or "BrowserType.launch" in error_str:
            print("⚠ Patchright browsers not found. Attempting to install Chromium...")
        else:
            print(f"⚠ Browser check failed: {e}")
            print("⚠ Attempting to install Chromium...")
    
    # Try to install browsers
    try:
        # Try both playwright and patchright commands
        # Try installing all browsers first (ensures full Chromium, not just headless shell)
        # Then fall back to chromium-only if needed
        for cmd in ["playwright", "patchright"]:
            try:
                # First try installing all browsers (includes full Chromium)
                print(f"Attempting to install all browsers using {cmd}...")
                result_all = subprocess.run(
                    [sys.executable, "-m", cmd, "install"],
                    capture_output=True,
                    text=True,
                    timeout=600  # Longer timeout for all browsers
                )
                if result_all.returncode == 0:
                    print(f"✓ All browsers install completed using {cmd}")
                    # Verify installation worked
                    try:
                        with sync_playwright() as p:
                            browser = p.chromium.launch(headless=True)
                            browser.close()
                            print("✓ Browser verification successful")
                            return True
                    except Exception as verify_e:
                        print(f"⚠ Full install succeeded but verification failed: {verify_e}")
                        # Try chromium-only as fallback
                        print(f"⚠ Attempting chromium-only install as fallback...")
                        try:
                            result_chromium = subprocess.run(
                                [sys.executable, "-m", cmd, "install", "chromium"],
                                capture_output=True,
                                text=True,
                                timeout=300
                            )
                            if result_chromium.returncode == 0:
                                # Verify again
                                try:
                                    with sync_playwright() as p:
                                        browser = p.chromium.launch(headless=True)
                                        browser.close()
                                        print("✓ Browser verification successful after chromium install")
                                        return True
                                except Exception as verify_e2:
                                    print(f"⚠ Still failed after chromium install: {verify_e2}")
                                    continue
                        except Exception as chromium_e:
                            print(f"⚠ Could not install chromium: {chromium_e}")
                            continue
                else:
                    print(f"⚠ {cmd} install all browsers output: {result_all.stderr}")
                    # Fall back to chromium-only
                    print(f"Attempting chromium-only install using {cmd}...")
                    result = subprocess.run(
                        [sys.executable, "-m", cmd, "install", "chromium"],
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    if result.returncode == 0:
                        # Verify
                        try:
                            with sync_playwright() as p:
                                browser = p.chromium.launch(headless=True)
                                browser.close()
                                print("✓ Browser verification successful")
                                return True
                        except Exception as verify_e:
                            print(f"⚠ Chromium install succeeded but verification failed: {verify_e}")
                            continue
            except FileNotFoundError:
                continue  # Try next command
            except Exception as e:
                print(f"⚠ Could not install using {cmd}: {e}")
                continue
    except Exception as e:
        print(f"⚠ Could not install automatically: {e}")
    
    print("\n" + "="*80)
    print("❌ PLAYWRIGHT/PATCHRIGHT BROWSERS NOT INSTALLED")
    print("="*80)
    print("Please install manually:")
    print("\n    playwright install")
    print("    # OR")
    print("    playwright install chromium")
    print("    # OR")
    print("    patchright install chromium\n")
    print("="*80 + "\n")
    return False

# Advanced human simulation with smooth mouse movements and typing
def simulate_human_behavior(page):
    """Simulate realistic human behavior"""
    try:
        print("👤 Simulating advanced human behavior...")
        
        # Random mouse movements with smooth paths
        page.mouse.move(0, 0, steps=5)
        for _ in range(random.randint(3, 7)):
            target_x = random.randint(100, 1800)
            target_y = random.randint(100, 900)
            page.mouse.move(target_x, target_y, steps=random.randint(15, 30))
            #time.sleep(random.uniform(0.3, 1.2))
        
        # Scroll naturally
        scroll_amount = random.randint(100, 400)
        page.evaluate(f"window.scrollBy(0, {scroll_amount});")
        #time.sleep(random.uniform(0.8, 2.0))
        page.evaluate(f"window.scrollBy(0, -{random.randint(50, 200)});")
        
        print("✓ Advanced human behavior simulation complete")
    except Exception as e:
        print(f"⚠ Could not simulate human behavior: {e}")

# Helper to type text slowly like a human
def human_type(element, text):
    """Type text with human-like delays"""
    # Clear the field first and ensure focus
    element.click()  # Focus the element
    element.fill('')  # Clear any existing text
    #time.sleep(random.uniform(0.2, 0.5))  # Small delay after clearing
    # Type character by character
    for char in text:
        element.type(char, delay=random.uniform(80, 200))
    #time.sleep(random.uniform(0.5, 1.5))

# Detect current stage of the login/chat flow
def detect_stage(page):
    """
    Detect which stage we're currently at:
    - 'email': Email input stage
    - 'password': Password input stage (passed email)
    - 'chatgpt': ChatGPT interface (passed password)
    - 'unknown': Can't determine stage
    """
    # Check for ChatGPT stage first (most specific)
    try:
        # Check for contenteditable div (the actual prompt input)
        chatgpt_prompt_input = page.locator('#prompt-textarea')
        if chatgpt_prompt_input.is_visible(timeout=1000):
            # Try multiple send button selectors
            send_button_selectors = [
                '#composer-submit-button',
                'button[data-testid="send-button"]',
                'button[aria-label="Send prompt"]',
                'xpath=/html/body/div[1]/div[1]/div/div[2]/div/main/div/div/div[2]/div[1]/div/div/div[2]/form/div[2]/div/div[3]/div/button',
            ]
            for selector in send_button_selectors:
                try:
                    chatgpt_send_button = page.locator(selector)
                    if chatgpt_send_button.is_visible(timeout=500):
                        return 'chatgpt'
                except:
                    continue
    except:
        pass
    
    # Check for password stage (means we passed email)
    try:
        password_locator = page.locator('input[name="Passwd"]').first
        next_button_locator = page.locator('xpath=/html/body/div[2]/div[1]/div[1]/div[2]/c-wiz/main/div[3]/div/div[1]/div/div/button')
        if password_locator.is_visible(timeout=1000) and next_button_locator.is_visible(timeout=1000):
            return 'password'
    except:
        pass
    
    # Check for email stage
    try:
        email_locator = page.locator('input[type="email"]').first
        if email_locator.is_visible(timeout=1000):
            return 'email'
    except:
        pass
    
    return 'unknown'

# Check current page state to determine what step we're on
def check_page_state(page):
    """Check what elements are currently visible on the page"""
    state = {
        'email_input': False,
        'password_input': False,
        'next_button': False,
        'intermediate_button': False,
        'login_button': False,
        'chatgpt_textarea': False,
        'chatgpt_send_button': False,
        'current_stage': 'unknown'
    }
    
    # Detect current stage
    state['current_stage'] = detect_stage(page)
    
    try:
        email_locator = page.locator('input[type="email"]').first
        if email_locator.is_visible(timeout=1000):
            state['email_input'] = True
    except:
        pass
    
    try:
        password_locator = page.locator('input[name="Passwd"]').first
        if password_locator.is_visible(timeout=1000):
            state['password_input'] = True
    except:
        pass
    
    try:
        next_button_locator = page.locator('xpath=/html/body/div[2]/div[1]/div[1]/div[2]/c-wiz/main/div[3]/div/div[1]/div/div/button')
        if next_button_locator.is_visible(timeout=1000):
            state['next_button'] = True
    except:
        pass
    
    try:
        intermediate_button_locator = page.locator('xpath=/html/body/div[4]/div/div/div/div/div/div/form/div[1]/button[1]')
        if intermediate_button_locator.is_visible(timeout=1000):
            state['intermediate_button'] = True
    except:
        pass
    
    try:
        login_button_locator = page.locator('button:has-text("Log in")')
        if login_button_locator.is_visible(timeout=1000):
            state['login_button'] = True
    except:
        pass
    
    try:
        chatgpt_prompt_input = page.locator('#prompt-textarea')
        if chatgpt_prompt_input.is_visible(timeout=1000):
            state['chatgpt_textarea'] = True  # Keep same key name for compatibility
    except:
        pass
    
    try:
        # Try multiple send button selectors
        send_button_selectors = [
            '#composer-submit-button',
            'button[data-testid="send-button"]',
            'button[aria-label="Send prompt"]',
            'xpath=/html/body/div[1]/div[1]/div/div[2]/div/main/div/div/div[2]/div[1]/div/div/div[2]/form/div[2]/div/div[3]/div/button',
        ]
        for selector in send_button_selectors:
            try:
                chatgpt_send_button = page.locator(selector)
                if chatgpt_send_button.is_visible(timeout=500):
                    state['chatgpt_send_button'] = True
                    break
            except:
                continue
    except:
        pass
    
    return state

# Enhanced find element with timeout handling and state checking
def find_element_safe(page, selector, description, timeout=30000, state='visible', retry_on_failure=True):
    try:
        print(f"🔍 Looking for {description}...")
        locator = page.locator(selector)
        locator.wait_for(state=state, timeout=timeout)
        print(f"✓ Found {description}")
        return locator
    except PlaywrightTimeoutError:
        if retry_on_failure:
            print(f"⚠ Timeout for {description}, checking current stage...")
            current_stage = detect_stage(page)
            page_state = check_page_state(page)
            print(f"📊 Current stage: {current_stage}")
            print(f"📊 Page state: {page_state}")
            
            # Handle retries based on current stage and what we're looking for
            # If we're looking for password but still at email stage
            if 'password' in description.lower() and current_stage == 'email':
                print("  → Still at email stage, completing email step...")
                try:
                    email_input = page.locator('input[type="email"]').first
                    if email_input.is_visible(timeout=2000):
                        email_value = email_input.input_value()
                        if not email_value or email_value != EMAIL_VALUE:
                            print("  → Filling email...")
                            human_type(email_input, EMAIL_VALUE)
                        # Click next button
                        next_button = page.locator('xpath=/html/body/div[2]/div[1]/div[1]/div[2]/c-wiz/main/div[3]/div/div[1]/div/div/button')
                        if next_button.is_visible(timeout=2000):
                            next_button.click()
                            print("  → Clicked next button, retrying to find password...")
                            # time.sleep(2)
                            locator = page.locator(selector)
                            locator.wait_for(state=state, timeout=timeout)
                            print(f"✓ Found {description} after completing email stage")
                            return locator
                except Exception as e:
                    print(f"  ⚠ Error completing email stage: {e}")
            
            # If we're looking for ChatGPT textarea but still at password stage
            if ('chatgpt' in description.lower() or 'textarea' in description.lower() or 'prompt' in description.lower()) and current_stage == 'password':
                print("  → Still at password stage, completing password step...")
                try:
                    password_input = page.locator('input[name="Passwd"]').first
                    if password_input.is_visible(timeout=2000):
                        password_value = password_input.input_value()
                        if not password_value or password_value != PASSWORD_VALUE:
                            print("  → Filling password...")
                            human_type(password_input, PASSWORD_VALUE)
                        # Click submit button
                        submit_button = page.locator('button:has-text("Log in")')
                        if submit_button.is_visible(timeout=2000):
                            submit_button.click()
                            print("  → Clicked submit button, retrying to find ChatGPT interface...")
                            # time.sleep(3)
                            locator = page.locator(selector)
                            locator.wait_for(state=state, timeout=timeout)
                            print(f"✓ Found {description} after completing password stage")
                            return locator
                except Exception as e:
                    print(f"  ⚠ Error completing password stage: {e}")
            
            # If we're looking for ChatGPT but still at email stage
            if ('chatgpt' in description.lower() or 'textarea' in description.lower() or 'prompt' in description.lower()) and current_stage == 'email':
                print("  → Still at email stage, need to complete email and password steps...")
                try:
                    # Complete email step
                    email_input = page.locator('input[type="email"]').first
                    if email_input.is_visible(timeout=2000):
                        email_value = email_input.input_value()
                        if not email_value or email_value != EMAIL_VALUE:
                            human_type(email_input, EMAIL_VALUE)
                        next_button = page.locator('xpath=/html/body/div[2]/div[1]/div[1]/div[2]/c-wiz/main/div[3]/div/div[1]/div/div/button')
                        if next_button.is_visible(timeout=2000):
                            next_button.click()
                            # time.sleep(2)
                    # Complete password step
                    password_input = page.locator('input[name="Passwd"]').first
                    if password_input.is_visible(timeout=5000):
                        password_value = password_input.input_value()
                        if not password_value or password_value != PASSWORD_VALUE:
                            human_type(password_input, PASSWORD_VALUE)
                        submit_button = page.locator('button:has-text("Log in")')
                        if submit_button.is_visible(timeout=2000):
                            submit_button.click()
                            print("  → Completed email and password steps, retrying to find ChatGPT interface...")
                            # time.sleep(3)
                            locator = page.locator(selector)
                            locator.wait_for(state=state, timeout=timeout)
                            print(f"✓ Found {description} after completing email and password stages")
                            return locator
                except Exception as e:
                    print(f"  ⚠ Error completing stages: {e}")
            
            # General retry logic for other cases
            if page_state['email_input']:
                print("  → Email input is visible, checking if it needs to be filled...")
                try:
                    email_input = page.locator('input[type="email"]').first
                    email_value = email_input.input_value()
                    if not email_value or email_value != EMAIL_VALUE:
                        print("  → Email input is empty/mismatched, re-filling...")
                        human_type(email_input, EMAIL_VALUE)
                        # Try clicking next button
                        try:
                            next_button = page.locator('xpath=/html/body/div[2]/div[1]/div[1]/div[2]/c-wiz/main/div[3]/div/div[1]/div/div/button')
                            if next_button.is_visible(timeout=2000):
                                next_button.click()
                                print("  → Clicked next button, retrying to find target element...")
                                # time.sleep(2)
                                locator = page.locator(selector)
                                locator.wait_for(state=state, timeout=timeout)
                                print(f"✓ Found {description} after retry")
                                return locator
                        except:
                            pass
                except:
                    pass
            
            if page_state['next_button']:
                print("  → Next button is visible, clicking it...")
                try:
                    next_button = page.locator('xpath=/html/body/div[2]/div[1]/div[1]/div[2]/c-wiz/main/div[3]/div/div[1]/div/div/button')
                    if next_button.is_visible(timeout=2000):
                        next_button.click()
                        print("  → Clicked next button, retrying to find target element...")
                        # time.sleep(2)
                        locator = page.locator(selector)
                        locator.wait_for(state=state, timeout=timeout)
                        print(f"✓ Found {description} after retry")
                        return locator
                except:
                    pass
            
            if page_state['intermediate_button']:
                print("  → Intermediate button is visible, clicking it...")
                try:
                    intermediate_button = page.locator('xpath=/html/body/div[4]/div/div/div/div/div/div/form/div[1]/button[1]')
                    if intermediate_button.is_visible(timeout=2000):
                        intermediate_button.click()
                        print("  → Clicked intermediate button, retrying to find target element...")
                        # time.sleep(2)
                        locator = page.locator(selector)
                        locator.wait_for(state=state, timeout=timeout)
                        print(f"✓ Found {description} after retry")
                        return locator
                except:
                    pass
        
        print(f"❌ Timeout for {description} after retries")
        raise
    except Exception as e:
        print(f"❌ Error finding {description}: {e}")
        raise

if not ensure_browsers_installed():
    sys.exit(1)

# Set up virtual display for headless mode
setup_virtual_display()

print("🚀 Starting undetected Patchright browser...")

try:
    with sync_playwright() as p:
        # Use persistent context for user-data-dir (fixes the error)
        user_data_dir = os.path.join(os.path.expanduser("~"), "patchright_user_data")
        os.makedirs(user_data_dir, exist_ok=True)

        # Launch persistent context (replaces launch + new_context)
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=True,  # Running in headless mode
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-infobars',
                    '--window-size=1920,1080',
                    '--disable-gpu',
                    '--disable-extensions',
                ],
                # Add residential proxy if needed (uncomment and fill)
                # proxy={
                #     "server": "http://residential-proxy-ip:port",
                #     "username": "user",
                #     "password": "pass"
                # }
            )
        except Exception as launch_error:
            error_str = str(launch_error)
            if "Executable doesn't exist" in error_str:
                print("\n" + "="*80)
                print("❌ BROWSER EXECUTABLE NOT FOUND")
                print("="*80)
                print("The browser executable is missing. Attempting to install...")
                print("="*80 + "\n")
                
                # Try to install again - first chromium, then all browsers if needed
                try:
                    # Try installing chromium first
                    print("Attempting to install Chromium...")
                    result = subprocess.run(
                        [sys.executable, "-m", "playwright", "install", "chromium"],
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    if result.returncode == 0:
                        print("✓ Chromium install completed. Retrying launch...")
                        # Retry launch
                        try:
                            context = p.chromium.launch_persistent_context(
                                user_data_dir=user_data_dir,
                                headless=True,
                                args=[
                                    '--disable-blink-features=AutomationControlled',
                                    '--disable-dev-shm-usage',
                                    '--no-sandbox',
                                    '--disable-infobars',
                                    '--window-size=1920,1080',
                                    '--disable-gpu',
                                    '--disable-extensions',
                                ],
                            )
                        except Exception as retry_error:
                            # If chromium install didn't work, try installing all browsers
                            print("⚠ Chromium install didn't fix the issue. Installing all browsers...")
                            subprocess.run(
                                [sys.executable, "-m", "playwright", "install"],
                                check=True,
                                timeout=600
                            )
                            print("✓ All browsers installed. Retrying launch...")
                            context = p.chromium.launch_persistent_context(
                                user_data_dir=user_data_dir,
                                headless=True,
                                args=[
                                    '--disable-blink-features=AutomationControlled',
                                    '--disable-dev-shm-usage',
                                    '--no-sandbox',
                                    '--disable-infobars',
                                    '--window-size=1920,1080',
                                    '--disable-gpu',
                                    '--disable-extensions',
                                ],
                            )
                    else:
                        raise Exception(f"Installation failed: {result.stderr}")
                except Exception as install_error:
                    print(f"❌ Failed to install browser: {install_error}")
                    print("\nPlease run manually:")
                    print("    playwright install")
                    print("    # OR")
                    print("    playwright install chromium")
                    raise
            else:
                raise  # Re-raise if it's a different error

        # Get the page from persistent context
        if context.pages:
            page = context.pages[0]
        else:
            page = context.new_page()

        # Apply super-enhanced stealth script for 2025
        context.add_init_script("""
            // Remove all automation traces
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            delete navigator.webdriver;
            window.chrome = { runtime: {}, app: {}, loadTimes: () => {}, csi: () => {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [{name: 'Chrome PDF Viewer'}, {name: 'Widevine Content Decryption Module'}] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
            Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
            Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 0 });
            Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
            navigator.permissions.query = () => Promise.resolve({ state: 'granted' });
            window._playwright = undefined;
        """)

        print("✓ Stealth applied successfully")
        print("🌐 Navigating to ChatGPT...")
        # Construct URL based on CHAT_ID
        if CHAT_ID:
            chatgpt_url = f'https://chatgpt.com/c/{CHAT_ID}'
            print(f"  → Using chat URL: {chatgpt_url}")
        else:
            chatgpt_url = 'https://chatgpt.com'
            print(f"  → Using base URL: {chatgpt_url}")
        page.goto(chatgpt_url, wait_until='networkidle', timeout=60000)

        page.wait_for_load_state('domcontentloaded')
        page.wait_for_load_state('networkidle', timeout=30000)
        #time.sleep(random.uniform(3, 6))

        simulate_human_behavior(page)

        # Helper function for authenticated flow (send prompt and get response)
        def authenticated_flow():
            """Flow when user is already authenticated"""
            print("🔐 Authenticated flow: User is already logged in")
            
            # Find prompt input (contenteditable div) - refresh page if not found initially
            prompt_input = None
            max_retries = 2  # Try once, then refresh and try again
            for attempt in range(max_retries):
                try:
                    # Try finding by ID first (most reliable)
                    prompt_input = find_element_safe(
                        page,
                        '#prompt-textarea',
                        'ChatGPT prompt input (contenteditable)',
                        retry_on_failure=True,
                        timeout=10000  # Shorter timeout for initial check
                    )
                    print("✓ ChatGPT prompt input found!")
                    break
                except (PlaywrightTimeoutError, Exception) as e:
                    # Try alternative selector: contenteditable div
                    try:
                        prompt_input = find_element_safe(
                            page,
                            'div[contenteditable="true"][id="prompt-textarea"]',
                            'ChatGPT prompt input (contenteditable by attribute)',
                            retry_on_failure=True,
                            timeout=10000
                        )
                        print("✓ ChatGPT prompt input found (via contenteditable attribute)!")
                        break
                    except (PlaywrightTimeoutError, Exception):
                        if attempt < max_retries - 1:
                            print(f"⚠ Prompt input not found (attempt {attempt + 1}/{max_retries})")
                            print("  → Refreshing page and retrying...")
                            page.reload(wait_until='networkidle', timeout=30000)
                            page.wait_for_load_state('domcontentloaded')
                            page.wait_for_load_state('networkidle', timeout=30000)
                            time.sleep(2)  # Small delay after refresh
                        else:
                            print(f"❌ Could not find prompt input after {max_retries} attempts (including refresh)")
                            raise
            
            if prompt_input is None:
                raise Exception("Failed to find prompt input even after page refresh")
            
            # Fill prompt in contenteditable div
            # Click to focus first
            prompt_input.click()
            time.sleep(0.5)
            # Clear any existing content
            prompt_input.fill('')
            # Type the prompt character by character (human-like)
            for char in PROMPT:
                prompt_input.type(char, delay=random.uniform(80, 200))
            time.sleep(random.uniform(0.5, 1.0))
            print(f"✓ Prompt filled: {PROMPT[:50]}...")
            
            # Find and click send button - try multiple selectors
            send_button = None
            send_button_selectors = [
                '#composer-submit-button',  # ID selector (most reliable)
                'button[data-testid="send-button"]',  # data-testid selector
                'button[aria-label="Send prompt"]',  # aria-label selector
                'xpath=/html/body/div[1]/div[1]/div/div[2]/div/main/div/div/div[2]/div[1]/div/div/div[2]/form/div[2]/div/div[3]/div/button',  # Original XPath fallback
            ]
            
            for selector in send_button_selectors:
                try:
                    send_button = find_element_safe(
                        page,
                        selector,
                        'ChatGPT send button',
                        retry_on_failure=False,  # Don't retry on individual selectors
                        timeout=5000  # Shorter timeout for each attempt
                    )
                    print(f"✓ Send button found using selector: {selector[:50]}...")
                    break
                except (PlaywrightTimeoutError, Exception) as e:
                    continue
            
            if send_button is None:
                # Final attempt with retry enabled on the last selector
                print("⚠ Trying final send button selector with retry...")
                send_button = find_element_safe(
                    page,
                    send_button_selectors[-1],  # Use XPath as final fallback
                    'ChatGPT send button',
                    retry_on_failure=True
                )
            
            send_button.click()
            print("✓ Prompt sent!")
            
            # Wait for response article to appear
            print("⏳ Waiting for response to start...")
            try:
                # Wait for the assistant turn article to appear
                page.wait_for_selector('article[data-turn="assistant"]', timeout=90000)
                print("✓ Response article appeared")
            except PlaywrightTimeoutError:
                # Fallback: wait for any markdown content
                print("⚠ Assistant article not found, waiting for markdown content...")
                page.wait_for_selector('div.markdown', timeout=90000)
            
            # Wait for response to complete (check for data-is-last-node or wait for content to stabilize)
            print("⏳ Waiting for response to complete...")
            max_wait_time = 180  # Maximum 3 minutes
            check_interval = 2  # Check every 2 seconds
            elapsed_time = 0
            last_content_length = 0
            stable_count = 0
            response_complete = False
            
            while elapsed_time < max_wait_time and not response_complete:
                try:
                    # Find the latest assistant response article
                    assistant_articles = page.locator('article[data-turn="assistant"]').all()
                    if assistant_articles:
                        latest_article = assistant_articles[-1]  # Get the most recent one
                        
                        # Scroll to the article to ensure it's fully rendered
                        latest_article.scroll_into_view_if_needed()
                        time.sleep(0.5)  # Small delay for rendering
                        
                        # Check if response is complete (has data-is-last-node attribute)
                        markdown_div = latest_article.locator('div.markdown').first
                        if markdown_div.is_visible(timeout=1000):
                            # Check for data-is-last-node in any p element
                            try:
                                last_node = markdown_div.locator('p[data-is-last-node=""]').first
                                if last_node.is_visible(timeout=1000):
                                    print("✓ Response complete (data-is-last-node found)")
                                    # Wait a bit more to ensure all content is rendered
                                    time.sleep(2)
                                    response_complete = True
                                    break
                            except:
                                pass
                            
                            # Check if content has stabilized (same length for 5 checks = 10 seconds)
                            # Use text_content() which gets all text including hidden content
                            current_content = markdown_div.text_content() or markdown_div.inner_text()
                            
                            current_length = len(current_content)
                            
                            if current_length > 0:
                                if current_length == last_content_length:
                                    stable_count += 1
                                    if stable_count >= 5:  # 10 seconds of stability
                                        print(f"✓ Response appears complete (content stable for {stable_count * check_interval}s)")
                                        # Wait a bit more to ensure all content is rendered
                                        time.sleep(3)
                                        response_complete = True
                                        break
                                else:
                                    stable_count = 0
                                    last_content_length = current_length
                                    print(f"  📝 Response length: {current_length} chars (still streaming...)")
                    else:
                        # Fallback: check for any markdown content
                        markdown_divs = page.locator('div.markdown').all()
                        if markdown_divs:
                            latest_markdown = markdown_divs[-1]
                            if latest_markdown.is_visible(timeout=1000):
                                latest_markdown.scroll_into_view_if_needed()
                                time.sleep(0.5)
                                current_content = latest_markdown.text_content() or latest_markdown.inner_text()
                                current_length = len(current_content)
                                if current_length > 0:
                                    if current_length == last_content_length:
                                        stable_count += 1
                                        if stable_count >= 5:
                                            print(f"✓ Response appears complete (content stable for {stable_count * check_interval}s)")
                                            time.sleep(3)
                                            response_complete = True
                                            break
                                    else:
                                        stable_count = 0
                                        last_content_length = current_length
                except Exception as e:
                    print(f"  ⚠ Error checking response status: {e}")
                
                time.sleep(check_interval)
                elapsed_time += check_interval
            
            if elapsed_time >= max_wait_time:
                print("⚠ Max wait time reached, extracting current response...")
            
            # Extract full response from the latest assistant article using JavaScript for reliability
            print("📄 Extracting response content...")
            try:
                assistant_articles = page.locator('article[data-turn="assistant"]').all()
                if assistant_articles:
                    latest_article = assistant_articles[-1]
                    # Scroll to ensure all content is visible
                    latest_article.scroll_into_view_if_needed()
                    time.sleep(1)
                    
                    markdown_div = latest_article.locator('div.markdown').first
                    if markdown_div.is_visible(timeout=5000):
                            # Use text_content() which gets all text including hidden content, more reliable than inner_text()
                            response_text = markdown_div.text_content() or markdown_div.inner_text()
                            
                            # If text_content() doesn't work well, try getting text from all elements
                            if not response_text or len(response_text.strip()) < 10:
                                print("  ⚠ Primary extraction yielded little content, trying element-by-element extraction...")
                                all_elements = markdown_div.locator('p, ul, li, ol, h1, h2, h3, h4, h5, h6, blockquote, code, pre, strong, em, span').all()
                                element_texts = []
                                for elem in all_elements:
                                    elem_text = elem.text_content() or elem.inner_text()
                                    if elem_text and elem_text.strip():
                                        element_texts.append(elem_text.strip())
                                if element_texts:
                                    response_text = '\n'.join(element_texts)
                else:
                    # Fallback: extract from any markdown div
                    markdown_divs = page.locator('div.markdown').all()
                    if markdown_divs:
                        latest_markdown = markdown_divs[-1]
                        latest_markdown.scroll_into_view_if_needed()
                        time.sleep(1)
                        response_text = latest_markdown.text_content() or latest_markdown.inner_text()
                    else:
                        response_text = "⚠ Could not extract response content"
            except Exception as e:
                print(f"⚠ Error extracting response: {e}")
                import traceback
                traceback.print_exc()
                response_text = f"⚠ Error extracting response: {e}"
            
            print("\n" + "="*80)
            print("CHATGPT RESPONSE:")
            print("="*80)
            print(response_text)
            print("="*80 + "\n")
            
            # Save session state
            context.storage_state(path="chatgpt_state.json")
            print("✓ Session saved to chatgpt_state.json")

        # Check authentication status and route to appropriate flow
        try:
            # Check if we're already authenticated by checking multiple elements
            print("🔍 Checking authentication status...")
            is_authenticated = False
            
            # Check 1: Look for the prompt textarea itself (most reliable - works whether empty or has content)
            try:
                prompt_textarea = page.locator('#prompt-textarea')
                if prompt_textarea.is_visible(timeout=3000):
                    print("✓ User is authenticated - prompt textarea found (may contain existing text)")
                    is_authenticated = True
            except (PlaywrightTimeoutError, Exception):
                pass
            
            # Check 2: Look for the placeholder element with "Ask anything" data-placeholder attribute
            if not is_authenticated:
                try:
                    placeholder_element = page.locator('p[data-placeholder="Ask anything"]')
                    if placeholder_element.is_visible(timeout=3000):
                        print("✓ User is authenticated - 'Ask anything' placeholder element found")
                        is_authenticated = True
                except (PlaywrightTimeoutError, Exception):
                    # Also try the XPath
                    try:
                        placeholder_element = page.locator('xpath=/html/body/div[1]/div[1]/div/div[2]/div/main/div/div/div[2]/div[2]/div/div/div[2]/form/div[2]/div/div[1]/div/div/p')
                        if placeholder_element.is_visible(timeout=3000):
                            data_placeholder = placeholder_element.get_attribute('data-placeholder') or ''
                            if "ask anything" in data_placeholder.lower():
                                print("✓ User is authenticated - 'Ask anything' placeholder element found (via XPath)")
                                is_authenticated = True
                    except (PlaywrightTimeoutError, Exception):
                        pass
            
            # Check 3: Look for the prompt input container element
            if not is_authenticated:
                try:
                    prompt_container = page.locator('xpath=/html/body/div[1]/div[1]/div/div[2]/div/main/div/div/div[2]/div[1]/div/div/div[2]/form/div[2]/div/div[1]/div/div')
                    if prompt_container.is_visible(timeout=3000):
                        print("✓ User is authenticated - prompt input container element found")
                        is_authenticated = True
                except (PlaywrightTimeoutError, Exception):
                    pass
            
            if not is_authenticated:
                print("⚠ User is not authenticated - authentication elements not found")
            
            if is_authenticated:
                # ============================================
                # AUTHENTICATED FLOW - Send prompt and get response
                # ============================================
                authenticated_flow()
            else:
                # ============================================
                # UNAUTHENTICATED FLOW - Full login process
                # ============================================
                print("🔓 Unauthenticated flow: Starting login process...")
                
                # Click login button
                login_button = find_element_safe(page, 'button:has-text("Log in")', 'login button', retry_on_failure=True)
                login_button.click()
                #time.sleep(random.uniform(2, 4))

                # Wait for and click the intermediate button in the popup
                intermediate_button = find_element_safe(
                    page,
                    'xpath=/html/body/div[4]/div/div/div/div/div/div/form/div[1]/button[1]',
                    'intermediate button in popup',
                    retry_on_failure=True
                )
                intermediate_button.click()
                print("✓ Intermediate button clicked successfully")
                #time.sleep(random.uniform(2, 4))

                # Wait for email input to appear (will retry if intermediate button is still visible)
                email_input = find_element_safe(page, 'input[type="email"]', 'email input', retry_on_failure=True)
                human_type(email_input, EMAIL_VALUE)
                
                # Verify email value is in the input field before clicking next
                max_retries = 3
                for attempt in range(max_retries):
                    current_value = email_input.input_value()
                    if current_value == EMAIL_VALUE:
                        print(f"✓ Email value verified: {EMAIL_VALUE[:10]}...")
                        break
                    else:
                        print(f"⚠ Email value mismatch (attempt {attempt + 1}/{max_retries})")
                        print(f"  Expected: {EMAIL_VALUE}")
                        print(f"  Found: {current_value}")
                        if attempt < max_retries - 1:
                            print("  Re-entering email...")
                            human_type(email_input, EMAIL_VALUE)
                        else:
                            print("  ⚠ Max retries reached, proceeding anyway...")
                
                # Click the next button using the specific XPath (don't clear the email text)
                next_button = find_element_safe(
                    page,
                    'xpath=/html/body/div[2]/div[1]/div[1]/div[2]/c-wiz/main/div[3]/div/div[1]/div/div/button',
                    'next button after email',
                    retry_on_failure=True
                )
                next_button.click()
                print("✓ Next button clicked")
                # time.sleep(2)  # Wait for page transition
                
                # Verify we've passed email stage
                current_stage = detect_stage(page)
                if current_stage == 'password':
                    print("✓ Successfully passed email stage - password input detected!")
                elif current_stage == 'email':
                    print("⚠ Still at email stage after clicking next - fake button detected!")
                    # Additional check: if email input is still visible, re-fill and click next again
                    try:
                        email_input_check = page.locator('input[type="email"]').first
                        if email_input_check.is_visible(timeout=2000):
                            email_value_check = email_input_check.input_value()
                            if not email_value_check or email_value_check != EMAIL_VALUE:
                                print("  → Re-filling email and retrying...")
                                human_type(email_input_check, EMAIL_VALUE)
                                if email_input_check.input_value() == EMAIL_VALUE:
                                    next_button_retry = page.locator('xpath=/html/body/div[2]/div[1]/div[1]/div[2]/c-wiz/main/div[3]/div/div[1]/div/div/button')
                                    if next_button_retry.is_visible(timeout=2000):
                                        next_button_retry.click()
                                        print("✓ Next button clicked again after re-filling email")
                                        # time.sleep(2)
                                        # Check stage again
                                        current_stage = detect_stage(page)
                                        if current_stage == 'password':
                                            print("✓ Successfully passed email stage after retry!")
                    except Exception:
                        pass
                else:
                    print(f"📊 Current stage after clicking next: {current_stage}")
                
                print("⏳ Waiting for password input to appear...")
                # Wait for password input to appear after clicking next button
                # Use name="Passwd" to target the visible input, not the hidden one
                # This will automatically check page state and retry if needed
                password_input = find_element_safe(page, 'input[name="Passwd"]', 'password input', retry_on_failure=True)
                print("✓ Password input appeared - passed email stage!")
                human_type(password_input, PASSWORD_VALUE)
                submit_button = find_element_safe(page, 'button:has-text("Log in")', 'submit button')
                submit_button.click()
                print("✓ Submit button clicked, waiting for ChatGPT interface...")
                # time.sleep(3)  # Wait for page transition
                
                # Verify we've passed password stage
                current_stage = detect_stage(page)
                if current_stage == 'chatgpt':
                    print("✓ Successfully passed password stage - ChatGPT interface detected!")
                else:
                    print(f"⚠ Still at stage: {current_stage}, will retry when looking for ChatGPT elements...")

                # Wait for ChatGPT interface - use specific XPath
                print("⏳ Waiting for ChatGPT dashboard...")
                print("📊 Checking current stage...")
                current_stage = detect_stage(page)
                print(f"📊 Current stage: {current_stage}")
                
                # Login complete - now execute authenticated flow (send prompt and get response)
                print("✓ Login complete - proceeding to send prompt...")
                authenticated_flow()

        except Exception as e:
            print(f"❌ Error during automation: {e}")
            print("Page content snippet:")
            print(page.content()[:2000])

        finally:
            print("🧹 Closing browser...")
            context.close()
            # Clean up virtual display
            cleanup_virtual_display()

except Exception as e:
    print(f"❌ Fatal error: {e}")
    import traceback
    traceback.print_exc()
    # Ensure virtual display is cleaned up even on fatal errors
    cleanup_virtual_display()