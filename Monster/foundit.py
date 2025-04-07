from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv

# Set up Selenium
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")  # Run without opening a window
chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Bypass bot detection
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

# Use webdriver_manager to handle driver compatibility
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
driver.get("https://www.foundit.in/srp/results?query=PHP+Developer&locations=usa")

print("Page Title:", driver.title)

jobs_container_element = driver.find_element(By.CLASS_NAME, "srpResultCard")
job_elements = jobs_container_element.find_elements(By.CLASS_NAME, "srpResultCardContainer")

jobs = []
for job in job_elements:
    try:
        job_title_element = job.find_elements(By.CLASS_NAME, "jobTitle")  
        job_title = job_title_element[0].text if job_title_element else "N/A"  

        company_name_element = job.find_elements(By.CLASS_NAME, "companyName")  
        company_name = company_name_element[0].text if company_name_element else "N/A"  

        experience_element = job.find_elements(By.CLASS_NAME, "details")  
        experience = experience_element[0].text if experience_element else "N/A"  

        job_location_element = job.find_elements(By.CLASS_NAME, "location")  
        job_location = job_location_element[0].text if job_location_element else "N/A"  

        job_title_element = jobs_container_element.find_element(By.CLASS_NAME, "infoSection")
        job_title_element.click()
        job_link = job.find_element(By.CLASS_NAME, "infoSection")
        job_link = driver.current_url

        
        print(f"Job Title: {job_title} | Company: {company_name} | Experience: {experience} | Location: {job_location} | Job Link: {job_link} ")
        
        print('--' * 68)

        # Save the job data in the list
        jobs.append({
            'Job Title': job_title,
            'Company': company_name,
            'Experience': experience,
            'Location': job_location,
            'Job Link': job_link,
        })
    
    except Exception as e:
            print(f"Error extracting job details: {e}")


# Save job data to CSV

csv_file = "foundit_jobs.csv"
csv_headers = ["Job Title", "Company", "Experience", "Location","Job Link"]

with open("foundit_jobs.csv", "w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=csv_headers)
    writer.writeheader()
    writer.writerows(jobs)

print("Data saved to foundit_jobs.csv successfully!")

# Close the web driver            
driver.quit()