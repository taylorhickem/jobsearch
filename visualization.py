import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import match
import report

def load():
    match.load_db()
    report.load(db_only=True)

#tags

#01 frequency distribution of tags
def visualize_tags(tag_type,norm=True):
    match.update_tags()
    counts = match.get_tag_counts(tag_type,norm)
    plt.barh(counts.index, counts)
    plt.gca().invert_yaxis()
    plt.show()

#openings

#02 openings by week
def visualize_openings(width=2):
    byweek = report.get_openings_byweek()
    plt.bar(byweek.index,byweek,width=width)
    date_form = DateFormatter('%m-%d')
    plt.gca().xaxis.set_major_formatter(date_form)
    plt.show()