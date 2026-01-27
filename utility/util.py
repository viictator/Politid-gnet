from datetime import date

def get_danish_date():
    today = date.today()
    months = ["januar", "februar", "marts", "april", "maj", "juni", 
              "juli", "august", "september", "oktober", "november", "december"]
    return f"{today.day}. {months[today.month-1]} {today.year}"

DANISH_TODAY = get_danish_date()
