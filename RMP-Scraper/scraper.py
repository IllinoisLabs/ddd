import os.path, time
from datetime import datetime
from dateutil import relativedelta
import pandas
import requests
import json
import math

class RateMyProfScraper:
        def __init__(self,schoolid):
            self.UniversityId = schoolid
            self.professorlist = self.createprofessorlist()
            self.indexnumber = False

        def createprofessorlist(self):#creates List object that include basic information on all Professors from the IDed University
            tempprofessorlist = []
            num_of_prof = self.GetNumOfProfessors(self.UniversityId)
            num_of_pages = math.ceil(num_of_prof / 20)
            i = 1
            while (i <= num_of_pages):# the loop insert all professor into list
                page = requests.get("http://www.ratemyprofessors.com/filter/professor/?&page=" + str(
                    i) + "&filter=teacherlastname_sort_s+asc&query=*%3A*&queryoption=TEACHER&queryBy=schoolId&sid=" + str(
                    self.UniversityId))
                temp_jsonpage = json.loads(page.content)
                temp_list = temp_jsonpage['professors']
                tempprofessorlist.extend(temp_list)
                i += 1
            return tempprofessorlist

        def GetNumOfProfessors(self,id):  # function returns the number of professors in the university of the given ID.
            page = requests.get(
                "http://www.ratemyprofessors.com/filter/professor/?&page=1&filter=teacherlastname_sort_s+asc&query=*%3A*&queryoption=TEACHER&queryBy=schoolId&sid=" + str(
                    id))  # get request for page
            temp_jsonpage = json.loads(page.content)
            num_of_prof = temp_jsonpage[
                              'remaining'] + 20  # get the number of professors at William Paterson University
            return num_of_prof

        def SearchProfessor(self, ProfessorName):
            self.indexnumber = self.GetProfessorIndex(ProfessorName)
            self.PrintProfessorInfo()
            return self.indexnumber

        def GetProfessorIndex(self,ProfessorName):  # function searches for professor in list
            for i in range(0, len(self.professorlist)):
                if (ProfessorName == (self.professorlist[i]['tFname'] + " " + self.professorlist[i]['tLname'])):
                    return i
            return False  # Return False is not found

        def PrintProfessorInfo(self):  # print search professor's name and RMP score
            if self.indexnumber == False:
                print("error")
            else:
                print(self.professorlist[self.indexnumber])

        def PrintProfessorDetail(self,key):  # print search professor's name and RMP score
            if self.indexnumber == False:
                print("error")
                return "error"
            else:
                print(self.professorlist[self.indexnumber][key])
                return self.professorlist[self.indexnumber][key]

ILLINOIS_ID = 1112
PROFESSOR_LIST_FILE = "data/professor_list.dat"

def create_prof_data():
    print("Creating data")
    UIUC = RateMyProfScraper(ILLINOIS_ID)
    df = pandas.DataFrame(UIUC.professorlist)
    df.to_csv(path_or_buf=PROFESSOR_LIST_FILE, index_label="index")

def should_update_data():
    if not os.path.exists(PROFESSOR_LIST_FILE):
        print("Does not exist creating now")
        create_prof_data()
        return

    now = datetime.now()
    mtime_data = os.path.getmtime(PROFESSOR_LIST_FILE)
    file_mod_time = datetime.fromtimestamp(mtime_data)

    time_diff = relativedelta.relativedelta(now, file_mod_time)
    if time_diff.years > 0:
        print("time diff is greater than a year, creating now")
        create_prof_data()
        return
    print("professor data list is up to date")

def scraper_main():
    should_update_data()

    df = pandas.read_csv(filepath_or_buffer=PROFESSOR_LIST_FILE, index_col="index")
    print(df)

scraper_main()