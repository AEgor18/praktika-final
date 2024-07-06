import mysql.connector
from bs4 import BeautifulSoup as bs
import requests

mydb = mysql.connector.connect(
    host = '127.1.1.1',
    user = 'root',
    passwd = '12345',
    database = 'hh_ru'
)

mycursor = mydb.cursor()
mycursor.execute("ALTER TABLE vacancies AUTO_INCREMENT = 1")
mycursor.execute("TRUNCATE TABLE vacancies")
mydb.commit()

text = input()
items = 20
headers = {
    'Host': 'hh.ru',
    'User-Agent': 'Yandex',
    'Accept': '*/*',
    'Connection': 'keep-alive',
    'Accept-Encoding': 'gzip, deflate, br'
}

def get_url(page):
    url = f'https://hh.ru/search/vacancy?text={text}&salary=&ored_clusters=true&page={page}'
    response = requests.get(url, headers=headers)
    soup = bs(response.text, 'lxml')
    data = soup.find_all('div',  {'class': 'vacancy-search-item__card'})
    for i in data:
        card_url = i.find('a').get('href')
        yield card_url

def array():
    vacancy_count = 0
    page = 0
    while vacancy_count < items:
        try:
            for card_url in get_url(page):
                response = requests.get(card_url, headers=headers)
                soup = bs(response.text, 'lxml')
                data = soup.find('div', {'class': 'wrapper-flat--H4DVL_qLjKLCo1sytcNI'})
                data1 = soup.find('div', {'class': 'vacancy-company-redesigned'})
                if data:
                    position = data.find('h1', {'class': 'bloko-header-section-1'}).text
                    salary = data.find('span', {'class': 'magritte-text___pbpft_3-0-9 magritte-text_style-primary___AQ7MW_3-0-9 magritte-text_typography-label-1-regular___pi3R-_3-0-9'}).text.replace(' ', ' ')
                    description = data.find_all('p', {'class': 'vacancy-description-list-item'})
                    experience = description[0].text if description else "Не указано"
                    schedule1 = description[1].text
                    parts = schedule1.split(', ')
                    schedule = parts[0]
                    employment = parts[1] if len(parts) > 1 else None
                    company = data1.find('span', {'class': 'bloko-header-section-2 bloko-header-section-2_lite'}).text
                    address_element = data1.find('div', {'class': 'magritte-text___pbpft_3-0-9 magritte-text_style-primary___AQ7MW_3-0-9 magritte-text_typography-paragraph-2-regular___VO638_3-0-9'})
                    address = address_element.find('p').text if address_element else None
                    if address is None:
                        address1_element = data1.find('span', {'class': 'magritte-text___tkzIl_4-1-4'})
                        address = address1_element.find('span').text if address1_element else None
                    yield position, company, experience.replace('Требуемый опыт работы:', ''), salary, schedule, employment,  address
                    # print(position, company, experience.replace('Требуемый опыт работы:', ''), salary, schedule, employment,  address)
                    vacancy_count += 1
                    if vacancy_count >= items:
                        break
            page += 1
        except:
            pass

for item in array():
    position, company, experience, salary, employment, schedule, address = item
    mycursor.execute("INSERT INTO vacancies (position, company, experience, salary, employment, schedule, address) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                     (position, company, experience, salary, employment, schedule, address))
mydb.commit()


mycursor.execute('SELECT * FROM vacancies')
myresult = mycursor.fetchall()
