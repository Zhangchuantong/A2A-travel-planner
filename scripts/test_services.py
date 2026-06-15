# scripts/test_services.py

from services.weather_service import get_weather
from services.ticket_service import search_train_tickets


def main():
    print("===== Test Weather Service =====")
    weather = get_weather("上海", "2025-08-02")
    print(weather)

    print("\n===== Test Ticket Service =====")
    tickets = search_train_tickets("北京", "上海", "2025-08-02")
    for ticket in tickets:
        print(ticket)


if __name__ == "__main__":
    main()
