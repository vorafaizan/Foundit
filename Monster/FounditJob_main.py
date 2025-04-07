import logging
import csv
import random
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, WebDriverException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
from random import uniform, choice
from datetime import datetime
import os

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36',
]

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

class FounditJob:
    def __init__(self, job_titles, job_locations, output_file='foundit.csv'):
        self.job_titles = job_titles
        self.job_locations = job_locations
        self.output_file = output_file
        self.unique_jobs = set()
        self.driver = self.setup_selenium_driver()
        self.initialize_csv()

    def setup_selenium_driver(self):
        chrome_options = Options()
        # Uncomment to run headless if needed
        # chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")  
        chrome_options.add_argument("--disable-software-rasterizer")  
        chrome_options.add_argument("--enable-unsafe-swiftshader")
        chrome_options.add_argument("--disable-webgl")  
        # Set a longer page load timeout
        chrome_options.page_load_strategy = 'eager'

        chrome_options.add_argument(f"user-agent={choice(USER_AGENTS)}")
        try:
            # Use webdriver-manager to automatically handle ChromeDriver compatibility
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            driver.set_page_load_timeout(30)
            driver.set_script_timeout(30)
            driver.implicitly_wait(10)
            logging.info("Selenium WebDriver initialized successfully.")
            return driver
        except WebDriverException as e:
            logging.error(f"Error initializing Selenium WebDriver: {e}")
            raise

    def initialize_csv(self):
        try:
            # Make sure output directory exists
            os.makedirs(os.path.dirname(os.path.abspath(self.output_file)) or '.', exist_ok=True)
            
            with open(self.output_file, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow([
                    'Job Title', 
                    'Company Name',
                    'Salary',
                    'Job Link',
                    'Job Description',
                    'More Info',
                    'Skills Required',
                    'About Company'
                ])
            print(f"✅ CSV file initialized at: {os.path.abspath(self.output_file)}")
            logging.info(f"CSV file '{self.output_file}' initialized with headers.")
            return True
        except Exception as e:
            print(f"❌ ERROR initializing CSV: {e}")
            logging.error(f"Failed to initialize CSV file: {e}")
            
            # Try creating a backup file
            try:
                backup_file = 'foundit_backup.csv'
                with open(backup_file, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow([
                        'Job Title', 
                        'Company Name',
                        'Salary',
                        'Job Link',
                        'Job Description',
                        'More Info',
                        'Skills Required',
                        'About Company'
                    ])
                print(f"✅ Backup CSV file initialized at: {os.path.abspath(backup_file)}")
                self.output_file = backup_file  # Switch to backup file
            except Exception as backup_error:
                print(f"❌ ERROR initializing backup CSV: {backup_error}")
            
            return False

    def save_record_to_csv(self, record):
        try:
            # Print debug info
            print(f"\nTrying to save record to {self.output_file}:")
            print(f"Record length: {len(record)}")
            print(f"First few fields: {record[0]}, {record[1]}")
            
            # Make sure output directory exists
            os.makedirs(os.path.dirname(os.path.abspath(self.output_file)) or '.', exist_ok=True)
            
            # Write to CSV with explicit error handling
            with open(self.output_file, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(record)

            print(f"✅ Successfully saved record to CSV file")
            logging.info(f"Record saved to CSV: {record[0]} at {record[1]}")
            return True
        except Exception as e:
            print(f"❌ ERROR saving to CSV: {e}")
            logging.error(f"Failed to save record to CSV: {e}")
            
            # Try to create a backup file if regular save failed
            try:
                backup_file = 'foundit_backup.csv'
                print(f"Attempting to save to backup file: {backup_file}")
                with open(backup_file, mode='a', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(record)
                print(f"✅ Successfully saved to backup CSV file")
            except Exception as backup_error:
                print(f"❌ ERROR saving to backup CSV: {backup_error}")
                
            return False

    def generate_url(self, job_title, job_location, start=0):
        base_url = "https://www.foundit.in/srp/results"
        query = f"?query={job_title.replace(' ', '+')}&locations={job_location.replace(' ', '+')}&start={start}"
        return base_url + query

    def sleep_for_random_interval(self, min_seconds=2, max_seconds=5):
        sleep_time = uniform(min_seconds, max_seconds)
        sleep(sleep_time)

    def scrape_job_details(self, job_link):
        """Scrape detailed information from a job details page"""
        job_description = role = industry = function = job_type = skills = posted_date = about_company = salary = "Not available"
        
        try:
            # Wait for the job details container to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "srpJdContainerTop"))
            )
            
            print("Job details page loaded successfully")
            
            # Job Description
            try:
                job_desc_elem = self.driver.find_element(By.ID, 'jobDescription')
                job_description = job_desc_elem.text.strip()
                print(f"\n--- JOB DESCRIPTION ---\n{job_description}\n")
            except:
                print("Job description element not found")
            
            # More Info section
            try:
                more_info = self.driver.find_element(By.CLASS_NAME, 'moreInfo')
                info_items = more_info.find_elements(By.TAG_NAME, 'p')
                
                # Also parse individual fields for better organization
                more_info_parts = []
                for item in info_items:
                    try:
                        # Check if this item has the key and value elements
                        key_elem = item.find_elements(By.CLASS_NAME, 'key')
                        value_elem = item.find_elements(By.CLASS_NAME, 'value')
                        
                        if key_elem and value_elem:
                            key = key_elem[0].text.strip().replace(':', '')
                            value = value_elem[0].text.strip()
                            
                            # Add formatted key-value pair to more_info_parts
                            more_info_parts.append(f"{key}:{value}")
                            
                            if key == "Role":
                                role = value
                            elif key == "Industry":
                                industry = value
                            elif key == "Function":
                                function = value
                            elif key == "Job Type":
                                job_type = value
                    except:
                        continue
                        
                # Create a combined more_info string with the desired format
                more_info = "\n".join(more_info_parts)
                print(f"\n--- MORE INFO ---\n{more_info}\n")
            except:
                print("More Info section not found")
            
            # Skills section
            try:
                skills_section = self.driver.find_element(By.ID, 'skillScoreSection')
                skill_items = skills_section.find_elements(By.CLASS_NAME, 'pillItem')
                
                if skill_items:
                    skills_list = [skill.text.strip() for skill in skill_items if skill.text.strip()]
                    skills = ", ".join(skills_list)
                    print(f"\n--- SKILLS REQUIRED ---\n{skills}\n")
            except:
                print("Skills section not found")
            
            # About Company
            try:
                company_section = self.driver.find_element(By.ID, 'jobCompany')
                company_desc = company_section.find_element(By.CLASS_NAME, 'companyDesc')
                about_company = company_desc.text.strip()
                print(f"\n--- ABOUT COMPANY ---\n{about_company}\n")
            except:
                print("About company section not found")
                
            # Get salary if available
            try:
                salary_element = self.driver.find_element(By.XPATH, "//span[contains(text(), 'INR') or contains(text(), 'LPA')]")
                if salary_element:
                    salary = salary_element.text.strip()
                    print(f"\n--- SALARY ---\n{salary}\n")
            except:
                print("Salary information not found")
                
            return {
                'job_description': job_description,
                'more_info': more_info,
                'skills': skills,
                'about_company': about_company,
                'salary': salary
            }
                
        except Exception as e:
            print(f"Error scraping job details: {e}")
            return {
                'job_description': "Not available",
                'more_info': "Not available",
                'skills': "Not available",
                'about_company': "Not available",
                'salary': "Not available"
            }

    def scrape(self):
        try:
            for job_title in self.job_titles:
                for job_location in self.job_locations:
                    logging.info(f"Scraping for '{job_title}' in '{job_location}'")
                    
                    # Only process the first page
                    url = self.generate_url(job_title, job_location, 0)
                    logging.info(f"Navigating to URL: {url}")
                    print(f"\nSearching for '{job_title}' in '{job_location}' - Page 1")
                    
                    # Navigate to the search results page
                    self.driver.get(url)
                    self.sleep_for_random_interval(3, 5)  # Longer wait for page load
                    
                    # Wait for page to load completely
                    try:
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.CLASS_NAME, 'srpResultCardContainer'))
                        )
                    except TimeoutException:
                        print("Timeout waiting for job cards to load. Check if page structure has changed.")
                        continue

                    # Find job cards
                    job_cards = self.driver.find_elements(By.CLASS_NAME, 'srpResultCardContainer')
                    
                    if not job_cards:
                        logging.warning("No job cards found on this page.")
                        print(f"No job listings found for {job_title} in {job_location}.")
                        continue
                    
                    num_cards = len(job_cards)
                    logging.info(f"Found {num_cards} job cards on page 1")
                    print(f"Found {num_cards} job listings to process")
                    
                    # Process each job card one by one
                    for i in range(num_cards):
                        print(f"\n{'='*50}")
                        print(f"Processing job {i+1}/{num_cards}")
                        print(f"{'-'*50}")
                        
                        # Re-get job cards before each access to avoid stale references
                        try:
                            job_cards = self.driver.find_elements(By.CLASS_NAME, 'srpResultCardContainer')
                            if i >= len(job_cards):
                                print(f"Job card index {i} out of range. Refreshing page.")
                                self.driver.refresh()
                                self.sleep_for_random_interval(2, 3)
                                job_cards = self.driver.find_elements(By.CLASS_NAME, 'srpResultCardContainer')
                                if i >= len(job_cards):
                                    print(f"Still can't find job card {i+1}. Skipping.")
                                    continue
                        except Exception as e:
                            print(f"Error refreshing job cards: {e}")
                            self.driver.get(url)
                            self.sleep_for_random_interval(2, 3)
                            job_cards = self.driver.find_elements(By.CLASS_NAME, 'srpResultCardContainer')
                            if i >= len(job_cards):
                                print(f"Cannot find job card {i+1} after refresh. Skipping.")
                                continue
                        
                        current_card = job_cards[i]
                        
                        # Extract basic info from the card before clicking
                        try:
                            # Get job title
                            job_title_elem = current_card.find_element(By.CLASS_NAME, 'jobTitle')
                            job_title_text = job_title_elem.text.strip()
                            
                            # Get company name
                            company_elem = current_card.find_element(By.CLASS_NAME, 'companyName')
                            company_name = company_elem.text.strip()
                            
                            # Create unique identifier
                            job_key = f"{job_title_text}_{company_name}"
                            
                            # Skip if we've seen this job before
                            if job_key in self.unique_jobs:
                                print(f"Skipping duplicate job: {job_title_text} at {company_name}")
                                continue
                                
                            print(f"Job: {job_title_text}")
                            print(f"Company: {company_name}")
                        except Exception as e:
                            print(f"Error extracting basic info from card: {e}")
                            continue
                        
                        # Scroll card into view
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", current_card)
                            self.sleep_for_random_interval(1, 2)
                        except Exception as e:
                            print(f"Error scrolling to card: {e}")
                        
                        # Click on the job card to view details
                        print("Clicking on job card...")
                        try:
                            # Try clicking on job title first
                            try:
                                job_title_elem.click()
                            except:
                                # Try clicking the card itself
                                try:
                                    current_card.click()
                                except:
                                    # Try JavaScript click as last resort
                                    self.driver.execute_script("arguments[0].click();", job_title_elem)
                        except Exception as e:
                            print(f"Failed to click job card: {e}")
                            continue
                        
                        # Wait for job details page to load
                        self.sleep_for_random_interval(3, 5)
                        
                        # Get job link
                        job_link = self.driver.current_url
                        print(f"Job URL: {job_link}")
                        
                        # Check if we're on a job details page - MODIFIED to detect job details more reliably
                        is_job_details_page = False
                        
                        # Method 1: Check URL pattern
                        if 'job-details' in job_link or 'job/' in job_link:
                            is_job_details_page = True
                            print("Detected job details page via URL pattern")
                        
                        # Method 2: Check for job details container
                        if not is_job_details_page:
                            try:
                                # Look for the srpJdContainerTop div which contains job details
                                job_details_container = self.driver.find_element(By.ID, 'srpJdContainerTop')
                                if job_details_container:
                                    is_job_details_page = True
                                    print("Detected job details page via job details container")
                            except:
                                pass
                                
                        # Method 3: Check for job description section
                        if not is_job_details_page:
                            try:
                                job_desc_elem = self.driver.find_element(By.ID, 'jobDescription')
                                if job_desc_elem:
                                    is_job_details_page = True
                                    print("Detected job details page via job description element")
                            except:
                                pass
                        
                        # Check for other common elements on job details pages
                        if not is_job_details_page:
                            try:
                                # Check for skills section
                                skills_section = self.driver.find_element(By.ID, 'skillScoreSection')
                                if skills_section:
                                    is_job_details_page = True
                                    print("Detected job details page via skills section")
                            except:
                                pass
                                
                        # Final check - look for more info section
                        if not is_job_details_page:
                            try:
                                more_info = self.driver.find_element(By.CLASS_NAME, 'moreInfo')
                                if more_info:
                                    is_job_details_page = True
                                    print("Detected job details page via more info section")
                            except:
                                pass
                        
                        if is_job_details_page:
                            print("Successfully detected job details page")
                            
                            # Extract all details from the job page
                            details = self.scrape_job_details(job_link)
                            
                            # Create record and save to CSV
                            record = [
                                job_title_text,
                                company_name,
                                details['salary'],
                                job_link,
                                details['job_description'],
                                details['more_info'],
                                details['skills'],
                                details['about_company']
                            ]
                            
                            self.save_record_to_csv(record)
                            self.unique_jobs.add(job_key)
                            print(f"✅ Saved to CSV - Total unique jobs: {len(self.unique_jobs)}")
                        else:
                            print("WARNING: Not on a job details page. Could not find job details elements")
                            
                            # Try an alternative approach - see if we're in a popup/modal
                            try:
                                print("Trying to detect job details in popup/modal...")
                                
                                # Look for common job details elements in any container
                                job_title_elem = self.driver.find_element(By.CLASS_NAME, 'jdTitle')
                                if job_title_elem:
                                    print("Found job title in popup/modal")
                                    
                                    # Try to extract what we can from this view
                                    job_description = "Not available"
                                    try:
                                        # Try to find any job description content
                                        job_desc_elems = self.driver.find_elements(By.XPATH, "//*[contains(@class, 'jobDesc')]")
                                        if job_desc_elems:
                                            job_description = job_desc_elems[0].text.strip()
                                            print(f"Found job description in popup: {len(job_description)} chars")
                                    except:
                                        pass
                                    
                                    # Create a minimal record with what we have
                                    record = [
                                        job_title_text,
                                        company_name,
                                        "Not available",  # salary
                                        job_link,
                                        job_description,
                                        "Not available",  # more info
                                        "Not available",  # skills
                                        "Not available"   # about company
                                    ]
                                    
                                    self.save_record_to_csv(record)
                                    self.unique_jobs.add(job_key)
                                    print(f"✅ Saved partial data to CSV (popup/modal view)")
                            except:
                                print("Could not find job details in popup/modal either. Skipping this job.")
                        
                        # Go back to search results page for next job
                        print("Returning to search results page...")
                        self.driver.get(url)
                        self.sleep_for_random_interval(2, 3)
                        
                    print(f"\n{'#'*50}")
                    print(f"Completed processing {len(self.unique_jobs)} jobs for {job_title} in {job_location}")
                    print(f"{'#'*50}")
            
            print("\nScraping completed successfully!")
            
        except Exception as e:
            logging.error(f"[ERROR] {e}")
        finally:
            self.driver.quit()
            logging.info(f"Job listings saved to '{self.output_file}'.")

if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("🔍 FOUNDIT.IN JOB SCRAPER 🔍".center(80))
    print("=" * 80 + "\n")
    
    # Get current directory to show file location
    current_dir = os.getcwd()
    output_file = os.path.join(current_dir, 'foundit.csv')
    
    job_titles = ['Full Stack Developer']
    job_locations = ['Pune']
    
    print(f"🔎 Searching for: {', '.join(job_titles)}")
    print(f"📍 Locations: {', '.join(job_locations)}")
    print(f"💾 Output file: {output_file}\n")
    
    scraper = FounditJob(job_titles, job_locations, output_file=output_file)
    
    print("🚀 Starting scraper...\n")
    scraper.scrape()
    
    # Verify file was created
    if os.path.exists(output_file):
        print(f"\n✅ CSV file exists at: {output_file}")
        file_size = os.path.getsize(output_file)
        print(f"File size: {file_size} bytes")
        
        # Try to read and count rows
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                line_count = sum(1 for _ in f)
            print(f"Lines in CSV: {line_count} (including header)")
        except Exception as e:
            print(f"Error reading CSV file: {e}")
    else:
        print(f"\n❌ CSV file doesn't exist at: {output_file}")
        
        # Check if backup file exists
        backup_file = os.path.join(current_dir, 'foundit_backup.csv')
        if os.path.exists(backup_file):
            print(f"✅ Backup CSV file exists at: {backup_file}")
            file_size = os.path.getsize(backup_file)
            print(f"Backup file size: {file_size} bytes")
    
    print("\n" + "=" * 80)
    print("✅ SCRAPING COMPLETED ✅".center(80))
    print("=" * 80)