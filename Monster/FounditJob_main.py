import logging
import csv
import random
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
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")  
        chrome_options.add_argument("--disable-software-rasterizer")  
        chrome_options.add_argument("--enable-unsafe-swiftshader")
        chrome_options.add_argument("--disable-webgl")  

        chrome_options.add_argument(f"user-agent={choice(USER_AGENTS)}")
        try:
            # Use webdriver-manager to automatically handle ChromeDriver compatibility
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            logging.info("Selenium WebDriver initialized successfully.")
            return driver
        except WebDriverException as e:
            logging.error(f"Error initializing Selenium WebDriver: {e}")
            raise

    def initialize_csv(self):
        with open(self.output_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Title', 'Company', 'Experience', 'Location', 'Job Link'])
        logging.info(f"CSV file '{self.output_file}' initialized with headers.")

    def save_record_to_csv(self, record):
        with open(self.output_file, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(record)

    def generate_url(self, job_title, job_location, start=15):
        base_url = "https://www.foundit.in/srp/results"
        query = f"?query={job_title.replace(' ', '+')}&locations={job_location.replace(' ', '+')}&start={start}"
        return base_url + query

    def extract_job_card_data(self, card):
        try:
            job_title = card.find('div', class_='jobTitle').text.strip() if card.find('div', class_='jobTitle') else 'N/A'
            print(job_title)
            company_name = card.find('div', class_='companyName').text.strip() if card.find('div', class_='companyName') else 'N/A'
            print(company_name)
            experience = card.find('span', class_='details').text.strip() if card.find('span', class_='details') else 'N/A'
            print(experience)
            job_location = card.find('div', class_='location').text.strip() if card.find('div', class_='location') else 'N/A'
            print(job_location)
            
            # Extract job link
            job_link = 'N/A'
            link_element = card.find('a', class_='cardUpper')
            if link_element and 'href' in link_element.attrs:
                job_link = 'https://www.foundit.in' + link_element['href']
            print(f"Job Link: {job_link}")
            
            return [job_title, company_name, experience, job_location, job_link]
        except Exception as e:
            logging.error(f"Error extracting data from job card: {e}")
            return None

    def on_data(self, record):
        if record and record[-1] not in self.unique_jobs:
            self.save_record_to_csv(record)
            self.unique_jobs.add(record[-1])

    def sleep_for_random_interval(self, min_seconds=3, max_seconds=6):
        sleep_time = uniform(min_seconds, max_seconds)
        sleep(sleep_time)

    def scrape(self):
        try:
            for job_title in self.job_titles:
                for job_location in self.job_locations:
                    logging.info(f"Scraping for '{job_title}' in '{job_location}'")
                    start = 0
                    while True:
                        url = self.generate_url(job_title, job_location, start)
                        logging.info(f"Navigating to URL: {url}")
                        self.driver.get(url)
                        self.sleep_for_random_interval()

                        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                        cards = soup.find_all('div', class_='srpResultCardContainer')

                        if not cards:
                            logging.warning("No job cards found on this page.")
                            break

                        for card in cards:
                            record = self.extract_job_card_data(card)
                            self.on_data(record)

                        try:
                            next_button = self.driver.find_element(By.XPATH, '//*[@id="srpContent"]/div[1]/div/div[17]')
                            if 'aria-disabled' in next_button.get_attribute('outerHTML'):
                                logging.info("No more pages found.")
                                break
                            else:
                                start += 15
                                self.sleep_for_random_interval()
                        except NoSuchElementException:
                            logging.info("No next page button found.")
                            break
        except Exception as e:
            logging.error(f"[ERROR] {e}")
        finally:
            self.driver.quit()
            logging.info(f"Job listings saved to '{self.output_file}'.")

if __name__ == '__main__':
    job_titles = ['Full Stack Developer']
    job_locations = ['Mumbai']
    scraper = FounditJob(job_titles, job_locations, output_file='foundit.csv')
    scraper.scrape()