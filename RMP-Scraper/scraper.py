import os.path, time
from datetime import datetime
from dateutil import relativedelta
from bs4 import BeautifulSoup
import concurrent.futures
import threading
import pandas
import requests
import json
import math

ILLINOIS_ID = 1112
PROFESSOR_LIST_FILE = "data/professor_list.dat"
REVIEWS_FILE = "data/reviews.json"
COL_TO_WRITE = [
    "tDept",
    "tFname",
    "tMiddlename",
    "tLname",
    "tid",
    "tNumRatings",
    "rating_class",
    "overall_rating",
]
thread_local = threading.local()


class ProfListScraper:
    def __init__(self, schoolid):
        self.UniversityId = schoolid
        self.professorlist = self.createprofessorlist()

    def createprofessorlist(
        self,
    ):  # creates List object that include basic information on all Professors from the IDed University
        tempprofessorlist = []
        num_of_prof = self.GetNumOfProfessors(self.UniversityId)
        num_of_pages = math.ceil(num_of_prof / 20)
        i = 1
        while i <= num_of_pages:  # the loop insert all professor into list
            page = requests.get(
                "http://www.ratemyprofessors.com/filter/professor/?&page="
                + str(i)
                + "&filter=teacherlastname_sort_s+asc&query=*%3A*&queryoption=TEACHER&queryBy=schoolId&sid="
                + str(self.UniversityId)
            )
            temp_jsonpage = json.loads(page.content)
            temp_list = temp_jsonpage["professors"]
            tempprofessorlist.extend(temp_list)
            i += 1
        return tempprofessorlist

    def GetNumOfProfessors(
        self, id
    ):  # function returns the number of professors in the university of the given ID.
        page = requests.get(
            "http://www.ratemyprofessors.com/filter/professor/?&page=1&filter=teacherlastname_sort_s+asc&query=*%3A*&queryoption=TEACHER&queryBy=schoolId&sid="
            + str(id)
        )  # get request for page
        temp_jsonpage = json.loads(page.content)
        num_of_prof = (
            temp_jsonpage["remaining"] + 20
        )  # get the number of professors at William Paterson University
        return num_of_prof

class ReviewsScraper:
    def __init__(self, id_list):
        self.id_list = id_list
        self.update_reviews()
        # self.reviews = pandas.read_json(REVIEWS_FILE)

    def update_reviews(self):
        if not os.path.exists(REVIEWS_FILE):
            print("Data doesn't exist, creating file now")
            self.scrape_reviews()
            return

        now = datetime.now()
        mtime_data = os.path.getmtime(REVIEWS_FILE)
        file_mod_time = datetime.fromtimestamp(mtime_data)

        time_diff = relativedelta.relativedelta(now, file_mod_time)
        if time_diff.years > 0:
            print("time diff is greater than a year, creating now")
            self.scrape_reviews()

    def get_session(self):
        if not hasattr(thread_local, "session"):
            thread_local.session = requests.Session()
        return thread_local.session

    def scrape_worker(self, id):
        BASE_URL = "https://www.ratemyprofessors.com/ShowRatings.jsp?tid="
        session = self.get_session()
        with session.get(BASE_URL + str(id)) as response:
            print(f"Currently at professor {id}")
            soup = BeautifulSoup(response.text, "html.parser")
            reviews_soup = [
                li for li in soup.find_all("div", "Rating__RatingBody-sc-1rhvpxz-0")
            ]
            reviews = list()
            for review in reviews_soup:
                if not reviews_soup:
                    break

                reviews.append(
                    {
                        "date": review.select_one(
                            ".TimeStamp__StyledTimeStamp-sc-9q2r30-0"
                        ).text,
                        "message": review.select_one(
                            ".Comments__StyledComments-dzzyvm-0"
                        ).text,
                        "class": review.select_one(
                            ".RatingHeader__StyledClass-sc-1dlkqw1-2"
                        ).text,
                        "quality": review.find_all(
                            "div", "CardNumRating__CardNumRatingNumber-sc-17t4b9u-2"
                        )[0].text,
                        "difficulty": review.find_all(
                            "div", "CardNumRating__CardNumRatingNumber-sc-17t4b9u-2"
                        )[1].text,
                    }
                )

            name = soup.select_one(".NameTitle__Name-dowf0z-0")
            return {
                "name": name.text if name else "No Name" ,
                "reviews": reviews,
            }
        return dict()

    def scrape_reviews(self):
        num_workers = 10
        review_list = list()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executer:
            for professor in executer.map(self.scrape_worker, self.id_list):
                review_list.append(professor)

        with open(REVIEWS_FILE, "w") as outfile:
            json.dump(review_list, outfile)


def create_prof_data():
    print("Creating data")
    UIUC = ProfListScraper(ILLINOIS_ID)
    df = pandas.DataFrame(UIUC.professorlist)
    df.to_csv(
        path_or_buf=PROFESSOR_LIST_FILE, index_label="index", columns=COL_TO_WRITE
    )


def update_prof_data():
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


def update_reviews_data(prof_df):
    prof_id_list = prof_df["tid"].values.tolist()
    rev_scraper = ReviewsScraper(prof_id_list)


def scraper_main():
    update_prof_data()
    prof_df = pandas.read_csv(filepath_or_buffer=PROFESSOR_LIST_FILE, index_col="index")
    update_reviews_data(prof_df)


scraper_main()
