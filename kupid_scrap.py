#크롬 기반으로 돌아가는 코드이기에 크롬이 깔려 있어야 함.
#만약 크롬을 깔기 어려운 환경이라면 해당 컴퓨터에 있는 인터넷 드라이버로 변경 가능
#설치 필요 파이썬 모듈: beautifulsoup4(bs4), requests, selenium, psycopg2, python-dotenv
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import pickle
from selenium.common.exceptions import NoSuchElementException
import psycopg2
import os
from selenium.webdriver.common.keys import Keys
from dotenv import load_dotenv
from pyvirtualdisplay import Display
display = Display(visible=0, size=(800, 600))
display.start()
load_dotenv()#.env 활용

#속도 빠르게 하기 위한 headless, image disable, gpu disable 기능 등

options = webdriver.ChromeOptions()

options.add_argument('--disable-images')
options.add_experimental_option("prefs", {'profile.managed_default_content_settings.images': 2})
options.add_argument('--blink-settings=imagesEnabled=false')

options.add_argument('--headless') 
options.add_argument("--disable-infobars")

options.add_argument('--ignore-ssl-errors=yes')
options.add_argument('--ignore-certificate-errors')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--no-sandbox')
options.add_argument('--log-level=3')
options.add_argument('--disable-gpu')
options.add_argument('--incognito')
user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
options.add_argument(f'user-agent={user_agent}')


#postgresql 접근
conn = psycopg2.connect(host=os.getenv("DB_HOST"), dbname=os.getenv("DB_DATABASE"), user=os.getenv("DB_USERNAME"), password=os.getenv("DB_PASSWORD"), port=os.getenv("DB_PORT"))
cur = conn.cursor()

# notice ids for notification
ids =[]

#일반 공지사항/장학금 공지사항/학사일정 알림 url
url = 'https://grw.korea.ac.kr/GroupWare/user/NoticeList.jsp?kind='
notice_list = ['11', '88', '89']#각각 일반공지, 장학금공지, 학사일정공지
driver = webdriver.Chrome(options = options)

driver.get(url)

print (driver.page_source)
#맨 처음 기동 시 url 즉시 접속 가능하게 하는 쿠키 저장 필요.
#try-except로 쿠키 만료 및 에러 확인. 에러 발생 시 쿠키 재저장
#모든 글에 접속하면 굉장히 느려지기에 html로 사전 검사 후 새로운 글들만 접근

try:#쿠키로 로그인 과정 생략
    cookies = pickle.load(open("kupid_cookies.pkl", 'rb'))
    for cookie in cookies:
        driver.add_cookie(cookie)
    driver.get(url+notice_list[0])
    cookiecheck = driver.find_element(By.XPATH, '//*[@id="Search"]/div[1]/div[1]/span[2]')
    
except:#쿠키 만료시(접속 불가 시) 수동 로그인으로 쿠키 갱신 및 저장
    login_box = driver.find_element(By.XPATH, '//*[@id="oneid"]')
    print(login_box.get_attribute('innerHTML'))
    pw_box = driver.find_element(By.XPATH, '//*[@id="_pw"]')
    login_button = driver.find_element(By.XPATH, '//*[@id="loginsubmit"]')
    USER = os.getenv("KUPID_ID")
    PASS = os.getenv("KUPID_PASSWORD")
    login_box.send_keys(USER)
    pw_box.send_keys(PASS)
    login_button.click()
    time.sleep(5)
    print(driver.find_element(By.XPATH, '//*[@id="header"]').get_attribute('innerHTML'))
    print('-------------------')
    notice_button = driver.find_element(By.XPATH, '//*[@id="header"]/div[2]/div/div/ul/li[6]/a')
    notice_button.click()
    time.sleep(3)
    pickle.dump(driver.get_cookies(), open("kupid_cookies.pkl", "wb"))
    
    cookies = pickle.load(open("kupid_cookies.pkl", 'rb'))
    for cookie in cookies:
        driver.add_cookie(cookie)

    time.sleep(1)
    
#일반공지, 장학금공지 탐색
for i in range(2):
    driver.get(url+notice_list[i])
    number_of_pages = len(driver.find_element(By.CLASS_NAME, 'paging').find_elements(By.CSS_SELECTOR, 'a')) - 3 #나타나는 페이지 수(최대 5)

    for k in range(number_of_pages):#페이지 순회하며 탐색

        articles = driver.find_elements(By.CSS_SELECTOR, 'tr')#각 게시글 요소
        article_tosearch = [False for i in range(len(articles)-1)]#해당 페이지 탐색 여부
        onearticle_datas = [0 for i in range(5)]#셀레니움 요소는 띄우는 화면이 달라질 시 같은 요소 불러오면 오류 발생. 따라서 데이터 저장 배열
        
        for j in range(len(articles)-1):#tr요소는 첫번째가 표 제목이다. 따라서 하나 빼고 탐색한다
            link = driver.find_elements(By.CSS_SELECTOR, 'tr')[j+1].find_element(By.CSS_SELECTOR, 'a')#javascript파일 여는 링크
            article_id = int(link.get_attribute('href').split(',')[2].strip("'"))
            cur.execute(f"select * from notice where id = {article_id};")
        
            if cur.fetchall() == []:#id로 저장된 게시글이 없다면 탐색
                article_tosearch[j] = True
                text = driver.find_elements(By.CSS_SELECTOR, 'tr')[j+1].find_elements(By.CSS_SELECTOR, 'td')
            
            
                onearticle_datas[0] = article_id#id
                onearticle_datas[1] = text[2].text.replace("\'", "\'\'")#   title
                onearticle_datas[2] = text[3].text.replace("\'", "\'\'")#   writer
                onearticle_datas[3] = text[0].text[0:10] #   date(등록일자)
                onearticle_datas[4] = text[4].text#   view

                driver.find_elements(By.CSS_SELECTOR, 'tr')[j+1].find_element(By.CSS_SELECTOR, 'a').send_keys(Keys.ENTER)
                time.sleep(1)

                # get Title
                title = driver.find_element(By.XPATH, '/html/body/div/div[2]/form/table/tbody/tr[5]/td').text.replace("\'", "\'\'")

                article_content = driver.find_element(By.XPATH, '/html/body/div/div[2]/form/table/tbody/tr[6]').get_attribute('innerHTML')
                article_content = article_content.replace("\'", "\'\'")
                attatchments = driver.find_elements(By.XPATH, '/html/body/div/div[2]/form/table/tbody/tr[7]')
                if attatchments != []:
                    attatchment_list = attatchments[0].find_elements(By.CSS_SELECTOR, 'a')
                    attatchments = attatchments[0].get_attribute('innerHTML')
                
                    for l in attatchment_list:
                        attatchment_link = l.get_attribute("href").split("'")[1]
                        attatchments = attatchments.replace(l.get_attribute("outerHTML").split('"')[1], "https://grw.korea.ac.kr"+attatchment_link)#여기는 조금 생각해 볼 것.
                    
                    attatchments = attatchments.replace("\'", "\'\'")
                    article_content = article_content + "\n" + attatchments
                #여기도 가독성 개선해볼 것...
                ids.append(article_id)
                cur.execute(f"insert into notice (id, title, content, writer, date, view, url, \"categoryId\") values ({article_id}, '{title}', '{article_content}', '{onearticle_datas[2]}', '{onearticle_datas[3]}', {onearticle_datas[4]}, -1, {i + 23});")
                conn.commit()
                time.sleep(0.5)
                driver.find_element(By.XPATH, '/html/body/div/div[2]/div/input[3]').send_keys(Keys.ENTER)
                time.sleep(1)

        driver.find_element(By.XPATH, f'//*[@id="Search"]/div[2]/div/a[{number_of_pages+2}]').send_keys(Keys.ENTER)
        time.sleep(1)

#학사일정공지는 생긴게 달라서 따로 탐색. 방법은 같으나 접근하는 요소의 위치가 달라짐
driver.get(url+notice_list[2])
number_of_pages = len(driver.find_element(By.CLASS_NAME, 'paging').find_elements(By.CSS_SELECTOR, 'a')) - 3 #나타나는 페이지 수(최대 5)

for k in range(number_of_pages):#페이지 순회하며 탐색

    articles = driver.find_elements(By.CSS_SELECTOR, 'tr')#각 게시글 요소
    article_tosearch = [False for i in range(len(articles)-1)]#해당 페이지 탐색 여부
    onearticle_datas = [0 for i in range(5)]#셀레니움 요소는 띄우는 화면이 달라질 시 같은 요소 불러오면 오류 발생. 따라서 데이터 저장 배열
        
    for j in range(len(articles)-1):#tr요소는 첫번째가 표 제목이다. 따라서 하나 빼고 탐색한다
        link = driver.find_elements(By.CSS_SELECTOR, 'tr')[j+1].find_element(By.CSS_SELECTOR, 'a')#javascript파일 여는 링크
        article_id = int(link.get_attribute('href').split(',')[2].strip("'"))
        cur.execute(f"select * from notice where id = {article_id};")
        
        if cur.fetchall() == []:#id로 저장된 게시글이 없다면 탐색
            article_tosearch[j] = True
            text = driver.find_elements(By.CSS_SELECTOR, 'tr')[j+1].find_elements(By.CSS_SELECTOR, 'td')
            
            
            onearticle_datas[0] = article_id#id
            onearticle_datas[1] = text[3].text.replace("\'", "\'\'")#   title
            onearticle_datas[2] = text[4].text.replace("\'", "\'\'")#   writer
            onearticle_datas[3] = text[1].text[0:10] #   date(등록일자)
            onearticle_datas[4] = text[5].text#   view

            driver.find_elements(By.CSS_SELECTOR, 'tr')[j+1].find_element(By.CSS_SELECTOR, 'a').send_keys(Keys.ENTER)
            time.sleep(1)
           # get Title
            title = driver.find_element(By.XPATH, '/html/body/div/div[2]/form/table/tbody/tr[5]/td').text.replace("\'", "\'\'")
            article_content = driver.find_element(By.XPATH, '/html/body/div/div[2]/form/table/tbody/tr[6]').get_attribute('innerHTML')
            article_content = article_content.replace("\'", "\'\'")
            attatchments = driver.find_elements(By.XPATH, '/html/body/div/div[2]/form/table/tbody/tr[7]')
            if attatchments != []:
                attatchment_list = attatchments[0].find_elements(By.CSS_SELECTOR, 'a')
                attatchments = attatchments[0].get_attribute('innerHTML')
                
                for l in attatchment_list:
                    attatchment_link = l.get_attribute("href").split("'")[1]
                    attatchments = attatchments.replace(l.get_attribute("outerHTML").split('"')[1], "https://grw.korea.ac.kr"+attatchment_link)#여기는 조금 생각해 볼 것.
                    
                attatchments = attatchments.replace("\'", "\'\'")
                article_content = article_content + "\n" + attatchments
                
            ids.append(article_id)
            cur.execute(f"insert into notice (id, title, content, writer, date, view, url, \"categoryId\") values ({article_id}, '{title}', '{article_content}', '{onearticle_datas[2]}', '{onearticle_datas[3]}', {onearticle_datas[4]}, -1, {25});")
            conn.commit()
            time.sleep(0.5)
            driver.find_element(By.XPATH, '/html/body/div/div[2]/div/input[3]').send_keys(Keys.ENTER)
            time.sleep(1)

    driver.find_element(By.XPATH, f'//*[@id="Search"]/div[2]/div/a[{number_of_pages+2}]').send_keys(Keys.ENTER)
    time.sleep(1)

           

driver.quit()#스크랩 끝나면 누수 방지 위해 selenium 종료      

os.system("taskkill /f /im chromedriver.exe /t")#크롬드라이버가 끝나도 꺼지지 않을 때를 대비하여 강제종료

display.stop()

cur.close()
conn.close()#sql 종료

requests.post('http://localhost:3050/notifications/kupid-crawler-notification', json={"ids": ids}, headers={
    'Authorization': 'Bearer ' + os.getenv("PY_TOKEN")
})

#추후 개선 사항: 가독성 개선, time.sleep대신 implicit/explicit wait으로 코드 속도 향
