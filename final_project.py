from textwrap import indent
import matplotlib.pyplot as plt
import requests
import sqlite3
import json
import csv
import os

#PULL EVENT ID FROM SEAT GEEK API
def get_sg_events(pg_num):
    url = "https://api.seatgeek.com/2/events?client_id=MjY1NDY4OTd8MTY0OTk0NTE3My42OTY4NTg2&client_secret=a005a2e60e8f8d3e548cc78a3371d72d28b95a3d4b5a3070f41db576d70cd3ad&type=concert&per_page=25&page="+str(pg_num)
    response = requests.get(url)
    data = json.loads(response.content)

    concerts_only = []
    for event in data['events']:
        if event['type'] == 'concert':
            concerts_only.append(event["id"])
    return concerts_only

#GET EVENT INFO AND CREATE JSON OBJ FOR SEAT GEEK
def create_sg_json(concert_list):
    info_list = []
    for event_id in concert_list:
        base_url = "https://api.seatgeek.com/2/events/{}?client_id=MjY1NDY4OTd8MTY0OTk0NTE3My42OTY4NTg2&client_secret=a005a2e60e8f8d3e548cc78a3371d72d28b95a3d4b5a3070f41db576d70cd3ad"
        formatted_url = base_url.format(event_id)
        response = requests.get(formatted_url)
        information = json.loads(response.content)
        info_list.append(information)
    return info_list

#GET INFO FROM TICKET MASTER API
def get_tm_events():
    pages_lst=[1,2,3,4]
    lst_events =[]
    for page in pages_lst:
        baseURL='https://app.ticketmaster.com/discovery/v2/events.json?apikey=vpuocOuAAzZoQtLZalLRNHbMxxuecGWU&size=200&page={}&classificationName=Music'
        formatedURL = baseURL.format(page)
        #print(formatedURL)
        response_API = requests.get(formatedURL)
        data = json.loads(response_API.text)
        #print(data['_embedded'])
        #print("NEW PAGE __________________")
        for i in range(len(data['_embedded']['events'])):
            lst_events.append(data['_embedded']['events'][i])
    #print(len(lst_events))
    event_concert_lst=[]
    for i in range(len(lst_events)):
        event_classification_id= lst_events[i]['classifications'][0]['segment']['id']
        if event_classification_id == 'KZFzniwnSyZfZ7v7nJ':
            if 'priceRanges' in lst_events[i]:
                if 'name' in lst_events[i]['_embedded']['venues'][0]:
                    event_concert_lst.append(lst_events[i])
    
    #print(len(event_concert_lst))
    return event_concert_lst

# CREATE DATABASE
def setUpDatabase(db_name):
    path = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(path+'/'+db_name)
    cur = conn.cursor()
    return cur, conn

# CREATE TABLE FOR EVENT INFORMATION IN DATABASE AND ADD INFORMATION FOR SEAT GEEK
def create_sg_events_table(cur, conn):
    cur.execute("CREATE TABLE IF NOT EXISTS Seat_Geek_Events (event_id INTEGER UNIQUE PRIMARY KEY, event_title TEXT, performers TEXT, dates TEXT, location TEXT, max_price INTEGER, min_price INTEGER)")
    conn.commit()

def add_sg_events(info, cur, conn):
    for i in info:
        event_id = int(i['id'])
        event_title = i['title']
        dates = i['datetime_local']
        performers = i['performers'][0]['name']
        location = i['venue']['name_v2']
        max_price = i['stats']['highest_price']
        min_price = i['stats']['lowest_price']
        if max_price is None and min_price is None:
            continue
        else:
            cur.execute("INSERT OR IGNORE INTO Seat_Geek_Events (event_id, event_title, dates, performers, location, max_price, min_price) VALUES (?,?,?,?,?,?,?)", (event_id, event_title, dates, performers, location, max_price, min_price))
            conn.commit() 

# CREATE TABLE FOR TICKET MASTER INFORMATION IN DATABASE
def create_tm_table(cur, conn):
    cur.execute("CREATE TABLE IF NOT EXISTS Ticket_Master_Events (event_id TEXT UNIQUE PRIMARY KEY, event_title TEXT, date TEXT, location TEXT, max_price INTEGER, min_price INTEGER)")
    conn.commit()

# ADD EVENT INFORMATION FOR TICKET MASTER
def add_tm_info(data, cur, conn):
    for event in data:
        id = event['id']
        title= event['name']
        date = event['dates']['start']['localDate']
        location = event['_embedded']['venues'][0]['name']
        min_price= int(event['priceRanges'][0]['max'])
        max_price = int(event['priceRanges'][0]['min'])
        cur.execute(
            """
            INSERT OR IGNORE INTO Ticket_Master_Events (event_id, event_title, date, location, max_price, min_price)
            VALUES (?, ?, ?, ?,?, ?)
            """,
            (id, title, date, location, min_price, max_price,)
        )
    conn.commit()

#CALCULATING AVERAGE PRICES FOR SEAT GEEK EVENTS
def calc_sg_avgs(cur, conn):
    cur.execute("""SELECT event_title, max_price, min_price
    FROM Seat_Geek_Events
    """ )
    results = cur.fetchall()

    events = []
    avgs = []
    for result in results:
        event = result[0]
        events.append(event)
        sg_avg = (result[1] + result[2])/2
        avgs.append(sg_avg)
    return [events, avgs]
    
#CALCULATING AVERAGE PRICES FOR TICKET MASTER EVENTS
def calc_tm_avgs(cur, conn):
    cur.execute("""SELECT event_title, max_price, min_price
    FROM Ticket_Master_Events 
    """ )
    results = cur.fetchall()

    events = []
    avgs = []
    for result in results:
        event = result[0]
        events.append(event)
        sg_avg = (result[1] + result[2])/2
        avgs.append(sg_avg)
    return [events, avgs]

#CALCULATING MEAN PRICE FOR SEAT GEEK 
def calc_sg_mean(cur, conn):
    avgs = calc_sg_avgs(cur, conn)[1]
    count = 0
    total = 0
    for avg in avgs:
        total += avg
        count += 1
    mean = round(total/count, 2)
    return mean

#CALCULATING MEAN PRICE FOR TICKET MASTER 
def calc_tm_mean(cur, conn):
    avgs = calc_tm_avgs(cur, conn)[1]
    count = 0
    total = 0
    for avg in avgs:
        total += avg
        count += 1
    mean = round(total/count, 2)
    return mean


#WRITE CALCULATIONS INTO CSV FOR SEAT GEEK
def write_sg_csv(cur, conn):
    events = calc_sg_avgs(cur, conn)[0]
    avgs = calc_sg_avgs(cur, conn)[1]
    mean = calc_sg_mean(cur, conn)

    event_avgs = zip(events, avgs)
    header = ['Event Title', 'Seat Geek Average Ticket Prices']

    base_path = os.path.abspath(os.path.dirname(__file__))
    full_path = os.path.join(base_path, "sg_avg_prices.csv")
    with open(full_path, "w", newline='') as f:
        writer = csv.writer(f, delimiter = ',')
        writer.writerow(header)
        for tup in event_avgs:
            writer.writerow(tup)
        writer.writerow(("Mean Price", mean))
    f.close()

#WRITE CALCULATIONS INTO CSV FOR TICKET MASTER
def write_tm_csv(cur, conn):
    events = calc_tm_avgs(cur, conn)[0]
    avgs = calc_tm_avgs(cur, conn)[1]
    mean = calc_tm_mean(cur, conn)

    event_avgs = zip(events, avgs)
    header = ['Event Title', 'Ticket Master Average Ticket Prices']

    base_path = os.path.abspath(os.path.dirname(__file__))
    full_path = os.path.join(base_path, "tm_avg_prices.csv")
    with open(full_path, "w", newline='') as f:
        writer = csv.writer(f, delimiter = ',')
        writer.writerow(header)
        for tup in event_avgs:
            writer.writerow(tup)
        writer.writerow(("Mean Price", mean))

#MINIMUM PRICE VISUAL FOR SEAT GEEK
def min_price_sg_visual(cur, conn):
    cur.execute("""SELECT event_title, min_price
    FROM Seat_Geek_Events 
    """ )
    results = cur.fetchall()
    sorted_results = sorted(results, key= lambda t: t[1], reverse = False)

    x = []
    y = []
    for concert, min_price in sorted_results:
        x.append(concert)
        y.append(min_price)
    plt.bar(x[:3],y[:3])
    plt.ylabel('Minimum Ticket Price in USD')
    plt.xlabel('Event Title')
    plt.xticks(x[:3],  rotation=15)
    plt.title('Top 3 Least Expensive Concerts From Seat Geek')
    plt.show()

#MAXIMUM PRICE VISUAL FOR SEAT GEEK
def max_price_sg_visual(cur, conn):
    cur.execute("""SELECT event_title, max_price
    FROM Seat_Geek_Events 
    """ )
    results = cur.fetchall()
    sorted_results = sorted(results, key= lambda t: t[1], reverse = True)

    x = []
    y = []
    for concert, max_price in sorted_results:
        x.append(concert)
        y.append(max_price)
    plt.bar(x[:3],y[:3])
    plt.ylabel('Maximum Ticket Price in USD')
    plt.xlabel('Event title')
    plt.xticks(x[:3],  rotation=15)
    plt.title('Top 3 Most Expensive Concerts From Seat Geek')
    plt.show()

#MAXIMUM PRICE VISUAL FOR TICKET MASTER
def max_price_tm_visual(cur, conn):
    cur.execute("""SELECT event_title, max_price
    FROM Ticket_Master_Events 
    """ )
    results = cur.fetchall()
    sorted_results = sorted(results, key= lambda t: t[1], reverse = True)

    x = []
    y = []
    for concert, max_price in sorted_results:
        x.append(concert)
        y.append(max_price)
    plt.bar(x[:5], y[:5])
    plt.ylabel('Maximum Ticket Price in USD')
    plt.xlabel('Event title')
    plt.xticks(x[:5],  rotation=15)
    plt.title('Top 3 Most Expensive Concerts From Ticket Master')
    plt.show()

#AVERAGE PRICE VISUAL COMAPRING TICKET MASTER AND SEAT GEEK
def avg_price_visual(cur, conn):
    sg_mean = calc_sg_mean(cur, conn)
    tm_mean = calc_tm_mean(cur, conn)
    x = ["Mean Ticket Price for Seat Geek", "Mean Ticket Price for Ticket Master"]
    y = [sg_mean, tm_mean]
    plt.bar(x,y)
    plt.ylabel('Average Ticket Price in USD')
    plt.xlabel('Ticket Platform')
    plt.title('Mean Price for Concert')
    plt.show()

#MAIN FUNCTION
def main():
    page_number = input("Page Number: ")
    concert_list = get_sg_events(page_number)
    info_list = create_sg_json(concert_list)
    cur, conn = setUpDatabase("ticket_platforms.db")
    
    create_sg_events_table(cur,conn)
    add_sg_events(info_list, cur, conn)

    data = get_tm_events()
    create_tm_table(cur, conn)
    add_tm_info(data, cur, conn)

    calc_sg_avgs(cur, conn)
    calc_sg_mean(cur, conn)

    calc_tm_avgs(cur, conn)
    calc_tm_mean(cur, conn)

    write_sg_csv(cur, conn)
    write_tm_csv(cur, conn)

    min_price_sg_visual(cur,conn)
    max_price_sg_visual(cur, conn)
    max_price_tm_visual(cur, conn)
    avg_price_visual(cur, conn)

main()
