import logging
import csv
import random
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from bs4 import BeautifulSoup
from time import sleep
from random import uniform, choice
from datetime import datetime

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
        # Remove headless mode for better interaction with elements
        # chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")  
        chrome_options.add_argument("--disable-software-rasterizer")  
        chrome_options.add_argument("--enable-unsafe-swiftshader")
        chrome_options.add_argument("--disable-webgl")  

        chrome_options.add_argument(f"user-agent={choice(USER_AGENTS)}")
        try:
            # Use webdriver-manager to automatically handle ChromeDriver compatibility
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            # Set page load timeout
            driver.set_page_load_timeout(30)
            logging.info("Selenium WebDriver initialized successfully.")
            return driver
        except WebDriverException as e:
            logging.error(f"Error initializing Selenium WebDriver: {e}")
            raise

    def initialize_csv(self):
        with open(self.output_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Job Title', 'Company', 'Experience', 'Location', 'Job Link', 'Job Description', 'More Info', 'Skills Required', 'About Company'])
        logging.info(f"CSV file '{self.output_file}' initialized with headers.")

    def save_record_to_csv(self, record):
        with open(self.output_file, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(record)

    def generate_url(self, job_title, job_location, start=0):
        base_url = "https://www.foundit.in/srp/results"
        query = f"?query={job_title.replace(' ', '+')}&locations={job_location.replace(' ', '+')}&start={start}"
        return base_url + query

    def verify_page_number(self, expected_start):
        """Verify we're on the correct page number and fix if not"""
        current_url = self.driver.current_url
        if f"start={expected_start}" not in current_url:
            logging.warning(f"URL doesn't reflect expected page (start={expected_start}). Current URL: {current_url}")
            
            # Try to extract the current job title and location from URL
            import re
            query_match = re.search(r'query=([^&]+)', current_url)
            locations_match = re.search(r'locations=([^&]+)', current_url)
            
            if query_match and locations_match:
                job_title = query_match.group(1).replace('+', ' ')
                job_location = locations_match.group(1).replace('+', ' ')
                
                # Generate the correct URL and navigate to it
                correct_url = self.generate_url(job_title, job_location, expected_start)
                logging.info(f"Navigating to correct page URL: {correct_url}")
                self.driver.get(correct_url)
                self.sleep_for_random_interval(2, 3)
                return True
            return False
        return True

    def extract_job_card_data(self, card):
        try:
            # Extract job title - check both list and detail view selectors
            job_title_element = card.find('div', class_='jobTitle') or card.find('h1', class_='jdTitle')
            job_title = job_title_element.text.strip() if job_title_element else 'N/A'
            
            # Extract company name - check both list and detail view selectors
            company_element = card.find('div', class_='companyName') or card.find('div', class_='jdCompanyName')
            company_name = company_element.text.strip() if company_element else 'N/A'
            
            # Extract experience - try multiple selectors/approaches
            experience = 'N/A'
            try:
                # First attempt: using highlightsRow class
                experience_element = card.find('div', class_='highlightsRow')
                if experience_element:
                    # Look for experience within highlights
                    exp_text = experience_element.text.strip()
                    # Try to find the pattern that typically indicates experience
                    exp_match = re.search(r'(\d+\s*-\s*\d+|\d+\+)\s*[Yy]ears?', exp_text)
                    if exp_match:
                        experience = exp_match.group(0)
                    else:
                        experience = exp_text
            except:
                pass
                
            if experience == 'N/A':
                try:
                    # Second attempt: try finding elements with class containing 'experience'
                    exp_elements = [e for e in card.find_all() if 'experience' in str(e.get('class', '')).lower()]
                    if exp_elements:
                        experience = exp_elements[0].text.strip()
                except:
                    pass
                    
            if experience == 'N/A':
                try:
                    # Third attempt: look for specific patterns in card text
                    card_text = card.text
                    exp_patterns = [
                        r'(\d+\s*-\s*\d+|\d+\+)\s*[Yy]ears?',  # matches "3-5 Years" or "5+ Years"
                        r'[Ee]xperience\s*:\s*([^,\n]+)',       # matches "Experience: 5 Years"
                        r'[Ee]xp\s*:\s*([^,\n]+)',              # matches "Exp: 5 Years"
                        r'[Ee]xperience\s*([^,\n]+)'            # matches "Experience 5 Years"
                    ]
                    
                    for pattern in exp_patterns:
                        exp_match = re.search(pattern, card_text)
                        if exp_match:
                            experience = exp_match.group(0)
                            break
                except:
                    pass
            
            # Extract location - using location class
            location_element = card.find('div', class_='location')
            job_location = location_element.text.strip() if location_element else 'N/A'
            
            return [job_title, company_name, experience, job_location, 'placeholder_for_link']
        except Exception as e:
            logging.error(f"Error extracting data from job card: {e}")
            return None

    def on_data(self, record):
        if record is None:
            return
            
        # Create a unique identifier using job title and company
        unique_id = f"{record[0]}_{record[1]}"
        if unique_id not in self.unique_jobs:
            self.save_record_to_csv(record)
            self.unique_jobs.add(unique_id)
            
            # Print job details in CSV format
            print("\n" + "=" * 80)
            print("CSV FORMAT OUTPUT:")
            print("-" * 30)
            
            # Print headers
            headers = ['Job Title', 'Company', 'Experience', 'Location', 'Job Link', 'Job Description', 'More Info', 'Skills Required', 'About Company']
            
            # Print each field with its header
            for i, field in enumerate(headers):
                print(f"{field}: {record[i]}")
                
            print("=" * 80)
            
            logging.info(f"Added new job: {record[0]} at {record[1]}")
        else:
            logging.info(f"Skipped duplicate job: {record[0]} at {record[1]}")
            
        print("+" * 50)

    def sleep_for_random_interval(self, min_seconds=3, max_seconds=6):
        sleep_time = uniform(min_seconds, max_seconds)
        sleep(sleep_time)

    def scrape(self):
        try:
            for job_title in self.job_titles:
                for job_location in self.job_locations:
                    logging.info(f"Scraping for '{job_title}' in '{job_location}'")
                    start = 0
                    current_page = 1
                    
                    while True:
                        url = self.generate_url(job_title, job_location, start)
                        logging.info(f"Navigating to URL: {url}")
                        self.driver.get(url)
                        self.sleep_for_random_interval()

                        # Wait for page to load completely
                        try:
                            self.driver.execute_script("return document.readyState") == "complete"
                        except:
                            pass
                            
                        # Verify we're on the correct page
                        self.verify_page_number(start)
                        
                        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                        # Try both possible card container classes
                        cards = soup.find_all('div', class_='srpResultCardContainer') or soup.find_all('div', class_='card')

                        if not cards:
                            logging.warning("No job cards found on this page.")
                            break

                        # Get all job cards using Selenium for clicking
                        job_cards = self.driver.find_elements(By.CLASS_NAME, 'srpResultCardContainer') or self.driver.find_elements(By.CLASS_NAME, 'card')
                        
                        if not job_cards:
                            logging.warning("No job cards found with Selenium.")
                            break
                        
                        logging.info(f"Found {len(job_cards)} job cards on this page")
                        print(f"\n[Page {current_page}] Processing {len(job_cards)} jobs for {job_title} in {job_location}...")
                        
                        # Process all job cards on the current page
                        for i, card in enumerate(cards):
                            if i >= len(job_cards):
                                break
                                
                            print(f"\n[Page {current_page}] Processing job {i+1}/{len(job_cards)}")
                            
                            # First extract basic job data from BeautifulSoup
                            record = self.extract_job_card_data(card)
                            
                            if record:
                                try:
                                    # Re-get job cards as the DOM may have changed
                                    job_cards = self.driver.find_elements(By.CLASS_NAME, 'srpResultCardContainer') or self.driver.find_elements(By.CLASS_NAME, 'card')
                                    
                                    if i >= len(job_cards):
                                        logging.warning(f"Job card index {i} out of range after DOM refresh. Skipping.")
                                        continue
                                    
                                    # Try different approaches to click on the job card
                                    try:
                                        # Try clicking job title first
                                        job_title_elem = job_cards[i].find_element(By.CLASS_NAME, 'jobTitle') or job_cards[i].find_element(By.CLASS_NAME, 'jdTitle')
                                        self.driver.execute_script("arguments[0].click();", job_title_elem)
                                    except:
                                        try:
                                            # Try clicking on card header
                                            card_elem = job_cards[i].find_element(By.CLASS_NAME, 'cardUpper') or job_cards[i].find_element(By.CLASS_NAME, 'jdHeaderNew')
                                            self.driver.execute_script("arguments[0].click();", card_elem)
                                        except:
                                            try:
                                                # Last resort - click the card itself
                                                self.driver.execute_script("arguments[0].click();", job_cards[i])
                                            except Exception as e:
                                                logging.error(f"Failed to click job card: {e}")
                                                continue
                                    
                                    # Wait for the job details page to load
                                    self.sleep_for_random_interval(2, 3)
                                    
                                    # Get the current URL which should be the job details page
                                    job_link = self.driver.current_url
                                    
                                    # Verify we're actually on a job detail page, not still on search results
                                    if 'job-details' in job_link or 'job/' in job_link:
                                        logging.info(f"Successfully navigated to job detail page: {job_link}")
                                    else:
                                        # If we're still on search results, try to get the link directly
                                        try:
                                            # First attempt - try to find a direct link in the card
                                            link_elem = job_cards[i].find_element(By.TAG_NAME, 'a')
                                            direct_link = link_elem.get_attribute('href')
                                            if direct_link and ('job-details' in direct_link or 'job/' in direct_link):
                                                job_link = direct_link
                                                logging.info(f"Using direct link from card: {job_link}")
                                                # Navigate to this link
                                                self.driver.get(job_link)
                                                self.sleep_for_random_interval(2, 3)
                                        except:
                                            logging.warning("Could not find direct job link in card")
                                            
                                    # Double-check we're not still on search results page
                                    if 'srp/results' in job_link or 'searchId' in job_link:
                                        logging.warning(f"Failed to navigate to job detail page, still on search results: {job_link}")
                                        job_link = "Failed to retrieve job detail link"
                                    
                                    # Extract More Info section (Role, Industry, Function, Job Type)
                                    role = industry = function = job_type = "N/A"
                                    try:
                                        more_info = self.driver.find_element(By.CLASS_NAME, 'moreInfo')
                                        info_items = more_info.find_elements(By.TAG_NAME, 'p')
                                        
                                        for item in info_items:
                                            try:
                                                key_elem = item.find_element(By.CLASS_NAME, 'key')
                                                value_elem = item.find_element(By.CLASS_NAME, 'value')
                                                
                                                key = key_elem.text.strip().replace(':', '')
                                                value = value_elem.text.strip()
                                                
                                                if "Role" in key:
                                                    role = value
                                                elif "Industry" in key:
                                                    industry = value
                                                elif "Function" in key:
                                                    function = value
                                                elif "Job Type" in key:
                                                    job_type = value
                                            except:
                                                continue
                                        
                                    except:
                                        logging.info(f"No 'More Info' section found for {record[0]}")
                                    
                                    # Extract Skills Required
                                    skills_required = "N/A"
                                    try:
                                        skills_section = self.driver.find_element(By.ID, 'skillScoreSection')
                                        skill_items = skills_section.find_elements(By.CLASS_NAME, 'pillItem')
                                        
                                        if skill_items:
                                            skills_list = [skill.text.strip() for skill in skill_items if skill.text.strip()]
                                            skills_required = ", ".join(skills_list)
                                    except:
                                        try:
                                            # Alternative approach - try finding elements with class containing "skill"
                                            skill_elements = self.driver.find_elements(By.XPATH, "//*[contains(@class, 'skill')]")
                                            if skill_elements:
                                                skills_list = []
                                                for elem in skill_elements:
                                                    if elem.text and len(elem.text.strip()) < 30:  # Likely a skill, not a container
                                                        skills_list.append(elem.text.strip())
                                                
                                                if skills_list:
                                                    skills_required = ", ".join(skills_list)
                                        except:
                                            logging.info(f"No skills found for {record[0]}")
                                    
                                    # Extract About Company
                                    about_company = "N/A"
                                    company_link = "N/A"
                                    try:
                                        # Try to find company description using the specific classes from the HTML structure
                                        company_container = self.driver.find_element(By.ID, 'jobCompany')
                                        
                                        # Try to extract company link
                                        try:
                                            company_name_element = company_container.find_element(By.CLASS_NAME, 'companyName')
                                            if company_name_element.tag_name == 'a' and company_name_element.get_attribute('href'):
                                                company_link = company_name_element.get_attribute('href')
                                                if not company_link.startswith('http'):
                                                    company_link = 'https://www.foundit.in' + company_link
                                        except:
                                            try:
                                                # Alternative way to find company link
                                                company_link_element = company_container.find_element(By.XPATH, ".//a[contains(@class, 'company')]")
                                                company_link = company_link_element.get_attribute('href')
                                                if not company_link.startswith('http'):
                                                    company_link = 'https://www.foundit.in' + company_link
                                            except:
                                                logging.info(f"No company link found for {record[0]}")
                                        
                                        # Get company description
                                        company_desc = company_container.find_element(By.CLASS_NAME, 'companyDesc')
                                        
                                        if company_desc:
                                            about_company = company_desc.text.strip()
                                    except:
                                        try:
                                            # Alternative approach - try finding section with company information
                                            company_section = self.driver.find_element(By.CLASS_NAME, 'companySection')
                                            
                                            # Try to extract company link
                                            try:
                                                company_name_element = company_section.find_element(By.CLASS_NAME, 'companyName')
                                                if company_name_element.tag_name == 'a' and company_name_element.get_attribute('href'):
                                                    company_link = company_name_element.get_attribute('href')
                                                    if not company_link.startswith('http'):
                                                        company_link = 'https://www.foundit.in' + company_link
                                            except:
                                                logging.info(f"No company link found in company section for {record[0]}")
                                            
                                            company_paragraphs = company_section.find_elements(By.TAG_NAME, 'p')
                                            
                                            if company_paragraphs:
                                                about_company = "\n".join([p.text.strip() for p in company_paragraphs if p.text.strip()])
                                        except:
                                            logging.info(f"No company description found for {record[0]}")
                                    
                                    # Update About Company to include the link
                                    if company_link != "N/A":
                                        about_company = f"{about_company}\n\nCompany Profile: {company_link}"
                                    
                                    # Also try to get job description if available
                                    job_description = "N/A"
                                    try:
                                        # Try to get job description using the specific classes from the HTML structure
                                        job_desc_container = self.driver.find_element(By.CLASS_NAME, 'jobDescNewContainer')
                                        job_desc_content = job_desc_container.find_element(By.CLASS_NAME, 'jobDescriptionNew')
                                        job_desc_info = job_desc_content.find_elements(By.CLASS_NAME, 'jobDescInfoNew')
                                        
                                        if job_desc_info:
                                            # Combine all paragraphs of the job description
                                            job_description = "\n".join([info.text for info in job_desc_info if info.text.strip()])
                                        else:
                                            # Fallback to the entire container text
                                            job_description = job_desc_content.text.strip()
                                    except:
                                        try:
                                            # First backup approach: Try using the jobDescription ID
                                            job_desc_elem = self.driver.find_element(By.ID, 'jobDescription')
                                            job_description = job_desc_elem.text.strip()
                                        except:
                                            try:
                                                # Second backup: just find any job description container
                                                job_desc_elem = self.driver.find_element(By.XPATH, "//*[contains(@class, 'jobDesc')]")
                                                job_description = job_desc_elem.text.strip()
                                            except:
                                                logging.info(f"No job description found for {record[0]}")
                                    
                                    # Update the record with all the data in the correct sequence
                                    record[4] = job_link
                                    record.append(job_description)
                                    record.append(f"Role: {role}, Industry: {industry}, Function: {function}, Job Type: {job_type}")
                                    record.append(skills_required)
                                    record.append(about_company)
                                    
                                    # Try to find related/similar jobs before navigating back
                                    similar_jobs = []
                                    try:
                                        # Look for similar jobs section - could be SimilarJobs, RecommendedJobs, etc.
                                        similar_jobs_section = None
                                        possible_selectors = [
                                            'similarJobsNew', 
                                            'recommendedJobsContainer', 
                                            'similarJobsWidget',
                                            'similarJobs'
                                        ]
                                        
                                        for selector in possible_selectors:
                                            try:
                                                similar_jobs_section = self.driver.find_element(By.ID, selector) or self.driver.find_element(By.CLASS_NAME, selector)
                                                if similar_jobs_section:
                                                    logging.info(f"Found similar jobs section with selector: {selector}")
                                                    break
                                            except:
                                                continue
                                                
                                        if similar_jobs_section:
                                            # Try to find job cards within the similar jobs section
                                            similar_job_cards = similar_jobs_section.find_elements(By.CLASS_NAME, 'jobCard') or \
                                                              similar_jobs_section.find_elements(By.CLASS_NAME, 'card') or \
                                                              similar_jobs_section.find_elements(By.CLASS_NAME, 'srpResultCardContainer')
                                                              
                                            if similar_job_cards:
                                                logging.info(f"Found {len(similar_job_cards)} similar job cards")
                                                
                                                # Process each similar job (up to 3 to avoid too much processing)
                                                for i, similar_card in enumerate(similar_job_cards[:3]):
                                                    try:
                                                        # Extract basic info from the similar job card
                                                        job_title_elem = similar_card.find_element(By.CLASS_NAME, 'jobTitle')
                                                        job_title = job_title_elem.text.strip() if job_title_elem else 'N/A'
                                                        
                                                        company_elem = similar_card.find_element(By.CLASS_NAME, 'companyName')
                                                        company = company_elem.text.strip() if company_elem else 'N/A'
                                                        
                                                        # Try to find experience
                                                        experience = 'N/A'
                                                        try:
                                                            experience_elem = similar_card.find_element(By.XPATH, ".//*[contains(text(), 'Year')]")
                                                            if experience_elem:
                                                                experience = experience_elem.text.strip()
                                                        except:
                                                            pass
                                                            
                                                        # Try to find location
                                                        location = 'N/A'
                                                        try:
                                                            location_elem = similar_card.find_element(By.CLASS_NAME, 'location')
                                                            if location_elem:
                                                                location = location_elem.text.strip()
                                                        except:
                                                            pass
                                                            
                                                        # Try to get the job link
                                                        similar_job_link = 'N/A'
                                                        try:
                                                            link_elem = job_title_elem if job_title_elem.tag_name == 'a' else similar_card.find_element(By.TAG_NAME, 'a')
                                                            similar_job_link = link_elem.get_attribute('href')
                                                            if not similar_job_link.startswith('http'):
                                                                similar_job_link = 'https://www.foundit.in' + similar_job_link
                                                        except:
                                                            pass
                                                            
                                                        if job_title != 'N/A' and company != 'N/A':
                                                            similar_job_record = [
                                                                job_title,
                                                                company,
                                                                experience,
                                                                location,
                                                                similar_job_link,
                                                                "To be viewed directly",  # Job Description
                                                                "Related job - see link for details",  # More Info
                                                                "Check job link for skills",  # Skills
                                                                f"Related to: {record[0]} at {record[1]}"  # About Company
                                                            ]
                                                            self.on_data(similar_job_record)
                                                    except Exception as e:
                                                        logging.error(f"Error processing similar job: {e}")
                                    except Exception as e:
                                        logging.error(f"Error processing similar jobs section: {e}")
                                    
                                    # Go back to the search results page
                                    self.driver.back()
                                    self.sleep_for_random_interval(1, 2)
                                    
                                    # Re-get job cards as we're back on the search page
                                    job_cards = self.driver.find_elements(By.CLASS_NAME, 'srpResultCardContainer') or self.driver.find_elements(By.CLASS_NAME, 'card')
                                    
                                except Exception as e:
                                    logging.error(f"Error getting job link: {e}")
                                    record[4] = "Error retrieving link"
                                    
                                    # Try to get back to the search results page if we're stuck
                                    try:
                                        self.driver.get(url)
                                        self.sleep_for_random_interval(1, 2)
                                        job_cards = self.driver.find_elements(By.CLASS_NAME, 'srpResultCardContainer') or self.driver.find_elements(By.CLASS_NAME, 'card')
                                    except:
                                        pass
                                
                                # Save the record with the job link
                                self.on_data(record)
                        
                        # After processing all jobs on this page, move to the next page
                        logging.info(f"Finished processing all jobs on page {current_page}")
                        print(f"\n✅ Completed page {current_page} for {job_title} in {job_location}. Checking for next page...")
                        
                        # Increment for next page
                        start += 15
                        current_page += 1
                        
                        # Try to navigate to the next page
                        next_page_url = self.generate_url(job_title, job_location, start)
                        print(f"Moving to page {current_page} for {job_title} in {job_location}...")
                        self.driver.get(next_page_url)
                        self.sleep_for_random_interval(2, 3)
                        
                        # Check if we actually got results on the next page
                        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                        no_results = soup.find('div', class_='noResults')
                        next_cards = soup.find_all('div', class_='srpResultCardContainer') or soup.find_all('div', class_='card')
                        
                        if no_results or not next_cards:
                            logging.info(f"No more results found on page {current_page}")
                            print(f"No more results for {job_title} in {job_location}. Moving to next search.")
                            break
                        
                        logging.info(f"Successfully navigated to page {current_page}")
                        # Continue to process this new page in the next loop iteration
        except Exception as e:
            logging.error(f"[ERROR] {e}")
        finally:
            self.driver.quit()
            logging.info(f"Job listings saved to '{self.output_file}'.")

if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("🔍 FOUNDIT.IN JOB SCRAPER 🔍".center(80))
    print("=" * 80 + "\n")
    
    # More comprehensive job titles and locations for wider coverage
    job_titles = [
        'Full Stack Developer', 
        'Frontend Developer',
        'Backend Developer',
        'Software Engineer',
        'Web Developer'
    ]
    
    job_locations = [
        'Pune', 
        'Mumbai',
        'Bangalore',
        'Delhi',
        'Hyderabad'
    ]
    
    print(f"🔎 Searching for: {', '.join(job_titles)}")
    print(f"📍 Locations: {', '.join(job_locations)}")
    print(f"💾 Output file: foundit.csv\n")
    
    scraper = FounditJob(job_titles, job_locations, output_file='foundit.csv')
    
    print("🚀 Starting scraper...\n")
    scraper.scrape()
    
    print("\n" + "=" * 80)
    print("✅ SCRAPING COMPLETED ✅".center(80))
    print("=" * 80)