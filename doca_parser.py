from selenium import webdriver
import time
import json
import os


class DocaParser(object):

    def __init__(self, driver, config, patients, log_index=0):
        self.driver = driver
        self.patients = patients
        self.cookies = config
        self.log_index = log_index
        self.errors = []

    def write_log(self, index):
        with open(f'logs_{index}.txt', 'a') as file:
            file.writelines(self.errors)
    
    def get_payload(self, data):
        payload = None
        if len(data) > 2:
            payload = {
                'name': data[1],
                'surname': data[0],
                'patronymic': data[2]
            }
        elif len(data) > 1:
            payload = {
                'name': data[1],
                'surname': data[0],
                'patronymic': ''
            }
        else:
            payload = {
                'name': '',
                'surname': data[0],
                'patronymic': ''
            }
        return payload

    def switch_to_frame_by_xpath(self, xpath):
        print(f'Переключение фрейма {xpath}...')
        self.driver.switch_to.frame(self.driver.find_element_by_xpath(xpath))

    def parse(self, start=0, end=0):
        if end <= 0:
            end = len(self.patients)
        total_an = 0
        total_his = 0
        errors = 0
        total_patients = end - start
        for i in range(start, end):
            print(f'# {i - start + 1} из {total_patients} [id: {i}]')
            data = self.patients[i].split()
            payload = self.get_payload(data)
            if payload is not None:
                try:
                    self.open()
                    info = self.find_patient_info(payload)
                    total_an += info[0]
                    total_his += info[1]
                    # histories_count = info[2] - 1
                    # while histories_count > 0:
                    #     self.open()
                    #     info = self.find_patient_info(payload, histories_count)
                    #     total_an += info[0]
                    #     total_his += info[1]
                    #     histories_count -= 1
                except Exception as e:
                    errors += 1
        if len(self.errors) > 0:
            self.write_log(self.log_index)
        print(f'Разобранно {total_patients - errors} / {total_patients}')
        print(f'Удалось получить - анализы: {total_an}, ИБ: {total_his}')

    def open(self):
        doca_url = 'http://docavlad/docaplus/main/main.php?first=1'
        print(f'Открытие {doca_url}...')
        try:
            self.driver.get(doca_url)
            for cookie in self.cookies:
                self.driver.add_cookie({'name': cookie['name'], 'value': cookie['value']})
            self.driver.get(doca_url)
        except Exception as e:
            self.errors.append(f'[{time.ctime()}] {e}')
            print(e)
    
    def save_to_file(self, file_name, text):
        print(f'Сохранение в файл {file_name}...')
        with open(file_name, 'w', encoding='utf-8') as file:
            file.write(text)
    
    def save_to_json(self, file_name, data):
        print(f'Сохранение в файл{file_name}...')
        with open(file_name, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False)

    def find_patient_info(self, patient, history_num=1):
        print(f'Поиск информации о пациенте [{patient["surname"] + patient["name"] + patient["patronymic"]}]...')
        try:
            self.switch_to_frame_by_xpath("//frame[@name='main_menu_window']")
            archive_btn = self.driver.find_element_by_id('sid9')
            archive_btn.click()
            self.driver.switch_to.default_content()
            self.switch_to_frame_by_xpath("//frame[@name='doc_window']")
            surname = self.driver.find_element_by_xpath("//input[@name='fam']")
            name = self.driver.find_element_by_xpath("//input[@name='nam']")
            patronymic = self.driver.find_element_by_xpath("//input[@name='ots']")
            submit_btn = self.driver.find_element_by_xpath("//input[@name='Submit']")
            surname.clear()
            if len(patient['surname']) > 0:
                surname.send_keys(patient['surname'])
            name.clear()
            if len(patient['name']) > 0:
                name.send_keys(patient['name'])
            patronymic.clear()
            if len(patient['patronymic']) > 0:
                patronymic.send_keys(patient['patronymic'])
            submit_btn.click()
            patient_links = self.driver.find_elements_by_tag_name('a')
            patient_links[0].click()
            hos_links = self.driver.find_elements_by_xpath("//td[@title='№ Истории болезни']/a")
            print(len(hos_links))
            # hos_links = self.driver.find_elements_by_tag_name('a')
            print(f'История {history_num} из {len(hos_links)}')
            hos = self.hos_info(hos_links[0], patient, history_num - 1)
            result = [hos[0], hos[1], len(hos_links)]
            return result
        except Exception as e:
            self.errors.append(f'[{time.ctime()} in find_patient_info] [{patient["surname"] + patient["name"] + patient["patronymic"]}] {e}')
            print(e)
            return 0
    
    def hos_info(self, hos_link, patient, num=0):
        hos_link.click()
        an = self.analyzes(patient, num)
        his = self.history(patient, num)
        return [an, his]
    
    def history(self, patient, num=0):
        print('Просмотр истории...')
        try:
            history_link = self.driver.find_element_by_id('sid4')
            history_link.click()
            all_btn = self.driver.find_element_by_xpath("//a[text()='Вывести все документы']")
            all_btn.click()
            self.switch_to_frame_by_xpath("//frame[@name='view_window']")
            file_name = patient['surname'] + patient['name'] + patient['patronymic'] + '_history_' + str(num) + '.html'
            self.save_to_file(file_name, self.driver.page_source)
            return 1
        except Exception as e:
            self.errors.append(f'[{time.ctime()} in history] [{patient["surname"] + patient["name"] + patient["patronymic"]}] {e}')
            print(e)
            return 0

    def analyzes(self, patient, num=0):
        print('Получение анализов...')
        try:
            an_link = self.driver.find_element_by_id('sid8')
            an_link.click()
            file_name = patient['surname'] + patient['name'] + patient['patronymic'] + '_analyzes_' + str(num) + '.html'
            self.save_to_file(file_name, self.driver.page_source)
            self.go_next()
            return 1
        except Exception as e:
            self.errors.append(f'[{time.ctime()} in analyzes] [{patient["surname"] + patient["name"] + patient["patronymic"]}] {e}')
            print(e)
            return 0
    
    def go_next(self):
        print('Переход далее...')
        try:
            next_btn = self.driver.find_element_by_xpath("//input[@onclick='GoNext()']")
            next_btn.click()
        except Exception as e:
            self.errors.append(f'[{time.ctime()} in nex] {e}')
            print(e)


def load_config(file_name):
        print('Загрузка конфигурации...')
        data = {}
        with open(file_name, 'r') as file:
            data = json.load(file)
        return data['cookie']

def load_patients(txt):
        print('Загрузка списка пациентов....')
        lines = []
        with open(txt, 'r') as file:
            lines = file.readlines()
        print(f'Загружено {len(lines)} строк')
        return lines


def main(shutdown=False, headless=True):
    print('Добро пожаловать в DocA Parser!\nПожалуйста, подождите пока программа загрузит необходимые ресурсы...\n')
    options = webdriver.ChromeOptions()
    options.headless = headless
    config = load_config('config.json')
    patients = load_patients('patients.txt')
    driver = webdriver.Chrome(options=options)
    parser = DocaParser(driver, config, patients)
    print('Доступные команды:\n  exit\n  start [start=0, end=max]\n  count')
    while True:
        cmd = input('> ').split()
        try:
            if cmd[0] == 'exit':
                break
            elif cmd[0] == 'start':
                start_time = time.perf_counter()
                if len(cmd) > 2:
                    parser.parse(int(cmd[1])-1, int(cmd[2]))
                elif len(cmd) > 1:
                    parser.parse(end=int(cmd[1]))
                else:
                    parser.parse()
                result_time = time.perf_counter() - start_time

                print('Время выполнения программы %.2f секунд' % result_time)
            elif cmd[0] == 'count':
                print(len(patients))
            else:
                print('Неверная команда!')
        except:
            print('Неверная команда!')

    if shutdown:
        os.system('shutdown /s /t 1')
    driver.quit()


if __name__ == "__main__":
    main()