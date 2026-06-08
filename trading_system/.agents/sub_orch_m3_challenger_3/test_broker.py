from src.broker.real_broker import RealBroker

def test_real_broker():
    broker = RealBroker()
    broker.connect()
    
    # Valid input
    print("Testing valid input...")
    res = broker.submit_order("AAPL", 10, "BUY")
    print("Valid order:", res)
    
    # Invalid qty types
    try:
        broker.submit_order("AAPL", 0, "BUY")
        print("Failed to reject qty=0")
    except ValueError as e:
        print("Caught qty=0:", e)
        
    try:
        broker.submit_order("AAPL", -10, "BUY")
        print("Failed to reject qty=-10")
    except ValueError as e:
        print("Caught qty=-10:", e)
        
    # Valid floating point?
    res2 = broker.submit_order("AAPL", 10.5, "BUY")
    print("Valid float order:", res2)
    
    # Invalid side
    try:
        broker.submit_order("AAPL", 10, "BUYING")
        print("Failed to reject invalid side")
    except ValueError as e:
        print("Caught invalid side:", e)
        
    # Unconnected broker
    broker2 = RealBroker()
    try:
        broker2.submit_order("AAPL", 10, "BUY")
        print("Failed to reject unconnected")
    except Exception as e:
        print("Caught unconnected:", e)

    # Empty symbol?
    res3 = broker.submit_order("", 10, "BUY")
    print("Empty symbol order:", res3)
    
test_real_broker()
