# scripts/test_ticket_mcp_logic.py

from mcp_servers.ticket_server import query_train_tickets_logic


def main():
    print("===== Test Ticket MCP Logic: success =====")
    result = query_train_tickets_logic(
        departure_city="富山",
        arrival_city="东京",
        travel_date="2026-06-20",
    )
    print(result)

    print("\n===== Test Ticket MCP Logic: not_found =====")
    result_not_found = query_train_tickets_logic(
        departure_city="富山",
        arrival_city="东京",
        travel_date="2026-07-01",
    )
    print(result_not_found)


if __name__ == "__main__":
    main()