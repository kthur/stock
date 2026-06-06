# Scope: Milestone 3

## Architecture
- `src/broker/real_broker.py`: Contains `RealBroker` implementation connecting to an API and submitting orders.
- `src/utils/report.py`: PDF report generator taking trade mock data and writing to a file.
- `tests/phase3/test_broker_reporting.py`: Acceptance tests for Milestone 3.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 3 | Broker & Reporting | Implement `RealBroker` with `connect()` and `submit_order()`, and a PDF generation function from mock trade data. | none | IN_PROGRESS |

## Interface Contracts
### Broker
- `RealBroker.connect()`: Establishes connection mock.
- `RealBroker.submit_order(...)`: Submits a dummy order.

### Reporting
- `generate_pdf_report(trade_data: list, file_path: str)`: Creates a `.pdf` file.
