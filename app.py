from flask import Flask, render_template, request,  url_for, redirect
import mysql.connector
from bs4 import BeautifulSoup as bs
import requests
import time
import os 

app = Flask(__name__)

headers = {
    'Host': 'hh.ru',
    'User-Agent': 'Yandex',
    'Accept': '*/*',
    'Connection': 'keep-alive',
    'Accept-Encoding': 'gzip, deflate, br'
}

DATABASE_HOST = os.getenv('DATABASE_HOST', 'db')
DATABASE_USER = os.getenv('DATABASE_USER', 'root')
DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD', '123456')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'hh_ru')


retries = 5
while retries > 0:
    try:
        mydb = mysql.connector.connect(
            host=DATABASE_HOST,
            user=DATABASE_USER,
            passwd=DATABASE_PASSWORD,
            database=DATABASE_NAME
        )
        mycursor = mydb.cursor()
        mycursor.execute(mycursor.execute("""CREATE TABLE IF NOT EXISTS resume (
                 id INTEGER AUTO_INCREMENT PRIMARY KEY,
                 position VARCHAR(255),
                 experience VARCHAR(255),
                 salary INTEGER,
                 currency VARCHAR(255),
                 last_job VARCHAR(255)
                 )"""))
        mycursor.execute(mycursor.execute("""CREATE TABLE IF NOT EXISTS vacancies (
                id INTEGER AUTO_INCREMENT PRIMARY KEY,
                position VARCHAR(255),
                company VARCHAR(255),
                experience VARCHAR(255),
                salary VARCHAR(255),
                employment VARCHAR(255),
                schedule VARCHAR(255),
                address VARCHAR(255)
                )"""))

        break
    except mysql.connector.Error as err:
        app.logger.error(f"Error: {err}")
        retries -= 1
        time.sleep(5)  # Задержка 5 секунд перед повторной попыткой

if retries == 0:
    raise RuntimeError("Failed to connect to the database after several attempts")

mycursor = mydb.cursor()
mycursor.execute("TRUNCATE TABLE vacancies")
mycursor.execute("ALTER TABLE vacancies AUTO_INCREMENT = 1")
mydb.commit()
mycursor.execute("TRUNCATE TABLE resume")
mycursor.execute("ALTER TABLE resume AUTO_INCREMENT = 1")
mydb.commit()
def parse_resumes(text, min_salary=None, max_salary=None, items=50):
    mycursor.execute("TRUNCATE TABLE resume")
    mycursor.execute("ALTER TABLE resume AUTO_INCREMENT = 1")
    mydb.commit()
    resume_count = 0
    page = 0
    while resume_count < items:
        url = f'https://hh.ru/search/resume?text={text}&exp_period=all_time&logic=normal&pos=full_text&page={page}'
        response = requests.get(url, headers=headers)
        soup = bs(response.text, 'lxml')
        data = soup.find_all('div', {'class': 'wrapper--eiknuhp1KcZ2hosUJO7g'})
        for i in data:
            try:
                position = i.find('a', 'bloko-link').text
                experience = i.find('div', {'class': 'content--uYCSpLiTsRfIZJe2wiYy'}).text.replace(' ', ' ')
                salary_str = i.find('div', {'class': 'bloko-text bloko-text_strong'}).text
                currency = salary_str[-2:]
                salary = int(salary_str[:-2].replace(' ', ''))
                last_job = i.find('span', {'class': 'bloko-text bloko-text_strong'}).text
                if min_salary and salary < min_salary:
                    continue
                if max_salary and salary > max_salary:
                    continue
                mycursor.execute("INSERT INTO resume (position, experience, salary, currency, last_job) VALUES (%s, %s, %s, %s, %s)",
                                 (position, experience, int(salary), currency, last_job))
                mydb.commit()
                resume_count += 1
                if resume_count >= items:
                    break
            except:
                pass
        page += 1

def parse_vacancies(text, items=30):
    mycursor.execute("TRUNCATE TABLE vacancies")
    mycursor.execute("ALTER TABLE vacancies AUTO_INCREMENT = 1")
    mydb.commit()
    def get_url(page):
        try:
            url = f'https://hh.ru/search/vacancy?text={text}&salary=&ored_clusters=true&page={page}'
            response = requests.get(url, headers=headers)
            soup = bs(response.text, 'lxml')
            data = soup.find_all('div', {'class': 'vacancy-search-item__card'})
            for i in data:
                card_url = i.find('a').get('href')
                yield card_url
        except:
            pass
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
                        salary = data.find('span', {
                            'class': 'magritte-text___pbpft_3-0-9 magritte-text_style-primary___AQ7MW_3-0-9 magritte-text_typography-label-1-regular___pi3R-_3-0-9'}).text.replace(
                            ' ', ' ')
                        description = data.find_all('p', {'class': 'vacancy-description-list-item'})
                        experience = description[0].text if description else "Не указано"
                        schedule1 = description[1].text
                        parts = schedule1.split(', ')
                        schedule = parts[0]
                        employment = parts[1] if len(parts) > 1 else None
                        company = data1.find('span',
                                             {'class': 'bloko-header-section-2 bloko-header-section-2_lite'}).text
                        address_element = data1.find('div', {
                            'class': 'magritte-text___pbpft_3-0-9 magritte-text_style-primary___AQ7MW_3-0-9 magritte-text_typography-paragraph-2-regular___VO638_3-0-9'})
                        address = address_element.find('p').text if address_element else None
                        if address is None:
                            address1_element = data1.find('span', {'class': 'magritte-text___tkzIl_4-1-4'})
                            address = address1_element.find('span').text if address1_element else None
                        yield position, company, experience.replace('Требуемый опыт работы: ',
                                                                    ''), salary, schedule, employment, address
                        # print(position, company, experience.replace('Требуемый опыт работы:', ''), salary, schedule, employment,  address)
                        vacancy_count += 1
                        if vacancy_count >= items:
                            break
                    page += 1
            except:
                pass

    for item in array():
        position, company, experience, salary, employment, schedule, address = item
        mycursor.execute(
            "INSERT INTO vacancies (position, company, experience, salary, employment, schedule, address) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (position, company, experience, salary, employment, schedule, address))
    mydb.commit()

@app.route('/', methods=['GET'])
def main():
    return render_template('main.html')

@app.route('/process', methods=['POST'])
def process():
    text = request.form['text']
    parse_resumes(text)
    return redirect(url_for('index', text=text))


@app.route('/index', methods=['GET', 'POST'])
def index():
    text = request.args.get('text')
    if request.method == 'POST':
        text = request.form.get('text')
        min_salary = request.form.get('min_salary', type=int)
        max_salary = request.form.get('max_salary', type=int)
        parse_resumes(text, min_salary, max_salary)
        query = "SELECT * FROM resume WHERE TRUE"
        query_params = []
        if min_salary is not None:
            query += " AND salary >= %s"
            query_params.append(min_salary)
        if max_salary is not None:
            query += " AND salary <= %s"
            query_params.append(max_salary)

        mycursor.execute(query, query_params)
        resumes = mycursor.fetchall()
        return render_template('index.html', resumes=resumes, text=text)
    else:
        mycursor.execute("SELECT * FROM resume")
        resumes = mycursor.fetchall()
        return render_template('index.html', resumes=resumes)


@app.route('/vacancies', methods=['GET', 'POST'])
def vacancies():
    if request.method == 'POST':
        text = request.form.get('text')
        employment_filter = request.form.getlist('employment')
        schedule_filter = request.form.getlist('schedule')
        experience_filter = request.form.getlist('experience')
        parse_vacancies(text)

        query = "SELECT * FROM vacancies"
        query_params = []
        filters = []
        if employment_filter:
            filters.append("employment IN ({})".format(', '.join(['%s'] * len(employment_filter))))
            query_params.extend(employment_filter)
        if schedule_filter:
            filters.append("schedule IN ({})".format(', '.join(['%s'] * len(schedule_filter))))
            query_params.extend(schedule_filter)
        if experience_filter:
            filters.append("experience IN ({})".format(', '.join(['%s'] * len(experience_filter))))
            query_params.extend(experience_filter)

        if filters:
            query += " WHERE " + " AND ".join(filters)

        mycursor.execute(query, query_params)
        vacancies = mycursor.fetchall()
        query_params.clear()
        filters.clear()
        return render_template('vacancies.html', vacancies=vacancies, text=text)
    else:
        mycursor.execute("SELECT * FROM vacancies")
        vacancies = mycursor.fetchall()
        return render_template('vacancies.html', vacancies=vacancies)


if __name__ == '__main__':
    app.run(debug=True)