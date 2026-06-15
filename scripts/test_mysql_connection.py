# scripts/test_services.py

from services.weather_service import get_weather
from services.ticket_service import search_train_tickets


def main():
    print("===== Test Weather Service =====")
    weather = get_weather("东京", "2026-06-20")
    print(weather)

    print("\n===== Test Ticket Service =====")
    tickets = search_train_tickets("富山", "东京", "2026-06-20")
    for ticket in tickets:
        print(ticket)


if __name__ == "__main__":
    main()