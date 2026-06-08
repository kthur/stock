import sys
import os
sys.path.insert(0, os.getcwd())

with open(".agents/sub_orch_m3_challenger_4/trace.txt", "w") as f:
    f.write("Starting...\n")
    f.flush()

    try:
        from src.utils.report import generate_pdf_report
        f.write("Imported generate_pdf_report\n")
        f.flush()
    except Exception as e:
        f.write(f"Error importing generate_pdf_report: {e}\n")
        f.flush()

    try:
        from src.broker.real_broker import RealBroker
        f.write("Imported RealBroker\n")
        f.flush()
    except Exception as e:
        f.write(f"Error importing RealBroker: {e}\n")
        f.flush()

    f.write("Testing RealBroker...\n")
    f.flush()
    broker = RealBroker()
    broker.connect()
    receipt = broker.submit_order("AAPL", 10, "BUY")
    f.write(f"Receipt: {receipt}\n")
    f.flush()

    f.write("Testing pagination...\n")
    f.flush()
    trade_data = [{"symbol": f"SYM{i}", "qty": 10, "side": "BUY", "price": 100} for i in range(50)]
    pdf_path = os.path.join(os.getcwd(), ".agents", "sub_orch_m3_challenger_4", "test_pagination.pdf")
    generate_pdf_report(trade_data, pdf_path)
    f.write("Pagination test done\n")
    f.flush()

    f.write("Done\n")
